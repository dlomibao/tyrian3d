// The terrain's own palette shade under the C's blended layers (DECISIONS.md D204; hueBlend.ts, D174).
//
// blit_sprite2_blend and draw_background_2_blend average the blended pixel's shade with the shade of
// the pixel underneath, `*pixels & 0x0f`: the palette index that pixel was drawn with. The 3D frame
// has lit colours, not indices, and guessing the index from a lit colour (its nearest palette entry)
// hops between ramps on painted ground: SAVARA Y's lit sea fell between banks 0, 1, 3, 8, 10 and 13,
// the shade jumped several steps from texel to texel, and the cloud over it drew the painting's
// gradients as contour lines (E3 QA L5, D203).
//
// So before the frame, the ground layers draw their own shade into a target of their own:
// - the classic tiles: the index's low nibble, exactly the C's;
// - the 4x MMPX ground: the four nearest texels' low nibbles, weighted as its colour is;
// - an HD painting: its unlit brightness along the raw palette's ramp (before JE_filterScreen, which
//   the C applies to the indices' colours, not to the indices) of the original tile's main bank (the second
//   bank too where the tile has one, read along whichever ramp the painted colour is nearer, mixed
//   where they're about as near: a shore's sand and sea), as the blend sheets' own shade is read
//   along their tile's bank (`instBank`).
// Everything else that writes depth draws its own shade too where it has one, in the same render
// and behind the same depth test, so the terrain shows only where the frame shows it: a pal_<index>
// material its index's low nibble, an HD rock its palette data's shade (rockMaterial.ts). Anything
// else (no palette index) marks "not known". The blended layers read this shade where it is known
// and fall back to the lit frame copy's guess elsewhere.
//
// The target's texels: r = shade / 15, g = 1 where the shade is known, b = 1 under a background-2
// sheet. The explosions and background2over 2's sheets read a copy made after the sheets are drawn,
// so where a sheet lies the frame shows the sheet's blend, not the terrain: there they guess from the
// copy (whose colour is then an exact palette colour, which the guess finds).
//
// Not in this pass (they keep the shade under them): what writes no depth (the shadows, the scorch
// marks: the C has neither; models while they fade), and the shots' and explosions' art under a later
// copy. The cost is one more render of the scene, scissored to the blended layers' area, on frames
// that have one.

import * as THREE from "three";
import { areaPixels, HB_SHADE_PARS, ShadeLut, type NdcRect } from "./hueBlend";
import type { PaletteTexture } from "./paletteTexture";
import { cutMaskMaterial, type MaskCut } from "./screenFilters";
import { SAMPLE_PARS, TERRAIN_VERTEX_MAIN, TERRAIN_VERTEX_PARS } from "./remaster/terrainMaterial";
import { passHeight } from "./passHeights";
import { Pass } from "../sim/draw";
import { PALETTE_MATERIAL } from "./modelFrames";
import { rockShadeMap } from "./rockMaterial";

/** How a ground material's own shade is drawn (`material.userData.shadeOut`). */
export type ShadeOut =
  /** The classic tile atlas (indices): `atlasMap`, `tileUv`, per instance `instTile`. */
  | { kind: "tileIndex"; uniforms: { atlasMap: { value: THREE.Texture | null }; tileUv: { value: THREE.Vector2 } } }
  /** The 4x MMPX index atlas, the four texels round a point weighted as remasterGroundMaterial does. */
  | { kind: "remasterIndex"; uniforms: { atlasMap: { value: THREE.Texture | null }; tileUv: { value: THREE.Vector2 }; sharpness: { value: number } } }
  /**
   * An HD terrain atlas (terrainMaterial.ts), per instance `instTile4` and `instBank` (the original
   * tile's two main banks). `cutout`: alpha-cut at one half, premultiplied colour.
   */
  | { kind: "terrainHd"; cutout: boolean; uniforms: { terrainMap: { value: THREE.Texture | null }; rectSize: { value: THREE.Vector2 } } };

/** A known texel's output for a shade `s` (0..15). */
const SHADE_OUTPUT = "gl_FragColor = vec4(clamp(s, 0.0, 15.0) / 15.0, 1.0, 0.0, 1.0);";

const SHADE_VERTEX: Record<ShadeOut["kind"], string> = {
  tileIndex: /* glsl */ `
attribute vec2 tileUvIn;
attribute vec2 instTile;
uniform vec2 tileUv;
varying vec2 vAtlasUv;
varying vec2 vTileOrigin;
void main() {
  mat4 m = modelMatrix;
  #ifdef USE_INSTANCING
    m = m * instanceMatrix;
  #endif
  vTileOrigin = instTile;
  vAtlasUv = instTile + tileUvIn * tileUv;
  gl_Position = projectionMatrix * viewMatrix * m * vec4(position, 1.0);
}`,
  remasterIndex: /* glsl */ `
attribute vec2 tileUvIn;
attribute vec2 instTile;
uniform vec2 tileUv;
varying vec2 vAtlasUv;
void main() {
  mat4 m = modelMatrix;
  #ifdef USE_INSTANCING
    m = m * instanceMatrix;
  #endif
  vAtlasUv = instTile + tileUvIn * tileUv;
  gl_Position = projectionMatrix * viewMatrix * m * vec4(position, 1.0);
}`,
  terrainHd: /* glsl */ `
${TERRAIN_VERTEX_PARS}
attribute vec2 instBank;
varying vec2 vBanks;
void main() {
  ${TERRAIN_VERTEX_MAIN}
  vBanks = instBank;
  mat4 m = modelMatrix;
  #ifdef USE_INSTANCING
    m = m * instanceMatrix;
  #endif
  gl_Position = projectionMatrix * viewMatrix * m * vec4(position, 1.0);
}`,
};

const SHADE_FRAGMENT: Record<ShadeOut["kind"], (cutout: boolean) => string> = {
  // groundTileMaterial's read; index 0 (black space) is shade 0.
  tileIndex: () => /* glsl */ `
uniform sampler2D atlasMap;
uniform vec2 tileUv;
varying vec2 vAtlasUv;
varying vec2 vTileOrigin;
void main() {
  vec2 halfTexel = vec2(0.5 / float(textureSize(atlasMap, 0).x));
  vec2 uv = clamp(vAtlasUv, vTileOrigin + halfTexel, vTileOrigin + tileUv - halfTexel);
  float index = floor(texture2D(atlasMap, uv).r * 255.0 + 0.5);
  float s = index - floor(index / 16.0) * 16.0;
  ${SHADE_OUTPUT}
}`,
  // remasterGroundMaterial's four texels and weights.
  remasterIndex: () => /* glsl */ `
uniform sampler2D atlasMap;
uniform float sharpness;
varying vec2 vAtlasUv;
float texelShade(ivec2 p) {
  float index = floor(texelFetch(atlasMap, p, 0).r * 255.0 + 0.5);
  return index - floor(index / 16.0) * 16.0;
}
void main() {
  vec2 tp = vAtlasUv * vec2(textureSize(atlasMap, 0)) - 0.5;
  ivec2 t0 = ivec2(floor(tp));
  vec2 f = clamp((fract(tp) - 0.5) * sharpness + 0.5, 0.0, 1.0);
  float s = mix(mix(texelShade(t0), texelShade(t0 + ivec2(1, 0)), f.x), mix(texelShade(t0 + ivec2(0, 1)), texelShade(t0 + ivec2(1, 1)), f.x), f.y);
  ${SHADE_OUTPUT}
}`,
  // terrainMaterial's read (level-limited, inside the tile's rect, D138's tint added); the shade of
  // its unlit brightness along the tile's banks.
  terrainHd: (cutout) => /* glsl */ `
uniform sampler2D paletteMap;
${HB_SHADE_PARS}
${SAMPLE_PARS}
varying vec2 vBanks;
vec3 shadeSrgb(vec3 rgb) {
  rgb = clamp(rgb, 0.0, 1.0);
  return mix(1.055 * pow(rgb, vec3(1.0 / 2.4)) - 0.055, rgb * 12.92, step(rgb, vec3(0.0031308)));
}
vec3 shadeLinear(vec3 s) {
  s = clamp(s, 0.0, 1.0);
  return mix(pow((s + 0.055) / 1.055, vec3(2.4)), s / 12.92, step(s, vec3(0.04045)));
}
void main() {
  vec4 tex = terrainSample(vTileTexel, terrainLod());
  ${cutout ? "if (tex.a < 0.5) discard;\n  vec3 painted = tex.rgb / max(tex.a, 1e-4);" : "vec3 painted = tex.rgb;"}
  if (vTintOrigin.x >= 0.0) painted = shadeLinear(shadeSrgb(painted) + terrainTint());
  float lum = hbLum(painted);
  float s = hbShade(vBanks.x, lum);
  if (vBanks.y != vBanks.x) {
    // Two ramps: the one whose colour at this brightness is nearer the painting's (sRGB), mixed
    // over a small band where they're about as near, so a texel never hops between them.
    float s2 = hbShade(vBanks.y, lum);
    vec3 p = shadeSrgb(painted);
    float d1 = distance(p, shadeSrgb(hbRamp(vBanks.x, s)));
    float d2 = distance(p, shadeSrgb(hbRamp(vBanks.y, s2)));
    s = mix(s, s2, clamp(0.5 + (d1 - d2) * 8.0, 0.0, 1.0));
  }
  ${SHADE_OUTPUT}
}`,
};

/** The shade material for a ground material's `shadeOut` (sharing its uniforms, so atlas swaps follow). */
export function shadeOutMaterial(out: ShadeOut, shared: { paletteMap: { value: THREE.Texture }; blendShadeLut: { value: THREE.Texture } }): THREE.ShaderMaterial {
  const uniforms: Record<string, THREE.IUniform> = { ...out.uniforms };
  if (out.kind === "terrainHd") Object.assign(uniforms, shared);
  return new THREE.ShaderMaterial({
    name: "under_shade",
    vertexShader: SHADE_VERTEX[out.kind],
    fragmentShader: SHADE_FRAGMENT[out.kind](out.kind === "terrainHd" && out.cutout),
    uniforms,
    side: THREE.DoubleSide,
  });
}

/**
 * Instances higher than this are background2over 2's sheets (PASS_HEIGHT[Background2Top]), which no
 * copy before them reads: they don't mark the target. The lower sheets stay below it however far
 * they're lifted over the models they cover (sheetLift.ts: they end under the explosions).
 */
export const SHEET_MARK_MAX_HEIGHT = passHeight(Pass.Background2Top) - 0.2;

/** The mark a background-2 sheet's covered texel adds to the target (added: the shade under it stays). */
const SHEET_MARK_OUTPUT = `if (vHeight > ${SHEET_MARK_MAX_HEIGHT.toFixed(3)}) discard;\n  gl_FragColor = vec4(0.0, 0.0, 1.0, 0.0);`;

/** The camera layer the pass's own draws use for a moment; nothing else is on it. */
const SHADE_LAYER = 29;

/** Whether a material is a blended background-2 sheet's (its texels' cover is known: `maskCut`). */
function sheetCut(m: THREE.Material): MaskCut | undefined {
  return m.transparent && !m.depthWrite && m.colorWrite ? (m.userData.maskCut as MaskCut | undefined) : undefined;
}

/**
 * A model material's own shade (the C's sprite pixel's): a flat `shade` for a pal_<index> material (index &
 * 15), or the R channel (shade / 15) of a rock material's palette data (rockMaterial.ts).
 */
function modelShadeMaterial(shade: number | THREE.Texture): THREE.MeshBasicMaterial {
  const rock = typeof shade !== "number";
  const m = new THREE.MeshBasicMaterial({ name: "under_shade_model", fog: false, side: THREE.DoubleSide, map: rock ? shade : null });
  const value = rock ? "texture2D(map, vMapUv).r" : `${(Math.min(15, Math.max(0, shade)) / 15).toFixed(6)}`;
  m.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace("#include <dithering_fragment>", `#include <dithering_fragment>\ngl_FragColor = vec4(${value}, 1.0, 0.0, 1.0);`);
  };
  m.customProgramCacheKey = () => (rock ? "under-shade-rock" : `under-shade-model-${shade}`);
  return m;
}

/** The terrain shades' target and the pass that draws it each frame (see the top of this file). */
export class UnderShadePass {
  readonly target = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.UnsignedByteType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
    depthBuffer: true,
    stencilBuffer: false,
    generateMipmaps: false,
  });
  private readonly unknown = new THREE.MeshBasicMaterial({ name: "under_shade_unknown", color: 0x000000, fog: false, side: THREE.DoubleSide });
  private readonly shadeMaterials = new WeakMap<THREE.Material, THREE.Material>();
  private readonly palShades: THREE.MeshBasicMaterial[] = [];
  private readonly size = new THREE.Vector2();
  private readonly clearColor = new THREE.Color();
  /** Frames drawn (for tests and the harness). */
  renders = 0;
  /**
   * The raw palette (before JE_filterScreen) and its shade lookup: an HD painting's shade is its
   * brightness along the ramp its tile's indices were drawn with, whatever the level filter does to
   * the screen's colours afterwards (CAMANIS, D193).
   */
  private readonly rawPalette: THREE.DataTexture;
  private readonly rawShades = new ShadeLut();
  private readonly shared: { paletteMap: { value: THREE.Texture }; blendShadeLut: { value: THREE.Texture } };

  constructor(private readonly palette: PaletteTexture) {
    this.target.texture.name = "under-shade";
    this.rawPalette = new THREE.DataTexture(palette.raw, 256, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
    this.rawPalette.colorSpace = THREE.SRGBColorSpace;
    this.rawPalette.magFilter = this.rawPalette.minFilter = THREE.NearestFilter;
    this.rawPalette.generateMipmaps = false;
    this.shared = { paletteMap: { value: this.rawPalette }, blendShadeLut: { value: this.rawShades.texture } };
  }

  /**
   * What `material` draws in the pass: the ground's shade, a lower sheet's mark, a model's own shade,
   * "unknown" for anything else that writes depth, or null (left out: it writes no depth or colour).
   */
  private passMaterial(material: THREE.Material, isMesh: boolean): THREE.Material | null {
    if (!isMesh) return null;
    const out = material.userData.shadeOut as ShadeOut | undefined;
    const cut = sheetCut(material);
    // (Checked each frame: a model's materials turn translucent while it fades.)
    if (!out && !cut && (material.transparent || !material.depthWrite || !material.colorWrite)) return null;
    const cached = this.shadeMaterials.get(material);
    if (cached) return cached;
    let m: THREE.Material;
    if (out) m = shadeOutMaterial(out, this.shared);
    else if (cut) {
      const mark = cutMaskMaterial(cut, SHEET_MARK_OUTPUT);
      mark.name = "under_shade_sheet";
      mark.transparent = true;
      mark.depthTest = false;
      mark.depthWrite = false;
      mark.blending = THREE.CustomBlending;
      mark.blendSrc = mark.blendDst = THREE.OneFactor;
      mark.blendEquation = THREE.AddEquation;
      m = mark;
    } else {
      const rock = rockShadeMap(material);
      const pal = PALETTE_MATERIAL.exec(material.name);
      if (rock) m = modelShadeMaterial(rock);
      else if (pal) {
        const s = Number(pal[1]) & 15;
        m = this.palShades[s] ??= modelShadeMaterial(s);
      } else m = this.unknown;
    }
    this.shadeMaterials.set(material, m);
    return m;
  }

  /**
   * Draw the terrain's shades over `area` of a target the size of the renderer's current one, for
   * the scene as `camera` sees it. Returns false (nothing drawn) when `area` is empty.
   */
  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, area: NdcRect): boolean {
    if (area.empty) return false;
    if (this.rawShades.update(this.palette.raw, this.palette.version)) this.rawPalette.needsUpdate = true;
    const current = renderer.getRenderTarget();
    let w: number, h: number;
    if (current) {
      w = current.width;
      h = current.height;
    } else {
      renderer.getDrawingBufferSize(this.size);
      w = Math.max(1, Math.floor(this.size.x));
      h = Math.max(1, Math.floor(this.size.y));
    }
    if (this.target.width !== w || this.target.height !== h) this.target.setSize(w, h);
    const [x0, y0, x1, y1] = areaPixels(area, w, h);
    if (x1 <= x0 || y1 <= y0) return false;
    this.target.scissor.set(x0, y0, x1 - x0, y1 - y0);
    this.target.scissorTest = true;

    // Each object the camera would draw, in its pass material (or left out), on the pass's layer.
    const drawn: { object: THREE.Mesh; material: THREE.Material | THREE.Material[]; layers: number }[] = [];
    scene.traverseVisible((o) => {
      const r = o as THREE.Mesh;
      if (!r.isMesh || !o.layers.test(camera.layers) || !r.material) return;
      const source = r.material;
      let pass: THREE.Material | THREE.Material[] | null;
      if (Array.isArray(source)) {
        const list = source.map((m) => this.passMaterial(m, true));
        pass = list.every((m) => m === null) ? null : list.map((m) => m ?? this.unknown);
      } else pass = this.passMaterial(source, true);
      if (pass) drawn.push({ object: r, material: pass, layers: o.layers.mask });
    });

    const background = scene.background;
    const override = scene.overrideMaterial;
    const autoClear = renderer.autoClear;
    const shadows = renderer.shadowMap.autoUpdate;
    const layers = camera.layers.mask;
    renderer.getClearColor(this.clearColor);
    const clearAlpha = renderer.getClearAlpha();
    // Objects join the render by the pass's layer, not left out by `visible` (that would hide their
    // children too); their materials are swapped for the render and back.
    const saved = drawn.map((d) => d.object.material);
    scene.background = null;
    scene.overrideMaterial = null;
    renderer.shadowMap.autoUpdate = false;
    renderer.autoClear = true;
    renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(this.target);
    try {
      for (const d of drawn) {
        d.object.material = d.material;
        d.object.layers.set(SHADE_LAYER);
      }
      camera.layers.set(SHADE_LAYER);
      renderer.render(scene, camera);
    } finally {
      drawn.forEach((d, i) => {
        d.object.material = saved[i];
        d.object.layers.mask = d.layers;
      });
      camera.layers.mask = layers;
      scene.overrideMaterial = override;
      scene.background = background;
      renderer.autoClear = autoClear;
      renderer.shadowMap.autoUpdate = shadows;
      renderer.setClearColor(this.clearColor, clearAlpha);
      renderer.setRenderTarget(current);
    }
    this.renders++;
    return true;
  }

  dispose(): void {
    this.target.dispose();
    this.unknown.dispose();
    this.rawPalette.dispose();
    this.rawShades.texture.dispose();
    for (const m of this.palShades) m?.dispose();
  }
}
