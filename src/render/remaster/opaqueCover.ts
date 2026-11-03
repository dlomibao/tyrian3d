// What the frame's enemy models cover the way their sprites did (D67). A ground enemy such as the
// dome works or the carapace bunker is an opaque sprite with dirt to its rectangle's edge, and the
// level puts it on the tiles of its own wreck, which the sprite hides until the enemy is killed.
// The models no longer draw the sprite's dirt (it was a floor of pixel cells), so the wreck's
// structure model (a ground structure, D34) would show round and under the machine; the renderer
// leaves out a ground structure whose whole pattern lies under opaque pixels of modelled enemies,
// as the original's sprites hid its tiles. A covered wreck tile draws without its wreck: its
// "covered" HD painting (terrainArt.ts), else its pixels with the wreck painted out (paintOutWreck).

import { decodeSprite2, type DecodedSprite } from "../../data/sprites";
import type { Sprite2Sheet } from "../../sim/draw";
import { composeSprite2x2 } from "../spriteMesh";

interface Cover {
  x: number;
  y: number;
  sprite: DecodedSprite;
}

/** Sample spacing and edge inset of the coverage test, in screen px. */
const STEP = 4;
const INSET = 3;

export class OpaqueCover {
  private readonly covers: Cover[] = [];
  private readonly sprites = new Map<string, DecodedSprite>();

  /** Start a frame: nothing covered. */
  begin(): void {
    this.covers.length = 0;
  }

  /** A sprite drawn as a model this frame, top-left at screen (x, y). */
  add(sheet: Sprite2Sheet, index: number, size: 1 | 2, x: number, y: number): void {
    const key = `${sheet.id}|${index}|${size}`;
    let sprite = this.sprites.get(key);
    if (!sprite) {
      sprite = size === 2 ? composeSprite2x2(sheet.data, index) : decodeSprite2(sheet.data, index);
      this.sprites.set(key, sprite);
    }
    if (sprite.height > 0) this.covers.push({ x, y, sprite });
  }

  /** Whether some sprite added this frame has an opaque pixel at screen point (px, py). */
  private opaqueAt(px: number, py: number): boolean {
    for (const c of this.covers) {
      const col = Math.floor(px - c.x);
      const row = Math.floor(py - c.y);
      if (col < 0 || row < 0 || col >= c.sprite.width || row >= c.sprite.height) continue;
      if (c.sprite.pixels[row * c.sprite.width + col] >= 0) return true;
    }
    return false;
  }

  /** Whether the screen rectangle (left, top, w, h) lies under opaque sprite pixels (sampled every STEP px, INSET px in from its edges). */
  covered(left: number, top: number, w: number, h: number): boolean {
    if (this.covers.length === 0) return false;
    for (let y = top + INSET; y <= top + h - INSET; y += STEP) {
      for (let x = left + INSET; x <= left + w - INSET; x += STEP) {
        if (!this.opaqueAt(x, y)) return false;
      }
    }
    return true;
  }
}

/** TYRIAN's dirt ramp (palette indices), what its ground enemies' sprites paint round them. */
const DIRT_FIRST = 16;
const DIRT_LAST = 21;

/**
 * A ground tile with every pixel that isn't dirt replaced by the nearest dirt pixel's index (ties to
 * the first found, breadth first from the dirt), as the tile would read with its wreck dug out (D67).
 * A tile with no dirt is returned as it is.
 */
export function paintOutWreck(tile: Uint8Array, width = 24, height = 28): Uint8Array {
  const out = Uint8Array.from(tile);
  const done = new Uint8Array(width * height);
  let queue: number[] = [];
  for (let i = 0; i < width * height; i++) {
    if (tile[i] >= DIRT_FIRST && tile[i] <= DIRT_LAST) {
      done[i] = 1;
      queue.push(i);
    }
  }
  if (queue.length === 0) return out;
  while (queue.length > 0) {
    const next: number[] = [];
    for (const i of queue) {
      const x = i % width, y = (i - x) / width;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx, ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
        const j = ny * width + nx;
        if (done[j]) continue;
        done[j] = 1;
        out[j] = out[i];
        next.push(j);
      }
    }
    queue = next;
  }
  return out;
}
