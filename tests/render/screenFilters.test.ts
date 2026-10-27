// The screen filters' renderer-side rules (src/render/screenFilters.ts, screenHue.ts): which draws
// a filter covers, how the previous frame is weighted per display frame, and the hue stages.
import { describe, expect, test } from "vitest";
import { hueStages, passCeiling, previousFrameWeight, stageUniforms } from "../../src/render/screenFilters";
import { ScreenHue } from "../../src/render/screenHue";
import { PASS_HEIGHT } from "../../src/render/passHeights";
import { CLASSIC_TICK_MS } from "../../src/core/timing";
import { Pass } from "../../src/sim/draw";

describe("screen filters", () => {
  test("a filter's ceiling sits between its last pass and the next one up", () => {
    const passes = Object.keys(PASS_HEIGHT).map(Number) as Pass[];
    for (const p of passes) {
      const c = passCeiling(p);
      expect(c).toBeGreaterThan(PASS_HEIGHT[p]);
      for (const q of passes) if (PASS_HEIGHT[q] > PASS_HEIGHT[p]) expect(c).toBeLessThan(PASS_HEIGHT[q]);
    }
    // The ground enemies are under the lava when smoothie_data[0] > 0, background 2 (mid) isn't.
    expect(PASS_HEIGHT[Pass.GroundEnemies]).toBeLessThan(passCeiling(Pass.GroundEnemies));
    expect(PASS_HEIGHT[Pass.Background2Mid]).toBeGreaterThan(passCeiling(Pass.GroundEnemies));
  });

  test("the previous frame fades by half per classic tick, whatever the frame rate", () => {
    expect(previousFrameWeight(CLASSIC_TICK_MS / 1000)).toBeCloseTo(0.5, 6);
    expect(previousFrameWeight(0)).toBe(1);
    // Two frames of half a tick each: the same as one tick.
    const half = previousFrameWeight(CLASSIC_TICK_MS / 2000);
    expect(half * half).toBeCloseTo(0.5, 6);
  });

  test("only the first filter reads the previous frame; the others work in place", () => {
    const u = stageUniforms(
      [
        { kind: "lava", pass: Pass.GroundEnemies, temporal: true },
        { kind: "blur", pass: Pass.Background3Under, temporal: false },
      ],
      CLASSIC_TICK_MS / 1000,
      true,
    );
    expect(u.count).toBe(2);
    expect(u.kind.slice(0, 2)).toEqual([1, 4]);
    expect(u.prev[0]).toBeCloseTo(0.5, 6);
    expect(u.prev[1]).toBe(-1);
    // No history yet (the filter just switched on, or the window resized): nothing to blend.
    expect(stageUniforms([{ kind: "blur", pass: Pass.Background3Under, temporal: true }], 0.016, false).prev[0]).toBe(0);
  });

  test("the hue stages: lava 0x70, iced 0x80, water its own hue on water indices, blur none", () => {
    const stages = hueStages([
      { kind: "iced", pass: Pass.Starfield, temporal: true },
      { kind: "water", pass: Pass.Background2Under, temporal: false, hue: 0x50 },
      { kind: "lava", pass: Pass.GroundEnemies, temporal: false },
      { kind: "blur", pass: Pass.Background3Under, temporal: false },
    ]);
    expect(stages).toEqual([
      { ceiling: passCeiling(Pass.Starfield), hue: 8, water: false },
      { ceiling: passCeiling(Pass.Background2Under), hue: 5, water: true },
      { ceiling: passCeiling(Pass.GroundEnemies), hue: 7, water: false },
    ]);

    // Models take the last whole-model hue that covers their pass; the water's per-index test
    // doesn't apply to them.
    const hue = new ScreenHue();
    hue.set(stages);
    expect(hue.uniforms.screenHueCount.value).toBe(3);
    expect(hue.modelHue(PASS_HEIGHT[Pass.Background1])).toBe(0x70);
    expect(hue.modelHue(PASS_HEIGHT[Pass.GroundEnemies])).toBe(0x70);
    expect(hue.modelHue(PASS_HEIGHT[Pass.SkyEnemies])).toBe(-1);
    hue.set([]);
    expect(hue.uniforms.screenHueCount.value).toBe(0);
    expect(hue.modelHue(0)).toBe(-1);
  });
});
