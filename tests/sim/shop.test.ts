// The item screen (src/sim/game_menu.ts, a port of OpenTyrian's game_menu.c) and item values
// (JE_getCost/JE_getValue in mainint.ts).
//
// The first suite is a cross-check against the real C code: fixtures/shop-trace.c.txt was produced
// by tools/opentyrian-shop/build.sh, which compiles OpenTyrian with a driver that feeds the scripted
// keys (fixtures/shop-trace.script) to the real JE_itemScreen through JE_loadMap and prints the
// screen's state each time it reads a key. The port must print the same lines.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, test } from "vitest";
import {
  itemScreenCash,
  itemScreenEntries,
  JE_cashLeft,
  JE_computeDots,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_mouse,
  JE_itemScreen_quitAnswer,
  JE_itemScreen_update,
  JE_mainMenuHelpText,
  JE_menuHeader,
  MENU_FULL_GAME,
  MENU_PLAY_NEXT_LEVEL,
  MENU_UPGRADE_SUB,
  MENU_UPGRADES,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { loadHelpText } from "../../src/sim/helptext";
import { JE_endLevelAni, JE_getCost, JE_getValue, JE_initPlayerData, weapon_upgrade_cost } from "../../src/sim/mainint";
import { mt_srand } from "../../src/sim/mtrand";
import { buildResources } from "../../src/sim/resources";
import { S_CLINK } from "../../src/sim/sndmast";
import { DIFFICULTY_NORMAL, g, type PlayerItems } from "../../src/sim/state";
import { loadLevel, sectionLevelName } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const fixture = (name: string) => readFileSync(join(__dirname, "fixtures", name), "utf8");
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");

/** A fresh one-player game, as the C driver sets one up. */
function freshGame(cash: number): void {
  mt_srand(1);
  if (!g.res || g.episodeNum !== 1) g.res = buildResources(files, 1);
  g.episodeNum = 1;
  loadHelpText(readData("tyrian.hdt"));
  JE_initPlayerData();
  g.playDemo = false;
  g.jumpSection = false;
  g.onePlayerAction = false;
  g.twoPlayerMode = false;
  g.superTyrian = false;
  g.constantPlay = false;
  g.difficultyLevel = DIFFICULTY_NORMAL;
  g.initialDifficulty = DIFFICULTY_NORMAL;
  g.gameLoaded = true;
  g.player[0].cash = cash;
  g.upgradeCost = g.downgradeCost = 0;
  g.cubeMax = 0;
  g.mapPNum = 0;
}

const ITEM_FIELDS: Record<string, (it: PlayerItems, v: number) => void> = {
  ship: (it, v) => (it.ship = v),
  front: (it, v) => (it.weapon[0].id = v),
  fpow: (it, v) => (it.weapon[0].power = v),
  rear: (it, v) => (it.weapon[1].id = v),
  rpow: (it, v) => (it.weapon[1].power = v),
  shield: (it, v) => (it.shield = v),
  gen: (it, v) => (it.generator = v),
  sk0: (it, v) => (it.sidekick[0] = v),
  sk1: (it, v) => (it.sidekick[1] = v),
};

/** The driver's print_state. */
function stateLine(): string {
  const it = g.player[0].items;
  let s = `K menu=${menu.curMenu} sel=${menu.curSel[menu.curMenu]} cash=${g.player[0].cash}`;
  if (menu.curMenu === MENU_UPGRADE_SUB) {
    const left = JE_cashLeft();
    s += ` left=${left} upg=${g.upgradeCost}`;
  }
  const b = (x: boolean) => (x ? 1 : 0);
  s +=
    ` items=${it.ship},${it.weapon[0].id}:${it.weapon[0].power},${it.weapon[1].id}:${it.weapon[1].power},` +
    `${it.shield},${it.generator},${it.sidekick[0]},${it.sidekick[1]} mode=${g.player[0].weapon_mode} ` +
    `power=${b(menu.leftPower)}${b(menu.rightPower)}${b(menu.rightPower && menu.rightPowerAfford)}`;
  return s;
}

/** Drives the item screen like JE_itemScreen's loop does with queued keys, logging like the driver. */
function scriptedItemScreen(keys: ItemScreenKey[], out: string[]): () => void {
  return () => {
    JE_itemScreen_init();
    JE_itemScreen_update();
    itemScreenEntries(); // the C draws the menu (and calls JE_drawScore) before reading a key
    for (let i = 0; i < 9; i++) out.push(`A ${i}${g.itemAvail[i].slice(0, g.itemAvailMax[i]).map((x) => ` ${x}`).join("")}`);
    for (const k of keys) {
      if (JE_itemScreen_done()) break;
      out.push(stateLine());
      JE_itemScreen_key(k);
      if (JE_itemScreen_done()) break;
      JE_itemScreen_update();
      itemScreenEntries();
    }
    if (!JE_itemScreen_done()) throw new Error("script ran out of keys");
  };
}

describe.skipIf(!HAVE)("item screen cross-check with OpenTyrian's C", () => {
  test("every scripted session prints the C's states", () => {
    const expected = fixture("shop-trace.c.txt").trimEnd().split("\n");
    const out: string[] = [];
    for (const line of fixture("shop-trace.script").split("\n")) {
      if (!line || line.startsWith("#")) continue;
      out.push(`S ${line}`);
      const [section, cash, ...rest] = line.split(" ");
      freshGame(Number(cash));
      const keys: ItemScreenKey[] = [];
      for (const tok of rest) {
        const eq = tok.indexOf("=");
        if (eq >= 0) {
          const v = Number(tok.slice(eq + 1));
          ITEM_FIELDS[tok.slice(0, eq)](g.player[0].items, v);
          ITEM_FIELDS[tok.slice(0, eq)](g.player[0].last_items, v);
        } else keys.push(tok as ItemScreenKey);
      }
      loadLevel(files, 1, Number(section), scriptedItemScreen(keys, out));
      out.push(stateLine());
      out.push(`E mainLevel=${g.mainLevel} level=${g.levelName}`);
    }
    expect(out).toEqual(expected);
  });
});

describe.skipIf(!HAVE)("item values (JE_getCost, JE_getValue, JE_cashLeft)", () => {
  beforeEach(() => freshGame(10000));

  test("weapon power upgrades cost base × (1 + 2 + … + power), as weapon_upgrade_cost", () => {
    expect([1, 2, 3, 4, 5, 10, 11].map((p) => weapon_upgrade_cost(100, p))).toEqual([100, 300, 600, 1000, 1500, 5500, 6600]);
    expect(() => weapon_upgrade_cost(100, 12)).toThrow();
  });

  test("JE_getCost: base prices per category, custom ships cost 100, weapons set upgradeCost for the current power", () => {
    const { items } = g.res;
    expect(JE_getCost(2, 1)).toBe(items.ships[1].cost);
    expect(JE_getCost(2, 91)).toBe(100);
    expect(JE_getCost(5, 4)).toBe(items.shields[4].cost);
    expect(JE_getCost(6, 2)).toBe(items.powerSys[2].cost);
    expect(JE_getCost(7, 9)).toBe(items.options[9].cost);
    expect(JE_getCost(8, 9)).toBe(items.options[9].cost);

    // Pulse-Cannon (port 1) at power 3: upgrading to 4 costs base × (1 + 2 + 3), and downgrading
    // to 2 refunds base × (1 + 2).
    g.player[0].items.weapon[0].power = 3;
    const base = items.weaponPorts[1].cost;
    expect(base).toBe(500);
    expect(JE_getCost(3, 1)).toBe(base);
    expect(g.upgradeCost).toBe(base * 6);
    expect(g.downgradeCost).toBe(base * 3);
  });

  test("JE_getValue: a weapon is worth its base plus every upgrade bought", () => {
    const base = g.res.items.weaponPorts[1].cost;
    for (const power of [1, 2, 5, 11]) {
      g.player[0].items.weapon[0].power = power;
      let expected = base;
      for (let i = 1; i < power; i++) expected += weapon_upgrade_cost(base, i);
      expect(JE_getValue(3, 1)).toBe(expected);
    }
  });

  test("JE_cashLeft sums power upgrades in a 16-bit word, which would wrap for a weapon over 1191", () => {
    // No episode 1 weapon costs that much (base × 55 > 65535 at power 11), so price one up for the test.
    const ports = g.res.items.weaponPorts;
    const id = 1;
    const saved = ports[id].cost;
    const cost = (ports[id].cost = 1500);
    menu.curSel[MENU_UPGRADES] = 3;
    g.player[0].items.weapon[0] = { id, power: 11 };
    let tempW = 0;
    let wrapped = 10000 - cost;
    let exact = 10000 - cost;
    for (let i = 1; i < 11; i++) {
      tempW = (tempW + cost * i) & 0xffff;
      wrapped -= tempW;
      exact -= weapon_upgrade_cost(cost, i);
    }
    expect(JE_cashLeft()).toBe(wrapped);
    expect(wrapped).not.toBe(exact);
    ports[id].cost = saved;
  });
});

/** Run the item screen at section `section` with `drive` doing the player's part; returns loadLevel's result. */
function withItemScreen(section: number, drive: () => void): boolean {
  return loadLevel(files, 1, section, () => {
    JE_itemScreen_init();
    JE_itemScreen_update();
    drive();
  });
}

const press = (...keys: ItemScreenKey[]) => {
  for (const k of keys) {
    JE_itemScreen_key(k);
    if (JE_itemScreen_done()) return;
    JE_itemScreen_update();
  }
};

describe.skipIf(!HAVE)("buying", () => {
  beforeEach(() => freshGame(10000));

  test("the menus: titles and choices come from tyrian.hdt", () => {
    withItemScreen(2, () => {
      expect(menu.curMenu).toBe(MENU_FULL_GAME);
      expect(itemScreenEntries().map((e) => e.label)).toEqual(g.menuInt[1].slice(1, 7));
      expect(itemScreenEntries().map((e) => e.sel)).toEqual([2, 3, 4, 5, 6, 7]);
      press("down", "down", "enter");
      expect(menu.curMenu).toBe(MENU_UPGRADES);
      expect(JE_menuHeader()).toBe(g.menuInt[2][0]);
      expect(itemScreenEntries()).toHaveLength(8); // 7 categories and Done
      expect(JE_mainMenuHelpText()).toBe(g.mainMenuHelp[6 - 1]);
      press("down", "enter");
      expect(menu.curMenu).toBe(MENU_UPGRADE_SUB);
      expect(JE_menuHeader()).toBe(g.menuInt[2][2]); // Front Gun
      const rows = itemScreenEntries();
      expect(rows.map((r) => r.item)).toEqual([1, 2, 7, 13, undefined]); // WeapF 13 2 7 + the Pulse-Cannon, sorted; Done
      expect(rows[0].owned).toBe(true);
      expect(rows[4].done).toBe(true);
      press("esc", "esc", "down", "down", "enter", "enter");
    });
  });

  test("buying with too little cash is refused: the cursor skips it, and clicking it clinks", () => {
    g.player[0].cash = 0;
    withItemScreen(2, () => {
      press("down", "down", "enter", "down", "enter"); // Front Gun: cash 0 + the Pulse-Cannon's 500
      expect(g.player[0].cash).toBe(500);
      expect(itemScreenCash()).toBe(0);
      const rows = itemScreenEntries();
      const pricey = rows.find((r) => r.cost !== undefined && r.cost > g.player[0].cash)!;
      expect(pricey.unaffordable).toBe(true);

      const before = menu.curSel[MENU_UPGRADE_SUB];
      menu.sounds.length = 0;
      JE_itemScreen_mouse(pricey.sel);
      JE_itemScreen_update();
      expect(menu.sounds).toContain(S_CLINK);
      expect(menu.curSel[MENU_UPGRADE_SUB]).toBe(before);

      press("down"); // every other weapon costs more than 500: the cursor lands on Done
      expect(menu.curSel[MENU_UPGRADE_SUB]).toBe(menu.menuChoices[MENU_UPGRADE_SUB]);
      expect(g.player[0].items.weapon[0].id).toBe(1);
      press("enter");
      expect(menu.curMenu).toBe(MENU_UPGRADES);
      expect(g.player[0].cash).toBe(0);
      press("esc", "down", "down", "enter", "enter");
    });
    expect(g.player[0].items.weapon[0]).toEqual({ id: 1, power: 1 });
  });

  test("weapon power: going up from power p costs base × (1 + … + p), refused when unaffordable", () => {
    g.player[0].cash = 2000;
    withItemScreen(2, () => {
      press("down", "down", "enter", "down", "enter");
      expect(menu.rightPower && menu.rightPowerAfford).toBe(true);
      expect(g.upgradeCost).toBe(500); // 1 → 2
      press("right");
      expect(g.player[0].items.weapon[0].power).toBe(2);
      expect(JE_cashLeft()).toBe(2000 - 500);
      expect(g.upgradeCost).toBe(1500); // 2 → 3: 500 × 3, exactly the 1500 left
      press("right");
      expect(g.player[0].items.weapon[0].power).toBe(3);
      expect(JE_cashLeft()).toBe(0);
      menu.sounds.length = 0;
      press("right"); // 3 → 4 costs 3000
      expect(g.player[0].items.weapon[0].power).toBe(3);
      expect(menu.sounds).toContain(S_CLINK);
      press("left"); // downgrading refunds 1500
      expect(JE_cashLeft()).toBe(1500);
      press("enter", "enter");
      expect(g.player[0].cash).toBe(1500);
      press("esc", "down", "down", "enter", "enter");
    });
    expect(g.player[0].items.weapon[0]).toEqual({ id: 1, power: 2 });
    expect(g.player[0].cash).toBe(1500);
  });

  test("Escape leaves a submenu without buying", () => {
    withItemScreen(2, () => {
      press("down", "down", "enter", "down", "enter", "down", "right");
      expect(g.player[0].items.weapon[0].id).not.toBe(1);
      press("esc");
      expect(g.player[0].items.weapon[0]).toEqual({ id: 1, power: 1 });
      expect(g.player[0].cash).toBe(10000);
      press("esc", "down", "down", "enter", "enter");
    });
  });

  test("selling: the owned item's value (with upgrades) is credited on entering its submenu", () => {
    g.player[0].items.weapon[0] = { id: 1, power: 3 };
    g.player[0].last_items.weapon[0] = { id: 1, power: 3 };
    withItemScreen(2, () => {
      press("down", "down", "enter", "down", "enter");
      expect(g.player[0].cash).toBe(10000 + JE_getValue(3, 1));
      expect(JE_getValue(3, 1)).toBe(500 + 500 + 1500);
      expect(itemScreenCash()).toBe(10000);
      press("esc", "esc", "down", "down", "enter", "enter");
    });
  });

  test("the next item screen offers what the player flew last (JE_endLevelAni's last_items)", () => {
    g.player[0].items.weapon[1].id = 15; // Vulcan Cannon, not on section 2's list
    JE_endLevelAni();
    withItemScreen(2, () => {
      expect(g.itemAvail[2].slice(0, g.itemAvailMax[2])).toEqual([10, 11, 15, 29, 0]);
      press("down", "down", "down", "down", "enter", "enter");
    });
  });
});

describe.skipIf(!HAVE)("navigation (]G[ and Play Next Level)", () => {
  beforeEach(() => freshGame(10000));

  test("the first ]G[ (section 2) offers one destination, Tyrian, section 3", () => {
    withItemScreen(2, () => {
      expect([g.mapOrigin, g.mapPNum, g.mapPlanet[0], g.mapSection[0]]).toEqual([1, 1, 1, 3]);
      press("down", "down", "down", "down", "enter");
      expect(menu.curMenu).toBe(MENU_PLAY_NEXT_LEVEL);
      expect(itemScreenEntries().map((e) => e.label)).toEqual([g.pName[0], g.miscText[5]]);
      expect(sectionLevelName(files, 1, g.mapSection[0])).toBe("TYRIAN");
      press("enter");
    });
    expect(g.mainLevel).toBe(3);
    expect(g.levelName.trim()).toBe("TYRIAN");
  });

  test.each([
    [0, 5, "ASTEROID1"],
    [1, 6, "ASTEROID2"],
  ])("section 4's ]G[: choice %i goes to section %i (%s)", (choice, section, level) => {
    withItemScreen(4, () => {
      expect(g.mapPNum).toBe(2);
      expect(g.mapSection.slice(0, 2)).toEqual([5, 6]);
      press("down", "down", "down", "down", "enter");
      expect(itemScreenEntries().map((e) => e.label)).toEqual([g.pName[1], g.pName[2], g.miscText[5]]);
      for (let i = 0; i < choice; i++) press("down");
      press("enter");
    });
    expect(g.mainLevel).toBe(section);
    expect(g.levelName.trim()).toBe(level);
  });

  test("the route dots (JE_computeDots) follow JE_partWay", () => {
    g.mapOrigin = 1;
    g.mapPNum = 2;
    g.mapPlanet[0] = 2;
    g.mapPlanet[1] = 3;
    JE_computeDots();
    // Tyrian (200, 40) to planet 2 (150, 90): sqrt(sqrt(5000)) = 8.4 → 8 - 1 = 7 dots.
    expect(menu.planetDots[0]).toBe(7);
    expect(menu.planetDotX[0][0]).toBe(Math.trunc(-50 / 9) * 1 + 200);
    expect(menu.planetDotY[0][6]).toBe(Math.trunc(50 / 9) * 7 + 40);
  });

  test("without a player, loadLevel takes the C's non-interactive choice: the last destination", () => {
    expect(loadLevel(files, 1, 4)).toBe(true);
    expect(g.mainLevel).toBe(6);
  });

  test("quitting from the item screen returns to the title (loadLevel returns false, mainLevel 0)", () => {
    const loaded = withItemScreen(2, () => {
      press("esc");
      expect(menu.quitRequest).toBe(true);
      JE_itemScreen_quitAnswer(false);
      expect(JE_itemScreen_done()).toBe(false);
      press("esc");
      JE_itemScreen_quitAnswer(true);
      expect(JE_itemScreen_done()).toBe(true);
    });
    expect(loaded).toBe(false);
    expect(g.mainLevel).toBe(0);
  });
});
