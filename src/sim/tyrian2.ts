// Port of the world side of OpenTyrian src/tyrian2.c: enemies (JE_drawEnemy, JE_newEnemy,
// JE_makeEnemy, JE_createNewEventEnemy), the level event system (JE_eventSystem, JE_eventJump,
// JE_searchFor), boss bar state (draw_boss_bar) and level loading (JE_loadMap). JE_main itself is
// the integrator's; initLevelWorld() holds the world half of its start-of-level setup.
//
// The C's scratch globals (temp, temp2, temp3, tempW, b from varz.h) are module variables here.
// Within the code ported here only `b` carries a value between functions (JE_createNewEventEnemy
// sets it for JE_eventSystem), and nothing outside these functions reads them afterwards.

import {
  EVENT_MAXIMUM,
  atoi,
  levelTiles,
  parseEpisodeScript,
  parseLevel,
  parseShapes,
  readEncryptedString,
  readLevelPositions,
  BinaryReader,
  type EpisodeScript,
  type LevelEvent,
} from "../data";
import { fdiv, fmul, mt_rand_mod, roundf } from "./cfloat";
import { s8, s16, u8, u16, u32 } from "./cint";
import { blit_sprite2, blit_sprite2_filter, drawGroup, drawList, drawState, type Sprite2Sheet } from "./draw";
import { JE_itemScreenNonInteractive } from "./game_menu";
import { loadMenuText } from "./helptext";
import { mt_rand } from "./mtrand";
import { JE_drawTextWindow } from "./mainint";
import { buildResources, requireFile, type TyrianFiles } from "./resources";
import { windowTextSamples, V_GOOD_LUCK } from "./sndmast";
import {
  DIFFICULTY_10,
  DIFFICULTY_EASY,
  DIFFICULTY_HARD,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_INSANITY,
  DIFFICULTY_MANIACAL,
  DIFFICULTY_NORMAL,
  DIFFICULTY_NORTANEOUS,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_WIMP,
  DIFFICULTY_ZINGLON,
  ENEMY_SHOT_MAX,
  FRONT_WEAPON,
  REAR_WEAPON,
  SA_NONE,
  SHOT_SPECIAL,
  SHOT_SPECIAL2,
  g,
  newEnemy,
  newExplosion,
  newPlayerShotData,
  newRepExplosion,
  newSuperpixel,
  type Enemy,
} from "./state";
import { JE_setupExplosion, randomEnemyLaunchSounds, superTyrianSpecials } from "./varz";
import { initialize_starfield } from "./backgrnd";

/** shapeFile[34] (lvlmast.c): newsh?.shp suffix per enemy shape bank (event 5). */
export const shapeFile = [
  "2", "4", "7", "8", "A", "B", "C", "D", "E", "F",
  "G", "H", "I", "J", "K", "L", "M", "N", "O", "P",
  "Q", "R", "S", "T", "U", "5", "#", "V", "0", "@", // [25] should be '&' rather than '5'
  "3", "^", "5", "9",
] as const;

/** EPISODE_AVAILABLE (episodes.h) */
const EPISODE_AVAILABLE = 4;

/** pcxpal (pcxmast.c): palette index for each JE_loadPic picture, [1..PCXnum]. */
const pcxpal = [0, 7, 5, 8, 10, 5, 18, 19, 19, 20, 21, 22, 5] as const;

/** Base for enemy draw keys (drawState.key), clear of small keys other draw code may use. */
export const ENEMY_KEY_BASE = 1 << 24;

// Scratch globals (varz.c temp, tempW, b).
let tempW = 0;
let b = 0;

// --- Per-enemy sidecar state the C gets from its pointer layout ---

/**
 * Which enemySpriteSheets slot an enemy's sprites come from. The C stores a pointer to the slot
 * (`&enemySpriteSheets[i]`), so a later event 5 that reloads the slot changes what the enemy draws
 * with. -1: a fixed sheet (spriteSheet10/11).
 */
let enemySheetSlot = new WeakMap<Enemy, number>();
/** A serial number per JE_makeEnemy call, so draw keys change when a slot is reused. */
let enemySerial = new WeakMap<Enemy, number>();
let nextEnemySerial = 1;

function enemySprite2s(e: Enemy): Sprite2Sheet | null {
  const slot = enemySheetSlot.get(e);
  if (slot !== undefined && slot >= 0) return g.enemySpriteSheets[slot];
  return e.sprite2s;
}

/**
 * `enemy.egr[enemycycle - 1]`, including the out-of-range reads the C can make through the
 * struct layout: egr[-1] is `ani` plus a zero padding byte, egr[20] overlaps size/linknum and
 * egr[21] aniactive/animax (little-endian JE_word).
 */
function egrAt(e: Enemy, k: number): number {
  if (k >= 0 && k < 20) return e.egr[k];
  if (k === -1) return e.ani;
  if (k === 20) return e.size | (e.linknum << 8);
  if (k === 21) return e.aniactive | (e.animax << 8);
  if (k === 22) return e.aniwhenfire;
  return 0;
}

/**
 * eventRec[i], 0-based. Past maxEvent + 1 the C array keeps stale records from earlier levels
 * (only malformed jumps and skips reach them); here they read as a fresh event that never fires,
 * which also stops JE_eventJump's search. JE_main's event loop should use this too:
 * `while (eventAt(eventLoc - 1).eventTime <= curLoc && eventLoc <= maxEvent) JE_eventSystem();`
 */
export function eventAt(i: number): LevelEvent {
  return (
    g.lvl.eventRec[i] ?? {
      eventTime: 0xffff, eventType: 0, eventDat: 0, eventDat2: 0, eventDat3: 0, eventDat5: 0, eventDat6: 0, eventDat4: 0,
    }
  );
}

/** nortsong.c play_song: the audio layer plays g.song. */
function play_song(song_num: number): void {
  g.song = song_num;
}

/**
 * blit_enemy (tyrian2.c L109-122). `part` (0..3) tells the 2x2 enemy's quarters apart in draw keys;
 * `first` marks the first quarter drawn this tick. The draw also records the whole enemy
 * (drawGroup), so the renderer can replace its tiles with one model.
 */
function blit_enemy(i: number, x_offset: number, y_offset: number, sprite_offset: number, part: number, first: boolean): void {
  const e = g.enemy[i];
  const sprite2s = enemySprite2s(e);
  if (sprite2s === null) return;

  const x = e.ex + x_offset + g.tempMapXOfs;
  const y = e.ey + y_offset;
  const index = u32(egrAt(e, e.enemycycle - 1) + sprite_offset);

  drawState.key = ENEMY_KEY_BASE + (enemySerial.get(e) ?? 0) * 4 + part;
  // The object's centre: a 2x2 enemy's 24x28 block is centred on (ex + 6, ey + 7), a 1x1 enemy's
  // 12x14 tile on (ex + 6, ey + 7) too.
  drawGroup.index = u32(egrAt(e, e.enemycycle - 1));
  drawGroup.size = e.size === 1 ? 2 : 1;
  drawGroup.dx = e.ex + 6 + g.tempMapXOfs - x;
  drawGroup.dy = e.ey + 7 - y;
  drawGroup.first = first;
  if (e.filter !== 0) blit_sprite2_filter(x, y, sprite2s, index, e.filter);
  else blit_sprite2(x, y, sprite2s, index);
  drawState.key = -1;
  drawGroup.index = -1;
}

/**
 * JE_drawEnemy (tyrian2.c L124-568): moves, animates, fires and launches the 25 enemies in slots
 * enemyOffset-25 .. enemyOffset-1, and draws them. The caller sets tempMapXOfs, tempBackMove and
 * drawState.pass first, as JE_main does.
 */
export function JE_drawEnemy(enemyOffset: number): void {
  g.player[0].x -= 25;

  for (let i = enemyOffset - 25; i < enemyOffset; i++) {
    if (g.enemyAvail[i] !== 1) drawOneEnemy(i, enemyOffset);
  }

  g.player[0].x += 25;
}

/** The body of JE_drawEnemy's loop for one enemy; `return` is `goto draw_enemy_end`. */
function drawOneEnemy(i: number, enemyOffset: number): void {
  const e = g.enemy[i];
  const p0 = g.player[0];
  const items = g.res.items;

  e.mapoffset = g.tempMapXOfs;

  if (e.xaccel && u32(e.xaccel - 89) > mt_rand() % 11) {
    if (p0.x > e.ex) {
      if (e.exc < e.xaccel - 89) e.exc = s8(e.exc + 1);
    } else {
      if (e.exc >= 0 || -e.exc < e.xaccel - 89) e.exc = s8(e.exc - 1);
    }
  }

  if (e.yaccel && u32(e.yaccel - 89) > mt_rand() % 11) {
    if (p0.y > e.ey) {
      if (e.eyc < e.yaccel - 89) e.eyc = s8(e.eyc + 1);
    } else {
      if (e.eyc >= 0 || -e.eyc < e.yaccel - 89) e.eyc = s8(e.eyc - 1);
    }
  }

  if (e.ex + g.tempMapXOfs > -29 && e.ex + g.tempMapXOfs < 300) {
    if (e.aniactive === 1) {
      e.enemycycle = u8(e.enemycycle + 1);

      if (e.enemycycle === e.animax) e.aniactive = e.aniwhenfire;
      else if (e.enemycycle > e.ani) e.enemycycle = e.animin;
    }

    if (egrAt(e, e.enemycycle - 1) === 999) {
      enemy_gone(i);
      return;
    }

    if (e.size === 1) {
      // 2x2 enemy
      if (e.ey > -13) {
        blit_enemy(i, -6, -7, 0, 0, true);
        blit_enemy(i, 6, -7, 1, 1, false);
      }
      if (e.ey > -26 && e.ey < 182) {
        blit_enemy(i, -6, 7, 19, 2, !(e.ey > -13));
        blit_enemy(i, 6, 7, 20, 3, false);
      }
    } else {
      if (e.ey > -13) blit_enemy(i, 0, 0, 0, 0, true);
    }

    e.filter = 0;
  }

  if (e.excc) {
    e.exccw = s8(e.exccw - 1);
    if (e.exccw <= 0) {
      if (e.exc === e.exrev) {
        e.excc = s8(-e.excc);
        e.exrev = s8(-e.exrev);
        e.exccadd = s16(-e.exccadd);
      } else {
        e.exc = s8(e.exc + e.exccadd);
        e.exccw = s8(e.exccwmax);
        if (e.exc === e.exrev) {
          e.excc = s8(-e.excc);
          e.exrev = s8(-e.exrev);
          e.exccadd = s16(-e.exccadd);
        }
      }
    }
  }

  if (e.eycc) {
    e.eyccw = s8(e.eyccw - 1);
    if (e.eyccw <= 0) {
      if (e.eyc === e.eyrev) {
        e.eycc = s8(-e.eycc);
        e.eyrev = s8(-e.eyrev);
        e.eyccadd = s16(-e.eyccadd);
      } else {
        e.eyc = s8(e.eyc + e.eyccadd);
        e.eyccw = s8(e.eyccwmax);
        if (e.eyc === e.eyrev) {
          e.eycc = s8(-e.eycc);
          e.eyrev = s8(-e.eyrev);
          e.eyccadd = s16(-e.eyccadd);
        }
      }
    }
  }

  e.ey = s16(e.ey + e.fixedmovey);

  e.ex = s16(e.ex + e.exc);
  if (e.ex < -80 || e.ex > 340) {
    enemy_gone(i);
    return;
  }

  e.ey = s16(e.ey + e.eyc);
  if (e.ey < -112 || e.ey > 190) {
    enemy_gone(i);
    return;
  }

  // enemy_still_exists:

  /*X bounce*/
  if (e.ex <= e.xminbounce || e.ex >= e.xmaxbounce) e.exc = s8(-e.exc);

  /*Y bounce*/
  if (e.ey <= e.yminbounce || e.ey >= e.ymaxbounce) e.eyc = s8(-e.eyc);

  /* Evalue != 0 - score item at boundary */
  if (e.scoreitem) {
    if (e.ex < -5) e.ex = s16(e.ex + 1);
    if (e.ex > 245) e.ex = s16(e.ex - 1);
  }

  e.ey = s16(e.ey + g.tempBackMove);

  if (e.ex <= -24 || e.ex >= 296) return;

  const tempX = e.ex;
  const tempY = e.ey;

  /* Enemy Shots */
  if (e.edamaged) return;

  g.enemyOnScreen = u16(g.enemyOnScreen + 1);

  if (e.iced) {
    e.iced = u8(e.iced - 1);
    if (e.enemyground) {
      e.filter = 0x09;
    }
    return;
  }

  for (let j = 3; j > 0; j--) {
    if (e.freq[j - 1]) {
      const temp3 = e.tur[j - 1];

      e.eshotwait[j - 1] = u8(e.eshotwait[j - 1] - 1);
      if (e.eshotwait[j - 1] === 0 && temp3) {
        e.eshotwait[j - 1] = e.freq[j - 1];
        if (g.difficultyLevel > DIFFICULTY_NORMAL) {
          e.eshotwait[j - 1] = u8(Math.trunc(e.eshotwait[j - 1] / 2) + 1);
          if (g.difficultyLevel > DIFFICULTY_MANIACAL) e.eshotwait[j - 1] = u8(Math.trunc(e.eshotwait[j - 1] / 2) + 1);
        }

        if (g.galagaMode && (e.eyc === 0 || mt_rand() % 400 >= g.galagaShotFreq)) return;

        switch (temp3) {
          case 252 /* Savara Boss DualMissile */:
            if (e.ey > 20) {
              JE_setupExplosion(tempX - 8 + g.tempMapXOfs, tempY - 20 - g.backMove * 8, -2, 6, false, false);
              JE_setupExplosion(tempX + 4 + g.tempMapXOfs, tempY - 20 - g.backMove * 8, -2, 6, false, false);
            }
            break;
          case 251: {
            /* Suck-O-Magnet */
            const attraction = s16(4 - Math.trunc((Math.abs(p0.x - tempX) + Math.abs(p0.y - tempY)) / 100));
            if (attraction > 0) p0.x_velocity += p0.x > tempX ? -attraction : attraction;
            break;
          }
          case 253 /* Left ShortRange Magnet */:
            if (Math.abs(p0.x + 25 - 14 - tempX) < 24 && Math.abs(p0.y - tempY) < 28) {
              p0.x_velocity += 2;
            }
            if (g.twoPlayerMode && Math.abs(g.player[1].x - 14 - tempX) < 24 && Math.abs(g.player[1].y - tempY) < 28) {
              g.player[1].x_velocity += 2;
            }
            break;
          case 254 /* Left ShortRange Magnet */:
            if (Math.abs(p0.x + 25 - 14 - tempX) < 24 && Math.abs(p0.y - tempY) < 28) {
              p0.x_velocity -= 2;
            }
            if (g.twoPlayerMode && Math.abs(g.player[1].x - 14 - tempX) < 24 && Math.abs(g.player[1].y - tempY) < 28) {
              g.player[1].x_velocity -= 2;
            }
            break;
          case 255 /* Magneto RePulse!! */:
            if (g.difficultyLevel !== DIFFICULTY_EASY) {
              /*DIF*/
              if (j === 3) {
                e.filter = 0x70;
              } else {
                const repulsion = s16(4 - Math.trunc((Math.abs(p0.x - tempX) + Math.abs(p0.y - tempY)) / 20));
                if (repulsion > 0) p0.x_velocity += p0.x > tempX ? repulsion : -repulsion;
              }
            }
            break;
          default: {
            /*Rot*/
            const w = items.weapons[temp3];
            for (let tempCount = w.multi; tempCount > 0; tempCount--) {
              let b: number;
              for (b = 0; b < ENEMY_SHOT_MAX; b++) {
                if (g.enemyShotAvail[b]) break;
              }
              if (b === ENEMY_SHOT_MAX) return;

              g.enemyShotAvail[b] = !g.enemyShotAvail[b];

              if (w.sound > 0) {
                let temp: number;
                do {
                  temp = mt_rand() % 8;
                } while (temp === 3);
                g.soundQueue[temp] = w.sound;
              }

              if (e.aniactive === 2) e.aniactive = 1;

              e.eshotmultipos[j - 1] = u8(e.eshotmultipos[j - 1] + 1);
              if (e.eshotmultipos[j - 1] > w.max) e.eshotmultipos[j - 1] = 1;

              const tempPos = e.eshotmultipos[j - 1] - 1;

              const s = g.enemyShot[b];
              s.sx = s16(tempX + w.bx[tempPos] + g.tempMapXOfs);
              s.sy = s16(tempY + w.by[tempPos]);
              s.sdmg = u8(w.attack[tempPos]);
              s.tx = w.tx;
              s.ty = w.ty;
              s.duration = u8(w.del[tempPos]);
              s.animate = 0;
              s.animax = u16(w.weapAni);

              s.sgr = u16(w.sg[tempPos]);
              switch (j) {
                case 1:
                  s.syc = s8(w.acceleration);
                  s.sxc = s8(w.accelerationX);

                  s.sxm = s16(w.sx[tempPos]);
                  s.sym = s16(w.sy[tempPos]);
                  break;
                case 3:
                  s.sxc = s8(-w.acceleration);
                  s.syc = s8(w.accelerationX);

                  s.sxm = s16(-w.sy[tempPos]);
                  s.sym = s16(-w.sx[tempPos]);
                  break;
                case 2:
                  s.sxc = s8(w.acceleration);
                  s.syc = s8(-w.acceleration);

                  s.sxm = s16(w.sy[tempPos]);
                  s.sym = s16(-w.sx[tempPos]);
                  break;
              }

              if (w.aim > 0) {
                let aim = w.aim;

                /*DIF*/
                if (g.difficultyLevel > DIFFICULTY_NORMAL) aim = u8(aim + g.difficultyLevel - 2);

                let targetX = u16(p0.x);
                let targetY = u16(p0.y);

                if (g.twoPlayerMode) {
                  // fire at live player(s)
                  let temp: number;
                  if (p0.is_alive && !g.player[1].is_alive) temp = 0;
                  else if (g.player[1].is_alive && !p0.is_alive) temp = 1;
                  else temp = mt_rand() % 2;

                  if (temp === 1) {
                    targetX = u16(g.player[1].x - 25);
                    targetY = u16(g.player[1].y);
                  }
                }

                let aimX = s16(targetX + 25 - tempX - g.tempMapXOfs - 4);
                if (aimX === 0) aimX = 1;
                let aimY = s16(targetY - tempY);
                if (aimY === 0) aimY = 1;
                const maxMagAim = s16(Math.max(Math.abs(aimX), Math.abs(aimY)));
                s.sxm = s16(roundf(fmul(fdiv(aimX, maxMagAim), aim)));
                s.sym = s16(roundf(fmul(fdiv(aimY, maxMagAim), aim)));
              }
            }
            break;
          }
        }
      }
    }
  }

  /* Enemy Launch Routine */
  if (e.launchfreq) {
    e.launchwait = u8(e.launchwait - 1);
    if (e.launchwait === 0) {
      e.launchwait = e.launchfreq;

      if (e.launchspecial !== 0) {
        /*Type  1 : Must be inline with player*/
        if (Math.abs(e.ey - p0.y) > 5) return;
      }

      if (e.aniactive === 2) {
        e.aniactive = 1;
      }

      if (e.launchtype === 0) return;

      tempW = e.launchtype;
      b = JE_newEnemy(enemyOffset === 50 ? 75 : enemyOffset - 25, tempW, 0);

      /*Launch Enemy Placement*/
      if (b > 0) {
        const ne = g.enemy[b - 1];

        ne.ex = tempX;
        ne.ey = s16(tempY + g.res.enemyDat[ne.enemytype].startYC);
        if (ne.size === 0) ne.ey = s16(ne.ey - 7);

        if (ne.launchtype > 0 && ne.launchfreq === 0) {
          if (ne.launchtype > 90) {
            ne.ex = s16(ne.ex + mt_rand_mod((ne.launchtype - 90) * 4) - (ne.launchtype - 90) * 2);
          } else {
            let aimX = s16(p0.x + 25 - tempX - g.tempMapXOfs - 4);
            if (aimX === 0) aimX = 1;
            let aimY = s16(p0.y - tempY);
            if (aimY === 0) aimY = 1;
            const maxMagAim = s16(Math.max(Math.abs(aimX), Math.abs(aimY)));
            ne.exc = s8(roundf(fmul(fdiv(aimX, maxMagAim), ne.launchtype)));
            ne.eyc = s8(roundf(fmul(fdiv(aimY, maxMagAim), ne.launchtype)));
          }
        }

        let temp: number;
        do {
          temp = mt_rand() % 8;
        } while (temp === 3);
        g.soundQueue[temp] = randomEnemyLaunchSounds[mt_rand() % 3];

        if (e.launchspecial === 1 && e.linknum < 100) {
          ne.linknum = e.linknum;
        }
      }
    }
  }
}

/** enemy_gone: (tyrian2.c L259-262) */
function enemy_gone(i: number): void {
  /* enemy[i].egr[10] &= 0x00ff; <MXD> madness? */
  g.enemyAvail[i] = 1;
}

/** JE_newEnemy (tyrian2.c L3765-3777): returns the 1-based slot, or 0 if the block is full. */
export function JE_newEnemy(enemyOffset: number, eDatI: number, uniqueShapeTableI: number): number {
  for (let i = enemyOffset; i < enemyOffset + 25; ++i) {
    if (g.enemyAvail[i] === 1) {
      g.enemyAvail[i] = JE_makeEnemy(g.enemy[i], eDatI, uniqueShapeTableI);
      return i + 1;
    }
  }

  return 0;
}

/** JE_makeEnemy (tyrian2.c L3779-4062): returns what to set enemyAvail to (0 enemy, 2 pick-up). */
export function JE_makeEnemy(enemy: Enemy, eDatI: number, uniqueShapeTableI: number): number {
  eDatI = u16(eDatI);
  uniqueShapeTableI = s16(uniqueShapeTableI);
  let avail: number;

  let shapeTableI: number;

  if (g.superArcadeMode !== SA_NONE && eDatI === 534) eDatI = 533;

  const dat = g.res.enemyDat[eDatI];
  if (!dat) throw new Error(`JE_makeEnemy: no enemy type ${eDatI}`);

  if (uniqueShapeTableI > 0) {
    shapeTableI = u8(uniqueShapeTableI);
  } else {
    shapeTableI = dat.shapeBank;
  }

  let sprite2s: Sprite2Sheet | null = null;
  let slot = -1;
  if (shapeTableI === 21) {
    sprite2s = g.res.spriteSheet11; // Coins&Gems
  } else if (shapeTableI === 26) {
    sprite2s = g.res.spriteSheet10; // Two-Player Stuff
  } else {
    for (let i = 0; i < g.enemySpriteSheetIds.length; ++i)
      if (shapeTableI === g.enemySpriteSheetIds[i]) {
        sprite2s = g.enemySpriteSheets[i];
        slot = i;
      }
  }

  if (sprite2s !== null || slot >= 0) {
    enemy.sprite2s = sprite2s;
    enemySheetSlot.set(enemy, slot);
  }
  // else: use shape table value from previous enemy that occupied the enemy slot (ex. APPROACH).
  // The C logs "Ignoring sprite from unloaded shape table" here.

  enemySerial.set(enemy, nextEnemySerial++);

  enemy.enemydatofs = dat;

  enemy.mapoffset = 0;

  for (let i = 0; i < 3; ++i) {
    enemy.eshotmultipos[i] = 0;
  }

  enemy.enemyground = (dat.explosionType & 1) === 0;
  enemy.explonum = dat.explosionType >> 1;

  enemy.launchfreq = dat.eLaunchFreq;
  enemy.launchwait = dat.eLaunchFreq;
  enemy.launchtype = dat.eLaunchType % 1000;
  enemy.launchspecial = u8(Math.trunc(dat.eLaunchType / 1000));

  enemy.xaccel = u8(dat.xAccel);
  enemy.yaccel = u8(dat.yAccel);

  enemy.xminbounce = -10000;
  enemy.xmaxbounce = 10000;
  enemy.yminbounce = -10000;
  enemy.ymaxbounce = 10000;
  /*Far enough away to be impossible to reach*/

  for (let i = 0; i < 3; ++i) {
    enemy.tur[i] = dat.tur[i];
  }

  enemy.ani = dat.ani;
  enemy.animin = 1;

  switch (dat.animate) {
    case 0:
      enemy.enemycycle = 1;
      enemy.aniactive = 0;
      enemy.animax = 0;
      enemy.aniwhenfire = 0;
      break;
    case 1:
      enemy.enemycycle = 0;
      enemy.aniactive = 1;
      enemy.animax = 0;
      enemy.aniwhenfire = 0;
      break;
    case 2:
      enemy.enemycycle = 1;
      enemy.aniactive = 2;
      enemy.animax = enemy.ani;
      enemy.aniwhenfire = 2;
      break;
  }

  if (dat.startXC !== 0) enemy.ex = s16(dat.startX + mt_rand_mod(dat.startXC * 2) - dat.startXC + 1);
  else enemy.ex = s16(dat.startX + 1);

  if (dat.startYC !== 0) enemy.ey = s16(dat.startY + mt_rand_mod(dat.startYC * 2) - dat.startYC + 1);
  else enemy.ey = s16(dat.startY + 1);

  enemy.exc = dat.xMove;
  enemy.eyc = dat.yMove;
  enemy.excc = dat.xCAccel;
  enemy.eycc = dat.yCAccel;
  enemy.exccw = s8(Math.abs(enemy.excc));
  enemy.exccwmax = u8(enemy.exccw);
  enemy.eyccw = s8(Math.abs(enemy.eycc));
  enemy.eyccwmax = u8(enemy.eyccw);
  enemy.exccadd = enemy.excc > 0 ? 1 : -1;
  enemy.eyccadd = enemy.eycc > 0 ? 1 : -1;
  enemy.special = false;
  enemy.iced = 0;

  if (dat.xRev === 0) enemy.exrev = 100;
  else if (dat.xRev === -99) enemy.exrev = 0;
  else enemy.exrev = dat.xRev;

  if (dat.yRev === 0) enemy.eyrev = 100;
  else if (dat.yRev === -99) enemy.eyrev = 0;
  else enemy.eyrev = dat.yRev;

  enemy.exca = enemy.xaccel > 0 ? 1 : -1;
  enemy.eyca = enemy.yaccel > 0 ? 1 : -1;

  enemy.enemytype = eDatI;

  for (let i = 0; i < 3; ++i) {
    if (enemy.tur[i] === 252) enemy.eshotwait[i] = 1;
    else if (enemy.tur[i] > 0) enemy.eshotwait[i] = 20;
    else enemy.eshotwait[i] = 255;
  }
  for (let i = 0; i < 20; ++i) enemy.egr[i] = dat.eGraphic[i];
  enemy.size = dat.eSize;
  enemy.linknum = 0;
  enemy.edamaged = dat.dAni < 0;
  enemy.enemydie = dat.eEnemyDie;

  enemy.freq[1 - 1] = dat.freq[1 - 1];
  enemy.freq[2 - 1] = dat.freq[2 - 1];
  enemy.freq[3 - 1] = dat.freq[3 - 1];

  enemy.edani = dat.dAni;
  enemy.edgr = dat.dGr;
  enemy.edlevel = dat.dLevel;

  enemy.fixedmovey = 0;

  enemy.filter = 0x00;

  // `value * 0.75f` etc.: float arithmetic, truncated to int.
  const ftrunc = (v: number) => Math.trunc(Math.fround(v));
  let tempValue = 0;
  if (dat.value > 1 && dat.value < 10000) {
    switch (g.difficultyLevel) {
      case -1:
      case DIFFICULTY_WIMP:
        tempValue = ftrunc(fmul(dat.value, 0.75));
        break;
      case DIFFICULTY_EASY:
      case DIFFICULTY_NORMAL:
        tempValue = dat.value;
        break;
      case DIFFICULTY_HARD:
        tempValue = ftrunc(fmul(dat.value, 1.125));
        break;
      case DIFFICULTY_IMPOSSIBLE:
        tempValue = ftrunc(fmul(dat.value, 1.5));
        break;
      case DIFFICULTY_INSANITY:
        tempValue = dat.value * 2;
        break;
      case DIFFICULTY_SUICIDE:
        tempValue = ftrunc(fmul(dat.value, 2.5));
        break;
      case DIFFICULTY_MANIACAL:
      case DIFFICULTY_ZINGLON:
        tempValue = dat.value * 4;
        break;
      case DIFFICULTY_NORTANEOUS:
      case DIFFICULTY_10:
        tempValue = dat.value * 8;
        break;
    }
    if (tempValue > 10000) tempValue = 10000;
    enemy.evalue = s16(tempValue);
  } else {
    enemy.evalue = dat.value;
  }

  let tempArmor = 1;
  if (dat.armor > 0) {
    if (dat.armor !== 255) {
      switch (g.difficultyLevel) {
        case -1:
        case DIFFICULTY_WIMP:
          tempArmor = ftrunc(fmul(dat.armor, 0.5) + 1);
          break;
        case DIFFICULTY_EASY:
          tempArmor = ftrunc(fmul(dat.armor, 0.75) + 1);
          break;
        case DIFFICULTY_NORMAL:
          tempArmor = dat.armor;
          break;
        case DIFFICULTY_HARD:
          tempArmor = ftrunc(fmul(dat.armor, 1.2));
          break;
        case DIFFICULTY_IMPOSSIBLE:
          tempArmor = ftrunc(fmul(dat.armor, 1.5));
          break;
        case DIFFICULTY_INSANITY:
          tempArmor = ftrunc(fmul(dat.armor, 1.8));
          break;
        case DIFFICULTY_SUICIDE:
          tempArmor = dat.armor * 2;
          break;
        case DIFFICULTY_MANIACAL:
          tempArmor = dat.armor * 3;
          break;
        case DIFFICULTY_ZINGLON:
          tempArmor = dat.armor * 4;
          break;
        case DIFFICULTY_NORTANEOUS:
        case DIFFICULTY_10:
          tempArmor = dat.armor * 8;
          break;
      }

      if (tempArmor > 254) {
        tempArmor = 254;
      }
    } else {
      tempArmor = 255;
    }

    enemy.armorleft = u8(tempArmor);

    avail = 0;
    enemy.scoreitem = false;
  } else {
    avail = 2;
    enemy.armorleft = 255;
    if (enemy.evalue !== 0) enemy.scoreitem = true;
  }

  if (!enemy.scoreitem) {
    g.totalEnemy = u16(g.totalEnemy + 1); /*Destruction ratio*/
  }

  /* indicates what to set ENEMYAVAIL to */
  return avail;
}

/** JE_createNewEventEnemy (tyrian2.c L4064-4125): spawns the current event's enemy; sets `b`. */
export function JE_createNewEventEnemy(enemyTypeOfs: number, enemyOffset: number, uniqueShapeTableI: number): void {
  b = 0;

  for (let i = enemyOffset; i < enemyOffset + 25; i++) {
    if (g.enemyAvail[i] === 1) {
      b = i + 1;
      break;
    }
  }

  if (b === 0) return;

  const ev = eventAt(g.eventLoc - 1);

  tempW = u16(ev.eventDat + enemyTypeOfs);

  const e = g.enemy[b - 1];
  g.enemyAvail[b - 1] = JE_makeEnemy(e, tempW, uniqueShapeTableI);

  if (ev.eventDat2 !== -99) {
    switch (enemyOffset) {
      case 0:
        e.ex = s16(ev.eventDat2 - (g.mapX - 1) * 24);
        e.ey = s16(e.ey - g.backMove2);
        break;
      case 25:
      case 75:
        e.ex = s16(ev.eventDat2 - (g.mapX - 1) * 24 - 12);
        e.ey = s16(e.ey - g.backMove);
        break;
      case 50:
        if (g.background3x1) e.ex = s16(ev.eventDat2 - (g.mapX - 1) * 24 - 12);
        else e.ex = s16(ev.eventDat2 - g.mapX3 * 24 - 24 * 2 + 6);
        e.ey = s16(e.ey - g.backMove3);

        if (g.background3x1b) e.ex = s16(e.ex - 6);
        break;
    }
    e.ey = -28;
    if (g.background3x1b && enemyOffset === 50) e.ey = s16(e.ey + 4);
  }

  if (g.smallEnemyAdjust && e.size === 0) {
    e.ex = s16(e.ex - 10);
    e.ey = s16(e.ey - 7);
  }

  e.ey = s16(e.ey + ev.eventDat5);
  e.eyc = s8(e.eyc + ev.eventDat3);
  e.linknum = u8(ev.eventDat4);
  e.fixedmovey = ev.eventDat6;
}

/** JE_eventJump (tyrian2.c L4127-4146): jump curLoc (65535 = return), and the event pointer with it. */
export function JE_eventJump(jump: number): void {
  jump = u16(jump);
  let tempW: number;

  if (jump === 65535) {
    g.curLoc = g.returnLoc;
  } else {
    g.returnLoc = u16(g.curLoc + 1);
    g.curLoc = jump;
  }
  tempW = 0;
  do {
    tempW++;
  } while (!(eventAt(tempW - 1).eventTime >= g.curLoc));
  g.eventLoc = tempW - 1;
}

/**
 * JE_searchFor (tyrian2.c L4148-4172): whether a live enemy has link number PLType; `out_index`
 * receives the last one found. In galaga mode it also doubles every match's value.
 */
export function JE_searchFor(PLType: number, out_index?: { value: number }): boolean {
  PLType = u8(PLType);
  let found_id = -1;

  for (let i = 0; i < 100; i++) {
    if (g.enemyAvail[i] === 0 && g.enemy[i].linknum === PLType) {
      found_id = i;
      if (g.galagaMode) g.enemy[i].evalue = s16(g.enemy[i].evalue + g.enemy[i].evalue);
    }
  }

  if (found_id !== -1) {
    if (out_index) out_index.value = found_id;
    return true;
  } else {
    return false;
  }
}

/** Sets which enemies an "Enemy Global" event addresses via newPL (eventdat3 80..89). */
function applyNewPL(ev: LevelEvent): void {
  if (ev.eventDat3 > 79 && ev.eventDat3 < 90) ev.eventDat4 = g.newPL[ev.eventDat3 - 80];
}

/**
 * JE_eventSystem (tyrian2.c L4174-5029): runs eventRec[eventLoc-1] and advances eventLoc. JE_main
 * calls it while `eventRec[eventLoc-1].eventtime <= curLoc && eventLoc <= maxEvent`.
 */
export function JE_eventSystem(): void {
  const ev = eventAt(g.eventLoc - 1);
  let temp: number;

  switch (ev.eventType) {
    case 1:
      g.starfield_speed = ev.eventDat;
      break;

    case 2:
      g.map1YDelay = 1;
      g.map1YDelayMax = 1;
      g.map2YDelay = 1;
      g.map2YDelayMax = 1;

      g.backMove = u16(ev.eventDat);
      g.backMove2 = u16(ev.eventDat2);

      if (g.backMove2 > 0) g.explodeMove = g.backMove2;
      else g.explodeMove = g.backMove;

      g.backMove3 = u16(ev.eventDat3);

      if (g.backMove > 0) g.stopBackgroundNum = 0;
      break;

    case 3:
      g.backMove = 1;
      g.map1YDelay = 3;
      g.map1YDelayMax = 3;
      g.backMove2 = 1;
      g.map2YDelay = 2;
      g.map2YDelayMax = 2;
      g.backMove3 = 1;
      break;

    case 4:
      g.stopBackgrounds = true;
      switch (ev.eventDat) {
        case 0:
        case 1:
          g.stopBackgroundNum = 1;
          break;
        case 2:
          g.stopBackgroundNum = 2;
          break;
        case 3:
          g.stopBackgroundNum = 3;
          break;
      }
      break;

    case 5: {
      // load enemy shape banks
      const newEnemyShapeTables = [
        u8(ev.eventDat > 0 ? ev.eventDat : 0),
        u8(ev.eventDat2 > 0 ? ev.eventDat2 : 0),
        u8(ev.eventDat3 > 0 ? ev.eventDat3 : 0),
        u8(ev.eventDat4 > 0 ? ev.eventDat4 : 0),
      ];

      for (let i = 0; i < newEnemyShapeTables.length; ++i) {
        if (g.enemySpriteSheetIds[i] !== newEnemyShapeTables[i]) {
          if (newEnemyShapeTables[i] > 0) {
            if (newEnemyShapeTables[i] > shapeFile.length) throw new Error(`event 5: shape table ${newEnemyShapeTables[i]}`);
            g.enemySpriteSheets[i] = g.res.loadCompShapes(shapeFile[newEnemyShapeTables[i] - 1]);
          } else g.enemySpriteSheets[i] = null; // free_sprite2s

          g.enemySpriteSheetIds[i] = newEnemyShapeTables[i];
        }
      }
      break;
    }

    case 6 /* Ground Enemy */:
      JE_createNewEventEnemy(0, 25, 0);
      break;

    case 7 /* Top Enemy */:
      JE_createNewEventEnemy(0, 50, 0);
      break;

    case 8:
      g.starActive = false;
      break;

    case 9:
      g.starActive = true;
      break;

    case 10 /* Ground Enemy 2 */:
      JE_createNewEventEnemy(0, 75, 0);
      break;

    case 11:
      if (g.allPlayersGone || ev.eventDat === 1) {
        g.reallyEndLevel = true;
      } else if (!g.endLevel) {
        g.readyToEndLevel = false;
        g.endLevel = true;
        g.levelEnd = 40;
      }
      break;

    case 12: {
      /* Custom 4x4 Ground Enemy */
      let temp = 0;
      switch (ev.eventDat6) {
        case 0:
        case 1:
          temp = 25;
          break;
        case 2:
          temp = 0;
          break;
        case 3:
          temp = 50;
          break;
        case 4:
          temp = 75;
          break;
      }
      ev.eventDat6 = 0; /* We use EVENTDAT6 for the background */
      JE_createNewEventEnemy(0, temp, 0);
      JE_createNewEventEnemy(1, temp, 0);
      if (b > 0) g.enemy[b - 1].ex = s16(g.enemy[b - 1].ex + 24);
      JE_createNewEventEnemy(2, temp, 0);
      if (b > 0) g.enemy[b - 1].ey = s16(g.enemy[b - 1].ey - 28);
      JE_createNewEventEnemy(3, temp, 0);
      if (b > 0) {
        g.enemy[b - 1].ex = s16(g.enemy[b - 1].ex + 24);
        g.enemy[b - 1].ey = s16(g.enemy[b - 1].ey - 28);
      }
      break;
    }
    case 13:
      g.enemiesActive = false;
      break;

    case 14:
      g.enemiesActive = true;
      break;

    case 15 /* Sky Enemy */:
      JE_createNewEventEnemy(0, 0, 0);
      break;

    case 16: {
      // Window Text
      const id = ev.eventDat;
      if (id < 1 || id > 9) {
        // The C logs "Event has invalid window text ID".
        break;
      }
      JE_drawTextWindow(g.outputs[id - 1]);
      g.soundQueue[3] = windowTextSamples[id - 1];
      break;
    }

    case 17 /* Ground Bottom */:
      JE_createNewEventEnemy(0, 25, 0);
      if (b > 0) g.enemy[b - 1].ey = s16(190 + ev.eventDat5);
      break;

    case 18 /* Sky Enemy on Bottom */:
      JE_createNewEventEnemy(0, 0, 0);
      if (b > 0) g.enemy[b - 1].ey = s16(190 + ev.eventDat5);
      break;

    case 19: {
      /* Enemy Global Move */
      let initial_i = 0;
      let max_i = 0;
      let all_enemies = false;

      if (ev.eventDat3 > 79 && ev.eventDat3 < 90) {
        initial_i = 0;
        max_i = 100;
        all_enemies = false;
        ev.eventDat4 = g.newPL[ev.eventDat3 - 80];
      } else {
        switch (ev.eventDat3) {
          case 0:
            initial_i = 0;
            max_i = 100;
            all_enemies = false;
            break;
          case 2:
            initial_i = 0;
            max_i = 25;
            all_enemies = true;
            break;
          case 1:
            initial_i = 25;
            max_i = 50;
            all_enemies = true;
            break;
          case 3:
            initial_i = 50;
            max_i = 75;
            all_enemies = true;
            break;
          case 99:
            initial_i = 0;
            max_i = 100;
            all_enemies = true;
            break;
        }
      }

      for (let i = initial_i; i < max_i; i++) {
        const e = g.enemy[i];
        if (all_enemies || e.linknum === ev.eventDat4) {
          if (ev.eventDat !== -99) e.exc = s8(ev.eventDat);

          if (ev.eventDat2 !== -99) e.eyc = s8(ev.eventDat2);

          if (ev.eventDat6 !== 0) e.fixedmovey = ev.eventDat6;

          if (ev.eventDat6 === -99) e.fixedmovey = 0;

          if (ev.eventDat5 > 0) e.enemycycle = u8(ev.eventDat5);
        }
      }
      break;
    }

    case 20 /* Enemy Global Accel */:
      applyNewPL(ev);

      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (g.enemyAvail[temp] !== 1 && (e.linknum === ev.eventDat4 || ev.eventDat4 === 0)) {
          if (ev.eventDat !== -99) {
            e.excc = s8(ev.eventDat);
            e.exccw = s8(Math.abs(ev.eventDat));
            e.exccwmax = u8(Math.abs(ev.eventDat));
            if (ev.eventDat > 0) e.exccadd = 1;
            else e.exccadd = -1;
          }

          if (ev.eventDat2 !== -99) {
            e.eycc = s8(ev.eventDat2);
            e.eyccw = s8(Math.abs(ev.eventDat2));
            e.eyccwmax = u8(Math.abs(ev.eventDat2));
            if (ev.eventDat2 > 0) e.eyccadd = 1;
            else e.eyccadd = -1;
          }

          if (ev.eventDat5 > 0) {
            e.enemycycle = u8(ev.eventDat5);
          }
          if (ev.eventDat6 > 0) {
            e.ani = u8(ev.eventDat6);
            e.animin = u8(ev.eventDat5);
            e.animax = 0;
            e.aniactive = 1;
          }
        }
      }
      break;

    case 21:
      g.background3over = 1;
      break;

    case 22:
      g.background3over = 0;
      break;

    case 23 /* Sky Enemy on Bottom */:
      JE_createNewEventEnemy(0, 50, 0);
      if (b > 0) g.enemy[b - 1].ey = s16(180 + ev.eventDat5);
      break;

    case 24 /* Enemy Global Animate */:
      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (e.linknum === ev.eventDat4) {
          e.aniactive = 1;
          e.aniwhenfire = 0;
          if (ev.eventDat2 > 0) {
            e.enemycycle = u8(ev.eventDat2);
            e.animin = e.enemycycle;
          } else {
            e.enemycycle = 0;
          }

          if (ev.eventDat > 0) e.ani = u8(ev.eventDat);

          if (ev.eventDat3 === 1) {
            e.animax = e.ani;
          } else if (ev.eventDat3 === 2) {
            e.aniactive = 2;
            e.animax = e.ani;
            e.aniwhenfire = 2;
          }
        }
      }
      break;

    case 25 /* Enemy Global Damage change */:
      for (temp = 0; temp < 100; temp++) {
        if (ev.eventDat4 === 0 || g.enemy[temp].linknum === ev.eventDat4) {
          if (g.galagaMode) g.enemy[temp].armorleft = u8(roundf(ev.eventDat * Math.trunc(g.difficultyLevel / 2)));
          else g.enemy[temp].armorleft = u8(ev.eventDat);
        }
      }
      break;

    case 26:
      g.smallEnemyAdjust = ev.eventDat !== 0;
      break;

    case 27 /* Enemy Global AccelRev */:
      applyNewPL(ev);

      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (ev.eventDat4 === 0 || e.linknum === ev.eventDat4) {
          if (ev.eventDat !== -99) e.exrev = s8(ev.eventDat);
          if (ev.eventDat2 !== -99) e.eyrev = s8(ev.eventDat2);
          if (ev.eventDat3 !== 0 && ev.eventDat3 < 17) e.filter = u8(ev.eventDat3);
        }
      }
      break;

    case 28:
      g.topEnemyOver = false;
      break;

    case 29:
      g.topEnemyOver = true;
      break;

    case 30:
      g.map1YDelay = 1;
      g.map1YDelayMax = 1;
      g.map2YDelay = 1;
      g.map2YDelayMax = 1;

      g.backMove = u16(ev.eventDat);
      g.backMove2 = u16(ev.eventDat2);
      g.explodeMove = g.backMove2;
      g.backMove3 = u16(ev.eventDat3);
      break;

    case 31 /* Enemy Fire Override */:
      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (ev.eventDat4 === 99 || e.linknum === ev.eventDat4) {
          e.freq[1 - 1] = u8(ev.eventDat);
          e.freq[2 - 1] = u8(ev.eventDat2);
          e.freq[3 - 1] = u8(ev.eventDat3);
          for (let temp2 = 0; temp2 < 3; temp2++) {
            e.eshotwait[temp2] = 1;
          }
          if (e.launchtype > 0) {
            e.launchfreq = u8(ev.eventDat5);
            e.launchwait = 1;
          }
        }
      }
      break;

    case 32: // create enemy
      JE_createNewEventEnemy(0, 50, 0);
      if (b > 0) g.enemy[b - 1].ey = 190;
      break;

    case 33 /* Enemy From other Enemies */:
      if (!((ev.eventDat === 512 || ev.eventDat === 513) && (g.twoPlayerMode || g.onePlayerAction || g.superTyrian))) {
        if (g.superArcadeMode !== SA_NONE) {
          if (ev.eventDat === 534) ev.eventDat = 827;
        } else if (!g.superTyrian) {
          const lives = u8(g.player[0].lives.value);

          if (ev.eventDat === 533 && (lives === 11 || mt_rand() % 15 < lives)) {
            // enemy will drop random special weapon
            ev.eventDat = 829 + (mt_rand() % 6);
          }
        }
        if (ev.eventDat === 534 && g.superTyrian) ev.eventDat = 828 + superTyrianSpecials[mt_rand() % 4];

        for (temp = 0; temp < 100; temp++) {
          if (g.enemy[temp].linknum === ev.eventDat4) g.enemy[temp].enemydie = u16(ev.eventDat);
        }
      }
      break;

    case 34 /* Start Music Fade */:
      if (g.firstGameOver) {
        g.musicFade = true;
        // tempVolume = tyrMusicVolume: audio, not simulated.
      }
      break;

    case 35 /* Play new song */:
      if (g.firstGameOver) {
        play_song(ev.eventDat - 1);
        // set_volume(tyrMusicVolume, fxVolume): audio, not simulated.
      }
      g.musicFade = false;
      break;

    case 36:
      g.readyToEndLevel = true;
      break;

    case 37:
      g.levelEnemyFrequency = u16(ev.eventDat);
      break;

    case 38: {
      g.curLoc = u16(ev.eventDat);
      let new_event_loc = 1;
      for (tempW = 0; tempW < g.maxEvent; tempW++) {
        if (eventAt(tempW).eventTime <= g.curLoc) new_event_loc = tempW + 1 - 1;
      }
      g.eventLoc = new_event_loc;
      break;
    }

    case 39 /* Enemy Global Linknum Change */:
      for (temp = 0; temp < 100; temp++) {
        if (g.enemy[temp].linknum === ev.eventDat) g.enemy[temp].linknum = u8(ev.eventDat2);
      }
      break;

    case 40 /* Enemy Continual Damage */:
      g.enemyContinualDamage = true;
      break;

    case 41:
      if (ev.eventDat === 0) {
        g.enemyAvail.fill(1);
      } else {
        for (let x = 0; x <= 24; x++) g.enemyAvail[x] = 1;
      }
      break;

    case 42:
      g.background3over = 2;
      break;

    case 43:
      g.background2over = u8(ev.eventDat);
      break;

    case 44:
      g.filterActive = ev.eventDat > 0;
      g.filterFade = ev.eventDat === 2;
      g.levelFilter = s8(ev.eventDat2);
      g.levelBrightness = ev.eventDat3;
      g.levelFilterNew = s8(ev.eventDat4);
      g.levelBrightnessChg = ev.eventDat5;
      g.filterFadeStart = ev.eventDat6 === 0;
      break;

    case 45 /* arcade-only enemy from other enemies */:
      if (!g.superTyrian) {
        const lives = u8(g.player[0].lives.value);

        if (ev.eventDat === 533 && (lives === 11 || mt_rand() % 15 < lives)) {
          ev.eventDat = 829 + (mt_rand() % 6);
        }
        if (g.twoPlayerMode || g.onePlayerAction) {
          for (temp = 0; temp < 100; temp++) {
            if (g.enemy[temp].linknum === ev.eventDat4) g.enemy[temp].enemydie = u16(ev.eventDat);
          }
        }
      }
      break;

    case 46: // change difficulty
      if (ev.eventDat3 !== 0) g.damageRate = u8(ev.eventDat3);

      if (ev.eventDat2 === 0 || g.twoPlayerMode || g.onePlayerAction) {
        g.difficultyLevel = s8(g.difficultyLevel + ev.eventDat);
        if (g.difficultyLevel < DIFFICULTY_EASY) g.difficultyLevel = DIFFICULTY_EASY;
        if (g.difficultyLevel > DIFFICULTY_10) g.difficultyLevel = DIFFICULTY_10;
      }
      break;

    case 47 /* Enemy Global AccelRev */:
      for (temp = 0; temp < 100; temp++) {
        if (ev.eventDat4 === 0 || g.enemy[temp].linknum === ev.eventDat4) g.enemy[temp].armorleft = u8(ev.eventDat);
      }
      break;

    case 48 /* Background 2 Cannot be Transparent */:
      g.background2notTransparent = true;
      break;

    case 49:
    case 50:
    case 51:
    case 52: {
      const tempDat2 = ev.eventDat;
      ev.eventDat = 0;
      const tempDat = ev.eventDat3;
      ev.eventDat3 = 0;
      const tempDat3 = ev.eventDat6;
      ev.eventDat6 = 0;
      g.res.enemyDat[0].armor = u8(tempDat3);
      g.res.enemyDat[0].eGraphic[1 - 1] = u16(tempDat2);
      let temp = 0;
      switch (ev.eventType - 48) {
        case 1:
          temp = 25;
          break;
        case 2:
          temp = 0;
          break;
        case 3:
          temp = 50;
          break;
        case 4:
          temp = 75;
          break;
      }
      JE_createNewEventEnemy(0, temp, tempDat);
      ev.eventDat = tempDat2;
      ev.eventDat3 = tempDat;
      ev.eventDat6 = tempDat3;
      break;
    }

    case 53:
      g.forceEvents = ev.eventDat !== 99;
      break;

    case 54:
      JE_eventJump(ev.eventDat);
      break;

    case 55 /* Enemy Global AccelRev */:
      applyNewPL(ev);

      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (ev.eventDat4 === 0 || e.linknum === ev.eventDat4) {
          if (ev.eventDat !== -99) e.xaccel = u8(ev.eventDat);
          if (ev.eventDat2 !== -99) e.yaccel = u8(ev.eventDat2);
        }
      }
      break;

    case 56 /* Ground2 Bottom */:
      JE_createNewEventEnemy(0, 75, 0);
      if (b > 0) g.enemy[b - 1].ey = 190;
      break;

    case 57:
      g.superEnemy254Jump = u16(ev.eventDat);
      break;

    case 60 /*Assign Special Enemy*/:
      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (e.linknum === ev.eventDat4) {
          e.special = true;
          e.flagnum = u8(ev.eventDat);
          e.setto = ev.eventDat2 === 1;
        }
      }
      break;

    case 61: // if specific flag set to specific value, skip events
      if (Number(g.globalFlags[ev.eventDat - 1]) === ev.eventDat2) g.eventLoc = u16(g.eventLoc + ev.eventDat3);
      break;

    case 62 /*Play sound effect*/:
      g.soundQueue[3] = u8(ev.eventDat);
      break;

    case 63: // skip events if not in 2-player mode
      if (!g.twoPlayerMode && !g.onePlayerAction) g.eventLoc = u16(g.eventLoc + ev.eventDat);
      break;

    case 64:
      if (!(ev.eventDat === 6 && g.twoPlayerMode && g.difficultyLevel > DIFFICULTY_NORMAL)) {
        g.smoothies[ev.eventDat - 1] = ev.eventDat2 !== 0;
        temp = u8(ev.eventDat);
        if (temp === 5) temp = 3;
        g.smoothie_data[temp - 1] = u8(ev.eventDat3);
      }
      break;

    case 65:
      g.background3x1 = ev.eventDat === 0;
      break;

    case 66 /*If not on this difficulty level or higher then...*/:
      if (g.initialDifficulty <= ev.eventDat) g.eventLoc = u16(g.eventLoc + ev.eventDat2);
      break;

    case 67:
      g.levelTimer = ev.eventDat === 1;
      g.levelTimerCountdown = u16(ev.eventDat3 * 100);
      g.levelTimerJumpTo = u16(ev.eventDat2);
      break;

    case 68:
      g.randomExplosions = ev.eventDat === 1;
      break;

    case 69:
      for (const p of g.player) p.invulnerable_ticks = u32(ev.eventDat);
      break;

    case 70:
      if (ev.eventDat2 === 0) {
        /*1-10*/
        let found = false;

        for (temp = 1; temp <= 19; temp++) found = found || JE_searchFor(temp);

        if (!found) JE_eventJump(ev.eventDat);
      } else if (
        !JE_searchFor(ev.eventDat2) &&
        (ev.eventDat3 === 0 || !JE_searchFor(ev.eventDat3)) &&
        (ev.eventDat4 === 0 || !JE_searchFor(ev.eventDat4))
      ) {
        JE_eventJump(ev.eventDat);
      }
      break;

    case 71: {
      // ((mapYPos - &megaData1.mainmap) / sizeof(JE_byte *)) * 2 <= (unsigned)eventdat2, in
      // unsigned long arithmetic: a negative pointer offset compares as huge.
      const pos = g.mapYPos * 2;
      if (pos >= 0 && pos <= u32(ev.eventDat2)) JE_eventJump(ev.eventDat);
      break;
    }

    case 72:
      g.background3x1b = ev.eventDat === 1;
      break;

    case 73:
      g.skyEnemyOverAll = ev.eventDat === 1;
      break;

    case 74 /* Enemy Global BounceParams */:
      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (ev.eventDat4 === 0 || e.linknum === ev.eventDat4) {
          if (ev.eventDat5 !== -99) e.xminbounce = ev.eventDat5;

          if (ev.eventDat6 !== -99) e.yminbounce = ev.eventDat6;

          if (ev.eventDat !== -99) e.xmaxbounce = ev.eventDat;

          if (ev.eventDat2 !== -99) e.ymaxbounce = ev.eventDat2;
        }
      }
      break;

    case 75: {
      let temp_no_clue = false; // TODO: figure out what this is doing

      for (temp = 0; temp < 100; temp++) {
        const e = g.enemy[temp];
        if (g.enemyAvail[temp] === 0 && e.eyc === 0 && e.linknum >= ev.eventDat && e.linknum <= ev.eventDat2) {
          temp_no_clue = true;
        }
      }

      if (temp_no_clue) {
        const enemy_i = { value: 0 };
        do {
          temp = u8(mt_rand_mod(ev.eventDat2 + 1 - ev.eventDat) + ev.eventDat);
        } while (!(JE_searchFor(temp, enemy_i) && g.enemy[enemy_i.value].eyc === 0));

        g.newPL[ev.eventDat3 - 80] = temp;
      } else {
        g.newPL[ev.eventDat3 - 80] = 255;
        if (ev.eventDat4 > 0) {
          /*Skip*/
          g.curLoc = u16(eventAt(g.eventLoc - 1 + ev.eventDat4).eventTime - 1);
          g.eventLoc = u16(g.eventLoc + ev.eventDat4 - 1);
        }
      }

      break;
    }

    case 76:
      g.returnActive = true;
      break;

    case 77:
      g.mapYPos = 0;
      g.mapYPos += Math.trunc(ev.eventDat / 2);
      if (ev.eventDat2 > 0) {
        g.mapY2Pos = 0;
        g.mapY2Pos += Math.trunc(ev.eventDat2 / 2);
      } else {
        g.mapY2Pos = 0;
        g.mapY2Pos += Math.trunc(ev.eventDat / 2);
      }
      break;

    case 78:
      if (g.galagaShotFreq < 10) g.galagaShotFreq++;
      break;

    case 79:
      g.boss_bar[0].link_num = u8(ev.eventDat);
      g.boss_bar[1].link_num = u8(ev.eventDat2);
      break;

    case 80: // skip events if in 2-player mode
      if (g.twoPlayerMode) g.eventLoc = u16(g.eventLoc + ev.eventDat);
      break;

    case 81 /*WRAP2*/:
      g.BKwrap2 = 0;
      g.BKwrap2 += Math.trunc(ev.eventDat / 2);
      g.BKwrap2to = 0;
      g.BKwrap2to += Math.trunc(ev.eventDat2 / 2);
      break;

    case 82 /*Give SPECIAL WEAPON*/:
      g.player[0].items.special = u8(ev.eventDat);
      g.shotMultiPos[SHOT_SPECIAL] = 0;
      g.shotRepeat[SHOT_SPECIAL] = 0;
      g.shotMultiPos[SHOT_SPECIAL2] = 0;
      g.shotRepeat[SHOT_SPECIAL2] = 0;
      break;

    default:
      // The C logs "Event has invalid type." and moves on.
      break;
  }

  g.eventLoc = u16(g.eventLoc + 1);
}

/**
 * draw_boss_bar (tyrian2.c L5117-5161): updates boss_bar[] (which enemy, how much armor, the hit
 * flash). The bars are HTML: shown while link_num != 0, with x as below; JE_barX isn't recorded.
 */
export function draw_boss_bar(): void {
  for (let bi = 0; bi < g.boss_bar.length; bi++) {
    if (g.boss_bar[bi].link_num === 0) continue;

    let armor = 256; // higher than armor max

    for (let e = 0; e < g.enemy.length; e++) {
      // find most damaged
      if (g.enemyAvail[e] !== 1 && g.enemy[e].linknum === g.boss_bar[bi].link_num)
        if (g.enemy[e].armorleft < armor) armor = g.enemy[e].armorleft;
    }

    if (armor > 255 || armor === 0)
      // boss dead?
      g.boss_bar[bi].link_num = 0;
    else g.boss_bar[bi].armor = armor === 255 ? 254 : armor; // 255 would make the bar too long
  }

  const bars = (g.boss_bar[0].link_num !== 0 ? 1 : 0) + (g.boss_bar[1].link_num !== 0 ? 1 : 0);

  // if only one bar left, make it the first one
  if (bars === 1 && g.boss_bar[0].link_num === 0) {
    g.boss_bar[0] = { ...g.boss_bar[1] };
    g.boss_bar[1].link_num = 0;
  }

  for (let bi = 0; bi < bars; bi++) {
    // x = bars == 2 ? (bi == 0 ? 125 : 185) : (levelTimer ? 250 : 155);
    // JE_barX(x - 25, 7, x + 25, 12, 115);
    // JE_barX(x - armor / 10, 7, x + (armor + 5) / 10, 12, 118 + color);

    if (g.boss_bar[bi].color > 0) g.boss_bar[bi].color--;
  }
}

// --- Level loading (JE_loadMap, tyrian2.c L2295-3117) ---

/** str_pop_int (mainint.c L2690): every integer in a whitespace-separated string. */
function strPopInts(s: string): number[] {
  const out: number[] = [];
  let rest = s;
  for (;;) {
    const m = /^\s*([+-]?\d+)/.exec(rest);
    if (!m) return out;
    out.push(parseInt(m[1], 10));
    rest = rest.slice(m[0].length);
  }
}

const scriptCache = new WeakMap<Uint8Array, EpisodeScript>();

/** Reads levelsN.dat line by line, as JE_loadMap's readEpisodeString does. */
class EpisodeReader {
  private pos = 0;
  constructor(private readonly script: EpisodeScript) {}
  read(): string {
    if (this.pos >= this.script.lines.length) throw new Error("Failed to read from the episode file: past the end");
    return this.script.lines[this.pos++];
  }
}

/** Thrown by JE_loadMap when the episode script reaches `]Q` (end of episode). */
export class EpisodeEndError extends Error {}

/** What JE_loadMapSteps pauses for: the item screen (`]I[` calls JE_itemScreen in the C). */
export type LoadMapPause = "itemScreen";

/** musmast.h DEFAULT_SONG_BUY */
const DEFAULT_SONG_BUY = 2;

/**
 * JE_loadMap (tyrian2.c L2295-3117): steps through the episode script (levelsN.dat) from section
 * g.mainLevel until a `]L[` command, then loads that level from tyrianN.lvl and its tiles from
 * shapes?.dat into g.lvl and the level globals.
 *
 * A generator, so the host can show the item screen where the C calls JE_itemScreen (`]I[`): it
 * yields "itemScreen" after recording the shop lists, and the host runs the item screen
 * (src/sim/game_menu.ts) to completion before resuming it. The item screen ends by choosing a
 * destination (mainLevel + jumpSection) or quitting (gameLoaded with mainLevel 0). Returns true
 * when a level was loaded, false when the player quit from the item screen (back to the title).
 * JE_loadMap and JE_loadMapAsync below drive it.
 *
 * Ported: every script command's effect on game state. Not ported (no-ops, marked below):
 * pictures, fades, palette changes and text screens (the `]W` text is kept in
 * g.levelWarningText), the end-of-episode sequence (`]Q` throws EpisodeEndError), demos, saving,
 * loading a saved game from the item screen, and network sync.
 */
export function* JE_loadMapSteps(files: TyrianFiles): Generator<LoadMapPause, boolean, void> {
  g.lastCubeMax = g.cubeMax;

  /*Defaults*/
  g.songBuy = DEFAULT_SONG_BUY; /*Item Screen default song*/

  /* Load LEVELS.DAT - Section = MAINLEVEL */
  g.saveLevel = g.mainLevel;

  // new_game:
  g.galagaMode = false;
  g.useLastBank = false;
  g.extraGame = false;
  // haltGame = false: menus, not simulated.

  g.gameLoaded = false;

  const episodeData = requireFile(files, `levels${g.episodeNum}.dat`);
  let script = scriptCache.get(episodeData);
  if (!script) {
    script = parseEpisodeScript(episodeData);
    scriptCache.set(episodeData, script);
  }

  let loadLevelOk = false;

  if (!g.playDemo) {
    do {
      const episodeFile = new EpisodeReader(script);

      g.jumpSection = false;
      loadLevelOk = false;

      /* Seek Section # Mainlevel */
      for (let i = 0; i < g.mainLevel; ) {
        const s = episodeFile.read();
        if (s[0] === "*") i++;
      }

      // ESCPressed = false

      do {
        if (g.gameLoaded) {
          if (g.mainLevel === 0) {
            // if quit itemscreen
            return false; // back to title screen
          }
          // goto new_game: only the item screen's load-game menu gets here, and it isn't ported.
          throw new Error("JE_loadMap: loading a saved game isn't ported");
        }

        let s = episodeFile.read();

        if (s[0] === "]") {
          switch (s[1]) {
            case "A": // Show animation.
              // playAnim("tyrend.anm", 0, 7): not ported.
              break;

            case "G": // Set next level choices.
              g.mapOrigin = u16(atoi(s.slice(4)));
              g.mapPNum = u16(atoi(s.slice(7)));
              for (let i = 0; i < g.mapPNum; i++) {
                g.mapPlanet[i] = u8(atoi(s.slice(1 + (i + 1) * 8)));
                g.mapSection[i] = u8(atoi(s.slice(4 + (i + 1) * 8)));
              }
              break;

            case "?": {
              // Set data cubes.
              let temp = u8(atoi(s.slice(4)));
              if (temp > g.cubeList.length) temp = g.cubeList.length;
              for (let i = 0; i < temp; i++) g.cubeList[i] = u16(atoi(s.slice(3 + (i + 1) * 4)));
              if (g.cubeMax > temp) g.cubeMax = temp;
              break;
            }

            case "!": // Set number of data cubes acquired.
              g.cubeMax = u16(atoi(s.slice(4))); /*Auto set CubeMax*/
              if (g.cubeMax > g.cubeList.length) g.cubeMax = g.cubeList.length;
              break;

            case "+": {
              // Increase number of data cubes acquired.
              const temp = u8(atoi(s.slice(4)));
              g.cubeMax = u16(g.cubeMax + temp);
              if (g.cubeMax > g.cubeList.length) g.cubeMax = g.cubeList.length;
              break;
            }

            case "g": // Enable GALAGA mode.  (Used for bonus games.)
              g.galagaMode = true;

              g.player[1].items = structuredClone(g.player[0].items);
              g.player[1].items.weapon[REAR_WEAPON].id = 15; // Vulcan Cannon
              for (let i = 0; i < g.player[1].items.sidekick.length; ++i) g.player[1].items.sidekick[i] = 0; // None
              break;

            case "x": // Enable bonus game.
              g.extraGame = true;
              break;

            case "e": // Enable ENGAGE mode.  (Used for bonus games.)
              g.doNotSaveBackup = true;
              g.constantDie = false;
              g.onePlayerAction = true;
              g.superTyrian = true;
              g.twoPlayerMode = false;

              g.player[0].cash = 0;

              g.player[0].items.ship = 13; // The Stalker 21.126
              g.player[0].items.weapon[FRONT_WEAPON].id = 39; // Atomic RailGun
              g.player[0].items.weapon[REAR_WEAPON].id = 0; // None
              for (let i = 0; i < g.player[0].items.sidekick.length; ++i) g.player[0].items.sidekick[i] = 0; // None
              g.player[0].items.generator = 2; // Advanced MR-12
              g.player[0].items.shield = 4; // Advanced Integrity Field
              g.player[0].items.special = 0; // None

              g.player[0].items.weapon[FRONT_WEAPON].power = 3;
              g.player[0].items.weapon[REAR_WEAPON].power = 1;
              break;

            case "J": // Jump to section.
              g.mainLevel = u8(atoi(s.slice(3)));
              g.jumpSection = true;
              break;

            case "2": {
              // Jump to section in two-player or one-player arcade.
              const temp = u8(atoi(s.slice(3)));
              if (g.twoPlayerMode || g.onePlayerAction) {
                g.mainLevel = temp;
                g.jumpSection = true;
              }
              break;
            }

            case "w": {
              // Jump to section if player has Stalker 21.126.
              const temp = u8(atoi(s.slice(3))); /*Allowed to go to Time War?*/
              if (g.player[0].items.ship === 13) {
                g.mainLevel = temp;
                g.jumpSection = true;
              }
              break;
            }

            case "t": {
              // Jump to section if level timer expired.
              const temp = u8(atoi(s.slice(3)));
              if (g.levelTimer && g.levelTimerCountdown === 0) {
                g.mainLevel = temp;
                g.jumpSection = true;
              }
              break;
            }

            case "l": {
              // Jump to section if player died.
              const temp = u8(atoi(s.slice(3)));
              if (!(g.player[0].is_alive && (!g.twoPlayerMode || g.player[1].is_alive))) {
                g.mainLevel = temp;
                g.jumpSection = true;
              }
              break;
            }

            case "s": // Set section that will be stored in saved game to current section.
              g.saveLevel = g.mainLevel;
              break; /*store savepoint*/

            case "b": // Explicit auto-save.  (Used before bonus games.)
              // JE_saveGame(11, "LAST LEVEL    "): not ported.
              break;

            case "i": // Set menu music track.
              g.songBuy = atoi(s.slice(3)) - 1;
              break;

            case "I": // Menu.
              /*Load Items Available Information*/
              for (const row of g.itemAvail) row.fill(0);

              for (let i = 0; i < 9; ++i) {
                s = episodeFile.read();

                const buf = s.length > 8 ? s.slice(8) : "";

                let j = 0;
                for (const temp of strPopInts(buf)) g.itemAvail[i][j++] = u8(temp);
                g.itemAvailMax[i] = j;
              }

              yield "itemScreen"; // JE_itemScreen()
              break;

            case "L": {
              // Play level.
              g.nextLevel = u8(atoi(s.slice(9)));
              g.levelName = s.slice(13, 22);
              g.levelSong = u8(atoi(s.slice(22)));
              if (g.nextLevel === 0) {
                g.nextLevel = u8(g.mainLevel + 1);
              }
              g.lvlFileNum = u8(atoi(s.slice(25)));
              loadLevelOk = true;
              g.bonusLevelCurrent = s.length > 28 && s[28] === "$";
              g.normalBonusLevelCurrent = s.length > 27 && s[27] === "$";
              g.gameJustLoaded = false;
              break;
            }

            case "@": // Toggle text color bank.
              g.useLastBank = !g.useLastBank;
              break;

            case "Q": // End of episode.
              // Hint text, the ending screens and JE_nextEpisode: not ported.
              throw new EpisodeEndError(`episode ${g.episodeNum} ends at section ${g.mainLevel}`);

            case "P": // Show picture or clear and set palette.
            case "U": // Pan up to picture.
            case "V": // Slide picture up.
            case "R": // Pan right to picture.
            case "C": // Fade to black, clear, and reset palette.
            case "B": // Fade to black.
            case "F": // Flash and clear.
              // Screens between levels: not ported. (JE_main sets the in-level palette.)
              break;

            case "W": // Show text, optionally with warning flashers and sirens.
              if (!g.constantPlay) {
                // (ESCPressed is never set here.)
                const frames = atoi(s.slice(4));
                g.frameCountMax = frames % 10;
                g.levelWarningText = [];

                // Read text.
                for (;;) {
                  s = episodeFile.read();

                  if (s[0] === "#") break;

                  g.levelWarningText.push(s);
                }

                // JE_displayText(): the text screen isn't ported.
              }
              break;

            case "H": // Jump to section if difficulty is less than hard.
              if (g.initialDifficulty < DIFFICULTY_HARD) {
                g.mainLevel = u8(atoi(s.slice(4)));
                g.jumpSection = true;
              }
              break;

            case "h": // Skip next line of script if difficulty is hard or higher.
              if (g.initialDifficulty > DIFFICULTY_NORMAL) {
                s = episodeFile.read();
              }
              break;

            case "S": // (Not used.)
              break;

            case "n": // End of scene.
              break;

            case "M": // Play music track.
              play_song(atoi(s.slice(3)) - 1);
              break;
          }
        }
      } while (!(loadLevelOk || g.jumpSection));
    } while (!loadLevelOk);
  }

  // Demos and fade_black(50): not ported.

  loadLevelFile(files);
  return true;
}

/**
 * JE_loadMap run to completion, with `itemScreen` run synchronously at each `]I[`. The default
 * makes the choice the C makes when nobody is choosing (JE_itemScreenNonInteractive). Returns
 * false if the item screen quit to the title.
 */
export function JE_loadMap(files: TyrianFiles, itemScreen: () => void = JE_itemScreenNonInteractive): boolean {
  const steps = JE_loadMapSteps(files);
  for (;;) {
    const r = steps.next();
    if (r.done) return r.value;
    itemScreen();
  }
}

/** JE_loadMap with an asynchronous item screen (the host's UI). */
export async function JE_loadMapAsync(files: TyrianFiles, itemScreen: () => Promise<void>): Promise<boolean> {
  const steps = JE_loadMapSteps(files);
  for (;;) {
    const r = steps.next();
    if (r.done) return r.value;
    await itemScreen();
  }
}

/** The level-file half of JE_loadMap (tyrian2.c L2934-3117). */
function loadLevelFile(files: TyrianFiles): void {
  const levelFile = requireFile(files, `tyrian${g.episodeNum}.lvl`);
  const { lvlPos } = readLevelPositions(levelFile); // analyzeLevel, done by JE_initEpisode in C

  const level = parseLevel(levelFile, lvlPos[(g.lvlFileNum - 1) * 2]);

  g.mapX = level.mapX;
  g.mapX2 = level.mapX2;
  g.mapX3 = level.mapX3;

  g.levelEnemyMax = level.levelEnemy.length;
  level.levelEnemy.forEach((t, i) => (g.levelEnemy[i] = t));

  g.maxEvent = level.events.length;
  if (g.maxEvent >= EVENT_MAXIMUM) throw new Error("Level has too many events.");
  // eventRec is modified by some events, so each level load gets fresh copies.
  const eventRec: LevelEvent[] = level.events.map((e) => ({ ...e }));
  eventRec.push({ eventTime: 65500, eventType: 0, eventDat: 0, eventDat2: 0, eventDat3: 0, eventDat5: 0, eventDat6: 0, eventDat4: 0 }); /*Not needed but just in case*/

  /* Read Shapes.DAT */
  const shapesFilename = `shapes${level.shapeFile.toLowerCase()}.dat`;
  const shapes = parseShapes(requireFile(files, shapesFilename));

  g.lvl = {
    level,
    eventRec,
    tiles: [levelTiles(level, shapes, 0), levelTiles(level, shapes, 1), levelTiles(level, shapes, 2)],
    shapesFile: shapesFilename,
  };
}

/**
 * The event and message texts JE_loadHelpText (helptext.c L165-222) reads from tyrian.hdt:
 * miscText and outputs. Other help text isn't needed by the sim.
 */
export function loadHelpTextStrings(hdt: Uint8Array): void {
  const r = new BinaryReader(hdt);
  r.u32(); // Episode 1-3 item data position
  const group = (count: number): string[] => {
    readEncryptedString(r);
    const out: string[] = [];
    for (let i = 0; i < count; i++) out.push(readEncryptedString(r));
    readEncryptedString(r);
    return out;
  };
  group(39); /*Online Help*/
  group(21); /*Planet names*/
  const miscText = group(68); /*Miscellaneous text*/
  group(5); /*Little Miscellaneous text*/
  group(11); /*Key names*/ // menuInt_entries[6]
  group(7); /*Main Menu*/
  const outputs = group(9); /*Event text*/
  // The C buffers truncate: miscText to 41 characters, outputs to 30.
  g.miscText = miscText.map((s) => s.slice(0, 41));
  g.outputs = outputs.map((s) => s.slice(0, 30));
}

/**
 * Loads a level the way a new game reaches it: JE_initEpisode(episode) (item data, via
 * buildResources), the event and menu texts, then JE_loadMap from episode-script section
 * `mainLevel`. Episode 1's first level is mainLevel 1 (section 1 jumps to 2, whose item screen
 * leads to section 3's `]L[`: TYRIAN, tyrian1.lvl level 9, or 15 on hard).
 *
 * `itemScreen` runs at each `]I[`; by default the C's non-interactive choice (the last
 * destination the script lists). Returns false if the item screen quit to the title.
 */
export function loadLevel(files: TyrianFiles, episode: number, mainLevel: number, itemScreen?: () => void): boolean {
  loadLevelPrelude(files, episode, mainLevel);
  return JE_loadMap(files, itemScreen);
}

/** loadLevel with the host's asynchronous item screen. */
export function loadLevelAsync(files: TyrianFiles, episode: number, mainLevel: number, itemScreen: () => Promise<void>): Promise<boolean> {
  loadLevelPrelude(files, episode, mainLevel);
  return JE_loadMapAsync(files, itemScreen);
}

function loadLevelPrelude(files: TyrianFiles, episode: number, mainLevel: number): void {
  if (!g.res || g.episodeNum !== episode) g.res = buildResources(files, episode);
  g.episodeNum = episode;
  const hdt = requireFile(files, "tyrian.hdt");
  loadHelpTextStrings(hdt);
  if (!g.menuInt[1]?.length) loadMenuText(hdt);
  g.mainLevel = u8(mainLevel);
}

/**
 * The level a section reaches with its own `]L[` (the first one in the section), for showing
 * where a navigation choice leads. Not in the C; null if the section has no `]L[` of its own.
 */
export function sectionLevelName(files: TyrianFiles, episode: number, section: number): string | null {
  const data = requireFile(files, `levels${episode}.dat`);
  let script = scriptCache.get(data);
  if (!script) {
    script = parseEpisodeScript(data);
    scriptCache.set(data, script);
  }
  const sec = script.sections.find((x) => x.number === section);
  const line = sec?.lines.find((l) => l.startsWith("]L["));
  return line ? line.slice(13, 22).trim() : null;
}

/**
 * The world half of JE_main's start-of-level setup (tyrian2.c L659-969, after JE_loadMap): map
 * pointers and scrolling, level-event state, filters, enemy/shot/explosion tables, and the
 * starfield. Call it after loadLevel and after the player setup that precedes it in JE_main.
 *
 * Left to the integrator (player side, HUD, audio), in JE_main order: player[].is_alive = true,
 * player positions and old_x/old_y (L679-706), JE_loadPic/JE_drawOptions/HUD text (L708-716),
 * JE_getShipInfo() (L751, in varz.ts; needs player items), player velocities and
 * invulnerable_ticks = 100 (L753-759), the JE_main locals warningCol/warningColChange/
 * warningSoundDelay/armorShipDelay (L765-768) and old_weapon_bar, JE_drawTextWindow(miscText[20])
 * (L821), shieldWait/shieldT and player shields (L824-831), superbombs (L836-837),
 * JE_setNewGameSpeed, twoPlayerLinked/linkGunDirec (L874-875), calc_purple_balls_needed
 * (L877-878), yourInGameMenuRequest, player exploding_ticks (L902-903).
 */
export function initLevelWorld(): void {
  // free_sprite2s(&enemySpriteSheets[0..3]) (start_level, L600-603)
  g.enemySpriteSheets.fill(null);

  g.endLevel = false; // L663-666 (before JE_loadMap in C; harmless to repeat)
  g.reallyEndLevel = false;
  g.playerEndLevel = false;

  g.oldDifficultyLevel = g.difficultyLevel; // L682-686
  if (g.episodeNum === EPISODE_AVAILABLE) g.difficultyLevel = s8(g.difficultyLevel - 1);
  if (g.difficultyLevel < DIFFICULTY_EASY) g.difficultyLevel = DIFFICULTY_EASY;

  // JE_loadPic(VGAScreen, twoPlayerMode ? 6 : 3, false): its palette is the in-level palette.
  drawList.palette = pcxpal[(g.twoPlayerMode ? 6 : 3) - 1];

  /* MAPX will already be set correctly */
  g.mapY = 300 - 8;
  g.mapY2 = 600 - 8;
  g.mapY3 = 600 - 8;
  g.mapYPos = g.mapY * 14 - 1; // &megaData1.mainmap[mapY][0] - 1
  g.mapY2Pos = g.mapY2 * 14 - 1;
  g.mapY3Pos = g.mapY3 * 15 - 1;
  g.mapXPos = 0;
  g.mapXOfs = 0;
  g.mapX2Pos = 0;
  g.mapX3Pos = 0;
  g.mapX3Ofs = 0;
  g.mapXbpPos = 0;
  g.mapX2bpPos = 0;
  g.mapX3bpPos = 0;

  g.map1YDelay = 1;
  g.map1YDelayMax = 1;
  g.map2YDelay = 1;
  g.map2YDelayMax = 1;

  g.musicFade = false;

  g.backPos = 0;
  g.backPos2 = 0;
  g.backPos3 = 0;
  g.power = 0;
  g.starfield_speed = 1;

  /* Initialize Level Data and Debug Mode */
  g.levelEnd = 255;
  g.levelEndWarp = -4;
  g.levelEndFxWait = 0;

  g.bonusLevel = false;
  g.readyToEndLevel = false;
  g.firstGameOver = true;
  g.eventLoc = 1;
  g.curLoc = 0;
  g.backMove = 1;
  g.backMove2 = 2;
  g.backMove3 = 3;
  g.explodeMove = 2;
  g.enemiesActive = true;
  for (let temp = 0; temp < 3; temp++) g.button[temp] = false;
  g.stopBackgrounds = false;
  g.stopBackgroundNum = 0;
  g.background3x1 = false;
  g.background3x1b = false;
  g.background3over = 0;
  g.background2over = 1;
  g.topEnemyOver = false;
  g.skyEnemyOverAll = false;
  g.smallEnemyAdjust = false;
  g.starActive = true;
  g.enemyContinualDamage = false;
  g.levelEnemyFrequency = 96;
  g.quitRequested = false;

  for (const bar of g.boss_bar) bar.link_num = 0;

  g.forceEvents = false; /*Force events to continue if background movement = 0*/

  g.superEnemy254Jump = 0; /*When Enemy with PL 254 dies*/

  /* Filter Status */
  g.filterActive = true;
  g.filterFade = true;
  g.filterFadeStart = false;
  g.levelFilter = -99;
  g.levelBrightness = -14;
  g.levelBrightnessChg = 1;

  g.background2notTransparent = false;

  g.lastPower = Math.trunc(g.power / 10);

  /* Set cubes to 0 */
  g.cubeMax = 0;

  /* Secret Level Display */
  g.flash = 0;
  g.flashChange = 1;
  g.displayTime = 0;

  play_song(g.levelSong - 1);

  initialize_starfield();

  g.damageRate = 2; /*Normal Rate for Collision Damage*/

  g.chargeWait = 5;
  g.chargeLevel = 0;
  g.chargeMax = 5;
  g.chargeGr = 0;
  g.chargeGrWait = 3;

  g.portConfigChange = false;

  /*Destruction Ratio*/
  g.totalEnemy = 0;
  g.enemyKilled = 0;

  g.astralDuration = 0;

  g.superArcadePowerUp = 1;

  g.constantLastX = -1;

  g.enemyAvail.fill(1);
  g.enemyShotAvail.fill(true);

  /*Initialize Shots*/
  for (const s of g.playerShotData) Object.assign(s, newPlayerShotData());
  g.shotAvail.fill(0);
  g.shotMultiPos.fill(0);
  g.shotRepeat.fill(1);

  g.button.fill(false);

  g.globalFlags.fill(false);

  for (const e of g.explosions) Object.assign(e, newExplosion());
  for (const r of g.rep_explosions) Object.assign(r, newRepExplosion());

  /* --- Clear Sound Queue --- */
  g.soundQueue.fill(0);
  g.soundQueue[3] = V_GOOD_LUCK;

  g.enemySpriteSheetIds.fill(0);
  for (const e of g.enemy) Object.assign(e, newEnemy());
  enemySheetSlot = new WeakMap();
  enemySerial = new WeakMap();

  for (const code of g.SFCurrentCode) code.fill(0);
  g.SFExecuted.fill(0);

  g.zinglonDuration = 0;
  g.specialWait = 0;
  g.nextSpecialWait = 0;
  g.optionAttachmentMove = 0; /*Launch the Attachments!*/
  g.optionAttachmentLinked = true;

  g.editShip1 = false;
  g.editShip2 = false;

  g.smoothies.fill(false);

  g.levelTimer = false;
  g.randomExplosions = false;

  g.last_superpixel = 0;
  for (const sp of g.superpixels) Object.assign(sp, newSuperpixel());

  g.returnActive = false;

  g.galagaShotFreq = 0;

  if (g.galagaMode) {
    g.difficultyLevel = DIFFICULTY_NORMAL;
  }
  g.galagaLife = 10000;

  // keeps map from scrolling past the top
  g.BKwrap1 = g.BKwrap1to = 14; // &megaData1.mainmap[1][0]
  g.BKwrap2 = g.BKwrap2to = 14; // &megaData2.mainmap[1][0]
  g.BKwrap3 = g.BKwrap3to = 15; // &megaData3.mainmap[1][0]
}
