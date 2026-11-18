// Strict validation of POST /api/runs and POST /api/scores bodies. Unknown keys are ignored; the
// values that are kept are the client's own (unchanged), so the run hash can be recomputed on them.
import { DIFFICULTIES } from "./plausibility.mjs";

export const MODES = ["story", "arcade", "twoPlayer", "superArcade", "superTyrian"];
export const MAX_SCORE = 2 ** 31 - 1;
export const MAX_TICKS = 10_000_000;
export const NAME_MAX = 28; // HIGH_SCORE_NAME_MAX (src/sim/highscores.ts)

/** The game's name-entry letters above ASCII (src/sim/highscores.ts CP437_HIGH). */
const CP437_HIGH = "ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿";

/** highScoreNameAccepts (src/sim/highscores.ts): space, ASCII 33..125 but &<>@^_`, the CP437 letters. */
export function nameCharAccepted(ch) {
  if (ch === " ") return true;
  if (CP437_HIGH.includes(ch)) return true;
  if (ch.length !== 1) return false;
  const c = ch.charCodeAt(0);
  return c >= 33 && c <= 125 && !"&<>@^_`".includes(ch);
}

/** Drop the characters the game wouldn't accept, collapse spaces, trim, cut to 28. */
export function sanitizeName(raw) {
  if (typeof raw !== "string") return "";
  const kept = [...raw.slice(0, 256)].filter(nameCharAccepted).join("");
  return [...kept.replace(/ {2,}/g, " ").trim()].slice(0, NAME_MAX).join("").trim();
}

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const isUuidV4 = (s) => typeof s === "string" && UUID_V4.test(s);

const isInt = (v, lo, hi) => Number.isSafeInteger(v) && v >= lo && v <= hi;
const isObj = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
/** Printable ASCII, 1..max characters (build ids). */
export const isPrintable = (s, max) => typeof s === "string" && s.length >= 1 && s.length <= max && /^[\x20-\x7e]+$/.test(s);

class Invalid extends Error {
  constructor(reason, message) {
    super(message);
    this.reason = reason;
  }
}
const need = (cond, what) => {
  if (!cond) throw new Invalid("invalid", what);
};

/** POST /api/runs: {episode, difficulty, mode, build, playerId?} -> {ok, value} | {ok: false, reason, error}. */
export function validateRunRequest(body) {
  try {
    need(isObj(body), "body");
    need(isInt(body.episode, 1, 4), "episode");
    need(DIFFICULTIES.includes(body.difficulty), "difficulty");
    need(MODES.includes(body.mode), "mode");
    need(isPrintable(body.build, 40), "build");
    need(body.playerId === undefined || body.playerId === null || isUuidV4(body.playerId), "playerId");
    return {
      ok: true,
      value: { episode: body.episode, difficulty: body.difficulty, mode: body.mode, build: body.build, playerId: body.playerId ? body.playerId.toLowerCase() : null },
    };
  } catch (e) {
    if (e instanceof Invalid) return { ok: false, reason: e.reason, error: e.message };
    throw e;
  }
}

const item = (v, what) => {
  need(isObj(v) && isInt(v.id, 0, 255) && isInt(v.power, 0, 11), what);
  return { id: v.id, power: v.power };
};

/**
 * POST /api/scores: RunData + name + hash. `tickHz` is maxScores.json's. Returns
 * {ok: true, run, name, hash} or {ok: false, reason: "invalid" | "mode", error}.
 */
export function validateScore(body, tickHz) {
  try {
    need(isObj(body), "body");
    need(typeof body.token === "string" && body.token.length >= 1 && body.token.length <= 512, "token");
    need(isInt(body.episode, 1, 4), "episode");
    need(DIFFICULTIES.includes(body.difficulty), "difficulty");
    need(typeof body.mode === "string", "mode");
    // The bounds only model a one-player full game.
    if (body.mode !== "story") throw new Invalid("mode", "only story-mode runs are ranked");
    need(typeof body.tickHz === "number" && Math.abs(body.tickHz - tickHz) <= 1e-6, "tickHz");
    need(body.ended === "quit" || body.ended === "episode", "ended");
    need(isInt(body.ship, 0, 255), "ship");
    need(isInt(body.shield, 0, 255), "shield");
    need(isInt(body.generator, 0, 255), "generator");
    need(Array.isArray(body.sidekicks) && body.sidekicks.length === 2 && body.sidekicks.every((s) => isInt(s, 0, 255)), "sidekicks");
    need(Array.isArray(body.levels) && body.levels.length <= 60, "levels");
    const levels = body.levels.map((l, i) => {
      need(isObj(l) && isInt(l.lvl, 1, 60) && isInt(l.ticks, 0, MAX_TICKS) && isInt(l.score, 0, MAX_SCORE) && typeof l.done === "boolean", `levels[${i}]`);
      return { lvl: l.lvl, ticks: l.ticks, score: l.score, done: l.done };
    });
    need(isInt(body.score, 0, MAX_SCORE), "score");
    need(typeof body.hash === "string" && /^[0-9a-f]{64}$/.test(body.hash), "hash");
    need(typeof body.name === "string", "name");
    const name = sanitizeName(body.name);
    need(name.length > 0, "name");
    const run = {
      token: body.token,
      episode: body.episode,
      difficulty: body.difficulty,
      mode: body.mode,
      tickHz: body.tickHz,
      ended: body.ended,
      ship: body.ship,
      front: item(body.front, "front"),
      rear: item(body.rear, "rear"),
      shield: body.shield,
      generator: body.generator,
      sidekicks: [body.sidekicks[0], body.sidekicks[1]],
      levels,
      score: body.score,
    };
    return { ok: true, run, name, hash: body.hash };
  } catch (e) {
    if (e instanceof Invalid) return { ok: false, reason: e.reason, error: e.message };
    throw e;
  }
}
