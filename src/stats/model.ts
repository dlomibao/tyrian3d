// What the stats page shows, derived from the summary (pure functions, no DOM; tests/stats/).
// Nothing here estimates or fills in: every figure is a sum, share or ranking of the summary's own
// counts, and a section with no data says so instead of drawing zeros.

import type { Counts, Outcome, StatsSummary } from "./summary";

export const sum = (xs: Iterable<number>): number => {
  let s = 0;
  for (const x of xs) s += x;
  return s;
};

const values = (c: Counts | undefined): number[] => Object.values(c ?? {});

/** An outcome with every field. */
export const outcome = (o: Partial<Outcome> | undefined): Outcome => ({ finished: o?.finished ?? 0, died: o?.died ?? 0, quit: o?.quit ?? 0 });
export const attempts = (o: Outcome): number => o.finished + o.died + o.quit;

function addOutcome(a: Outcome, b: Partial<Outcome>): Outcome {
  const o = outcome(b);
  return { finished: a.finished + o.finished, died: a.died + o.died, quit: a.quit + o.quit };
}

/** Outcomes of one level, over the difficulties in `only` (all when null). */
export function levelOutcome(s: StatsSummary, ep: number | string, lvl: number | string, only: number | null = null): Outcome {
  const byDiff = s.outcomes[ep]?.[lvl] ?? {};
  let o = outcome(undefined);
  for (const [d, x] of Object.entries(byDiff)) if (only === null || Number(d) === only) o = addOutcome(o, x);
  return o;
}

/** Every outcome summed (all episodes, levels and difficulties). */
export function totalOutcome(s: StatsSummary): Outcome {
  let o = outcome(undefined);
  for (const levels of Object.values(s.outcomes)) for (const byDiff of Object.values(levels)) for (const x of Object.values(byDiff)) o = addOutcome(o, x);
  return o;
}

export interface Headline {
  players: number;
  /** Players seen on more than one day. */
  returning: number;
  runs: number;
  reports: number;
  submitted: number;
  cleared: number;
  lost: number;
  quit: number;
  /** Countries other than "unknown" (ZZ). */
  countries: number;
}

export function headline(s: StatsSummary): Headline {
  const o = totalOutcome(s);
  const days = s.players.daysPerPlayer ?? {};
  return {
    players: s.players.total,
    returning: sum(Object.entries(days).filter(([k]) => Number(k) > 1).map(([, n]) => n)),
    runs: s.runs.total,
    reports: s.reports.total,
    submitted: s.runs.submitted,
    cleared: o.finished,
    lost: o.died,
    quit: o.quit,
    countries: Object.keys(s.countries.runs ?? {}).filter((c) => c !== "ZZ").length,
  };
}

/** Nothing recorded yet. */
export const isEmpty = (s: StatsSummary): boolean => s.runs.total === 0 && s.reports.total === 0 && s.players.total === 0;

/** Episodes with any gameplay data, most-played first. */
export function episodesPlayed(s: StatsSummary): { ep: number; attempts: number }[] {
  return Object.keys(s.outcomes)
    .map((ep) => ({ ep: Number(ep), attempts: sum(Object.keys(s.outcomes[ep]).map((lvl) => attempts(levelOutcome(s, ep, lvl)))) }))
    .filter((e) => e.attempts > 0)
    .sort((a, b) => a.ep - b.ep);
}

/** Difficulties with outcomes in an episode, ascending. */
export function difficultiesIn(s: StatsSummary, ep: number): number[] {
  const set = new Set<number>();
  for (const byDiff of Object.values(s.outcomes[ep] ?? {})) for (const d of Object.keys(byDiff)) set.add(Number(d));
  return [...set].sort((a, b) => a - b);
}

export interface LevelRow {
  lvl: number;
  outcome: Outcome;
  attempts: number;
  /** finished / attempts. */
  clearRate: number;
  /** Score gained on finished attempts (all difficulties). */
  score: { n: number; p25?: number; p50?: number; p75?: number; p90?: number } | null;
  deaths: number;
}

/**
 * One row per level played in the episode: in `order` (the script's) first, then any others by
 * lvl. `only` restricts the outcomes to one starting difficulty.
 */
export function levelRows(s: StatsSummary, ep: number, order: number[], only: number | null = null): LevelRow[] {
  const played = Object.keys(s.outcomes[ep] ?? {}).map(Number);
  const rank = (lvl: number) => {
    const i = order.indexOf(lvl);
    return i < 0 ? 1000 + lvl : i;
  };
  return played
    .sort((a, b) => rank(a) - rank(b))
    .map((lvl) => {
      const o = levelOutcome(s, ep, lvl, only);
      const n = attempts(o);
      return {
        lvl,
        outcome: o,
        attempts: n,
        clearRate: n ? o.finished / n : 0,
        score: s.scoreGained[ep]?.[lvl] ?? null,
        deaths: sum((s.deaths[ep]?.[lvl] ?? []).map((d) => d[2])),
      };
    })
    .filter((r) => r.attempts > 0);
}

/** The funnel as [k, players reaching the k-th level, share of those who started], k = 1.. */
export function funnel(s: StatsSummary, ep: number): { k: number; players: number; share: number }[] {
  const f = s.funnel[ep] ?? {};
  const start = f[1] ?? 0;
  if (!start) return [];
  return Object.keys(f)
    .map(Number)
    .sort((a, b) => a - b)
    .map((k) => ({ k, players: f[k], share: f[k] / start }));
}

export interface Branch {
  from: number;
  total: number;
  to: { lvl: number; n: number; share: number }[];
}

/** Levels after which pilots went to more than one next level (the item screen's choices, warps). */
export function branches(s: StatsSummary, ep: number): Branch[] {
  const byFrom = new Map<number, { lvl: number; n: number }[]>();
  for (const p of s.paths[ep] ?? []) {
    if (p.from === null) continue;
    const list = byFrom.get(p.from) ?? [];
    list.push({ lvl: p.to, n: p.n });
    byFrom.set(p.from, list);
  }
  return [...byFrom.entries()]
    .filter(([, to]) => to.length > 1)
    .map(([from, to]) => {
      const total = sum(to.map((t) => t.n));
      return { from, total, to: to.sort((a, b) => b.n - a.n).map((t) => ({ ...t, share: t.n / total })) };
    })
    .sort((a, b) => b.total - a.total);
}

/** First levels of runs: {lvl: runs}. */
export function openers(s: StatsSummary, ep: number): { lvl: number; n: number }[] {
  return (s.paths[ep] ?? []).filter((p) => p.from === null).map((p) => ({ lvl: p.to, n: p.n })).sort((a, b) => b.n - a.n);
}

export interface DeathMap {
  ep: number;
  lvl: number;
  total: number;
  max: number;
  cells: [number, number, number][];
}

/** Each level's death buckets, most deaths first. */
export function deathMaps(s: StatsSummary, ep?: number): DeathMap[] {
  const out: DeathMap[] = [];
  for (const [e, levels] of Object.entries(s.deaths)) {
    if (ep !== undefined && Number(e) !== ep) continue;
    for (const [lvl, cells] of Object.entries(levels)) {
      const total = sum(cells.map((c) => c[2]));
      if (total > 0) out.push({ ep: Number(e), lvl: Number(lvl), total, max: Math.max(...cells.map((c) => c[2])), cells });
    }
  }
  return out.sort((a, b) => b.total - a.total || a.lvl - b.lvl);
}

/** {id: count} summed over every episode and level of a per-level count (ships, weapons). */
export function overall(per: Record<string, Record<string, Counts>>, ep?: number): Counts {
  const out: Counts = {};
  for (const [e, levels] of Object.entries(per)) {
    if (ep !== undefined && Number(e) !== ep) continue;
    for (const counts of Object.values(levels)) for (const [id, n] of Object.entries(counts)) out[id] = (out[id] ?? 0) + n;
  }
  return out;
}

/** A count map ranked, with shares of its total; ids in `skip` are left out of both. */
export function ranked(c: Counts, skip: string[] = []): { id: string; n: number; share: number }[] {
  const entries = Object.entries(c).filter(([id, n]) => !skip.includes(id) && n > 0);
  const total = sum(entries.map(([, n]) => n));
  return entries.map(([id, n]) => ({ id, n, share: total ? n / total : 0 })).sort((a, b) => b.n - a.n || Number(a.id) - Number(b.id));
}

export const SHOP_SLOTS = ["ship", "front", "rear", "shield", "generator", "left", "right"] as const;
export type ShopSlot = (typeof SHOP_SLOTS)[number];

/** Purchases of every slot, ranked: [{slot, id, n}]. Sidekicks left and right count together. */
export function purchases(s: StatsSummary): { slot: ShopSlot | "sidekick"; id: number; n: number }[] {
  const buy = s.shop.buy ?? {};
  const out = new Map<string, { slot: ShopSlot | "sidekick"; id: number; n: number }>();
  for (const [slot, items] of Object.entries(buy)) {
    const group = slot === "left" || slot === "right" ? "sidekick" : (slot as ShopSlot);
    for (const [id, n] of Object.entries(items)) {
      const key = `${group}:${id}`;
      const e = out.get(key) ?? { slot: group, id: Number(id), n: 0 };
      e.n += n;
      out.set(key, e);
    }
  }
  return [...out.values()].filter((e) => e.n > 0).sort((a, b) => b.n - a.n || a.id - b.id);
}

/** Trades of a kind ("upgrade", "sell", ...) summed. */
export const tradeCount = (s: StatsSummary, kind: string): number => sum(Object.values(s.shop[kind] ?? {}).flatMap((items) => values(items)));

/** Every UTC day from the first in `perDay` to `last` (YYYY-MM-DD), missing days as zeros. */
export function dailySeries(perDay: StatsSummary["players"]["perDay"], last: string): { day: string; players: number; new: number; returning: number }[] {
  if (perDay.length === 0) return [];
  const byDay = new Map(perDay.map((d) => [d.day, d]));
  const out = [];
  const end = Date.parse(`${last > perDay.at(-1)!.day ? last : perDay.at(-1)!.day}T00:00:00Z`);
  for (let t = Date.parse(`${perDay[0].day}T00:00:00Z`); t <= end; t += 86400000) {
    const day = new Date(t).toISOString().slice(0, 10);
    const d = byDay.get(day);
    out.push({ day, players: d?.players ?? 0, new: d?.new ?? 0, returning: d?.returning ?? 0 });
  }
  return out;
}

/** A small-count distribution folded at `cap` ("5+"): [{label, n}]. */
export function folded(c: Counts, cap: number): { label: string; n: number }[] {
  const out: { label: string; n: number }[] = [];
  for (let k = 1; k < cap; k++) out.push({ label: String(k), n: c[k] ?? 0 });
  out.push({ label: `${cap}+`, n: sum(Object.entries(c).filter(([k]) => Number(k) >= cap).map(([, n]) => n)) });
  return out;
}

/** The fewest attempts a level needs before the page calls it the deadliest or easiest. */
export const MIN_ATTEMPTS = 10;

export interface Highlights {
  deadliest: { ep: number; lvl: number; rate: number; attempts: number } | null;
  topScore: { ep: number; lvl: number; p50: number; n: number } | null;
  topShip: { id: string; share: number } | null;
  topWeapon: { id: string; share: number } | null;
}

/** A few facts worth a line, each only when the data supports it. */
export function highlights(s: StatsSummary): Highlights {
  let deadliest: Highlights["deadliest"] = null;
  let topScore: Highlights["topScore"] = null;
  for (const [ep, levels] of Object.entries(s.outcomes)) {
    for (const lvl of Object.keys(levels)) {
      const o = levelOutcome(s, ep, lvl);
      const n = attempts(o);
      if (n >= MIN_ATTEMPTS) {
        const rate = o.died / n;
        if (!deadliest || rate > deadliest.rate) deadliest = { ep: Number(ep), lvl: Number(lvl), rate, attempts: n };
      }
    }
  }
  for (const [ep, levels] of Object.entries(s.scoreGained)) {
    for (const [lvl, p] of Object.entries(levels)) {
      if (p.n >= 5 && p.p50 !== undefined && (!topScore || p.p50 > topScore.p50)) topScore = { ep: Number(ep), lvl: Number(lvl), p50: p.p50, n: p.n };
    }
  }
  const ships = ranked(overall(s.ships), ["0"]);
  const weapons = ranked(overall(s.weapons), ["0"]);
  const enough = sum(ships.map((x) => x.n)) >= MIN_ATTEMPTS;
  return {
    deadliest: deadliest && deadliest.rate > 0 ? deadliest : null,
    topScore,
    topShip: enough && ships[0] ? { id: ships[0].id, share: ships[0].share } : null,
    topWeapon: enough && weapons[0] ? { id: weapons[0].id, share: weapons[0].share } : null,
  };
}
