// TYRIAN's floating islands (map 1-9, background 3) look the same from tile to tile (DECISIONS.md
// D63): every island cell is drawn by a model, the rock tile models are the tiles' own pixels in one
// shared set of palette colours, and the rock that the structures on the islands carry stays plain
// (their concept bake leaves it alone), so it matches the per-tile rock next to it.
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import type { TileDraw } from "../../src/sim/draw";
import { TILE_MODELS, TileModelIndex } from "../../src/render/remaster/tileModels";
import { BG_KEY_LAYER } from "../../src/sim/backgrnd";
import { MAP_SIZES, parseLevelFile } from "../../src/data/levels";
import { hasData, readData } from "../data/dataDir";

/** The island rock tiles of shapesz.dat (assets/blender/tiles/shapesz_bg3.py, recipe "rock"). */
const ROCK_TILES = [120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 140, 141, 142, 150, 151, 152];
/** lib_tiles.ROCK_COLOURS: the only palette indices the island rock is drawn in. */
const ROCK_COLOURS = new Set([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 24, 25, 27, 28, 163, 165, 167, 169, 171]);
/** TYRIAN's structures that stand on the islands and carry their tiles' rock (Structure.rock). */
const ON_ROCK = ["crater", "lava-pit", "purple-2x2", "purple-2x3", "purple-2x5", "purple-cross", "purple-orb", "drum-e", "drum-w", "white-gate-e", "white-gate-w", "fortress"];

interface GltfMaterial {
  name: string;
  extras?: { tyrian_plain?: boolean };
  pbrMetallicRoughness?: { baseColorTexture?: unknown };
  normalTexture?: unknown;
}

/** The JSON chunk of a .glb in public/models/. */
function gltf(model: string): { materials?: GltfMaterial[]; images?: unknown[] } {
  const b = readFileSync(new URL(`../../public/models/${model}.glb`, import.meta.url));
  const len = b.readUInt32LE(12);
  return JSON.parse(b.subarray(20, 20 + len).toString("utf8"));
}

const palIndex = (name: string) => Number(/^pal_(\d+)/.exec(name)?.[1] ?? NaN);

describe("island rock models", () => {
  test("every rock tile is drawn in the shared rock colours, untextured", () => {
    for (const n of ROCK_TILES) {
      const entry = TILE_MODELS.find((e) => e.layer === 2 && e.tiles.length === 1 && e.tiles[0].length === 1 && e.tiles[0][0] === n);
      expect(entry, `tile ${n} has a per-tile model`).toBeDefined();
      const doc = gltf(entry!.model);
      expect(doc.images ?? [], `${entry!.model} has no textures`).toEqual([]);
      for (const m of doc.materials ?? []) expect(ROCK_COLOURS.has(palIndex(m.name)), `${entry!.model}: ${m.name}`).toBe(true);
    }
  });

  test("the structures on the islands carry plain rock in the same colours", () => {
    for (const name of ON_ROCK) {
      const plain = (gltf(`tiles/shapesz/tyrbld-${name}`).materials ?? []).filter((m) => m.extras?.tyrian_plain);
      expect(plain.length, `tyrbld-${name} has rock`).toBeGreaterThan(0);
      for (const m of plain) {
        expect(ROCK_COLOURS.has(palIndex(m.name)), `tyrbld-${name}: ${m.name}`).toBe(true);
        expect(m.pbrMetallicRoughness?.baseColorTexture, `tyrbld-${name}: ${m.name} is not baked`).toBeUndefined();
        expect(m.normalTexture, `tyrbld-${name}: ${m.name} has no normal map`).toBeUndefined();
      }
    }
  });
});

describe.skipIf(!hasData("tyrian1.lvl"))("TYRIAN's background 3 in the real map", () => {
  test("every painted cell is drawn by a model in every screenful", () => {
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[8];
    const layer = 2;
    const { width, height } = MAP_SIZES[layer];
    // Tile 0 is all index 0, see-through on layers 1 and 2: nothing is drawn there.
    const at = (x: number, y: number) => level.mapSh[layer][level.maps[layer][y * width + x]] - 1;
    const idx = new TileModelIndex(TILE_MODELS);
    const missing = new Set<string>();
    let cells = 0;
    for (let top = -7; top < height; top++) {
      const draws: TileDraw[] = [];
      for (let y = Math.max(0, top); y < Math.min(height, top + 8); y++)
        for (let x = 0; x < width; x++) {
          const t = at(x, y);
          if (t > 0) draws.push({ kind: "tile", key: layer * BG_KEY_LAYER + y * width + x, tileId: `shapesz.dat:${t}`, layer, x: 0, y: 0 } as unknown as TileDraw);
        }
      idx.prepare(draws);
      for (const d of draws) {
        cells++;
        if (!idx.match(d)) missing.add(`${d.tileId} at map index ${d.key - layer * BG_KEY_LAYER}`);
      }
    }
    expect(cells).toBeGreaterThan(0);
    expect([...missing]).toEqual([]);
  });
});
