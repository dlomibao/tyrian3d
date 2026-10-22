import { describe, expect, test } from "vitest";
import { decodeSprite2, decodeTableSprite, mainShapeTables, parseSpriteTable, sprite2Count } from "../../src/data";
import { hasData, readData } from "./dataDir";

describe.skipIf(!hasData("tyrian.shp"))("tyrian.shp", () => {
  const tables = mainShapeTables(readData("tyrian.shp"));

  test("has the 12 tables JE_loadMainShapeTables expects", () => {
    expect(tables).toHaveLength(12);
  });

  test("sprite tables 0-6 parse to exactly their byte range", () => {
    for (let i = 0; i < 7; i++) {
      const { sprites, end } = parseSpriteTable(tables[i]);
      expect(sprites.length).toBeGreaterThan(0);
      expect(end).toBeLessThanOrEqual(tables[i].length);
      for (const s of sprites) if (s) expect(decodeTableSprite(s).pixels.length).toBe(s.width * s.height);
    }
  });

  test("decodes the USP Talon's top-left tile (player ships sheet, sprite 233)", () => {
    const ships = tables[8];
    expect(sprite2Count(ships)).toBe(304);
    const tile = decodeSprite2(ships, 233);
    expect(tile.height).toBe(14);
    // Row 2 of the 24x28 ship has its nose tip at x 11-12: x 11 is in this tile, outlined in colour 0x10.
    expect(tile.pixels[2 * 12 + 11]).toBe(0x10);
    expect(tile.pixels[2 * 12 + 10]).toBe(-1);
  });
});
