import { FixedStepper } from "./fixedStep";

export interface LoopCallbacks {
  /** Advance game logic by one tick. */
  update(): void;
  /** Draw a frame; alpha interpolates between the previous and current logic state. */
  render(alpha: number): void;
}

/** Drives fixed-rate logic and display-rate rendering from requestAnimationFrame. */
export function startLoop(tickMs: number, callbacks: LoopCallbacks): () => void {
  const stepper = new FixedStepper(tickMs);
  let last = performance.now();
  let handle = 0;

  const frame = (now: number) => {
    const { steps, alpha } = stepper.advance(now - last);
    last = now;
    for (let i = 0; i < steps; i++) callbacks.update();
    callbacks.render(alpha);
    handle = requestAnimationFrame(frame);
  };
  handle = requestAnimationFrame(frame);
  return () => cancelAnimationFrame(handle);
}
