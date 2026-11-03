// Enemies don't pop between their models and their sprites (DECISIONS.md D54).
//
// Plays levels with the test bot (tests/sim/bot.ts: invulnerable, always firing, sweeping), so
// enemies are hit, flash, die and fire, and routes every Sprite2 draw of every tick the way the
// renderer does (src/render/sprite2Route.ts), in the default looks (remastered sprites: shots and
// pickups flat where there's art). Two checks:
//
// - Preload coverage: every model a level shows is one DrawListRenderer.preloadLevel loads first
//   (sim/levelSprites.ts), so no enemy waits for its model. Every level of episode 1.
// - Sprites left, level 1: no enemy is drawn as its extruded sprite but for those damaged frames.
//   The bot flies level 1 on low armour so the armour ship (spawned only then) and its crates show.
// - Frame coverage, level 1: each enemy's draws on a tick are one of its model, flat art, the
//   extruded sprite, or a mix (some tiles one way, some another). An enemy seen two ways over its
//   life pops on screen. The only ones allowed are KNOWN_DAMAGE_SWAPS below: damaged frames (an
//   enemy's look once hit hard enough, or destroyed) that have no model of their own yet.
//
// MODEL_SWAP_REPORT=1 prints each enemy type's routes, the swaps, the unmodelled damaged frames and
// every sprite level 1 still draws extruded (enemies, shots, explosions; "still a sprite: ...").
import { readFileSync, statSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { decodeSprite2 } from "../../src/data/sprites";
import { parseSpriteArtManifest, SpriteArt } from "../../src/render/spriteArt";
import { Route, Sprite2Router } from "../../src/render/sprite2Route";
import { spriteModels } from "../../src/render/spriteModels";
import type { SpriteDraw } from "../../src/sim/draw";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const REPORT = process.env.MODEL_SWAP_REPORT === "1";

/**
 * Level 1's enemies whose damaged frames have no model while their normal frames do, so they turn
 * from model to sprite when damaged (`sheet|size|enemy type: damaged frames (normal frames)`). Too
 * many to model here (13 damaged pieces); each needs its own damaged model (D54 lists them; the rocks
 * of newshe.shp, types 522-527, got theirs in D67).
 */
const KNOWN_DAMAGE_SWAPS = [
  // The pieces of a large multi-part enemy (newsh4.shp): their battle-damaged frames.
  "newsh4.shp|2|46: damaged frames 162 (normal 10)",
  "newsh4.shp|2|47: damaged frames 164 (normal 12)",
  "newsh4.shp|2|49: damaged frames 168 (normal 16)",
  "newsh4.shp|2|50: damaged frames 170 (normal 18)",
  "newsh4.shp|2|51: damaged frames 200 (normal 48)",
  "newsh4.shp|2|52: damaged frames 202 (normal 50)",
  "newsh4.shp|2|54: damaged frames 206 (normal 54)",
  "newsh4.shp|2|55: damaged frames 208 (normal 56)",
  "newsh4.shp|2|57: damaged frames 240 (normal 88)",
  "newsh4.shp|2|58: damaged frames 242 (normal 90)",
  "newsh4.shp|2|59: damaged frames 244 (normal 92)",
  "newsh4.shp|2|60: damaged frames 246 (normal 94)",
  "newsh4.shp|2|63: damaged frames 280 (normal 128)",
];

type Look = "model" | "flat" | "sprite" | "mixed" | "none";

interface TypeStat {
  /** sheet|groupSize */
  sheet: string;
  /** Frames (groupIndex) seen per look. */
  frames: Map<Look, Set<number>>;
  ticks: Map<Look, number>;
  /** Enemies of this type seen two ways (or mixed): serial, and their frames each way. */
  swaps: { serial: number; looks: Map<Look, Set<number>> }[];
  instances: number;
}

interface LevelResult {
  main: number;
  completed: boolean;
  /** Models the level showed, and those preloadLevel would have loaded. */
  shown: Map<string, string>;
  preloaded: Set<string>;
  types: Map<string, TypeStat>;
  /** Damaged frames per enemy type met (sheet|size|type), and its normal frames. */
  damagedFrames: Map<string, { sheet: SpriteDraw["sheet"]; size: 1 | 2; frames: number[]; normal: number[] }>;
  /** Every Sprite2 draw left as its extruded sprite: "what sheet frame" -> ticks drawn. */
  sprites: Map<string, number>;
}

const sim = async () => ({
  ...(await import("../../src/sim/game")),
  ...(await import("../../src/sim/helptext")),
  ...(await import("../../src/sim/input")),
  ...(await import("../../src/sim/mtrand")),
  ...(await import("../../src/sim/newgame")),
  ...(await import("../../src/sim/resources")),
  ...(await import("../../src/sim/state")),
  ...(await import("../../src/sim/tyrian2")),
  ...(await import("../../src/sim/draw")),
  ...(await import("../../src/sim/mainint")),
  ...(await import("../../src/sim/shots")),
  ...(await import("../../src/sim/levelSprites")),
  ...(await import("../sim/bot")),
});

const router = new Sprite2Router(spriteModels());
const empty = new Map<string, boolean>();
const emptyTileOf = (d: Pick<SpriteDraw, "sheet">) => (index: number) => {
  const key = `${d.sheet.id}|${index}`;
  let e = empty.get(key);
  if (e === undefined) empty.set(key, (e = decodeSprite2(d.sheet.data, index).pixels.every((c) => c < 0)));
  return e;
};
const drawsNothing = (d: Pick<SpriteDraw, "size" | "index">, emptyTile: (i: number) => boolean) =>
  d.size === 1 ? emptyTile(d.index) : [0, 1, 19, 20].every((di) => emptyTile(d.index + di));

function spriteArt(): SpriteArt<object> {
  const manifest = parseSpriteArtManifest(JSON.parse(readFileSync("public/art/sprites/manifest.json", "utf8")))!;
  const art = new SpriteArt<object>(manifest);
  for (const s of art.sheets.values()) s.setTexture({}, 1 << 20, 1 << 20);
  return art;
}

/** Play the level loadLevel has set up (from startLevel on) with the bot, classifying every draw. */
async function playLevel(main: number, art: SpriteArt<object>, lowArmor: boolean): Promise<LevelResult> {
  const s = await sim();
  const { g } = s;
  s.startLevel();
  s.clearSimInput();
  const preloaded = router.modelsOf(s.levelSprites());

  const shown = new Map<string, string>();
  const types = new Map<string, TypeStat>();
  /** Per enemy (serial): its type, and the looks and frames it's been drawn with. */
  const enemies = new Map<number, { type: string; looks: Map<Look, Set<number>> }>();
  const damagedFrames: LevelResult["damagedFrames"] = new Map();
  const sprites = new Map<string, number>();
  let result = s.tick();
  for (let t = 0; t < 60000 && !result.levelOver; t++) {
    for (let i = 0; i < 100; i++) {
      if (g.enemyAvail[i] === 1) continue;
      const e = g.enemy[i];
      const sheet = s.enemySprite2s(e);
      if (!sheet) continue;
      const size: 1 | 2 = e.size === 1 ? 2 : 1;
      const key = `${sheet.id}|${size}|${e.enemytype}`;
      if (damagedFrames.has(key)) continue;
      // game.ts's damage (and death with edlevel -1): edani != 0 animates egr[edgr-1 .. |edani|-1];
      // otherwise egr[0] becomes edgr.
      const dat = g.res.enemyDat[e.enemytype];
      const frames: number[] = [];
      if (dat.dAni !== 0) for (let k = dat.dGr - 1; k < Math.abs(dat.dAni); k++) frames.push(dat.eGraphic[k]);
      else if (dat.dGr > 0) frames.push(dat.dGr);
      const normal = dat.eGraphic.slice(0, Math.max(1, dat.ani));
      damagedFrames.set(key, { sheet, size, frames: frames.filter((f) => f > 0 && f !== 999), normal });
    }
    // This tick's draws per enemy: the looks of its tiles.
    const now = new Map<number, { d: SpriteDraw; looks: Set<Look> }>();
    for (const item of s.drawList.items) {
      if (item.kind !== "sprite2" || item.effect === "darken") continue;
      const d = item;
      const emptyTile = emptyTileOf(d);
      const r = router.route(d, art.sheet(d.sheet.id) ?? null, emptyTile);
      const modelled = r.route === Route.Group || r.route === Route.Override || r.route === Route.Ungrouped;
      if (modelled && !shown.has(r.model)) shown.set(r.model, `${d.sheet.id} ${d.groupIndex >= 0 ? `group ${d.groupIndex}` : `sprite ${d.index}`} at tick ${t}`);
      const look: Look = modelled ? "model" : r.route === Route.Flat ? "flat" : drawsNothing(d, emptyTile) ? "none" : "sprite";
      if (look === "sprite") {
        const what = d.key >= s.ENEMY_KEY_BASE ? "enemy" : d.key >= s.PLAYER_SHOT_KEY_BASE ? "shot"
          : d.key >= 30000 ? "explosion" : d.key >= 20000 ? "enemy-shot" : d.key >= s.PLAYER_KEY_BASE ? "player" : "other";
        const k = `${what} ${d.sheet.id} ${d.groupIndex >= 0 ? `group ${d.groupSize}x${d.groupSize} ${d.groupIndex}` : `sprite ${d.index}`}`;
        sprites.set(k, (sprites.get(k) ?? 0) + 1);
      }
      if (d.groupIndex < 0 || d.key < s.ENEMY_KEY_BASE) continue;
      const serial = (d.key - s.ENEMY_KEY_BASE) >> 2;
      let e = now.get(serial);
      if (!e) now.set(serial, (e = { d, looks: new Set() }));
      e.looks.add(look);
    }
    for (const [serial, { d, looks }] of now) {
      looks.delete("none");
      if (looks.size === 0) continue;
      const look: Look = looks.size > 1 ? "mixed" : [...looks][0];
      const type = `${d.sheet.id}|${d.groupSize}`;
      let ts = types.get(type);
      if (!ts) types.set(type, (ts = { sheet: type, frames: new Map(), ticks: new Map(), swaps: [], instances: 0 }));
      if (!ts.frames.has(look)) ts.frames.set(look, new Set());
      ts.frames.get(look)!.add(d.groupIndex);
      ts.ticks.set(look, (ts.ticks.get(look) ?? 0) + 1);
      let e = enemies.get(serial);
      if (!e) {
        enemies.set(serial, (e = { type, looks: new Map() }));
        ts.instances++;
      }
      if (!e.looks.has(look)) e.looks.set(look, new Set());
      e.looks.get(look)!.add(d.groupIndex);
    }
    s.botTick(t);
    // Low on armour (under 6), JE_main's warning sends the armour ship (enemy type 560, dropping
    // 561-563) every 500 ticks; the bot keeps 10, so on level 1 it flies on 5 to meet it.
    if (lowArmor) g.player[0].armor = 5;
    result = s.tick();
  }
  for (const [serial, e] of enemies) {
    if (e.looks.size < 2 && !e.looks.has("mixed")) continue;
    types.get(e.type)!.swaps.push({ serial, looks: e.looks });
  }
  return { main, completed: result.completed, shown, preloaded, types, damagedFrames, sprites };
}

/** Episode 1 from its first level, each level after the last (g.nextLevel), until it comes round again. */
async function playEpisode1(levels: number): Promise<LevelResult[]> {
  const s = await sim();
  const { g } = s;
  const art = spriteArt();
  s.mt_srand(1);
  g.res = s.buildResources(files, 1);
  s.loadHelpText(readData("tyrian.hdt"));
  s.newOnePlayerGame(1);
  const out: LevelResult[] = [];
  let main = g.mainLevel;
  const seen = new Set<number>();
  for (let n = 0; n < levels && main > 0 && !seen.has(main); n++) {
    seen.add(main);
    s.loadLevel(files, 1, main);
    g.player[0].items.weapon[0].power = 11;
    const r = await playLevel(main, art, n === 0);
    out.push(r);
    if (!r.completed || g.nextLevel <= 0 || g.nextLevel === main) break;
    main = g.nextLevel;
  }
  return out;
}

const fmtFrames = (m: Map<Look, Set<number>>) => [...m].map(([look, f]) => `${look}: ${[...f].sort((a, b) => a - b).join(",")}`).join("; ");

/** Damaged frames without a model, of enemy types whose own frames have one. */
function unmodelledDamage(r: LevelResult): string[] {
  const grouped = spriteModels().grouped;
  const out: string[] = [];
  for (const [key, { sheet, size, frames, normal }] of r.damagedFrames) {
    const modelled = (f: number) => grouped.has(`${sheet.id}|${size}|${f}`);
    const blank = (f: number) => drawsNothing({ index: f, size }, emptyTileOf({ sheet }));
    if (!normal.some(modelled)) continue;
    const missing = frames.filter((f) => !modelled(f) && !blank(f));
    if (missing.length) out.push(`${key}: damaged frames ${[...new Set(missing)].join(",")} (normal ${normal.join(",")})`);
  }
  return out.sort();
}

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat", "tyrian.hdt", "palette.dat", "tyrian.shp"))("model/sprite pops", () => {
  let episode: Promise<LevelResult[]> | null = null;
  const played = () => (episode ??= playEpisode1(Number(process.env.MODEL_SWAP_LEVELS ?? 99)));

  test("level 1: no enemy is drawn as its model on some ticks and as a sprite on others, but for known damaged frames", async () => {
    const [level1] = await played();
    expect(level1.completed, "the bot finishes level 1").toBe(true);
    const damaged = unmodelledDamage(level1);
    if (REPORT) {
      for (const ts of [...level1.types.values()].sort((a, b) => a.sheet.localeCompare(b.sheet))) {
        console.log(`${ts.sheet}: ${ts.instances} enemies; ${fmtFrames(ts.frames)}; ticks ${[...ts.ticks].map(([l, n]) => `${l} ${n}`).join(", ")}`);
        for (const sw of ts.swaps.slice(0, 5)) console.log(`   swap #${sw.serial} ${fmtFrames(sw.looks)}`);
        if (ts.swaps.length > 5) console.log(`   ... ${ts.swaps.length - 5} more`);
      }
      for (const d of damaged) console.log(`unmodelled ${d}`);
      for (const [k, n] of [...level1.sprites].sort()) console.log(`still a sprite: ${k} (${n} draws)`);
    }
    // A swap is explained when every frame it wasn't a model in is a known unmodelled damaged frame.
    const known = new Map<string, Set<number>>();
    for (const k of KNOWN_DAMAGE_SWAPS) {
      const [, sheet, size, frames] = /^([^|]+)\|(\d)\|\d+: damaged frames ([\d,]+)/.exec(k)!;
      const set = known.get(`${sheet}|${size}`) ?? new Set<number>();
      for (const f of frames.split(",")) set.add(Number(f));
      known.set(`${sheet}|${size}`, set);
    }
    const unexplained = [...level1.types.values()].flatMap((ts) =>
      ts.swaps
        .filter((sw) => sw.looks.has("mixed") || sw.looks.has("flat") || [...(sw.looks.get("sprite") ?? [])].some((f) => !known.get(ts.sheet)?.has(f)))
        .map((sw) => `${ts.sheet} #${sw.serial} ${fmtFrames(sw.looks)}`),
    );
    expect(unexplained, "enemies drawn more than one way (a frame without a model? see sprite2Route.ts)").toEqual([]);
    expect(damaged.filter((d) => !KNOWN_DAMAGE_SWAPS.includes(d)), "modelled enemies with new unmodelled damaged frames").toEqual([]);
  }, 600000);

  test("level 1: every enemy is drawn as its model or flat art, but for known damaged frames (with the armour ship)", async () => {
    const [level1] = await played();
    const known = new Set(KNOWN_DAMAGE_SWAPS.map((k) => {
      const [, sheet, size, frames] = /^([^|]+)\|(\d)\|\d+: damaged frames ([\d,]+)/.exec(k)!;
      return frames.split(",").map((f) => `enemy ${sheet} group ${size}x${size} ${f}`);
    }).flat());
    const sprites = [...level1.sprites.keys()].filter((k) => k.startsWith("enemy ") && !known.has(k));
    expect(sprites, "enemies still drawn as extruded sprites (MODEL_SWAP_REPORT=1 lists every sprite drawn)").toEqual([]);
    // The bot flew level 1 on low armour, so the armour ship came, and was drawn as its model.
    expect([...level1.shown.keys()]).toContain("enemies/tyrian10-279");
  }, 600000);

  test("every model a level of episode 1 shows is preloaded before it starts (sim/levelSprites.ts)", async () => {
    const levels = await played();
    expect(levels.length).toBeGreaterThan(0);
    const missing: string[] = [];
    for (const r of levels) {
      for (const [model, where] of r.shown) if (!r.preloaded.has(model)) missing.push(`level ${r.main}: ${model} (${where})`);
      if (REPORT) {
        const kb = [...r.preloaded].reduce((n, m) => n + statSync(`public/models/${m}.glb`).size, 0) >> 10;
        console.log(`level ${r.main}: ${r.completed ? "completed" : "not completed"}; shows ${r.shown.size} models, preloads ${r.preloaded.size} (${kb} KiB)`);
      }
    }
    expect(missing).toEqual([]);
  }, 600000);
});
