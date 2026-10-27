// The data cube reader's input and clock (src/app/cubeReaderControl.ts): the framework's presses
// become the C's per-frame input, run at the C's frame rate, drawn smoothly between frames.
import { beforeEach, describe, expect, test } from "vitest";
import { CubeReaderControl, HOLD_FRAMES, PAGE_FRAMES } from "../../src/app/cubeReaderControl";
import { CLASSIC_TICK_MS } from "../../src/core/timing";
import { cubeReader, type cube_struct } from "../../src/sim/cubes";

const c: cube_struct = { title: "", header: "", face_sprite: -1, text: [], last_line: 40 };

/** Run `ms` of display frames of `step` ms each; returns the drawn positions. */
function run(control: CubeReaderControl, ms: number, step = 1000 / 60, onFrame?: (t: number) => void): number[] {
  const drawn: number[] = [];
  for (let t = 0; t < ms; t += step) {
    onFrame?.(t);
    drawn.push(control.advance(c, step));
  }
  return drawn;
}

describe("CubeReaderControl", () => {
  let control: CubeReaderControl;
  beforeEach(() => {
    cubeReader.yLoc = 0;
    cubeReader.yChg = 0;
    control = new CubeReaderControl();
    control.sync();
  });

  test("a press is a tap: one line, a pixel per C frame, drawn smoothly", () => {
    control.press("down");
    const drawn = run(control, 1000);
    expect(cubeReader.yLoc).toBe(12);
    expect(drawn.at(-1)).toBe(12);
    // Never backwards, and in steps under a C pixel at 60 Hz (the C's frames are ~35 Hz).
    for (let i = 1; i < drawn.length; i++) {
      expect(drawn[i]).toBeGreaterThanOrEqual(drawn[i - 1]);
      expect(drawn[i] - drawn[i - 1]).toBeLessThan(1);
    }
    expect(drawn.some((y) => y % 1 !== 0)).toBe(true);
  });

  test("a tap takes the C's twelve frames for a line, and six at Page Down", () => {
    const frames = (n: number) => {
      for (let i = 0; i < n; i++) control.advance(c, CLASSIC_TICK_MS + 1e-9);
    };
    control.press("down");
    frames(1); // the press: yChg = 1
    frames(11);
    expect(cubeReader.yLoc).toBe(11);
    frames(1);
    expect(cubeReader.yLoc).toBe(12);
    expect(cubeReader.yChg).toBe(0);
    frames(20);
    expect(cubeReader.yLoc).toBe(12);
    control.press("pageDown");
    frames(7);
    expect(cubeReader.yLoc).toBe(24);
    frames(20);
    expect(cubeReader.yLoc).toBe(24);
    expect(HOLD_FRAMES).toBeLessThanOrEqual(6);
  });

  test("a press lets go of the opposite direction", () => {
    control.press("down");
    run(control, 60);
    control.press("up");
    run(control, 1000);
    expect(cubeReader.yLoc).toBe(0);
  });

  test("a click is one frame of the C's click", () => {
    control.press("clickDown");
    run(control, 1000);
    expect(cubeReader.yLoc).toBe(12);
    control.press("clickUp");
    run(control, 1000);
    expect(cubeReader.yLoc).toBe(0);
  });

  test("a held direction's repeats keep the text moving without a stop", () => {
    // The framework's pad repeat: a press, then 380 ms, then every 110 ms.
    const presses = [0, 380, 490, 600, 710, 820, 930];
    let next = 0;
    const drawn = run(control, 2000, 1000 / 60, (t) => {
      if (next < presses.length && t >= presses[next]) control.press("down"), next++;
    });
    // Moving from the end of the first line until the last line runs out, never pausing (the
    // first line can, as the first repeat comes after it).
    const start = drawn.findIndex((y) => y > 12);
    const end = drawn.findIndex((y) => y === cubeReader.yLoc);
    for (let i = start + 1; i <= end; i++) expect(drawn[i]).toBeGreaterThan(drawn[i - 1]);
    expect(cubeReader.yLoc % 12).toBe(0);
    expect(cubeReader.yLoc).toBeGreaterThanOrEqual(36);
  });

  test("a pad page is one page of Page Down", () => {
    control.page(true);
    run(control, 4000);
    expect(PAGE_FRAMES).toBe(54);
    expect(cubeReader.yLoc).toBe(9 * 12);
    control.page(false);
    run(control, 4000);
    expect(cubeReader.yLoc).toBe(0);
  });

  test("a page stops at the end of the text", () => {
    cubeReader.yLoc = (40 - 9) * 12 - 24;
    control.sync();
    control.page(true);
    run(control, 4000);
    expect(cubeReader.yLoc).toBe((40 - 9) * 12);
  });

  test("sync draws a position set from outside at once and drops pending input", () => {
    control.press("down");
    cubeReader.yLoc = 60;
    control.sync();
    expect(control.advance(c, 5)).toBe(60);
    run(control, 1000);
    expect(cubeReader.yLoc).toBe(60);
  });

  test("a stall doesn't race the text", () => {
    control.press("down");
    control.advance(c, 0);
    control.advance(c, 10_000);
    expect(cubeReader.yLoc).toBeLessThan(12);
  });
});
