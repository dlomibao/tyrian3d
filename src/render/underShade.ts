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
// Only the pixels under a blended draw are read (each reads its own pixel), so a model whose screen
// box reaches none of the draws' own rectangles is left out of the pass (D207: GYGES's boss, framed
// by the sheets on three sides, lies inside their bounding box but under none of them).
//
// Not in this pass (they keep the shade under them): what writes no depth (the shadows, the scorch
// marks: the C has neither; models while they fade), and the shots' and explosions' art under a later
// copy. The cost is one more render of the scene, on frames that have a blended layer: through a
// camera narrowed to the blended layers' area, so only what lies there is drawn (D206).

import * as THREE from "three";
import { areaPixels, GRAB_MARGIN, HB_SHADE_PARS, RawShades, type NdcRect } from "./hueBlend";
import type { PaletteTexture } from "./paletteTexture";
import { ART_MARK, cutMaskMaterial, flatArtMaskMaterial, isFlatArt, MODEL_MARK, TOP_MARK, type MaskCut } from "./screenFilters";
import { SAMPLE_PARS, TERRAIN_VERTEX_MAIN, TERRAIN_VERTEX_PARS } from "./remaster/terrainMaterial";
import { passHeight } from "./passHeights";
import { Pass } from "../sim/draw";
import { PALETTE_MATERIAL } from "./modelFrames";
import { rockRamps, rockShadeMap } from "./rockMaterial";
import { addLightsToLayer, isLight, restoreLights } from "./passLights";

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

/**
 * A known texel's output for a shade `s` (0..15) in bank `hue` (0..15, the index's high nibble), or
 * mixed between banks `hue` and `hue2` with weight `tw` on the second (a painting's two ramps, a
 * rock's two). A: hue * 16 + hue2; G: 1 - tw * 127 / 255, so it stays over one half (known) and a
 * single bank (tw = 0) writes 1, as before. The headlight reads both (D220).
 */
const shadeOutput = (mark: string) =>
  `gl_FragColor = vec4(clamp(s, 0.0, 15.0) / 15.0, 1.0 - clamp(tw, 0.0, 1.0) * 127.0 / 255.0, ${mark}, (clamp(hue, 0.0, 15.0) * 16.0 + clamp(hue2, 0.0, 15.0)) / 255.0);`;
const SHADE_OUTPUT = shadeOutput("0.0");
/** A model's: B is MODEL_MARK (the headlight reads its shade off its lit colour, D220). */
const MODEL_SHADE_OUTPUT = shadeOutput(MODEL_MARK.toFixed(4));

/** The two banks and weight of SHADE_OUTPUT, unpacked from a texel (for tests and the shaders' docs). */
export function unpackShadeBanks(g: number, a: number): { hue: number; hue2: number; weight: number } {
  const packed = Math.round(a * 255);
  return { hue: packed >> 4, hue2: packed & 15, weight: Math.min(1, Math.max(0, ((1 - g) * 255) / 127)) };
}

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
  float hue = floor(index / 16.0);
  float s = index - hue * 16.0;
  float hue2 = hue;
  float tw = 0.0;
  ${SHADE_OUTPUT}
}`,
  // remasterGroundMaterial's four texels and weights.
  remasterIndex: () => /* glsl */ `
uniform sampler2D atlasMap;
uniform float sharpness;
varying vec2 vAtlasUv;
float texelIndex(ivec2 p) { return floor(texelFetch(atlasMap, p, 0).r * 255.0 + 0.5); }
float texelShade(ivec2 p) {
  float index = texelIndex(p);
  return index - floor(index / 16.0) * 16.0;
}
void main() {
  vec2 tp = vAtlasUv * vec2(textureSize(atlasMap, 0)) - 0.5;
  ivec2 t0 = ivec2(floor(tp));
  vec2 f = clamp((fract(tp) - 0.5) * sharpness + 0.5, 0.0, 1.0);
  float s = mix(mix(texelShade(t0), texelShade(t0 + ivec2(1, 0)), f.x), mix(texelShade(t0 + ivec2(0, 1)), texelShade(t0 + ivec2(1, 1)), f.x), f.y);
  // The bank: the most-weighted of the four texels' (a bank can't be mixed).
  ivec2 near = t0 + ivec2(f.x > 0.5 ? 1 : 0, f.y > 0.5 ? 1 : 0);
  float hue = floor(texelIndex(near) / 16.0);
  float hue2 = hue;
  float tw = 0.0;
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
  float hue = floor(vBanks.x / 16.0 + 0.5);
  float hue2 = floor(vBanks.y / 16.0 + 0.5);
  float tw = 0.0;
  if (vBanks.y != vBanks.x) {
    // Two ramps: the one whose colour at this brightness is nearer the painting's (sRGB), mixed
    // over a small band where they're about as near, so a texel never hops between them.
    float s2 = hbShade(vBanks.y, lum);
    vec3 p = shadeSrgb(painted);
    float d1 = distance(p, shadeSrgb(hbRamp(vBanks.x, s)));
    float d2 = distance(p, shadeSrgb(hbRamp(vBanks.y, s2)));
    tw = clamp(0.5 + (d1 - d2) * 8.0, 0.0, 1.0);
    s = mix(s, s2, tw);
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

/**
 * The mark a background-2 sheet's covered texel writes (max-blended, so the shade under it stays;
 * its bank replaces A). background2over 2's sheets mark only for the headlight (`shadeMarksTop`).
 */
const SHEET_MARK_OUTPUT = `float markBanks = (markHue * 16.0 + markHue) / 255.0;
  if (vHeight > ${SHEET_MARK_MAX_HEIGHT.toFixed(3)}) {
    if (shadeMarksTop < 0.5) discard;
    gl_FragColor = vec4(0.0, 0.0, ${TOP_MARK.toFixed(3)}, markBanks);
  } else gl_FragColor = vec4(0.0, 0.0, 1.0, markBanks);`;

/** A flat-art texel's mark (headlight frames only); A (0) leaves the bank under it. */
const ART_MARK_OUTPUT = `gl_FragColor = vec4(0.0, 0.0, ${ART_MARK.toFixed(3)}, 0.0);`;

/** Marks keep what is under them: each channel takes the larger of the two (B: the mark; R, G 0). */
function markBlending(m: THREE.Material): void {
  m.transparent = true;
  m.depthWrite = false;
  m.blending = THREE.CustomBlending;
  m.blendSrc = m.blendDst = THREE.OneFactor;
  m.blendEquation = THREE.MaxEquation;
}

/** The camera layer the pass's own draws use for a moment; nothing else is on it. */
const SHADE_LAYER = 29;

/** Whether a material is a blended background-2 sheet's (its texels' cover is known: `maskCut`). */
function sheetCut(m: THREE.Material): MaskCut | undefined {
  return m.transparent && !m.depthWrite && m.colorWrite ? (m.userData.maskCut as MaskCut | undefined) : undefined;
}

/**
 * A model material's own shade (the C's sprite pixel's) and bank: a flat `shade` in bank `hue` for a
 * pal_<index> material (index & 15, index >> 4), or the R channel (shade / 15) of a rock material's
 * palette data, in the ramp its G channel picks of `ramps` (rockMaterial.ts).
 */
function modelShadeMaterial(shade: number | THREE.Texture, hue = 0, ramps: readonly number[] = [0]): THREE.MeshBasicMaterial {
  const rock = typeof shade !== "number";
  const m = new THREE.MeshBasicMaterial({ name: "under_shade_model", fog: false, side: THREE.DoubleSide, map: rock ? shade : null });
  const value = rock ? "texture2D(map, vMapUv).r" : `${(Math.min(15, Math.max(0, shade)) / 15).toFixed(6)}`;
  const n = Math.max(1, Math.min(4, ramps.length));
  const list = Array.from({ length: 4 }, (_, i) => (ramps[Math.min(i, n - 1)] ?? 0) & 15);
  // The rock's ramps: G steps through them (0..1), weights between the two nearest (rockMaterial.ts).
  const ramp = (j: string) => `(${j} < 0.5 ? ${list[0].toFixed(1)} : ${j} < 1.5 ? ${list[1].toFixed(1)} : ${j} < 2.5 ? ${list[2].toFixed(1)} : ${list[3].toFixed(1)})`;
  const banks = rock
    ? `float rockCode = texture2D(map, vMapUv).g * ${(n - 1).toFixed(1)}; float rockJ = min(floor(rockCode), ${Math.max(0, n - 2).toFixed(1)}); float hue = ${ramp("rockJ")}; float hue2 = ${ramp("(rockJ + 1.0)")}; float tw = ${n > 1 ? "clamp(rockCode - rockJ, 0.0, 1.0)" : "0.0"};`
    : `float hue = ${(hue & 15).toFixed(1)}; float hue2 = hue; float tw = 0.0;`;
  m.onBeforeCompile = (shader) => {
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <dithering_fragment>",
      `#include <dithering_fragment>\n${banks}\nfloat s = ${value} * 15.0;\n${MODEL_SHADE_OUTPUT}`,
    );
  };
  m.customProgramCacheKey = () => (rock ? `under-shade-rock-${list.slice(0, n).join(",")}` : `under-shade-model-${shade}-${hue & 15}`);
  return m;
}

/** Cells across and down the screen in the grid the blended draws' rectangles are marked in (D207). */
const COVER_COLS = 128;
const COVER_ROWS = 72;

/**
 * The screen cells (COVER_COLS x COVER_ROWS over NDC -1..1) any of a frame's blended draws' rectangles
 * touch, with a summed-area table, so whether a box reaches one is four reads.
 */
export class CoverGrid {
  private readonly sum = new Int32Array((COVER_COLS + 1) * (COVER_ROWS + 1));

  /** Mark `rects` (NDC x0, y0, x1, y1 each), each grown by (mx, my). */
  build(rects: ArrayLike<number>, mx: number, my: number): void {
    const W = COVER_COLS + 1;
    const sum = this.sum;
    sum.fill(0);
    for (let i = 0; i + 3 < rects.length; i += 4) {
      const c0 = Math.max(0, col(rects[i] - mx));
      const r0 = Math.max(0, row(rects[i + 1] - my));
      const c1 = Math.min(COVER_COLS - 1, col(rects[i + 2] + mx));
      const r1 = Math.min(COVER_ROWS - 1, row(rects[i + 3] + my));
      for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) sum[(r + 1) * W + c + 1] = 1;
    }
    for (let r = 1; r <= COVER_ROWS; r++) for (let c = 1; c <= COVER_COLS; c++) sum[r * W + c] += sum[(r - 1) * W + c] + sum[r * W + c - 1] - sum[(r - 1) * W + c - 1];
  }

  /** Whether the NDC box (x0, y0)-(x1, y1) touches a marked cell. */
  hits(x0: number, y0: number, x1: number, y1: number): boolean {
    const c0 = Math.max(0, col(x0));
    const r0 = Math.max(0, row(y0));
    const c1 = Math.min(COVER_COLS - 1, col(x1));
    const r1 = Math.min(COVER_ROWS - 1, row(y1));
    if (c1 < c0 || r1 < r0) return false;
    const W = COVER_COLS + 1;
    const s = this.sum;
    return s[(r1 + 1) * W + c1 + 1] - s[r0 * W + c1 + 1] - s[(r1 + 1) * W + c0] + s[r0 * W + c0] > 0;
  }
}

const col = (x: number) => Math.floor(((x + 1) / 2) * COVER_COLS);
const row = (y: number) => Math.floor(((y + 1) / 2) * COVER_ROWS);

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
  /** The flat art's marks, one per atlas (headlight frames). */
  private readonly artMarks = new WeakMap<THREE.Texture, THREE.ShaderMaterial>();
  /** 1 while a headlight frame's pass runs: background2over 2's sheets and the flat art mark too. */
  private readonly marksTop = { value: 0 };
  /** The sheets' mark materials, depth-tested on headlight frames. */
  private readonly sheetMarks = new Set<THREE.Material>();
  private readonly size = new THREE.Vector2();
  private readonly clearColor = new THREE.Color();
  /**
   * The camera the pass draws with: the frame's, its projection narrowed to the blended area and drawn
   * into that area's viewport, so the same pixels land where they do in the frame and three's frustum
   * culling leaves out what is outside the area (D206; scissoring alone drew every model in view).
   */
  private readonly areaCamera = new THREE.Camera();
  private readonly crop = new THREE.Matrix4();
  /** Frames drawn (for tests and the harness). */
  renders = 0;
  /** Meshes the last frame left out for reaching none of the blended draws' rectangles (D207). */
  culled = 0;
  private readonly cover = new CoverGrid();
  private readonly frustum = new THREE.Frustum();
  private readonly viewProj = new THREE.Matrix4();
  private readonly toClip = new THREE.Matrix4();
  private readonly corner = new THREE.Vector4();
  /**
   * The raw palette (before JE_filterScreen) and its shade lookup: an HD painting's shade is its
   * brightness along the ramp its tile's indices were drawn with, whatever the level filter does to
   * the screen's colours afterwards (CAMANIS, D193).
   */
  private readonly raw: RawShades;
  private readonly shared: { paletteMap: { value: THREE.Texture }; blendShadeLut: { value: THREE.Texture } };

  constructor(palette: PaletteTexture) {
    this.target.texture.name = "under-shade";
    this.raw = new RawShades(palette);
    this.shared = { paletteMap: { value: this.raw.palette }, blendShadeLut: { value: this.raw.shades.texture } };
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
      mark.fragmentShader = `uniform float shadeMarksTop;\n${mark.fragmentShader}`;
      mark.uniforms.shadeMarksTop = this.marksTop;
      markBlending(mark);
      // Its bank replaces the one under it (the frame shows the sheet's colour there).
      mark.blendEquationAlpha = THREE.AddEquation;
      mark.blendSrcAlpha = THREE.OneFactor;
      mark.blendDstAlpha = THREE.ZeroFactor;
      // Over everything for the blends' copies (D204); behind what covers the sheet in the frame for
      // the headlight, whose shade it says (render() sets it per frame).
      mark.depthTest = false;
      this.sheetMarks.add(mark);
      m = mark;
    } else {
      const rock = rockShadeMap(material);
      const pal = PALETTE_MATERIAL.exec(material.name);
      if (rock) m = modelShadeMaterial(rock, 0, rockRamps(material));
      else if (pal) {
        const index = Number(pal[1]) & 255;
        m = this.palShades[index] ??= modelShadeMaterial(index & 15, index >> 4);
      } else m = this.unknown;
    }
    this.shadeMaterials.set(material, m);
    return m;
  }

  /** The mark material for a flat-art batch drawn with `material` (one per atlas). */
  private artMark(material: THREE.ShaderMaterial): THREE.ShaderMaterial {
    const map = material.uniforms.map.value as THREE.Texture;
    let m = this.artMarks.get(map);
    if (!m) {
      m = flatArtMaskMaterial(map, ART_MARK_OUTPUT);
      m.name = "under_shade_art";
      markBlending(m);
      this.artMarks.set(map, m);
    }
    return m;
  }

  /**
   * Draw the terrain's shades over `area` of a target the size of the renderer's current one, for
   * the scene as `camera` sees it. Returns false (nothing drawn) when `area` is empty. `rects`: the
   * blended draws' own screen rectangles (NDC x0, y0, x1, y1 each) inside `area`; a model reaching
   * none of them is left out (D207). Without them every model in `area` is drawn. `marks` (the
   * headlight, D220): background2over 2's sheets and the flat art mark the texels they cover too.
   */
  render(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, area: NdcRect, rects?: ArrayLike<number>, marks = false): boolean {
    if (area.empty) return false;
    this.raw.update();
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
    this.target.viewport.set(x0, y0, x1 - x0, y1 - y0);
    const view = this.cropCamera(camera, x0 / w, y0 / h, x1 / w, y1 / h);
    // A model is left out when it lies outside the narrowed view or its screen box reaches none of
    // the rectangles (grown by the copies' margin, as the area is).
    const cull = rects !== undefined && rects.length >= 4;
    if (cull) {
      // This frame's matrices (the pass's render below then leaves them as they are).
      if (scene.matrixWorldAutoUpdate) scene.updateMatrixWorld();
      this.cover.build(rects, (2 * GRAB_MARGIN) / w, (2 * GRAB_MARGIN) / h);
      this.viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
      this.frustum.setFromProjectionMatrix(this.toClip.multiplyMatrices(view.projectionMatrix, view.matrixWorldInverse));
    }
    this.culled = 0;

    // Each object the camera would draw, in its pass material (or left out), on the pass's layer.
    const drawn: { object: THREE.Mesh; material: THREE.Material | THREE.Material[]; layers: number }[] = [];
    const lights: THREE.Object3D[] = [];
    scene.traverseVisible((o) => {
      if (isLight(o)) lights.push(o);
      const r = o as THREE.Mesh;
      if (!r.isMesh || !o.layers.test(camera.layers) || !r.material) return;
      if (isFlatArt(o)) {
        if (marks) drawn.push({ object: r, material: this.artMark(r.material as THREE.ShaderMaterial), layers: o.layers.mask });
        return;
      }
      if (cull && !this.reachesCover(r)) {
        this.culled++;
        return;
      }
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
    const matrices = scene.matrixWorldAutoUpdate;
    renderer.getClearColor(this.clearColor);
    const clearAlpha = renderer.getClearAlpha();
    // Objects join the render by the pass's layer, not left out by `visible` (that would hide their
    // children too); their materials are swapped for the render and back.
    const saved = drawn.map((d) => d.object.material);
    // The lights join the render too, so their state (and every lit material's program) stays as the
    // main render has it (passLights.ts, D206).
    const lightMasks = addLightsToLayer(lights, camera.layers, SHADE_LAYER);
    scene.background = null;
    scene.overrideMaterial = null;
    renderer.shadowMap.autoUpdate = false;
    if (cull) scene.matrixWorldAutoUpdate = false;
    renderer.autoClear = true;
    renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(this.target);
    this.marksTop.value = marks ? 1 : 0;
    for (const m of this.sheetMarks) m.depthTest = marks;
    try {
      for (const d of drawn) {
        d.object.material = d.material;
        d.object.layers.set(SHADE_LAYER);
      }
      renderer.render(scene, view);
    } finally {
      drawn.forEach((d, i) => {
        d.object.material = saved[i];
        d.object.layers.mask = d.layers;
      });
      restoreLights(lights, lightMasks);
      scene.overrideMaterial = override;
      scene.background = background;
      renderer.autoClear = autoClear;
      renderer.shadowMap.autoUpdate = shadows;
      scene.matrixWorldAutoUpdate = matrices;
      renderer.setClearColor(this.clearColor, clearAlpha);
      renderer.setRenderTarget(current);
    }
    this.renders++;
    return true;
  }

  /**
   * Whether a mesh may draw into a blended draw's rectangle: a plain mesh whose bounding box is in
   * the narrowed view and whose screen box touches a marked cell. Instanced meshes (the ground,
   * the structures, the sheets), meshes three never culls and boxes reaching behind the camera
   * always may.
   */
  private reachesCover(mesh: THREE.Mesh): boolean {
    if ((mesh as THREE.InstancedMesh).isInstancedMesh || (mesh as THREE.SkinnedMesh).isSkinnedMesh || !mesh.frustumCulled) return true;
    const geometry = mesh.geometry;
    if (!geometry.boundingSphere) geometry.computeBoundingSphere();
    if (!this.frustum.intersectsObject(mesh)) return false;
    if (!geometry.boundingBox) geometry.computeBoundingBox();
    const b = geometry.boundingBox!;
    const m = this.toClip.multiplyMatrices(this.viewProj, mesh.matrixWorld);
    const v = this.corner;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (let c = 0; c < 8; c++) {
      v.set(c & 1 ? b.max.x : b.min.x, c & 2 ? b.max.y : b.min.y, c & 4 ? b.max.z : b.min.z, 1).applyMatrix4(m);
      if (v.w <= 1e-6) return true;
      const x = v.x / v.w;
      const y = v.y / v.w;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
    return this.cover.hits(x0, y0, x1, y1);
  }

  /**
   * `camera`, narrowed to the part of the view between (u0, v0) and (u1, v1) (0..1 from the bottom
   * left), on the pass's layer.
   */
  private cropCamera(camera: THREE.Camera, u0: number, v0: number, u1: number, v1: number): THREE.Camera {
    const c = this.areaCamera;
    camera.updateMatrixWorld();
    c.matrixWorldAutoUpdate = false;
    c.matrixWorld.copy(camera.matrixWorld);
    c.matrixWorldInverse.copy(camera.matrixWorldInverse);
    // Clip space x' = sx x + tx w maps NDC (2 u0 - 1 .. 2 u1 - 1) onto -1 .. 1 (and y likewise).
    const sx = 1 / (u1 - u0);
    const sy = 1 / (v1 - v0);
    this.crop.set(sx, 0, 0, sx * (1 - u0 - u1), 0, sy, 0, sy * (1 - v0 - v1), 0, 0, 1, 0, 0, 0, 0, 1);
    c.projectionMatrix.multiplyMatrices(this.crop, camera.projectionMatrix);
    c.projectionMatrixInverse.copy(c.projectionMatrix).invert();
    c.layers.set(SHADE_LAYER);
    return c;
  }

  dispose(): void {
    this.target.dispose();
    this.unknown.dispose();
    this.raw.dispose();
    for (const m of this.palShades) m?.dispose();
  }
}
