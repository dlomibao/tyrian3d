// HD terrain's palette bank lookup (paletteTexture.ts nearestIndexLut, terrainMaterial.ts, D111):
// painted colours find the raw palette's nearest index, so water_filter's exception for the
// (index & 0x30) == 0 banks reaches them. LAVA EXIT (4.9) drew its salmon-pink patches as
// saturated red when every painting took the hue ramp's bank (16 + shade).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { parsePalettes } from "../../src/data/palette";
import {
  nearestIndexLut,
  PALETTE_LUT_HEIGHT,
  PALETTE_LUT_SIZE,
  PALETTE_LUT_WIDTH,
  PaletteTexture,
  paletteLutCell,
  paletteLutOffset,
} from "../../src/render/paletteTexture";
import { terrainMaterial } from "../../src/render/remaster/terrainMaterial";
import { hasData, readData } from "../data/dataDir";

/** The LUT's index for an sRGB colour (0..255 channels), looked up as the shader does. */
function lookup(lut: Uint8Array, r: number, g: number, b: number): number {
  return lut[paletteLutOffset(paletteLutCell(r / 255), paletteLutCell(g / 255), paletteLutCell(b / 255))];
}

/** A palette (6-bit) from 16 ramps given as functions of the shade 0..15 -> 8-bit RGB. */
function ramps(fns: Record<number, (s: number) => [number, number, number]>): Uint8Array {
  const p = new Uint8Array(768);
  for (let i = 0; i < 256; i++) {
    const fn = fns[i >> 4] ?? (() => [0, 0, 0] as [number, number, number]);
    const c = fn(i & 15);
    for (let k = 0; k < 3; k++) p[i * 3 + k] = Math.round(c[k] / 4.05);
  }
  return p;
}

describe("nearestIndexLut", () => {
  test("the texture layout matches the shader's texelFetch (blue slices, 8 to a row)", () => {
    expect([PALETTE_LUT_WIDTH, PALETTE_LUT_HEIGHT]).toEqual([256, 128]);
    const n = PALETTE_LUT_SIZE;
    const seen = new Set<number>();
    for (let b = 0; b < n; b++)
      for (let g = 0; g < n; g++)
        for (let r = 0; r < n; r++) {
          const o = paletteLutOffset(r, g, b);
          // terrainNearest: ivec2(c.r + 32 * (c.b & 7), c.g + 32 * (c.b >> 3)).
          expect(o).toBe((g + n * (b >> 3)) * PALETTE_LUT_WIDTH + r + n * (b & 7));
          seen.add(o);
        }
    expect(seen.size).toBe(PALETTE_LUT_WIDTH * PALETTE_LUT_HEIGHT);
    expect(paletteLutCell(0)).toBe(0);
    expect(paletteLutCell(1)).toBe(n - 1);
    expect(paletteLutCell(1.2)).toBe(n - 1);
  });

  test("a colour takes the bank of its nearest ramp, exempt or not", () => {
    const pal = ramps({
      0: (s) => [s * 17, s * 17, s * 17], // grey
      4: (s) => [40 + s * 14, 10 + s * 9, 8 + s * 8], // salmon
      7: (s) => [30 + s * 15, s * 4, 0], // red
    });
    const lut = nearestIndexLut(pal);
    expect(lookup(lut, 200, 110, 96) & 0xf0).toBe(0x40);
    expect(lookup(lut, 200, 30, 0) & 0xf0).toBe(0x70);
    expect(lookup(lut, 128, 128, 128) & 0xf0).toBe(0x00);
    expect(nearestIndexLut(pal)).toBe(lut); // cached per palette
  });
});

describe.skipIf(!hasData("palette.dat"))("LAVA EXIT's palette (5)", () => {
  test("the atlas's salmon pink is water_filter-exempt, its lava is not", () => {
    const lut = nearestIndexLut(parsePalettes(readData("palette.dat"))[5]);
    // Medians and percentiles of public/art/terrain/shapes)/0.webp's pink and lava tiles.
    for (const pink of [[160, 68, 55], [134, 48, 36], [192, 97, 83]] as const) {
      const i = lookup(lut, pink[0], pink[1], pink[2]);
      expect(i & 0xf0).toBe(0x40);
      expect(i & 0x30).toBe(0);
    }
    for (const lava of [[158, 8, 0], [230, 60, 10]] as const) expect(lookup(lut, lava[0], lava[1], lava[2]) & 0x30).not.toBe(0);
    expect(lookup(lut, 128, 128, 128) & 0xf0).toBe(0);
  });

  test("PaletteTexture keeps its lookup texture in step with the palette", () => {
    const palettes = parsePalettes(readData("palette.dat"));
    const pt = new PaletteTexture();
    pt.set(palettes[0], -99, 0);
    const tex = pt.indexLut;
    expect(tex.image.data).toEqual(nearestIndexLut(palettes[0]));
    pt.set(palettes[5], -99, 0);
    expect(pt.indexLut).toBe(tex);
    expect(tex.image.data).toEqual(nearestIndexLut(palettes[5]));
  });
});

test("the HD terrain shader picks the index's bank from the lookup", () => {
  const pt = new PaletteTexture();
  const level = { levelFilter: { value: -99 }, levelBrightness: { value: 0 } };
  const m = terrainMaterial(pt, new THREE.Texture(), level, { kind: "ground", scale: 8 });
  const shader = {
    uniforms: {} as Record<string, { value: unknown }>,
    vertexShader: "#include <common>\n#include <begin_vertex>",
    fragmentShader: "#include <common>\n#include <color_fragment>\n#include <normal_fragment_maps>\n#include <opaque_fragment>",
  };
  m.onBeforeCompile(shader as never, {} as never);
  expect(shader.uniforms.paletteLut.value).toBe(pt.indexLut);
  expect(shader.fragmentShader).toMatch(/float bank = chroma < 0\.04 \? 0\.0 : nearBank;/);
  // Under JE_filterScreen the shade is the nearest index's value (D193); otherwise, and for a grey off bank 0, the brightness's.
  expect(shader.fragmentShader).toMatch(/float shade = levelFilter > -98\.5 && bank == nearBank \? nearest - nearBank : clamp\(floor\(lum \* 15\.0 \+ 0\.5\), 0\.0, 15\.0\);/);
  // The near-grey test is on the sRGB colour (dark saturated colours aren't grey).
  expect(shader.fragmentShader).toMatch(/vec3 srgb = terrainSrgb\(rgb\);\s+float chroma = max\(srgb\.r/);
});
