// Fixed-timestep accumulator: logic advances in whole ticks, rendering happens every display
// frame and interpolates between the last two logic states using `alpha`.

export interface StepResult {
  /** Logic ticks to run this frame. */
  steps: number;
  /** Fraction (0..1) of the way from the previous logic state to the current one. */
  alpha: number;
}

export class FixedStepper {
  private accumulatorMs = 0;

  /**
   * @param tickMs length of one logic tick
   * @param maxSteps cap on catch-up ticks per frame, so a stalled tab doesn't fast-forward
   */
  constructor(
    private readonly tickMs: number,
    private readonly maxSteps = 8,
  ) {}

  advance(elapsedMs: number): StepResult {
    this.accumulatorMs += Math.max(0, elapsedMs);
    let steps = Math.floor(this.accumulatorMs / this.tickMs);
    if (steps > this.maxSteps) {
      steps = this.maxSteps;
      this.accumulatorMs = 0;
    } else {
      this.accumulatorMs -= steps * this.tickMs;
    }
    return { steps, alpha: this.accumulatorMs / this.tickMs };
  }
}
