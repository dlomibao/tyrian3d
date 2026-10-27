// The screens between levels: plays the StorySteps JE_loadMap records (src/sim/story.ts) on a
// canvas that stands in for the C's VGA screen. Each step is the C function it came from, ported
// with the C's frame timing (nortsong.c's frame timer, src/app/fade.ts): JE_loadPic / JE_loadPCX,
// JE_clr256, fade_palette, fade_black, fade_white, set_palette, the `]U` `]V` `]R` pans
// (tyrian2.c L2686-2814), and JE_displayText with JE_outCharGlow and JE_updateWarning
// (tyrian2.c L3709-3762, mainint.c L85-171, fonthand.c L258-286).
//
// Differences from the C, all invisible with the game's own scripts (DECISIONS.md, "Screens
// between levels"):
// - The screen is RGB, not palette indices. Each picture is coloured with its own palette when it
//   loads, text with the palette in `colors`, and palette fades are a black or white layer over
//   the screen (fade.ts). The C shows a picture in the previous palette until the fade, and pans in
//   the previous palette; every script shows pictures from black or in the same palette.
// - The screen is STORY_SCALE times 320x200, so remastered pictures (pictureArt.ts) can be sharper.
// - Esc does what ESCPressed does in the C (skips the rest of the scene's pans and text until `]n`
//   or the end of the screens), which OpenTyrian never sets.
// - The screen state starts black at each set of screens, as the C's palette is after the item
//   screen or a level; a fade to black with nothing on screen is skipped.

import "./story.css";
import { decodePcxFile, decodePicture, PICTURE_H, PICTURE_W } from "../data/pictures";
import { vga6To8 } from "../data/palette";
import { decodeTableSprite, type DecodedSprite } from "../data/sprites";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import { fontMap, JE_fontCenter, TINY_FONT } from "../sim/fonthand";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { S_WARNING } from "../sim/sndmast";
import { g } from "../sim/state";
import type { StoryStep } from "../sim/story";
import { BLACK, FadeLayer, FrameClock, WHITE } from "./fade";
import { pictureArtUrl } from "./pictureArt";

/** The story canvas is this many times 320x200. */
export const STORY_SCALE = 6;
const S = STORY_SCALE;

export interface StoryHost {
  files: TyrianFiles;
  sfx: SoundEffects;
  music: MusicPlayer;
}

export interface StoryOptions {
  /** Leave the last screen up (e.g. for a message over it); closeStoryScreens() takes it down. */
  keepOpen?: boolean;
}

/** A picture ready to draw: remastered art (drawn smoothly) or the original (pixels kept sharp). */
interface PictureSource {
  image: CanvasImageSource & { width: number; height: number };
  art: boolean;
}

/** An 8-bit RGB palette, 256 × [r, g, b]: `colors` in the C. */
type Colors = Uint8Array;

/** palettes[n] from palette.dat, 6-bit values scaled as loadPals does. */
function paletteColors(n: number): Colors {
  const pal = g.res.palettes[n] ?? g.res.palettes[0];
  return pal.map(vga6To8);
}

const css = (c: Colors, i: number) => `rgb(${c[i * 3]} ${c[i * 3 + 1]} ${c[i * 3 + 2]})`;

/**
 * Where every picture comes from: the remastered image mapped in pictureArt.ts if there is one
 * (and it loads), else JE_loadPic's picture `pic` (or JE_loadPCX's tshp2.pcx for 0) coloured
 * with its palette. Also returns the picture's `colors`.
 */
export async function pictureSource(files: TyrianFiles, pic: number, palette: number): Promise<{ source: PictureSource; colors: Colors }> {
  let indices: Uint8Array | null;
  let colors: Colors;
  if (pic === 0) {
    const pcx = decodePcxFile(requireFile(files, "tshp2.pcx"));
    indices = pcx?.pixels ?? null;
    colors = pcx?.palette8 ?? paletteColors(0);
  } else {
    indices = decodePicture(requireFile(files, "tyrian.pic"), pic);
    colors = paletteColors(palette);
  }

  const url = pictureArtUrl(pic);
  if (url) {
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return { source: { image: img, art: true }, colors };
    } catch (err) {
      console.warn(`picture ${pic}: remastered art ${url} didn't load; using the original`, err);
    }
  }

  const canvas = document.createElement("canvas");
  canvas.width = PICTURE_W;
  canvas.height = PICTURE_H;
  const ctx = canvas.getContext("2d")!;
  const img = ctx.createImageData(PICTURE_W, PICTURE_H);
  // "Attempted to load picture %d, which does not exist": the C leaves the screen as it was; here
  // it's black.
  if (indices) {
    for (let i = 0; i < indices.length; i++) {
      const c = indices[i] * 3;
      img.data[i * 4] = colors[c];
      img.data[i * 4 + 1] = colors[c + 1];
      img.data[i * 4 + 2] = colors[c + 2];
      img.data[i * 4 + 3] = 255;
    }
  } else {
    for (let i = 3; i < img.data.length; i += 4) img.data[i] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return { source: { image: canvas, art: false }, colors };
}

/** The text-screen state JE_displayText and its helpers share (C globals and its locals). */
interface TextState {
  frameCountMax: number;
  warningRed: boolean;
  levelWarningDisplay: boolean;
  useLastBank: boolean;
  warningCol: number;
  warningColChange: number;
  warningSoundDelay: number;
}

class StoryScreen {
  readonly el: HTMLDivElement;
  private readonly canvas: HTMLCanvasElement;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly fade = new FadeLayer("story-fade");
  private readonly clock = new FrameClock();
  /** colors: the palette the next fade goes to, and the one text is drawn in. */
  private colors: Colors = paletteColors(0);
  private host!: StoryHost;
  private visible = false;

  // Input (keyboard.c's newkey / mousedown / joystick, and ESCPressed).
  private pending = false;
  private ESCPressed = false;
  private padHeld: boolean[] = [];
  private readonly glyphs = new Map<number, DecodedSprite | null>();

  constructor() {
    this.el = document.createElement("div");
    this.el.className = "story";
    this.el.hidden = true;
    const screen = document.createElement("div");
    screen.className = "story-screen";
    this.canvas = document.createElement("canvas");
    this.canvas.width = PICTURE_W * S;
    this.canvas.height = PICTURE_H * S;
    this.ctx = this.canvas.getContext("2d")!;
    screen.append(this.canvas, this.fade.el);
    this.el.appendChild(screen);
    this.el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      this.pending = true;
    });
  }

  async play(steps: StoryStep[], host: StoryHost, opts: StoryOptions): Promise<void> {
    this.host = host;
    // Load every picture first, so a slow image doesn't stretch the C's timing.
    const pictures = new Map<string, Promise<{ source: PictureSource; colors: Colors }>>();
    for (const s of steps) {
      if (s.op === "loadPic" || s.op === "pan") {
        const key = `${s.pic}/${s.palette}`;
        if (!pictures.has(key)) pictures.set(key, pictureSource(host.files, s.pic, s.palette));
      }
    }
    const picture = (s: { pic: number; palette: number }) => pictures.get(`${s.pic}/${s.palette}`)!;
    await Promise.all(pictures.values());

    this.ESCPressed = false;
    this.pending = false;
    this.padHeld = this.padButtons();
    window.addEventListener("keydown", this.onKey);
    try {
      for (const step of steps) {
        switch (step.op) {
          case "loadPic": {
            this.show();
            const { source, colors } = await picture(step);
            this.drawPicture(source);
            this.colors = colors;
            break;
          }
          case "setColors":
            this.colors = paletteColors(step.palette);
            break;
          case "clear":
            this.show();
            this.JE_clr256();
            break;
          case "fadePalette":
            this.show();
            await this.fadeTo(0, BLACK, step.steps);
            break;
          case "setPalette":
            this.fade.set(0);
            break;
          case "fadeBlack":
            if (!this.visible) break; // nothing on screen to fade
            await this.fadeTo(1, BLACK, step.steps);
            break;
          case "fadeWhite":
            this.show();
            await this.fadeTo(1, WHITE, step.steps);
            break;
          case "pan": {
            this.show();
            const { source, colors } = await picture(step);
            await this.pan(step.dir, source, step.frames);
            this.colors = colors;
            break;
          }
          case "text":
            this.show();
            await this.JE_displayText(step);
            break;
          case "song":
            host.music.play(step.song);
            break;
          case "endScene":
            this.ESCPressed = false;
            break;
        }
      }
    } finally {
      window.removeEventListener("keydown", this.onKey);
      if (!opts.keepOpen) this.close();
    }
  }

  close(): void {
    this.visible = false;
    this.el.hidden = true;
  }

  /** Put the screen up, on top of everything else. A fresh screen starts black, as the C's palette is. */
  private show(): void {
    if (!this.visible) {
      this.visible = true;
      this.ctx.fillStyle = "#000";
      this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      this.fade.set(1, BLACK);
    }
    if (this.el.hidden || this.el !== document.body.lastElementChild) document.body.appendChild(this.el);
    this.el.hidden = false;
  }

  // --- Input ---

  private readonly onKey = (e: KeyboardEvent) => {
    if (e.repeat || e.ctrlKey || e.metaKey || e.altKey) return;
    if (["Shift", "Control", "Alt", "Meta", "CapsLock"].includes(e.key)) return;
    if (/^(Space|Enter|NumpadEnter|Escape|Arrow\w+)$/.test(e.code)) e.preventDefault();
    if (e.code === "Escape") this.ESCPressed = true;
    this.pending = true;
  };

  private padButtons(): boolean[] {
    const pad = (navigator.getGamepads?.() ?? []).find((p) => p);
    return pad ? pad.buttons.map((b) => b.pressed) : [];
  }

  /** getInput (keyboard.c): a key, click, tap or gamepad button pressed since the last call. */
  private getInput(): boolean {
    const now = this.padButtons();
    if (now.some((b, i) => b && !this.padHeld[i])) this.pending = true;
    this.padHeld = now;
    const pressed = this.pending;
    this.pending = false;
    return pressed;
  }

  /** keyboardClearInput / mouseClearInput */
  private clearInput(): void {
    this.pending = false;
    this.padHeld = this.padButtons();
  }

  /** waitUntilGetInputOrElapsed (keyboard.c L451-469): true if input came before the frame ended. */
  private async waitUntilGetInputOrElapsed(): Promise<boolean> {
    for (;;) {
      if (this.getInput()) return true;
      if (this.clock.elapsed()) return false;
      await new Promise((r) => setTimeout(r, Math.min(this.clock.remaining(), 5)));
    }
  }

  // --- Drawing (320x200 coordinates, scaled by S) ---

  private drawPicture(src: PictureSource): void {
    this.ctx.imageSmoothingEnabled = src.art;
    this.ctx.drawImage(src.image, 0, 0, this.canvas.width, this.canvas.height);
  }

  /** Copy rows [sy, sy + h) of a picture (any size, standing for 320x200) to row dy of the screen. */
  private blitRows(src: PictureSource, sy: number, dy: number, h: number): void {
    if (h <= 0) return;
    const k = src.image.height / PICTURE_H;
    this.ctx.imageSmoothingEnabled = src.art;
    this.ctx.drawImage(src.image, 0, sy * k, src.image.width, h * k, 0, dy * S, PICTURE_W * S, h * S);
  }

  /** Copy columns [sx, sx + w) of a picture to column dx of the screen. */
  private blitColumns(src: PictureSource, sx: number, dx: number, w: number): void {
    if (w <= 0) return;
    const k = src.image.width / PICTURE_W;
    this.ctx.imageSmoothingEnabled = src.art;
    this.ctx.drawImage(src.image, sx * k, 0, w * k, src.image.height, dx * S, 0, w * S, PICTURE_H * S);
  }

  /** fill_rectangle_xy: an inclusive rectangle in palette colour `color`. */
  private fill_rectangle_xy(x1: number, y1: number, x2: number, y2: number, color: number): void {
    this.ctx.fillStyle = css(this.colors, color);
    this.ctx.fillRect(x1 * S, y1 * S, (x2 - x1 + 1) * S, (y2 - y1 + 1) * S);
  }

  /** JE_clr256: every pixel index 0. */
  private JE_clr256(): void {
    this.fill_rectangle_xy(0, 0, PICTURE_W - 1, PICTURE_H - 1, 0);
  }

  /** fade_palette / fade_solid: one step per frame; input during a fade is discarded. */
  private async fadeTo(alpha: number, rgb: readonly number[], steps: number): Promise<void> {
    for (; steps > 0; steps--) {
      this.clock.setFrameCount(1);
      this.fade.step(alpha, rgb, steps);
      await this.clock.waitUntilElapsed();
    }
    this.clearInput();
  }

  /**
   * `]U` / `]V` / `]R` (tyrian2.c L2686-2814): VGAScreen2 holds the old screen; each frame shows
   * one more row or column of the new picture, until input or the last frame, then the whole
   * picture.
   */
  private async pan(dir: "up" | "slideUp" | "right", pic: PictureSource, frames: number): Promise<void> {
    const old = document.createElement("canvas");
    old.width = this.canvas.width;
    old.height = this.canvas.height;
    old.getContext("2d")!.drawImage(this.canvas, 0, 0);
    const vga2: PictureSource = { image: old, art: true };

    for (let z = 0; z < frames; z++) {
      if (this.ESCPressed) break;

      this.clock.setFrameCount(1);

      if (dir === "up") {
        // Rows 0..z: the picture's last z + 1 rows; below them the old screen from its top.
        this.blitRows(pic, 199 - z, 0, z + 1);
        this.blitRows(vga2, 0, z + 1, 199 - z);
      } else if (dir === "slideUp") {
        // The old screen stays; the picture's top rises from the bottom (rows 200 - z..198: the
        // C's loop stops at y < 199, so the last row waits for the end).
        this.blitRows(vga2, 0, 0, 200 - z);
        this.blitRows(pic, 0, 200 - z, z - 1);
      } else {
        // The old screen moves left by z; the picture's first z columns come in at the right.
        // (The C leaves column 319 - z as it was; here it's the old screen's column 319.)
        this.blitColumns(vga2, z, 0, 320 - z);
        this.blitColumns(pic, 0, 320 - z, z);
      }

      if (await this.waitUntilGetInputOrElapsed()) break;
    }

    this.drawPicture(pic);
  }

  // --- Text (TINY_FONT from tyrian.shp) ---

  private glyph(sprite_id: number): DecodedSprite | null {
    let d = this.glyphs.get(sprite_id);
    if (d === undefined) {
      const sprite = g.res.spriteTables[TINY_FONT].sprites[sprite_id];
      d = sprite ? decodeTableSprite(sprite) : null;
      this.glyphs.set(sprite_id, d);
    }
    return d;
  }

  /** blit_sprite_hv (sprite.c L304-366): the glyph's shades in colour bank `hue`, `value` brighter. */
  private blit_sprite_hv(x: number, y: number, sprite_id: number, hue: number, value: number): void {
    const d = this.glyph(sprite_id);
    if (!d) return;
    for (let j = 0; j < d.height; j++) {
      for (let i = 0; i < d.width; i++) {
        const p = d.pixels[j * d.width + i];
        if (p < 0) continue;
        let temp_value = ((p & 0x0f) + value) & 0xff; // Uint8
        if (temp_value > 0xf) temp_value = temp_value >= 0x1f ? 0x0 : 0xf;
        this.ctx.fillStyle = css(this.colors, (hue << 4) | temp_value);
        this.ctx.fillRect((x + i) * S, (y + j) * S, S, S);
      }
    }
  }

  /** blit_sprite_dark(..., true) (sprite.c L441-495): the glyph's shape in index 0. */
  private blit_sprite_dark(x: number, y: number, sprite_id: number): void {
    const d = this.glyph(sprite_id);
    if (!d) return;
    this.ctx.fillStyle = css(this.colors, 0);
    for (let j = 0; j < d.height; j++) {
      for (let i = 0; i < d.width; i++) {
        if (d.pixels[j * d.width + i] >= 0) this.ctx.fillRect((x + i) * S, (y + j) * S, S, S);
      }
    }
  }

  /** JE_outText (fonthand.c L143-174): brightness -1 draws the shadow; `~` toggles +4 brightness. */
  private JE_outText(x: number, y: number, s: string, colorbank: number, brightness: number): void {
    let bright = 0;
    for (let i = 0; i < s.length; ++i) {
      const sprite_id = fontMap[s.charCodeAt(i) & 0xff];
      switch (s[i]) {
        case " ":
          x += 6;
          break;
        case "~":
          bright = bright === 0 ? 4 : 0;
          break;
        default: {
          const d = sprite_id !== -1 ? this.glyph(sprite_id) : null;
          if (d) {
            if (brightness >= 0) this.blit_sprite_hv(x, y, sprite_id, colorbank, brightness + bright);
            else this.blit_sprite_dark(x, y, sprite_id);
            x += d.width + 1;
          }
          break;
        }
      }
    }
  }

  /** JE_textShade(..., PART_SHADE) (fonthand.c L119-126): a shadow one pixel down and right. */
  private JE_textShade(x: number, y: number, s: string, colorbank: number, brightness: number): void {
    this.JE_outText(x + 1, y + 1, s, 0, -1);
    this.JE_outText(x, y, s, colorbank, brightness);
  }

  /** JE_updateWarning (fonthand.c L258-286): every 6 frames the bars change shade; the siren every 15. */
  private JE_updateWarning(t: TextState): void {
    if (this.clock.elapsed2()) {
      /*Update Color Bars*/

      t.warningCol += t.warningColChange;
      if (t.warningCol > 14 * 16 + 10 || t.warningCol < 14 * 16 + 4) {
        t.warningColChange = -t.warningColChange;
      }
      this.fill_rectangle_xy(0, 0, 319, 5, t.warningCol);
      this.fill_rectangle_xy(0, 194, 319, 199, t.warningCol);

      this.clock.setFrameCount2(6);

      if (t.warningSoundDelay > 0) {
        t.warningSoundDelay--;
      } else {
        t.warningSoundDelay = 14;

        this.host.sfx.playSampleNum(S_WARNING);
      }
    }
  }

  /**
   * JE_outCharGlow (mainint.c L85-171): the text appears one character per step, each glowing up
   * from dark to bright over 19 steps and settling over 10 more; frameCountMax frames per step.
   * Input makes the rest of the text appear at once (frameCountMax = 0).
   */
  private async JE_outCharGlow(x: number, y: number, s: string, t: TextState): Promise<void> {
    const bank = t.warningRed ? 7 : t.useLastBank ? 15 : 14;

    if (s === "") return;

    if (t.frameCountMax === 0) {
      this.JE_textShade(x, y, s, bank, 0);
      return;
    }

    const maxloc = s.length;
    const glowcol = new Array<number>(Math.max(60, maxloc)).fill(-8);
    const glowcolc = new Array<number>(Math.max(60, maxloc)).fill(1);
    const textloc: number[] = [];

    let loc = x;
    for (let z = 0; z < maxloc; z++) {
      textloc[z] = loc;

      const sprite_id = fontMap[s.charCodeAt(z) & 0xff];

      if (s[z] === " ") loc += 6;
      else if (sprite_id !== -1) loc += (this.glyph(sprite_id)?.width ?? 0) + 1;
    }

    for (loc = 0; loc < s.length + 28; loc++) {
      if (this.ESCPressed) break;

      this.clock.setFrameCount(1);

      let sprite_id = -1;
      let z: number;
      for (z = loc - 28; z <= loc; z++) {
        if (z >= 0 && z < maxloc) {
          sprite_id = fontMap[s.charCodeAt(z) & 0xff];

          if (sprite_id !== -1) {
            this.blit_sprite_hv(textloc[z], y, sprite_id, bank, glowcol[z]);

            glowcol[z] += glowcolc[z];
            if (glowcol[z] > 9) glowcolc[z] = -1;
          }
        }
      }
      if (sprite_id !== -1 && --z < maxloc) this.blit_sprite_dark(textloc[z] + 1, y + 1, sprite_id);

      // JE_showVGA()

      for (let frameCount = t.frameCountMax; frameCount > 0; --frameCount) {
        if (t.levelWarningDisplay) this.JE_updateWarning(t);

        await this.clock.waitUntilElapsed();

        if (this.getInput()) t.frameCountMax = 0;

        if (this.ESCPressed) break;

        this.clock.setFrameCount(1);
      }
    }
  }

  /** `]W` and JE_displayText (tyrian2.c L2844-2876, L3709-3762). */
  private async JE_displayText(step: Extract<StoryStep, { op: "text" }>): Promise<void> {
    if (this.ESCPressed) return; // if (!ESCPressed)

    const t: TextState = {
      frameCountMax: step.frameCountMax,
      warningRed: step.warningRed,
      levelWarningDisplay: step.warningDisplay,
      useLastBank: step.useLastBank,
      warningCol: 14 * 16 + 5,
      warningColChange: 1,
      warningSoundDelay: 0,
    };
    this.clock.setFrameCount2(6);

    /* Display Warning Text */
    let tempY = 55;
    if (t.warningRed) tempY = 2;
    for (const line of step.lines) {
      if (!this.ESCPressed) {
        await this.JE_outCharGlow(10, tempY, line, t);
        tempY += 10;
      }
    }

    let slow: boolean;
    if (t.frameCountMax !== 0) {
      t.frameCountMax = 6;
      slow = true;
    } else {
      slow = false;
    }
    let tempW = 184;
    if (t.warningRed) tempW = 7 * 16 + 6;

    await this.JE_outCharGlow(JE_fontCenter(step.prompt, TINY_FONT), tempW, step.prompt, t);

    for (;;) {
      this.clock.setFrameCount(1);

      if (t.levelWarningDisplay) this.JE_updateWarning(t);

      if (await this.waitUntilGetInputOrElapsed()) break;

      if ((t.frameCountMax === 0 && slow) || this.ESCPressed) break;
    }
  }
}

let screen: StoryScreen | null = null;

/**
 * Play the screens JE_loadMap recorded (takeStorySteps()), in order and with the C's timing. Any
 * key, click, tap or gamepad button does what a key press does in the C (finishes a pan, shows the
 * rest of a text at once, then leaves it); Esc also skips the scene's remaining pans and text.
 * Resolves when the last step is done.
 */
export async function playStoryScreens(steps: StoryStep[], host: StoryHost, opts: StoryOptions = {}): Promise<void> {
  if (steps.length === 0) return;
  screen ??= new StoryScreen();
  await screen.play(steps, host, opts);
}

/** Take down a screen left up with keepOpen. */
export function closeStoryScreens(): void {
  screen?.close();
}
