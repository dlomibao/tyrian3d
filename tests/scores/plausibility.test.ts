// The server's plausibility checks (server/scores/lib/plausibility.mjs) against the committed level
// data (server/scores/maxScores.json): path, tick floor and ceiling, wall time, the cap, a level's
// own gain and its rate, and the run hash the game and the server both compute.
import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { checkRun, difficultyForScore, levelCap, randomSpawnBound } from "../../server/scores/lib/plausibility.mjs";
import { canonicalRun, runHash } from "../../server/scores/lib/runHash.mjs";
import { CLASSIC_TICK_HZ } from "../../src/core/timing";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const data: any = JSON.parse(readFileSync("server/scores/maxScores.json", "utf8"));

type L = { lvl: number; ticks: number; score: number; done: boolean };
const run = (levels: L[], extra: Partial<{ difficulty: number; ended: string; score: number; episode: number }> = {}) => ({
  episode: 1,
  difficulty: 2,
  ended: "quit",
  levels,
  score: levels.at(-1)?.score ?? 19500,
  ...extra,
});
/** Enough wall time for the ticks. */
const wall = (levels: L[]) => (levels.reduce((a, l) => a + l.ticks, 0) / data.tickHz) * 1000;
/** The test bot's real run (tests/tools/maxScores.test.ts): TYRIAN then ASTEROID2. */
const BOT: L[] = [
  { lvl: 9, ticks: 9350, score: 33750, done: true },
  { lvl: 2, ticks: 12861, score: 36030, done: true },
];

describe("plausibility", () => {
  test("the game's tick rate is the data's", () => {
    expect(data.tickHz).toBe(CLASSIC_TICK_HZ);
  });

  test("a played run passes", () => {
    expect(checkRun(data, run(BOT), wall(BOT))).toMatchObject({ ok: true });
    // D264: an empty one (quit from the first item screen) is ranked, bounded by the start total
    expect(checkRun(data, run([], { score: 19500 }), 1000)).toMatchObject({ ok: true });
    expect(checkRun(data, run([], { score: 19501 }), 1000)).toMatchObject({ ok: false, reason: "cap" });
    // and it can't claim the episode's end
    expect(checkRun(data, run([], { score: 19500, ended: "episode" }), 1000)).toMatchObject({ ok: false, reason: "path" });
  });

  describe("path", () => {
    test("the episode's first level, by difficulty class", () => {
      const hard = [{ lvl: 15, ticks: 9000, score: 30000, done: true }];
      expect(checkRun(data, run(hard, { difficulty: 3 }), wall(hard))).toMatchObject({ ok: true });
      // Normal starts on lvl 9, not 15 (`]h[` in section 3)
      expect(checkRun(data, run(hard), wall(hard))).toMatchObject({ ok: false, reason: "path" });
    });
    test("item-screen branches: after TYRIAN, ASTEROID1 or ASTEROID2", () => {
      for (const lvl of [1, 2]) {
        const levels = [BOT[0], { lvl, ticks: 9000, score: 40000, done: true }];
        expect(checkRun(data, run(levels), wall(levels))).toMatchObject({ ok: true });
      }
    });
    test("a warp: TYRIAN's warp pick-ups lead to HOLES (section 27) and SOH JIN (section 30)", () => {
      const levels = [BOT[0], { lvl: 11, ticks: 4000, score: 40000, done: true }];
      expect(checkRun(data, run(levels), wall(levels))).toMatchObject({ ok: true });
    });
    test("a level that can't follow", () => {
      const levels = [BOT[0], { lvl: 16, ticks: 4000, score: 40000, done: true }];
      expect(checkRun(data, run(levels), wall(levels))).toMatchObject({ ok: false, reason: "path" });
    });
    test("an unfinished level only last; the episode's end only after an ending level", () => {
      const levels = [{ ...BOT[0], done: false }, BOT[1]];
      expect(checkRun(data, run(levels), wall(levels))).toMatchObject({ ok: false, reason: "path" });
      expect(checkRun(data, run(BOT, { ended: "episode" }), wall(BOT))).toMatchObject({ ok: false, reason: "path" });
    });
  });

  describe("ticks", () => {
    test("a finished level under its floor fails; at the floor less 3% passes", () => {
      const min = data.episodes[1].levels[9].minTicks;
      expect(min).toBe(1800);
      const fast = [{ lvl: 9, ticks: 1700, score: 30000, done: true }];
      expect(checkRun(data, run(fast), wall(fast))).toMatchObject({ ok: false, reason: "ticks" });
      const ok = [{ lvl: 9, ticks: 1746, score: 30000, done: true }];
      expect(checkRun(data, run(ok), wall(ok))).toMatchObject({ ok: true });
    });
    test("a quit level has no floor", () => {
      const quit = [{ lvl: 9, ticks: 200, score: 20000, done: false }];
      expect(checkRun(data, run(quit), wall(quit))).toMatchObject({ ok: true });
    });
    test("past a ceiling (TYRIAN can't stall: 37450)", () => {
      const slow = [{ lvl: 9, ticks: 40000, score: 30000, done: true }];
      expect(checkRun(data, run(slow), wall(slow))).toMatchObject({ ok: false, reason: "ticks" });
    });
  });

  test("wall: the ticks must fit the time since the token", () => {
    // 22211 ticks are ~639 s: not in 60 s of wall time (+60 s slack)
    expect(checkRun(data, run(BOT), 60_000)).toMatchObject({ ok: false, reason: "wall" });
    expect(checkRun(data, run(BOT), 600_000)).toMatchObject({ ok: true });
  });

  test("cap: the score over the path's bound", () => {
    const rich = [{ ...BOT[0], score: 5_000_000 }];
    expect(checkRun(data, run(rich), wall(rich))).toMatchObject({ ok: false, reason: "cap" });
    expect(checkRun(data, run(BOT, { score: 9_999_999 }), wall(BOT))).toMatchObject({ ok: false, reason: "cap" });
  });

  test("level: one level can't use earlier levels' headroom", () => {
    // ASTEROID1 (lvl 1) can add at most ~6.5k plus its random spawns; TYRIAN's unused bound doesn't carry over
    const levels = [{ ...BOT[0], score: 20000 }, { lvl: 1, ticks: 4000, score: 300000, done: true }];
    const cap1 = levelCap(data.episodes[1].levels[1], 2, 4000);
    expect(cap1).toBeLessThan(20000);
    expect(checkRun(data, run(levels), wall(levels))).toMatchObject({ ok: false, reason: "level" });
  });

  test("rate: a quit level's gain per tick", () => {
    // TYRIAN's bound at its floor is ~514k over 1800 ticks: x1.25, ~357 per tick
    const quick = [{ lvl: 9, ticks: 100, score: 19500 + 200000, done: false }];
    expect(checkRun(data, run(quick), wall(quick))).toMatchObject({ ok: false, reason: "rate" });
    const fine = [{ lvl: 9, ticks: 100, score: 19500 + 20000, done: false }];
    expect(checkRun(data, run(fine), wall(fine))).toMatchObject({ ok: true });
  });

  test("helpers: adjust_difficulty's thresholds and the random-spawn bound", () => {
    expect(difficultyForScore(30000, 2)).toBe(1); // 24000 adjusted: Easy
    expect(difficultyForScore(100000, 2)).toBe(3); // 80000: Hard
    expect(difficultyForScore(10_000_000, 8)).toBe(9);
    expect(randomSpawnBound(0, 0.03)).toBe(0);
    expect(randomSpawnBound(10000, 0.03)).toBe(Math.ceil(300 + 6 * Math.sqrt(291) + 6));
    expect(randomSpawnBound(10, 0.98)).toBe(10); // never more than one a tick
  });

  test("bad episode or difficulty", () => {
    expect(checkRun(data, run(BOT, { episode: 9 }), wall(BOT))).toMatchObject({ ok: false, reason: "episode" });
    expect(checkRun(data, run(BOT, { difficulty: 5 }), wall(BOT))).toMatchObject({ ok: false, reason: "difficulty" });
  });
});

describe("run hash", () => {
  const r = {
    token: "t.x",
    episode: 1,
    difficulty: 2,
    mode: "story",
    tickHz: CLASSIC_TICK_HZ,
    ended: "quit" as const,
    ship: 1,
    front: { id: 1, power: 2 },
    rear: { id: 0, power: 1 },
    shield: 1,
    generator: 1,
    sidekicks: [0, 0],
    levels: BOT,
    score: 36030,
  };
  test("same data, same hash; any change, another", async () => {
    const h = await runHash(r);
    expect(h).toMatch(/^[0-9a-f]{64}$/);
    expect(await runHash(JSON.parse(JSON.stringify(r)))).toBe(h);
    expect(await runHash({ ...r, score: 36031 })).not.toBe(h);
    expect(await runHash({ ...r, levels: [BOT[0], { ...BOT[1], ticks: 12862 }] })).not.toBe(h);
    expect(await runHash({ ...r, token: "t.y" })).not.toBe(h);
    // key order doesn't matter: the canonical form is an array
    const reordered = Object.fromEntries(Object.entries(r).reverse()) as typeof r;
    expect(canonicalRun(reordered)).toBe(canonicalRun(r));
  });
});
