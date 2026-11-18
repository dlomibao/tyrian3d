// Whether a submitted run could have happened, from the level data alone (maxScores.json, made by
// tools/maxScores/maxScores.ts from the game data). No replay: the checks are
//
//  1. path   the levels form a path through the episode's level graph (story order, the item
//            screen's next-level choices, the script's jumps, in-level warps), for the run's
//            difficulty class (`]H[`/`]h[` branch on Hard). A run that ended with the episode must
//            end on a level the episode's end can follow.
//  2. ticks  each finished level ran at least its tick floor (the fewest ticks to its end at the
//            fastest scroll, minus 3%), and no level ran past its ceiling (levels that can't stall).
//  3. wall   the summed ticks fit the wall time since the run token: ticks / tickHz <= elapsed x
//            1.02 + 60 s. The port has one speed (OpenTyrian's Normal, ~34.8 Hz); the only way to
//            run faster is the debug console, which taints the run.
//  4. cap    each level's cumulative score is at most the start total plus every level's bound so
//            far. A level's bound is static + perTick x ticks + randomValue x (a 6-sigma bound on
//            its random spawns), at the difficulty level the run can have reached by then (raised
//            from the cumulative bound, as adjust_difficulty raises it from the score), plus
//            ENGAGE's gear and galaga's extra lives where they apply.
//            Each level's own gain (from the previous level's end, the item screen included) is
//            also at most its bound (plus the item screen's itemSurplus).
//  5. rate   each level's score gain per tick is at most 1.25 x its bound at its tick floor divided
//            by the floor (levels with a floor). This is what catches a quit level's score: it
//            has no floor of its own, so a big gain in a few ticks fails here.
// Every bound is an upper bound (see the tool's header), so an honest run always passes; a run
// that fails was edited, or played with something that changes the game.

/** Initial difficulties difficultySelect offers (Easy, Normal, Hard, Impossible, Suicide, Lord of Game). */
export const DIFFICULTIES = [1, 2, 3, 4, 6, 8];

/** adjust_difficulty's score_multiplier (mainint.c), by initial difficulty. */
const SCORE_MULTIPLIER = [0, 0.4, 0.8, 1.3, 1.6, 2, 2, 3, 3, 3];

/** adjust_difficulty for one player: the difficulty level a total score raises the game to. */
export function difficultyForScore(score, initialDifficulty) {
  const s = Math.round(Math.fround(score * Math.fround(SCORE_MULTIPLIER[initialDifficulty] ?? 3)));
  const steps = [40000, 70000, 150000, 300000, 600000, 1000000, 2000000, 3000000];
  let d = 1;
  for (const t of steps) if (s >= t) d++;
  return d; // 1 (Easy) .. 9 (Nortaneous)
}

/** At most how many random spawns N ticks at chance p give, but for a 1e-9 tail: a 6-sigma bound. */
export function randomSpawnBound(n, p) {
  if (!(p > 0) || n <= 0) return 0;
  return Math.min(n, Math.ceil(n * p + 6 * Math.sqrt(n * p * (1 - p)) + 6));
}

/** The bound on one level's score over `ticks` ticks, starting at difficulty level d. */
export function levelCap(level, d, ticks) {
  const i = Math.min(Math.max(d, 1), 10);
  return level.static[i] + level.perTick[i] * ticks + level.random.value[i] * randomSpawnBound(ticks, level.random.p);
}

/** Margins: the tick floor's slack, the wall clock's, and the score rate's. */
export const MARGINS = { floor: 0.97, wallFactor: 1.02, wallSlackS: 60, rate: 1.25 };

/**
 * Check a run against the episode data. `run` holds episode, difficulty, ended ("quit" or
 * "episode"), levels [{lvl, ticks, score, done}] and score; `elapsedMs` is the wall time since its
 * token was issued. Returns { ok: true, cap } or { ok: false, reason, detail }.
 */
export function checkRun(data, run, elapsedMs) {
  const fail = (reason, detail) => ({ ok: false, reason, detail });
  const ep = data.episodes[run.episode];
  if (!ep) return fail("episode", `no data for episode ${run.episode}`);
  if (!DIFFICULTIES.includes(run.difficulty)) return fail("difficulty", `difficulty ${run.difficulty}`);
  const graph = run.difficulty >= 3 ? ep.graph.hi : ep.graph.lo;
  const levels = run.levels;

  // 1. path (D264: no level needed; a run quit from the first item screen is bounded by the start total)
  for (let i = 0; i < levels.length; i++) {
    const l = levels[i];
    if (!ep.levels[l.lvl]) return fail("path", `level ${l.lvl} isn't in episode ${run.episode}`);
    const allowed = i === 0 ? graph.start : graph.next[levels[i - 1].lvl] ?? [];
    if (!allowed.includes(l.lvl)) return fail("path", i === 0 ? `level ${l.lvl} can't start the episode` : `level ${l.lvl} can't follow ${levels[i - 1].lvl}`);
    if (!l.done && i !== levels.length - 1) return fail("path", `unfinished level ${l.lvl} before the last`);
  }
  if (run.ended === "episode") {
    const last = levels.at(-1);
    if (!last || !last.done || !graph.end.includes(last.lvl)) return fail("path", "the episode can't end after the last level");
  }

  // 2. ticks
  for (const l of levels) {
    const b = ep.levels[l.lvl];
    if (l.done && l.ticks < Math.floor(b.minTicks * MARGINS.floor)) return fail("ticks", `level ${l.lvl} in ${l.ticks} ticks, floor ${b.minTicks}`);
    if (b.maxTicks !== null && l.ticks > b.maxTicks) return fail("ticks", `level ${l.lvl} ran ${l.ticks} ticks, ceiling ${b.maxTicks}`);
  }

  // 3. wall
  const ticks = levels.reduce((a, l) => a + l.ticks, 0);
  const playedS = ticks / data.tickHz;
  const allowedS = (elapsedMs / 1000) * MARGINS.wallFactor + MARGINS.wallSlackS;
  if (playedS > allowedS) return fail("wall", `${Math.round(playedS)} s of play in ${Math.round(elapsedMs / 1000)} s`);

  // 4. cap and 5. rate
  const c = ep.constants;
  let cap = c.startTotal + c.itemSurplus;
  let prev = c.startTotal;
  let d = run.difficulty;
  for (const l of levels) {
    const b = ep.levels[l.lvl];
    let lc = levelCap(b, d, l.ticks) + (b.engage ? c.engage : 0);
    // Galaga mode: an extra life or 1000 per 25000 of cash (thresholds 10000, 20000, then +25000).
    if (b.galaga) lc += 1000 * (Math.ceil((cap + lc) / 25000) + 2);
    cap += lc;
    if (l.score > cap) return fail("cap", `level ${l.lvl}: score ${l.score} over the bound ${Math.round(cap)}`);
    // The level's own gain (with the item screen before it, which can add at most itemSurplus).
    const gain = l.score - prev;
    if (gain > lc + c.itemSurplus) return fail("level", `level ${l.lvl}: gained ${gain}, its bound ${Math.round(lc)}`);
    if (b.minTicks > 0 && l.ticks > 0) {
      const floorCap = levelCap(b, d, b.minTicks) + (b.engage ? c.engage : 0) + (b.galaga ? lc - levelCap(b, d, l.ticks) - (b.engage ? c.engage : 0) : 0);
      if (gain / l.ticks > (MARGINS.rate * floorCap) / b.minTicks) return fail("rate", `level ${l.lvl}: ${Math.round(gain / l.ticks)} per tick`);
    }
    prev = l.score;
    d = Math.max(d, difficultyForScore(cap, run.difficulty));
  }
  if (run.score > cap) return fail("cap", `score ${run.score} over the bound ${Math.round(cap)}`);
  return { ok: true, cap: Math.round(cap) };
}
