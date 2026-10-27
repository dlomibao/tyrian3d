// [two-player] Starting a local two-player game: OpenTyrian's "2 Player Arcade".
//
// newTwoPlayerGame() follows what OpenTyrian does from the main loop to JE_main when the title's
// gameplay menu picks "2 Player Arcade":
//   opentyr.c L873-880   JE_initPlayerData(); playDemo = false; gameLoaded = false; jumpSection = false;
//   menus.c   L206-207   gameplaySelect: onePlayerAction = false; twoPlayerMode = true;
//   menus.c   L384       episodeSelect: JE_initEpisode(episode)
//   tyrian2.c L3533-3575 newGame(): gameLoaded = true; initialDifficulty = difficultyLevel; then the
//                        twoPlayerMode branch: both players' cash = 0, player 1 flies the Silver
//                        Ship (11), difficultyLevel++ ("one step harder for 2-player mode"), and
//                        inputDevice[0] = 1 (keyboard), inputDevice[1] = 2 (mouse).
// Player 2 keeps JE_initPlayerData's loadout: player 1's items with the Vulcan Cannon as rear
// weapon and no sidekick series; JE_getShipInfo makes it the dragonwing (shipGr2 = 0, armor 10).
// Each player's lives are the power of their own weapon (player 1's front, player 2's rear:
// point_lives_at_weapon_power).
//
// Input devices: the port gives each player their own input (simInputs, src/sim/input.ts), filled
// by the host from that player's keys and gamepad, so both read every device of their own: the
// game sets inputDevice to 0 for both instead of the C's keyboard and mouse (DECISIONS.md D28).
// newTwoPlayerGame(..., { inputDevices: [1, 2] }) keeps the C's, for the cross-check.
//
// After that, a two-player game runs on the same code as a one-player one: the sim's
// twoPlayerMode branches (src/sim/game.ts, mainint.ts, varz.ts, tyrian2.ts), the item screen's
// MENU_2_PLAYER_ARCADE (game_menu.ts) and save slots 12-22 (savegame.ts).

import { JE_initPlayerData } from "./mainint";
import { DIFFICULTY_NORMAL, g } from "./state";

export interface TwoPlayerGameOptions {
  /** inputDevice[0..1] (0 any, 1 keyboard, 2 mouse, 3+ joystick). Default [0, 0] (see above). */
  inputDevices?: readonly [number, number];
}

/**
 * Start a new two-player game on `episode` at the chosen `difficulty` (the game then plays one
 * step harder). Needs g.res (item data). Call once before loading the first level.
 */
export function newTwoPlayerGame(episode = 1, difficulty = DIFFICULTY_NORMAL, opts: TwoPlayerGameOptions = {}): void {
  // opentyr.c L873-880
  JE_initPlayerData();
  g.playDemo = false;
  g.gameLoaded = false;
  g.jumpSection = false;

  // titleScreen() -> newGame() (tyrian2.c L3533)
  // gameplaySelect(): "2 Player Arcade" (menus.c L206-207)
  g.onePlayerAction = false;
  g.twoPlayerMode = true;
  // episodeSelect(): JE_initEpisode(episode) (the item data is g.res)
  g.episodeNum = episode;
  g.initial_episode_num = g.episodeNum;
  // difficultySelect()
  g.difficultyLevel = difficulty;
  g.gameLoaded = true;

  g.initialDifficulty = g.difficultyLevel;

  for (const p of g.player) p.cash = 0;

  g.player[0].items.ship = 11; // Silver Ship

  g.difficultyLevel++; // Make it one step harder for 2-player mode!

  const [device1, device2] = opts.inputDevices ?? [0, 0];
  g.inputDevice[0] = device1;
  g.inputDevice[1] = device2;
}

/** [two-player] Whether a player is still in the game: alive, exploding, or with a life to respawn on. */
export function playerInGame(i: 0 | 1): boolean {
  const p = g.player[i];
  return p.is_alive || p.exploding_ticks > 0 || p.lives.value > 1;
}
