// The playfield in Tyrian pixel coordinates, and how it maps onto the 3D world.
//
// Game logic works in the original's pixel space (x right, y down) so ported code keeps its
// numbers. Rendering maps that onto the world's XZ plane: Three.js is Y-up, "forward" (up the
// screen) is -Z, and one world unit is PX_PER_UNIT Tyrian pixels. Nothing here depends on the
// display resolution.

/** Visible playfield in Tyrian pixels (src/backgrnd.c draws 264x184). */
export const PLAYFIELD_W = 264;
export const PLAYFIELD_H = 184;

/** Player position limits (src/mainint.c). */
export const PLAYER_MIN_X = 40;
export const PLAYER_MAX_X = 256;
export const PLAYER_MIN_Y = 10;
export const PLAYER_MAX_Y = 160;

/** Tyrian pixels per world unit. A ~24 px ship is about 2 units long. */
export const PX_PER_UNIT = 12;

export const PLAYFIELD_WORLD_W = PLAYFIELD_W / PX_PER_UNIT;
export const PLAYFIELD_WORLD_D = PLAYFIELD_H / PX_PER_UNIT;

/** Tyrian pixel x to world X (playfield centred on the origin). */
export function worldX(px: number): number {
  return (px - PLAYFIELD_W / 2) / PX_PER_UNIT;
}

/** Tyrian pixel y to world Z (down the screen is toward the camera, +Z). */
export function worldZ(py: number): number {
  return (py - PLAYFIELD_H / 2) / PX_PER_UNIT;
}

/**
 * Where the playfield is in the draw list's coordinates (OpenTyrian's game_screen). The game draws
 * into a 320x200 buffer and showNormal (src/backgrnd.c) copies its 264x184 window at (24, 0) to
 * the top-left of the screen; the HUD fills the rest of the real screen. Tiles and sprites are
 * drawn beyond the window so the edges never need clipping.
 */
export const PLAYFIELD_SCREEN_X = 24;
export const PLAYFIELD_SCREEN_Y = 0;

/** Draw-list (game_screen) x to world X. */
export function screenWorldX(x: number): number {
  return worldX(x - PLAYFIELD_SCREEN_X);
}

/** Draw-list (game_screen) y to world Z. */
export function screenWorldZ(y: number): number {
  return worldZ(y - PLAYFIELD_SCREEN_Y);
}
