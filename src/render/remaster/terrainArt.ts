// HD terrain: painted replacements for the background tiles (DECISIONS.md D57), drawn in the
// remastered look where they exist and the setting asks for them (core/terrainStyle.ts). This is
// the pure part (manifest parsing, per-tile lookup with neighbour variants, the seam-free texel
// maths the shader uses); terrainMaterial.ts draws, terrainLoader.ts fetches.
//
// public/art/terrain/<tileset>/manifest.json, per tileset (the shapes file without ".dat"):
//
//   { "version": 1, "scale": 8,
//     "layers": { "0": { "image": "0.webp",
//                        "tiles": { "123": { "x": 16, "y": 16, "w": 192, "h": 224 } },
//                        "variants": { "123": [ { "n": { "right": 124 }, "x": 240, "y": 16, "w": 192, "h": 224 } ] },
//                        "covered": { "330": { "x": 464, "y": 16, "w": 192, "h": 224 } } } } }
//
// "covered" (optional, D86): the tile as it looks under an opaque enemy sprite that hides it, e.g. a
// bunker's wreck painted out to plain dirt while the live bunker stands on it.
//
// Layers are the draw list's: 0 background 1 (ground), 1 background 2 (TYRIAN's clouds), 2
// background 3 (islands, fortresses). A tile key is its 0-based record in shapes?.dat (the number
// after ":" in TileDraw.tileId). Every rect is the tile's 24x28 px times `scale`, at a multiple of
// 16 texels, with at least 16 texels of edge-extended gutter around it, so mip levels 0..MAX_LOD
// never average two tiles together. A tile that isn't listed (or a rect of the wrong size, or one
// outside the image) draws as before: the 4x MMPX ground, and the original tile if that can't.

import { TILE_HEIGHT, TILE_WIDTH } from "../../data/levels";

/** Mip levels the sampler may use: rects are 16-aligned, so levels 0..4 keep tiles apart. */
export const TERRAIN_MAX_LOD = 4;
/** Rect alignment (and minimum gutter) in texels that keeps mip levels 0..TERRAIN_MAX_LOD apart. */
export const TERRAIN_ALIGN = 1 << TERRAIN_MAX_LOD;

/** Where the manifests live, under the site root: <dir><tileset>/manifest.json. */
export const TERRAIN_ART_DIR = "art/terrain/";

export type TerrainLayer = 0 | 1 | 2;
export type Side = "left" | "right" | "up" | "down";
export const SIDES: readonly Side[] = ["left", "right", "up", "down"];

export interface TerrainRect {
  x: number;
  y: number;
  w: number;
  h: number;
  /** An atlas of its own (relative to the manifest) instead of the layer's. */
  image?: string;
}

export interface TerrainVariant extends TerrainRect {
  /** Neighbours on the same layer this variant is for: a tile number, or -1 for none/empty. */
  n: Partial<Record<Side, number>>;
}

export interface TerrainLayerArt {
  image: string;
  tiles: Map<number, TerrainRect>;
  variants: Map<number, TerrainVariant[]>;
  /** The tile painted as it looks while an enemy covers it (D86). */
  covered: Map<number, TerrainRect>;
}

export interface TerrainManifest {
  scale: number;
  layers: Map<TerrainLayer, TerrainLayerArt>;
}

const isCount = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v) && v >= 0;

function parseRect(v: unknown, scale: number, where: string, warn: (msg: string) => void): TerrainRect | null {
  const { x, y, w, h, image } = (v ?? {}) as Record<string, unknown>;
  if (!isCount(x) || !isCount(y) || !isCount(w) || !isCount(h)) {
    warn(`terrain art: ${where} is malformed; skipped`);
    return null;
  }
  if (w !== TILE_WIDTH * scale || h !== TILE_HEIGHT * scale) {
    warn(`terrain art: ${where} is ${w}x${h}, not ${TILE_WIDTH * scale}x${TILE_HEIGHT * scale}; skipped`);
    return null;
  }
  if (x % TERRAIN_ALIGN !== 0 || y % TERRAIN_ALIGN !== 0) {
    // Still drawn: only the coarsest mips may then blend in a neighbour's edge.
    warn(`terrain art: ${where} isn't at a multiple of ${TERRAIN_ALIGN} texels; its far mips may bleed`);
  }
  const r: TerrainRect = { x, y, w, h };
  if (typeof image === "string" && image !== "") r.image = image;
  return r;
}

/**
 * Check and index a manifest. Returns null if it isn't one (the tileset draws as before); layers,
 * tiles and variants that are malformed are dropped with a warning, the rest kept.
 */
export function parseTerrainManifest(json: unknown, warn: (msg: string) => void = console.warn): TerrainManifest | null {
  if (typeof json !== "object" || json === null) return null;
  const { scale, layers } = json as { scale?: unknown; layers?: unknown };
  if (!isCount(scale) || scale <= 0 || typeof layers !== "object" || layers === null) return null;
  const out: TerrainManifest = { scale, layers: new Map() };
  for (const [key, layer] of Object.entries(layers as Record<string, unknown>)) {
    if (key !== "0" && key !== "1" && key !== "2") {
      warn(`terrain art: layer ${key} isn't 0, 1 or 2; skipped`);
      continue;
    }
    const { image, tiles, variants, covered } = (layer ?? {}) as { image?: unknown; tiles?: unknown; variants?: unknown; covered?: unknown };
    if (typeof image !== "string" || image === "" || typeof tiles !== "object" || tiles === null) {
      warn(`terrain art: layer ${key} has no image or tiles; skipped`);
      continue;
    }
    const art: TerrainLayerArt = { image, tiles: new Map(), variants: new Map(), covered: new Map() };
    for (const [t, rect] of Object.entries(tiles as Record<string, unknown>)) {
      const n = Number(t);
      if (!Number.isInteger(n) || n < 0) {
        warn(`terrain art: layer ${key} tile "${t}" isn't a tile number; skipped`);
        continue;
      }
      const r = parseRect(rect, scale, `layer ${key} tile ${t}`, warn);
      if (r) art.tiles.set(n, r);
    }
    if (typeof variants === "object" && variants !== null) {
      for (const [t, list] of Object.entries(variants as Record<string, unknown>)) {
        const n = Number(t);
        if (!Number.isInteger(n) || n < 0 || !Array.isArray(list)) {
          warn(`terrain art: layer ${key} variants of "${t}" are malformed; skipped`);
          continue;
        }
        const kept: TerrainVariant[] = [];
        list.forEach((v, i) => {
          const r = parseRect(v, scale, `layer ${key} tile ${t} variant ${i}`, warn);
          const need = (v as { n?: unknown })?.n;
          if (!r) return;
          if (typeof need !== "object" || need === null) return warn(`terrain art: layer ${key} tile ${t} variant ${i} has no "n"; skipped`);
          const sides: Partial<Record<Side, number>> = {};
          for (const [side, tile] of Object.entries(need as Record<string, unknown>)) {
            if (!SIDES.includes(side as Side) || !Number.isInteger(tile) || (tile as number) < -1) return warn(`terrain art: layer ${key} tile ${t} variant ${i}: bad neighbour ${side}; skipped`);
            sides[side as Side] = tile as number;
          }
          kept.push({ ...r, n: sides });
        });
        if (kept.length > 0) art.variants.set(n, kept);
      }
    }
    if (typeof covered === "object" && covered !== null) {
      for (const [t, rect] of Object.entries(covered as Record<string, unknown>)) {
        const n = Number(t);
        if (!Number.isInteger(n) || n < 0) {
          warn(`terrain art: layer ${key} covered tile "${t}" isn't a tile number; skipped`);
          continue;
        }
        const r = parseRect(rect, scale, `layer ${key} covered tile ${t}`, warn);
        if (r) art.covered.set(n, r);
      }
    }
    if (art.tiles.size > 0 || art.variants.size > 0) out.layers.set(Number(key) as TerrainLayer, art);
  }
  return out;
}

/** "shapesz.dat:123" → ["shapesz", 123]; null if the id isn't a tileset tile. */
export function parseTileId(tileId: string): [tileset: string, tile: number] | null {
  const colon = tileId.lastIndexOf(":");
  if (colon <= 0) return null;
  const tile = Number(tileId.slice(colon + 1));
  if (!Number.isInteger(tile) || tile < 0) return null;
  return [tileId.slice(0, colon).replace(/\.dat$/i, "").toLowerCase(), tile];
}

/** A tile ready to draw: its atlas texture and the rect's origin in texels. */
export interface ReadyTerrainTile<T = unknown> {
  texture: T;
  /** Top-left of the tile's art in atlas texels (top-left origin). */
  x: number;
  y: number;
}

/**
 * A level map of one layer, as tile numbers (-1: no tile), for choosing neighbour variants. The map
 * index is the draw key's (TileDraw.key - layer * BG_KEY_LAYER).
 */
export interface TerrainMap {
  width: number;
  tiles: ArrayLike<number>;
}

/** The neighbour of map cell `index` on `side`, or -1 outside the map or where there's no tile. */
export function neighbourTile(map: TerrainMap, index: number, side: Side): number {
  const { width, tiles } = map;
  const col = index % width;
  let j: number;
  switch (side) {
    case "left":
      if (col === 0) return -1;
      j = index - 1;
      break;
    case "right":
      if (col === width - 1) return -1;
      j = index + 1;
      break;
    case "up":
      j = index - width;
      break;
    case "down":
      j = index + width;
      break;
  }
  return j < 0 || j >= tiles.length ? -1 : tiles[j];
}

/**
 * One tileset's art: per layer, the rects and their atlases. `T` is the drawing side's texture
 * (THREE.Texture); a rect draws once its atlas has loaded and only if it lies inside the image.
 */
export class TerrainTileset<T = unknown> {
  /** Atlas image names (relative to the manifest) → texture and size, once loaded; null: failed. */
  readonly images = new Map<string, { texture: T; width: number; height: number } | null>();
  private readonly maps: (TerrainMap | undefined)[] = [];
  /** Resolved tile per layer and map index (variants depend on the map, so cached per cell). */
  private readonly cellCache: Map<number, { tile: number; ready: ReadyTerrainTile<T> | undefined }>[] = [new Map(), new Map(), new Map()];

  constructor(
    readonly name: string,
    readonly manifest: TerrainManifest,
  ) {
    for (const art of manifest.layers.values()) {
      this.images.set(art.image, null);
      for (const r of art.tiles.values()) if (r.image) this.images.set(r.image, null);
      for (const list of art.variants.values()) for (const r of list) if (r.image) this.images.set(r.image, null);
      for (const r of art.covered.values()) if (r.image) this.images.set(r.image, null);
    }
  }

  get scale(): number {
    return this.manifest.scale;
  }

  /** An atlas has loaded (or failed: null). */
  setImage(image: string, loaded: { texture: T; width: number; height: number } | null): void {
    this.images.set(image, loaded);
    for (const c of this.cellCache) c.clear();
  }

  /** The level's map for `layer`, so cells can pick neighbour variants (none: the plain tiles). */
  setMap(layer: TerrainLayer, map: TerrainMap | undefined): void {
    this.maps[layer] = map;
    this.cellCache[layer].clear();
  }

  /** Whether the manifest lists `tile` on `layer` (loaded or not). */
  listed(layer: TerrainLayer, tile: number): boolean {
    const art = this.manifest.layers.get(layer);
    return !!art && (art.tiles.has(tile) || art.variants.has(tile));
  }

  /**
   * The art for `tile` at map cell `index` of `layer`: the first variant whose neighbours all match
   * the map, else the plain tile; undefined if neither exists, its atlas hasn't loaded (or failed),
   * or its rect lies outside the image. Then the tile draws as before.
   */
  tile(layer: TerrainLayer, tile: number, index: number): ReadyTerrainTile<T> | undefined {
    const cache = this.cellCache[layer];
    const hit = cache.get(index);
    // Kept per cell while the same tile is there (the debug harnesses can put another under a key).
    if (hit && hit.tile === tile) return hit.ready;
    const ready = this.resolve(layer, tile, index);
    cache.set(index, { tile, ready });
    return ready;
  }

  /** The art for `tile` on `layer` while an enemy sprite covers it (D86), if it has any and it's ready. */
  coveredTile(layer: TerrainLayer, tile: number): ReadyTerrainTile<T> | undefined {
    const art = this.manifest.layers.get(layer);
    const r = art?.covered.get(tile);
    return art && r ? this.ready(art, r) : undefined;
  }

  private resolve(layer: TerrainLayer, tile: number, index: number): ReadyTerrainTile<T> | undefined {
    const art = this.manifest.layers.get(layer);
    if (!art) return undefined;
    const map = this.maps[layer];
    const variants = art.variants.get(tile);
    if (variants && map) {
      for (const v of variants) {
        if (SIDES.every((s) => v.n[s] === undefined || v.n[s] === neighbourTile(map, index, s))) {
          const ready = this.ready(art, v);
          if (ready) return ready;
        }
      }
    }
    const plain = art.tiles.get(tile);
    return plain ? this.ready(art, plain) : undefined;
  }

  private ready(art: TerrainLayerArt, r: TerrainRect): ReadyTerrainTile<T> | undefined {
    const img = this.images.get(r.image ?? art.image);
    if (!img || r.x + r.w > img.width || r.y + r.h > img.height) return undefined;
    return { texture: img.texture, x: r.x, y: r.y };
  }
}

/**
 * Where the sampler reads for a point of a tile (what terrainMaterial.ts's shader does, here for
 * tests): `t` is the position in atlas texels (texel i spans [i, i + 1)), `origin` the rect's
 * top-left and `size` its size, `lod` the mip level (fractional: trilinear). Clamped half a texel
 * of the coarser of the two levels blended inside the rect, so a bilinear tap at either level
 * reads only this tile's texels: the tile's edge texel is what shows right at the cell's edge, and
 * the neighbouring cell shows its own; nothing comes from the gutter or another tile.
 */
export function clampTerrainTexel(t: number, origin: number, size: number, lod: number): number {
  const l = Math.min(Math.max(lod, 0), TERRAIN_MAX_LOD);
  const margin = 0.5 * 2 ** Math.ceil(l);
  return Math.min(Math.max(t, origin + margin), origin + size - margin);
}

/** The mip level the GPU would pick for a texel-space footprint (as the shader computes it). */
export function terrainLod(texelsPerPixel: number): number {
  return Math.min(Math.max(Math.log2(Math.max(texelsPerPixel, 1e-6)), 0), TERRAIN_MAX_LOD);
}
