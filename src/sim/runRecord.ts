// The run record for the shared high-score list (only used when the build has VITE_SCORES_API; see
// src/scores/): the server's run token, the levels played so far (the path the server checks),
// and whether anything outside normal play touched the run (the taint: a tainted run never submits).
//
// It rides along with the game's state: JE_saveGame stores it in the slot and JE_loadGame brings it
// back (src/sim/savegame.ts), when `runRecord.persist` is on (builds with the shared list), so a
// saved and reloaded run keeps its token, its path and its taint. The game's own behaviour doesn't
// change: nothing here is read by the simulation.

export interface RunLevelEntry {
  /** lvlFileNum: the level's id in its episode. */
  lvl: number;
  /** Sim ticks the level ran. */
  ticks: number;
  /** JE_totalScore at its end. */
  score: number;
  /** Finished; false only for the level a run was quit in (never stored). */
  done: boolean;
}

export type RunMode = "story" | "arcade" | "twoPlayer" | "superArcade" | "superTyrian";

export interface RunRecord {
  v: 1;
  /** Random id made when the run starts: matches a run across its own saves (the retry backup). */
  runId: string;
  /** The server's run token; null until (or unless) it arrives. */
  token: string | null;
  issuedAt: number;
  episode: number;
  /** initialDifficulty */
  difficulty: number;
  mode: RunMode;
  tainted: boolean;
  /** Why (each source once): "console", "cheat-keys", "loot", "seed", "debug", ... */
  taints: string[];
  levels: RunLevelEntry[];
}

export const runRecord: {
  /** The run being played (null: none, or a game loaded from a save made without one). */
  current: RunRecord | null;
  /** Store the record in saves (builds with the shared list). */
  persist: boolean;
  /** Taints of this page session (the console, URL parameters): every run touched since carries them. */
  sessionTaints: string[];
} = { current: null, persist: false, sessionTaints: [] };

const randomId = (): string =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;

/** A new game's record, carrying the session's taints. */
export function newRunRecord(episode: number, difficulty: number, mode: RunMode): RunRecord {
  const r: RunRecord = { v: 1, runId: randomId(), token: null, issuedAt: 0, episode, difficulty, mode, tainted: false, taints: [], levels: [] };
  for (const t of runRecord.sessionTaints) addTaint(r, t);
  runRecord.current = r;
  return r;
}

function addTaint(r: RunRecord, reason: string): void {
  r.tainted = true;
  if (!r.taints.includes(reason)) r.taints.push(reason);
}

/**
 * Something outside normal play happened. `session`: it lasts for the rest of the page session, so
 * runs started or loaded later carry it too (the debug console, a URL parameter); otherwise only the
 * current run is touched (a cheat key in flight).
 */
export function taintRun(reason: string, session = false): void {
  if (session && !runRecord.sessionTaints.includes(reason)) runRecord.sessionTaints.push(reason);
  if (runRecord.current) addTaint(runRecord.current, reason);
}

export function cloneRunRecord(r: RunRecord): RunRecord {
  return { ...r, taints: [...r.taints], levels: r.levels.map((l) => ({ ...l })) };
}

const isInt = (v: unknown, lo: number, hi: number): v is number => Number.isInteger(v) && (v as number) >= lo && (v as number) <= hi;
const MODES: readonly RunMode[] = ["story", "arcade", "twoPlayer", "superArcade", "superTyrian"];

/** A stored record, checked field by field; null if anything is off (the save then has none). */
export function parseRunRecord(o: unknown): RunRecord | null {
  if (!o || typeof o !== "object") return null;
  const r = o as Record<string, unknown>;
  if (r.v !== 1 || typeof r.runId !== "string" || r.runId.length > 64) return null;
  if (!(r.token === null || (typeof r.token === "string" && r.token.length <= 1024))) return null;
  if (!isInt(r.issuedAt, 0, Number.MAX_SAFE_INTEGER) || !isInt(r.episode, 1, 5) || !isInt(r.difficulty, 0, 10)) return null;
  if (!MODES.includes(r.mode as RunMode) || typeof r.tainted !== "boolean") return null;
  if (!Array.isArray(r.taints) || !r.taints.every((t) => typeof t === "string" && t.length <= 32)) return null;
  if (!Array.isArray(r.levels) || r.levels.length > 100) return null;
  const levels: RunLevelEntry[] = [];
  for (const l of r.levels as Record<string, unknown>[]) {
    if (!l || !isInt(l.lvl, 0, 255) || !isInt(l.ticks, 0, 1e9) || !isInt(l.score, -(2 ** 31), 2 ** 32) || typeof l.done !== "boolean") return null;
    levels.push({ lvl: l.lvl, ticks: l.ticks, score: l.score, done: l.done });
  }
  return { v: 1, runId: r.runId, token: r.token as string | null, issuedAt: r.issuedAt, episode: r.episode, difficulty: r.difficulty, mode: r.mode as RunMode, tainted: r.tainted, taints: [...(r.taints as string[])], levels };
}

/** For JE_saveGame: what the slot stores (undefined: nothing, without the shared list). */
export function runRecordToSave(): RunRecord | undefined {
  return runRecord.persist && runRecord.current ? cloneRunRecord(runRecord.current) : undefined;
}

/**
 * For JE_loadGame: the slot's record becomes the current run. A taint is never lost: reloading the
 * same run's earlier save (the retry backup, or a save from before a cheat) keeps the taint and the
 * token it has now, and the session's taints apply to whatever is loaded.
 */
export function runRecordFromSave(saved: RunRecord | undefined): void {
  if (!runRecord.persist) return;
  const now = runRecord.current;
  const r = saved ? cloneRunRecord(saved) : null;
  if (r && now && now.runId === r.runId) {
    r.token ??= now.token;
    if (!r.issuedAt) r.issuedAt = now.issuedAt;
    for (const t of now.taints) addTaint(r, t);
  }
  if (r) for (const t of runRecord.sessionTaints) addTaint(r, t);
  runRecord.current = r;
}
