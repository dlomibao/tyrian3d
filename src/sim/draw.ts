// The draw list: what the ported simulation "blits" each tick, for the 3D renderer to draw.
//
// OpenTyrian draws while it simulates (JE_drawEnemy moves and draws in one pass). The port keeps
// that structure: the C `blit_*` calls are reimplemented here with the same names and argument
// order (minus the surface), and record a draw instead of writing pixels. The renderer turns each
// record into a 3D object; it never reads game state directly (DECISIONS.md D1).
//
// Coordinates are the original's 320x200 VGA screen pixels, x right and y down, for the top-left of
// the sprite, exactly as passed to the C blit.

/** A Sprite2 sheet (OpenTyrian Sprite2_array): u16 offset table then RLE data (src/sprite.c). */
export interface Sprite2Sheet {
  /** Stable name for caching meshes, e.g. "tyrian.shp#8" or "newsh1.shp". */
  readonly id: string;
  readonly data: Uint8Array;
}

/**
 * A sprite table in the older Sprite format (OpenTyrian Sprite_array, load_sprites): used for
 * fonts, interface pieces and option (sidekick) shapes.
 */
export interface SpriteTable {
  readonly id: string;
  readonly sprites: ReadonlyArray<{ width: number; height: number; data: Uint8Array } | null>;
}

/**
 * Draw passes, in JE_main's draw order. The renderer gives each pass a height so later passes sit
 * above earlier ones (DECISIONS.md D5).
 */
export const enum Pass {
  Background1 = 0,
  Starfield,
  Background2Under, // background2over == 3 or 0
  GroundEnemies, // JE_drawEnemy(50), JE_drawEnemy(100)
  Background2Mid, // background2over == 1
  Background3Under, // background3over == 2
  SkyEnemies, // JE_drawEnemy(25), when !skyEnemyOverAll
  Background3, // background3over == 0
  TopEnemies, // JE_drawEnemy(75), when !topEnemyOver
  PlayerShots,
  Player, // the ship, its shadow and sidekicks (JE_mainGamePlayerFunctions)
  EnemyShots,
  Background3Over, // background3over == 1
  TopEnemiesOver, // topEnemyOver
  SkyEnemiesOver, // skyEnemyOverAll
  Explosions,
  Background2Top, // background2over == 2
  Effects, // superpixels (JE_drawSP), warning bars
}

export type SpriteEffect = "none" | "blend" | "darken" | "filter" | "hv";

export interface SpriteDraw {
  kind: "sprite2";
  sheet: Sprite2Sheet;
  /** 1-based sprite index, as in the C call. */
  index: number;
  x: number;
  y: number;
  /** 1 = one 12x14 tile (blit_sprite2), 2 = a 24x28 block of 4 tiles (blit_sprite2x2). */
  size: 1 | 2;
  pass: Pass;
  /** Identity across ticks for interpolation; -1 means "don't interpolate". */
  key: number;
  effect: SpriteEffect;
  /** For "filter": the hue filter byte (high nibble = hue). For "hv": hue and value. */
  filter: number;
  value: number;
  /**
   * The whole object this tile belongs to, for drawing it as one model (DECISIONS.md D15). Only
   * enemies set it: a 2x2 enemy is four blit_sprite2 calls (index, +1, +19, +20). groupIndex is
   * the sprite index of the object's top-left tile in this animation frame (-1: not grouped),
   * groupSize its size in tiles (1 or 2), and (groupDx, groupDy) the offset from this tile's
   * top-left to the object's centre. groupFirst is true on the first tile drawn for the object
   * this tick, which is where its model goes.
   */
  groupIndex: number;
  groupSize: 1 | 2;
  groupDx: number;
  groupDy: number;
  groupFirst: boolean;
}

export interface TableSpriteDraw {
  kind: "sprite";
  table: SpriteTable;
  /** 0-based index into the table, as in blit_sprite(…, table, index). */
  index: number;
  x: number;
  y: number;
  pass: Pass;
  key: number;
  effect: SpriteEffect;
  filter: number;
  value: number;
}

export interface TileDraw {
  kind: "tile";
  /** Background layer: 0 = background 1 (ground), 1 = background 2, 2 = background 3. */
  layer: 0 | 1 | 2;
  /** The 24x28 tile's pixels (palette indices; 0 is transparent on layers 1 and 2). */
  tile: Uint8Array;
  /** Stable id of the tile graphic, for caching meshes and textures. */
  tileId: string;
  x: number;
  y: number;
  pass: Pass;
  key: number;
  effect: "none" | "blend";
}

export interface PixelDraw {
  kind: "pixel";
  x: number;
  y: number;
  /** Palette index. */
  color: number;
  pass: Pass;
}

export interface RectDraw {
  kind: "rect";
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color: number;
  pass: Pass;
}

export type Draw = SpriteDraw | TableSpriteDraw | TileDraw | PixelDraw | RectDraw;

/** The draws of one tick, plus the frame-wide settings the renderer needs. */
export interface DrawList {
  items: Draw[];
  /** Index into the 23 palettes from palette.dat. */
  palette: number;
  /** JE_filterScreen state: levelFilter (-99 = off) and levelBrightness. */
  filter: number;
  brightness: number;
}

export const drawList: DrawList = { items: [], palette: 0, filter: -99, brightness: 0 };

/** The pass and key that the next blits record. Set by the sim around each draw section. */
export const drawState = { pass: Pass.Background1 as Pass, key: -1 };

/** The object the next sprite2 blits belong to (SpriteDraw.groupIndex and so on). Set by blit_enemy. */
export const drawGroup = { index: -1, size: 1 as 1 | 2, dx: 0, dy: 0, first: false };

export function beginDrawList(): void {
  drawList.items = [];
  drawState.pass = Pass.Background1;
  drawState.key = -1;
}

function sprite2(x: number, y: number, sheet: Sprite2Sheet, index: number, size: 1 | 2, effect: SpriteEffect, filter = 0): void {
  const gr = drawGroup;
  drawList.items.push({
    kind: "sprite2", sheet, index, x, y, size, pass: drawState.pass, key: drawState.key, effect, filter, value: 0,
    groupIndex: gr.index, groupSize: gr.size, groupDx: gr.dx, groupDy: gr.dy, groupFirst: gr.first,
  });
}

export const blit_sprite2 = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 1, "none");
export const blit_sprite2_clip = blit_sprite2;
export const blit_sprite2_blend = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 1, "blend");
export const blit_sprite2_darken = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 1, "darken");
export const blit_sprite2_filter = (x: number, y: number, sheet: Sprite2Sheet, index: number, filter: number) => sprite2(x, y, sheet, index, 1, "filter", filter);
export const blit_sprite2_filter_clip = blit_sprite2_filter;
export const blit_sprite2x2 = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 2, "none");
export const blit_sprite2x2_clip = blit_sprite2x2;
export const blit_sprite2x2_blend = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 2, "blend");
export const blit_sprite2x2_darken = (x: number, y: number, sheet: Sprite2Sheet, index: number) => sprite2(x, y, sheet, index, 2, "darken");
export const blit_sprite2x2_filter = (x: number, y: number, sheet: Sprite2Sheet, index: number, filter: number) => sprite2(x, y, sheet, index, 2, "filter", filter);
export const blit_sprite2x2_filter_clip = blit_sprite2x2_filter;

function tableSprite(x: number, y: number, table: SpriteTable, index: number, effect: SpriteEffect, filter = 0, value = 0): void {
  drawList.items.push({ kind: "sprite", table, index, x, y, pass: drawState.pass, key: drawState.key, effect, filter, value });
}

export const blit_sprite = (x: number, y: number, table: SpriteTable, index: number) => tableSprite(x, y, table, index, "none");
export const blit_sprite_blend = (x: number, y: number, table: SpriteTable, index: number) => tableSprite(x, y, table, index, "blend");
export const blit_sprite_dark = (x: number, y: number, table: SpriteTable, index: number) => tableSprite(x, y, table, index, "darken");
export const blit_sprite_hv = (x: number, y: number, table: SpriteTable, index: number, hue: number, value: number) =>
  tableSprite(x, y, table, index, "hv", hue, value);
export const blit_sprite_hv_unsafe = blit_sprite_hv;
export const blit_sprite_hv_blend = blit_sprite_hv;

export function drawTile(layer: 0 | 1 | 2, tile: Uint8Array, tileId: string, x: number, y: number, key: number, blend = false): void {
  drawList.items.push({ kind: "tile", layer, tile, tileId, x, y, pass: drawState.pass, key, effect: blend ? "blend" : "none" });
}

export function drawPixel(x: number, y: number, color: number): void {
  drawList.items.push({ kind: "pixel", x, y, color, pass: drawState.pass });
}

/** fill_rectangle_xy, inclusive corners. */
export function fill_rectangle_xy(x1: number, y1: number, x2: number, y2: number, color: number): void {
  drawList.items.push({ kind: "rect", x1, y1, x2, y2, color, pass: drawState.pass });
}
