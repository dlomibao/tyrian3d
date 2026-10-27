// [two-player] The messages between levels, for one player or two. The C shows its level-end
// screen (JE_endLevelAni) and, in a two-player game, both players' scores ("Player 1 Score:",
// miscText[40..41], as its episode-end text does: tyrian2.c L2496-2502).

import { g } from "../sim/state";

const scoreLabel = (i: number) => g.miscText[40 + i]?.trim() || `Player ${i + 1} Score:`;

/** The "Level complete" message's lines. */
export function levelCompleteLines(): string[] {
  const scores = g.twoPlayerMode ? [0, 1].map((i) => `${scoreLabel(i)} ${g.player[i].cash}`) : [`Score ${g.player[0].cash}`];
  return [g.levelName.trim(), ...scores, `Enemies destroyed ${g.enemyKilled} of ${g.totalEnemy}`];
}

/** The "Game over" message's lines. */
export function gameOverLines(): string[] {
  return g.twoPlayerMode ? ["Both ships were destroyed."] : ["Your ship was destroyed."];
}
