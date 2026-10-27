// The test bot of tests/sim/episode.test.ts and botTrace.test.ts (and of its C twin,
// tools/opentyrian-bot/driver.c): an invulnerable ship that always fires and sweeps left and right.
import { simInput, simInputs } from "../../src/sim/input";
import { g } from "../../src/sim/state";

/** Input and cheats for the bot's tick `t` (0 = the tick after the level's first). */
export function botTick(t: number): void {
  g.player[0].invulnerable_ticks = 2;
  g.player[0].armor = Math.max(g.player[0].armor, 10);
  simInput.fire = true;
  simInput.left = Math.floor(t / 50) % 2 === 0;
  simInput.right = !simInput.left;
}

/**
 * [two-player] Player 2's mouse for the bot's tick `t` (driver.c bot2Mouse): in a 300-tick cycle,
 * steer toward player 1 until the two are stopped within 8 pixels (they link), circle with fire
 * held (turns the linked gun), then move without firing (breaks the link). Player 1 is botTick's.
 */
export function botTick2(t: number): void {
  const input = simInputs[1];
  const [p1, p2] = g.player;
  const phase = t % 300;
  const ddx = p1.x - p2.x;
  const ddy = p1.y - p2.y;
  const clamp = (v: number) => Math.max(-12, Math.min(12, v));
  let dx = 0;
  let dy = 0;
  let fire = true;
  if (phase < 150) {
    if (Math.abs(ddx) >= 6 || Math.abs(ddy) >= 6) {
      dx = clamp(ddx);
      dy = clamp(ddy);
    }
  } else if (phase < 250) {
    const circle = [[8, 0], [0, 8], [-8, 0], [0, -8]];
    [dx, dy] = circle[Math.floor(phase / 10) % 4];
  } else {
    fire = false;
    dx = phase < 275 ? -10 : 10;
    dy = -6;
  }
  input.mouseXR = dx;
  input.mouseYR = dy;
  input.mouseLeft = fire;
}
