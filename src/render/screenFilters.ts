// Post-processing for OpenTyrian's screen filters (DECISIONS.md D31): the smoothies (lava, water,
// iced blur, blur), JE_starShowVGA's flipped screen and headlight, and JE_barBright's Zinglon beam.
// The sim records them per tick in drawList.screen (src/sim/smoothies.ts).
//
// The C rewrites the palette indices of the pixels drawn so far, so each filter only touches the
// draw passes before it. The hue half of that happens in the palette materials (screenHue.ts), on
// the real indices. The value half (the lava's wave and smear, the water's ripple, the blurs) is
// done here: the scene is drawn to a render target, and a mask pass draws it again with every
// object's pass height (D5) as its colour, so a filter changes a pixel only when the object on top
// there is from one of its passes. Positions are worked out in game_screen pixels: every draw sits
// on the camera ray through its original screen position (D6), so a pixel's game position is where
// its ray meets the ground, and the C's offsets apply in its units. They are continuous, though: the
// C's waves step by whole pixels per row and 8-pixel chunk, which at output resolution cut the HD
// scene into staircases, so the waves here are sines through the same extremes, read at sub-pixel
// positions (D135). A colour's value is its brightness; a new
// value scales the lit colour, keeping its hue and lighting. Filters that mix with the previous
// frame do so per display frame with the weight, and the offset, that give the C's per-tick blend.
// Nothing here runs while drawList.screen is null.

import * as THREE from "three";
import { CLASSIC_TICK_MS } from "../core/timing";
import { PLAYFIELD_H, PLAYFIELD_SCREEN_X, PLAYFIELD_SCREEN_Y, PLAYFIELD_W, PX_PER_UNIT } from "../game/playfield";
import { Pass, type DrawList } from "../sim/draw";
import type { ScreenFilters, ScreenFilterStage } from "../sim/smoothies";
import { PASS_HEIGHT } from "./passHeights";
import type { PaletteTexture } from "./paletteTexture";
import type { ScreenHue, ScreenHueStage } from "./screenHue";
import { VFX_LAYER } from "./vfx/vfxMode";

/** Classic ticks per second (DECISIONS.md D2): the C runs each filter once a tick. */
const TICK_HZ = 1000 / CLASSIC_TICK_MS;
/** At most 6 filters a frame (iced, lava, water, iced, blur; lava runs once). */
const MAX_STAGES = 6;
const MAX_BARS = 4;

const KIND = { lava: 1, water: 2, iced: 3, blur: 4 } as const;

/** A frame with JE_filterScreen's hue and none of drawList.screen's effects. */
const NO_SCREEN_FILTERS: ScreenFilters = { stages: [], showCode: 0, playerX: 0, playerY: 0, bars: [] };

/** Height between a pass and the next: a filter covers every object below it (D5). */
export function passCeiling(pass: Pass): number {
  const h = PASS_HEIGHT[pass];
  const above = Object.values(PASS_HEIGHT).filter((v) => v > h);
  return above.length ? (h + Math.min(...above)) / 2 : h + 1;
}

/**
 * The weight of the previous frame for a filter that reads it, per display frame of `dt` seconds:
 * the C mixes half of the previous tick's screen in, so after one tick's worth of frames the old
 * picture has faded by half.
 */
export function previousFrameWeight(dt: number): number {
  return Math.pow(0.5, Math.max(0, dt) * TICK_HZ);
}

/** The shader's per-stage uniforms for one frame. */
export function stageUniforms(stages: readonly ScreenFilterStage[], dt: number, historyValid: boolean) {
  const kind = new Array<number>(MAX_STAGES).fill(0);
  const ceiling = new Array<number>(MAX_STAGES).fill(-1);
  const prev = new Array<number>(MAX_STAGES).fill(-1);
  const bank = new Array<number>(MAX_STAGES).fill(-1);
  stages.slice(0, MAX_STAGES).forEach((s, i) => {
    kind[i] = KIND[s.kind];
    ceiling[i] = passCeiling(s.pass);
    // -1: works in place on this frame's pixels; otherwise the previous frame's weight.
    prev[i] = s.temporal ? (historyValid ? previousFrameWeight(dt) : 0) : -1;
    bank[i] = stageBank(s);
  });
  return { kind, ceiling, prev, bank, count: Math.min(stages.length, MAX_STAGES) };
}

/**
 * The palette bank (hue << 4) a filter gives the pixels it covers, or -1 (blur_filter keeps each
 * pixel's own): lava_filter 0x70, iced_blur_filter 0x80, water_filter its hue (backgrnd.c).
 */
export function stageBank(s: ScreenFilterStage): number {
  if (s.kind === "lava") return 0x70;
  if (s.kind === "iced") return 0x80;
  if (s.kind === "water") return s.hue & 0xf0;
  return -1;
}

/** JE_filterScreen's hue as a palette bank (hue << 4), or -1 when it's off (-99). */
export function levelBank(filter: number): number {
  return filter === -99 ? -1 : (filter & 0x0f) << 4;
}

/** The hue changes of a frame's filters, for the palette materials (screenHue.ts). */
export function hueStages(stages: readonly ScreenFilterStage[]): ScreenHueStage[] {
  const out: ScreenHueStage[] = [];
  for (const s of stages) {
    if (s.kind === "lava") out.push({ ceiling: passCeiling(s.pass), hue: 0x7, water: false });
    else if (s.kind === "iced") out.push({ ceiling: passCeiling(s.pass), hue: 0x8, water: false });
    else if (s.kind === "water") out.push({ ceiling: passCeiling(s.pass), hue: (s.hue >> 4) & 0x0f, water: true });
  }
  return out;
}

/** A filter's sideways wave: mean + amplitude * cos(2 pi diw / period), in game_screen pixels. */
export interface Wave {
  mean: number;
  amplitude: number;
  period: number;
}

/** lava_filter's wave, -1..7 px: abs(((diw >> 9) & 15) - 8) - 1, period 16 * 512 (as a sine, D135). */
export const LAVA_WAVE: Wave = { mean: 3, amplitude: 4, period: 16 * 512 };
/** water_filter's wave, -1..3 px: abs(((diw >> 10) & 7) - 4) - 1, period 8 * 1024. */
export const WATER_WAVE: Wave = { mean: 1, amplitude: 2, period: 8 * 1024 };

/** The wave's shift at a (continuous) diw: what the shader computes. */
export function waveAt(w: Wave, diw: number): number {
  return w.mean + w.amplitude * Math.cos((2 * Math.PI * diw) / w.period);
}

const glslWave = (w: Wave) => [w.mean, w.amplitude, w.period].map((v) => v.toFixed(1)).join(", ");

/** Rec. 709 luminance weights (linear RGB). */
const LUMA = [0.2126, 0.7152, 0.0722] as const;
type Rgb = readonly [number, number, number];
const lumaOf = (c: Rgb) => LUMA[0] * c[0] + LUMA[1] * c[1] + LUMA[2] * c[2];
const NEUTRAL_START = 0.8 - 0.04;
const NEUTRAL_DESATURATION = 0.15;
/** neutralInverse holds a displayed peak under this: at 1 the scene colour would be infinite. */
const NEUTRAL_MAX_PEAK = 0.995;

/**
 * A hue filter's colour for a luminance (D191), as the shader's bankAtLuma works it out. The C gives
 * every pixel a filter covers the hue's shade of that pixel's value, so its flat pixels never leave
 * the hue; a model's lighting does (a white sheen, a white light's reflection) unless the hue is
 * given to the lit colour as well. So a covered pixel takes the colour on the hue's own run of 16
 * shades (`bank`: linear RGB as displayed, the level filter's brightness already in) that has its
 * displayed luminance: the levels stay as they are and only the hue changes. Between two shades the
 * colours mix; a shade no brighter than the one before (a run that dips, or shades a level
 * brightness clamped together) is passed over, so the run never folds back. Past either end the end
 * shade is scaled.
 */
export function bankAtLuma(l: number, bank: readonly Rgb[]): [number, number, number] {
  const scaled = (a: Rgb, k: number): [number, number, number] => [a[0] * k, a[1] * k, a[2] * k];
  l = Math.max(l, 0);
  let lo = bank[0];
  let llo = lumaOf(lo);
  if (l <= llo) return llo > 1e-6 ? scaled(lo, l / llo) : [...lo];
  for (let k = 1; k < 16; k++) {
    const hi = bank[k];
    const lhi = lumaOf(hi);
    if (lhi <= llo) continue; // a shade no brighter than the last (a dip, or a brightness's clamp)
    if (l <= lhi) {
      const t = (l - llo) / (lhi - llo);
      return [lo[0] + (hi[0] - lo[0]) * t, lo[1] + (hi[1] - lo[1]) * t, lo[2] + (hi[2] - lo[2]) * t];
    }
    lo = hi;
    llo = lhi;
  }
  return scaled(lo, l / Math.max(llo, 1e-6));
}

/**
 * JE_filterScreen's hue on a lit pixel (D193): its luminance, the hue's direction, and its own
 * saturation along that direction, never less than the hue's shade at that luminance. bankAtLuma
 * alone takes the saturation of the shade the luminance lands on, and the 3D's lighting lifts a
 * palette colour (already the hue's shade: the palette texture holds the filter) up the run to the
 * paler shades, so CAMANIS's lit ice went near white. A pixel already in the hue so keeps its colour
 * (its shade lit, as an unfiltered level shows its colours); a white sheen (no saturation of its
 * own) takes the shade's, and an off-hue colour loses the part across the hue, as under bankAtLuma
 * alone (D191). Colours are linear RGB as displayed; the result stays inside 0..1.
 */
export function hueKeepingChroma(c: Rgb, bank: readonly Rgb[]): [number, number, number] {
  const l = lumaOf(c);
  const r = bankAtLuma(l, bank);
  const dr = [r[0] - l, r[1] - l, r[2] - l];
  const n = Math.hypot(dr[0], dr[1], dr[2]);
  if (n < 1e-6) return r;
  const u = dr.map((v) => v / n);
  const own = (c[0] - l) * u[0] + (c[1] - l) * u[1] + (c[2] - l) * u[2];
  let limit = Infinity;
  for (const v of u) {
    if (v < -1e-6) limit = Math.min(limit, l / -v);
    else if (v > 1e-6) limit = Math.min(limit, Math.max(1 - l, 0) / v);
  }
  const s = Math.max(n, Math.min(own, limit));
  return [l + u[0] * s, l + u[1] * s, l + u[2] * s];
}

/** three's NeutralToneMapping (Khronos PBR Neutral), the canvas's tone mapping (view.ts). */
export function neutralToneMap(c: Rgb, exposure = 1): [number, number, number] {
  let [r, g, b] = [c[0] * exposure, c[1] * exposure, c[2] * exposure];
  const x = Math.min(r, g, b);
  const offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  r -= offset;
  g -= offset;
  b -= offset;
  const peak = Math.max(r, g, b);
  if (peak < NEUTRAL_START) return [r, g, b];
  const d = 1 - NEUTRAL_START;
  const newPeak = 1 - (d * d) / (peak + d - NEUTRAL_START);
  const k = newPeak / peak;
  const w = 1 - 1 / (NEUTRAL_DESATURATION * (peak - newPeak) + 1);
  return [r * k + (newPeak - r * k) * w, g * k + (newPeak - g * k) * w, b * k + (newPeak - b * k) * w];
}

/**
 * The scene colour that neutralToneMap shows as `c` (its peak held under 1): how a colour chosen as
 * displayed goes back into the scene's linear light, which the canvas tone maps.
 */
export function neutralInverse(c: Rgb, exposure = 1): [number, number, number] {
  let out: [number, number, number] = [Math.max(c[0], 0), Math.max(c[1], 0), Math.max(c[2], 0)];
  const peak = Math.min(Math.max(...out), NEUTRAL_MAX_PEAK);
  if (peak >= NEUTRAL_START) {
    const d = 1 - NEUTRAL_START;
    const p = (d * d) / (1 - peak) - d + NEUTRAL_START;
    const w = 1 - 1 / (NEUTRAL_DESATURATION * (p - peak) + 1);
    out = out.map((v) => (Math.max(Math.min(v, peak) - w * peak, 0) / (1 - w)) * (p / peak)) as [number, number, number];
  }
  const y = Math.min(...out);
  const offset = y >= 0.04 ? 0.04 : Math.sqrt(y) / 2.5 - y;
  return out.map((v) => (v + offset) / exposure) as [number, number, number];
}

const QUAD_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`;

/** Shared GLSL: game_screen pixels <-> screen UVs, and colours' values. */
const COMMON = /* glsl */ `
uniform mat4 viewProj;
uniform mat4 invViewProj;
const float PX = ${PX_PER_UNIT.toFixed(1)};
const vec2 ORIGIN = vec2(${(PLAYFIELD_SCREEN_X + PLAYFIELD_W / 2).toFixed(1)}, ${(PLAYFIELD_SCREEN_Y + PLAYFIELD_H / 2).toFixed(1)});

// Where the camera ray through this screen point meets the ground, in game_screen pixels.
vec2 gameAt(vec2 uv) {
  vec4 n = invViewProj * vec4(uv * 2.0 - 1.0, -1.0, 1.0);
  vec4 f = invViewProj * vec4(uv * 2.0 - 1.0, 1.0, 1.0);
  n /= n.w;
  f /= f.w;
  vec3 d = f.xyz - n.xyz;
  vec3 p = n.xyz + d * (-n.y / d.y);
  return p.xz * PX + ORIGIN;
}

vec2 uvAt(vec2 game) {
  vec2 w = (game - ORIGIN) / PX;
  vec4 c = viewProj * vec4(w.x, 0.0, w.y, 1.0);
  return c.xy / c.w * 0.5 + 0.5;
}

// A colour's value, 0..15, as the 16 shades of a palette hue run (sRGB brightness).
float valueOf(vec3 c) {
  float m = max(max(c.r, c.g), c.b);
  return clamp(pow(max(m, 0.0), 1.0 / 2.2) * 15.0, 0.0, 15.0);
}

// The colour with its value changed, its hue kept.
vec3 withValue(vec3 c, float v) {
  float v0 = valueOf(c);
  if (v0 < 0.25) return vec3(pow(clamp(v, 0.0, 15.0) / 15.0, 2.2));
  return c * pow(clamp(v, 0.0, 15.0) / v0, 2.2);
}

// The palette texture (paletteTexture.ts, the level filter folded in), linear when sampled.
uniform sampler2D paletteMap;
vec3 paletteEntry(float index) { return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb; }
float lumaOf(vec3 c) { return dot(c, vec3(${LUMA.join(", ")})); }

// A hue filter's colour for a displayed luminance (bankAtLuma in this file, D191).
vec3 bankAtLuma(float l, float bank) {
  l = max(l, 0.0);
  vec3 lo = paletteEntry(bank);
  float llo = lumaOf(lo);
  if (l <= llo) return llo > 1e-6 ? lo * (l / llo) : lo;
  for (int k = 1; k < 16; k++) {
    vec3 hi = paletteEntry(bank + float(k));
    float lhi = lumaOf(hi);
    if (lhi <= llo) continue;
    if (l <= lhi) return mix(lo, hi, (l - llo) / (lhi - llo));
    lo = hi;
    llo = lhi;
  }
  return lo * (l / max(llo, 1e-6));
}
// JE_filterScreen's hue on a lit pixel (hueKeepingChroma in this file, D193): the hue's direction
// at the pixel's luminance, with the pixel's own saturation along it, at least the shade's.
vec3 hueKeepingChroma(vec3 c, float bank) {
  float l = lumaOf(c);
  vec3 r = bankAtLuma(l, bank);
  vec3 dr = r - vec3(l);
  float n = length(dr);
  if (n < 1e-6) return r;
  vec3 u = dr / n;
  float own = dot(c - vec3(l), u);
  float limit = 1e9;
  for (int i = 0; i < 3; i++) {
    if (u[i] < -1e-6) limit = min(limit, l / -u[i]);
    else if (u[i] > 1e-6) limit = min(limit, max(1.0 - l, 0.0) / u[i]);
  }
  return vec3(l) + u * max(n, min(own, limit));
}

// The canvas's tone mapping (neutralToneMap in this file; off: identity) and its inverse
// (neutralInverse), so a filter can choose a colour as it will be displayed.
uniform float toneExposure; // renderer.toneMappingExposure, or 0 when it isn't Neutral
const float NEUTRAL_START = ${NEUTRAL_START.toFixed(2)};
const float NEUTRAL_DESATURATION = ${NEUTRAL_DESATURATION.toFixed(2)};
vec3 displayed(vec3 c) {
  if (toneExposure <= 0.0) return c;
  c *= toneExposure;
  float x = min(c.r, min(c.g, c.b));
  c -= x < 0.08 ? x - 6.25 * x * x : 0.04;
  float peak = max(c.r, max(c.g, c.b));
  if (peak < NEUTRAL_START) return c;
  float d = 1.0 - NEUTRAL_START;
  float newPeak = 1.0 - d * d / (peak + d - NEUTRAL_START);
  c *= newPeak / peak;
  return mix(c, vec3(newPeak), 1.0 - 1.0 / (NEUTRAL_DESATURATION * (peak - newPeak) + 1.0));
}
vec3 undisplayed(vec3 c) {
  if (toneExposure <= 0.0) return c;
  c = max(c, 0.0);
  float peak = min(max(c.r, max(c.g, c.b)), ${NEUTRAL_MAX_PEAK});
  if (peak >= NEUTRAL_START) {
    float d = 1.0 - NEUTRAL_START;
    float p = d * d / (1.0 - peak) - d + NEUTRAL_START;
    float w = 1.0 - 1.0 / (NEUTRAL_DESATURATION * (p - peak) + 1.0);
    c = max(min(c, vec3(peak)) - w * peak, 0.0) / (1.0 - w) * (p / peak);
  }
  float y = min(c.r, min(c.g, c.b));
  return (c + (y >= 0.04 ? 0.04 : sqrt(y) / 2.5 - y)) / toneExposure;
}
// A scene colour's luminance as displayed, gamma-encoded (0..1): the filters' smear measure (D191).
float shownLuma(vec3 c) { return pow(clamp(lumaOf(displayed(c)), 0.0, 1.0), 1.0 / 2.2); }
// The scene colour a filter's hue shows at gamma-encoded displayed luminance v.
vec3 hueAt(float v, float bank) { return undisplayed(bankAtLuma(pow(max(v, 0.0), 2.2), bank)); }
`;

const FILTER_FRAGMENT = /* glsl */ `
precision highp float;
precision highp int;
${COMMON}
uniform sampler2D sceneMap;
uniform sampler2D prevMap;
uniform sampler2D maskMap;
uniform int stageCount;
uniform int stageKind[${MAX_STAGES}];
uniform float stageCeiling[${MAX_STAGES}];
uniform float stagePrev[${MAX_STAGES}];
uniform float stageBank[${MAX_STAGES}];
varying vec2 vUv;

float heightAt(vec2 uv) { return texture2D(maskMap, uv).r; }

// This frame's pixel at a game position, if it's from the filter's passes; otherwise the fallback
// (the C's buffer only holds what was drawn before the filter). Alpha < 1 marks the water's pixels.
vec4 below(vec2 game, float ceiling, vec4 fallback) {
  vec2 uv = uvAt(game);
  return heightAt(uv) < ceiling ? texture2D(sceneMap, uv) : fallback;
}

vec3 previous(vec2 game) { return texture2D(prevMap, uvAt(game)).rgb; }

bool isWater(vec4 c) { return c.a < 0.75; }

// The waves are the C's (diw, the 8-pixel chunk's offset in the 320-wide screen, which it counts
// down from the bottom-right, through a triangle table), but read continuously: the C's steps are
// whole pixels per row and chunk, which at output resolution cut the HD scene into staircases. A
// sine through the same extremes and period keeps the wobble's size and shape (D135).
const float TAU = 6.2831853;
float diwAt(vec2 g) { return 320.0 * g.y + g.x + 4.0; }
float wave(vec2 g, vec3 w) { return w.x + w.y * cos(TAU * diwAt(g) / w.z); }
float lavaWave(vec2 g) { return wave(g, vec3(${glslWave(LAVA_WAVE)})); }
float waterWave(vec2 g) { return wave(g, vec3(${glslWave(WATER_WAVE)})); }

// water_filter leaves grey and cloud-blue pixels alone, a choice the C makes per original pixel. An
// HD painting's exempt texels (its darkest, near-grey ones, D114) can be much smaller than that, and
// showed as black specks in the water. So a non-water pixel counts as water when there is water
// round it a third of an original pixel away (3 of 4 points), with those points' colour as its hue.
// Exempt areas an original pixel wide (grey bricks, the dark edges of the shores) stay exempt.
bool exemptSpeck(vec2 p, float ceiling, out vec3 water) {
  water = vec3(0.0);
  float n = 0.0;
  for (int i = 0; i < 4; i++) {
    vec2 o = i < 2 ? vec2(i == 0 ? 0.35 : -0.35, 0.0) : vec2(0.0, i == 2 ? 0.35 : -0.35);
    vec4 s = below(p + o, ceiling, vec4(0.0, 0.0, 0.0, 1.0));
    if (isWater(s)) {
      water += s.rgb;
      n += 1.0;
    }
  }
  water /= max(n, 1.0);
  return n > 2.5;
}

void main() {
  vec4 c = texture2D(sceneMap, vUv);
  float h = heightAt(vUv);
  vec2 g = gameAt(vUv);
  for (int i = 0; i < ${MAX_STAGES}; i++) {
    if (i >= stageCount) break;
    float ceiling = stageCeiling[i];
    if (h >= ceiling) continue;
    float a = stagePrev[i];
    int kind = stageKind[i];
    float bank = stageBank[i];
    if (kind == 1) {
      // lava_filter: value = (2 * src[x + wave] + dst below + dst above) / 4, hue 0x70. The
      // materials already take the hue's indices; hueAt gives it to their lighting too, so the
      // value is measured as the displayed luminance that hueAt keeps (D191).
      float wave = lavaWave(g);
      vec2 p = g + vec2(wave, 0.0);
      vec4 s = below(p, ceiling, c);
      float v;
      if (a >= 0.0) {
        // The previous frame, as the C reads its last tick's screen: shifted by the wave and
        // spread a row up and down per tick. This frame is a fraction t of a tick, so the history
        // moves t of the wave and sqrt(t) of a row (the spread adds up as a variance): the smear's
        // length doesn't depend on the frame rate (the C's averages twice the wave).
        float t = a > 0.0 ? min(1.0, -log2(a)) : 1.0;
        vec2 q = g + vec2(t * wave, 0.0);
        vec2 d = vec2(0.0, sqrt(t));
        v = mix(shownLuma(s.rgb), 0.5 * (shownLuma(previous(q + d)) + shownLuma(previous(q - d))), a);
      } else {
        v = 0.5 * shownLuma(s.rgb) + 0.25 * (shownLuma(below(p + vec2(0.0, 1.0), ceiling, s).rgb) + shownLuma(below(p - vec2(0.0, 1.0), ceiling, s).rgb));
      }
      c.rgb = hueAt(v, bank);
    } else if (kind == 2) {
      // water_filter, bottom row up: dst = hue | (src value + dst[below, x + wave] value) / 2 for the
      // pixels it recoloured. The rows below are this frame's results, so the value is a running
      // half-and-half down the column, as far as the water goes (six rows here). The taps stay
      // whole rows apart: half-row taps turned the HD jungle into streaks the C doesn't draw.
      vec3 unused;
      if (isWater(c) || exemptSpeck(g, ceiling, unused)) {
        float acc = 0.5 * shownLuma(c.rgb);
        float w = 0.5;
        vec2 p = g;
        for (int k = 0; k < 6; k++) {
          p += vec2(waterWave(p), 1.0);
          vec4 s = below(p, ceiling, vec4(c.rgb, 1.0));
          float vk = shownLuma(s.rgb);
          if (k == 5 || !(isWater(s) || exemptSpeck(p, ceiling, unused))) {
            acc += w * vk;
            break;
          }
          acc += w * 0.5 * vk;
          w *= 0.5;
        }
        c.rgb = hueAt(acc, bank); // the water's hue, also on an exempt speck (D191)
      }
    } else if (kind == 3 || kind == 4) {
      // iced_blur_filter and blur_filter: value = (src + dst) / 2, this pixel's hue: ice blue for
      // the iced one (its lighting too, through hueAt, D191), its own for the blur. In place they
      // change nothing more.
      if (bank >= 0.0) c.rgb = hueAt(a >= 0.0 ? mix(shownLuma(c.rgb), shownLuma(previous(g)), a) : shownLuma(c.rgb), bank);
      else if (a >= 0.0) c.rgb = withValue(c.rgb, mix(valueOf(c.rgb), valueOf(previous(g)), a));
    }
  }
  gl_FragColor = vec4(c.rgb, 1.0);
}
`;

const PRESENT_FRAGMENT = /* glsl */ `
precision highp float;
${COMMON}
uniform sampler2D sourceMap;
uniform int showCode;
uniform vec2 player;
uniform int barCount;
uniform vec4 bars[${MAX_BARS}];
uniform float levelBank; // JE_filterScreen's hue << 4, or -1
varying vec2 vUv;

// The playfield in game_screen pixels: what JE_filterScreen covers.
bool inPlayfield(vec2 g) {
  return g.x >= ${PLAYFIELD_SCREEN_X.toFixed(1)} && g.x < ${(PLAYFIELD_SCREEN_X + PLAYFIELD_W).toFixed(1)} && g.y >= ${PLAYFIELD_SCREEN_Y.toFixed(1)} && g.y < ${(PLAYFIELD_SCREEN_Y + PLAYFIELD_H).toFixed(1)};
}

// showHeadlight (backgrnd.c L855-988): a cone of light up from the ship, the rest at a quarter.
float headlight(vec2 g, float v) {
  float col = g.x - 24.0;
  float row = g.y;
  float lx = (player.x - 17.0) - (player.y + 12.0) + 1.0 + row;
  float rx = (player.x - 17.0) + (player.y + 12.0) - row;
  float dark = v / 4.0;
  if (lx > rx + 1.0) return dark;
  if (col < lx - 5.0) return dark;
  if (col < lx) return (v + 3.0 * (6.0 - (lx - col))) / 4.0;
  if (col < rx) return v;
  if (col < rx + 5.0) return (v + 3.0 * (rx + 5.0 - col)) / 4.0;
  return dark;
}

void main() {
  vec2 g = gameAt(vUv);
  vec2 src = g;
  vec2 uv = vUv;
  // showFlipped: the 184 rows upside down.
  if (showCode == 1) {
    src = vec2(g.x, 184.0 - g.y);
    uv = uvAt(src);
  }
  vec3 c = texture2D(sourceMap, uv).rgb;

  // JE_barBright: +2 value per rectangle.
  float add = 0.0;
  for (int i = 0; i < ${MAX_BARS}; i++) {
    if (i >= barCount) break;
    vec4 b = bars[i];
    if (src.x >= b.x && src.x < b.z + 1.0 && src.y >= b.y && src.y < b.w + 1.0) add += 2.0;
  }
  if (add > 0.0) c = withValue(c, valueOf(c) + add);

  if (showCode == 2) c = withValue(c, headlight(g, valueOf(c)));

  gl_FragColor = vec4(c, 1.0);
  #include <tonemapping_fragment>
  // JE_filterScreen's hue: every playfield pixel takes it, lighting and effects too (D191), after
  // the tone mapping (the palette texture already holds it for whatever looks colours up). A pixel
  // keeps its own saturation along the hue, so lit shades don't pale up the run (D193).
  if (levelBank >= 0.0 && inPlayfield(src)) gl_FragColor.rgb = hueKeepingChroma(gl_FragColor.rgb, levelBank);
  #include <colorspace_fragment>
}
`;

const MASK_VERTEX = /* glsl */ `
uniform float objectHeight;
varying float vHeight;
void main() {
  mat4 m = modelMatrix;
  #ifdef USE_INSTANCING
    m = m * instanceMatrix;
  #endif
  vHeight = objectHeight > -1000.0 ? objectHeight : m[3][1];
  gl_Position = projectionMatrix * viewMatrix * m * vec4(position, 1.0);
}
`;

const MASK_FRAGMENT = /* glsl */ `
varying float vHeight;
void main() {
  gl_FragColor = vec4(vHeight, 0.0, 0.0, 1.0);
}
`;

/**
 * The flat sprite art (spriteArtLayer.ts, D42) places its quads from instance attributes the mask
 * material doesn't read, so drawn with it the shots and enemies in flat art were missing from the
 * mask, and the filters wobbled and smeared them as if they were ground (ASSASSIN's beam). The mask
 * draws them again with this: the art's quad, its texels' cut-out, its pass height.
 */
const ART_MASK_VERTEX = /* glsl */ `
attribute vec3 aOrigin;
attribute vec2 aSize;
attribute vec4 aUv;
attribute vec4 aFx;
varying vec2 vUv;
varying vec4 vUvRect;
varying float vAlpha;
varying float vHeight;
void main() {
  vec3 p = aOrigin + vec3(position.x * aSize.x, 0.0, position.z * aSize.y);
  vUv = mix(aUv.xy, aUv.zw, position.xz);
  vUvRect = aUv;
  vAlpha = aFx.w;
  vHeight = aOrigin.y;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.0);
}
`;

const ART_MASK_FRAGMENT = /* glsl */ `
uniform sampler2D map;
varying vec2 vUv;
varying vec4 vUvRect;
varying float vAlpha;
varying float vHeight;
void main() {
  vec2 halfTexel = 0.5 / vec2(textureSize(map, 0));
  float a = texture2D(map, clamp(vUv, vUvRect.xy + halfTexel, vUvRect.zw - halfTexel)).a;
  if (a * vAlpha < 0.004 || a < 0.5) discard;
  gl_FragColor = vec4(vHeight, 0.0, 0.0, 1.0);
}
`;

/** The camera layer the mask's flat-art draw uses for a moment; nothing else is on it. */
const ART_MASK_LAYER = 30;

/** Whether an object is a batch of the flat sprite art (spriteArtLayer.ts). */
function isFlatArt(o: THREE.Object3D): o is THREE.Mesh {
  const m = o as THREE.Mesh;
  return m.isMesh === true && m.name === "sprite-art" && m.geometry.getAttribute("aOrigin") !== undefined && m.geometry.getAttribute("aUv") !== undefined;
}

const renderTarget = (samples: number) =>
  new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    depthBuffer: true,
    stencilBuffer: true, // explosions draw through a stencil (spriteArtLayer.ts)
    samples,
  });

/**
 * Draws the scene through the screen filters when a draw list asks for any. `render` replaces the
 * plain scene render for those frames.
 */
export class ScreenFilterPass {
  private state: ScreenFilters | null = null;
  /** JE_filterScreen's hue as a bank (levelBank), or -1. */
  private levelBank = -1;
  private prevPlayer = { x: 0, y: 0 };
  private readonly screenHue: ScreenHue;

  private readonly sceneTarget: THREE.WebGLRenderTarget;
  private readonly maskTarget = renderTarget(0);
  private history = [renderTarget(0), renderTarget(0)];
  private historyValid = false;
  private lastTime = performance.now();

  private readonly quadScene = new THREE.Scene();
  private readonly quadCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly quad: THREE.Mesh;
  private readonly filterMaterial: THREE.ShaderMaterial;
  private readonly presentMaterial: THREE.ShaderMaterial;
  private readonly maskMaterial: THREE.ShaderMaterial;
  private readonly artMaskMaterials = new WeakMap<THREE.Texture, THREE.ShaderMaterial>();
  private readonly size = new THREE.Vector2();
  private readonly viewProj = new THREE.Matrix4();
  private readonly invViewProj = new THREE.Matrix4();

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    palette: PaletteTexture,
  ) {
    this.sceneTarget = renderTarget(Math.min(4, renderer.capabilities.maxSamples));
    this.screenHue = palette.screenHue;

    const common = {
      viewProj: { value: this.viewProj },
      invViewProj: { value: this.invViewProj },
      paletteMap: { value: palette.texture ?? null },
      toneExposure: { value: 0 },
    };
    this.filterMaterial = new THREE.ShaderMaterial({
      vertexShader: QUAD_VERTEX,
      fragmentShader: FILTER_FRAGMENT,
      uniforms: {
        ...common,
        sceneMap: { value: null },
        prevMap: { value: null },
        maskMap: { value: null },
        stageCount: { value: 0 },
        stageKind: { value: new Array(MAX_STAGES).fill(0) },
        stageCeiling: { value: new Array(MAX_STAGES).fill(0) },
        stagePrev: { value: new Array(MAX_STAGES).fill(0) },
        stageBank: { value: new Array(MAX_STAGES).fill(-1) },
      },
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    this.presentMaterial = new THREE.ShaderMaterial({
      vertexShader: QUAD_VERTEX,
      fragmentShader: PRESENT_FRAGMENT,
      uniforms: {
        ...common,
        sourceMap: { value: null },
        showCode: { value: 0 },
        player: { value: new THREE.Vector2() },
        barCount: { value: 0 },
        bars: { value: Array.from({ length: MAX_BARS }, () => new THREE.Vector4()) },
        levelBank: { value: -1 },
      },
      depthTest: false,
      depthWrite: false,
    });
    this.maskMaterial = new THREE.ShaderMaterial({
      vertexShader: MASK_VERTEX,
      fragmentShader: MASK_FRAGMENT,
      uniforms: { objectHeight: { value: -2000 } },
      side: THREE.DoubleSide,
    });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.filterMaterial);
    this.quad.frustumCulled = false;
    this.quadScene.add(this.quad);
  }

  /** Take one tick's screen state (call with every draw list). */
  setDrawList(list: DrawList): void {
    if (this.state) this.prevPlayer = { x: this.state.playerX, y: this.state.playerY };
    else if (list.screen) this.prevPlayer = { x: list.screen.playerX, y: list.screen.playerY };
    if (!list.screen || list.screen.stages.length === 0) this.historyValid = false;
    this.state = list.screen;
    this.levelBank = levelBank(list.filter);
    this.screenHue.set(list.screen ? hueStages(list.screen.stages) : []);
  }

  /**
   * Whether the next frame needs the filters: a smoothie, flip, headlight or bar, or JE_filterScreen's
   * hue, which the lighting takes here (D191).
   */
  get active(): boolean {
    return this.state !== null || this.levelBank >= 0;
  }

  /**
   * Start compiling, in the background, the programs a filtered frame draws the scene with (D159):
   * `compile` runs with the scene target bound. three keys a program by its target (a render target
   * gets linear output and no tone mapping), so every material has a second program for these
   * frames. Unwarmed, the first filtered frame of a level (the Soul of Zinglon's beam, a smoothie)
   * compiled them all at once: a frame of 0.5-2.4 s.
   */
  compileFiltered(compile: () => Promise<unknown>[]): Promise<unknown>[] {
    return this.withTarget(this.sceneTarget, compile);
  }

  /**
   * After compileFiltered: draw the scene into one pixel of the scene target (`drawPixel`), which
   * sizes and allocates it and builds what compiling doesn't, and compile the filter and present
   * quads (D159).
   */
  warmFiltered(drawPixel: () => void): Promise<unknown> {
    this.fitTargets();
    this.withTarget(this.sceneTarget, () => drawPixel());
    const r = this.renderer;
    const quad = (material: THREE.ShaderMaterial, target: THREE.WebGLRenderTarget | null) =>
      this.withTarget(target, () => {
        this.quad.material = material;
        return r.compileAsync(this.quadScene, this.quadCamera);
      });
    return Promise.all([quad(this.filterMaterial, this.history[0]), quad(this.presentMaterial, null)]);
  }

  private withTarget<T>(target: THREE.WebGLRenderTarget | null, f: () => T): T {
    const r = this.renderer;
    const previous = r.getRenderTarget();
    r.setRenderTarget(target);
    try {
      return f();
    } finally {
      r.setRenderTarget(previous);
    }
  }

  /** The targets at the drawing buffer's size; true if they were resized. */
  private fitTargets(): boolean {
    this.renderer.getDrawingBufferSize(this.size);
    const { x: w, y: h } = this.size;
    if (this.sceneTarget.width === w && this.sceneTarget.height === h) return false;
    for (const t of [this.sceneTarget, this.maskTarget, ...this.history]) t.setSize(w, h);
    return true;
  }

  /**
   * Draw a frame through the filters: `drawScene` renders the scene (with its outlines) into the
   * current render target. `root` holds the draw list's objects, for the mask.
   */
  render(scene: THREE.Scene, camera: THREE.Camera, root: THREE.Object3D, drawScene: () => void, alpha: number): void {
    if (!this.active) {
      drawScene();
      return;
    }
    const state = this.state ?? NO_SCREEN_FILTERS;
    const r = this.renderer;
    const now = performance.now();
    const dt = Math.min(0.25, (now - this.lastTime) / 1000);
    this.lastTime = now;

    if (this.fitTargets()) this.historyValid = false;
    // The hues are chosen as displayed (D191): the filter quad tone maps as the canvas will.
    this.filterMaterial.uniforms.toneExposure.value = r.toneMapping === THREE.NeutralToneMapping ? r.toneMappingExposure : 0;
    camera.updateMatrixWorld();
    this.viewProj.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    this.invViewProj.copy(this.viewProj).invert();

    const previousTarget = r.getRenderTarget();
    // [vfx] The remastered effects' particles and glows (VFX_LAYER) stand for shots and
    // explosions, which the C draws after its filters: while a filter runs they're left out of the
    // scene and the mask, and drawn over the filtered image (before the flip and headlight, which
    // the C applies to the whole screen). DECISIONS.md D35.
    const filtering = state.stages.length > 0;
    const layers = camera.layers.mask;
    if (filtering) camera.layers.disable(VFX_LAYER);
    r.setRenderTarget(this.sceneTarget);
    drawScene();

    let source: THREE.Texture = this.sceneTarget.texture;
    if (filtering) {
      this.renderMask(scene, camera, root);
      const u = this.filterMaterial.uniforms;
      const stages = stageUniforms(state.stages, dt, this.historyValid);
      u.sceneMap.value = this.sceneTarget.texture;
      u.prevMap.value = this.history[1].texture;
      u.maskMap.value = this.maskTarget.texture;
      u.stageCount.value = stages.count;
      u.stageKind.value = stages.kind;
      u.stageCeiling.value = stages.ceiling;
      u.stagePrev.value = stages.prev;
      u.stageBank.value = stages.bank;
      this.quad.material = this.filterMaterial;
      r.setRenderTarget(this.history[0]);
      r.render(this.quadScene, this.quadCamera);
      source = this.history[0].texture;
      camera.layers.mask = layers;
      if (camera.layers.isEnabled(VFX_LAYER)) this.renderOver(scene, camera, VFX_LAYER);
      this.history.reverse(); // this frame's result is the next frame's previous one
      this.historyValid = true;
    }

    const p = this.presentMaterial.uniforms;
    p.sourceMap.value = source;
    p.showCode.value = state.showCode;
    (p.player.value as THREE.Vector2).set(
      this.prevPlayer.x + (state.playerX - this.prevPlayer.x) * alpha,
      this.prevPlayer.y + (state.playerY - this.prevPlayer.y) * alpha,
    );
    const bars = p.bars.value as THREE.Vector4[];
    const count = Math.min(MAX_BARS, state.bars.length / 4);
    for (let i = 0; i < count; i++) bars[i].fromArray(state.bars, i * 4);
    p.barCount.value = count;
    p.levelBank.value = this.levelBank;
    this.quad.material = this.presentMaterial;
    r.setRenderTarget(previousTarget);
    r.render(this.quadScene, this.quadCamera);
  }

  /** Draw only `layer`'s objects of the scene over the current target, in front of everything. */
  private renderOver(scene: THREE.Scene, camera: THREE.Camera, layer: number): void {
    const r = this.renderer;
    const background = scene.background;
    const shadows = r.shadowMap.autoUpdate;
    const autoClear = r.autoClear;
    const layers = camera.layers.mask;
    scene.background = null;
    r.shadowMap.autoUpdate = false;
    r.autoClear = false;
    r.clearDepth();
    camera.layers.set(layer);
    r.render(scene, camera);
    camera.layers.mask = layers;
    r.autoClear = autoClear;
    r.shadowMap.autoUpdate = shadows;
    scene.background = background;
  }

  /** The mask material for a flat-art batch drawn with `material` (one per atlas). */
  private artMaskMaterial(material: THREE.ShaderMaterial): THREE.ShaderMaterial {
    const map = material.uniforms.map.value as THREE.Texture;
    let m = this.artMaskMaterials.get(map);
    if (!m) {
      m = new THREE.ShaderMaterial({
        vertexShader: ART_MASK_VERTEX,
        fragmentShader: ART_MASK_FRAGMENT,
        uniforms: { map: { value: map } },
        side: THREE.DoubleSide,
      });
      this.artMaskMaterials.set(map, m);
    }
    return m;
  }

  /** Draw every object's pass height (D5) into the mask target. */
  private renderMask(scene: THREE.Scene, camera: THREE.Camera, root: THREE.Object3D): void {
    const r = this.renderer;
    const background = scene.background;
    const override = scene.overrideMaterial;
    const shadows = r.shadowMap.autoUpdate;
    const clearColor = r.getClearColor(new THREE.Color());
    const clearAlpha = r.getClearAlpha();
    const material = this.maskMaterial;
    // Models are groups under root at their pass height; instanced sprites carry it per instance.
    material.onBeforeRender = (_r, _s, _c, _g, object) => {
      let height = -2000;
      if (!(object as THREE.InstancedMesh).isInstancedMesh) {
        let o: THREE.Object3D = object;
        while (o.parent && o.parent !== root) o = o.parent;
        height = o.parent === root ? o.position.y : 0;
      }
      if (material.uniforms.objectHeight.value !== height) {
        material.uniforms.objectHeight.value = height;
        material.uniformsNeedUpdate = true;
      }
    };
    // The flat art is left out of this draw and drawn after it with its own material.
    const art: THREE.Mesh[] = [];
    scene.traverseVisible((o) => {
      if (isFlatArt(o) && o.layers.test(camera.layers)) art.push(o);
    });
    for (const m of art) m.visible = false;
    scene.background = null;
    scene.overrideMaterial = material;
    r.shadowMap.autoUpdate = false;
    r.setClearColor(0x000000, 0);
    r.setRenderTarget(this.maskTarget);
    r.render(scene, camera);
    for (const m of art) m.visible = true;
    if (art.length > 0) {
      const saved = art.map((m) => ({ material: m.material, layers: m.layers.mask }));
      for (const m of art) {
        m.material = this.artMaskMaterial(m.material as THREE.ShaderMaterial);
        m.layers.set(ART_MASK_LAYER);
      }
      const layers = camera.layers.mask;
      const autoClear = r.autoClear;
      scene.overrideMaterial = null;
      camera.layers.set(ART_MASK_LAYER);
      r.autoClear = false;
      r.render(scene, camera);
      r.autoClear = autoClear;
      camera.layers.mask = layers;
      art.forEach((m, i) => {
        m.material = saved[i].material;
        m.layers.mask = saved[i].layers;
      });
    }
    r.setClearColor(clearColor, clearAlpha);
    r.shadowMap.autoUpdate = shadows;
    scene.overrideMaterial = override;
    scene.background = background;
  }
}
