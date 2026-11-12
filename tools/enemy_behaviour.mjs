// Dump, per inventory unit, the enemy types that draw it, their movement/fire data (launcher, motion px/tick), the
// events that spawn them in every level (all four episodes, each with its own enemy data and level file), what spawns
// in the same tick beside them ("stacked with": composite craft) and a motion summary per type and level (D122).
// Usage: OUT=file.json NODE_OPTIONS= node tools/enemy_behaviour.mjs <unit-id>...
//   needs the data (TYRIAN_DATA, default ./data) and docs/roadmap/inventory.json. Without OUT the JSON goes to stdout.
//
// Spawn events follow JE_eventSystem (src/sim/tyrian2.ts): 6/7/10/15 ground/top/ground2/sky, 17/18/23/32/56 the
// bottom variants, 12 a 2x2 group of types eventdat+0..3 (eventdat6 0/1 ground, 2 sky, 3 top, 4 ground2), 49-52 a
// custom picture on type 0 (eventdat = graphic, eventdat3 = shape bank; 49 ground, 50 sky, 51 top, 52 ground2).
// Event 28 is not a spawn (it only clears topEnemyOver).
// Motion comes from a kinematic walk of each level: the event clock and scroll (events 2/3/30/53), every
// event-spawned enemy moved as JE_drawEnemy moves it (xmove/ymove, cycling accel with xrev/yrev, homing accel,
// fixedmovey, bounce, the layer's scroll), and the global events that steer them: 19 (eventdat3 0 = link
// eventdat4, 1/2/3 = every ground/sky/top enemy, 99 = all, 80-89 = the link event 75 picked), 20/27/55/74 (link 0 =
// all), 39 (relink), 75 (random pick among links eventdat..eventdat2 with eyc 0, or skip eventdat4 events).
// Not modelled: event jumps (38/54/70/71) and difficulty/2-player skips (flagged per spawn instead), slot limits,
// the player killing things, launched enemies (their type data motion is in `typeMotion`). The player is taken
// to stay at its start (x 100, y 180) for homing. Scroll stops with no forced events are released when the walk's
// enemies are gone, or after 700 ticks (the player would have cleared them).
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
process.chdir(ROOT);
const DATA = resolve(ROOT, process.env.TYRIAN_DATA ?? "data");
const { createServer } = await import(join(ROOT, "node_modules/vite/dist/node/index.js"));
const server = await createServer({ configFile: false, root: ROOT, logLevel: "error", server: { middlewareMode: true, hmr: false, ws: false, watch: null }, appType: "custom", optimizeDeps: { noDiscovery: true, include: [] } });
const data = await server.ssrLoadModule("/src/data/index.ts");
const resources = await server.ssrLoadModule("/src/sim/resources.ts");
const { shapeFile } = await server.ssrLoadModule("/src/sim/tyrian2.ts");
const files = { get: (n) => { const p = join(DATA, n); return existsSync(p) ? new Uint8Array(readFileSync(p)) : undefined; } };
const inv = JSON.parse(readFileSync(join(ROOT, "docs/roadmap/inventory.json")));
const units = new Map(inv.units.map((u) => [u.id, u]));
const names = Object.fromEntries(inv.levels.map((l) => [l.id, l.name]));
const want = process.argv.slice(2);

const s8 = (v) => ((v & 255) ^ 128) - 128;
const u8 = (v) => v & 255;
const u16 = (v) => v & 0xffff;
const s16 = (v) => ((v & 0xffff) ^ 0x8000) - 0x8000;
const sgn = (v) => (v > 0 ? `+${v}` : `${v}`);
const num = (v) => String(Math.round(v * 100) / 100);
const group = (ep) => (ep === 4 ? "e4" : "e1-3");
const LAYER = { 0: "sky", 25: "ground", 50: "top", 75: "ground2" };

// --- per-episode data, loaded on first use ---
const resBy = {}, lvlBy = {};
const res = (ep) => (resBy[ep] ??= resources.buildResources(files, ep));
function level(ep, n) {
  const f = files.get(`tyrian${ep}.lvl`);
  if (!f) return null;
  const lv = (lvlBy[ep] ??= { pos: data.readLevelPositions(f), lv: [] });
  return (lv.lv[n] ??= data.parseLevel(f, lv.pos.lvlPos[(n - 1) * 2]));
}
const bankSheet = (bank) => (bank === 21 ? "tyrian.shp#10" : bank === 26 ? "tyrian.shp#9" : bank >= 1 && bank <= shapeFile.length ? `newsh${shapeFile[bank - 1].toLowerCase()}.shp` : `bank${bank}`);

// --- which inventory units draw a spawn: "e1-3:13", or "e1-3:custom:newshh.shp|159" for events 49-52 ---
const unitsByKey = new Map();
const addKey = (k, id) => { const a = unitsByKey.get(k) ?? []; if (!a.includes(id)) a.push(id); unitsByKey.set(k, a); };
for (const u of inv.units) for (const t of u.types) {
  addKey(t, u.id);
  if (t.endsWith(":0")) for (const [fk, frames] of Object.entries(u.frames ?? {})) for (const gr of frames) addKey(`${t.split(":")[0]}:custom:${fk.split("|")[0]}|${gr}`, u.id);
}
const unitsFor = (key, lid) => { const all = unitsByKey.get(key) ?? []; const here = all.filter((id) => units.get(id).levels.includes(lid)); return here.length ? here : all; };

/** The enemies one event creates (JE_eventSystem's spawn cases). */
function spawnsOf(ev, R) {
  const one = (base, label, extra = {}) => [{ type: ev.eventDat, base, label, k: 0, eycAdd: ev.eventDat3, fixedmovey: ev.eventDat6, ...extra }];
  switch (ev.eventType) {
    case 6: return one(25, "ground(25)");
    case 7: return one(50, "top(50)");
    case 10: return one(75, "ground2(75)");
    case 15: return one(0, "sky(0)");
    case 17: return one(25, "groundBottom(25)", { y: 190 + ev.eventDat5 });
    case 18: return one(0, "skyBottom(0)", { y: 190 + ev.eventDat5 });
    case 23: return one(50, "topBottom(50)", { y: 180 + ev.eventDat5 });
    case 32: return one(50, "top190(50)", { y: 190 });
    case 56: return one(75, "ground2Bottom(75)", { y: 190 });
    case 12: {
      const base = { 0: 25, 1: 25, 2: 0, 3: 50, 4: 75 }[ev.eventDat6] ?? 0;
      return [0, 1, 2, 3].map((k) => ({ type: ev.eventDat + k, base, label: `group12/${LAYER[base]}(${base})`, k, eycAdd: ev.eventDat3, fixedmovey: 0 }));
    }
    case 49: case 50: case 51: case 52: {
      const base = { 49: 25, 50: 0, 51: 50, 52: 75 }[ev.eventType];
      const bank = ev.eventDat3 > 0 ? ev.eventDat3 : R.enemyDat[0].shapeBank;
      return [{ type: 0, base, label: `custom${ev.eventType}/${LAYER[base]}(${base})`, k: 0, eycAdd: 0, fixedmovey: 0, custom: { graphic: ev.eventDat, bank, sheet: bankSheet(bank) } }];
    }
  }
  return [];
}
const spawnKey = (ep, s) => (s.custom ? `${group(ep)}:custom:${s.custom.sheet}|${s.custom.graphic}` : `${group(ep)}:${s.type}`);

function rng32(seed) { let a = seed >>> 0; return () => { a = (a + 0x6d2b79f5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return (t ^ (t >>> 14)) >>> 0; }; }

/** JE_makeEnemy's motion fields for type `dat`. */
function makeMover(dat) {
  const rev = (r) => (r === 0 ? 100 : r === -99 ? 0 : r);
  return { ex: 0, ey: 0, exc: dat.xMove, eyc: dat.yMove, excc: dat.xCAccel, eycc: dat.yCAccel, exccw: s8(Math.abs(dat.xCAccel)), eyccw: s8(Math.abs(dat.yCAccel)),
    exccwmax: u8(Math.abs(dat.xCAccel)), eyccwmax: u8(Math.abs(dat.yCAccel)), exccadd: dat.xCAccel > 0 ? 1 : -1, eyccadd: dat.yCAccel > 0 ? 1 : -1,
    exrev: rev(dat.xRev), eyrev: rev(dat.yRev), xaccel: u8(dat.xAccel), yaccel: u8(dat.yAccel), fixedmovey: 0, link: 0,
    xminbounce: -10000, xmaxbounce: 10000, yminbounce: -10000, ymaxbounce: 10000 };
}
const MOTION_FIELDS = ["exc", "eyc", "excc", "eycc", "exrev", "eyrev", "xaccel", "yaccel", "fixedmovey", "xminbounce", "xmaxbounce", "yminbounce", "ymaxbounce"];
const snap = (e) => MOTION_FIELDS.map((f) => e[f]).join(",");

/** One tick of JE_drawEnemy's movement (src/sim/tyrian2.ts drawOneEnemy). `gone` says why it left, or is null. */
function moveTick(e, scroll, rnd) {
  const px = 100 - 25, py = 180; // player[0] at its start; JE_drawEnemy compares x - 25
  let homing = false, cycled = false, bounced = false;
  if (e.xaccel && ((e.xaccel - 89) >>> 0) > rnd() % 11) {
    const o = e.exc;
    if (px > e.ex) { if (e.exc < e.xaccel - 89) e.exc = s8(e.exc + 1); }
    else if (e.exc >= 0 || -e.exc < e.xaccel - 89) e.exc = s8(e.exc - 1);
    homing ||= o !== e.exc;
  }
  if (e.yaccel && ((e.yaccel - 89) >>> 0) > rnd() % 11) {
    const o = e.eyc;
    if (py > e.ey) { if (e.eyc < e.yaccel - 89) e.eyc = s8(e.eyc + 1); }
    else if (e.eyc >= 0 || -e.eyc < e.yaccel - 89) e.eyc = s8(e.eyc - 1);
    homing ||= o !== e.eyc;
  }
  for (const a of ["x", "y"]) {
    const c = `e${a}c`, cc = `e${a}cc`, w = `e${a}ccw`, wm = `e${a}ccwmax`, add = `e${a}ccadd`, rv = `e${a}rev`;
    if (!e[cc]) continue;
    e[w] = s8(e[w] - 1);
    if (e[w] > 0) continue;
    const flip = () => { e[cc] = s8(-e[cc]); e[rv] = s8(-e[rv]); e[add] = s16(-e[add]); };
    if (e[c] === e[rv]) flip();
    else { e[c] = s8(e[c] + e[add]); cycled = true; e[w] = s8(e[wm]); if (e[c] === e[rv]) flip(); }
  }
  e.ey = s16(e.ey + e.fixedmovey);
  e.ex = s16(e.ex + e.exc);
  if (e.ex < -80 || e.ex > 340) return { gone: e.ex < 0 ? "left the screen (left)" : "left the screen (right)", homing, cycled, bounced };
  e.ey = s16(e.ey + e.eyc);
  if (e.ey < -112 || e.ey > 190) return { gone: e.ey < 0 ? "left the screen (top)" : "left the screen (bottom)", homing, cycled, bounced };
  if (e.ex <= e.xminbounce || e.ex >= e.xmaxbounce) { e.exc = s8(-e.exc); bounced = true; }
  if (e.ey <= e.yminbounce || e.ey >= e.ymaxbounce) { e.eyc = s8(-e.eyc); bounced = true; }
  e.ey = s16(e.ey + scroll);
  return { gone: null, homing, cycled, bounced };
}

/** Segment bookkeeping: own velocity (exc, eyc + fixedmovey) between velocity-changing events. */
const newSeg = (tick, cause) => ({ from: tick, causes: cause ? [cause] : [], n: 0, xmin: Infinity, xmax: -Infinity, ymin: Infinity, ymax: -Infinity, homing: false, cycled: false, bounced: false, scroll: 0 });
function segAdd(s, e, r, scroll) {
  s.n++; s.scroll += scroll;
  const vy = e.eyc + e.fixedmovey;
  s.xmin = Math.min(s.xmin, e.exc); s.xmax = Math.max(s.xmax, e.exc); s.ymin = Math.min(s.ymin, vy); s.ymax = Math.max(s.ymax, vy);
  s.homing ||= r.homing; s.cycled ||= r.cycled; s.bounced ||= r.bounced;
}
const span = (a, b) => (a === b ? sgn(a) : `${sgn(a)}..${sgn(b)}`);
/** "ev19+20+27 link35 (ev75 pick)": the events (type, whom) that changed the motion in one tick. */
function causeText(causes) {
  const by = new Map();
  for (const [t, w] of causes) by.set(w, [...(by.get(w) ?? []), t]);
  return [...by].map(([w, ts]) => `ev${ts.join("+")}${w}`).join(", ");
}
const segVel = (s) => (s.xmin === s.xmax && s.ymin === s.ymax ? `(${sgn(s.xmin)},${sgn(s.ymin)})` : `x ${span(s.xmin, s.xmax)}, y ${span(s.ymin, s.ymax)}`);

/** Short label for one enemy's life: terrain-fixed, hovering, steady drift, weaving or swooping, with px/tick. */
function motionLabel(segs, base) {
  segs = segs.filter((s) => s.n > 0);
  if (!segs.length) return "never moved";
  const still = (s) => s.xmin === 0 && s.xmax === 0 && s.ymin === 0 && s.ymax === 0;
  const n = segs.reduce((a, s) => a + s.n, 0);
  const scroll = segs.reduce((a, s) => a + s.scroll, 0) / n;
  const where = base === 0 ? "sky layer (no scroll)" : `${LAYER[base]} layer, scroll ${num(scroll)}`;
  const byEvent = segs.length > 1;
  const homing = segs.some((s) => s.homing), weave = segs.some((s) => s.cycled || s.bounced);
  let kind;
  if (byEvent || homing) kind = homing && !byEvent ? "swooping (homes on the player)" : "swooping";
  else if (weave) kind = segs[0].bounced && !segs[0].cycled ? "weaving (bounces)" : "weaving";
  else if (still(segs[0])) kind = base === 0 ? "hovering (screen-fixed)" : "terrain-fixed";
  else kind = "steady drift";
  if (kind === "terrain-fixed" || kind.startsWith("hovering")) return `${kind}, ${where}`;
  const parts = segs.slice(0, 4).map((s, i) => (i ? `${causeText(s.causes)} ` : "") + segVel(s));
  return `${kind} ${parts.join(" → ")}${segs.length > 4 ? " → …" : ""} px/tick, ${where}`;
}

/** Event 63 (2-player only) and 66 (difficulty) skip windows, as tools/inventory.mjs reads them. */
function spawnFlags(events) {
  const flags = [];
  let twoUntil = -1;
  const harder = [];
  events.forEach((ev, i) => {
    const f = [];
    if (i <= twoUntil) f.push("2P only");
    const d = Math.max(0, ...harder.filter(([until]) => i <= until).map(([, dd]) => dd));
    if (d > 2) f.push(`difficulty ${d}+`);
    flags[i] = f;
    if (ev.eventType === 63) twoUntil = Math.max(twoUntil, i + ev.eventDat);
    if (ev.eventType === 66 && ev.eventDat2 > 0) harder.push([i + ev.eventDat2, ev.eventDat + 1]);
  });
  return flags;
}

/** Walks one level: event clock, scroll, every event-spawned enemy's kinematics. */
const walked = {};
function walkLevel(ep, n) {
  const key = `${ep}.${n}`;
  if (walked[key]) return walked[key];
  const lv = level(ep, n), R = res(ep), evs = lv.events, flags = spawnFlags(evs);
  const st = { curLoc: 0, backMove: 1, backMove2: 2, backMove3: 3, map1YDelay: 1, map1YDelayMax: 1, forceEvents: false, small: false, bg3x1: false, bg3x1b: false, newPL: new Array(10).fill(0) };
  const rnd = rng32(1);
  const spawns = [], alive = [], touched = new Map(); // event index -> spawns whose motion or link it changed
  let tick = 0;
  const end = (e, why) => { e.sp.life = tick - e.sp.tick; e.sp.end = why; e.sp.motion = motionLabel(e.segs, e.sp.base); };
  const touch = (i, sp) => (touched.get(i) ?? touched.set(i, new Set()).get(i)).add(sp);
  const steer = (i, match, apply, cause) => {
    for (const e of alive) {
      if (!match(e)) continue;
      const before = snap(e);
      apply(e);
      if (snap(e) === before) continue;
      touch(i, e.sp);
      const last = e.segs.at(-1);
      if (last.n === 0 && last.causes.length) { if (!last.causes.some((c) => c[0] === cause[0] && c[1] === cause[1])) last.causes.push(cause); } // one tick's events make one change
      else e.segs.push(newSeg(tick, cause));
    }
  };
  const isPL = (ev) => ev.eventDat3 > 79 && ev.eventDat3 < 90;
  const pl = (ev) => (isPL(ev) ? st.newPL[ev.eventDat3 - 80] : ev.eventDat4);
  const who = (ev, L) => (L === 0 ? " all" : ` link${L}`) + (isPL(ev) ? " (ev75 pick)" : "");
  /** Runs event i; returns the index of the last event it consumed. */
  function fire(i) {
    const ev = evs[i];
    switch (ev.eventType) {
      case 2: case 30: st.map1YDelay = 1; st.map1YDelayMax = 1; st.backMove = u16(ev.eventDat); st.backMove2 = u16(ev.eventDat2); st.backMove3 = u16(ev.eventDat3); return i;
      case 3: st.backMove = 1; st.map1YDelay = 3; st.map1YDelayMax = 3; st.backMove2 = 1; st.backMove3 = 1; return i;
      case 26: st.small = ev.eventDat !== 0; return i;
      case 53: st.forceEvents = ev.eventDat !== 99; return i;
      case 65: st.bg3x1 = ev.eventDat === 0; return i;
      case 72: st.bg3x1b = ev.eventDat === 1; return i;
      case 41: for (const e of [...alive]) if (ev.eventDat === 0 || e.sp.base === 0) { end(e, `cleared by event 41 at t${ev.eventTime}`); alive.splice(alive.indexOf(e), 1); } return i;
      case 19: {
        const sel = ev.eventDat3, L = pl(ev);
        const range = { 2: [0, 25], 1: [25, 50], 3: [50, 75], 99: [0, 100] }[sel];
        const match = isPL(ev) || sel === 0 ? (e) => e.link === L : range ? (e) => e.sp.base >= range[0] && e.sp.base < range[1] : () => false;
        steer(i, match, (e) => {
          if (ev.eventDat !== -99) e.exc = s8(ev.eventDat);
          if (ev.eventDat2 !== -99) e.eyc = s8(ev.eventDat2);
          if (ev.eventDat6 !== 0) e.fixedmovey = ev.eventDat6;
          if (ev.eventDat6 === -99) e.fixedmovey = 0;
        }, [19, range ? ` all ${sel === 99 ? "" : LAYER[range[0]] + " "}enemies` : who(ev, L)]);
        return i;
      }
      case 20: {
        const L = pl(ev);
        steer(i, (e) => L === 0 || e.link === L, (e) => {
          if (ev.eventDat !== -99) { e.excc = s8(ev.eventDat); e.exccw = s8(Math.abs(ev.eventDat)); e.exccwmax = u8(Math.abs(ev.eventDat)); e.exccadd = ev.eventDat > 0 ? 1 : -1; }
          if (ev.eventDat2 !== -99) { e.eycc = s8(ev.eventDat2); e.eyccw = s8(Math.abs(ev.eventDat2)); e.eyccwmax = u8(Math.abs(ev.eventDat2)); e.eyccadd = ev.eventDat2 > 0 ? 1 : -1; }
        }, [20, who(ev, L)]);
        return i;
      }
      case 27: {
        const L = pl(ev);
        steer(i, (e) => L === 0 || e.link === L, (e) => { if (ev.eventDat !== -99) e.exrev = s8(ev.eventDat); if (ev.eventDat2 !== -99) e.eyrev = s8(ev.eventDat2); }, [27, who(ev, L)]);
        return i;
      }
      case 55: {
        const L = pl(ev);
        steer(i, (e) => L === 0 || e.link === L, (e) => { if (ev.eventDat !== -99) e.xaccel = u8(ev.eventDat); if (ev.eventDat2 !== -99) e.yaccel = u8(ev.eventDat2); }, [55, who(ev, L)]);
        return i;
      }
      case 74:
        steer(i, (e) => ev.eventDat4 === 0 || e.link === ev.eventDat4, (e) => {
          if (ev.eventDat5 !== -99) e.xminbounce = ev.eventDat5;
          if (ev.eventDat6 !== -99) e.yminbounce = ev.eventDat6;
          if (ev.eventDat !== -99) e.xmaxbounce = ev.eventDat;
          if (ev.eventDat2 !== -99) e.ymaxbounce = ev.eventDat2;
        }, [74, who(ev, ev.eventDat4)]);
        return i;
      case 39: for (const e of alive) if (e.link === ev.eventDat) { e.link = u8(ev.eventDat2); touch(i, e.sp); } return i;
      case 75: {
        const links = [...new Set(alive.filter((e) => e.eyc === 0 && e.link >= ev.eventDat && e.link <= ev.eventDat2).map((e) => e.link))];
        if (links.length) { st.newPL[ev.eventDat3 - 80] = links[rnd() % links.length]; return i; }
        st.newPL[ev.eventDat3 - 80] = 255;
        if (ev.eventDat4 > 0 && i + ev.eventDat4 < evs.length) { st.curLoc = evs[i + ev.eventDat4].eventTime - 1; return i + ev.eventDat4 - 1; }
        return i;
      }
    }
    for (const s of spawnsOf(ev, R)) {
      const dat = R.enemyDat[s.type];
      if (!dat) continue;
      const e = makeMover(dat);
      if (ev.eventDat2 !== -99) {
        if (s.base === 0) e.ex = ev.eventDat2 - (lv.mapX - 1) * 24;
        else if (s.base === 50) { e.ex = st.bg3x1 ? ev.eventDat2 - (lv.mapX - 1) * 24 - 12 : ev.eventDat2 - lv.mapX3 * 24 - 42; if (st.bg3x1b) e.ex -= 6; }
        else e.ex = ev.eventDat2 - (lv.mapX - 1) * 24 - 12;
        e.ey = -28 + (st.bg3x1b && s.base === 50 ? 4 : 0);
      } else { e.ex = dat.startX + 1; e.ey = dat.startY + 1; } // startXC/startYC randomness left out
      if (st.small && dat.eSize === 0) { e.ex -= 10; e.ey -= 7; }
      e.ey += ev.eventDat5;
      e.eyc = s8(e.eyc + s.eycAdd);
      e.link = ev.eventDat4;
      e.fixedmovey = s.fixedmovey;
      if (s.k & 1) e.ex += 24;
      if (s.k & 2) e.ey -= 28;
      if (s.y !== undefined) e.ey = s.y;
      const sp = { ...s, i, ev, tick, ex: e.ex, ey: e.ey, link: e.link, flags: flags[i], key: spawnKey(ep, s), xs: [], ys: [] };
      e.sp = sp;
      e.segs = [newSeg(tick, null)];
      spawns.push(sp);
      alive.push(e);
    }
    return i;
  }
  let i = 0, frozen = 0, idleAfterEnd = 0;
  while (tick < 100000) {
    while (i < evs.length && evs[i].eventTime <= st.curLoc) i = fire(i) + 1;
    if (i >= evs.length && (!alive.length || ++idleAfterEnd > 3000)) break;
    if (st.forceEvents && !st.backMove) st.curLoc++;
    if (st.map1YDelayMax > 1 && st.backMove < 2) st.backMove = st.map1YDelay === 1 ? 1 : 0;
    st.map1YDelay--;
    if (st.map1YDelay === 0) { st.map1YDelay = st.map1YDelayMax; st.curLoc += st.backMove; }
    for (const e of [...alive]) {
      const scroll = e.sp.base === 0 ? 0 : e.sp.base === 50 ? st.backMove3 : st.backMove;
      const r = moveTick(e, scroll, rnd);
      if (!r.gone) { e.sp.xs.push(e.ex); e.sp.ys.push(e.ey); segAdd(e.segs.at(-1), e, r, scroll); }
      if (r.gone || tick - e.sp.tick >= 3000) { end(e, r.gone ?? "still there after 3000 ticks"); alive.splice(alive.indexOf(e), 1); }
    }
    // A stopped scroll with no forced events: the game waits for the player to clear the screen.
    if (st.backMove === 0 && st.map1YDelayMax === 1 && !st.forceEvents) {
      if (!alive.length || ++frozen > 700) {
        for (const e of alive) end(e, "held on screen while the scroll was stopped (until destroyed)");
        alive.length = 0; st.backMove = 1; st.backMove2 = 2; st.backMove3 = 3; frozen = 0;
      }
    } else frozen = 0;
    tick++;
  }
  for (const e of alive) end(e, "level walk ended");
  // Stacks: spawns of the same tick within one tile column (|dx| <= 24); rigid = the offset holds (±1) while both live.
  const byTick = new Map();
  for (const s of spawns) (byTick.get(s.tick) ?? byTick.set(s.tick, []).get(s.tick)).push(s);
  for (const s of spawns) {
    s.stack = [];
    for (const o of byTick.get(s.tick)) {
      if (o === s || Math.abs(o.ex - s.ex) > 24) continue;
      const len = Math.min(s.xs.length, o.xs.length);
      let dev = 0;
      for (let k = 0; k < len; k++) dev = Math.max(dev, Math.abs(o.xs[k] - s.xs[k] - (o.ex - s.ex)), Math.abs(o.ys[k] - s.ys[k] - (o.ey - s.ey)));
      s.stack.push({ o, dx: o.ex - s.ex, dy: o.ey - s.ey, rigid: len > 0 && dev <= 1, together: len });
    }
  }
  return (walked[key] = { spawns, touched, evs });
}

/** Motion of a type from its data alone (no events, no scroll): what a launched or random enemy does. */
function typeMotion(dat) {
  const e = makeMover(dat);
  e.ex = 120;
  const segs = [newSeg(0, null)], rnd = rng32(2);
  for (let t = 0; t < 400; t++) { const r = moveTick(e, 0, rnd); if (r.gone) break; segAdd(segs[0], e, r, 0); }
  return motionLabel(segs, 0).replace("hovering (screen-fixed)", "still").replace(", sky layer (no scroll)", " (own motion, before events and scroll)");
}

const out = {};
for (const id of want) {
  const u = units.get(id);
  if (!u) { out[id] = "missing"; continue; }
  const rows = [];
  for (const raw of u.types) {
    const [g, tn] = raw.split(":");
    const t = Number(tn);
    const R = res(g === "e4" ? 4 : 1);
    const d = R.enemyDat[t];
    const mine = t === 0
      ? (sp) => sp.custom && Object.entries(u.frames ?? {}).some(([fk, fr]) => fk.split("|")[0] === sp.custom.sheet && fr.includes(sp.custom.graphic))
      : (sp) => !sp.custom && sp.type === t;
    const spawns = {}, moves = {}, motion = {}, stacked = {}, detail = {};
    for (const lid of u.levels) {
      const [e, n] = lid.split(".").map(Number);
      if (group(e) !== g || !level(e, n)) continue;
      const W = walkLevel(e, n);
      const mineHere = W.spawns.filter(mine);
      if (!mineHere.length) continue;
      const label = `${lid} ${names[lid] ?? ""}`;
      for (const sp of mineHere) {
        const s = (spawns[`${label}: ${sp.label}`] ??= { n: 0, x: new Set(), dat3: new Set(), dat5: new Set(), dat6: new Set(), link: new Set() });
        s.n++; s.x.add(sp.ev.eventDat2); s.dat3.add(sp.eycAdd); s.dat5.add(sp.ev.eventDat5); s.dat6.add(sp.fixedmovey); s.link.add(sp.link);
      }
      // the events that changed this type's enemies' motion (or link) here
      const mv = [];
      for (const [ei, set] of [...W.touched].sort((a, b) => a[0] - b[0])) {
        if (!mineHere.some((sp) => set.has(sp))) continue;
        const ev = W.evs[ei];
        mv.push(`ev${ev.eventType}@t${ev.eventTime}${ev.eventType === 19 ? ` sel=${ev.eventDat3}` : ""} link${ev.eventDat4} d=${ev.eventDat},${ev.eventDat2},${ev.eventDat3},${ev.eventDat5},${ev.eventDat6}`);
      }
      if (mv.length) moves[lid] = mv.slice(0, 16).concat(mv.length > 16 ? [`… ${mv.length - 16} more`] : []);
      const counts = {};
      for (const sp of mineHere) { const m = sp.motion.replace(/ link\d+/g, " link"); counts[m] = (counts[m] ?? 0) + 1; } // spawnDetail keeps the link numbers
      const top = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      motion[lid] = top.slice(0, 4).map(([m, c]) => `${m} ×${c}`).join("; ") + (top.length > 4 ? `; +${top.length - 4} more` : "");
      const st = {};
      for (const sp of mineHere) for (const s of sp.stack) {
        const k = `${unitsFor(s.o.key, lid).join("|") || s.o.key} (${s.o.custom ? `custom ${s.o.custom.graphic}` : `type ${s.o.type}`}) dx ${sgn(s.dx)} dy ${sgn(s.dy)}${sp.link && s.o.link === sp.link ? " same link" : ""}${s.rigid ? " rigid" : ""}`;
        st[k] = (st[k] ?? 0) + 1;
      }
      if (Object.keys(st).length) stacked[lid] = Object.fromEntries(Object.entries(st).sort((a, b) => b[1] - a[1]).slice(0, 12));
      detail[lid] = mineHere.slice(0, 24).map((sp) => ({
        t: sp.ev.eventTime, ev: sp.ev.eventType, layer: sp.label, x: sp.ev.eventDat2, ex: sp.ex, ey: sp.ey, link: sp.link, ...(sp.flags.length ? { only: sp.flags.join(", ") } : {}),
        motion: sp.motion, life: sp.life, end: sp.end,
        stackedWith: sp.stack.map((s) => ({ unit: unitsFor(s.o.key, lid).join("|") || null, type: s.o.custom ? `custom ${s.o.custom.sheet}#${s.o.custom.graphic}` : s.o.type, layer: s.o.label, dx: s.dx, dy: s.dy, link: s.o.link, rigid: s.rigid, together: s.together })),
      }));
      if (mineHere.length > 24) detail[lid].push(`… ${mineHere.length - 24} more spawns`);
    }
    const launchedBy = [], diesFrom = [];
    R.enemyDat.forEach((o, i) => { if (o && t && o.eLaunchType % 1000 === t) launchedBy.push(i); if (o && t && o.eEnemyDie === t) diesFrom.push(i); });
    rows.push({ type: raw, xMove: d.xMove, yMove: d.yMove, xAccel: d.xAccel, yAccel: d.yAccel, xCAccel: d.xCAccel, yCAccel: d.yCAccel, xRev: d.xRev, yRev: d.yRev,
      armor: d.armor, explosionType: d.explosionType, air: (d.explosionType & 1) === 1, animate: d.animate, ani: d.ani, eGraphic: d.eGraphic.slice(0, Math.max(1, d.ani)),
      tur: d.tur, freq: d.freq, launch: d.eLaunchType, launchFreq: d.eLaunchFreq, dieInto: d.eEnemyDie, value: d.value, dGr: d.dGr, launchedBy, diesFrom,
      typeMotion: typeMotion(d), motion, stackedWith: stacked,
      moves, spawns: Object.fromEntries(Object.entries(spawns).map(([k, s]) => [k, `${s.n}x x=[${[...s.x].slice(0, 6)}] dat3(ymove+)=[${[...s.dat3]}] dat5(y)=[${[...s.dat5].slice(0, 5)}] dat6(fixmovey)=[${[...s.dat6]}] link=[${[...s.link].slice(0, 5)}]`])),
      spawnDetail: detail });
  }
  out[id] = { kind: u.kind, boss: u.boss, levels: u.levels.map((l) => `${l} ${names[l] ?? ""}`), frames: u.frames, types: rows };
}
const json = JSON.stringify(out, null, 1);
if (process.env.OUT) { writeFileSync(process.env.OUT, json); process.stderr.write(`wrote ${process.env.OUT} (${want.length} units)\n`); }
else await new Promise((ok) => process.stdout.write(json + "\n", ok)); // a stream write waits out EAGAIN; writeFileSync("/dev/stdout") does not
await server.close();
