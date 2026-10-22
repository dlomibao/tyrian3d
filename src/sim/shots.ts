// Port of OpenTyrian src/shots.c: player shot creation, movement and drawing.
//
// Draws go through draw.ts. Each shot gets a fresh draw key when it's created (shot slots are
// reused, and a reused slot must not interpolate from the previous shot's position):
// key = PLAYER_SHOT_KEY_BASE + 2 * serial, and its shadow uses key + 1.

import { s16, s8, u16, u32, u8 } from "./cint";
import { blit_sprite2, blit_sprite2_darken, blit_sprite_blend, drawState } from "./draw";
import { MAX_PWEAPON, g } from "./state";
import { JE_doSP, JE_setupExplosion, shadowYDist } from "./varz";
import { PORT_NUM, WEAP_NUM, type Weapon } from "../data";

// config.h shot bays (indices into shotRepeat[] / shotMultiPos[]).
export const SHOT_FRONT = 0;
export const SHOT_REAR = 1;
export const SHOT_LEFT_SIDEKICK = 2;
export const SHOT_RIGHT_SIDEKICK = 3;
export const SHOT_MISC = 4;
export const SHOT_P2_CHARGE = 5;
export const SHOT_P1_SUPERBOMB = 6;
export const SHOT_P2_SUPERBOMB = 7;
export const SHOT_SPECIAL = 8;
export const SHOT_NORTSPARKS = 9;
export const SHOT_SPECIAL2 = 10;

/** Draw keys for player shots start here (see the header comment). */
export const PLAYER_SHOT_KEY_BASE = 1_000_000;
/** Per shot slot: its current draw key. */
export const playerShotKey = new Array<number>(MAX_PWEAPON + 1).fill(-1);
let nextShotSerial = 0;

/** OPTION_SHAPES (sprite.h): sprite table 5. */
const OPTION_SHAPES = 5;

/** C roundf: round half away from zero. */
export function roundf(v: number): number {
  v = Math.fround(v);
  return v < 0 ? -Math.floor(-v + 0.5) : Math.floor(v + 0.5);
}
export const sinf = (v: number): number => Math.fround(Math.sin(Math.fround(v)));
export const cosf = (v: number): number => Math.fround(Math.cos(Math.fround(v)));

/** shots.c L33-104: shop weapon preview simulation (not used in gameplay). */
export function simulate_player_shots(): void {
  /* Player Shot Images */
  for (let z = 0; z < MAX_PWEAPON; z++) {
    if (g.shotAvail[z] !== 0) {
      g.shotAvail[z] = u8(g.shotAvail[z] - 1);
      if (z !== MAX_PWEAPON - 1) {
        const shot = g.playerShotData[z];

        shot.shotXM = s16(shot.shotXM + shot.shotXC);

        if (shot.shotXM <= 100) shot.shotX = s16(shot.shotX + shot.shotXM);

        shot.shotYM = s16(shot.shotYM + shot.shotYC);
        shot.shotY = s16(shot.shotY + shot.shotYM);

        if (shot.shotYM > 100) {
          shot.shotY = s16(shot.shotY - 120);
          shot.shotY = s16(shot.shotY + g.player[0].delta_y_shot_move);
        }

        if (shot.shotComplicated) {
          shot.shotDevX = s16(shot.shotDevX + shot.shotDirX);
          shot.shotX = s16(shot.shotX + shot.shotDevX);

          if (Math.abs(shot.shotDevX) === shot.shotCirSizeX) shot.shotDirX = s16(-shot.shotDirX);

          shot.shotDevY = s16(shot.shotDevY + shot.shotDirY);
          shot.shotY = s16(shot.shotY + shot.shotDevY);

          if (Math.abs(shot.shotDevY) === shot.shotCirSizeY) shot.shotDirY = s16(-shot.shotDirY);
          /*Double Speed Circle Shots - add a second copy of above loop*/
        }

        const tempShotX = shot.shotX;
        const tempShotY = shot.shotY;

        if (shot.shotX < 0 || shot.shotX > 140 || shot.shotY < 0 || shot.shotY > 170) {
          g.shotAvail[z] = 0;
          continue; // goto draw_player_shot_loop_end
        }

        let anim_frame = u16(shot.shotGr + shot.shotAni);
        shot.shotAni = u16(shot.shotAni + 1);
        if (shot.shotAni === shot.shotAniMax) shot.shotAni = 0;

        if (anim_frame < 60000) {
          if (anim_frame > 1000) anim_frame = anim_frame % 1000;
          if (anim_frame > 500) blit_sprite2(tempShotX + 1, tempShotY, g.res.spriteSheet12, anim_frame - 500);
          else blit_sprite2(tempShotX + 1, tempShotY, g.res.spriteSheet8, anim_frame);
        }
      }
    }
  }
}

const linkMultiGr = [77, 221, 183, 301, 1, 282, 164, 202, 58, 201, 163, 281, 39, 300, 182, 220, 77];
const linkSonicGr = [85, 242, 131, 303, 47, 284, 150, 223, 66, 224, 149, 283, 9, 302, 130, 243, 85];
const linkMult2Gr = [78, 299, 295, 297, 2, 278, 276, 280, 59, 279, 275, 277, 40, 296, 294, 298, 78];

const M_PI = Math.PI;
const M_PI_2 = Math.PI / 2;

/** shots.c L113-151: points shot movement in a direction (the two-player turret gun). */
export function player_shot_set_direction(shot_id: number, weapon_id: number, direction: number): void {
  const shot = g.playerShotData[shot_id];
  direction = Math.fround(direction);

  shot.shotXM = s16(-roundf(sinf(direction) * shot.shotYM));
  shot.shotYM = s16(-roundf(cosf(direction) * shot.shotYM));

  // Some weapons have sprites for each direction, use those.
  let rounded_dir: number;

  switch (weapon_id) {
    case 27:
    case 32:
    case 10:
      rounded_dir = roundf(direction * (16 / (2 * M_PI))); /*16 directions*/
      shot.shotGr = linkMultiGr[rounded_dir];
      break;
    case 28:
    case 33:
    case 11:
      rounded_dir = roundf(direction * (16 / (2 * M_PI))); /*16 directions*/
      shot.shotGr = linkSonicGr[rounded_dir];
      break;
    case 30:
    case 35:
    case 14:
      if (direction > M_PI_2 && direction < M_PI + M_PI_2) {
        shot.shotYC = 1;
      }
      break;
    case 38:
    case 22:
      rounded_dir = roundf(direction * (16 / (2 * M_PI))); /*16 directions*/
      shot.shotGr = linkMult2Gr[rounded_dir];
      break;
  }
}

/** The out-parameters of player_shot_move_and_draw (C pointers). */
export interface PlayerShotMoveOut {
  is_special: boolean;
  shotx: number;
  shoty: number;
  /** JE_integer */
  shot_damage: number;
  /** JE_byte */
  blast_filter: number;
  chain: number;
  playerNum: number;
  /** JE_word */
  special_radiusw: number;
  special_radiush: number;
}

export const newPlayerShotMoveOut = (): PlayerShotMoveOut => ({
  is_special: false, shotx: 0, shoty: 0, shot_damage: 0, blast_filter: 0, chain: 0, playerNum: 0,
  special_radiusw: 0, special_radiush: 0,
});

/**
 * shots.c L153-298: moves and draws a shot; does not collide it with enemies.
 * Writes the C out-parameters into `out`. Returns false if the shot went off-screen.
 * Call with shotAvail[shot_id] != 0, from JE_main's "Player Shot Images" loop, with
 * drawState.pass set to Pass.PlayerShots.
 */
export function player_shot_move_and_draw(shot_id: number, out: PlayerShotMoveOut): boolean {
  const shot = g.playerShotData[shot_id];

  g.shotAvail[shot_id] = u8(g.shotAvail[shot_id] - 1);
  if (shot_id !== MAX_PWEAPON - 1) {
    const owner = g.player[shot.playerNumber - 1];

    shot.shotXM = s16(shot.shotXM + shot.shotXC);
    shot.shotX = s16(shot.shotX + shot.shotXM);
    const tmp_shotXM = shot.shotXM;

    if (shot.shotXM > 100) {
      if (shot.shotXM === 101) {
        shot.shotX = s16(shot.shotX - 101);
        shot.shotX = s16(shot.shotX + owner.delta_x_shot_move);
        shot.shotY = s16(shot.shotY + owner.delta_y_shot_move);
      } else {
        shot.shotX = s16(shot.shotX - 120);
        shot.shotX = s16(shot.shotX + owner.delta_x_shot_move);
      }
    }

    shot.shotYM = s16(shot.shotYM + shot.shotYC);
    shot.shotY = s16(shot.shotY + shot.shotYM);

    if (shot.shotYM > 100) {
      shot.shotY = s16(shot.shotY - 120);
      shot.shotY = s16(shot.shotY + owner.delta_y_shot_move);
    }

    if (shot.shotComplicated) {
      shot.shotDevX = s16(shot.shotDevX + shot.shotDirX);
      shot.shotX = s16(shot.shotX + shot.shotDevX);

      if (Math.abs(shot.shotDevX) === shot.shotCirSizeX) shot.shotDirX = s16(-shot.shotDirX);

      shot.shotDevY = s16(shot.shotDevY + shot.shotDirY);
      shot.shotY = s16(shot.shotY + shot.shotDevY);

      if (Math.abs(shot.shotDevY) === shot.shotCirSizeY) shot.shotDirY = s16(-shot.shotDirY);

      /*Double Speed Circle Shots - add a second copy of above loop*/
    }

    out.shotx = shot.shotX;
    out.shoty = shot.shotY;

    if (shot.shotX < -34 || shot.shotX > 290 || shot.shotY < -15 || shot.shotY > 190) {
      g.shotAvail[shot_id] = 0;
      return false;
    }

    if (shot.shotTrail !== 255) {
      if (shot.shotTrail === 98)
        JE_setupExplosion(shot.shotX - shot.shotXM, shot.shotY - shot.shotYM, 0, shot.shotTrail, false, false);
      else JE_setupExplosion(shot.shotX, shot.shotY, 0, shot.shotTrail, false, false);
    }

    if (shot.aimAtEnemy !== 0) {
      shot.aimDelay = u8(shot.aimDelay - 1);
      if (shot.aimDelay === 0) {
        shot.aimDelay = shot.aimDelayMax;

        if (g.enemyAvail[shot.aimAtEnemy - 1] !== 1) {
          if (shot.shotX < g.enemy[shot.aimAtEnemy - 1].ex) shot.shotXM = s16(shot.shotXM + 1);
          else shot.shotXM = s16(shot.shotXM - 1);

          if (shot.shotY < g.enemy[shot.aimAtEnemy - 1].ey) shot.shotYM = s16(shot.shotYM + 1);
          else shot.shotYM = s16(shot.shotYM - 1);
        } else {
          if (shot.shotXM > 0) shot.shotXM = s16(shot.shotXM + 1);
          else shot.shotXM = s16(shot.shotXM - 1);
        }
      }
    }

    let sprite_frame = u16(shot.shotGr + shot.shotAni);
    shot.shotAni = u16(shot.shotAni + 1);
    if (shot.shotAni === shot.shotAniMax) shot.shotAni = 0;

    out.shot_damage = shot.shotDmg;
    out.blast_filter = shot.shotBlastFilter;
    out.chain = shot.chainReaction;
    out.playerNum = shot.playerNumber;

    out.is_special = sprite_frame > 60000;

    const savedKey = drawState.key;
    const key = playerShotKey[shot_id];

    if (out.is_special) {
      const table = g.res.spriteTables[OPTION_SHAPES];
      drawState.key = key;
      blit_sprite_blend(out.shotx + 1, out.shoty, table, sprite_frame - 60001);

      const spr = table.sprites[sprite_frame - 60001];
      out.special_radiusw = u16(Math.trunc((spr?.width ?? 0) / 2));
      out.special_radiush = u16(Math.trunc((spr?.height ?? 0) / 2));
    } else {
      if (sprite_frame > 1000) {
        JE_doSP(out.shotx + 1 + 6, out.shoty + 6, 5, 3, u8(Math.trunc(sprite_frame / 1000) << 4));
        sprite_frame = sprite_frame % 1000;
      }
      // `*out_shoty + shadowYDist < 190` compares as unsigned (shadowYDist is uint).
      const shadow = g.background2 && u32(out.shoty + shadowYDist) < 190 && tmp_shotXM < 100;
      if (sprite_frame > 500) {
        if (shadow) {
          drawState.key = key < 0 ? -1 : key + 1;
          blit_sprite2_darken(out.shotx + 1, out.shoty + shadowYDist, g.res.spriteSheet12, sprite_frame - 500);
        }
        drawState.key = key;
        blit_sprite2(out.shotx + 1, out.shoty, g.res.spriteSheet12, sprite_frame - 500);
      } else {
        if (shadow) {
          drawState.key = key < 0 ? -1 : key + 1;
          blit_sprite2_darken(out.shotx + 1, out.shoty + shadowYDist, g.res.spriteSheet8, sprite_frame);
        }
        drawState.key = key;
        blit_sprite2(out.shotx + 1, out.shoty, g.res.spriteSheet8, sprite_frame);
      }
    }
    drawState.key = savedKey;
  }

  return true;
}

/** One entry of a weapon's per-shot pattern arrays (attack[], del[], sx[] ...). */
interface WeaponPattern {
  attack: number;
  del: number;
  sx: number;
  sy: number;
  bx: number;
  by: number;
  sg: number;
}

/**
 * weapon->attack[i], weapon->del[i] ... for i in 0..8. The arrays are [8], but player_shot_create
 * can index 8: shotMultiPos only resets when it equals `max` or exceeds 8, so a value of 8 left by
 * a previous weapon with a smaller `max` steps to 9. In JE_WeaponType (episodes.h, no padding)
 * element [8] of each array is the first byte(s) of the next field, which is what the C reads.
 */
function weapon_pattern(weapon: Weapon, i: number): WeaponPattern {
  if (i < 8) {
    return { attack: weapon.attack[i], del: weapon.del[i], sx: weapon.sx[i], sy: weapon.sy[i], bx: weapon.bx[i], by: weapon.by[i], sg: weapon.sg[i] };
  }
  return {
    attack: weapon.del[0],
    del: u8(weapon.sx[0]),
    sx: weapon.sy[0],
    sy: weapon.bx[0],
    bx: weapon.by[0],
    by: s8(weapon.sg[0] & 0xff),
    sg: u16((weapon.acceleration & 0xff) | ((weapon.accelerationX & 0xff) << 8)),
  };
}

/**
 * shots.c L300-504 (FKA Varz.initPlayerShot): creates a player shot. `bay_i` indexes
 * shotRepeat/shotMultiPos (SHOT_*). Returns the last shot slot used, or MAX_PWEAPON if none.
 */
export function player_shot_create(
  portNum: number, bay_i: number, PX: number, PY: number, mouseX: number, mouseY: number, wpNum: number, playerNum: number,
): number {
  const soundChannel = [0, 2, 4, 4, 2, 2, 5, 5, 1, 4, 1];

  // JE_word / JE_byte parameters
  portNum = u16(portNum);
  PX = u16(PX);
  PY = u16(PY);
  mouseX = u16(mouseX);
  mouseY = u16(mouseY);
  wpNum = u16(wpNum);
  playerNum = u8(playerNum);

  // Bounds check
  if (portNum > PORT_NUM || wpNum <= 0 || wpNum > WEAP_NUM) return MAX_PWEAPON;

  const weapon = g.res.items.weapons[wpNum];

  if (g.power < g.res.items.weaponPorts[portNum].powerUse) return MAX_PWEAPON;
  g.power -= g.res.items.weaponPorts[portNum].powerUse;

  if (weapon.sound > 0) g.soundQueue[soundChannel[bay_i]] = weapon.sound;

  let shot_id = MAX_PWEAPON;
  /*Rot*/
  for (let multi_i = 1; multi_i <= weapon.multi; multi_i++) {
    for (shot_id = 0; shot_id < MAX_PWEAPON; shot_id++) if (g.shotAvail[shot_id] === 0) break;
    if (shot_id === MAX_PWEAPON) return MAX_PWEAPON;

    if (g.shotMultiPos[bay_i] === weapon.max || g.shotMultiPos[bay_i] > 8) g.shotMultiPos[bay_i] = 1;
    else g.shotMultiPos[bay_i] = u8(g.shotMultiPos[bay_i] + 1);

    const w = weapon_pattern(weapon, g.shotMultiPos[bay_i] - 1);

    const shot = g.playerShotData[shot_id];
    shot.chainReaction = 0;

    shot.playerNumber = playerNum;

    shot.shotAni = 0;

    shot.shotComplicated = weapon.circleSize !== 0;

    if (weapon.circleSize === 0) {
      shot.shotDevX = 0;
      shot.shotDirX = 0;
      shot.shotDevY = 0;
      shot.shotDirY = 0;
      shot.shotCirSizeX = 0;
      shot.shotCirSizeY = 0;
    } else {
      let circsize = weapon.circleSize;

      if (circsize > 19) {
        const circsize_mod20 = circsize % 20;
        shot.shotCirSizeX = circsize_mod20;
        shot.shotDevX = circsize_mod20 >> 1;

        circsize = Math.trunc(circsize / 20);
        shot.shotCirSizeY = circsize;
        shot.shotDevY = circsize >> 1;
      } else {
        shot.shotCirSizeX = circsize;
        shot.shotCirSizeY = circsize;
        shot.shotDevX = circsize >> 1;
        shot.shotDevY = circsize >> 1;
      }
      shot.shotDirX = 1;
      shot.shotDirY = -1;
    }

    shot.shotTrail = weapon.trail;

    if (w.attack > 99 && w.attack < 250) {
      shot.chainReaction = w.attack - 100;
      shot.shotDmg = 1;
    } else {
      shot.shotDmg = w.attack;
    }

    shot.shotBlastFilter = weapon.shipBlastFilter;

    let tmp_by = w.by; // JE_integer

    /*Note: Only front selection used for player shots...*/

    shot.shotX = s16(PX + w.bx);

    shot.shotY = s16(PY + tmp_by);
    shot.shotYC = s16(-weapon.acceleration);
    shot.shotXC = weapon.accelerationX;

    shot.shotXM = w.sx;

    // Not sure what this field does exactly.
    let del = w.del; // JE_byte

    if (del === 121) {
      shot.shotTrail = 0;
      del = 255;
    }

    shot.shotGr = w.sg;
    if (shot.shotGr === 0) g.shotAvail[shot_id] = 0;
    else g.shotAvail[shot_id] = del;

    if (del > 100 && del < 120) shot.shotAniMax = del - 100 + 1;
    else shot.shotAniMax = u16(weapon.weapAni + 1);

    if (del === 99 || del === 98) {
      tmp_by = s16(PX - mouseX);
      if (tmp_by < -5) tmp_by = -5;
      else if (tmp_by > 5) tmp_by = 5;
      shot.shotXM = s16(shot.shotXM + tmp_by);
    }

    if (del === 99 || del === 100) {
      tmp_by = s16(PY - mouseY - w.sy);
      if (tmp_by < -4) tmp_by = -4;
      else if (tmp_by > 4) tmp_by = 4;
      shot.shotYM = tmp_by;
    } else if (w.sy === 98) {
      shot.shotYM = 0;
      shot.shotYC = -1;
    } else if (w.sy > 100) {
      shot.shotYM = w.sy;
      shot.shotY = s16(shot.shotY - g.player[shot.playerNumber - 1].delta_y_shot_move);
    } else {
      shot.shotYM = -w.sy;
    }

    if (w.sx > 100) {
      shot.shotXM = w.sx;
      shot.shotX = s16(shot.shotX - g.player[shot.playerNumber - 1].delta_x_shot_move);
      if (shot.shotXM === 101) shot.shotY = s16(shot.shotY - g.player[shot.playerNumber - 1].delta_y_shot_move);
    }

    if (weapon.aim > 5) {
      /*Guided Shot*/
      let best_dist = 65000;
      let closest_enemy = 0;
      /*Find Closest Enemy*/
      for (let x = 0; x < 100; x++) {
        if (g.enemyAvail[x] !== 1 && !g.enemy[x].scoreitem) {
          const y = u16(Math.abs(g.enemy[x].ex - shot.shotX) + Math.abs(g.enemy[x].ey - shot.shotY)); // JE_word y
          if (y < best_dist) {
            best_dist = y;
            closest_enemy = x + 1;
          }
        }
      }
      shot.aimAtEnemy = closest_enemy;
      shot.aimDelay = 5;
      shot.aimDelayMax = u8(weapon.aim - 5);
    } else {
      shot.aimAtEnemy = 0;
    }

    g.shotRepeat[bay_i] = weapon.shotRepeat;

    // A new shot in this slot: give it a new draw key (not in the C).
    playerShotKey[shot_id] = PLAYER_SHOT_KEY_BASE + 2 * nextShotSerial;
    nextShotSerial = (nextShotSerial + 1) % 0x10000000;
  }

  return shot_id;
}
