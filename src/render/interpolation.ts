// Matches each tick's draws to the previous tick's so positions can be interpolated between them
// at display rate (DECISIONS.md D2).
//
// A draw matches the previous tick's draw of the same kind with the same `key`. When the sim
// records several draws under one key in a tick (an enemy drawn from several sprites, the ship
// and its sidekicks), they match in order of appearance: the n-th draw with key k matches the
// previous tick's n-th draw with key k. Key -1, and pixels and rectangles (which have no key),
// never interpolate. A draw that moved further than SNAP_PX in one tick teleported (a respawn,
// a wrapped background row) and snaps instead of sliding.

import type { Draw } from "../sim/draw";

/** Moves longer than this (px, either axis) in one tick snap instead of interpolating. */
export const SNAP_PX = 40;
/** Draws sharing a key beyond this many in one tick stop matching (they snap). */
const MAX_PER_KEY = 64;

const KIND_CODE = { sprite2: 1, sprite: 2, tile: 3, pixel: 0, rect: 0 } as const;

function drawX(d: Draw): number {
  return d.kind === "rect" ? d.x1 : d.x;
}
function drawY(d: Draw): number {
  return d.kind === "rect" ? d.y1 : d.y;
}
function drawKey(d: Draw): number {
  return d.kind === "pixel" || d.kind === "rect" ? -1 : d.key;
}

export class DrawInterpolator {
  /** Previous-tick position of each current draw (equal to its own position when unmatched). */
  prevX = new Float32Array(1024);
  prevY = new Float32Array(1024);
  private items: readonly Draw[] = [];
  /** (key, kind, occurrence) → index in the previous tick's items. */
  private prevIndex = new Map<number, number>();
  private nextIndex = new Map<number, number>();
  private occurrences = new Map<number, number>();

  /** Take the new tick's draws and match them against the previous tick's. */
  push(items: readonly Draw[]): void {
    const prev = this.items;
    if (this.prevX.length < items.length) {
      const n = Math.max(items.length, this.prevX.length * 2);
      this.prevX = new Float32Array(n);
      this.prevY = new Float32Array(n);
    }
    // Index the new items while matching them against the old index.
    const next = this.nextIndex;
    next.clear();
    this.occurrences.clear();
    for (let i = 0; i < items.length; i++) {
      const d = items[i];
      const x = drawX(d);
      const y = drawY(d);
      this.prevX[i] = x;
      this.prevY[i] = y;
      const key = drawKey(d);
      if (key < 0) continue;
      const combo = this.combo(key, KIND_CODE[d.kind]);
      if (combo < 0) continue;
      next.set(combo, i);
      const j = this.prevIndex.get(combo);
      if (j === undefined) continue;
      const p = prev[j];
      const px = drawX(p);
      const py = drawY(p);
      if (Math.abs(x - px) <= SNAP_PX && Math.abs(y - py) <= SNAP_PX) {
        this.prevX[i] = px;
        this.prevY[i] = py;
      }
    }
    this.nextIndex = this.prevIndex;
    this.prevIndex = next;
    this.items = items;
  }

  /** Forget the previous tick, e.g. after a level change. */
  reset(): void {
    this.items = [];
    this.prevIndex.clear();
  }

  /** Key, kind and occurrence packed into one map key; -1 past MAX_PER_KEY occurrences. */
  private combo(key: number, kind: number): number {
    const base = key * 4 + kind;
    const n = this.occurrences.get(base) ?? 0;
    this.occurrences.set(base, n + 1);
    return n < MAX_PER_KEY ? base * MAX_PER_KEY + n : -1;
  }
}

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;
