// The shape of GET /api/stats/summary (server/scores/lib/stats.mjs computeSummary, README
// "Summary"). JSON object keys are strings: episode, lvl, difficulty, item ids, k, CC, YYYY-MM.

export type Counts = Record<string, number>;

export interface Outcome {
  finished: number;
  died: number;
  quit: number;
}

export interface Percentiles {
  n: number;
  p25?: number;
  p50?: number;
  p75?: number;
  p90?: number;
}

export interface DayPlayers {
  day: string;
  players: number;
  new: number;
  returning: number;
}

export interface MonthPlayers {
  month: string;
  players: number;
  new: number;
  returning: number;
}

export interface StatsSummary {
  generatedAt: string;
  deathBucketPx: number;
  reports: { total: number; tainted: number };
  runs: { total: number; submitted: number };
  /** {episode: [{from: prev lvl | null, to: lvl, n}]}: a retry isn't a transition. */
  paths: Record<string, { from: number | null; to: number; n: number }[]>;
  /** {episode: {lvl: {difficulty: outcome counts}}}. */
  outcomes: Record<string, Record<string, Record<string, Partial<Outcome>>>>;
  /** {episode: {lvl: [[bx, by, n]]}}, bx = floor(x / deathBucketPx). */
  deaths: Record<string, Record<string, [number, number, number][]>>;
  /** {episode: {lvl: {front weapon port id: levels flown}}}. */
  weapons: Record<string, Record<string, Counts>>;
  /** {episode: {lvl: {ship id: levels flown}}}. */
  ships: Record<string, Record<string, Counts>>;
  /** {episode: {lvl: percentiles}}, finished levels only. */
  scoreGained: Record<string, Record<string, Percentiles>>;
  /** {kind: {slot: {item id: trades}}}. */
  shop: Record<string, Record<string, Counts>>;
  countries: {
    runs: Counts;
    reports: Counts;
    runsByMonth: Record<string, Counts>;
    reportsByMonth: Record<string, Counts>;
  };
  players: {
    total: number;
    perDay: DayPlayers[];
    perMonth: MonthPlayers[];
    /** {runs: players}. */
    runsPerPlayer: Counts;
    /** {days: players}. */
    daysPerPlayer: Counts;
  };
  /** {episode: {k: players who reached at least the k-th level of their run}}. */
  funnel: Record<string, Counts>;
}

/** The summary, or null if `v` isn't one (a dev server's fallback page, a proxy's error page). */
export function asSummary(v: unknown): StatsSummary | null {
  if (!v || typeof v !== "object") return null;
  const s = v as Partial<StatsSummary>;
  if (typeof s.generatedAt !== "string" || !s.reports || !s.runs || !s.players || !s.countries) return null;
  return s as StatsSummary;
}
