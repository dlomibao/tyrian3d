// Storing the high score tables (src/app/highScores.ts). There is no localStorage under node, so
// this also covers the fallback for blocked storage: the tables last for the session.
import { describe, expect, test } from "vitest";
import { loadHighScores, parseHighScores, saveHighScores } from "../../src/app/highScores";
import { SAVE_FILES_NUM } from "../../src/sim/highscores";

describe("high score storage", () => {
  test("a missing table gets sorted defaults, which then stay the same", () => {
    const t = loadHighScores();
    expect(t).toHaveLength(SAVE_FILES_NUM);
    for (let table = 0; table < 6; table++) {
      const scores = t.slice(table * 3, table * 3 + 3).map((e) => e.highScore1);
      expect(scores).toEqual([...scores].sort((a, b) => b - a));
    }
    expect(loadHighScores()).toEqual(t);
  });

  test("saved tables come back", () => {
    const t = loadHighScores();
    t[0].highScore1 = 999999;
    t[0].highScoreName = "Ace";
    saveHighScores(t);
    expect(loadHighScores()[0]).toMatchObject({ highScore1: 999999, highScoreName: "Ace" });
  });

  test("malformed tables are rejected; fields are clamped to the C types", () => {
    expect(parseHighScores(null)).toBeNull();
    expect(parseHighScores("not json")).toBeNull();
    expect(parseHighScores("[]")).toBeNull();
    const e = { highScore1: 1, highScore2: 0, highScoreName: "x", highScoreDiff: 0 };
    expect(parseHighScores(JSON.stringify(Array(SAVE_FILES_NUM).fill({ ...e, highScoreName: 3 })))).toBeNull();
    const ok = parseHighScores(JSON.stringify(Array(SAVE_FILES_NUM).fill({ ...e, highScoreName: "y".repeat(40), highScoreDiff: 257 })));
    expect(ok![0].highScoreName).toHaveLength(29);
    expect(ok![0].highScoreDiff).toBe(1);
  });
});
