// D129: a blended background-2 sheet tile is raised over the models of earlier passes it overlaps on
// screen and kept under those of later passes, so a tall ground model isn't cut by a straight line.
import { describe, expect, test } from "vitest";
import { Pass } from "../../src/sim/draw";
import { SHEET_CLEARANCE, sheetHeight, type PlacedExtent } from "../../src/render/sheetLift";

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
