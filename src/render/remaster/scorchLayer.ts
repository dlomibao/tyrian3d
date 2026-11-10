// Scorch marks where an enemy standing on a structure was shot off it (D96), remastered look only.
//
// TYRIAN's purple eye fortress (and the like) is a terrain structure with enemies sitting on its
// cells: the tile under each cap already paints the cap's broken socket, so in the original a
// destroyed cap leaves cracked, blackened stone where it stood. The remastered structure models
// carry the intact block, so the renderer leaves a mark there instead: a ragged soot stain over a
// shattered-crack network whose cracks glow and cool for a second or so. A structure whose model
// already builds the broken socket (the purple machines, D115: `brokenSockets` in its entry) gets a
// lighter mark: the fresh break's glow, cooling, and a faint soot, so the modelled break shows.
//
// A mark is pinned to the background tile it fell on (by draw key), so it scrolls with that layer
// exactly, and lasts until the tile leaves the screen, as the original's painted socket does. All
// marks are one instanced draw call (premultiplied alpha: dark char plus additive embers), from a
// fixed pool; the oldest mark gives way when it is full.

import * as THREE from "three";
import { ENEMY_KEY_BASE, type Draw, type DrawList, type TileDraw } from "../../sim/draw";
import { CLASSIC_TICK_MS } from "../../core/timing";
import { PX_PER_UNIT, screenWorldX, screenWorldZ } from "../../game/playfield";
import { passHeight } from "../passHeights";

/** Most marks at once (a screen of fortresses is under 30). */
const CAPACITY = 64;
/** The mark's radius (px): a 24x28 enemy's socket, a 12x14 one's. */
const RADIUS_PX = { 1: 6.5, 2: 11.5 } as const;
/**
 * Height above the structure's pass: just over what the models build under an enemy (ENEMY_MAX
 * 0.38 on the ground, L2_ENEMY_MAX 0.33 on backgrounds 2 and 3, lib_tyrbld.py) and under the
 * enemies' own pass, so a live neighbour's model still covers it.
 */
const LIFT = [0.4, 0.35, 0.35] as const;
/** What a structure tile takes when an enemy standing on it is shot off (D96, D115). */
export const enum StructureMark {
  /** Not a structure: no mark. */
  None = 0,
  /** A full scorch mark: soot and a shattered-crack network over the intact model. */
  Scorch = 1,
  /** The model shows the broken socket itself: only the glow of the fresh break and a light soot. */
  Socket = 2,
}

/** An enemy counts as standing on the tile if the two moved together (px, either axis) over its last tick. */
const STILL_PX = 1;

const VERTEX = /* glsl */ `
attribute vec4 aPlace;  // world x, y, z, radius
attribute vec3 aParams; // age (s), seed, socket (1: the model shows the break, D115)
varying vec2 vP;
varying vec3 vParams;
void main() {
  vP = position.xy;
  vParams = aParams;
  vec3 w = aPlace.xyz + vec3(position.x, 0.0, position.y) * aPlace.w;
  gl_Position = projectionMatrix * viewMatrix * vec4(w, 1.0);
}
`;

const FRAGMENT = /* glsl */ `
varying vec2 vP;
varying vec3 vParams;

vec2 hash2(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return fract(sin(p) * 43758.5453);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash2(i).x, b = hash2(i + vec2(1.0, 0.0)).x, c = hash2(i + vec2(0.0, 1.0)).x, d = hash2(i + vec2(1.0, 1.0)).x;
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
// Distance to the nearest Voronoi cell edge (F2 - F1): the shattered plates' cracks.
float edges(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float f1 = 8.0, f2 = 8.0;
  for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
    vec2 g = vec2(float(x), float(y));
    vec2 r = g + hash2(i + g) - f;
    float d = dot(r, r);
    if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) f2 = d;
  }
  return sqrt(f2) - sqrt(f1);
}

void main() {
  float seed = vParams.y;
  float age = vParams.x;
  float cs = cos(seed * 6.2832), sn = sin(seed * 6.2832);
  vec2 p = mat2(cs, -sn, sn, cs) * vP;
  float d = length(p);
  float n = 0.6 * noise(p * 2.7 + seed * 17.0) + 0.4 * noise(p * 6.3 - seed * 9.0);
  float e = d + (n - 0.5) * 0.5;
  if (e > 1.0) discard;
  // Soot: heaviest in the middle, a ragged edge.
  float soot = smoothstep(1.0, 0.1, e);
  // Shattered plates round the impact (cells shrink toward it), and a few long radial cracks.
  vec2 q = p * (2.4 + 1.6 * (1.0 - d)) + seed * 5.0;
  float crack = (1.0 - smoothstep(0.03, 0.11, edges(q))) * smoothstep(0.9, 0.2, d);
  float ang = atan(p.y, p.x);
  float rays = pow(abs(sin(ang * 2.5 + seed * 11.0 + n * 2.5)), 30.0) * smoothstep(1.0, 0.25, e) * step(0.12, d);
  crack = max(crack, 0.85 * rays);
  float hole = smoothstep(0.34, 0.1, e);
  float heat = exp(-age * 3.0);
  // Over a modelled broken socket: no painted cracks once cool, only a light soot (D115).
  float socket = vParams.z;
  crack *= mix(1.0, heat, socket);
  hole *= mix(1.0, heat, socket);
  soot *= mix(1.0, 0.35, socket);
  float a = clamp(0.5 * soot + 0.4 * crack + 0.3 * hole, 0.0, 0.9);
  // Burnt metal: near-black char, a little warm toward the stain's edge.
  vec3 charred = mix(vec3(0.03, 0.025, 0.03), vec3(0.11, 0.06, 0.04), smoothstep(0.35, 0.95, e) * (1.0 - crack));
  // The cracks and the hole glow, cooling within about a second.
  vec3 ember = vec3(1.0, 0.38, 0.08) * (crack + hole) * heat * 1.3;
  gl_FragColor = vec4(charred * a + ember * a, a);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}
`;

interface Mark {
  /** The background tile it is pinned to, and its offset from that tile's top-left (px). */
  tileKey: number;
  dx: number;
  dy: number;
  radius: number;
  seed: number;
  /** The tick it was made (ScorchLayer's tick count). */
  born: number;
  /** Its structure's model shows the broken socket (D115). */
  socket: boolean;
  /** This tick's draw index of its tile, or -1. */
  at: number;
}

export class ScorchLayer {
  readonly mesh: THREE.Mesh;
  private readonly geometry = new THREE.InstancedBufferGeometry();
  private readonly place = new THREE.InstancedBufferAttribute(new Float32Array(CAPACITY * 4), 4);
  private readonly params = new THREE.InstancedBufferAttribute(new Float32Array(CAPACITY * 3), 3);
  private readonly marks: Mark[] = [];
  private ticks = 0;
  private serial = 0;

  constructor() {
    this.geometry.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
    this.geometry.setIndex([0, 2, 1, 0, 3, 2]);
    this.place.setUsage(THREE.DynamicDrawUsage);
    this.params.setUsage(THREE.DynamicDrawUsage);
    this.geometry.setAttribute("aPlace", this.place);
    this.geometry.setAttribute("aParams", this.params);
    this.geometry.instanceCount = 0;
    const material = new THREE.ShaderMaterial({
      vertexShader: VERTEX,
      fragmentShader: FRAGMENT,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
      blending: THREE.CustomBlending,
      blendSrc: THREE.OneFactor,
      blendDst: THREE.OneMinusSrcAlphaFactor,
      userData: { outlineParameters: { visible: false } },
    });
    this.mesh = new THREE.Mesh(this.geometry, material);
    this.mesh.frustumCulled = false;
    this.mesh.visible = false;
    this.mesh.name = "scorch-marks";
  }

  get count(): number {
    return this.marks.length;
  }

  clear(): void {
    this.marks.length = 0;
    this.mesh.visible = false;
  }

  /**
   * Take a tick's draw list: drop the marks whose tile left the screen, and add one for each enemy
   * destroyed this tick that stood on a structure tile of its layer (`structure`: which mark it takes). `prevX`/`prevY`
   * are the draws' positions last tick (DrawInterpolator), to tell standing enemies from flying ones.
   */
  tick(list: DrawList, prevX: Float32Array, prevY: Float32Array, structure: (d: TileDraw) => StructureMark): void {
    this.ticks++;
    const items = list.items;
    const deaths = list.deaths;
    if (this.marks.length === 0 && !deaths?.length) return;
    for (const m of this.marks) m.at = -1;
    if (this.marks.length > 0) {
      for (let i = 0; i < items.length; i++) {
        const d = items[i];
        if (d.kind !== "tile") continue;
        for (const m of this.marks) if (m.tileKey === d.key) m.at = i;
      }
    }
    for (const death of deaths ?? []) {
      const e = findEnemy(items, death.key);
      if (e < 0) continue;
      const t = findTile(items, death.layer, death.x, death.y, structure);
      if (t < 0) continue;
      const ed = items[e] as { x: number; y: number };
      const td = items[t] as TileDraw;
      if (Math.abs(ed.x - prevX[e] - (td.x - prevX[t])) > STILL_PX || Math.abs(ed.y - prevY[e] - (td.y - prevY[t])) > STILL_PX) continue;
      if (this.marks.length >= CAPACITY) this.marks.shift();
      this.marks.push({
        tileKey: td.key, dx: death.x - td.x, dy: death.y - td.y, radius: RADIUS_PX[death.size],
        seed: fract(this.serial++ * 0.618034 + death.x * 0.0137), born: this.ticks, at: t,
        socket: structure(td) === StructureMark.Socket,
      });
    }
    let n = 0;
    for (const m of this.marks) if (m.at >= 0) this.marks[n++] = m;
    this.marks.length = n;
  }

  /** Place this display frame's marks on their (interpolated) tiles. */
  update(items: readonly Draw[], prevX: Float32Array, prevY: Float32Array, alpha: number, cam: THREE.Vector3): void {
    const n = this.marks.length;
    this.mesh.visible = n > 0;
    if (n === 0) return;
    const pl = this.place.array as Float32Array;
    const pa = this.params.array as Float32Array;
    for (let j = 0; j < n; j++) {
      const m = this.marks[j];
      const d = items[m.at] as TileDraw;
      const x = prevX[m.at] + (d.x - prevX[m.at]) * alpha + m.dx;
      const y = prevY[m.at] + (d.y - prevY[m.at]) * alpha + m.dy;
      // On the camera ray through its screen point, scaled to keep its screen size (D6).
      const h = passHeight(d.pass) + LIFT[d.layer];
      const k = h / cam.y;
      const gx = screenWorldX(x), gz = screenWorldZ(y);
      pl[j * 4] = gx + (cam.x - gx) * k;
      pl[j * 4 + 1] = h;
      pl[j * 4 + 2] = gz + (cam.z - gz) * k;
      pl[j * 4 + 3] = (m.radius / PX_PER_UNIT) * (1 - k);
      pa[j * 3] = ((this.ticks - m.born + alpha) * CLASSIC_TICK_MS) / 1000;
      pa[j * 3 + 1] = m.seed;
      pa[j * 3 + 2] = m.socket ? 1 : 0;
    }
    this.geometry.instanceCount = n;
    for (const attr of [this.place, this.params]) {
      attr.clearUpdateRanges();
      attr.addUpdateRange(0, n * attr.itemSize);
      attr.needsUpdate = true;
    }
  }

  dispose(): void {
    this.geometry.dispose();
    (this.mesh.material as THREE.Material).dispose();
  }
}

function fract(v: number): number {
  return v - Math.floor(v);
}

/** The first draw of the enemy whose object key is `key` (its tiles use key..key+3), or -1. */
function findEnemy(items: readonly Draw[], key: number): number {
  if (key < ENEMY_KEY_BASE) return -1;
  for (let i = 0; i < items.length; i++) {
    const d = items[i];
    if (d.kind === "sprite2" && d.key >= key && d.key < key + 4) return i;
  }
  return -1;
}

/** The last-drawn (topmost) structure tile of `layer` with an opaque pixel at (x, y), or -1. */
function findTile(items: readonly Draw[], layer: 0 | 1 | 2, x: number, y: number, structure: (d: TileDraw) => StructureMark): number {
  let found = -1;
  const px = Math.floor(x), py = Math.floor(y);
  for (let i = 0; i < items.length; i++) {
    const d = items[i];
    if (d.kind !== "tile" || d.layer !== layer || d.effect !== "none") continue;
    const tx = px - d.x, ty = py - d.y;
    if (tx < 0 || tx >= 24 || ty < 0 || ty >= 28) continue;
    if (layer !== 0 && d.tile[ty * 24 + tx] === 0) continue;
    if (structure(d) !== StructureMark.None) found = i;
  }
  return found;
}
