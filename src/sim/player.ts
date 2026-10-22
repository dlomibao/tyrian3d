// Port of OpenTyrian src/player.c (and the Player helpers from player.h).

import { u8 } from "./cint";
import { FRONT_WEAPON, g, REAR_WEAPON, type Player, type PlayerItems } from "./state";

/** player.c L23-28 */
export function calc_purple_balls_needed(this_player: Player): void {
  const purple_balls_required = [1, 1, 2, 4, 8, 12, 16, 20, 25, 30, 40, 50];

  this_player.purple_balls_needed = purple_balls_required[this_player.lives.value];
}

/** player.c L30-47 */
export function power_up_weapon(this_player: Player, port: number): boolean {
  const can_power_up =
    this_player.items.weapon[port].id !== 0 && // not None
    this_player.items.weapon[port].power < 11; // not at max power
  if (can_power_up) {
    this_player.items.weapon[port].power = u8(this_player.items.weapon[port].power + 1);
    g.shotMultiPos[port] = 0; // TODO: should be part of Player structure

    calc_purple_balls_needed(this_player);
  } // cash consolation prize
  else {
    this_player.cash += 1000;
  }

  return can_power_up;
}

/** player.c L49-55 */
export function handle_got_purple_ball(this_player: Player): void {
  if (this_player.purple_balls_needed > 1) --this_player.purple_balls_needed;
  else power_up_weapon(this_player, this_player.is_dragonwing ? REAR_WEAPON : FRONT_WEAPON);
}

// --- C struct semantics the port needs ---

/**
 * `this_player->lives = &this_player->items.weapon[weapon_index].power` (JE_initPlayerData): lives
 * is a pointer into the player's items, so it aliases the weapon power. The accessor re-reads
 * `items` each time, so it survives struct assignments to `items`.
 */
export function point_lives_at_weapon_power(this_player: Player, weapon_index: number): void {
  this_player.lives = {
    get value() {
      return this_player.items.weapon[weapon_index].power;
    },
    set value(v: number) {
      this_player.items.weapon[weapon_index].power = u8(v);
    },
  };
}

/** C struct copy of PlayerItems (`a = b`). */
export function copyPlayerItems(src: PlayerItems): PlayerItems {
  return {
    ...src,
    weapon: src.weapon.map((w) => ({ id: w.id, power: w.power })),
    sidekick: [...src.sidekick],
  };
}
