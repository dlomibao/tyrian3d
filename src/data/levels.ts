// tyrian1.lvl..tyrian4.lvl and the shapes?.dat tile files. Ports analyzeLevel (OpenTyrian
// src/lvllib.c) and the level-file half of JE_loadMap (src/tyrian2.c).
//
// A level file starts with a u16 count (lvlNum) and that many u32 offsets (lvlPos). Level n
// (lvlFileNum, 1-based, from the episode script's `]L[`) is at lvlPos[(n - 1) * 2]: header,
// enemies and events, then the map at lvlPos[(n - 1) * 2 + 1], which JE_loadMap simply reads
// on into. In episode 4, lvlPos[lvlNum - 1] is the item data (see items.ts).
//
// Units are raw. Event times are in curLoc units: the background-1 scroll position, which
// the main loop advances by backMove each time background 1 steps (every map1YDelay logic
// frames). Tiles are 24×28 px; map x offsets (mapX..mapX3) are 1-based tile columns. Levels
// scroll from the bottom of each map (mapY starts at height - 8) toward row 0.

import { BinaryReader, type Bytes } from "./reader";

/** JE_LvlPosType holds 43 entries ([1..42 + 1]); lvlNum is clamped to 42. */
export const LVL_POS_COUNT = 43;
/** EVENT_MAXIMUM (src/lvlmast.h): JE_loadMap rejects levels with this many events or more. */
export const EVENT_MAXIMUM = 2500;
/** Background layers' map sizes in tiles (JE_MapType, JE_MapType2, JE_MapType3). */
export const MAP_SIZES = [
  { width: 14, height: 300 },
  { width: 14, height: 600 },
  { width: 15, height: 600 },
] as const;
/** Tile size in px (JE_DanCShape: 24 × 28 palette indices, row-major). */
export const TILE_WIDTH = 24;
export const TILE_HEIGHT = 28;
/** Tile records in every shapes?.dat. */
export const SHAPES_PER_FILE = 600;

/** One event record (JE_EventRecType). Meanings depend on eventType; see JE_eventSystem. */
export interface LevelEvent {
  /** eventtime: curLoc at which the event fires. */
  eventTime: number;
  /** eventtype */
  eventType: number;
  /** eventdat, eventdat2 (s16), eventdat3, eventdat5, eventdat6 (s8), eventdat4 (u8). */
  eventDat: number;
  eventDat2: number;
  eventDat3: number;
  eventDat5: number;
  eventDat6: number;
  eventDat4: number;
}

export interface Level {
  /** char_mapFile: read but unused by OpenTyrian. */
  mapFile: string;
  /** char_shapeFile: tiles come from `shapes${shapeFile.toLowerCase()}.dat`. */
  shapeFile: string;
  /** mapX, mapX2, mapX3: initial horizontal tile offset of each background layer. */
  mapX: number;
  mapX2: number;
  mapX3: number;
  /** levelEnemy[levelEnemyMax]: enemy types for random spawns (C array holds 40). */
  levelEnemy: number[];
  /** eventRec[maxEvent], in file order. JE_loadMap appends a 65500 sentinel at runtime. */
  events: LevelEvent[];
  /** mapSh[3][128] (big-endian): per layer, map byte → 1-based tile in the shapes file. */
  mapSh: [number[], number[], number[]];
  /** Map bytes per layer (indices into mapSh), row-major MAP_SIZES[i].width × height. */
  maps: [Uint8Array, Uint8Array, Uint8Array];
  /** File offsets: the level's start, where the map section starts, and just past its end. */
  start: number;
  mapStart: number;
  end: number;
}

export interface LevelPositions {
  /** lvlNum: offsets stored in the header (clamped to 42). */
  lvlNum: number;
  /** lvlPos[43]: entries past lvlNum are the file length, as analyzeLevel fills them. */
  lvlPos: number[];
}

export interface LevelFile extends LevelPositions {
  /** levels[n - 1] is lvlFileNum n; there are floor(lvlNum / 2). */
  levels: Level[];
}

/** analyzeLevel: read the offset table of a tyrianN.lvl file. */
export function readLevelPositions(data: Bytes): LevelPositions {
  const r = new BinaryReader(data);
  const lvlNum = Math.min(r.u16(), LVL_POS_COUNT - 1);
  const lvlPos: number[] = [];
  for (let i = 0; i < LVL_POS_COUNT; i++) lvlPos.push(i < lvlNum ? r.u32() : r.length);
  return { lvlNum, lvlPos };
}

/** The level-file part of JE_loadMap: one level starting at `offset`. */
export function parseLevel(data: Bytes, offset: number): Level {
  const r = new BinaryReader(data, offset);
  const mapFile = String.fromCharCode(r.u8());
  const shapeFile = String.fromCharCode(r.u8());
  const mapX = r.u16();
  const mapX2 = r.u16();
  const mapX3 = r.u16();

  const levelEnemy = r.u16Array(r.u16());

  const maxEvent = r.u16();
  if (maxEvent >= EVENT_MAXIMUM) throw new Error(`level at ${offset} has too many events (${maxEvent})`);
  const events: LevelEvent[] = [];
  for (let i = 0; i < maxEvent; i++) {
    events.push({
      eventTime: r.u16(),
      eventType: r.u8(),
      eventDat: r.s16(),
      eventDat2: r.s16(),
      eventDat3: r.s8(),
      eventDat5: r.s8(),
      eventDat6: r.s8(),
      eventDat4: r.u8(),
    });
  }

  const mapStart = r.pos;
  const readMapSh = () => Array.from({ length: 128 }, () => r.u16be());
  const mapSh: Level["mapSh"] = [readMapSh(), readMapSh(), readMapSh()];
  const maps = MAP_SIZES.map(({ width, height }) => r.bytesCopy(width * height)) as Level["maps"];

  return { mapFile, shapeFile, mapX, mapX2, mapX3, levelEnemy, events, mapSh, maps, start: offset, mapStart, end: r.pos };
}

/** Parse a whole tyrianN.lvl: the offset table and every level in it. */
export function parseLevelFile(data: Bytes): LevelFile {
  const positions = readLevelPositions(data);
  const levels: Level[] = [];
  for (let n = 1; n <= Math.floor(positions.lvlNum / 2); n++) {
    levels.push(parseLevel(data, positions.lvlPos[(n - 1) * 2]!));
  }
  return { ...positions, levels };
}

/**
 * shapes?.dat: 600 tile records, each a bool "blank" byte followed, unless blank, by 24×28
 * palette indices. Blank tiles are null.
 */
export function parseShapes(data: Bytes): (Uint8Array | null)[] {
  const r = new BinaryReader(data);
  const shapes: (Uint8Array | null)[] = [];
  for (let z = 0; z < SHAPES_PER_FILE; z++) {
    shapes.push(r.bool() ? null : r.bytesCopy(TILE_WIDTH * TILE_HEIGHT));
  }
  return shapes;
}

/**
 * Resolve a layer's map bytes to tiles the way JE_loadMap's "Match 1/2/3" loops do: byte x
 * (only 0..71 are matched) uses shapes[mapSh[layer][x] - 1]. Layer 0 keeps blank tiles as
 * all-zero tiles; layer 1 drops x == 71 and blanks, layer 2 drops x >= 70 and blanks (null =
 * nothing drawn). Unmatched entries are null too; in C they'd be uninitialised pointers.
 */
export function levelTiles(level: Level, shapes: (Uint8Array | null)[], layer: 0 | 1 | 2): (Uint8Array | null)[] {
  const blankTile = new Uint8Array(TILE_WIDTH * TILE_HEIGHT);
  const tiles: (Uint8Array | null)[] = new Array(128).fill(null);
  for (let x = 0; x <= 71; x++) {
    const z = level.mapSh[layer][x]! - 1;
    if (z < 0 || z >= shapes.length) continue;
    const shape = shapes[z]!;
    if (layer === 0) tiles[x] = shape ?? blankTile;
    else if (shape && (layer === 1 ? x !== 71 : x < 70)) tiles[x] = shape;
  }
  return tiles;
}
