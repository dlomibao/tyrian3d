// The galaga bonus games, ALE (episode 1, section 41) and SQUADRON (episode 4, section 45), and the
// item-table overruns their doubled enemy values cause (D75). The C cross-checks of the same runs are
// botTrace.test.ts's ale-seed1041 and squadron-mortal fixtures.
import { describe, expect, test } from "vitest";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import {
  constFromSAWeapon,
  itemMemory,
  itemName,
  ITEM_MEMORY_SIZE,
  optionRecordAt,
  optionSelectAt,
  SAWeaponAt,
  specialArcadeWeaponAt,
  specialRecordAt,
  weaponPortAt,
} from "../../src/sim/overrun";
import { buildResources } from "../../src/sim/resources";
import { DIFFICULTY_NORMAL, FRONT_WEAPON, g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { optionSelect, SAWeapon, specialArcadeWeapon } from "../../src/sim/varz";
import { hasData, readData } from "../data/dataDir";
import { botTick } from "./bot";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

/** tools/inventory.mjs's start of a level: the seed first, then a new normal game, then JE_loadMap. */
function inventoryStart(episode: number, section: number): void {
  mt_srand(episode * 1000 + section);
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  newOnePlayerGame(episode, DIFFICULTY_NORMAL);
  loadLevel(files, episode, section);
  g.player[0].items.weapon[FRONT_WEAPON].power = 11;
  startLevel();
  clearSimInput();
}

describe("the reference build's read-only data past SAWeapon", () => {
  test("starts with SAWeapon, specialArcadeWeapon and optionSelect, as compiled", () => {
    const bytes = constFromSAWeapon();
    expect(bytes.length).toBe(2562);
    for (let mode = 0; mode < SAWeapon.length; mode++)
      for (let i = 0; i < 5; i++) expect(SAWeaponAt(mode, i)).toBe(SAWeapon[mode][i]);
    specialArcadeWeapon.forEach((v, i) => expect(specialArcadeWeaponAt(i)).toBe(v));
    optionSelect.forEach((rows, s) => rows.forEach((pair, l) => pair.forEach((v, side) => expect(optionSelectAt(s, l, side)).toBe(v))));
  });

  test("past their ends: what ALE's doubled values read", () => {
    expect(specialArcadeWeaponAt(30720 - 30001)).toBe(0); // value 15 doubled 11 times
    expect(specialArcadeWeaponAt(30464 - 30001)).toBe(125); // value 375 (a cash pickup) doubled 8 times
    expect(SAWeaponAt(0, 5000)).toBe(0); // past the block: zeros
  });
});

describe.skipIf(!hasData("tyrian.hdt", "tyrian4.lvl", "tyrian.shp", "palette.dat"))("the item tables as the C holds them in memory", () => {
  test.each([1, 4])("episode %i: every record in range reads back as the item data parses it", (episode) => {
    const { items } = buildResources(files, episode);
    expect(itemMemory(items).length).toBe(ITEM_MEMORY_SIZE);
    // buildResources appended what a Uint8 id can reach.
    expect([items.weaponPorts.length, items.specials.length, items.options.length]).toEqual([256, 256, 256]);
    for (let i = 0; i <= 42; i++) expect(weaponPortAt(items, i)).toEqual(items.weaponPorts[i]);
    for (let i = 0; i <= 46; i++) expect(specialRecordAt(items, i)).toEqual(items.specials[i]);
    for (let i = 0; i <= 30; i++) expect(optionRecordAt(items, i)).toEqual(items.options[i]);
    for (let i = 0; i <= 42; i++) expect(itemName(items, "weaponPort", i)).toBe(items.weaponPorts[i].name);
    // Past the block (the C's mutable globals): an empty name.
    expect(itemName(items, "weaponPort", 999)).toBe("");
  });

  test("episode 1: weaponPort[208] is bytes of weapons[169..170], as the C build read them", () => {
    const port = buildResources(files, 1).items.weaponPorts[208];
    expect(port.opNum).toBe(0);
    expect(port.op[0]).toEqual([1531, 0, 0, 0, 0, 0, 0, 0, 163, 164, 59]);
    expect(port.powerUse).toBe(257);
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat", "tyrian4.lvl", "levels4.dat", "tyrian.hdt"))("galaga bonus games", () => {
  test("ALE: the inventory's run survives the pickup that read past weaponPort at tick 2815", () => {
    inventoryStart(1, 41);
    expect(g.galagaMode).toBe(true);
    let t = 0;
    let result = tick();
    let pickedUpAt = -1;
    for (; t < 3000 && !result.levelOver; t++) {
      botTick(t);
      result = tick(); // threw "reading 'name'" at t = 2815 before D75
      if (pickedUpAt < 0 && g.player[0].items.weapon[FRONT_WEAPON].id !== 39) pickedUpAt = t;
    }
    expect(t).toBe(3000);
    // An enemy of value 15, doubled by every JE_searchFor to 30720, taken for weapon 720: the id is
    // u8(720) = 208 and the special specialArcadeWeapon[719], 0 in the reference build.
    expect(pickedUpAt).toBe(2815);
    expect(g.player[0].items.weapon[FRONT_WEAPON].id).toBe(208);
    expect(g.player[0].items.special).toBe(0);
    expect(g.messageText.startsWith(g.miscText[64 - 1])).toBe(true);
  }, 120000);

  test("SQUADRON has no end of its own: its waves loop until the ship is out of lives", () => {
    inventoryStart(4, 45);
    expect(g.galagaMode).toBe(true);
    const events = g.lvl.eventRec;
    // No end-level event (11) and no ready-to-end (36): JE_eventSystem never ends it.
    expect(events.filter((e) => e.eventType === 11 || e.eventType === 36)).toEqual([]);
    // The wave table at 60000+ calls the waves (event 54 jumps, each wave returning via event 76)
    // and then jumps back to 60000 (-5536 is 60000 as a JE_word): it repeats forever.
    const table = events.filter((e) => e.eventTime >= 60000 && e.eventTime < 65500);
    expect(table[0].eventType).toBe(77);
    expect(table.filter((e) => e.eventType === 54).map((e) => e.eventDat & 0xffff).at(-1)).toBe(60000);

    // So the invulnerable bot never ends it (tools/inventory.mjs's 60,000-tick run, which matched
    // the C tick for tick). Without the cheats the ship dies, and the level ends at game over:
    // the C shows "game over" and waits for a key (src/app/run.ts gives it one).
    let result = tick();
    let t = 0;
    for (; t < 20000 && !result.gameOver; t++) {
      botTick(t, true);
      result = tick();
    }
    expect(result.gameOver).toBe(true);
    expect(g.player[0].lives.value).toBe(1);
    g.reallyEndLevel = true; // the host's key press
    result = tick();
    expect(result.levelOver).toBe(true);
    expect(result.completed).toBe(false);
  }, 120000);
});
