import { expect, test } from "vitest";
import { PLAYFIELD_H, PLAYFIELD_W, PX_PER_UNIT, worldX, worldZ } from "../../src/game/playfield";

test("playfield centre maps to the world origin", () => {
  expect(worldX(PLAYFIELD_W / 2)).toBe(0);
  expect(worldZ(PLAYFIELD_H / 2)).toBe(0);
});

test("down the screen is toward the camera (+Z)", () => {
  expect(worldZ(PLAYFIELD_H)).toBeGreaterThan(0);
  expect(worldX(PLAYFIELD_W / 2 + PX_PER_UNIT)).toBe(1);
});
