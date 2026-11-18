// GET /api/stats/summary: aggregates over the level reports and runs. Gameplay aggregates leave
// out tainted (cheated/debug) reports; the player and country counts include them. Every query is
// a GROUP BY over an indexed column or a single pass; the server caches the result (~10 min).

export const DEATH_BUCKET_PX = 16;
const PERCENTILES = [0.25, 0.5, 0.75, 0.9];

/** Group rows into nested objects: group(rows, ["episode", "lvl"], fn) -> {1: {9: fn(rows)}}. */
function nest(rows, keys, leaf) {
  const out = {};
  for (const r of rows) {
    let o = out;
    for (const k of keys.slice(0, -1)) o = o[r[k]] ??= {};
    const last = r[keys.at(-1)];
    o[last] = leaf(r, o[last]);
  }
  return out;
}

export function computeSummary(db, now) {
  const all = (sql, ...params) => db.prepare(sql).all(...params);
  const one = (sql) => db.prepare(sql).get();

  const reports = one("SELECT count(*) AS total, coalesce(sum(tainted), 0) AS tainted FROM levels");
  const runs = one("SELECT count(*) AS total, count(used_at) AS submitted FROM runs");

  // Path transitions prev -> lvl (a retry isn't a transition).
  const paths = {};
  for (const r of all(`SELECT episode, prev, lvl, count(*) AS n FROM levels
                       WHERE tainted = 0 AND via != 'retry' GROUP BY episode, prev, lvl ORDER BY episode, n DESC`)) {
    (paths[r.episode] ??= []).push({ from: r.prev, to: r.lvl, n: r.n });
  }

  // Outcomes per level and initial difficulty.
  const outcomes = nest(
    all(`SELECT episode, lvl, difficulty, result, count(*) AS n FROM levels
         WHERE tainted = 0 GROUP BY episode, lvl, difficulty, result`),
    ["episode", "lvl", "difficulty"],
    (r, o = { finished: 0, died: 0, quit: 0 }) => ({ ...o, [r.result]: r.n }),
  );

  // Death positions in 16 px buckets: [bx, by, n] with bx = floor(x / 16).
  const deaths = {};
  for (const r of all(`SELECT l.episode, l.lvl,
                              CAST(json_extract(d.value, '$[1]') AS INTEGER) / ${DEATH_BUCKET_PX} AS bx,
                              CAST(json_extract(d.value, '$[2]') AS INTEGER) / ${DEATH_BUCKET_PX} AS by,
                              count(*) AS n
                       FROM levels AS l, json_each(l.deaths) AS d
                       WHERE l.tainted = 0 AND l.deaths IS NOT NULL
                       GROUP BY l.episode, l.lvl, bx, by`)) {
    ((deaths[r.episode] ??= {})[r.lvl] ??= []).push([r.bx, r.by, r.n]);
  }

  // Front weapon and ship popularity per level: {id: count}.
  const counts = (col) =>
    nest(
      all(`SELECT episode, lvl, ${col} AS id, count(*) AS n FROM levels WHERE tainted = 0 GROUP BY episode, lvl, ${col}`),
      ["episode", "lvl", "id"],
      (r) => r.n,
    );
  const weapons = counts("front_id");
  const ships = counts("ship");

  // score_gained percentiles per level, finished levels only (nearest rank, low side).
  const scoreGained = {};
  for (const r of all(`SELECT episode, lvl, n, rn, score_gained FROM (
                         SELECT episode, lvl, score_gained,
                                row_number() OVER (PARTITION BY episode, lvl ORDER BY score_gained) AS rn,
                                count(*) OVER (PARTITION BY episode, lvl) AS n
                         FROM levels WHERE tainted = 0 AND result = 'finished')
                       WHERE rn IN (1 + CAST(0.25 * (n - 1) AS INTEGER), 1 + CAST(0.5 * (n - 1) AS INTEGER),
                                    1 + CAST(0.75 * (n - 1) AS INTEGER), 1 + CAST(0.9 * (n - 1) AS INTEGER))`)) {
    const o = ((scoreGained[r.episode] ??= {})[r.lvl] ??= { n: r.n });
    for (const p of PERCENTILES) if (r.rn === 1 + Math.trunc(p * (r.n - 1))) o[`p${Math.round(p * 100)}`] = r.score_gained;
  }

  // Shop trades by kind, slot and item: {buy: {front: {id: count}}}.
  const shop = nest(
    all(`SELECT kind, slot, item_id, count(*) AS n FROM shop_trades WHERE tainted = 0 GROUP BY kind, slot, item_id`),
    ["kind", "slot", "item_id"],
    (r) => r.n,
  );

  // Countries (all reports, tainted included: this is reach, not gameplay).
  const countries = {
    runs: Object.fromEntries(all("SELECT country, count(*) AS n FROM runs GROUP BY country ORDER BY n DESC").map((r) => [r.country, r.n])),
    reports: Object.fromEntries(all("SELECT country, count(*) AS n FROM levels GROUP BY country ORDER BY n DESC").map((r) => [r.country, r.n])),
    reportsByMonth: nest(all("SELECT month, country, count(*) AS n FROM levels GROUP BY month, country"), ["month", "country"], (r) => r.n),
    runsByMonth: nest(
      all("SELECT strftime('%Y-%m', issued_at / 1000, 'unixepoch') AS month, country, count(*) AS n FROM runs GROUP BY month, country"),
      ["month", "country"],
      (r) => r.n,
    ),
  };

  // Players (stats sharing on): unique per day/month, new vs returning (returning = first seen on an
  // earlier day; per month: first seen in an earlier month).
  const firstSeen = "SELECT player_id, min(day) AS first FROM levels GROUP BY player_id";
  const perDay = all(`SELECT p.day, count(*) AS players, sum(p.day = f.first) AS new, sum(p.day > f.first) AS "returning"
                      FROM (SELECT DISTINCT player_id, day FROM levels) AS p JOIN (${firstSeen}) AS f USING (player_id)
                      GROUP BY p.day ORDER BY p.day`);
  const perMonth = all(`SELECT p.month, count(*) AS players, sum(p.month = substr(f.first, 1, 7)) AS new,
                               sum(p.month > substr(f.first, 1, 7)) AS "returning"
                        FROM (SELECT DISTINCT player_id, month FROM levels) AS p JOIN (${firstSeen}) AS f USING (player_id)
                        GROUP BY p.month ORDER BY p.month`);
  const distribution = (sql) => Object.fromEntries(all(sql).map((r) => [r.k, r.n]));
  const players = {
    total: one("SELECT count(DISTINCT player_id) AS n FROM levels").n,
    perDay,
    perMonth,
    // {runs: players}: how many players started 1, 2, ... runs.
    runsPerPlayer: distribution(`SELECT k, count(*) AS n FROM (SELECT count(*) AS k FROM runs WHERE player_id IS NOT NULL GROUP BY player_id)
                                 GROUP BY k ORDER BY k`),
    // {days: players}: distinct play days per player.
    daysPerPlayer: distribution(`SELECT k, count(*) AS n FROM (SELECT count(DISTINCT day) AS k FROM levels GROUP BY player_id)
                                 GROUP BY k ORDER BY k`),
  };

  // Funnel: each player's furthest level per episode (max idx + 1), then players reaching >= k.
  const funnel = {};
  const furthest = all(`SELECT episode, k, count(*) AS n FROM (
                          SELECT episode, max(idx) + 1 AS k FROM levels WHERE tainted = 0 GROUP BY player_id, episode)
                        GROUP BY episode, k ORDER BY episode, k DESC`);
  for (const r of furthest) {
    const f = (funnel[r.episode] ??= {});
    f[r.k] = r.n;
  }
  for (const ep of Object.keys(funnel)) {
    const ks = Object.keys(funnel[ep]).map(Number).sort((a, b) => b - a);
    const max = ks[0];
    const reached = {};
    let acc = 0;
    for (let k = max; k >= 1; k--) {
      acc += funnel[ep][k] ?? 0;
      reached[k] = acc;
    }
    funnel[ep] = reached;
  }

  return {
    generatedAt: new Date(now).toISOString(),
    deathBucketPx: DEATH_BUCKET_PX,
    reports,
    runs,
    paths,
    outcomes,
    deaths,
    weapons,
    ships,
    scoreGained,
    shop,
    countries,
    players,
    funnel,
  };
}
