// Tyrian 3D shared high scores and anonymous play stats (README.md). Dependency-free: node:http and
// node:sqlite (Node 22). Run with: node --env-file=<scores.env> server.mjs
import { readFileSync, realpathSync } from "node:fs";
import http from "node:http";
import { pathToFileURL } from "node:url";
import { DEFAULT_LIMITS, loadConfig } from "./lib/config.mjs";
import { openDb, transaction } from "./lib/db.mjs";
import { lookupCountry } from "./lib/geo.mjs";
import { HttpError, clientIp, readJson, sendEmpty, sendJson } from "./lib/http.mjs";
import { checkRun, DIFFICULTIES } from "./lib/plausibility.mjs";
import { RateLimiter, ipHash, utcDay, utcMonth } from "./lib/ratelimit.mjs";
import { insertReport, validateReport } from "./lib/report.mjs";
import { runHash } from "./lib/runHash.mjs";
import { computeSummary } from "./lib/stats.mjs";
import { REPORT_TOKEN_MAX_AGE_MS, issueToken, verifyToken } from "./lib/token.mjs";
import { validateRunRequest, validateScore } from "./lib/validate.mjs";

/** Level reports per run token. */
export const REPORTS_PER_RUN = 200;
/** Entries in GET /api/scores. */
export const TOP_N = 20;
/** How long GET /api/stats/summary is cached. */
export const SUMMARY_TTL_MS = 10 * 60 * 1000;

/**
 * The service. `config` is loadConfig()'s, plus for tests: `now` (a clock, ms), `maxScores` (the
 * parsed data instead of maxScoresPath), `limits` (per-hour overrides). Returns
 * {server, db, listen(port?, host?) -> Promise<port>, close() -> Promise}.
 */
export function createServer(config) {
  const now = config.now ?? Date.now;
  const maxScores = config.maxScores ?? JSON.parse(readFileSync(config.maxScoresPath, "utf8"));
  const db = openDb(config.dbPath);
  const limits = { ...DEFAULT_LIMITS, ...config.limits };
  const summaryTtl = config.summaryTtlMs ?? SUMMARY_TTL_MS;
  // Two separate limiters: an IP hash and a player id are never put in one key.
  const ipLimiter = new RateLimiter();
  const playerLimiter = new RateLimiter();
  let summaryCache = null;

  const sql = {
    insertRun: db.prepare(`INSERT INTO runs (id, issued_at, episode, difficulty, mode, build, player_id, country)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`),
    getRun: db.prepare("SELECT player_id, used_at FROM runs WHERE id = ?"),
    consumeRun: db.prepare("UPDATE runs SET used_at = ? WHERE id = ? AND used_at IS NULL"),
    countReport: db.prepare(`UPDATE runs SET report_count = report_count + 1 WHERE id = ? AND report_count < ${REPORTS_PER_RUN}`),
    insertScore: db.prepare(`INSERT INTO scores (run_id, name, score, episode, difficulty, ended, levels, level_count, ticks, cap, created_at, country)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`),
    rankOf: db.prepare(`SELECT count(*) AS n FROM scores WHERE episode = ? AND difficulty = ?
                        AND (score > ? OR (score = ? AND (created_at < ? OR (created_at = ? AND id < ?))))`),
    boardSize: db.prepare("SELECT count(*) AS n FROM scores WHERE episode = ? AND difficulty = ?"),
    topByDifficulty: db.prepare(`SELECT name, score, difficulty, level_count, created_at FROM scores
                                 WHERE episode = ? AND difficulty = ? ORDER BY score DESC, created_at, id LIMIT ${TOP_N}`),
    topByEpisode: db.prepare(`SELECT name, score, difficulty, level_count, created_at FROM scores
                              WHERE episode = ? ORDER BY score DESC, created_at, id LIMIT ${TOP_N}`),
    insertRejected: db.prepare(`INSERT INTO rejected (created_at, reason, detail, run_id, episode, difficulty, score, country)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)`),
    health: db.prepare("SELECT 1 AS one"),
  };

  /** 429 if the IP hash (and the player id, if given) is over this endpoint's hourly limit. */
  function rateLimit(kind, t, ipKey, playerId) {
    const retry = (ipKey ? ipLimiter.hit(`${kind}:${ipKey}`, limits[kind], t) : 0) || (playerId ? playerLimiter.hit(`${kind}:${playerId}`, limits[kind], t) : 0);
    if (retry) throw new HttpError(429, { ok: false, reason: "rate-limited", retryAfter: retry });
  }

  async function postRun(req, res, t, ip) {
    rateLimit("runs", t, ipHash(config.ipSalt, ip, t));
    const v = validateRunRequest(await readJson(req));
    if (!v.ok) return sendJson(res, 400, { ok: false, reason: v.reason, error: v.error });
    rateLimit("runs", t, null, v.value.playerId);
    const { episode, difficulty, mode, build, playerId } = v.value;
    const { token, payload } = issueToken(config.hmacSecret, { ep: episode, diff: difficulty, mode }, t);
    sql.insertRun.run(payload.id, t, episode, difficulty, mode, build, playerId, lookupCountry(db, ip));
    sendJson(res, 200, { token, issuedAt: t });
  }

  async function postScore(req, res, t, ip) {
    rateLimit("scores", t, ipHash(config.ipSalt, ip, t));
    const v = validateScore(await readJson(req), maxScores.tickHz);
    if (!v.ok) return sendJson(res, 400, { ok: false, reason: v.reason, error: v.error });
    const { run, name } = v;
    const hash = await runHash(run); // before the synchronous token-consume-insert section below
    const country = lookupCountry(db, ip);
    const reject = (reason, detail, runId) => {
      sql.insertRejected.run(t, reason, String(detail ?? "").slice(0, 200), runId ?? null, run.episode, run.difficulty, run.score, country);
      sendJson(res, 422, { ok: false, reason });
    };

    // The token: signed, not expired, for this episode/difficulty/mode, issued, unused.
    const tk = verifyToken(config.hmacSecret, run.token, t);
    if (!tk.ok) return reject(tk.reason, "", tk.payload?.id);
    const p = tk.payload;
    if (p.ep !== run.episode || p.diff !== run.difficulty || p.mode !== run.mode) return reject("mismatch", `token ${p.ep}/${p.diff}/${p.mode}`, p.id);
    const row = sql.getRun.get(p.id);
    if (!row) return reject("unknown-run", "", p.id);
    rateLimit("scores", t, null, row.player_id); // before consuming, so a 429 can be retried
    // Consumed by any submission that gets this far, accepted or not: a token can't probe the bounds.
    if (row.used_at !== null || sql.consumeRun.run(t, p.id).changes !== 1) return reject("reused", "", p.id);

    if (hash !== v.hash) return reject("hash", "", p.id);
    const check = checkRun(maxScores, run, t - p.iat);
    if (!check.ok) return reject(check.reason, check.detail, p.id);

    const ticks = run.levels.reduce((a, l) => a + l.ticks, 0);
    const levelCount = run.levels.filter((l) => l.done).length;
    const { lastInsertRowid } = sql.insertScore.run(p.id, name, run.score, run.episode, run.difficulty, run.ended, JSON.stringify(run.levels), levelCount, ticks, check.cap, t, country);
    const rank = sql.rankOf.get(run.episode, run.difficulty, run.score, run.score, t, t, lastInsertRowid).n + 1;
    const total = sql.boardSize.get(run.episode, run.difficulty).n;
    sendJson(res, 200, { ok: true, rank, total });
  }

  function getScores(res, url, t, ip) {
    rateLimit("get", t, ipHash(config.ipSalt, ip, t));
    const episode = Number(url.searchParams.get("episode"));
    const d = url.searchParams.get("difficulty");
    const difficulty = d === null || d === "" ? null : Number(d);
    if (!Number.isInteger(episode) || episode < 1 || episode > 4) return sendJson(res, 400, { ok: false, reason: "invalid", error: "episode" });
    if (difficulty !== null && !DIFFICULTIES.includes(difficulty)) return sendJson(res, 400, { ok: false, reason: "invalid", error: "difficulty" });
    const rows = difficulty === null ? sql.topByEpisode.all(episode) : sql.topByDifficulty.all(episode, difficulty);
    sendJson(res, 200, {
      episode,
      difficulty,
      scores: rows.map((r, i) => ({ rank: i + 1, name: r.name, score: r.score, difficulty: r.difficulty, levels: r.level_count, date: utcDay(r.created_at) })),
    });
  }

  async function postReport(req, res, t, ip) {
    rateLimit("reports", t, ipHash(config.ipSalt, ip, t));
    const body = await readJson(req);
    const v = validateReport(body);
    if (!v.ok) return sendJson(res, 400, { ok: false, reason: "invalid", error: v.error });
    const r = v.report;
    rateLimit("reports", t, null, r.playerId);
    // A signed token, up to 60 days old, for this run's episode/difficulty/mode.
    const tk = verifyToken(config.hmacSecret, body.token, t, REPORT_TOKEN_MAX_AGE_MS);
    if (!tk.ok) return sendJson(res, 403, { ok: false, reason: tk.reason });
    const p = tk.payload;
    if (p.ep !== r.episode || p.diff !== r.difficulty || p.mode !== r.mode) return sendJson(res, 403, { ok: false, reason: "mismatch" });
    const stored = transaction(db, () => {
      if (sql.countReport.run(p.id).changes !== 1) return false; // no such run, or its 200 reports are in
      insertReport(db, r, { runId: p.id, country: lookupCountry(db, ip), now: t, month: utcMonth(t), day: utcDay(t) });
      return true;
    });
    if (!stored) return sendJson(res, 429, { ok: false, reason: sql.getRun.get(p.id) ? "cap" : "unknown-run" });
    sendEmpty(res, 204);
  }

  function getSummary(res, t, ip) {
    rateLimit("get", t, ipHash(config.ipSalt, ip, t));
    if (!summaryCache || t - summaryCache.at >= summaryTtl) summaryCache = { at: t, body: computeSummary(db, t) };
    sendJson(res, 200, summaryCache.body);
  }

  async function handle(req, res) {
    const t = now();
    const url = new URL(req.url ?? "/", "http://localhost");
    const ip = clientIp(req, config.trustProxy); // used for the rate-limit hash and the country, then dropped
    if (config.corsOrigin) {
      res.setHeader("Access-Control-Allow-Origin", config.corsOrigin);
      res.setHeader("Vary", "Origin");
    }
    const route = `${req.method} ${url.pathname}`;
    switch (route) {
      case "POST /api/runs":
        return postRun(req, res, t, ip);
      case "POST /api/scores":
        return postScore(req, res, t, ip);
      case "GET /api/scores":
        return getScores(res, url, t, ip);
      case "POST /api/levels/report":
        return postReport(req, res, t, ip);
      case "GET /api/stats/summary":
        return getSummary(res, t, ip);
      case "GET /api/health":
        sql.health.get();
        return sendJson(res, 200, { ok: true, db: true });
    }
    if (req.method === "OPTIONS" && config.corsOrigin && url.pathname.startsWith("/api/")) {
      return sendEmpty(res, 204, { "Access-Control-Allow-Methods": "GET, POST", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" });
    }
    sendJson(res, 404, { ok: false, reason: "not-found" });
  }

  const server = http.createServer((req, res) => {
    handle(req, res).catch((e) => {
      if (e instanceof HttpError) {
        const headers = e.body?.retryAfter ? { "Retry-After": String(e.body.retryAfter) } : {};
        if (!res.headersSent) sendJson(res, e.status, e.body, headers);
        return;
      }
      console.error(e?.stack ?? e); // no request details: they could hold an address
      if (!res.headersSent) sendJson(res, 500, { ok: false, reason: "server" });
    });
  });
  server.requestTimeout = 15000;
  server.headersTimeout = 10000;

  return {
    server,
    db,
    /** Listen; resolves with the bound port. */
    listen(port = config.port, host = config.host ?? "127.0.0.1") {
      return new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(port, host, () => resolve(server.address().port));
      });
    },
    /** Stop listening and close the database. */
    close() {
      return new Promise((resolve) => {
        server.close(() => {
          db.close();
          resolve();
        });
        server.closeAllConnections();
      });
    },
  };
}

/** The entry point: config from the environment, listen, print {"listening": port}. */
export async function start(env = process.env) {
  let config;
  try {
    config = loadConfig(env);
  } catch (e) {
    console.error(`tyrian-scores: ${e.message}`);
    process.exit(1);
  }
  const app = createServer(config);
  const port = await app.listen();
  console.log(JSON.stringify({ listening: port }));
  const stop = () => app.close().then(() => process.exit(0));
  process.once("SIGINT", stop);
  process.once("SIGTERM", stop);
  return app;
}

if (process.argv[1] && import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) start();
