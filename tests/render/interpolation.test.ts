import { expect, test } from "vitest";
import { Pass, type Draw, type Sprite2Sheet } from "../../src/sim/draw";
import { DrawInterpolator } from "../../src/render/interpolation";
import { remapScreenIndex } from "../../src/render/paletteTexture";

const sheet: Sprite2Sheet = { id: "s", data: new Uint8Array(0) };
const spr = (key: number, x: number, y: number): Draw => ({
  kind: "sprite2", sheet, index: 1, x, y, size: 2, pass: Pass.SkyEnemies, key, effect: "none", filter: 0, value: 0,
  groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false,
});
const prev = (ip: DrawInterpolator, i: number) => [ip.prevX[i], ip.prevY[i]];

test("matches draws by key across ticks", () => {
  const ip = new DrawInterpolator();
  ip.push([spr(1, 10, 10), spr(2, 50, 50)]);
  ip.push([spr(2, 52, 49), spr(1, 13, 12), spr(3, 0, 0)]);
  expect(prev(ip, 0)).toEqual([50, 50]);
  expect(prev(ip, 1)).toEqual([10, 10]);
  // New draws start where they are.
  expect(prev(ip, 2)).toEqual([0, 0]);
});

test("draws sharing a key match in order of appearance", () => {
  const ip = new DrawInterpolator();
  ip.push([spr(7, 0, 0), spr(7, 12, 0), spr(7, 0, 14)]);
  ip.push([spr(7, 1, 1), spr(7, 13, 1), spr(7, 1, 15)]);
  expect([prev(ip, 0), prev(ip, 1), prev(ip, 2)]).toEqual([[0, 0], [12, 0], [0, 14]]);
});

test("key -1 never interpolates, and long moves snap", () => {
  const ip = new DrawInterpolator();
  ip.push([spr(-1, 0, 0), spr(4, 100, 100)]);
  ip.push([spr(-1, 5, 5), spr(4, 100, 141)]);
  expect(prev(ip, 0)).toEqual([5, 5]);
  expect(prev(ip, 1)).toEqual([100, 141]);
  ip.push([spr(-1, 5, 5), spr(4, 100, 181)]);
  expect(prev(ip, 1)).toEqual([100, 141]);
});

test("kinds don't match each other, and reset forgets the last tick", () => {
  const ip = new DrawInterpolator();
  const tile: Draw = { kind: "tile", layer: 0, tile: new Uint8Array(0), tileId: "t", x: 0, y: 0, pass: Pass.Background1, key: 4, effect: "none" };
  ip.push([tile]);
  ip.push([spr(4, 3, 3)]);
  expect(prev(ip, 0)).toEqual([3, 3]);
  ip.reset();
  ip.push([spr(4, 6, 6)]);
  expect(prev(ip, 0)).toEqual([6, 6]);
});

test("grows past its initial capacity", () => {
  const ip = new DrawInterpolator();
  const many = (dy: number) => Array.from({ length: 3000 }, (_, i) => spr(i, i % 300, dy));
  ip.push(many(0));
  ip.push(many(2));
  expect(prev(ip, 2999)).toEqual([2999 % 300, 0]);
});

test("JE_filterScreen remaps hue, then value with the C's saturation rules", () => {
  expect(remapScreenIndex(0x37, -99, 0)).toBe(0x37);
  expect(remapScreenIndex(0x37, 0x0c, 0)).toBe(0xc7);
  expect(remapScreenIndex(0x37, -99, 5)).toBe(0x3c);
  expect(remapScreenIndex(0x37, -99, 10)).toBe(0x3f); // 0x11: saturates to 0xF
  expect(remapScreenIndex(0x37, -99, -8)).toBe(0x30); // borrow: 0
  expect(remapScreenIndex(0x3f, -99, 0x10)).toBe(0x30); // 0x1F and up: 0
  expect(remapScreenIndex(0x37, -99, -99)).toBe(0x37);
});
