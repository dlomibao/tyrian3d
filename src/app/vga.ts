// A 320x200 8-bit screen for the screens that are the original's pictures (the episode ending's
// animation, text and credits): VGAScreen, its palette and fades, the sprite and font blits they
// use, and the C's frame timing and input waits, shown in a canvas scaled to fit the window.
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

/** fonthand.c fontMap[256]: character to font sprite index, -1 for none. */
// prettier-ignore
const fontMap = [
   -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
   -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,  -1,
   -1,  26,  33,  60,  61,  62,  -1,  32,  64,  65,  63,  84,  29,  83,  28,  80, //  !"#$%&'()*+,-./
   79,  70,  71,  72,  73,  74,  75,  76,  77,  78,  31,  30,  -1,  85,  -1,  27, // 0123456789:;<=>?
   -1,   0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,  13,  14, // @ABCDEFGHIJKLMNO
   15,  16,  17,  18,  19,  20,  21,  22,  23,  24,  25,  68,  82,  69,  -1,  -1, // PQRSTUVWXYZ[\]^_
   -1,  34,  35,  36,  37,  38,  39,  40,  41,  42,  43,  44,  45,  46,  47,  48, // `abcdefghijklmno
   49,  50,  51,  52,  53,  54,  55,  56,  57,  58,  59,  66,  81,  67,  -1,  -1, // pqrstuvwxyz{|}~⌂
   86,  87,  88,  89,  90,  91,  92,  93,  94,  95,  96,  97,  98,  99, 100, 101, // ÇüéâäàåçêëèïîìÄÅ
  102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, // ÉæÆôöòûùÿÖÜ¢£¥₧ƒ
  118, 119, 120, 121, 122, 123, 124, 125, 126,  -1,  -1,  -1,  -1,  -1,  -1,  -1, // áíóúñÑªº¿
];
/** fontMap[(unsigned char)s[i]] */
export const fontSprite = (s: string, i: number): number => fontMap[s.charCodeAt(i) & 0xff] ?? -1;

/** A sprite table (Sprite_array): the fonts are tyrian.shp tables 0-2, estsc.shp is EXTRA_SHAPES. */
export type SpriteTableSprites = (TableSprite | null)[];

/** RGB triples (8-bit) from a palette.dat palette (6-bit VGA). */
export function paletteRgb(palette: Palette): Uint8Array {
  const rgb = new Uint8Array(768);
  for (let i = 0; i < 768; i++) rgb[i] = vga6To8(palette[i]);
  return rgb;
}

/** Fresh key, click and gamepad presses: OpenTyrian's getInput() for the screens that wait. */
class Input {
  private pressed = false;
  private padHeld = true; // ignore buttons held when the screen appears
  private readonly onKey = (e: KeyboardEvent) => {
    if (e.repeat) return;
    e.preventDefault();
    this.pressed = true;
  };
  private readonly onPointer = () => (this.pressed = true);

  constructor(private readonly target: HTMLElement) {
    window.addEventListener("keydown", this.onKey);
    target.addEventListener("pointerdown", this.onPointer);
  }

  /** getInput(): true once per press. */
  get(): boolean {
    const held = (navigator.getGamepads?.() ?? []).some((p) => p?.buttons.some((b) => b.pressed));
    if (held && !this.padHeld) this.pressed = true;
    this.padHeld = held;
    const was = this.pressed;
    this.pressed = false;
    return was;
  }

  /** keyboardClearInput / mouseClearInput */
  clear(): void {
    this.get();
    this.pressed = false;
  }

  dispose(): void {
    window.removeEventListener("keydown", this.onKey);
    this.target.removeEventListener("pointerdown", this.onPointer);
  }
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
  readonly el: HTMLDivElement;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly image: ImageData;
  readonly input: Input;
  private frameCountEnd = performance.now();
  private frameCount2End = performance.now();

  constructor() {
    this.el = document.createElement("div");
    this.el.className = "vga-screen";
    const canvas = document.createElement("canvas");
    canvas.width = VGA_WIDTH;
    canvas.height = VGA_HEIGHT;
    this.el.appendChild(canvas);
    document.body.appendChild(this.el);
    this.ctx = canvas.getContext("2d")!;
    this.image = this.ctx.createImageData(VGA_WIDTH, VGA_HEIGHT);
    this.input = new Input(this.el);
  }

  dispose(): void {
    this.input.dispose();
    this.el.remove();
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

  // --- text (fonthand.c) ---

  /** JE_textWidth */
  static textWidth(s: string, font: SpriteTableSprites): number {
    let x = 0;
    for (let i = 0; i < s.length; ++i) {
      const sprite_id = fontSprite(s, i);
      if (s[i] === " ") x += 6;
      else if (sprite_id !== -1) x += (font[sprite_id]?.width ?? 0) + 1;
    }
    return x;
  }

  /** JE_fontCenter */
  static fontCenter(s: string, font: SpriteTableSprites): number {
    return 160 - Math.trunc(Vga.textWidth(s, font) / 2);
  }

  /** JE_dString: shadowed text in the bright bank (fonthand.c L64-95). */
  dString(x: number, y: number, s: string, font: SpriteTableSprites): void {
    const defaultBrightness = -3;
    let bright = 0;
    for (let i = 0; i < s.length; ++i) {
      const sprite_id = fontSprite(s, i);
      switch (s[i]) {
        case " ":
          x += 6;
          break;
        case "~":
          bright = bright === 0 ? 2 : 0;
          break;
        default: {
          const sprite = font[sprite_id];
          if (sprite_id !== -1 && sprite) {
            this.blitSpriteDark(x + 2, y + 2, sprite, false);
            this.blitSpriteHV(x, y, sprite, 0xf, defaultBrightness + bright);
            x += sprite.width + 1;
          }
          break;
        }
      }
    }
  }

  /**
   * JE_outTextAdjust (fonthand.c L195-225). `tiny` is TINY_FONT, which the C checks for the
   * character whatever the font.
   */
  outTextAdjust(x: number, y: number, s: string, filter: number, brightness: number, font: SpriteTableSprites, tiny: SpriteTableSprites, shadow: boolean): void {
    let bright = 0;
    for (let i = 0; i < s.length; ++i) {
      const sprite_id = fontSprite(s, i);
      switch (s[i]) {
        case " ":
          x += 6;
          break;
        case "~":
          bright = bright === 0 ? 4 : 0;
          break;
        default: {
          const sprite = font[sprite_id];
          if (sprite_id !== -1 && tiny[sprite_id] && sprite) {
            if (shadow) this.blitSpriteDark(x + 2, y + 2, sprite, false);
            this.blitSpriteHV(x, y, sprite, filter, brightness + bright);
            x += sprite.width + 1;
          }
          break;
        }
      }
    }
  }

  /** JE_outText (fonthand.c L143-174), in TINY_FONT: a negative brightness draws black. */
  outText(x: number, y: number, s: string, colorbank: number, brightness: number, tiny: SpriteTableSprites): void {
    let bright = 0;
    for (let i = 0; i < s.length; ++i) {
      const sprite_id = fontSprite(s, i);
      switch (s[i]) {
        case " ":
          x += 6;
          break;
        case "~":
          bright = bright === 0 ? 4 : 0;
          break;
        default: {
          const sprite = tiny[sprite_id];
          if (sprite_id !== -1 && sprite) {
            if (brightness >= 0) this.blitSpriteHV(x, y, sprite, colorbank, brightness + bright);
            else this.blitSpriteDark(x, y, sprite, true);
            x += sprite.width + 1;
          }
          break;
        }
      }
    }
  }

  /** JE_textShade(..., PART_SHADE) */
  textShadePart(x: number, y: number, s: string, colorbank: number, brightness: number, tiny: SpriteTableSprites): void {
    this.outText(x + 1, y + 1, s, 0, -1, tiny);
    this.outText(x, y, s, colorbank, brightness, tiny);
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
