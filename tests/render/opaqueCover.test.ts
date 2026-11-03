// D67: a ground structure (a wreck) is left out while opaque enemy sprites drawn as models cover
// its whole pattern, as the original's sprites hid its tiles.
import { describe, expect, test } from "vitest";
import { OpaqueCover, paintOutWreck } from "../../src/render/remaster/opaqueCover";

/** A Sprite2 sheet with one 12x14 sprite: fully opaque, or with its left `hole` columns transparent. */
function sheet(hole = 0): { id: string; data: Uint8Array } {
  const bytes: number[] = [2, 0]; // offset of sprite 1
  for (let r = 0; r < 14; r++) {
    bytes.push(hole | ((12 - hole) << 4)); // skip `hole`, then 12 - hole opaque pixels
    for (let c = hole; c < 12; c++) bytes.push(20);
    bytes.push(0); // next row
  }
  bytes.push(0x0f);
  return { id: `test${hole}`, data: Uint8Array.from(bytes) };
}

describe("opaque cover", () => {
  test("a rectangle under opaque sprites is covered; one reaching past them, or nothing drawn, isn't", () => {
    const c = new OpaqueCover();
    const s = sheet();
    c.begin();
    expect(c.covered(0, 0, 24, 28)).toBe(false);
    for (const [x, y] of [[0, 0], [12, 0], [0, 14], [12, 14]]) c.add(s, 1, 1, 100 + x, 50 + y);
    expect(c.covered(100, 50, 24, 28)).toBe(true);
    expect(c.covered(100.5, 50.5, 24, 28)).toBe(true); // a fraction off still fits the inset
    expect(c.covered(110, 50, 24, 28)).toBe(false);
    c.begin();
    expect(c.covered(100, 50, 24, 28)).toBe(false);
  });

  test("transparent sprite pixels don't cover", () => {
    const c = new OpaqueCover();
    c.begin();
    c.add(sheet(6), 1, 1, 0, 0);
    expect(c.covered(0, 0, 12, 14)).toBe(false);
    expect(c.covered(6, 0, 6, 14)).toBe(true);
  });
});

describe("paint out a wreck", () => {
  test("pixels that aren't dirt (16-21) take their nearest dirt pixel's index; dirt stays", () => {
    // 4x3: a wreck (index 5) in the middle of dirt
    const tile = Uint8Array.from([16, 17, 18, 19, 20, 5, 5, 21, 16, 16, 17, 18]);
    expect([...paintOutWreck(tile, 4, 3)]).toEqual([16, 17, 18, 19, 20, 17, 18, 21, 16, 16, 17, 18]);
    expect([...paintOutWreck(Uint8Array.from([1, 2]), 2, 1)]).toEqual([1, 2]); // no dirt: as it was
  });
});

describe("covered paintings (D67)", () => {
  test("every tile of a wreck pattern (a ground structure that keeps its tiles) has a covered HD painting", async () => {
    const { readFileSync, readdirSync } = await import("node:fs");
    const { join } = await import("node:path");
    const root = join(__dirname, "../..");
    const manifest = JSON.parse(readFileSync(join(root, "public/art/terrain/shapesz/manifest.json"), "utf8"));
    const covered = new Set(Object.keys(manifest.layers["0"].covered ?? {}).map(Number));
    const dir = join(root, "src/render/tileModels");
    const wrecks = readdirSync(dir)
      .filter((f) => f.startsWith("shapesz-"))
      .map((f) => JSON.parse(readFileSync(join(dir, f), "utf8")))
      .filter((e) => e.layer === 0 && e.keepTiles === true);
    expect(wrecks.length).toBeGreaterThanOrEqual(4); // bunker ring, hull, wreck, wreck-cut
    const missing = wrecks.flatMap((e) => (e.tiles as number[][]).flat().filter((n) => n >= 0 && !covered.has(n)));
    expect(missing).toEqual([]);
  });
});
