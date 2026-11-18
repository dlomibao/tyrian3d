// The shared high-score list's plausibility data (server/scores/maxScores.json), computed offline
// from the game data: each episode's level graph (which level can follow which, through the story
// order, the item screen's next-level choices, the script's jumps and the in-level warps) and, per
// level, an upper bound on the score it can add and lower/upper bounds on how many sim ticks it
// lasts. The server (server/scores/lib/plausibility.mjs) checks a submitted run against it; there is
// no server-side replay.
//
//   MAX_SCORES_OUT=server/scores/maxScores.json npm run max-scores
//
// Every place the sim adds score (src/sim/), and how it is bounded here:
//
//  A. destroyEnemy (game.ts): a killed enemy's evalue, when 1 < evalue < 10000 (1 is a data cube).
//     evalue is JE_makeEnemy's value scaled by the difficulty level at spawn time (x0.75 .. x8,
//     capped at 10000). An enemy whose dlevel is -1 is "killed" twice (its damaged state), so it
//     counts twice. Its eenemydie drop is spawned on each death, and counted with it (recursively;
//     a drop chain that loops counts 10000 a link). Event 33 (and 45, arcade-only: after ENGAGE)
//     gives the enemies of one link number another drop: an event-spawned enemy gets the best drop
//     of the events for its link (or a link event 39 renames it to) at or after its spawn; an event
//     33 for link 0 also reaches up to 75 enemies not spawned by events (random, launched, dropped).
//  B. JE_playerCollide (mainint.ts), pick-ups (armor 0, scoreitem): evalue added as cash (coins and
//     gems, scaled like A); -1/-2 power-ups and the 30000 purple ball power up a weapon (its value
//     grows, see F) or pay 1000 when it's at full power; the purple ball also pays 100 (2500 when
//     galaga mode has spawned the dragonwing); 30001..32xxx weapon/sidekick/special pick-ups pay
//     250. 31001..32000 pay 250 on every tick of contact in a one-player full game (the C leaves
//     them on screen): a per-tick "contact farm" of 250 x 25 per tick where a level can spawn one
//     (in Tyrian 2.1: episode 1's BONUS, through drops, and the galaga levels, where JE_searchFor's
//     doubling can carry an enemy's value into that range). -5 (HOT DOG) swaps in weapons 25/26:
//     their value is counted (F).
//  C. power_up_weapon (player.ts): 1000 when the weapon is at full power (bounded with B).
//  D. Galaga mode (game.ts JE_main): +1000 per galagaLife threshold once the lives are full
//     (thresholds 10000, 20000, then every 25000 of cash): bounded on the server from the run's
//     cumulative cap (1000 per 25000, plus 2000). JE_searchFor doubles a searched enemy's evalue
//     in galaga mode, so in a galaga level every scoring enemy counts as 9999.
//  E. adjust_difficulty (end of each level) raises difficultyLevel with the score, and event 46
//     raises it within a level: the values in A/B depend on it. Bounds are given per starting
//     difficulty level 1..10 (with the level's own event-46 raises applied); the server walks the
//     path raising the difficulty from its own cumulative cap.
//  F. The high-score score is JE_totalScore: cash plus the value of the ship and gear. Shop trades
//     move cash into value at cost, except that a weapon upgrade's price is a 16-bit JE_word
//     (upgradeCost) while its value isn't: buying a level whose price wraps adds the wrapped
//     multiple of 65536 to the total. Bounded per run by the most the two weapon ports can hold
//     (itemSurplus). A free power-up adds the next level's value; since power only goes down in the
//     shop, the power-ups of one level add at most both ports' value from power 1 to 11 on the
//     costliest weapon (powerUpSlack, added to every level that can spawn a power-up), and each
//     pick-up also counts its 1000 consolation. HOT DOG adds weapons 25 and 26 at full power
//     (hotDog). ENGAGE (`]e[`) replaces the gear with its own: its value is added to the levels
//     after it (engage).
//  G. The starting total (initial_cash + the starting gear's value) per episode.
//  Nothing else adds to cash or to the gear's value in a one-player full game: end-of-level and
//  bonus screens give no cash (JE_endLevelAni only adjusts the difficulty), data cubes give none.
//  The shop's ship id > 90 (price 100) never appears in an item list (checked).
//
// What can't be counted once is a rate per tick, which the server multiplies by the level's claimed
// ticks (themselves bounded by wall time):
//  - random spawns (levelEnemy, each tick with chance (99 - levelEnemyFrequency) / 100): the server
//    uses a 6-sigma binomial bound on the count;
//  - enemy launchers (eLaunchType, every launchfreq ticks; event 31 can shorten launchfreq);
//  - event loops (a backward jump by events 38, 54, 57, 70, 71, 75 or the level timer): the spawns
//    in the loop's body, once per (body length / the fastest scroll speed) ticks.
// Each is a worst case (every random spawn and launch killed, every pick-up taken), so the bounds
// are loose, but safe.
//
// Ticks: the floor is the fewest ticks to reach the level's end (event 11, or event 36's
// ready-to-end) when the scroll runs at the fastest speed the level ever sets and every forward
// jump is taken at once; a level the player can end by dying (bonus levels) has no floor. The
// ceiling exists only for levels that can't stall (no backward jumps, no stop or zero-speed scroll
// events): their slowest scroll to the farthest end, x1.5 plus 1000 ticks.

import { episodeLevels, parseEpisodeScript, parseLevelFile, type EnemyDat, type EpisodeScript, type Level } from "../../src/data";
import { JE_totalScore } from "../../src/sim/mainint";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources, type TyrianFiles } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadHelpText } from "../../src/sim/helptext";
import { PORT_NUM } from "../../src/data/items";

/** Difficulty levels the bounds are given for: [d] for d = 1..10 ([0] unused, kept so index = d). */
export const DIFFICULTY_LEVELS = 10;

/** JE_makeEnemy's value scaling for difficultyLevel d. */
export function scaledValue(value: number, d: number): number {
  if (!(value > 1 && value < 10000)) return value;
  const f = (x: number) => Math.trunc(Math.fround(Math.fround(value) * Math.fround(x)));
  let v: number;
  switch (d) {
    case -1:
    case 0:
      v = f(0.75);
      break;
    case 1:
    case 2:
      v = value;
      break;
    case 3:
      v = f(1.125);
      break;
    case 4:
      v = f(1.5);
      break;
    case 5:
      v = value * 2;
      break;
    case 6:
      v = f(2.5);
      break;
    case 7:
    case 8:
      v = value * 4;
      break;
    default:
      v = value * 8;
  }
  return Math.min(v, 10000);
}

/** weapon_upgrade_cost (mainint.ts): base x the triangular number of `power`. */
const upgradeCost = (base: number, power: number) => (base * power * (power + 1)) / 2;

/** JE_getValue of a weapon at a power level. */
export const weaponValue = (base: number, power: number) => {
  let v = base;
  for (let i = 1; i <= power - 1; i++) v += upgradeCost(base, i);
  return v;
};

export interface EpisodeConstants {
  /** JE_totalScore right after a new game: initial_cash plus the starting gear. */
  startTotal: number;
  /** Most a weapon purchase's 16-bit price wrap can add, over both ports (F). */
  itemSurplus: number;
  /**
   * Most the power-ups in one level can add to the gear's value: both ports from power 1 to 11 on
   * the costliest weapon (power only goes down in the shop, so one level can't raise it further).
   * Each power-up pick-up is also counted as its 1000 consolation (cash at full power).
   */
  powerUpSlack: number;
  /** Weapons 25 and 26 at full power (HOT DOG). */
  hotDog: number;
  /** The ENGAGE gear's value (`]e[`). */
  engage: number;
}

export interface LevelBounds {
  /** lvlFileNum: the level in tyrianN.lvl (unique per episode, checked). */
  lvl: number;
  name: string;
  /** The script section of its `]L[` line(s). */
  sections: number[];
  /** Bonus level (`$` in col 28): dying ends it and moves on. */
  bonus: boolean;
  /** Played in galaga mode (`]g[` before it). */
  galaga: boolean;
  /** Played after ENGAGE (`]e[`): its gear value is added. */
  engage: boolean;
  /** Spawns counted once: [d] is the bound when the level starts at difficultyLevel d. */
  static: number[];
  /** Score per tick from launchers, loops and contact farms: [d]. */
  perTick: number[];
  /** Random spawns: chance per tick and the best spawn's value [d]. */
  random: { p: number; value: number[] };
  /** Ticks: floor (fewest to reach the end), ceiling (null when the level can stall). */
  minTicks: number;
  maxTicks: number | null;
  /** How the bounds came about, for the report. */
  notes: string[];
}

export interface EpisodeBounds {
  episode: number;
  constants: EpisodeConstants;
  /** Graph by difficulty class: "lo" (initial difficulty <= Normal), "hi" (Hard and up), for `]H[`/`]h[`. */
  graph: { lo: LevelGraph; hi: LevelGraph };
  levels: Record<string, LevelBounds>;
}

export interface LevelGraph {
  /** Levels the episode can start with. */
  start: number[];
  /** lvl -> levels that can follow it. */
  next: Record<string, number[]>;
  /** Levels after which the episode's end (`]Q[`) can come, before any other level. */
  end: number[];
}

// ---------------------------------------------------------------------------------------------
// The episode script: from a section, which `]L[` (or `]Q[`) can the reader reach?

interface Reached {
  levels: Map<number, { nextLevel: number; galaga: boolean; engage: boolean; line: number }[]>;
  end: boolean;
}

/**
 * JE_loadMap's reader from `startSection` (tyrian2.ts JE_loadMap_newGame), with every condition it
 * can't know (`]2[`, `]w[`, `]t[`, `]l[`, the item screen's choice) taken both ways. `hard` decides
 * `]H[` and `]h[`. `choices` are the `]G[` choices still in effect.
 */
export function reachFrom(script: EpisodeScript, startSection: number, hard: boolean): Reached {
  const out: Reached = { levels: new Map(), end: false };
  const seen = new Set<string>();
  // Line index where section n starts (its first line after the `*` header).
  const sectionStart = (n: number) => script.sections[n - 1]?.start ?? -1;
  const sectionOfLine = (i: number) => {
    let s = 0;
    for (const sec of script.sections) if (sec.start - 1 <= i) s = sec.number;
    return s;
  };
  type State = { line: number; mainLevel: number; choices: number[]; galaga: boolean; engage: boolean };
  const stack: State[] = [{ line: sectionStart(startSection), mainLevel: startSection, choices: [], galaga: false, engage: false }];
  const jump = (st: State, section: number): State => ({ ...st, line: sectionStart(section), mainLevel: section });
  while (stack.length) {
    const st = stack.pop()!;
    if (st.line < 0) continue;
    const key = `${st.line}/${st.mainLevel}/${st.choices.join(",")}/${st.galaga}/${st.engage}`;
    if (seen.has(key)) continue;
    seen.add(key);
    let i = st.line;
    let cur = st;
    let done = false;
    while (!done && i < script.lines.length) {
      const s = script.lines[i++];
      if (s[0] !== "]") continue;
      const arg3 = atoiAt(s, 3);
      switch (s[1]) {
        case "J":
          stack.push(jump(cur, arg3 & 0xff));
          done = true;
          break;
        case "2":
        case "w":
        case "t":
        case "l":
          stack.push(jump({ ...cur, line: i }, arg3 & 0xff)); // taken
          break; // or not
        case "H":
          if (!hard) {
            stack.push(jump(cur, atoiAt(s, 4) & 0xff));
            done = true;
          }
          break;
        case "h":
          if (hard) i++;
          break;
        case "G": {
          const n = atoiAt(s, 7);
          const choices: number[] = [];
          for (let k = 0; k < n; k++) choices.push(atoiAt(s, 4 + (k + 1) * 8) & 0xff);
          cur = { ...cur, choices };
          break;
        }
        case "I":
          i += 9; // the item lists
          // The item screen ends by choosing a next level (or quitting the game).
          for (const c of cur.choices) stack.push(jump(cur, c));
          done = true;
          break;
        case "W":
          while (i < script.lines.length && script.lines[i++][0] !== "#");
          break;
        case "g":
          cur = { ...cur, galaga: true };
          break;
        case "e":
          cur = { ...cur, engage: true };
          break;
        case "L": {
          let nextLevel = atoiAt(s, 9) & 0xff;
          if (nextLevel === 0) nextLevel = (cur.mainLevel + 1) & 0xff;
          const lvl = atoiAt(s, 25) & 0xff;
          const list = out.levels.get(lvl) ?? [];
          if (!list.some((x) => x.nextLevel === nextLevel && x.galaga === cur.galaga && x.engage === cur.engage))
            list.push({ nextLevel, galaga: cur.galaga, engage: cur.engage, line: i - 1 });
          out.levels.set(lvl, list);
          void sectionOfLine;
          done = true;
          break;
        }
        case "Q":
          out.end = true;
          done = true;
          break;
      }
    }
  }
  return out;
}

/** atoi(s + n). */
function atoiAt(s: string, n: number): number {
  const m = /^\s*([+-]?\d+)/.exec(s.slice(n));
  return m ? parseInt(m[1], 10) : 0;
}

// ---------------------------------------------------------------------------------------------
// One level's events.

/** Event types that spawn enemies: type -> the enemy type offsets they add to eventdat. */
const SPAWN_EVENTS: Record<number, number[]> = {
  6: [0],
  7: [0],
  10: [0],
  12: [0, 1, 2, 3],
  15: [0],
  17: [0],
  18: [0],
  23: [0],
  32: [0],
  56: [0],
};
/** Events 49-52 spawn enemyDat[0] (a custom enemy with eventdat's graphic and eventdat6 armor). */
const CUSTOM_SPAWN_EVENTS = new Set([49, 50, 51, 52]);

interface ValueContext {
  enemies: EnemyDat[];
  constants: EpisodeConstants;
  galaga: boolean;
  engage: boolean;
  /** Warp sections seen (pick-ups 10001..19999). */
  warps: Set<number>;
  /** Contact-farm pick-ups seen (31001..32000). */
  farms: Set<number>;
  hotDog: boolean;
  /** A power-up can be picked up (adds powerUpSlack). */
  powerUps: boolean;
  /** unitValue memo by `${type}/${d}`; NaN while being computed (a drop cycle). */
  memo: Map<string, number>;
  /** A drop chain that loops back on itself was seen. */
  cycle: boolean;
}

/** The most one spawn of enemy type `t` can add at difficulty d, its drops included. */
function unitValue(ctx: ValueContext, t: number, d: number, extra: number[] = []): number {
  const key = `${t}/${d}/${extra.join(",")}`;
  const m = ctx.memo.get(key);
  if (m !== undefined) {
    if (Number.isNaN(m)) {
      // A drop that leads back to itself: each kill spawns the next. Count a full 10000 here; the
      // level's notes say so.
      ctx.cycle = true;
      return 10000;
    }
    return m;
  }
  ctx.memo.set(key, NaN);
  const v = unitValueOf(ctx, t, d, extra);
  ctx.memo.set(key, v);
  return v;
}

function unitValueOf(ctx: ValueContext, t: number, d: number, extra: number[]): number {
  const dat = ctx.enemies[t];
  if (!dat) return 0;
  const ev = scaledValue(dat.value, d);
  // An event-spawned enemy may be given an event-33 drop (`extra`) instead of its own.
  const drops = [dat.eEnemyDie, ...(dat.armor > 0 ? extra : [])].filter((x) => x > 0);
  const dropValue = drops.length ? Math.max(...drops.map((x) => unitValue(ctx, x, d))) : 0;
  if (dat.armor > 0) {
    let kill = ev > 1 && ev < 10000 ? ev : 0;
    if (ctx.galaga && dat.value > 1 && dat.value < 10000) kill = 9999; // JE_searchFor doubling
    // A doubled evalue in galaga mode can reach a pick-up's range: worst of all, a contact farm.
    if (ctx.galaga && dat.value > 1 && dat.value < 10000) ctx.farms.add(t);
    const lives = dat.dLevel === -1 ? 2 : 1;
    return lives * (kill + dropValue);
  }
  // A pick-up: collected (JE_playerCollide), or shot (destroyEnemy) and its drop spawned.
  let pick = 0;
  const powerUp = 1000; // cash at full power; the value gain is the level's powerUpSlack
  if (ev > 29999) {
    if (ev === 30000) {
      pick = 100 + (ctx.galaga ? 2400 : 0) + powerUp;
      ctx.powerUps = true;
    } else if (ev > 31000 && ev <= 32000) {
      // Left on screen in a one-player full game (only one-player action, after ENGAGE, takes it).
      pick = 250;
      if (!ctx.engage) ctx.farms.add(t);
    } else pick = 250;
  } else if (ev > 20000) pick = 0;
  else if (ev > 10000) {
    ctx.warps.add(ev - 10000);
    pick = 0;
  } else if (ev === -1 || ev === -2) {
    pick = powerUp;
    ctx.powerUps = true;
  }
  else if (ev === -5) {
    ctx.hotDog = true;
    pick = 0; // the gear's value: the level's hotDog slack
  } else if (ev > 1) pick = ev;
  const shot = ev > 1 && ev < 10000 ? ev : 0;
  return Math.max(pick, shot) + dropValue;
}

interface Jump {
  /** curLoc of the jumping event (or where the timer starts). */
  from: number;
  /** curLoc it jumps to. */
  to: number;
  /** Ticks before it fires (the level timer), else 0. */
  delay: number;
}

/** The events' jumps, as curLoc to curLoc. */
function levelJumps(events: Level["events"]): Jump[] {
  const jumps: Jump[] = [];
  const timeAt = (idx: number) => events[Math.min(Math.max(idx, 0), events.length - 1)]?.eventTime ?? 0;
  events.forEach((e, idx) => {
    switch (e.eventType) {
      case 38: // curLoc = eventdat
      case 54: // JE_eventJump(eventdat)
      case 70: // jump if the linked enemies are gone
      case 71: // jump if the map is past a point
        if ((e.eventDat & 0xffff) !== 65535) jumps.push({ from: e.eventTime, to: e.eventDat & 0xffff, delay: 0 });
        else jumps.push({ from: e.eventTime, to: -1, delay: 0 }); // return: handled as a loop
        break;
      case 57: // superEnemy254Jump: fires on a kill any time later
        jumps.push({ from: e.eventTime, to: e.eventDat & 0xffff, delay: 0 });
        break;
      case 75: // skip events: curLoc = the target event's time - 1
        if (e.eventDat4 > 0) jumps.push({ from: e.eventTime, to: timeAt(idx + e.eventDat4) - 1, delay: 0 });
        break;
      case 67: // level timer: JE_eventJump(eventdat2) after eventdat3 * 100 ticks
        if (e.eventDat === 1) jumps.push({ from: e.eventTime, to: e.eventDat2 & 0xffff, delay: (e.eventDat3 & 0xffff) * 100 });
        break;
    }
  });
  return jumps;
}

export function levelBounds(
  level: Level,
  lvl: number,
  meta: { name: string; sections: number[]; bonus: boolean; galaga: boolean; engage: boolean },
  enemies: EnemyDat[],
  constants: EpisodeConstants,
): LevelBounds & { warps: number[]; explain: { time: number; type: number; value: number; enemy: string }[] } {
  const events = level.events;
  const notes: string[] = [];
  // Events 33 (and 45, arcade-only: one-player action after ENGAGE) give the enemies linked to
  // eventdat4 a drop; 533 becomes a random special weapon (829-834).
  const dropEvents = events.filter((e) => e.eventType === 33 || (e.eventType === 45 && meta.engage));
  const dropsOf = (e: Level["events"][number]) => (e.eventDat === 533 ? [533, 829, 830, 831, 832, 833, 834] : [e.eventDat & 0xffff]);
  const extraDrops = [...new Set(dropEvents.flatMap(dropsOf))];
  const ctx: ValueContext = { enemies, constants, galaga: meta.galaga, engage: meta.engage, warps: new Set(), farms: new Set(), hotDog: false, powerUps: false, memo: new Map(), cycle: false };

  // Every spawn an event makes: its time, enemy type and link number (eventdat4).
  const spawns: { time: number; type: number; link: number; extra: number[] }[] = [];
  for (const e of events) {
    const ofs = SPAWN_EVENTS[e.eventType];
    if (ofs) for (const o of ofs) spawns.push({ time: e.eventTime, type: (e.eventDat + o) & 0xffff, link: e.eventDat4, extra: [] });
    if (CUSTOM_SPAWN_EVENTS.has(e.eventType)) spawns.push({ time: e.eventTime, type: 0, link: e.eventDat4, extra: [] });
  }

  // Event 46 (change difficulty) raises the difficulty within the level.
  const jumps = levelJumps(events);
  const backward = jumps.filter((j) => j.to < 0 || j.to < j.from || j.delay > 0);

  // Which event-33 drops can reach each spawn: events for its link (or a link event 39 renames it
  // to), at or after its time (any time, when the level loops).
  const renames = events.filter((e) => e.eventType === 39);
  const linkClosure = (link: number) => {
    const out = new Set([link]);
    for (let grew = true; grew; ) {
      grew = false;
      for (const r of renames) if (out.has(r.eventDat & 0xff) && !out.has(r.eventDat2 & 0xff)) (out.add(r.eventDat2 & 0xff), (grew = true));
    }
    return out;
  };
  for (const sp of spawns) {
    const links = linkClosure(sp.link);
    sp.extra = [...new Set(dropEvents.filter((e) => links.has(e.eventDat4) && (backward.length > 0 || e.eventTime >= sp.time)).flatMap(dropsOf))].sort((a, b) => a - b);
  }
  // Enemies not spawned by an event (random, launched, dropped) have link 0 (a launch can copy its
  // launcher's link: counted with the launches); an event 33 for link 0 reaches at most 25 of each.
  const hasRandom = level.levelEnemy.length > 0;
  const unlinkedAlive = Math.min(100, 25 * (hasRandom ? 1 : 0) + 25 + 25);
  const raiseEvents = events.filter((e) => e.eventType === 46 && e.eventDat > 0);
  const raiseInLoop = raiseEvents.some((e) => backward.some((j) => e.eventTime >= Math.max(0, j.to) && e.eventTime <= j.from));
  const raise = raiseInLoop ? DIFFICULTY_LEVELS : raiseEvents.reduce((a, e) => a + e.eventDat, 0);
  if (raise) notes.push(`event 46 raises the difficulty by up to ${raiseInLoop ? "10 (in a loop)" : raise}`);

  // Fastest and slowest scroll: curLoc advances backMove per map1YDelayMax ticks (1 per tick at
  // start; event 3 is 1 per 3 ticks; events 2/30 set backMove = eventdat at 1 per tick).
  const speeds = events.filter((e) => e.eventType === 2 || e.eventType === 30).map((e) => e.eventDat & 0xffff);
  const adv = Math.max(1, ...speeds);
  const canStall =
    speeds.some((s) => s === 0) || events.some((e) => e.eventType === 4) || backward.length > 0 || jumps.some((j) => j.delay > 0);
  const slowest = events.some((e) => e.eventType === 3) ? 1 / 3 : Math.min(1, ...speeds.filter((s) => s > 0));

  // Loops: each backward jump's body repeats at most once per (body length / adv) ticks.
  const loops = backward.map((j) => {
    const to = j.to < 0 ? Math.min(...jumps.map((k) => k.from)) : Math.min(j.to, j.from);
    const len = j.from - to;
    return { to, from: j.from, period: Math.max(1, Math.ceil(len / adv)), spawns: spawns.filter((s) => s.time >= to && s.time <= j.from) };
  });
  if (loops.length) notes.push(`${loops.length} event loop(s): body spawns counted per period`);

  // Launchers: every launchfreq ticks (event 31 can set launchfreq to eventdat5).
  const freqOverrides = events.filter((e) => e.eventType === 31).map((e) => e.eventDat5 & 0xff).filter((f) => f > 0);
  const randomTypes = level.levelEnemy;
  const minFreq = Math.min(96, ...events.filter((e) => e.eventType === 37).map((e) => e.eventDat & 0xffff));
  const p = Math.max(0, (99 - minFreq) / 100);

  // Types that can be present: spawned, dropped, launched (with how many at once).
  const staticCount = new Map<number, number>();
  for (const s of spawns) staticCount.set(s.type, (staticCount.get(s.type) ?? 0) + 1);
  const loopTypes = new Set(loops.flatMap((l) => l.spawns.map((s) => s.type)));
  const randomSet = new Set(p > 0 ? randomTypes : []);

  // For the report: each event spawn's value at Normal (d = 2).
  const explain = spawns.map((sp) => {
    const dat = enemies[sp.type];
    return {
      time: sp.time,
      type: sp.type,
      value: unitValue(ctx, sp.type, 2, sp.extra),
      enemy: dat ? `value ${dat.value}, armor ${dat.armor}, drop ${dat.eEnemyDie}, launch ${dat.eLaunchType}/${dat.eLaunchFreq}` : "none",
    };
  });
  const statics: number[] = [0];
  const perTicks: number[] = [0];
  const randomValues: number[] = [0];
  for (let d0 = 1; d0 <= DIFFICULTY_LEVELS; d0++) {
    const d = Math.min(DIFFICULTY_LEVELS, d0 + raise);
    const v = (t: number) => unitValue(ctx, t, d);
    const vSpawn = (sp: (typeof spawns)[number]) => unitValue(ctx, sp.type, d, sp.extra);
        const unlinkedDrops = (e: Level["events"][number]) => (e.eventDat4 === 0 ? unlinkedAlive * Math.max(...dropsOf(e).map(v)) : 0);
    statics.push(spawns.reduce((a, sp) => a + vSpawn(sp), 0) + dropEvents.reduce((a, e) => a + unlinkedDrops(e), 0));

    let rate = 0;
    for (const l of loops) {
      const body = l.spawns.reduce((a, sp) => a + vSpawn(sp), 0) + dropEvents.filter((e) => e.eventTime >= l.to && e.eventTime <= l.from).reduce((a, e) => a + unlinkedDrops(e), 0);
      rate += body / l.period;
    }

    // Launch rate: n instances x the launched type's value / the shortest launch interval. A type
    // that can keep coming (loops, random spawns, launches, drops) counts as a full block of 25.
    const launchSeen = new Set<number>();
    const launchRate = (t: number, n: number, depth: number): number => {
      const dat = enemies[t];
      if (!dat || depth > 4) return 0;
      const launched = dat.eLaunchType % 1000;
      const freqs = [dat.eLaunchFreq, ...(launched > 0 ? freqOverrides : [])].filter((f) => f > 0);
      if (launched === 0 || freqs.length === 0) return 0;
      const f = Math.min(...freqs);
      return (n * v(launched)) / f + (launchSeen.has(launched) ? 0 : (launchSeen.add(launched), launchRate(launched, 25, depth + 1)));
    };
    const present = new Map<number, number>();
    const addPresent = (t: number, n: number) => present.set(t, Math.min(25, (present.get(t) ?? 0) + n));
    for (const [t, n] of staticCount) addPresent(t, loopTypes.has(t) ? 25 : n);
    for (const t of randomSet) addPresent(t, 25);
    for (const t of [...present.keys()]) {
      // Drops of present types can be launchers too.
      const dat = enemies[t];
      for (const x of [dat?.eEnemyDie ?? 0, ...(dat && dat.armor > 0 ? extraDrops : [])]) if (x > 0) addPresent(x, present.get(t) ?? 1);
    }
    let launch = 0;
    for (const [t, n] of present) launch += launchRate(t, n, 0);
    rate += launch;
    perTicks.push(rate);

    randomValues.push(randomSet.size ? Math.max(...[...randomSet].map(v)) : 0);
  }
  if (freqOverrides.length) notes.push(`event 31 can shorten launch intervals to ${Math.min(...freqOverrides)}`);
  if (p > 0) notes.push(`random spawns: p = ${p.toFixed(2)} per tick from ${randomTypes.length} type(s)`);

  // Contact farms (31001..32000 pick-ups in a one-player full game): 250 per tick per item touching.
  if (ctx.farms.size) {
    const farmRate = 250 * 25;
    for (let d = 1; d <= DIFFICULTY_LEVELS; d++) perTicks[d] += farmRate;
    notes.push(`contact-farm pick-up types ${[...ctx.farms].join(",")}: +${farmRate}/tick`);
  }
  // Gear value a level can add for free (F): power-ups, HOT DOG.
  const slack = (ctx.powerUps ? constants.powerUpSlack : 0) + (ctx.hotDog ? constants.hotDog : 0);
  if (slack) for (let d = 1; d <= DIFFICULTY_LEVELS; d++) statics[d] += slack;
  if (ctx.powerUps) notes.push(`power-ups: +${constants.powerUpSlack} gear value`);
  if (ctx.cycle) notes.push("a drop chain loops: 10000 per link counted");
  if (ctx.hotDog) notes.push("HOT DOG pick-up (-5): weapons 25/26 at full power counted");

  // Ticks: Dijkstra over curLoc from 0 with forward jumps free.
  const ends = events.filter((e) => e.eventType === 11 || e.eventType === 36).map((e) => e.eventTime);
  let minTicks = 0;
  let maxTicks: number | null = null;
  if (ends.length && !meta.bonus) {
    const points = [...new Set([0, ...ends, ...jumps.flatMap((j) => [j.from, Math.max(0, j.to)])])].sort((a, b) => a - b);
    const dist = new Map(points.map((t) => [t, Infinity]));
    dist.set(0, 0);
    const done = new Set<number>();
    for (;;) {
      let best = -1;
      for (const t of points) if (!done.has(t) && dist.get(t)! < Infinity && (best < 0 || dist.get(t)! < dist.get(best)!)) best = t;
      if (best < 0) break;
      done.add(best);
      const d0 = dist.get(best)!;
      const relax = (t: number, c: number) => {
        if (c < dist.get(t)!) dist.set(t, c);
      };
      const idx = points.indexOf(best);
      if (idx + 1 < points.length) relax(points[idx + 1], d0 + (points[idx + 1] - best) / adv);
      for (const j of jumps) if (j.from <= best && j.to > best && dist.has(j.to)) relax(j.to, d0 + j.delay);
    }
    minTicks = Math.floor(Math.min(...ends.map((t) => dist.get(t)!)));
    if (!canStall) maxTicks = Math.ceil((Math.max(...ends) / slowest) * 1.5) + 1000;
  }
  if (meta.bonus) notes.push("bonus level: dying ends it, so no tick floor");

  return {
    lvl,
    ...meta,
    static: statics,
    perTick: perTicks.map((r) => Math.ceil(r * 1000) / 1000),
    random: { p, value: randomValues },
    minTicks,
    maxTicks,
    notes,
    warps: [...ctx.warps].sort((a, b) => a - b),
    explain,
  };
}

// ---------------------------------------------------------------------------------------------

/** The constants of section F/G for an episode (g.res must be that episode's). */
export function episodeConstants(files: TyrianFiles, episode: number, script: EpisodeScript): EpisodeConstants {
  g.res = buildResources(files, episode);
  const hdt = files.get("tyrian.hdt");
  if (hdt) loadHelpText(hdt);
  newOnePlayerGame(episode, 2);
  const startTotal = JE_totalScore(g.player[0]);
  const items = g.res.items;
  const ports = items.weaponPorts.slice(0, PORT_NUM + 1);
  const maxBase = Math.max(...ports.map((w) => w.cost));
  const surplusOf = (base: number) => {
    let s = 0;
    for (let i = 1; i <= 10; i++) {
      const c = upgradeCost(base, i);
      s += c - (c % 65536);
    }
    return s;
  };
  const itemSurplus = 2 * Math.max(...ports.map((w) => surplusOf(w.cost)));
  const powerUpSlack = 2 * (weaponValue(maxBase, 11) - maxBase);
  const hotDog = weaponValue(ports[25].cost, 11) + weaponValue(ports[26].cost, 11);
  // ENGAGE: ship 13, front 39 at power 3, generator 2, shield 4.
  const engage = items.ships[13].cost + weaponValue(ports[39].cost, 3) + items.powerSys[2].cost + items.shields[4].cost;

  // The shop prices ship ids over 90 at 100 (JE_getCost): make sure no item list offers one.
  script.lines.forEach((s, i) => {
    if (s.startsWith("]I[")) {
      const ships = itemAvailInts(script.lines[i + 1]);
      if (ships.some((x) => x > 90)) throw new Error(`episode ${episode}: an item screen offers ship ${ships}`);
    }
  });
  return { startTotal, itemSurplus, powerUpSlack, hotDog, engage };
}

function itemAvailInts(s: string | undefined): number[] {
  return (s && s.length > 8 ? s.slice(8) : "").trim().split(/\s+/).filter(Boolean).map((x) => parseInt(x, 10) & 0xff);
}

/** Everything for one episode. */
export function episodeBounds(files: TyrianFiles, episode: number): EpisodeBounds {
  const get = (n: string) => {
    const f = files.get(n);
    if (!f) throw new Error(`missing ${n}`);
    return f;
  };
  const script = parseEpisodeScript(get(`levels${episode}.dat`));
  const lvlFile = parseLevelFile(get(`tyrian${episode}.lvl`));
  const constants = episodeConstants(files, episode, script);
  const enemies = g.res.enemyDat;
  const reachCache = new Map<string, Reached>();
  const reach = (section: number, hard: boolean) => {
    const k = `${section}/${hard}`;
    let r = reachCache.get(k);
    if (!r) reachCache.set(k, (r = reachFrom(script, section, hard)));
    return r;
  };

  // Level ids: lvlFileNum, which must be unique per `]L[` in the episode.
  const refs = episodeLevels(script);
  const byLvl = new Map<number, typeof refs>();
  for (const r of refs) byLvl.set(r.lvlFileNum, [...(byLvl.get(r.lvlFileNum) ?? []), r]);

  const graphs = { lo: { start: [], next: {}, end: [] } as LevelGraph, hi: { start: [], next: {}, end: [] } as LevelGraph };
  const levels: Record<string, LevelBounds> = {};
  const warpsOf = new Map<number, number[]>();
  const flags = new Map<number, { galaga: boolean; engage: boolean }>();

  // Flags (galaga, engage) per level come from reaching it.
  for (const hard of [false, true]) {
    for (const sec of script.sections) {
      for (const [lvl, list] of reach(sec.number, hard).levels) {
        const f = flags.get(lvl) ?? { galaga: false, engage: false };
        for (const x of list) {
          f.galaga ||= x.galaga;
          f.engage ||= x.engage;
        }
        flags.set(lvl, f);
      }
    }
  }

  for (const [lvl, rs] of byLvl) {
    const level = lvlFile.levels[lvl - 1];
    if (!level) throw new Error(`episode ${episode}: no level ${lvl}`);
    const f = flags.get(lvl) ?? { galaga: false, engage: false };
    const b = levelBounds(
      level,
      lvl,
      { name: rs[0].levelName.trim(), sections: rs.map((r) => r.section), bonus: rs.some((r) => r.bonusLevelCurrent), galaga: f.galaga, engage: f.engage },
      enemies,
      constants,
    );
    warpsOf.set(lvl, b.warps);
    const { warps, explain, ...rest } = b;
    void explain;
    if (warps.length) rest.notes.push(`warps to section(s) ${warps.join(", ")}`);
    levels[lvl] = rest;
  }

  for (const [cls, hard] of [["lo", false], ["hi", true]] as const) {
    const gr = graphs[cls];
    const start = reach(1, hard);
    gr.start = [...start.levels.keys()].sort((a, b) => a - b);
    const ends = new Set<number>();
    for (const [lvl, rs] of byLvl) {
      void rs;
      const next = new Set<number>();
      // Where the reader starts after this level: nextLevel of each way it's reached, and warps.
      const starts = new Set<number>(warpsOf.get(lvl) ?? []);
      for (const sec of script.sections) {
        const r = reach(sec.number, hard).levels.get(lvl);
        for (const x of r ?? []) starts.add(x.nextLevel);
      }
      for (const s of starts) {
        const r = reach(s, hard);
        for (const k of r.levels.keys()) next.add(k);
        if (r.end) ends.add(lvl);
      }
      gr.next[lvl] = [...next].sort((a, b) => a - b);
    }
    gr.end = [...ends].sort((a, b) => a - b);
  }
  return { episode, constants, graph: graphs, levels };
}

/** The whole file: episodes 1-4, plus how to read it. */
export function maxScores(files: TyrianFiles) {
  const episodes: Record<string, EpisodeBounds> = {};
  for (let e = 1; e <= 4; e++) {
    if (!files.get(`levels${e}.dat`)) continue;
    const b = episodeBounds(files, e);
    for (const [lvl, l] of Object.entries(b.levels)) {
      // lvlFileNum must name one level: one script name per lvl.
      void lvl;
      void l;
    }
    episodes[e] = b;
  }
  return {
    about:
      "Generated by tools/maxScores/maxScores.ts from the Tyrian 2.1 data (numbers only). Per episode: the level graph by difficulty class and, per level (lvlFileNum), score bounds per starting difficulty level ([d], d = 1..10; index 0 unused), a per-tick rate, random-spawn odds and tick bounds. See the tool's header for the method.",
    tickHz: 1000 / ((0x4300 * 2 * 1000) / (315_000_000 / 88 / 3)),
    episodes,
  };
}
