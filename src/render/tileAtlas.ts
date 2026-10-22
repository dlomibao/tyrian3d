// Background-1 (ground) tiles packed into one palette-index texture, so the whole ground is a
// single instanced draw: each instance picks its tile with an atlas offset. Indices (not colours)
// are stored, and looked up in the palette texture in the shader, like the sprite meshes.

import * as THREE from "three";
import { TILE_HEIGHT, TILE_WIDTH } from "../data/levels";

const ATLAS_SIZE = 1024;
const COLS = Math.floor(ATLAS_SIZE / TILE_WIDTH);
const ROWS = Math.floor(ATLAS_SIZE / TILE_HEIGHT);

export class TileAtlas {
  readonly texture: THREE.DataTexture;
  /** One tile's size in UV units. */
  readonly tileUv = new THREE.Vector2(TILE_WIDTH / ATLAS_SIZE, TILE_HEIGHT / ATLAS_SIZE);
  private readonly data = new Uint8Array(ATLAS_SIZE * ATLAS_SIZE);
  private readonly slots = new Map<string, number>();
  private dirty = false;

  constructor() {
    this.texture = new THREE.DataTexture(this.data, ATLAS_SIZE, ATLAS_SIZE, THREE.RedFormat, THREE.UnsignedByteType);
    this.texture.magFilter = this.texture.minFilter = THREE.NearestFilter;
    this.texture.generateMipmaps = false;
    this.texture.unpackAlignment = 1;
    this.texture.needsUpdate = true;
  }

  /**
   * The atlas slot of a tile, adding it if new. Writes the UV offset of the slot's top-left
   * corner into out[o], out[o + 1].
   */
  place(tileId: string, tile: Uint8Array, out: Float32Array, o: number): void {
    let slot = this.slots.get(tileId);
    if (slot === undefined) {
      if (this.slots.size >= COLS * ROWS) this.slots.clear(); // Full: start over (tiles re-add on use).
      slot = this.slots.size;
      this.slots.set(tileId, slot);
      const sx = (slot % COLS) * TILE_WIDTH;
      const sy = Math.floor(slot / COLS) * TILE_HEIGHT;
      for (let r = 0; r < TILE_HEIGHT; r++) {
        this.data.set(tile.subarray(r * TILE_WIDTH, (r + 1) * TILE_WIDTH), (sy + r) * ATLAS_SIZE + sx);
      }
      this.dirty = true;
    }
    out[o] = ((slot % COLS) * TILE_WIDTH) / ATLAS_SIZE;
    out[o + 1] = (Math.floor(slot / COLS) * TILE_HEIGHT) / ATLAS_SIZE;
  }

  /** Upload new tiles, once per frame at most. */
  flush(): void {
    if (this.dirty) {
      this.texture.needsUpdate = true;
      this.dirty = false;
    }
  }

  get size(): number {
    return this.slots.size;
  }
}
