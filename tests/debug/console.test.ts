// The debug console (src/debug/console/, D109): its command line (words, completion, history), the
// level numbering and jumps (sections, not levels: the harness's main=), and its cheats acting on a
// real level through the sim's own functions.
import { beforeEach, describe, expect, test } from "vitest";
import { commonPrefix, completeLine, findCommand, helpLines, History, tokenize, type CommandSpec } from "../../src/debug/console/parse";
import { listLevels, navTargets, resolveLevel, shopSectionFor } from "../../src/debug/console/levels";
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
