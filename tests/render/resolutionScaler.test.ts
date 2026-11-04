import { describe, expect, it } from "vitest";
import { HOLD_S, MIN_SCALE, ResolutionScaler, STEP, WINDOW } from "../../src/render/resolutionScaler";

/** Feed `n` frames `dt` ms apart with `cpu` ms of main-thread work; returns the scale changes. */
function run(s: ResolutionScaler, n: number, dt: number, cpu = 2, t0 = { t: 0 }): number {
  let changes = 0;
  for (let i = 0; i < n; i++) {
    t0.t += dt;
    if (s.frame(t0.t, cpu)) changes++;
  }
  return changes;
}

describe("ResolutionScaler (D91)", () => {
  it("never moves at 60 fps, or at 120 fps with every other frame late", () => {
    const s = new ResolutionScaler();
    const t = { t: 0 };
    run(s, 600, 1000 / 60, 3, t);
    expect(s.scale).toBe(1);
    for (let i = 0; i < 600; i++) s.frame((t.t += i % 2 ? 8.3 : 16.7), 3);
    expect(s.scale).toBe(1);
  });

  it("lowers a step per late window while the GPU can't keep up, down to MIN_SCALE", () => {
    const s = new ResolutionScaler();
    const t = { t: 0 };
    run(s, WINDOW + 1, 33, 3, t); // the first frame only starts the clock
    expect(s.scale).toBeCloseTo(STEP);
    run(s, WINDOW * 20, 33, 3, t);
    expect(s.scale).toBeCloseTo(MIN_SCALE);
  });

  it("doesn't lower when the main thread is the slow part", () => {
    const s = new ResolutionScaler();
    run(s, WINDOW * 3, 33, 20);
    expect(s.scale).toBe(1);
  });

  it("raises again after a calm spell, waiting longer after an undone raise", () => {
    const s = new ResolutionScaler();
    const t = { t: 0 };
    run(s, WINDOW + 1, 33, 3, t); // the first frame only starts the clock
    expect(s.scale).toBeCloseTo(STEP);
    run(s, Math.ceil((HOLD_S * 1000) / 16.7) + WINDOW, 1000 / 60, 3, t);
    expect(s.scale).toBe(1);
    run(s, WINDOW, 33, 3, t); // undone at once
    expect(s.scale).toBeCloseTo(STEP);
    run(s, Math.ceil((HOLD_S * 1000) / 16.7) + WINDOW, 1000 / 60, 3, t);
    expect(s.scale).toBeCloseTo(STEP); // now holds twice as long
    run(s, Math.ceil((HOLD_S * 1000) / 16.7) + WINDOW, 1000 / 60, 3, t);
    expect(s.scale).toBe(1);
  });

  it("ignores pauses, and off or reset means full scale", () => {
    const s = new ResolutionScaler();
    const t = { t: 0 };
    for (let i = 0; i < WINDOW * 2; i++) s.frame((t.t += 400), 2);
    expect(s.scale).toBe(1);
    run(s, WINDOW, 33, 3, t);
    expect(s.scale).toBeLessThan(1);
    expect(s.reset()).toBe(true);
    expect(s.scale).toBe(1);
    s.enabled = false;
    run(s, WINDOW * 3, 33, 3, t);
    expect(s.scale).toBe(1);
  });
});
