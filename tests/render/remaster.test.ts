// The remastered backgrounds (DECISIONS.md D34): the MMPX upscaler, the context-aware ground atlas
// and the structure models' tile patterns.
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

describe("structure patterns", () => {
  const bunker: TileModelEntry = { model: "tiles/test/bunker", shapes: "shapesz.dat", layer: 0, tiles: [[320, 321], [330, 331]] };
  const rock: TileModelEntry = { model: "tiles/test/rock", shapes: "shapesz.dat", layer: 2, tiles: [[141]] };
  const tileDraw = (layer: 0 | 1 | 2, index: number, tile: number, x = 0, y = 0): TileDraw => ({
    kind: "tile", layer, tile: new Uint8Array(0), tileId: `shapesz.dat:${tile}`, x, y, pass: Pass.Background1, key: layer * BG_KEY_LAYER + index, effect: "none",
  });

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

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("structure patterns in the real maps", () => {
  test("wherever a pattern's tile is on its layer, the whole pattern is there (or cut by the map's edge)", () => {
    const multi = TILE_MODELS.filter((e) => e.tiles.length * e.tiles[0].length > 1 && e.minRows === undefined);
    let checked = 0;
    for (let ep = 1; ep <= 4; ep++) {
      if (!hasData(`tyrian${ep}.lvl`)) continue;
      for (const level of parseLevelFile(readData(`tyrian${ep}.lvl`)).levels) {
        const shapes = `shapes${level.shapeFile.toLowerCase()}.dat`;
        for (const e of multi.filter((m) => m.shapes === shapes)) {
          const { width, height } = MAP_SIZES[e.layer];
          const at = (x: number, y: number) => level.mapSh[e.layer][level.maps[e.layer][y * width + x]] - 1;
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
    }
    expect(checked).toBeGreaterThan(0);
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat"))("structure patterns with minRows in the real maps", () => {
  // The ground shows about 8 rows; a structure is seen as a run of its rows at the top or bottom of
  // the screen (or a screenful in the middle). Wherever such a run of at least minRows rows matches
  // in any level, the whole structure must be there.
  const SCREEN_ROWS = 8;
  test("minRows rows always tell the structure apart from other terrain", () => {
    const shared = TILE_MODELS.filter((e) => e.minRows !== undefined);
    let found = 0;
    for (let ep = 1; ep <= 4; ep++) {
      if (!hasData(`tyrian${ep}.lvl`)) continue;
      for (const level of parseLevelFile(readData(`tyrian${ep}.lvl`)).levels) {
        const shapes = `shapes${level.shapeFile.toLowerCase()}.dat`;
        for (const e of shared.filter((m) => m.shapes === shapes)) {
          const { width, height } = MAP_SIZES[e.layer];
          const at = (x: number, y: number) => level.mapSh[e.layer][level.maps[e.layer][y * width + x]] - 1;
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
    }
    if (shared.length > 0) expect(found).toBeGreaterThan(0);
  }, 60_000); // scans every level's maps
});
