// The shared high-score list's level data (tools/maxScores/maxScores.ts):
//
//   MAX_SCORES_OUT=server/scores/maxScores.json npm run max-scores     (re-generate the committed file)
//
// Without MAX_SCORES_OUT it checks the committed file against the data, two levels' bounds by hand,
// and the bounds against levels the test bot really plays.
import { describe, expect, test } from "vitest";
import { readFileSync, writeFileSync } from "node:fs";
import { parseEpisodeScript, parseLevelFile } from "../../src/data";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { JE_totalScore } from "../../src/sim/mainint";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { episodeConstants, levelBounds, maxScores, scaledValue, weaponValue } from "../../tools/maxScores/maxScores";
import { checkRun, levelCap } from "../../server/scores/lib/plausibility.mjs";
import { hasData, readData } from "../data/dataDir";
import { botTick } from "../sim/bot";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const OUT = process.env.MAX_SCORES_OUT ?? "";
const COMMITTED = "server/scores/maxScores.json";
const DATA = hasData("tyrian1.lvl", "levels1.dat", "tyrian.hdt");

describe("max-score helpers", () => {
  test("JE_makeEnemy's value scaling", () => {
    expect(scaledValue(100, 2)).toBe(100);
    expect(scaledValue(100, 3)).toBe(112); // x1.125, truncated
    expect(scaledValue(100, 9)).toBe(800);
    expect(scaledValue(2000, 10)).toBe(10000); // capped
    expect(scaledValue(1, 9)).toBe(1); // a data cube stays a data cube
    expect(scaledValue(30000, 9)).toBe(30000); // pick-up codes aren't scaled
  });
  test("JE_getValue of a weapon", () => {
    // base + base x (1 + 3 + 6 + ...): power 3 is base x (1 + 1 + 3)
    expect(weaponValue(100, 1)).toBe(100);
    expect(weaponValue(100, 3)).toBe(500);
    expect(weaponValue(100, 11)).toBe(100 * 221);
  });
});

describe.skipIf(!DATA)("max scores from the game data", { timeout: 60000 }, () => {
  test.runIf(OUT)("write maxScores.json", () => {
    writeFileSync(OUT, JSON.stringify(maxScores(files), null, 1) + "\n");
  });

  test("the committed file matches the data", () => {
    const committed = JSON.parse(readFileSync(COMMITTED, "utf8"));
    expect(committed).toEqual(JSON.parse(JSON.stringify(maxScores(files))));
  });

  // Episode 1, MINES (lvl 7): no power-ups, drops, loops or launchers, so its static bound at Normal
  // is the plain sum of its event spawns' values: 117 x 50 (type 554) + 7 x 500 (pick-up 396) +
  // 3 x 1000 (397) + 13 x 200 (567) + 38 x 50 (564, armor 255: unkillable, but counted) + 17 x 75
  // (555) + 3 x 250 (395) + 6 x 50 (565) + 3 x 100 (394) = 19475. At Lord of Game (d 8) every
  // value is x4: 77900. Its random spawns (levelEnemy 1,2,3,4,5,10,11; chance 3%) are worth at most
  // 2250 each. Ticks: its end event is at curLoc 1300 and nothing scrolls faster than 1 per tick,
  // so 1300 at least; it can't stall, so at most 1300 x 3 (event 3's slow scroll) x 1.5 + 1000.
  test("MINES (episode 1): the event spawns' values", () => {
    const script = parseEpisodeScript(readData("levels1.dat"));
    const c = episodeConstants(files, 1, script);
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[7 - 1];
    const b = levelBounds(level, 7, { name: "MINES", sections: [13], bonus: false, galaga: false, engage: false }, g.res.enemyDat, c);
    const byType = new Map<number, { n: number; value: number }>();
    for (const e of b.explain) byType.set(e.type, { n: (byType.get(e.type)?.n ?? 0) + 1, value: e.value });
    expect(byType.get(554)).toEqual({ n: 117, value: 50 });
    expect(byType.get(396)).toEqual({ n: 7, value: 500 });
    expect(byType.get(397)).toEqual({ n: 3, value: 1000 });
    expect(b.static[2]).toBe(19475);
    expect(b.static[8]).toBe(77900);
    expect(b.perTick[2]).toBeLessThan(10); // the random-spawn block's launchers only
    expect(b.random).toEqual({ p: 0.03, value: expect.arrayContaining([2250]) });
    expect(b.minTicks).toBe(1300);
    expect(b.maxTicks).toBe(12550);
  });

  // Episode 1, TYRIAN (lvl 9, the first level): 473 event spawns worth 29331 at Normal (the
  // biggest: 3 x 1000 for types 72 and 79, 48 x 25 for type 4), plus power-up pick-ups, which may
  // add the most two weapon ports can gain in value (powerUpSlack: 2 x (221 - 1) x 1101 = 484440,
  // the costliest weapon from power 1 to 11): 513771.
  test("TYRIAN (episode 1): spawns plus the power-up slack", () => {
    const script = parseEpisodeScript(readData("levels1.dat"));
    const c = episodeConstants(files, 1, script);
    expect(c.powerUpSlack).toBe(484440);
    expect(c.startTotal).toBe(19500); // 10000 credits + the starting ship and gear
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[9 - 1];
    const b = levelBounds(level, 9, { name: "TYRIAN", sections: [3], bonus: false, galaga: false, engage: false }, g.res.enemyDat, c);
    expect(b.explain.length).toBe(473);
    const spawnSum = b.explain.reduce((a, e) => a + e.value, 0);
    expect(spawnSum + c.powerUpSlack).toBe(b.static[2]);
    expect(b.static[2]).toBe(513771);
    expect(b.warps).toEqual([27, 30]);
  });

  test("the graph follows the script: story order, item-screen choices, warps, difficulty", () => {
    const m = maxScores(files);
    const e1 = m.episodes[1];
    // Normal starts on TYRIAN lvl 9, Hard on lvl 15 (`]h[` skips a line in section 3).
    expect(e1.graph.lo.start).toEqual([9]);
    expect(e1.graph.hi.start).toEqual([15]);
    // TYRIAN -> the asteroid decision (ASTEROID1 or 2, a `]G[` choice), or its warps (sections 27
    // and 30: HOLES 11, SOH JIN 13).
    expect(e1.graph.lo.next[9]).toEqual([1, 2, 11, 13]);
    // Savara: Normal plays lvl 12 (section 29 via `]H[`), Hard lvl 8.
    expect(e1.graph.lo.next[1]).toContain(8);
    expect(e1.graph.hi.next[1]).toContain(12);
    expect(e1.graph.lo.end).toEqual([16, 18]);
  });

  // The bot (invulnerable, always firing) plays the first two levels of episode 1; its real score
  // and ticks must sit inside the bounds, and its run must pass every server check.
  test("a played run is inside the bounds", () => {
    const m = maxScores(files);
    mt_srand(7);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1, 2);
    const levels: { lvl: number; ticks: number; score: number; done: boolean }[] = [];
    for (let i = 0; i < 2; i++) {
      loadLevel(files, 1, g.mainLevel);
      g.player[0].items.weapon[0].power = 5;
      startLevel();
      clearSimInput();
      let result = tick();
      let t = 1;
      for (; t < 60000 && !result.levelOver; t++) {
        botTick(t);
        result = tick();
      }
      expect(result.completed).toBe(true);
      levels.push({ lvl: g.lvlFileNum, ticks: t, score: JE_totalScore(g.player[0]), done: true });
      g.mainLevel = g.nextLevel;
    }
    const e1 = m.episodes[1];
    for (const l of levels) {
      const b = e1.levels[l.lvl];
      expect(l.ticks).toBeGreaterThanOrEqual(b.minTicks);
      if (b.maxTicks !== null) expect(l.ticks).toBeLessThanOrEqual(b.maxTicks);
    }
    const gain = levels[0].score - e1.constants.startTotal;
    expect(gain).toBeLessThanOrEqual(levelCap(e1.levels[levels[0].lvl], 2, levels[0].ticks));
    const ticks = levels.reduce((a, l) => a + l.ticks, 0);
    const run = { episode: 1, difficulty: 2, ended: "quit", levels, score: levels[1].score };
    expect(checkRun(m, run, (ticks / m.tickHz) * 1000)).toMatchObject({ ok: true });
    console.log("bot run:", JSON.stringify(levels));
  }, 120000);
});
