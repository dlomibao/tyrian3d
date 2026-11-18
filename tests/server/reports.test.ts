// Level reports (POST /api/levels/report) and the stats summary.
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { loadGeo } from "../../server/scores/lib/geo.mjs";
import { issueToken } from "../../server/scores/lib/token.mjs";
import { DAY, GEO_FIXTURE, SECRET, from, newRun, report, startApi, type Api } from "./helpers";

const send = (api: Api, body: unknown, headers: Record<string, string> = {}) => api.call("POST", "/api/levels/report", body, headers);
type Row = Record<string, unknown>;

describe("level reports", () => {
  let api: Api;
  const player = crypto.randomUUID();
  let token: string;
  beforeAll(async () => {
    api = await startApi({ limits: { runs: 10000, reports: 10000 } });
    token = await newRun(api, { playerId: player });
  });
  afterAll(() => api.close());
  const last = () => api.app.db.prepare("SELECT * FROM levels ORDER BY id DESC LIMIT 1").get() as Row;

  test("accepted as text/plain (sendBeacon), stored flat", async () => {
    const r = await send(api, report(token, player, { shop: [{ kind: "buy", slot: "front", id: 3, power: 1, price: 500 }] }), { "content-type": "text/plain;charset=UTF-8" });
    expect(r.status).toBe(204);
    const row = last();
    expect(row).toMatchObject({
      player_id: player, country: "ZZ", build: "test", tainted: 0, episode: 1, difficulty: 2, difficulty_now: 2, mode: "story",
      lvl: 9, name: "TYRIAN", section: 3, idx: 0, prev: null, via: "start", ship: 1, front_id: 1, front_power: 1,
      sidekick_l: 0, sidekick_r: 0, armor: 10, credits: 10000, result: "finished", ticks: 9350, score_gained: 14250,
      bosses_killed: 1, specials: null, deaths: null, month: "2026-11", day: "2026-11-18",
    });
    expect(api.app.db.prepare("SELECT kind, slot, item_id, power, price FROM shop_trades WHERE level_id = ?").all(row.id as number)).toEqual([
      { kind: "buy", slot: "front", item_id: 3, power: 1, price: 500 },
    ]);
    expect(api.app.db.prepare("SELECT report_count FROM runs WHERE player_id = ?").get(player)).toEqual({ report_count: 1 });
  });

  test("fields are clamped and cut", async () => {
    const deaths = Array.from({ length: 25 }, (_, i) => ({ tick: i, x: 9999, y: -5 }));
    const shop = Array.from({ length: 150 }, () => ({ kind: "upgrade" as const, slot: "rear" as const, id: 999, power: 40, price: -3 }));
    const body = report(token, player, {
      level: { name: "éVIL\u0000 LEVEL NAME THAT GOES ON AND ON AND ON", section: 9999, index: -4 },
      loadout: { credits: 1e15, armor: -5, ship: 3.7 },
      outcome: { result: "died", deaths, bossesKilled: "lots" as unknown as number, shotsFired: 1e12, scoreGained: -1e12 },
      shop,
    });
    expect((await send(api, body)).status).toBe(204);
    const row = last();
    expect(row).toMatchObject({ section: 255, idx: 0, credits: 2 ** 31 - 1, armor: 0, ship: 3, bosses_killed: null, shots_fired: 1e9, score_gained: -(2 ** 31 - 1) });
    expect(row.name).toBe("VIL LEVEL NAME THAT GOES ON AND");
    const d = JSON.parse(row.deaths as string);
    expect(d).toHaveLength(20);
    expect(d[0]).toEqual([0, 511, 0]);
    const trades = api.app.db.prepare("SELECT item_id, power, price FROM shop_trades WHERE level_id = ?").all(row.id as number);
    expect(trades).toHaveLength(100);
    expect(trades[0]).toEqual({ item_id: 255, power: 11, price: 0 });
  });

  test("tainted runs are recorded, flagged", async () => {
    expect((await send(api, report(token, player, { tainted: true }))).status).toBe(204);
    expect(last().tainted).toBe(1);
    expect(api.app.db.prepare("SELECT count(*) AS n FROM shop_trades WHERE tainted = 1").get()).toEqual({ n: 0 });
  });

  test.each([
    ["playerId", { playerId: "1234" }],
    ["playerId v1", { playerId: "6ba7b810-9dad-11d1-80b4-00c04fd430c8" }],
    ["version", { v: 2 }],
    ["episode", { run: { episode: 7 } }],
    ["mode", { run: { mode: "coop" } }],
    ["via", { level: { via: "teleport" } }],
    ["result", { outcome: { result: "won" } }],
    ["sidekicks", { loadout: { sidekicks: [1] } }],
    ["a required count", { outcome: { ticks: "many" } }],
  ])("rejects a bad %s (400)", async (_, over: Record<string, unknown>) => {
    const base = report(token, player) as unknown as Record<string, Record<string, unknown>>;
    const body: Record<string, unknown> = { ...base };
    for (const [k, v] of Object.entries(over)) body[k] = typeof v === "object" && v !== null && !Array.isArray(v) ? { ...base[k], ...v } : v;
    const r = await send(api, body);
    expect(r.status).toBe(400);
  });

  test("needs a signed token for the same run", async () => {
    const [part] = token.split(".");
    expect((await send(api, report(`${part}.AAAA`, player))).status).toBe(403);
    expect((await send(api, report(token, player, { run: { difficulty: 4 } }))).status).toBe(403);
    // Signed but never issued here.
    const stray = issueToken(SECRET, { ep: 1, diff: 2, mode: "story" }, api.clock.t).token;
    expect((await send(api, report(stray, player))).json).toEqual({ ok: false, reason: "unknown-run" });
  });

  test("at most 200 reports per run token", async () => {
    const t = await newRun(api);
    api.app.db.prepare("UPDATE runs SET report_count = 199 WHERE report_count = 0").run();
    expect((await send(api, report(t, player))).status).toBe(204);
    const r = await send(api, report(t, player));
    expect(r.status).toBe(429);
    expect(r.json.reason).toBe("cap");
  });

  test("tokens are accepted up to 60 days old", async () => {
    const t = await newRun(api);
    api.clock.t += 59 * DAY;
    expect((await send(api, report(t, player))).status).toBe(204);
    api.clock.t += 2 * DAY;
    expect((await send(api, report(t, player))).json).toEqual({ ok: false, reason: "expired" });
  });

  test("per player id rate limit", async () => {
    const limited = await startApi({ limits: { reports: 3 } });
    try {
      const p = crypto.randomUUID();
      const t = await newRun(limited, { playerId: p });
      for (let i = 0; i < 3; i++) expect((await send(limited, report(t, p), from(`198.51.100.${i}`))).status).toBe(204);
      expect((await send(limited, report(t, p), from("198.51.100.9"))).status).toBe(429);
      expect((await send(limited, report(t, crypto.randomUUID()), from("198.51.100.9"))).status).toBe(204);
    } finally {
      await limited.close();
    }
  });
});

describe("GET /api/stats/summary", () => {
  let api: Api;
  const A = crypto.randomUUID();
  const B = crypto.randomUUID();
  const day1 = Date.UTC(2026, 10, 1, 10);
  const day2 = Date.UTC(2026, 10, 2, 10);
  beforeAll(async () => {
    api = await startApi({ limits: { runs: 10000, reports: 10000, get: 10000 } }, day1);
    loadGeo(api.app.db, readFileSync(GEO_FIXTURE, "utf8").split("\n"));
    // Day 1: A plays TYRIAN, then dies in ASTEROID2.
    const a1 = await newRun(api, { playerId: A }, from("192.0.2.10"));
    await send(api, report(a1, A, { shop: [{ kind: "buy", slot: "front", id: 3, power: 1, price: 500 }] }), from("192.0.2.10"));
    await send(api, report(a1, A, { level: { lvl: 2, index: 1, prev: 9, via: "story" }, outcome: { result: "died", scoreGained: 300, deaths: [{ tick: 100, x: 40, y: 100 }] } }), from("192.0.2.10"));
    // Day 2: A again; B dies in TYRIAN, then cheats through it.
    api.clock.t = day2;
    const a2 = await newRun(api, { playerId: A }, from("192.0.2.10"));
    await send(api, report(a2, A, { outcome: { scoreGained: 20000 } }), from("192.0.2.10"));
    const b1 = await newRun(api, { playerId: B }, from("2001:db8::1"));
    await send(api, report(b1, B, { loadout: { front: { id: 7, power: 2 } }, outcome: { result: "died", deaths: [{ tick: 50, x: 41, y: 101 }] } }), from("2001:db8::1"));
    await send(api, report(b1, B, { tainted: true, level: { lvl: 2, index: 1, prev: 9, via: "story" }, shop: [{ kind: "buy", slot: "front", id: 3, power: 1, price: 500 }] }), from("2001:db8::1"));
  });
  afterAll(() => api.close());

  test("shape and aggregates", async () => {
    const r = await api.call("GET", "/api/stats/summary");
    expect(r.status).toBe(200);
    const s = r.json;
    expect(s.reports).toEqual({ total: 5, tainted: 1 });
    expect(s.runs).toEqual({ total: 3, submitted: 0 });
    // Paths: start -> 9 three times (the tainted 9 -> 2 isn't counted).
    expect(s.paths["1"]).toEqual([
      { from: null, to: 9, n: 3 },
      { from: 9, to: 2, n: 1 },
    ]);
    expect(s.outcomes["1"]["9"]["2"]).toEqual({ finished: 2, died: 1, quit: 0 });
    expect(s.outcomes["1"]["2"]["2"]).toEqual({ finished: 0, died: 1, quit: 0 });
    expect(s.deathBucketPx).toBe(16);
    expect(s.deaths["1"]["9"]).toEqual([[2, 6, 1]]);
    expect(s.deaths["1"]["2"]).toEqual([[2, 6, 1]]);
    expect(s.weapons["1"]["9"]).toEqual({ 1: 2, 7: 1 });
    expect(s.ships["1"]["9"]).toEqual({ 1: 3 });
    expect(s.scoreGained["1"]["9"]).toEqual({ n: 2, p25: 14250, p50: 14250, p75: 14250, p90: 14250 });
    expect(s.shop).toEqual({ buy: { front: { 3: 1 } } });
    expect(s.countries.runs).toEqual({ AU: 2, NZ: 1 });
    expect(s.countries.reports).toEqual({ AU: 3, NZ: 2 });
    expect(s.countries.reportsByMonth).toEqual({ "2026-11": { AU: 3, NZ: 2 } });
    expect(s.countries.runsByMonth).toEqual({ "2026-11": { AU: 2, NZ: 1 } });
    // Players: A new on day 1 and returning on day 2; B new on day 2.
    expect(s.players.total).toBe(2);
    expect(s.players.perDay).toEqual([
      { day: "2026-11-01", players: 1, new: 1, returning: 0 },
      { day: "2026-11-02", players: 2, new: 1, returning: 1 },
    ]);
    expect(s.players.perMonth).toEqual([{ month: "2026-11", players: 2, new: 2, returning: 0 }]);
    expect(s.players.runsPerPlayer).toEqual({ 1: 1, 2: 1 });
    expect(s.players.daysPerPlayer).toEqual({ 1: 1, 2: 1 });
    // Funnel: A reached the 2nd level of episode 1, B (untainted) only the 1st.
    expect(s.funnel["1"]).toEqual({ 1: 2, 2: 1 });
  });

  test("cached for 10 minutes", async () => {
    const first = (await api.call("GET", "/api/stats/summary")).json;
    const t = await newRun(api, { playerId: A });
    await send(api, report(t, A));
    expect((await api.call("GET", "/api/stats/summary")).json).toEqual(first);
    api.clock.t += 11 * 60 * 1000;
    const later = (await api.call("GET", "/api/stats/summary")).json;
    expect(later.reports.total).toBe(first.reports.total + 1);
  });
});
