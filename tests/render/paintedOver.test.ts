// D183: a sprite every one of whose seen opaque pixels later opaque sprites overwrite left nothing in
// the original's frame, so the renderer leaves it out.
import { describe, expect, test } from "vitest";
import { PaintedOver } from "../../src/render/paintedOver";
import { Pass, type Draw, type Sprite2Sheet, type SpriteDraw, type SpriteTable, type TableSpriteDraw } from "../../src/sim/draw";
import { hasData, readData } from "../data/dataDir";

/** A Sprite2 sheet with one 12x14 sprite: fully opaque, or with its left `hole` columns transparent. */
function sheet(hole = 0): Sprite2Sheet {
  const bytes: number[] = [2, 0]; // offset of sprite 1
  for (let r = 0; r < 14; r++) {
    bytes.push(hole | ((12 - hole) << 4)); // skip `hole`, then 12 - hole opaque pixels
    for (let c = hole; c < 12; c++) bytes.push(20);
    bytes.push(0); // next row
  }
  bytes.push(0x0f);
  return { id: `test${hole}`, data: Uint8Array.from(bytes) };
}

const SOLID = sheet();
const HOLED = sheet(6);

function sprite(x: number, y: number, o: Partial<SpriteDraw> = {}): SpriteDraw {
  return {
    kind: "sprite2", sheet: SOLID, index: 1, x, y, size: 1, pass: Pass.TopEnemies, key: -1, effect: "none", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false, ...o,
  };
}

function hidden(items: Draw[]): number[] {
  const p = new PaintedOver();
  p.update(items);
  return items.map((_, i) => i).filter((i) => p.hides(i));
}

describe("painted over (D183)", () => {
  test("a sprite under a later opaque sprite is left out; the later one, and one drawn after, stay", () => {
    expect(hidden([sprite(100, 50), sprite(100, 50)])).toEqual([0]);
    expect(hidden([sprite(100, 50), sprite(101, 50)])).toEqual([]); // its left column shows
    expect(hidden([sprite(100, 50)])).toEqual([]);
  });

  test("the union of later sprites covers it, across passes", () => {
    const under = sprite(100, 50, { pass: Pass.GroundEnemies });
    expect(hidden([under, sprite(94, 50), sprite(106, 50, { pass: Pass.SkyEnemies })])).toEqual([0]);
    expect(hidden([under, sprite(94, 50), sprite(106, 52)])).toEqual([]); // two rows of it show
  });

  test("only opaque pixels count, the earlier sprite's and the later one's", () => {
    // A sprite with its left half transparent hides only what is under its right half.
    expect(hidden([sprite(100, 50), sprite(100, 50, { sheet: HOLED })])).toEqual([]);
    expect(hidden([sprite(106, 50, { sheet: SOLID }), sprite(100, 50, { sheet: HOLED })])).toEqual([]); // 6 columns still out
    expect(hidden([sprite(100, 50, { sheet: HOLED }), sprite(100, 50, { sheet: HOLED })])).toEqual([0]);
  });

  test("translucent, shadow and effect-pass draws don't cover; a hit-flashed one does", () => {
    const under = sprite(100, 50);
    expect(hidden([under, sprite(100, 50, { effect: "blend" })])).toEqual([]);
    expect(hidden([under, sprite(100, 50, { effect: "darken" })])).toEqual([]);
    for (const pass of [Pass.PlayerShots, Pass.EnemyShots, Pass.Explosions, Pass.Effects]) expect(hidden([under, sprite(100, 50, { pass })])).toEqual([]);
    expect(hidden([under, sprite(100, 50, { effect: "filter", filter: 0x40 })])).toEqual([0]);
    // A shadow is never left out; a translucent sprite is.
    expect(hidden([sprite(100, 50, { effect: "darken" }), sprite(100, 50)])).toEqual([]);
    expect(hidden([sprite(100, 50, { effect: "blend" }), sprite(100, 50)])).toEqual([0]);
  });

  test("a grouped object goes only when none of its tiles shows", () => {
    const tile = (x: number, first: boolean) => sprite(x, 50, { groupIndex: 7, groupSize: 2, groupFirst: first });
    expect(hidden([tile(100, true), tile(112, false), sprite(100, 50), sprite(112, 50)])).toEqual([0, 1]);
    // One tile covered and one showing: the model stays (it can't show half of itself).
    expect(hidden([tile(100, true), tile(112, false), sprite(100, 50)])).toEqual([]);
    expect(hidden([tile(100, true), tile(112, false), sprite(112, 50)])).toEqual([]);
    // The next object's tiles are its own.
    expect(hidden([tile(100, true), tile(112, false), tile(140, true), sprite(100, 50), sprite(112, 50)])).toEqual([0, 1]);
  });

  test("only the seen playfield counts; a sprite with nothing in it isn't left out", () => {
    // The playfield starts at screen x 24: a sprite at x 16 shows its columns 8-11 there.
    expect(hidden([sprite(16, 50), sprite(24, 50)])).toEqual([0]);
    expect(hidden([sprite(16, 50), sprite(16, 50)])).toEqual([0]);
    expect(hidden([sprite(0, 50), sprite(0, 50)])).toEqual([]); // wholly left of the playfield
    expect(hidden([sprite(100, -20), sprite(100, -20)])).toEqual([]); // above it
  });

  test("table sprites (the older format) are tested and cover too", () => {
    // 4x2, all opaque (a row wraps at the width).
    const table: SpriteTable = { id: "t", sprites: [{ width: 4, height: 2, data: Uint8Array.from([5, 5, 5, 5, 5, 5, 5, 5]) }] };
    const t = (x: number): TableSpriteDraw => ({ kind: "sprite", table, index: 0, x, y: 50, pass: Pass.Player, key: -1, effect: "none", filter: 0, value: 0 });
    expect(hidden([t(102), sprite(100, 50)])).toEqual([0]);
    expect(hidden([sprite(100, 50), t(102)])).toEqual([]);
  });

  test("a new draw list starts over", () => {
    const p = new PaintedOver();
    p.update([sprite(100, 50), sprite(100, 50)]);
    expect(p.hides(0)).toBe(true);
    p.update([sprite(100, 50)]);
    expect(p.hides(0)).toBe(false);
    expect(p.hides(1)).toBe(false);
  });
});

describe.skipIf(!hasData("newshh.shp"))("painted over: GYGES t2550 (QA M1)", () => {
  test("the green orb newshh-91 under the drill column's tiles is left out; the orbs beside it stay", () => {
    const sheetH: Sprite2Sheet = { id: "newshh.shp", data: readData("newshh.shp") };
    // The draw list's enemies in its order (normal difficulty, seed 1): object (top-left tile), x, y.
    const objects: [number, number, number][] = [
      [91, 168, 50], [127, 201, 52], [115, 200, 107], [77, 200, 79], [125, 183, 70],
      [123, 159, 70], [87, 183, 49], [85, 159, 49], [79, 171, 28], [89, 185, 40],
    ];
    const items: SpriteDraw[] = [];
    for (const [g, x, y] of objects) {
      [0, 1, 19, 20].forEach((di, k) => items.push(sprite(x + (k % 2) * 12, y + (k >> 1) * 14, {
        sheet: sheetH, index: g + di, pass: Pass.TopEnemies, groupIndex: g, groupSize: 2, groupFirst: k === 0,
      })));
    }
    expect(hidden(items)).toEqual([0, 1, 2, 3]);
  });
});
