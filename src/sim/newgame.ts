// Setting up a new one-player game, and the player-side part of a level start.
//
// newOnePlayerGame() follows what OpenTyrian does from the main loop to JE_main for "1 Player,
// Full Game", episode 1, default difficulty:
//   opentyr.c L873-880   JE_initPlayerData(); playDemo = false; gameLoaded = false; jumpSection = false;
//   menus.c   L206-207   gameplaySelect: onePlayerAction = false; twoPlayerMode = false;
//   menus.c   L384       episodeSelect: JE_initEpisode(1)
//   menus.c   L412, 616  difficultySelect: the default selection (index 1) -> DIFFICULTY_NORMAL
//   tyrian2.c L3533-3575 newGame(): gameLoaded = true; initialDifficulty = difficultyLevel;
//                        player[0].cash = richMode ? 1000000 : initial_cash[episodeNum - 1] (10000)
// The resulting loadout (JE_initPlayerData, mainint.c L1014-1061): USP Talon (ship 1), Pulse-Cannon
// front weapon (port 1) at power 1, no rear weapon, Gencore High Energy Shield (4), Advanced MR-12
// generator (2), no sidekicks or special, weapon_mode 1, armor = ships[1].dmg.
//
// startLevelPlayerSetup() is the player/shot subset of JE_main's start_level_first (tyrian2.c
// L659-969). If the level loop's port includes start_level_first wholesale, skip it.

import { u8 } from "./cint";
import { JE_drawTextWindow, JE_initPlayerData } from "./mainint";
import { calc_purple_balls_needed } from "./player";
import { playerShotKey } from "./shots";
import { DIFFICULTY_NORMAL, g, newPlayerShotData } from "./state";
import { JE_drawOptions, JE_getShipInfo } from "./varz";

/** tyrian2.c newGame(): starting cash per episode. */
const initial_cash = [10000, 15000, 20000, 30000];

/**
 * Start a new one-player full game on `episode` (default 1) at `difficulty` (default Normal).
 * Needs g.res (item data) and, for lastLevelName, g.miscText (loadHelpText). Call once before
 * loading the first level; then load the level (JE_loadMap) and call startLevelPlayerSetup().
 */
export function newOnePlayerGame(episode = 1, difficulty = DIFFICULTY_NORMAL): void {
  // opentyr.c L873-880
  JE_initPlayerData();
  g.playDemo = false;
  g.gameLoaded = false;
  g.jumpSection = false;

  // titleScreen() -> newGame() (tyrian2.c L3533)
  // gameplaySelect(): "1 Player Full Game" (menus.c L206-207)
  g.onePlayerAction = false;
  g.twoPlayerMode = false;
  // episodeSelect(): JE_initEpisode(episode) (episodes.c L247-259; the item data is g.res)
  g.episodeNum = episode;
  g.initial_episode_num = g.episodeNum; // menus.c L385 (episodes port)
  // difficultySelect()
  g.difficultyLevel = difficulty;
  g.gameLoaded = true;

  g.initialDifficulty = g.difficultyLevel;

  if (g.richMode) {
    g.player[0].cash = 1000000;
  } else if (g.gameLoaded) {
    g.player[0].cash = initial_cash[g.episodeNum - 1];
  }
}

/**
 * The player and player-shot statements of start_level_first (tyrian2.c L659-969), in order.
 * Call after the level is loaded (JE_loadMap) and before the first tick.
 */
export function startLevelPlayerSetup(): void {
  const player = g.player;

  // L679-680
  for (let i = 0; i < player.length; ++i) player[i].is_alive = true;

  // L688-705
  player[0].x = 100;
  player[0].y = 180;

  player[1].x = 190;
  player[1].y = 180;

  for (let i = 0; i < player.length; ++i) {
    for (let j = 0; j < player[i].old_x.length; ++j) {
      player[i].old_x[j] = player[i].x - (19 - j);
      player[i].old_y[j] = player[i].y - 18;
    }

    player[i].last_x_shot_move = player[i].x;
    player[i].last_y_shot_move = player[i].y;
  }

  // L710: sets up the sidekicks' ammo, style, animation and charge (its HUD drawing is omitted)
  JE_drawOptions();

  // L747
  g.power = 0;

  // L750-759: Setup player ship graphics
  JE_getShipInfo();

  for (let i = 0; i < player.length; ++i) {
    player[i].x_velocity = 0;
    player[i].y_velocity = 0;

    player[i].invulnerable_ticks = 100;
  }

  // L773-776 (twiddle input buttons)
  for (let temp = 0; temp < 3; temp++) g.button[temp] = false;

  // L820-821: Initial Text
  JE_drawTextWindow(g.miscText[20]);

  // L823-833: Setup Armor/Shield Data (shieldT is a JE_byte)
  g.shieldWait = 1;
  g.shieldT = u8(g.res.items.shields[player[0].items.shield].tpwr * 20);

  for (let i = 0; i < player.length; ++i) {
    player[i].shield = g.res.items.shields[player[i].items.shield].mpwr;
    player[i].shield_max = player[i].shield * 2;
  }

  // L836-837
  for (let i = 0; i < player.length; ++i) player[i].superbombs = 0;

  // L874-878
  g.twoPlayerLinked = false;
  g.linkGunDirec = Math.fround(Math.PI);

  for (let i = 0; i < player.length; ++i) calc_purple_balls_needed(player[i]);

  // L880-888
  g.damageRate = 2; /*Normal Rate for Collision Damage*/

  g.chargeWait = 5;
  g.chargeLevel = 0;
  g.chargeMax = 5;
  g.chargeGr = 0;
  g.chargeGrWait = 3;

  g.portConfigChange = false;

  // L900-903
  g.constantLastX = -1;

  for (let i = 0; i < player.length; ++i) player[i].exploding_ticks = 0;

  // L914-920: Initialize Shots
  for (let i = 0; i < g.playerShotData.length; i++) g.playerShotData[i] = newPlayerShotData();
  g.shotAvail.fill(0);
  g.shotMultiPos.fill(0);
  g.shotRepeat.fill(1); // memset(shotRepeat, 1, ...)
  playerShotKey.fill(-1);

  g.button.fill(false);

  // L934-935
  for (const code of g.SFCurrentCode) code.fill(0);
  g.SFExecuted.fill(0);

  // L937-941
  g.zinglonDuration = 0;
  g.specialWait = 0;
  g.nextSpecialWait = 0;
  g.optionAttachmentMove = 0; /*Launch the Attachments!*/
  g.optionAttachmentLinked = true;

}
