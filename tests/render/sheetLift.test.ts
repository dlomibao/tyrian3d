// D129: a blended background-2 sheet tile is raised over the models of earlier passes it overlaps on
// screen and kept under those of later passes, so a tall ground model isn't cut by a straight line.
import { describe, expect, test } from "vitest";
import { Pass } from "../../src/sim/draw";
import { COVER_CLEARANCE, coverHeight, MODEL_COVER_OVERLAP, SHEET_CLEARANCE, sheetHeight, type PlacedExtent } from "../../src/render/sheetLift";

const block = (pass: Pass, left: number, top: number, low: number, high: number): PlacedExtent => ({ pass, left, top, right: left + 24, bottom: top + 28, low, high });
const SHEET = Pass.Background2Mid;
const BASE = 0.9;

describe("sheet lift", () => {
  test("no model under it: the pass's own height", () => {
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [])).toBe(BASE);
  });

  test("a tall ground block it covers lifts it just over the block's top", () => {
    const ground = block(Pass.GroundEnemies, 110, 60, 0.45, 1.26);
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [ground])).toBeCloseTo(1.26 + SHEET_CLEARANCE);
  });

  test("a block elsewhere on screen, or one lower than the sheet, changes nothing", () => {
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [block(Pass.GroundEnemies, 200, 60, 0.45, 1.26)])).toBe(BASE);
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [block(Pass.GroundEnemies, 110, 60, 0.45, 0.7)])).toBe(BASE);
  });

  test("a later pass's model above stays above; if they'd cross, half way", () => {
    const ground = block(Pass.GroundEnemies, 110, 60, 0.45, 1.26);
    const sky = block(Pass.SkyEnemies, 105, 55, 1.6, 2.1);
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [ground, sky])).toBeCloseTo(1.26 + SHEET_CLEARANCE);
    const lowSky = block(Pass.SkyEnemies, 105, 55, 1.2, 2.1);
    expect(sheetHeight(BASE, SHEET, 100, 50, 24, 28, [ground, lowSky])).toBeCloseTo((1.26 + 1.2) / 2);
  });

  test("never lower than its pass's height", () => {
    const sunk = block(Pass.GroundEnemies, 110, 60, -0.2, 1.0);
    expect(sheetHeight(0.05, Pass.Background2Under, 100, 50, 24, 28, [sunk])).toBe(0.05);
  });
});

// D181: a later draw rises over the earlier models that bury it on screen, as the C drew it over them.
describe("cover height", () => {
  const SHOT = 3.75;
  test("nothing earlier, or nothing taller: its own height", () => {
    expect(coverHeight(SHOT, SHOT, SHOT, 100, 50, 108, 58, [])).toBe(SHOT);
    expect(coverHeight(SHOT, SHOT, SHOT, 100, 50, 108, 58, [block(Pass.TopEnemies, 96, 44, 2.1, 3.2)])).toBe(SHOT);
  });

  test("a shot over a boss piece taller than the shot pass clears its top (BOTANY A, L3)", () => {
    const hull = block(Pass.TopEnemies, 96, 44, 2.1, 4.78);
    expect(coverHeight(SHOT, SHOT, SHOT, 100, 50, 108, 58, [hull])).toBeCloseTo(4.78 + COVER_CLEARANCE);
    // Off the piece, or only touching its edge, it stays.
    expect(coverHeight(SHOT, SHOT, SHOT, 121, 50, 129, 58, [hull])).toBe(SHOT);
    expect(coverHeight(SHOT, SHOT, SHOT, 200, 50, 208, 58, [hull])).toBe(SHOT);
  });

  test("a model is raised by its lowest point, and only when its top is buried", () => {
    // GEM WAR: the gem disc (0.36 tall over its base) drawn over the hull (0.62).
    const hull = block(Pass.TopEnemies, 100, 50, 2.3, 3.04);
    const lifted = coverHeight(2.5, 2.08, 2.81, 100, 50, 124, 78, [hull], MODEL_COVER_OVERLAP);
    expect(lifted - 2.5 + 2.08).toBeCloseTo(3.04 + COVER_CLEARANCE);
    // Its top already the higher one (D166's two halves): left alone.
    expect(coverHeight(2.5, 2.3, 3.2, 100, 50, 124, 78, [hull], MODEL_COVER_OVERLAP)).toBe(2.5);
  });

  test("models meeting along a seam don't stack; ones over each other do", () => {
    const upper = block(Pass.GroundEnemies, 100, 50, 0.45, 1.5);
    // Assembly pieces side by side, boxes crossing by 3 px.
    expect(coverHeight(0.45, 0.45, 1.2, 121, 50, 145, 78, [upper], MODEL_COVER_OVERLAP)).toBe(0.45);
    // A seam 6 px deep: under a quarter of the box.
    expect(coverHeight(0.45, 0.45, 1.2, 100, 72, 124, 100, [upper], MODEL_COVER_OVERLAP)).toBe(0.45);
    // Half over it.
    expect(coverHeight(0.45, 0.45, 1.2, 100, 64, 124, 92, [upper], MODEL_COVER_OVERLAP)).toBeCloseTo(1.5 + COVER_CLEARANCE);
  });
});
