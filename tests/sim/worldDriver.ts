// A test driver for the world side of the sim: the parts of JE_main's level loop (tyrian2.c
// L971-2280) that run the backgrounds, events and enemies, in JE_main's order. Player movement,
// player shots, collisions and the HUD are left out (the player is parked at a fixed position).
// It is not the real main loop; it exists to exercise the world port.

import { draw_background_1, draw_background_2, draw_background_2_blend, draw_background_3, JE_checkSmoothies, JE_filterScreen, update_and_draw_starfield } from "../../src/sim/backgrnd";
import { s16, u8, u16 } from "../../src/sim/cint";
import { beginDrawList, drawList, drawState, Pass } from "../../src/sim/draw";
import { mt_rand } from "../../src/sim/mtrand";
import { g } from "../../src/sim/state";
import { draw_boss_bar, eventAt, JE_drawEnemy, JE_eventSystem, JE_newEnemy } from "../../src/sim/tyrian2";
import { JE_drawSP } from "../../src/sim/varz";

/** The parallax part of JE_mainGamePlayerFunctions (mainint.c L4436-4461). */
export function parallax(): void {
  const tempX = g.player[0].x;
  const tempW = u16(Math.floor(Math.fround(Math.fround(260 - (tempX - 36)) / (260 - 36)) * (24 * 3) - 1));
  g.mapX3Ofs = tempW;
  g.mapX3Pos = g.mapX3Ofs % 24;
  g.mapX3bpPos = 1 - Math.trunc(g.mapX3Ofs / 24);

  g.mapX2Ofs = Math.trunc((tempW * 2) / 3);
  g.mapX2Pos = g.mapX2Ofs % 24;
  g.mapX2bpPos = 1 - Math.trunc(g.mapX2Ofs / 24);

  g.oldMapXOfs = g.mapXOfs;
  g.mapXOfs = Math.trunc(g.mapX2Ofs / 2);
  g.mapXPos = g.mapXOfs % 24;
  g.mapXbpPos = 1 - Math.trunc(g.mapXOfs / 24);

  if (g.background3x1) {
    g.mapX3Ofs = g.mapXOfs;
    g.mapX3Pos = g.mapXPos;
    g.mapX3bpPos = g.mapXbpPos - 1;
  }
}

function drawBackground2(): void {
  if (g.wild && !g.background2notTransparent) draw_background_2_blend();
  else draw_background_2();
}

/** One tick of the world half of JE_main's level loop. */
export function worldTick(): void {
  beginDrawList();

  /*Background Wrapping*/
  if (g.mapYPos <= g.BKwrap1) g.mapYPos = g.BKwrap1to;
  if (g.mapY2Pos <= g.BKwrap2) g.mapY2Pos = g.BKwrap2to;
  if (g.mapY3Pos <= g.BKwrap3) g.mapY3Pos = g.BKwrap3to;

  if (!g.endLevel) {
    g.oldMapX3Ofs = g.mapX3Ofs;
    g.enemyOnScreen = 0;
  }

  /*---------------------------EVENTS-------------------------*/
  while (eventAt(g.eventLoc - 1).eventTime <= g.curLoc && g.eventLoc <= g.maxEvent) JE_eventSystem();

  JE_checkSmoothies();

  /* --- BACKGROUND 1 --- */
  if (g.forceEvents && !g.backMove) g.curLoc = u16(g.curLoc + 1);

  if (g.map1YDelayMax > 1 && g.backMove < 2) g.backMove = g.map1YDelay === 1 ? 1 : 0;

  drawState.pass = Pass.Background1;
  if (g.astralDuration === 0) draw_background_1();

  /*Set Movement of background 1*/
  g.map1YDelay = u8(g.map1YDelay - 1);
  if (g.map1YDelay === 0) {
    g.map1YDelay = g.map1YDelayMax;
    g.curLoc = u16(g.curLoc + g.backMove);
    g.backPos = u16(g.backPos + g.backMove);
    if (g.backPos > 27) {
      g.backPos = u16(g.backPos - 28);
      g.mapY = u16(g.mapY - 1);
      g.mapYPos -= 14; /*Map Width*/
    }
  }

  drawState.pass = Pass.Starfield;
  if (g.starActive || g.astralDuration > 0) update_and_draw_starfield(g.starfield_speed);

  drawState.pass = Pass.Background2Under;
  if (g.background2over === 3) {
    draw_background_2();
    g.background2 = true;
  }
  if (g.background2over === 0) drawBackground2();

  /*-----------------------Ground Enemy------------------------*/
  let lastEnemyOnScreen = g.enemyOnScreen;
  drawState.pass = Pass.GroundEnemies;
  g.tempMapXOfs = g.mapXOfs;
  g.tempBackMove = g.backMove;
  JE_drawEnemy(50);
  JE_drawEnemy(100);

  if (g.enemyOnScreen === 0 || g.enemyOnScreen === lastEnemyOnScreen) {
    if (g.stopBackgroundNum === 1) g.stopBackgroundNum = 9;
  }

  drawState.pass = Pass.Background2Mid;
  if (g.background2over === 1) drawBackground2();

  drawState.pass = Pass.Background3Under;
  if (g.background3over === 2) draw_background_3();

  /* New Enemy */
  if (g.enemiesActive && mt_rand() % 100 > g.levelEnemyFrequency) {
    const tempW = g.levelEnemy[mt_rand() % g.levelEnemyMax];
    JE_newEnemy(0, tempW, 0);
  }

  /* Draw Sky Enemy */
  if (!g.skyEnemyOverAll) {
    lastEnemyOnScreen = g.enemyOnScreen;
    drawState.pass = Pass.SkyEnemies;
    g.tempMapXOfs = g.mapX2Ofs;
    g.tempBackMove = 0;
    JE_drawEnemy(25);
    if (g.enemyOnScreen === lastEnemyOnScreen && g.stopBackgroundNum === 2) g.stopBackgroundNum = 9;
  }

  drawState.pass = Pass.Background3;
  if (g.background3over === 0) draw_background_3();

  /* Draw Top Enemy */
  if (!g.topEnemyOver) {
    drawState.pass = Pass.TopEnemies;
    g.tempMapXOfs = g.background3x1 ? g.mapXOfs : g.oldMapX3Ofs;
    g.tempBackMove = g.backMove3;
    JE_drawEnemy(75);
  }

  // (Player shots, collisions and the player are the player port's.)
  parallax();

  /* Enemy shots: movement only, no player collision (tyrian2.c L1661-1751). */
  for (let z = 0; z < g.enemyShot.length; z++) {
    if (!g.enemyShotAvail[z]) {
      const s = g.enemyShot[z];
      s.sxm = s16(s.sxm + s.sxc);
      s.sx = s16(s.sx + s.sxm);
      if (s.tx !== 0) {
        if (s.sx > g.player[0].x) {
          if (s.sxm > -s.tx) s.sxm = s16(s.sxm - 1);
        } else if (s.sxm < s.tx) s.sxm = s16(s.sxm + 1);
      }
      s.sym = s16(s.sym + s.syc);
      s.sy = s16(s.sy + s.sym);
      if (s.ty !== 0) {
        if (s.sy > g.player[0].y) {
          if (s.sym > -s.ty) s.sym = s16(s.sym - 1);
        } else if (s.sym < s.ty) s.sym = s16(s.sym + 1);
      }
      const duration = s.duration;
      s.duration = u8(s.duration - 1);
      if (duration === 0 || s.sy > 190 || s.sy <= -14 || s.sx > 275 || s.sx <= 0) g.enemyShotAvail[z] = true;
    }
  }

  drawState.pass = Pass.Background3Over;
  if (g.background3over === 1) draw_background_3();

  if (g.topEnemyOver) {
    drawState.pass = Pass.TopEnemiesOver;
    g.tempMapXOfs = g.background3x1 ? g.oldMapXOfs : g.oldMapX3Ofs;
    g.tempBackMove = g.backMove3;
    JE_drawEnemy(75);
  }

  if (g.skyEnemyOverAll) {
    lastEnemyOnScreen = g.enemyOnScreen;
    drawState.pass = Pass.SkyEnemiesOver;
    g.tempMapXOfs = g.mapX2Ofs;
    g.tempBackMove = 0;
    JE_drawEnemy(25);
    if (g.enemyOnScreen === lastEnemyOnScreen && g.stopBackgroundNum === 2) g.stopBackgroundNum = 9;
  }

  drawState.pass = Pass.Background2Top;
  if (g.background2over === 2) drawBackground2();

  drawState.pass = Pass.Effects;
  JE_drawSP();

  if (g.filterActive) JE_filterScreen(g.levelFilter, g.levelBrightness);
  else {
    drawList.filter = -99;
    drawList.brightness = 0;
  }

  draw_boss_bar();

  /*Start backgrounds if no enemies on screen*/
  if (g.stopBackgroundNum === 9 && g.backMove === 0 && !g.enemyStillExploding) {
    g.backMove = 1;
    g.backMove2 = 2;
    g.backMove3 = 3;
    g.explodeMove = 2;
    g.stopBackgroundNum = 0;
    g.stopBackgrounds = false;
    if (g.waitToEndLevel) {
      g.endLevel = true;
      g.levelEnd = 40;
    }
  }

  if (!g.endLevel && g.enemyOnScreen === 0) {
    if (g.readyToEndLevel && !g.enemyStillExploding) {
      if (g.levelTimerCountdown > 0) g.levelTimer = false;
      g.readyToEndLevel = false;
      g.endLevel = true;
      g.levelEnd = 40;
    }
    if (g.stopBackgrounds) {
      g.stopBackgrounds = false;
      g.backMove = 1;
      g.backMove2 = 2;
      g.backMove3 = 3;
      g.explodeMove = 2;
    }
  }
}
