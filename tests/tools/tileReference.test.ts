// Opt-in: reference data for the remastered backgrounds (DECISIONS.md D34), the tile counterpart
// of the sprite catalogue.
//
//   TILES_OUT=reference/tiles npm run tiles          (TILES_SHAPES=z,y picks the tilesets; default z)
//
// For each tileset (shapes?.dat) it plays nothing; it reads every level that uses the tileset and
// writes reference/tiles/<shapes>/:
//   tiles.json        every tile the levels use: pixels as palette indices (rows of space-separated
//                     ints; on layers 1-2, 0 is transparent) at 1x and MMPX 2x (`pixels2x`, for
//                     smooth outlines), which layers and levels use it, how
//                     often, and its most common neighbours on each side; plus the in-level
//                     palette's colours. assets/blender/tiles/ build the structure models from it.
//   tile-<n>.png      the tile, 4 image px per tile px (nearest), and tile-<n>-4x.png, the MMPX 4x
//                     upscale the remastered ground uses (src/render/remaster/mmpx.ts)
//   used-l<layer>.png the tiles each layer uses, in index order, 10 per row
//   map-<level>-l<layer>.png  each level's map for each layer (the rows it can show), 1x
//   ground-<level>-4x.png     a stretch of a level's ground upscaled in context, as the game does
// The output is derived from the game data, so it stays out of git (reference/ is ignored, D3, D16).
import { describe, test } from "vitest";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { crc32, deflateSync } from "node:zlib";
import { episodeLevels, parseEpisodeScript, parsePalettes, vga6To8 } from "../../src/data";
import { levelTiles, MAP_SIZES, parseLevelFile, parseShapes, TILE_HEIGHT, TILE_WIDTH, type Level } from "../../src/data/levels";
import { mmpx2x, mmpx4x, paletteLuma } from "../../src/render/remaster/mmpx";
import { upscaleInContext } from "../../src/render/remaster/groundAtlas";
import { hasData, readData } from "../data/dataDir";

const OUT = process.env.TILES_OUT ?? "";
const SHAPES = (process.env.TILES_SHAPES ?? "z").split(",").map((s) => s.trim().toLowerCase());
/** The in-level palette: JE_loadPic(3)'s, pcxpal[2] (tyrian2.ts). */
const LEVEL_PALETTE = 5;

export function writePng(path: string, width: number, height: number, rgba: Uint8Array): void {
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

interface LevelUse {
  id: string;
  name: string;
  level: Level;
}

interface TileInfo {
  layers: Set<number>;
  levels: Set<string>;
  count: number;
  /** Neighbour tile (or -1 for none/transparent) to count, per side. */
  sides: Record<"left" | "right" | "up" | "down", Map<number, number>>;
}

describe.skipIf(!OUT || !hasData("palette.dat", "levels1.dat", "tyrian1.lvl"))("tile reference", () => test("tiles", () => {
  const rgb = Array.from(parsePalettes(readData("palette.dat"))[LEVEL_PALETTE], vga6To8);
  const luma = paletteLuma(rgb);
  const lumaClear = paletteLuma(rgb, true);
  const colorOf = (i: number) => [rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2]];

  for (const letter of SHAPES) {
    const file = `shapes${letter}.dat`;
    if (!hasData(file)) continue;
    const shapes = parseShapes(readData(file));
    const dir = join(OUT, `shapes${letter}`);
    mkdirSync(dir, { recursive: true });

    // Levels that use this tileset, once each (a level can be played from several script lines).
    const uses: LevelUse[] = [];
    for (let ep = 1; ep <= 4; ep++) {
      if (!hasData(`levels${ep}.dat`, `tyrian${ep}.lvl`)) continue;
      const lvl = parseLevelFile(readData(`tyrian${ep}.lvl`));
      const seen = new Set<number>();
      for (const ref of episodeLevels(parseEpisodeScript(readData(`levels${ep}.dat`)))) {
        const level = lvl.levels[ref.lvlFileNum - 1];
        if (!level || seen.has(ref.lvlFileNum) || `shapes${level.shapeFile.toLowerCase()}.dat` !== file) continue;
        seen.add(ref.lvlFileNum);
        uses.push({ id: `${ep}-${ref.lvlFileNum}`, name: ref.levelName.trim(), level });
      }
    }

    const info = new Map<number, TileInfo>();
    /** Pixels by tile number; a blank record on layer 0 is an all-zero tile (levelTiles). */
    const pixelsOf = new Map<number, Uint8Array>();
    const tileAt = (level: Level, layer: 0 | 1 | 2, tiles: (Uint8Array | null)[], x: number, y: number) => {
      const { width, height } = MAP_SIZES[layer];
      if (x < 0 || x >= width || y < 0 || y >= height) return -1;
      const b = level.maps[layer][y * width + x];
      const t = tiles[b];
      if (!t) return -1;
      pixelsOf.set(level.mapSh[layer][b] - 1, t);
      return level.mapSh[layer][b] - 1;
    };
    for (const { id, name, level } of uses) {
      for (const layer of [0, 1, 2] as const) {
        const tiles = levelTiles(level, shapes, layer);
        const { width, height } = MAP_SIZES[layer];
        for (let y = 0; y < height; y++) {
          for (let x = 0; x < width; x++) {
            const n = tileAt(level, layer, tiles, x, y);
            if (n < 0) continue;
            let t = info.get(n);
            if (!t) info.set(n, (t = { layers: new Set(), levels: new Set(), count: 0, sides: { left: new Map(), right: new Map(), up: new Map(), down: new Map() } }));
            t.layers.add(layer);
            t.levels.add(`${id} ${name}`);
            t.count++;
            const bump = (m: Map<number, number>, k: number) => m.set(k, (m.get(k) ?? 0) + 1);
            bump(t.sides.left, tileAt(level, layer, tiles, x - 1, y));
            bump(t.sides.right, tileAt(level, layer, tiles, x + 1, y));
            bump(t.sides.up, tileAt(level, layer, tiles, x, y - 1));
            bump(t.sides.down, tileAt(level, layer, tiles, x, y + 1));
          }
        }
        writeMap(join(dir, `map-${id}-l${layer}.png`), level, layer, tiles, colorOf);
      }
      writeGround4x(join(dir, `ground-${id}-4x.png`), level, levelTiles(level, shapes, 0), luma, colorOf);
    }

    // tiles.json, tile PNGs and per-layer sheets.
    const used = [...info.keys()].sort((a, b) => a - b);
    const top = (m: Map<number, number>) => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([tile, count]) => ({ tile, count }));
    const json = {
      shapes: file,
      palette: LEVEL_PALETTE,
      levels: uses.map((u) => `${u.id} ${u.name}`),
      colors: Object.fromEntries(Array.from({ length: 256 }, (_, i) => [i, colorOf(i)])),
      tiles: Object.fromEntries(used.map((n) => {
        const t = info.get(n)!;
        const px = pixelsOf.get(n)!;
        const rows = Array.from({ length: TILE_HEIGHT }, (_, y) => Array.from(px.subarray(y * TILE_WIDTH, (y + 1) * TILE_WIDTH)).join(" "));
        // MMPX 2x on its own (edges clamped); on layers 1-2, 0 stays transparent.
        const up = mmpx2x(px, TILE_WIDTH, TILE_HEIGHT, t.layers.has(0) ? luma : lumaClear);
        const rows2x = Array.from({ length: TILE_HEIGHT * 2 }, (_, y) => Array.from(up.subarray(y * TILE_WIDTH * 2, (y + 1) * TILE_WIDTH * 2)).join(" "));
        return [n, {
          layers: [...t.layers].sort(),
          levels: [...t.levels],
          count: t.count,
          neighbours: { left: top(t.sides.left), right: top(t.sides.right), up: top(t.sides.up), down: top(t.sides.down) },
          pixels: rows,
          pixels2x: rows2x,
        }];
      })),
    };
    writeFileSync(join(dir, "tiles.json"), JSON.stringify(json, null, 1) + "\n");

    for (const n of used) {
      const px = pixelsOf.get(n)!;
      const transparent = !info.get(n)!.layers.has(0);
      const up = mmpx4x(px, TILE_WIDTH, TILE_HEIGHT, transparent ? lumaClear : luma);
      writeIndexPng(join(dir, `tile-${n}.png`), px, TILE_WIDTH, TILE_HEIGHT, 4, transparent, colorOf);
      writeIndexPng(join(dir, `tile-${n}-4x.png`), up, TILE_WIDTH * 4, TILE_HEIGHT * 4, 1, transparent, colorOf);
    }
    for (const layer of [0, 1, 2]) {
      const ids = used.filter((n) => info.get(n)!.layers.has(layer));
      if (ids.length === 0) continue;
      const S = 3, per = 10, cw = TILE_WIDTH * S + 6, ch = TILE_HEIGHT * S + 6;
      const W = per * cw, H = Math.ceil(ids.length / per) * ch;
      const img = new Uint8Array(W * H * 4);
      ids.forEach((n, k) => {
        const px = pixelsOf.get(n)!;
        const ox = (k % per) * cw, oy = Math.floor(k / per) * ch;
        for (let y = 0; y < TILE_HEIGHT * S; y++) {
          for (let x = 0; x < TILE_WIDTH * S; x++) {
            const p = px[Math.floor(y / S) * TILE_WIDTH + Math.floor(x / S)];
            const c = layer > 0 && p === 0 ? [255, 0, 255] : colorOf(p);
            img.set([c[0], c[1], c[2], 255], ((oy + y) * W + ox + x) * 4);
          }
        }
      });
      writePng(join(dir, `used-l${layer}.png`), W, H, img);
      writeFileSync(join(dir, `used-l${layer}.txt`), ids.join(" ") + "\n");
    }
    console.log(`${file}: ${used.length} tiles in ${uses.length} levels -> ${dir}`);
  }
}, 120_000));

function writeIndexPng(path: string, px: Uint8Array, w: number, h: number, scale: number, transparent: boolean, colorOf: (i: number) => number[]): void {
  const W = w * scale, H = h * scale;
  const img = new Uint8Array(W * H * 4);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const p = px[Math.floor(y / scale) * w + Math.floor(x / scale)];
      if (transparent && p === 0) continue;
      const c = colorOf(p);
      img.set([c[0], c[1], c[2], 255], (y * W + x) * 4);
    }
  }
  writePng(path, W, H, img);
}

/** A layer's whole map at 1x, transparent where nothing is drawn. */
function writeMap(path: string, level: Level, layer: 0 | 1 | 2, tiles: (Uint8Array | null)[], colorOf: (i: number) => number[]): void {
  const { width, height } = MAP_SIZES[layer];
  const W = width * TILE_WIDTH, H = height * TILE_HEIGHT;
  const img = new Uint8Array(W * H * 4);
  for (let ty = 0; ty < height; ty++) {
    for (let tx = 0; tx < width; tx++) {
      const t = tiles[level.maps[layer][ty * width + tx]];
      if (!t) continue;
      for (let y = 0; y < TILE_HEIGHT; y++) {
        for (let x = 0; x < TILE_WIDTH; x++) {
          const p = t[y * TILE_WIDTH + x];
          if (layer > 0 && p === 0) continue;
          const c = colorOf(p);
          img.set([c[0], c[1], c[2], 255], ((ty * TILE_HEIGHT + y) * W + tx * TILE_WIDTH + x) * 4);
        }
      }
    }
  }
  writePng(path, W, H, img);
}

/** The last 24 rows of a level's ground (where it starts), each cell upscaled with its neighbours. */
function writeGround4x(path: string, level: Level, tiles: (Uint8Array | null)[], luma: Float32Array, colorOf: (i: number) => number[]): void {
  const { width, height } = MAP_SIZES[0];
  const rows = 24, y0 = height - rows;
  const S = 4, W = width * TILE_WIDTH * S, H = rows * TILE_HEIGHT * S;
  const img = new Uint8Array(W * H * 4);
  const at = (x: number, y: number) => (x < 0 || x >= width || y < 0 || y >= height ? null : tiles[level.maps[0][y * width + x]]);
  for (let ty = 0; ty < rows; ty++) {
    for (let tx = 0; tx < width; tx++) {
      const n = [-1, 0, 1].map((dy) => [-1, 0, 1].map((dx) => at(tx + dx, y0 + ty + dy)));
      if (!n[1][1]) continue;
      const slot = upscaleInContext(n, luma);
      const sw = TILE_WIDTH * S + 2;
      for (let y = 0; y < TILE_HEIGHT * S; y++) {
        for (let x = 0; x < TILE_WIDTH * S; x++) {
          const c = colorOf(slot[(y + 1) * sw + x + 1]);
          img.set([c[0], c[1], c[2], 255], ((ty * TILE_HEIGHT * S + y) * W + tx * TILE_WIDTH * S + x) * 4);
        }
      }
    }
  }
  writePng(path, W, H, img);
}
