import { describe, expect, test } from "vitest";
import { bankShift, visibleCentreX } from "../../src/render/bankShift";
import { mainShapeTables } from "../../src/data/sprites";
import { hasData, readData } from "../data/dataDir";

// The USP Talon (shipGraphic 233, tyrian.shp table 8): its banking frames 229..237, step 2.
const TALON = 233;

describe.skipIf(!hasData("tyrian.shp"))("bank shift (D62)", () => {
  const sheet = () => mainShapeTables(readData("tyrian.shp"))[8];

  test("the Talon's banking frames sit up to 3 pixels toward the bank", () => {
    const s = sheet();
    // Opaque columns: hard left 2-15, level 3-20, hard right 8-21.
    expect(visibleCentreX(s, TALON)).toBe(12);
    expect([-2, -1, 0, 1, 2].map((b) => bankShift("talon", s, TALON, TALON + b * 2))).toEqual([-3, -1, 0, 1, 3]);
  });

  test("with the shift, the model at the x limits covers the original sprite's columns", () => {
    // At x = 40 the cell starts 11 pixels into the window (x - 5 - 24), at x = 256 at 227; the
    // model is centred on the cell's middle plus the shift.
    const s = sheet();
    const left = 11 + 12 + bankShift("talon", s, TALON, TALON - 4);
    const right = 227 + 12 + bankShift("talon", s, TALON, TALON + 4);
    expect(left).toBe(11 + visibleCentreX(s, TALON - 4)); // middle of window columns 13-26
    expect(right).toBe(227 + visibleCentreX(s, TALON + 4)); // middle of window columns 235-248
    expect([left, right]).toEqual([20, 242]);
  });
});
