import type { InputState } from "../core/input";
import type { Timing } from "../core/timing";
import { PLAYER_MAX_X, PLAYER_MAX_Y, PLAYER_MIN_X, PLAYER_MIN_Y } from "./playfield";

// Placeholder movement until OpenTyrian's player physics is ported (#11).
const MOVE_PX_PER_CLASSIC_TICK = 4;

export class Player {
  /** Position in Tyrian pixels. */
  x = 148;
  y = 140;
  /** Position at the previous tick, for render interpolation. */
  prevX = this.x;
  prevY = this.y;
  /** Horizontal movement this tick, -1..1, used to bank the ship. */
  bank = 0;

  update(input: InputState, timing: Timing): void {
    this.prevX = this.x;
    this.prevY = this.y;
    const speed = timing.perTick(MOVE_PX_PER_CLASSIC_TICK);
    this.x = clamp(this.x + input.x * speed, PLAYER_MIN_X, PLAYER_MAX_X);
    this.y = clamp(this.y + input.y * speed, PLAYER_MIN_Y, PLAYER_MAX_Y);
    this.bank = input.x;
  }
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
