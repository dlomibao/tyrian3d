// `?debug=play&armor=`: hold the bot's armour at N, or a schedule `N@T,N@T,...` (hold N from tick T
// on), e.g. `1@0,4@330,8@420` for a pickup (D90). Without the parameter nothing is held (-1), and the
// harness keeps the armour topped up instead. Empty and malformed entries are ignored: `Number("")`
// is 0, so an absent parameter once parsed as "hold at 0" and every capture showed heavy wear (D119).

export interface ArmorHold {
  n: number;
  at: number;
}

/** The schedule from `&armor=` (null or "" when absent), sorted by tick. */
export function parseArmorPlan(param: string | null): ArmorHold[] {
  const num = (s: string | undefined) => (s !== undefined && s.trim() !== "" ? Number(s) : Number.NaN);
  return (param ?? "")
    .split(",")
    .map((entry) => entry.split("@"))
    .map(([n, at]) => ({ n: num(n), at: num(at) }))
    .filter(({ n }) => Number.isFinite(n) && n >= 0)
    .map(({ n, at }) => ({ n, at: Number.isFinite(at) ? at : 0 }))
    .sort((a, b) => a.at - b.at);
}

/** The armour held at `tick`, or -1 when the plan holds nothing then. */
export function armorAt(plan: readonly ArmorHold[], tick: number): number {
  return plan.reduce((v, s) => (tick >= s.at ? s.n : v), -1);
}
