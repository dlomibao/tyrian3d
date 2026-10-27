// The high score tables (src/sim/highscores.ts, a port of OpenTyrian's JE_highScoreCheck,
// JE_sortHighScores and loadSaves' defaults).
import { describe, expect, test } from "vitest";
import {
  defaultHighScoreNames,
  defaultHighScores,
  defaultTeamNames,
  EPISODE_AVAILABLE,
  highScoreCheckDue,
  highScoreCheckScore,
  highScoreNameAccepts,
  highScoreRank,
  highScoreStoredName,
  highScoreTable,
  JE_highScoreCheckEnter,
  JE_highScoreCheckSlot,
  JE_sortHighScores,
  SAVE_FILES_NUM,
  type HighScoreEntry,
} from "../../src/sim/highscores";
import { loadHelpText, parseMenuText } from "../../src/sim/helptext";
import { JE_getValue } from "../../src/sim/mainint";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { DIFFICULTY_HARD, DIFFICULTY_NORMAL, g } from "../../src/sim/state";
import { hasData, readData } from "../data/dataDir";

const entry = (highScore1: number, highScoreName: string, highScoreDiff = 0): HighScoreEntry => ({
  highScore1,
  highScore2: 0,
  highScoreName,
  highScoreDiff,
});

/** Every table at 3000, 2000, 1000 with names "<slot>". */
function ladder(): HighScoreEntry[] {
  return Array.from({ length: SAVE_FILES_NUM }, (_, i) => entry((3 - (i % 3)) * 1000, `n${i}`, 0));
}

describe("default tables (loadSaves)", () => {
  test("random 1000..20000 scores and names, team names for the two-player tables", () => {
    mt_srand(1);
    const t = defaultHighScores(mt_rand);
    expect(t).toHaveLength(SAVE_FILES_NUM);
    t.forEach((e, i) => {
      expect(e.highScore1 % 1000).toBe(0);
      expect(e.highScore1).toBeGreaterThanOrEqual(1000);
      expect(e.highScore1).toBeLessThanOrEqual(20000);
      expect(e.highScoreDiff).toBe(0);
      if (i % 6 < 3) {
        expect(defaultHighScoreNames).toContain(e.highScoreName);
        expect(e.highScore2).toBe(0);
      } else {
        expect(defaultTeamNames).toContain(e.highScoreName);
        expect(e.highScore2 % 1000).toBe(0);
        expect(e.highScore2).toBeGreaterThan(0);
      }
    });
  });

  test("draws mt_rand in the C's order: score, then name (then the team's second score)", () => {
    mt_srand(7);
    const r = [mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand(), mt_rand()];
    mt_srand(7);
    const t = defaultHighScores(mt_rand);
    expect(t[0]).toEqual(entry(((r[0] % 20) + 1) * 1000, defaultHighScoreNames[r[1] % 34]));
    expect(t[1]).toEqual(entry(((r[2] % 20) + 1) * 1000, defaultHighScoreNames[r[3] % 34]));
    expect(t[2]).toEqual(entry(((r[4] % 20) + 1) * 1000, defaultHighScoreNames[r[5] % 34]));
    expect(t[3]).toEqual({
      highScore1: ((r[6] % 20) + 1) * 1000,
      highScore2: ((r[7] % 20) + 1) * 1000,
      highScoreName: defaultTeamNames[r[8] % 22],
      highScoreDiff: 0,
    });
  });

  test("the lists are the C's (34 and 22 names)", () => {
    expect(defaultHighScoreNames).toHaveLength(34);
    expect(defaultTeamNames).toHaveLength(22);
    expect(defaultHighScoreNames[0]).toBe("The Prime Chair");
    expect(defaultHighScoreNames[33]).toBe("Rennis the Rat Guard");
    expect(defaultTeamNames[21]).toBe("Carlos' Crawlers");
  });
});

describe("JE_sortHighScores", () => {
  test("sorts each of the six tables of episodes 1-3, highest first, and leaves episode 4's slots", () => {
    const t = Array.from({ length: SAVE_FILES_NUM }, (_, i) => entry(((i * 7) % 5) * 1000 + i, `n${i}`, i));
    const before = t.map((e) => ({ ...e }));
    JE_sortHighScores(t);
    for (let table = 0; table < 6; table++) {
      const rows = t.slice(table * 3, table * 3 + 3);
      expect(rows.map((e) => e.highScore1)).toEqual([...rows.map((e) => e.highScore1)].sort((a, b) => b - a));
      // Names and difficulties move with their scores.
      for (const e of rows) {
        const orig = before.find((b) => b.highScore1 === e.highScore1)!;
        expect(e.highScoreName).toBe(orig.highScoreName);
        expect(e.highScoreDiff).toBe(orig.highScoreDiff);
      }
    }
    expect(t.slice(18)).toEqual(before.slice(18));
  });
});

describe("JE_highScoreCheck", () => {
  test("each episode has a one-player and a two-player table", () => {
    expect(highScoreTable(1, false)).toEqual({ first_slot: 0, slot_limit: 3 });
    expect(highScoreTable(1, true)).toEqual({ first_slot: 3, slot_limit: 6 });
    expect(highScoreTable(2, false)).toEqual({ first_slot: 6, slot_limit: 9 });
    expect(highScoreTable(3, false)).toEqual({ first_slot: 12, slot_limit: 15 });
  });

  test("a score qualifies only by beating an entry; ties don't", () => {
    expect(JE_highScoreCheckSlot(ladder(), 1, false, 1000)).toBe(-1);
    expect(JE_highScoreCheckSlot(ladder(), 1, false, 999)).toBe(-1);
    expect(JE_highScoreCheckSlot(ladder(), 1, false, 1001)).toBe(2);
    expect(JE_highScoreCheckSlot(ladder(), 1, false, 2500)).toBe(1);
    expect(JE_highScoreCheckSlot(ladder(), 1, false, 3001)).toBe(0);
  });

  test("the new entry goes in its place and the rest move down; other tables are untouched", () => {
    const t = ladder();
    t[6].highScoreDiff = 3;
    t[7].highScoreDiff = 4;
    t[8].highScoreDiff = 5;
    const slot = JE_highScoreCheckSlot(t, 2, false, 2500);
    expect(slot).toBe(7);
    JE_highScoreCheckEnter(t, slot, 2500, "Ace", DIFFICULTY_HARD);
    expect(t.slice(6, 9).map((e) => [e.highScore1, e.highScoreName.trimEnd(), e.highScoreDiff])).toEqual([
      [3000, "n6", 3],
      [2500, "Ace", DIFFICULTY_HARD],
      // The C's shift moves the score and name but not highScoreDiff.
      [2000, "n7", 5],
    ]);
    expect(t.slice(0, 6)).toEqual(ladder().slice(0, 6));
    expect(t.slice(9)).toEqual(ladder().slice(9));
  });

  test("the tables are sorted before the check", () => {
    const t = ladder();
    [t[0], t[2]] = [t[2], t[0]];
    expect(JE_highScoreCheckSlot(t, 1, false, 1500)).toBe(2);
    expect(t[0].highScoreName).toBe("n0");
  });

  test("cancelling the name entry leaves the shifted table, as in the C", () => {
    const t = ladder();
    const slot = JE_highScoreCheckSlot(t, 1, false, 5000);
    JE_highScoreCheckEnter(t, slot, 5000, null, DIFFICULTY_NORMAL);
    expect(t.slice(0, 3).map((e) => e.highScoreName)).toEqual(["n0", "n0", "n1"]);
  });

  test("the name is what was typed over the 29-space buffer, at most 28 characters the font has", () => {
    expect(highScoreStoredName("Ace")).toBe("Ace" + " ".repeat(26));
    expect(highScoreStoredName("")).toBe(" ".repeat(29));
    expect(highScoreStoredName("x".repeat(40))).toBe("x".repeat(28) + " ");
    expect(highScoreStoredName("a<b>@c_d")).toHaveLength(29);
    expect(highScoreStoredName("a<b>@c_d").trimEnd()).toBe("abcd");
    for (const ch of "!\"#$%'()*+,-./09:;=?AZ[\\]az{|}Çü¿ ") expect(highScoreNameAccepts(ch)).toBe(true);
    for (const ch of "&<>@^_`~€\t") expect(highScoreNameAccepts(ch)).toBe(false);
    expect(highScoreNameAccepts("é")).toBe(true);
    expect(highScoreNameAccepts("ab")).toBe(false);
  });

  test("difficultyNameB's index is the difficulty level, capped at the last name", () => {
    expect(highScoreRank(0)).toBe(0);
    expect(highScoreRank(DIFFICULTY_NORMAL)).toBe(2);
    expect(highScoreRank(12)).toBe(10);
  });

  test("JE_nextEpisode checks only the starting episode, never episode 4 or a repeated game", () => {
    g.isNetworkGame = false;
    g.constantPlay = false;
    g.gameHasRepeated = false;
    g.episodeNum = 2;
    expect(highScoreCheckDue(2)).toBe(true);
    expect(highScoreCheckDue(1)).toBe(false);
    g.gameHasRepeated = true;
    expect(highScoreCheckDue(2)).toBe(false);
    g.gameHasRepeated = false;
    g.constantPlay = true;
    expect(highScoreCheckDue(2)).toBe(false);
    g.constantPlay = false;
    g.episodeNum = EPISODE_AVAILABLE;
    expect(highScoreCheckDue(EPISODE_AVAILABLE)).toBe(false);
  });
});

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

describe.skipIf(!hasData("tyrian.hdt", "tyrian1.lvl", "levels1.dat"))("with the game data", () => {
  test("difficultyNameB is read from tyrian.hdt", () => {
    const t = parseMenuText(readData("tyrian.hdt"));
    expect(t.difficultyNameB).toHaveLength(11);
    expect(t.difficultyNameB[0]).toBe("Unranked");
    expect(t.difficultyNameB[10]).toBe("Nortaneous");
  });

  test("the one-player score is cash plus the value of the ship and gear (JE_totalScore)", () => {
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1, DIFFICULTY_NORMAL);
    const it = g.player[0].items;
    const gear =
      JE_getValue(2, it.ship) +
      JE_getValue(3, it.weapon[0].id) +
      JE_getValue(4, it.weapon[1].id) +
      JE_getValue(5, it.shield) +
      JE_getValue(6, it.generator) +
      JE_getValue(7, it.sidekick[0]) +
      JE_getValue(8, it.sidekick[1]);
    expect(gear).toBeGreaterThan(0);
    expect(highScoreCheckScore()).toBe(g.player[0].cash + gear);
    g.player[0].cash = 0x7fffffff;
    expect(highScoreCheckScore()).toBeLessThan(0); // temp_score is a Sint32
  });
});
