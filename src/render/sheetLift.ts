// How high a blended background-2 sheet sits (DECISIONS.md D127).
//
// draw_background_2_blend (WINDY's clouds, TYRIAN's ice) averages its tiles over whatever was drawn
// before it and under whatever comes after. Here a sheet is a flat translucent quad at its pass's
// height (D5), so a model of an earlier pass taller than that height poked through it and the sheet
// cut the model with a straight line (a ground block 0.45-1.26 under a sheet at 0.9). Every draw is
// lifted along its camera ray (D6), so a sheet's height changes only its depth, never its place on
// screen: each sheet tile is raised over the models of earlier passes it overlaps on screen, and kept
// under those of later passes.

/** A model placed this frame: its pass, its box on screen (game px) and its world heights. */
export interface PlacedExtent {
  pass: number;
  left: number;
  top: number;
  right: number;
  bottom: number;
  /** Lowest and highest world y. */
  low: number;
  high: number;
}

/** Clearance between a sheet and a model above or below it, world units. */
export const SHEET_CLEARANCE = 0.04;
/** Screen px added round a model's box: a tall model's top leans past its footprint under the tilt. */
const SCREEN_MARGIN = 4;

/**
 * The height for a sheet tile of pass `pass` at screen (x, y), w x h px, normally `base`: just above
 * the tops of the earlier passes' models it overlaps. If that would reach into a later pass's model
 * it overlaps, half way between the two (neither is fully right then, and neither is cut by much).
 */
export function sheetHeight(base: number, pass: number, x: number, y: number, w: number, h: number, models: readonly PlacedExtent[]): number {
  let below = -Infinity;
  let above = Infinity;
  for (const m of models) {
    if (m.pass === pass) continue;
    if (m.right + SCREEN_MARGIN <= x || m.left - SCREEN_MARGIN >= x + w || m.bottom + SCREEN_MARGIN <= y || m.top - SCREEN_MARGIN >= y + h) continue;
    if (m.pass < pass) below = Math.max(below, m.high);
    else above = Math.min(above, m.low);
  }
  const lifted = Math.max(base, below + SHEET_CLEARANCE);
  if (lifted <= above - SHEET_CLEARANCE) return lifted;
  return Math.max(base, (below + above) / 2);
}
