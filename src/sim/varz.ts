// STUB: replaced by the world port
//
// Minimal stand-ins for the varz.c functions and tables the player port calls, so this branch
// builds and its tests run. The world port owns varz.c; at merge, take its varz.ts and drop this
// one (fix any signature drift at the call sites in mainint.ts / shots.ts / newgame.ts).
//
// What's here:
// - The const tables from varz.c L39-155 and hud_sidekick_y (varz.h), copied verbatim.
// - Real ports of the *state* parts of JE_getShipInfo, JE_drawOptions, JE_playerDamage and
//   JE_portConfigs (player tests need them); their HUD drawing is omitted.
// - No-ops for JE_setupExplosion, JE_setupExplosionLarge, JE_doSpecialShot, JE_doSP and the
//   HUD redraws. NOTE: the real JE_doSP calls mt_rand(), so the RNG sequence differs until the
//   world port lands.

import { u8 } from "./cint";
import type { Sprite2Sheet } from "./draw";
import { g, type Player } from "./state";
import { S_EXPLOSION_22, S_HULL_HIT, S_SHIELD_HIT } from "./sndmast";

export const SA = 7;
export const SA_NORTSHIPZ = 7;

export const SASpecialWeapon = [7, 8, 9, 10, 11, 12, 13];
export const SASpecialWeaponB = [37, 6, 15, 40, 16, 14, 41];
export const SAShip = [3, 1, 5, 10, 2, 11, 12];
export const SAWeapon = [
  [9, 31, 32, 33, 34], /* Stealth Ship */
  [19, 8, 22, 41, 34], /* StormWind    */
  [27, 5, 20, 42, 31], /* Techno       */
  [15, 3, 28, 22, 12], /* Enemy        */
  [23, 35, 25, 14, 6], /* Weird        */
  [2, 5, 21, 4, 7], /* Unknown      */
  [40, 38, 37, 41, 36], /* NortShip Z   */
];
export const specialArcadeWeapon = [
  17, 17, 18, 0, 0, 0, 10, 0, 0, 0, 0, 0, 44, 0, 10, 0, 19, 0, 0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 45, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
];
/** optionSelect[16][3][2] */
export const optionSelect = [
  [[0, 0], [0, 0], [0, 0]],
  [[1, 1], [16, 16], [30, 30]], /*Single Shot*/
  [[2, 2], [29, 29], [29, 20]], /*Dual Shot*/
  [[3, 3], [21, 21], [12, 0]], /*Charge Cannon*/
  [[4, 4], [18, 18], [16, 23]], /*Vulcan*/
  [[0, 0], [0, 0], [0, 0]],
  [[6, 6], [29, 16], [0, 22]], /*Super Missile*/
  [[7, 7], [19, 19], [19, 28]], /*Atom Bomb*/
  [[0, 0], [0, 0], [0, 0]],
  [[0, 0], [0, 0], [0, 0]],
  [[10, 10], [21, 21], [21, 27]], /*Mini Missile*/
  [[0, 0], [0, 0], [0, 0]],
  [[0, 0], [0, 0], [0, 0]],
  [[13, 13], [17, 17], [13, 26]], /*MicroBomb*/
  [[0, 0], [0, 0], [0, 0]],
  [[15, 15], [15, 16], [15, 16]], /*Post-It*/
];
export const linkGunWeapons = [
  0, 0, 0, 0, 0, 0, 0, 0, 444, 445, 446, 447, 0, 448, 449, 0, 0, 0, 0, 0, 450, 451, 0, 506, 0, 564,
  445, 446, 447, 448, 449, 445, 446, 447, 448, 449, 450, 451,
];
export const chargeGunWeapons = [
  0, 0, 0, 0, 0, 0, 0, 0, 476, 458, 464, 482, 0, 488, 470, 0, 0, 0, 0, 0, 494, 500, 0, 528, 0, 558,
  458, 458, 458, 458, 458, 458, 458, 458, 458, 458, 458, 458,
];
/** keyboardCombos[26][8] (twiddles) */
export const keyboardCombos = [
  [2, 1, 2, 5, 137, 0, 0, 0], /*Invulnerability*/
  [4, 3, 2, 5, 138, 0, 0, 0], /*Atom Bomb*/
  [3, 4, 6, 139, 0, 0, 0, 0], /*Seeker Bombs*/
  [2, 5, 142, 0, 0, 0, 0, 0], /*Ice Blast*/
  [6, 2, 6, 143, 0, 0, 0, 0], /*Auto Repair*/
  [6, 7, 5, 8, 6, 7, 5, 112], /*Spin Wave*/
  [7, 8, 101, 0, 0, 0, 0, 0], /*Repulsor*/
  [1, 7, 6, 146, 0, 0, 0, 0], /*Protron Field*/
  [8, 6, 7, 1, 120, 0, 0, 0], /*Minefield*/
  [3, 6, 8, 5, 121, 0, 0, 0], /*Post-It Blast*/
  [1, 2, 7, 8, 119, 0, 0, 0], /*Drone Ship - TBC*/
  [3, 4, 3, 6, 123, 0, 0, 0], /*Repair Player 2*/
  [6, 7, 5, 8, 124, 0, 0, 0], /*Super Bomb - TBC*/
  [1, 6, 125, 0, 0, 0, 0, 0], /*Hot Dog*/
  [9, 5, 126, 0, 0, 0, 0, 0], /*Lightning UP      */
  [1, 7, 127, 0, 0, 0, 0, 0], /*Lightning UP+LEFT */
  [1, 8, 128, 0, 0, 0, 0, 0], /*Lightning UP+RIGHT*/
  [9, 7, 129, 0, 0, 0, 0, 0], /*Lightning    LEFT */
  [9, 8, 130, 0, 0, 0, 0, 0], /*Lightning    RIGHT*/
  [4, 2, 3, 5, 131, 0, 0, 0], /*Warfly            */
  [3, 1, 2, 8, 132, 0, 0, 0], /*FrontBlaster      */
  [2, 4, 5, 133, 0, 0, 0, 0], /*Gerund            */
  [3, 4, 2, 8, 134, 0, 0, 0], /*FireBomb          */
  [1, 4, 6, 135, 0, 0, 0, 0], /*Indigo            */
  [1, 3, 6, 137, 0, 0, 0, 0], /*Invulnerability [easier] */
  [1, 4, 3, 4, 7, 136, 0, 0], /*D-Media Protron Drone    */
];
export const shipCombosB = [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 7, 8, 5, 25, 14, 4, 6, 3, 9, 2, 26];
/** shipCombos[14][3] */
export const shipCombos = [
  [5, 4, 7], /*2nd Player ship*/
  [1, 2, 0], /*USP Talon*/
  [14, 4, 0], /*Super Carrot*/
  [4, 5, 0], /*Gencore Phoenix*/
  [6, 5, 0], /*Gencore Maelstrom*/
  [7, 8, 0], /*MicroCorp Stalker*/
  [7, 9, 0], /*MicroCorp Stalker-B*/
  [10, 3, 5], /*Prototype Stalker-C*/
  [5, 8, 9], /*Stalker*/
  [1, 3, 0], /*USP Fang*/
  [7, 16, 17], /*U-Ship*/
  [2, 11, 12], /*1st Player ship*/
  [3, 8, 10], /*Nort ship*/
  [0, 0, 0], // Dummy entry added for Stalker 21.126
];

/** varz.c: const uint shadowYDist = 10; */
export const shadowYDist = 10;

/** varz.h hud_sidekick_y[2][2] */
export const hud_sidekick_y = [
  [64, 82], // one player HUD
  [108, 126], // two player HUD
];

/**
 * JE_getShipInfo (varz.c L315-368), minus the extra (custom, ship > 90) ships: their data
 * (extraShips from the editship file) isn't loaded, so they're treated like normal ships.
 */
export function JE_getShipInfo(): void {
  const { ships, powerSys } = g.res.items;
  const player = g.player;

  g.shipGrPtr = g.res.spriteSheet9;
  g.shipGr2ptr = g.res.spriteSheet9;

  g.powerAdd = powerSys[player[0].items.generator].power;

  g.shipGr = ships[player[0].items.ship].shipGraphic;
  player[0].armor = ships[player[0].items.ship].dmg;

  g.shipGr2 = 0;
  player[1].armor = 10;

  for (let i = 0; i < player.length; ++i) {
    player[i].initial_armor = player[i].armor;

    const temp = ships[player[i].items.ship].ani;

    if (temp === 0) {
      player[i].shot_hit_area_x = 12;
      player[i].shot_hit_area_y = 10;
    } else {
      player[i].shot_hit_area_x = 11;
      player[i].shot_hit_area_y = 14;
    }
  }
}

/** JE_SGr (varz.c L370-382): extra ships aren't supported; returns the first GR entry. */
export function JE_SGr(_ship: number, _ptr: { value: Sprite2Sheet | null }): number {
  return 233;
}

/** JE_drawOptions (varz.c L384-421), state only (the sidekick HUD isn't drawn). */
export function JE_drawOptions(): void {
  const this_player = g.player[g.twoPlayerMode ? 1 : 0];

  for (let i = 0; i < this_player.sidekick.length; ++i) {
    const this_option = g.res.items.options[this_player.items.sidekick[i]];

    this_player.sidekick[i].ammo = this_player.sidekick[i].ammo_max = this_option.ammo;

    this_player.sidekick[i].ammo_refill_ticks = this_player.sidekick[i].ammo_refill_ticks_max =
      (105 - this_player.sidekick[i].ammo) * 4;

    this_player.sidekick[i].style = this_option.tr;

    this_player.sidekick[i].animation_enabled = this_option.option === 1;
    this_player.sidekick[i].animation_frame = 0;

    this_player.sidekick[i].charge = 0;
    this_player.sidekick[i].charge_ticks = 20;
  }

  JE_drawOptionLevel();
}

/** JE_drawOptionLevel: HUD only. */
export function JE_drawOptionLevel(): void {}

/** JE_doSpecialShot (varz.c L644-834). The C passes &this_player->armor, &this_player->shield. NO-OP STUB. */
export function JE_doSpecialShot(_playerNum: number, _this_player: Player): void {}

/** JE_wipeShieldArmorBars / JE_drawShield / JE_drawArmor: HUD only. */
export function JE_wipeShieldArmorBars(): void {}
export function JE_drawShield(): void {}
export function JE_drawArmor(): void {}

/** JE_playerDamage (varz.c L1002-1065), minus the HUD redraw and music volume. */
export function JE_playerDamage(temp: number, this_player: Player): number {
  temp = u8(temp);
  let playerDamage = 0;
  g.soundQueue[7] = S_SHIELD_HIT;

  /* Player Damage Routines */
  if (this_player.shield < temp) {
    playerDamage = temp;
    temp = u8(temp - this_player.shield);
    this_player.shield = 0;

    if (temp > 0) {
      /*Through Shields - Now Armor */

      if (this_player.armor < temp) {
        temp = u8(temp - this_player.armor);
        this_player.armor = 0;

        if (this_player.is_alive && !g.youAreCheating) {
          g.levelTimer = false;
          this_player.is_alive = false;
          this_player.exploding_ticks = 60;
          g.levelEnd = 40;
          // tempVolume = tyrMusicVolume; (music)
          g.soundQueue[1] = S_EXPLOSION_22;
        }
      } else {
        this_player.armor -= temp;
        g.soundQueue[7] = S_HULL_HIT;
      }
    }
  } else {
    this_player.shield -= temp;

    const f = !g.twoPlayerMode;
    JE_setupExplosion(this_player.x - 17, this_player.y - 12, 0, 14, false, f);
    JE_setupExplosion(this_player.x - 5, this_player.y - 12, 0, 15, false, f);
    JE_setupExplosion(this_player.x + 7, this_player.y - 12, 0, 16, false, f);
    JE_setupExplosion(this_player.x + 19, this_player.y - 12, 0, 17, false, f);

    JE_setupExplosion(this_player.x - 17, this_player.y + 2, 0, 18, false, f);
    JE_setupExplosion(this_player.x + 19, this_player.y + 2, 0, 19, false, f);

    JE_setupExplosion(this_player.x - 17, this_player.y + 16, 0, 20, false, f);
    JE_setupExplosion(this_player.x - 5, this_player.y + 16, 0, 21, false, f);
    JE_setupExplosion(this_player.x + 7, this_player.y + 16, 0, 22, false, f);
  }

  JE_wipeShieldArmorBars();
  JE_drawShield();
  JE_drawArmor();

  return playerDamage;
}

/** JE_setupExplosion (varz.c L836-929). NO-OP STUB. */
export function JE_setupExplosion(
  _x: number, _y: number, _deltaY: number, _type: number, _fixedPosition: boolean, _followPlayer: boolean,
): void {}

/** JE_setupExplosionLarge (varz.c L931-978). NO-OP STUB. */
export function JE_setupExplosionLarge(_enemyGround: boolean, _exploNum: number, _x: number, _y: number): void {}

/** JE_portConfigs (varz.c L1067-1071). The C also leaves the result in the scratch global tempW. */
export function JE_portConfigs(): number {
  const player_index = g.twoPlayerMode ? 1 : 0;
  return g.res.items.weaponPorts[g.player[player_index].items.weapon[1].id].opNum;
}

/** JE_doSP (varz.c L1108-1125): superpixels. NO-OP STUB (the real one calls mt_rand). */
export function JE_doSP(_x: number, _y: number, _num: number, _explowidth: number, _color: number): void {}
