// [two-player] A local two-player game: newTwoPlayerGame (newGame's "2 Player Arcade"), each
// player's input, the 2 Player Arcade item-screen menu, two-player saves and JE_main's
// two-player rules. botTrace.test.ts plays a two-player level against the C itself.
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import {
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_update,
  MENU_2_PLAYER_ARCADE,
  MENU_OPTIONS,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput, joystick_analog_angle, playerInput, simInput, simInputs } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { JE_loadGame, JE_saveGame, loadSaves, saveSlotViews, setSaveStorage, type SaveStorage } from "../../src/sim/savegame";
import { DIFFICULTY_HARD, DIFFICULTY_NORMAL, FRONT_WEAPON, g, REAR_WEAPON } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { newTwoPlayerGame, playerInGame } from "../../src/sim/twoplayer";
import { JE_getShipInfo } from "../../src/sim/varz";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");

class MemoryStorage implements SaveStorage {
  data = new Map<string, string>();
  getItem(k: string): string | null {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string): void {
    this.data.set(k, v);
  }
}

function newGame(two = true, episode = 1, difficulty = DIFFICULTY_NORMAL): void {
  mt_srand(1);
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  g.constantPlay = false;
  g.cubeMax = 0;
  if (two) newTwoPlayerGame(episode, difficulty);
  else newOnePlayerGame(episode, difficulty);
}

const press = (...keys: ItemScreenKey[]) => {
  for (const k of keys) {
    JE_itemScreen_key(k);
    if (JE_itemScreen_done()) return;
    JE_itemScreen_update();
  }
};

beforeEach(() => {
  setSaveStorage(new MemoryStorage());
  loadSaves();
  clearSimInput();
});
afterEach(() => setSaveStorage(null));

describe("each player's input", () => {
  test("player 2 reads their own input in a two-player game, player 1's otherwise (and in galaga mode)", () => {
    expect(simInput).toBe(simInputs[0]);
    expect(playerInput(1, true, false)).toBe(simInputs[0]);
    expect(playerInput(2, true, false)).toBe(simInputs[1]);
    expect(playerInput(2, false, false)).toBe(simInputs[0]);
    expect(playerInput(2, true, true)).toBe(simInputs[0]);
    simInputs[1].fire = true;
    simInputs[1].analogAngle = 1;
    clearSimInput();
    expect(simInputs[1].fire).toBe(false);
    expect(simInputs[1].analogAngle).toBeNull();
  });

  test("joystick_analog_angle: the linked gun's direction from a stick (0 = down the screen)", () => {
    const close = (a: number | null, b: number) => expect(a).toBeCloseTo(b, 5);
    expect(joystick_analog_angle(0, 0)).toBeNull();
    expect(joystick_analog_angle(0.1, -0.1)).toBeNull(); // inside the dead zone (threshold 5000)
    close(joystick_analog_angle(0, 1), 0);
    close(joystick_analog_angle(0, -1), Math.PI);
    close(joystick_analog_angle(1, 0), Math.PI / 2);
    close(joystick_analog_angle(-1, 0), -Math.PI / 2);
    close(joystick_analog_angle(1, 1), Math.PI / 4);
  });
});

describe.skipIf(!HAVE)("a two-player game", () => {
  test("newGame's 2 Player Arcade: Silver Ship and dragonwing, no cash, one step harder", () => {
    newGame(true, 1, DIFFICULTY_NORMAL);
    const [p1, p2] = g.player;
    expect(g.twoPlayerMode).toBe(true);
    expect(g.onePlayerAction).toBe(false);
    expect(g.initialDifficulty).toBe(DIFFICULTY_NORMAL);
    expect(g.difficultyLevel).toBe(DIFFICULTY_HARD);
    expect([p1.cash, p2.cash]).toEqual([0, 0]);
    expect(p1.items.ship).toBe(11);
    expect(p2.items.weapon[REAR_WEAPON].id).toBe(15); // Vulcan Cannon
    expect(g.inputDevice).toEqual([0, 0]);
    JE_getShipInfo();
    expect(g.shipGr2).toBe(0); // the dragonwing
    expect(p2.armor).toBe(10);
    // Each player's lives are their own weapon's power.
    p1.items.weapon[FRONT_WEAPON].power = 3;
    p2.items.weapon[REAR_WEAPON].power = 4;
    expect([p1.lives.value, p2.lives.value]).toEqual([3, 4]);
    newTwoPlayerGame(1, DIFFICULTY_NORMAL, { inputDevices: [1, 2] });
    expect(g.inputDevice).toEqual([1, 2]); // the C's keyboard and mouse
  });

  test("the item screen is the 2 Player Arcade menu: next level, input rows, options, quit", () => {
    newGame();
    loadLevel(files, 1, 1, () => {
      JE_itemScreen_init();
      JE_itemScreen_update();
      expect(menu.curMenu).toBe(MENU_2_PLAYER_ARCADE);
      const entries = itemScreenEntries();
      expect(entries.map((e) => e.sel)).toEqual([2, 3, 4, 5, 6]);
      expect(entries.some((e) => e.unavailable)).toBe(false);
      expect(entries.map((e) => e.inputPlayer)).toEqual([undefined, 0, 1, undefined, undefined]);
      press("down", "enter"); // Player 1 Input
      expect(menu.inputRequest).toBe(0);
      menu.inputRequest = null;
      press("down", "enter"); // Player 2 Input
      expect(menu.inputRequest).toBe(1);
      menu.inputRequest = null;
      press("down", "enter"); // Options
      expect(menu.curMenu).toBe(MENU_OPTIONS);
      press("esc"); // back to the game menu
      expect(menu.curMenu).toBe(MENU_2_PLAYER_ARCADE);
      press("up", "up", "up", "enter"); // Play Next Level
      expect(JE_itemScreen_done()).toBe(true);
    });
    expect(g.levelName.trim()).toBe("TYRIAN");
  });

  test("two-player saves go to slots 12-22 and bring both players back", () => {
    newGame();
    g.player[0].cash = 1234;
    g.player[1].cash = 567;
    g.player[1].items.weapon[REAR_WEAPON] = { id: 21, power: 3 };
    g.saveLevel = 3;
    JE_saveGame(13, "DUO");
    expect(saveSlotViews(12, 11)[1].name.trim()).toBe("DUO");
    newGame(false);
    JE_loadGame(13, files);
    expect(g.twoPlayerMode).toBe(true);
    expect([g.player[0].cash, g.player[1].cash]).toEqual([1234, 567]);
    expect(g.player[1].items.weapon[REAR_WEAPON]).toEqual({ id: 21, power: 3 });
  });

  test("JE_main: both shields recharge, power stays full, and the level goes on while either player is in", () => {
    newGame();
    loadLevel(files, 1, 3);
    startLevel();
    const [p1, p2] = g.player;
    p1.shield = 0;
    p2.shield = 0;
    for (let i = 0; i < 40; i++) tick();
    expect(p1.shield).toBeGreaterThan(0);
    expect(p2.shield).toBeGreaterThan(0);
    expect(g.power).toBe(900);

    // Player 1 out of lives and done exploding; player 2 still flying.
    p1.is_alive = false;
    p1.exploding_ticks = 0;
    p1.items.weapon[FRONT_WEAPON].power = 1;
    tick();
    expect(g.allPlayersGone).toBe(false);
    expect(playerInGame(0)).toBe(false);
    expect(playerInGame(1)).toBe(true);
    p2.is_alive = false;
    p2.exploding_ticks = 0;
    p2.items.weapon[REAR_WEAPON].power = 1;
    tick();
    expect(g.allPlayersGone).toBe(true);
  });
});
