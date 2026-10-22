import type { InputState } from "../core/input";
import type { Timing } from "../core/timing";
import { Player } from "./player";

// Placeholder background scroll speed until level data drives it (#14).
const SCROLL_PX_PER_CLASSIC_TICK = 1;

/** All game state advanced by the logic loop. Rendering reads it but never writes it. */
export class World {
  readonly player = new Player();
  /** Distance scrolled, in Tyrian pixels. */
  scrollY = 0;
  prevScrollY = 0;
  tick = 0;

  constructor(readonly timing: Timing) {}

  update(input: InputState): void {
    this.prevScrollY = this.scrollY;
    this.scrollY += this.timing.perTick(SCROLL_PX_PER_CLASSIC_TICK);
    this.player.update(input, this.timing);
    this.tick++;
  }
}
