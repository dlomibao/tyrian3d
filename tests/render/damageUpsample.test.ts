// D128: a damaged frame's textures are its sprite pixels upsampled 4x, the cut by a Catmull-Rom cubic
// (it passes through every pixel, so a one-pixel hole stays a hole) and the paint by a slight blur,
// so bilinear filtering shows no pixel-sized steps.
import { describe, expect, test } from "vitest";
import { DAMAGE_UPSAMPLE, upsample, Upsample } from "../../src/render/damage/damageFrames";

const W = 12, H = 14;
const U = DAMAGE_UPSAMPLE;

/** A 12x14 RGBA field with channel 0 set to 1 at the given pixels. */
function field(pixels: [number, number][]): Float32Array {
  const f = new Float32Array(W * H * 4);
  for (const [x, y] of pixels) f[(y * W + x) * 4] = 1;
  return f;
}

/** Channel 0 of the upsampled texels, 0..1. */
function up(f: Float32Array, kind: Upsample): (X: number, Y: number) => number {
  const out = new Uint8Array(W * U * H * U * 4);
  upsample(f, W, H, out, [kind, kind, kind, kind]);
  return (X, Y) => out[(Y * W * U + X) * 4] / 255;
}

describe("damage texture upsampling", () => {
  test("a one-pixel cut stays cut at its centre (cubic) and fades out a pixel away", () => {
    const v = up(field([[5, 6]]), Upsample.Cubic);
    // The texels round pixel (5, 6)'s centre, which sits between texels 5U+1 and 5U+2.
    expect(v(5 * U + 1, 6 * U + 1)).toBeGreaterThan(0.5);
    expect(v(5 * U + 2, 6 * U + 2)).toBeGreaterThan(0.5);
    expect(v(7 * U + 1, 6 * U + 1)).toBeLessThan(0.05);
  });

  test("a straight edge has no steps: the 0.5 crossing is the same on every texel row", () => {
    const edge = field(Array.from({ length: H }, (_, y) => Array.from({ length: 6 }, (_, x) => [x, y] as [number, number])).flat());
    for (const kind of [Upsample.Cubic, Upsample.Blur]) {
      const v = up(edge, kind);
      const crossing = (Y: number) => {
        let X = 0;
        while (X < W * U && v(X, Y) >= 0.5) X++;
        return X;
      };
      const c0 = crossing(0);
      expect(c0).toBe(6 * U); // at the pixel boundary
      for (let Y = 1; Y < H * U; Y++) expect(crossing(Y)).toBe(c0);
    }
  });

  test("blurred paint changes smoothly: no jump between neighbouring texels over a quarter", () => {
    // A checkerboard: the worst case of a repainted sprite's pixel noise.
    const checker = field(Array.from({ length: W * H }, (_, i) => [i % W, Math.floor(i / W)] as [number, number]).filter(([x, y]) => (x + y) % 2 === 0));
    const v = up(checker, Upsample.Blur);
    let jump = 0;
    for (let Y = 0; Y < H * U; Y++) for (let X = 1; X < W * U; X++) jump = Math.max(jump, Math.abs(v(X, Y) - v(X - 1, Y)));
    expect(jump).toBeLessThan(0.25);
  });
});
