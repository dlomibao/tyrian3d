// The shared high-score list's client: the run token, score submissions, the top 20, and the
// per-level play reports. Only in builds made with VITE_SCORES_API (the lomibao.net deployment, e.g.
// VITE_SCORES_API=/api); without it every call here is a no-op and the game behaves as before.
// Every call is best effort: a failure or timeout changes nothing in the game.

import type { RunData } from "../../server/scores/lib/runHash.d.mts";
import type { LevelReport } from "../../server/scores/lib/report.d.mts";

/** The API's base URL, or null when the build has no shared list. */
export const SCORES_API: string | null = (import.meta.env.VITE_SCORES_API as string | undefined)?.replace(/\/+$/, "") || null;

/** The build's id for reports (VITE_BUILD_ID, e.g. a git commit), or "dev". */
export const BUILD_ID: string = ((import.meta.env.VITE_BUILD_ID as string | undefined) || "dev").slice(0, 40);

export const scoresEnabled = (): boolean => SCORES_API !== null;

/** fetch with a time limit; null on any failure. */
async function call<T>(path: string, init: RequestInit = {}, ms = 6000): Promise<T | null> {
  if (!SCORES_API) return null;
  try {
    const res = await fetch(`${SCORES_API}${path}`, { ...init, signal: AbortSignal.timeout(ms) });
    const body = (await res.json().catch(() => null)) as T | null;
    return body;
  } catch {
    return null;
  }
}

const post = <T>(path: string, body: unknown) => call<T>(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export interface RunStart {
  episode: number;
  difficulty: number;
  mode: string;
  /** Only when "Share anonymous play stats" is on. */
  playerId?: string;
}

/** POST /api/runs: a run token for a new game, or null. */
export async function requestRunToken(start: RunStart): Promise<{ token: string; issuedAt: number } | null> {
  const r = await post<{ token?: unknown; issuedAt?: unknown }>("/runs", { ...start, build: BUILD_ID });
  return r && typeof r.token === "string" && typeof r.issuedAt === "number" ? { token: r.token, issuedAt: r.issuedAt } : null;
}

export type SubmitResult = { ok: true; rank: number; total?: number } | { ok: false; reason: string };

/** POST /api/scores. */
export async function submitScore(run: RunData & { name: string; hash: string }): Promise<SubmitResult | null> {
  const r = await post<SubmitResult>("/scores", run);
  return r && typeof r.ok === "boolean" ? r : null;
}

export interface SharedScore {
  rank: number;
  name: string;
  score: number;
  difficulty: number;
  levels: number;
  date: string;
}

/** GET /api/scores: the top 20 for an episode (and difficulty, or all). */
export async function fetchTopScores(episode: number, difficulty?: number): Promise<SharedScore[] | null> {
  const q = `episode=${episode}${difficulty ? `&difficulty=${difficulty}` : ""}`;
  const r = await call<{ scores?: unknown }>(`/scores?${q}`, {}, 5000);
  return r && Array.isArray(r.scores) ? (r.scores as SharedScore[]) : null;
}

/** POST /api/levels/report, fire and forget (sendBeacon, or a keepalive fetch). */
export function sendLevelReport(report: LevelReport): void {
  if (!SCORES_API) return;
  const url = `${SCORES_API}/levels/report`;
  const body = JSON.stringify(report);
  try {
    // text/plain keeps the beacon a simple request; the server reads JSON whatever the type.
    if (typeof navigator !== "undefined" && navigator.sendBeacon?.(url, new Blob([body], { type: "text/plain;charset=UTF-8" }))) return;
  } catch {
    /* fall through to fetch */
  }
  try {
    void fetch(url, { method: "POST", body, keepalive: true, headers: { "Content-Type": "text/plain;charset=UTF-8" } }).catch(() => {});
  } catch {
    /* never let a report affect the game */
  }
}
