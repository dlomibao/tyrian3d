// What the frame's enemy models cover the way their sprites did (D86). A ground enemy such as the
// dome works or the carapace bunker is an opaque sprite with dirt to its rectangle's edge, and the
// level puts it on the tiles of its own wreck, which the sprite hides until the enemy is killed.
// The models no longer draw the sprite's dirt (it was a floor of pixel cells), so the wreck's
// structure model (a ground structure, D34) would show round and under the machine; the renderer
// leaves out a ground structure whose pattern lies under opaque pixels of modelled ground enemies
// (not aircraft or the ship flying over it), as the original's sprites hid its tiles. A covered
// wreck tile draws without its wreck: its "covered" HD painting (terrainArt.ts), else its pixels
// with the wreck painted out (paintOutWreck).
//
// Only the part of a pattern inside the playfield has to be covered. The tiles scroll in a row ahead
// of the screen, but the sim draws an enemy's sprites only once they near it (JE_drawEnemy: a 2x2
// enemy's top half once ey > -13, its bottom half once ey > -26), so the part above the top edge
// is never under sprites even when the enemies standing on it are there. Testing it there showed
// the rock outcrop's crater for the 35 ticks it took the outcrop to scroll fully in. Outside the
// playfield nothing is seen (View masks it), so what covers it doesn't matter.

import { decodeSprite2, type DecodedSprite } from "../../data/sprites";
import { PLAYFIELD_H, PLAYFIELD_SCREEN_X, PLAYFIELD_SCREEN_Y, PLAYFIELD_W } from "../../game/playfield";
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

/** The part of the draw list's screen that is seen (the playfield, D6), as [x0, y0, x1, y1), screen px. */
export interface VisibleRect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export const PLAYFIELD_VISIBLE: VisibleRect = {
  x0: PLAYFIELD_SCREEN_X,
  y0: PLAYFIELD_SCREEN_Y,
  x1: PLAYFIELD_SCREEN_X + PLAYFIELD_W,
  y1: PLAYFIELD_SCREEN_Y + PLAYFIELD_H,
};

export class OpaqueCover {
  private readonly covers: Cover[] = [];
  private readonly sprites = new Map<string, DecodedSprite>();

  constructor(private readonly visible: VisibleRect = PLAYFIELD_VISIBLE) {}

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

  /**
   * Whether the seen part of the screen rectangle (left, top, w, h) lies under opaque sprite pixels,
   * sampled every STEP px, INSET px in from the rectangle's own edges (sprites and patterns can be
   * a pixel or two apart); a seen sliver narrower than that is sampled down its middle. A rectangle
   * wholly outside the playfield isn't covered: nothing is known about it.
   */
  covered(left: number, top: number, w: number, h: number): boolean {
    if (this.covers.length === 0) return false;
    const v = this.visible;
    if (left + w <= v.x0 || left >= v.x1 || top + h <= v.y0 || top >= v.y1) return false;
    const [x0, x1] = sampleSpan(left, w, v.x0, v.x1);
    const [y0, y1] = sampleSpan(top, h, v.y0, v.y1);
    for (let y = y0; y <= y1; y += STEP) {
      for (let x = x0; x <= x1; x += STEP) {
        if (!this.opaqueAt(x, y)) return false;
      }
    }
    return true;
  }
}

/**
 * Where to sample a span (start, length) on one axis, seen between [lo, hi): INSET in from the span's
 * ends, clipped to what is seen; if that leaves nothing, the middle of the seen part.
 */
function sampleSpan(start: number, length: number, lo: number, hi: number): [number, number] {
  const a = Math.max(start + INSET, lo), b = Math.min(start + length - INSET, hi - 1);
  if (a <= b) return [a, b];
  const mid = Math.max(lo, (Math.max(start, lo) + Math.min(start + length, hi) - 1) / 2);
  return [mid, mid];
}

/** TYRIAN's dirt ramp (palette indices), what its ground enemies' sprites paint round them. */
const DIRT_FIRST = 16;
const DIRT_LAST = 21;

/**
 * A ground tile with every pixel that isn't dirt replaced by the nearest dirt pixel's index (ties to
 * the first found, breadth first from the dirt), as the tile would read with its wreck dug out (D86).
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
