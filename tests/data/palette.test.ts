import { beforeAll, describe, expect, test } from "vitest";
import {
  PALETTE_COUNT,
  paletteToRgba8,
  parsePalettes,
  vga6To8,
  type Palette,
} from "../../src/data/palette";
import { hasData, readData } from "./dataDir";

test("vga6To8 matches loadPals' rescale", () => {
  expect(vga6To8(0)).toBe(0);
  expect(vga6To8(1)).toBe(4);
  expect(vga6To8(32)).toBe(130);
  expect(vga6To8(63)).toBe(255);
});

describe.skipIf(!hasData("palette.dat"))("palette.dat", () => {
  let bytes: Uint8Array;
  let palettes: Palette[];
  beforeAll(() => {
    bytes = readData("palette.dat");
    palettes = parsePalettes(bytes);
  });

  test("holds exactly 23 palettes, as loadPals asserts", () => {
    expect(bytes.length).toBe(PALETTE_COUNT * 768);
    expect(palettes).toHaveLength(PALETTE_COUNT);
  });

  test("values are raw 6-bit VGA components", () => {
    for (const p of palettes) {
      expect(p).toHaveLength(768);
      expect(Math.max(...p)).toBeLessThanOrEqual(63);
    }
  });

  test("known entries", () => {
    // Palette 7 is the one the episode script's `]C[` command resets to (JE_loadMap).
    expect([...palettes[7]!.subarray(0, 3)]).toEqual([0, 0, 0]);
    expect([...palettes[7]!.subarray(255 * 3)]).toEqual([63, 63, 63]);
    expect([...paletteToRgba8(palettes[7]!).subarray(255 * 4)]).toEqual([255, 255, 255, 255]);
  });
});
