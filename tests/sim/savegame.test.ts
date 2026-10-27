// Saved games (src/sim/savegame.ts, a port of config.c JE_saveGame/JE_loadGame) and the item
// screen's Options and Load/Save menus (src/sim/game_menu.ts).
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import {
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_mouse,
  JE_itemScreen_operation,
  JE_itemScreen_update,
  JE_itemScreen_volumeClick,
  JE_itemScreenNonInteractive,
  JE_mainMenuHelpText,
  JE_menuHeader,
  MENU_FULL_GAME,
  MENU_LOAD_SAVE,
  MENU_OPTIONS,
  MENU_UPGRADES,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { loadHelpText } from "../../src/sim/helptext";
import { JE_endLevelAni } from "../../src/sim/mainint";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import {
  emptySaveFile,
  JE_loadGame,
  JE_loadScreen_select,
  JE_operation_saveName,
  JE_saveGame,
  loadSaves,
  SAVE_FILES_NUM,
  SAVE_FORMAT_VERSION,
  SAVE_STORAGE_KEY,
  saveFiles,
  saveNameChar,
  saveSlotViews,
  serializeSaves,
  setSaveStorage,
  type SaveStorage,
} from "../../src/sim/savegame";
import { S_CLINK, S_CURSOR, S_SELECT, S_SPRING } from "../../src/sim/sndmast";
import { DIFFICULTY_HARD, DIFFICULTY_NORMAL, g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { DEFAULT_VOLUME, JE_changeVolume, setVolumeHandler, volume, volumeFromBarCells } from "../../src/sim/volume";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");
const HAVE_EP2 = HAVE && hasData("levels2.dat", "tyrian2.lvl");

/** An in-memory stand-in for localStorage. */
class MemoryStorage implements SaveStorage {
  data = new Map<string, string>();
  getItem(k: string): string | null {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string): void {
    this.data.set(k, v);
  }
}

let store: MemoryStorage;

/** A new one-player game on `episode`, as the title screen starts one. */
function newGame(episode = 1, difficulty = DIFFICULTY_NORMAL): void {
  mt_srand(1);
  g.res = buildResources(files, episode);
  g.episodeNum = episode;
  loadHelpText(readData("tyrian.hdt"));
  g.constantPlay = false;
  g.cubeMax = 0;
  newOnePlayerGame(episode, difficulty);
}

const press = (...keys: ItemScreenKey[]) => {
  for (const k of keys) {
    JE_itemScreen_key(k);
    if (JE_itemScreen_done()) return;
    JE_itemScreen_update();
  }
};

/** Run the item screen at `section` with `drive` doing the player's part (each visit, numbered). */
function withItemScreen(episode: number, section: number, drive: (visit: number) => void): boolean {
  let visit = 0;
  return loadLevel(files, episode, section, () => {
    JE_itemScreen_init();
    JE_itemScreen_update();
    drive(visit++);
    if (!JE_itemScreen_done()) JE_itemScreenNonInteractive();
  });
}

/** From the Game Menu, open Options (row 5). */
const openOptions = () => press("down", "down", "down", "enter");

beforeEach(() => {
  store = new MemoryStorage();
  setSaveStorage(store);
  loadSaves();
  volume.tyrMusicVolume = DEFAULT_VOLUME;
  volume.fxVolume = DEFAULT_VOLUME;
});
afterEach(() => {
  setSaveStorage(null);
  setVolumeHandler(() => {});
});

describe.skipIf(!HAVE)("JE_saveGame / JE_loadGame", () => {
  test("a save holds the loadout, cash, section, episode, difficulty and cubes, and loading restores them", () => {
    newGame(1, DIFFICULTY_HARD);
    const p = g.player[0];
    p.items.ship = 3;
    p.items.weapon[0] = { id: 5, power: 4 };
    p.items.weapon[1] = { id: 17, power: 2 };
    p.items.shield = 6;
    p.items.generator = 4;
    p.items.sidekick = [7, 9];
    p.last_items = structuredClone(p.items);
    p.last_items.ship = 2;
    p.cash = 123456;
    g.saveLevel = 9;
    g.lastCubeMax = 2;
    g.lastLevelName = "SAVARA";
    g.secretHint = 3;

    JE_saveGame(4, "PILOT ONE     ");
    const f = saveFiles[3];
    expect(f.level).toBe(9);
    expect(f.name).toBe("PILOT ONE     ");
    expect(f.levelName).toBe("SAVARA");
    expect(f.episode).toBe(1);
    expect(f.difficulty).toBe(DIFFICULTY_HARD);
    expect(f.initialDifficulty).toBe(DIFFICULTY_HARD);
    expect(f.score).toBe(123456);
    expect(f.cubes).toBe(2);
    expect(f.power).toEqual([4, 2]);
    // playeritems_to_pitems: front, rear, super arcade, sidekicks, generator, sidekick level/series, initial episode, shield, special, ship
    expect(f.items).toEqual([5, 17, 0, 7, 9, 4, 0, 0, 1, 6, 0, 3]);
    expect(f.lastItems[11]).toBe(2);

    newGame(1);
    JE_loadGame(4, files);
    expect(g.player[0].items.ship).toBe(3);
    expect(g.player[0].items.weapon).toEqual([{ id: 5, power: 4 }, { id: 17, power: 2 }]);
    expect(g.player[0].items.sidekick).toEqual([7, 9]);
    expect(g.player[0].items.shield).toBe(6);
    expect(g.player[0].last_items.ship).toBe(2);
    expect(g.player[0].cash).toBe(123456);
    expect(g.mainLevel).toBe(9);
    expect(g.saveLevel).toBe(9);
    expect(g.cubeMax).toBe(2);
    expect(g.lastCubeMax).toBe(2);
    expect(g.difficultyLevel).toBe(DIFFICULTY_HARD);
    expect(g.initialDifficulty).toBe(DIFFICULTY_HARD);
    expect(g.levelName).toBe("SAVARA");
    expect(g.lastLevelName).toBe("SAVARA");
    expect(g.secretHint).toBe(3);
    expect(g.twoPlayerMode).toBe(false);
  });

  test("LAST LEVEL (slot 11) is the retry backup: JE_loadGame(11) puts back what the level started with", () => {
    newGame();
    g.saveLevel = 4;
    g.player[0].cash = 777;
    JE_saveGame(11, "LAST LEVEL    ");
    const before = structuredClone(g.player[0].items);
    g.player[0].items.weapon[0] = { id: 2, power: 9 };
    g.player[0].cash = 0;
    g.mainLevel = 7;
    g.difficultyLevel = DIFFICULTY_HARD;
    JE_loadGame(11, files);
    expect(g.player[0].items).toEqual(before);
    expect(g.player[0].cash).toBe(777);
    expect(g.mainLevel).toBe(4);
    expect(g.difficultyLevel).toBe(DIFFICULTY_NORMAL);
    // JE_operation can't save over it.
    expect(JE_operation_saveName(11)).toBeNull();
    expect(JE_operation_saveName(1)).toBe("");
  });

  test.skipIf(!HAVE_EP2)("loading a save from another episode switches the episode's item data (JE_initEpisode)", () => {
    newGame(2);
    g.saveLevel = 1;
    JE_saveGame(2, "EPISODE TWO   ");
    newGame(1);
    const ep1Items = g.res.items;
    expect(JE_loadScreen_select(2, files)).toBe(true);
    expect(g.episodeNum).toBe(2);
    expect(g.res.items).not.toBe(ep1Items);
    expect(g.gameJustLoaded).toBe(true);
  });

  test("an empty slot doesn't load", () => {
    newGame();
    g.gameLoaded = false;
    expect(JE_loadScreen_select(5, files)).toBe(false);
  });
});

describe.skipIf(!HAVE)("the slots in storage", () => {
  test("saving writes versioned JSON; loadSaves reads the same slots back", () => {
    newGame();
    g.saveLevel = 6;
    JE_saveGame(1, "ALPHA         ");
    const stored = JSON.parse(store.getItem(SAVE_STORAGE_KEY)!);
    expect(stored.version).toBe(SAVE_FORMAT_VERSION);
    expect(stored.slots).toHaveLength(SAVE_FILES_NUM);
    const saved = structuredClone(saveFiles);
    saveFiles.fill(emptySaveFile());
    loadSaves();
    expect(saveFiles).toEqual(saved);
    expect(serializeSaves()).toBe(store.getItem(SAVE_STORAGE_KEY));
  });

  test("a bad store leaves every slot empty; one bad slot is emptied on its own", () => {
    store.setItem(SAVE_STORAGE_KEY, "{not json");
    loadSaves();
    expect(saveFiles.every((f) => f.level === 0)).toBe(true);

    store.setItem(SAVE_STORAGE_KEY, JSON.stringify({ version: 99, slots: [] }));
    loadSaves();
    expect(saveFiles.every((f) => f.level === 0)).toBe(true);

    newGame();
    g.saveLevel = 3;
    JE_saveGame(1, "GOOD          ");
    JE_saveGame(2, "BAD           ");
    const data = JSON.parse(store.getItem(SAVE_STORAGE_KEY)!);
    data.slots[1].items = [1, 2, 3];
    store.setItem(SAVE_STORAGE_KEY, JSON.stringify(data));
    loadSaves();
    expect(saveFiles[0].name).toBe("GOOD          ");
    expect(saveFiles[1].level).toBe(0);
  });

  test("the save-name prompt takes a space and what the font has (fontMap's ASCII part)", () => {
    expect([..."Az09 !?.-'"].every(saveNameChar)).toBe(true);
    expect([..."_<>@^&~`"].some(saveNameChar)).toBe(false);
    expect(saveNameChar("ab")).toBe(false);
  });

  test("the slot list shows the C's names: EMPTY SLOT, or the name, last level and episode", () => {
    newGame();
    g.saveLevel = 3;
    g.lastLevelName = "TYRIAN";
    JE_saveGame(3, "BRAVO         ");
    const rows = saveSlotViews(1, 11);
    expect(rows[0]).toMatchObject({ slot: 1, empty: true, name: g.miscText[2] });
    expect(rows[2]).toMatchObject({ slot: 3, empty: false, name: "BRAVO", levelName: "TYRIAN", episode: 1 });
  });
});

describe.skipIf(!HAVE)("the item screen's Options menu", () => {
  beforeEach(() => newGame());

  test("Options opens from the Game Menu with the C's rows; Done goes back", () => {
    withItemScreen(1, 2, () => {
      openOptions();
      expect(menu.curMenu).toBe(MENU_OPTIONS);
      expect(JE_menuHeader()).toBe(g.menuInt[3][0]);
      const rows = itemScreenEntries();
      expect(rows.map((e) => e.label)).toEqual(g.menuInt[3].slice(1, 8));
      expect(rows.some((e) => e.unavailable)).toBe(false);
      expect(rows.find((e) => e.sel === 4)?.volume).toBe(DEFAULT_VOLUME);
      expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[13 - 1]);
      press("up");
      expect(menu.curSel[MENU_OPTIONS]).toBe(8);
      press("enter");
      expect(menu.curMenu).toBe(MENU_FULL_GAME);
    });
  });

  test("Music and Sound change by 12 with left/right, clinking at the ends; the bars set them by click", () => {
    const set: [number, number][] = [];
    setVolumeHandler((m, s) => set.push([m, s]));
    withItemScreen(1, 2, () => {
      openOptions();
      press("down", "down"); // Music
      menu.sounds.length = 0;
      press("left");
      expect(volume.tyrMusicVolume).toBe(DEFAULT_VOLUME - 12);
      expect(menu.sounds).toEqual([S_CURSOR]);
      press("right", "right", "right", "right");
      expect(volume.tyrMusicVolume).toBe(255);
      expect(menu.sounds.slice(-2)).toEqual([S_CURSOR, S_CLINK]);
      press("down", "right"); // Sound
      expect(volume.fxVolume).toBe(235);
      expect(set.at(-1)).toEqual([255, 235]);
      JE_itemScreen_volumeClick(4, 5);
      expect(volume.tyrMusicVolume).toBe(60);
      expect(menu.curSel[MENU_OPTIONS]).toBe(4);
      // left/right elsewhere in the menu leave the volumes alone
      press("up", "up", "left");
      expect([volume.tyrMusicVolume, volume.fxVolume]).toEqual([60, 235]);
    });
    expect(volumeFromBarCells(30)).toBe(255);
    volume.fxVolume = 5;
    const sounds: number[] = [];
    JE_changeVolume(0, -12, (n) => sounds.push(n));
    expect(volume.fxVolume).toBe(0);
    expect(sounds).toEqual([S_CLINK]);
  });

  test("Joystick and Keyboard ask the host for its settings screen", () => {
    withItemScreen(1, 2, () => {
      openOptions();
      press("down", "down", "down", "down", "enter");
      expect(menu.setupRequest).toBe("joystick");
      menu.setupRequest = null;
      press("down", "enter");
      expect(menu.setupRequest).toBe("keyboard");
      expect(menu.curMenu).toBe(MENU_OPTIONS);
    });
  });

  test("Save: pick a slot, the host asks for a name, JE_operation saves it; cancelling saves nothing", () => {
    withItemScreen(1, 2, () => {
      openOptions();
      press("down", "enter"); // Save
      expect(menu.curMenu).toBe(MENU_LOAD_SAVE);
      expect(JE_menuHeader()).toBe(g.menuInt[3][2]);
      const rows = itemScreenEntries();
      expect(rows).toHaveLength(12);
      expect(rows[0].label).toBe(g.miscText[2]);
      expect(rows[11]).toMatchObject({ sel: 13, label: g.miscText[5], done: true });
      expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[21 - 1]);
      press("down", "enter"); // slot 2
      expect(menu.operationRequest).toBe(2);
      menu.sounds.length = 0;
      JE_itemScreen_operation(files, null);
      expect(saveFiles[1].level).toBe(0);
      expect(menu.sounds).toEqual([S_SPRING]);
      press("enter");
      JE_itemScreen_operation(files, "MY GAME");
      expect(menu.sounds.at(-1)).toBe(S_SELECT);
      expect(menu.curMenu).toBe(MENU_LOAD_SAVE);
      expect(itemScreenEntries()[1].label).toBe("MY GAME");
      // the last row goes back to Options
      press("up", "up", "enter");
      expect(menu.curMenu).toBe(MENU_OPTIONS);
    });
    expect(saveFiles[1]).toMatchObject({ name: "MY GAME       ", level: 2, episode: 1, levelName: g.miscText[19] });
    expect(store.getItem(SAVE_STORAGE_KEY)).toContain("MY GAME");
  });

  test("Alt-S saves from any menu and goes back to it; Escape does too", () => {
    withItemScreen(1, 2, () => {
      press("down", "down", "enter"); // Upgrade Ship
      expect(menu.curMenu).toBe(MENU_UPGRADES);
      press("quickSave");
      expect(menu.curMenu).toBe(MENU_LOAD_SAVE);
      expect(menu.performSave).toBe(true);
      press("enter");
      JE_itemScreen_operation(files, "QUICK");
      expect(menu.curMenu).toBe(MENU_UPGRADES);
      press("quickLoad");
      expect(JE_menuHeader()).toBe(g.menuInt[3][1]);
      press("esc");
      expect(menu.curMenu).toBe(MENU_UPGRADES);
    });
    expect(saveFiles[0].name.trim()).toBe("QUICK");
  });

  test("Load continues the saved game where the C does: JE_loadMap starts over at its section", () => {
    // Reference: section 4's item screen, left to its default choice.
    newGame();
    g.player[0].cash = 5000;
    expect(loadLevel(files, 1, 4)).toBe(true);
    const expected = { mainLevel: g.mainLevel, levelName: g.levelName, lvlFileNum: g.lvlFileNum };

    // Save at section 4 with some cash and a new front gun.
    newGame();
    withItemScreen(1, 4, (visit) => {
      if (visit > 0) return;
      g.player[0].cash = 5000;
      g.player[0].items.weapon[0].id = 3;
      g.player[0].items.weapon[0].power = 5;
      JE_endLevelAni(); // last_items, lastLevelName
      press("quickSave", "down", "down", "enter"); // slot 3
      JE_itemScreen_operation(files, "SECTION FOUR");
    });
    expect(saveFiles[2].level).toBe(4);

    // A new game, then load slot 3 from its first item screen.
    newGame();
    g.player[0].cash = 1;
    const visits: number[] = [];
    const loaded = withItemScreen(1, 1, (visit) => {
      visits.push(g.mainLevel);
      if (visit > 0) return;
      openOptions();
      press("enter"); // Load
      expect(JE_menuHeader()).toBe(g.menuInt[3][1]);
      press("down", "down", "enter");
      expect(menu.operationRequest).toBe(3);
      JE_itemScreen_operation(files);
      expect(JE_itemScreen_done()).toBe(true);
    });
    expect(loaded).toBe(true);
    // The item screen came back at the saved section, with the saved loadout.
    expect(visits).toEqual([2, 4]);
    expect({ mainLevel: g.mainLevel, levelName: g.levelName, lvlFileNum: g.lvlFileNum }).toEqual(expected);
    expect(g.player[0].cash).toBe(5000);
    expect(g.player[0].items.weapon[0]).toEqual({ id: 3, power: 5 });
    expect(g.saveLevel).toBe(4);
  });

  test("loading an empty slot does nothing; the mouse picks slots like rows", () => {
    withItemScreen(1, 2, () => {
      openOptions();
      press("enter");
      JE_itemScreen_mouse(5);
      JE_itemScreen_mouse(5);
      expect(menu.operationRequest).toBe(4);
      JE_itemScreen_operation(files);
      expect(JE_itemScreen_done()).toBe(false);
      expect(menu.curMenu).toBe(MENU_LOAD_SAVE);
    });
  });
});
