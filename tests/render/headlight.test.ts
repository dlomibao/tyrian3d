// D220: showHeadlight keeps each pixel's palette bank and quarters its shade within it,
// (p & 0xf0) | (((p & 0x0f) + light) >> 2) (backgrnd.c). The 3D had quartered the brightness, a
// ramp to black: TYRIAN hard's shaded ice drew at 0.17x of lit where the C's is about 0.6x, because
// the ice bank's low entries are still mid-blue. The shaders need WebGL; here: the shade rule, the
// colour rule as the shader works it out, and the frame's wiring (the effects over the frame, the
// shades and banks of the shade pass, the smoothies' hue).
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import {
  bankLumaAt,
  HEADLIGHT_FLOOR_LOSS,
  headlightShade,
  headlitInBank,
  ScreenFilterPass,
  ART_MARK,
  MODEL_MARK,
  TOP_MARK,
} from "../../src/render/screenFilters";
import { UnderShadePass, unpackShadeBanks } from "../../src/render/underShade";
import { NdcRect, UnderGrab } from "../../src/render/hueBlend";
import { PaletteTexture } from "../../src/render/paletteTexture";
import { ScreenHue } from "../../src/render/screenHue";
import { groundTileMaterial } from "../../src/render/paletteMaterial";
import { TileAtlas } from "../../src/render/tileAtlas";
import { Pass, type DrawList } from "../../src/sim/draw";
import type { ScreenFilterStage } from "../../src/sim/smoothies";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import type { Palette } from "../../src/data/palette";
import { SHOT_ART_LAYER, VFX_LAYER } from "../../src/render/vfx/vfxMode";

vi.stubGlobal("location", { search: "" });

// TYRIAN's palette, bank 8 (the ice): its low entries are mid-blue, not black.
const ICE_SRGB = [
  [36, 85, 109], [44, 93, 117], [56, 105, 125], [65, 117, 138], [77, 130, 146], [85, 142, 158], [97, 154, 166], [109, 166, 178],
  [125, 178, 186], [138, 190, 199], [154, 203, 207], [166, 211, 215], [186, 223, 227], [203, 235, 235], [219, 247, 247], [239, 255, 255],
];
const toLinear = (v: number) => ((v /= 255) <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));
const toSrgb = (v: number) => 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
const ice = ICE_SRGB.map((c) => c.map(toLinear) as [number, number, number]);
const luma = (c: readonly number[]) => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];

describe("showHeadlight's shade (D220)", () => {
  test("a whole shade takes the C's (shade + light) >> 2", () => {
    for (let s = 0; s < 16; s++) {
      expect(headlightShade(s, 0)).toBe(s >> 2);
      for (const light of [3, 9, 18]) expect(headlightShade(s, light)).toBe((s + light) >> 2);
    }
  });

  test("a painting's fractional shade goes smoothly, at the floor's mean loss", () => {
    expect(headlightShade(10.5, 0)).toBeCloseTo(10.5 / 4 - HEADLIGHT_FLOOR_LOSS, 9);
    expect(headlightShade(0.5, 0)).toBe(0);
    // The loss is the C's floor's mean over the 16 whole shades.
    let loss = 0;
    for (let k = 0; k < 16; k++) loss += k / 4 - (k >> 2);
    expect(loss / 16).toBeCloseTo(HEADLIGHT_FLOOR_LOSS, 9);
    // No step at the half shades.
    for (const s of [3.4, 7.6, 11.3]) expect(Math.abs(headlightShade(s + 0.01, 0) - headlightShade(s, 0))).toBeLessThan(0.01);
  });
});

describe("showHeadlight's colour (D220)", () => {
  test("TYRIAN's lit ice at shade 10 takes the ice bank's shade 2, about 0.6x of lit as in the C", () => {
    const shaded = headlitInBank(ice[10], 10, ice, 0);
    shaded.forEach((v, i) => expect(Math.abs(toSrgb(v) - ICE_SRGB[2][i])).toBeLessThan(1));
    const ratio = Math.pow(luma(shaded) / luma(ice[10]), 1 / 2.2); // gamma-encoded, as the QA measured
    expect(ratio).toBeGreaterThan(0.5);
    expect(ratio).toBeLessThan(0.7);
    // The old rule, the value quartered on a ramp to black, came out near-black.
    const old = ice[10].map((v) => v * Math.pow(1 / 4, 2.2));
    expect(Math.pow(luma(old) / luma(ice[10]), 1 / 2.2)).toBeLessThan(0.3);
  });

  test("every whole shade lands on its bank's entry at the C's shade", () => {
    for (let s = 0; s < 16; s++) {
      // In the dark, the entry itself.
      const c = headlitInBank(ice[s], s, ice, 0);
      c.forEach((v, i) => expect(Math.abs(toSrgb(v) - toSrgb(ice[s >> 2][i]))).toBeLessThan(1.5));
      // Across the gradients, its luminance (a shade raised keeps its own saturation where it has more).
      for (const light of [6, 15]) expect(luma(headlitInBank(ice[s], s, ice, light))).toBeCloseTo(luma(ice[(s + light) >> 2]), 4);
    }
  });

  test("a lit model keeps its light and shade, scaled as its bank's shades are", () => {
    const lit = ice[9].map((v) => v * 1.6) as [number, number, number];
    const dim = ice[9].map((v) => v * 0.6) as [number, number, number];
    const a = headlitInBank(lit, 9, ice, 0);
    const b = headlitInBank(dim, 9, ice, 0);
    const k = bankLumaAt(2, ice) / bankLumaAt(9, ice);
    expect(luma(a) / luma(lit)).toBeCloseTo(k, 2);
    expect(luma(b) / luma(dim)).toBeCloseTo(k, 2);
    expect(luma(a)).toBeGreaterThan(luma(b) * 2.5);
  });

  test("black stays black in the dark", () => {
    const black = [0, 0, 0] as [number, number, number];
    const bank = [black, ...ice.slice(1)];
    headlitInBank(black, 0, bank, 0).forEach((v) => expect(v).toBeCloseTo(0, 6));
  });
});

/** A renderer stand-in that records each render(scene, camera). */
function fakeRenderer() {
  let target: THREE.WebGLRenderTarget | null = null;
  const renders: { target: THREE.WebGLRenderTarget | null; scene: THREE.Scene; material?: THREE.ShaderMaterial; layers: number }[] = [];
  const renderer = {
    capabilities: { maxSamples: 4 },
    toneMapping: THREE.NeutralToneMapping,
    toneMappingExposure: 1,
    shadowMap: { autoUpdate: true },
    autoClear: true,
    getRenderTarget: () => target,
    setRenderTarget: (t: THREE.WebGLRenderTarget | null) => (target = t),
    getDrawingBufferSize: (v: THREE.Vector2) => v.set(64, 32),
    getClearColor: (c: THREE.Color) => c,
    getClearAlpha: () => 1,
    setClearColor: () => {},
    clearDepth: () => {},
    render: (scene: THREE.Scene, cam: THREE.Camera) => {
      const quad = scene.children[0] as THREE.Mesh | undefined;
      renders.push({ target, scene, material: quad?.material as THREE.ShaderMaterial | undefined, layers: cam.layers.mask });
    },
  } as unknown as THREE.WebGLRenderer;
  return { renderer, renders, target: () => target };
}

describe("the headlight frame (D220)", () => {
  const list = (stages: ScreenFilterStage[], showCode = 2) =>
    ({ items: [], palette: 0, filter: -99, brightness: 0, screen: { stages, showCode, playerX: 100, playerY: 150, bars: [] } }) as DrawList;

  test("the effects go over a copy of the frame; the present reads both, and this frame's shades", () => {
    const { renderer, renders } = fakeRenderer();
    const shade = new THREE.Texture();
    const pass = new ScreenFilterPass(renderer, { screenHue: new ScreenHue() } as unknown as PaletteTexture, () => shade);
    pass.setDrawList(list([]));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera();
    camera.layers.enable(VFX_LAYER);
    let sceneLayers = 0;
    pass.render(scene, camera, new THREE.Group(), () => ((sceneLayers = camera.layers.mask), renders.push({ target: null, scene, layers: camera.layers.mask })), 1);
    // The frame without the effects, then the effects (and the shots' art again) over a copy of it.
    expect(sceneLayers & (1 << VFX_LAYER)).toBe(0);
    const effects = renders.filter((r) => r.scene === scene).at(-1)!;
    expect(effects.layers).toBe((1 << VFX_LAYER) | (1 << SHOT_ART_LAYER));
    const present = renders.at(-1)!;
    expect(present.target).toBeNull();
    const u = present.material!.uniforms;
    expect(u.showCode.value).toBe(2);
    expect(u.sourceMap.value).toBe(effects.target!.texture);
    expect(u.baseMap.value).not.toBe(u.sourceMap.value);
    expect(u.shadeMap.value).toBe(shade);
    expect(u.shadeOn.value).toBe(1);
    expect(u.baseHue.value).toBe(0);
    expect(camera.layers.isEnabled(VFX_LAYER)).toBe(true);
    // The rule is in the present pass, on the displayed colour.
    const fs = present.material!.fragmentShader;
    expect(fs).toMatch(/#include <tonemapping_fragment>[\s\S]*headlit\(gl_FragColor\.rgb, displayed\(base\), light, hued\)/);
  });

  test("under a smoothie the base is the filters' output, whose alpha holds their hue", () => {
    const { renderer, renders } = fakeRenderer();
    const pass = new ScreenFilterPass(renderer, { screenHue: new ScreenHue() } as unknown as PaletteTexture, () => null);
    pass.setDrawList(list([{ kind: "lava", pass: Pass.GroundEnemies, temporal: true }]));
    const camera = new THREE.PerspectiveCamera();
    camera.layers.enable(VFX_LAYER);
    pass.render(new THREE.Scene(), camera, new THREE.Group(), () => {}, 1);
    const filter = renders.find((r) => (r.material?.fragmentShader ?? "").includes("lavaWave"))!;
    expect(filter.material!.fragmentShader).toContain("gl_FragColor = vec4(c.rgb, hue >= 0.0 ? hue / 16.0 : 1.0);");
    const u = renders.at(-1)!.material!.uniforms;
    expect(u.baseMap.value).toBe(filter.target!.texture);
    expect(u.baseHue.value).toBe(1);
    expect(u.shadeOn.value).toBe(0); // no shades: the guess everywhere
  });

  test("without the headlight nothing changes: the effects stay in the frame", () => {
    const { renderer, renders } = fakeRenderer();
    const pass = new ScreenFilterPass(renderer, { screenHue: new ScreenHue() } as unknown as PaletteTexture, () => new THREE.Texture());
    pass.setDrawList(list([], 1));
    const camera = new THREE.PerspectiveCamera();
    camera.layers.enable(VFX_LAYER);
    let layers = 0;
    pass.render(new THREE.Scene(), camera, new THREE.Group(), () => (layers = camera.layers.mask), 1);
    expect(layers & (1 << VFX_LAYER)).not.toBe(0);
    expect(renders).toHaveLength(1); // the present alone
    expect(renders[0].material!.uniforms.shadeOn.value).toBe(0);
  });
});

describe("the shade pass on a headlight frame (D220)", () => {
  test("the marks keep the blends' reads: under one half but a lower sheet's", () => {
    expect(TOP_MARK).toBeLessThan(0.5);
    expect(ART_MARK).toBeLessThan(TOP_MARK);
    expect(MODEL_MARK).toBeLessThan(ART_MARK);
    expect(unpackShadeBanks(1, (8 * 16 + 8) / 255)).toEqual({ hue: 8, hue2: 8, weight: 0 });
    const two = unpackShadeBanks(1 - (0.5 * 127) / 255, (10 * 16 + 3) / 255);
    expect(two.hue).toBe(10);
    expect(two.hue2).toBe(3);
    expect(two.weight).toBeCloseTo(0.5, 6);
  });

  test("the flat art and the sheets mark; the sheets' marks are depth-tested, and write their bank", () => {
    const s = new THREE.Scene();
    const art = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.ShaderMaterial({ transparent: true, depthWrite: false, uniforms: { map: { value: new THREE.Texture() } } }));
    art.name = "sprite-art";
    art.geometry.setAttribute("aOrigin", new THREE.InstancedBufferAttribute(new Float32Array(3), 3));
    art.geometry.setAttribute("aUv", new THREE.InstancedBufferAttribute(new Float32Array(4), 4));
    const sheet = new THREE.Mesh(new THREE.PlaneGeometry(), groundTileMaterial(new PaletteTexture(), new TileAtlas(), new UnderGrab(new THREE.Texture())));
    const pal = new THREE.Mesh(new THREE.PlaneGeometry(), new THREE.MeshStandardMaterial({ name: "pal_117" }));
    s.add(art, sheet, pal);
    const drawn: THREE.Material[][] = [];
    let target: THREE.WebGLRenderTarget | null = null;
    const renderer = {
      autoClear: true,
      shadowMap: { autoUpdate: true },
      getRenderTarget: () => target,
      setRenderTarget: (t: THREE.WebGLRenderTarget | null) => (target = t),
      getDrawingBufferSize: (v: THREE.Vector2) => v.set(64, 32),
      getClearColor: (c: THREE.Color) => c,
      getClearAlpha: () => 1,
      setClearColor: () => {},
      render(scene: THREE.Scene, camera: THREE.Camera) {
        const list: THREE.Material[] = [];
        scene.traverseVisible((o) => {
          if ((o as THREE.Mesh).isMesh && o.layers.test(camera.layers)) list.push((o as THREE.Mesh).material as THREE.Material);
        });
        drawn.push(list);
      },
    } as unknown as THREE.WebGLRenderer;
    const pass = new UnderShadePass(new PaletteTexture());
    const area = new NdcRect();
    area.add(-1, -1);
    area.add(1, 1);
    const camera = new THREE.PerspectiveCamera();
    pass.render(renderer, s, camera, area, undefined, true);
    const names = drawn[0].map((m) => m.name).sort();
    expect(names).toEqual(["under_shade_art", "under_shade_model", "under_shade_sheet"]);
    const mark = drawn[0].find((m) => m.name === "under_shade_sheet") as THREE.ShaderMaterial;
    expect(mark.depthTest).toBe(true);
    expect(mark.uniforms.shadeMarksTop.value).toBe(1);
    expect(mark.blendEquation).toBe(THREE.MaxEquation);
    expect([mark.blendSrcAlpha, mark.blendDstAlpha]).toEqual([THREE.OneFactor, THREE.ZeroFactor]); // its bank replaces A
    expect(mark.fragmentShader).toContain("float markBanks = (markHue * 16.0 + markHue) / 255.0;");
    const artMark = drawn[0].find((m) => m.name === "under_shade_art") as THREE.ShaderMaterial;
    expect(artMark.fragmentShader).toContain(`gl_FragColor = vec4(0.0, 0.0, ${ART_MARK.toFixed(3)}, 0.0);`);
    expect(artMark.depthWrite).toBe(false);
    // pal_117: shade 5, bank 7, the model's mark.
    const model = drawn[0].find((m) => m.name === "under_shade_model") as THREE.MeshBasicMaterial;
    expect(model.customProgramCacheKey()).toBe("under-shade-model"); // the shade and bank are uniforms (D235)
    const shader = { fragmentShader: "#include <dithering_fragment>", vertexShader: "", uniforms: {} as Record<string, THREE.IUniform> };
    model.onBeforeCompile(shader as never, {} as never);
    expect(shader.fragmentShader).toContain("float hue = shadeHue;");
    expect(shader.uniforms.shadeHue.value).toBe(7);
    expect(shader.uniforms.shadeValue.value).toBe(Number((5 / 15).toFixed(6)));
    expect(shader.fragmentShader).toContain(MODEL_MARK.toFixed(4));
    // A plain frame: no art, sheet marks over everything (the blends' copies, D204), top sheets don't mark.
    pass.render(renderer, s, camera, area);
    expect(drawn[1].map((m) => m.name).sort()).toEqual(["under_shade_model", "under_shade_sheet"]);
    expect(mark.depthTest).toBe(false);
    expect(mark.uniforms.shadeMarksTop.value).toBe(0);
  });
});

describe("the renderer's shade pass for the headlight (D220)", () => {
  test("a headlight frame draws every pixel's shade and hands it to the screen filters", () => {
    const r = new DrawListRenderer();
    r.setPalettes([new Uint8Array(768) as unknown as Palette]);
    const camera = new THREE.PerspectiveCamera();
    camera.position.set(0, 30, 10);
    const s = new THREE.Scene();
    s.add(r.root);
    const renders: number[] = [];
    let target: THREE.WebGLRenderTarget | null = null;
    const renderer = {
      autoClear: true,
      shadowMap: { autoUpdate: true },
      getRenderTarget: () => target,
      setRenderTarget: (t: THREE.WebGLRenderTarget | null) => (target = t),
      getDrawingBufferSize: (v: THREE.Vector2) => v.set(640, 360),
      getClearColor: (c: THREE.Color) => c,
      getClearAlpha: () => 1,
      setClearColor: () => {},
      render: () => renders.push(1),
    } as unknown as THREE.WebGLRenderer;
    const frame = (showCode: number) => {
      const list: DrawList = { items: [], palette: 0, filter: -99, brightness: 0, screen: { stages: [], showCode, playerX: 100, playerY: 150, bars: [] } };
      r.setDrawList(list);
      r.update(1, camera);
      r.renderUnderShade(renderer, s, camera);
    };
    // Nothing blended and no headlight: no pass.
    frame(0);
    expect(renders).toHaveLength(0);
    expect(r.headlightShadeMap).toBeNull();
    frame(2);
    expect(renders).toHaveLength(1);
    expect(r.headlightShadeMap?.name).toBe("under-shade");
    frame(1); // the flipped screen: no headlight
    expect(r.headlightShadeMap).toBeNull();
  });
});
