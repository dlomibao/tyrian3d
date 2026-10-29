// The remastered backgrounds (DECISIONS.md D34): the MMPX upscaler, the context-aware ground atlas
// and the structure models' tile patterns.
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { Pass, type Draw, type TileDraw } from "../../src/sim/draw";
import { mmpx2x, mmpx4x } from "../../src/render/remaster/mmpx";
import { RemasterGroundAtlas, upscaleInContext } from "../../src/render/remaster/groundAtlas";
import { TILE_MODELS, TileModelIndex, type TileModelEntry } from "../../src/render/remaster/tileModels";
import { BG_KEY_LAYER } from "../../src/sim/backgrnd";
import { MAP_SIZES, parseLevelFile } from "../../src/data/levels";
import { hasData, readData } from "../data/dataDir";

/** Luminance = index, so brighter indices are higher numbers. */
const luma = Array.from({ length: 256 }, (_, i) => i);

function image(rows: string[]): { px: Uint8Array; w: number; h: number } {
  const h = rows.length, w = rows[0].length;
  const px = new Uint8Array(w * h);
  rows.forEach((r, y) => [...r].forEach((c, x) => (px[y * w + x] = c === "#" ? 200 : 10)));
  return { px, w, h };
}

describe("mmpx", () => {
  test("never invents a colour: every output pixel is an input index", () => {
    const w = 24, h = 28;
    const px = new Uint8Array(w * h);
    let seed = 7;
    for (let i = 0; i < px.length; i++) px[i] = [3, 50, 51, 120, 200][(seed = (seed * 1103515245 + 12345) & 0x7fffffff) % 5];
    const out = mmpx4x(px, w, h, luma);
    expect(out.length).toBe(w * h * 16);
    const inputs = new Set(px);
    expect([...new Set(out)].every((v) => inputs.has(v))).toBe(true);
  });

  test("a flat image stays flat", () => {
    const out = mmpx2x(new Uint8Array(12).fill(9), 4, 3, luma);
    expect([...new Set(out)]).toEqual([9]);
  });

  test("a 1:1 diagonal line is smoothed, not doubled into stairs", () => {
    const { px, w, h } = image(["#.....", ".#....", "..#...", "...#..", "....#.", ".....#"]);
    const out = mmpx2x(px, w, h, luma);
    const at = (x: number, y: number) => out[y * w * 2 + x];
    // Nearest-neighbour would leave (3, 2) and (2, 3) dark beside the 2x2 blocks; MMPX fills the
    // inner corners so the line reads as a continuous diagonal.
    expect(at(2, 2)).toBe(200);
    expect(at(3, 2)).toBe(200);
    expect(at(2, 3)).toBe(200);
    // Away from the line stays background.
    expect(at(11, 0)).toBe(10);
  });

  test("square corners stay square", () => {
    const { px, w, h } = image(["......", ".####.", ".####.", ".####.", ".####.", "......"]);
    const out = mmpx2x(px, w, h, luma);
    // The block's top-left corner pixel at 2x is still filled.
    expect(out[2 * w * 2 + 2]).toBe(200);
    expect(out[2 * w * 2 + 1]).toBe(10);
  });
});

describe("ground upscaled in context", () => {
  const tile = (seed: number) => {
    const t = new Uint8Array(24 * 28);
    for (let i = 0; i < t.length; i++) t[i] = ((i * 7 + seed * 13) % 23 < 9 ? 40 : 90) + ((i >> 5) % 3);
    return t;
  };

  test("a cell comes out as it would in the whole map upscaled at once", () => {
    const tiles = [0, 1, 2, 3, 4, 5, 6, 7, 8].map(tile);
    const n = [tiles.slice(0, 3), tiles.slice(3, 6), tiles.slice(6, 9)];
    // The 3x3 block as one image, upscaled, then the centre cropped.
    const W = 72, H = 84;
    const whole = new Uint8Array(W * H);
    for (let ty = 0; ty < 3; ty++)
      for (let tx = 0; tx < 3; tx++)
        for (let y = 0; y < 28; y++) whole.set(n[ty][tx].subarray(y * 24, y * 24 + 24), (ty * 28 + y) * W + tx * 24);
    const up = mmpx4x(whole, W, H, luma);
    const slot = upscaleInContext(n, luma);
    const SW = 98;
    let diff = 0;
    for (let y = -1; y < 113; y++)
      for (let x = -1; x < 97; x++) if (slot[(y + 1) * SW + x + 1] !== up[(112 + y) * W * 4 + 96 + x]) diff++;
    expect(diff).toBe(0);
  });

  test("slots are keyed by context and reused when a cell scrolls back", () => {
    const atlas = new RemasterGroundAtlas();
    atlas.setLuma(luma);
    const t = tile(1);
    const draw = (key: number, tileId: string): TileDraw => ({ kind: "tile", layer: 0, tile: t, tileId, x: 0, y: 0, pass: Pass.Background1, key, effect: "none" });
    const items: Draw[] = [draw(15, "z:1"), draw(16, "z:1"), draw(29, "z:2")];
    atlas.prepare(items);
    expect(atlas.size).toBe(3); // each cell has different neighbours
    const uv = new Float32Array(2);
    expect(atlas.place(16, uv, 0)).toBe(true);
    expect(atlas.place(99, uv, 0)).toBe(false);
    atlas.prepare(items);
    expect(atlas.size).toBe(3);
    expect(atlas.upscaled).toBe(3);
  });
});

const tileDraw = (layer: 0 | 1 | 2, index: number, tile: number, x = 0, y = 0): TileDraw => ({
  kind: "tile", layer, tile: new Uint8Array(0), tileId: `shapesz.dat:${tile}`, x, y, pass: Pass.Background1, key: layer * BG_KEY_LAYER + index, effect: "none",
});

describe("structure patterns", () => {
  const bunker: TileModelEntry = { model: "tiles/test/bunker", shapes: "shapesz.dat", layer: 0, tiles: [[320, 321], [330, 331]] };
  const rock: TileModelEntry = { model: "tiles/test/rock", shapes: "shapesz.dat", layer: 2, tiles: [[141]] };

  test("any tile of a pattern finds the whole structure and its centre", () => {
    const idx = new TileModelIndex([bunker, rock]);
    // Map width 14: (row 10, col 3) is index 143.
    const cells = [tileDraw(0, 143, 320, 100, 50), tileDraw(0, 144, 321, 124, 50), tileDraw(0, 157, 330, 100, 78), tileDraw(0, 158, 331, 124, 78)];
    idx.prepare(cells);
    const fromTopLeft = idx.match(cells[0])!;
    const fromBottomRight = idx.match(cells[3])!;
    expect(fromTopLeft.anchorKey).toBe(143);
    expect(fromBottomRight.anchorKey).toBe(143);
    // Both put the model at the pattern's centre, (124, 78) on screen.
    expect([100 + fromTopLeft.dx, 50 + fromTopLeft.dy]).toEqual([124, 78]);
    expect([124 + fromBottomRight.dx, 78 + fromBottomRight.dy]).toEqual([124, 78]);
  });

  test("a visible cell that doesn't fit the pattern rejects it; off-screen cells don't", () => {
    const idx = new TileModelIndex([bunker]);
    const wrong = [tileDraw(0, 143, 320), tileDraw(0, 144, 999)];
    idx.prepare(wrong);
    expect(idx.match(wrong[0])).toBeNull();
    const partial = [tileDraw(0, 157, 330), tileDraw(0, 158, 331)]; // the top row has scrolled off
    idx.prepare(partial);
    expect(idx.match(partial[1])?.anchorKey).toBe(143);
  });

  test("layers are separate and patterns don't wrap around the map's edge", () => {
    const idx = new TileModelIndex([bunker, rock]);
    const onLayer2 = tileDraw(2, 5, 320);
    idx.prepare([onLayer2]);
    expect(idx.match(onLayer2)).toBeNull();
    const atRightEdge = tileDraw(0, 13, 320); // column 13: its right half would be off the map
    idx.prepare([atRightEdge]);
    expect(idx.match(atRightEdge)).toBeNull();
    const single = tileDraw(2, 20, 141);
    idx.prepare([single]);
    expect(idx.match(single)?.anchorKey).toBe(2 * BG_KEY_LAYER + 20);
  });

  test("a pattern with minRows waits until that many of its rows are drawn and match", () => {
    // A 3x2 platform whose tiles (360-362 rim, 371 paving) are plain terrain elsewhere too.
    const pad: TileModelEntry = { model: "tiles/test/pad", shapes: "shapesz.dat", layer: 0, tiles: [[360, 362], [371, 371], [380, 382]], minRows: 2 };
    const idx = new TileModelIndex([pad]);
    const top = [tileDraw(0, 143, 360), tileDraw(0, 144, 362)]; // only its first row is on screen
    idx.prepare(top);
    expect(idx.match(top[0])).toBeNull();
    const two = [...top, tileDraw(0, 157, 371), tileDraw(0, 158, 371)];
    idx.prepare(two);
    expect(idx.match(two[3])?.anchorKey).toBe(143);
    const wrong = [...two, tileDraw(0, 171, 380), tileDraw(0, 172, 999)];
    idx.prepare(wrong);
    expect(idx.match(wrong[0])).toBeNull();
  });

  test("the committed entries are well formed and each tile is claimed once per layer", () => {
    const claimed = new Map<string, string>();
    for (const e of TILE_MODELS) {
      expect(e.model).toMatch(/^tiles\//);
      expect(e.tiles.length).toBeGreaterThan(0);
      for (const row of e.tiles) expect(row.length).toBe(e.tiles[0].length);
      if (e.minRows !== undefined) {
        expect(e.minRows).toBeGreaterThanOrEqual(1);
        continue; // shares its tiles with other terrain and structures by design
      }
      for (const t of e.tiles.flat()) {
        if (t < 0) continue;
        const k = `${e.shapes}:${e.layer}:${t}:${e.tiles.length}x${e.tiles[0].length}`;
        expect(claimed.get(k), `${k} claimed by ${claimed.get(k)} and ${e.model}`).toBeUndefined();
        claimed.set(k, e.model);
      }
    }
  });
});

type Level = ReturnType<typeof parseLevelFile>["levels"][number];

/** Every level in the episodes there is data for, with its tileset's file name. */
function* levels(): Generator<{ ep: number; n: number; level: Level; shapes: string }> {
  for (let ep = 1; ep <= 4; ep++) {
    if (!hasData(`tyrian${ep}.lvl`)) continue;
    const all = parseLevelFile(readData(`tyrian${ep}.lvl`)).levels;
    for (let n = 0; n < all.length; n++) yield { ep, n: n + 1, level: all[n], shapes: `shapes${all[n].shapeFile.toLowerCase()}.dat` };
  }
}

/** A level's tile (0-based, -1 = none) at map cell (x, y) of a layer. */
const tileAt = (level: Level, layer: 0 | 1 | 2, x: number, y: number) =>
  level.mapSh[layer][level.maps[layer][y * MAP_SIZES[layer].width + x]] - 1;

/** Patterns without minRows: wherever one of their tiles is, the whole pattern is (or is cut by the map's edge). */
function checkWholePatterns(entries: readonly TileModelEntry[]): number {
  const multi = entries.filter((e) => e.tiles.length * e.tiles[0].length > 1 && e.minRows === undefined);
  let checked = 0;
  for (const { ep, level, shapes } of levels()) {
    for (const e of multi.filter((m) => m.shapes === shapes)) {
      const { width, height } = MAP_SIZES[e.layer];
      const at = (x: number, y: number) => tileAt(level, e.layer, x, y);
      const rows = e.tiles.length, cols = e.tiles[0].length;
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const t = at(x, y);
          const cells: [number, number][] = [];
          e.tiles.forEach((row, r) => row.forEach((v, c) => v === t && cells.push([r, c])));
          if (cells.length === 0) continue;
          // Some placement of the pattern containing (x, y) must match every cell inside the map.
          const fits = cells.some(([r, c]) => {
            for (let rr = 0; rr < rows; rr++)
              for (let cc = 0; cc < cols; cc++) {
                const mx = x - c + cc, my = y - r + rr;
                if (mx < 0 || my < 0 || mx >= width || my >= height) continue;
                if (e.tiles[rr][cc] >= 0 && at(mx, my) !== e.tiles[rr][cc]) return false;
              }
            return true;
          });
          expect(fits, `${e.model}: tile ${t} at (${x}, ${y}) of a level in tyrian${ep}.lvl outside its pattern`).toBe(true);
          checked++;
        }
      }
    }
  }
  return checked;
}

// The ground shows about 8 rows; a structure is seen as a run of its rows at the top or bottom of
// the screen (or a screenful in the middle). Wherever such a run of at least minRows rows matches
// in any level, the whole structure must be there.
const SCREEN_ROWS = 8;

/** Patterns with minRows: minRows rows always tell the structure apart. Returns the whole copies found. */
function checkMinRows(entries: readonly TileModelEntry[]): number {
  const shared = entries.filter((e) => e.minRows !== undefined);
  let found = 0;
  for (const { ep, level, shapes } of levels()) {
    for (const e of shared.filter((m) => m.shapes === shapes)) {
      const { width, height } = MAP_SIZES[e.layer];
      const at = (x: number, y: number) => tileAt(level, e.layer, x, y);
      const rows = e.tiles.length, cols = e.tiles[0].length;
      const need = Math.min(e.minRows!, rows);
      for (let ax = 0; ax + cols <= width; ax++) {
        for (let ay = -rows + 1; ay < height; ay++) {
          // Which of the pattern's rows (inside the map) hold all their tiles here.
          const rowOk = e.tiles.map((row, r) => {
            const y = ay + r;
            if (y < 0 || y >= height) return null;
            return row.every((t, c) => t < 0 || at(ax + c, y) === t);
          });
          if (rowOk.every((v) => v === true)) {
            found++;
            continue;
          }
          for (let a = 0; a < rows; a++) {
            for (let b = a + need - 1; b < Math.min(rows, a + SCREEN_ROWS); b++) {
              if (!(a === 0 || b === rows - 1 || b - a + 1 === SCREEN_ROWS)) continue;
              let ok = true;
              for (let r = a; r <= b && ok; r++) ok = rowOk[r] === true;
              expect(ok, `${e.model}: rows ${a}-${b} match at (${ax}, ${ay}) of a level in tyrian${ep}.lvl without the rest`).toBe(false);
            }
          }
        }
      }
    }
  }
  return found;
}

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("structure patterns in the real maps", () => {
  test("wherever a pattern's tile is on its layer, the whole pattern is there (or cut by the map's edge)", () => {
    expect(checkWholePatterns(TILE_MODELS)).toBeGreaterThan(0);
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("structure patterns with minRows in the real maps", () => {
  test("minRows rows always tell the structure apart from other terrain", () => {
    const found = checkMinRows(TILE_MODELS);
    if (TILE_MODELS.some((e) => e.minRows !== undefined)) expect(found).toBeGreaterThan(0);
  }, 60_000); // scans every level's maps
});

// TYRIAN's (map 1-9) structures, planned in assets/blender/tiles/tyrbld_patterns.json and built one
// by one (lib_tyrbld.py): the plan is checked here before (and after) each model lands, so every
// pattern is told apart from the others and from terrain, and wins over the per-tile models.
interface PlannedStructure {
  layer: 0 | 2;
  tiles: number[][];
  minRows: number | null;
  keepTiles?: boolean;
  occurrences: [number, number][];
  replaces: string[];
  variants?: { name: string; tiles: number[][]; offset: [number, number] }[];
}
const PLAN = JSON.parse(readFileSync(new URL("../../assets/blender/tiles/tyrbld_patterns.json", import.meta.url), "utf8")) as {
  structures: Record<string, PlannedStructure>;
};

/** The plan as tile model entries (what each unit's export writes), variants included. */
function plannedEntries(): TileModelEntry[] {
  const out: TileModelEntry[] = [];
  for (const [name, s] of Object.entries(PLAN.structures)) {
    const base = { model: `tiles/shapesz/tyrbld-${name}`, shapes: "shapesz.dat", layer: s.layer } as const;
    const extra = { ...(s.minRows !== null ? { minRows: s.minRows } : {}), ...(s.keepTiles !== undefined ? { keepTiles: s.keepTiles } : {}) };
    out.push({ ...base, tiles: s.tiles, ...extra });
    for (const v of s.variants ?? []) out.push({ ...base, tiles: v.tiles, offset: v.offset, ...extra });
  }
  return out;
}

/** The committed entries as they'll be once every planned model has landed. */
function withPlan(): { all: TileModelEntry[]; planned: TileModelEntry[] } {
  const planned = plannedEntries();
  const replaced = new Set(Object.values(PLAN.structures).flatMap((s) => s.replaces.map((n) => `tiles/shapesz/${n.replace(/^shapesz-/, "")}`)));
  const kept = TILE_MODELS.filter((e) => !replaced.has(e.model) && !e.model.startsWith("tiles/shapesz/tyrbld-"));
  return { all: [...kept, ...planned], planned };
}

const cellCount = (e: TileModelEntry) => e.tiles.flat().filter((t) => t >= 0).length;

describe("TYRIAN structure plan (tyrbld_patterns.json)", () => {
  test("each structure's pattern is where the plan says, and its tiles are claimed once per pattern size", () => {
    const { all } = withPlan();
    const claimed = new Map<string, string>();
    for (const e of all) {
      if (e.minRows !== undefined) continue;
      for (const t of e.tiles.flat()) {
        if (t < 0) continue;
        const k = `${e.layer}:${t}:${e.tiles.length}x${e.tiles[0].length}`;
        expect(claimed.get(k), `${k} claimed by ${claimed.get(k)} and ${e.model}`).toBeUndefined();
        claimed.set(k, e.model);
      }
    }
    for (const s of Object.values(PLAN.structures)) for (const row of s.tiles) expect(row.length).toBe(s.tiles[0].length);
  });

  test.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("the planned patterns are told apart from each other and from terrain in every level", () => {
    const { planned } = withPlan();
    expect(checkWholePatterns(planned)).toBeGreaterThan(0);
    expect(checkMinRows(planned)).toBeGreaterThan(0);
    // Every copy the plan lists is in map 1-9.
    const tyrian = parseLevelFile(readData("tyrian1.lvl")).levels[8];
    for (const [name, s] of Object.entries(PLAN.structures)) {
      for (const [row, col] of s.occurrences) {
        s.tiles.forEach((r, dr) =>
          r.forEach((t, dc) => {
            if (t >= 0 && col + dc < MAP_SIZES[s.layer].width) expect(tileAt(tyrian, s.layer, col + dc, row + dr), `${name} at (${col}, ${row})`).toBe(t);
          }),
        );
      }
    }
   }, 60_000); // scans every level's maps

  test.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("on screen, a structure's tiles go to the structure (not a per-tile model) and nothing else is taken for one", () => {
    const { all, planned } = withPlan();
    const idx = new TileModelIndex(all);
    const plannedSet = new Set(planned);
    let found = 0;
    for (const { ep, n, level, shapes } of levels()) {
      if (shapes !== "shapesz.dat") continue;
      for (const layer of [0, 2] as const) {
        const { width, height } = MAP_SIZES[layer];
        const mine = planned.filter((e) => e.layer === layer);
        const tiles = new Set(mine.flatMap((e) => e.tiles.flat()).filter((t) => t >= 0));
        let any = false;
        for (let i = 0; i < width * height && !any; i++) any = tiles.has(tileAt(level, layer, i % width, Math.floor(i / width)));
        if (!any) continue;
        // Every whole copy (inside the map's width, as tileModels.ts places them) of each planned pattern.
        const copies = new Map<TileModelEntry, Set<number>>();
        for (const e of mine) {
          const rows = e.tiles.length, cols = e.tiles[0].length;
          const set = new Set<number>();
          for (let ax = 0; ax + cols <= width; ax++)
            for (let ay = -rows + 1; ay < height; ay++) {
              let ok = true, cells = 0;
              for (let r = 0; r < rows && ok; r++)
                for (let c = 0; c < cols && ok; c++) {
                  const t = e.tiles[r][c], y = ay + r;
                  if (t < 0 || y < 0 || y >= height) continue;
                  ok = tileAt(level, layer, ax + c, y) === t;
                  cells++;
                }
              if (ok && cells > 0) set.add(ay * width + ax);
            }
          copies.set(e, set);
        }
        for (let top = -SCREEN_ROWS + 1; top < height; top++) {
          const draws: TileDraw[] = [];
          for (let y = Math.max(0, top); y < Math.min(height, top + SCREEN_ROWS); y++)
            for (let x = 0; x < width; x++) {
              const t = tileAt(level, layer, x, y);
              if (t >= 0) draws.push(tileDraw(layer, y * width + x, t));
            }
          idx.prepare(draws);
          for (const d of draws) {
            const index = d.key - layer * BG_KEY_LAYER;
            const x = index % width, y = Math.floor(index / width);
            const m = idx.match(d);
            const where = `tyrian${ep}.lvl level ${n} layer ${layer} (${x}, ${y}), screen rows ${top}-${top + SCREEN_ROWS - 1}`;
            if (m && plannedSet.has(m.entry)) {
              // Never a structure where there's none.
              expect(copies.get(m.entry)!.has(m.anchorKey - layer * BG_KEY_LAYER), `${m.entry.model} matched at ${where} without its copy`).toBe(true);
            }
            // A cell of a whole copy, with enough of its rows on screen, goes to that structure (or a bigger one).
            for (const e of mine) {
              const rows = e.tiles.length, cols = e.tiles[0].length;
              for (let r = 0; r < rows; r++)
                for (let c = 0; c < cols; c++) {
                  if (e.tiles[r][c] !== tileAt(level, layer, x, y) || x - c < 0) continue;
                  const anchor = (y - r) * width + (x - c);
                  if (!copies.get(e)!.has(anchor)) continue;
                  let seen = 0;
                  for (let rr = 0; rr < rows; rr++) {
                    const yy = y - r + rr;
                    if (yy >= Math.max(0, top) && yy < Math.min(height, top + SCREEN_ROWS) && e.tiles[rr].some((t) => t >= 0)) seen++;
                  }
                  if (seen < Math.min(e.minRows ?? 1, rows)) continue;
                  expect(m && plannedSet.has(m.entry), `${e.model}'s tile at ${where} not matched to a structure (got ${m?.entry.model})`).toBe(true);
                  expect(cellCount(m!.entry), `${e.model}'s tile at ${where} went to ${m!.entry.model}`).toBeGreaterThanOrEqual(cellCount(e));
                  found++;
                }
            }
          }
        }
      }
    }
    expect(found).toBeGreaterThan(0);
  }, 120_000);
});
