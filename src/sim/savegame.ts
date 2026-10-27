// Saved games: port of OpenTyrian's JE_saveGame / JE_loadGame (src/config.c L357-528), the load
// half of JE_operation (mainint.c L2713-2729), and the save slots (saveFiles, loadSaves/saveSaves).
//
// The C keeps 22 slots in tyrian.sav: 1-11 for one player and 12-22 for two, the last of each
// being the automatic "LAST LEVEL" backup that a failed level retries from (JE_saveGame(11, ...)
// in JE_main; DECISIONS.md D14). Here the slots live in localStorage as versioned JSON (see
// SAVE_STORAGE_KEY) with the same fields; the high-score table that shares tyrian.sav isn't ported.
// The slots are always kept in memory too, so the retry backup works without storage.

import { s32, u32, u8 } from "./cint";
import { buildResources, type TyrianFiles } from "./resources";
import { g, SA_ARCADE, SA_NONE, SA_NORTSHIPZ, SA_SUPERTYRIAN, FRONT_WEAPON, LEFT_SIDEKICK, REAR_WEAPON, RIGHT_SIDEKICK, type PlayerItems } from "./state";

/** config.h SAVE_FILES_NUM: 11 one-player slots, then 11 two-player ones. */
export const SAVE_FILES_NUM = 11 * 2;
/** episodes.h EPISODE_AVAILABLE */
const EPISODE_AVAILABLE = 4;

/** JE_SaveFileType (config.h L64-89), without the high scores. */
export interface JE_SaveFileType {
  /** JE_word: the episode-script section to continue from; 0 is an empty slot. */
  level: number;
  /** JE_PItemsType (12 bytes): player 1's items (playeritems_to_pitems). */
  items: number[];
  /** JE_longint: player 1's and player 2's cash. */
  score: number;
  score2: number;
  /** lastLevelName when saved: the last level completed (or "NEW GAME", "Completed"). */
  levelName: string;
  /** The slot's name, 14 characters (space-padded). */
  name: string;
  cubes: number;
  /** The front and rear weapons' power. */
  power: [number, number];
  episode: number;
  /** last_items (player 2's items in a two-player game). */
  lastItems: number[];
  difficulty: number;
  secretHint: number;
  input1: number;
  input2: number;
  gameHasRepeated: boolean;
  initialDifficulty: number;
}

/** An empty slot, as loadSaves leaves an invalid or missing file (config.c L835-845). */
export function emptySaveFile(): JE_SaveFileType {
  return {
    level: 0,
    items: new Array<number>(12).fill(0),
    score: 0,
    score2: 0,
    levelName: "",
    name: " ".repeat(14),
    cubes: 0,
    power: [0, 0],
    episode: 0,
    lastItems: new Array<number>(12).fill(0),
    difficulty: 0,
    secretHint: 0,
    input1: 0,
    input2: 0,
    gameHasRepeated: false,
    initialDifficulty: 0,
  };
}

/** saveFiles[SAVE_FILES_NUM]: slot n is saveFiles[n - 1]. */
export const saveFiles: JE_SaveFileType[] = Array.from({ length: SAVE_FILES_NUM }, emptySaveFile);

// --- Storage (tyrian.sav in the C) ---

/** localStorage key for the slots: {"version": SAVE_FORMAT_VERSION, "slots": JE_SaveFileType[22]}. */
export const SAVE_STORAGE_KEY = "tyrian3d.saves";
/** Bump when a slot's fields change meaning; older versions are then converted (or dropped). */
export const SAVE_FORMAT_VERSION = 1;

/** The part of the Web Storage API the saves use (localStorage, or a stand-in in tests). */
export interface SaveStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function defaultStorage(): SaveStorage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null; // storage disabled
  }
}

let storage: SaveStorage | null | undefined;

/** Use `s` for the slots instead of localStorage (null: memory only). */
export function setSaveStorage(s: SaveStorage | null): void {
  storage = s;
}

const getStorage = (): SaveStorage | null => (storage === undefined ? (storage = defaultStorage()) : storage);

const isByte = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0 && (v as number) <= 255;
const isBytes = (v: unknown, n: number): v is number[] => Array.isArray(v) && v.length === n && v.every(isByte);

/** A stored slot, checked field by field; null if anything is missing or out of range. */
function parseSlot(o: unknown): JE_SaveFileType | null {
  if (!o || typeof o !== "object") return null;
  const r = o as Record<string, unknown>;
  const int = (k: string) => Number.isInteger(r[k]);
  if (!(Number.isInteger(r.level) && (r.level as number) >= 0 && (r.level as number) <= 0xffff)) return null;
  if (!isBytes(r.items, 12) || !isBytes(r.lastItems, 12) || !isBytes(r.power, 2)) return null;
  if (!int("score") || !int("score2")) return null;
  if (typeof r.levelName !== "string" || typeof r.name !== "string" || typeof r.gameHasRepeated !== "boolean") return null;
  for (const k of ["cubes", "episode", "difficulty", "secretHint", "input1", "input2", "initialDifficulty"]) if (!isByte(r[k])) return null;
  return {
    level: r.level as number,
    items: [...(r.items as number[])],
    score: s32(r.score as number),
    score2: s32(r.score2 as number),
    levelName: (r.levelName as string).slice(0, 10),
    name: (r.name as string).slice(0, 14).padEnd(14),
    cubes: r.cubes as number,
    power: [...(r.power as number[])] as [number, number],
    episode: r.episode as number,
    lastItems: [...(r.lastItems as number[])],
    difficulty: r.difficulty as number,
    secretHint: r.secretHint as number,
    input1: r.input1 as number,
    input2: r.input2 as number,
    gameHasRepeated: r.gameHasRepeated as boolean,
    initialDifficulty: r.initialDifficulty as number,
  };
}

/**
 * loadSaves (config.c L771-855): read the slots from storage. A missing or unreadable store, or one
 * from an unknown format version, leaves every slot empty, as the C does with a bad tyrian.sav; a
 * single damaged slot is emptied on its own.
 */
export function loadSaves(): void {
  for (let i = 0; i < SAVE_FILES_NUM; i++) saveFiles[i] = emptySaveFile();

  let text: string | null = null;
  try {
    text = getStorage()?.getItem(SAVE_STORAGE_KEY) ?? null;
  } catch {
    /* storage unavailable */
  }
  if (!text) return;

  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    return;
  }
  const d = data as { version?: unknown; slots?: unknown };
  if (d?.version !== SAVE_FORMAT_VERSION || !Array.isArray(d.slots)) return;
  for (let i = 0; i < SAVE_FILES_NUM; i++) saveFiles[i] = parseSlot(d.slots[i]) ?? emptySaveFile();
}

/** The slots as stored. */
export function serializeSaves(): string {
  return JSON.stringify({ version: SAVE_FORMAT_VERSION, slots: saveFiles });
}

/** saveSaves (config.c L872-917): write the slots to storage (nothing happens without storage). */
export function saveSaves(): void {
  try {
    getStorage()?.setItem(SAVE_STORAGE_KEY, serializeSaves());
  } catch {
    /* storage full or unavailable: the slots stay in memory */
  }
}

// --- config.c ---

/** playeritems_to_pitems (config.c L357-371). */
function playeritems_to_pitems(pItems: number[], items: PlayerItems, initial_episode_num: number): void {
  pItems[0] = u8(items.weapon[FRONT_WEAPON].id);
  pItems[1] = u8(items.weapon[REAR_WEAPON].id);
  pItems[2] = u8(items.super_arcade_mode);
  pItems[3] = u8(items.sidekick[LEFT_SIDEKICK]);
  pItems[4] = u8(items.sidekick[RIGHT_SIDEKICK]);
  pItems[5] = u8(items.generator);
  pItems[6] = u8(items.sidekick_level);
  pItems[7] = u8(items.sidekick_series);
  pItems[8] = u8(initial_episode_num);
  pItems[9] = u8(items.shield);
  pItems[10] = u8(items.special);
  pItems[11] = u8(items.ship);
}

/** pitems_to_playeritems (config.c L373-388); returns pItems[8], the initial episode. */
function pitems_to_playeritems(items: PlayerItems, pItems: number[]): number {
  items.weapon[FRONT_WEAPON].id = pItems[0];
  items.weapon[REAR_WEAPON].id = pItems[1];
  items.super_arcade_mode = pItems[2];
  items.sidekick[LEFT_SIDEKICK] = pItems[3];
  items.sidekick[RIGHT_SIDEKICK] = pItems[4];
  items.generator = pItems[5];
  items.sidekick_level = pItems[6];
  items.sidekick_series = pItems[7];
  items.shield = pItems[9];
  items.special = pItems[10];
  items.ship = pItems[11];
  return pItems[8];
}

/** JE_saveGame (config.c L390-447): store the game in `slot` (1-based) under `name` (14 characters). */
export function JE_saveGame(slot: number, name: string): void {
  const f = saveFiles[slot - 1];
  const player = g.player;

  f.initialDifficulty = u8(g.initialDifficulty);
  f.gameHasRepeated = g.gameHasRepeated;
  f.level = g.saveLevel;

  if (g.superTyrian) player[0].items.super_arcade_mode = SA_SUPERTYRIAN;
  else if (g.superArcadeMode === SA_NONE && g.onePlayerAction) player[0].items.super_arcade_mode = SA_ARCADE;
  else player[0].items.super_arcade_mode = g.superArcadeMode;

  playeritems_to_pitems(f.items, player[0].items, g.initial_episode_num);

  if (g.twoPlayerMode) playeritems_to_pitems(f.lastItems, player[1].items, 0);
  else playeritems_to_pitems(f.lastItems, player[0].last_items, 0);

  f.score = s32(player[0].cash);
  f.score2 = s32(player[1].cash);

  f.levelName = g.lastLevelName;
  f.cubes = u8(g.lastCubeMax);

  if (g.lastLevelName === "Completed") {
    let temp = g.episodeNum - 1;
    if (temp < 1) temp = EPISODE_AVAILABLE; /* JE: {Episodemax is 4 for completion purposes} */
    f.episode = temp;
  } else {
    f.episode = g.episodeNum;
  }

  f.difficulty = u8(g.difficultyLevel);
  f.secretHint = g.secretHint;
  f.input1 = g.inputDevice[0];
  f.input2 = g.inputDevice[1];

  f.name = name.padEnd(14).slice(0, 14);

  for (let port = 0; port < 2; ++port) {
    // if two-player, use first player's front and second player's rear weapon
    f.power[port] = player[g.twoPlayerMode ? port : 0].items.weapon[port].power;
  }

  saveSaves();
}

/**
 * JE_initEpisode (episodes.c L247-259): switch to another episode's data. The port's item data
 * comes from buildResources, so it needs the game's files.
 */
export function JE_initEpisode(newEpisode: number, files: TyrianFiles): void {
  if (newEpisode === g.episodeNum) return;

  g.episodeNum = newEpisode;

  // levelFilename, cubeFilename, episodeFilename and analyzeLevel: read by episode number when used.
  g.res = buildResources(files, newEpisode); // JE_loadItemDat
}

/** JE_loadGame (config.c L449-528): continue the game in `slot` (1-based). */
export function JE_loadGame(slot: number, files: TyrianFiles): void {
  const f = saveFiles[slot - 1];
  const player = g.player;

  g.superTyrian = false;
  g.onePlayerAction = false;
  g.twoPlayerMode = false;
  g.extraGame = false;
  g.galagaMode = false;

  g.initialDifficulty = f.initialDifficulty;
  g.gameHasRepeated = f.gameHasRepeated;
  g.twoPlayerMode = slot - 1 > 10;
  g.difficultyLevel = f.difficulty;

  g.initial_episode_num = pitems_to_playeritems(player[0].items, f.items);

  g.superArcadeMode = player[0].items.super_arcade_mode;

  if (g.superArcadeMode === SA_SUPERTYRIAN) g.superTyrian = true;
  if (g.superArcadeMode !== SA_NONE) g.onePlayerAction = true;
  if (g.superArcadeMode > SA_NORTSHIPZ) g.superArcadeMode = SA_NONE;

  if (g.twoPlayerMode) {
    g.onePlayerAction = false;

    pitems_to_playeritems(player[1].items, f.lastItems);
  } else {
    pitems_to_playeritems(player[0].last_items, f.lastItems);
  }

  /* Compatibility with old version */
  if (player[1].items.sidekick_level < 101) {
    player[1].items.sidekick_level = 101;
    player[1].items.sidekick_series = player[1].items.sidekick[LEFT_SIDEKICK];
  }

  player[0].cash = u32(f.score);
  player[1].cash = u32(f.score2);

  g.mainLevel = u8(f.level);
  g.cubeMax = f.cubes;
  g.lastCubeMax = g.cubeMax;

  g.secretHint = f.secretHint;
  g.inputDevice[0] = f.input1;
  g.inputDevice[1] = f.input2;

  for (let port = 0; port < 2; ++port) {
    // if two-player, use first player's front and second player's rear weapon
    player[g.twoPlayerMode ? port : 0].items.weapon[port].power = f.power[port];
  }

  let episode = f.episode;

  g.levelName = f.levelName;

  if (g.levelName === "Completed") {
    if (episode === EPISODE_AVAILABLE) episode = 1;
    else if (episode < EPISODE_AVAILABLE) episode++;
    /* Increment episode.  Episode EPISODE_AVAILABLE goes to 1. */
  }

  JE_initEpisode(episode, files);
  g.saveLevel = g.mainLevel;
  g.lastLevelName = g.levelName;
}

// --- mainint.c ---

/** The load half of JE_operation (mainint.c L2719-2727): load `slot` unless it's empty. */
export function JE_operation_load(slot: number, files: TyrianFiles): void {
  if (saveFiles[slot - 1].level > 0) {
    g.gameJustLoaded = true;
    JE_loadGame(slot, files);
    g.gameLoaded = true;
  }
}

/**
 * Whether JE_operation's save half runs for `slot` (mainint.c L2729: `slot % 11 != 0`, so the
 * LAST LEVEL slots can't be overwritten), and the name its prompt starts with: the slot's name with
 * its trailing spaces removed.
 */
export function JE_operation_saveName(slot: number): string | null {
  if (slot % 11 === 0) return null;
  return saveFiles[slot - 1].name.replace(/ +$/, "");
}

/**
 * Whether the save-name prompt takes `ch` (mainint.c L2834: a space, or a character the font has,
 * fontMap in fonthand.c L29-48). Only its ASCII part: the names are stored as text here.
 */
export function saveNameChar(ch: string): boolean {
  return ch.length === 1 && (ch === " " || /[!"#$%'()*+,\-./0-9:;=?A-Z[\\\]a-z{|}]/.test(ch));
}

/**
 * The save half of JE_operation once the player confirms a name (Enter or OK, mainint.c L2795,
 * L2823): JE_saveGame with the name padded to 14 characters. The prompt keeps at most 14
 * characters, each a space or one the game's font has (fontMap).
 */
export function JE_operation_save(slot: number, name: string): void {
  if (slot % 11 === 0) return;
  JE_saveGame(slot, name.slice(0, 14).padEnd(14));
}

/**
 * Loading a game from the title screen: what the main loop does before the title (opentyr.c
 * L873-880: JE_initPlayerData, playDemo/gameLoaded/jumpSection = false) is the caller's; this is
 * JE_loadScreen picking `slot` (mainint.c L870-889): performSave = false, JE_operation(slot).
 * Returns gameLoaded.
 */
export function JE_loadScreen_select(slot: number, files: TyrianFiles): boolean {
  JE_operation_load(slot, files);
  return g.gameLoaded;
}

// --- What the slot lists show ---

/** One save slot as the load/save lists show it. */
export interface SaveSlotView {
  /** 1-based slot number. */
  slot: number;
  empty: boolean;
  /** The slot's name, or miscText[2] ("EMPTY SLOT"). */
  name: string;
  /** The last level completed (empty for an empty slot). */
  levelName: string;
  episode: number;
}

/** Slots `first`..`first + count - 1` as the item screen's load/save menu (game_menu.c L328-383) and JE_loadScreen list them. */
export function saveSlotViews(first: number, count: number): SaveSlotView[] {
  const out: SaveSlotView[] = [];
  for (let slot = first; slot < first + count; slot++) {
    const f = saveFiles[slot - 1];
    const empty = f.level === 0;
    out.push({
      slot,
      empty,
      name: empty ? (g.miscText[3 - 1] ?? "EMPTY SLOT") : f.name.trimEnd(),
      levelName: empty ? "" : f.levelName.trim(),
      episode: f.episode,
    });
  }
  return out;
}
