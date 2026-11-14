// The C's translucency, ported to the GPU (DECISIONS.md D174). OpenTyrian blends background 2
// (draw_background_2_blend, TYRIAN's ice clouds) and explosions (blit_sprite2_blend) per palette
// index, not by opacity:
//
//   *pixels = (((*data & 0x0f) + (*pixels & 0x0f)) / 2) | (*data & 0xf0);     // src/sprite.c
//
// The result keeps the sprite's palette bank (its colour ramp: hue, and for the fire ramp also how
// red it gets as it darkens) and takes the average of the two values (shades 0..15). Over dark
// ground a cloud stays cloud-blue and a fireball goes down its ramp to crimson; an alpha blend
// instead mixed in the ground's colour (green clouds, orange fire).
//
// Here: the frame drawn so far is copied (UnderGrab) just before the blended layers, at hooks in
// three.js's translucent list (like the outline pass, outlineHook.ts), and the blended materials
// read it under each fragment. A colour's shade within a bank is found by its brightness along the
// live palette's ramp for that bank (fractional, so painted art stays smooth; precomputed per palette
// as a 256 x 16 lookup, ShadeLut).
//
// The shade of what's underneath is the terrain's own where it can be (underShade.ts, D204): before
// the frame, the ground layers draw their palette shade (the tile's low nibble; for HD paintings their
// unlit brightness along the original tile's banks) into a target of their own, with the models'
// palette shades over them. That is the C's `*pixels & 0x0f`. Elsewhere (a material with no palette
// index, the sheets' own output under an explosion) it is guessed from the lit frame copy: the shade in the bank of its
// nearest palette colour (PaletteTexture's indexLut). The output is the ramp's colour at the averaged
// shade, unlit, through the smoothies' hue (screenHue.ts) like any palette index.

import * as THREE from "three";
import { PALETTE_LUT_SIZE } from "./paletteTexture";

const L = PALETTE_LUT_SIZE;
/** Brightness steps of the shade lookup. */
const SHADE_BINS = 256;

const srgbToLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
/** hbLum on an sRGB byte triple. */
const lumOf = (r: number, g: number, b: number) =>
  (0.2126 * srgbToLinear(r / 255) + 0.7152 * srgbToLinear(g / 255) + 0.0722 * srgbToLinear(b / 255)) ** (1 / 2.2);

/**
 * The shade (0..15, fractional) along a bank's ramp that has brightness `lum`, from the ramp's 16
 * brightnesses (`lums`, hbLum of each entry, from `at`): piecewise linear between the entries, 0 below
 * the first, 15 above the brightest (a ramp that dips is read as if it didn't).
 */
export function rampShade(lums: ArrayLike<number>, at: number, lum: number): number {
  let prev = lums[at];
  if (lum <= prev) return 0;
  for (let i = 1; i < 16; i++) {
    const cur = lums[at + i];
    if (lum <= cur) return i - 1 + Math.min(1, Math.max(0, (lum - prev) / Math.max(cur - prev, 1e-4)));
    prev = Math.max(prev, cur);
  }
  return 15;
}

/** hbLum of each of a palette's 256 entries (sRGB RGBA bytes). */
export function paletteLums(palette: ArrayLike<number>): Float32Array {
  const out = new Float32Array(256);
  for (let i = 0; i < 256; i++) out[i] = lumOf(palette[i * 4], palette[i * 4 + 1], palette[i * 4 + 2]);
  return out;
}

/** rampShade for every bank and SHADE_BINS brightnesses, as a texture (shade / 15), rebuilt when the palette changes. */
export class ShadeLut {
  readonly texture: THREE.DataTexture;
  private readonly data = new Uint8Array(SHADE_BINS * 16);
  private version = -1;

  constructor() {
    this.texture = new THREE.DataTexture(this.data, SHADE_BINS, 16, THREE.RedFormat, THREE.UnsignedByteType);
    this.texture.magFilter = this.texture.minFilter = THREE.LinearFilter;
    this.texture.generateMipmaps = false;
    this.texture.needsUpdate = true;
  }

  /** Rebuild from a palette (256 RGBA bytes) if `version` changed; returns whether it did. */
  update(palette: ArrayLike<number>, version: number): boolean {
    if (version === this.version) return false;
    this.version = version;
    const lums = paletteLums(palette);
    for (let b = 0; b < 16; b++) {
      for (let i = 0; i < SHADE_BINS; i++) {
        this.data[b * SHADE_BINS + i] = Math.round((rampShade(lums, b * 16, i / (SHADE_BINS - 1)) / 15) * 255);
      }
    }
    this.texture.needsUpdate = true;
    return true;
  }
}

/**
 * GLSL for reading shades off the live palette's ramps: needs `paletteMap` (the live palette); declares
 * the shade lookup's uniform (UnderGrab.uniforms.blendShadeLut).
 */
export const HB_SHADE_PARS = /* glsl */ `
uniform sampler2D blendShadeLut;   // ShadeLut: (brightness, bank) -> shade / 15
vec3 hbPalette(float index) {
  return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb;
}
// Brightness of a linear colour, as the art's palette effects measure it (spriteArtLayer.ts).
float hbLum(vec3 lin) {
  return pow(max(dot(lin, vec3(0.2126, 0.7152, 0.0722)), 0.0), 1.0 / 2.2);
}
// The shade (0..15, fractional) along bank's ramp (bank = hue * 16) that has brightness lum.
float hbShade(float bank, float lum) {
  vec2 uv = vec2((clamp(lum, 0.0, 1.0) * ${SHADE_BINS - 1}.0 + 0.5) / ${SHADE_BINS}.0, (floor(bank / 16.0 + 0.5) + 0.5) / 16.0);
  return texture2D(blendShadeLut, uv).r * 15.0;
}
// The live palette's colour (linear) at a fractional shade of a bank's ramp.
vec3 hbRamp(float bank, float shade) {
  float v = clamp(shade, 0.0, 15.0);
  float lo = min(floor(v), 14.0);
  return mix(hbPalette(bank + lo), hbPalette(bank + lo + 1.0), v - lo);
}
`;

/**
 * GLSL for the blended materials. Needs `paletteMap` (the live palette) and SCREEN_HUE_PARS
 * declared before it; declares the grab's, the terrain shades' and the nearest-index lookup's
 * uniforms (UnderGrab.uniforms).
 */
export const HUE_BLEND_PARS = /* glsl */ `
uniform sampler2D blendUnder;      // the frame so far (UnderGrab)
uniform vec2 blendUnderSize;       // its size in pixels
uniform float blendUnderLinear;    // 1: it holds linear colour (a render target); 0: sRGB (the canvas)
uniform sampler2D blendUnderLut;   // PaletteTexture.indexLut: sRGB cube cell -> nearest raw index
uniform sampler2D blendShade;      // UnderShadePass: r = the terrain's own shade / 15, g = 1 where known, b = under a sheet
uniform float blendShadeOn;        // 1: blendShade holds this frame's terrain shades
uniform float blendShadeSheets;    // 1: this copy was made before the sheets (their marks don't count)
${HB_SHADE_PARS}
// The shade of the frame under this fragment. The terrain's own palette shade where nothing else
// covers it (the C's *pixels & 0x0f, D204); otherwise guessed from the lit frame copy, in the bank of
// its nearest palette colour.
float hbUnderShade() {
  if (blendShadeOn > 0.5) {
    vec4 own = texelFetch(blendShade, ivec2(gl_FragCoord.xy), 0);
    if (own.g > 0.5 && (own.b < 0.5 || blendShadeSheets > 0.5)) return own.r * 15.0;
  }
  vec3 c = texture2D(blendUnder, gl_FragCoord.xy / blendUnderSize).rgb;
  vec3 s = clamp(c, 0.0, 1.0);
  vec3 lin = s;
  if (blendUnderLinear > 0.5) s = mix(1.055 * pow(s, vec3(1.0 / 2.4)) - 0.055, s * 12.92, step(s, vec3(0.0031308)));
  else lin = mix(pow((s + 0.055) / 1.055, vec3(2.4)), s / 12.92, step(s, vec3(0.04045)));
  ivec3 q = clamp(ivec3(s * ${L}.0), 0, ${L - 1});
  float index = floor(texelFetch(blendUnderLut, ivec2(q.r + ${L} * (q.b & 7), q.g + ${L} * (q.b >> 3)), 0).r * 255.0 + 0.5);
  return hbShade(floor(index / 16.0) * 16.0, hbLum(lin));
}
// blit_sprite2_blend: bank's colour at the mean of the two shades (linear RGB), through the
// smoothies' hue at the draw's height.
vec3 hbColor(float bank, float srcShade, float underShade, float height, inout float water) {
  float v = clamp(0.5 * (srcShade + underShade), 0.0, 15.0);
  float lo = min(floor(v), 14.0);
  float i0 = screenHueIndex(bank + lo, height, water);
  float i1 = screenHueIndex(bank + lo + 1.0, height, water);
  return mix(hbPalette(i0), hbPalette(i1), v - lo);
}
`;

/** Where the grabs sit among the translucent draws (their renderOrder). */
export const UNDER_GRAB_ORDER = {
  /** After the outline pass (-1.5) and the depth-writing translucent draws; before the blend sheets (-1). */
  sheets: -1.25,
  /** Just before the explosions' flat art (SPRITE_ART_ORDER + Pass.Explosions / 100, its stencil setter 0.001 earlier). */
  explosions: -1 + 15 / 100 - 0.002,
  /** Before background2over 2's sheets (1), after the explosions and effects drawn under them. */
  top: 0.999,
};

/**
 * A screen area in normalized device coordinates (-1..1), grown by `add`. Empty while x0 > x1.
 */
export class NdcRect {
  x0 = Infinity;
  y0 = Infinity;
  x1 = -Infinity;
  y1 = -Infinity;

  clear(): void {
    this.x0 = this.y0 = Infinity;
    this.x1 = this.y1 = -Infinity;
  }

  get empty(): boolean {
    return this.x0 > this.x1;
  }

  /** Whether the two overlap, or come within `slack` of each other. */
  near(o: NdcRect, slack: number): boolean {
    return !this.empty && !o.empty && this.x0 <= o.x1 + slack && o.x0 <= this.x1 + slack && this.y0 <= o.y1 + slack && o.y0 <= this.y1 + slack;
  }

  /** Grow to cover `o` too. */
  union(o: NdcRect): void {
    if (o.empty) return;
    this.add(o.x0, o.y0);
    this.add(o.x1, o.y1);
  }

  add(x: number, y: number): void {
    if (x < this.x0) this.x0 = x;
    if (x > this.x1) this.x1 = x;
    if (y < this.y0) this.y0 = y;
    if (y > this.y1) this.y1 = y;
  }
}

/** Pixels added round the copied area (camera motion within a frame, soft edges). */
const GRAB_MARGIN = 8;

/**
 * The pixel box [x0, y0, x1, y1) of a w x h target that `area` covers, GRAB_MARGIN pixels bigger
 * each side; all of it if `area` is omitted or empty.
 */
export function areaPixels(area: NdcRect | undefined, w: number, h: number): [number, number, number, number] {
  if (!area || area.empty) return [0, 0, w, h];
  return [
    Math.max(0, Math.floor(((area.x0 + 1) / 2) * w) - GRAB_MARGIN),
    Math.max(0, Math.floor(((area.y0 + 1) / 2) * h) - GRAB_MARGIN),
    Math.min(w, Math.ceil(((area.x1 + 1) / 2) * w) + GRAB_MARGIN),
    Math.min(h, Math.ceil(((area.y1 + 1) / 2) * h) + GRAB_MARGIN),
  ];
}

/**
 * A copy of the frame drawn so far, shared by every hue-blended material through `uniforms`.
 * capture() copies the current target (the canvas, or the screen filters' multisampled render
 * target) with blitFramebuffer into a single-sample target of the same texel type, only the area
 * the blended draws cover. Each copy ends the GPU's render pass for a moment (a tiler stores and
 * reloads the frame), so a frame copies at most where it needs to: before the sheets and before the
 * explosions, when there are any.
 */
export class UnderGrab {
  readonly uniforms: {
    blendUnder: { value: THREE.Texture | null };
    blendUnderSize: { value: THREE.Vector2 };
    blendUnderLinear: { value: number };
    blendUnderLut: { value: THREE.Texture };
    blendShadeLut: { value: THREE.Texture };
    blendShade: { value: THREE.Texture };
    blendShadeOn: { value: number };
    blendShadeSheets: { value: number };
  };
  /** The shade lookup the materials read; update it from the palette each frame (DrawListRenderer). */
  readonly shades = new ShadeLut();
  private targetCopy: THREE.WebGLRenderTarget | null = null;
  private readonly size = new THREE.Vector2();
  /** Captures made (for tests and the harness). */
  captures = 0;

  constructor(lut: THREE.Texture) {
    const blank = new THREE.DataTexture(new Uint8Array([0, 0, 0, 255]), 1, 1);
    blank.needsUpdate = true;
    this.uniforms = {
      blendUnder: { value: blank },
      blendUnderSize: { value: new THREE.Vector2(1, 1) },
      blendUnderLinear: { value: 0 },
      blendUnderLut: { value: lut },
      blendShadeLut: { value: this.shades.texture },
      blendShade: { value: blank },
      blendShadeOn: { value: 0 },
      blendShadeSheets: { value: 1 },
    };
  }

  /**
   * Copy `area` (all of it if omitted) of the current target. `beforeSheets`: the copy the background-2
   * sheets read, made before any of them is drawn; a later copy has them in it, so the terrain shades
   * they cover don't count there (underShade.ts).
   */
  capture(renderer: THREE.WebGLRenderer, area?: NdcRect, beforeSheets = true): void {
    const target = renderer.getRenderTarget();
    if (target) this.captureTarget(renderer, target, area);
    else this.captureCanvas(renderer, area);
    this.uniforms.blendShadeSheets.value = beforeSheets ? 1 : 0;
    this.captures++;
  }

  private captureCanvas(renderer: THREE.WebGLRenderer, area?: NdcRect): void {
    renderer.getDrawingBufferSize(this.size);
    const w = Math.max(1, Math.floor(this.size.x));
    const h = Math.max(1, Math.floor(this.size.y));
    const copy = this.copyTarget(renderer, w, h, THREE.UnsignedByteType);
    this.blit(renderer, null, copy, w, h, area);
    this.uniforms.blendUnderLinear.value = 0;
  }

  private captureTarget(renderer: THREE.WebGLRenderer, target: THREE.WebGLRenderTarget, area?: NdcRect): void {
    const w = target.width;
    const h = target.height;
    const copy = this.copyTarget(renderer, w, h, target.texture.type);
    const src = renderer.properties.get(target) as { __webglMultisampledFramebuffer?: WebGLFramebuffer; __webglFramebuffer?: WebGLFramebuffer };
    const from = src.__webglMultisampledFramebuffer ?? src.__webglFramebuffer;
    if (!from) return;
    this.blit(renderer, from, copy, w, h, area);
    this.uniforms.blendUnderLinear.value = 1;
  }

  /** The single-sample target the copy goes to, at this size and texel type. */
  private copyTarget(renderer: THREE.WebGLRenderer, w: number, h: number, type: THREE.TextureDataType): THREE.WebGLRenderTarget {
    let copy = this.targetCopy;
    if (!copy || copy.width !== w || copy.height !== h || copy.texture.type !== type) {
      copy?.dispose();
      copy = this.targetCopy = new THREE.WebGLRenderTarget(w, h, {
        type,
        minFilter: THREE.NearestFilter,
        magFilter: THREE.NearestFilter,
        depthBuffer: false,
        stencilBuffer: false,
        generateMipmaps: false,
      });
      renderer.initRenderTarget(copy);
    }
    return copy;
  }

  /** Copy the current colour buffer of `from` (null: the canvas) into `copy` (resolving multisampling). */
  private blit(renderer: THREE.WebGLRenderer, from: WebGLFramebuffer | null, copy: THREE.WebGLRenderTarget, w: number, h: number, area?: NdcRect): void {
    const gl = renderer.getContext() as WebGL2RenderingContext;
    const dst = (renderer.properties.get(copy) as { __webglFramebuffer?: WebGLFramebuffer }).__webglFramebuffer;
    if (!dst) return;
    const [x0, y0, x1, y1] = areaPixels(area, w, h);
    if (x1 <= x0 || y1 <= y0) return;
    const state = renderer.state;
    state.bindFramebuffer(gl.READ_FRAMEBUFFER, from);
    state.bindFramebuffer(gl.DRAW_FRAMEBUFFER, dst);
    gl.blitFramebuffer(x0, y0, x1, y1, x0, y0, x1, y1, gl.COLOR_BUFFER_BIT, gl.NEAREST);
    state.bindFramebuffer(gl.READ_FRAMEBUFFER, null);
    state.bindFramebuffer(gl.DRAW_FRAMEBUFFER, from);
    this.uniforms.blendUnder.value = copy.texture;
    this.uniforms.blendUnderSize.value.set(w, h);
  }

  dispose(): void {
    this.targetCopy?.dispose();
  }
}

/**
 * An empty, never-drawn mesh in the translucent list at `order` that captures the frame once when
 * three.js reaches it, if armed for this frame (`arm`). Other renders of the scene (the screen
 * filters' mask, an effects-only redraw) pass it unarmed.
 */
export class UnderGrabHook extends THREE.Mesh<THREE.BufferGeometry, THREE.MeshBasicMaterial> {
  private armed = false;
  /** Where this frame's readers are on screen; DrawListRenderer grows it while it lays the frame out. */
  readonly area = new NdcRect();

  constructor(private readonly grab: UnderGrab, order: number, mainRenderOnly = false, private readonly beforeSheets = false) {
    super(
      new THREE.BufferGeometry(),
      new THREE.MeshBasicMaterial({
        name: "under_grab_hook",
        transparent: true,
        colorWrite: false,
        depthTest: false,
        depthWrite: false,
        userData: { outlineParameters: { visible: false } },
      }),
    );
    this.name = "under-grab";
    // The outline pass's own render of the scene (outlineEffect.js) runs inside the main render at
    // OUTLINE_ORDER and reaches the hooks too. A copy made there (it uses up the arming) has the
    // frame as it was at OUTLINE_ORDER, the main render's state below the sheets' hook (so the
    // sheets' copy may be made there), but not the blend sheets and flat art the explosions' and
    // the top sheets' copies need: those hooks are left out of it (`mainRenderOnly`, D193).
    if (mainRenderOnly) this.userData.outlineSkip = true;
    this.renderOrder = order;
    this.frustumCulled = false;
    this.castShadow = false;
    this.receiveShadow = false;
    this.onBeforeRender = (renderer) => {
      if (!this.armed) return;
      this.armed = false;
      this.grab.capture(renderer, this.area, this.beforeSheets);
    };
  }

  /** Capture `area` at the next render that reaches the hook, if anything was added to it. */
  arm(): void {
    this.armed = !this.area.empty;
  }
}

/**
 * The palette bank (hue << 4) most of a sprite's or tile's opaque pixels are in (index > 0 for tiles);
 * with `byShade`, each pixel counted by its shade + 1, so bright pixels outweigh a dark backing (D181).
 */
export function dominantBank(pixels: ArrayLike<number>, skipZero: boolean, byShade = false): number {
  const counts = new Array<number>(16).fill(0);
  for (let i = 0; i < pixels.length; i++) {
    const p = pixels[i];
    if (p < 0 || (skipZero && p === 0)) continue;
    counts[(p >> 4) & 15] += byShade ? (p & 15) + 1 : 1;
  }
  let best = 0;
  for (let b = 1; b < 16; b++) if (counts[b] > counts[best]) best = b;
  return best * 16;
}

/** The share of a tile's pixels a second bank needs to count in topBanks. */
export const SECOND_BANK_SHARE = 0.05;

/**
 * A tile's two main palette banks (hue << 4), by pixel count (index > 0 with `skipZero`): the
 * dominant one (as dominantBank), then the next if at least SECOND_BANK_SHARE of the counted pixels
 * are in it, else the dominant one again. An HD painting's shade is read along them (underShade.ts).
 */
export function topBanks(pixels: ArrayLike<number>, skipZero: boolean): [number, number] {
  const counts = new Array<number>(16).fill(0);
  let total = 0;
  for (let i = 0; i < pixels.length; i++) {
    const p = pixels[i];
    if (p < 0 || (skipZero && p === 0)) continue;
    counts[(p >> 4) & 15]++;
    total++;
  }
  let best = 0;
  for (let b = 1; b < 16; b++) if (counts[b] > counts[best]) best = b;
  let second = best === 0 ? 1 : 0;
  for (let b = 0; b < 16; b++) if (b !== best && counts[b] > counts[second]) second = b;
  if (counts[second] === 0 || counts[second] < SECOND_BANK_SHARE * total) second = best;
  return [best * 16, second * 16];
}
