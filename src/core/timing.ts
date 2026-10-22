// Game-logic timing.
//
// Tyrian's logic runs in fixed frames. At the "Normal" speed setting OpenTyrian programs the
// PIT (1193181.8 Hz = 315 MHz / 88 / 3) to interrupt every 0x4300 cycles and advances one
// logic frame every 2 interrupts (src/config.c, src/nortsong.c): 28.75 ms, ~34.8 Hz.
//
// Game code measures time and speed in *classic ticks* and converts them through a Timing,
// so the logic rate can later be raised (e.g. to 60 Hz) without touching game code.

const PIT_HZ = 315_000_000 / 88 / 3;
const NORMAL_PIT_DIVISOR = 0x4300;
const NORMAL_FRAME_COUNT = 2;

/** Length of one original logic frame at Normal speed, in milliseconds (~28.75). */
export const CLASSIC_TICK_MS = (NORMAL_PIT_DIVISOR * NORMAL_FRAME_COUNT * 1000) / PIT_HZ;

/** Original logic rate at Normal speed (~34.8 Hz). */
export const CLASSIC_TICK_HZ = 1000 / CLASSIC_TICK_MS;

export class Timing {
  /** Milliseconds per logic tick at this rate. */
  readonly tickMs: number;
  /** How many classic ticks one logic tick represents (1 at the classic rate, ~0.58 at 60 Hz). */
  readonly classicTicksPerTick: number;

  constructor(readonly tickHz: number = CLASSIC_TICK_HZ) {
    if (!(tickHz > 0)) throw new Error(`invalid tick rate: ${tickHz}`);
    this.tickMs = 1000 / tickHz;
    this.classicTicksPerTick = this.tickMs / CLASSIC_TICK_MS;
  }

  /** Scale a per-classic-tick quantity (speed, acceleration step) to one tick at this rate. */
  perTick(valuePerClassicTick: number): number {
    return valuePerClassicTick * this.classicTicksPerTick;
  }

  /** Convert a duration in classic ticks to ticks at this rate, rounded to the nearest tick. */
  ticks(classicTicks: number): number {
    return Math.round(classicTicks / this.classicTicksPerTick);
  }
}
