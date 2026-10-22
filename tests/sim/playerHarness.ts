// Shared setup for the player-port tests: a fresh one-player episode-1 game, and a tick that runs
// the player-related parts of JE_main's level loop in the C's order.
import { beginDrawList, drawList, drawState, Pass } from "../../src/sim/draw";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { JE_mainGamePlayerFunctions, JE_playerCollide } from "../../src/sim/mainint";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame, startLevelPlayerSetup } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { newPlayerShotMoveOut, player_shot_move_and_draw } from "../../src/sim/shots";
import { g, MAX_PWEAPON, newEnemy, newPlayer, type Resources } from "../../src/sim/state";
import { hasData, readData } from "../data/dataDir";

export const PLAYER_DATA_FILES = ["tyrian.shp", "tyrian.hdt", "palette.dat", "newsh6.shp"];
export const havePlayerData = () => hasData(...PLAYER_DATA_FILES);

let res: Resources | undefined;

/** A new one-player episode-1 game, at level start. */
export function freshGame(seed = 1): void {
  res ??= buildResources({ get: (n) => (hasData(n) ? readData(n) : undefined) });
  g.res = res;
  loadHelpText(readData("tyrian.hdt"));
  mt_srand(seed);
  clearSimInput();
  g.player = [newPlayer(), newPlayer()];
  for (let i = 0; i < g.enemy.length; i++) g.enemy[i] = newEnemy();
  g.enemyAvail.fill(1);
  g.endLevel = false;
  g.reallyEndLevel = false;
  g.levelEnd = 255;
  g.levelEndWarp = -4;
  g.portConfigDone = false;
  g.background2 = true;
  g.firstGameOver = true;
  g.soundQueue.fill(0);

  newOnePlayerGame();
  startLevelPlayerSetup();
}

/**
 * One tick of JE_main's level loop, player parts only (tyrian2.c L1020-1124 power,
 * L1323-1638 player shots without enemy collision, L1640-1655, L1855-1856).
 * `fixedPower` replaces the generator accrual when given.
 */
export function tick(fixedPower?: number): { shotsMoved: number } {
  beginDrawList();
  g.soundQueue.fill(0);

  if (!g.endLevel && g.textErase > 0) --g.textErase;

  if (fixedPower !== undefined) g.power = fixedPower;
  else {
    g.power += g.powerAdd;
    if (g.power > 900) g.power = 900;
  }

  drawState.pass = Pass.PlayerShots;
  const out = newPlayerShotMoveOut();
  let shotsMoved = 0;
  for (let z = 0; z < MAX_PWEAPON; z++) {
    if (g.shotAvail[z] !== 0) {
      shotsMoved++;
      player_shot_move_and_draw(z, out);
    }
  }

  for (const p of g.player) {
    p.last_x_shot_move = p.x;
    p.last_y_shot_move = p.y;
  }

  for (let i = 0; i < (g.twoPlayerMode ? 2 : 1); ++i) if (g.player[i].is_alive && !g.endLevel) JE_playerCollide(g.player[i], i + 1);

  drawState.pass = Pass.Player;
  if (g.firstGameOver) JE_mainGamePlayerFunctions();

  if (!g.portConfigChange) g.portConfigDone = true;
  return { shotsMoved };
}

export { drawList };
