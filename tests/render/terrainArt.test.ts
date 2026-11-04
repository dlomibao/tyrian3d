// HD terrain (DECISIONS.md D57): the manifest, the per-tile fallback, neighbour variants, the
// loader's graceful failures, the seam-free texel maths (checked on a CPU model of the GPU's
// trilinear sampling over a synthetic atlas whose gutters are magenta), and the terrain setting.
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import {
  clampTerrainTexel,
  neighbourTile,
  parseTerrainManifest,
  parseTileId,
  TERRAIN_ALIGN,
  TERRAIN_MAX_LOD,
  TerrainTileset,
  type TerrainMap,
} from "../../src/render/remaster/terrainArt";
import { loadTerrainTileset, TerrainArtSet, type TerrainLoadIo } from "../../src/render/remaster/terrainLoader";
import { loadTerrainStyle, onTerrainStyle, resetTerrainStyle, setTerrainStyle, storedTerrainStyle, terrainStyle, terrainStyleFromSearch } from "../../src/core/terrainStyle";
import { optionsRows, SettingsMenu } from "../../src/app/options";
import { loadPrefs, PREFS_STORAGE_KEY, PREFS_VERSION, savePrefs, type PrefsStorage } from "../../src/app/prefs";

const W = 24 * 8, H = 28 * 8;
const rect = (x: number, y: number) => ({ x, y, w: W, h: H });
const quiet = () => {};

describe("manifest", () => {
  test("keeps well-formed layers, tiles and variants; drops the rest with a warning", () => {
    const warnings: string[] = [];
    const m = parseTerrainManifest(
      {
        scale: 8,
        layers: {
          "0": {
            image: "0.webp",
            tiles: { "5": rect(16, 16), "6": { x: 0, y: 0, w: 96, h: 112 }, nope: rect(16, 256), "7": { x: 1 } },
            variants: { "5": [{ n: { right: 6, up: -1 }, ...rect(224, 16) }, { n: { diagonal: 1 }, ...rect(432, 16) }] },
          },
          "2": { image: "2.webp", tiles: { "9": rect(16, 16) } },
          "3": { image: "3.webp", tiles: { "1": rect(16, 16) } },
          "1": { tiles: { "1": rect(16, 16) } },
        },
      },
      (w) => warnings.push(w),
    )!;
    expect(m.scale).toBe(8);
    expect([...m.layers.keys()].sort()).toEqual([0, 2]);
    const l0 = m.layers.get(0)!;
    expect([...l0.tiles.keys()]).toEqual([5]); // 6 is 4x-sized, "nope" isn't a number, 7 is malformed
    expect(l0.variants.get(5)).toEqual([{ ...rect(224, 16), n: { right: 6, up: -1 } }]);
    expect(warnings.length).toBe(6);
  });

  test("not a manifest → null (the tileset draws as before)", () => {
    for (const bad of [null, 3, "x", {}, { scale: 0, layers: {} }, { scale: 8 }, { scale: 2.5, layers: {} }]) expect(parseTerrainManifest(bad, quiet)).toBeNull();
  });

  test("a rect off the 16-texel grid is kept, with a warning about its far mips", () => {
    const warnings: string[] = [];
    const m = parseTerrainManifest({ scale: 8, layers: { "0": { image: "0.webp", tiles: { "1": rect(8, 16) } } } }, (w) => warnings.push(w))!;
    expect(m.layers.get(0)!.tiles.has(1)).toBe(true);
    expect(warnings[0]).toMatch(/multiple of 16/);
  });

  test("tile ids name the tileset without .dat and the 0-based record", () => {
    expect(parseTileId("shapesz.dat:123")).toEqual(["shapesz", 123]);
    expect(parseTileId("SHAPESZ.DAT:0")).toEqual(["shapesz", 0]);
    expect(parseTileId("shapesz.dat:-1")).toBeNull();
    expect(parseTileId("nonsense")).toBeNull();
  });
});

describe("fallback per tile", () => {
  const manifest = parseTerrainManifest(
    {
      scale: 8,
      layers: {
        "0": { image: "0.webp", tiles: { "1": rect(16, 16), "2": rect(224, 16), "3": rect(16, 4096) }, variants: { "1": [{ n: { right: 2 }, ...rect(432, 16) }] } },
        "1": { image: "1.webp", tiles: { "4": rect(16, 16) } },
      },
    },
    quiet,
  )!;

  test("nothing draws until its atlas has loaded, and never if it failed", () => {
    const t = new TerrainTileset<string>("shapesz", manifest);
    expect(t.tile(0, 1, 0)).toBeUndefined();
    t.setImage("0.webp", { texture: "atlas0", width: 1024, height: 512 });
    expect(t.tile(0, 1, 0)).toEqual({ texture: "atlas0", x: 16, y: 16 });
    expect(t.tile(1, 4, 0)).toBeUndefined(); // 1.webp not loaded
    t.setImage("1.webp", null); // failed
    expect(t.tile(1, 4, 0)).toBeUndefined();
  });

  test("an unlisted tile, another layer's tile, or a rect outside the image falls back", () => {
    const t = new TerrainTileset<string>("shapesz", manifest);
    t.setImage("0.webp", { texture: "a", width: 1024, height: 512 });
    expect(t.tile(0, 99, 0)).toBeUndefined();
    expect(t.tile(2, 1, 0)).toBeUndefined();
    expect(t.tile(0, 3, 0)).toBeUndefined(); // y 4096 is past a 512-high atlas
    expect(t.listed(0, 3)).toBe(true);
    expect(t.listed(0, 99)).toBe(false);
  });

  test("a variant is used where the map's neighbours match it, the plain tile elsewhere", () => {
    const t = new TerrainTileset<string>("shapesz", manifest);
    t.setImage("0.webp", { texture: "a", width: 1024, height: 512 });
    // 3 wide: row 0 = 1 2 1, row 1 = 1 1 1
    const map: TerrainMap = { width: 3, tiles: [1, 2, 1, 1, 1, 1] };
    expect(t.tile(0, 1, 0)?.x).toBe(16); // no map yet: plain
    t.setMap(0, map);
    expect(t.tile(0, 1, 0)?.x).toBe(432); // right of cell 0 is 2
    expect(t.tile(0, 1, 2)?.x).toBe(16); // right of cell 2 is outside
    expect(t.tile(0, 1, 3)?.x).toBe(16);
    // The same key with another tile under it (a debug harness) is looked up again.
    expect(t.tile(0, 2, 0)?.x).toBe(224);
  });

  test("a covered tile (D67) has its own painting, possibly in an atlas of its own; others have none", () => {
    const warnings: string[] = [];
    const m = parseTerrainManifest(
      { scale: 8, layers: { "0": { image: "0.webp", tiles: { "1": rect(16, 16) }, covered: { "1": { ...rect(16, 16), image: "0-covered.webp" }, "2": { x: 3 } } } } },
      (w) => warnings.push(w),
    )!;
    expect(warnings.length).toBe(1); // "2" is malformed
    const t = new TerrainTileset<string>("shapesz", m);
    expect([...t.images.keys()].sort()).toEqual(["0-covered.webp", "0.webp"]);
    t.setImage("0.webp", { texture: "a", width: 1024, height: 512 });
    expect(t.coveredTile(0, 1)).toBeUndefined(); // its atlas hasn't loaded
    t.setImage("0-covered.webp", { texture: "c", width: 1024, height: 512 });
    expect(t.coveredTile(0, 1)).toEqual({ texture: "c", x: 16, y: 16 });
    expect(t.coveredTile(0, 2)).toBeUndefined();
    expect(t.tile(0, 1, 0)).toEqual({ texture: "a", x: 16, y: 16 });
  });

  test("neighbours: outside the map or another row's edge is -1", () => {
    const map: TerrainMap = { width: 2, tiles: [10, 11, 12, 13] };
    expect([neighbourTile(map, 0, "left"), neighbourTile(map, 0, "right"), neighbourTile(map, 0, "up"), neighbourTile(map, 0, "down")]).toEqual([-1, 11, -1, 12]);
    expect([neighbourTile(map, 1, "right"), neighbourTile(map, 2, "left"), neighbourTile(map, 3, "down")]).toEqual([-1, -1, -1]);
  });
});

describe("loading", () => {
  const io = (files: Record<string, unknown>, failImages: string[] = []): TerrainLoadIo & { asked: string[] } => {
    const asked: string[] = [];
    return {
      asked,
      fetchJson: async (url) => {
        asked.push(url);
        if (url in files) return files[url];
        throw new SyntaxError("index.html is not JSON"); // what a dev server's fallback page gives
      },
      loadTexture: async (url) => {
        asked.push(url);
        if (failImages.some((f) => url.endsWith(f))) throw new Error("404");
        return { texture: new THREE.Texture(), width: 1024, height: 1024 };
      },
    };
  };
  const manifest = { scale: 8, layers: { "0": { image: "0.webp", tiles: { "1": rect(16, 16) } }, "2": { image: "2.webp", tiles: { "7": rect(16, 16) } } } };

  test("no manifest, or a bad one → null", async () => {
    expect(await loadTerrainTileset("shapesz", "/", io({}), "art/terrain/")).toBeNull();
    expect(await loadTerrainTileset("shapesz", "/", io({ "/art/terrain/shapesz/manifest.json": { nope: 1 } }), "art/terrain/")).toBeNull();
  });

  test("atlases load beside the manifest; a failed one leaves only its tiles original", async () => {
    const f = io({ "/art/terrain/shapesz/manifest.json": manifest }, ["2.webp"]);
    const t = (await loadTerrainTileset("shapesz", "/", f, "art/terrain/"))!;
    expect(f.asked).toEqual(["/art/terrain/shapesz/manifest.json", "/art/terrain/shapesz/0.webp", "/art/terrain/shapesz/2.webp"]);
    expect(t.tile(0, 1, 0)).toMatchObject({ x: 16, y: 16 });
    expect(t.tile(2, 7, 0)).toBeUndefined();
    // Layer 0 is opaque (not premultiplied), mipmapped, unflipped, sRGB.
    const tex = t.tile(0, 1, 0)!.texture;
    expect([tex.premultiplyAlpha, tex.flipY, tex.generateMipmaps, tex.minFilter, tex.colorSpace]).toEqual([false, false, true, THREE.LinearMipmapLinearFilter, THREE.SRGBColorSpace]);
  });

  test("a merged tileset: rects in images of their own load, layer 0's opaque, the others premultiplied (D83)", async () => {
    const merged = {
      scale: 8,
      layers: {
        "0": { image: "0.webp", tiles: { "1": rect(16, 16), "5": { ...rect(16, 16), image: "0-2.webp" } } },
        "2": { image: "2.webp", tiles: { "7": rect(16, 16), "8": { ...rect(224, 16), image: "2-2.webp" } } },
      },
    };
    const f = io({ "/art/terrain/shapesz/manifest.json": merged });
    const t = (await loadTerrainTileset("shapesz", "/", f, "art/terrain/"))!;
    expect(new Set(f.asked)).toEqual(new Set(["/art/terrain/shapesz/manifest.json", "/art/terrain/shapesz/0.webp", "/art/terrain/shapesz/0-2.webp",
      "/art/terrain/shapesz/2.webp", "/art/terrain/shapesz/2-2.webp"]));
    const premult = (layer: 0 | 2, n: number) => t.tile(layer, n, 0)!.texture.premultiplyAlpha;
    expect([premult(0, 1), premult(0, 5), premult(2, 7), premult(2, 8)]).toEqual([false, false, true, true]);
    expect(t.tile(0, 5, 0)!.texture).not.toBe(t.tile(0, 1, 0)!.texture);
  });

  test("the set loads a tileset once and reports it ready only when done", async () => {
    let calls = 0;
    const set = new TerrainArtSet(async () => (calls++, null));
    expect(set.get("shapesz")).toBeUndefined();
    const a = set.request("shapesz");
    const b = set.request("shapesz");
    expect(a).toBe(b);
    await a;
    expect(set.get("shapesz")).toBeNull();
    expect(calls).toBe(1);
    const failing = new TerrainArtSet(() => Promise.reject(new Error("boom")));
    expect(await failing.request("x")).toBeNull();
  });
});

// --- Seam-free sampling, on a CPU model of the GPU ---

/** One channel atlas with mips by 2x2 box filter, as generateMipmap does. */
function mipChain(base: Float32Array, w: number, h: number): { data: Float32Array; w: number; h: number }[] {
  const levels = [{ data: base, w, h }];
  for (let l = 1; l <= TERRAIN_MAX_LOD; l++) {
    const p = levels[l - 1];
    const nw = p.w >> 1, nh = p.h >> 1;
    const d = new Float32Array(nw * nh);
    for (let y = 0; y < nh; y++) for (let x = 0; x < nw; x++) d[y * nw + x] = (p.data[2 * y * p.w + 2 * x] + p.data[2 * y * p.w + 2 * x + 1] + p.data[(2 * y + 1) * p.w + 2 * x] + p.data[(2 * y + 1) * p.w + 2 * x + 1]) / 4;
    levels.push({ data: d, w: nw, h: nh });
  }
  return levels;
}

/** Bilinear at level l for a position in base-level texels (texel i spans [i, i + 1)). */
function bilinear(level: { data: Float32Array; w: number; h: number }, l: number, tx: number, ty: number): number {
  const s = 2 ** l;
  const x = tx / s - 0.5, y = ty / s - 0.5;
  const x0 = Math.floor(x), y0 = Math.floor(y), fx = x - x0, fy = y - y0;
  const at = (i: number, j: number) => level.data[Math.min(Math.max(j, 0), level.h - 1) * level.w + Math.min(Math.max(i, 0), level.w - 1)];
  return (at(x0, y0) * (1 - fx) + at(x0 + 1, y0) * fx) * (1 - fy) + (at(x0, y0 + 1) * (1 - fx) + at(x0 + 1, y0 + 1) * fx) * fy;
}

function trilinear(levels: ReturnType<typeof mipChain>, tx: number, ty: number, lod: number): number {
  const l0 = Math.floor(lod), l1 = Math.min(l0 + 1, TERRAIN_MAX_LOD), f = lod - l0;
  return bilinear(levels[l0], l0, tx, ty) * (1 - f) + bilinear(levels[l1], l1, tx, ty) * f;
}

describe("seam-free sampling", () => {
  // Two tiles side by side with a 16-texel gutter of "magenta" (1) between and around them; the
  // tiles themselves are 0 inside. Any gutter reaching a sample shows as a value above 0.
  const G = TERRAIN_ALIGN;
  const AW = G + 2 * (W + G), AH = G + H + G;
  const base = new Float32Array(AW * AH).fill(1);
  const origins = [G, G + W + G];
  for (const ox of origins) for (let y = G; y < G + H; y++) base.fill(0, y * AW + ox, y * AW + ox + W);
  const levels = mipChain(base, AW, AH);

  test("the clamp keeps every tap of both blended levels inside the rect", () => {
    for (let lod = 0; lod <= TERRAIN_MAX_LOD; lod += 0.25) {
      const margin = 0.5 * 2 ** Math.ceil(lod);
      for (const t of [-5, 0, 0.1, 3.7, W / 2, W - 0.2, W, W + 9]) {
        const c = clampTerrainTexel(G + t, G, W, lod);
        expect(c - margin).toBeGreaterThanOrEqual(G - 1e-9);
        expect(c + margin).toBeLessThanOrEqual(G + W + 1e-9);
      }
    }
  });

  test("no sample of either tile, edges included, picks up the gutter at any mip level", () => {
    let worst = 0;
    for (let lod = 0; lod <= TERRAIN_MAX_LOD; lod += 0.125) {
      for (const ox of origins) {
        for (let u = 0; u <= 1.0001; u += 1 / 96) {
          for (const v of [0, 0.001, 0.5, 0.999, 1]) {
            const tx = clampTerrainTexel(ox + u * W, ox, W, lod);
            const ty = clampTerrainTexel(G + v * H, G, H, lod);
            worst = Math.max(worst, trilinear(levels, tx, ty, lod));
          }
        }
      }
    }
    expect(worst).toBe(0);
  });

  test("without the clamp the gutter does bleed in (the test can see a seam)", () => {
    expect(trilinear(levels, G + W, G + H / 2, 0)).toBeGreaterThan(0);
    expect(trilinear(levels, G + W - 1, G + H / 2, 3)).toBeGreaterThan(0);
  });

  test("at a shared cell edge each side shows its own edge texel", () => {
    // Tile A's last column is 0.25, tile B's first is 0.75: the two cells meet on these values.
    const b2 = new Float32Array(base);
    for (let y = G; y < G + H; y++) {
      b2[y * AW + origins[0] + W - 1] = 0.25;
      b2[y * AW + origins[1]] = 0.75;
    }
    const lv = mipChain(b2, AW, AH);
    const y = clampTerrainTexel(G + H / 2, G, H, 0);
    expect(trilinear(lv, clampTerrainTexel(origins[0] + W, origins[0], W, 0), y, 0)).toBeCloseTo(0.25);
    expect(trilinear(lv, clampTerrainTexel(origins[1] + 0, origins[1], W, 0), y, 0)).toBeCloseTo(0.75);
  });
});

// --- The setting ---

class MemoryStorage implements PrefsStorage {
  private items = new Map<string, string>();
  getItem(key: string): string | null {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string): void {
    this.items.set(key, value);
  }
}

describe("terrain setting", () => {
  test("HD by default; the URL's choice wins over the stored one until the player picks", () => {
    resetTerrainStyle();
    expect(terrainStyle()).toBe("hd");
    expect(terrainStyleFromSearch("?terrain=original")).toBe("original");
    expect(terrainStyleFromSearch("?terrain=weird")).toBeUndefined();
    resetTerrainStyle("original");
    loadTerrainStyle("hd");
    expect(terrainStyle()).toBe("original");
    const seen: string[] = [];
    const off = onTerrainStyle((s) => seen.push(s));
    setTerrainStyle("hd");
    expect(terrainStyle()).toBe("hd");
    setTerrainStyle("original");
    off();
    setTerrainStyle("hd");
    expect(seen).toEqual(["hd", "original"]);
    resetTerrainStyle();
  });

  test("kept in the prefs", () => {
    resetTerrainStyle();
    const store = new MemoryStorage();
    setTerrainStyle("original");
    savePrefs(store);
    expect(JSON.parse(store.getItem(PREFS_STORAGE_KEY)!)).toMatchObject({ version: PREFS_VERSION, terrain: "original" });
    resetTerrainStyle();
    loadPrefs(store);
    expect(storedTerrainStyle()).toBe("original");
    expect(terrainStyle()).toBe("original");
    store.setItem(PREFS_STORAGE_KEY, JSON.stringify({ version: PREFS_VERSION, terrain: "sepia" }));
    loadPrefs(store);
    expect(terrainStyle()).toBe("hd");
    resetTerrainStyle();
  });

  test("Options has a Terrain row that switches between Original and HD remaster", () => {
    expect(optionsRows([], [], []).some((r) => r.kind === "style")).toBe(false);
    const rows = optionsRows([], [], ["original", "hd"]);
    const i = rows.findIndex((r) => r.kind === "style" && r.which === "terrain");
    expect(rows[i]).toEqual({ kind: "style", which: "terrain", label: "Terrain" });
    let style = "hd";
    const menu = new SettingsMenu(rows, "sound", {
      sound: () => {},
      styles: [],
      style: () => undefined,
      setStyle: () => {},
      terrainStyles: ["original", "hd"],
      terrainStyle: () => style,
      setTerrainStyle: (s) => (style = s),
      close: () => {},
    });
    menu.cur = i;
    menu.intent("left", "keys");
    expect(style).toBe("original");
    menu.intent("right", "keys");
    expect(style).toBe("hd");
    menu.tap(i, { style: "original" });
    expect(style).toBe("original");
    expect(menu.helpText()).toMatch(/HD remaster/);
  });
});
