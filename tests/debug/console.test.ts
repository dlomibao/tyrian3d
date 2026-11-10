// The debug console (src/debug/console/, D109): its command line (words, completion, history), the
// level numbering and jumps (sections, not levels: the harness's main=), and its cheats acting on a
// real level through the sim's own functions.
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { commonPrefix, completeLine, findCommand, helpLines, History, tokenize, type CommandSpec } from "../../src/debug/console/parse";
import { listLevels, navTargets, resolveLevel, shopSectionFor } from "../../src/debug/console/levels";
import { categoryLabel, findCategory, itemScreenLists, offered, resetShopLists, SHOP_CATEGORIES, soldEverywhere } from "../../src/debug/console/shopLists";
import {
  itemScreenEntries,
  JE_itemScreen_done,
  JE_itemScreen_init,
  JE_itemScreen_key,
  JE_itemScreen_mouse,
  JE_itemScreen_update,
  JE_itemScreenNonInteractive,
  MENU_FULL_GAME,
  MENU_UPGRADE_SUB,
  MENU_UPGRADES,
  menu,
  type ItemScreenKey,
} from "../../src/sim/game_menu";
import { JE_getValue, JE_initPlayerData } from "../../src/sim/mainint";
import { createCommands, runLine, type ConsoleCtx } from "../../src/debug/console/commands";
import { consoleBridge, type ConsoleBridge } from "../../src/app/consoleBridge";
import { parseEpisodeScript, type EpisodeScript } from "../../src/data/episodeScript";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput, simInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { JE_playerDamage } from "../../src/sim/varz";
import { cameraStyle } from "../../src/core/displayStyle";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

describe("the command line", () => {
  const specs: CommandSpec[] = [
    { name: "camera", usage: "[overhead|tilted|steep]", help: "the camera", complete: (i) => (i === 0 ? ["overhead", "tilted", "steep"] : []) },
    { name: "credits", aliases: ["cash"], usage: "[N]", help: "the credits" },
    { name: "clear", usage: "", help: "empty it" },
    { name: "weapon", usage: "front|rear [id [power]]", help: "a gun", complete: (i) => (i === 0 ? ["front", "rear"] : []) },
  ];

  test("words split on spaces; quotes keep spaces", () => {
    expect(tokenize("  level 1   soh jin ")).toEqual(["level", "1", "soh", "jin"]);
    expect(tokenize(`level 1 "soh jin"`)).toEqual(["level", "1", "soh jin"]);
    expect(tokenize("")).toEqual([]);
  });

  test("a command by name or alias, any case", () => {
    expect(findCommand(specs, "CASH")?.name).toBe("credits");
    expect(findCommand(specs, "nope")).toBeUndefined();
  });

  test("Tab finishes a single fit, extends several to what they share and lists them", () => {
    expect(completeLine(specs, "cam")).toEqual({ line: "camera ", options: [] });
    expect(completeLine(specs, "c")).toEqual({ line: "c", options: ["camera", "cash", "clear", "credits"] });
    expect(completeLine(specs, "cr")).toEqual({ line: "credits ", options: [] });
    expect(completeLine(specs, "camera t")).toEqual({ line: "camera tilted ", options: [] });
    expect(completeLine(specs, "weapon ")).toEqual({ line: "weapon ", options: ["front", "rear"] });
    expect(completeLine(specs, "camera x")).toEqual({ line: "camera x", options: [] });
    expect(commonPrefix(["steep", "stereo"])).toBe("ste");
  });

  test("help lists every command with its arguments", () => {
    const lines = helpLines(specs);
    expect(lines).toHaveLength(4);
    expect(lines[1]).toMatch(/^credits\/cash \[N\]\s+the credits$/);
  });

  test("history: Up goes back, Down forward to the line being typed; repeats aren't kept twice", () => {
    const h = new History();
    h.push("god");
    h.push("armor 5");
    h.push("armor 5");
    expect(h.lines).toEqual(["god", "armor 5"]);
    expect(h.up("kil")).toBe("armor 5");
    expect(h.up("armor 5")).toBe("god");
    expect(h.up("god")).toBe("god"); // the oldest stays
    expect(h.down("god")).toBe("armor 5");
    expect(h.down("armor 5")).toBe("kil"); // back to the draft
    expect(h.down("kil")).toBe("kil");
  });
});

/** An episode script with sections like episode 1's start: an item screen, then a level with two variants. */
function fakeScript(): EpisodeScript {
  const sections = [
    ["]J 002["],
    ["]G[ 01 2 01 003  02 004", "]I["],
    ["]L[ 9999 004 TYRIAN   18 09", "]L[ 9999 004 TYRIAN   18 15"],
    ["]L[ 9999 005 SOH JIN  16 13"],
    ["]L[ 9999 006 SAVARA   33 12"],
    ["]L[ 9999 007 SAVARA   33 08$$"],
  ];
  const lines: string[] = [];
  const out: EpisodeScript = { lines, sections: [] };
  sections.forEach((sec, i) => {
    lines.push(`*${i + 1}`);
    out.sections.push({ number: i + 1, header: `*${i + 1}`, start: lines.length, lines: sec });
    lines.push(...sec);
  });
  return out;
}

describe("levels and sections", () => {
  const script = fakeScript();
  const levels = listLevels(script);

  test("one level per section that plays one, numbered in script order; variants share theirs", () => {
    expect(levels.map((l) => [l.number, l.name, l.section])).toEqual([
      [1, "TYRIAN", 3],
      [2, "SOH JIN", 4],
      [3, "SAVARA", 5],
      [4, "SAVARA", 6],
    ]);
    expect(levels[0].lvlFileNums).toEqual([9, 15]);
    expect(levels[3].bonus).toBe(true);
  });

  test("a level number is the list's, and jumps to its section (not main=N's level N)", () => {
    expect(resolveLevel(script, levels, "2")).toMatchObject({ section: 4, level: { name: "SOH JIN" } });
    expect(resolveLevel(script, levels, "9")).toMatchObject({ error: expect.stringMatching(/no level 9/) });
  });

  test("names: any case, spaces ignored, a unique start is enough; a shared name takes the first", () => {
    expect(resolveLevel(script, levels, "soh jin")).toMatchObject({ section: 4 });
    expect(resolveLevel(script, levels, "SOHJIN")).toMatchObject({ section: 4 });
    expect(resolveLevel(script, levels, "ty")).toMatchObject({ section: 3 });
    const savara = resolveLevel(script, levels, "savara");
    expect(savara).toMatchObject({ section: 5, note: expect.stringMatching(/took 3; the others are 4/) });
    expect(resolveLevel(script, levels, "s")).toMatchObject({ error: expect.stringMatching(/could be/) });
    expect(resolveLevel(script, levels, "zz")).toMatchObject({ error: expect.stringMatching(/no level called/) });
  });

  test("s<N> is a raw section, as the harness's main=N", () => {
    expect(resolveLevel(script, levels, "s2")).toEqual({ section: 2, level: null });
    expect(resolveLevel(script, levels, "#3")).toMatchObject({ section: 3, level: { name: "TYRIAN" } });
    expect(resolveLevel(script, levels, "s99")).toMatchObject({ error: expect.stringMatching(/no section 99/) });
  });

  test("]G['s destinations, and the item screen that leads to a level", () => {
    expect(navTargets("]G[ 01 2 02 005  03 006")).toEqual([5, 6]);
    expect(navTargets("]I[")).toEqual([]);
    expect(shopSectionFor(script, 3)).toBe(2);
    expect(shopSectionFor(script, 4)).toBe(2);
    expect(shopSectionFor(script, 5)).toBeNull();
  });

  test.skipIf(!hasData("levels1.dat", "levels2.dat"))("the data: episode 1 starts with TYRIAN in section 3, after section 2's item screen", () => {
    const s1 = parseEpisodeScript(readData("levels1.dat"));
    const l1 = listLevels(s1);
    expect(l1[0]).toMatchObject({ number: 1, name: "TYRIAN", section: 3, lvlFileNums: [9, 15] });
    expect(resolveLevel(s1, l1, "soh jin")).toMatchObject({ section: 31 });
    expect(shopSectionFor(s1, 3)).toBe(2);
    expect(shopSectionFor(s1, 5)).toBe(4); // ASTEROID1, from the asteroid decision's map
    const l2 = listLevels(parseEpisodeScript(readData("levels2.dat")));
    expect(l2[0]).toMatchObject({ name: "TORM", section: 2 });
  });
});

/** A console context on the bridge, as the screen makes one (no screen: close and clear do nothing). */
function ctxFor(place: ConsoleBridge["place"]): { ctx: ConsoleCtx; closed: () => number } {
  let closes = 0;
  Object.assign(consoleBridge, { place, files, view: null, host: null, jump: null, leave: null, refresh: null, speed: 1 });
  let perf = false;
  const ctx: ConsoleCtx = {
    bridge: consoleBridge,
    close: () => closes++,
    clear: () => {},
    overLeaveScreen: () => true,
    perf: { get: () => perf, set: (on) => (perf = on) },
  };
  return { ctx, closed: () => closes };
}

describe("console commands", () => {
  const cmds = createCommands();
  const run = (ctx: ConsoleCtx, line: string) => runLine(cmds, line, ctx);
  const text = (ctx: ConsoleCtx, line: string) => run(ctx, line).map((l) => `${l.kind}: ${l.text}`);

  test("help lists every command, and each has a usage line", () => {
    const { ctx } = ctxFor("title");
    const out = run(ctx, "help").map((l) => l.text);
    for (const c of cmds) expect(out.some((l) => l.startsWith(c.name))).toBe(true);
    for (const name of ["god", "armor", "shield", "credits", "weapon", "power", "sidekick", "kill", "heal", "level", "skip", "levels", "shop", "camera", "terrain", "sprites", "vfx", "bg", "music", "sound", "interface", "fps", "tick", "speed", "seed", "clear", "help", "reset"])
      expect(findCommand(cmds, name), name).toBeDefined();
    expect(text(ctx, "help weapon")[0]).toMatch(/weapon front\|rear \[id \[power\]\]/);
  });

  test("unknown commands and misuse are errors, not throws", () => {
    const { ctx } = ctxFor("title");
    expect(text(ctx, "frobnicate")).toEqual(['err: no command "frobnicate" (`help` lists them)']);
    expect(text(ctx, "armor 5")[0]).toMatch(/^err: only in a level/);
    expect(text(ctx, "speed 9")[0]).toMatch(/^err: speed: 0 to 8/);
    expect(text(ctx, "camera sideways")[0]).toMatch(/^err: camera: "sideways" isn't one of/);
  });

  test("settings: no argument shows, one sets (the same DisplayChoice as Options)", () => {
    const { ctx } = ctxFor("title");
    cameraStyle.reset();
    expect(text(ctx, "camera")).toEqual(["out: camera: tilted  (overhead | tilted | steep)"]);
    expect(text(ctx, "camera OVERHEAD")).toEqual(["out: camera: overhead"]);
    expect(cameraStyle.get()).toBe("overhead");
    expect(text(ctx, "reset")[0]).toMatch(/camera tilted/);
    expect(cameraStyle.get()).toBe("tilted");
    expect(text(ctx, "speed 2.5")).toEqual(["out: speed 2.5"]);
    expect(consoleBridge.speed).toBe(2.5);
    expect(text(ctx, "fps on")).toEqual(["out: perf overlay on"]);
    expect(ctx.perf.get()).toBe(true);
  });

  test.skipIf(!hasData("levels1.dat", "tyrian1.lvl"))("level on the title asks the game flow for that section; elsewhere it's refused", () => {
    const { ctx, closed } = ctxFor("title");
    expect(text(ctx, "level 1 tyrian")).toEqual(["out: → episode 1, level 1 TYRIAN (section 3)"]);
    expect(consoleBridge.jump).toEqual({ episode: 1, section: 3 });
    expect(closed()).toBe(1);
    expect(text(ctx, "level 1 13")).toEqual(["out: → episode 1, level 13 SOH JIN (section 31)"]);
    expect(text(ctx, "level 1 s31")).toEqual(["out: → episode 1, level 13 SOH JIN (section 31)"]);
    expect(text(ctx, "level 1 s2")).toEqual(["out: → episode 1, section 2"]);
    const menu = ctxFor("menu");
    expect(text(menu.ctx, "level 1 1")[0]).toMatch(/^err: not from this screen/);
    expect(consoleBridge.jump).toBeNull();
    const title = ctxFor("title").ctx; // the bridge is shared: back on the title
    expect(text(title, "level 1 99")[0]).toMatch(/^err: no level 99/);
    expect(text(title, "shop")).toEqual(["out: → a new game"]);
    expect(consoleBridge.jump).toEqual({ episode: 0, section: null });
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "levels1.dat"))("console cheats in a level", () => {
  const cmds = createCommands();
  let ctx: ConsoleCtx;
  const out = (line: string) => runLine(cmds, line, ctx).map((l) => `${l.kind}: ${l.text}`);
  beforeEach(() => {
    mt_srand(3);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1);
    g.youAreCheating = false;
    loadLevel(files, 1, g.mainLevel);
    startLevel();
    clearSimInput();
    ctx = ctxFor("level").ctx;
  });

  test("armor, shield and heal change the player as the game keeps them (armour capped at 28)", () => {
    const p = g.player[0];
    expect(out("armor 3")).toEqual(["out: armor 3"]);
    expect(p.armor).toBe(3);
    expect(out("armor 200")).toEqual(["out: armor 28"]);
    expect(out("shield 0")).toEqual([`out: shield 0 of ${p.shield_max}`]);
    expect(out("shield 255")).toEqual([`out: shield ${p.shield_max} of ${p.shield_max}`]);
    p.armor = 1;
    p.shield = 0;
    expect(out("heal")).toEqual([`out: armor ${p.initial_armor}, shield ${p.shield_max}`]);
    expect(out("credits 123456")).toEqual(["out: credits 123456"]);
    expect(p.cash).toBe(123456);
  });

  test("god is the original's invulnerability: a hit that would destroy the ship doesn't", () => {
    const p = g.player[0];
    expect(out("god")).toEqual(["out: god mode on"]);
    expect(g.youAreCheating).toBe(true);
    p.shield = 0;
    JE_playerDamage(200, p);
    expect(p.is_alive).toBe(true);
    expect(out("god off")).toEqual(["out: god mode off"]);
    JE_playerDamage(200, p);
    expect(p.is_alive).toBe(false);
  });

  test("a gun fitted by the console fires its new pattern at the new power, like a pickup", () => {
    for (let t = 0; t < 30; t++) tick();
    g.shotMultiPos[0] = 3;
    expect(out("weapon front 4 7")[0]).toMatch(/^out: front: 4 .+, power 7$/);
    const w = g.player[0].items.weapon[0];
    expect([w.id, w.power, g.shotMultiPos[0]]).toEqual([4, 7, 0]);
    expect(g.player[0].lives.value).toBe(7); // lives alias the front power (JE_initPlayerData)
    expect(out("power 11")).toEqual(["out: front power 11"]);
    expect(out("power 12")[0]).toMatch(/^err: power must be/);
    expect(out("weapon front 99")[0]).toMatch(/^err: weapon id must be/);
    // The sim fires it: the next ticks make shots.
    simInput.fire = true;
    let fired = false;
    for (let t = 0; t < 20 && !fired; t++) {
      tick();
      fired = g.shotAvail.some((s) => s !== 0);
    }
    expect(fired).toBe(true);
  });

  test("a sidekick is set up by JE_drawOptions (its ammo from the item data)", () => {
    expect(out("sidekick left 9")[0]).toMatch(/^out: left: 9 /);
    expect(g.player[0].items.sidekick[0]).toBe(9);
    expect(g.player[0].sidekick[0].ammo).toBe(g.res.items.options[9].ammo);
  });

  test("kill destroys what's on screen the way a shot does; skip finishes the level as completed", () => {
    let killed = "";
    for (let t = 0; t < 2000 && !killed; t++) {
      g.player[0].invulnerable_ticks = 2;
      tick();
      const before = g.enemyKilled;
      const line = out("kill")[0];
      if (g.enemyKilled > before) killed = line;
    }
    expect(killed).toMatch(/^out: \d+ destroyed$/);
    expect(out("skip")).toEqual(["out: level ends in 40 ticks"]);
    let r = tick();
    for (let t = 0; t < 400 && !r.levelOver; t++) r = tick();
    expect(r.levelOver).toBe(true);
    expect(r.completed).toBe(true);
  });
});

// --- the shop's lists (D110) ---

const HAVE_SHOP = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "levels2.dat", "levels3.dat", "levels4.dat", "tyrian1.lvl", "palette.dat", "newsh1.shp");

/** A one-player game in episode 1 with `cash`, as tests/sim/shop.test.ts sets one up. */
function shopGame(cash: number): void {
  mt_srand(1);
  if (!g.res || g.episodeNum !== 1) g.res = buildResources(files, 1);
  g.episodeNum = 1;
  loadHelpText(readData("tyrian.hdt"));
  JE_initPlayerData();
  Object.assign(g, { playDemo: false, jumpSection: false, onePlayerAction: false, twoPlayerMode: false, superTyrian: false, constantPlay: false, gameLoaded: true, cubeMax: 0, mapPNum: 0 });
  g.player[0].cash = cash;
}

/** Run the item screen of episode 1's section `section`, `drive` playing it (it must leave it). */
function inItemScreen(section: number, drive: () => void): void {
  loadLevel(files, 1, section, () => {
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
/** Open category `sel`'s list (2 ship .. 8 right sidekick) through Upgrade Ship, from wherever the screen is. */
const openList = (sel: number) => {
  while (menu.curMenu !== MENU_FULL_GAME) press("esc");
  menu.curSel[MENU_FULL_GAME] = 4; // Upgrade Ship
  press("enter");
  menu.curSel[MENU_UPGRADES] = sel;
  press("enter");
};
/** Out of the screen: back to the main menu, Play Next Level, its first destination. */
const leave = () => {
  while (menu.curMenu !== MENU_FULL_GAME) press("esc");
  menu.curSel[MENU_FULL_GAME] = 6;
  press("enter", "enter");
};
const listed = () => itemScreenEntries().filter((e) => !e.done).map((e) => e.item);
const rows = () => g.itemAvail.map((r, i) => r.slice(0, g.itemAvailMax[i]));
const category = (k: string) => findCategory(k)!;

describe("shop lists: the command line", () => {
  test("categories by the shop's names and short aliases", () => {
    expect(SHOP_CATEGORIES.map((c) => [c.key, c.sel, c.row])).toEqual([
      ["ships", 2, 0],
      ["front", 3, 1],
      ["rear", 4, 2],
      ["shields", 5, 8],
      ["generators", 6, 3],
      ["left", 7, 5],
      ["right", 8, 6],
    ]);
    for (const [w, k] of [["ship", "ships"], ["FRONT-GUNS", "front"], ["front gun", "front"], ["f", "front"], ["reargun", "rear"], ["shield", "shields"], ["gen", "generators"], ["generator", "generators"], ["ls", "left"], ["left-sidekick", "left"], ["rs", "right"], ["Right Sidekick", "right"]])
      expect(findCategory(w)?.key, w).toBe(k);
    expect(findCategory("hat")).toBeUndefined();
  });

  test("Tab completes the subcommands, categories and item ids and names", () => {
    const cmds = createCommands();
    expect(completeLine(cmds, "shop a")).toEqual({ line: "shop a", options: ["add", "all"] });
    expect(completeLine(cmds, "shop all o")).toEqual({ line: "shop all o", options: ["off", "on"] });
    expect(completeLine(cmds, "shop set fr")).toEqual({ line: "shop set front ", options: [] });
    expect(completeLine(cmds, "shop items g")).toEqual({ line: "shop items generators ", options: [] });
  });
});

describe.skipIf(!HAVE_SHOP)("shop lists: what the real game sells (shop all)", () => {
  beforeEach(() => shopGame(0));

  test("the union of every item screen in episodes 1-4: non-empty, in each category's range, sorted as the shop sorts", () => {
    const s = soldEverywhere(files);
    expect(s.episodes).toEqual([1, 2, 3, 4]);
    expect(s.screens).toBe(16 + 11 + 12 + 22);
    expect(s.dropped).toEqual([]);
    const counts = Object.fromEntries(SHOP_CATEGORIES.map((c) => [c.key, s.lists[c.key].length]));
    expect(counts).toEqual({ ships: 9, front: 18, rear: 13, shields: 9, generators: 6, left: 23, right: 30 });
    for (const c of SHOP_CATEGORIES) {
      const l = s.lists[c.key];
      expect(l.length, c.key).toBeGreaterThan(0);
      for (const id of l) expect(id >= c.min && id <= c.max, `${c.key} ${id}`).toBe(true);
      expect(new Set(l).size).toBe(l.length);
      expect(l.filter((x) => x !== 0)).toEqual([...l.filter((x) => x !== 0)].sort((a, b) => a - b));
      if (l.includes(0)) expect(l.at(-1)).toBe(0); // None last, as the merchant sorts
    }
    // Nothing the game never sells: no front "None", no ship no screen sells (Stalker, U-Ship,
    // Silver, Nort), no internal, joke or Nort guns, no Quicksilver, no HXS Class C.
    expect(s.lists.front).not.toContain(0);
    for (const id of [8, 10, 11, 12]) expect(s.lists.ships).not.toContain(id);
    for (const id of [16, 23, 24, 25, 26, 36, 37, 38, 39]) {
      expect(s.lists.front).not.toContain(id);
      expect(s.lists.rear).not.toContain(id);
    }
    expect(s.lists.left).not.toContain(24);
    expect(s.lists.right).not.toContain(24);
    expect(s.lists.shields).not.toContain(10);
    // The right sidekicks include the front-firing ones only the right side is sold.
    for (const id of [20, 22, 23, 25, 26, 27, 28]) {
      expect(s.lists.right).toContain(id);
      expect(s.lists.left).not.toContain(id);
    }
  });

  test("the lists are the sim's own: each item screen's itemAvail as the sim loads it at its ]I[", () => {
    const screens = itemScreenLists(readData("levels1.dat"));
    const script = parseEpisodeScript(readData("levels1.dat"));
    const withShop = script.sections.filter((sec) => sec.lines.some((l) => l.startsWith("]I[")));
    expect(withShop).toHaveLength(screens.length);
    for (const [k, sec] of withShop.entries()) {
      if (!sec.lines.some((l) => l.startsWith("]G["))) continue; // no destinations of its own
      shopGame(0);
      let seen: number[][] | null = null;
      loadLevel(files, 1, sec.number, () => {
        seen ??= rows(); // before JE_itemScreen_init adds the loadout
        JE_itemScreenNonInteractive();
      });
      expect(seen, `section ${sec.number}`).toEqual(screens[k]);
    }
  });
});

describe.skipIf(!HAVE_SHOP)("shop lists in the item screen", () => {
  const cmds = createCommands();
  let ctx: ConsoleCtx;
  const out = (line: string) => runLine(cmds, line, ctx).map((l) => `${l.kind}: ${l.text}`);
  beforeEach(() => {
    shopGame(1_000_000);
    ctx = ctxFor("shop").ctx;
  });
  afterEach(() => resetShopLists(false));

  test("shop all sells the union in every list, and buying from it is a normal purchase; off restores the level's lists exactly", () => {
    const union = soldEverywhere(files).lists;
    inItemScreen(2, () => {
      const level = rows().map((r) => [...r]);
      openList(3);
      const own = listed();
      expect(own).toEqual([1, 2, 7, 13]); // section 2's WeapF 13 2 7 and the Pulse-Cannon
      expect(out("shop all")).toEqual(["out: shop all: off (the level's lists)"]);
      expect(out("shop all on")[0]).toMatch(/^out: shop all: on\. Every list is the union of 61 item screens in episodes 1, 2, 3, 4:$/);
      // Still in the front gun list, now the union's (the Pulse-Cannon is in it).
      expect(menu.curMenu).toBe(MENU_UPGRADE_SUB);
      expect(listed()).toEqual(union.front);
      expect(itemScreenEntries().find((e) => e.item === 1)?.owned).toBe(true);
      expect(menu.curSel[MENU_UPGRADE_SUB]).toBe(2); // on the owned Pulse-Cannon
      expect(rows()).toEqual(level); // the level's lists untouched

      // Buy the Widget Beam (40, sold only in episode 4) the way a player does: click it twice, then Done.
      const widget = itemScreenEntries().find((e) => e.item === 40)!;
      const cost = widget.cost!;
      JE_itemScreen_mouse(widget.sel);
      JE_itemScreen_update();
      expect(g.player[0].items.weapon[0].id).toBe(40); // previewed
      JE_itemScreen_mouse(widget.sel);
      JE_itemScreen_update();
      press("enter"); // Done
      expect(menu.curMenu).toBe(MENU_UPGRADES);
      expect(g.player[0].items.weapon[0]).toEqual({ id: 40, power: 1 });
      expect(g.player[0].cash).toBe(1_000_000 + JE_getValue(3, 1) - cost);

      // Every other category sells the union too.
      for (const c of SHOP_CATEGORIES) expect(offered(c)).toEqual(merchantOrderOf([...union[c.key], playerItemOf(c.sel)]));

      expect(out("shop all off")).toEqual(["out: shop all: off; the level's own lists"]);
      expect(rows()).toEqual(level);
      openList(3);
      expect(listed()).toEqual([1, 2, 7, 13]); // the level's again (the Widget Beam comes with the next screen's last_items)
      leave();
    });
  });

  test("set, add, remove and clear edit one list; the shop shows the player's own item too", () => {
    inItemScreen(2, () => {
      expect(out("shop set front 40 zica-laser 3")).toEqual(["out: front (3): 3 Mega Cannon · 5 Zica Laser · 40 Widget Beam", "out: the shop still lists 1 Pulse-Cannon, what you have"]);
      openList(3);
      expect(listed()).toEqual([1, 3, 5, 40]);
      expect(out("shop add f 41 42")).toEqual(["out: front (5): 3 Mega Cannon · 5 Zica Laser · 40 Widget Beam · 41 Sonic Impulse · 42 RetroBall", "out: the shop still lists 1 Pulse-Cannon, what you have"]);
      expect(listed()).toEqual([1, 3, 5, 40, 41, 42]);
      expect(out("shop remove front 5 retroball")[0]).toBe("out: front (3): 3 Mega Cannon · 40 Widget Beam · 41 Sonic Impulse");
      expect(listed()).toEqual([1, 3, 40, 41]);
      expect(out("shop clear front")[0]).toBe("out: front (0): (nothing)");
      expect(listed()).toEqual([1]);
      expect(out("shop list front")).toEqual([`out: ${categoryLabel(category("front"))} (front), edited list: 1 item`, "out:   1  Pulse-Cannon                    500  (yours)"]);
      // Not sold anywhere: allowed, and said so.
      expect(out("shop set rear 24")).toEqual(["out: rear (1): 24 Banana Blast Rear", "out: not sold here in the real game: 24 Banana Blast Rear", "out: the shop still lists 0 None, what you have"]);
      // Two Vulcan Cannons: the rear list takes the one sold as a rear gun; the front list sells both.
      expect(out("shop set rear vulcan")[0]).toBe("out: rear (1): 15 Vulcan Cannon");
      expect(out("shop set front vulcan")[0]).toBe('err: front: "vulcan" could be 7 Vulcan Cannon, 15 Vulcan Cannon: use the id');
      expect(out("shop set front 0")[0]).toBe("err: front: ids are 1-42 (`shop items front` lists them)");
      expect(out("shop set hats 1")[0]).toMatch(/^err: no category "hats": one of ships, front/);
      expect(out("shop set front")[0]).toBe("err: usage: shop set <category> <id|name…>");
      expect(out("shop all")).toEqual(["out: shop all: off; console lists for front, rear"]);
      expect(out("shop reset front")).toEqual(["out: front: the level's own list"]);
      expect(listed()).toEqual([1, 2, 7, 13]);
      expect(out("shop reset")).toEqual(["out: the level's own lists; shop all off"]);
      leave();
    });
  });

  test("the lists last through the next item screens until shop reset; items lists the ids to pick from", () => {
    const title = ctxFor("title").ctx;
    expect(runLine(cmds, "shop set front 40", title).map((l) => l.text)[0]).toBe("front (1): 40 Widget Beam (from the next item screen on)");
    ctx = ctxFor("shop").ctx;
    for (const section of [2, 4]) {
      inItemScreen(section, () => {
        openList(3);
        expect(listed(), `section ${section}`).toEqual([1, 40]);
        leave();
      });
    }
    const items = out("shop items front zica");
    expect(items).toEqual([expect.stringMatching(/^out: .+ \(front\): ids 1-42; · = no shop in the game sells it here$/), "out:    5  Zica Laser                     1100"]);
    expect(out("shop items front").length).toBe(1 + 42);
    expect(out("shop items front").filter((l) => /^out: ·/.test(l)).length).toBe(42 - 18);
    resetShopLists(false);
    inItemScreen(4, () => {
      openList(3);
      expect(listed()).toEqual([1, 2, 13, 17]);
      leave();
    });
  });

  test("Tab completes item names and ids; help shop lists the subcommands", () => {
    expect(completeLine(cmds, "shop add front zica")).toEqual({ line: "shop add front zica-laser ", options: [] });
    expect(completeLine(cmds, "shop set rs beno-")).toEqual({ line: "shop set rs beno-", options: ["beno-protron-system-b", "beno-wallop-beam"] });
    expect(completeLine(cmds, "shop set shields 1").options).toEqual(["1", "10"]);
    const help = out("help shop");
    expect(help[0]).toMatch(/^out: shop \[episode\] \| all \[on\|off\]/);
    for (const sub of ["all", "list", "items", "set", "add|remove", "clear", "reset"]) expect(help.some((l) => l.startsWith(`out: shop ${sub}`)), sub).toBe(true);
  });

  test("a long list: every row reachable with the keys, the cursor wrapping at both ends", () => {
    inItemScreen(2, () => {
      out("shop all on");
      openList(8); // right sidekicks: 30 and Done
      const n = menu.menuChoices[MENU_UPGRADE_SUB];
      expect(n).toBe(30 + 2);
      const seen = new Set<number>();
      for (let i = 0; i < n; i++) {
        seen.add(menu.curSel[MENU_UPGRADE_SUB]);
        press("down");
      }
      expect(seen.size).toBe(n - 1); // every row 2..n
      press("up");
      expect(menu.curSel[MENU_UPGRADE_SUB]).toBeGreaterThanOrEqual(2);
      leave();
    });
  });
});

/** The merchant's order, for expectations. */
const merchantOrderOf = (ids: number[]) => {
  const all = [...new Set(ids)];
  return [...all.filter((x) => x !== 0).sort((a, b) => a - b), ...all.filter((x) => x === 0)];
};
/** The player's item in Upgrade Ship category `sel`. */
const playerItemOf = (sel: number) => {
  const it = g.player[0].items;
  return [it.ship, it.weapon[0].id, it.weapon[1].id, it.shield, it.generator, it.sidekick[0], it.sidekick[1]][sel - 2];
};
