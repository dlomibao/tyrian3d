import { describe, expect, test } from "vitest";
import type { DecodedSprite } from "../../src/data/sprites";
import {
  composeSprite2x2,
  edgeDistances,
  extrudeSprite,
  SPRITE_EXTRUDE,
  SpriteMeshCache,
  TILE_EXTRUDE,
  tileToSprite,
  type ExtrudeOptions,
} from "../../src/render/spriteMesh";

const OPTS: ExtrudeOptions = { maxHeight: 6, edgeHeight: 2, radius: 1, bottom: 1 };

/** A sprite from rows of palette indices; -1 is transparent. */
function sprite(rows: number[][]): DecodedSprite {
  const width = rows[0].length;
  return { width, height: rows.length, pixels: Int16Array.from(rows.flat()) };
}

/** Every triangle's winding agrees with its vertices' normals (faces point outward). */
function windingMatchesNormals(data: NonNullable<ReturnType<typeof extrudeSprite>>): boolean {
  const p = data.positions;
  const n = data.normals;
  for (let t = 0; t < data.indices.length; t += 3) {
    const [a, b, c] = [data.indices[t], data.indices[t + 1], data.indices[t + 2]];
    const ux = p[b * 3] - p[a * 3], uy = p[b * 3 + 1] - p[a * 3 + 1], uz = p[b * 3 + 2] - p[a * 3 + 2];
    const vx = p[c * 3] - p[a * 3], vy = p[c * 3 + 1] - p[a * 3 + 1], vz = p[c * 3 + 2] - p[a * 3 + 2];
    const gx = uy * vz - uz * vy, gy = uz * vx - ux * vz, gz = ux * vy - uy * vx;
    if (gx * n[a * 3] + gy * n[a * 3 + 1] + gz * n[a * 3 + 2] <= 0) return false;
  }
  return true;
}

describe("extrudeSprite", () => {
  test("a 3x3 block: one top quad per pixel, an underside per row, walls around the rim", () => {
    const data = extrudeSprite(sprite([[1, 2, 3], [4, 5, 6], [7, 8, 9]]), OPTS)!;
    // 9 top quads + 3 underside runs + 12 wall quads, 4 vertices each.
    expect(data.positions.length / 3).toBe((9 + 3 + 12) * 4);
    expect(data.indices.length / 3).toBe((9 + 3 + 12) * 2);
    expect(windingMatchesNormals(data)).toBe(true);
  });

  test("heights rise from the edge to the middle", () => {
    const data = extrudeSprite(sprite([[1, 1, 1], [1, 1, 1], [1, 1, 1]]), OPTS)!;
    const h = data.heights;
    expect(h[0]).toBeCloseTo(OPTS.edgeHeight);
    expect(h[4]).toBeCloseTo(OPTS.maxHeight);
    expect(h[1]).toBeCloseTo(h[3]);
    // The top surface reaches the centre height and the underside sits at -bottom.
    const ys = Array.from({ length: data.positions.length / 3 }, (_, i) => data.positions[i * 3 + 1]);
    expect(Math.max(...ys)).toBeLessThanOrEqual(OPTS.maxHeight);
    expect(Math.min(...ys)).toBe(-OPTS.bottom);
  });

  test("vertices carry their pixel's palette index; transparent pixels make nothing", () => {
    const data = extrudeSprite(sprite([[-1, 7, -1], [9, -1, -1]]), OPTS)!;
    expect(new Set(data.palIndex)).toEqual(new Set([7, 9]));
    // Two isolated pixels: top, underside and 4 walls each.
    expect(data.positions.length / 3).toBe(2 * 6 * 4);
    expect(data.heights[0]).toBe(0);
    expect(windingMatchesNormals(data)).toBe(true);
  });

  test("an empty sprite has no mesh", () => {
    expect(extrudeSprite(sprite([[-1, -1], [-1, -1]]), OPTS)).toBeNull();
  });

  test("open borders: tiles stay full height up to their edges", () => {
    const solid = tileToSprite(new Uint8Array(24 * 28).fill(5), false);
    expect(edgeDistances(solid, true)[0]).toBe(Infinity);
    const data = extrudeSprite(solid, TILE_EXTRUDE)!;
    expect(data.heights[0]).toBeCloseTo(TILE_EXTRUDE.maxHeight);
    // Closed borders round the corner pixel down to the rim height.
    expect(extrudeSprite(solid, { ...TILE_EXTRUDE, openBorders: false })!.heights[0]).toBeCloseTo(TILE_EXTRUDE.edgeHeight);
  });

  test("real sprite sizes stay within 16-bit indices", () => {
    const data = extrudeSprite(tileToSprite(new Uint8Array(24 * 28).fill(3), true), SPRITE_EXTRUDE)!;
    expect(data.indices).toBeInstanceOf(Uint16Array);
  });
});

/** A Sprite2 sheet whose sprite i (1-based) is one pixel of colour i at (0, 0). */
function onePixelSheet(count: number): Uint8Array {
  const header = count * 2;
  const bytes = new Uint8Array(header + count * 3);
  for (let i = 0; i < count; i++) {
    const at = header + i * 3;
    bytes[i * 2] = at & 0xff;
    bytes[i * 2 + 1] = at >> 8;
    bytes.set([0x10, i + 1, 0x0f], at); // 1 opaque pixel, end
  }
  return bytes;
}

describe("composeSprite2x2", () => {
  test("places index, +1, +19 and +20 like blit_sprite2x2", () => {
    const s = composeSprite2x2(onePixelSheet(30), 5);
    expect(s.width).toBe(24);
    expect(s.height).toBe(28);
    const at = (x: number, y: number) => s.pixels[y * 24 + x];
    expect([at(0, 0), at(12, 0), at(0, 14), at(12, 14)]).toEqual([5, 6, 24, 25]);
    expect(s.pixels.filter((p) => p >= 0)).toHaveLength(4);
  });
});

describe("SpriteMeshCache", () => {
  test("builds each sprite once and returns null for empty ones", () => {
    const cache = new SpriteMeshCache();
    const sheet = { id: "test.shp", data: onePixelSheet(30) };
    const a = cache.sprite2Geometry(sheet, 3, 1);
    expect(a).not.toBeNull();
    expect(cache.sprite2Geometry(sheet, 3, 1)).toBe(a);
    expect(cache.sprite2Geometry(sheet, 3, 2)).not.toBe(a);
    // A second sheet object with the same id shares the geometry.
    expect(cache.sprite2Geometry({ id: "test.shp", data: sheet.data }, 3, 1)).toBe(a);
    expect(cache.sprite2Geometry(sheet, 99, 1)).toBeNull();
    expect(a!.getAttribute("palIndex").getX(0)).toBe(3);
  });
});
