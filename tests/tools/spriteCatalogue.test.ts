// Opt-in: the catalogue of everything to model in Blender (DECISIONS.md D15).
//
//   CATALOGUE_OUT=reference/models npm run catalogue
//
// Plays every level's world (events and enemies, tests/sim/worldDriver.ts) and records each enemy
// drawn: its sheet, size and animation frames. Frames that one enemy cycles through, and frames
// whose pictures are identical, are one model. Adds every player ship with its banking frames.
// For each model it writes reference/models/<name>/:
//   sprite.json   what the model replaces (the SpriteModelEntry sprites), how often and where it's
//                 seen, every frame's pixels as palette indices, and those indices' colours
//   frame-*.png   each frame, 1 sprite px = 12 image px, transparent background
//   contact.png   all frames side by side on a checkerboard
//   assembly.png  for a piece of a bigger object (a boss is several 2x2 enemies side by side, each
//                 with its own model): the whole object as seen in game, with this piece outlined
// and reference/models/catalogue.json, every model in priority order. The output is derived from
// the game data, so it stays out of git (reference/ is ignored).
import { describe, test, vi } from "vitest";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { crc32, deflateSync } from "node:zlib";
import { parseEpisodeScript, parsePalettes, vga6To8 } from "../../src/data";
import { decodeSprite2 } from "../../src/data/sprites";
import { hasData, readData } from "../data/dataDir";

const OUT = process.env.CATALOGUE_OUT ?? "";
const MAX_TICKS = Number(process.env.TICKS ?? 30000);
const SCALE = 12;

interface FrameStat {
  sheet: string;
  size: 1 | 2;
  index: number;
  ticks: number;
  levels: Set<string>;
  air: number;
  ground: number;
  palettes: Map<number, number>;
}

/** "newsh1.shp" -> "newsh1", "newsh#.shp" -> "newsh-hash", "tyrian.shp#8" -> "tyrian8". */
export function sheetSlug(id: string): string {
  const special: Record<string, string> = { "#": "-hash", "^": "-caret", "@": "-at", "~": "-tilde", "&": "-amp" };
  const m = /^newsh(.)\.shp$/.exec(id);
  if (m) return `newsh${special[m[1]] ?? m[1]}`;
  const t = /^tyrian\.shp#(\d+)$/.exec(id);
  if (t) return `tyrian${t[1]}`;
  return id.replace(/[^a-z0-9]+/gi, "-");
}

/** A frame's picture: 12x14 (size 1) or the 2x2 block index, +1, +19, +20 (24x28), -1 = transparent. */
function compose(sheet: Uint8Array, size: 1 | 2, index: number): Int16Array {
  const w = size * 12, h = size * 14;
  const out = new Int16Array(w * h).fill(-1);
  const tiles = size === 1 ? [[0, 0, 0]] : [[0, 0, 0], [1, 12, 0], [19, 0, 14], [20, 12, 14]];
  for (const [offset, ox, oy] of tiles) {
    const s = decodeSprite2(sheet, index + offset);
    for (let y = 0; y < Math.min(14, s.height); y++)
      for (let x = 0; x < 12; x++) out[(oy + y) * w + ox + x] = s.pixels[y * 12 + x];
  }
  return out;
}

function writePng(path: string, width: number, height: number, rgba: Uint8Array): void {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) raw.set(rgba.subarray(y * width * 4, (y + 1) * width * 4), y * (width * 4 + 1) + 1);
  const chunk = (type: string, data: Buffer) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 6, 0, 0, 0], 8);
  writeFileSync(path, Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", Buffer.alloc(0)),
  ]));
}

/** Draw a picture into an RGBA image at (ox, oy), `scale` image px per sprite px. */
function paint(img: Uint8Array, imgW: number, pic: Int16Array, w: number, h: number, rgb: (i: number) => number[], ox: number, oy: number, scale: number) {
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const c = pic[y * w + x];
      if (c < 0) continue;
      const [r, g, b] = rgb(c);
      for (let dy = 0; dy < scale; dy++)
        for (let dx = 0; dx < scale; dx++) img.set([r, g, b, 255], ((oy + y * scale + dy) * imgW + ox + x * scale + dx) * 4);
    }
}

class UnionFind {
  private parent = new Map<string, string>();
  find(a: string): string {
    if (!this.parent.has(a)) this.parent.set(a, a);
    let r = a;
    while (this.parent.get(r) !== r) r = this.parent.get(r)!;
    this.parent.set(a, r);
    return r;
  }
  union(a: string, b: string): void {
    const ra = this.find(a), rb = this.find(b);
    if (ra !== rb) this.parent.set(rb, ra);
  }
}

async function playLevel(ep: number, section: number, onTick: (items: unknown[], palette: number) => void): Promise<void> {
  vi.resetModules();
  const { mt_srand } = await import("../../src/sim/mtrand");
  const { DIFFICULTY_NORMAL, g, newPlayer } = await import("../../src/sim/state");
  const { initLevelWorld, loadLevel } = await import("../../src/sim/tyrian2");
  const { drawList } = await import("../../src/sim/draw");
  const { worldTick } = await import("../sim/worldDriver");
  g.player = [newPlayer(), newPlayer()];
  g.difficultyLevel = DIFFICULTY_NORMAL;
  g.initialDifficulty = DIFFICULTY_NORMAL;
  g.background2 = true;
  g.constantPlay = true;
  const files = { get: (n: string) => (hasData(n) ? readData(n) : undefined) };
  mt_srand(1);
  loadLevel(files, ep, section);
  initLevelWorld();
  g.player[0].x = 100;
  g.player[0].y = 180;
  g.player[0].is_alive = true;
  let after = -1;
  for (let tick = 0; tick < MAX_TICKS && after !== 0; tick++) {
    worldTick();
    onTick(drawList.items, drawList.palette);
    if (after > 0) after--;
    else if (after < 0 && g.endLevel) after = 300;
  }
}

describe.skipIf(!OUT || !hasData("levels1.dat", "tyrian1.lvl", "palette.dat", "tyrian.shp"))("sprite catalogue", () => test("catalogue", async () => {
  const { ENEMY_KEY_BASE } = await import("../../src/sim/tyrian2");
  const { Pass } = await import("../../src/sim/draw");
  const stats = new Map<string, FrameStat>();
  const sheets = new Map<string, Uint8Array>();
  const uf = new UnionFind();
  const levelsPlayed: string[] = [];
  // Pieces of bigger objects: 2x2 enemies drawn exactly side by side (centres 24 or 28 px apart).
  const touching = new Map<string, number>();
  /** The biggest cluster of touching pieces seen with each frame in it, for assembly.png. */
  const clusterOf = new Map<string, { key: string; cx: number; cy: number }[]>();

  for (let ep = 1; ep <= 4; ep++) {
    const script = parseEpisodeScript(readData(`levels${ep}.dat`));
    for (const sec of script.sections) {
      if (!sec.lines.some((l) => l.startsWith("]L"))) continue;
      const level = `${ep}.${sec.number}`;
      const enemyFirst = new Map<number, string>();
      try {
        await playLevel(ep, sec.number, (items, palette) => {
          const at = new Map<string, { key: string; cx: number; cy: number }>();
          for (const d of items as import("../../src/sim/draw").Draw[]) {
            if (d.kind !== "sprite2" || d.groupIndex < 0 || !d.groupFirst) continue;
            if (compose(d.sheet.data, d.groupSize, d.groupIndex).every((c) => c < 0)) continue;
            sheets.set(d.sheet.id, d.sheet.data);
            const key = `${d.sheet.id}|${d.groupSize}|${d.groupIndex}`;
            let s = stats.get(key);
            if (!s) stats.set(key, (s = { sheet: d.sheet.id, size: d.groupSize, index: d.groupIndex, ticks: 0, levels: new Set(), air: 0, ground: 0, palettes: new Map() }));
            s.ticks++;
            s.levels.add(level);
            if (d.pass === Pass.GroundEnemies) s.ground++;
            else s.air++;
            s.palettes.set(palette, (s.palettes.get(palette) ?? 0) + 1);
            // One enemy's frames are one model.
            const enemy = (d.key - ENEMY_KEY_BASE) >> 2;
            const first = enemyFirst.get(enemy);
            if (first === undefined) enemyFirst.set(enemy, key);
            else uf.union(first, key);
            if (d.groupSize === 2) {
              const cx = d.x + d.groupDx, cy = d.y + d.groupDy;
              at.set(`${cx},${cy}`, { key, cx, cy });
            }
          }
          // Clusters of touching pieces this tick (flood fill over the 8 neighbours).
          const seen = new Set<string>();
          for (const [pos, piece] of at) {
            if (seen.has(pos)) continue;
            const cluster: typeof piece[] = [];
            const stack = [pos];
            seen.add(pos);
            while (stack.length) {
              const p = at.get(stack.pop()!)!;
              cluster.push(p);
              for (const dx of [-24, 0, 24])
                for (const dy of [-28, 0, 28]) {
                  const q = `${p.cx + dx},${p.cy + dy}`;
                  const n = at.get(q);
                  if (!n || (dx === 0 && dy === 0)) continue;
                  if (p.key < n.key) touching.set(`${p.key}\n${n.key}`, (touching.get(`${p.key}\n${n.key}`) ?? 0) + 1);
                  if (!seen.has(q)) {
                    seen.add(q);
                    stack.push(q);
                  }
                }
            }
            if (cluster.length < 2) continue;
            for (const c of cluster) if ((clusterOf.get(c.key)?.length ?? 0) < cluster.length) clusterOf.set(c.key, cluster);
          }
        });
        levelsPlayed.push(level);
      } catch (e) {
        console.log("level", level, "failed:", String(e));
      }
    }
  }

  // Identical pictures are one model.
  const byPicture = new Map<string, string>();
  for (const [key, s] of stats) {
    const pic = compose(sheets.get(s.sheet)!, s.size, s.index).join(",");
    const other = byPicture.get(pic);
    if (other) uf.union(other, key);
    else byPicture.set(pic, key);
  }

  const palettes = parsePalettes(readData("palette.dat"));
  const rgbOf = (pal: number) => (i: number) => [0, 1, 2].map((k) => vga6To8(palettes[pal][i * 3 + k]));

  interface Model {
    name: string;
    sprites: { sheet: string; size: 1 | 2; frames: number[]; bank?: { step: number; max: number } }[];
    kind: "ship" | "air" | "ground";
    ticks: number;
    levels: string[];
    palette: number;
    pictures: { sheet: string; size: 1 | 2; index: number; pic: Int16Array }[];
    assembly?: string;
    assemblyPieces?: string[];
    assemblyView?: { key: string; cx: number; cy: number }[];
  }
  const components = new Map<string, FrameStat[]>();
  for (const key of stats.keys()) {
    const root = uf.find(key);
    if (!components.has(root)) components.set(root, []);
    components.get(root)!.push(stats.get(key)!);
  }

  const models: Model[] = [];
  for (const frames of components.values()) {
    frames.sort((a, b) => b.ticks - a.ticks);
    const ticks = frames.reduce((n, f) => n + f.ticks, 0);
    const pal = new Map<number, number>();
    for (const f of frames) for (const [p, n] of f.palettes) pal.set(p, (pal.get(p) ?? 0) + n);
    const palette = [...pal].sort((a, b) => b[1] - a[1])[0][0];
    const air = frames.reduce((n, f) => n + f.air, 0), ground = frames.reduce((n, f) => n + f.ground, 0);
    const bySheet = new Map<string, { sheet: string; size: 1 | 2; frames: number[] }>();
    for (const f of frames) {
      const k = `${f.sheet}|${f.size}`;
      if (!bySheet.has(k)) bySheet.set(k, { sheet: f.sheet, size: f.size, frames: [] });
      bySheet.get(k)!.frames.push(f.index);
    }
    const sprites = [...bySheet.values()];
    for (const s of sprites) s.frames.sort((a, b) => a - b);
    const main = sprites[0]; // the sheet of the most-seen frame
    models.push({
      name: `${sheetSlug(main.sheet)}-${main.frames[0]}`,
      sprites,
      kind: air >= ground ? "air" : "ground",
      ticks,
      levels: [...new Set(frames.flatMap((f) => [...f.levels]))].sort(),
      palette,
      pictures: sprites.flatMap((s) => s.frames.map((index) => ({ sheet: s.sheet, size: s.size, index, pic: compose(sheets.get(s.sheet)!, s.size, index) }))),
    });
  }

  // Assemblies: models whose pieces touch for a good part of the time they're on screen.
  const modelOf = new Map<string, Model>();
  for (const m of models) for (const s of m.sprites) for (const f of s.frames) modelOf.set(`${s.sheet}|${s.size}|${f}`, m);
  const auf = new UnionFind();
  for (const [pair, n] of touching) {
    const [a, b] = pair.split("\n");
    const ma = modelOf.get(a)!, mb = modelOf.get(b)!;
    if (ma === mb) continue;
    if (n >= 20 && n >= 0.3 * Math.min(stats.get(a)!.ticks, stats.get(b)!.ticks)) auf.union(ma.name, mb.name);
  }
  const assemblies = new Map<string, Model[]>();
  for (const m of models) {
    const root = auf.find(m.name);
    if (!assemblies.has(root)) assemblies.set(root, []);
    assemblies.get(root)!.push(m);
  }
  for (const group of assemblies.values()) {
    if (group.length < 2) continue;
    group.sort((a, b) => b.ticks - a.ticks);
    const assembly = `assembly-${group[0].name}`;
    // Its picture: the biggest cluster seen that has one of its pieces.
    let best: { key: string; cx: number; cy: number }[] = [];
    for (const m of group)
      for (const s of m.sprites)
        for (const f of s.frames) {
          const c = clusterOf.get(`${s.sheet}|${s.size}|${f}`);
          if (c && c.length > best.length) best = c;
        }
    for (const m of group) {
      m.assembly = assembly;
      m.assemblyPieces = group.map((x) => x.name);
      m.assemblyView = best;
    }
  }

  // Player ships: blit_sprite2x2 from tyrian.shp#8 at shipGraphic + bank * 2, bank -2..2.
  const { buildResources } = await import("../../src/sim/resources");
  const files = { get: (n: string) => (hasData(n) ? readData(n) : undefined) };
  const shipSheet = buildResources(files, 1).spriteSheet9 ?? null;
  const shipGraphics = new Map<number, string>();
  for (let ep = 1; ep <= 4; ep++) {
    for (const ship of buildResources(files, ep).items.ships) {
      if (ship.shipGraphic > 0 && ship.name.trim() && !shipGraphics.has(ship.shipGraphic)) shipGraphics.set(ship.shipGraphic, ship.name.trim());
    }
  }
  if (shipSheet) {
    sheets.set(shipSheet.id, shipSheet.data);
    for (const [graphic, shipName] of shipGraphics) {
      const frames = [-2, -1, 0, 1, 2].map((b) => graphic + b * 2);
      models.push({
        name: `ship-${shipName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
        sprites: [{ sheet: shipSheet.id, size: 2, frames: [graphic], bank: { step: 2, max: 2 } }],
        kind: "ship",
        ticks: Number.MAX_SAFE_INTEGER,
        levels: [],
        palette: 5,
        pictures: frames.map((index) => ({ sheet: shipSheet.id, size: 2 as const, index, pic: compose(shipSheet.data, 2, index) })),
      });
    }
  }

  const order = { ship: 0, air: 1, ground: 2 };
  models.sort((a, b) => order[a.kind] - order[b.kind] || b.ticks - a.ticks || a.name.localeCompare(b.name));
  const names = new Set<string>();
  for (const m of models) {
    while (names.has(m.name)) m.name += "-b";
    names.add(m.name);
  }

  mkdirSync(OUT, { recursive: true });
  for (const m of models) {
    const dir = join(OUT, m.name);
    mkdirSync(dir, { recursive: true });
    const rgb = rgbOf(m.palette);
    const used = new Set<number>();
    for (const p of m.pictures) for (const c of p.pic) if (c >= 0) used.add(c);
    const w = m.pictures[0].size * 12, h = m.pictures[0].size * 14;
    for (const p of m.pictures) {
      const pw = p.size * 12, ph = p.size * 14;
      const img = new Uint8Array(pw * SCALE * ph * SCALE * 4);
      paint(img, pw * SCALE, p.pic, pw, ph, rgb, 0, 0, SCALE);
      writePng(join(dir, `frame-${sheetSlug(p.sheet)}-${p.index}.png`), pw * SCALE, ph * SCALE, img);
    }
    // Contact sheet: every frame, 8x, on a checkerboard.
    const cs = 8, pad = 2;
    const cw = m.pictures.length * (w + pad) * cs, ch = (h + pad) * cs;
    const contact = new Uint8Array(cw * ch * 4);
    for (let y = 0; y < ch; y++)
      for (let x = 0; x < cw; x++) {
        const v = ((x >> 3) + (y >> 3)) & 1 ? 40 : 28;
        contact.set([v, v, v + 6, 255], (y * cw + x) * 4);
      }
    m.pictures.forEach((p, i) => paint(contact, cw, p.pic, p.size * 12, p.size * 14, rgb, i * (w + pad) * cs + cs, cs, cs));
    writePng(join(dir, "contact.png"), cw, ch, contact);

    if (m.assemblyView && m.assemblyView.length > 0) {
      // The whole object, 6x, with this model's frames outlined in white.
      const v = m.assemblyView, as = 6;
      const x0 = Math.min(...v.map((p) => p.cx)) - 12, y0 = Math.min(...v.map((p) => p.cy)) - 14;
      const aw = (Math.max(...v.map((p) => p.cx)) + 12 - x0) * as, ah = (Math.max(...v.map((p) => p.cy)) + 14 - y0) * as;
      const img = new Uint8Array(aw * ah * 4);
      for (let i = 0; i < aw * ah; i++) img.set([24, 24, 30, 255], i * 4);
      const mine = new Set(m.sprites.flatMap((s) => s.frames.map((f) => `${s.sheet}|${s.size}|${f}`)));
      for (const p of v) {
        const [sheet, , index] = p.key.split("|");
        const px = (p.cx - 12 - x0) * as, py = (p.cy - 14 - y0) * as;
        paint(img, aw, compose(sheets.get(sheet)!, 2, Number(index)), 24, 28, rgb, px, py, as);
        if (!mine.has(p.key)) continue;
        for (let k = 0; k < 24 * as; k++) for (const yy of [py, py + 28 * as - 1]) img.set([255, 255, 255, 255], (yy * aw + px + k) * 4);
        for (let k = 0; k < 28 * as; k++) for (const xx of [px, px + 24 * as - 1]) img.set([255, 255, 255, 255], ((py + k) * aw + xx) * 4);
      }
      writePng(join(dir, "assembly.png"), aw, ah, img);
    }

    const rowsOf = (p: Model["pictures"][number]) => {
      const pw = p.size * 12;
      return Array.from({ length: p.size * 14 }, (_, y) => Array.from(p.pic.subarray(y * pw, (y + 1) * pw)));
    };
    writeFileSync(join(dir, "sprite.json"), JSON.stringify({
      name: m.name,
      kind: m.kind,
      sprites: m.sprites,
      ticksSeen: m.kind === "ship" ? null : m.ticks,
      levels: m.levels,
      assembly: m.assembly ?? null,
      assemblyPieces: m.assemblyPieces ?? null,
      // Where each piece sits in assembly.png's object: centre offsets in sprite px.
      assemblyLayout: m.assemblyView?.map((p) => ({ model: modelOf.get(p.key)?.name, frame: p.key, cx: p.cx, cy: p.cy })) ?? null,
      palette: m.palette,
      colors: Object.fromEntries([...used].sort((a, b) => a - b).map((i) => [i, rgb(i)])),
      frames: m.pictures.map((p) => ({ sheet: p.sheet, size: p.size, index: p.index, image: `frame-${sheetSlug(p.sheet)}-${p.index}.png`, pixels: rowsOf(p) })),
    }, (k, v) => (k === "pixels" ? v.map((r: number[]) => r.join(" ")) : v), 1) + "\n");
  }
  writeFileSync(join(OUT, "catalogue.json"), JSON.stringify(models.map((m) => ({
    name: m.name, kind: m.kind, size: m.sprites[0].size, frames: m.pictures.length, ticksSeen: m.kind === "ship" ? null : m.ticks, levels: m.levels.length,
    assembly: m.assembly ?? null,
  })), null, 1) + "\n");
  console.log(`${levelsPlayed.length} levels played; ${stats.size} frames; ${models.length} models (${models.filter((m) => m.kind === "ship").length} ships, ${models.filter((m) => m.kind === "air").length} air, ${models.filter((m) => m.kind === "ground").length} ground)`);
}), 600_000);
