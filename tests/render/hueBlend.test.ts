// D168: the C's blends (blit_sprite2_blend, draw_background_2_blend) keep the sprite's palette bank and
// average the shades. The shader half needs WebGL; here: the bank choice, and which draws take the blend.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { dominantBank, paletteLums, rampShade, UNDER_GRAB_ORDER } from "../../src/render/hueBlend";
import { ART_HUE_BLEND } from "../../src/render/spriteArtLayer";
import { parseSpriteArtManifest, SpriteArt } from "../../src/render/spriteArt";
import { OUTLINE_ORDER } from "../../src/render/outlineHook";
import { blendSheetOrder } from "../../src/render/drawListRenderer";
import { Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";

vi.stubGlobal("location", { search: "" });

/** A one-sprite Sprite2 sheet: three opaque pixels, two of colour 0x75 (the fire ramp) and one 0x42. */
function fireSheet(id: string): Sprite2Sheet {
  return { id, data: Uint8Array.from([2, 0, 0x30, 0x75, 0x75, 0x42, 0x0f]) };
}

function draw(sh: Sprite2Sheet, over: Partial<SpriteDraw> = {}): SpriteDraw {
  return {
    kind: "sprite2", sheet: sh, index: 1, x: 100, y: 50, size: 1, pass: Pass.Explosions, key: 7, effect: "blend", filter: 0, value: 0,
    groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false, ...over,
  };
}

type Peek = { peek(s: unknown, p: number): { instance(i: number): { fx: number[] } } | undefined };

function frame(items: SpriteDraw[]) {
  const art = new SpriteArt<THREE.Texture>(parseSpriteArtManifest({ scale: 8, sheets: { "fire.shp": { image: "f.webp", frames: { "1": { x: 0, y: 0, w: 96, h: 8 } } } } })!);
  art.sheet("fire.shp")!.setTexture(new THREE.Texture(), 128, 16);
  const r = new DrawListRenderer();
  r.setVfxMode("original");
  r.setSpriteArtMode("remastered");
  r.setPalettes([new Uint8Array(768) as unknown as Palette]);
  r.setSpriteArt(art);
  const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
  r.setDrawList(list);
  r.setDrawList(list);
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 30, 10);
  r.update(1, camera);
  const inner = r as unknown as { artLayer: Peek; grabExplosions: { armed: boolean }; grabSheets: { armed: boolean } };
  return { layer: inner.artLayer, sheet: art.sheet("fire.shp"), explosionsArmed: inner.grabExplosions.armed, sheetsArmed: inner.grabSheets.armed };
}

describe("hue-keeping blend (D168)", () => {
  test("a sprite's or tile's bank is the one most of its pixels are in", () => {
    expect(dominantBank([0x75, 0x76, 0x42, -1, -1], false)).toBe(0x70);
    // Tiles: index 0 is see-through, so it doesn't count.
    expect(dominantBank([0, 0, 0, 0x8f, 0x8e, 0x93], true)).toBe(0x80);
    expect(dominantBank([0, 0, 0x8f], false)).toBe(0x00);
  });

  test("a brightness reads as a fractional shade along the bank's ramp", () => {
    // Bank 1 (entries 16-31): a grey ramp 0, 17, 34 .. 255; the rest black.
    const pal = new Uint8Array(256 * 4);
    for (let i = 0; i < 16; i++) pal.set([i * 17, i * 17, i * 17, 255], (16 + i) * 4);
    const lums = paletteLums(pal);
    expect(rampShade(lums, 16, lums[16 + 7])).toBeCloseTo(7, 5);
    expect(rampShade(lums, 16, (lums[16 + 7] + lums[16 + 8]) / 2)).toBeCloseTo(7.5, 5);
    expect(rampShade(lums, 16, 0)).toBe(0);
    expect(rampShade(lums, 16, 1)).toBe(15);
    // A bank that is all black: anything brighter is its top shade.
    expect(rampShade(lums, 32, 0.5)).toBe(15);
  });

  test("a blended explosion's flat art takes the blend in its sprite's bank, at its fade", () => {
    const sh = fireSheet("fire.shp");
    const f = frame([draw(sh)]);
    expect(f.layer.peek(f.sheet, Pass.Explosions)!.instance(0).fx).toEqual([ART_HUE_BLEND, 7, 0, 1]);
    expect(f.explosionsArmed).toBe(true);
    expect(f.sheetsArmed).toBe(false);
  });

  test("blended art outside the explosions, and unblended explosions, keep their opacity", () => {
    const sh = fireSheet("fire.shp");
    const f = frame([draw(sh, { pass: Pass.PlayerShots }), draw(sh, { effect: "none" })]);
    expect(f.layer.peek(f.sheet, Pass.PlayerShots)!.instance(0).fx).toEqual([0, 0, 0, Math.fround(0.55)]);
    expect(f.layer.peek(f.sheet, Pass.Explosions)!.instance(0).fx).toEqual([0, 0, 0, 1]);
    expect(f.explosionsArmed).toBe(false);
  });

  test("the grabs come after the outlines and just before the layers that read them", () => {
    expect(UNDER_GRAB_ORDER.sheets).toBeGreaterThan(OUTLINE_ORDER);
    expect(UNDER_GRAB_ORDER.sheets).toBeLessThan(blendSheetOrder(Pass.Background2Under));
    // The explosions' flat art and its stencil setter (spriteArtLayer.ts) start at -1 + pass / 100 - 0.001.
    expect(UNDER_GRAB_ORDER.explosions).toBeLessThan(-1 + Pass.Explosions / 100 - 0.001);
    expect(UNDER_GRAB_ORDER.explosions).toBeGreaterThan(-1 + Pass.SkyEnemiesOver / 100);
    expect(UNDER_GRAB_ORDER.top).toBeLessThan(blendSheetOrder(Pass.Background2Top));
  });
});
