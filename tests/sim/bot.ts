// The test bot of tests/sim/episode.test.ts and botTrace.test.ts (and of its C twin,
// tools/opentyrian-bot/driver.c): an invulnerable ship that always fires and sweeps left and right.
import { simInput } from "../../src/sim/input";
import { g } from "../../src/sim/state";

/** Input and cheats for the bot's tick `t` (0 = the tick after the level's first). */
export function botTick(t: number): void {
  g.player[0].invulnerable_ticks = 2;
  g.player[0].armor = Math.max(g.player[0].armor, 10);
  simInput.fire = true;
  simInput.left = Math.floor(t / 50) % 2 === 0;
  simInput.right = !simInput.left;
}
