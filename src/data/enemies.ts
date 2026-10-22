// Enemy definitions (JE_EnemyDatType, OpenTyrian src/episodes.h). They're the last table
// JE_loadItemDat reads (src/episodes.c); parseItemDat in items.ts calls readEnemyDat.
//
// Units are raw, as the original logic uses them: positions in pixels, movement in pixels
// per logic frame, frequencies and delays in logic frames. See JE_makeEnemy (src/tyrian2.c)
// for how each field seeds a live enemy.

import type { BinaryReader } from "./reader";

/** ENEMY_NUM (src/lvlmast.h): the table holds ENEMY_NUM + 1 entries, [0..enemynum]. */
export const ENEMY_NUM = 850;

/** One enemy type. Per-logic-frame quantities are marked "/frame". */
export interface EnemyDat {
  /** ani: animation frame count. */
  ani: number;
  /** tur[3]: weapon (enemy shot) id per turret; 0 = none, 252 is a special case in JE_makeEnemy. */
  tur: number[];
  /** freq[3]: frames between shots per turret. */
  freq: number[];
  /** xmove, ymove: starting velocity, px/frame. */
  xMove: number;
  yMove: number;
  /** xaccel, yaccel: homing toward the player; raw, the game uses value - 89 (JE_drawEnemy). */
  xAccel: number;
  yAccel: number;
  /** xcaccel, ycaccel: cyclic acceleration, raw (see JE_drawEnemy). */
  xCAccel: number;
  yCAccel: number;
  /** startx, starty: spawn position, px (JE_makeEnemy adds 1). */
  startX: number;
  startY: number;
  /** startxc, startyc: random spawn spread, ± px. */
  startXC: number;
  startYC: number;
  /** armor: hit points; 255 is special-cased (takes no damage) in the shot collision code. */
  armor: number;
  /** esize: 1 = 2×2-sprite enemy (JE_drawEnemy). */
  eSize: number;
  /** egraphic[20]: sprite index per animation frame. */
  eGraphic: number[];
  /** explosiontype: bit 0 = air (else ground), bits 1+ = explosion number. */
  explosionType: number;
  /** animate: 0 not yet, 1 always, 2 only when firing. */
  animate: number;
  /** shapebank: sprite sheet id (see LEVELMAK.DOC / JE_makeEnemy). */
  shapeBank: number;
  /** xrev, yrev: velocity reversal limits; 0 means 100, -99 means 0 (JE_makeEnemy). */
  xRev: number;
  yRev: number;
  /** dgr: damaged-state graphic. */
  dGr: number;
  /** dlevel: remaining armor at or below which the damaged state starts. */
  dLevel: number;
  /** dani: damaged-state animation; the sign matters (JE_makeEnemy sets edamaged = dani < 0). */
  dAni: number;
  /** elaunchfreq: frames between launches. */
  eLaunchFreq: number;
  /** elaunchtype: launched enemy type (% 1000) plus special flag (/ 1000). */
  eLaunchType: number;
  /** value: score/bonus value, interpreted by JE_makeEnemy. */
  value: number;
  /** eenemydie: enemy type spawned on death. */
  eEnemyDie: number;
}

/** Read one 77-byte enemy record, in the field order of JE_loadItemDat. */
export function readEnemyDat(r: BinaryReader): EnemyDat {
  return {
    ani: r.u8(),
    tur: r.u8Array(3),
    freq: r.u8Array(3),
    xMove: r.s8(),
    yMove: r.s8(),
    xAccel: r.s8(),
    yAccel: r.s8(),
    xCAccel: r.s8(),
    yCAccel: r.s8(),
    startX: r.s16(),
    startY: r.s16(),
    startXC: r.s8(),
    startYC: r.s8(),
    armor: r.u8(),
    eSize: r.u8(),
    eGraphic: r.u16Array(20),
    explosionType: r.u8(),
    animate: r.u8(),
    shapeBank: r.u8(),
    xRev: r.s8(),
    yRev: r.s8(),
    dGr: r.u16(),
    dLevel: r.s8(),
    dAni: r.s8(),
    eLaunchFreq: r.u8(),
    eLaunchType: r.u16(),
    value: r.s16(),
    eEnemyDie: r.u16(),
  };
}
