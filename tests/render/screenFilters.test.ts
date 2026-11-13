// The screen filters' renderer-side rules (src/render/screenFilters.ts, screenHue.ts): which draws
// a filter covers, how the previous frame is weighted per display frame, and the hue stages.
import { describe, expect, test } from "vitest";
import * as THREE from "three";
import {
  LAVA_WAVE,
  ScreenFilterPass,
  WATER_WAVE,
  bankAtLuma,
  hueStages,
  levelBank,
  neutralInverse,
  neutralToneMap,
  passCeiling,
  previousFrameWeight,
  stageBank,
  stageUniforms,
  waveAt,
  type Wave,
} from "../../src/render/screenFilters";
import type { DrawList } from "../../src/sim/draw";
import type { PaletteTexture } from "../../src/render/paletteTexture";
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

  test("the waves have the C's extremes and period, without its whole-pixel steps (D135)", () => {
    // backgrnd.c: lava_filter abs(((diw >> 9) & 0xF) - 8) - 1, water_filter abs(((diw >> 10) & 0x7) - 4) - 1.
    const lava = (diw: number) => Math.abs(((diw >> 9) & 0xf) - 8) - 1;
    const water = (diw: number) => Math.abs(((diw >> 10) & 0x7) - 4) - 1;
    const check = (w: Wave, c: (diw: number) => number) => {
      let lo = Infinity;
      let hi = -Infinity;
      for (let diw = 0; diw < 320 * 185; diw += 8) {
        lo = Math.min(lo, c(diw));
        hi = Math.max(hi, c(diw));
        // Close to the C's table everywhere (a triangle; the sine bows out a little).
        expect(Math.abs(waveAt(w, diw) - c(diw))).toBeLessThan(w.amplitude / 2 + 1);
        // Periodic like the table.
        expect(c(diw + w.period)).toBe(c(diw));
      }
      expect(w.mean - w.amplitude).toBe(lo);
      expect(w.mean + w.amplitude).toBe(hi);
      expect(waveAt(w, 0)).toBeCloseTo(c(0), 6);
      // Continuous: a sixteenth of a row (20 diw) moves it far less than a pixel.
      for (let diw = 0; diw < w.period; diw += 7) expect(Math.abs(waveAt(w, diw + 20) - waveAt(w, diw))).toBeLessThan(0.1);
    };
    check(LAVA_WAVE, lava);
    check(WATER_WAVE, water);
  });
});

describe("a hue filter's colour for the lit scene (D191)", () => {
  // LAVA RUN's palette (5), bank 7: lava_filter's hue. sRGB levels as palette.dat gives them.
  const LAVA_SRGB = [
    [32, 0, 0], [56, 0, 0], [81, 0, 0], [109, 4, 0], [134, 4, 0], [158, 8, 0], [186, 12, 0], [211, 20, 0],
    [223, 60, 0], [231, 97, 12], [235, 138, 24], [243, 174, 36], [251, 203, 48], [255, 231, 60], [255, 251, 150], [255, 255, 243],
  ];
  const toLinear = (v: number) => ((v /= 255) <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
  const bank = LAVA_SRGB.map((c) => c.map(toLinear) as [number, number, number]);
  const luma = (c: readonly number[]) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];

  test("every shade of the hue maps to itself", () => {
    for (const e of bank) bankAtLuma(luma(e), bank).forEach((v, i) => expect(v).toBeCloseTo(e[i], 6));
  });

  test("a white sheen or grey reflection takes the hue at its luminance, which it keeps", () => {
    for (const grey of [0.02, 0.1, 0.2, 0.4, 0.7, 0.95]) {
      const c = bankAtLuma(luma([grey, grey, grey]), bank);
      expect(luma(c)).toBeCloseTo(grey, 6);
      // Lava's hue: red at least as strong as green, green at least as strong as blue.
      expect(c[0]).toBeGreaterThanOrEqual(c[1]);
      expect(c[1]).toBeGreaterThanOrEqual(c[2]);
    }
    // A mid grey, the crust's sheen, comes out red-orange, not pink-grey: between shades 8 and 9.
    const sheen = bankAtLuma(luma([0.22, 0.22, 0.22]), bank);
    expect(sheen[2]).toBeLessThan(0.01);
    expect(sheen[0]).toBeGreaterThan(0.7);
    // Black stays black (below the first shade it is scaled), and past the top the top shade is.
    expect(bankAtLuma(0, bank)).toEqual([0, 0, 0]);
    const over = bankAtLuma(2 * luma(bank[15]), bank);
    over.forEach((v, i) => expect(v).toBeCloseTo(2 * bank[15][i], 6));
  });

  test("a run that dips is read by its running maximum (a level brightness clamps shades)", () => {
    const dipped = bank.slice();
    dipped[9] = bank[5];
    let prev = -1;
    for (let l = 0; l <= 1; l += 0.01) {
      const c = bankAtLuma(l, dipped);
      expect(Number.isFinite(c[0] + c[1] + c[2])).toBe(true);
      expect(luma(c)).toBeGreaterThanOrEqual(prev - 1e-9);
      prev = luma(c);
    }
  });

  test("the tone mapping's inverse gives back the scene colour", () => {
    for (const c of [[0.01, 0.002, 0], [0.3, 0.05, 0.01], [0.75, 0.2, 0.05], [0.9, 0.4, 0.02], [1.6, 0.5, 0.1], [3, 2.5, 1]] as const) {
      neutralInverse(neutralToneMap(c)).forEach((v, i) => expect(v).toBeCloseTo(c[i], 4));
      neutralInverse(neutralToneMap(c, 0.8), 0.8).forEach((v, i) => expect(v).toBeCloseTo(c[i], 4));
    }
    // So a shade chosen as displayed is displayed as that shade, as far as the tone mapping can show
    // it: over a peak of 0.76 it pales every colour a little (shade 11's blue comes out 42, not 36),
    // and near a peak of 1 a lot (the lava's yellow, 13, shows cream), as it does any lit colour.
    for (const e of bank) {
      const shown = neutralToneMap(neutralInverse(e));
      const peak = Math.max(...e);
      if (peak <= 0.9) shown.forEach((v, i) => expect(Math.abs(v - e[i])).toBeLessThan(0.008));
      expect(luma(shown)).toBeGreaterThan(luma(e) - 0.01);
      expect(shown[0]).toBeGreaterThanOrEqual(shown[1] - 1e-9);
      expect(shown[1]).toBeGreaterThanOrEqual(shown[2] - 1e-9);
    }
  });

  test("each filter's bank: lava 0x70, iced 0x80, water its hue, blur none; JE_filterScreen's hue", () => {
    expect(stageBank({ kind: "lava", pass: Pass.GroundEnemies, temporal: true })).toBe(0x70);
    expect(stageBank({ kind: "iced", pass: Pass.Starfield, temporal: true })).toBe(0x80);
    expect(stageBank({ kind: "water", pass: Pass.Background2Under, temporal: false, hue: 0x30 })).toBe(0x30);
    expect(stageBank({ kind: "blur", pass: Pass.Background3Under, temporal: false })).toBe(-1);
    const u = stageUniforms([{ kind: "lava", pass: Pass.GroundEnemies, temporal: true }], 0.016, true);
    expect(u.bank.slice(0, 2)).toEqual([0x70, -1]);
    expect(levelBank(-99)).toBe(-1);
    expect(levelBank(9)).toBe(0x90);
    expect(levelBank(0x1c)).toBe(0xc0);
  });

  test("JE_filterScreen's hue alone turns the filtered frame on", () => {
    const renderer = { capabilities: { maxSamples: 4 } } as unknown as THREE.WebGLRenderer;
    const pass = new ScreenFilterPass(renderer, { screenHue: new ScreenHue() } as unknown as PaletteTexture);
    const list = (filter: number) => ({ items: [], palette: 0, filter, brightness: 0, screen: null }) as unknown as DrawList;
    pass.setDrawList(list(-99));
    expect(pass.active).toBe(false);
    pass.setDrawList(list(9));
    expect(pass.active).toBe(true);
    pass.setDrawList(list(-99));
    expect(pass.active).toBe(false);
  });
});

describe("the filtered frame's programs, warmed (D159)", () => {
  test("compileFiltered compiles with the scene target bound, then puts the previous target back", () => {
    let target: unknown = null;
    const renderer = {
      capabilities: { maxSamples: 4 },
      getRenderTarget: () => target,
      setRenderTarget: (t: unknown) => (target = t),
    } as unknown as THREE.WebGLRenderer;
    const pass = new ScreenFilterPass(renderer, { screenHue: new ScreenHue() } as unknown as PaletteTexture);
    const seen: unknown[] = [];
    const done = Promise.resolve();
    const out = pass.compileFiltered(() => (seen.push(target), [done, done]));
    expect(out).toEqual([done, done]);
    expect(seen[0]).toBeInstanceOf(THREE.WebGLRenderTarget);
    expect(target).toBeNull();
  });
});
