// The screens between levels, as JE_loadMap draws them (OpenTyrian src/tyrian2.c L2662-2876 and
// L2928): the episode script's pictures (`]P`, `]U`, `]V`, `]R`), fades (`]C`, `]B`, `]F`), text
// (`]W`, JE_displayText) and music (`]M`), and the fade to black before the level.
//
// The C draws these straight to the VGA screen and waits on the timer inside JE_loadMap. Here the
// script runner records each drawing or palette call as a StoryStep, in order and with the C's
// frame counts, and the host plays them (src/app/storyScreens.ts) where JE_loadMap would have
// paused: before the item screen (`]I[`), before the level starts, and at the end of an episode
// (`]Q[`). The steps keep the C's primitives (JE_loadPic, fade_palette, fade_black, ...) rather
// than one step per script command, so the player is a transliteration of those functions.
//
// One frame is one setFrameCount(1) period: 0x4300 PIT cycles, ~14.4 ms, half a game tick.

import { g } from "./state";

/** One drawing, palette or timing call JE_loadMap makes between levels. */
export type StoryStep =
  /**
   * JE_loadPic(VGAScreen, pic, false), or JE_loadPCX("tshp2.pcx") for pic 0: the picture replaces
   * the screen, and `colors` becomes palettes[palette] (tshp2.pcx brings its own: palette -1).
   * The displayed palette doesn't change until a fade or set_palette.
   */
  | { op: "loadPic"; pic: number; palette: number }
  /** memcpy(colors, palettes[palette], sizeof(colors)): the palette the next fade goes to. */
  | { op: "setColors"; palette: number }
  /** JE_clr256(VGAScreen); JE_showVGA(): the screen becomes index 0. */
  | { op: "clear" }
  /** fade_palette(colors, steps, 0, 255): from the displayed palette to `colors`; ignores input. */
  | { op: "fadePalette"; steps: number }
  /** set_palette(colors, 0, 255): show `colors` at once. */
  | { op: "setPalette" }
  /** fade_black(steps) / fade_white(steps): to a solid colour; ignores input. */
  | { op: "fadeBlack"; steps: number }
  | { op: "fadeWhite"; steps: number }
  /**
   * `]U` pan up (the new picture comes down from the top, 200 frames), `]V` slide up (it rises
   * from the bottom, 200 frames) or `]R` pan right (it comes in from the right, 319 frames) to
   * picture `pic`, one row or column per frame. Any input ends the pan with the whole picture shown.
   * Like `loadPic`, it sets `colors` to palettes[palette] without showing it.
   */
  | { op: "pan"; dir: "up" | "slideUp" | "right"; pic: number; palette: number; frames: number }
  /**
   * JE_displayText: `lines` glow in one character at a time at x 10 from y 55 (y 2 with
   * warningRed), 10 px apart, `frameCountMax` frames per character, then the prompt (miscText[4])
   * glows in centred at y 184 (y 118 with warningRed) and the screen waits for input. With
   * `warningDisplay` the warning bars flash at the top and bottom with the warning sound.
   */
  | {
      op: "text";
      lines: string[];
      prompt: string;
      frameCountMax: number;
      warningRed: boolean;
      warningDisplay: boolean;
      /** useLastBank when the text was drawn: colour bank 15 instead of 14 (7 with warningRed). */
      useLastBank: boolean;
    }
  /** play_song(song): `]M`, 0-based. */
  | { op: "song"; song: number }
  /** `]n`: end of scene, ESCPressed = false (Esc skips the rest of a scene). */
  | { op: "endScene" };

// fonthand.c globals JE_displayText reads (the warning colours and sound are the player's).
/** warningRed: `]W`'s tens digit; red text higher up. Kept until the next `]W`, as in the C. */
export let warningRed = false;
/** levelWarningDisplay: flash the warning bars (`]Wy`); JE_displayText clears it. */
export let levelWarningDisplay = false;

/** `]W`'s settings (tyrian2.c L2849-2857): levelWarningDisplay = (s[2] == 'y'), warningRed. */
export function setWarning(display: boolean, red: boolean): void {
  levelWarningDisplay = display;
  warningRed = red;
}

/**
 * JE_displayText (tyrian2.c L3709-3762): show g.levelWarningText at g.frameCountMax, with the
 * prompt miscText[4], and wait for input. Used by `]W` (and the `]Q` hint, which shows the same
 * way). The C then sets frameCountMax to 6 or 0 depending on whether a key was pressed; that's
 * the player's, so g.frameCountMax is left as it was.
 */
export function JE_displayText(): void {
  storyStep({
    op: "text",
    lines: [...g.levelWarningText],
    prompt: g.miscText[4],
    frameCountMax: g.frameCountMax,
    warningRed,
    warningDisplay: levelWarningDisplay,
    useLastBank: g.useLastBank,
  });
  levelWarningDisplay = false;
}

/** What the script has drawn since JE_loadMap started, for the host to play. */
const steps: StoryStep[] = [];

/** Record one step. */
export function storyStep(step: StoryStep): void {
  steps.push(step);
}

/** The steps recorded and not yet played, in order; the queue is emptied. */
export function takeStorySteps(): StoryStep[] {
  return steps.splice(0);
}

/** Drop unplayed steps (JE_loadMap starts with a fresh queue; hosts that never play them). */
export function clearStorySteps(): void {
  steps.length = 0;
}
