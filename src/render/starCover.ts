// Which starfield pixels the ground hides (DECISIONS.md D127).
//
// update_and_draw_starfield (src/sim/backgrnd.ts) paints a star pixel only where the screen is still
// black (palette 0) after background 1, so stars show only through the gaps in the ground. The
// draw list has no screen, so the sim records every star pixel and the renderer tests it here:
// against the background-1 tiles of the same draw list, at their tick positions (not interpolated,
// as the C tested the screen it had just drawn). Everything the C drew after the stars (background 2
// and 3, enemies, shots) is drawn higher than the stars (D5) and covers them by depth.

import { Pass, type Draw, type TileDraw } from "../sim/draw";
import { TILE_HEIGHT, TILE_WIDTH } from "../data/levels";

/** VGAScreen's size: the C's star test reads this screen. */
const SCREEN_W = 320;
const SCREEN_H = 200;

/**
 * Which screen pixels a set of tile draws paints (non-zero pixels), from a draw list's tiles at their
 * tick positions; rebuilt once per draw list (the sim starts a new array every tick).
 */
export class TileCover {
  /** 1 where a counted tile painted a non-zero pixel, per screen pixel. */
  private readonly painted = new Uint8Array(SCREEN_W * SCREEN_H);
  private items: readonly Draw[] | null = null;
  private any = false;

  constructor(private readonly counts: (d: TileDraw) => boolean) {}

  /** Whether screen pixel (x, y) (rounded) is painted by a counted tile of draw list `items`. */
  covers(items: readonly Draw[], x: number, y: number): boolean {
    if (items !== this.items) this.build(items);
    if (!this.any) return false;
    x = Math.round(x);
    y = Math.round(y);
    if (x < 0 || y < 0 || x >= SCREEN_W || y >= SCREEN_H) return false;
    return this.painted[y * SCREEN_W + x] !== 0;
  }

  private build(items: readonly Draw[]): void {
    this.items = items;
    const g = this.painted;
    if (this.any) g.fill(0);
    this.any = false;
    for (const d of items) {
      if (d.kind !== "tile" || !this.counts(d)) continue;
      this.any = true;
      const x0 = Math.round(d.x), y0 = Math.round(d.y);
      for (let ty = 0; ty < TILE_HEIGHT; ty++) {
        const y = y0 + ty;
        if (y < 0 || y >= SCREEN_H) continue;
        for (let tx = 0; tx < TILE_WIDTH; tx++) {
          const x = x0 + tx;
          if (x < 0 || x >= SCREEN_W) continue;
          if (d.tile[ty * TILE_WIDTH + tx] !== 0) g[y * SCREEN_W + x] = 1;
        }
      }
    }
  }
}

export class StarCover {
  /** Background 1's painted pixels. */
  private readonly ground = new TileCover((d) => d.layer === 0 && d.pass === Pass.Background1);

  /**
   * Whether a star pixel at screen (x, y) of draw list `items` is hidden by the ground. The cover is
   * rebuilt once per draw list (the sim starts a new array every tick).
   */
  hides(items: readonly Draw[], x: number, y: number): boolean {
    return this.ground.covers(items, x, y);
  }
}
