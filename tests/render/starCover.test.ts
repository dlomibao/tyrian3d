// D127: a star pixel shows only where background 1 left the screen black, as update_and_draw_starfield
// tests the screen in the C.
import { describe, expect, test } from "vitest";
import { Pass, type Draw } from "../../src/sim/draw";
import { StarCover } from "../../src/render/starCover";

/** A background-1 tile at (x, y) whose left half is ground (index 20) and right half black space. */
function halfTile(x: number, y: number): Draw {
  const tile = new Uint8Array(24 * 28);
  for (let r = 0; r < 28; r++) for (let c = 0; c < 12; c++) tile[r * 24 + c] = 20;
  return { kind: "tile", layer: 0, tile, tileId: "test:1", x, y, pass: Pass.Background1, key: 0, effect: "none" };
}

const star = (x: number, y: number): Draw => ({ kind: "pixel", x, y, color: 0x9f, pass: Pass.Starfield });

describe("star cover", () => {
  test("stars over ground are hidden, stars over black space and off the tiles show", () => {
    const items = [halfTile(100, 50), star(105, 60), star(115, 60)];
    const c = new StarCover();
    expect(c.hides(items, 105, 60)).toBe(true); // ground pixel
    expect(c.hides(items, 111, 77)).toBe(true); // the ground's last column and row
    expect(c.hides(items, 112, 60)).toBe(false); // black pixel of the same tile
    expect(c.hides(items, 99, 60)).toBe(false); // no tile there
    expect(c.hides(items, 105, 78)).toBe(false); // below the tile
    expect(c.hides(items, -1, 60)).toBe(false); // off screen
  });

  test("the cover follows each new draw list; layers 2 and 3 never hide stars", () => {
    const c = new StarCover();
    expect(c.hides([halfTile(0, 0)], 5, 5)).toBe(true);
    expect(c.hides([halfTile(30, 0)], 5, 5)).toBe(false);
    const upper: Draw = { ...halfTile(0, 0), layer: 1, pass: Pass.Background2Under } as Draw;
    expect(c.hides([upper], 5, 5)).toBe(false);
  });
});
