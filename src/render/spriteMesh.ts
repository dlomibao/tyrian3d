// Sprites as 3D meshes (DECISIONS.md D4): every opaque pixel becomes a column whose height rises
// with its distance from the sprite's edge, so a flat sprite turns into a rounded, solid-looking
// object with exactly the original silhouette and colours.
//
// Geometry is in Tyrian pixel units with the sprite's top-left corner at the origin: x right,
// z down the screen (toward the camera), y up. Pixel (px, py) covers x ∈ [px, px+1],
// z ∈ [py, py+1]. Vertices carry the pixel's palette index (`palIndex`), not a colour: the shader
// looks it up in the active palette (src/render/paletteTexture.ts), so one mesh serves every
// palette, filter and brightness.
//
// The surface is a height field over pixel corners (shared between neighbouring pixels, so it's
// continuous and smoothly shaded) with one flat colour per pixel quad, vertical walls down the
// silhouette, and a flat underside, which closes the mesh for shadows and the outline effect.

import * as THREE from "three";
import { decodeSprite2, decodeTableSprite, type DecodedSprite } from "../data/sprites";
import type { Sprite2Sheet, SpriteTable } from "../sim/draw";

export interface ExtrudeOptions {
  /** Height of the thickest part above the centre plane, in px. */
  maxHeight: number;
  /** Height at the silhouette edge, in px. */
  edgeHeight: number;
  /** Distance from the edge over which the rounded profile rises to maxHeight, in px. */
  radius: number;
  /** Depth of the flat underside below the centre plane, in px. */
  bottom: number;
  /**
   * Treat everything outside the sprite's bounds as opaque when measuring distance to the edge.
   * For background tiles, whose shapes continue into the neighbouring tile.
   */
  openBorders?: boolean;
}

/** Ships, enemies, shots: rounded and chunky enough to read as solid from the tilted camera. */
export const SPRITE_EXTRUDE: ExtrudeOptions = { maxHeight: 6, edgeHeight: 1.5, radius: 4, bottom: 1 };
/** Background layers 2 and 3: a low bevelled slab, continuous across tile borders. */
export const TILE_EXTRUDE: ExtrudeOptions = { maxHeight: 4, edgeHeight: 1.5, radius: 3, bottom: 0.5, openBorders: true };

export interface SpriteMeshData {
  positions: Float32Array;
  normals: Float32Array;
  /** Palette index per vertex. */
  palIndex: Float32Array;
  indices: Uint16Array | Uint32Array;
  /** Height of each pixel's column (0 where transparent), for tests and tuning. */
  heights: Float32Array;
  width: number;
  height: number;
}

/** Distance from each opaque pixel's centre to the nearest transparent pixel's centre (0 if transparent). */
export function edgeDistances(sprite: DecodedSprite, openBorders = false): Float32Array {
  const { width: w, height: h, pixels } = sprite;
  const out = new Float32Array(w * h);
  const holes: number[] = [];
  for (let i = 0; i < w * h; i++) if (pixels[i] < 0) holes.push(i % w, Math.floor(i / w));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (pixels[y * w + x] < 0) continue;
      // The pixels just outside the bounds count as transparent unless the borders are open.
      let best = openBorders ? Infinity : Math.min(x + 1, w - x, y + 1, h - y);
      let best2 = best * best;
      for (let k = 0; k < holes.length; k += 2) {
        const dx = holes[k] - x;
        const dy = holes[k + 1] - y;
        const d2 = dx * dx + dy * dy;
        if (d2 < best2) best2 = d2;
      }
      best = Math.sqrt(best2);
      out[y * w + x] = best;
    }
  }
  return out;
}

/** Column height for a pixel `d` px from the edge: a quarter-circle rising from edge to max. */
export function profileHeight(d: number, opts: ExtrudeOptions): number {
  if (!(d > 0)) return 0;
  const t = Math.min(1, (d - 1) / opts.radius);
  return opts.edgeHeight + (opts.maxHeight - opts.edgeHeight) * Math.sqrt(1 - (1 - t) * (1 - t));
}

/** Build the extruded mesh of a decoded sprite. Returns null if it has no opaque pixels. */
export function extrudeSprite(sprite: DecodedSprite, opts: ExtrudeOptions): SpriteMeshData | null {
  const { width: w, height: h, pixels } = sprite;
  const opaque = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h && pixels[y * w + x] >= 0;

  const dist = edgeDistances(sprite, opts.openBorders);
  const heights = new Float32Array(w * h);
  let count = 0;
  for (let i = 0; i < w * h; i++) {
    if (pixels[i] >= 0) {
      heights[i] = profileHeight(dist[i], opts);
      count++;
    }
  }
  if (count === 0) return null;

  // Corner heights: the mean of the opaque pixels sharing the corner (NaN where there are none).
  const cw = w + 1;
  const corner = new Float32Array(cw * (h + 1));
  for (let cy = 0; cy <= h; cy++) {
    for (let cx = 0; cx <= w; cx++) {
      let sum = 0;
      let n = 0;
      for (let dy = -1; dy <= 0; dy++) {
        for (let dx = -1; dx <= 0; dx++) {
          if (opaque(cx + dx, cy + dy)) {
            sum += heights[(cy + dy) * w + cx + dx];
            n++;
          }
        }
      }
      corner[cy * cw + cx] = n ? sum / n : NaN;
    }
  }
  const H = (cx: number, cy: number) => corner[cy * cw + cx];
  // Smooth normals from the corner height field's gradient.
  const cornerNormal = (cx: number, cy: number, out: number[]) => {
    const c = H(cx, cy);
    const at = (x: number, y: number) => {
      if (x < 0 || y < 0 || x > w || y > h) return c;
      const v = H(x, y);
      return Number.isNaN(v) ? c : v;
    };
    const gx = (at(cx + 1, cy) - at(cx - 1, cy)) / 2;
    const gz = (at(cx, cy + 1) - at(cx, cy - 1)) / 2;
    const len = Math.hypot(gx, 1, gz);
    out[0] = -gx / len;
    out[1] = 1 / len;
    out[2] = -gz / len;
  };

  const pos: number[] = [];
  const nor: number[] = [];
  const pal: number[] = [];
  const idx: number[] = [];
  const nrm = [0, 0, 0];
  const vertex = (x: number, y: number, z: number, nx: number, ny: number, nz: number, color: number) => {
    pos.push(x, y, z);
    nor.push(nx, ny, nz);
    pal.push(color);
  };
  /** Two triangles over vertices v..v+3 (a quad in order around its edge), facing `facing`. */
  const quad = (v: number, facing: [number, number, number]) => {
    // Pick the winding whose geometric normal agrees with the intended facing.
    const ax = pos[(v + 1) * 3] - pos[v * 3], ay = pos[(v + 1) * 3 + 1] - pos[v * 3 + 1], az = pos[(v + 1) * 3 + 2] - pos[v * 3 + 2];
    const bx = pos[(v + 2) * 3] - pos[v * 3], by = pos[(v + 2) * 3 + 1] - pos[v * 3 + 1], bz = pos[(v + 2) * 3 + 2] - pos[v * 3 + 2];
    const dot = (ay * bz - az * by) * facing[0] + (az * bx - ax * bz) * facing[1] + (ax * by - ay * bx) * facing[2];
    if (dot >= 0) idx.push(v, v + 1, v + 2, v, v + 2, v + 3);
    else idx.push(v, v + 2, v + 1, v, v + 3, v + 2);
  };
  const b = -opts.bottom;
  const UP: [number, number, number] = [0, 1, 0];
  const DOWN: [number, number, number] = [0, -1, 0];

  for (let y = 0; y < h; y++) {
    let runStart = -1;
    for (let x = 0; x <= w; x++) {
      const isOpaque = x < w && opaque(x, y);
      // Underside: one quad per horizontal run of opaque pixels.
      if (isOpaque && runStart < 0) runStart = x;
      if (!isOpaque && runStart >= 0) {
        const v = pos.length / 3;
        const c = pixels[y * w + runStart];
        vertex(runStart, b, y, 0, -1, 0, c);
        vertex(x, b, y, 0, -1, 0, c);
        vertex(x, b, y + 1, 0, -1, 0, c);
        vertex(runStart, b, y + 1, 0, -1, 0, c);
        quad(v, DOWN);
        runStart = -1;
      }
      if (!isOpaque) continue;

      const c = pixels[y * w + x];
      // Top: corners (x,y) (x+1,y) (x+1,y+1) (x,y+1).
      let v = pos.length / 3;
      cornerNormal(x, y, nrm);
      vertex(x, H(x, y), y, nrm[0], nrm[1], nrm[2], c);
      cornerNormal(x + 1, y, nrm);
      vertex(x + 1, H(x + 1, y), y, nrm[0], nrm[1], nrm[2], c);
      cornerNormal(x + 1, y + 1, nrm);
      vertex(x + 1, H(x + 1, y + 1), y + 1, nrm[0], nrm[1], nrm[2], c);
      cornerNormal(x, y + 1, nrm);
      vertex(x, H(x, y + 1), y + 1, nrm[0], nrm[1], nrm[2], c);
      quad(v, UP);

      // Walls where the neighbour is transparent or outside the sprite.
      const walls: [number, number, number, number, number, number][] = [];
      if (!opaque(x - 1, y)) walls.push([x, y, x, y + 1, -1, 0]);
      if (!opaque(x + 1, y)) walls.push([x + 1, y, x + 1, y + 1, 1, 0]);
      if (!opaque(x, y - 1)) walls.push([x, y, x + 1, y, 0, -1]);
      if (!opaque(x, y + 1)) walls.push([x, y + 1, x + 1, y + 1, 0, 1]);
      for (const [x0, z0, x1, z1, nx, nz] of walls) {
        v = pos.length / 3;
        vertex(x0, b, z0, nx, 0, nz, c);
        vertex(x1, b, z1, nx, 0, nz, c);
        vertex(x1, H(x1, z1), z1, nx, 0, nz, c);
        vertex(x0, H(x0, z0), z0, nx, 0, nz, c);
        quad(v, [nx, 0, nz]);
      }
    }
  }

  const vertexCount = pos.length / 3;
  return {
    positions: new Float32Array(pos),
    normals: new Float32Array(nor),
    palIndex: new Float32Array(pal),
    indices: vertexCount > 0xffff ? new Uint32Array(idx) : new Uint16Array(idx),
    heights,
    width: w,
    height: h,
  };
}

/** A BufferGeometry from mesh data, with `palIndex` as a vertex attribute. */
export function toGeometry(data: SpriteMeshData): THREE.BufferGeometry {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(data.positions, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(data.normals, 3));
  g.setAttribute("palIndex", new THREE.BufferAttribute(data.palIndex, 1));
  g.setIndex(new THREE.BufferAttribute(data.indices, 1));
  g.computeBoundingSphere();
  return g;
}

/**
 * The pixels blit_sprite2x2 draws: sprites index, index+1, index+19 and index+20 at offsets
 * (0,0), (12,0), (0,14), (12,14), later ones over earlier ones, as one 24-wide sprite.
 */
export function composeSprite2x2(sheet: Uint8Array, index: number): DecodedSprite {
  const parts = [
    { s: decodeSprite2(sheet, index), x: 0, y: 0 },
    { s: decodeSprite2(sheet, index + 1), x: 12, y: 0 },
    { s: decodeSprite2(sheet, index + 19), x: 0, y: 14 },
    { s: decodeSprite2(sheet, index + 20), x: 12, y: 14 },
  ];
  const width = 24;
  const height = Math.max(28, ...parts.map((p) => p.y + p.s.height));
  const pixels = new Int16Array(width * height).fill(-1);
  for (const { s, x, y } of parts) {
    for (let r = 0; r < s.height; r++) {
      for (let c = 0; c < s.width; c++) {
        const v = s.pixels[r * s.width + c];
        if (v >= 0) pixels[(y + r) * width + x + c] = v;
      }
    }
  }
  return { width, height, pixels };
}

/** A background tile (24x28 palette indices) as a sprite; index 0 is transparent unless `opaque`. */
export function tileToSprite(tile: Uint8Array, opaque: boolean, width = 24, height = 28): DecodedSprite {
  const pixels = new Int16Array(width * height);
  for (let i = 0; i < width * height; i++) pixels[i] = !opaque && tile[i] === 0 ? -1 : tile[i];
  return { width, height, pixels };
}

/**
 * Generated geometry, built once per sprite and kept. Keys follow `${sheet.id}:${index}:${size}`;
 * lookups go through object-keyed maps first so the per-frame path never builds strings.
 */
export class SpriteMeshCache {
  private readonly byKey = new Map<string, THREE.BufferGeometry | null>();
  private readonly sprite2 = new WeakMap<Sprite2Sheet, Map<number, THREE.BufferGeometry | null>>();
  private readonly table = new WeakMap<SpriteTable, Map<number, THREE.BufferGeometry | null>>();
  private readonly tiles = new Map<string, THREE.BufferGeometry | null>();

  /** Geometry for a Sprite2 draw (size 1 or the 2x2 composite), or null if it's empty. */
  sprite2Geometry(sheet: Sprite2Sheet, index: number, size: 1 | 2): THREE.BufferGeometry | null {
    let m = this.sprite2.get(sheet);
    if (!m) this.sprite2.set(sheet, (m = new Map()));
    const k = index * 2 + size - 1;
    let g = m.get(k);
    if (g === undefined) {
      const key = `${sheet.id}:${index}:${size}`;
      g = this.byKey.get(key);
      if (g === undefined) {
        const decoded = size === 2 ? composeSprite2x2(sheet.data, index) : decodeSprite2(sheet.data, index);
        const data = extrudeSprite(decoded, SPRITE_EXTRUDE);
        g = data ? toGeometry(data) : null;
        this.byKey.set(key, g);
      }
      m.set(k, g);
    }
    return g;
  }

  /** Geometry for a sprite-table draw, or null if it's empty or missing. */
  tableGeometry(table: SpriteTable, index: number): THREE.BufferGeometry | null {
    let m = this.table.get(table);
    if (!m) this.table.set(table, (m = new Map()));
    let g = m.get(index);
    if (g === undefined) {
      const key = `${table.id}:${index}:t`;
      g = this.byKey.get(key);
      if (g === undefined) {
        const sprite = table.sprites[index];
        const data = sprite ? extrudeSprite(decodeTableSprite(sprite), SPRITE_EXTRUDE) : null;
        g = data ? toGeometry(data) : null;
        this.byKey.set(key, g);
      }
      m.set(index, g);
    }
    return g;
  }

  /** Extruded geometry for a transparent background tile (layers 1 and 2). */
  tileGeometry(tileId: string, tile: Uint8Array): THREE.BufferGeometry | null {
    let g = this.tiles.get(tileId);
    if (g === undefined) {
      const data = extrudeSprite(tileToSprite(tile, false), TILE_EXTRUDE);
      g = data ? toGeometry(data) : null;
      this.tiles.set(tileId, g);
    }
    return g;
  }

  get size(): number {
    return this.byKey.size + this.tiles.size;
  }
}
