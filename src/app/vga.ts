// A 320x200 8-bit screen for the screens that are the original's pictures (the episode ending's
// animation, the credits' pictures and ships): VGAScreen, its palette and fades, the sprite and
// font blits they use, and the C's frame timing and input waits. It draws into its own small
// canvas, which the stage (cinema.ts) scales up; the input is the stage's.
//
// The blits are ported from OpenTyrian src/sprite.c, src/fonthand.c and src/vga256d.c, keeping
// their linear addressing: like the C, a sprite running off the right edge wraps onto the next
// row, and only the top and bottom of the screen clip.

import { vga6To8, type Palette, type TableSprite } from "../data";
import { CLASSIC_TICK_MS } from "../core/timing";

export const VGA_WIDTH = 320;
export const VGA_HEIGHT = 200;

/**
 * framePeriod (nortsong.c L49-58) at the Normal speed (0x4300) the game sets outside levels: one
 * setFrameCount unit, ~14.4 ms. A level's logic frame is two of these (CLASSIC_TICK_MS).
 */
export const FRAME_PERIOD_MS = CLASSIC_TICK_MS / 2;

/** A sprite table (Sprite_array): the fonts are tyrian.shp tables 0-2, estsc.shp is EXTRA_SHAPES. */
export type SpriteTableSprites = (TableSprite | null)[];

/** RGB triples (8-bit) from a palette.dat palette (6-bit VGA). */
export function paletteRgb(palette: Palette): Uint8Array {
  const rgb = new Uint8Array(768);
  for (let i = 0; i < 768; i++) rgb[i] = vga6To8(palette[i]);
  return rgb;
}

/** Fresh key, click and gamepad presses: OpenTyrian's getInput() for the screens that wait. */
export interface PressSource {
  /** getInput(): true once per press. */
  get(): boolean;
  /** keyboardClearInput / mouseClearInput */
  clear(): void;
}

/** No input (a screen drawn only to be copied, such as a sprite). */
const NO_INPUT: PressSource = { get: () => false, clear: () => {} };

export interface VgaOptions {
  /** Where presses come from (the stage's input). */
  input?: PressSource;
  /** Called after each JE_showVGA with the 320x200 canvas, to put it on screen. */
  onShow?: (canvas: HTMLCanvasElement) => void;
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, Math.max(0, ms)));

/** SDL_POLL_INTERVAL: how often the C's waits look at the input. */
const POLL_MS = 5;

/** VGAScreen with its canvas, palette (colors), timing and input. */
export class Vga {
  /** VGAScreen->pixels */
  readonly pixels = new Uint8Array(VGA_WIDTH * VGA_HEIGHT);
  /** The palette on screen (set_palette), 8-bit RGB. */
  readonly shown = new Uint8Array(768);
  /** The screen at 320x200, as JE_showVGA last left it. */
  readonly canvas: HTMLCanvasElement;
  readonly input: PressSource;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly image: ImageData;
  private readonly onShow?: (canvas: HTMLCanvasElement) => void;
  private frameCountEnd = performance.now();
  private frameCount2End = performance.now();

  constructor(opts: VgaOptions = {}) {
    this.canvas = document.createElement("canvas");
    this.canvas.width = VGA_WIDTH;
    this.canvas.height = VGA_HEIGHT;
    this.ctx = this.canvas.getContext("2d")!;
    this.image = this.ctx.createImageData(VGA_WIDTH, VGA_HEIGHT);
    this.input = opts.input ?? NO_INPUT;
    this.onShow = opts.onShow;
  }

  /**
   * A w x h corner of the screen as an image, palette index 0 transparent: a sprite drawn at 0,0
   * (the credits' pictures and ships), to show on its own.
   */
  cutOut(w: number, h: number, rgb: Uint8Array): HTMLCanvasElement {
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d")!;
    const img = ctx.createImageData(w, h);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const p = this.pixels[y * VGA_WIDTH + x];
        if (p === 0) continue;
        const o = (y * w + x) * 4;
        img.data[o] = rgb[p * 3];
        img.data[o + 1] = rgb[p * 3 + 1];
        img.data[o + 2] = rgb[p * 3 + 2];
        img.data[o + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    return canvas;
  }

  /** JE_showVGA */
  showVGA(): void {
    const d = this.image.data;
    const pal = this.shown;
    for (let i = 0; i < this.pixels.length; i++) {
      const c = this.pixels[i] * 3;
      d[i * 4] = pal[c];
      d[i * 4 + 1] = pal[c + 1];
      d[i * 4 + 2] = pal[c + 2];
      d[i * 4 + 3] = 255;
    }
    this.ctx.putImageData(this.image, 0, 0);
    this.onShow?.(this.canvas);
  }

  /** JE_clr256 */
  clr256(): void {
    this.pixels.fill(0);
  }

  /** set_palette(colors, 0, 255) */
  setPalette(rgb: Uint8Array): void {
    this.shown.set(rgb);
    this.showVGA();
  }

  // --- timing (nortsong.c L64-112, keyboard.c L398-470) ---

  /** setFrameCount: keep the partial period already elapsed, then wait `frameCount` more. */
  setFrameCount(frameCount: number): void {
    this.frameCountEnd = advance(this.frameCountEnd, frameCount);
  }

  /** setFrameCount2 */
  setFrameCount2(frameCount2: number): void {
    this.frameCount2End = advance(this.frameCount2End, frameCount2);
  }

  /** getFrameCount2Ticks() == 0 */
  frameCount2Elapsed(): boolean {
    return performance.now() >= this.frameCount2End - FRAME_PERIOD_MS / 2;
  }

  /** waitUntilElapsed */
  async waitUntilElapsed(): Promise<void> {
    for (;;) {
      const delay = this.frameCountEnd - performance.now();
      if (delay <= 0) return;
      await sleep(Math.min(delay, POLL_MS));
    }
  }

  /** waitUntilGetInputOrElapsed: true if the player pressed something. */
  async waitUntilGetInputOrElapsed(): Promise<boolean> {
    for (;;) {
      if (this.input.get()) return true;
      const delay = this.frameCountEnd - performance.now();
      if (delay <= 0) return false;
      await sleep(Math.min(delay, POLL_MS));
    }
  }

  /** waitUntilGetInput */
  async waitUntilGetInput(): Promise<void> {
    while (!this.input.get()) await sleep(POLL_MS * 2);
  }

  // --- palette fades (palette.c L100-196) ---

  /** fade_palette(colors, steps, 0, 255): from the palette on screen to `rgb`, one step per frame. */
  async fadePalette(rgb: Uint8Array, steps: number): Promise<void> {
    const from = Float64Array.from(this.shown);
    for (let step = steps; step > 0; step--) {
      this.setFrameCount(1);
      // step_fade_palette: each step moves 1/steps of the way that's left.
      for (let i = 0; i < 768; i++) {
        from[i] += (rgb[i] - from[i]) / step;
        this.shown[i] = Math.round(from[i]);
      }
      this.showVGA();
      await this.waitUntilElapsed();
    }
    // Discard input during fade.
    this.input.clear();
  }

  /** fade_black(steps) */
  fadeBlack(steps: number): Promise<void> {
    return this.fadePalette(new Uint8Array(768), steps);
  }

  // --- blits ---

  /** fill_rectangle_xy (vga256d.c L80-84), clipped to the screen like SDL_FillRect. */
  fillRectangleXY(x: number, y: number, x2: number, y2: number, color: number): void {
    for (let yy = Math.max(0, y); yy <= Math.min(VGA_HEIGHT - 1, y2); yy++) {
      this.pixels.fill(color, yy * VGA_WIDTH + Math.max(0, x), yy * VGA_WIDTH + Math.min(VGA_WIDTH - 1, x2) + 1);
    }
  }

  /**
   * The walk blit_sprite, blit_sprite_hv and blit_sprite_dark share (sprite.c L304-500): byte RLE
   * (255 n skip n, 254 next row, 253 skip 1), plotting each pixel with `plot(old, data)`.
   */
  private blitTable(x: number, y: number, sprite: TableSprite, plot: (old: number, data: number) => number): void {
    const { data, width } = sprite;
    let x_offset = 0;
    let pixels = y * VGA_WIDTH + x;
    const pixels_ul = VGA_WIDTH * VGA_HEIGHT;
    for (let i = 0; i < data.length; ++i) {
      switch (data[i]) {
        case 255: // transparent pixels
          i++; // next byte tells how many
          pixels += data[i];
          x_offset += data[i];
          break;

        case 254: // next pixel row
          pixels += width - x_offset;
          x_offset = width;
          break;

        case 253: // 1 transparent pixel
          pixels++;
          x_offset++;
          break;

        default: // set a pixel
          if (pixels >= pixels_ul) return;
          if (pixels >= 0) this.pixels[pixels] = plot(this.pixels[pixels], data[i]);

          pixels++;
          x_offset++;
          break;
      }
      if (x_offset >= width) {
        pixels += VGA_WIDTH - x_offset;
        x_offset = 0;
      }
    }
  }

  /** blit_sprite_hv: the sprite's shade (low nibble) plus `value`, in colour bank `hue`. */
  blitSpriteHV(x: number, y: number, sprite: TableSprite, hue: number, value: number): void {
    const h = (hue << 4) & 0xff;
    this.blitTable(x, y, sprite, (_old, d) => {
      let temp_value = ((d & 0x0f) + value) & 0xff; // Uint8
      if (temp_value > 0xf) temp_value = temp_value >= 0x1f ? 0x0 : 0xf;
      return h | temp_value;
    });
  }

  /** blit_sprite_dark: black, or half the shade of what's under it. */
  blitSpriteDark(x: number, y: number, sprite: TableSprite, black: boolean): void {
    this.blitTable(x, y, sprite, (old) => (black ? 0x00 : (old & 0xf0) | ((old & 0x0f) >> 1)));
  }

  /** blit_sprite2 (sprite.c L543-576): one 12-pixel-wide tile of a Sprite2 sheet. */
  blitSprite2(x: number, y: number, sheet: Uint8Array, index: number): void {
    if (index < 1 || (index - 1) * 2 + 1 >= sheet.length) return;
    let pixels = y * VGA_WIDTH + x;
    const pixels_ul = VGA_WIDTH * VGA_HEIGHT;
    let p = sheet[(index - 1) * 2] | (sheet[(index - 1) * 2 + 1] << 8);
    for (; p < sheet.length && sheet[p] !== 0x0f; ++p) {
      pixels += sheet[p] & 0x0f; // second nibble: transparent pixel count
      let count = (sheet[p] & 0xf0) >> 4; // first nibble: opaque pixel count

      if (count === 0) {
        // move to next pixel row
        pixels += VGA_WIDTH - 12;
      } else {
        while (count--) {
          ++p;
          if (pixels >= pixels_ul) return;
          if (pixels >= 0) this.pixels[pixels] = sheet[p];
          ++pixels;
        }
      }
    }
  }

  /** blit_sprite2x2 */
  blitSprite2x2(x: number, y: number, sheet: Uint8Array, index: number): void {
    this.blitSprite2(x, y, sheet, index);
    this.blitSprite2(x + 12, y, sheet, index + 1);
    this.blitSprite2(x, y + 14, sheet, index + 19);
    this.blitSprite2(x + 12, y + 14, sheet, index + 20);
  }
}

/** Advance a frame-count deadline as setFrameCount does: keep the partial period already elapsed. */
function advance(end: number, frameCount: number): number {
  const now = performance.now();
  const diff = now - end;
  if (diff >= FRAME_PERIOD_MS) end = now - (diff % FRAME_PERIOD_MS);
  else if (-diff >= FRAME_PERIOD_MS) end = now + (-diff % FRAME_PERIOD_MS);
  return end + frameCount * FRAME_PERIOD_MS;
}
