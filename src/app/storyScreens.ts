// The screens between levels: plays the StorySteps JE_loadMap records (src/sim/story.ts) on the
// stage (cinema.ts), a framework screen that stands in for the C's VGA screen. Each step is the C
// function it came from, ported with the C's frame timing (nortsong.c's frame timer,
// src/app/fade.ts): JE_loadPic / JE_loadPCX, JE_clr256, fade_palette, fade_black, fade_white,
// set_palette, the `]U` `]V` `]R` pans (tyrian2.c L2686-2814), and JE_displayText with
// JE_outCharGlow and JE_updateWarning (tyrian2.c L3709-3762, mainint.c L85-171, fonthand.c
// L258-286).
//
// Differences from the C, all invisible with the game's own scripts (DECISIONS.md, "Screens
// between levels"):
// - The screen is RGB, not palette indices. Each picture is coloured with its own palette when it
//   loads, text with the palette in `colors`, and palette fades are a black or white layer over
//   the screen (fade.ts). The C shows a picture in the previous palette until the fade, and pans in
//   the previous palette; every script shows pictures from black or in the same palette.
// - Pictures are the remastered ones (pictureArt.ts) where they exist, at 6 times 320x200, shown
//   as large as the window allows (cinema.ts).
// - Text is in the interface's type on a panel over the picture, not the tiny font on it: each
//   character still glows in step by step as JE_outCharGlow drew it, and the warning bars flash
//   along the screen's edges in JE_updateWarning's colours. Text and bars stay until the next
//   picture, as they stayed on the C's screen; a pan takes them off as it starts.
// - Esc (pad B, the Skip button) does what ESCPressed does in the C (skips the rest of the scene's
//   pans and text until `]n` or the end of the screens), which OpenTyrian never sets.
// - The screen state starts black at each set of screens, as the C's palette is after the item
//   screen or a level; a fade to black with nothing on screen is skipped.

import { decodePcxFile, decodePicture, PICTURE_H, PICTURE_W } from "../data/pictures";
import { vga6To8 } from "../data/palette";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import { fontMap } from "../sim/fonthand";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { S_WARNING } from "../sim/sndmast";
import { g } from "../sim/state";
import type { StoryStep } from "../sim/story";
import { cssColor, openCinema, releaseCinema, STAGE_H, STAGE_SCALE, STAGE_W, type Cinema, type Colors, type GlowLine } from "./cinema";
import { BLACK, WHITE } from "./fade";
import { pictureArtUrl } from "./pictureArt";

const S = STAGE_SCALE;

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
export interface PictureSource {
  image: CanvasImageSource & { width: number; height: number };
  art: boolean;
}

/** palettes[n] from palette.dat, 6-bit values scaled as loadPals does. */
export function paletteColors(n: number): Colors {
  const pal = g.res.palettes[n] ?? g.res.palettes[0];
  return pal.map(vga6To8);
}

/**
 * Where every picture comes from: the remastered image listed in public/art/pictures.json
 * (pictureArt.ts) if there is one and it loads, else JE_loadPic's picture `pic` (or JE_loadPCX's
 * tshp2.pcx for 0) coloured with its palette. Also returns the picture's `colors`.
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

  const url = await pictureArtUrl(pic);
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

/** Draw a whole picture on the stage. */
export function drawPicture(cinema: Cinema, src: PictureSource): void {
  cinema.ctx.imageSmoothingEnabled = src.art;
  cinema.ctx.drawImage(src.image, 0, 0, STAGE_W, STAGE_H);
  cinema.present();
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

/** What JE_displayText shows: a `]W` step, or the `]Q` hint (episodeEnd.ts). */
export type DisplayText = Omit<Extract<StoryStep, { op: "text" }>, "op">;

class StoryPlayer {
  /** The stage, once something is shown (a set of screens with only music doesn't open it). */
  private cinema: Cinema | null = null;
  /** colors: the palette the next fade goes to, and the one text is drawn in. */
  private colors: Colors = paletteColors(0);
  private visible = false;

  constructor(
    private readonly host: StoryHost | null,
    /** Esc skips the rest of the scene (ESCPressed); off for the `]Q` hint, where it's any key. */
    private readonly escSkips = true,
  ) {}

  /** ESCPressed */
  private get ESCPressed(): boolean {
    return this.escSkips && (this.cinema?.escape ?? false);
  }

  private set ESCPressed(v: boolean) {
    if (this.cinema) this.cinema.escape = v;
  }

  private get stage(): Cinema {
    return this.cinema!;
  }

  async play(steps: StoryStep[], opts: StoryOptions): Promise<void> {
    const host = this.host!;
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

    try {
      for (const step of steps) {
        switch (step.op) {
          case "loadPic": {
            this.show();
            const { source, colors } = await picture(step);
            this.stage.clearOverlay();
            drawPicture(this.stage, source);
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
            await this.stage.fadeTo(0, BLACK, step.steps);
            break;
          case "setPalette":
            this.cinema?.fade.set(0);
            break;
          case "fadeBlack":
            if (!this.visible) break; // nothing on screen to fade
            await this.stage.fadeTo(1, BLACK, step.steps);
            break;
          case "fadeWhite":
            this.show();
            await this.stage.fadeTo(1, WHITE, step.steps);
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
      if (this.cinema) {
        this.cinema.setSkip("none");
        if (!opts.keepOpen) releaseCinema();
      }
    }
  }

  /**
   * Put the stage up. A fresh set of screens starts black, as the C's palette is after the item
   * screen or a level, and with nothing pressed yet.
   */
  private show(): void {
    if (this.visible) return;
    this.visible = true;
    this.cinema = openCinema();
    this.cinema.blank();
    this.cinema.clearInput();
    this.cinema.escape = false;
    this.cinema.setSkip(this.escSkips ? "scene" : "none");
  }

  /** Show `text` over whatever is on the stage now (the `]Q` hint over the script's picture 5). */
  async displayOver(cinema: Cinema, colors: Colors, text: DisplayText): Promise<void> {
    this.cinema = cinema;
    this.visible = true;
    this.colors = colors;
    cinema.clearInput();
    await this.JE_displayText(text);
  }

  /** JE_clr256: every pixel index 0. */
  private JE_clr256(): void {
    this.stage.clearOverlay();
    this.stage.ctx.fillStyle = cssColor(this.colors, 0);
    this.stage.ctx.fillRect(0, 0, STAGE_W, STAGE_H);
    this.stage.present();
  }

  // --- Drawing (320x200 coordinates, scaled by S) ---

  /** Copy rows [sy, sy + h) of a picture (any size, standing for 320x200) to row dy of the screen. */
  private blitRows(src: PictureSource, sy: number, dy: number, h: number): void {
    if (h <= 0) return;
    const k = src.image.height / PICTURE_H;
    const ctx = this.stage.ctx;
    ctx.imageSmoothingEnabled = src.art;
    ctx.drawImage(src.image, 0, sy * k, src.image.width, h * k, 0, dy * S, PICTURE_W * S, h * S);
  }

  /** Copy columns [sx, sx + w) of a picture to column dx of the screen. */
  private blitColumns(src: PictureSource, sx: number, dx: number, w: number): void {
    if (w <= 0) return;
    const k = src.image.width / PICTURE_W;
    const ctx = this.stage.ctx;
    ctx.imageSmoothingEnabled = src.art;
    ctx.drawImage(src.image, sx * k, 0, w * k, src.image.height, dx * S, 0, w * S, PICTURE_H * S);
  }

  /**
   * `]U` / `]V` / `]R` (tyrian2.c L2686-2814): VGAScreen2 holds the old screen; each frame shows
   * one more row or column of the new picture, until input or the last frame, then the whole
   * picture.
   */
  private async pan(dir: "up" | "slideUp" | "right", pic: PictureSource, frames: number): Promise<void> {
    const stage = this.stage;
    const old = document.createElement("canvas");
    old.width = STAGE_W;
    old.height = STAGE_H;
    old.getContext("2d")!.drawImage(stage.canvas, 0, 0);
    const vga2: PictureSource = { image: old, art: true };
    // The text goes with the old screen.
    stage.clearOverlay(true);

    for (let z = 0; z < frames; z++) {
      if (this.ESCPressed) break;

      stage.clock.setFrameCount(1);

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
      stage.present();

      if (await stage.waitUntilGetInputOrElapsed()) break;
    }

    drawPicture(stage, pic);
  }

  // --- Text ---

  /** JE_updateWarning (fonthand.c L258-286): every 6 frames the bars change shade; the siren every 15. */
  private JE_updateWarning(t: TextState): void {
    const stage = this.stage;
    if (stage.clock.elapsed2()) {
      /*Update Color Bars*/

      t.warningCol += t.warningColChange;
      if (t.warningCol > 14 * 16 + 10 || t.warningCol < 14 * 16 + 4) {
        t.warningColChange = -t.warningColChange;
      }
      // fill_rectangle_xy(0, 0, 319, 5) and (0, 194, 319, 199): the bars along the edges.
      stage.setBars(cssColor(this.colors, t.warningCol));

      stage.clock.setFrameCount2(6);

      if (t.warningSoundDelay > 0) {
        t.warningSoundDelay--;
      } else {
        t.warningSoundDelay = 14;

        this.host?.sfx.playSampleNum(S_WARNING);
      }
    }
  }

  /**
   * JE_outCharGlow (mainint.c L85-171): the text appears one character per step, each glowing up
   * from dark to bright over 19 steps and settling over 10 more; frameCountMax frames per step.
   * Input makes the rest of the text appear at once (frameCountMax = 0). The characters are
   * `line`'s; the C's x positions and the shadow under the newest one are the panel's layout.
   */
  private async JE_outCharGlow(line: GlowLine, s: string, t: TextState): Promise<void> {
    const stage = this.stage;

    if (s === "") return;

    if (t.frameCountMax === 0) {
      line.shade(); // JE_textShade
      return;
    }

    const maxloc = s.length;
    const glowcol = new Array<number>(Math.max(60, maxloc)).fill(-8);
    const glowcolc = new Array<number>(Math.max(60, maxloc)).fill(1);

    for (let loc = 0; loc < s.length + 28; loc++) {
      if (this.ESCPressed) break;

      stage.clock.setFrameCount(1);

      for (let z = loc - 28; z <= loc; z++) {
        if (z >= 0 && z < maxloc) {
          const sprite_id = fontMap[s.charCodeAt(z) & 0xff];

          if (sprite_id !== -1) {
            line.glow(z, glowcol[z]); // blit_sprite_hv(textloc[z], y, sprite_id, bank, glowcol[z])

            glowcol[z] += glowcolc[z];
            if (glowcol[z] > 9) glowcolc[z] = -1;
          }
        }
      }

      // JE_showVGA()

      for (let frameCount = t.frameCountMax; frameCount > 0; --frameCount) {
        if (t.levelWarningDisplay) this.JE_updateWarning(t);

        await stage.clock.waitUntilElapsed();

        if (stage.getInput()) t.frameCountMax = 0;

        if (this.ESCPressed) break;

        stage.clock.setFrameCount(1);
      }
    }
  }

  /** `]W` and JE_displayText (tyrian2.c L2844-2876, L3709-3762). */
  private async JE_displayText(step: DisplayText): Promise<void> {
    if (this.ESCPressed) return; // if (!ESCPressed)

    const stage = this.stage;
    const t: TextState = {
      frameCountMax: step.frameCountMax,
      warningRed: step.warningRed,
      levelWarningDisplay: step.warningDisplay,
      useLastBank: step.useLastBank,
      warningCol: 14 * 16 + 5,
      warningColChange: 1,
      warningSoundDelay: 0,
    };
    stage.clock.setFrameCount2(6);

    const text = stage.showText({
      lines: step.lines,
      colors: this.colors,
      bank: t.warningRed ? 7 : t.useLastBank ? 15 : 14,
      top: t.warningRed, // tempY = 2, the prompt at 7 * 16 + 6
      prompt: step.prompt,
    });

    /* Display Warning Text */
    for (let i = 0; i < step.lines.length; i++) {
      if (!this.ESCPressed) await this.JE_outCharGlow(text.lines[i], step.lines[i], t);
    }

    let slow: boolean;
    if (t.frameCountMax !== 0) {
      t.frameCountMax = 6;
      slow = true;
    } else {
      slow = false;
    }

    await this.JE_outCharGlow(text.prompt, step.prompt, t);

    for (;;) {
      stage.clock.setFrameCount(1);

      if (t.levelWarningDisplay) this.JE_updateWarning(t);

      if (await stage.waitUntilGetInputOrElapsed()) break;

      if ((t.frameCountMax === 0 && slow) || this.ESCPressed) break;
    }
  }
}

/**
 * Play the screens JE_loadMap recorded (takeStorySteps()), in order and with the C's timing. Any
 * key, click, tap or gamepad button does what a key press does in the C (finishes a pan, shows the
 * rest of a text at once, then leaves it); Esc (pad B, the Skip button) also skips the scene's
 * remaining pans and text. Resolves when the last step is done.
 */
export async function playStoryScreens(steps: StoryStep[], host: StoryHost, opts: StoryOptions = {}): Promise<void> {
  if (steps.length === 0) return;
  await new StoryPlayer(host).play(steps, opts);
}

/**
 * JE_displayText over what the stage shows now, in `colors`, for the `]Q` hint (episodeEnd.ts):
 * Esc is any key there, and there are no warning bars unless `text` asks for them.
 */
export function displayTextOver(cinema: Cinema, colors: Colors, text: DisplayText, sfx?: SoundEffects): Promise<void> {
  const host = sfx ? ({ sfx } as StoryHost) : null;
  return new StoryPlayer(host, false).displayOver(cinema, colors, text);
}

/** Take down a screen left up with keepOpen (it goes once no other screen between levels takes it). */
export function closeStoryScreens(): void {
  releaseCinema();
}
