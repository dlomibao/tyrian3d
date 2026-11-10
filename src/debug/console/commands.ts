// The debug console's commands (D109). Each reuses what the game already has: the cheats act on the
// sim through its own functions (cheats.ts), the settings go through the same DisplayChoice /
// terrain style / music and sound style setters as Options (and are saved by savePrefs, as Options
// saves them), the URL-only looks (?vfx, ?sprites, ?bg) switch live in the renderer, and the level
// jumps hand the game flow (src/app/run.ts) an episode-script section through consoleBridge, or in
// the shop set the sim's own jump (mainLevel with jumpSection, or gameLoaded for another episode,
// as loading a game from the shop does).

import { CheatError, heal, killAll, POWER_MAX, setArmor, setCredits, setGod, setPower, setShield, setSidekick, setWeapon, sidekickName, skipLevel, weaponName } from "./cheats";
import { findCommand, helpLines, tokenize, type CommandSpec } from "./parse";
import { hasItemScreen, listLevels, resolveLevel, shopSectionFor, type ConsoleLevel } from "./levels";
import { parseEpisodeScript, type EpisodeScript } from "../../data/episodeScript";
import { OPTION_NUM, PORT_NUM } from "../../data/items";
import type { ConsoleBridge } from "../../app/consoleBridge";
import { cameraStyle, interfaceStyle, resolutionStyle, type DisplayChoice } from "../../core/displayStyle";
import { DEFAULT_TERRAIN_STYLE, loadTerrainStyle, setTerrainStyle, TERRAIN_STYLES, terrainStyle, type TerrainStyle } from "../../core/terrainStyle";
import { savePrefs } from "../../app/prefs";
import { DEFAULT_MUSIC_STYLE } from "../../audio/remaster";
import { DEFAULT_VFX_MODE } from "../../render/vfx/vfxMode";
import { JE_initEpisode } from "../../sim/episodes";
import { mt_srand } from "../../sim/mtrand";
import { FRONT_WEAPON, g, REAR_WEAPON } from "../../sim/state";

/** What a command can do besides printing: the console's own actions. */
export interface ConsoleCtx {
  bridge: ConsoleBridge;
  /** Close the console (the game resumes, or the menu under it takes the input back). */
  close(): void;
  /** Empty the scrollback. */
  clear(): void;
  /** Whether the console is right over the screen a jump has to close (ConsoleBridge.leave). */
  overLeaveScreen(): boolean;
  /** The perf overlay: on or off. */
  perf: { get(): boolean; set(on: boolean): void };
}

/** A command's output: a line, lines, or nothing. Errors are thrown (UsageError, CheatError). */
export type Output = string | string[] | void;

export interface Command extends CommandSpec {
  run(args: string[], ctx: ConsoleCtx): Output;
}

/** A command used wrongly, or where it can't act: shown as an error line. */
export class UsageError extends Error {}

const usage = (c: CommandSpec) => new UsageError(`usage: ${c.name} ${c.usage}`);
const fail = (msg: string) => new UsageError(msg);

function num(s: string | undefined, what: string): number {
  const v = Number(s);
  if (s === undefined || s.trim() === "" || !Number.isFinite(v)) throw fail(`${what}: "${s ?? ""}" is not a number`);
  return v;
}

/** A game is going on (in a level or the shop between levels): the cheats have a player to act on. */
function needGame(ctx: ConsoleCtx): void {
  if (ctx.bridge.place !== "level" && ctx.bridge.place !== "shop") throw fail("start a game first: this works in a level or the shop");
}
function needLevel(ctx: ConsoleCtx): void {
  if (ctx.bridge.place !== "level") throw fail("only in a level");
}

/** Episodes whose data is here (levelsN.dat and tyrianN.lvl). */
function episodes(b: ConsoleBridge): number[] {
  return [1, 2, 3, 4, 5].filter((n) => b.files?.get(`levels${n}.dat`) && b.files?.get(`tyrian${n}.lvl`));
}

const scripts = new Map<number, EpisodeScript>();
function scriptOf(b: ConsoleBridge, episode: number): EpisodeScript {
  const data = b.files?.get(`levels${episode}.dat`);
  if (!data || !episodes(b).includes(episode)) throw fail(`no episode ${episode} here (have ${episodes(b).join(", ") || "none"})`);
  let s = scripts.get(episode);
  if (!s) scripts.set(episode, (s = parseEpisodeScript(data)));
  return s;
}

/** The episode the console means without one given: the game's, else 1. */
const currentEpisode = () => (g.episodeNum >= 1 && g.episodeNum <= 5 ? g.episodeNum : 1);

/** A level's names as one completable word each (`sohjin`). */
const levelWords = (levels: ConsoleLevel[]) => levels.flatMap((l) => l.names.map((n) => n.toLowerCase().replace(/[^a-z0-9]/g, ""))).filter(Boolean);

/**
 * Go to `section` of `episode` (null: the episode's start, its first item screen), from wherever the
 * console is. Returns the line to show.
 */
function jumpTo(ctx: ConsoleCtx, episode: number, section: number | null, what: string): string {
  const b = ctx.bridge;
  if (b.place === "menu") throw fail("not from this screen: open the console in a level, the shop or the title");
  if (!ctx.overLeaveScreen()) throw fail("close the menu on top first (the console has to be right over the title, the pause screen or the shop)");
  if (b.place === "shop") {
    if (section === null) throw fail("already in the shop");
    // The sim's own ways out of the item screen: the map's choice (mainLevel, jumpSection), or a
    // game loaded from it (gameLoaded: JE_loadMap goes back to new_game, in the episode now set).
    if (episode !== g.episodeNum && b.files) {
      JE_initEpisode(episode, b.files);
      b.view?.setPalettes(g.res.palettes);
      g.mainLevel = section;
      g.gameLoaded = true;
    } else {
      g.mainLevel = section;
      g.jumpSection = true;
    }
  } else {
    b.jump = { episode, section };
  }
  ctx.close();
  if (b.leave?.screen.open) b.leave.go();
  return `→ ${what}`;
}

/** A setting with a few values: no argument shows it, one sets it. */
function choiceCommand(
  name: string,
  help: string,
  values: () => readonly string[],
  get: () => string,
  set: (v: string) => void,
  note = "",
): Command {
  return {
    name,
    get usage() {
      return `[${values().join("|")}]`;
    },
    help,
    complete: (i) => (i === 0 ? values() : []),
    run(args) {
      const vs = values();
      if (!args.length) return `${name}: ${get()}  (${vs.join(" | ")})${note}`;
      const v = vs.find((x) => x.toLowerCase() === args[0].toLowerCase());
      if (!v) throw fail(`${name}: "${args[0]}" isn't one of ${vs.join(", ")}`);
      set(v);
      return `${name}: ${get()}${note}`;
    },
  };
}

/** A setting kept as a DisplayChoice (Options' Graphics rows): set it and save the prefs, as Options does. */
const displayCommand = <T extends string>(name: string, choice: DisplayChoice<T>, help: string) =>
  choiceCommand(
    name,
    help,
    () => choice.values,
    () => choice.get(),
    (v) => {
      if (choice.is(v)) choice.set(v);
      savePrefs();
    },
  );

/** The console's commands, in `help` order. */
export function createCommands(): Command[] {
  const cmds: Command[] = [];
  const add = (c: Command) => (cmds.push(c), c);

  // --- the console ---
  add({
    name: "help",
    aliases: ["?"],
    usage: "[command]",
    help: "list the commands, or one command's arguments",
    complete: (i) => (i === 0 ? cmds.map((c) => c.name) : []),
    run(args) {
      if (args.length) {
        const c = findCommand(cmds, args[0]);
        if (!c) throw fail(`no command "${args[0]}"`);
        return helpLines([c]);
      }
      return [...helpLines(cmds), "Tab completes, Up/Down go through the history, ` (backtick) or Esc closes."];
    },
  });
  add({ name: "clear", aliases: ["cls"], usage: "", help: "empty the console", run: (_a, ctx) => ctx.clear() });
  add({ name: "close", aliases: ["exit", "quit"], usage: "", help: "close the console", run: (_a, ctx) => ctx.close() });

  // --- cheats ---
  const onOff = (s: string | undefined, now: boolean) => {
    if (s === undefined) return !now;
    if (/^(on|1|true|yes)$/i.test(s)) return true;
    if (/^(off|0|false|no)$/i.test(s)) return false;
    throw fail(`"${s}": on or off`);
  };
  add({
    name: "god",
    usage: "[on|off]",
    help: "invulnerability: the original's cheat (F2 F3 F6), toggled",
    complete: (i) => (i === 0 ? ["on", "off"] : []),
    run(args, ctx) {
      needGame(ctx);
      return `god mode ${setGod(onOff(args[0], g.youAreCheating)) ? "on" : "off"}`;
    },
  });
  add({
    name: "armor",
    aliases: ["armour"],
    usage: "[N]",
    help: "show or set the armour (0-28, the game's cap)",
    run(args, ctx) {
      needLevel(ctx);
      if (!args.length) return `armor ${g.player[0].armor} of ${g.player[0].initial_armor}`;
      return `armor ${setArmor(num(args[0], "armor"))}`;
    },
  });
  add({
    name: "shield",
    usage: "[N]",
    help: "show or set the shield (up to its maximum)",
    run(args, ctx) {
      needLevel(ctx);
      const p = g.player[0];
      if (!args.length) return `shield ${p.shield} of ${p.shield_max}`;
      return `shield ${setShield(num(args[0], "shield"))} of ${p.shield_max}`;
    },
  });
  add({
    name: "heal",
    usage: "",
    help: "full armour and shield",
    run(_a, ctx) {
      needLevel(ctx);
      const r = heal();
      return `armor ${r.armor}, shield ${r.shield}`;
    },
  });
  add({
    name: "credits",
    aliases: ["cash"],
    usage: "[N]",
    help: "show or set the credits",
    run(args, ctx) {
      needGame(ctx);
      if (!args.length) return `credits ${g.player[0].cash}`;
      return `credits ${setCredits(num(args[0], "credits"))}`;
    },
  });
  const portLine = (port: "front" | "rear") => {
    const w = g.player[0].items.weapon[port === "front" ? FRONT_WEAPON : REAR_WEAPON];
    return `${port}: ${w.id} ${weaponName(w.id)}, power ${w.power}`;
  };
  add({
    name: "weapon",
    usage: "front|rear [id [power]]",
    help: `show or fit a gun (id 0-${PORT_NUM}, see \`weapons\`; power 1-${POWER_MAX})`,
    complete: (i) => (i === 0 ? ["front", "rear"] : []),
    run(args, ctx) {
      needGame(ctx);
      if (!args.length) return [portLine("front"), portLine("rear")];
      const port = args[0].toLowerCase();
      if (port !== "front" && port !== "rear") throw usage(this);
      if (args.length === 1) return portLine(port);
      const w = setWeapon(port, num(args[1], "id"), args[2] === undefined ? undefined : num(args[2], "power"));
      return `${port}: ${w.id} ${w.name}, power ${w.power}`;
    },
  });
  add({
    name: "weapons",
    usage: "",
    help: "list the guns' ids (this episode's item data)",
    run(_a, ctx) {
      needGame(ctx);
      return Array.from({ length: PORT_NUM }, (_, i) => `${String(i + 1).padStart(3)}  ${weaponName(i + 1)}`);
    },
  });
  add({
    name: "power",
    usage: "[N] [front|rear]",
    help: `show or set a gun's power (1-${POWER_MAX}; the front one unless rear is given)`,
    complete: (i) => (i === 1 ? ["front", "rear"] : []),
    run(args, ctx) {
      needGame(ctx);
      if (!args.length) return [portLine("front"), portLine("rear")];
      const port = (args[1] ?? "front").toLowerCase();
      if (port !== "front" && port !== "rear") throw usage(this);
      return `${port} power ${setPower(num(args[0], "power"), port)}`;
    },
  });
  add({
    name: "sidekick",
    usage: "left|right [id]",
    help: `show or fit a sidekick (id 0-${OPTION_NUM}, see \`sidekicks\`)`,
    complete: (i) => (i === 0 ? ["left", "right"] : []),
    run(args, ctx) {
      needGame(ctx);
      const sk = g.player[0].items.sidekick;
      if (!args.length) return [`left: ${sk[0]} ${sidekickName(sk[0])}`, `right: ${sk[1]} ${sidekickName(sk[1])}`];
      const side = args[0].toLowerCase();
      if (side !== "left" && side !== "right") throw usage(this);
      if (args.length === 1) return `${side}: ${sk[side === "left" ? 0 : 1]} ${sidekickName(sk[side === "left" ? 0 : 1])}`;
      const r = setSidekick(side, num(args[1], "id"));
      return `${side}: ${r.id} ${r.name}`;
    },
  });
  add({
    name: "sidekicks",
    usage: "",
    help: "list the sidekicks' ids",
    run(_a, ctx) {
      needGame(ctx);
      return Array.from({ length: OPTION_NUM }, (_, i) => `${String(i + 1).padStart(3)}  ${sidekickName(i + 1)}`);
    },
  });
  add({
    name: "kill",
    usage: "",
    help: "destroy every enemy on screen (not the indestructible ones or pickups)",
    run(_a, ctx) {
      needLevel(ctx);
      const n = killAll();
      return n ? `${n} destroyed` : "nothing on screen to destroy";
    },
  });

  // --- levels ---
  add({
    name: "levels",
    usage: "[episode]",
    help: "list an episode's levels: number, name, section",
    complete: (i, _a) => (i === 0 ? ["1", "2", "3", "4"] : []),
    run(args, ctx) {
      const ep = args.length ? num(args[0], "episode") : currentEpisode();
      const levels = listLevels(scriptOf(ctx.bridge, ep));
      const here = ctx.bridge.place === "level" && ep === g.episodeNum ? g.mainLevel : -1;
      return [
        `episode ${ep} (s = section, the harness's main=; lvl = tyrian${ep}.lvl's level):`,
        ...levels.map(
          (l) =>
            `${l.section === here ? ">" : " "}${String(l.number).padStart(2)} ${l.name.padEnd(10)} s${String(l.section).padEnd(3)} lvl ${l.lvlFileNums.join("/")}${l.bonus ? " bonus" : ""}`,
        ),
      ];
    },
  });
  add({
    name: "level",
    aliases: ["goto"],
    usage: "[episode] <number|name|s<section>>",
    help: "jump to a level (numbers as `levels` lists them; the harness's main= is the section)",
    complete(i, args) {
      const b = bridge();
      const eps = b ? episodes(b).map(String) : [];
      try {
        if (i === 0) return [...eps, ...(b ? levelWords(listLevels(scriptOf(b, currentEpisode()))) : [])];
        if (i === 1 && eps.includes(args[0]) && b) return levelWords(listLevels(scriptOf(b, Number(args[0]))));
      } catch {
        /* no data */
      }
      return [];
    },
    run(args, ctx) {
      if (!args.length) throw usage(this);
      const b = ctx.bridge;
      const eps = episodes(b).map(String);
      const [ep, rest] = args.length >= 2 && eps.includes(args[0]) ? [Number(args[0]), args.slice(1).join(" ")] : [currentEpisode(), args.join(" ")];
      const script = scriptOf(b, ep);
      const t = resolveLevel(script, listLevels(script), rest);
      if ("error" in t) throw fail(t.error);
      const what = t.level ? `episode ${ep}, level ${t.level.number} ${t.level.name} (section ${t.section})` : `episode ${ep}, section ${t.section}`;
      return [...(t.note ? [t.note] : []), jumpTo(ctx, ep, t.section, what)];
    },
  });
  add({
    name: "skip",
    aliases: ["next"],
    usage: "",
    help: "finish this level (the original's skip-level cheat), then on to the next",
    run(_a, ctx) {
      needLevel(ctx);
      if (!ctx.overLeaveScreen()) throw fail("close the menu on top first");
      skipLevel();
      ctx.close();
      if (ctx.bridge.leave?.screen.open) ctx.bridge.leave.go();
      return "level ends in 40 ticks";
    },
  });
  add({
    name: "shop",
    usage: "[episode]",
    help: "to the item screen before this level (from the title: a new game's first)",
    complete: (i) => (i === 0 ? ["1", "2", "3", "4"] : []),
    run(args, ctx) {
      const b = ctx.bridge;
      if (b.place === "shop") throw fail("already in the shop");
      if (b.place === "title") {
        const ep = args.length ? num(args[0], "episode") : 0;
        if (ep) scriptOf(b, ep); // is it here?
        return jumpTo(ctx, ep, null, ep ? `a new game of episode ${ep}` : "a new game");
      }
      needLevel(ctx);
      const script = scriptOf(b, g.episodeNum);
      const section = shopSectionFor(script, g.mainLevel) ?? (hasItemScreen(script, g.saveLevel) ? g.saveLevel : null);
      if (section === null) throw fail(`no item screen leads to section ${g.mainLevel}; try \`level s<section>\``);
      return jumpTo(ctx, g.episodeNum, section, `the item screen (episode ${g.episodeNum}, section ${section})`);
    },
  });

  // --- settings and looks ---
  add(
    choiceCommand(
      "terrain",
      "HD terrain paintings or the original's (Options → Terrain, saved)",
      () => TERRAIN_STYLES,
      () => terrainStyle(),
      (v) => {
        setTerrainStyle(v as TerrainStyle);
        savePrefs();
      },
    ),
  );
  add(displayCommand("camera", cameraStyle, "the game camera (Options → Camera, saved)"));
  add(displayCommand("interface", interfaceStyle, "the in-game HUD (Options → Interface, saved)"));
  add(displayCommand("resolution", resolutionStyle, "dynamic or full resolution (Options → Resolution, saved)"));
  const view = () => bridge()?.view ?? null;
  add(
    choiceCommand(
      "vfx",
      "shots and explosions: remastered effects or the original sprites (?vfx=, this page only)",
      () => ["remastered", "original"],
      () => view()?.draws.vfxMode ?? "?",
      (v) => view()?.draws.setVfxMode(v as "remastered" | "original"),
    ),
  );
  add(
    choiceCommand(
      "sprites",
      "shots and pickups: flat art or the original sprites (?sprites=, this page only)",
      () => ["remastered", "original"],
      () => view()?.draws.spriteArtMode ?? "?",
      (v) => view()?.draws.setSpriteArtMode(v as "remastered" | "original"),
    ),
  );
  add(
    choiceCommand(
      "bg",
      "backgrounds: remastered (models, upscaled ground) or the original tiles (?bg=, this page only; structures already placed keep theirs)",
      () => ["remaster", "original"],
      () => view()?.draws.backgroundStyle ?? "?",
      (v) => view()?.draws.setBackgroundStyle(v as "remaster" | "original"),
    ),
  );
  add(
    choiceCommand(
      "music",
      "the music style (Options → Music style; remaster packs add styles)",
      () => bridge()?.host?.music.styles ?? ["original"],
      () => bridge()?.host?.music.style ?? "original",
      (v) => bridge()?.host?.music.setStyle?.(v),
    ),
  );
  add(
    choiceCommand(
      "sound",
      "the sound-effect style (Options → Sound style; remaster packs add styles)",
      () => bridge()?.host?.sfx.styles ?? ["original"],
      () => bridge()?.host?.sfx.style ?? "original",
      (v) => bridge()?.host?.sfx.setStyle(v),
    ),
  );
  add({
    name: "fps",
    aliases: ["perf"],
    usage: "[on|off]",
    help: "the frame-rate and tick overlay, toggled (kept in this browser)",
    complete: (i) => (i === 0 ? ["on", "off"] : []),
    run(args, ctx) {
      const on = onOff(args[0], ctx.perf.get());
      ctx.perf.set(on);
      return `perf overlay ${on ? "on" : "off"}`;
    },
  });
  add({
    name: "tick",
    usage: "",
    help: "the tick count in this level",
    run(_a, ctx) {
      return ctx.bridge.place === "level" ? `tick ${ctx.bridge.ticks}` : `no level running (the last one ran ${ctx.bridge.ticks} ticks)`;
    },
  });
  add({
    name: "speed",
    usage: "[N]",
    help: "sim speed, 0-8 (0 freezes; the ticks stay fixed, more or fewer of them run)",
    run(args, ctx) {
      if (!args.length) return `speed ${ctx.bridge.speed}`;
      const v = num(args[0], "speed");
      if (v < 0 || v > 8) throw fail("speed: 0 to 8");
      ctx.bridge.speed = v;
      return `speed ${v}`;
    },
  });
  add({
    name: "seed",
    usage: "[N]",
    help: "the random seed: show it, or reseed mt_rand now (?seed=N fixes a page's start)",
    run(args, ctx) {
      if (!args.length) return `seed ${ctx.bridge.seed}`;
      if (!/^\d+$/.test(args[0])) throw fail("seed: a whole number");
      const seed = Number(args[0]) >>> 0;
      mt_srand(seed);
      ctx.bridge.seed = seed;
      return `reseeded with ${seed}`;
    },
  });
  add({
    name: "reset",
    usage: "",
    help: "settings and looks back to their defaults (terrain, camera, interface, resolution, looks, styles, speed, overlay)",
    run(_a, ctx) {
      loadTerrainStyle(undefined);
      for (const c of [cameraStyle, interfaceStyle, resolutionStyle] as DisplayChoice<string>[]) c.load(undefined);
      savePrefs();
      const v = ctx.bridge.view;
      v?.draws.setVfxMode(DEFAULT_VFX_MODE);
      v?.draws.setSpriteArtMode(undefined);
      v?.draws.setBackgroundStyle("remaster");
      const music = ctx.bridge.host?.music;
      if (music?.styles?.includes(DEFAULT_MUSIC_STYLE)) music.setStyle?.(DEFAULT_MUSIC_STYLE);
      else music?.setStyle?.("original");
      ctx.bridge.host?.sfx.setStyle("original");
      ctx.bridge.speed = 1;
      ctx.perf.set(false);
      return `defaults: terrain ${DEFAULT_TERRAIN_STYLE}, camera ${cameraStyle.get()}, interface ${interfaceStyle.get()}, resolution ${resolutionStyle.get()}, vfx ${DEFAULT_VFX_MODE}, speed 1 (volumes and keys untouched)`;
    },
  });

  return cmds;
}

/** The bridge, for completion (which has no ctx); set by runLine. */
let lastBridge: ConsoleBridge | null = null;
const bridge = () => lastBridge;

export type LineKind = "cmd" | "out" | "err";

/** Run one line; returns what to print. Never throws: errors come back as "err" lines. */
export function runLine(cmds: readonly Command[], line: string, ctx: ConsoleCtx): { kind: LineKind; text: string }[] {
  lastBridge = ctx.bridge;
  const words = tokenize(line);
  if (!words.length) return [];
  const cmd = findCommand(cmds, words[0]);
  if (!cmd) return [{ kind: "err", text: `no command "${words[0]}" (\`help\` lists them)` }];
  try {
    const out = cmd.run(words.slice(1), ctx);
    const lines = out === undefined ? [] : Array.isArray(out) ? out : [out];
    return lines.map((text) => ({ kind: "out" as const, text }));
  } catch (err) {
    if (err instanceof UsageError || err instanceof CheatError) return [{ kind: "err", text: err.message }];
    console.error(err);
    return [{ kind: "err", text: `${cmd.name} failed: ${(err as Error)?.message ?? err}` }];
  }
}

/** For completion before any line has run. */
export function setCompletionBridge(b: ConsoleBridge): void {
  lastBridge = b;
}
