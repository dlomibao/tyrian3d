// Rewrites the inventory-derived cells of docs/agents/MILESTONES.md from docs/roadmap/inventory.json.
// Usage: node tools/milestones-tables.mjs [inventory.json] [--check]
import { readFileSync, writeFileSync } from "node:fs";
const args = process.argv.slice(2);
const jsonPath = args.find((a) => a.endsWith(".json")) ?? "docs/roadmap/inventory.json";
const mdPath = "docs/agents/MILESTONES.md";
const inv = JSON.parse(readFileSync(jsonPath, "utf8"));
const unit = new Map(inv.units.map((u) => [u.id, u]));
const shot = new Map(inv.shots.map((s) => [s.id, s]));
const lv = new Map(inv.levels.map((l) => [l.id.replace(".", "-"), l]));

function rowFor(l) {
  const us = l.units.map((id) => unit.get(id)).filter((u) => u && u.kind !== "pickup");
  const shared = us.filter((u) => u.levels.length > 1).length;
  const uniq = us.length - shared;
  const fl = us.filter((u) => u.status === "flagship").length;
  const uniqUnfinished = us.filter((u) => u.levels.length === 1 && u.status !== "flagship").length;
  const T = l.layers.reduce((a, x) => a + x.tiles, 0), H = l.layers.reduce((a, x) => a + x.hd, 0), C = l.layers.reduce((a, x) => a + x.covered, 0);
  const pk = l.pickups.map((id) => unit.get(id)).filter((u) => u && u.status !== "flat" && u.status !== "blank").length;
  const sh = l.enemyShots.filter((id) => shot.get(id)?.status !== "flat").length;
  const per = l.episode <= 2 ? 6 : 4;
  return {
    models: `${us.length} / ${shared} / ${uniq} / ${fl}`,
    hd: H === T ? `done (${T}/${T})` : `${H}/${T}`,
    flat: pk + sh === 0 ? "done" : `todo: ${pk} pickup units, ${sh} shots`,
    agents: `~${3 + uniqUnfinished * per}`,
    uniqUnfinished, covered: C === T,
  };
}

const lines = readFileSync(mdPath, "utf8").split("\n");
const sums = { 1: 0, 2: 0, 3: 0, 4: 0 };
for (const l of inv.levels) sums[l.episode] += rowFor(l).uniqUnfinished;
let n = 0;
const out = lines.map((ln) => {
  const m = ln.match(/^  \| (\d-\d+) \|/);
  if (!m || m[1] === "1-9" || !lv.has(m[1])) return ln;
  const r = rowFor(lv.get(m[1]));
  const c = ln.split(" | ");
  // cols: id, name, tileset, models, structures, hd, flat, agents, status
  if (c.length < 10) return ln;
  c[4] = r.models; c[6] = r.hd; c[7] = r.flat; c[8] = r.agents;
  n++;
  return c.join(" | ");
});
// Asset-group rows and totals.
const enemy = inv.units.filter((u) => u.kind !== "pickup");
const shared = enemy.filter((u) => u.levels.length > 1);
const sharedTodo = shared.filter((u) => u.status !== "flagship");
const multiEp = sharedTodo.filter((u) => u.episodes.length > 1).length;
const epHist = [1, 2, 3, 4].map((k) => sharedTodo.filter((u) => u.episodes.length === k).length);
const top = [...sharedTodo].sort((a, b) => b.levels.length - a.levels.length || a.id.localeCompare(b.id)).slice(0, 5).map((u) => `${u.id} (${u.levels.length} levels)`).join(", ");
const flagAll = enemy.filter((u) => u.status === "flagship").length;
const picks = inv.units.filter((u) => u.kind === "pickup");
const picksTodo = picks.filter((u) => u.status !== "flat" && u.status !== "blank");
const frames = (u) => Object.values(u.frames).reduce((a, f) => a + f.length, 0);
const shotsFlat = inv.shots.filter((s) => s.status === "flat").length;
const per = (e) => (e <= 2 ? 6 : 4);
const epAgents = [1, 2, 3, 4].map((e) => inv.levels.filter((l) => l.episode === e).reduce((a, l) => a + 3 + rowFor(l).uniqUnfinished * per(e), 0));
const uniqTotal = sums[1] + sums[2] + sums[3] + sums[4];
const idx = (e) => `| M${e} |`;
const patched = out.map((ln) => {
  if (ln.startsWith("  | Shared enemy/boss models |")) {
    const c = ln.split(" | ");
    c[2] = `${sharedTodo.length} enemy units not flagship-done, used by ≥ 2 levels (${multiEp} of them span ≥ 2 episodes). Top: ${top}`;
    c[3] = `${epHist[0]} units in 1 episode, ${epHist[1]} in 2, ${epHist[2]} in 3, ${epHist[3]} in 4`;
    c[4] = `${shared.length - sharedTodo.length} of ${shared.length} shared units`;
    c[6] = `~${sharedTodo.length * 6} (${sharedTodo.length} x ~6)`;
    return c.join(" | ");
  }
  let m = ln.match(/^  \| Tileset `(shapes.)`( \(other levels\))? \| /);
  if (m) {
    const t = inv.tilesets.find((x) => x.id === m[1]);
    if (t) {
      const left = t.tiles.map((n, L) => n - t.covered[L]);
      return ln.replace(/\d+ \/ \d+ \/ \d+ = \d+ tiles left/, `${left.join(" / ")} = ${left.reduce((a, b) => a + b, 0)} tiles left`);
    }
  }
  if (ln.startsWith("  | Shot frames |")) return ln.replace(/\| \d+ without flat art \(of \d+; \d+ flat\)/, `| ${inv.shots.length - shotsFlat} without flat art (of ${inv.shots.length}; ${shotsFlat} flat)`);
  if (ln.startsWith("  | Pickup frames |")) return ln.replace(/\| \d+ pickup units without flat art \(\d+ frames; of \d+ units, \d+ flat\)/, `| ${picksTodo.length} pickup units without flat art (${picksTodo.reduce((a, u) => a + frames(u), 0)} frames; of ${picks.length} units, ${picks.length - picksTodo.length} flat)`);
  if (ln.startsWith("| M0 |")) return ln.replace(/\| \d+ shared \| ~\d+ for/, `| ${sharedTodo.length} shared | ~${sharedTodo.length * 6} for`);
  m = ln.match(/^\| M([1-4]) \| (\d+) \| \d+ \| \d+ \|$/);
  if (m) return `| M${m[1]} | ${m[2]} | ${sums[m[1]]} | ${epAgents[m[1] - 1]} |`;
  if (ln.startsWith("M1-M4 together:")) return `M1-M4 together: ${epAgents.reduce((a, b) => a + b, 0)} agents; ${uniqTotal} unique + ${sharedTodo.length} shared = ${uniqTotal + sharedTodo.length} unfinished enemy units (${enemy.length} enemy units − ${flagAll} flagship, per \`inventory.json\`).`;
  return ln;
});
const text = patched.join("\n");
if (args.includes("--check")) console.log(`${n} rows`, JSON.stringify(sums));
else writeFileSync(mdPath, text);
console.log(`updated ${n} level rows; unique unfinished per episode ${JSON.stringify(sums)}`);
