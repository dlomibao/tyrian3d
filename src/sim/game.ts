// JE_main's level loop (OpenTyrian src/tyrian2.c L570–2283), transliterated: `startLevel` is the
// start_level_first section and `tick` is one pass of level_loop. Drawing goes to the draw list
// (src/sim/draw.ts); the passes follow JE_main's draw order (DECISIONS.md D5).
//
// Not ported: network play, demos, super-arcade mode, pause/menu/cheat keys (the host handles
// pause), palette fades, the in-game text
// renderer (the HUD is HTML), and the screen filters (lava, water, blur): their flags are kept
// so the renderer can approximate them.

import { beginDrawList, drawList, drawState, fill_rectangle_xy, Pass, blit_sprite2, blit_sprite2_blend } from "./draw";
import { mt_rand } from "./mtrand";
import { s8, s16, u8, u16, u32 } from "./cint";

const abs = Math.abs;
import {
  all_players_dead,
  ENEMY_SHOT_MAX,
  g,
  MAX_EXPLOSIONS,
  MAX_PWEAPON,
  type Player,
} from "./state";
import {
  S_ENEMY_HIT,
  S_EXPLOSION_11,
  S_EXPLOSION_4,
  S_EXPLOSION_8,
  S_EXPLOSION_9,
  S_SOUL_OF_ZINGLON,
  S_WARNING,
  S_WEAPON_7,
} from "./sndmast";
import {
  draw_background_1,
  draw_background_2,
  draw_background_2_blend,
  draw_background_3,
  update_and_draw_starfield,
  JE_checkSmoothies,
  JE_filterScreen,
} from "./backgrnd";
import { draw_boss_bar, eventAt, initLevelWorld, JE_drawEnemy, JE_eventJump, JE_eventSystem, JE_newEnemy } from "./tyrian2";
import { JE_doSP, JE_drawSP, JE_getShipInfo, JE_playerDamage, JE_setupExplosion, JE_setupExplosionLarge } from "./varz";
import { JE_mainGamePlayerFunctions, JE_playerCollide } from "./mainint";
import { newPlayerShotMoveOut, player_shot_create, player_shot_move_and_draw, SHOT_MISC } from "./shots";
import { startLevelPlayerSetup } from "./newgame";

/** Out-parameters of player_shot_move_and_draw, reused every call. */
const shotOut = newPlayerShotMoveOut();

/** JE_main locals that live across level_loop iterations. */
const loop = {
  old_weapon_bar: [0, 0],
  lastEnemyOnScreen: 0,
};

/**
 * start_level_first, after JE_loadMap (tyrian2.c L659-969): the player half (startLevelPlayerSetup,
 * src/sim/newgame.ts), the world half (initLevelWorld, src/sim/tyrian2.ts), then JE_main's locals.
 * Call once the level is loaded.
 */
export function startLevel(): void {
  startLevelPlayerSetup();
  initLevelWorld();
  JE_getShipInfo();

  // JE_main locals (L765-768, L815)
  warning.col = 120;
  warning.colChange = 1;
  warning.soundDelay = 0;
  warning.armorShipDelay = 50;
  loop.old_weapon_bar[0] = loop.old_weapon_bar[1] = 0;
}

/** Warning-bar state (JE_main locals). */
const warning = { col: 120, colChange: 1, soundDelay: 0, armorShipDelay: 50 };

/** What a tick tells the host. */
export interface TickResult {
  /** reallyEndLevel: the level is over (completed, or the player is out of lives). */
  levelOver: boolean;
  /** The player finished the level (rather than dying). */
  completed: boolean;
  /** Game over shown and waiting for input (the C waits for a key before reallyEndLevel). */
  gameOver: boolean;
}

/** One pass of level_loop. Fills the draw list and g.soundQueue; the host plays sounds and renders. */
export function tick(): TickResult {
  beginDrawList(); // keeps drawList.palette, which initLevelWorld sets for the level

  // Background Wrapping
  if (g.mapYPos <= g.BKwrap1) g.mapYPos = g.BKwrap1to;
  if (g.mapY2Pos <= g.BKwrap2) g.mapY2Pos = g.BKwrap2to;
  if (g.mapY3Pos <= g.BKwrap3) g.mapY3Pos = g.BKwrap3to;

  // In one-player story mode the lives clause is short-circuited by (!onePlayerAction && !twoPlayerMode):
  // losing a life ends the level and the host restarts it (start_level / JE_loadGame in the C).
  g.allPlayersGone =
    all_players_dead() &&
    ((g.player[0].lives.value === 1 && g.player[0].exploding_ticks === 0) || (!g.onePlayerAction && !g.twoPlayerMode)) &&
    ((g.player[1].lives.value === 1 && g.player[1].exploding_ticks === 0) || !g.twoPlayerMode);

  if (!g.endLevel) {
    // draw HUD
    // Message Bar
    if (g.textErase > 0) g.textErase--;

    // Shield Gen
    const p0 = g.player[0];
    if (g.galagaMode) {
      for (const p of g.player) p.shield = 0;

      // spawned dragonwing died :(
      if (g.player[1].lives.value === 0 || g.player[1].armor === 0) g.twoPlayerMode = false;

      if (p0.cash >= u32(g.galagaLife)) {
        g.soundQueue[6] = S_EXPLOSION_11;
        g.soundQueue[7] = S_SOUL_OF_ZINGLON;

        if (p0.lives.value < 11) ++p0.lives.value;
        else p0.cash += 1000;

        if (g.galagaLife === 10000) g.galagaLife = 20000;
        else g.galagaLife += 25000;
      }
    } else if (g.twoPlayerMode) {
      // [two-player] tyrian2.c L1057-1071: both shields recharge without drawing power.
      if (--g.shieldWait === 0) {
        g.shieldWait = 15;
        for (const p of g.player) if (p.shield < p.shield_max && p.is_alive) ++p.shield;
      }
    } else if (p0.is_alive && p0.shield < p0.shield_max && g.power > g.shieldT) {
      if (--g.shieldWait === 0) {
        g.shieldWait = 15;
        g.power -= g.shieldT;
        ++p0.shield;
        if (g.player[1].shield < p0.shield_max) ++g.player[1].shield;
      }
    }

    // Weapon Display
    for (let i = 0; i < 2; i++) loop.old_weapon_bar[i] = g.player[g.twoPlayerMode ? i : 0].items.weapon[i].power;

    // Power Bar
    if (g.twoPlayerMode || g.onePlayerAction) {
      g.power = 900;
    } else {
      g.power += g.powerAdd;
      if (g.power > 900) g.power = 900;
      g.lastPower = Math.trunc(g.power / 10);
    }

    g.oldMapX3Ofs = g.mapX3Ofs;
    g.enemyOnScreen = 0;
  }

  // EVENTS
  while (eventAt(g.eventLoc - 1).eventTime <= g.curLoc && g.eventLoc <= g.maxEvent) JE_eventSystem();

  // SMOOTHIES!
  JE_checkSmoothies();

  // --- BACKGROUND 1 ---
  if (g.forceEvents && !g.backMove) g.curLoc = u16(g.curLoc + 1);

  if (g.map1YDelayMax > 1 && g.backMove < 2) g.backMove = g.map1YDelay === 1 ? 1 : 0;

  // Draw background
  drawState.pass = Pass.Background1;
  if (g.astralDuration === 0) draw_background_1();

  // Set Movement of background 1
  g.map1YDelay = u8(g.map1YDelay - 1);
  if (g.map1YDelay === 0) {
    g.map1YDelay = g.map1YDelayMax;
    g.curLoc = u16(g.curLoc + g.backMove);
    g.backPos = u16(g.backPos + g.backMove);
    if (g.backPos > 27) {
      g.backPos = u16(g.backPos - 28);
      g.mapY = u16(g.mapY - 1);
      g.mapYPos -= 14; // Map Width
    }
  }

  drawState.pass = Pass.Starfield;
  if (g.starActive || g.astralDuration > 0) update_and_draw_starfield(g.starfield_speed);

  // --- BACKGROUND 2 ---
  if (g.background2over === 3) {
    drawState.pass = Pass.Background2Under;
    draw_background_2();
    g.background2 = true;
  }
  if (g.background2over === 0) {
    drawState.pass = Pass.Background2Under;
    if (g.wild && !g.background2notTransparent) draw_background_2_blend();
    else draw_background_2();
  }

  // Ground Enemy
  let lastEnemyOnScreen = g.enemyOnScreen;
  drawState.pass = Pass.GroundEnemies;
  g.tempMapXOfs = g.mapXOfs;
  g.tempBackMove = g.backMove;
  JE_drawEnemy(50);
  JE_drawEnemy(100);

  if (g.enemyOnScreen === 0 || g.enemyOnScreen === lastEnemyOnScreen) {
    if (g.stopBackgroundNum === 1) g.stopBackgroundNum = 9;
  }

  if (g.superWild) g.neat += 3;

  // --- BACKGROUND 2 ---
  if (g.background2over === 1) {
    drawState.pass = Pass.Background2Mid;
    if (g.wild && !g.background2notTransparent) draw_background_2_blend();
    else draw_background_2();
  }

  if (g.superWild) g.neat++;

  if (g.background3over === 2) {
    drawState.pass = Pass.Background3Under;
    draw_background_3();
  }

  // New Enemy
  if (g.enemiesActive && mt_rand() % 100 > g.levelEnemyFrequency) {
    const tempW = g.levelEnemy[mt_rand() % g.levelEnemyMax];
    if (tempW === 2) g.soundQueue[3] = S_WEAPON_7;
    JE_newEnemy(0, tempW, 0);
  }

  // Draw Sky Enemy
  if (!g.skyEnemyOverAll) {
    lastEnemyOnScreen = g.enemyOnScreen;
    drawState.pass = Pass.SkyEnemies;
    g.tempMapXOfs = g.mapX2Ofs;
    g.tempBackMove = 0;
    JE_drawEnemy(25);
    if (g.enemyOnScreen === lastEnemyOnScreen) {
      if (g.stopBackgroundNum === 2) g.stopBackgroundNum = 9;
    }
  }

  if (g.background3over === 0) {
    drawState.pass = Pass.Background3;
    draw_background_3();
  }

  // Draw Top Enemy
  if (!g.topEnemyOver) {
    drawState.pass = Pass.TopEnemies;
    g.tempMapXOfs = g.background3x1 === false ? g.oldMapX3Ofs : g.mapXOfs;
    g.tempBackMove = g.backMove3;
    JE_drawEnemy(75);
  }

  // Player Shot Images
  drawState.pass = Pass.PlayerShots;
  playerShotsAndCollisions();

  // Player movement indicators for shots that track your ship
  for (const p of g.player) {
    p.last_x_shot_move = p.x;
    p.last_y_shot_move = p.y;
  }

  // Collisions Detection
  drawState.pass = Pass.Player;
  for (let i = 0; i < (g.twoPlayerMode ? 2 : 1); ++i) if (g.player[i].is_alive && !g.endLevel) JE_playerCollide(g.player[i], i + 1);

  if (g.firstGameOver) JE_mainGamePlayerFunctions(); // PLAYER DRAW+MOVEMENT

  if (!g.endLevel) {
    // MAIN DRAWING IS STOPPED STARTING HERE
    drawState.pass = Pass.EnemyShots;
    enemyShots();
  }

  if (g.background3over === 1) {
    drawState.pass = Pass.Background3Over;
    draw_background_3();
  }

  // Draw Top Enemy
  if (g.topEnemyOver) {
    drawState.pass = Pass.TopEnemiesOver;
    g.tempMapXOfs = g.background3x1 === false ? g.oldMapX3Ofs : g.oldMapXOfs;
    g.tempBackMove = g.backMove3;
    JE_drawEnemy(75);
  }

  // Draw Sky Enemy
  if (g.skyEnemyOverAll) {
    lastEnemyOnScreen = g.enemyOnScreen;
    drawState.pass = Pass.SkyEnemiesOver;
    g.tempMapXOfs = g.mapX2Ofs;
    g.tempBackMove = 0;
    JE_drawEnemy(25);
    if (g.enemyOnScreen === lastEnemyOnScreen) {
      if (g.stopBackgroundNum === 2) g.stopBackgroundNum = 9;
    }
  }

  drawState.pass = Pass.Explosions;
  sequencedExplosions();
  drawExplosions();

  if (!g.portConfigChange) g.portConfigDone = true;

  // --- BACKGROUND 2 ---
  if (g.background2over === 2) {
    drawState.pass = Pass.Background2Top;
    if (g.wild && !g.background2notTransparent) draw_background_2_blend();
    else draw_background_2();
  }

  // Warning
  drawState.pass = Pass.Effects;
  armorWarning();

  // Random Explosions
  if (g.randomExplosions && mt_rand() % 10 === 1) JE_setupExplosionLarge(false, 20, mt_rand() % 280, mt_rand() % 180);

  // The Sound Routine: the host drains g.soundQueue after the tick.

  if (g.returnActive && g.enemyOnScreen === 0) {
    JE_eventJump(65535);
    g.returnActive = false;
  }

  if (g.displayTime > 0) {
    g.displayTime--;
    g.flash += g.flashChange;
    if (g.flash > 4 || g.flash === 0) g.flashChange = -g.flashChange;
  }

  // Level Timer
  if (g.levelTimer && g.levelTimerCountdown > 0) {
    g.levelTimerCountdown--;
    if (g.levelTimerCountdown === 0) JE_eventJump(g.levelTimerJumpTo);
    if (g.levelTimerCountdown > 200) {
      if (g.levelTimerCountdown % 100 === 0) g.soundQueue[7] = S_WARNING;
      if (g.levelTimerCountdown % 10 === 0) g.soundQueue[6] = 24; // S_CLICK
    } else if (g.levelTimerCountdown % 20 === 0) {
      g.soundQueue[7] = S_WARNING;
    }
  }

  // GAME OVER
  let gameOver = false;
  if (!g.constantPlay && !g.constantDie) {
    if (g.allPlayersGone) {
      if (g.player[0].exploding_ticks > 0 || g.player[1].exploding_ticks > 0) {
        if (g.galagaMode) g.player[1].exploding_ticks = 0;
        // musicFade = true
      } else {
        gameOver = true;
        if (g.firstGameOver) g.firstGameOver = false;
        // The C waits for any key here and then sets reallyEndLevel; the host does that.
      }
    }
  }

  // Test
  drawState.pass = Pass.Effects;
  JE_drawSP();

  // Filtration
  if (g.filterActive) {
    JE_filterScreen(g.levelFilter, g.levelBrightness);
  } else {
    drawList.filter = -99;
    drawList.brightness = 0;
  }

  draw_boss_bar();

  // Start backgrounds if no enemies on screen; end level if number of enemies left to kill equals 0.
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
    if (g.allPlayersGone) g.reallyEndLevel = true;
  }

  if (!g.endLevel && g.enemyOnScreen === 0) {
    if (g.readyToEndLevel && !g.enemyStillExploding) {
      if (g.levelTimerCountdown > 0) g.levelTimer = false;
      g.readyToEndLevel = false;
      g.endLevel = true;
      g.levelEnd = 40;
      if (g.allPlayersGone) g.reallyEndLevel = true;
    }
    if (g.stopBackgrounds) {
      g.stopBackgrounds = false;
      g.backMove = 1;
      g.backMove2 = 2;
      g.backMove3 = 3;
      g.explodeMove = 2;
    }
  }

  return {
    levelOver: g.reallyEndLevel,
    completed: g.reallyEndLevel && !all_players_dead(),
    gameOver,
  };
}

/** JE_main "Player Shot Images": move and draw player shots, collide them with enemies (L1290–1555). */
function playerShotsAndCollisions(): void {
  for (let z = 0; z < MAX_PWEAPON; z++) {
    if (g.shotAvail[z] === 0) continue;

    if (!player_shot_move_and_draw(z, shotOut)) continue;
    const { is_special, playerNum } = shotOut;
    const tempShotX = shotOut.shotx;
    const tempShotY = shotOut.shoty;
    const tempX2 = shotOut.special_radiusw;
    const tempY2 = shotOut.special_radiush;
    let damage = shotOut.shot_damage;
    let chain = shotOut.chain;
    let temp2 = shotOut.blast_filter;

    for (let b = 0; b < 100; b++) {
      if (g.enemyAvail[b] !== 0) continue;
      const e = g.enemy[b];
      let collided: boolean;

      if (z === MAX_PWEAPON - 1) {
        const temp = 25 - abs(g.zinglonDuration - 25);
        collided = abs(e.ex + e.mapoffset - (g.player[0].x + 7)) < temp;
        temp2 = 9;
        chain = 0;
        damage = 10;
      } else if (is_special) {
        collided =
          (e.enemycycle === 0 &&
            abs(e.ex + e.mapoffset - tempShotX - tempX2) < 25 + tempX2 &&
            abs(e.ey - tempShotY - 12 - tempY2) < 29 + tempY2) ||
          (e.enemycycle > 0 &&
            abs(e.ex + e.mapoffset - tempShotX - tempX2) < 13 + tempX2 &&
            abs(e.ey - tempShotY - 6 - tempY2) < 15 + tempY2);
      } else {
        collided =
          (e.enemycycle === 0 && abs(e.ex + e.mapoffset - tempShotX) < 25 && abs(e.ey - tempShotY - 12) < 29) ||
          (e.enemycycle > 0 && abs(e.ex + e.mapoffset - tempShotX) < 13 && abs(e.ey - tempShotY - 6) < 15);
      }

      if (!collided) continue;

      if (chain > 0) {
        g.shotMultiPos[SHOT_MISC] = 0;
        player_shot_create(0, SHOT_MISC, tempShotX, tempShotY, g.player[0].mouseX, g.player[0].mouseY, chain, playerNum);
        g.shotAvail[z] = 0;
        break; // goto draw_player_shot_loop_end
      }

      g.infiniteShot = false;

      if (damage === 99) {
        damage = 0;
        g.doIced = 40;
        e.iced = 40;
      } else {
        g.doIced = 0;
        if (damage >= 250) {
          damage = damage - 250;
          g.infiniteShot = true;
        }
      }

      const armorleft = e.armorleft;

      let temp = e.linknum;
      if (temp === 0) temp = 255;

      if (e.armorleft < 255) {
        for (const bar of g.boss_bar) if (temp === bar.link_num) bar.color = 6;

        if (e.enemyground) e.filter = temp2;

        for (let i = 0; i < g.enemy.length; i++) {
          const o = g.enemy[i];
          if (o.linknum === temp && g.enemyAvail[i] !== 1 && o.enemyground) {
            if (g.doIced) o.iced = g.doIced;
            o.filter = temp2;
          }
        }
      }

      if (armorleft > damage) {
        if (z !== MAX_PWEAPON - 1) {
          if (e.armorleft !== 255) {
            e.armorleft = u8(e.armorleft - damage);
            JE_setupExplosion(tempShotX, tempShotY, 0, 0, false, false);
          } else {
            JE_doSP(tempShotX + 6, tempShotY + 6, Math.trunc(damage / 2) + 3, Math.trunc(damage / 4) + 2, temp2);
          }
        }

        g.soundQueue[5] = S_ENEMY_HIT;

        if (armorleft - damage <= e.edlevel && (!e.edamaged) !== (e.edani < 0)) {
          for (let temp3 = 0; temp3 < 100; temp3++) {
            if (g.enemyAvail[temp3] === 1) continue;
            const o = g.enemy[temp3];
            const linknum = o.linknum;
            if (
              temp3 === b ||
              (temp !== 255 &&
                ((o.edlevel > 0 && linknum === temp) ||
                  (g.enemyContinualDamage && temp - 100 === linknum) ||
                  (linknum > 40 && Math.trunc(linknum / 20) === Math.trunc(temp / 20) && linknum <= temp)))
            ) {
              o.enemycycle = 1;
              o.edamaged = !o.edamaged;

              if (o.edani !== 0) {
                o.ani = abs(o.edani);
                o.aniactive = 1;
                o.animax = 0;
                o.animin = o.edgr;
                o.enemycycle = u8(o.animin - 1);
              } else if (o.edgr > 0) {
                o.egr[0] = o.edgr;
                o.ani = 1;
                o.aniactive = 0;
                o.animax = 0;
                o.animin = 1;
              } else {
                g.enemyAvail[temp3] = 1;
                g.enemyKilled++;
              }

              o.aniwhenfire = 0;

              if (o.armorleft > u8(o.edlevel)) o.armorleft = u8(o.edlevel);

              const tempX = s16(o.ex + o.mapoffset);
              const tempY = o.ey;

              if (g.res.enemyDat[o.enemytype].eSize !== 1) JE_setupExplosion(tempX, tempY - 6, 0, 1, false, false);
              else JE_setupExplosionLarge(o.enemyground, Math.trunc(o.explonum / 2), tempX, tempY);
            }
          }
        }
      } else {
        if (temp === 254 && g.superEnemy254Jump > 0) JE_eventJump(g.superEnemy254Jump);

        for (let t2 = 0; t2 < 100; t2++) {
          if (g.enemyAvail[t2] === 1) continue;
          const o = g.enemy[t2];
          const temp3 = o.linknum;
          if (
            t2 === b ||
            temp === 254 ||
            (temp !== 255 &&
              (temp === temp3 || temp - 100 === temp3 || (temp3 > 40 && Math.trunc(temp3 / 20) === Math.trunc(temp / 20) && temp3 <= temp)))
          ) {
            const enemy_screen_x = s16(o.ex + o.mapoffset);

            if (o.special) g.globalFlags[o.flagnum - 1] = o.setto;

            if (o.enemydie > 0 && !(g.superArcadeMode !== 0 && g.res.enemyDat[o.enemydie].value === 30000)) {
              const tempW = o.enemydie;
              let enemy_offset = t2 - (t2 % 25);
              if (g.res.enemyDat[tempW].value > 30000) enemy_offset = 0;
              const nb = JE_newEnemy(enemy_offset, tempW, 0);
              if (nb !== 0) {
                const n = g.enemy[nb - 1];
                n.scoreitem = n.evalue !== 0;
                n.ex = o.ex;
                n.ey = o.ey;
              }
            }

            if (o.evalue > 0 && o.evalue < 10000) {
              if (o.evalue === 1) g.cubeMax++;
              else g.player[playerNum - 1].cash += o.evalue;
            }

            if (o.edlevel === -1 && temp === temp3) {
              o.edlevel = 0;
              g.enemyAvail[t2] = 2;
              o.egr[0] = o.edgr;
              o.ani = 1;
              o.aniactive = 0;
              o.animax = 0;
              o.animin = 1;
              o.edamaged = true;
              o.enemycycle = 1;
            } else {
              g.enemyAvail[t2] = 1;
              g.enemyKilled++;
            }

            if (g.res.enemyDat[o.enemytype].eSize === 1) {
              JE_setupExplosionLarge(o.enemyground, o.explonum, enemy_screen_x, o.ey);
              g.soundQueue[6] = S_EXPLOSION_9;
            } else {
              JE_setupExplosion(enemy_screen_x, o.ey, 0, 1, false, false);
              g.soundQueue[6] = S_EXPLOSION_8;
            }
          }
        }
      }

      if (g.infiniteShot) {
        damage += 250;
      } else if (z !== MAX_PWEAPON - 1) {
        if (damage <= armorleft) {
          g.shotAvail[z] = 0;
          break; // goto draw_player_shot_loop_end
        } else {
          g.playerShotData[z].shotDmg = u8(g.playerShotData[z].shotDmg - armorleft);
        }
      }
    }
  }
}

/** JE_main "Draw Enemy Shots" (L1661–1757): move, collide with the player, draw. */
function enemyShots(): void {
  for (let z = 0; z < ENEMY_SHOT_MAX; z++) {
    if (g.enemyShotAvail[z]) continue;
    const s = g.enemyShot[z];
    const p0 = g.player[0];

    s.sxm = s16(s.sxm + s.sxc);
    s.sx = s16(s.sx + s.sxm);
    if (s.tx !== 0) {
      if (s.sx > p0.x) {
        if (s.sxm > -s.tx) s.sxm--;
      } else if (s.sxm < s.tx) {
        s.sxm++;
      }
    }

    s.sym = s16(s.sym + s.syc);
    s.sy = s16(s.sy + s.sym);
    if (s.ty !== 0) {
      if (s.sy > p0.y) {
        if (s.sym > -s.ty) s.sym--;
      } else if (s.sym < s.ty) {
        s.sym++;
      }
    }

    // enemyShot[z].duration-- == 0 (post-decrement on a JE_byte)
    const durationWasZero = s.duration === 0;
    s.duration = u8(s.duration - 1);
    if (durationWasZero || s.sy > 190 || s.sy <= -14 || s.sx > 275 || s.sx <= 0) {
      g.enemyShotAvail[z] = true;
      continue;
    }

    // check if shot collided with player
    let hit = false;
    for (let i = 0; i < (g.twoPlayerMode ? 2 : 1); ++i) {
      const p: Player = g.player[i];
      if (
        p.is_alive &&
        s.sx > p.x - p.shot_hit_area_x &&
        s.sx < p.x + p.shot_hit_area_x &&
        s.sy > p.y - p.shot_hit_area_y &&
        s.sy < p.y + p.shot_hit_area_y
      ) {
        const tempX = s.sx;
        const tempY = s.sy;
        let temp = s.sdmg;
        g.enemyShotAvail[z] = true;
        JE_setupExplosion(tempX, tempY, 0, 0, false, false);
        if (p.invulnerable_ticks === 0) {
          if ((temp = JE_playerDamage(temp, p)) > 0) {
            p.x_velocity += Math.trunc((s.sxm * temp) / 2);
            p.y_velocity += Math.trunc((s.sym * temp) / 2);
          }
        }
        hit = true;
        break;
      }
    }
    if (hit) continue;

    if (s.animax !== 0) {
      if (++s.animate >= s.animax) s.animate = 0;
    }

    drawState.key = 20000 + z;
    if (s.sgr >= 500) blit_sprite2(s.sx, s.sy, g.res.spriteSheet12, s.sgr + s.animate - 500);
    else blit_sprite2(s.sx, s.sy, g.res.spriteSheet8, s.sgr + s.animate);
    drawState.key = -1;
  }
}

/** JE_main "Sequenced Explosions" (L1780–1822). */
function sequencedExplosions(): void {
  g.enemyStillExploding = false;
  for (const r of g.rep_explosions) {
    if (r.ttl === 0) continue;
    g.enemyStillExploding = true;

    if (r.delay > 0) {
      r.delay--;
      continue;
    }

    r.y += g.backMove2 + 1;
    const tempX = s16(r.x + (mt_rand() % 24) - 12);
    const tempY = s16(r.y + (mt_rand() % 27) - 24);

    if (r.big) {
      JE_setupExplosionLarge(false, 2, tempX, tempY);
      if (r.ttl === 1 || mt_rand() % 5 === 1) g.soundQueue[7] = S_EXPLOSION_11;
      else g.soundQueue[6] = S_EXPLOSION_9;
      r.delay = 4 + (mt_rand() % 3);
    } else {
      JE_setupExplosion(tempX, tempY, 0, 1, false, false);
      g.soundQueue[5] = S_EXPLOSION_4;
      r.delay = 3;
    }

    r.ttl--;
  }
}

/** JE_main "Draw Explosions" (L1824–1852). */
function drawExplosions(): void {
  for (let j = 0; j < MAX_EXPLOSIONS; j++) {
    const e = g.explosions[j];
    if (e.ttl === 0) continue;

    if (!e.fixedPosition) {
      e.sprite++;
      e.y = s16(e.y + g.explodeMove);
    } else if (e.followPlayer) {
      e.x = s16(e.x + g.explosionFollowAmountX);
      e.y = s16(e.y + g.explosionFollowAmountY);
    }
    e.y = s16(e.y + e.deltaY);

    if (e.y > 200 - 14) {
      e.ttl = 0;
    } else {
      drawState.key = 30000 + j;
      if (g.explosionTransparent) blit_sprite2_blend(e.x, e.y, g.res.explosionSpriteSheet, e.sprite + 1);
      else blit_sprite2(e.x, e.y, g.res.explosionSpriteSheet, e.sprite + 1);
      drawState.key = -1;
      e.ttl--;
    }
  }
}

/** JE_main "Warning" (L1872–1932): low-armor warning, spawning the armor-repair ship. */
function armorWarning(): void {
  const [p0, p1] = g.player;
  if (!((p0.is_alive && p0.armor < 6) || (g.twoPlayerMode && !g.galagaMode && p1.is_alive && p1.armor < 6))) return;
  const armor_amount = p0.is_alive && p0.armor < 6 ? p0.armor : p1.armor;

  if (warning.armorShipDelay > 0) {
    warning.armorShipDelay--;
  } else {
    const b = JE_newEnemy(50, 560, 0);
    if (b > 0) {
      const e = g.enemy[b - 1];
      e.enemydie = 560 + (mt_rand() % 3) + 1;
      e.eyc = s8(e.eyc - g.backMove3);
      e.armorleft = 4;
    }
    warning.armorShipDelay = 500;
  }

  // (the C's network test, thisPlayerNum, is always true here)
  if (!((p0.is_alive && p0.armor < 6) || (g.twoPlayerMode && p1.is_alive && p1.armor < 6))) return;

  const tempW = armor_amount * 4 + 8;
  if (warning.soundDelay > tempW) warning.soundDelay = tempW;
  if (warning.soundDelay > 1) {
    warning.soundDelay--;
  } else {
    g.soundQueue[7] = S_WARNING;
    warning.soundDelay = tempW;
  }

  warning.col += warning.colChange;
  if (warning.col > 113 + (14 - armor_amount * 2)) {
    warning.colChange = -warning.colChange;
    warning.col = 113 + (14 - armor_amount * 2);
  } else if (warning.col < 113) {
    warning.colChange = -warning.colChange;
  }
  fill_rectangle_xy(24, 181, 138, 183, warning.col);
  fill_rectangle_xy(175, 181, 287, 183, warning.col);
  fill_rectangle_xy(24, 0, 287, 3, warning.col);
}
