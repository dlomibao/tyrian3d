// The cheats and secret inputs (src/sim/cheats.ts): JE_mainKeyboardInput's chords, titleScreen's
// specialName codes, difficultySelect's hidden difficulties and the LOOT parameter.
import { beforeEach, describe, expect, test } from "vitest";
import {
  applyCheatParams,
  difficultyNamesByLevel,
  difficultySelectKey,
  difficultySelectLevels,
  JE_mainKeyboardInput,
  newDifficultySelectState,
  specialNameChar,
  SpecialNameMatcher,
  titleCodeFor,
} from "../../src/sim/cheats";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText, parseMenuText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import {
  DIFFICULTY_EASY,
  DIFFICULTY_HARD,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_NORMAL,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_ZINGLON,
  g,
  SA_NONE,
} from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { JE_playerDamage } from "../../src/sim/varz";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

/** Tyrian 2.1's specialName (tyrian.hdt), for the tests that don't read the data. */
const SPECIAL_NAME = ["STEALTH", "STORMWIND", "TECHNO", "ENEMY", "WEIRD", "UNKNOWN", "NORTSHIPZ", "DESTRUCT", "ENGAGE"];

const type = (m: SpecialNameMatcher, text: string): number[] => [...text].map((c) => m.key(specialNameChar(c))).filter((i) => i >= 0);

describe("title codes (titleScreen's specialNameProgress)", () => {
  test("each code, typed in either case, completes on its last letter", () => {
    SPECIAL_NAME.forEach((name, i) => {
      const m = new SpecialNameMatcher(SPECIAL_NAME);
      const done = [...name.toLowerCase()].map((c) => m.key(specialNameChar(c)));
      expect(done.slice(0, -1).every((d) => d === -1)).toBe(true);
      expect(done.at(-1)).toBe(i);
    });
  });

  test("codes can follow other keys, but a wrong key starts over without counting itself", () => {
    const m = new SpecialNameMatcher(SPECIAL_NAME);
    expect(type(m, "xyzTECHNO")).toEqual([2]);
    expect(type(m, "SSTEALTH")).toEqual([]); // the second S breaks STEALTH and isn't a new start
    expect(type(m, " STEALTH")).toEqual([0]);
    expect(type(m, "STEALXTH")).toEqual([]);
    // Shared prefixes run side by side: ST is the start of STEALTH and STORMWIND.
    expect(type(m, "STORMWIND")).toEqual([1]);
  });

  test("a key without a character ('\\0', an arrow) breaks a code, and a finished code doesn't re-fire", () => {
    const m = new SpecialNameMatcher(SPECIAL_NAME);
    expect(type(m, "ENEM")).toEqual([]);
    expect(m.key(specialNameChar("ArrowUp"))).toBe(-1);
    expect(type(m, "Y")).toEqual([]);
    expect(type(m, "ENEMY")).toEqual([3]);
    expect(m.key(specialNameChar("ArrowUp"))).toBe(-1);
    expect(m.progress.every((p) => p === 0)).toBe(true);
  });

  test("typing: two or more letters of some code", () => {
    const m = new SpecialNameMatcher(SPECIAL_NAME);
    m.key("S");
    expect(m.typing).toBe(false);
    m.key("T");
    expect(m.typing).toBe(true);
    m.key("Q");
    expect(m.typing).toBe(false);
  });

  test("specialName[i] starts Super Arcade mode i + 1, then Destruct (8) and Super Tyrian (9)", () => {
    for (let i = 0; i < 7; i++) expect(titleCodeFor(i)).toEqual({ kind: "superArcade", index: i });
    expect(titleCodeFor(7)).toEqual({ kind: "destruct" });
    expect(titleCodeFor(8)).toEqual({ kind: "superTyrian" });
  });

  test("specialNameChar: uppercase ASCII, '\\0' for anything else", () => {
    expect(specialNameChar("a")).toBe("A");
    expect(specialNameChar("Z")).toBe("Z");
    expect(specialNameChar(" ")).toBe(" ");
    expect(specialNameChar("Enter")).toBe("\0");
    expect(specialNameChar("é")).toBe("\0");
  });

  test.skipIf(!hasData("tyrian.hdt"))("the data's codes are the ones above", () => {
    expect(parseMenuText(readData("tyrian.hdt")).specialName).toEqual(SPECIAL_NAME);
  });
});

describe("hidden difficulties (difficultySelect)", () => {
  test("Shift+G, then Shift+], then L O R D show one more each, only in that order", () => {
    const s = newDifficultySelectState();
    expect(difficultySelectKey(s, "]", true, false)).toBe(false); // not yet
    expect(difficultySelectKey(s, "g", false, false)).toBe(false); // needs Shift
    expect(s.visible).toBe(3);
    expect(difficultySelectKey(s, "g", true, false)).toBe(true);
    expect(s.visible).toBe(4);
    expect(difficultySelectKey(s, "g", true, false)).toBe(false);
    expect(difficultySelectKey(s, "]", true, false)).toBe(true);
    expect(s.visible).toBe(5);
    for (const c of "lor") expect(difficultySelectKey(s, c, false, false)).toBe(true);
    expect(s.visible).toBe(5);
    expect(difficultySelectKey(s, "d", false, false)).toBe(true);
    expect(s.visible).toBe(6);
  });

  test("a wrong key sets LORD back; holding all four at once works too", () => {
    const s = { visible: 5, lordProgress: 0 };
    for (const c of "loxrd") difficultySelectKey(s, c, false, false);
    expect(s.visible).toBe(5);
    expect(s.lordProgress).toBe(0);
    expect(difficultySelectKey(s, "r", false, true)).toBe(true);
    expect(s.visible).toBe(6);
  });

  test("the six items set Easy, Normal, Hard, Impossible, Suicide and Lord of the Game", () => {
    expect([...difficultySelectLevels]).toEqual([
      DIFFICULTY_EASY,
      DIFFICULTY_NORMAL,
      DIFFICULTY_HARD,
      DIFFICULTY_IMPOSSIBLE,
      DIFFICULTY_SUICIDE,
      DIFFICULTY_ZINGLON,
    ]);
    const names = difficultyNamesByLevel(["Difficulty", "a", "b", "c", "d", "e", "f"]);
    expect(difficultySelectLevels.map((l) => names[l])).toEqual(["a", "b", "c", "d", "e", "f"]);
  });

  test.skipIf(!hasData("tyrian.hdt"))("names by level from the data", () => {
    const names = difficultyNamesByLevel(parseMenuText(readData("tyrian.hdt")).difficultyName);
    expect(names[DIFFICULTY_SUICIDE]).toMatch(/suicide/i);
    expect(names[DIFFICULTY_ZINGLON]).toMatch(/lord/i);
  });
});

/** keysactive as the host keeps it. */
const keys = (...codes: string[]) => new Set(codes);

function resetCheatState(): void {
  g.youAreCheating = false;
  g.isNetworkGame = false;
  g.twoPlayerMode = false;
  g.superTyrian = false;
  g.superArcadeMode = SA_NONE;
  g.constantPlay = false;
  g.levelTimer = false;
  g.levelTimerCountdown = 0;
  g.endLevel = false;
  g.levelEnd = 0;
  g.textErase = 0;
  g.messageText = "";
}

describe("JE_mainKeyboardInput's chords", () => {
  beforeEach(resetCheatState);

  test("F2 F4 F6 F7 F9 \\ / gives the Nort ship with its weapons and Astral Zone", () => {
    JE_mainKeyboardInput(keys("F2", "F4", "F6", "F7", "F9", "Backslash"));
    expect(g.player[0].items.ship).not.toBe(12);
    JE_mainKeyboardInput(keys("F2", "F4", "F6", "F7", "F9", "Backslash", "Slash"));
    expect(g.player[0].items.ship).toBe(12);
    expect(g.player[0].items.special).toBe(13);
    expect(g.player[0].items.weapon[0].id).toBe(36);
    expect(g.player[0].items.weapon[1].id).toBe(37);
    expect(g.shipGr).toBe(1);
  });

  test("F2 F3 F6 toggles invulnerability and lets go of F2, so holding the rest doesn't toggle back", () => {
    const k = keys("F2", "F3", "F6");
    JE_mainKeyboardInput(k);
    expect(g.youAreCheating).toBe(true);
    expect(k.has("F2")).toBe(false);
    JE_mainKeyboardInput(k);
    expect(g.youAreCheating).toBe(true);
    k.add("F2");
    JE_mainKeyboardInput(k);
    expect(g.youAreCheating).toBe(false);
  });

  test("F2 F3 F4 (or F5) empties the armor, toggles cheating and says miscText[62]", () => {
    g.miscText[62] = "Destruction:";
    g.player[0].armor = 10;
    JE_mainKeyboardInput(keys("F2", "F3", "F5"));
    expect(g.player[0].armor).toBe(0);
    expect(g.player[1].armor).toBe(0);
    expect(g.youAreCheating).toBe(true);
    expect(g.messageText).toBe("Destruction:");
    expect(g.textErase).toBe(100);
  });

  test("no cheating in Super Arcade, Super Tyrian or two-player games; Super Tyrian clears it", () => {
    g.superArcadeMode = 1;
    JE_mainKeyboardInput(keys("F2", "F3", "F6"));
    expect(g.youAreCheating).toBe(false);
    g.superArcadeMode = SA_NONE;
    g.twoPlayerMode = true;
    JE_mainKeyboardInput(keys("F2", "F3", "F6"));
    expect(g.youAreCheating).toBe(false);
    g.twoPlayerMode = false;
    g.youAreCheating = true;
    g.superTyrian = true;
    JE_mainKeyboardInput(keys("KeyA"));
    expect(g.youAreCheating).toBe(false);
  });

  test("constantPlay's C toggles cheating only with constantPlay", () => {
    JE_mainKeyboardInput(keys("KeyC"));
    expect(g.youAreCheating).toBe(false);
    g.constantPlay = true;
    JE_mainKeyboardInput(keys("KeyC"));
    expect(g.youAreCheating).toBe(true);
  });

  test("F2 F6 F7 (or F8), without F9, ends the level through the level timer", () => {
    JE_mainKeyboardInput(keys("F2", "F6", "F7", "F9"));
    expect(g.endLevel).toBe(false);
    JE_mainKeyboardInput(keys("F2", "F6", "F8"));
    expect(g.endLevel).toBe(true);
    expect(g.levelEnd).toBe(40);
    expect(g.levelTimer).toBe(true);
    expect(g.levelTimerCountdown).toBe(0);
  });

  test("not in Super Arcade", () => {
    g.superArcadeMode = 3;
    JE_mainKeyboardInput(keys("F2", "F6", "F7"));
    expect(g.endLevel).toBe(false);
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "levels1.dat"))("the chords in a level", () => {
  const start = () => {
    mt_srand(3);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1);
    resetCheatState();
    loadLevel(files, 1, g.mainLevel);
    startLevel();
    clearSimInput();
  };

  test("skipping the level finishes it, as completed, within a few seconds", () => {
    start();
    for (let t = 0; t < 50; t++) tick();
    JE_mainKeyboardInput(keys("F2", "F6", "F7"));
    let r = tick();
    let t = 0;
    for (; t < 1000 && !r.levelOver; t++) r = tick();
    expect(r.levelOver).toBe(true);
    expect(r.completed).toBe(true);
    expect(t).toBeLessThan(400);
  });

  test("while cheating, emptied armor and any hit don't destroy the ship", () => {
    start();
    JE_mainKeyboardInput(keys("F2", "F3", "F6"));
    expect(g.youAreCheating).toBe(true);
    const p = g.player[0];
    p.shield = 0;
    JE_playerDamage(200, p);
    expect(p.armor).toBe(0);
    expect(p.is_alive).toBe(true);
    g.youAreCheating = false;
    JE_playerDamage(200, p);
    expect(p.is_alive).toBe(false);
  });
});

describe("LOOT (params.c richMode)", () => {
  test("?loot in the address gives a new game 1,000,000 credits", () => {
    g.richMode = false;
    applyCheatParams("?music=synth");
    expect(g.richMode).toBe(false);
    applyCheatParams("?LOOT");
    expect(g.richMode).toBe(true);
    g.richMode = false;
    applyCheatParams("?a=1&loot");
    expect(g.richMode).toBe(true);
    g.richMode = false;
  });

  test.skipIf(!hasData("tyrian.hdt", "tyrian.shp", "levels1.dat"))("newGame's cash", () => {
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    g.richMode = true;
    newOnePlayerGame(1, DIFFICULTY_NORMAL);
    expect(g.player[0].cash).toBe(1000000);
    g.richMode = false;
    newOnePlayerGame(1, DIFFICULTY_NORMAL);
    expect(g.player[0].cash).toBe(10000);
  });
});
