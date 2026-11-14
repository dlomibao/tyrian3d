// D204: the shade under the C's blends is the terrain's own palette shade (underShade.ts), not a guess
// from the lit frame's nearest palette colour, which hopped between ramps on SAVARA Y's painted sea
// and drew its gradients through the cloud as contour lines (E3 QA L5, D203). The shaders need WebGL;
// here: which draws give their shade, what the pass draws and restores, and the wiring to the blends.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DrawListRenderer, underShadeFromSearch } from "../../src/render/drawListRenderer";
import { HUE_BLEND_PARS, NdcRect, SECOND_BANK_SHARE, topBanks, UnderGrab, UnderGrabHook } from "../../src/render/hueBlend";
import { groundTileMaterial } from "../../src/render/paletteMaterial";
import { PaletteTexture } from "../../src/render/paletteTexture";
import { remasterGroundMaterial } from "../../src/render/remaster/groundMaterial";
import { RemasterGroundAtlas } from "../../src/render/remaster/groundAtlas";
import { terrainMaterial } from "../../src/render/remaster/terrainMaterial";
import { TileAtlas } from "../../src/render/tileAtlas";
import { rockMaterial } from "../../src/render/rockMaterial";
import { SHEET_MARK_MAX_HEIGHT, UnderShadePass, type ShadeOut } from "../../src/render/underShade";
import { passHeight } from "../../src/render/passHeights";
import { Pass, type DrawList, type SpriteDraw, type Sprite2Sheet } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";
import { parseSpriteArtManifest, SpriteArt } from "../../src/render/spriteArt";

vi.stubGlobal("location", { search: "" });

/** What a render drew: each object the camera saw, with the material it was drawn in. */
type Drawn = { object: THREE.Object3D; material: THREE.Material }[];

/** A stand-in renderer that records what each render(scene, camera) would draw. */
function fakeRenderer(size = [640, 360]) {
  const renders: { target: THREE.WebGLRenderTarget | null; autoClear: boolean; drawn: Drawn }[] = [];
  let target: THREE.WebGLRenderTarget | null = null;
  const clear = { color: new THREE.Color(0x123456), alpha: 1 };
  const r = {
    autoClear: true,
    shadowMap: { autoUpdate: true },
    getRenderTarget: () => target,
    setRenderTarget: (t: THREE.WebGLRenderTarget | null) => (target = t),
    getDrawingBufferSize: (v: THREE.Vector2) => v.set(size[0], size[1]),
    getClearColor: (c: THREE.Color) => c.copy(clear.color),
    getClearAlpha: () => clear.alpha,
    setClearColor: (c: THREE.ColorRepresentation, a = 1) => {
      clear.color.set(c);
      clear.alpha = a;
    },
    render(scene: THREE.Scene, camera: THREE.Camera) {
      const drawn: Drawn = [];
      scene.traverseVisible((o) => {
        const m = o as THREE.Mesh;
        if (!m.isMesh || !o.layers.test(camera.layers)) return;
        drawn.push({ object: o, material: scene.overrideMaterial ?? (m.material as THREE.Material) });
      });
      renders.push({ target, autoClear: this.autoClear, drawn });
    },
  };
  return { renderer: r as unknown as THREE.WebGLRenderer, renders, clear, raw: r };
}

const mesh = (material: THREE.Material, name: string) => {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(), material);
  m.name = name;
  return m;
};

function scene() {
  const s = new THREE.Scene();
  const ground = mesh(groundTileMaterial(new PaletteTexture(), new TileAtlas()), "ground");
  const model = mesh(new THREE.MeshStandardMaterial(), "model");
  const shadow = mesh(new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false }), "shadow");
  // A transparent model part with an opaque child: leaving the part out must not hide the child.
  const child = mesh(new THREE.MeshStandardMaterial(), "child");
  shadow.add(child);
  const sheet = mesh(groundTileMaterial(new PaletteTexture(), new TileAtlas(), new UnderGrab(new THREE.Texture())), "sheet");
  const cover = mesh(new THREE.MeshBasicMaterial({ transparent: true, colorWrite: false, depthWrite: true }), "cover");
  const pal = mesh(new THREE.MeshStandardMaterial({ name: "pal_117" }), "pal");
  const rockSource = new THREE.MeshStandardMaterial({ name: "rock", map: new THREE.Texture() });
  rockSource.userData.tyrian_rock_ramps = [0, 9];
  const rock = mesh(rockMaterial(rockSource, new PaletteTexture()), "rock");
  s.add(ground, model, shadow, sheet, cover, pal, rock);
  return { scene: s, ground, model, shadow, child, sheet, cover, pal, rock };
}


describe("the terrain's own shade under the blends (D204)", () => {
  test("an HD tile's shade is read along its original tile's two main banks", () => {
    // All sea (bank 3): one bank.
    expect(topBanks([0x31, 0x33, 0x34, 0x32], true)).toEqual([0x30, 0x30]);
    // A shore: sand (bank 0xa) and sea.
    expect(topBanks([0xa5, 0xa6, 0xa7, 0x33, 0x34, 0, 0], true)).toEqual([0xa0, 0x30]);
    // A stray pixel of another bank under SECOND_BANK_SHARE doesn't count.
    const sea = [...Array(99).fill(0x33), 0x05];
    expect(1 / sea.length).toBeLessThan(SECOND_BANK_SHARE);
    expect(topBanks(sea, true)).toEqual([0x30, 0x30]);
    // Index 0 is skipped for the count when asked (see-through), counted (bank 0) when not.
    expect(topBanks([0, 0, 0, 0x33], true)).toEqual([0x30, 0x30]);
    expect(topBanks([0, 0, 0, 0x33], false)).toEqual([0x00, 0x30]);
  });

  test("the ground materials say how they draw their shade; the blend sheets don't", { timeout: 60000 }, () => {
    const pt = new PaletteTexture();
    const atlas = new TileAtlas();
    const under = new UnderGrab(new THREE.Texture());
    const classic = groundTileMaterial(pt, atlas).userData.shadeOut as Extract<ShadeOut, { kind: "tileIndex" }>;
    expect(classic.kind).toBe("tileIndex");
    expect(classic.uniforms.atlasMap.value).toBe(atlas.texture);
    expect(groundTileMaterial(pt, atlas, under).userData.shadeOut).toBeUndefined();
    const rAtlas = new RemasterGroundAtlas();
    const mmpx = remasterGroundMaterial(pt, rAtlas);
    expect((mmpx.userData.shadeOut as ShadeOut).kind).toBe("remasterIndex");
    // Shared with the colour material, so the atlas and sharpness it reads are the same.
    expect((mmpx.userData.shadeOut as ShadeOut).uniforms).toMatchObject({ atlasMap: mmpx.userData.remasterUniforms.atlasMap, sharpness: mmpx.userData.remasterUniforms.sharpness });
    expect(remasterGroundMaterial(pt, rAtlas, undefined, under).userData.shadeOut).toBeUndefined();
    const level = { levelFilter: { value: -99 }, levelBrightness: { value: 0 } };
    const tex = new THREE.Texture();
    expect(terrainMaterial(pt, tex, level, { kind: "ground", scale: 8 }).userData.shadeOut).toMatchObject({ kind: "terrainHd", cutout: false });
    expect(terrainMaterial(pt, tex, level, { kind: "cutout", scale: 8 }).userData.shadeOut).toMatchObject({ kind: "terrainHd", cutout: true });
    expect(terrainMaterial(pt, tex, level, { kind: "blend", scale: 8, under }).userData.shadeOut).toBeUndefined();
  });

  test("an HD blend sheet keeps its tile's main bank from the pair", () => {
    const m = terrainMaterial(new PaletteTexture(), new THREE.Texture(), { levelFilter: { value: -99 }, levelBrightness: { value: 0 } }, { kind: "blend", scale: 8, under: new UnderGrab(new THREE.Texture()) });
    const shader = {
      uniforms: {} as Record<string, unknown>,
      vertexShader: "#include <common>\n#include <begin_vertex>",
      fragmentShader: "#include <common>\n#include <color_fragment>\n#include <normal_fragment_maps>\n#include <opaque_fragment>",
    };
    m.onBeforeCompile(shader as never, {} as never);
    expect(shader.vertexShader).toMatch(/attribute vec2 instBank;/);
    expect(shader.vertexShader).toMatch(/vBank = instBank\.x;/);
  });

  test("the blends read the terrain's shade where it is known, and the lit copy's guess elsewhere", () => {
    expect(HUE_BLEND_PARS).toMatch(/if \(blendShadeOn > 0\.5\) \{\s+vec4 own = texelFetch\(blendShade, ivec2\(gl_FragCoord\.xy\), 0\);\s+if \(own\.g > 0\.5 && \(own\.b < 0\.5 \|\| blendShadeSheets > 0\.5\)\) return own\.r \* 15\.0;/);
    // The guess is still there after it.
    expect(HUE_BLEND_PARS.indexOf("texture2D(blendUnder")).toBeGreaterThan(HUE_BLEND_PARS.indexOf("blendShadeOn > 0.5"));
  });

  test("the pass: the ground's shades, the models' own, unknown elsewhere, the lower sheets' marks; all restored", () => {
    const { scene: s, ground, model, shadow, child, sheet, cover, pal, rock } = scene();
    const camera = new THREE.PerspectiveCamera();
    camera.layers.enable(1);
    const layersBefore = camera.layers.mask;
    const { renderer, renders, clear, raw } = fakeRenderer();
    const pass = new UnderShadePass(new PaletteTexture());
    const area = new NdcRect();
    expect(pass.render(renderer, s, camera, area)).toBe(false); // nothing blended in view
    expect(renders).toHaveLength(0);
    area.add(-0.5, -0.5);
    area.add(0.5, 0.25);
    expect(pass.render(renderer, s, camera, area)).toBe(true);
    expect(renders).toHaveLength(1);
    const [first] = renders;
    // Into the pass's own target, the size of the canvas, only over the blended area (+ margin), cleared.
    expect(first.target).toBe(pass.target);
    expect([pass.target.width, pass.target.height]).toEqual([640, 360]);
    expect(pass.target.scissorTest).toBe(true);
    expect(pass.target.scissor.toArray()).toEqual([160 - 8, 90 - 8, 320 + 16, 225 - 90 + 16]);
    expect(first.autoClear).toBe(true);
    // What writes depth and colour, each in its pass material; the translucent shadow and the
    // colourless cover are left out (the shadow's opaque child is not).
    const by = new Map(first.drawn.map((d) => [d.object.name, d.material]));
    expect([...by.keys()].sort()).toEqual(["child", "ground", "model", "pal", "rock", "sheet"]);
    expect(by.get("ground")!.name).toBe("under_shade");
    expect(by.get("model")!.name).toBe("under_shade_unknown");
    expect(by.get("child")).toBe(by.get("model"));
    expect(by.get("pal")!.name).toBe("under_shade_model");
    expect((by.get("pal")! as THREE.MeshBasicMaterial).customProgramCacheKey()).toBe("under-shade-model-5"); // pal_117: 117 & 15
    expect((by.get("rock")! as THREE.MeshBasicMaterial).map).toBe((rock.material as THREE.MeshStandardMaterial).map);
    const mark = by.get("sheet") as THREE.ShaderMaterial;
    expect(mark.name).toBe("under_shade_sheet");
    expect(mark.blending).toBe(THREE.CustomBlending); // added: the shade under it stays
    expect(mark.depthTest).toBe(false);
    expect(mark.fragmentShader).toContain(`if (vHeight > ${SHEET_MARK_MAX_HEIGHT.toFixed(3)}) discard;`);
    // Everything as it was: materials, layers, visibility, the renderer's state.
    expect(ground.material).toBeInstanceOf(THREE.MeshStandardMaterial);
    expect((sheet.material as THREE.Material).userData.maskCut).toBeDefined();
    expect((pal.material as THREE.Material).name).toBe("pal_117");
    for (const o of [ground, model, shadow, child, sheet, cover, pal, rock]) {
      expect(o.layers.mask).toBe(1);
      expect(o.visible).toBe(true);
    }
    expect(camera.layers.mask).toBe(layersBefore);
    expect(s.overrideMaterial).toBeNull();
    expect(raw.getRenderTarget()).toBeNull();
    expect(raw.autoClear).toBe(true);
    expect(raw.shadowMap.autoUpdate).toBe(true);
    expect([clear.color.getHex(), clear.alpha]).toEqual([0x123456, 1]);
    // The materials are made once per source material; a model that turns translucent drops out.
    (model.material as THREE.Material).transparent = true;
    pass.render(renderer, s, camera, area);
    const again = new Map(renders[1].drawn.map((d) => [d.object.name, d.material]));
    expect(again.get("ground")).toBe(by.get("ground"));
    expect(again.has("model")).toBe(false);
  });

  test("under a render target the pass matches its size", () => {
    const { scene: s } = scene();
    const { renderer, raw } = fakeRenderer();
    const rt = new THREE.WebGLRenderTarget(300, 200);
    raw.setRenderTarget(rt);
    const pass = new UnderShadePass(new PaletteTexture());
    const area = new NdcRect();
    area.add(-1, -1);
    area.add(1, 1);
    pass.render(renderer, s, new THREE.PerspectiveCamera(), area);
    expect([pass.target.width, pass.target.height]).toEqual([300, 200]);
    expect(raw.getRenderTarget()).toBe(rt);
  });

  test("background2over 2's sheets don't mark: no copy before them reads the mark", () => {
    expect(SHEET_MARK_MAX_HEIGHT).toBeLessThan(passHeight(Pass.Background2Top));
    expect(SHEET_MARK_MAX_HEIGHT).toBeGreaterThan(passHeight(Pass.Explosions));
  });

  test("only the sheets' copy is made before the sheets: later copies don't take the shade under a sheet", () => {
    const capture = vi.fn();
    const grab = { capture } as unknown as UnderGrab;
    const hooks = [new UnderGrabHook(grab, -1.25, false, true), new UnderGrabHook(grab, 0.1, true)];
    for (const h of hooks) {
      h.area.add(0, 0);
      h.arm();
      h.onBeforeRender({} as never, {} as never, {} as never, {} as never, {} as never, {} as never);
    }
    expect(capture.mock.calls.map((c) => c[2])).toEqual([true, false]);
  });

  test("the renderer draws the pass where a blended layer is, and tells the blends", () => {
    const fire: Sprite2Sheet = { id: "fire.shp", data: Uint8Array.from([2, 0, 0x30, 0x75, 0x75, 0x42, 0x0f]) };
    const draw: SpriteDraw = {
      kind: "sprite2", sheet: fire, index: 1, x: 100, y: 50, size: 1, pass: Pass.Explosions, key: 7, effect: "blend", filter: 0, value: 0,
      groupIndex: -1, groupSize: 1, groupDx: 0, groupDy: 0, groupFirst: false,
    };
    const art = new SpriteArt<THREE.Texture>(parseSpriteArtManifest({ scale: 8, sheets: { "fire.shp": { image: "f.webp", frames: { "1": { x: 0, y: 0, w: 96, h: 8 } } } } })!);
    art.sheet("fire.shp")!.setTexture(new THREE.Texture(), 128, 16);
    const r = new DrawListRenderer();
    r.setVfxMode("original");
    r.setSpriteArtMode("remastered");
    r.setPalettes([new Uint8Array(768) as unknown as Palette]);
    r.setSpriteArt(art);
    const camera = new THREE.PerspectiveCamera();
    camera.position.set(0, 30, 10);
    const u = (r as unknown as { under: UnderGrab }).under.uniforms;
    const s = new THREE.Scene();
    s.add(r.root);
    const { renderer } = fakeRenderer();
    const hooks = r as unknown as { grabExplosions: { area: NdcRect } };
    const frameOf = (items: SpriteDraw[]) => {
      const list: DrawList = { items, palette: 0, filter: -99, brightness: 0, screen: null };
      r.setDrawList(list);
      r.setDrawList(list);
      r.update(1, camera);
      u.blendShadeSheets.value = 0;
    };
    // A blended explosion: its grab area is the pass's (here moved on screen; the test camera's
    // projection puts it off screen, where the pass draws nothing).
    frameOf([draw]);
    expect(hooks.grabExplosions.area.empty).toBe(false);
    r.renderUnderShade(renderer, s, camera);
    expect(u.blendShadeOn.value).toBe(0);
    hooks.grabExplosions.area.add(0, 0);
    hooks.grabExplosions.area.add(0.2, 0.2);
    r.renderUnderShade(renderer, s, camera);
    expect(u.blendShadeOn.value).toBe(1);
    expect(u.blendShadeSheets.value).toBe(1); // until a later copy is made
    expect((u.blendShade.value as THREE.Texture).name).toBe("under-shade");
    // Nothing blended: no pass, the blends guess.
    frameOf([]);
    r.renderUnderShade(renderer, s, camera);
    expect(u.blendShadeOn.value).toBe(0);
  });

  test("the HD paintings' shades are read against the raw palette, before JE_filterScreen", () => {
    const pt = new PaletteTexture();
    const pal = new Uint8Array(768);
    for (let i = 0; i < 256; i++) pal.set([i & 63, (i >> 2) & 63, 63 - (i & 63)], i * 3);
    pt.set(pal as unknown as Palette, 8, 0); // CAMANIS's filter: every bank shows as bank 8's ramp
    // The screen's colours are filtered; the raw ones are the palette's own.
    expect(pt.color(0x31).getHex()).not.toBe(new THREE.Color().setRGB(pt.raw[0x31 * 4] / 255, pt.raw[0x31 * 4 + 1] / 255, pt.raw[0x31 * 4 + 2] / 255, THREE.SRGBColorSpace).getHex());
    expect(Array.from(pt.raw.subarray(0x31 * 4, 0x31 * 4 + 3))).toEqual([0x31 & 63, (0x31 >> 2) & 63, 63 - (0x31 & 63)].map((v) => (v << 2) | (v >> 4)));
  });

  test("?undershade=0 turns it off, for comparisons", () => {
    expect(underShadeFromSearch("")).toBe(true);
    expect(underShadeFromSearch("?debug=play&undershade=0")).toBe(false);
    expect(underShadeFromSearch(undefined)).toBe(true);
  });
});
