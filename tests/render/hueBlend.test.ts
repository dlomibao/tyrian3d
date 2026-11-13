// D174: the C's blends (blit_sprite2_blend, draw_background_2_blend) keep the sprite's palette bank and
// average the shades. The shader half needs WebGL; here: the bank choice, and which draws take the blend.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { dominantBank, NdcRect, paletteLums, rampShade, UNDER_GRAB_ORDER } from "../../src/render/hueBlend";
import { ART_HUE_BLEND } from "../../src/render/spriteArtLayer";
import { parseSpriteArtManifest, SpriteArt } from "../../src/render/spriteArt";
import { OUTLINE_ORDER } from "../../src/render/outlineHook";
import { blendSheetOrder } from "../../src/render/drawListRenderer";
import { beginDrawList, blit_sprite2, blit_sprite2_hud, drawList, isHudDraw, Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
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

type Peek = { peek(s: unknown, p: number): { geometry: THREE.InstancedBufferGeometry; mesh: THREE.Mesh<THREE.BufferGeometry, THREE.ShaderMaterial>; instance(i: number): { fx: number[] } } | undefined };

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
  const inner = r as unknown as {
    artLayer: Peek; grabExplosions: THREE.Object3D & { armed: boolean }; grabSheets: THREE.Object3D & { armed: boolean };
    grabTop: THREE.Object3D; under: { uniforms: Record<string, unknown> };
  };
  return {
    layer: inner.artLayer, sheet: art.sheet("fire.shp"), explosionsArmed: inner.grabExplosions.armed, sheetsArmed: inner.grabSheets.armed,
    hooks: [inner.grabSheets, inner.grabExplosions, inner.grabTop], under: inner.under,
  };
}

describe("hue-keeping blend (D174)", () => {
  test("a sprite's or tile's bank is the one most of its pixels are in", () => {
    expect(dominantBank([0x75, 0x76, 0x42, -1, -1], false)).toBe(0x70);
    // Tiles: index 0 is see-through, so it doesn't count.
    expect(dominantBank([0, 0, 0, 0x8f, 0x8e, 0x93], true)).toBe(0x80);
    expect(dominantBank([0, 0, 0x8f], false)).toBe(0x00);
  });

  test("by shade, bright pixels outweigh a dark backing (the score numbers, D181)", () => {
    // newsh6.shp frame 204 ("50"): digits in bank 0x80 at shades 9-13, a box of 46 pixels of index 0x90.
    const fifty = [...Array(12).fill(137), ...Array(8).fill(139), ...Array(3).fill(140), ...Array(3).fill(141), ...Array(46).fill(144)];
    expect(dominantBank(fifty, false)).toBe(0x90);
    expect(dominantBank(fifty, false, true)).toBe(0x80);
    // A fireball stays in its fire ramp either way.
    expect(dominantBank([0x75, 0x76, 0x42, -1, -1], false, true)).toBe(0x70);
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

  test("the explosions read the live frame copy, palette and filters, in the main render only (D193)", () => {
    const f = frame([draw(fireSheet("fire.shp"))]);
    const mesh = f.layer.peek(f.sheet, Pass.Explosions)!.mesh;
    // The stencilled material is a clone: its uniforms must be the shared ones, not copies frozen
    // at creation (a blank 1x1 frame copy made every explosion blend as if over black).
    for (const k of ["blendUnder", "blendUnderSize", "blendUnderLinear", "blendUnderLut", "blendShadeLut"])
      expect(mesh.material.uniforms[k]).toBe(f.under.uniforms[k]);
    expect(mesh.material.stencilWrite).toBe(true);
    // The outline pass's own render of the scene leaves them out (outlineEffect.js).
    expect(mesh.userData.outlineSkip).toBe(true);
    // So do the explosions' and the top sheets' frame copies; the sheets' copy may be made there.
    expect(f.hooks.map((h) => h.userData.outlineSkip === true)).toEqual([false, true, true]);
  });

  test("a HUD indicator (the special's ready lamp) is left to the HTML HUD (D193)", () => {
    const sh = fireSheet("fire.shp");
    const f = frame([draw(sh, { pass: Pass.Player, effect: "none", hud: true }), draw(sh)]);
    expect(f.layer.peek(f.sheet, Pass.Player)?.geometry.instanceCount ?? 0).toBe(0);
    expect(f.layer.peek(f.sheet, Pass.Explosions)!.geometry.instanceCount).toBe(1);
  });

  test("JE_doSpecialShot's lamp is recorded as a HUD draw, other blits aren't", () => {
    const sh = fireSheet("tyrian.shp#9");
    beginDrawList();
    blit_sprite2_hud(47, 4, sh, 94);
    blit_sprite2(47, 4, sh, 94);
    expect(drawList.items.map(isHudDraw)).toEqual([true, false]);
    expect(drawList.items[0]).toMatchObject({ kind: "sprite2", x: 47, y: 4, index: 94, hud: true });
    beginDrawList();
  });

  test("a grab's screen area grows to cover its draws; areas far apart are not near", () => {
    const a = new NdcRect();
    expect(a.empty).toBe(true);
    a.add(-0.5, -0.5);
    a.add(-0.2, 0.1);
    expect([a.x0, a.y0, a.x1, a.y1]).toEqual([-0.5, -0.5, -0.2, 0.1]);
    const b = new NdcRect();
    b.add(0.5, 0.5);
    expect(a.near(b, 0.05)).toBe(false);
    expect(a.near(b, 0.8)).toBe(true); // 0.7 apart in x, 0.4 in y
    a.union(b);
    expect([a.x0, a.y0, a.x1, a.y1]).toEqual([-0.5, -0.5, 0.5, 0.5]);
    expect(new NdcRect().near(a, 1)).toBe(false);
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
