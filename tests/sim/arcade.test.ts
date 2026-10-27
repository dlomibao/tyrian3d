// [arcade] Starting the arcade games (src/sim/arcade.ts: newGame's arcade branch,
// newSuperArcadeGame, newSuperTyrianGame), the title's typed codes (titleScreen's
// specialNameProgress), and the arcade item screen menus. tests/sim/arcadeTrace.test.ts plays the
// games against the C.
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { CodeMatcher, codeChar, startNewGame, titleCode, type NewGameChoice } from "../../src/sim/arcade";
import {
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_key,
  JE_itemScreen_update,
  MENU_1_PLAYER_ARCADE,
  MENU_FULL_GAME,
  MENU_OPTIONS,
  MENU_SUPER_TYRIAN,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { loadHelpText, parseMenuText } from "../../src/sim/helptext";
import { buildResources } from "../../src/sim/resources";
import { JE_loadGame, JE_saveGame, loadSaves, setSaveStorage, type SaveStorage } from "../../src/sim/savegame";
import {
  DIFFICULTY_HARD,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_NORMAL,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_ZINGLON,
  g,
  SA_ARCADE,
  SA_NONE,
  SA_SUPERTYRIAN,
} from "../../src/sim/state";
import { SASpecialWeapon, SAShip, SAWeapon } from "../../src/sim/varz";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");

/** The title's choice, after the item data and help text are loaded (as run.ts does). */
function start(choice: Partial<NewGameChoice>): void {
  const c: NewGameChoice = { mode: "fullGame", episode: 1, difficulty: DIFFICULTY_NORMAL, ...choice };
  g.res = buildResources(files, c.superTyrian ? 1 : c.episode);
  loadHelpText(readData("tyrian.hdt"));
  startNewGame(c);
}

describe("the title's codes (titleScreen's specialNameProgress)", () => {
  const codes = ["STEALTH", "STORMWIND", "TECHNO", "ENEMY", "WEIRD", "UNKNOWN", "NORTSHIPZ", "DESTRUCT", "ENGAGE"];
  const type = (m: CodeMatcher, s: string) => [...s].map((c) => m.feed(c));

  test("a code completes on its last letter, naming its index", () => {
    const m = new CodeMatcher(codes);
    expect(type(m, "STEALTH")).toEqual([-1, -1, -1, -1, -1, -1, 0]);
    expect(type(m, "NORTSHIPZ").at(-1)).toBe(6); // nine letters: the longest a code can be
    expect(type(m, "ENGAGE").at(-1)).toBe(8);
  });

  test("codes sharing a start are followed together", () => {
    const m = new CodeMatcher(codes);
    type(m, "ST");
    expect(m.progress.slice(0, 2)).toEqual([2, 2]);
    expect(type(m, "ORMWIND").at(-1)).toBe(1);
  });

  test("a wrong letter starts the code over without counting as its first (the C's quirk)", () => {
    const m = new CodeMatcher(codes);
    expect(type(m, "SSTEALTH")).not.toContain(0);
    expect(type(m, "XSTEALTH").at(-1)).toBe(0);
  });

  test("a key with no character resets every code; a code longer than nine letters never completes", () => {
    const m = new CodeMatcher(codes);
    type(m, "STEAL");
    m.feed(codeChar("ArrowUp"));
    expect(m.progress.every((p) => p === 0)).toBe(true);
    expect(type(m, "TH")).toEqual([-1, -1]);
    const long = new CodeMatcher(["ABCDEFGHIJ"]);
    expect(type(long, "ABCDEFGHIJ")).not.toContain(0);
  });

  test("continuing() tells a letter inside a code from a fresh one (the title's L/O/H/M shortcuts)", () => {
    const m = new CodeMatcher(codes);
    m.feed("T");
    expect(m.continuing()).toBe(false);
    m.feed("E"); // TE.. of TECHNO
    expect(m.continuing()).toBe(true);
    m.feed("O");
    expect(m.continuing()).toBe(false);
  });

  test("codeChar is the C's toupper of an ASCII key, else '\\0'", () => {
    expect(codeChar("s")).toBe("S");
    expect(codeChar("Z")).toBe("Z");
    expect(codeChar("Enter")).toBe("\0");
    expect(codeChar("é")).toBe("\0");
  });

  test("specialName[i] starts Super Arcade ship i + 1, Destruct (8) or Super Tyrian (9)", () => {
    expect(titleCode(0)).toEqual({ kind: "superArcade", superArcadeMode: 1 });
    expect(titleCode(6)).toEqual({ kind: "superArcade", superArcadeMode: 7 });
    expect(titleCode(7)).toEqual({ kind: "destruct" });
    expect(titleCode(8)).toEqual({ kind: "superTyrian" });
  });

  test.skipIf(!HAVE)("the codes in the data are the ones the title matches", () => {
    const { specialName, superShips } = parseMenuText(readData("tyrian.hdt"));
    expect(specialName).toEqual(codes);
    expect(superShips[0]).toBe("Super Arcade Mode");
    expect(superShips[1]).toBe("Ninja Star");
  });
});

describe.skipIf(!HAVE)("starting an arcade game", () => {
  test("1 Player Arcade: the Stalker, no cash, one life (the front weapon's power)", () => {
    start({ mode: "arcade", difficulty: DIFFICULTY_HARD });
    const p = g.player[0];
    expect(g.onePlayerAction).toBe(true);
    expect(g.twoPlayerMode).toBe(false);
    expect(g.superArcadeMode).toBe(SA_NONE);
    expect(p.cash).toBe(0);
    expect(p.items.ship).toBe(8);
    expect(p.items.weapon[0]).toEqual({ id: 1, power: 1 });
    expect(p.lives.value).toBe(1);
    expect(g.difficultyLevel).toBe(DIFFICULTY_HARD);
    expect(g.initialDifficulty).toBe(DIFFICULTY_HARD);
  });

  test("a full game keeps its cash, and a smuggled Super Arcade ship", () => {
    start({ mode: "fullGame", episode: 2, smuggledShip: SAShip[0] });
    expect(g.onePlayerAction).toBe(false);
    expect(g.player[0].cash).toBe(15000);
    expect(g.player[0].items.ship).toBe(SAShip[0]);
  });

  test.each([1, 2, 3, 4, 5, 6, 7])("Super Arcade ship %i: its ship, first weapon and special, one step harder", (m) => {
    start({ superArcade: m, episode: 2, difficulty: DIFFICULTY_HARD });
    const p = g.player[0];
    expect(g.superArcadeMode).toBe(m);
    expect(g.onePlayerAction).toBe(true);
    expect(g.superTyrian).toBe(false);
    expect(g.episodeNum).toBe(2);
    expect(g.difficultyLevel).toBe(DIFFICULTY_IMPOSSIBLE);
    expect(g.initialDifficulty).toBe(DIFFICULTY_IMPOSSIBLE);
    expect(p.cash).toBe(0);
    expect(p.items.ship).toBe(SAShip[m - 1]);
    expect(p.items.weapon[0].id).toBe(SAWeapon[m - 1][0]);
    expect(p.items.special).toBe(SASpecialWeapon[m - 1]);
    expect(p.items.sidekick).toEqual(m === 7 ? [24, 24] : [0, 0]); // Nort-Ship Z's Quicksilvers
  });

  test("Super Tyrian: episode 1 at Lord of Game (or Suicide), the Stalker 21.126 and its RailGun", () => {
    start({ superTyrian: { suicide: false }, episode: 3 });
    expect(g.superTyrian).toBe(true);
    expect(g.onePlayerAction).toBe(true);
    expect(g.episodeNum).toBe(1);
    expect(g.difficultyLevel).toBe(DIFFICULTY_ZINGLON);
    expect(g.initialDifficulty).toBe(DIFFICULTY_ZINGLON);
    expect(g.player[0].items.ship).toBe(13);
    expect(g.player[0].items.weapon[0].id).toBe(39);
    expect(g.player[0].cash).toBe(0);
    start({ superTyrian: { suicide: true } });
    expect(g.difficultyLevel).toBe(DIFFICULTY_SUICIDE);
  });

  test("a new game after an arcade one is a full game again (JE_initPlayerData)", () => {
    start({ superArcade: 3 });
    start({ mode: "fullGame" });
    expect(g.superArcadeMode).toBe(SA_NONE);
    expect(g.onePlayerAction).toBe(false);
    expect(g.player[0].items.ship).toBe(1);
    expect(g.player[0].items.special).toBe(0);
  });

  test("2 Player Arcade: newGame's two-player branch (src/sim/twoplayer.ts), one step harder", () => {
    start({ mode: "twoPlayerArcade", episode: 2, difficulty: DIFFICULTY_NORMAL, smuggledShip: SAShip[0] });
    expect(g.twoPlayerMode).toBe(true);
    expect(g.onePlayerAction).toBe(false);
    expect(g.episodeNum).toBe(2);
    expect(g.player[0].items.ship).toBe(11); // Silver Ship, not the smuggled one
    expect(g.player.map((p) => p.cash)).toEqual([0, 0]);
    expect(g.initialDifficulty).toBe(DIFFICULTY_NORMAL);
    expect(g.difficultyLevel).toBe(DIFFICULTY_HARD);
  });

  test("a one-player game after a two-player one is one-player again", () => {
    start({ mode: "twoPlayerArcade" });
    start({ mode: "arcade" });
    expect(g.twoPlayerMode).toBe(false);
    expect(g.onePlayerAction).toBe(true);
  });
});

describe.skipIf(!HAVE)("arcade games in the save slots", () => {
  class MemoryStorage implements SaveStorage {
    data = new Map<string, string>();
    getItem(k: string): string | null {
      return this.data.get(k) ?? null;
    }
    setItem(k: string, v: string): void {
      this.data.set(k, v);
    }
  }
  beforeEach(() => {
    setSaveStorage(new MemoryStorage());
    loadSaves();
  });
  afterEach(() => setSaveStorage(null));

  test.each([
    ["arcade", { mode: "arcade" }, SA_ARCADE],
    ["Super Arcade", { superArcade: 5 }, 5],
    ["Super Tyrian", { superTyrian: { suicide: false } }, SA_SUPERTYRIAN],
  ] as const)("the LAST LEVEL backup of a %s game loads back into it", (_, choice, saved) => {
    start(choice);
    const before = { mode: g.superArcadeMode, ship: g.player[0].items.ship, special: g.player[0].items.special };
    JE_saveGame(11, "LAST LEVEL    ");
    expect(g.player[0].items.super_arcade_mode).toBe(saved);
    start({ mode: "fullGame" });
    JE_loadGame(11, files);
    expect(g.onePlayerAction).toBe(true);
    expect(g.superTyrian).toBe(saved === SA_SUPERTYRIAN);
    expect(g.superArcadeMode).toBe(before.mode);
    expect(g.player[0].items.ship).toBe(before.ship);
    expect(g.player[0].items.special).toBe(before.special);
  });
});

describe.skipIf(!HAVE)("the arcade item screen", () => {
  /** The item screen as JE_loadMap opens it (gameLoaded is false again by then). */
  const openItemScreen = () => {
    g.gameLoaded = false;
    g.jumpSection = false;
    menu.curMenu = MENU_FULL_GAME;
    menu.curSel.fill(2);
    JE_itemScreen_update();
  };
  const press = (...keys: ItemScreenKey[]) => {
    for (const k of keys) {
      JE_itemScreen_key(k);
      if (JE_itemScreen_done()) return;
      JE_itemScreen_update();
    }
  };

  test("1 Player Arcade shows its own menu, and its Options row opens Options and comes back", () => {
    start({ mode: "arcade" });
    openItemScreen();
    expect(menu.curMenu).toBe(MENU_1_PLAYER_ARCADE);
    expect(itemScreenEntries().map((e) => e.label)).toEqual(["Play Next Level", "Options", "Quit Game"]);
    expect(itemScreenEntries().some((e) => e.unavailable)).toBe(false);
    press("down", "enter");
    expect(menu.curMenu).toBe(MENU_OPTIONS);
    press("esc");
    expect(menu.curMenu).toBe(MENU_1_PLAYER_ARCADE);
  });

  test("Super Tyrian's menu has Ship Specs and Options", () => {
    start({ superTyrian: { suicide: false } });
    openItemScreen();
    expect(menu.curMenu).toBe(MENU_SUPER_TYRIAN);
    expect(itemScreenEntries().map((e) => e.label)).toEqual(["Play Next Level", "Ship Specs", "Options", "Quit Game"]);
    press("down", "down", "enter");
    expect(menu.curMenu).toBe(MENU_OPTIONS);
    press("esc");
    expect(menu.curMenu).toBe(MENU_SUPER_TYRIAN);
  });
});
