// The shared high-score service (server/scores/): run tokens, score submissions, the list.
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { issueToken, verifyToken, TOKEN_MAX_AGE_MS } from "../../server/scores/lib/token.mjs";
import { sanitizeName } from "../../server/scores/lib/validate.mjs";
import { checkRun } from "../../server/scores/lib/plausibility.mjs";
import { DAY, HOUR, MAX_SCORES, SECRET, from, newRun, startApi, submit, validRun, type Api } from "./helpers";

describe("run tokens", () => {
  const t = Date.UTC(2026, 10, 18);
  const { token, payload } = issueToken(SECRET, { ep: 1, diff: 2, mode: "story" }, t);

  test("issue and verify", () => {
    expect(payload).toMatchObject({ v: 1, iat: t, ep: 1, diff: 2, mode: "story" });
    expect(payload.id).toMatch(/^[0-9a-f]{32}$/);
    const v = verifyToken(SECRET, token, t + 1000);
    expect(v.ok && v.payload).toEqual(payload);
  });

  test("expiry after 30 days", () => {
    expect(verifyToken(SECRET, token, t + TOKEN_MAX_AGE_MS).ok).toBe(true);
    expect(verifyToken(SECRET, token, t + TOKEN_MAX_AGE_MS + 1)).toMatchObject({ ok: false, reason: "expired" });
  });

  test("tampering", () => {
    const [part, sig] = token.split(".");
    const forged = Buffer.from(JSON.stringify({ ...payload, diff: 8 })).toString("base64url");
    expect(verifyToken(SECRET, `${forged}.${sig}`, t)).toMatchObject({ ok: false, reason: "token" });
    const flipped = sig.slice(0, -2) + (sig.at(-2) === "A" ? "B" : "A") + sig.at(-1);
    expect(verifyToken(SECRET, `${part}.${flipped}`, t)).toMatchObject({ ok: false, reason: "token" });
    expect(verifyToken(SECRET + "x", token, t)).toMatchObject({ ok: false, reason: "token" });
    expect(verifyToken(SECRET, part, t)).toMatchObject({ ok: false, reason: "token" });
    expect(verifyToken(SECRET, `${token}.x`, t)).toMatchObject({ ok: false, reason: "token" });
    expect(verifyToken(SECRET, 42, t)).toMatchObject({ ok: false, reason: "token" });
    // Issued in the future.
    expect(verifyToken(SECRET, token, t - 3600 * 1000)).toMatchObject({ ok: false, reason: "token" });
  });
});

describe("name sanitising (the game's name-entry rule)", () => {
  test.each([
    ["  Bob__  the <Great>  ", "Bob the Great"],
    ["a&b<c>d@e^f_g`h", "abcdefgh"],
    ["Çé ñ ¿ ₧ƒ", "Çé ñ ¿ ₧ƒ"],
    ["tab\there\nnew", "tabherenew"],
    ["emoji 🚀 ship", "emoji ship"],
    ["{}|~ !", "{}| !"], // ~ is 126: outside 33..125
    ["x".repeat(40), "x".repeat(28)],
    [`${"y".repeat(27)}  z`, "y".repeat(27)], // cut at 28, then trimmed
  ])("%j -> %j", (raw, clean) => expect(sanitizeName(raw)).toBe(clean));
});

describe("score submissions", () => {
  let api: Api;
  beforeAll(async () => {
    api = await startApi({ limits: { runs: 10000, scores: 10000 } });
  });
  afterAll(() => api.close());

  /** A token issued now, with the clock then moved on an hour (the wall-time check passes). */
  async function playedToken(body = {}) {
    const token = await newRun(api, body);
    api.clock.t += HOUR;
    return token;
  }
  const rejectedRow = () => api.app.db.prepare("SELECT * FROM rejected ORDER BY id DESC LIMIT 1").get() as Record<string, unknown>;

  test("POST /api/runs issues a token and stores the run", async () => {
    const playerId = crypto.randomUUID();
    const r = await api.call("POST", "/api/runs", { episode: 2, difficulty: 4, mode: "arcade", build: "abc123", playerId });
    expect(r.status).toBe(200);
    expect(r.json.issuedAt).toBe(api.clock.t);
    const v = verifyToken(SECRET, r.json.token, api.clock.t);
    expect(v.ok).toBe(true);
    if (!v.ok) return;
    const row = api.app.db.prepare("SELECT * FROM runs WHERE id = ?").get(v.payload.id);
    expect(row).toMatchObject({ episode: 2, difficulty: 4, mode: "arcade", build: "abc123", player_id: playerId, country: "ZZ", used_at: null, report_count: 0 });
  });

  test.each([
    [{ episode: 5 }],
    [{ difficulty: 5 }],
    [{ mode: "coop" }],
    [{ build: "" }],
    [{ build: "x".repeat(41) }],
    [{ playerId: "not-a-uuid" }],
  ])("POST /api/runs rejects %j", async (bad) => {
    const r = await api.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "t", ...bad });
    expect(r.status).toBe(400);
  });

  test("an accepted run gets its rank, and the token is single-use", async () => {
    const token = await playedToken();
    const run = validRun(token);
    expect(checkRun(MAX_SCORES, run, HOUR).ok).toBe(true);
    const r = await submit(api, run, "  Bob__  the <Great> ");
    expect(r.status).toBe(200);
    expect(r.json).toEqual({ ok: true, rank: 1, total: 1 });
    const row = api.app.db.prepare("SELECT * FROM scores WHERE run_id = (SELECT id FROM runs WHERE used_at IS NOT NULL)").get() as Record<string, unknown>;
    expect(row).toMatchObject({ name: "Bob the Great", score: 36030, episode: 1, difficulty: 2, level_count: 2, ticks: 22211, verified: "plausible", country: "ZZ" });
    expect(row.cap as number).toBeGreaterThanOrEqual(36030);

    const again = await submit(api, run);
    expect(again.status).toBe(422);
    expect(again.json).toEqual({ ok: false, reason: "reused" });
    expect(rejectedRow()).toMatchObject({ reason: "reused", episode: 1, difficulty: 2, score: 36030 });
  });

  test("a rejected submission consumes the token too", async () => {
    const token = await playedToken();
    const run = validRun(token);
    const bad = await submit(api, run, "x", { hash: "0".repeat(64) });
    expect(bad.json).toEqual({ ok: false, reason: "hash" });
    const retry = await submit(api, run);
    expect(retry.json).toEqual({ ok: false, reason: "reused" });
  });

  test("validation 400s are not stored and don't consume the token", async () => {
    const token = await playedToken();
    const run = validRun(token);
    const before = (api.app.db.prepare("SELECT count(*) AS n FROM rejected").get() as { n: number }).n;
    const lvl = (over: object) => ({ levels: [{ ...run.levels[0], ...over }] });
    const cases: [Record<string, unknown>, string][] = [
      [{ episode: 5 }, "invalid"],
      [{ difficulty: 5 }, "invalid"],
      [{ ...lvl({ ticks: -1 }) }, "invalid"],
      [{ ...lvl({ ticks: 1.5 }) }, "invalid"],
      [{ ...lvl({ ticks: 10_000_001 }) }, "invalid"],
      [{ ...lvl({ lvl: 61 }) }, "invalid"],
      [{ ...lvl({ done: 1 }) }, "invalid"],
      [{ levels: Array.from({ length: 61 }, () => run.levels[0]) }, "invalid"],
      [{ score: 2 ** 31 }, "invalid"],
      [{ front: { id: 1, power: 12 } }, "invalid"],
      [{ rear: { id: 256, power: 0 } }, "invalid"],
      [{ sidekicks: [0] }, "invalid"],
      [{ tickHz: 35 }, "invalid"],
      [{ tickHz: run.tickHz + 2e-6 }, "invalid"],
      [{ ended: "won" }, "invalid"],
      [{ name: "<<<___>>>" }, "invalid"],
      [{ name: "   " }, "invalid"],
      [{ name: 7 }, "invalid"],
      [{ hash: "abc" }, "invalid"],
      [{ mode: "arcade" }, "mode"],
      [{ mode: "twoPlayer" }, "mode"],
    ];
    for (const [over, reason] of cases) {
      const r = await submit(api, run, "Tester", over);
      expect(r.status, JSON.stringify(over)).toBe(400);
      expect(r.json.reason, JSON.stringify(over)).toBe(reason);
    }
    expect((await api.call("POST", "/api/scores", "{not json")).status).toBe(400);
    expect((await api.call("POST", "/api/scores", JSON.stringify({ pad: "x".repeat(33 * 1024) }))).status).toBe(413);
    expect((api.app.db.prepare("SELECT count(*) AS n FROM rejected").get() as { n: number }).n).toBe(before);
    // Unknown keys are ignored; the token is still good.
    const ok = await submit(api, run, "Tester", { extra: { anything: true } });
    expect(ok.status).toBe(200);
  });

  test("every reject reason is stored", async () => {
    const t0 = api.clock.t;
    const at = (lvl: number, ticks: number, score: number, done = true) => ({ lvl, ticks, score, done });
    // The cap after both reference levels: a second level ending just under it gains more than its own bound.
    const cap = (checkRun(MAX_SCORES, validRun(""), HOUR) as { cap: number }).cap;
    const cases: [string, Partial<ReturnType<typeof validRun>>][] = [
      ["path", { levels: [at(2, 12861, 21780)], score: 21780 }],
      ["ticks", { levels: [at(9, 100, 20000)], score: 20000 }],
      ["ticks", { levels: [at(9, 40000, 33750)], score: 33750 }],
      ["cap", { levels: [at(9, 9350, 5_000_000)], score: 5_000_000 }],
      ["level", { levels: [at(9, 9350, 33750), at(2, 12861, cap - 5)], score: cap - 5 }],
      ["rate", { levels: [at(9, 100, 119500, false)], score: 119500 }],
    ];
    for (const [reason, over] of cases) {
      const token = await playedToken();
      const run = validRun(token, over);
      expect(checkRun(MAX_SCORES, run, HOUR), reason).toMatchObject({ ok: false, reason });
      const r = await submit(api, run);
      expect(r.status, reason).toBe(422);
      expect(r.json, reason).toEqual({ ok: false, reason });
      const row = rejectedRow();
      expect(row, reason).toMatchObject({ reason, episode: 1, difficulty: 2, score: run.score, country: "ZZ" });
      expect(row.run_id, reason).toMatch(/^[0-9a-f]{32}$/);
      expect(String(row.detail).length, reason).toBeGreaterThan(0);
    }

    // wall: submitted straight after the token was issued.
    const quick = validRun(await newRun(api));
    expect((await submit(api, quick)).json).toEqual({ ok: false, reason: "wall" });
    expect(rejectedRow().reason).toBe("wall");

    // The token: tampered, expired, for another difficulty.
    const tok = await playedToken();
    const [part, sig] = tok.split(".");
    const tampered = `${part}.${sig.slice(0, -2)}${sig.at(-2) === "A" ? "B" : "A"}${sig.at(-1)}`;
    expect((await submit(api, validRun(tampered))).json).toEqual({ ok: false, reason: "token" });
    expect(rejectedRow()).toMatchObject({ reason: "token", run_id: null });

    const mismatch = await submit(api, validRun(tok, { difficulty: 1 }));
    expect(mismatch.json).toEqual({ ok: false, reason: "mismatch" });

    api.clock.t += 31 * DAY;
    expect((await submit(api, validRun(tok))).json).toEqual({ ok: false, reason: "expired" });
    expect(rejectedRow()).toMatchObject({ reason: "expired" });
    expect(api.clock.t).toBeGreaterThan(t0);
  });

  test("GET /api/scores: top 20, score desc, ties earlier first", async () => {
    const fresh = await startApi({ limits: { runs: 10000, scores: 10000 } });
    try {
      const tokens: string[] = [];
      for (let i = 0; i < 25; i++) tokens.push(await newRun(fresh));
      fresh.clock.t += HOUR;
      // Scores 36000 + 10 i, but entries 20 and 21 tie (the earlier submission ranks first).
      const scoreOf = (i: number) => 36000 + 10 * (i === 21 ? 20 : i);
      const ranks: number[] = [];
      for (let i = 0; i < 25; i++) {
        const s = scoreOf(i);
        const run = validRun(tokens[i], { levels: [{ lvl: 9, ticks: 9350, score: 33750, done: true }, { lvl: 2, ticks: 12861, score: s, done: true }], score: s });
        const r = await submit(fresh, run, `P${i}`);
        expect(r.status).toBe(200);
        ranks.push(r.json.rank);
        expect(r.json.total).toBe(i + 1);
        fresh.clock.t += 1000;
      }
      expect(ranks[0]).toBe(1);
      expect(ranks[20]).toBe(1);
      expect(ranks[21]).toBe(2); // ties with P20, submitted later
      // Another difficulty doesn't share the board.
      const hard = validRun(await newRun(fresh, { difficulty: 3 }), { difficulty: 3, levels: [{ lvl: 15, ticks: 0, score: 19500, done: false }], score: 19500 });
      fresh.clock.t += HOUR;
      const hr = await submit(fresh, hard, "Hard");
      expect(hr.json).toEqual({ ok: true, rank: 1, total: 1 });

      const list = await fresh.call("GET", "/api/scores?episode=1&difficulty=2");
      expect(list.status).toBe(200);
      expect(list.json.episode).toBe(1);
      expect(list.json.difficulty).toBe(2);
      expect(list.json.scores).toHaveLength(20);
      const names = list.json.scores.map((s: { name: string }) => s.name);
      expect(names.slice(0, 3)).toEqual(["P24", "P23", "P22"]);
      expect(names.indexOf("P20")).toBe(names.indexOf("P21") - 1);
      expect(list.json.scores[0]).toEqual({ rank: 1, name: "P24", score: 36240, difficulty: 2, levels: 2, date: "2026-11-18" });
      expect(list.json.scores.map((s: { rank: number }) => s.rank)).toEqual(Array.from({ length: 20 }, (_, i) => i + 1));

      const all = await fresh.call("GET", "/api/scores?episode=1");
      expect(all.json.difficulty).toBeNull();
      expect(all.json.scores).toHaveLength(20);
      expect(all.json.scores.some((s: { name: string }) => s.name === "Hard")).toBe(false); // 19500 is below the 20th
      expect((await fresh.call("GET", "/api/scores?episode=2")).json.scores).toEqual([]);
      expect((await fresh.call("GET", "/api/scores?episode=9")).status).toBe(400);
      expect((await fresh.call("GET", "/api/scores?episode=1&difficulty=5")).status).toBe(400);
    } finally {
      await fresh.close();
    }
  });

  test("GET /api/health", async () => {
    expect((await api.call("GET", "/api/health")).json).toEqual({ ok: true, db: true });
    expect((await api.call("GET", "/api/nope")).status).toBe(404);
  });
});

describe("rate limits", () => {
  let api: Api;
  beforeAll(async () => {
    api = await startApi();
  });
  afterAll(() => api.close());

  test("runs: 30 an hour per IP hash, with Retry-After", async () => {
    for (let i = 0; i < 30; i++) await newRun(api, {}, from("198.51.100.1"));
    const r = await api.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "t" }, from("198.51.100.1"));
    expect(r.status).toBe(429);
    expect(Number(r.headers.get("retry-after"))).toBeGreaterThan(0);
    expect(Number(r.headers.get("retry-after"))).toBeLessThanOrEqual(3600);
    // Another address isn't limited.
    await newRun(api, {}, from("198.51.100.2"));
    // An hour later the window has reset.
    api.clock.t += HOUR;
    await newRun(api, {}, from("198.51.100.1"));
  });

  test("runs: 30 an hour per player id, across addresses", async () => {
    const playerId = crypto.randomUUID();
    for (let i = 0; i < 30; i++) await newRun(api, { playerId }, from(`198.51.100.${10 + i}`));
    const r = await api.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "t", playerId }, from("198.51.100.99"));
    expect(r.status).toBe(429);
    await newRun(api, { playerId: crypto.randomUUID() }, from("198.51.100.99"));
  });

  test("scores: 10 an hour per IP hash (counted before validation)", async () => {
    for (let i = 0; i < 10; i++) expect((await api.call("POST", "/api/scores", {}, from("198.51.100.200"))).status).toBe(400);
    expect((await api.call("POST", "/api/scores", {}, from("198.51.100.200"))).status).toBe(429);
    expect((await api.call("POST", "/api/scores", {}, from("198.51.100.201"))).status).toBe(400);
  });

  test("scores: per player id, before the token is consumed", async () => {
    const limited = await startApi({ limits: { scores: 2 } });
    try {
      const playerId = crypto.randomUUID();
      const tokens = [await newRun(limited, { playerId }), await newRun(limited, { playerId }), await newRun(limited, { playerId })];
      limited.clock.t += HOUR;
      expect((await submit(limited, validRun(tokens[0]), "A", {}, from("192.0.2.1"))).status).toBe(200);
      expect((await submit(limited, validRun(tokens[1]), "A", {}, from("192.0.2.2"))).status).toBe(200);
      const r = await submit(limited, validRun(tokens[2]), "A", {}, from("192.0.2.3"));
      expect(r.status).toBe(429);
      expect(limited.app.db.prepare("SELECT count(*) AS n FROM runs WHERE used_at IS NULL").get()).toEqual({ n: 1 });
    } finally {
      await limited.close();
    }
  });

  test("an untrusted peer's X-Forwarded-For is ignored", async () => {
    const strict = await startApi({ trustProxy: [] });
    try {
      for (let i = 0; i < 30; i++) await newRun(strict, {}, from(`198.51.100.${i}`));
      expect((await strict.call("POST", "/api/runs", { episode: 1, difficulty: 2, mode: "story", build: "t" }, from("198.51.100.250"))).status).toBe(429);
    } finally {
      await strict.close();
    }
  });
});
