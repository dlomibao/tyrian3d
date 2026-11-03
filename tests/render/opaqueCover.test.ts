// D67: a ground structure (a wreck) is left out while opaque ground-enemy sprites drawn as models
// cover the part of its pattern inside the playfield, as the original's sprites hid its tiles.
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

  test("only the part inside the playfield has to be covered (the sim draws no sprites above it)", () => {
    // The rock outcrop scrolling in (tick 1336): its crater's pattern (72x56) starts 37 px above the
    // playfield's top edge, and only its bottom rocks, which reach above the edge, are drawn yet.
    const c = new OpaqueCover();
    const s = sheet();
    c.begin();
    for (let col = 0; col < 6; col++) for (const y of [-8, 6]) c.add(s, 1, 1, 212 + col * 12, y);
    expect(c.covered(212, -37, 72, 56)).toBe(true);
    expect(c.covered(212, -37, 72, 60)).toBe(false); // reaches past the rocks inside the playfield
    // a sliver of a pattern inside the top edge, narrower than the inset, is sampled down its middle
    expect(c.covered(212, -55, 72, 56)).toBe(true);
    expect(c.covered(140, -55, 72, 56)).toBe(false);
    // a pattern wholly outside the playfield isn't covered (nothing there is known)
    c.add(s, 1, 1, 212, -40);
    expect(c.covered(212, -40, 12, 14)).toBe(false);
    // custom seen area: the left edge clips the same way
    const d = new OpaqueCover({ x0: 24, y0: 0, x1: 288, y1: 184 });
    d.begin();
    d.add(s, 1, 1, 24, 50);
    expect(d.covered(0, 50, 36, 14)).toBe(true);
    expect(d.covered(0, 50, 40, 14)).toBe(false);
  });

  test("transparent sprite pixels don't cover", () => {
    const c = new OpaqueCover();
    c.begin();
    c.add(sheet(6), 1, 1, 100, 50);
    expect(c.covered(100, 50, 12, 14)).toBe(false);
    expect(c.covered(106, 50, 6, 14)).toBe(true);
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
