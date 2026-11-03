// The remastered HUD frame's geometry and its gauges' arithmetic (DECISIONS.md D61), kept free of
// the DOM so it can be tested.
//
// The frame is drawn in "frame units": the original's 320x200 screen is 320x200 units, its
// playfield 264x184 at the top left, the sidebar (JE_loadPic 3) to its right and the message bar
// (JE_drawTextWindow, y 189) below.
//
// Landscape: the opening is 184 units tall and at least 264 wide, the original's playfield; the
// approved design ("A — Faithful bronze") draws the sidebar from x 259, here it follows the
// opening, 61 units wide. The block (opening and sidebar over the bar) is scaled to the window's
// height, or to its width when that's narrower than 325 units' worth. A wider window widens the
// opening, up to the playfield's own on-screen width (the camera's, playfieldScreenAspect in
// render/view.ts), and anything left after that is bronze "wing" plate at the sides, or above and
// below on a 4:3 screen. The playfield is fitted into the opening, sitting on the message bar like
// the original's; with the overhead camera it fills a 264-wide opening exactly. Tilted (15°, or 32°
// steep), it's wider than 264:184 and narrower at the far edge, and the opening's rest is a
// recessed bezel.
//
// Portrait (narrower than square): the playfield across the top of the screen and the instruments
// as a console under it (the design's phone layout), centred, with bronze plate above and below
// (touches steer anywhere, so the plate is steering room too).

/** The sidebar's width and the message bar's height, in frame units. */
export const SIDEBAR_W = 61;
export const BAR_H = 16;
/** The opening's height: the playfield's 184 rows. */
export const OPENING_H = 184;
/** The opening's least width: the playfield's 264 columns. */
export const OPENING_MIN_W = 264;
/** The portrait layout's width and console height, in frame units (the design's phone layout). */
export const PORTRAIT_W = 172;
export const CONSOLE_H = 78;

/** A rectangle; in frame units or CSS pixels as noted. */
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The safe area's insets in CSS pixels (notches, home bars). */
export interface Insets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export const NO_INSETS: Insets = { top: 0, right: 0, bottom: 0, left: 0 };

export interface HudLayout {
  mode: "landscape" | "portrait";
  /** CSS pixels per frame unit. */
  scale: number;
  /** The block's top left on the window, CSS pixels: frame unit (0, 0). */
  originX: number;
  originY: number;
  /** The opening's width in frame units (its height is OPENING_H; in portrait, PORTRAIT_W / aspect). */
  openingW: number;
  openingH: number;
  /** The block's size in frame units: the opening and the instruments. */
  blockW: number;
  blockH: number;
  /** The opening on the window, CSS pixels. */
  opening: Rect;
  /** Where the playfield goes on the window (inside the opening), CSS pixels: the 3D view's viewport. */
  playfield: Rect;
  /** The whole window in frame units (the SVG's viewBox), wings included. */
  viewBox: Rect;
}

/**
 * Lay the frame out on a `width` x `height` window for a playfield whose on-screen width over
 * height is `aspect`.
 */
export function hudLayout(width: number, height: number, aspect: number, insets: Insets = NO_INSETS): HudLayout {
  const portrait = width < height;
  const availW = Math.max(1, width - insets.left - insets.right);
  const availH = Math.max(1, height - insets.top - insets.bottom);
  let scale: number, openingW: number, openingH: number, blockW: number, blockH: number;
  if (portrait) {
    openingW = PORTRAIT_W;
    openingH = PORTRAIT_W / aspect;
    blockW = PORTRAIT_W;
    blockH = openingH + CONSOLE_H;
    scale = Math.min(availW / blockW, availH / blockH);
  } else {
    openingH = OPENING_H;
    blockH = OPENING_H + BAR_H;
    scale = Math.min(availH / blockH, availW / (OPENING_MIN_W + SIDEBAR_W));
    openingW = Math.max(OPENING_MIN_W, Math.min(availW / scale - SIDEBAR_W, OPENING_H * aspect));
    blockW = openingW + SIDEBAR_W;
  }
  const originX = insets.left + (availW - blockW * scale) / 2;
  const originY = insets.top + (availH - blockH * scale) / 2;
  const opening = { x: originX, y: originY, w: openingW * scale, h: openingH * scale };
  // The playfield: as wide as fits, centred across, on the opening's floor.
  const pw = Math.min(opening.w, opening.h * aspect);
  const ph = pw / aspect;
  return {
    mode: portrait ? "portrait" : "landscape",
    scale,
    originX,
    originY,
    openingW,
    openingH,
    blockW,
    blockH,
    opening,
    playfield: { x: opening.x + (opening.w - pw) / 2, y: opening.y + opening.h - ph, w: pw, h: ph },
    viewBox: { x: -originX / scale, y: -originY / scale, w: width / scale, h: height / scale },
  };
}

/** A point on the window (CSS pixels) in frame units. */
export function toFrameUnits(layout: HudLayout, p: { x: number; y: number }): { x: number; y: number } {
  return { x: (p.x - layout.originX) / layout.scale, y: (p.y - layout.originY) / layout.scale };
}

/** Rows in the shield and armor gauges (2 units each, like JE_dBar3's 2-pixel rows). */
export const GAUGE_ROWS = 30;

/**
 * JE_drawShield / JE_drawArmor: the C draws one 2-pixel row per point (JE_dBar3), so a full armor
 * of 28 (JE_drawArmor's cap) fills 28 rows whatever the ship; the gauges here keep that absolute
 * scale. Rows lit for a value, 0..GAUGE_ROWS.
 */
export function gaugeRows(value: number): number {
  return Math.max(0, Math.min(GAUGE_ROWS, Math.round(value)));
}

/** The generator's power, 0..900: the C's column is power / 10 pixels tall out of 90 (tyrian2.c). */
export const POWER_MAX = 900;
export const POWER_ROWS = 90;
export function powerRows(power: number): number {
  return Math.max(0, Math.min(POWER_ROWS, Math.floor(power / 10)));
}

/** The power read-out at the top of its column: percent of full. */
export function powerPercent(power: number): number {
  return Math.max(0, Math.min(100, Math.round((power / POWER_MAX) * 100)));
}

/** A weapon's power pips: the C draws one per level (tyrian2.c's weapon display), 11 at most. */
export const MAX_PIPS = 11;
export function pipCount(power: number, fitted: boolean): number {
  return fitted ? Math.max(0, Math.min(MAX_PIPS, Math.trunc(power))) : 0;
}

/**
 * A sidekick's ammo gauge (draw_segmented_gauge, vga256d.c): one segment per tenth of the full
 * load, the last one dim while partly spent. Empty when the sidekick has no ammo to run out of.
 */
export function ammoSegments(ammo: number, ammoMax: number): { slots: number; full: number; partial: number } {
  if (ammoMax <= 0) return { slots: 0, full: 0, partial: 0 };
  const per = Math.max(1, Math.floor(ammoMax / 10));
  const slots = Math.ceil(ammoMax / per);
  const a = Math.max(0, Math.min(ammoMax, ammo));
  const full = Math.floor(a / per);
  const rest = a % per;
  return { slots, full, partial: rest > 0 ? rest / per : 0 };
}
