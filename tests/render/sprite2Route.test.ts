// How a grouped object with flat art is routed (src/render/sprite2Route.ts, D42, D244): by its first
// non-empty tile, so an asteroid assembly piece whose first tile is empty (newshd 7) is still drawn flat;
// and the preload's matching test (artListsSprite), which leaves such an object's model out.
import { describe, expect, test } from "vitest";
import { artListsSprite, Route, Sprite2Router } from "../../src/render/sprite2Route";
import type { SpriteDraw } from "../../src/sim/draw";

const sheet = { id: "newshd.shp" } as SpriteDraw["sheet"];
const draw = (index: number, groupIndex: number): SpriteDraw =>
  ({ kind: "sprite2", sheet, index, size: 1, groupIndex, groupSize: 2, groupDx: 0, groupDy: 0, groupFirst: index === groupIndex } as unknown as SpriteDraw);

/** Art for tiles 8, 26, 27 (an object at 7 whose first tile is empty), and a model for that object. */
const tiles = new Set([8, 26, 27]);
const art = { frame: (i: number) => (tiles.has(i) ? {} : undefined), listed: (i: number) => tiles.has(i) };
const router = () =>
  new Sprite2Router({ grouped: new Map([["newshd.shp|2|7", "enemies/newshd-7"]]), banked: [], groupRoll: new Map(), ungrouped: new Map() });

describe("Sprite2Router with flat art", () => {
  test("an object whose first tile is empty goes by its first non-empty tile: drawn flat, not as its model", () => {
    const r = router();
    const empty = (i: number) => i === 7;
    expect(r.route(draw(8, 7), art, empty).route).toBe(Route.Flat);
    expect(r.route(draw(26, 7), art, empty).route).toBe(Route.Flat);
    // the empty tile itself has no art: drawn as its (empty) sprite, which draws nothing
    expect(r.route(draw(7, 7), art, empty).route).toBe(Route.Sprite);
  });

  test("without art, or in the original look (art null), the object is its model", () => {
    const none = { frame: () => undefined, listed: () => false };
    expect(router().route(draw(8, 7), none, (i) => i === 7).route).toBe(Route.Group);
    expect(router().route(draw(8, 7), null, (i) => i === 7).route).toBe(Route.Group);
  });

  test("a non-empty first tile without art still decides (the model), as before", () => {
    expect(router().route(draw(8, 7), art, () => false).route).toBe(Route.Group);
  });

  test("artListsSprite: the preload leaves out an object any of whose tiles the manifest lists", () => {
    expect(artListsSprite(art, 2, 7, true)).toBe(true);
    expect(artListsSprite(art, 2, 1, true)).toBe(false);
    expect(artListsSprite(art, 1, 8, false)).toBe(true);
    expect(artListsSprite(art, 1, 7, false)).toBe(false);
    expect(artListsSprite(undefined, 2, 7, true)).toBe(false);
  });
});
