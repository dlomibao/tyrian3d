// Where the high score tables live: OpenTyrian keeps them in tyrian.sav (loadSaves/saveSaves,
// config.c); here they are the same 22 saveFiles entries (src/sim/highscores.ts) as JSON in
// localStorage. A missing or unreadable copy gets loadSaves' random defaults, as a missing
// tyrian.sav does.

import { defaultHighScores, JE_sortHighScores, SAVE_FILES_NUM, type HighScoreEntry } from "../sim/highscores";

const STORAGE_KEY = "tyrian3d.highScores";

/** The last tables saved, for when localStorage is blocked or full: they last until the page closes. */
let sessionCopy: string | null = null;

/** mt_rand as the C has it at loadSaves: seeded with the time, so any 32-bit random number. */
const timeSeededRand = (): number => Math.floor(Math.random() * 0x100000000);

function valid(e: unknown): e is HighScoreEntry {
  if (typeof e !== "object" || e === null) return false;
  const o = e as Record<string, unknown>;
  return (
    Number.isInteger(o.highScore1) &&
    Number.isInteger(o.highScore2) &&
    typeof o.highScoreName === "string" &&
    Number.isInteger(o.highScoreDiff)
  );
}

/** Read and parse a stored table; null if it isn't a well-formed 22-entry table. */
export function parseHighScores(json: string | null): HighScoreEntry[] | null {
  if (!json) return null;
  try {
    const data: unknown = JSON.parse(json);
    if (!Array.isArray(data) || data.length !== SAVE_FILES_NUM || !data.every(valid)) return null;
    return data.map((e) => ({
      highScore1: e.highScore1 | 0, // JE_longint
      highScore2: e.highScore2 | 0,
      highScoreName: e.highScoreName.slice(0, 29), // string[29]
      highScoreDiff: e.highScoreDiff & 0xff, // JE_byte
    }));
  } catch {
    return null;
  }
}

/**
 * loadSaves (config.c L774-862) then JE_sortHighScores (opentyr.c L874): the stored tables, or
 * new random defaults (which are stored, so they stay the same from then on).
 */
export function loadHighScores(): HighScoreEntry[] {
  let stored: string | null = null;
  try {
    stored = localStorage.getItem(STORAGE_KEY);
  } catch {
    // Storage blocked (private mode, sandbox): fall back to this session's copy.
  }
  let saveFiles = parseHighScores(stored ?? sessionCopy);
  if (!saveFiles) {
    saveFiles = defaultHighScores(timeSeededRand);
    saveHighScores(saveFiles);
  }
  JE_sortHighScores(saveFiles);
  return saveFiles;
}

/** saveSaves (config.c L866-913), the high score fields only. */
export function saveHighScores(saveFiles: HighScoreEntry[]): void {
  sessionCopy = JSON.stringify(saveFiles);
  try {
    localStorage.setItem(STORAGE_KEY, sessionCopy);
  } catch {
    // Storage full or blocked: sessionCopy keeps the tables until the page is closed.
  }
}
