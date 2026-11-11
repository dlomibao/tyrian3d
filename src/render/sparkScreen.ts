// The colour of a spark pixel in the original look (DECISIONS.md D147).
//
// JE_drawSP (src/sim/varz.ts) draws each superpixel as a plus of five pixels whose brightness is
// the screen's under it plus the spark's life, halved: `(((screen & 0x0f) + add) >> 1) + base`
// (sparkColor). Over the game's backgrounds that is a bright plus in the spark's hue fading into
// the ground. The draw list has no screen, so the sim records the colour over a black screen, which
// drew every spark as a dark plus. Here the screen pixel under a spark is read back from the draws
// before it in the same draw list, as the C's screen held it: the topmost tile, sprite, rectangle or
// pixel covering it, with the C's blend, darken, filter and hue/value blits applied to its value.

import { decodeSprite2, decodeTableSprite, type DecodedSprite } from "../data/sprites";
import { TILE_HEIGHT, TILE_WIDTH } from "../data/levels";
import { Pass, sparkColor, type Draw, type PixelDraw } from "../sim/draw";
import { composeSprite2x2 } from "./spriteMesh";

/** VGAScreen's size. */
const SCREEN_W = 320;
const SCREEN_H = 200;

export class SparkScreen {
  private items: readonly Draw[] | null = null;
  /** Colours worked out for this draw list's spark pixels (a later spark reads an earlier one's). */
  private readonly done = new Map<PixelDraw, number>();
  private readonly sprite2s = new Map<string, DecodedSprite>();
  private readonly tables = new WeakMap<object, DecodedSprite>();

  /** The palette index the C drew for spark pixel `items[index]` (its `spark` set). */
  color(items: readonly Draw[], index: number): number {
    if (items !== this.items) {
      this.items = items;
      this.done.clear();
    }
    const d = items[index] as PixelDraw;
    let c = this.done.get(d);
    if (c === undefined) {
      c = sparkColor(d.spark!, this.value(items, index, d.x, d.y));
      this.done.set(d, c);
    }
    return c;
  }

  /** The value nibble (0-15) of screen pixel (x, y) after items[0..end) were drawn; 0 if nothing covers it. */
  value(items: readonly Draw[], end: number, x: number, y: number): number {
    if (x < 0 || y < 0 || x >= SCREEN_W || y >= SCREEN_H) return 0;
    for (let i = end - 1; i >= 0; i--) {
      const d = items[i];
      let p: number;
      let effect: string = "none";
      let shift = 0;
      switch (d.kind) {
        case "tile": {
          const tx = x - Math.round(d.x), ty = y - Math.round(d.y);
          if (tx < 0 || ty < 0 || tx >= TILE_WIDTH || ty >= TILE_HEIGHT) continue;
          p = d.tile[ty * TILE_WIDTH + tx];
          if (p === 0 && d.layer > 0) continue; // backgrounds 2 and 3 skip index 0
          effect = d.effect;
          break;
        }
        case "sprite2":
        case "sprite": {
          const s = this.decoded(d);
          const sx = x - Math.round(d.x), sy = y - Math.round(d.y);
          if (!s || sx < 0 || sy < 0 || sx >= s.width || sy >= s.height) continue;
          p = s.pixels[sy * s.width + sx];
          if (p < 0) continue;
          effect = d.effect;
          shift = d.value;
          break;
        }
        case "rect":
          if (x < d.x1 || x > d.x2 || y < d.y1 || y > d.y2) continue;
          p = d.color;
          break;
        case "pixel":
          if (d.x !== x || d.y !== y) continue;
          // A star is drawn only on black (D127): over anything else the screen kept its pixel.
          if (d.pass === Pass.Starfield && this.value(items, i, x, y) !== 0) continue;
          p = d.spark ? this.color(items, i) : d.color;
          break;
      }
      switch (effect) {
        case "blend": // blit_sprite2_blend, draw_background_2_blend: the two values averaged
          return ((p & 0x0f) + this.value(items, i, x, y)) >> 1;
        case "darken": // blit_sprite2_darken: what's under it, half as bright
          return this.value(items, i, x, y) >> 1;
        case "hv": // blit_sprite_hv: the value shifted, kept in its ramp
          return Math.max(0, Math.min(15, (p & 0x0f) + shift));
        default: // a plain or filtered blit keeps the sprite's value
          return p & 0x0f;
      }
    }
    return 0;
  }

  private decoded(d: Draw & { kind: "sprite2" | "sprite" }): DecodedSprite | null {
    if (d.kind === "sprite2") {
      const key = `${d.sheet.id}#${d.index}#${d.size}`;
      let s = this.sprite2s.get(key);
      if (!s) {
        s = d.size === 2 ? composeSprite2x2(d.sheet.data, d.index) : decodeSprite2(d.sheet.data, d.index);
        this.sprite2s.set(key, s);
      }
      return s;
    }
    const t = d.table.sprites[d.index];
    if (!t) return null;
    let s = this.tables.get(t);
    if (!s) {
      s = decodeTableSprite(t);
      this.tables.set(t, s);
    }
    return s;
  }
}
