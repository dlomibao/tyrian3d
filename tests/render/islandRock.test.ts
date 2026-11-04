// TYRIAN's floating islands (map 1-9, background 3) look the same from tile to tile (DECISIONS.md
// D63, D84): every island cell is drawn by a model; the rock tile models, the rock the structures on
// the islands carry and the rock round the machines of the enemies that sit on them (D66) are all the
// HD rock: one material with a palette-data texture (lib_tiles.rock_material, rockMaterial.ts), left
// alone by the concept bake and textured from above. Every pair of rock tiles the map puts side by
// side has an edge band on both sides, so the stones meet across every seam.
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import type { TileDraw } from "../../src/sim/draw";
import { TILE_MODELS, TileModelIndex } from "../../src/render/remaster/tileModels";
import { BG_KEY_LAYER } from "../../src/sim/backgrnd";
import { MAP_SIZES, parseLevelFile } from "../../src/data/levels";
import { hasData, readData } from "../data/dataDir";

/** The island rock tiles of shapesz.dat (assets/blender/tiles/shapesz_bg3.py, recipe "rock"). */
const ROCK_TILES = [120, 121, 122, 123, 124, 130, 131, 132, 133, 134, 140, 141, 142, 150, 151, 152];
/** lib_rock_hd.RAMPS: the palette ramps the island rock's texture steps through (grey, tan, brass). */
const ROCK_RAMPS = [0, 10, 1];
/** TYRIAN's structures that stand on the islands and carry their tiles' rock (Structure.rock). */
const ON_ROCK = ["crater", "lava-pit", "purple-2x2", "purple-2x3", "purple-2x5", "purple-cross", "purple-orb", "drum-e", "drum-w", "white-gate-e", "white-gate-w", "fortress"];

/** The enemy pieces whose sprites paint island rock round the machine (lib_tiles.sprite_rock, D66). */
const ENEMIES_ON_ROCK = [
  "newsh2-279", "newsh2-281", "newsh2-283", // purple octagon wall
  "newsh2-273", "newsh2-275", "newsh2-277", // purple octagon wall, the long row
  "newsh2-245", "newsh2-169", "newsh2-207", // eye fortress
  "newsh2-15", "newsh2-17", "newsh2-53", "newsh2-55", // red machinery
  "newsh2-153", // star core panel
];

interface GltfNode {
  name?: string;
  mesh?: number;
  children?: number[];
  extras?: { tyrian_outline?: boolean; tyrian_ground?: boolean };
}

interface GltfMaterial {
  name: string;
  extras?: { tyrian_plain?: boolean; tyrian_rock_ramps?: number[]; tyrian_rock_bands?: string[]; tyrian_rock_band_depth?: number };
  pbrMetallicRoughness?: { baseColorTexture?: unknown };
  emissiveTexture?: unknown;
  normalTexture?: unknown;
}

/** A float accessor of a .glb as rows of `n` (the BIN chunk follows the JSON chunk). */
function floats(model: string, accessor: number, n: number): number[][] {
  const b = readFileSync(new URL(`../../public/models/${model}.glb`, import.meta.url));
  const len = b.readUInt32LE(12);
  const doc = JSON.parse(b.subarray(20, 20 + len).toString("utf8"));
  const a = doc.accessors[accessor];
  const view = doc.bufferViews[a.bufferView];
  const start = 20 + len + 8 + (view.byteOffset ?? 0) + (a.byteOffset ?? 0);
  const out: number[][] = [];
  for (let i = 0; i < a.count; i++) out.push(Array.from({ length: n }, (_, k) => b.readFloatLE(start + (i * n + k) * 4)));
  return out;
}

/** Pearson correlation of two columns. */
function corr(xs: number[], ys: number[]): number {
  const mx = xs.reduce((a, v) => a + v, 0) / xs.length;
  const my = ys.reduce((a, v) => a + v, 0) / ys.length;
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < xs.length; i++) {
    sxy += (xs[i] - mx) * (ys[i] - my);
    sxx += (xs[i] - mx) ** 2;
    syy += (ys[i] - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

/**
 * Whether a model's rock is textured from above: on every rock primitive the texture's UVs follow
 * the position (u with x, v with z). The concept bake re-exports structures with its own UV map; the
 * rock must stay on its own (texture_bake.keep_plain_uvs).
 */
function expectRockMappedFromAbove(model: string): void {
  const b = readFileSync(new URL(`../../public/models/${model}.glb`, import.meta.url));
  const doc = JSON.parse(b.subarray(20, 20 + b.readUInt32LE(12)).toString("utf8"));
  for (const mesh of doc.meshes)
    for (const prim of mesh.primitives) {
      const m = doc.materials[prim.material];
      if (!m.extras?.tyrian_rock_ramps) continue;
      const pos = floats(model, prim.attributes.POSITION, 3);
      const uv = floats(model, prim.attributes[`TEXCOORD_${m.pbrMetallicRoughness.baseColorTexture.texCoord ?? 0}`], 2);
      // A material can cover a few cells of one tile (its UVs repeat), so a loose bound.
      expect(corr(pos.map((p) => p[0]), uv.map((u) => u[0])), `${model}: ${m.name} u follows x`).toBeGreaterThan(0.3);
      expect(corr(pos.map((p) => p[2]), uv.map((u) => u[1])), `${model}: ${m.name} v follows z`).toBeGreaterThan(0.3);
    }
}

/** The JSON chunk of a .glb in public/models/. */
function gltf(model: string): {
  materials?: GltfMaterial[];
  images?: unknown[];
  nodes?: GltfNode[];
  meshes?: { primitives: { material?: number }[] }[];
} {
  const b = readFileSync(new URL(`../../public/models/${model}.glb`, import.meta.url));
  const len = b.readUInt32LE(12);
  return JSON.parse(b.subarray(20, 20 + len).toString("utf8"));
}

/** An HD rock material: the ramps, its texture, plain (no bake), no baked normal map. */
function expectRock(m: GltfMaterial, what: string, ramps = ROCK_RAMPS): void {
  expect(m.extras?.tyrian_rock_ramps?.slice(0, 3), `${what}: ${m.name} is HD rock`).toEqual(ramps);
  expect(m.extras?.tyrian_plain, `${what}: ${m.name} is plain`).toBe(true);
  expect(m.pbrMetallicRoughness?.baseColorTexture, `${what}: ${m.name} has its texture`).toBeDefined();
  expect(m.normalTexture, `${what}: ${m.name} has no baked normal map`).toBeUndefined();
}

function tileEntry(n: number) {
  return TILE_MODELS.find((e) => e.layer === 2 && e.tiles.length === 1 && e.tiles[0].length === 1 && e.tiles[0][0] === n);
}

describe("island rock models", () => {
  test("every rock tile is one HD rock material with its texture and edge bands", () => {
    for (const n of ROCK_TILES) {
      const entry = tileEntry(n);
      expect(entry, `tile ${n} has a per-tile model`).toBeDefined();
      const doc = gltf(entry!.model);
      expect((doc.materials ?? []).map((m) => m.name), entry!.model).toEqual([`rock_t${n}`]);
      const m = doc.materials![0];
      expectRock(m, entry!.model);
      expect(m.emissiveTexture, `${entry!.model}: its edge bands`).toBeDefined();
      expect(m.extras?.tyrian_rock_bands?.length, `${entry!.model}: its edge bands`).toBeGreaterThan(0);
      expect((doc.images ?? []).length, `${entry!.model}: texture and bands`).toBe(2);
      expectRockMappedFromAbove(entry!.model);
    }
  });

  test("the structures on the islands carry the same HD rock", () => {
    for (const name of ON_ROCK) {
      const rock = (gltf(`tiles/shapesz/tyrbld-${name}`).materials ?? []).filter((m) => m.extras?.tyrian_rock_ramps);
      expect(rock.length, `tyrbld-${name} has rock`).toBeGreaterThan(0);
      for (const m of rock) {
        // rock_t<tile>[_<hash>: dark under its parts]_<row>_<col>: one material per cell, with the
        // tile's edge bands, so each cell draws those of its own neighbours (D84).
        expect(m.name, `tyrbld-${name}`).toMatch(/^rock_t\d+(_[0-9a-f]{8})?_\d+_\d+$/);
        expectRock(m, `tyrbld-${name}`);
        expect((m.extras as { tyrian_rock_cell?: number[] })?.tyrian_rock_cell?.length, `tyrbld-${name}: ${m.name} cell`).toBe(2);
        expect(m.extras?.tyrian_rock_bands?.length, `tyrbld-${name}: ${m.name} bands`).toBeGreaterThan(0);
      }
      expectRockMappedFromAbove(`tiles/shapesz/tyrbld-${name}`);
    }
  });
});

describe("enemies on the islands", () => {
  test("carry their island rock as plain ground, apart from the machine and its outline", () => {
    for (const piece of ENEMIES_ON_ROCK) {
      const doc = gltf(`enemies/${piece}`);
      const nodes = doc.nodes ?? [];
      const mats = (n: GltfNode) => (n.mesh === undefined ? [] : doc.meshes![n.mesh].primitives.map((p) => p.material!));
      const ground = nodes.filter((n) => n.extras?.tyrian_ground);
      expect(ground.length, `${piece} has its rock`).toBe(1);
      expect(ground[0].extras?.tyrian_outline, `${piece}: the rock has no outline shell`).toBeUndefined();
      expect(nodes.filter((n) => n.extras?.tyrian_outline).length, `${piece} keeps the machine's outline`).toBe(1);
      const rockMats = new Set(mats(ground[0]));
      expect(rockMats.size).toBeGreaterThan(0);
      expect(rockMats.size, `${piece}: one rock material`).toBe(1);
      for (const i of rockMats) expectRock(doc.materials![i], piece);
      expectRockMappedFromAbove(`enemies/${piece}`);
      // The machine's own parts never use the rock's material (nor the rock the machine's baked ones).
      for (const n of nodes) if (!n.extras?.tyrian_ground) for (const i of mats(n)) expect(rockMats.has(i), `${piece}: ${n.name}`).toBe(false);
    }
  });
});

describe.skipIf(!hasData("tyrian1.lvl"))("TYRIAN's background 3 in the real map", () => {
  test("every pair of rock tiles side by side on the map has an edge band on both sides", () => {
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[8];
    const layer = 2;
    const { width, height } = MAP_SIZES[layer];
    const at = (x: number, y: number) => level.mapSh[layer][level.maps[layer][y * width + x]] - 1;
    const bands = new Map(ROCK_TILES.map((n) => [n, new Set(gltf(tileEntry(n)!.model).materials![0].extras?.tyrian_rock_bands ?? [])]));
    const missing = new Set<string>();
    let pairs = 0;
    for (let y = 0; y < height; y++)
      for (let x = 0; x < width; x++) {
        const a = at(x, y);
        if (!bands.has(a)) continue;
        for (const [dx, dy, side, back] of [[1, 0, "right", "left"], [0, 1, "down", "up"]] as const) {
          if (x + dx >= width || y + dy >= height) continue;
          const b = at(x + dx, y + dy);
          if (!bands.has(b)) continue;
          pairs++;
          if (!bands.get(a)!.has(`${side}:${b}`)) missing.add(`${a} ${side}:${b}`);
          if (!bands.get(b)!.has(`${back}:${a}`)) missing.add(`${b} ${back}:${a}`);
        }
      }
    expect(pairs).toBeGreaterThan(1000);
    expect([...missing]).toEqual([]);
  });

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
