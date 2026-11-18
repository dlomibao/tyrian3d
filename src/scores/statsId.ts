// "Share anonymous play stats" (Options, in builds with the shared list): on by default. When on,
// the game keeps a random player id (crypto.randomUUID, never derived from the device) in this
// browser and sends per-level play reports with it; when off, no id is made or sent and no reports
// go out (high-score submissions still do). Kept beside the settings, under its own key.

export const STATS_STORAGE_KEY = "tyrian3d.stats";

export interface StatsStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

interface StoredStats {
  share?: boolean;
  id?: string;
}

function defaultStorage(): StatsStorage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

/** The stats settings, in memory when storage is unavailable. */
let memory: StoredStats = {};
let storage: StatsStorage | null | undefined;

const store = () => (storage === undefined ? (storage = defaultStorage()) : storage);

/** Use `s` instead of localStorage (tests); resets the in-memory copy. */
export function setStatsStorage(s: StatsStorage | null): void {
  storage = s;
  memory = {};
}

function read(): StoredStats {
  try {
    const t = store()?.getItem(STATS_STORAGE_KEY);
    if (t) {
      const v = JSON.parse(t) as StoredStats;
      if (v && typeof v === "object") return { share: typeof v.share === "boolean" ? v.share : undefined, id: typeof v.id === "string" ? v.id : undefined };
    }
  } catch {
    /* unreadable: the defaults */
  }
  return { ...memory };
}

function write(v: StoredStats): void {
  memory = { ...v };
  try {
    store()?.setItem(STATS_STORAGE_KEY, JSON.stringify(v));
  } catch {
    /* storage full or blocked: kept until the page closes */
  }
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function newId(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  // A v4 UUID from getRandomValues (randomUUID needs a secure context).
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

/** Whether play stats are shared: on unless the player turned it off. */
export function statsSharing(): boolean {
  return read().share !== false;
}

export function setStatsSharing(on: boolean): void {
  write({ ...read(), share: on });
}

/**
 * The player id to send, made on first use while sharing is on; null while it's off (an id made
 * earlier is left unused, not sent).
 */
export function statsPlayerId(): string | null {
  const v = read();
  if (v.share === false) return null;
  if (v.id && UUID.test(v.id)) return v.id;
  const id = newId();
  write({ ...v, id });
  return id;
}

/** "Reset my stats ID": a new random id from now on. */
export function resetStatsPlayerId(): string {
  const id = newId();
  write({ ...read(), id });
  return id;
}

/** The stored id without making one (tests and the Options row). */
export function storedStatsPlayerId(): string | null {
  return read().id ?? null;
}
