// Draws the original paints over completely (DECISIONS.md D183).
//
// The C draws a frame back to front into one 320x200 buffer: a sprite whose every opaque pixel a
// later opaque sprite overwrites leaves nothing on screen. Here every draw is a model, flat art or an
// extruded sprite at its pass's height (D5), and a later model hides an earlier one only where it has
// geometry in front of it: GYGES's green orb `newshh-91` is drawn before the drill column's tiles
// (`newshh-85`/`-87`, opaque 24x28 blocks whose wall background hides the orb in the original), and
// its sphere showed round the column, where the column's sprite had wall, not geometry (QA M1).
//
// So a tick's draw list is read back to front once (when it arrives, not every display frame): each
// sprite is tested against the opaque pixels of the sprites drawn after it, then adds its own. A
// sprite with an opaque pixel inside the seen playfield and none left uncovered there is left out of
// the frame, as it was in the original. A grouped object (one enemy model over its tiles, D15) goes
// only when every tile of it is covered: one model can't show a part of itself.
//
// Only draws drawn solid in 3D cover: not "blend" (translucent) or "darken" (shadows), and not the
// shot, explosion and effect passes, which the remastered effects draw as glows and halos (D35).
// The test uses the sim's own integer positions, so it is the C's answer for that tick.

import { decodeSprite2, decodeTableSprite, type DecodedSprite } from "../data/sprites";
import { Pass, type Draw, type SpriteDraw, type SpriteTable, type TableSpriteDraw } from "../sim/draw";
import { PLAYFIELD_VISIBLE, type VisibleRect } from "./remaster/opaqueCover";
import { composeSprite2x2 } from "./spriteMesh";

/** Passes whose sprites don't hide what is under them in 3D: the remastered effects' glows (D35). */
const SEE_THROUGH_PASSES = new Set<Pass>([Pass.PlayerShots, Pass.EnemyShots, Pass.Explosions, Pass.Effects]);

/** A draw's state after the test: nothing seen in the playfield, every seen pixel covered, or some showing. */
const enum Seen {
  None = 0,
  Covered = 1,
  Shows = 2,
}

type SpriteLike = SpriteDraw | TableSpriteDraw;

/** Whether a sprite draw's pixels hide what was drawn under them, in the original and in 3D. */
export function paintsOver(d: SpriteLike): boolean {
  return (d.effect === "none" || d.effect === "filter" || d.effect === "hv") && !SEE_THROUGH_PASSES.has(d.pass);
}

export class PaintedOver {
  private readonly painted: Uint8Array;
  private seen = new Uint8Array(0);
  private hidden = new Uint8Array(0);
  private count = 0;
  private readonly sprites = new Map<string, DecodedSprite>();
  private readonly tables = new WeakMap<SpriteTable, Map<number, DecodedSprite>>();

  constructor(private readonly visible: VisibleRect = PLAYFIELD_VISIBLE) {
    this.painted = new Uint8Array((visible.x1 - visible.x0) * (visible.y1 - visible.y0));
  }

  /** Work out which of a tick's draws the later ones paint over. */
  update(items: readonly Draw[]): void {
    const n = items.length;
    if (this.seen.length < n) {
      this.seen = new Uint8Array(n * 2);
      this.hidden = new Uint8Array(n * 2);
    }
    this.count = n;
    const seen = this.seen;
    const hidden = this.hidden;
    seen.fill(0, 0, n);
    hidden.fill(0, 0, n);
    this.painted.fill(0);
    for (let i = n - 1; i >= 0; i--) {
      const d = items[i];
      if ((d.kind !== "sprite2" && d.kind !== "sprite") || d.effect === "darken") continue;
      const s = this.mask(d);
      if (s) seen[i] = this.test(s, Math.round(d.x), Math.round(d.y), paintsOver(d));
    }
    // A grouped object's tiles are drawn one after another, its first tile first (blit_enemy): it is
    // hidden only when none of its tiles shows and some tile is covered.
    for (let i = 0; i < n; i++) {
      const d = items[i];
      if (d.kind !== "sprite2" && d.kind !== "sprite") continue;
      if (d.kind === "sprite" || d.groupIndex < 0 || !d.groupFirst) {
        hidden[i] = seen[i] === Seen.Covered ? 1 : 0;
        continue;
      }
      let end = i + 1;
      while (end < n && sameObject(d, items[end])) end++;
      let state: Seen = Seen.None;
      for (let j = i; j < end; j++) state = Math.max(state, seen[j]);
      hidden.fill(state === Seen.Covered ? 1 : 0, i, end);
      i = end - 1;
    }
  }

  /** Whether draw `i` of the list last given to update is painted over by later draws. */
  hides(i: number): boolean {
    return i < this.count && this.hidden[i] === 1;
  }

  /**
   * Test a sprite's opaque pixels at screen (x, y) against what later draws painted, and paint them
   * when it covers too.
   */
  private test(s: DecodedSprite, x: number, y: number, paints: boolean): Seen {
    const v = this.visible;
    const w = v.x1 - v.x0;
    const painted = this.painted;
    const c0 = Math.max(0, v.x0 - x), c1 = Math.min(s.width, v.x1 - x);
    const r0 = Math.max(0, v.y0 - y), r1 = Math.min(s.height, v.y1 - y);
    let seen = 0;
    let open = 0;
    for (let r = r0; r < r1; r++) {
      const row = r * s.width;
      const at = (y + r - v.y0) * w + (x - v.x0);
      for (let c = c0; c < c1; c++) {
        if (s.pixels[row + c] < 0) continue;
        seen++;
        if (painted[at + c] === 0) {
          open++;
          if (paints) painted[at + c] = 1;
        }
      }
    }
    return seen === 0 ? Seen.None : open === 0 ? Seen.Covered : Seen.Shows;
  }

  private mask(d: SpriteLike): DecodedSprite | null {
    if (d.kind === "sprite2") {
      const key = `${d.sheet.id}|${d.index}|${d.size}`;
      let s = this.sprites.get(key);
      if (!s) this.sprites.set(key, (s = d.size === 2 ? composeSprite2x2(d.sheet.data, d.index) : decodeSprite2(d.sheet.data, d.index)));
      return s;
    }
    let m = this.tables.get(d.table);
    if (!m) this.tables.set(d.table, (m = new Map()));
    let s = m.get(d.index);
    if (s === undefined) {
      const sprite = d.table.sprites[d.index];
      m.set(d.index, (s = sprite ? decodeTableSprite(sprite) : { width: 0, height: 0, pixels: new Int16Array(0) }));
    }
    return s;
  }
}

/** Whether draw `e` is a later tile of the object whose first tile is `first`. */
function sameObject(first: SpriteDraw, e: Draw): boolean {
  return e.kind === "sprite2" && !e.groupFirst && e.groupIndex === first.groupIndex && e.groupSize === first.groupSize && e.pass === first.pass;
}
