// Port of OpenTyrian src/varz.c: explosions, superpixels, player damage, ship info and the special
// weapon handler. The variables varz.h declares live on `g` (state.ts); the constant tables are here.
//
// HUD drawing (JE_drawShield, JE_drawArmor, JE_wipeShieldArmorBars, the sidekick HUD in
// JE_drawOptions, JE_drawOptionLevel) is a no-op: the HUD is HTML and reads the state.

import { s8, s16, u8, u16, u32 } from "./cint";
import { roundf } from "./cfloat";
import { blit_sprite2, drawPixel, type Sprite2Sheet } from "./draw";
import { mt_rand, mt_rand_1, mt_rand_lt1 } from "./mtrand";
import { player_shot_create } from "./shots";
import { JE_barBright } from "./smoothies";
import { S_EXPLOSION_22, S_HULL_HIT, S_POWERUP, S_SHIELD_HIT, S_SOUL_OF_ZINGLON } from "./sndmast";
import {
  FRONT_WEAPON,
  LEFT_SIDEKICK,
  MAX_EXPLOSIONS,
  MAX_PWEAPON,
  MAX_REPEATING_EXPLOSIONS,
  MAX_SUPERPIXELS,
  REAR_WEAPON,
  RIGHT_SIDEKICK,
  SA,
  SA_NONE,
  SHOT_SPECIAL,
  SHOT_SPECIAL2,
  g,
  type Player,
} from "./state";

// --- Constant tables (varz.c L41-167) ---

export const SANextShip = [3, 9, 6, 2, 5, 1, 4, 3, 7] as const;
export const SASpecialWeapon = [7, 8, 9, 10, 11, 12, 13] as const;
export const SASpecialWeaponB = [37, 6, 15, 40, 16, 14, 41] as const;
export const SAShip = [3, 1, 5, 10, 2, 11, 12] as const;
export const SAWeapon: readonly (readonly number[])[] = [
  /*  R  Bl  Bk  G   P */
  [9, 31, 32, 33, 34] /* Stealth Ship */,
  [19, 8, 22, 41, 34] /* StormWind    */,
  [27, 5, 20, 42, 31] /* Techno       */,
  [15, 3, 28, 22, 12] /* Enemy        */,
  [23, 35, 25, 14, 6] /* Weird        */,
  [2, 5, 21, 4, 7] /* Unknown      */,
  [40, 38, 37, 41, 36] /* NortShip Z   */,
];

export const specialArcadeWeapon = [
  17, 17, 18, 0, 0, 0, 10, 0, 0, 0, 0, 0, 44, 0, 10, 0, 19, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 45, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0,
] as const;

/** optionSelect[16][3][2]: MAIN, OPT, FRONT. */
export const optionSelect: readonly (readonly (readonly number[])[])[] = [
  [[0, 0], [0, 0], [0, 0]],
  [[1, 1], [16, 16], [30, 30]] /*Single Shot*/,
  [[2, 2], [29, 29], [29, 20]] /*Dual Shot*/,
  [[3, 3], [21, 21], [12, 0]] /*Charge Cannon*/,
  [[4, 4], [18, 18], [16, 23]] /*Vulcan*/,
  [[0, 0], [0, 0], [0, 0]],
  [[6, 6], [29, 16], [0, 22]] /*Super Missile*/,
  [[7, 7], [19, 19], [19, 28]] /*Atom Bomb*/,
  [[0, 0], [0, 0], [0, 0]],
  [[0, 0], [0, 0], [0, 0]],
  [[10, 10], [21, 21], [21, 27]] /*Mini Missile*/,
  [[0, 0], [0, 0], [0, 0]],
  [[0, 0], [0, 0], [0, 0]],
  [[13, 13], [17, 17], [13, 26]] /*MicroBomb*/,
  [[0, 0], [0, 0], [0, 0]],
  [[15, 15], [15, 16], [15, 16]] /*Post-It*/,
];

export const PGR = [
  4, 1, 2, 3, 41 - 21, 57 - 21, 73 - 21, 89 - 21, 105 - 21, 121 - 21, 137 - 21, 153 - 21, 151, 151, 151, 151,
  73 - 21, 73 - 21, 1, 2, 4,
] as const;
export const PAni = [1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1] as const;

export const linkGunWeapons = [
  0, 0, 0, 0, 0, 0, 0, 0, 444, 445, 446, 447, 0, 448, 449, 0, 0, 0, 0, 0, 450, 451, 0, 506, 0, 564, 445, 446, 447,
  448, 449, 445, 446, 447, 448, 449, 450, 451,
] as const;
export const chargeGunWeapons = [
  0, 0, 0, 0, 0, 0, 0, 0, 476, 458, 464, 482, 0, 488, 470, 0, 0, 0, 0, 0, 494, 500, 0, 528, 0, 558, 458, 458, 458,
  458, 458, 458, 458, 458, 458, 458, 458, 458,
] as const;
export const randomEnemyLaunchSounds = [13, 6, 26] as const;

/* Twiddle cheat sheet: 1 UP, 2 DOWN, 3 LEFT, 4 RIGHT, 5 UP+FIRE, 6 DOWN+FIRE, 7 LEFT+FIRE,
 * 8 RIGHT+FIRE, 9 release all keys. */
export const keyboardCombos: readonly (readonly number[])[] = [
  [2, 1, 2, 5, 137, 0, 0, 0] /*Invulnerability*/,
  [4, 3, 2, 5, 138, 0, 0, 0] /*Atom Bomb*/,
  [3, 4, 6, 139, 0, 0, 0, 0] /*Seeker Bombs*/,
  [2, 5, 142, 0, 0, 0, 0, 0] /*Ice Blast*/,
  [6, 2, 6, 143, 0, 0, 0, 0] /*Auto Repair*/,
  [6, 7, 5, 8, 6, 7, 5, 112] /*Spin Wave*/,
  [7, 8, 101, 0, 0, 0, 0, 0] /*Repulsor*/,
  [1, 7, 6, 146, 0, 0, 0, 0] /*Protron Field*/,
  [8, 6, 7, 1, 120, 0, 0, 0] /*Minefield*/,
  [3, 6, 8, 5, 121, 0, 0, 0] /*Post-It Blast*/,
  [1, 2, 7, 8, 119, 0, 0, 0] /*Drone Ship - TBC*/,
  [3, 4, 3, 6, 123, 0, 0, 0] /*Repair Player 2*/,
  [6, 7, 5, 8, 124, 0, 0, 0] /*Super Bomb - TBC*/,
  [1, 6, 125, 0, 0, 0, 0, 0] /*Hot Dog*/,
  [9, 5, 126, 0, 0, 0, 0, 0] /*Lightning UP      */,
  [1, 7, 127, 0, 0, 0, 0, 0] /*Lightning UP+LEFT */,
  [1, 8, 128, 0, 0, 0, 0, 0] /*Lightning UP+RIGHT*/,
  [9, 7, 129, 0, 0, 0, 0, 0] /*Lightning    LEFT */,
  [9, 8, 130, 0, 0, 0, 0, 0] /*Lightning    RIGHT*/,
  [4, 2, 3, 5, 131, 0, 0, 0] /*Warfly            */,
  [3, 1, 2, 8, 132, 0, 0, 0] /*FrontBlaster      */,
  [2, 4, 5, 133, 0, 0, 0, 0] /*Gerund            */,
  [3, 4, 2, 8, 134, 0, 0, 0] /*FireBomb          */,
  [1, 4, 6, 135, 0, 0, 0, 0] /*Indigo            */,
  [1, 3, 6, 137, 0, 0, 0, 0] /*Invulnerability [easier] */,
  [1, 4, 3, 4, 7, 136, 0, 0] /*D-Media Protron Drone    */,
];

export const shipCombosB = [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 7, 8, 5, 25, 14, 4, 6, 3, 9, 2, 26] as const;
/*!! SUPER Tyrian !!*/
export const superTyrianSpecials = [1, 2, 4, 5] as const;

export const shipCombos: readonly (readonly number[])[] = [
  [5, 4, 7] /*2nd Player ship*/,
  [1, 2, 0] /*USP Talon*/,
  [14, 4, 0] /*Super Carrot*/,
  [4, 5, 0] /*Gencore Phoenix*/,
  [6, 5, 0] /*Gencore Maelstrom*/,
  [7, 8, 0] /*MicroCorp Stalker*/,
  [7, 9, 0] /*MicroCorp Stalker-B*/,
  [10, 3, 5] /*Prototype Stalker-C*/,
  [5, 8, 9] /*Stalker*/,
  [1, 3, 0] /*USP Fang*/,
  [7, 16, 17] /*U-Ship*/,
  [2, 11, 12] /*1st Player ship*/,
  [3, 8, 10] /*Nort ship*/,
  [0, 0, 0], // Dummy entry added for Stalker 21.126
];

/** shadowYDist (varz.c L274) */
export const shadowYDist = 10;

/** hud_sidekick_y (varz.h): sidekick HUD rows for the one- and two-player HUD. */
export const hud_sidekick_y = [
  [64, 82], // one player HUD
  [108, 126], // two player HUD
] as const;

// varz.c's scratch globals (temp, temp2, tempW, b). In C they're shared by every file, but
// JE_doSpecialShot -> JE_specialComplete is the only place where a value crosses functions
// (temp2: the special's power), and both are in this module.
let temp = 0;
let temp2 = 0;
let b = 0;

/** A `Sprite2_array *` out-parameter (JE_SGr's `ptr`). */
export interface SheetRef {
  value: Sprite2Sheet | null;
}

/** JE_getShipInfo (varz.c L315-368) */
export function JE_getShipInfo(): void {
  const { items } = g.res;

  const shipGrPtr: SheetRef = { value: g.res.spriteSheet9 };
  const shipGr2ptr: SheetRef = { value: g.res.spriteSheet9 };

  g.powerAdd = items.powerSys[g.player[0].items.generator].power;

  const extraShip = g.player[0].items.ship > 90;
  if (extraShip) {
    const base = u8((g.player[0].items.ship - 91) * 15);
    g.shipGr = JE_SGr(g.player[0].items.ship - 90, shipGrPtr);
    g.player[0].armor = g.extraShips[base + 7];
  } else {
    g.shipGr = items.ships[g.player[0].items.ship].shipGraphic;
    g.player[0].armor = items.ships[g.player[0].items.ship].dmg;
  }

  const extraShip2 = g.player[1].items.ship > 90;
  if (extraShip2) {
    const base2 = u8((g.player[1].items.ship - 91) * 15);
    g.shipGr2 = JE_SGr(g.player[1].items.ship - 90, shipGr2ptr);
    g.player[1].armor = g.extraShips[base2 + 7]; /* bug? */
  } else {
    g.shipGr2 = 0;
    g.player[1].armor = 10;
  }

  g.shipGrPtr = shipGrPtr.value;
  g.shipGr2ptr = shipGr2ptr.value;

  for (let i = 0; i < g.player.length; ++i) {
    g.player[i].initial_armor = g.player[i].armor;

    const temp = (i === 0 && extraShip) || (i === 1 && extraShip2) ? 2 : items.ships[g.player[i].items.ship].ani;

    if (temp === 0) {
      g.player[i].shot_hit_area_x = 12;
      g.player[i].shot_hit_area_y = 10;
    } else {
      g.player[i].shot_hit_area_x = 11;
      g.player[i].shot_hit_area_y = 14;
    }
  }
}

/** JE_SGr (varz.c L370-382): the ship editor's ship graphics. */
export function JE_SGr(ship: number, ptr: SheetRef): number {
  const GR = [233, 157, 195, 271, 81, 0, 119, 5, 43, 81, 119, 157, 195, 233, 271];

  const tempW = g.extraShips[(ship - 1) * 15];
  if (tempW > 7) ptr.value = g.extraShapes;

  return GR[tempW - 1];
}

/** JE_drawOptions (varz.c L384-421): resets the sidekicks' state. The sidekick HUD is HTML. */
export function JE_drawOptions(): void {
  const this_player = g.player[g.twoPlayerMode ? 1 : 0];

  for (let i = 0; i < this_player.sidekick.length; ++i) {
    const this_option = g.res.items.options[this_player.items.sidekick[i]];
    const sk = this_player.sidekick[i];

    sk.ammo = sk.ammo_max = this_option.ammo;

    sk.ammo_refill_ticks = sk.ammo_refill_ticks_max = u32((105 - sk.ammo) * 4);

    sk.style = this_option.tr;

    sk.animation_enabled = this_option.option === 1;
    sk.animation_frame = 0;

    sk.charge = 0;
    sk.charge_ticks = 20;

    // draw initial sidekick HUD: no-op (HTML HUD)
  }

  JE_drawOptionLevel();
}

/** JE_drawOptionLevel (varz.c L423-432): HUD only, a no-op. */
export function JE_drawOptionLevel(): void {}

/** JE_specialComplete (varz.c L469-642) */
export function JE_specialComplete(playerNum: number, specialType: number): void {
  const special = g.res.items.specials;
  const sp = special[specialType];

  g.nextSpecialWait = 0;
  switch (sp.sType) {
    /*Weapon*/
    case 1:
      if (playerNum === 1)
        b = player_shot_create(0, SHOT_SPECIAL2, g.player[0].x, g.player[0].y, g.player[0].mouseX, g.player[0].mouseY, sp.wpn, playerNum);
      else
        b = player_shot_create(0, SHOT_SPECIAL2, g.player[1].x, g.player[1].y, g.player[0].mouseX, g.player[0].mouseY, sp.wpn, playerNum);

      g.shotRepeat[SHOT_SPECIAL] = g.shotRepeat[SHOT_SPECIAL2];
      break;
    /*Repulsor*/
    case 2:
      for (temp = 0; temp < g.enemyShot.length; temp++) {
        if (!g.enemyShotAvail[temp]) {
          const s = g.enemyShot[temp];
          if (g.player[0].x > s.sx) s.sxm = s16(s.sxm - 1);
          else if (g.player[0].x < s.sx) s.sxm = s16(s.sxm + 1);

          if (g.player[0].y > s.sy) s.sym = s16(s.sym - 1);
          else if (g.player[0].y < s.sy) s.sym = s16(s.sym + 1);
        }
      }
      break;
    /*Zinglon Blast*/
    case 3:
      g.zinglonDuration = 50;
      g.shotRepeat[SHOT_SPECIAL] = 100;
      g.soundQueue[7] = S_SOUL_OF_ZINGLON;
      break;
    /*Attractor*/
    case 4:
      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (g.enemyAvail[temp] !== 1 && e.scoreitem && e.evalue !== 0) {
          if (g.player[0].x > e.ex) e.exc = s8(e.exc + 1);
          else if (g.player[0].x < e.ex) e.exc = s8(e.exc - 1);

          if (g.player[0].y > e.ey) e.eyc = s8(e.eyc + 1);
          else if (g.player[0].y < e.ey) e.eyc = s8(e.eyc - 1);
        }
      }
      break;
    /*Flare*/
    case 5:
    case 6:
    case 7:
    case 8:
    case 9:
    case 10:
    case 11:
    case 16: {
      if (g.flareDuration === 0) g.flareStart = true;

      g.specialWeaponWpn = sp.wpn;
      g.linkToPlayer = false;
      g.spraySpecial = false;
      const power = g.player[0].items.weapon[FRONT_WEAPON].power;
      switch (sp.sType) {
        case 5:
          g.specialWeaponFilter = 7;
          g.specialWeaponFreq = 2;
          g.flareDuration = 50;
          break;
        case 6:
          g.specialWeaponFilter = 1;
          g.specialWeaponFreq = 7;
          g.flareDuration = u16(200 + 25 * power);
          break;
        case 7:
          g.specialWeaponFilter = 3;
          g.specialWeaponFreq = 3;
          g.flareDuration = u16(50 + 10 * power);
          g.zinglonDuration = 50;
          g.shotRepeat[SHOT_SPECIAL] = 100;
          g.soundQueue[7] = S_SOUL_OF_ZINGLON;
          break;
        case 8:
          g.specialWeaponFilter = -99;
          g.specialWeaponFreq = 7;
          g.flareDuration = u16(10 + power);
          break;
        case 9:
          g.specialWeaponFilter = -99;
          g.specialWeaponFreq = 8;
          g.flareDuration = u16(8 + 2 * power);
          g.linkToPlayer = true;
          g.nextSpecialWait = u8(sp.pwr);
          break;
        case 10:
          g.specialWeaponFilter = -99;
          g.specialWeaponFreq = 8;
          g.flareDuration = u16(14 + 4 * power);
          g.linkToPlayer = true;
          break;
        case 11:
          g.specialWeaponFilter = -99;
          g.specialWeaponFreq = s8(sp.pwr);
          g.flareDuration = u16(10 + 10 * power);
          g.astralDuration = u8(20 + 10 * power);
          break;
        case 16:
          g.specialWeaponFilter = -99;
          g.specialWeaponFreq = 8;
          g.flareDuration = u16(temp2 * 16 + 8);
          g.linkToPlayer = true;
          g.spraySpecial = true;
          break;
      }
      break;
    }
    case 12: // Invulnerability
      g.player[playerNum - 1].invulnerable_ticks = temp2 * 10;

      if (g.superArcadeMode > 0 && g.superArcadeMode <= SA) {
        g.shotRepeat[SHOT_SPECIAL] = 250;
        b = player_shot_create(0, SHOT_SPECIAL2, g.player[0].x, g.player[0].y, g.player[0].mouseX, g.player[0].mouseY, 707, 1);
        g.player[0].invulnerable_ticks = 100;
      }
      break;
    case 13: // Repair Player 1
      g.player[0].armor = u32(g.player[0].armor + Math.trunc(temp2 / 4) + 1);

      g.soundQueue[3] = S_POWERUP;
      break;
    case 14: // Repair Player 2
      g.player[1].armor = u32(g.player[1].armor + Math.trunc(temp2 / 4) + 1);

      g.soundQueue[3] = S_POWERUP;
      break;

    case 17: // Spawn left or right sidekick
      g.soundQueue[3] = S_POWERUP;

      if (g.player[0].items.sidekick[LEFT_SIDEKICK] === sp.wpn) {
        g.player[0].items.sidekick[RIGHT_SIDEKICK] = u8(sp.wpn);
        g.shotMultiPos[RIGHT_SIDEKICK] = 0;
      } else {
        g.player[0].items.sidekick[LEFT_SIDEKICK] = u8(sp.wpn);
        g.shotMultiPos[LEFT_SIDEKICK] = 0;
      }

      JE_drawOptions();
      break;

    case 18: // Spawn right sidekick
      g.player[0].items.sidekick[RIGHT_SIDEKICK] = u8(sp.wpn);

      JE_drawOptions();

      g.soundQueue[4] = S_POWERUP;

      g.shotMultiPos[RIGHT_SIDEKICK] = 0;
      break;
  }
}

/**
 * JE_doSpecialShot (varz.c L644-834). The C takes `uint *armor, uint *shield`, which every caller
 * points at this_player->armor and ->shield; here the caller passes this_player instead.
 */
export function JE_doSpecialShot(playerNum: number, this_player: Player): void {
  const special = g.res.items.specials;

  if (g.player[0].items.special > 0) {
    if (g.shotRepeat[SHOT_SPECIAL] === 0 && g.specialWait === 0 && g.flareDuration < 2 && g.zinglonDuration < 2)
      blit_sprite2(47, 4, g.res.spriteSheet9, 94);
    else blit_sprite2(47, 4, g.res.spriteSheet9, 93);
  }

  if (g.shotRepeat[SHOT_SPECIAL] > 0) {
    --g.shotRepeat[SHOT_SPECIAL];
  }
  if (g.specialWait > 0) {
    g.specialWait--;
  }
  temp = g.SFExecuted[playerNum - 1];
  if (temp > 0 && g.shotRepeat[SHOT_SPECIAL] === 0 && g.flareDuration === 0) {
    temp2 = u8(special[temp].pwr);

    let can_afford = true;

    if (temp2 > 0) {
      if (temp2 < 98) {
        // costs some shield
        if (this_player.shield >= temp2) this_player.shield = u32(this_player.shield - temp2);
        else can_afford = false;
      } else if (temp2 === 98) {
        // costs all shield
        if (this_player.shield < 4) can_afford = false;
        temp2 = u8(this_player.shield);
        this_player.shield = 0;
      } else if (temp2 === 99) {
        // costs half shield
        temp2 = u8(Math.trunc(this_player.shield / 2));
        this_player.shield = temp2;
      } else {
        // costs some armor
        temp2 = u8(temp2 - 100);
        if (this_player.armor > temp2) this_player.armor = u32(this_player.armor - temp2);
        else can_afford = false;
      }
    }

    g.shotMultiPos[SHOT_SPECIAL] = 0;
    g.shotMultiPos[SHOT_SPECIAL2] = 0;

    if (can_afford) JE_specialComplete(playerNum, temp);

    g.SFExecuted[playerNum - 1] = 0;

    JE_wipeShieldArmorBars();
    JE_drawShield();
    JE_drawArmor();
  }

  if (playerNum === 1 && g.player[0].items.special > 0) {
    /*Main Begin*/

    if (g.superArcadeMode > 0 && (g.button[2 - 1] || g.button[3 - 1])) {
      g.fireButtonHeld = false;
    }
    if (!g.button[1 - 1] && !(g.superArcadeMode !== SA_NONE && (g.button[2 - 1] || g.button[3 - 1]))) {
      g.fireButtonHeld = false;
    } else if (g.shotRepeat[SHOT_SPECIAL] === 0 && !g.fireButtonHeld && !(g.flareDuration > 0) && g.specialWait === 0) {
      g.fireButtonHeld = true;
      JE_specialComplete(playerNum, g.player[0].items.special);
    }
  } /*Main End*/

  if (g.astralDuration > 0) g.astralDuration--;

  g.shotAvail[MAX_PWEAPON - 1] = 0;
  if (g.flareDuration > 1) {
    if (g.specialWeaponFilter !== -99) {
      if (g.levelFilter === -99 && g.levelBrightness === -99) {
        g.filterActive = false;
      }
      if (!g.filterActive) {
        g.levelFilter = g.specialWeaponFilter;
        if (g.levelFilter === 7) {
          g.levelBrightness = 0;
        }
        g.filterActive = true;
      }

      if (mt_rand() % 2 === 0) g.flareColChg = -1;
      else g.flareColChg = 1;

      if (g.levelFilter === 7) {
        if (g.levelBrightness < -6) {
          g.flareColChg = 1;
        }
        if (g.levelBrightness > 6) {
          g.flareColChg = -1;
        }
        g.levelBrightness = s8(g.levelBrightness + g.flareColChg);
      }
    }

    if (mt_rand() % 6 < g.specialWeaponFreq) {
      b = MAX_PWEAPON;

      if (g.linkToPlayer) {
        if (g.shotRepeat[SHOT_SPECIAL] === 0) {
          b = player_shot_create(0, SHOT_SPECIAL, g.player[0].x, g.player[0].y, g.player[0].mouseX, g.player[0].mouseY, g.specialWeaponWpn, playerNum);
        }
      } else {
        // C evaluates mt_rand() % 280 and mt_rand() % 180 as function arguments, in an unspecified
        // order; this assumes left to right.
        const px = mt_rand() % 280;
        const py = mt_rand() % 180;
        b = player_shot_create(0, SHOT_SPECIAL, px, py, g.player[0].mouseX, g.player[0].mouseY, g.specialWeaponWpn, playerNum);
      }

      if (g.spraySpecial && b !== MAX_PWEAPON) {
        g.playerShotData[b].shotXM = s16((mt_rand() % 5) - 2);
        g.playerShotData[b].shotYM = s16((mt_rand() % 5) - 2);
        if (g.playerShotData[b].shotYM === 0) {
          g.playerShotData[b].shotYM++;
        }
      }
    }

    g.flareDuration--;
    if (g.flareDuration === 1) {
      g.specialWait = g.nextSpecialWait;
    }
  } else if (g.flareStart) {
    g.flareStart = false;
    g.shotRepeat[SHOT_SPECIAL] = g.linkToPlayer ? 15 : 200;
    g.flareDuration = 0;
    if (g.levelFilter === g.specialWeaponFilter) {
      g.levelFilter = -99;
      g.levelBrightness = -99;
      g.filterActive = false;
    }
  }

  if (g.zinglonDuration > 1) {
    temp = u8(25 - Math.abs(g.zinglonDuration - 25));

    // The Zinglon beam: recorded for the renderer (src/sim/smoothies.ts).
    JE_barBright(g.player[0].x + 7 - temp, 0, g.player[0].x + 7 + temp, 184);
    JE_barBright(g.player[0].x + 7 - temp - 2, 0, g.player[0].x + 7 + temp + 2, 184);

    g.zinglonDuration--;
    if (g.zinglonDuration % 5 === 0) {
      g.shotAvail[MAX_PWEAPON - 1] = 1;
    }
  }
}

/** explosion_data[53] in JE_setupExplosion (varz.c L844-901): sprite and ttl per type. */
const explosion_data: readonly (readonly [number, number])[] = [
  [144, 7], [120, 12], [190, 12], [209, 12], [152, 12], [171, 12], [133, 7] /*White Smoke*/,
  [1, 12], [20, 12], [39, 12], [58, 12], [110, 3], [76, 7], [91, 3],
  /*15*/ [227, 3], [230, 3], [233, 3], [252, 3], [246, 3],
  /*20*/ [249, 3], [265, 3], [268, 3], [271, 3], [236, 3],
  /*25*/ [239, 3], [242, 3], [261, 3], [274, 3], [277, 3],
  /*30*/ [280, 3], [299, 3], [284, 3], [287, 3], [290, 3],
  /*35*/ [293, 3], [165, 8] /*Coin Values*/, [184, 8], [203, 8], [222, 8],
  [168, 8], [187, 8], [206, 8], [225, 10], [169, 10], [188, 10], [207, 20], [226, 14], [170, 14],
  [189, 14], [208, 14], [246, 14], [227, 14], [265, 14],
];

/** JE_setupExplosion (varz.c L836-929) */
export function JE_setupExplosion(
  x: number,
  y: number,
  deltaY: number,
  type: number,
  fixedPosition: boolean, // true when coin/gem value
  followPlayer: boolean, // true when player shield (1P only)
): void {
  x = s16(x);
  y = s16(y);
  deltaY = s16(deltaY);
  type = s16(type);

  if (y > -16 && y < 190) {
    for (let i = 0; i < MAX_EXPLOSIONS; i++) {
      const ex = g.explosions[i];
      if (ex.ttl === 0) {
        ex.x = x;
        ex.y = y;
        if (type === 6) {
          ex.y = s16(ex.y + 12);
          ex.x = s16(ex.x + 2);
        } else if (type === 98) {
          type = 6;
        }
        ex.sprite = explosion_data[type][0];
        ex.ttl = explosion_data[type][1];
        ex.followPlayer = followPlayer;
        ex.fixedPosition = fixedPosition;
        ex.deltaY = deltaY;
        break;
      }
    }
  }
}

/** JE_setupExplosionLarge (varz.c L931-978) */
export function JE_setupExplosionLarge(enemyGround: boolean, exploNum: number, x: number, y: number): void {
  exploNum = u8(exploNum);
  x = s16(x);
  y = s16(y);

  if (y >= 0) {
    if (enemyGround) {
      JE_setupExplosion(x - 6, y - 14, 0, 2, false, false);
      JE_setupExplosion(x + 6, y - 14, 0, 4, false, false);
      JE_setupExplosion(x - 6, y, 0, 3, false, false);
      JE_setupExplosion(x + 6, y, 0, 5, false, false);
    } else {
      JE_setupExplosion(x - 6, y - 14, 0, 7, false, false);
      JE_setupExplosion(x + 6, y - 14, 0, 9, false, false);
      JE_setupExplosion(x - 6, y, 0, 8, false, false);
      JE_setupExplosion(x + 6, y, 0, 10, false, false);
    }

    let big: boolean;

    if (exploNum > 10) {
      exploNum -= 10;
      big = true;
    } else {
      big = false;
    }

    if (exploNum) {
      for (let i = 0; i < MAX_REPEATING_EXPLOSIONS; i++) {
        const r = g.rep_explosions[i];
        if (r.ttl === 0) {
          // rep_explosion_type's fields are unsigned int.
          r.ttl = exploNum;
          r.delay = 2;
          r.x = u32(x);
          r.y = u32(y);
          r.big = big;
          break;
        }
      }
    }
  }
}

/** JE_wipeShieldArmorBars (varz.c L980-1000): HUD only, a no-op. */
export function JE_wipeShieldArmorBars(): void {}

/** JE_playerDamage (varz.c L1002-1065): returns the damage that got past the shield (JE_byte). */
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
          // tempVolume = tyrMusicVolume: audio, not simulated.
          g.soundQueue[1] = S_EXPLOSION_22;
        }
      } else {
        this_player.armor = u32(this_player.armor - temp);
        g.soundQueue[7] = S_HULL_HIT;
      }
    }
  } else {
    this_player.shield = u32(this_player.shield - temp);

    const follow = !g.twoPlayerMode;
    JE_setupExplosion(this_player.x - 17, this_player.y - 12, 0, 14, false, follow);
    JE_setupExplosion(this_player.x - 5, this_player.y - 12, 0, 15, false, follow);
    JE_setupExplosion(this_player.x + 7, this_player.y - 12, 0, 16, false, follow);
    JE_setupExplosion(this_player.x + 19, this_player.y - 12, 0, 17, false, follow);

    JE_setupExplosion(this_player.x - 17, this_player.y + 2, 0, 18, false, follow);
    JE_setupExplosion(this_player.x + 19, this_player.y + 2, 0, 19, false, follow);

    JE_setupExplosion(this_player.x - 17, this_player.y + 16, 0, 20, false, follow);
    JE_setupExplosion(this_player.x - 5, this_player.y + 16, 0, 21, false, follow);
    JE_setupExplosion(this_player.x + 7, this_player.y + 16, 0, 22, false, follow);
  }

  JE_wipeShieldArmorBars();
  JE_drawShield();
  JE_drawArmor();

  return u8(playerDamage);
}

/** JE_portConfigs (varz.c L1067-1071): the rear weapon's number of firing modes. */
export function JE_portConfigs(): number {
  const player_index = g.twoPlayerMode ? 1 : 0;
  return g.res.items.weaponPorts[g.player[player_index].items.weapon[REAR_WEAPON].id].opNum;
}

/** JE_drawShield (varz.c L1073-1089): HUD only, a no-op. */
export function JE_drawShield(): void {}

/** JE_drawArmor (varz.c L1091-1106): the HUD bar is HTML, but the armor clamp is game state. */
export function JE_drawArmor(): void {
  for (const p of g.player) if (p.armor > 28) p.armor = 28;
}

/** JE_doSP (varz.c L1108-1125): spawn `num` superpixels (sparks) around (x, y). */
export function JE_doSP(x: number, y: number, num: number, explowidth: number, color: number): void {
  x = u16(x);
  y = u16(y);
  num = u16(num);
  explowidth = u8(explowidth);
  color = u8(color);

  // temp is a JE_byte, as in the C; num never exceeds 255 in practice.
  for (let temp = 0; temp < num; temp = u8(temp + 1)) {
    const tempr = Math.fround(mt_rand_lt1() * (2 * Math.PI));
    const tempy = roundf(Math.fround(Math.fround(Math.fround(Math.cos(tempr)) * mt_rand_1()) * explowidth));
    const tempx = roundf(Math.fround(Math.fround(Math.fround(Math.sin(tempr)) * mt_rand_1()) * explowidth));

    if (++g.last_superpixel >= MAX_SUPERPIXELS) g.last_superpixel = 0;
    const sp = g.superpixels[g.last_superpixel];
    sp.x = u32(tempx + x);
    sp.y = u32(tempy + y);
    sp.delta_x = tempx;
    sp.delta_y = tempy + 1;
    sp.color = color;
    sp.z = 15;
  }
}

/**
 * JE_drawSP (varz.c L1127-1156): moves the superpixels and draws each as a plus of five pixels.
 * The C mixes the pixel already on screen into the color (`(*s & 0x0f) + z`); the draw list has
 * no screen to read, so this assumes the background's value nibble is 0.
 */
export function JE_drawSP(): void {
  const W = 320;
  const H = 200;
  for (let i = MAX_SUPERPIXELS; i--; ) {
    const sp = g.superpixels[i];
    if (sp.z) {
      sp.x = u32(sp.x + sp.delta_x);
      sp.y = u32(sp.y + sp.delta_y);

      if (sp.x < W && sp.y < H) {
        drawPixel(sp.x, sp.y, u8((sp.z >> 1) + sp.color));
        const side = u8(((sp.z >> 1) >> 1) + sp.color);
        if (sp.x > 0) drawPixel(sp.x - 1, sp.y, side);
        if (sp.x < W - 1) drawPixel(sp.x + 1, sp.y, side);
        if (sp.y > 0) drawPixel(sp.x, sp.y - 1, side);
        if (sp.y < H - 1) drawPixel(sp.x, sp.y + 1, side);
      }

      sp.z--;
    }
  }
}
