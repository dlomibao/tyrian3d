// A level preloads only the structure models whose pattern can match on its maps (DECISIONS.md D236):
// TileModelIndex.modelsOnMaps runs match() on every window of map cells the sim can draw.
//
// - Small maps: a lone tile of a pattern loads nothing; the whole pattern, or the part of it the
//   map's edge leaves, does; a per-tile model that a bigger pattern always takes over loads nothing,
//   unless the bigger one can show too few rows to match.
// - The real maps (episode 1 with the test bot, tests/sim/bot.ts; STRUCTURE_PRELOAD_EPISODES for
//   others): every structure match() draws on
//   every tick is in modelsOnMaps, so a structure the level shows is never left to load on sight.
//   STRUCTURE_PRELOAD_REPORT=1 prints each level's models: preloaded before, now, and drawn.
import { describe, expect, test } from "vitest";
import { TILE_MODELS, TileModelIndex, type TileModelEntry } from "../../src/render/remaster/tileModels";
import { BG_KEY_LAYER } from "../../src/sim/backgrnd";
import { Pass, type TileDraw } from "../../src/sim/draw";
import { hasData, readData } from "../data/dataDir";

const REPORT = process.env.STRUCTURE_PRELOAD_REPORT === "1";
const SHAPES = "shapesz.dat";
const W = [14, 14, 15];
const HEIGHT = 40;

/** A layer's map of `HEIGHT` rows of `cells` ([row, col, tile]); the rest is tile 1 (layer 0) or none. */
function mapWith(layer: 0 | 1 | 2, cells: [number, number, number][]): Int16Array {
  const m = new Int16Array(W[layer] * HEIGHT).fill(layer === 0 ? 1 : -1);
  for (const [r, c, t] of cells) m[r * W[layer] + c] = t;
  return m;
}

const maps = (layer: 0 | 1 | 2, cells: [number, number, number][]) =>
  [0, 1, 2].map((l) => (l === layer ? mapWith(layer, cells) : new Int16Array(W[l] * HEIGHT).fill(-1)));

/** The cells of `tiles` placed with its top-left at (row, col). */
const place = (tiles: number[][], row: number, col: number): [number, number, number][] =>
  tiles.flatMap((line, r) => line.flatMap((t, c): [number, number, number][] => (t < 0 ? [] : [[row + r, col + c, t]])));

describe("structure models a level can draw (modelsOnMaps)", () => {
  const bunker: TileModelEntry = { model: "tiles/test/bunker", shapes: SHAPES, layer: 0, tiles: [[320, 321], [330, 331]] };
  const orb: TileModelEntry = { model: "tiles/test/orb", shapes: SHAPES, layer: 2, tiles: [[155, 156, 157], [165, 149, 167], [175, 176, 177]], minRows: 2 };
  const t165: TileModelEntry = { model: "tiles/test/t165", shapes: SHAPES, layer: 2, tiles: [[165]] };

  test("a pattern with minRows doesn't load for a lone tile or row of it", () => {
    const pad: TileModelEntry = { ...bunker, model: "tiles/test/pad", minRows: 2 };
    const idx = new TileModelIndex([pad]);
    expect(idx.modelsOnMaps(SHAPES, maps(0, [[10, 5, 320]]))).toEqual(new Set());
    // Its top row, over a row that isn't the pattern's (the screen's 7 rows always show both).
    expect(idx.modelsOnMaps(SHAPES, maps(0, [[10, 5, 320], [10, 6, 321]]))).toEqual(new Set());
    expect(idx.modelsOnMaps(SHAPES, maps(0, place(pad.tiles, 10, 5)))).toEqual(new Set([pad.model]));
  });

  test("the whole pattern loads it, and so does any part of it a screen's edges can leave", () => {
    const idx = new TileModelIndex([bunker]);
    expect(idx.modelsOnMaps(SHAPES, maps(0, place(bunker.tiles, 10, 5)))).toEqual(new Set([bunker.model]));
    expect(idx.modelsOnMaps(SHAPES, maps(0, [[10, 5, 999]]))).toEqual(new Set());
    // Its bottom row in the map's first row: the top row would be above the map.
    expect(idx.modelsOnMaps(SHAPES, maps(0, [[0, 5, 330], [0, 6, 331]]))).toEqual(new Set([bunker.model]));
    // A lone tile with nothing drawn round it (layer 2) shows the pattern as far as the screen does.
    expect(new TileModelIndex([{ ...bunker, layer: 2 }]).modelsOnMaps(SHAPES, maps(2, [[10, 5, 320]]))).toEqual(new Set([bunker.model]));
    // Even among other tiles, a lone tile of a pattern without minRows loads it: a screen row is 12
    // of the map's 14 cells from wherever the scroll starts it (or wraps it, D236), so some window
    // ends right after the tile, on the screen's last row.
    expect(idx.modelsOnMaps(SHAPES, maps(0, [[10, 5, 320]]))).toEqual(new Set([bunker.model]));
  });

  test("a per-tile model that a bigger pattern always takes over doesn't load; one that can show does", () => {
    const idx = new TileModelIndex([orb, t165]);
    expect(idx.modelsOnMaps(SHAPES, maps(2, place(orb.tiles, 10, 4)))).toEqual(new Set([orb.model]));
    // The orb's middle row in the map's last row (its bottom row off the map): with the row above off
    // screen, that one row is too few for minRows, so the tile's own model draws.
    expect(idx.modelsOnMaps(SHAPES, maps(2, place(orb.tiles.slice(0, 2), HEIGHT - 2, 4)))).toEqual(new Set([orb.model, t165.model]));
    expect(idx.modelsOnMaps(SHAPES, maps(2, place(orb.tiles.slice(1, 2), HEIGHT - 1, 4)))).toEqual(new Set([t165.model]));
    // A lone 165 is the tile's own model.
    expect(idx.modelsOnMaps(SHAPES, maps(2, [[20, 7, 165]]))).toEqual(new Set([t165.model]));
  });

  test("it agrees with match() on every window the sim can draw, on random small maps", () => {
    // Patterns sharing tiles (precedence), with minRows, and per-tile ones, over maps of a few tiles.
    const entries: TileModelEntry[] = [
      { model: "tiles/test/big", shapes: SHAPES, layer: 0, tiles: [[1, 2, 2, 3], [4, 5, 5, 6], [7, 8, 8, 9]], minRows: 2 },
      { model: "tiles/test/bar", shapes: SHAPES, layer: 0, tiles: [[1, 2, 3], [7, 8, 9]], minRows: 2 },
      bunker,
      { model: "tiles/test/col", shapes: SHAPES, layer: 0, tiles: [[5], [8]] },
      { model: "tiles/test/t2", shapes: SHAPES, layer: 0, tiles: [[2]] },
      { model: "tiles/test/t8", shapes: SHAPES, layer: 0, tiles: [[8]] },
      { ...orb, layer: 2 },
      t165,
      { model: "tiles/test/edge", shapes: SHAPES, layer: 2, tiles: [[155, -1, 157]], minRows: 1 },
    ];
    let seed = 7;
    const rand = (n: number) => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) % n);
    const alphabet = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 320, 321, 330, 331], [], [155, 156, 157, 165, 149, 167, 175, 176, 177]];
    let found = 0;
    for (let trial = 0; trial < 80; trial++) {
      // Some of the patterns, so each decides alone sometimes and loses to a bigger one other times.
      const idx = new TileModelIndex(entries.filter(() => rand(5) < 3));
      const all = [0, 1, 2].map((layer) => {
        const m = new Int16Array(W[layer] * 16).fill(layer === 0 ? 0 : -1);
        const a = alphabet[layer];
        if (a.length) for (let i = 0; i < m.length; i++) if (rand(4) === 0) m[i] = a[rand(a.length)];
        // A copy of a pattern or two, whole or cut.
        for (const e of entries.filter((x) => x.layer === layer)) {
          if (rand(2)) continue;
          const r0 = rand(18) - 2, c0 = rand(W[layer] - e.tiles[0].length + 1);
          e.tiles.forEach((row, r) => row.forEach((t, c) => { if (t >= 0 && r0 + r >= 0 && r0 + r < 16 && rand(8)) m[(r0 + r) * W[layer] + c0 + c] = t; }));
        }
        return m;
      });
      const want = idx.modelsOnMaps(SHAPES, all);
      expect([...seenOnAllWindows(idx, all)].sort(), `trial ${trial}`).toEqual([...want].sort());
      found += want.size;
    }
    expect(found).toBeGreaterThan(20);
  }, 120_000); // every window of 80 maps
});

/** The models match() draws on any window of 7 or 8 screen rows of 12 cells over the maps (backgrnd.ts). */
function seenOnAllWindows(idx: TileModelIndex, all: ArrayLike<number>[]): Set<string> {
  const seen = new Set<string>();
  for (const layer of [0, 1, 2] as const) {
    const map = all[layer];
    for (let m = -9 * W[layer]; m < map.length; m++) {
      for (const rows of [7, 8]) {
        const draws: TileDraw[] = [];
        for (let j = 0; j < rows; j++) {
          for (let t = 0; t < 12; t++) {
            const i = m + j * W[layer] + t;
            if (i < 0 || i >= map.length || map[i] < 0) continue;
            draws.push(tileDraw(layer, i, map[i]));
          }
        }
        idx.prepare(draws);
        for (const d of draws) {
          const hit = idx.match(d);
          if (hit) seen.add(hit.entry.model);
        }
      }
    }
  }
  return seen;
}

function tileDraw(layer: 0 | 1 | 2, index: number, tile: number): TileDraw {
  return { kind: "tile", layer, tile: new Uint8Array(0), tileId: `${SHAPES}:${tile}`, x: 0, y: 0, pass: Pass.Background1, key: layer * BG_KEY_LAYER + index, effect: "none" };
}

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

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
  ...(await import("../../src/sim/levelSprites")),
  ...(await import("../sim/bot")),
});

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat", "tyrian.hdt", "palette.dat", "tyrian.shp"))("structure models in the real maps", () => {
  // STRUCTURE_PRELOAD_EPISODES=1,2,3,4 plays the others too (each from its first level, as far as the bot gets).
  const episodes = (process.env.STRUCTURE_PRELOAD_EPISODES ?? "1").split(",").map(Number);
  test.each(episodes)("every structure the bot sees match() draw in episode %i is one its level preloads", async (episode) => {
    if (!hasData(`tyrian${episode}.lvl`, `levels${episode}.dat`)) return;
    const s = await sim();
    const { g } = s;
    const idx = new TileModelIndex(TILE_MODELS);
    s.mt_srand(1);
    g.res = s.buildResources(files, episode);
    s.loadHelpText(readData("tyrian.hdt"));
    s.newOnePlayerGame(episode);
    const missing: string[] = [];
    let main = g.mainLevel;
    const seen = new Set<number>();
    const levels = Number(process.env.STRUCTURE_PRELOAD_LEVELS ?? 99);
    let played = 0;
    for (let n = 0; n < levels && main > 0 && !seen.has(main); n++) {
      seen.add(main);
      s.loadLevel(files, episode, main);
      g.player[0].items.weapon[0].power = 11;
      s.startLevel();
      s.clearSimInput();
      const shapes = g.lvl.shapesFile;
      const t0 = performance.now();
      const onMaps = idx.modelsOnMaps(shapes, s.levelDrawnMaps()!);
      const ms = performance.now() - t0;
      const anyTile = idx.modelsOfTiles(shapes, s.levelTiles());
      const drawn = new Set<string>();
      let result = s.tick();
      for (let t = 0; t < 60000 && !result.levelOver; t++) {
        idx.prepare(s.drawList.items);
        for (const d of s.drawList.items) {
          if (d.kind !== "tile" || d.effect !== "none" || !idx.has(d)) continue;
          const hit = idx.match(d);
          if (!hit) continue;
          if (!drawn.has(hit.entry.model) && !onMaps.has(hit.entry.model)) missing.push(`main ${main} ${g.levelName.trim()}: ${hit.entry.model} at tick ${t}`);
          drawn.add(hit.entry.model);
        }
        s.botTick(t);
        result = s.tick();
      }
      played++;
      // Every model that can be drawn had a tile on the maps.
      for (const m of onMaps) expect(anyTile.has(m), m).toBe(true);
      if (REPORT) {
        console.log(
          `E${episode} main ${main} ${g.levelName.trim()} (${shapes}): ${result.levelOver ? "completed" : "not completed"}; any tile ${anyTile.size}, ` +
            `pattern ${onMaps.size} (${ms.toFixed(0)} ms), drawn ${drawn.size}; dropped: ${[...anyTile.keys()].filter((m) => !onMaps.has(m)).join(" ") || "-"}; ` +
            `kept, not drawn: ${[...onMaps].filter((m) => !drawn.has(m)).join(" ") || "-"}`,
        );
      }
      if (!result.completed || g.nextLevel <= 0 || g.nextLevel === main) break;
      main = g.nextLevel;
    }
    expect(played).toBeGreaterThan(2);
    expect(missing).toEqual([]);
  }, 600000);
});
