// How the renderer draws one Sprite2 draw (DECISIONS.md D4, D15, D42, D49, D54): as flat art, as part
// of a model (an enemy's, a player ship's banking frames, a sidekick's), or as the extruded sprite.
//
// The decision only depends on the draw and on which sprites have models and art, never on what has
// loaded, so drawListRenderer.ts and the model-swap check (tests/render/modelSwap.test.ts) share it:
// whatever the check says about a level's draws is what the renderer does with them.

import type { SpriteDraw } from "../sim/draw";
import { spriteModelKey, type ModelOverride, type SpriteModels } from "./spriteModels";
import { SPRITE2X2_PARTS } from "./spriteArt";

/** A sheet's flat art (SpriteArtSheet): frame(index) is defined where a painting is ready. */
export interface ArtFrames {
  frame(index: number): unknown;
}

export const enum Route {
  /** The extruded sprite. */
  Sprite,
  /** Flat remastered art (D42). */
  Flat,
  /** One tile of a grouped object (an enemy) whose model replaces the whole object (D15). */
  Group,
  /** A player ship's sprite or banking frame (D4). */
  Override,
  /** A sprite drawn on its own, like a sidekick (D49). */
  Ungrouped,
}

/** The result of Sprite2Router.route; one object, reused. */
export interface Sprite2Route {
  route: Route;
  /** Model path in public/models/ (Group, Override, Ungrouped). */
  model: string;
  /** Override: the ship and its bank, -1..1. Group: the grouped ship's bank, or NaN. */
  override: ModelOverride | null;
  bank: number;
}

export class Sprite2Router {
  private readonly grouped: ReadonlyMap<string, string>;
  private readonly groupBank: ReadonlyMap<string, number>;
  private readonly ungrouped: ReadonlyMap<string, string>;
  private readonly overridesBySheet = new Map<string, ModelOverride[]>();
  private readonly out: Sprite2Route = { route: Route.Sprite, model: "", override: null, bank: Number.NaN };

  constructor(models: SpriteModels = { grouped: new Map(), banked: [], groupBank: new Map(), ungrouped: new Map() }) {
    this.grouped = models.grouped;
    this.groupBank = models.groupBank ?? new Map();
    this.ungrouped = models.ungrouped ?? new Map();
    for (const o of models.banked) {
      let list = this.overridesBySheet.get(o.sheetId);
      if (!list) this.overridesBySheet.set(o.sheetId, (list = []));
      list.push(o);
    }
  }

  /** Every model path the router can route to. */
  models(): Set<string> {
    const out = new Set<string>([...this.grouped.values(), ...this.ungrouped.values()]);
    for (const list of this.overridesBySheet.values()) for (const o of list) out.add(o.model);
    return out;
  }

  /**
   * The model sprite `index` of sheet `sheetId` is drawn as, if any (whatever the art): as the
   * first tile of a grouped object (an enemy, a two-half ship) when `grouped`, else drawn on its own
   * (a player ship's frame, a sidekick). For preloading (DrawListRenderer.preloadLevel).
   */
  modelFor(sheetId: string, size: 1 | 2, index: number, grouped: boolean): string | undefined {
    if (grouped) return this.grouped.get(spriteModelKey(sheetId, size, index));
    for (const o of this.overridesBySheet.get(sheetId) ?? []) {
      const offset = index - o.baseIndex;
      if (size === o.size && offset % o.bankStep === 0 && Math.abs(offset) <= o.bankStep * o.maxBank) return o.model;
    }
    return this.ungrouped.get(spriteModelKey(sheetId, size, index));
  }

  /** The models of `sprites` (sim/levelSprites.ts), for preloading a level. */
  modelsOf(sprites: Iterable<{ sheet: string; size: 1 | 2; index: number; grouped: boolean }>): Set<string> {
    const out = new Set<string>();
    for (const r of sprites) {
      const model = this.modelFor(r.sheet, r.size, r.index, r.grouped);
      if (model !== undefined) out.add(model);
    }
    return out;
  }

  /**
   * How draw `d` is drawn. `art` is its sheet's flat art (null: none, or the original look);
   * `emptyTile(index)` says whether 12x14 sprite `index` of the draw's sheet has no pixels (a
   * blit_sprite2x2 with an empty quarter still draws flat). The result is reused by the next call.
   */
  route(d: SpriteDraw, art: ArtFrames | null, emptyTile: (index: number) => boolean): Sprite2Route {
    const out = this.out;
    out.model = "";
    out.override = null;
    out.bank = Number.NaN;
    // With flat art for the sprite (for a grouped one, the object's first tile), it's drawn flat
    // instead of as a model (D42); a tile without art is then drawn as its sprite.
    if (art !== null && art.frame(d.groupIndex >= 0 ? d.groupIndex : d.index) !== undefined) {
      out.route = flatComplete(d, art, emptyTile) ? Route.Flat : Route.Sprite;
      return out;
    }
    if (d.groupIndex >= 0) {
      const key = spriteModelKey(d.sheet.id, d.groupSize, d.groupIndex);
      const model = this.grouped.get(key);
      if (model !== undefined) {
        out.route = Route.Group;
        out.model = model;
        out.bank = this.groupBank.get(key) ?? Number.NaN;
        return out;
      }
    }
    const overrides = this.overridesBySheet.get(d.sheet.id);
    if (overrides) {
      for (const o of overrides) {
        const offset = d.index - o.baseIndex;
        if (d.size !== o.size || offset % o.bankStep !== 0 || Math.abs(offset) > o.bankStep * o.maxBank) continue;
        out.route = Route.Override;
        out.model = o.model;
        out.override = o;
        out.bank = offset / o.bankStep / o.maxBank;
        return out;
      }
    }
    if (d.groupIndex < 0) {
      const model = this.ungrouped.get(spriteModelKey(d.sheet.id, d.size, d.index));
      if (model !== undefined) {
        out.route = Route.Ungrouped;
        out.model = model;
        return out;
      }
    }
    out.route = Route.Sprite;
    return out;
  }
}

/** Whether every non-empty 12x14 tile of the draw has art (addFlatSprite2 can draw it all flat). */
function flatComplete(d: SpriteDraw, art: ArtFrames, emptyTile: (index: number) => boolean): boolean {
  if (d.size === 1) return art.frame(d.index) !== undefined;
  for (const [di] of SPRITE2X2_PARTS) if (art.frame(d.index + di) === undefined && !emptyTile(d.index + di)) return false;
  return true;
}
