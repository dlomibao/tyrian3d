// STUB: replaced by the player port.
// Only the signatures the world port (varz.ts) calls, so it typechecks on its own branch.

import { MAX_PWEAPON } from "./state";

/** player_shot_create (shots.c). Returns the shot slot, or MAX_PWEAPON if none was created. */
export function player_shot_create(
  _portnum: number,
  _shot_i: number,
  _px: number,
  _py: number,
  _mousex: number,
  _mousey: number,
  _wpnum: number,
  _playernum: number,
): number {
  return MAX_PWEAPON;
}
