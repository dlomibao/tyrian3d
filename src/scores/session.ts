// The game flow's side of the shared high-score list and the play reports (src/app/run.ts calls
// these at a new game, a load, the item screen, each level's start, tick and end, and at the
// high-score check). Without VITE_SCORES_API nothing goes over the network and nothing changes in
// the game; the run record and the level summaries are only kept in memory.
//
// Taint rules (a tainted run never submits a score; its play reports are flagged):
//  - the debug console, opened or run from devtools (`tyrianConsole`): the rest of the page session;
//  - the in-flight cheat chords (Nort ship, invulnerability, self-destruct, skip level): that run;
//  - URL parameters that change the game: ?loot (1,000,000 credits), ?seed (a chosen random seed),
//    ?debug=... (the harnesses): the page session.
// Not taints: the hidden difficulties (harder, and they're their own table's column), the title's
// Super Arcade / Super Tyrian codes and the arcade and two-player modes (original modes, recorded
// in the stats by mode, but not eligible for the shared list, whose bounds model a one-player full
// game), DESTRUCT (a separate game), and the look parameters (?bg, ?vfx, ?terrain, ?compare, ...).

import type { RunData } from "../../server/scores/lib/runHash.d.mts";
import type { LevelReport, ShopTrade } from "../../server/scores/lib/report.d.mts";
import { runHash } from "../../server/scores/lib/runHash.mjs";
import { CLASSIC_TICK_HZ } from "../core/timing";
import { JE_totalScore, weapon_upgrade_cost } from "../sim/mainint";
import { newRunRecord, runRecord, taintRun, type RunMode, type RunRecord } from "../sim/runRecord";
import { FRONT_WEAPON, g, LEFT_SIDEKICK, REAR_WEAPON, RIGHT_SIDEKICK, SA_NONE } from "../sim/state";
import { BUILD_ID, requestRunToken, scoresEnabled, sendLevelReport, submitScore, type SubmitResult } from "./api";
import { statsPlayerId, statsSharing } from "./statsId";

/** URL parameters that change the game's state, as taints. */
export function urlTaints(search: string): string[] {
  const p = new URLSearchParams(search);
  const keys = [...p.keys()].map((k) => k.toLowerCase());
  const out: string[] = [];
  if (keys.includes("loot")) out.push("loot");
  if (keys.includes("seed")) out.push("seed");
  if (keys.includes("debug")) out.push("debug");
  return out;
}

/** At startup: keep run records in saves (with the shared list) and apply the URL's taints. */
export function initScoresSession(search: string = typeof location === "undefined" ? "" : location.search): void {
  runRecord.persist = scoresEnabled();
  for (const t of urlTaints(search)) taintRun(t, true);
}

/** The run's mode from the game's state (a loaded game). */
export function currentMode(): RunMode {
  if (g.superTyrian) return "superTyrian";
  if (g.superArcadeMode !== SA_NONE) return "superArcade";
  if (g.twoPlayerMode) return "twoPlayer";
  if (g.onePlayerAction) return "arcade";
  return "story";
}

/** A new game: a new run record and, with the shared list, a run token (asked for in the background). */
export function startRun(episode: number, difficulty: number, mode: RunMode): Promise<void> {
  const r = newRunRecord(episode, difficulty, mode);
  flow = { prev: null, warped: false, branched: false, retry: false, loaded: false, shop: [] };
  if (!scoresEnabled()) return Promise.resolve();
  const playerId = statsSharing() ? (statsPlayerId() ?? undefined) : undefined;
  return requestRunToken({ episode, difficulty, mode, ...(playerId ? { playerId } : {}) }).then((t) => {
    if (t && runRecord.current === r) {
      r.token = t.token;
      r.issuedAt = t.issuedAt;
    }
  });
}

/** A saved game was loaded (JE_loadGame has restored its record, if it had one). */
export function loadedRun(): void {
  flow = { prev: runRecord.current?.levels.at(-1)?.lvl ?? null, warped: false, branched: false, retry: false, loaded: true, shop: [] };
}

// --- How the levels connect, for the reports ---

interface Flow {
  prev: number | null;
  warped: boolean;
  branched: boolean;
  retry: boolean;
  loaded: boolean;
  shop: ShopTrade[];
}
let flow: Flow = { prev: null, warped: false, branched: false, retry: false, loaded: false, shop: [] };

// --- The item screen's trades ---

interface Slot {
  slot: ShopTrade["slot"];
  id: number;
  power: number;
}

function slots(): Slot[] {
  const it = g.player[0].items;
  return [
    { slot: "ship", id: it.ship, power: 0 },
    { slot: "front", id: it.weapon[FRONT_WEAPON].id, power: it.weapon[FRONT_WEAPON].power },
    { slot: "rear", id: it.weapon[REAR_WEAPON].id, power: it.weapon[REAR_WEAPON].power },
    { slot: "shield", id: it.shield, power: 0 },
    { slot: "generator", id: it.generator, power: 0 },
    { slot: "left", id: it.sidekick[LEFT_SIDEKICK], power: 0 },
    { slot: "right", id: it.sidekick[RIGHT_SIDEKICK], power: 0 },
  ];
}

/** JE_getValue for one slot at a power level. */
function slotValue(s: Slot, power = s.power): number {
  const items = g.res?.items;
  if (!items) return 0;
  switch (s.slot) {
    case "ship":
      return items.ships[s.id]?.cost ?? 0;
    case "front":
    case "rear": {
      const base = items.weaponPorts[s.id]?.cost ?? 0;
      let v = base;
      for (let i = 1; i <= power - 1; i++) v += weapon_upgrade_cost(base, i);
      return v;
    }
    case "shield":
      return items.shields[s.id]?.cost ?? 0;
    case "generator":
      return items.powerSys[s.id]?.cost ?? 0;
    default:
      return items.options[s.id]?.cost ?? 0;
  }
}

let shopBefore: Slot[] | null = null;

/** Entering the item screen. */
export function shopStart(): void {
  shopBefore = slots();
}

/** Leaving it: each slot that changed is a sale and a purchase (or a power change), kept for the next report. */
export function shopEnd(): void {
  if (!shopBefore) return;
  const after = slots();
  shopBefore.forEach((b, i) => {
    const a = after[i];
    if (a.id !== b.id) {
      if (b.id) flow.shop.push({ kind: "sell", slot: b.slot, id: b.id, power: b.power, price: slotValue(b) });
      if (a.id) flow.shop.push({ kind: "buy", slot: a.slot, id: a.id, power: a.power, price: slotValue(a) });
    } else if (a.power !== b.power) {
      flow.shop.push({ kind: a.power > b.power ? "upgrade" : "downgrade", slot: a.slot, id: a.id, power: a.power, price: Math.abs(slotValue(a) - slotValue(b)) });
    }
  });
  flow.shop = flow.shop.slice(-100);
  // `]G[` offered more than one next level: the item screen chose a branch.
  flow.branched = g.mapPNum > 1;
  shopBefore = null;
}

// --- One level ---

interface LevelTrack {
  lvl: number;
  name: string;
  section: number;
  startScore: number;
  difficultyNow: number;
  loadout: LevelReport["loadout"];
  via: LevelReport["level"]["via"];
  prev: number | null;
  index: number;
  enemyKilled: number;
  totalEnemy: number;
  cubes: number;
  ticks: number;
  damage: number;
  armor: number;
  shield: number;
  bombs: number;
  bombsUsed: number;
  alive: boolean;
  deaths: { tick: number; x: number; y: number }[];
}
let track: LevelTrack | null = null;

/** A level starts (after startLevel). */
export function levelStart(): void {
  // The game went on into the next episode (JE_nextEpisode): its levels are another path, so the
  // play reports carry a new run (and token) for it, with the old run's taints. The high-score
  // check isn't due outside the starting episode, so nothing is submitted for it.
  const old = runRecord.current;
  if (old && g.episodeNum !== old.episode) {
    void startRun(g.episodeNum, old.difficulty, old.mode);
    for (const t of old.taints) taintRun(t);
  }
  const p = g.player[0];
  const it = p.items;
  const via: LevelReport["level"]["via"] = flow.retry ? "retry" : flow.loaded ? "load" : flow.prev === null ? "start" : flow.warped ? "warp" : flow.branched ? "branch" : "story";
  track = {
    lvl: g.lvlFileNum,
    name: g.levelName.trim(),
    section: g.mainLevel,
    startScore: JE_totalScore(p),
    difficultyNow: g.difficultyLevel,
    loadout: {
      ship: it.ship,
      front: { id: it.weapon[FRONT_WEAPON].id, power: it.weapon[FRONT_WEAPON].power },
      rear: { id: it.weapon[REAR_WEAPON].id, power: it.weapon[REAR_WEAPON].power },
      sidekicks: [it.sidekick[LEFT_SIDEKICK], it.sidekick[RIGHT_SIDEKICK]],
      shield: it.shield,
      generator: it.generator,
      armor: p.armor,
      credits: p.cash,
    },
    via,
    prev: flow.prev,
    index: runRecord.current?.levels.length ?? 0,
    enemyKilled: g.enemyKilled,
    totalEnemy: g.totalEnemy,
    cubes: g.cubeMax,
    ticks: 0,
    damage: 0,
    armor: p.armor,
    shield: p.shield,
    bombs: p.superbombs,
    bombsUsed: 0,
    alive: p.is_alive,
    deaths: [],
  };
  flow.retry = false;
  flow.loaded = false;
}

/** After each tick: damage taken, superbombs, the ship's loss. */
export function levelTick(): void {
  const t = track;
  if (!t) return;
  const p = g.player[0];
  t.ticks++;
  t.damage += Math.max(0, t.armor - p.armor) + Math.max(0, t.shield - p.shield);
  t.armor = p.armor;
  t.shield = p.shield;
  if (p.superbombs < t.bombs) t.bombsUsed += t.bombs - p.superbombs;
  t.bombs = p.superbombs;
  if (t.alive && !p.is_alive && t.deaths.length < 20) t.deaths.push({ tick: t.ticks, x: p.x, y: p.y });
  t.alive = p.is_alive;
}

export type LevelOutcome = "completed" | "died" | "quit" | "jump";

/**
 * A level ended. A finished level joins the run's path; a quit one is kept aside for the
 * high-score check (the score counts what was earned in it). Sends the play report.
 */
export function levelEnd(outcome: LevelOutcome): void {
  const t = track;
  track = null;
  if (!t) return;
  const r = runRecord.current;
  const score = JE_totalScore(g.player[0]);
  quitLevel = null;
  if (outcome === "completed" && r) {
    r.levels.push({ lvl: t.lvl, ticks: t.ticks, score, done: true });
    flow.prev = t.lvl;
    flow.warped = g.bonusLevel;
  } else if (outcome === "quit") {
    quitLevel = { lvl: t.lvl, ticks: t.ticks, score, done: false };
  }
  if (outcome === "died") flow.retry = true;
  flow.branched = false;
  if (outcome !== "jump") report(t, outcome === "completed" ? "finished" : outcome === "died" ? "died" : "quit", score);
}

/**
 * After a lost level's retry backup is loaded: a bonus level the game moves on from (dying there
 * ends it) joins the path with the score the backup restored.
 */
export function bonusLevelSkipped(lvl: number, ticks: number): void {
  const r = runRecord.current;
  if (!r) return;
  r.levels.push({ lvl, ticks, score: JE_totalScore(g.player[0]), done: true });
  flow.prev = lvl;
  flow.retry = false;
}

/** The level a run was quit in, for the high-score check. */
let quitLevel: { lvl: number; ticks: number; score: number; done: false } | null = null;

/** The last level's tick count (the bonus-level skip needs it after the report). */
export function lastLevelTicks(): number {
  return lastTicks;
}
let lastTicks = 0;

function report(t: LevelTrack, result: LevelReport["outcome"]["result"], score: number): void {
  lastTicks = t.ticks;
  const r = runRecord.current;
  const shop = flow.shop;
  flow.shop = [];
  if (!scoresEnabled() || !statsSharing() || !r?.token) return;
  const playerId = statsPlayerId();
  if (!playerId) return;
  sendLevelReport({
    v: 1,
    token: r.token,
    playerId,
    build: BUILD_ID,
    tainted: r.tainted,
    run: { episode: r.episode, difficulty: r.difficulty, difficultyNow: t.difficultyNow, mode: r.mode, tickHz: CLASSIC_TICK_HZ },
    level: { lvl: t.lvl, name: t.name.slice(0, 16), section: t.section, index: t.index, prev: t.prev, via: t.via },
    loadout: t.loadout,
    outcome: {
      result,
      ticks: t.ticks,
      scoreGained: score - t.startScore,
      deaths: t.deaths,
      enemiesKilled: Math.max(0, g.enemyKilled - t.enemyKilled),
      enemiesSpawned: Math.max(0, g.totalEnemy - t.totalEnemy),
      bossesKilled: null,
      shotsFired: null,
      hits: null,
      damageTaken: t.damage,
      pickups: null,
      coins: null,
      cubes: Math.max(0, g.cubeMax - t.cubes),
      warps: g.bonusLevel ? 1 : 0,
      superbombs: t.bombsUsed,
      specials: null,
    },
    shop,
  });
}

// --- The high-score check ---

/** Why the run can't go on the global leaderboard, or null if it can (D264: no level needed). */
export function ineligibleReason(episode: number): string | null {
  if (!scoresEnabled()) return "off";
  const r = runRecord.current;
  if (!r) return "This game was saved before the global leaderboard, so it isn't eligible.";
  if (r.tainted) return "Cheats or debug tools were used in this run, so it isn't eligible for the global leaderboard.";
  if (r.mode !== "story" || g.twoPlayerMode) return "Only one-player full games go on the global leaderboard.";
  if (r.episode !== episode) return "Only the episode the game started on goes on the global leaderboard.";
  if (!r.token) return "The global leaderboard couldn't be reached when this game started.";
  return null;
}

/** The run as submitted. */
export function runData(r: RunRecord, ended: "quit" | "episode", score: number): RunData {
  const it = g.player[0].items;
  const levels = [...r.levels, ...(ended === "quit" && quitLevel ? [quitLevel] : [])];
  return {
    token: r.token ?? "",
    episode: r.episode,
    difficulty: r.difficulty,
    mode: r.mode,
    tickHz: CLASSIC_TICK_HZ,
    ended,
    ship: it.ship,
    front: { id: it.weapon[FRONT_WEAPON].id, power: it.weapon[FRONT_WEAPON].power },
    rear: { id: it.weapon[REAR_WEAPON].id, power: it.weapon[REAR_WEAPON].power },
    shield: it.shield,
    generator: it.generator,
    sidekicks: [it.sidekick[LEFT_SIDEKICK], it.sidekick[RIGHT_SIDEKICK]],
    levels,
    score,
  };
}

/**
 * The original recorded a high score with this name: send it to the shared list too, unless the run
 * isn't eligible. Resolves with the server's answer, or null (no list, not eligible, unreachable).
 */
export async function submitHighScore(name: string, score: number, episode: number, ended: "quit" | "episode"): Promise<SubmitResult | null> {
  const r = runRecord.current;
  if (!r || ineligibleReason(episode) !== null) return null;
  const run = runData(r, ended, score);
  const hash = await runHash(run);
  return submitScore({ ...run, name: name.trim(), hash });
}

/** After a run ends (back to the title). */
export function endRun(): void {
  quitLevel = null;
  track = null;
}

export { taintRun };
