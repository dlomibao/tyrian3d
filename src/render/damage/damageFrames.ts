// An enemy's damaged frame drawn with its intact model (DECISIONS.md D87).
//
// Sprite2Router (damageRoute.ts) says which intact model and frame draw a damaged frame. This builds,
// the first time the frame is drawn, what the model's shaders (damageShader.ts) need to damage it:
// textures of the difference between the intact and the damaged sprite frame, from the sheet's own
// pixels (no baking, no per-enemy data). Then, every frame, it sets each placed clone's uniforms:
// its damage, or none (clones are pooled per model and drawn for whichever enemy comes next).

import * as THREE from "three";
import type { SpriteDraw } from "../../sim/draw";
import { isModelHelper } from "../modelPrep";
import type { PaletteTexture } from "../paletteTexture";
import { spriteModelKey } from "../spriteModels";
import { damageDepthMaterial, damageUniforms, patchDamage, type DamageUniforms } from "./damageShader";
import { damageStats, framePixels } from "./damageRoute";
import type { ShipCondition } from "./shipDamage";

/** What the shaders need to draw one damaged frame over one intact frame. */
export interface DamageState {
  w: number;
  h: number;
  mask: THREE.DataTexture;
  tint: THREE.DataTexture;
  paint: THREE.DataTexture;
  /** The two frames' palette indices (-1 transparent), to recolour on a palette change. */
  normal: Int16Array;
  damaged: Int16Array;
  paletteVersion: number;
  /** Anything cut away: the materials go two-sided (a charred inside). */
  cuts: boolean;
  /** Nothing to draw (the same picture): the clone is drawn intact. */
  same: boolean;
}

/** A model clone's damage uniforms (one set shared by its materials) and its patched materials. */
interface CloneDamage {
  uniforms: DamageUniforms;
  patched: THREE.Material[];
  twoSided: boolean;
}

const LUMA = (c: THREE.Color) => 0.299 * c.r + 0.587 * c.g + 0.114 * c.b;

export class DamageFrames {
  /** sheet|size|damaged|normal -> its textures. */
  private readonly states = new Map<string, DamageState>();
  private readonly clones = new WeakMap<THREE.Object3D, CloneDamage>();
  private readonly a = new THREE.Color();
  private readonly b = new THREE.Color();

  constructor(private readonly palette: PaletteTexture) {}

  /** The damage of draw `d` (a damaged frame) drawn over intact frame `normal`. */
  state(d: SpriteDraw, normal: number): DamageState {
    const key = `${spriteModelKey(d.sheet.id, d.groupSize, d.groupIndex)}|${normal}`;
    let s = this.states.get(key);
    if (!s) this.states.set(key, (s = this.build(framePixels(d.sheet, d.groupSize, normal), framePixels(d.sheet, d.groupSize, d.groupIndex), d.groupSize)));
    if (s.paletteVersion !== this.palette.version) this.colour(s);
    return s;
  }

  private build(normal: Int16Array, damaged: Int16Array, size: 1 | 2): DamageState {
    const w = size === 2 ? 24 : 12;
    const h = size === 2 ? 28 : 14;
    const stats = damageStats(normal, damaged);
    const texture = () => {
      const t = new THREE.DataTexture(new Uint8Array(w * h * 4), w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
      t.magFilter = THREE.LinearFilter;
      t.minFilter = THREE.LinearFilter;
      t.generateMipmaps = false;
      t.colorSpace = THREE.NoColorSpace;
      return t;
    };
    return {
      w,
      h,
      mask: texture(),
      tint: texture(),
      paint: texture(),
      normal,
      damaged,
      paletteVersion: -1,
      cuts: stats.removed > 0,
      same: stats.removed + stats.changed < 0.005,
    };
  }

  /**
   * Fill the textures from the live palette (palettes change between levels and with fades).
   * mask: r = gone, g = darker, b = hot, a = changed colour. tint: damaged / intact (halved) and
   * how much to replace instead. paint: the damaged colours. Linear values.
   */
  private colour(s: DamageState): void {
    const { w, h, normal, damaged } = s;
    const mask = s.mask.image.data as Uint8Array;
    const tint = s.tint.image.data as Uint8Array;
    const paint = s.paint.image.data as Uint8Array;
    mask.fill(0);
    const has = new Uint8Array(w * h);
    const t = new Float32Array(w * h * 4);
    const p = new Float32Array(w * h * 3);
    for (let i = 0; i < w * h; i++) {
      t[i * 4] = t[i * 4 + 1] = t[i * 4 + 2] = 1;
      const n = normal[i];
      const d = damaged[i];
      if (n < 0) continue;
      if (d < 0) {
        mask[i * 4] = 255;
        continue;
      }
      has[i] = 1;
      const a = this.palette.color(n, this.a);
      const b = this.palette.color(d, this.b);
      p[i * 3] = b.r;
      p[i * 3 + 1] = b.g;
      p[i * 3 + 2] = b.b;
      if (n === d) continue;
      // Darker: scorch. Hot: red-orange and redder than it was (embers, fire showing through).
      const la = LUMA(a);
      const lb = LUMA(b);
      const darker = Math.max(0, Math.min(1, (la - lb) / Math.max(la, 0.05)));
      const hot = b.r > 0.45 && b.r > b.g * 1.6 && b.r > b.b * 1.6 && b.r > a.r + 0.1 ? Math.min(1, (b.r - 0.35) * 2) : 0;
      mask[i * 4 + 1] = Math.round(darker * 0.35 * 255);
      mask[i * 4 + 2] = Math.round(hot * 255);
      mask[i * 4 + 3] = 255;
      // The multiplier, and where it would have to go past 2x (a new hue from a dark channel), how
      // much to replace with the damaged colour instead.
      let over = 0;
      for (let k = 0; k < 3; k++) {
        const ca = k === 0 ? a.r : k === 1 ? a.g : a.b;
        const cb = k === 0 ? b.r : k === 1 ? b.g : b.b;
        const ratio = cb / Math.max(ca, 0.02);
        over = Math.max(over, ratio);
        t[i * 4 + k] = Math.min(2, ratio);
      }
      t[i * 4 + 3] = Math.min(1, Math.max(0, (over - 1.6) / 0.8));
    }
    // Pixels transparent in both frames next to ones that went go too, so a model's overhang past
    // its sprite's outline (bevels, the outline shell's margin) goes with them.
    for (let pass = 0; pass < 2; pass++) {
      const grow: number[] = [];
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const i = y * w + x;
          if (mask[i * 4] || normal[i] >= 0 || damaged[i] >= 0) continue;
          if (neighbours(x, y, w, h).some((j) => mask[j * 4] === 255)) grow.push(i);
        }
      }
      for (const i of grow) mask[i * 4] = 255;
    }
    // Tint and paint bleed into empty pixels, so bilinear filtering at the edges doesn't pull in 1 or black.
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        let j = y * w + x;
        for (let r = 1; !has[j] && r < 3; r++) {
          const near = neighbours(x, y, w, h, r).find((k) => has[k]);
          if (near !== undefined) j = near;
        }
        const o = (y * w + x) * 4;
        for (let k = 0; k < 3; k++) {
          tint[o + k] = Math.round(t[j * 4 + k] * 0.5 * 255);
          paint[o + k] = Math.round(Math.min(1, p[j * 3 + k]) * 255);
        }
        tint[o + 3] = Math.round(t[j * 4 + 3] * 255);
        paint[o + 3] = 255;
      }
    }
    s.mask.needsUpdate = s.tint.needsUpdate = s.paint.needsUpdate = true;
    s.paletteVersion = this.palette.version;
  }

  /**
   * Set a placed clone's damage (null: intact). The first time, its materials are patched and its
   * meshes get a depth material with the same cut, so cut parts cast no shadow.
   */
  apply(object: THREE.Object3D, materials: readonly THREE.Material[], s: DamageState | null): void {
    const c = this.clone(object, materials);
    const u = c.uniforms;
    u.uDmgCover.value = -1;
    if (!s || s.same) {
      u.uDmgOn.value = 0;
      this.twoSided(c, false);
      return;
    }
    u.uDmgOn.value = 1;
    object.updateMatrixWorld(true);
    u.uDmgInv.value.copy(object.matrixWorld).invert();
    u.uDmgSize.value.set(s.w, s.h);
    u.uDmgMask.value = s.mask;
    u.uDmgTint.value = s.tint;
    u.uDmgPaint.value = s.paint;
    this.twoSided(c, s.cuts);
  }

  /**
   * Set a placed player ship's wear (D90): `ship` its condition (null or clean: drawn clean), `size`
   * its sprite's size in tiles. Paint only: never a cut.
   */
  applyShip(object: THREE.Object3D, materials: readonly THREE.Material[], ship: ShipCondition | null, size: 1 | 2): void {
    const c = this.clone(object, materials);
    const u = c.uniforms;
    this.twoSided(c, false);
    if (!ship || !ship.damaged) {
      u.uDmgOn.value = 0;
      return;
    }
    const w = size * 12;
    const h = size * 14;
    u.uDmgOn.value = 1;
    u.uDmgCover.value = ship.cover;
    u.uDmgHot.value = ship.hot;
    object.updateMatrixWorld(true);
    u.uDmgInv.value.copy(object.matrixWorld).invert();
    u.uDmgSize.value.set(w, h);
    u.uDmgMask.value = this.wearPattern(w, h);
    u.uDmgTint.value = null;
    u.uDmgPaint.value = null;
  }

  private readonly patterns = new Map<string, THREE.DataTexture>();

  /**
   * The ship's scorch pattern: blotches of value noise, g = the coverage each texel scorches at
   * (ranked, so coverage c scorches a share c of the texels), b = where embers glow. Fixed.
   */
  private wearPattern(w: number, h: number): THREE.DataTexture {
    const key = `${w}x${h}`;
    let t = this.patterns.get(key);
    if (t) return t;
    const n = w * h;
    const noise = (x: number, y: number, seed: number, cell: number) => {
      const hash = (i: number, j: number) => {
        const v = Math.sin(i * 127.1 + j * 311.7 + seed * 74.7) * 43758.5453;
        return v - Math.floor(v);
      };
      const fx = x / cell;
      const fy = y / cell;
      const i = Math.floor(fx);
      const j = Math.floor(fy);
      const u = fx - i;
      const v = fy - j;
      const su = u * u * (3 - 2 * u);
      const sv = v * v * (3 - 2 * v);
      const a = hash(i, j) + (hash(i + 1, j) - hash(i, j)) * su;
      const b = hash(i, j + 1) + (hash(i + 1, j + 1) - hash(i, j + 1)) * su;
      return a + (b - a) * sv;
    };
    const g = new Float32Array(n);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) g[y * w + x] = 0.65 * noise(x, y, 1, 4) + 0.35 * noise(x, y, 2, 2);
    const order = [...g.keys()].sort((a, b) => g[a] - g[b]);
    const data = new Uint8Array(n * 4);
    order.forEach((i, rank) => (data[i * 4 + 1] = Math.round((rank / (n - 1)) * 255)));
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) data[(y * w + x) * 4 + 2] = Math.round(noise(x, y, 3, 1.5) * 255);
    t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
    t.magFilter = THREE.LinearFilter;
    t.minFilter = THREE.LinearFilter;
    t.generateMipmaps = false;
    t.colorSpace = THREE.NoColorSpace;
    t.needsUpdate = true;
    this.patterns.set(key, t);
    return t;
  }

  /**
   * Patch a new model clone's materials up front (D91), intact (uDmgOn = 0 draws as unpatched), so
   * its first damaged frame swaps no shader and the level's warm-up compiles the patched programs.
   */
  prepare(object: THREE.Object3D, materials: readonly THREE.Material[]): void {
    this.clone(object, materials);
  }

  /** A clone's damage uniforms; the first time, its materials are patched and its depth material set. */
  private clone(object: THREE.Object3D, materials: readonly THREE.Material[]): CloneDamage {
    let c = this.clones.get(object);
    if (!c) {
      const uniforms = damageUniforms();
      const patched: THREE.Material[] = [];
      for (const m of materials) {
        // The outline shell draws only its outline: the outline pass cuts it (outlineEffect.js).
        if (m.userData.outlineShell) m.userData.damageUniforms = uniforms;
        else if (patchDamage(m, uniforms)) patched.push(m);
      }
      object.traverse((o) => {
        const mesh = o as THREE.Mesh;
        if (mesh.isMesh && !isModelHelper(mesh)) mesh.customDepthMaterial = damageDepthMaterial(uniforms);
      });
      this.clones.set(object, (c = { uniforms, patched, twoSided: false }));
    }
    return c;
  }

  /** While cut, the materials draw their back faces too (charred), so a cut shows a wall, not a gap. */
  private twoSided(c: CloneDamage, on: boolean): void {
    if (c.twoSided === on) return;
    c.twoSided = on;
    // Culling is GL state set per draw, so no recompile (back faces are flat char, unlit by intent).
    for (const m of c.patched) m.side = on ? THREE.DoubleSide : THREE.FrontSide;
  }
}

/** The 4-neighbours at distance `r` that are inside a w x h grid, as indices. */
function neighbours(x: number, y: number, w: number, h: number, r = 1): number[] {
  const out: number[] = [];
  for (const [dx, dy] of [[r, 0], [-r, 0], [0, r], [0, -r]]) {
    const xx = x + dx;
    const yy = y + dy;
    if (xx >= 0 && yy >= 0 && xx < w && yy < h) out.push(yy * w + xx);
  }
  return out;
}
