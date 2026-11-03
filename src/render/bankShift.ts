// How far a player ship's banking frame sits sideways from its level frame, so the model can
// follow it (DECISIONS.md D62).
//
// The models are built from the level (unbanked) frame and rolled for the banking frames. Rolling
// leaves a model centred, but the original's banking frames are not: the USP Talon's hard-left
// frame covers columns 2-15 of its 24-pixel cell and its hard-right frame columns 8-21, three
// pixels either side of the level frame's 3-20. Holding against a side of the playfield banks the
// ship fully, so without the shift the model stopped three pixels further from the edge than the
// original's sprite did (mainint.c L3857-3865 clamps x to 40..256; the sprite is drawn at x - 5,
// and the window starts at game_screen x 24).

import { composeSprite2x2 } from "./spriteMesh";

/** The middle of a 2x2 sprite's opaque columns, in pixels from its left edge; NaN if it's empty. */
export function visibleCentreX(sheet: Uint8Array, index: number): number {
  const { width, height, pixels } = composeSprite2x2(sheet, index);
  let lo = width;
  let hi = -1;
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (pixels[y * width + x] < 0) continue;
      if (x < lo) lo = x;
      if (x > hi) hi = x;
    }
  }
  return hi < 0 ? Number.NaN : (lo + hi + 1) / 2;
}

const cache = new Map<string, number>();

/**
 * Game pixels to move a ship's model sideways when its sprite shows banking frame `index` rather
 * than the level frame `baseIndex` (blit_sprite2x2 frames of one sheet): how far the frame's
 * opaque columns are centred from the level frame's. 0 when either frame is empty.
 */
export function bankShift(sheetId: string, sheet: Uint8Array, baseIndex: number, index: number): number {
  if (index === baseIndex) return 0;
  const key = `${sheetId}|${baseIndex}|${index}`;
  let shift = cache.get(key);
  if (shift === undefined) {
    shift = visibleCentreX(sheet, index) - visibleCentreX(sheet, baseIndex);
    if (!Number.isFinite(shift)) shift = 0;
    cache.set(key, shift);
  }
  return shift;
}
