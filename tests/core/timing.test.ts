import { describe, expect, test } from "vitest";
import { CLASSIC_TICK_HZ, CLASSIC_TICK_MS, Timing } from "../../src/core/timing";

describe("Timing", () => {
  test("classic tick matches OpenTyrian's Normal speed", () => {
    expect(CLASSIC_TICK_MS).toBeCloseTo(28.75, 2);
    expect(CLASSIC_TICK_HZ).toBeCloseTo(34.78, 2);
  });

  test("classic rate is the identity", () => {
    const t = new Timing();
    expect(t.perTick(4)).toBeCloseTo(4);
    expect(t.ticks(35)).toBe(35);
  });

  test("60 Hz covers the same distance and duration per second", () => {
    const t = new Timing(60);
    expect(t.perTick(4) * 60).toBeCloseTo(4 * CLASSIC_TICK_HZ);
    expect(t.ticks(CLASSIC_TICK_HZ)).toBe(60);
  });
});
