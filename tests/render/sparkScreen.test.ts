// Sparks (JE_drawSP superpixels) mix with the screen under them as in the C (DECISIONS.md D147):
// the draw list's spark facts (src/sim/varz.ts), the C's formula (sparkColor) and the screen read
// back from the draw list (src/render/sparkScreen.ts).
import { describe, expect, test } from "vitest";
import { SparkScreen } from "../../src/render/sparkScreen";
import { beginDrawList, drawList, Pass, sparkColor, type Draw, type PixelDraw, type SparkPixel } from "../../src/sim/draw";
import { g } from "../../src/sim/state";
import { JE_drawSP } from "../../src/sim/varz";

const tile = (fill: number, x = 0, y = 0, layer: 0 | 1 | 2 = 0, effect: "none" | "blend" = "none"): Draw => ({
  kind: "tile", layer, tile: new Uint8Array(24 * 28).fill(fill), tileId: `t${fill}`, x, y, pass: Pass.Background1, key: -1, effect,
});
const spark = (x: number, y: number, s: SparkPixel): PixelDraw => ({ kind: "pixel", x, y, color: sparkColor(s, 0), pass: Pass.Effects, spark: s });
const centre = (z: number, base = 0x90): SparkPixel => ({ base, z, centre: true, dx: 1, dy: 2 });

describe("sparks (D147)", () => {
  test("JE_drawSP records a plus of five spark pixels, the colour over black as before", () => {
    beginDrawList();
    for (const sp of g.superpixels) sp.z = 0;
    Object.assign(g.superpixels[0], { x: 100, y: 50, delta_x: 2, delta_y: -1, color: 0x90, z: 15 });
    JE_drawSP();
    const px = drawList.items.filter((d): d is PixelDraw => d.kind === "pixel");
    expect(px).toHaveLength(5);
    expect(px.map((d) => [d.x, d.y])).toEqual([[102, 49], [101, 49], [103, 49], [102, 48], [102, 50]]);
    expect(px[0].spark).toEqual({ base: 0x90, z: 15, centre: true, dx: 2, dy: -1 });
    expect(px[0].color).toBe(0x90 + 7);
    expect(px.slice(1).every((d) => d.spark?.centre === false && d.color === 0x90 + 3)).toBe(true);
    expect(g.superpixels[0].z).toBe(14);
  });

  test("the C's mix: (((screen & 0x0f) + add) >> 1) + base, add z at the centre and z >> 1 on the arms", () => {
    expect(sparkColor(centre(15), 0x2c)).toBe(0x90 + 13);
    expect(sparkColor({ ...centre(15), centre: false }, 0x2c)).toBe(0x90 + 9);
    expect(sparkColor(centre(1), 0x2c)).toBe(0x90 + 6);
    expect(sparkColor(centre(15), 0)).toBe(0x90 + 7);
  });

  test("a spark reads the screen the earlier draws left: bright over a bright ground, as before over black", () => {
    const screen = new SparkScreen();
    const items = [tile(0x2c), spark(5, 5, centre(15)), spark(40, 5, centre(15))];
    expect(screen.color(items, 1)).toBe(0x90 + 13);
    expect(screen.color(items, 2)).toBe(0x90 + 7); // off the tile: nothing under it
  });

  test("background 2's index 0 is see-through, a blended tile averages, a later spark reads an earlier one", () => {
    const screen = new SparkScreen();
    const items = [tile(0x2c), tile(0, 0, 0, 1), spark(5, 5, centre(15))];
    expect(screen.value(items, 2, 5, 5)).toBe(12);
    const blended = [tile(0x2c), tile(0x34, 0, 0, 1, "blend")];
    expect(screen.value(blended, 2, 5, 5)).toBe(8);
    const twice = [tile(0x2c), spark(5, 5, centre(15)), spark(5, 5, centre(15))];
    expect(screen.color(twice, 1)).toBe(0x9d);
    expect(screen.color(twice, 2)).toBe(0x90 + ((13 + 15) >> 1));
  });
});
