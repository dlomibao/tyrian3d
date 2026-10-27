// The screen effects OpenTyrian applies to game_screen's pixels, recorded for the renderer.
//
// JE_main (tyrian2.c) runs pixel filters between its draw passes when a level switches them on
// with event 64 ("smoothies", backgrnd.c): lava_filter, water_filter, iced_blur_filter and
// blur_filter rewrite everything drawn so far, and at the end of the frame JE_starShowVGA shows the
// screen flipped (smoothie 9) or lit by the ship's headlight (smoothie 6). The Zinglon specials'
// JE_barBright (vga256d.c) brightens columns. There are no pixels here (DECISIONS.md D1), so each
// tick records which effects are on, and up to which draw pass, in drawList.screen; the renderer
// turns that into post-processing (src/render/screenFilters.ts, DECISIONS.md D31).
//
// The level colour filter and brightness (JE_filterScreen, levelFilter/levelBrightness) are already
// in drawList.filter and drawList.brightness (backgrnd.ts).

import { drawList, Pass } from "./draw";
import { g } from "./state";

/** What JE_main does to the screen this tick. Coordinates are game_screen pixels (as the draws). */
export interface ScreenFilters {
  /**
   * The effects that rewrite the pixels drawn so far, in the order JE_main runs them. `pass` is the
   * last draw pass already on the screen when the filter runs; later passes are drawn over its
   * result. Only the first filter of a frame reads the previous frame (see below).
   */
  stages: ScreenFilterStage[];
  /**
   * JE_starShowVGA's starShowVGASpecialCode: 1 = showFlipped (smoothie 9), 2 = showHeadlight
   * (smoothie 6), else showNormal.
   */
  showCode: number;
  /** player[0].x, .y for showHeadlight. */
  playerX: number;
  playerY: number;
  /** JE_barBright rectangles drawn this tick, as x1, y1, x2, y2 (inclusive), four numbers each. */
  bars: number[];
}

/**
 * One pixel filter. The C draws into VGAScreen2 while any smoothie is on, and the first filter of
 * the frame writes its result into game_screen, which still holds the previous frame: that's where
 * the blurs' and the lava's trails come from. Every later filter that frame works in place on
 * game_screen. `temporal` marks the first one.
 */
export type ScreenFilterStage =
  /** lava_filter: red hue, a wavy sideways shift and a vertical smear. */
  | { kind: "lava"; pass: Pass; temporal: boolean }
  /** water_filter: everything but grey and cloud-blue hues becomes `hue`, rippling down. */
  | { kind: "water"; pass: Pass; temporal: boolean; hue: number }
  /** iced_blur_filter: ice-blue hue (0x80), blurred with the previous frame when temporal. */
  | { kind: "iced"; pass: Pass; temporal: boolean }
  /** blur_filter: the hue kept, the value blurred with the previous frame when temporal. */
  | { kind: "blur"; pass: Pass; temporal: boolean };

type StageWithoutTemporal = ScreenFilterStage extends infer S ? (S extends ScreenFilterStage ? Omit<S, "temporal"> : never) : never;

/** The JE_barBright calls since the last recordScreenFilters. */
const bars: number[] = [];

/**
 * JE_barBright (vga256d.c L110-143): adds 2 to the value of every pixel in the rectangle, keeping
 * its hue. Recorded for the renderer.
 */
export function JE_barBright(a: number, b: number, c: number, d: number): void {
  // The C asserts the rectangle is on the 320x200 surface.
  if (a < 320 && b < 200 && c < 320 && d < 200) bars.push(a, b, c, d);
}

/** level_loop's starShowVGASpecialCode (tyrian2.c L974-983), worked out at the top of each tick. */
export function updateStarShowVGASpecialCode(): void {
  // (isNetworkGame clears smoothies 9 and 6 instead; there are no network games.)
  g.starShowVGASpecialCode = Number(g.smoothies[9 - 1]) + (Number(g.smoothies[6 - 1]) << 1);
}

/**
 * The smoothie filters JE_main runs this tick (tyrian2.c L1190-1292), in order, with the
 * processorType checks of the C.
 */
export function screenFilterStages(): ScreenFilterStage[] {
  const s = g.smoothies;
  const pt = g.processorType;
  const stages: ScreenFilterStage[] = [];
  const add = (stage: StageWithoutTemporal) => stages.push({ ...stage, temporal: stages.length === 0 } as ScreenFilterStage);

  // After the starfield, before background 2: iced_blur_filter for smoothie 5.
  if (pt > 1 && s[5 - 1]) add({ kind: "iced", pass: Pass.Starfield });
  // After background 2 (when under the ground enemies): lava (smoothie_data[0] == 0), water.
  if (s[0] && pt > 2 && g.smoothie_data[0] === 0) add({ kind: "lava", pass: Pass.Background2Under });
  if (s[2 - 1] && pt > 2) add({ kind: "water", pass: Pass.Background2Under, hue: (g.smoothie_data[2 - 1] << 4) & 0xff });
  // After the ground enemies: lava (smoothie_data[0] > 0).
  if (s[0] && pt > 2 && g.smoothie_data[0] > 0) add({ kind: "lava", pass: Pass.GroundEnemies });
  // After background 2 (over the ground enemies) and background 3 (under the sky enemies).
  if (pt > 1 && s[3 - 1]) add({ kind: "iced", pass: Pass.Background3Under });
  if (pt > 1 && s[4 - 1]) add({ kind: "blur", pass: Pass.Background3Under });
  return stages;
}

/**
 * Record this tick's screen effects in drawList.screen (null when there are none), and forget the
 * JE_barBright calls. Call once per tick, after the draws.
 */
export function recordScreenFilters(): void {
  const stages = screenFilterStages();
  // JE_starShowVGA: showHeadlight needs processorType >= 2; code 3 (both) is showNormal.
  const showCode = g.starShowVGASpecialCode === 1 || (g.starShowVGASpecialCode === 2 && g.processorType >= 2) ? g.starShowVGASpecialCode : 0;
  if (stages.length === 0 && showCode === 0 && bars.length === 0) {
    drawList.screen = null;
    return;
  }
  drawList.screen = { stages, showCode, playerX: g.player[0].x, playerY: g.player[0].y, bars: bars.splice(0) };
}
