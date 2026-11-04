// The sprites a level can draw that a model might replace, and its background tiles, worked out
// before it starts, so the renderer can load their models first, earliest needed first
// (DECISIONS.md D54; DrawListRenderer.preloadLevel).
//
// Call after loadLevel and startLevel (JE_getShipInfo has set the ships). The list over-covers
// rather than under-covers: every enemy type any event names (whatever the event), the types those
// launch or leave behind when they die, the random-spawn types, the armour ship and its crates (the
// game spawns them when armour is low), each with every frame of its egraphic and its damaged
// graphic, on the sheet its shape bank names, as long as some event of the level loads that bank
// (an enemy of an unloaded bank borrows another's sheet; the C logs "Ignoring sprite from unloaded
// shape table"). Then the players' ships and sidekicks.
// tests/render/modelSwap.test.ts checks that every model level 1 actually shows is in the list.

import { ENEMY_NUM } from "../data/enemies";
import { MAP_SIZES, TILE_HEIGHT } from "../data/levels";
import type { Sprite2Sheet } from "./draw";
import { g } from "./state";
import { shapeFile } from "./tyrian2";

/**
 * The armour ship (enemy type 560) and the crates it leaves (561-563, its enemydie, set by the
 * spawn, not its data): spawned by the game whenever a player's armour is low, in any level.
 */
export const ARMOR_SHIP_TYPES = [560, 561, 562, 563];

/** One sprite that may be drawn: grouped (part of an enemy or a two-half ship) or on its own. */
export interface LevelSprite {
  sheet: string;
  size: 1 | 2;
  index: number;
  grouped: boolean;
  /**
   * Roughly when it may first be needed, in curLoc units (event times; about one per tick): the
   * earliest event naming its enemy, 0 for the players. For loading in order, never exact (events
   * jump about).
   */
  time: number;
}

/**
 * An enemy type's damaged frames and its normal frames, on its sheet
 * (game.ts: edani != 0 animates egraphic[edgr-1 .. |edani|-1], else edgr replaces egraphic[0]).
 */
export interface LevelDamage {
  sheet: string;
  size: 1 | 2;
  damaged: number[];
  normal: number[];
}

/** A background tile of the level: layer, tile number in the shapes file, and roughly when it scrolls in. */
export interface LevelTile {
  layer: 0 | 1 | 2;
  tile: number;
  time: number;
}

/**
 * The damaged frames of every enemy type the current level can make, with the normal frames they
 * replace (levelSprites' enemy types), for drawing them with the intact models (D87,
 * render/damage/damageRoute.ts).
 */
export function levelDamageFrames(): LevelDamage[] {
  const out: LevelDamage[] = [];
  forLevelEnemyTypes((dat, sheet, size) => {
    const damaged: number[] = [];
    if (dat.dAni !== 0) for (let k = dat.dGr - 1; k < Math.abs(dat.dAni); k++) damaged.push(dat.eGraphic[k]);
    else if (dat.dGr > 0) damaged.push(dat.dGr);
    const normal = dat.eGraphic.slice(0, Math.max(1, dat.ani)).filter((f) => f > 0 && f !== 999);
    const d = damaged.filter((f) => f > 0 && f !== 999 && !normal.includes(f));
    if (d.length && normal.length) out.push({ sheet, size, damaged: d, normal });
  });
  return out;
}

/** Each enemy type the current level can make (levelSprites' rules), with its sheet and size. */
function forLevelEnemyTypes(each: (dat: (typeof g.res.enemyDat)[number], sheet: string, size: 1 | 2, time: number) => void): void {
  const events = g.lvl?.eventRec ?? [];
  const banks = new Set<number>([21, 26]);
  for (const ev of events) {
    if (ev.eventType !== 5) continue;
    for (const t of [ev.eventDat, ev.eventDat2, ev.eventDat3, ev.eventDat4]) if (t > 0 && t <= shapeFile.length) banks.add(t);
  }
  const bankSheet = (bank: number): string | null => {
    if (!banks.has(bank)) return null;
    if (bank === 21) return g.res.spriteSheet11.id;
    if (bank === 26) return g.res.spriteSheet10.id;
    return `newsh${shapeFile[bank - 1].toLowerCase()}.shp`;
  };
  const types = new Map<number, number>();
  const queue: number[] = [];
  const addType = (t: number, time: number) => {
    if (t <= 0 || t > ENEMY_NUM || (types.get(t) ?? Infinity) <= time) return;
    types.set(t, time);
    queue.push(t);
  };
  for (const ev of events) for (let k = 0; k < 4; k++) addType(ev.eventDat + k, ev.eventTime);
  for (let i = 0; i < g.levelEnemyMax; i++) addType(g.levelEnemy[i], 0);
  for (const t of ARMOR_SHIP_TYPES) addType(t, 0);
  while (queue.length) {
    const t = queue.pop()!;
    const dat = g.res.enemyDat[t];
    addType(dat.eLaunchType % 1000, types.get(t)!);
    addType(dat.eEnemyDie, types.get(t)!);
  }
  for (const [t, time] of types) {
    const dat = g.res.enemyDat[t];
    const sheet = bankSheet(dat.shapeBank);
    if (sheet) each(dat, sheet, dat.eSize === 1 ? 2 : 1, time);
  }
}

/** The sprites the current level (g.lvl, g.player) can draw. */
export function levelSprites(): LevelSprite[] {
  const out = new Map<string, LevelSprite>();
  const add = (sheet: Sprite2Sheet | string | null | undefined, size: 1 | 2, index: number, grouped: boolean, time: number) => {
    if (!sheet || index <= 0 || index === 999) return;
    const id = typeof sheet === "string" ? sheet : sheet.id;
    const key = `${id}|${size}|${index}|${grouped}`;
    const had = out.get(key);
    if (!had) out.set(key, { sheet: id, size, index, grouped, time });
    else had.time = Math.min(had.time, time);
  };

  // Shape banks the level loads (event 5), and the sheet of each bank.
  const events = g.lvl?.eventRec ?? [];
  const banks = new Set<number>([21, 26]);
  for (const ev of events) {
    if (ev.eventType !== 5) continue;
    for (const t of [ev.eventDat, ev.eventDat2, ev.eventDat3, ev.eventDat4]) if (t > 0 && t <= shapeFile.length) banks.add(t);
  }
  const bankSheet = (bank: number): string | null => {
    if (!banks.has(bank)) return null;
    if (bank === 21) return g.res.spriteSheet11.id; // Coins&Gems
    if (bank === 26) return g.res.spriteSheet10.id; // Two-Player Stuff
    return `newsh${shapeFile[bank - 1].toLowerCase()}.shp`; // resources.ts loadCompShapes
  };

  // Enemy types: anything an event names (JE_createNewEventEnemy reads eventdat + 0..3), the
  // random spawns, and what they launch or turn into, followed transitively.
  // Each type's earliest time; a type's time only ever goes down, so the queue settles.
  const types = new Map<number, number>();
  const queue: number[] = [];
  const addType = (t: number, time: number) => {
    if (t <= 0 || t > ENEMY_NUM || (types.get(t) ?? Infinity) <= time) return;
    types.set(t, time);
    queue.push(t);
  };
  for (const ev of events) for (let k = 0; k < 4; k++) addType(ev.eventDat + k, ev.eventTime);
  for (let i = 0; i < g.levelEnemyMax; i++) addType(g.levelEnemy[i], 0);
  // The armour ship and its crates, which no event names: JE_main's low-armour warning
  // (game.ts armorWarning) sends one whenever a player's armour is under 6, at any time.
  for (const t of ARMOR_SHIP_TYPES) addType(t, 0);
  while (queue.length) {
    const t = queue.pop()!;
    const dat = g.res.enemyDat[t];
    addType(dat.eLaunchType % 1000, types.get(t)!);
    addType(dat.eEnemyDie, types.get(t)!);
  }
  for (const [t, time] of types) {
    const dat = g.res.enemyDat[t];
    const sheet = bankSheet(dat.shapeBank);
    if (!sheet) continue;
    const size: 1 | 2 = dat.eSize === 1 ? 2 : 1;
    for (const f of dat.eGraphic) add(sheet, size, f, true, time);
    add(sheet, size, dat.dGr, true, time);
  }
  // Events 49-52: enemy type 0 drawn with eventdat's graphic, from eventdat3's bank (if set).
  const custom = g.res.enemyDat[0];
  for (const ev of events) {
    if (ev.eventType < 49 || ev.eventType > 52) continue;
    add(bankSheet(ev.eventDat3 > 0 ? ev.eventDat3 : custom.shapeBank), custom.eSize === 1 ? 2 : 1, ev.eventDat, true, ev.eventTime);
  }

  // The players' ships (mainint.c: shipGr 0 and 1 are two halves, a grouped object keyed by the
  // left half) and sidekicks (JE_playerMovement: each animation frame plus its charge).
  const players = g.twoPlayerMode ? [0, 1] : [0];
  for (const n of players) {
    const shipGr = n === 0 ? g.shipGr : g.shipGr2;
    const sheet = (n === 0 ? g.shipGrPtr : g.shipGr2ptr) ?? g.res.spriteSheet9;
    if (shipGr === 0) add(sheet, 2, 13, true, 0);
    else if (shipGr === 1) add(sheet, 2, 220, true, 0);
    else add(sheet, 2, shipGr, false, 0);
    for (const id of g.player[n].items.sidekick) {
      const o = g.res.items.options[id];
      if (!o || o.option <= 0) continue;
      const big = o.tr === 1 || o.tr === 2;
      for (let f = 0; f < Math.max(1, o.ani); f++) {
        for (let charge = 0; charge <= o.pwr; charge++) add(big ? g.res.spriteSheet10 : g.res.spriteSheet9, big ? 2 : 1, o.gr[f] + charge, false, 0);
      }
    }
  }
  return [...out.values()];
}

/**
 * Every tile on the current level's background maps, with roughly when it first scrolls into view
 * (curLoc units, as LevelSprite.time): maps scroll from row height - 8 toward row 0, background 1
 * (layer 0) at a pixel per curLoc unit, 2 and 3 about two and three times as fast (backMove2,
 * backMove3).
 */
export function levelTiles(): LevelTile[] {
  const level = g.lvl?.level;
  if (!level) return [];
  const out = new Map<string, LevelTile>();
  for (const layer of [0, 1, 2] as const) {
    const { width, height } = MAP_SIZES[layer];
    const map = level.maps[layer];
    for (let i = 0; i < map.length; i++) {
      const tile = level.mapSh[layer][map[i]] - 1;
      if (tile < 0) continue;
      const rows = Math.max(0, height - 8 - Math.floor(i / width) - 7); // about 7 rows show at once
      const time = Math.round((rows * TILE_HEIGHT) / (layer + 1));
      const key = `${layer}|${tile}`;
      const had = out.get(key);
      if (!had) out.set(key, { layer, tile, time });
      else had.time = Math.min(had.time, time);
    }
  }
  return [...out.values()];
}
