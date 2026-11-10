// Dump, per inventory unit, the enemy types that draw it, their movement/fire data (launcher, motion px/tick) and the layers of the events that spawn them.
// Usage: NODE_OPTIONS= node tools/enemy_behaviour.mjs <unit-id>...   (needs ./data and docs/roadmap/inventory.json; OUT=file.json writes JSON there; D122).
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
process.chdir(ROOT);
const { createServer } = await import(join(ROOT, "node_modules/vite/dist/node/index.js"));
const server = await createServer({ configFile: false, root: ROOT, logLevel: "error", server: { middlewareMode: true, hmr: false, ws: false, watch: null }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
const data = await server.ssrLoadModule("/src/data/index.ts");
const resources = await server.ssrLoadModule("/src/sim/resources.ts");
const files = { get: (n) => { const p = join(ROOT, "data", n); return existsSync(p) ? new Uint8Array(readFileSync(p)) : undefined; } };
const inv = JSON.parse(readFileSync(join(ROOT, "docs/roadmap/inventory.json")));
const units = new Map(inv.units.map((u) => [u.id, u]));
const want = process.argv.slice(2);
const LAYER = { 6: "ground(25)", 7: "top(50)", 10: "ground2(75)", 15: "sky(0)", 17: "groundBottom", 18: "skyBottom", 23: "sky?23", 32: "top32", 56: "ground2-56", 12: "group12" };
const names = {};
for (const l of inv.levels) names[l.id] = l.name;
const out = {};
const resBy = {}, lvls = {};
for (const ep of [1, 3]) {
  resBy[ep] = resources.buildResources(files, ep);
  const f = files.get(`tyrian${ep}.lvl`);
  const { lvlPos, lvlNum } = data.readLevelPositions(f);
  lvls[ep] = [];
  for (let n = 1; n <= Math.floor(lvlNum / 2); n++) lvls[ep][n] = data.parseLevel(f, lvlPos[(n - 1) * 2]);
}
for (const id of want) {
  const u = units.get(id);
  if (!u) { out[id] = "missing"; continue; }
  const types = u.types.map((t) => { const [e, n] = t.split(":"); return { ep: Number(e.replace("e", "").split("-")[0]), t: Number(n), raw: t }; });
  const rows = [];
  for (const { t, raw } of types) {
    const ep = 1;
    const d = resBy[ep].items.enemies[t];
    const spawns = {};
    for (const lid of u.levels) {
      const [e, n] = lid.split(".").map(Number);
      if (e !== 1 && e !== 3) continue;
      const lv = lvls[e][n];
      for (const ev of lv.events) {
        let hit = false, kindk = LAYER[ev.eventType];
        if ([6, 7, 10, 15, 17, 18, 23, 32, 56].includes(ev.eventType) && ev.eventDat === t) hit = true;
        if (ev.eventType === 12 && t >= ev.eventDat && t < ev.eventDat + 4) { hit = true; kindk = "group12/" + ({0:"sky?",1:"ground",2:"sky",3:"top",4:"ground2"}[ev.eventDat6] ?? ev.eventDat6); }
        if (!hit) continue;
        const k = `${lid} ${names[lid]}: ${kindk}`;
        const s = (spawns[k] ??= { n: 0, x: new Set(), dat3: new Set(), dat5: new Set(), dat6: new Set(), link: new Set() });
        s.n++; s.x.add(ev.eventDat2); s.dat3.add(ev.eventDat3); s.dat5.add(ev.eventDat5); s.dat6.add(ev.eventDat6); s.link.add(ev.eventDat4);
      }
    }
    // global move/accel events for the links these spawns use
    const moves = {};
    for (const lid of u.levels) {
      const [e, n] = lid.split(".").map(Number);
      if (e !== 1 && e !== 3) continue;
      const lv = lvls[e][n];
      const links = new Set();
      for (const [k, s] of Object.entries(spawns)) if (k.startsWith(lid + " ")) for (const l of s.link) if (l) links.add(l);
      for (const ev of lv.events) {
        if (![19, 20, 27, 47, 55, 24].includes(ev.eventType)) continue;
        if (!links.has(ev.eventDat4)) continue;
        const k = `${lid}`;
        (moves[k] ??= new Set()).add(`ev${ev.eventType}@t${ev.eventTime} link${ev.eventDat4} d=${ev.eventDat},${ev.eventDat2},${ev.eventDat3},${ev.eventDat5},${ev.eventDat6}`);
      }
    }
    // also launched by / dies-into
    const launchedBy = [], diesFrom = [];
    resBy[1].items.enemies.forEach((o, i) => { if (o && o.eLaunchType % 1000 === t) launchedBy.push(i); if (o && o.eEnemyDie === t) diesFrom.push(i); });
    rows.push({ type: raw, xMove: d.xMove, yMove: d.yMove, xAccel: d.xAccel, yAccel: d.yAccel, xCAccel: d.xCAccel, yCAccel: d.yCAccel, xRev: d.xRev, yRev: d.yRev,
      armor: d.armor, explosionType: d.explosionType, air: (d.explosionType & 1) === 1, animate: d.animate, ani: d.ani, eGraphic: d.eGraphic.slice(0, Math.max(1, d.ani)),
      tur: d.tur, freq: d.freq, launch: d.eLaunchType, launchFreq: d.eLaunchFreq, dieInto: d.eEnemyDie, value: d.value, dGr: d.dGr, launchedBy, diesFrom,
      moves: Object.fromEntries(Object.entries(moves).map(([k,v])=>[k,[...v].slice(0,12)])), spawns: Object.fromEntries(Object.entries(spawns).map(([k, s]) => [k, `${s.n}x x=[${[...s.x].slice(0,6)}] dat3(ymove+)=[${[...s.dat3]}] dat5(y)=[${[...s.dat5].slice(0,5)}] dat6(fixmovey)=[${[...s.dat6]}] link=[${[...s.link].slice(0,5)}]`])) });
  }
  out[id] = { kind: u.kind, boss: u.boss, levels: u.levels.map((l) => `${l} ${names[l]}`), frames: u.frames, types: rows };
}
writeFileSync(process.env.OUT ?? "/dev/stdout", JSON.stringify(out, null, 1));
await server.close();
