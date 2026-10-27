// The remastered ground (background 1): every tile upscaled 4x with MMPX (mmpx.ts) into a
// palette-index atlas, so the ground keeps the palette pipeline (D7) at four times the detail
// (DECISIONS.md D34).
//
// Seamless across tile edges: a tile is upscaled together with the edges of its eight neighbours as
// they are in the map this tick (from the draw list), and only its own part is kept. So a cell
// comes out exactly as if the whole map had been upscaled at once. Each slot also keeps a one-texel
// border from its neighbours, so the shader's bilinear filter and relief read across the seam too.
// Slots are keyed by the 3x3 context of tile ids; a level has one to two thousand of them, but only
// about a hundred are on screen at a time, so slots are reused least recently used first.

import * as THREE from "three";
import { TILE_HEIGHT, TILE_WIDTH } from "../../data/levels";
import type { Draw, TileDraw } from "../../sim/draw";
import { mmpx2x } from "./mmpx";

/** Upscale factor (two MMPX passes). */
export const GROUND_SCALE = 4;
/** One texel of neighbour border around each slot. */
const BORDER = 1;
const SLOT_W = TILE_WIDTH * GROUND_SCALE + 2 * BORDER;
const SLOT_H = TILE_HEIGHT * GROUND_SCALE + 2 * BORDER;
const ATLAS_SIZE = 2048;
const COLS = Math.floor(ATLAS_SIZE / SLOT_W);
const ROWS = Math.floor(ATLAS_SIZE / SLOT_H);
export const GROUND_SLOTS = COLS * ROWS;
/**
 * Source pixels of neighbour context around a tile. MMPX reads up to 3 pixels away, so two passes
 * spoil at most 18 texels at 4x in from a clamped edge; 6 source pixels (24 texels) keep the
 * cropped tile and its border clear of that.
 */
const PAD = 6;
/** Background 1's map width (JE_MapType): a cell's vertical neighbours are this many keys away. */
const MAP_WIDTH = 14;

/**
 * Upscale `center` 4x with its neighbours' pixels around it (`neighbours[dy + 1][dx + 1]`, null where
 * unknown: the centre's own edge is repeated there). Returns SLOT_W x SLOT_H indices: the tile and a
 * one-texel border.
 */
export function upscaleInContext(neighbours: (Uint8Array | null)[][], luma: ArrayLike<number>): Uint8Array {
  const center = neighbours[1][1]!;
  const w = TILE_WIDTH + 2 * PAD;
  const h = TILE_HEIGHT + 2 * PAD;
  const src = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) {
    const ty = y - PAD;
    const cy = ty < 0 ? 0 : ty >= TILE_HEIGHT ? 2 : 1;
    for (let x = 0; x < w; x++) {
      const tx = x - PAD;
      const cx = tx < 0 ? 0 : tx >= TILE_WIDTH ? 2 : 1;
      const n = neighbours[cy][cx];
      if (n) src[y * w + x] = n[(ty - (cy - 1) * TILE_HEIGHT) * TILE_WIDTH + (tx - (cx - 1) * TILE_WIDTH)];
      else src[y * w + x] = center[clamp(ty, TILE_HEIGHT) * TILE_WIDTH + clamp(tx, TILE_WIDTH)];
    }
  }
  // Only what's kept is computed: the slot (the tile and a texel of border) from the second pass,
  // and from the first pass what the second reads for it (MMPX reads 3 pixels around).
  const first = { x: PAD - 2, y: PAD - 2, w: TILE_WIDTH + 4, h: TILE_HEIGHT + 4 };
  const half = mmpx2x(src, w, h, luma, "clamp", first);
  const hw = first.w * 2, hh = first.h * 2;
  // In the first pass's output the tile starts at 4 px; the slot starts a texel before it in 4x.
  const second = { x: 3, y: 3, w: TILE_WIDTH * 2 + 2, h: TILE_HEIGHT * 2 + 2 };
  const up = mmpx2x(half, hw, hh, luma, "clamp", second);
  const uw = second.w * 2;
  const out = new Uint8Array(SLOT_W * SLOT_H);
  const o = 2 - BORDER; // the tile starts 2 texels into `up`
  for (let y = 0; y < SLOT_H; y++) out.set(up.subarray((o + y) * uw + o, (o + y) * uw + o + SLOT_W), y * SLOT_W);
  return out;
}

const clamp = (v: number, n: number) => (v < 0 ? 0 : v >= n ? n - 1 : v);

interface Slot {
  index: number;
  lastUsed: number;
}

export class RemasterGroundAtlas {
  readonly texture: THREE.DataTexture;
  /** A tile's size (without border) in UV units. */
  readonly tileUv = new THREE.Vector2((TILE_WIDTH * GROUND_SCALE) / ATLAS_SIZE, (TILE_HEIGHT * GROUND_SCALE) / ATLAS_SIZE);
  private readonly data = new Uint8Array(ATLAS_SIZE * ATLAS_SIZE);
  private readonly slots = new Map<string, Slot>();
  private readonly byIndex: (string | undefined)[] = [];
  /** This tick's cell (draw key) to slot index. */
  private readonly cells = new Map<number, number>();
  private luma: ArrayLike<number> | null = null;
  private tick = 0;
  private dirty = false;
  /** Tiles upscaled so far, for stats. */
  upscaled = 0;

  constructor() {
    this.texture = new THREE.DataTexture(this.data, ATLAS_SIZE, ATLAS_SIZE, THREE.RedFormat, THREE.UnsignedByteType);
    this.texture.magFilter = this.texture.minFilter = THREE.NearestFilter;
    this.texture.generateMipmaps = false;
    this.texture.unpackAlignment = 1;
    this.texture.needsUpdate = true;
  }

  /**
   * The brightness of each palette index, which MMPX uses to break ties. Set from the palette the
   * level is drawn with; changing it later doesn't redo tiles already upscaled.
   */
  setLuma(luma: ArrayLike<number>): void {
    this.luma ??= luma;
  }

  /** Find or make the slot of every background-1 cell in this tick's draw list. */
  prepare(items: readonly Draw[]): void {
    this.tick++;
    this.cells.clear();
    const luma = this.luma;
    if (!luma) return;
    const byKey = new Map<number, TileDraw>();
    for (const d of items) if (d.kind === "tile" && d.layer === 0) byKey.set(d.key, d);
    if (byKey.size === 0) return;
    const ids: string[] = new Array(9);
    const neighbours: (Uint8Array | null)[][] = [[null, null, null], [null, null, null], [null, null, null]];
    for (const key of byKey.keys()) {
      const col = key % MAP_WIDTH;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const c = col + dx;
          const n = c < 0 || c >= MAP_WIDTH ? undefined : byKey.get(key + dy * MAP_WIDTH + dx);
          neighbours[dy + 1][dx + 1] = n ? n.tile : null;
          ids[(dy + 1) * 3 + dx + 1] = n ? n.tileId : "?";
        }
      }
      const signature = ids.join("|");
      let slot = this.slots.get(signature);
      if (!slot) {
        slot = this.allocate(signature);
        this.write(slot.index, upscaleInContext(neighbours, luma));
        this.upscaled++;
      }
      slot.lastUsed = this.tick;
      this.cells.set(key, slot.index);
    }
  }

  /**
   * Write the UV of a cell's tile (its top-left, inside the border) into out[o], out[o + 1].
   * Returns false if the cell has no slot (no palette yet).
   */
  place(key: number, out: Float32Array, o: number): boolean {
    const index = this.cells.get(key);
    if (index === undefined) return false;
    out[o] = ((index % COLS) * SLOT_W + BORDER) / ATLAS_SIZE;
    out[o + 1] = (Math.floor(index / COLS) * SLOT_H + BORDER) / ATLAS_SIZE;
    return true;
  }

  flush(): void {
    if (this.dirty) {
      this.texture.needsUpdate = true;
      this.dirty = false;
    }
  }

  get size(): number {
    return this.slots.size;
  }

  private allocate(signature: string): Slot {
    let index: number;
    if (this.byIndex.length < GROUND_SLOTS) {
      index = this.byIndex.length;
    } else {
      // Reuse the least recently used slot that isn't on screen this tick.
      let oldest: Slot | null = null;
      let oldestKey = "";
      for (const [k, s] of this.slots) {
        if (s.lastUsed < this.tick && (!oldest || s.lastUsed < oldest.lastUsed)) {
          oldest = s;
          oldestKey = k;
        }
      }
      if (!oldest) throw new Error("remastered ground atlas is full");
      this.slots.delete(oldestKey);
      index = oldest.index;
    }
    const slot = { index, lastUsed: this.tick };
    this.byIndex[index] = signature;
    this.slots.set(signature, slot);
    return slot;
  }

  private write(index: number, pixels: Uint8Array): void {
    const sx = (index % COLS) * SLOT_W;
    const sy = Math.floor(index / COLS) * SLOT_H;
    for (let r = 0; r < SLOT_H; r++) this.data.set(pixels.subarray(r * SLOT_W, (r + 1) * SLOT_W), (sy + r) * ATLAS_SIZE + sx);
    this.dirty = true;
  }
}
