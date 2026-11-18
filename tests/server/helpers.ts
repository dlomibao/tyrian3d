// Shared set-up for the scores service tests: an in-process server on a random port with a temp
// database and an injectable clock.
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer, type ScoresApp, type ServerOptions } from "../../server/scores/server.mjs";
import { loadConfig } from "../../server/scores/lib/config.mjs";
import { runHash, type RunData } from "../../server/scores/lib/runHash.mjs";
import type { LevelReport } from "../../server/scores/lib/report.mjs";

export const MAX_SCORES = JSON.parse(readFileSync("server/scores/maxScores.json", "utf8"));
export const TICK_HZ: number = MAX_SCORES.tickHz;
export const SECRET = "test-secret-0123456789-abcdefghijklmnop";
export const SALT = "test-salt-0123456789";
export const GEO_FIXTURE = "tests/server/fixtures/dbip-country-lite-sample.csv";
export const HOUR = 3600 * 1000;
export const DAY = 24 * HOUR;

export interface Api {
  app: ScoresApp;
  base: string;
  dir: string;
  dbPath: string;
  clock: { t: number };
  call(method: string, path: string, body?: unknown, headers?: Record<string, string>): Promise<{ status: number; json: any; headers: Headers }>;
  close(): Promise<void>;
}

/** Start a server; `clock.t` is its time (ms). */
export async function startApi(options: Partial<ServerOptions> = {}, t0 = Date.UTC(2026, 10, 18, 12)): Promise<Api> {
  const dir = mkdtempSync(join(tmpdir(), "tyrian-scores-"));
  const dbPath = join(dir, "scores.db");
  const clock = { t: t0 };
  const config = {
    ...loadConfig({ SCORES_HMAC_SECRET: SECRET, SCORES_IP_SALT: SALT, SCORES_DB: dbPath, PORT: "0" }),
    maxScores: MAX_SCORES,
    now: () => clock.t,
    ...options,
  };
  const app = createServer(config);
  const port = await app.listen(0);
  const base = `http://127.0.0.1:${port}`;
  return {
    app,
    base,
    dir,
    dbPath,
    clock,
    async call(method, path, body, headers = {}) {
      const init: RequestInit = { method, headers: { "content-type": "application/json", ...headers } };
      if (body !== undefined) init.body = typeof body === "string" ? body : JSON.stringify(body);
      const r = await fetch(base + path, init);
      const text = await r.text();
      return { status: r.status, json: text ? JSON.parse(text) : null, headers: r.headers };
    },
    async close() {
      await app.close();
      rmSync(dir, { recursive: true, force: true });
    },
  };
}

/** X-Forwarded-For from the (trusted, loopback) test client: simulates a client address. */
export const from = (ip: string) => ({ "x-forwarded-for": ip });

export async function newRun(api: Api, body: Record<string, unknown> = {}, headers: Record<string, string> = {}): Promise<string> {
  const r = await api.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "test", ...body }, headers);
  if (r.status !== 200) throw new Error(`POST /api/runs ${r.status} ${JSON.stringify(r.json)}`);
  return r.json.token;
}

/**
 * A plausible episode 1 Normal run (the bot's reference: TYRIAN in 9350 ticks to 33750, then
 * ASTEROID2 in 12861 ticks to 36030, from 19500).
 */
export function validRun(token: string, over: Partial<RunData> = {}): RunData {
  return {
    token,
    episode: 1,
    difficulty: 2,
    mode: "story",
    tickHz: TICK_HZ,
    ended: "quit",
    ship: 1,
    front: { id: 1, power: 1 },
    rear: { id: 0, power: 0 },
    shield: 1,
    generator: 1,
    sidekicks: [0, 0],
    levels: [
      { lvl: 9, ticks: 9350, score: 33750, done: true },
      { lvl: 2, ticks: 12861, score: 36030, done: true },
    ],
    score: 36030,
    ...over,
  };
}

export async function submit(api: Api, run: RunData, name = "Tester", extra: Record<string, unknown> = {}, headers: Record<string, string> = {}) {
  return api.call("POST", "/api/scores", { ...run, name, hash: await runHash(run), ...extra }, headers);
}

export function report(token: string, playerId: string, over: {
  run?: Partial<LevelReport["run"]>;
  level?: Partial<LevelReport["level"]>;
  loadout?: Partial<LevelReport["loadout"]>;
  outcome?: Partial<LevelReport["outcome"]>;
  shop?: LevelReport["shop"];
  tainted?: boolean;
} = {}): LevelReport {
  return {
    v: 1,
    token,
    playerId,
    build: "test",
    tainted: over.tainted ?? false,
    run: { episode: 1, difficulty: 2, difficultyNow: 2, mode: "story", tickHz: TICK_HZ, ...over.run },
    level: { lvl: 9, name: "TYRIAN", section: 3, index: 0, prev: null, via: "start", ...over.level },
    loadout: { ship: 1, front: { id: 1, power: 1 }, rear: { id: 0, power: 0 }, sidekicks: [0, 0], shield: 1, generator: 1, armor: 10, credits: 10000, ...over.loadout },
    outcome: {
      result: "finished", ticks: 9350, scoreGained: 14250, deaths: [], enemiesKilled: 50, enemiesSpawned: 80, bossesKilled: 1,
      shotsFired: 900, hits: 400, damageTaken: 5, pickups: 3, coins: 10, cubes: 1, warps: 0, superbombs: 0, specials: null,
      ...over.outcome,
    },
    shop: over.shop ?? [],
  };
}
