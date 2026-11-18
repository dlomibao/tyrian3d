// Level reports (POST /api/levels/report, shape in report.d.mts): validate, clamp, store.
// Enums, ids that key the aggregates (episode, difficulty, lvl, mode, via, result), the player id
// and the sidekick pair are checked (a bad one rejects the report); counts are clamped to sane
// ranges, strings cut and limited to printable ASCII, arrays cut (deaths 20, shop 100).
import { DIFFICULTIES } from "./plausibility.mjs";
import { MAX_SCORE, MAX_TICKS, MODES, isUuidV4 } from "./validate.mjs";

const VIA = ["start", "story", "branch", "warp", "retry", "load"];
const RESULTS = ["finished", "died", "quit"];
const TRADE_KINDS = ["buy", "sell", "upgrade", "downgrade"];
const SLOTS = ["ship", "front", "rear", "shield", "generator", "left", "right"];
export const MAX_DEATHS = 20;
export const MAX_TRADES = 100;

class Invalid extends Error {}
const need = (cond, what) => {
  if (!cond) throw new Invalid(what);
};
const isObj = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
const finite = (v) => typeof v === "number" && Number.isFinite(v);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** A required number, truncated and clamped. */
const num = (v, lo, hi, what) => {
  need(finite(v), what);
  return clamp(Math.trunc(v), lo, hi);
};
/** A nullable count: null (not tracked) stays null, a number is clamped, anything else is null. */
const opt = (v, lo, hi) => (finite(v) ? clamp(Math.trunc(v), lo, hi) : null);
/** A string cut to `max` printable ASCII characters. */
const str = (v, max) => (typeof v === "string" ? v.replace(/[^\x20-\x7e]/g, "").slice(0, max).trim() : "");

/** Validate a report body. Returns {ok: true, report} (clamped) or {ok: false, error}. */
export function validateReport(body) {
  try {
    need(isObj(body) && body.v === 1, "v");
    need(typeof body.token === "string" && body.token.length <= 512, "token");
    need(isUuidV4(body.playerId), "playerId");
    const { run, level, loadout, outcome } = body;
    need(isObj(run) && isObj(level) && isObj(loadout) && isObj(outcome), "sections");
    need(Number.isInteger(run.episode) && run.episode >= 1 && run.episode <= 4, "run.episode");
    need(DIFFICULTIES.includes(run.difficulty), "run.difficulty");
    need(MODES.includes(run.mode), "run.mode");
    need(Number.isInteger(level.lvl) && level.lvl >= 1 && level.lvl <= 60, "level.lvl");
    need(VIA.includes(level.via), "level.via");
    need(RESULTS.includes(outcome.result), "outcome.result");
    need(Array.isArray(loadout.sidekicks) && loadout.sidekicks.length === 2, "loadout.sidekicks");
    need(isObj(loadout.front) && isObj(loadout.rear), "loadout.weapons");
    const deaths = (Array.isArray(outcome.deaths) ? outcome.deaths : [])
      .slice(0, MAX_DEATHS)
      .filter(isObj)
      .map((d) => [num(d.tick, 0, MAX_TICKS, "death.tick"), num(d.x, 0, 511, "death.x"), num(d.y, 0, 511, "death.y")]);
    const shop = (Array.isArray(body.shop) ? body.shop : [])
      .slice(0, MAX_TRADES)
      .filter((t) => isObj(t) && TRADE_KINDS.includes(t.kind) && SLOTS.includes(t.slot) && finite(t.id))
      .map((t) => ({ kind: t.kind, slot: t.slot, id: clamp(Math.trunc(t.id), 0, 255), power: opt(t.power, 0, 11) ?? 0, price: opt(t.price, 0, MAX_SCORE) ?? 0 }));
    const report = {
      playerId: body.playerId.toLowerCase(),
      build: str(body.build, 40) || "unknown",
      tainted: body.tainted === true ? 1 : 0,
      episode: run.episode,
      difficulty: run.difficulty,
      difficultyNow: num(run.difficultyNow, 0, 10, "run.difficultyNow"),
      mode: run.mode,
      tickHz: clamp(finite(run.tickHz) ? run.tickHz : 0, 0, 1000),
      lvl: level.lvl,
      name: str(level.name, 32),
      section: num(level.section, 0, 255, "level.section"),
      idx: num(level.index, 0, 1000, "level.index"),
      prev: Number.isInteger(level.prev) && level.prev >= 1 && level.prev <= 60 ? level.prev : null,
      via: level.via,
      ship: num(loadout.ship, 0, 255, "loadout.ship"),
      frontId: num(loadout.front.id, 0, 255, "front.id"),
      frontPower: num(loadout.front.power, 0, 11, "front.power"),
      rearId: num(loadout.rear.id, 0, 255, "rear.id"),
      rearPower: num(loadout.rear.power, 0, 11, "rear.power"),
      sidekickL: num(loadout.sidekicks[0], 0, 255, "sidekicks[0]"),
      sidekickR: num(loadout.sidekicks[1], 0, 255, "sidekicks[1]"),
      shield: num(loadout.shield, 0, 255, "loadout.shield"),
      generator: num(loadout.generator, 0, 255, "loadout.generator"),
      armor: num(loadout.armor, 0, 255, "loadout.armor"),
      credits: num(loadout.credits, 0, MAX_SCORE, "loadout.credits"),
      result: outcome.result,
      ticks: num(outcome.ticks, 0, MAX_TICKS, "outcome.ticks"),
      scoreGained: num(outcome.scoreGained, -MAX_SCORE, MAX_SCORE, "outcome.scoreGained"),
      enemiesKilled: num(outcome.enemiesKilled, 0, 1e6, "outcome.enemiesKilled"),
      enemiesSpawned: num(outcome.enemiesSpawned, 0, 1e6, "outcome.enemiesSpawned"),
      bossesKilled: opt(outcome.bossesKilled, 0, 1000),
      shotsFired: opt(outcome.shotsFired, 0, 1e9),
      hits: opt(outcome.hits, 0, 1e9),
      damageTaken: num(outcome.damageTaken, 0, 1e7, "outcome.damageTaken"),
      pickups: opt(outcome.pickups, 0, 1e6),
      coins: opt(outcome.coins, 0, 1e6),
      cubes: num(outcome.cubes, 0, 1000, "outcome.cubes"),
      warps: num(outcome.warps, 0, 100, "outcome.warps"),
      superbombs: num(outcome.superbombs, 0, 1000, "outcome.superbombs"),
      specials: opt(outcome.specials, 0, 1e6),
      deaths,
      shop,
    };
    return { ok: true, report };
  } catch (e) {
    if (e instanceof Invalid) return { ok: false, error: e.message };
    throw e;
  }
}

const statements = new WeakMap();

/** Insert a validated report (and its shop trades) for run `runId`. */
export function insertReport(db, r, { runId, country, now, month, day }) {
  let s = statements.get(db);
  if (!s) {
    s = {
      level: db.prepare(`INSERT INTO levels (created_at, month, day, run_id, player_id, country, build, tainted,
        episode, difficulty, difficulty_now, mode, tick_hz, lvl, name, section, idx, prev, via,
        ship, front_id, front_power, rear_id, rear_power, sidekick_l, sidekick_r, shield, generator, armor, credits,
        result, ticks, score_gained, enemies_killed, enemies_spawned, bosses_killed, shots_fired, hits, damage_taken,
        pickups, coins, cubes, warps, superbombs, specials, deaths)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`),
      trade: db.prepare("INSERT INTO shop_trades (level_id, tainted, kind, slot, item_id, power, price) VALUES (?, ?, ?, ?, ?, ?, ?)"),
    };
    statements.set(db, s);
  }
  const { lastInsertRowid } = s.level.run(
    now, month, day, runId, r.playerId, country, r.build, r.tainted,
    r.episode, r.difficulty, r.difficultyNow, r.mode, r.tickHz, r.lvl, r.name, r.section, r.idx, r.prev, r.via,
    r.ship, r.frontId, r.frontPower, r.rearId, r.rearPower, r.sidekickL, r.sidekickR, r.shield, r.generator, r.armor, r.credits,
    r.result, r.ticks, r.scoreGained, r.enemiesKilled, r.enemiesSpawned, r.bossesKilled, r.shotsFired, r.hits, r.damageTaken,
    r.pickups, r.coins, r.cubes, r.warps, r.superbombs, r.specials, r.deaths.length ? JSON.stringify(r.deaths) : null,
  );
  for (const t of r.shop) s.trade.run(lastInsertRowid, r.tainted, t.kind, t.slot, t.id, t.power, t.price);
  return Number(lastInsertRowid);
}
