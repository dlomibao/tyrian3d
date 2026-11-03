// The title's backdrop (DECISIONS.md D64): the original title's huge maroon planet, arcing from the
// top left down the right, as a painting in motion, with a slow amber sunrise past its limb and the
// odd Talon crossing. Only the "title" mood draws this (src/ui/backdrop.ts); the hangar and space
// moods keep their 3D scene.
//
// Two passes on the View's renderer:
// - the paint: one full-screen fragment shader (planet, flowing brush strokes, sunrise, stars),
//   drawn into a small render target (at most 0.9 MP, never above CSS pixels) about 30 times a
//   second. The paint is soft, so it upscales cleanly; that keeps it light on phones and weak GPUs.
//   A half-resolution path takes over when frames run long (or with ?titlefx=half).
// - the composite: the paint stretched over the canvas with the canvas grain and a vignette, plus
//   the flights of real Talon models (public/models/usp_talon.glb) with their engine glows. It only
//   redraws when the paint has changed or a ship is in flight, so between flights the canvas just
//   keeps its last picture.
// With prefers-reduced-motion one still frame is drawn (redrawn on resize) and no ships fly.

import * as THREE from "three";

/** The paint's resolution cap, in pixels. */
const PAINT_MAX_PIXELS = 0.9e6;
/** Milliseconds between paint frames (about 30 fps; the paint is slow, so this is plenty). */
const PAINT_INTERVAL_MS = 32;
/** The clock time shown as the reduced-motion still: the sun has cleared the limb. */
export const STILL_TIME = 26;
/** Paint frames slower than this on average (ms) switch to the half-resolution path. */
const SLOW_PAINT_MS = 50;

/** Planet placement in screen-height units (origin at the screen's centre, y up): centre x, y, radius. */
const PLACE_LANDSCAPE = [-0.3, -0.56, 1.03] as const;
const PLACE_PORTRAIT = [-0.32, -0.3, 0.7] as const;
/** The sun's bearing from the planet's centre, degrees above the right-hand horizontal. */
const SUN_BEARING_LANDSCAPE = 27;
const SUN_BEARING_PORTRAIT = 44;

/** How far toward the landscape framing an aspect ratio is (0 portrait, 1 landscape). Pure. */
export function landscapeAmount(aspect: number): number {
  return Math.min(1, Math.max(0, (aspect - 0.5) / 0.8));
}

export interface TitleShot {
  /** Planet centre and radius in screen-height units. */
  planet: [number, number, number];
  /** Camera roll, radians. */
  roll: number;
  /** Star field offset (x, y) and zoom: a fraction of the planet's push, for parallax. */
  stars: [number, number, number];
  /** Sun position (screen-height units), visibility 0..1, dawn 0..1. */
  sun: [number, number, number, number];
  /** Shading light direction (x right, y up, z toward the viewer), normalised. */
  light: [number, number, number];
}

const smoothstep = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

/**
 * The camera and the sun at time `t` (seconds since the title appeared) on a screen of `aspect`:
 * a slow push-in toward the sunrise that settles, a drift that never quite repeats, and the sun
 * climbing clear of the limb. Pure, for tests.
 */
export function titleShot(t: number, aspect: number): TitleShot {
  const k = landscapeAmount(aspect);
  const base = PLACE_PORTRAIT.map((v, i) => v + (PLACE_LANDSCAPE[i] - v) * k);
  const push = 1 - Math.exp(-t / 45);
  const zoom = 1 + 0.07 * push;
  // Push toward the limb where the sun comes up.
  const fx = 0.2;
  const fy = 0.05;
  const driftX = Math.sin(t * 0.11) * 0.012 + Math.sin(t * 0.047) * 0.008;
  const driftY = Math.sin(t * 0.083 + 1) * 0.008;
  const cx = fx + (base[0] - fx) * zoom + driftX;
  const cy = fy + (base[1] - fy) * zoom + driftY;
  const r = base[2] * zoom;

  const rise = 1 - Math.exp(-t / 16);
  const bearing = ((SUN_BEARING_PORTRAIT + (SUN_BEARING_LANDSCAPE - SUN_BEARING_PORTRAIT) * k + 1.5 * rise) * Math.PI) / 180;
  const sunR = 0.012;
  const alt = (-0.022 + 0.085 * rise) * r;
  const sx = cx + (r + alt) * Math.cos(bearing);
  const sy = cy + (r + alt) * Math.sin(bearing);
  const vis = smoothstep(-sunR, sunR * 1.5, alt);

  // The shading light comes from the sun's side, swung toward the viewer so the day side shows (a
  // painter's cheat), further as the morning grows; a slow breath of a wobble keeps it alive.
  const lz = 0.16 + 0.18 * rise;
  const lx = Math.cos(bearing) + 0.04 * Math.sin(t * 0.21);
  const ly = Math.sin(bearing) * 0.75 + 0.03 * Math.cos(t * 0.17);
  const ll = Math.hypot(lx, ly, lz);
  return {
    planet: [cx, cy, r],
    roll: Math.sin(t * 0.06) * 0.006,
    stars: [driftX * 0.3, driftY * 0.3, 1 + 0.02 * push],
    sun: [sx, sy, vis, rise],
    light: [lx / ll, ly / ll, lz / ll],
  };
}

/** The paint's size in pixels for a w x h (CSS px) canvas. Pure, for tests. */
export function paintSize(w: number, h: number, dpr: number, half: boolean): { width: number; height: number } {
  const scale = Math.min(0.75 * Math.max(1, Math.min(dpr, 2)), 1, Math.sqrt(PAINT_MAX_PIXELS / Math.max(1, w * h))) * (half ? 0.5 : 1);
  return { width: Math.max(1, Math.round(w * scale)), height: Math.max(1, Math.round(h * scale)) };
}

// --- flights ---

/** A pass across the frame: points (x, y as fractions of the half frame, z depth 0..1) on a Bézier. */
export interface Flight {
  start: number;
  duration: number;
  /** Formation offsets from the lead, in the same units. */
  ships: [number, number, number][];
  /** Size multiplier. */
  size: number;
  /** Bank: + rolls right through the pass, - left. */
  bank: number;
  path: [number, number, number][];
}

/** Every flight repeats this often (seconds). */
export const FLIGHT_PERIOD = 34;

export const FLIGHTS: Flight[] = [
  // The Talon, alone, coming in past the camera on the right and banking away toward the sunrise.
  { start: 2, duration: 13, ships: [[0, 0, 0]], size: 1, bank: 0.5, path: [[1.05, -0.2, 0.25], [0.78, -0.06, 0.38], [0.62, 0.06, 0.55], [0.5, 0.16, 0.95]] },
  // A squadron of four in echelon, crossing the night side low on the left.
  {
    start: 18,
    duration: 14,
    ships: [[0, 0, 0], [0.045, -0.04, 0.012], [0.09, -0.08, 0.024], [-0.045, -0.04, 0.012]],
    size: 1.5,
    bank: -0.2,
    path: [[-1.1, -0.42, 0.75], [-0.85, -0.36, 0.76], [-0.6, -0.33, 0.78], [-0.32, -0.28, 0.8]],
  },
];

function bezier(p: readonly (readonly number[])[], t: number): [number, number, number] {
  const u = 1 - t;
  const a = u * u * u;
  const b = 3 * u * u * t;
  const c = 3 * u * t * t;
  const d = t * t * t;
  return [0, 1, 2].map((i) => a * p[0][i] + b * p[1][i] + c * p[2][i] + d * p[3][i]) as [number, number, number];
}

/** Where a flight is at time t: its progress 0..1, or null while it isn't in the air. Pure. */
export function flightProgress(f: Flight, t: number): number | null {
  const local = (((t - f.start) % FLIGHT_PERIOD) + FLIGHT_PERIOD) % FLIGHT_PERIOD;
  const u = local / f.duration;
  return u <= 1 ? u : null;
}

// --- the noise texture ---

/**
 * A 256x256 tileable noise texture, four bands of isotropic noise (r fine, g medium, b large,
 * a medium-fine), so the shader reads noise with texture taps instead of computing it: wrapped
 * white noise through three box blurs (about a Gaussian), stretched to full contrast.
 */
function noiseTexture(): THREE.DataTexture {
  const N = 256;
  const blurred = (radius: number, seed: number) => {
    let s = seed >>> 0;
    const rnd = () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
    const a = new Float32Array(N * N).map(rnd);
    const b = new Float32Array(N * N);
    const w = 2 * radius + 1;
    const box = (src: Float32Array, dst: Float32Array, horiz: boolean) => {
      for (let j = 0; j < N; j++) {
        const at = (i: number) => (horiz ? src[j * N + (((i % N) + N) % N)] : src[(((i % N) + N) % N) * N + j]);
        let acc = 0;
        for (let i = -radius; i <= radius; i++) acc += at(i);
        for (let i = 0; i < N; i++) {
          if (horiz) dst[j * N + i] = acc / w;
          else dst[i * N + j] = acc / w;
          acc += at(i + radius + 1) - at(i - radius);
        }
      }
    };
    for (let pass = 0; pass < 3; pass++) {
      box(a, b, true);
      box(b, a, false);
    }
    let mean = 0;
    for (const v of a) mean += v;
    mean /= a.length;
    let sd = 0;
    for (const v of a) sd += (v - mean) ** 2;
    sd = Math.sqrt(sd / a.length);
    for (let i = 0; i < a.length; i++) a[i] = Math.min(1, Math.max(0, 0.5 + (a[i] - mean) / (sd * 5)));
    return a;
  };
  const chans = [blurred(1, 11), blurred(5, 23), blurred(18, 37), blurred(3, 51)];
  const px = new Uint8Array(N * N * 4);
  for (let i = 0; i < N * N; i++) for (let c = 0; c < 4; c++) px[i * 4 + c] = Math.round(chans[c][i] * 255);
  const tex = new THREE.DataTexture(px, N, N, THREE.RGBAFormat, THREE.UnsignedByteType);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.generateMipmaps = true;
  tex.needsUpdate = true;
  return tex;
}

// --- shaders ---

const FULLSCREEN_VERTEX = /* glsl */ `
varying vec2 vUv;
void main() {
  vUv = position.xy * 0.5 + 0.5;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}`;

/**
 * The painted planet (after the "Painted motion" concept) with the "Cinematic dawn" sunrise laid
 * over it in the same brushwork. Coordinates: P in screen-height units, origin at the centre, y up.
 */
const PAINT_FRAGMENT = /* glsl */ `
uniform vec2 uRes;
uniform float uTime;
uniform vec3 uPlanet;   // centre and radius
uniform float uRoll;
uniform vec3 uStars;    // star field offset and zoom
uniform vec4 uSun;      // position, visibility, dawn
uniform vec3 uLight;
uniform sampler2D uNoise; // r fine, g medium, b large, a medium-fine

#define TEX(p) texture2D(uNoise, p)

// The flow field on the planet's map: zonal jets that alternate with latitude, plus the curl of a
// slowly drifting stream function, so strokes swirl round eddies without converging.
vec2 flowAt(vec2 q, float t) {
  vec2 qs = q * 0.42 + vec2(t * 0.0025, 0.0);
  float e = 1.0 / 128.0;
  float p0 = TEX(qs).b;
  float px = TEX(qs + vec2(e, 0.0)).b;
  float py = TEX(qs + vec2(0.0, e)).b;
  vec2 curl = vec2(py - p0, -(px - p0)) / e;
  float jet = sin(q.y * 7.0 + TEX(q * 0.3).g * 4.0);
  return vec2(0.55 + 0.6 * jet, 0.08 * jet) * 0.1 + curl * 0.032;
}

// One layer of paint at map position q, its strokes combed along v (a short line-integral smear).
vec2 paint(vec2 q, vec2 v) {
  float body = TEX(q * vec2(0.2, 0.62)).g * 0.7 + TEX(q * vec2(0.45, 1.3) + 0.31).g * 0.3;
  body = mix(body, 0.5 + 0.5 * sin(q.y * 9.0 + TEX(q * 0.22 + 0.5).b * 7.0), 0.12);
  vec2 dir = normalize(v + vec2(1e-4, 0.0));
  vec2 sc = vec2(0.28, 1.15);
  vec2 qf = q * sc + vec2(0.0, 0.37);
  vec2 sf = dir * 0.032 * sc;
  float s = 0.0;
  for (int k = -4; k <= 4; k++) s += TEX(qf + sf * float(k)).a;
  s = (s / 9.0 - 0.5) * 1.9 + 0.5;
  // dry-brush bristle marks inside each stroke
  vec2 sb = vec2(0.5, 4.2);
  vec2 qb = q * sb;
  vec2 bb = dir * 0.012 * sb;
  float f = TEX(qb - bb * 2.0).r + TEX(qb - bb).r + TEX(qb).r + TEX(qb + bb).r + TEX(qb + bb * 2.0).r;
  f = (f / 5.0 - 0.5) * 2.4;
  return vec2(body, s + f * 0.12);
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

void main() {
  vec2 P = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
  float cr = cos(uRoll), sr = sin(uRoll);
  P = mat2(cr, sr, -sr, cr) * P;
  float t = uTime;
  float breath = 0.5 + 0.5 * sin(t * 0.45);
  vec3 L = uLight;
  vec2 sunP = uSun.xy;
  float sunVis = uSun.z, dawn = uSun.w;

  vec2 d = (P - uPlanet.xy) / uPlanet.z;
  float r = length(d);
  float aa = fwidth(r) * 1.25;
  vec2 toSun = P - sunP;
  float sd = length(toSun);

  // Space: warm near-black with a few soft painted stars, fading near the sun
  vec3 col = vec3(0.034, 0.022, 0.019);
  vec2 sg = (P * uStars.z - uStars.xy) * 46.0;
  vec2 cell = floor(sg);
  float h = hash(cell);
  if (h > 0.93) {
    vec2 o = vec2(hash(cell + 3.1), hash(cell + 7.7)) - 0.5;
    float std = length(fract(sg) - 0.5 - o * 0.6);
    float tw = 0.6 + 0.4 * sin(t * (0.6 + h * 1.4) + h * 40.0);
    col += vec3(0.95, 0.86, 0.74) * smoothstep(0.12, 0.0, std) * (h - 0.93) * 9.0 * tw * smoothstep(0.05, 0.4, sd);
  }

  // Atmosphere: a dusty rose rim on the lit side, and a wide copper haze
  vec3 rimCol = vec3(0.80, 0.60, 0.56);
  float sideLit = smoothstep(-0.35, 0.75, dot(normalize(vec3(d, 0.12)), L));
  float outside = max(r - 1.0, 0.0);
  float glow = exp(-outside * 34.0) * 0.85 + exp(-outside * 6.0) * 0.12;
  col += rimCol * glow * sideLit * (0.85 + 0.25 * breath);

  float onDisc = 0.0;
  if (r < 1.0 + aa) {
    vec3 Nn = vec3(d, sqrt(max(0.0, 1.0 - r * r)));
    // The pole sits just off the lower left (tipped toward us), so the latitude bands arc from the
    // top left down the right, along the limb, like the original's streaks.
    vec3 up = normalize(vec3(-0.5, -0.74, 0.45));
    vec3 fw = normalize(vec3(0.55, 0.45, 0.7) - up * dot(vec3(0.55, 0.45, 0.7), up));
    vec3 ea = cross(up, fw);
    float lon = atan(dot(Nn, ea), dot(Nn, fw)) + t * 0.007;
    float lat = asin(clamp(dot(Nn, up), -1.0, 1.0));
    vec2 q = vec2(lon * cos(lat) * 0.62, lat * 0.62);

    // Flow-map animation: two phases of the same paint carried along the flow and cross-faded.
    vec2 v = flowAt(q, t);
    float cyc = t / 6.0;
    float pa = fract(cyc), pb = fract(cyc + 0.5);
    float wa = 1.0 - abs(2.0 * pa - 1.0);
    vec2 A = paint(q - v * (pa - 0.5) * 1.7, v);
    vec2 B = paint(q - v * (pb - 0.5) * 1.7, v);
    vec2 pm = A * wa + B * (1.0 - wa);
    float body = pm.x, streak = pm.y;

    float cloud = smoothstep(0.52, 0.86, body * 0.55 + streak * 0.6);
    float high = smoothstep(0.62, 0.95, body * 0.4 + streak * 0.75);
    cloud = mix(cloud, floor(cloud * 5.0 + 0.5) / 5.0, 0.12);

    vec3 deep = vec3(0.13, 0.035, 0.03);
    vec3 maroon = vec3(0.34, 0.085, 0.075);
    vec3 umber = vec3(0.36, 0.17, 0.10);
    vec3 rose = vec3(0.64, 0.4, 0.32);
    vec3 bone = vec3(0.93, 0.87, 0.78);
    float zone = TEX(q * vec2(0.35, 0.9) + 0.6).a;
    vec3 ground = mix(deep, maroon, smoothstep(0.15, 0.75, body));
    ground = mix(ground, umber, smoothstep(0.45, 0.8, zone) * 0.75);
    vec3 cloudCol = mix(rose, bone, high);
    vec3 albedo = mix(ground, cloudCol, cloud * 0.92);

    // Impasto: the paint's own height catches a ridge of light
    float hgt = cloud * 0.8 + streak * 0.5;
    vec2 g = vec2(dFdx(hgt), dFdy(hgt)) * uRes.y / 600.0;
    float relief = clamp(1.0 - dot(g, normalize(L.xy)) * 0.9, 0.8, 1.25);

    // Sphere light: a wrapped, painted terminator with a copper band where day meets night
    float ndl = dot(Nn, L);
    float lit = smoothstep(-0.12, 0.75, ndl);
    lit = mix(lit, floor(lit * 4.0 + 0.5) / 4.0, 0.18);
    lit *= 0.9 + 0.14 * breath;
    vec3 c = albedo * (0.07 + 1.08 * lit) * relief;
    float band = exp(-pow((ndl + 0.02) / 0.16, 2.0));
    c += vec3(0.62, 0.32, 0.16) * band * (0.22 + 0.12 * dawn) * (0.4 + cloud);
    c += vec3(0.75, 0.42, 0.2) * pow(lit, 3.0) * (1.0 - cloud) * 0.1;

    // Faint lights of settlements on the night side, warm specks in the dark paint
    float night = 1.0 - smoothstep(-0.3, 0.02, ndl);
    float town = smoothstep(0.62, 0.8, TEX(q * vec2(0.9, 2.2) + 0.13).b);
    float specks = smoothstep(0.74, 0.92, TEX(q * vec2(2.6, 5.2) + 0.71).r);
    c += vec3(0.95, 0.55, 0.22) * night * town * specks * (1.0 - cloud) * 0.32;

    // Limb: the atmosphere thickens toward the edge
    float fr = pow(1.0 - Nn.z, 2.6);
    c = mix(c, rimCol * (0.25 + 0.95 * smoothstep(-0.2, 0.7, ndl)) * (0.9 + 0.2 * breath), clamp(fr * 0.75, 0.0, 1.0));

    onDisc = smoothstep(1.0 + aa, 1.0 - aa, r);
    col = mix(col, c, onDisc);
  }

  // --- the sunrise ---
  // Scatter along the rim: a long amber arc, strongest beside the sun, laid in strokes along the limb
  vec2 sunDir = normalize(sunP - uPlanet.xy);
  vec2 pDir = normalize(P - uPlanet.xy);
  float along = acos(clamp(dot(pDir, sunDir), -1.0, 1.0));
  float alt = (r - 1.0) * uPlanet.z;
  float limb = exp(-max(alt, 0.0) / 0.02) * smoothstep(-0.045, 0.0, alt);
  float stroke = TEX(vec2(along * 0.9 + 0.2, alt * 9.0 + 0.4)).a;
  float near = exp(-along * 3.2);
  vec3 amber = vec3(1.0, 0.56, 0.26);
  col += amber * limb * near * (0.25 + 1.25 * dawn) * (0.7 + 0.6 * stroke);
  // a soft warm wash of light in the sky around the sun, held back over the disc
  col += vec3(0.62, 0.32, 0.15) * exp(-sd * 3.5) * (0.06 + 0.22 * sunVis) * mix(1.0, 0.45, onDisc);

  // Disc and halo, the halo brushed in short radial strokes
  float sunR = 0.012;
  float ang = atan(toSun.y, toSun.x);
  float rays = TEX(vec2(ang * 0.65, sd * 0.35 - t * 0.002)).g;
  float halo = exp(-sd * 60.0) * 1.3 + exp(-sd * 14.0) * 0.35;
  halo *= 0.65 + 0.7 * rays;
  halo = mix(halo, floor(halo * 7.0) / 7.0, 0.2);
  float behind = 1.0 - onDisc;
  col += vec3(1.0, 0.66, 0.36) * halo * (0.2 + 0.8 * sunVis) * mix(0.4, 1.0, behind);
  float disc = smoothstep(sunR, sunR * 0.55, sd) * behind;
  col += vec3(1.6, 1.2, 0.8) * disc * sunVis;

  // An understated flare: a short anamorphic streak and two ghosts mirrored through the centre
  float streakL = exp(-abs(toSun.y) * 140.0) * exp(-abs(toSun.x) * 2.2);
  col += vec3(1.0, 0.62, 0.34) * streakL * 0.16 * sunVis;
  for (int i = 1; i <= 2; i++) {
    float k = float(i);
    vec2 gp = sunP * (-0.35 - 0.45 * k);
    float gr = 0.025 + 0.03 * k;
    float gh = smoothstep(gr, gr * 0.5, length(P - gp));
    col += vec3(0.8, 0.42, 0.22) * gh * 0.02 * sunVis;
  }

  // Grade: hold the palette muted and warm (maroon, umber, copper, bone)
  col = mix(vec3(dot(col, vec3(0.3, 0.59, 0.11))), col, 0.84) * vec3(1.0, 0.96, 0.9);
  col += (hash(gl_FragCoord.xy + fract(t)) - 0.5) / 255.0;
  gl_FragColor = vec4(col, 1.0);
}`;

/** The paint stretched over the canvas, with a static canvas grain and the vignette. */
const COMPOSITE_FRAGMENT = /* glsl */ `
uniform sampler2D uPaint;
uniform sampler2D uNoise;
uniform vec2 uRes;
varying vec2 vUv;
void main() {
  vec3 c = texture2D(uPaint, vUv).rgb;
  // Vignette: the frame's edges sink into warm dark
  vec2 v = (vUv - vec2(0.5, 0.55)) * vec2(1.0 / 1.2, 1.0);
  c *= mix(1.0, 0.5, smoothstep(0.32, 0.78, length(v)));
  // Canvas tooth: fine noise and a faint linen weave, laid on like an overlay blend
  vec2 px = gl_FragCoord.xy;
  float n = texture2D(uNoise, px / 256.0).r - 0.5;
  float weave = (step(mod(px.x + px.y, 4.0), 1.0) * 0.01 - step(mod(px.x - px.y, 4.0), 1.0) * 0.018);
  float g = clamp(0.5 + n * 0.16 + weave, 0.0, 1.0);
  vec3 over = mix(2.0 * c * g, 1.0 - 2.0 * (1.0 - c) * (1.0 - g), step(0.5, c));
  c = mix(c, over, 0.55);
  gl_FragColor = vec4(c, 1.0);
}`;

const NO_OUTLINE = { outlineParameters: { visible: false } };

interface Flyer {
  obj: THREE.Object3D;
  glows: THREE.SpriteMaterial[];
}

export class TitlePlanet {
  private readonly noise = noiseTexture();
  private readonly target = new THREE.WebGLRenderTarget(1, 1, { depthBuffer: false, stencilBuffer: false, generateMipmaps: false, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter });
  private readonly paintScene = new THREE.Scene();
  private readonly paintCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private readonly paintMaterial: THREE.ShaderMaterial;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(30, 1, 1, 400);
  private readonly composite: THREE.ShaderMaterial;
  private readonly sunLight = new THREE.DirectionalLight(0xffc890, 3.2);
  private flyers: Flyer[][] = [];
  private lastPaint = -Infinity;
  private paintedSize = "";
  private drawn = false;
  private still = false;
  /** Use the half-resolution paint (slow frames, or ?titlefx=half). */
  half = false;
  /** The shader didn't compile or link: the backdrop shows the CSS stand-in instead. */
  failed = false;
  private readonly slow = { since: 0, frames: 0 };
  /** Paint frames drawn, for the performance check (window.tyrianUi in dev). */
  paints = 0;

  constructor(private readonly renderer: THREE.WebGLRenderer, environment: THREE.Texture | null) {
    const tri = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
    this.paintMaterial = new THREE.ShaderMaterial({
      vertexShader: FULLSCREEN_VERTEX,
      fragmentShader: PAINT_FRAGMENT,
      uniforms: {
        uRes: { value: new THREE.Vector2(1, 1) },
        uTime: { value: 0 },
        uPlanet: { value: new THREE.Vector3() },
        uRoll: { value: 0 },
        uStars: { value: new THREE.Vector3(0, 0, 1) },
        uSun: { value: new THREE.Vector4() },
        uLight: { value: new THREE.Vector3(0.8, 0.3, 0.3) },
        uNoise: { value: this.noise },
      },
      depthTest: false,
      depthWrite: false,
    });
    const paintQuad = new THREE.Mesh(tri, this.paintMaterial);
    paintQuad.frustumCulled = false;
    this.paintScene.add(paintQuad);

    this.composite = new THREE.ShaderMaterial({
      vertexShader: FULLSCREEN_VERTEX,
      fragmentShader: COMPOSITE_FRAGMENT,
      uniforms: { uPaint: { value: this.target.texture }, uNoise: { value: this.noise }, uRes: { value: new THREE.Vector2(1, 1) } },
      depthTest: false,
      depthWrite: false,
      userData: NO_OUTLINE,
    });
    const back = new THREE.Mesh(tri, this.composite);
    back.frustumCulled = false;
    back.renderOrder = -1;
    this.scene.add(back);

    // The ships' light: the low sun from behind and to the right, a dim warm fill from our side.
    this.scene.add(this.sunLight, new THREE.AmbientLight(0x4a2418, 0.8));
    const fill = new THREE.DirectionalLight(0xd8a070, 0.45);
    fill.position.set(-2, 1, 6);
    this.scene.add(fill);
    this.scene.environment = environment;
    this.scene.environmentIntensity = 0.35;

    this.half = new URLSearchParams(location.search).get("titlefx") === "half";
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    this.still = !!reduce?.matches;
    reduce?.addEventListener?.("change", (e) => {
      this.still = e.matches;
      this.drawn = false;
    });
  }

  /**
   * The ship that flies past: a model normalised to length 1, nose along -Z, with its engine glows
   * (sprites) as children. Each ship in each flight gets a copy with its own glow materials.
   */
  setFlyer(template: THREE.Object3D): void {
    for (const ships of this.flyers) for (const f of ships) this.scene.remove(f.obj);
    this.flyers = FLIGHTS.map((flight) =>
      flight.ships.map(() => {
        const obj = template.clone(true);
        const glows: THREE.SpriteMaterial[] = [];
        obj.traverse((o) => {
          if (o instanceof THREE.Sprite) {
            o.material = o.material.clone();
            glows.push(o.material);
          }
        });
        obj.visible = false;
        this.scene.add(obj);
        return { obj, glows };
      }),
    );
  }

  /** Forget what was drawn (another mood used the canvas): the next frame redraws everything. */
  invalidate(): void {
    this.drawn = false;
    this.lastPaint = -Infinity;
  }

  /**
   * Draw a frame at `now` (ms) with the title's clock at `time` (s) on a w x h (CSS px) canvas.
   * Skips the draw when nothing has changed since the last one.
   */
  frame(now: number, time: number, w: number, h: number): void {
    if (this.failed) return;
    const dpr = this.renderer.getPixelRatio();
    const size = paintSize(w, h, dpr, this.half);
    const sizeKey = `${w}x${h}@${dpr}:${size.width}x${size.height}`;
    const resized = sizeKey !== this.paintedSize;
    const t = this.still ? STILL_TIME : time;
    if (this.still && this.drawn && !resized) return;

    const paintDue = resized || !this.drawn || now - this.lastPaint >= PAINT_INTERVAL_MS;
    const flying = !this.still && this.placeShips(t, w / Math.max(1, h));
    // Ships in flight redraw every frame, except on the half-resolution path (a weak GPU), where
    // they keep to the paint's pace.
    if (!paintDue && (!flying || this.half)) return;

    if (paintDue) {
      if (resized) {
        this.target.setSize(size.width, size.height);
        this.paintedSize = sizeKey;
      } else if (this.drawn) this.watchSpeed(now - this.lastPaint);
      this.lastPaint = now;
      this.paint(t, w / Math.max(1, h), size.width, size.height);
    }
    this.composite.uniforms.uRes.value.set(w * dpr, h * dpr);
    this.camera.aspect = w / Math.max(1, h);
    this.camera.updateProjectionMatrix();
    this.renderer.render(this.scene, this.camera);
    if (!this.drawn) this.checkCompiled();
    this.drawn = true;
  }

  /** Render the paint pass `n` times and wait for the GPU: ms per paint (the performance check). */
  benchmark(n = 30): number {
    const { width, height } = this.target;
    const px = new Uint8Array(4);
    this.renderer.readRenderTargetPixels(this.target, 0, 0, 1, 1, px);
    const t0 = performance.now();
    for (let i = 0; i < n; i++) this.paint(10 + i * 0.033, width / height, width, height);
    this.renderer.readRenderTargetPixels(this.target, 0, 0, 1, 1, px);
    return (performance.now() - t0) / n;
  }

  /** The paint's size now, for the performance check. */
  get paintPixels(): { width: number; height: number } {
    return { width: this.target.width, height: this.target.height };
  }

  private paint(t: number, aspect: number, pw: number, ph: number): void {
    const shot = titleShot(t, aspect);
    const u = this.paintMaterial.uniforms;
    u.uRes.value.set(pw, ph);
    u.uTime.value = t;
    u.uPlanet.value.set(...shot.planet);
    u.uRoll.value = shot.roll;
    u.uStars.value.set(...shot.stars);
    u.uSun.value.set(...shot.sun);
    u.uLight.value.set(...shot.light);
    // The ships' sun is behind the planet's limb, where the paint's sun is.
    const [sx, sy] = shot.sun;
    this.sunLight.position.set(sx * 4, sy * 4 + 1, -3);
    const before = this.renderer.getRenderTarget();
    this.renderer.setRenderTarget(this.target);
    this.renderer.render(this.paintScene, this.paintCamera);
    this.renderer.setRenderTarget(before);
    this.paints++;
  }

  /** Put the ships where their flights are at time t; true if any is in the air. */
  private placeShips(t: number, aspect: number): boolean {
    let any = false;
    const th = Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    // Depth of a path's z = 0..1: near enough at 0 for the Talon to fill about a twelfth of the frame.
    const depth = (z: number) => 4 + z * 70;
    const portrait = aspect < 0.8;
    const toWorld = (p: readonly number[], out: THREE.Vector3) => {
      const Z = depth(p[2]);
      // Portrait screens fly the ships lower, under the menu.
      const y = portrait ? p[1] - 0.45 : p[1];
      return out.set(p[0] * th * Z * aspect, y * th * Z, -Z);
    };
    const a = new THREE.Vector3();
    const b = new THREE.Vector3();
    FLIGHTS.forEach((f, fi) => {
      const u = flightProgress(f, t);
      const ships = this.flyers[fi] ?? [];
      ships.forEach((ship, si) => {
        ship.obj.visible = u !== null;
        if (u === null) return;
        any = true;
        const off = f.ships[si];
        const at = (k: number, out: THREE.Vector3) => {
          const p = bezier(f.path, Math.min(1, Math.max(0, k)));
          return toWorld([p[0] + off[0], p[1] + off[1], p[2] + off[2]], out);
        };
        at(u, a);
        at(u + 0.01, b);
        ship.obj.position.copy(a);
        // Nose (-Z) along the path: look back the way it came.
        ship.obj.lookAt(a.clone().multiplyScalar(2).sub(b));
        ship.obj.rotateZ(Math.sin(u * Math.PI) * f.bank);
        const fade = smoothstep(0, 0.08, u) * (1 - smoothstep(0.85, 1, u));
        ship.obj.scale.setScalar(f.size * (0.6 + 0.4 * fade));
        const flick = 0.85 + 0.15 * Math.sin(t * 37 + si * 1.7);
        for (const m of ship.glows) m.opacity = fade * flick * (m.userData.opacity ?? 0.8);
      });
    });
    return any;
  }

  /** Paint frames that keep running long (a weak GPU) switch to the half-resolution path. */
  private watchSpeed(interval: number): void {
    if (this.half) return;
    if (interval > 200) return; // a hitch or a hidden tab, not the GPU
    this.slow.since += interval;
    this.slow.frames++;
    if (this.slow.frames < 45) return;
    if (this.slow.since / this.slow.frames > SLOW_PAINT_MS) {
      this.half = true;
      console.info("title backdrop: frames are slow, painting at half resolution");
    }
    this.slow.since = 0;
    this.slow.frames = 0;
  }

  private checkCompiled(): void {
    for (const m of [this.paintMaterial, this.composite]) {
      const program = (this.renderer.properties.get(m) as { currentProgram?: { diagnostics?: { runnable: boolean } } }).currentProgram;
      if (program?.diagnostics && !program.diagnostics.runnable) this.failed = true;
    }
  }
}
