// Demo playback: OpenTyrian's demo.c (beginPlayDemo, playDemoKeys, endPlayDemo), transliterated.
//
// Tyrian ships five recorded demos, demo.1 .. demo.5. Each is a header (the episode, the level and
// the player's loadout) followed by the recorded keys: a key bitmask and how many ticks it was held.
// The title screen plays the next one when it sits idle (titleScreen, tyrian2.c L3304-3311), and the
// level loop replays the keys in place of the player's (JE_playerMovement, mainint.c L3439-3450).
// Any input stops the demo (JE_main, tyrian2.c L2077-2088), as does the recording running out
// (the level then ends normally) or the ship dying (the game-over branch ends the level at once).
//
// Recording (beginRecordDemo, recordDemoKeys, endRecordDemo) isn't ported: g.recordDemo stays false.

import { u16 } from "./cint";
import { JE_initEpisode } from "./episodes";
import { JE_initPlayerData } from "./mainint";
import { mt_srand } from "./mtrand";
import { requireFile, type TyrianFiles } from "./resources";
import { DIFFICULTY_NORMAL, FRONT_WEAPON, g, LEFT_SIDEKICK, newPlayer, REAR_WEAPON, RIGHT_SIDEKICK } from "./state";
import { loadLevel } from "./tyrian2";

/** config.h KEY_SETTING_*: the bits of a recorded key mask. */
export const KEY_SETTING_UP = 0;
export const KEY_SETTING_DOWN = 1;
export const KEY_SETTING_LEFT = 2;
export const KEY_SETTING_RIGHT = 3;
export const KEY_SETTING_FIRE = 4;
export const KEY_SETTING_CHANGE_FIRE = 5;
export const KEY_SETTING_LEFT_SIDEKICK = 6;
export const KEY_SETTING_RIGHT_SIDEKICK = 7;

/** varz.h CURRENT_KEY_SPEED */
const CURRENT_KEY_SPEED = 1;

/** demo.c `seed`: every demo plays with the random numbers from this seed. */
export const DEMO_SEED = 32402394;

/** The number of demo files (demo.c wraps demoNum after 5). */
export const DEMO_COUNT = 5;

/** demo.c's file-level state. */
const demo = {
  /** demoNum: the demo playing (1-5), or the last one played; beginPlayDemo plays the next. */
  num: 0,
  /** demoFile: the recording, and the read position in it. */
  file: null as Uint8Array | null,
  pos: 0,
  /** demoKeys: the key mask being replayed. */
  keys: 0,
  /** demoKeysWait (FKA Varz.lastMoveWait): ticks left to replay `keys`. */
  keysWait: 0,
};

/**
 * demo.h stoppedDemo: the player stopped the demo with a key (the main loop then skips the intro
 * logos, opentyr.c L869). Set by the host, which reads the input (JE_main, tyrian2.c L2077-2088).
 */
export const demoState = { stoppedDemo: false };

/** The demo beginPlayDemo picks next (1-5). */
export function nextDemoNum(): number {
  return demo.num + 1 > DEMO_COUNT ? 1 : demo.num + 1;
}

/** Make beginPlayDemo play demo `n` (1-5) next. Not in the C (its demoNum only counts up). */
export function setNextDemo(n: number): void {
  demo.num = (((n - 1) % DEMO_COUNT) + DEMO_COUNT) % DEMO_COUNT;
}

/** fileReadAtMost: up to `n` bytes from the recording, fewer at its end. */
function readAtMost(n: number): Uint8Array {
  const file = demo.file!;
  const bytes = file.subarray(demo.pos, Math.min(file.length, demo.pos + n));
  demo.pos += bytes.length;
  return bytes;
}

/** The header beginPlayDemo reads (demo.c L60-89), for tests and the host's display. */
export interface DemoHeader {
  episode: number;
  levelName: string;
  lvlFileNum: number;
  frontWeapon: number;
  rearWeapon: number;
  superArcadeMode: number;
  leftSidekick: number;
  rightSidekick: number;
  generator: number;
  sidekickLevel: number;
  sidekickSeries: number;
  initialEpisodeNum: number;
  shield: number;
  special: number;
  ship: number;
  frontPower: number;
  rearPower: number;
  levelSong: number;
}

/** The size of a demo's header, before the first key wait. */
export const DEMO_HEADER_SIZE = 30;

/** Parse a demo file's header (the fields beginPlayDemo reads, in its order). */
export function parseDemoHeader(bytes: Uint8Array): DemoHeader {
  if (bytes.length < DEMO_HEADER_SIZE) throw new Error("demo file too short");
  let p = 0;
  const u = () => bytes[p++];
  const episode = u();
  // fileReadCharArray(levelName, 10); levelName[10] = '\0': a C string, so it stops at a NUL.
  let levelName = "";
  for (let i = 0; i < 10; i++) levelName += String.fromCharCode(bytes[p + i]);
  p += 10;
  const nul = levelName.indexOf("\0");
  if (nul >= 0) levelName = levelName.slice(0, nul);
  const h: DemoHeader = {
    episode,
    levelName,
    lvlFileNum: u(),
    frontWeapon: u(),
    rearWeapon: u(),
    superArcadeMode: u(),
    leftSidekick: u(),
    rightSidekick: u(),
    generator: u(),
    sidekickLevel: u(),
    sidekickSeries: u(),
    initialEpisodeNum: u(),
    shield: u(),
    special: u(),
    ship: u(),
    frontPower: u(),
    rearPower: u(),
    levelSong: (p += 3, u()), // 3 unused bytes
  };
  return h;
}

/**
 * beginPlayDemo (demo.c L44-104): open the next demo, seed the random numbers, set the episode,
 * level and loadout from its header and read the first key wait. Called by JE_loadMap in place of
 * the episode script when g.playDemo is set.
 */
export function beginPlayDemo(files: TyrianFiles): void {
  if (++demo.num > DEMO_COUNT) demo.num = 1;

  const demoFilename = `demo.${demo.num}`;
  demo.file = requireFile(files, demoFilename);
  demo.pos = 0;

  mt_srand(DEMO_SEED);

  g.difficultyLevel = DIFFICULTY_NORMAL;

  const h = parseDemoHeader(demo.file);
  demo.pos = DEMO_HEADER_SIZE;
  const items = g.player[0].items;
  JE_initEpisode(h.episode, files);
  g.levelName = h.levelName;
  g.lvlFileNum = h.lvlFileNum;
  items.weapon[FRONT_WEAPON].id = h.frontWeapon;
  items.weapon[REAR_WEAPON].id = h.rearWeapon;
  items.super_arcade_mode = h.superArcadeMode;
  items.sidekick[LEFT_SIDEKICK] = h.leftSidekick;
  items.sidekick[RIGHT_SIDEKICK] = h.rightSidekick;
  items.generator = h.generator;
  items.sidekick_level = h.sidekickLevel;
  items.sidekick_series = h.sidekickSeries;
  g.initial_episode_num = h.initialEpisodeNum;
  items.shield = h.shield;
  items.special = h.special;
  items.ship = h.ship;
  items.weapon[FRONT_WEAPON].power = h.frontPower;
  items.weapon[REAR_WEAPON].power = h.rearPower;
  g.levelSong = h.levelSong;

  const data = readAtMost(2);

  demo.keys = 0;
  // memReadU16BE on a short read leaves 0 (the reader's error flag is asserted, not acted on).
  demo.keysWait = data.length === 2 ? u16((data[0] << 8) | data[1]) : 0;
}

/**
 * playDemoKeys (demo.c L106-145): this tick's recorded keys move player 1 and set the fire and
 * sidekick buttons. Returns false once the recording has run out.
 */
export function playDemoKeys(): boolean {
  while (demo.keysWait === 0) {
    const data = readAtMost(3);

    if (data.length < 3) return false;

    demo.keys = data[0];
    demo.keysWait = u16((data[1] << 8) | data[2]);
  }

  demo.keysWait = u16(demo.keysWait - 1);

  const p = g.player[0];
  const keys = demo.keys;
  if (keys & (1 << KEY_SETTING_UP)) p.y -= CURRENT_KEY_SPEED;
  if (keys & (1 << KEY_SETTING_DOWN)) p.y += CURRENT_KEY_SPEED;

  if (keys & (1 << KEY_SETTING_LEFT)) p.x -= CURRENT_KEY_SPEED;
  if (keys & (1 << KEY_SETTING_RIGHT)) p.x += CURRENT_KEY_SPEED;

  const button = g.button;
  button[0] = (keys & (1 << KEY_SETTING_FIRE)) !== 0;
  button[3] = (keys & (1 << KEY_SETTING_CHANGE_FIRE)) !== 0;
  button[1] = (keys & (1 << KEY_SETTING_LEFT_SIDEKICK)) !== 0;
  button[2] = (keys & (1 << KEY_SETTING_RIGHT_SIDEKICK)) !== 0;

  return true;
}

/** endPlayDemo (demo.c L147-150). */
export function endPlayDemo(): void {
  demo.file = null;
  demo.pos = 0;
}

/**
 * From the title to a demo's first tick, as the C goes there when the title sits idle: the main
 * loop's reset before the title (opentyr.c L873-880: JE_initPlayerData, gameLoaded and jumpSection
 * false), titleScreen's `playDemo = true` (tyrian2.c L3309), then JE_main's JE_loadMap, which runs
 * beginPlayDemo instead of the episode script. The host then calls startLevel() and ticks.
 *
 * Not in the C: the state a game or an earlier demo leaves behind that the level start doesn't
 * reset is put back to its value at program start, so a demo always plays the same whatever was
 * played before it, and as the cross-check against the C (which starts fresh) sees it. In the C a
 * demo after a game can play differently: the players (their movement friction counters, score and
 * the rest), optionAttachmentReturn, initialDifficulty (event 66 reads it) and the bonus-level flags
 * of the last `]L[` all carry over.
 */
export function loadDemoLevel(files: TyrianFiles): void {
  for (const p of g.player) Object.assign(p, newPlayer());
  g.initialDifficulty = 0;
  g.bonusLevelCurrent = false;
  g.normalBonusLevelCurrent = false;
  g.optionAttachmentReturn = false;

  JE_initPlayerData();
  g.gameLoaded = false;
  g.jumpSection = false;

  g.playDemo = true;
  demoState.stoppedDemo = false;

  // JE_loadMap; the episode and section are beginPlayDemo's to set.
  loadLevel(files, g.episodeNum >= 1 ? g.episodeNum : 1, g.mainLevel);
}

/**
 * The end of a demo (start_level, tyrian2.c L613-627 and L656-657): close the recording and put
 * the difficulty back; JE_main then returns to the title (opentyr.c's main loop clears playDemo).
 */
export function finishDemo(): void {
  endPlayDemo();
  g.difficultyLevel = g.oldDifficultyLevel; /*Return difficulty to normal*/
  g.playDemo = false;
}

/** Whether all five demo files are present. */
export function hasDemos(files: TyrianFiles): boolean {
  for (let n = 1; n <= DEMO_COUNT; n++) if (!files.get(`demo.${n}`)) return false;
  return true;
}
