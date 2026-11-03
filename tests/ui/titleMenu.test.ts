// The title's two-step menu (src/app/titleMenu.ts, D64): Start New Game opens the episodes with the
// difficulty row and Back; the other entries, the music style, the hidden difficulties and the codes'
// way back to where the menu was.
import { describe, expect, test } from "vitest";
import { episodeLabel, roman, TitleMenu, type TitleMenuConfig } from "../../src/app/titleMenu";

const menu = (cfg: Partial<TitleMenuConfig> = {}) =>
  new TitleMenu({ episodes: 4, more: 3, musicStyles: 3, difficulties: 3, episode: 0, difficulty: 1, musicStyle: 0, ...cfg });

describe("TitleMenu", () => {
  test("the top step is Start New Game, the other entries, then Music", () => {
    const m = menu();
    expect(m.rows().map((r) => r.kind)).toEqual(["start", "more", "more", "more", "music"]);
    expect(menu({ musicStyles: 1 }).rows().map((r) => r.kind)).toEqual(["start", "more", "more", "more"]);
    expect(menu({ more: 0, musicStyles: 0 }).rows().map((r) => r.kind)).toEqual(["start"]);
  });

  test("Start New Game opens the episodes, focused on the chosen one; Back and Escape return", () => {
    const m = menu({ episode: 2 });
    expect(m.intent("accept")).toEqual({ kind: "step" });
    expect(m.step).toBe("episodes");
    expect(m.rows().map((r) => r.kind)).toEqual(["episode", "episode", "episode", "episode", "difficulty", "back"]);
    expect(m.focus).toBe(2);
    expect(m.intent("back")).toEqual({ kind: "step" });
    expect(m.step).toBe("main");
    m.select(0);
    expect(m.select(5)).toEqual({ kind: "step" });
    expect(m.step).toBe("main");
    // Escape on the top step does nothing (the old title had no way back either).
    expect(m.intent("back")).toEqual({ kind: "none" });
  });

  test("up and down wrap; moving over an episode chooses it; choosing one starts", () => {
    const m = menu();
    m.intent("up");
    expect(m.row.kind).toBe("music");
    m.intent("down");
    expect(m.row.kind).toBe("start");
    m.open("episodes");
    m.intent("down");
    m.intent("down");
    expect(m.episode).toBe(2);
    m.intent("down");
    m.intent("down"); // the difficulty row keeps the chosen episode
    expect(m.row.kind).toBe("difficulty");
    expect(m.episode).toBe(3);
    expect(m.select(1)).toEqual({ kind: "start" });
    expect(m.episode).toBe(1);
  });

  test("the other entries ask to be opened", () => {
    const m = menu();
    expect(m.select(2)).toEqual({ kind: "more", index: 1 });
  });

  test("left and right pick the difficulty on the episodes step, stopping at the ends; Enter on the row wraps", () => {
    const m = menu();
    m.open("episodes");
    expect(m.intent("right")).toEqual({ kind: "paint" });
    expect(m.difficulty).toBe(2);
    expect(m.intent("right")).toEqual({ kind: "none" });
    m.focusRow(4);
    m.select(4);
    expect(m.difficulty).toBe(0);
    expect(m.intent("left")).toEqual({ kind: "none" });
  });

  test("left and right on Music change the style both ways; elsewhere on the top step they do nothing", () => {
    const m = menu();
    expect(m.intent("right")).toEqual({ kind: "none" });
    m.focusRow(4);
    expect(m.intent("left")).toEqual({ kind: "music", index: 2 });
    expect(m.intent("right")).toEqual({ kind: "music", index: 0 });
    expect(m.select(4)).toEqual({ kind: "music", index: 1 });
    expect(menu({ musicStyles: 1 }).cycleMusic(1)).toEqual({ kind: "none" });
  });

  test("revealed difficulties join the row; the choice stays in range", () => {
    const m = menu({ difficulty: 2 });
    m.setDifficulties(4);
    m.open("episodes");
    m.intent("right");
    expect(m.difficulty).toBe(3);
    m.setDifficulties(2);
    expect(m.difficulty).toBe(1);
  });

  test("a snapshot puts the step, focus and choices back (a code's first letter can move the menu)", () => {
    const m = menu();
    m.open("episodes");
    m.intent("down");
    const s = m.snapshot();
    m.intent("back");
    m.intent("down");
    m.restore(s);
    expect(m.snapshot()).toEqual(s);
    expect(m.step).toBe("episodes");
  });
});

describe("episode labels", () => {
  test("the data's names become a numeral and a title", () => {
    expect(episodeLabel("Episode 1: Escape", 1)).toEqual({ mark: "I", title: "Escape" });
    expect(episodeLabel("  Episode 3: Mission: Suicide ", 3)).toEqual({ mark: "III", title: "Mission: Suicide" });
    expect(episodeLabel("An End to Fate", 4)).toEqual({ mark: "IV", title: "An End to Fate" });
    expect(episodeLabel(undefined, 5)).toEqual({ mark: "V", title: "Episode 5" });
    expect(roman(9)).toBe("IX");
  });
});
