// D252: JE_drawSP's sparks keep the C's plus, in the colour the C wrote, in the remastered effects too
// (with a soft glow of that colour). D253: a small fireball (explosion type 1) throws no flash, streaks
// or embers in the remastered effects; a large explosion's quarters still do.
import * as THREE from "three";
import { afterEach, describe, expect, test, vi } from "vitest";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { EXPLOSION_DATA, EXPLOSION_SHEET_ID } from "../../src/render/vfx/explosionFrames";
import { Pass, type Draw, type DrawList, type PixelDraw, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";

vi.stubGlobal("location", { search: "" });

afterEach(() => vi.restoreAllMocks());

function renderer(vfx: "original" | "remastered"): DrawListRenderer {
  const r = new DrawListRenderer();
  r.setVfxMode(vfx);
  r.setPalettes([new Uint8Array(768) as unknown as Palette]);
  return r;
}

function draw(r: DrawListRenderer, items: Draw[]): void {
  const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera);
}

/** A spark's plus: its centre and four arms (JE_drawSP), base 112 (TIME WAR's red), new (z 15). */
function plus(x: number, y: number): PixelDraw[] {
  return [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]].map(([dx, dy], i) => ({
    kind: "pixel", x: x + dx, y: y + dy, color: 112, pass: Pass.Effects,
    spark: { base: 112, z: 15, centre: i === 0, dx: 0, dy: 1 },
  }));
}

describe("sparks (D252)", () => {
  test("the remastered effects draw the C's five-pixel plus, as the original effects do", () => {
    const remastered = renderer("remastered");
    draw(remastered, plus(100, 80));
    const original = renderer("original");
    draw(original, plus(100, 80));
    expect(remastered.stats().instances).toBe(5);
    expect(original.stats().instances).toBe(5);
  });
});

/** An explosion sheet whose sprite `index` is a 3-pixel row in the fire ramp, the rest empty. */
function explosionSheet(index: number): Sprite2Sheet {
  const table = index * 2;
  const data = new Uint8Array(table + 6);
  for (let i = 0; i < index; i++) {
    data[i * 2] = table & 0xff;
    data[i * 2 + 1] = table >> 8;
  }
  data.set([0x30, 0x75, 0x77, 0x75, 0x00, 0x0f], table);
  return { id: EXPLOSION_SHEET_ID, data };
}

/** Particles a lone explosion of `type` spawns on its first frame. */
function spawned(type: number): number {
  vi.spyOn(Math, "random").mockReturnValue(0.99); // no chance debris or smoke
  const index = EXPLOSION_DATA[type][0] + 2;
  const d: SpriteDraw = {
    kind: "sprite2", sheet: explosionSheet(index), index, x: 100, y: 80, size: 1, pass: Pass.Explosions, key: 30001, effect: "none", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false,
  };
  const r = renderer("remastered");
  draw(r, [d]);
  draw(r, [d]);
  return (r as unknown as { fx: { stats(): { spawned: number } } }).fx.stats().spawned;
}

describe("small fireballs (D253)", () => {
  test("a small fireball throws nothing; a large explosion's quarter still throws its sparks", () => {
    expect(spawned(1)).toBe(0);
    expect(spawned(2)).toBeGreaterThan(0);
  });
});
