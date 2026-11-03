// Which model draws an enemy's damaged frame (DECISIONS.md D79, docs/agents/DAMAGE-FRAMES.md).
//
// When an enemy is hit hard enough the game swaps it to a damaged frame (game.ts: edgr, edani).
// A damaged frame with a model of its own (spriteModels/*.json) is drawn with it, like any frame.
// That is kept for the few frames whose damage grows a new shape past the intact outline (the
// level-1 boss's wrecked arms). Every other damaged frame is drawn with the enemy's intact model,
// damaged by the difference between the two sprite frames (damageFrames.ts, damageShader.ts).
//
// This file is the routing half, shared by the renderer and the model-swap test
// (Sprite2Router.route): which intact model and which of its frames draw a damaged frame. Pure: no
// three.js.

import { decodeSprite2 } from "../../data/sprites";
import type { Sprite2Sheet } from "../../sim/draw";
import type { LevelDamage } from "../../sim/levelSprites";
import { spriteModelKey } from "../spriteModels";

/** A damaged frame drawn with an intact model: the model and the intact frame it shows. */
export interface DamageRoute {
  model: string;
  normal: number;
}

/** How a damaged frame differs from its intact frame, as shares of the intact frame's pixels. */
export interface DamageStats {
  /** Opaque pixels of the intact frame. */
  area: number;
  /** Gone (transparent in the damaged frame). */
  removed: number;
  /** Kept but another colour. */
  changed: number;
  /** Opaque in the damaged frame only (outside the intact outline). */
  added: number;
}

export type DamageKind = "blank" | "same" | "newShape" | "damage";

/**
 * Frames whose damage adds more than this share of new pixels outside the intact outline grow a new
 * shape, which a cut and repaint of the intact model can't show: those get a model of their own.
 */
export const NEW_SHAPE_ADDED = 0.25;

export function damageStats(normal: Int16Array, damaged: Int16Array): DamageStats {
  let area = 0;
  let removed = 0;
  let changed = 0;
  let added = 0;
  for (let i = 0; i < normal.length; i++) {
    const a = normal[i];
    const b = damaged[i];
    if (a < 0) {
      if (b >= 0) added++;
      continue;
    }
    area++;
    if (b < 0) removed++;
    else if (a !== b) changed++;
  }
  const n = Math.max(1, area);
  return { area, removed: removed / n, changed: changed / n, added: added / n };
}

export function damageKind(s: DamageStats, damaged: Int16Array): DamageKind {
  if (!damaged.some((p) => p >= 0)) return "blank";
  if (s.added > NEW_SHAPE_ADDED) return "newShape";
  if (s.removed + s.changed + s.added < 0.02) return "same";
  return "damage";
}

/** A frame's pixels: a 12x14 sprite, or a 2x2 group (index, +1, +19, +20) as 24x28, row-major. */
export function framePixels(sheet: Sprite2Sheet | Uint8Array, size: 1 | 2, index: number): Int16Array {
  const data = sheet instanceof Uint8Array ? sheet : sheet.data;
  const w = size === 2 ? 24 : 12;
  const h = size === 2 ? 28 : 14;
  const out = new Int16Array(w * h).fill(-1);
  const parts: [number, number, number][] = size === 2 ? [[0, 0, 0], [1, 12, 0], [19, 0, 14], [20, 12, 14]] : [[0, 0, 0]];
  for (const [di, ox, oy] of parts) {
    const s = decodeSprite2(data, index + di);
    for (let y = 0; y < Math.min(14, s.height); y++) {
      for (let x = 0; x < 12; x++) out[(oy + y) * w + ox + x] = s.pixels[y * 12 + x];
    }
  }
  return out;
}

/**
 * Of an enemy's intact frames, the one a damaged frame is drawn over: the one with a model whose
 * pixels it matches best (an animated enemy's damage replaces whichever frame it was on).
 */
export function bestNormal(
  sheet: Sprite2Sheet | Uint8Array,
  size: 1 | 2,
  damaged: Int16Array,
  normals: readonly number[],
  hasModel: (frame: number) => boolean = () => true,
): { normal: number; pixels: Int16Array } | null {
  let best: { normal: number; pixels: Int16Array; score: number } | null = null;
  for (const n of normals) {
    if (!hasModel(n)) continue;
    const px = framePixels(sheet, size, n);
    let score = 0;
    for (let i = 0; i < px.length; i++) if (px[i] !== damaged[i]) score++;
    if (!best || score < best.score) best = { normal: n, pixels: px, score };
  }
  return best && { normal: best.normal, pixels: best.pixels };
}

/** The current level's damaged frames, and which intact model draws each. */
export class DamageRoutes {
  /** sheet|size|damaged frame -> the enemy's intact frames. */
  private readonly normals = new Map<string, number[]>();
  private readonly routes = new Map<string, DamageRoute | null>();

  /** The level's damaged frames (sim/levelSprites.ts levelDamageFrames). Adds to what's known. */
  addLevel(damage: readonly LevelDamage[] | undefined): void {
    for (const d of damage ?? []) {
      for (const f of d.damaged) {
        const key = spriteModelKey(d.sheet, d.size, f);
        const had = this.normals.get(key);
        const merged = had ? [...new Set([...had, ...d.normal])] : [...d.normal];
        if (!had || merged.length !== had.length) {
          this.normals.set(key, merged);
          this.routes.delete(key);
        }
      }
    }
  }

  /**
   * The intact model that draws damaged frame `frame` of `sheet`, or null: not a damaged frame, no
   * intact frame has a model, or it draws nothing (a destroyed piece's blank frame).
   */
  resolve(sheet: Sprite2Sheet, size: 1 | 2, frame: number, modelOf: (key: string) => string | undefined): DamageRoute | null {
    const key = spriteModelKey(sheet.id, size, frame);
    let r = this.routes.get(key);
    if (r !== undefined) return r;
    r = null;
    const normals = this.normals.get(key);
    if (normals) {
      const damaged = framePixels(sheet, size, frame);
      const best = damaged.some((p) => p >= 0) ? bestNormal(sheet, size, damaged, normals, (n) => modelOf(spriteModelKey(sheet.id, size, n)) !== undefined) : null;
      if (best) r = { model: modelOf(spriteModelKey(sheet.id, size, best.normal))!, normal: best.normal };
    }
    this.routes.set(key, r);
    return r;
  }
}
