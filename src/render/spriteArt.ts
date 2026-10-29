// Remastered flat sprite art (DECISIONS.md D42): high-resolution paintings of the original sprites
// for shots and pickups, drawn as flat textured quads instead of extruded sprites or models.
//
// public/art/sprites/manifest.json lists, per original sprite sheet, an RGBA atlas image and where
// each sprite's painting is in it:
//
//   { "scale": 8,
//     "sheets": { "tyrian.shp#7": { "image": "tyrian.shp-7.webp",
//                                   "frames": { "1": { "x": 0, "y": 0, "w": 96, "h": 112 } } } } }
//
// The sheet key is the draw list's sheet id (Sprite2Sheet.id or SpriteTable.id, src/sim/draw.ts:
// "tyrian.shp#7".."tyrian.shp#11" for the Sprite2 sheets in tyrian.shp, "tyrian.shp#0".."#6" for
// its sprite tables, "newsh<c>.shp" for the enemy sheets), and the frame key is the draw's sprite
// index as the C passes it (1-based for Sprite2 sheets, 0-based for sprite tables). A frame is the
// original sprite's box times `scale`: 12 wide by the decoded height for a Sprite2 sprite, the
// table's width and height for a table sprite. A blit_sprite2x2 draw is the four 12x14 sprites
// index, index+1, index+19 and index+20, each with its own frame.
//
// This module is the pure part (parsing, lookup, placement); spriteArtLayer.ts draws.

import { PX_PER_UNIT, screenWorldX, screenWorldZ } from "../game/playfield";

/** How shots and pickups are drawn: the original sprites, or the remastered flat art. */
export type SpriteArtMode = "original" | "remastered";

/** One sprite's painting in its sheet's atlas, in atlas pixels (top-left origin). */
export interface SpriteArtFrame {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SpriteArtManifest {
  /** Atlas pixels per original pixel. */
  scale: number;
  sheets: Map<string, { image: string; frames: Map<number, SpriteArtFrame> }>;
}

const isCount = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v) && v >= 0;

/**
 * Check and index a manifest. Returns null if it isn't one (so the game draws the original
 * sprites); sheets and frames that are malformed are dropped with a warning, the rest kept.
 */
export function parseSpriteArtManifest(json: unknown, warn: (msg: string) => void = console.warn): SpriteArtManifest | null {
  if (typeof json !== "object" || json === null) return null;
  const { scale, sheets } = json as { scale?: unknown; sheets?: unknown };
  if (!isCount(scale) || scale <= 0 || typeof sheets !== "object" || sheets === null) return null;
  const out: SpriteArtManifest = { scale, sheets: new Map() };
  for (const [id, sheet] of Object.entries(sheets as Record<string, unknown>)) {
    const { image, frames } = (sheet ?? {}) as { image?: unknown; frames?: unknown };
    if (typeof image !== "string" || image === "" || typeof frames !== "object" || frames === null) {
      warn(`sprite art: sheet ${id} has no image or frames; drawing its sprites as before`);
      continue;
    }
    const map = new Map<number, SpriteArtFrame>();
    for (const [key, f] of Object.entries(frames as Record<string, unknown>)) {
      const index = Number(key);
      const { x, y, w, h } = (f ?? {}) as Record<string, unknown>;
      if (!Number.isInteger(index) || index < 0 || !isCount(x) || !isCount(y) || !isCount(w) || !isCount(h) || w === 0 || h === 0) {
        warn(`sprite art: ${id} frame ${key} is malformed; skipped`);
        continue;
      }
      map.set(index, { x, y, w, h });
    }
    if (map.size > 0) out.sheets.set(id, { image, frames: map });
  }
  return out;
}

/** The URL of a sheet's atlas, relative to the manifest's directory `dir` (ends in "/"). */
export function spriteArtImageUrl(dir: string, image: string): string {
  return dir + image.split("/").map(encodeURIComponent).join("/");
}

/**
 * A frame ready to draw: its texture rectangle (UV, v down from the top, as the atlas is uploaded
 * without a flip) and its size in original pixels.
 */
export interface ReadyFrame {
  u0: number;
  v0: number;
  u1: number;
  v1: number;
  /** Size in the original's pixels: the frame's size over the manifest's scale. */
  w: number;
  h: number;
}

/** One sheet's atlas and frames. `texture` is whatever the drawing side uses (a THREE.Texture). */
export class SpriteArtSheet<T = unknown> {
  /** Null until the atlas has loaded; until then the sheet's sprites draw as before. */
  texture: T | null = null;
  private readonly ready = new Map<number, ReadyFrame>();

  constructor(
    readonly id: string,
    readonly image: string,
    private readonly frames: ReadonlyMap<number, SpriteArtFrame>,
    private readonly scale: number,
  ) {}

  /** The atlas has loaded (`width` x `height` px): work out every frame's UVs. */
  setTexture(texture: T, width: number, height: number): void {
    this.ready.clear();
    for (const [index, f] of this.frames) {
      if (f.x + f.w > width || f.y + f.h > height) continue; // Outside the image: draw as before.
      this.ready.set(index, { u0: f.x / width, v0: f.y / height, u1: (f.x + f.w) / width, v1: (f.y + f.h) / height, w: f.w / this.scale, h: f.h / this.scale });
    }
    this.texture = texture;
  }

  /** Sprite `index`'s frame, or undefined if it has none or the atlas isn't loaded. */
  frame(index: number): ReadyFrame | undefined {
    return this.texture === null ? undefined : this.ready.get(index);
  }

  /** Whether sprite `index` is in the manifest (loaded or not). */
  listed(index: number): boolean {
    return this.frames.has(index);
  }
}

/** Every sheet's art, looked up by the draw list's sheet id. */
export class SpriteArt<T = unknown> {
  readonly sheets = new Map<string, SpriteArtSheet<T>>();
  /** Settles when every atlas has loaded or failed. */
  loaded: Promise<void> = Promise.resolve();

  constructor(manifest: SpriteArtManifest) {
    for (const [id, s] of manifest.sheets) this.sheets.set(id, new SpriteArtSheet<T>(id, s.image, s.frames, manifest.scale));
  }

  sheet(id: string): SpriteArtSheet<T> | undefined {
    return this.sheets.get(id);
  }

  /** Sprite `index` of sheet `id`, if it has art that has loaded. */
  frame(id: string, index: number): ReadyFrame | undefined {
    return this.sheets.get(id)?.frame(index);
  }
}

/** The mode a page's query string asks for (`?sprites=original|remastered`), or undefined if none. */
export function spriteArtModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): SpriteArtMode | undefined {
  const v = search === undefined ? null : new URLSearchParams(search).get("sprites");
  return v === "original" || v === "remastered" ? v : undefined;
}

/** World placement of a flat quad: its top-left corner and its size along world X and Z. */
export interface FlatQuad {
  x: number;
  y: number;
  z: number;
  w: number;
  d: number;
}

/**
 * Place a flat quad for a draw whose top-left is at screen (sx, sy) and which is `w` x `h` original
 * pixels, at `height` above the ground: on the camera ray through its screen point, shrunk by the
 * same factor, so it covers exactly the screen area the original sprite covered (DECISIONS.md D6;
 * the same maths as the renderer's writeMatrix).
 */
export function placeFlatQuad(sx: number, sy: number, w: number, h: number, height: number, cam: { x: number; y: number; z: number }, out: FlatQuad): FlatQuad {
  const k = height / cam.y;
  const gx = screenWorldX(sx);
  const gz = screenWorldZ(sy);
  const s = (1 - k) / PX_PER_UNIT;
  out.x = gx + (cam.x - gx) * k;
  out.y = height;
  out.z = gz + (cam.z - gz) * k;
  out.w = w * s;
  out.d = h * s;
  return out;
}

/** The four tiles of a blit_sprite2x2 draw: sprite index offsets and their pixel offsets. */
export const SPRITE2X2_PARTS: ReadonlyArray<readonly [di: number, dx: number, dy: number]> = [
  [0, 0, 0],
  [1, 12, 0],
  [19, 0, 14],
  [20, 12, 14],
];
