// [proposal: damage frames] Drawing an enemy's damaged frames with its intact model (?damage=a|b).
//
// On main a damaged frame without a model of its own is drawn as the extruded sprite (D54,
// KNOWN_DAMAGE_SWAPS). Here, when a draw's frame is one of the level's damaged frames
// (sim/levelSprites.ts levelDamageFrames) and the enemy's normal frame has a model, it is drawn with
// that model, damaged:
//
// - A: by the difference between the normal and the damaged sprite frame, worked out here from the
//   sheet's pixels the first time the frame is drawn (no baking, no per-enemy data): see
//   damageShader.ts for what each channel does.
// - B: by a generic level (light, heavy, wreck) chosen from how much of the sprite changed or went,
//   drawn as noise scorch and holes, with smoke and sparks.
//
// Which normal frame: of the enemy's normal frames that have a model, the one whose pixels the
// damaged frame matches best (an animated enemy's damage replaces whichever frame it was on).

import * as THREE from "three";
import { decodeSprite2 } from "../../data/sprites";
import type { Sprite2Sheet, SpriteDraw } from "../../sim/draw";
import type { LevelDamage } from "../../sim/levelSprites";
import type { PaletteTexture } from "../paletteTexture";
import { spriteModelKey } from "../spriteModels";
import { damageUniforms, patchDamage, type DamageUniforms } from "./damageShader";
import type { DamageMode } from "./damageMode";

/** How a damaged frame is drawn: the model of `normal`, damaged. */
export interface DamageState {
  model: string;
  normal: number;
  damaged: number;
  w: number;
  h: number;
  /** A: the mask and colour textures (damageShader.ts). */
  mask: THREE.DataTexture | null;
  color: THREE.DataTexture | null;
  /** Indices of the damaged frame's pixels (-1 transparent), to recolour on a palette change. */
  indices: Int16Array;
  normalIndices: Int16Array;
  paletteVersion: number;
  /** Shares of the normal frame's pixels that went, changed (of those kept), and that the damaged frame adds. */
  removed: number;
  changed: number;
  added: number;
  /** B: scorch, holes, embers (0..1) and how much smoke and sparks per second. */
  level: 1 | 2 | 3;
  params: THREE.Vector4;
  smoke: number;
}

/** A model clone's damage uniforms (one set shared by its materials). */
interface CloneDamage {
  uniforms: DamageUniforms;
  shells: THREE.Material[];
  shellsHidden: boolean;
  patched: THREE.Material[];
  twoSided: boolean;
}

const LUMA = (r: number, g: number, b: number) => 0.299 * r + 0.587 * g + 0.114 * b;

export class DamageFrames {
  /** sheet|size|damaged frame -> its normal frames. */
  private readonly normals = new Map<string, number[]>();
  private readonly states = new Map<string, DamageState | null>();
  private readonly clones = new WeakMap<THREE.Object3D, CloneDamage>();
  private readonly colour = new THREE.Color();

  constructor(
    readonly mode: DamageMode,
    private readonly palette: PaletteTexture,
    /** The model of a grouped frame (spriteModelKey), if any. */
    private readonly modelOf: (key: string) => string | undefined,
  ) {}

  /** The current level's damaged frames (LevelModelInfo.damage). */
  setLevel(damage: readonly LevelDamage[] | undefined): void {
    for (const d of damage ?? []) {
      for (const f of d.damaged) {
        const key = spriteModelKey(d.sheet, d.size, f);
        const had = this.normals.get(key) ?? [];
        this.normals.set(key, [...new Set([...had, ...d.normal])]);
      }
    }
  }

  /** How draw `d` (a grouped tile drawn as its sprite) is drawn damaged, or null if it isn't. */
  resolve(d: SpriteDraw): DamageState | null {
    if (d.groupIndex < 0) return null;
    const key = spriteModelKey(d.sheet.id, d.groupSize, d.groupIndex);
    let s = this.states.get(key);
    if (s === undefined) this.states.set(key, (s = this.build(d.sheet, d.groupSize, d.groupIndex, key)));
    if (s && s.mask && s.paletteVersion !== this.palette.version) this.recolour(s);
    return s;
  }

  private build(sheet: Sprite2Sheet, size: 1 | 2, damaged: number, key: string): DamageState | null {
    const normals = this.normals.get(key);
    if (!normals) return null;
    const dpx = framePixels(sheet, size, damaged);
    let best: { normal: number; model: string; px: Int16Array; score: number } | null = null;
    for (const n of normals) {
      const model = this.modelOf(spriteModelKey(sheet.id, size, n));
      if (model === undefined) continue;
      const npx = framePixels(sheet, size, n);
      let score = 0;
      for (let i = 0; i < npx.length; i++) if (npx[i] !== dpx[i]) score++;
      if (!best || score < best.score) best = { normal: n, model, px: npx, score };
    }
    if (!best) return null;
    const w = size === 2 ? 24 : 12;
    const h = size === 2 ? 28 : 14;
    const npx = best.px;
    let area = 0;
    let removed = 0;
    let changed = 0;
    let added = 0;
    const mask = new Uint8Array(w * h * 4);
    for (let i = 0; i < w * h; i++) {
      const a = npx[i];
      const b = dpx[i];
      if (a < 0) {
        if (b >= 0) added++;
        continue;
      }
      area++;
      if (b < 0) {
        removed++;
        mask[i * 4] = 255;
        continue;
      }
      if (a === b) continue;
      changed++;
      const ca = this.palette.color(a, this.colour);
      const la = LUMA(ca.r, ca.g, ca.b);
      const ra = ca.r;
      const cb = this.palette.color(b, this.colour);
      const lb = LUMA(cb.r, cb.g, cb.b);
      // Darker: scorch. Hot: red-orange and brighter in red than it was (embers, fire showing).
      const darker = Math.max(0, Math.min(1, (la - lb) / Math.max(la, 0.05)));
      const hot = cb.r > 0.45 && cb.r > cb.g * 1.6 && cb.r > cb.b * 1.6 && cb.r > ra + 0.1 ? Math.min(1, (cb.r - 0.35) * 2) : 0;
      mask[i * 4 + 1] = Math.round(darker * 0.35 * 255);
      mask[i * 4 + 2] = Math.round(hot * 255);
      mask[i * 4 + 3] = 255;
    }
    // Pixels transparent in both frames next to ones that went: gone too, so a model's overhang past
    // its sprite's outline (bevels, the outline shell's margin) goes with them.
    for (let pass = 0; pass < 2; pass++) {
      const grow: number[] = [];
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const i = y * w + x;
          if (mask[i * 4] || npx[i] >= 0 || dpx[i] >= 0) continue;
          for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
            const xx = x + dx;
            const yy = y + dy;
            if (xx >= 0 && yy >= 0 && xx < w && yy < h && mask[(yy * w + xx) * 4] === 255) {
              grow.push(i);
              break;
            }
          }
        }
      }
      for (const i of grow) mask[i * 4] = 255;
    }
    const texture = (data: Uint8Array, colorSpace: THREE.ColorSpace) => {
      const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat, THREE.UnsignedByteType);
      t.magFilter = THREE.LinearFilter;
      t.minFilter = THREE.LinearFilter;
      t.generateMipmaps = false;
      t.colorSpace = colorSpace;
      t.needsUpdate = true;
      return t;
    };
    const fr = (v: number) => v / Math.max(1, area);
    const rm = fr(removed);
    const ch = fr(changed);
    // B's three levels, picked from the same numbers (in a real B a small table per enemy, or this).
    const level: 1 | 2 | 3 = rm > 0.4 ? 3 : rm > 0.1 || ch > 0.45 ? 2 : 1;
    const params = level === 3 ? new THREE.Vector4(0.9, 0.45, 1, 0) : level === 2 ? new THREE.Vector4(0.75, 0.16, 1, 0) : new THREE.Vector4(0.5, 0, 0.7, 0);
    params.w = (damaged * 7.31) % 13;
    // A frame that shows the same picture (the boss's 242, 280): nothing to draw.
    const same = rm + ch < 0.02;
    if (same) params.set(0, 0, 0, params.w);
    const s: DamageState = {
      model: best.model,
      normal: best.normal,
      damaged,
      w,
      h,
      mask: this.mode === "a" ? texture(mask, THREE.NoColorSpace) : null,
      color: this.mode === "a" ? texture(new Uint8Array(w * h * 4), THREE.NoColorSpace) : null,
      indices: dpx,
      normalIndices: npx,
      paletteVersion: -1,
      removed: rm,
      changed: ch,
      added: fr(added),
      level,
      params,
      smoke: same ? 0 : level === 3 ? 3 : level === 2 ? 1.5 : 0.5,
    };
    if (s.mask) this.recolour(s);
    return s;
  }

  /**
   * A's colour texture from the live palette: per pixel the tint that turns the intact frame's colour
   * into the damaged one's (damaged / intact, linear, stored halved so up to 2x fits), 1 where
   * nothing changed. A multiplier rather than the damaged colour, so the model keeps its own shading
   * and the sprite's painted-in light isn't laid over it twice. Transparent pixels take a neighbour's.
   */
  private recolour(s: DamageState): void {
    const data = s.color!.image.data as Uint8Array;
    const { w, h, indices, normalIndices } = s;
    const tint = new Float32Array(w * h * 3).fill(1);
    const has = new Uint8Array(w * h);
    const a = new THREE.Color();
    const b = new THREE.Color();
    for (let i = 0; i < w * h; i++) {
      const n = normalIndices[i];
      const d = indices[i];
      if (n < 0 || d < 0) continue;
      has[i] = 1;
      if (n === d) continue;
      this.palette.color(n, a);
      this.palette.color(d, b);
      tint[i * 3] = Math.min(2, b.r / Math.max(a.r, 0.04));
      tint[i * 3 + 1] = Math.min(2, b.g / Math.max(a.g, 0.04));
      tint[i * 3 + 2] = Math.min(2, b.b / Math.max(a.b, 0.04));
    }
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        let j = y * w + x;
        // Bleed into empty pixels so bilinear filtering at the edges doesn't pull in plain 1.
        for (let r = 1; !has[j] && r < 3; r++) {
          for (const [dx, dy] of [[r, 0], [-r, 0], [0, r], [0, -r]]) {
            const xx = x + dx;
            const yy = y + dy;
            if (xx >= 0 && yy >= 0 && xx < w && yy < h && has[yy * w + xx]) {
              j = yy * w + xx;
              break;
            }
          }
        }
        const o = (y * w + x) * 4;
        for (let k = 0; k < 3; k++) data[o + k] = Math.round(tint[j * 3 + k] * 0.5 * 255);
        data[o + 3] = 255;
      }
    }
    s.color!.needsUpdate = true;
    s.paletteVersion = this.palette.version;
  }

  /**
   * Set a placed clone's damage (null: intact). Its materials are patched the first time. With
   * anything cut away the outline shell is hidden: OutlineEffect's outline material doesn't run the
   * patch, so it would still draw the intact silhouette (a production version would extend it).
   */
  apply(object: THREE.Object3D, materials: readonly THREE.Material[], s: DamageState | null): void {
    let c = this.clones.get(object);
    if (!c) {
      const uniforms = damageUniforms();
      const shells: THREE.Material[] = [];
      const patched: THREE.Material[] = [];
      for (const m of materials) {
        if (m.userData.outlineShell) shells.push(m);
        else if (patchDamage(m, uniforms)) patched.push(m);
      }
      this.clones.set(object, (c = { uniforms, shells, shellsHidden: false, patched, twoSided: false }));
    }
    const u = c.uniforms;
    if (!s) {
      u.uDmgOn.value = 0;
      this.showShells(c, true);
      this.twoSided(c, false);
      return;
    }
    u.uDmgOn.value = 1;
    u.uDmgMode.value = this.mode === "a" ? 0 : 1;
    object.updateMatrixWorld(true);
    u.uDmgInv.value.copy(object.matrixWorld).invert();
    u.uDmgSize.value.set(s.w, s.h);
    u.uDmgMask.value = s.mask;
    u.uDmgColor.value = s.color;
    u.uDmgParams.value.copy(s.params);
    const cuts = this.mode === "a" ? s.removed > 0.03 : s.params.y > 0;
    this.showShells(c, !cuts);
    this.twoSided(c, cuts);
  }

  /** While cut, the materials draw their back faces too (charred), so a cut shows a wall, not a gap. */
  private twoSided(c: CloneDamage, on: boolean): void {
    if (c.twoSided === on) return;
    c.twoSided = on;
    for (const m of c.patched) m.side = on ? THREE.DoubleSide : THREE.FrontSide;
  }

  private showShells(c: CloneDamage, show: boolean): void {
    if (c.shellsHidden === !show) return;
    c.shellsHidden = !show;
    for (const m of c.shells) (m.userData.outlineParameters as { visible?: boolean }).visible = show;
  }
}

/** A frame's pixels: a 12x14 sprite, or a 2x2 group (index, +1, +19, +20) as 24x28. */
export function framePixels(sheet: Sprite2Sheet, size: 1 | 2, index: number): Int16Array {
  const w = size === 2 ? 24 : 12;
  const h = size === 2 ? 28 : 14;
  const out = new Int16Array(w * h).fill(-1);
  const parts: [number, number, number][] = size === 2 ? [[0, 0, 0], [1, 12, 0], [19, 0, 14], [20, 12, 14]] : [[0, 0, 0]];
  for (const [di, ox, oy] of parts) {
    const s = decodeSprite2(sheet.data, index + di);
    for (let y = 0; y < Math.min(14, s.height); y++) {
      for (let x = 0; x < 12; x++) out[(oy + y) * w + ox + x] = s.pixels[y * 12 + x];
    }
  }
  return out;
}
