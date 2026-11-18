// The stats page's derivations (src/stats/model.ts) over a real summary from the scores service,
// and its names from the game data (src/stats/names.ts).
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { loadGeo } from "../../server/scores/lib/geo.mjs";
import { GEO_FIXTURE, from, newRun, report, startApi, type Api } from "../server/helpers";
import {
  branches,
  dailySeries,
  deathMaps,
  folded,
  funnel,
  headline,
  isEmpty,
  levelRows,
  overall,
  purchases,
  ranked,
  tradeCount,
} from "../../src/stats/model";
import { gameNames } from "../../src/stats/names";
import { asSummary, type StatsSummary } from "../../src/stats/summary";
import { hasData, readData } from "../data/dataDir";

const send = (api: Api, body: unknown, headers: Record<string, string> = {}) => api.call("POST", "/api/levels/report", body, headers);

describe("stats page model", () => {
  let api: Api;
  let s: StatsSummary;
  let empty: StatsSummary;
  const A = crypto.randomUUID();
  const B = crypto.randomUUID();
  const day1 = Date.UTC(2026, 10, 1, 10);
  const day3 = Date.UTC(2026, 10, 3, 10);
  beforeAll(async () => {
    api = await startApi({ limits: { runs: 10000, reports: 10000, get: 10000 }, summaryTtlMs: 0 }, day1);
    empty = asSummary((await api.call("GET", "/api/stats/summary")).json)!;
    loadGeo(api.app.db, readFileSync(GEO_FIXTURE, "utf8").split("\n"));
    // Day 1: A clears TYRIAN, then two levels branch from it (ASTEROID1, ASTEROID2).
    const a1 = await newRun(api, { playerId: A }, from("192.0.2.10"));
    await send(api, report(a1, A, { shop: [{ kind: "buy", slot: "front", id: 3, power: 1, price: 500 }, { kind: "upgrade", slot: "front", id: 3, power: 2, price: 500 }] }), from("192.0.2.10"));
    await send(api, report(a1, A, { level: { lvl: 2, index: 1, prev: 9, via: "branch" }, outcome: { result: "died", deaths: [{ tick: 100, x: 40, y: 100 }] } }), from("192.0.2.10"));
    // Day 3: A (AU) again, returning, going the other way; B (US) dies twice in TYRIAN.
    api.clock.t = day3;
    const a2 = await newRun(api, { playerId: A }, from("192.0.2.10"));
    await send(api, report(a2, A, { loadout: { ship: 3 } }), from("192.0.2.10"));
    await send(api, report(a2, A, { level: { lvl: 1, index: 1, prev: 9, via: "branch" } }), from("192.0.2.10"));
    const b1 = await newRun(api, { playerId: B }, from("198.51.100.5"));
    for (const x of [41, 200]) await send(api, report(b1, B, { outcome: { result: "died", deaths: [{ tick: 50, x, y: 101 }] } }), from("198.51.100.5"));
    s = asSummary((await api.call("GET", "/api/stats/summary")).json)!;
  });
  afterAll(() => api.close());

  test("an empty summary is empty, and every view of it is empty", () => {
    expect(empty).not.toBeNull();
    expect(isEmpty(empty)).toBe(true);
    expect(headline(empty)).toEqual({ players: 0, returning: 0, runs: 0, reports: 0, submitted: 0, cleared: 0, lost: 0, quit: 0, countries: 0 });
    expect(levelRows(empty, 1, [])).toEqual([]);
    expect(funnel(empty, 1)).toEqual([]);
    expect(deathMaps(empty)).toEqual([]);
    expect(dailySeries(empty.players.perDay, "2026-11-18")).toEqual([]);
    expect(purchases(empty)).toEqual([]);
  });

  test("not a summary", () => {
    expect(asSummary(null)).toBeNull();
    expect(asSummary("<!doctype html>")).toBeNull();
    expect(asSummary({ ok: false })).toBeNull();
  });

  test("headline totals", () => {
    expect(isEmpty(s)).toBe(false);
    expect(headline(s)).toEqual({ players: 2, returning: 1, runs: 3, reports: 6, submitted: 0, cleared: 3, lost: 3, quit: 0, countries: 2 });
  });

  test("levels in script order, with outcomes, clear rates and deaths", () => {
    const rows = levelRows(s, 1, [9, 1, 2]);
    expect(rows.map((r) => [r.lvl, r.attempts, r.outcome.died])).toEqual([[9, 4, 2], [1, 1, 0], [2, 1, 1]]);
    expect(rows[0].clearRate).toBe(0.5);
    expect(rows[0].deaths).toBe(2);
    expect(rows[0].score?.n).toBe(2);
    expect(levelRows(s, 1, [9, 1, 2], 3)).toEqual([]); // nothing on Hard
  });

  test("funnel, branches and death maps", () => {
    expect(funnel(s, 1)).toEqual([{ k: 1, players: 2, share: 1 }, { k: 2, players: 1, share: 0.5 }]);
    expect(branches(s, 1)).toEqual([{ from: 9, total: 2, to: [{ lvl: 1, n: 1, share: 0.5 }, { lvl: 2, n: 1, share: 0.5 }] }]);
    const maps = deathMaps(s, 1);
    expect(maps.map((m) => [m.lvl, m.total])).toEqual([[9, 2], [2, 1]]);
  });

  test("ships, weapons, shop", () => {
    expect(ranked(overall(s.ships))).toEqual([{ id: "1", n: 5, share: 5 / 6 }, { id: "3", n: 1, share: 1 / 6 }]);
    expect(purchases(s)).toEqual([{ slot: "front", id: 3, n: 1 }]);
    expect(tradeCount(s, "upgrade")).toBe(1);
  });

  test("players per day are filled to today; distributions fold", () => {
    const days = dailySeries(s.players.perDay, "2026-11-04");
    expect(days.map((d) => [d.day, d.new, d.returning])).toEqual([["2026-11-01", 1, 0], ["2026-11-02", 0, 0], ["2026-11-03", 1, 1], ["2026-11-04", 0, 0]]);
    expect(folded({ 1: 3, 2: 1, 7: 2 }, 5)).toEqual([{ label: "1", n: 3 }, { label: "2", n: 1 }, { label: "3", n: 0 }, { label: "4", n: 0 }, { label: "5+", n: 2 }]);
  });
});

describe("stats page names", () => {
  test("fallbacks without the data", () => {
    const n = gameNames(null, []);
    expect(n.fromData).toBe(false);
    expect([n.episode(2), n.difficulty(8), n.level(1, 9), n.item("ship", 3), n.item("weapon", 0)]).toEqual(["Episode 2", "Lord of Game", "Level 9", "Ship 3", "None"]);
  });

  test.skipIf(!hasData("tyrian.hdt", "levels1.dat", "levels2.dat", "levels3.dat", "levels4.dat"))("from the game data, as the game labels them", () => {
    const n = gameNames(readData("tyrian.hdt"), [1, 2, 3, 4].map((ep) => readData(`levels${ep}.dat`)));
    expect(n.fromData).toBe(true);
    expect([n.episode(1), n.episode(4)]).toEqual(["Escape", "An End to Fate"]);
    expect([1, 2, 3, 4, 6, 8].map((d) => n.difficulty(d))).toEqual(["Easy", "Normal", "Hard", "Impossible", "Suicide", "Lord of Game"]);
    // Two levels named TYRIAN (9, and its hard twin 15): the later one is marked.
    expect([n.level(1, 9), n.level(1, 15), n.level(1, 12), n.level(1, 8), n.level(4, 4)]).toEqual(["TYRIAN", "TYRIAN (2)", "SAVARA", "SAVARA (2)", "SURFACE"]);
    expect(n.sharedNames(1)).toBe(true);
    expect(n.levelOrder(1).slice(0, 3)).toEqual([9, 15, 1]);
    expect([n.item("ship", 1), n.item("weapon", 1), n.item("weapon", 39)]).toEqual(["USP Talon Light Fighter", "Pulse-Cannon", "Atomic RailGun"]);
  });
});
