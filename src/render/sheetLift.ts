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

/** Clearance a later draw keeps over the top of an earlier model it covers, world units. */
export const COVER_CLEARANCE = 0.04;
/**
 * Px taken off each side of both boxes before testing overlap: the pieces of an assembly meet edge to
 * edge, and their boxes may cross by a pixel, which must not stack them (D181).
 */
export const COVER_INSET = 2;
/** The overlap (of the smaller box) at which a model covers an earlier model (coverHeight's `minOverlap`). */
export const MODEL_COVER_OVERLAP = 0.25;

/**
 * The height a draw of base height `base` (its lowest and highest points `low` and `high`, world y)
 * and screen box (left, top)-(right, bottom) in game px is raised to, so it is above the tops of the
 * models placed before it in the frame (`models`, earlier in the C's draw order) that it overlaps on
 * screen and that bury its top: the C drew it over them. A model whose top is already the higher one
 * is left as it is (the two halves of D166's gunship are modelled to meet that way). Every draw is
 * lifted along its camera ray (D6), so the height changes depth and shadows, never the place on
 * screen. `base` if nothing earlier buries it. With `minOverlap`, only models whose box overlap is at
 * least that fraction of the smaller box count (two models that merely meet along a seam don't stack).
 */
export function coverHeight(
  base: number, low: number, high: number, left: number, top: number, right: number, bottom: number, models: readonly PlacedExtent[], minOverlap = 0,
): number {
  let need = -Infinity;
  const l = left + COVER_INSET, t = top + COVER_INSET, r = right - COVER_INSET, b = bottom - COVER_INSET;
  if (r <= l || b <= t) return base;
  for (const m of models) {
    if (m.high <= high || m.high + COVER_CLEARANCE <= low) continue;
    const ml = m.left + COVER_INSET, mt = m.top + COVER_INSET, mr = m.right - COVER_INSET, mb = m.bottom - COVER_INSET;
    const w = Math.min(r, mr) - Math.max(l, ml), h = Math.min(b, mb) - Math.max(t, mt);
    if (w <= 0 || h <= 0) continue;
    if (minOverlap > 0 && w * h < minOverlap * Math.min((r - l) * (b - t), Math.max(0, mr - ml) * Math.max(0, mb - mt))) continue;
    need = Math.max(need, m.high + COVER_CLEARANCE);
  }
  return need > low ? base + (need - low) : base;
}
