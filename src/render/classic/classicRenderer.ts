// The original look, for the side-by-side comparison (`?compare=1`, DECISIONS.md D158): each tick's
// draw list rasterised the way OpenTyrian draws it, onto a 320x200 indexed screen.
//
// The sim records the C's blits instead of writing pixels (draw.ts); this replays them with the C's
// pixel rules (sprite.c blit_sprite2*, blit_sprite*), the smoothie filters (backgrnd.c lava_filter,
// water_filter, iced_blur_filter, blur_filter), JE_filterScreen's hue and value, JE_barBright, and
// JE_starShowVGA's copy of game_screen's playfield (x 24..287, rows 0..183) to the screen's top left
// (showNormal, showFlipped, showHeadlight). The HUD around it is classicHud.ts.
//
// It is a debugging aid, not a second port: close enough to compare the looks, not pixel-exact
// (unclipped blits clip here instead of wrapping into the next row; the three blit_sprite_hv
// variants are drawn as blit_sprite_hv).

import { decodeSprite2, decodeTableSprite, type DecodedSprite } from "../../data/sprites";
import { Pass, sparkColor, type Draw, type DrawList, type SpriteTable, type Sprite2Sheet } from "../../sim/draw";
import type { ScreenFilterStage } from "../../sim/smoothies";

export const SCREEN_W = 320;
export const SCREEN_H = 200;
/** The playfield on game_screen (showNormal copies it to the screen's top left). */
export const PLAY_X = 24;
export const PLAY_W = 264;
export const PLAY_H = 184;

const sprite2Cache = new Map<string, DecodedSprite>();
const tableCache = new Map<string, DecodedSprite | null>();

function sprite2(sheet: Sprite2Sheet, index: number): DecodedSprite {
  const k = `${sheet.id}#${index}`;
  let s = sprite2Cache.get(k);
  if (!s) sprite2Cache.set(k, (s = decodeSprite2(sheet.data, index)));
  return s;
}

/** A sprite table entry, decoded (null if the slot is empty). */
export function tableSprite(table: SpriteTable, index: number): DecodedSprite | null {
  const k = `${table.id}#${index}`;
  let s = tableCache.get(k);
  if (s === undefined) {
    const t = table.sprites[index];
    s = t ? decodeTableSprite(t as never) : null;
    tableCache.set(k, s);
  }
  return s;
}

/** An indexed 320x200 surface. */
export class Surface {
  readonly px = new Uint8Array(SCREEN_W * SCREEN_H);

  /** Plot one pixel through `op(src, dst)`, clipped to the surface. */
  put(x: number, y: number, v: number): void {
    if (x < 0 || y < 0 || x >= SCREEN_W || y >= SCREEN_H) return;
    this.px[y * SCREEN_W + x] = v & 0xff;
  }

  get(x: number, y: number): number {
    if (x < 0 || y < 0 || x >= SCREEN_W || y >= SCREEN_H) return 0;
    return this.px[y * SCREEN_W + x];
  }

  /** fill_rectangle_xy: inclusive corners. */
  fill(x1: number, y1: number, x2: number, y2: number, c: number): void {
    for (let y = Math.max(0, y1); y <= Math.min(SCREEN_H - 1, y2); y++)
      for (let x = Math.max(0, x1); x <= Math.min(SCREEN_W - 1, x2); x++) this.px[y * SCREEN_W + x] = c & 0xff;
  }

  /**
   * Draw a decoded sprite with the C's per-pixel rule `op(src, dst)`.
   */
  blit(s: DecodedSprite, x: number, y: number, op: (src: number, dst: number) => number): void {
    for (let j = 0; j < s.height; j++) {
      const sy = y + j;
      if (sy < 0 || sy >= SCREEN_H) continue;
      for (let i = 0; i < s.width; i++) {
        const c = s.pixels[j * s.width + i];
        if (c < 0) continue;
        const sx = x + i;
        if (sx < 0 || sx >= SCREEN_W) continue;
        const o = sy * SCREEN_W + sx;
        this.px[o] = op(c, this.px[o]) & 0xff;
      }
    }
  }
}

// The C's pixel rules.
const OPAQUE = (s: number) => s;
const BLEND = (s: number, d: number) => (((s & 0x0f) + (d & 0x0f)) >> 1) | (s & 0xf0);
const DARKEN = (_s: number, d: number) => ((d & 0x0f) >> 1) + (d & 0xf0);
const filterOp = (filter: number) => (s: number) => (filter & 0xf0) | (s & 0x0f);
/** blit_sprite_hv: hue << 4, value added with the C's wrap (>= 0x1f becomes 0, above 0xf becomes 0xf). */
export const hvOp = (hue: number, value: number) => (s: number) => {
  let t = ((s & 0x0f) + value) & 0xff;
  if (t > 0x0f) t = t >= 0x1f ? 0 : 0x0f;
  return ((hue << 4) & 0xf0) | t;
};

function sprite2Op(d: { effect: string; filter: number }) {
  switch (d.effect) {
    case "blend":
      return BLEND;
    case "darken":
      return DARKEN;
    case "filter":
      return filterOp(d.filter);
    default:
      return OPAQUE;
  }
}

/** Replay one draw onto `screen`. */
export function drawOne(screen: Surface, d: Draw): void {
  switch (d.kind) {
    case "sprite2": {
      const op = sprite2Op(d);
      if (d.size === 1) screen.blit(sprite2(d.sheet, d.index), d.x, d.y, op);
      else {
        screen.blit(sprite2(d.sheet, d.index), d.x, d.y, op);
        screen.blit(sprite2(d.sheet, d.index + 1), d.x + 12, d.y, op);
        screen.blit(sprite2(d.sheet, d.index + 19), d.x, d.y + 14, op);
        screen.blit(sprite2(d.sheet, d.index + 20), d.x + 12, d.y + 14, op);
      }
      break;
    }
    case "sprite": {
      const s = tableSprite(d.table, d.index);
      if (!s) break;
      const op = d.effect === "blend" ? BLEND : d.effect === "darken" ? DARKEN : d.effect === "hv" ? hvOp(d.filter, d.value) : OPAQUE;
      screen.blit(s, d.x, d.y, op);
      break;
    }
    case "tile": {
      const opaque = d.layer === 0;
      for (let j = 0; j < 28; j++) {
        const sy = d.y + j;
        if (sy < 0 || sy >= SCREEN_H) continue;
        for (let i = 0; i < 24; i++) {
          const c = d.tile[j * 24 + i];
          if (!opaque && c === 0) continue;
          const sx = d.x + i;
          if (sx < 0 || sx >= SCREEN_W) continue;
          const o = sy * SCREEN_W + sx;
          screen.px[o] = d.effect === "blend" ? BLEND(c, screen.px[o]) : c;
        }
      }
      break;
    }
    case "pixel":
      screen.put(d.x, d.y, d.spark ? sparkColor(d.spark, screen.get(d.x, d.y)) : d.color);
      break;
    case "rect":
      screen.fill(d.x1, d.y1, d.x2, d.y2, d.color);
      break;
  }
}

// --- Smoothies (backgrnd.c), on whole surfaces: dst is written, src read ---

function lava(dst: Uint8Array, src: Uint8Array): void {
  const out = new Uint8Array(dst);
  for (let y = 0; y < 185 && y < SCREEN_H; y++) {
    for (let x = 0; x < SCREEN_W; x++) {
      const diw = y * SCREEN_W + x;
      const wavey = Math.abs(((diw >> 9) & 0xf) - 8) - 1;
      const i = y * SCREEN_W + x + wavey;
      const v = ((src[i] ?? 0) & 0x0f) * 2 + ((dst[i + SCREEN_W] ?? 0) & 0x0f) + (y > 0 ? (dst[i - SCREEN_W] ?? 0) & 0x0f : 0);
      out[y * SCREEN_W + x] = 0x70 | ((v >> 2) & 0x0f);
    }
  }
  dst.set(out);
}

function water(dst: Uint8Array, src: Uint8Array, hue: number): void {
  const out = new Uint8Array(dst);
  for (let y = 0; y < 185 && y < SCREEN_H; y++) {
    for (let x = 0; x < SCREEN_W; x++) {
      const o = y * SCREEN_W + x;
      const s = src[o];
      if ((s & 0x30) === 0) out[o] = s;
      else {
        const wavey = Math.abs(((o >> 10) & 0x7) - 4) - 1;
        const v = (s & 0x0f) + ((dst[o + wavey + SCREEN_W] ?? 0) & 0x0f);
        out[o] = (hue & 0xf0) | (v >> 1);
      }
    }
  }
  dst.set(out);
}

function iced(dst: Uint8Array, src: Uint8Array): void {
  for (let o = 0; o < 184 * SCREEN_W; o++) dst[o] = 0x80 | (((src[o] & 0x0f) + (dst[o] & 0x0f)) >> 1);
}

function blur(dst: Uint8Array, src: Uint8Array): void {
  for (let o = 0; o < 184 * SCREEN_W; o++) dst[o] = (src[o] & 0xf0) | (((src[o] & 0x0f) + (dst[o] & 0x0f)) >> 1);
}

function runStage(stage: ScreenFilterStage, dst: Uint8Array, src: Uint8Array): void {
  if (stage.kind === "lava") lava(dst, src);
  else if (stage.kind === "water") water(dst, src, stage.hue);
  else if (stage.kind === "iced") iced(dst, src);
  else blur(dst, src);
}

/** filterScreenHue / filterScreenValue (backgrnd.c) over the playfield. */
export function filterScreen(px: Uint8Array, hue: number, brightness: number): void {
  for (let y = 0; y < PLAY_H; y++) {
    for (let x = PLAY_X; x < PLAY_X + PLAY_W; x++) {
      const o = y * SCREEN_W + x;
      let p = px[o];
      if (hue !== -99) p = ((hue << 4) & 0xf0) | (p & 0x0f);
      if (brightness !== 0 && brightness !== -99) {
        const v = p & 0x0f;
        let nv: number;
        if (brightness < 0) nv = Math.max(0, v + brightness);
        else if (brightness <= 0xf) nv = Math.min(0xf, v + brightness);
        else nv = v + (brightness - 0xf) >= 0x10 ? 0 : 0xf;
        p = (p & 0xf0) | nv;
      }
      px[o] = p;
    }
  }
}

/** JE_barBright: value + 2, capped, hue kept. */
function barBright(px: Uint8Array, x1: number, y1: number, x2: number, y2: number): void {
  for (let y = y1; y <= y2; y++)
    for (let x = x1; x <= x2; x++) {
      const o = y * SCREEN_W + x;
      px[o] = (px[o] & 0xf0) | Math.min(0x0f, (px[o] & 0x0f) + 2);
    }
}

/** JE_starShowVGA: game_screen's playfield to the screen's top left. */
function show(dst: Uint8Array, src: Uint8Array, code: number, playerX: number, playerY: number): void {
  for (let y = 0; y < PLAY_H; y++) {
    const sy = code === 1 ? PLAY_H - 1 - y : y;
    dst.set(src.subarray(sy * SCREEN_W + PLAY_X, sy * SCREEN_W + PLAY_X + PLAY_W), y * SCREEN_W);
  }
  if (code !== 2) return;
  // showHeadlight (backgrnd.c L855-988): dark (value / 4) but for a cone ahead of the ship.
  let lx = playerX - 17 - (playerY + 12) + 1;
  let rx = playerX - 17 + (playerY + 12);
  for (let y = 0; y < PLAY_H; y++) {
    const row = y * SCREEN_W;
    const dark = (p: number) => (p & 0xf0) | ((p & 0x0f) >> 2);
    if (lx > rx + 1) {
      for (let c = 0; c < PLAY_W; c++) dst[row + c] = dark(dst[row + c]);
      continue;
    }
    const x1 = PLAY_W - Math.max(0, lx - 5);
    const x2 = PLAY_W - Math.max(0, lx);
    const x3 = PLAY_W - Math.min(rx, PLAY_W);
    const x4 = PLAY_W - Math.min(rx + 5, PLAY_W);
    lx++;
    rx--;
    for (let c = 0; c < PLAY_W; c++) {
      const x = PLAY_W - c; // the C counts x down from 264
      const p = dst[row + c];
      if (x > x1) dst[row + c] = dark(p);
      else if (x > x2) dst[row + c] = (p & 0xf0) | (((p & 0x0f) + 3 * (6 - (x - x2))) >> 2);
      else if (x > x3) continue;
      else if (x > x4) dst[row + c] = (p & 0xf0) | (((p & 0x0f) + 3 * (x - x4)) >> 2);
      else dst[row + c] = dark(p);
    }
  }
}

/** What JE_main draws on game_screen after the draw list (classicHud.ts fills it in). */
export type Overlay = (gameScreen: Surface) => void;

/**
 * The original renderer: keeps game_screen between ticks (the first smoothie of a frame reads the
 * previous one), and writes the frame's playfield into `screen` (the HUD draws the rest).
 */
export class ClassicRenderer {
  readonly gameScreen = new Surface();
  private readonly work = new Surface();

  /**
   * Draw one tick. `beforeFilter` and `afterFilter` are the overlays JE_main draws on game_screen
   * before JE_filterScreen (the secret-level banner) and after it (the boss bar, JE_inGameDisplays).
   */
  render(list: DrawList, screen: Surface, beforeFilter?: Overlay, afterFilter?: Overlay): void {
    const stages = list.screen?.stages ?? [];
    // With smoothies on, the C draws into VGAScreen2 and the first filter writes into game_screen,
    // which still holds the last frame.
    const target = stages.length ? this.work : this.gameScreen;
    if (stages.length) target.px.fill(0);
    let next = 0;
    let drawingOn = target;
    const runPending = (pass: Pass | null) => {
      while (next < stages.length && (pass === null || stages[next].pass < pass)) {
        const st = stages[next++];
        if (st.temporal) {
          runStage(st, this.gameScreen.px, drawingOn.px);
          drawingOn = this.gameScreen;
        } else runStage(st, drawingOn.px, new Uint8Array(drawingOn.px));
      }
    };
    for (const d of list.items) {
      runPending(d.pass);
      drawOne(drawingOn, d);
    }
    runPending(null);
    if (drawingOn !== this.gameScreen) this.gameScreen.px.set(drawingOn.px);
    const gs = this.gameScreen;
    const bars = list.screen?.bars ?? [];
    for (let i = 0; i + 3 < bars.length; i += 4) barBright(gs.px, bars[i], bars[i + 1], bars[i + 2], bars[i + 3]);
    beforeFilter?.(gs);
    if (list.filter !== -99 || list.brightness !== 0) filterScreen(gs.px, list.filter, list.brightness);
    afterFilter?.(gs);
    show(screen.px, gs.px, list.screen?.showCode ?? 0, list.screen?.playerX ?? 0, list.screen?.playerY ?? 0);
  }
}
