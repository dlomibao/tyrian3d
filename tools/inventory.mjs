#!/usr/bin/env node
// The whole-game asset inventory for planning the remaster of the rest of Tyrian 3D, episode by
// episode, shared assets first. Writes docs/roadmap/inventory.json (machine-readable: ids and
// counts) and docs/roadmap/inventory.md (tables for people and agents).
//
//   npm run inventory                     static parse plus a bot run of every level (a few minutes)
//   node tools/inventory.mjs --no-play    static parse only (a few seconds)
//   node tools/inventory.mjs --out DIR    write somewhere else (default docs/roadmap)
//   node tools/inventory.mjs --episodes 1,2   only these episodes (for trying changes quickly)
//   node tools/inventory.mjs --markdown-only  rewrite inventory.md from inventory.json
//   TYRIAN_DATA=/path/to/data             the Tyrian 2.1 data (default data/)
//
// Everything comes from the game's own data and code, loaded through Vite (src/ is TypeScript):
// - the episode scripts (levels?.dat): every `]L[` (level name, song, tyrian?.lvl level, bonus
//   flags, its section and whether a difficulty picks it), the cutscene commands round it;
// - each level's file (tyrian?.lvl): tileset, maps, random spawns and event list. The enemy types
//   a level can show are the events that create enemies (6, 7, 10, 12, 15, 17, 18, 23, 32, 49-52,
//   56), the drops events 33/45 assign, the random spawns, and what those launch or leave behind
//   (followed transitively), plus the armour ship and its crates, which the game sends to any
//   level when armour is low (src/sim/levelSprites.ts has the same rules for the preload, but
//   over-covers: it takes eventdat+0..3 of every event). Boss bars are event 79's link numbers;
//   a boss is an enemy created with that link number (event 39 renames links).
// - enemy shots: each enemy type's turret weapons (sg frames and their animation); player shots:
//   every front/rear weapon (all powers and modes) and sidekick the episode's shops offer.
// - the bot run (tests/sim/bot.ts, as tests/render/modelSwap.test.ts and the D65 scout used it):
//   plays every section with a `]L[` (and hard difficulty where the script branches on it) and
//   counts the ticks each object, shot and boss bar is on screen. That says how often an asset is
//   seen, which static parsing can't, and which statically possible enemies never show.
//
// Status comes from the repo: src/render/spriteModels/*.json (sprite -> model) and the .glb
// (a hard-surface "flagship" model has the outline shell, D51/D65; a concept-baked one textures
// but no shell, D44; otherwise the older basic style), src/viewer/assemblies.json (multi-piece
// objects, one script each), public/art/sprites/manifest.json (flat art, D42), public/art/terrain/
// <tileset>/manifest.json (HD terrain, D57), src/render/tileModels/*.json (structure models, D34/D47),
// public/tyrian-remaster/manifest.json (music arrangements, D40), public/art/pictures.json (D19),
// and the damaged frames the intact models draw (D87; KNOWN_DAMAGE_SWAPS in tests/render/modelSwap.test.ts
// before it, D54).
//
// Deterministic: fixed seeds, sorted output, no timestamps. Never writes game data or pixels.

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

/** The TypeScript modules the inventory uses, by repo path. */
export const MODULES = {
  data: "src/data/index.ts",
  resources: "src/sim/resources.ts",
  tyrian2: "src/sim/tyrian2.ts",
  levelSprites: "src/sim/levelSprites.ts",
  state: "src/sim/state.ts",
  game: "src/sim/game.ts",
  helptext: "src/sim/helptext.ts",
  input: "src/sim/input.ts",
  mtrand: "src/sim/mtrand.ts",
  newgame: "src/sim/newgame.ts",
  draw: "src/sim/draw.ts",
  shots: "src/sim/shots.ts",
  mainint: "src/sim/mainint.ts",
  bot: "tests/sim/bot.ts",
};

// --- Event types (JE_eventSystem, src/sim/tyrian2.ts) ---

/** Events that create one enemy of type eventdat (JE_createNewEventEnemy). */
const SPAWN_EVENTS = new Set([6, 7, 10, 15, 17, 18, 23, 32, 56]);
/** Event 12 creates eventdat + 0..3 (a 2x2 group); 49-52 create type 0 with a custom graphic. */
const GROUP_EVENT = 12;
const CUSTOM_EVENTS = new Set([49, 50, 51, 52]);
/** Events 33 (all games) and 45 (arcade and two-player only) set the drop of enemies with link eventdat4. */
const DROP_EVENT = 33;
const ARCADE_DROP_EVENT = 45;
/** Event 33's 533 becomes a random special weapon, 829 + rand % 6 (tyrian2.c). */
const RANDOM_SPECIAL = 533;
const RANDOM_SPECIALS = [829, 830, 831, 832, 833, 834];
/** Event 79: boss bars follow link numbers eventdat and eventdat2. Event 39 renames a link. */
const BOSS_EVENT = 79;
const RELINK_EVENT = 39;
const SMOOTHIES = { 1: "lava", 2: "water", 3: "iced", 4: "blur", 5: "iced-starfield", 6: "headlight", 9: "flip" };
/** In-level events worth listing as special presentation (the rest move enemies or scroll). */
const SPECIAL_EVENTS = {
  16: "text window",
  35: "song change",
  34: "music fade",
  44: "colour filter",
  64: "smoothie",
  67: "level timer",
  68: "random explosions",
  82: "special weapon given",
  48: "background 2 opaque",
  40: "enemy continual damage",
  41: "clear enemies",
  81: "background wrap",
  77: "map jump",
  46: "difficulty change",
  62: "sound effect",
};

// --- Small helpers ---

const sortNum = (a, b) => a - b;
const uniq = (xs) => [...new Set(xs)];
const frameKey = (sheet, size, index) => `${sheet}|${size}|${index}`;

/** "newsh1.shp" -> "newsh1", "newsh#.shp" -> "newsh-hash", "tyrian.shp#8" -> "tyrian8" (as the catalogue). */
export function sheetSlug(id) {
  const special = { "#": "-hash", "^": "-caret", "@": "-at", "~": "-tilde", "&": "-amp" };
  const m = /^newsh(.)\.shp$/.exec(id);
  if (m) return `newsh${special[m[1]] ?? m[1]}`;
  const t = /^tyrian\.shp#(\d+)$/.exec(id);
  if (t) return `tyrian${t[1]}`;
  return id.replace(/[^a-z0-9]+/gi, "-");
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

function jsonFiles(dir) {
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter((f) => f.endsWith(".json")).sort().map((f) => readJson(join(dir, f)));
}

/** The JSON chunk of a .glb: its material, mesh and node names and whether it carries images. */
function glbInfo(path) {
  if (!existsSync(path)) return null;
  const b = readFileSync(path);
  if (b.readUInt32LE(0) !== 0x46546c67) return null;
  const len = b.readUInt32LE(12);
  const j = JSON.parse(b.subarray(20, 20 + len).toString("utf8"));
  const names = [...(j.materials ?? []), ...(j.meshes ?? []), ...(j.nodes ?? [])].map((x) => x.name ?? "");
  return { shell: names.some((n) => /outline/i.test(n)), textured: (j.images ?? []).length > 0, bytes: b.length };
}

/** Quality tier of a model file: flagship (hard-surface, outline shell), concept (baked concept texture), basic. */
function modelTier(info) {
  if (!info) return "missing";
  if (info.shell) return "flagship";
  if (info.textured) return "concept";
  return "basic";
}

// --- What the repo already has ---

/** Everything the status columns need, read from the repo (never from the game data). */
export function repoStatus(root = ROOT) {
  // Sprite models (src/render/spriteModels.ts's index, rebuilt here: its import.meta.glob of 1,300
  // JSON files takes Vite about a minute).
  const grouped = new Map();
  const ungrouped = new Map();
  const models = new Map();
  for (const e of jsonFiles(join(root, "src/render/spriteModels"))) {
    for (const ref of e.sprites) {
      const frames = ref.bank ? Array.from({ length: ref.bank.max * 2 + 1 }, (_, n) => ref.frames[0] + (n - ref.bank.max) * ref.bank.step) : ref.frames;
      for (const f of frames) ((ref.ungrouped || (ref.bank && !ref.group)) ? ungrouped : grouped).set(frameKey(ref.sheet, ref.size, f), e.model);
    }
    if (!models.has(e.model)) {
      const info = glbInfo(join(root, "public/models", `${e.model}.glb`));
      models.set(e.model, { tier: modelTier(info), bytes: info?.bytes ?? 0 });
    }
  }
  // Multi-piece objects: one script builds every piece (assets/blender/enemies/assembly-*.py).
  const assemblyOf = new Map();
  const assemblyPath = join(root, "src/viewer/assemblies.json");
  for (const a of existsSync(assemblyPath) ? readJson(assemblyPath) : []) {
    for (const p of a.pieces) {
      const k = frameKey(p.sheet, p.size, p.index);
      if (!assemblyOf.has(k)) assemblyOf.set(k, a.name);
    }
  }
  // Pieces an assembly script names itself ("newsh4-1", its -fN frames) that assemblies.json (the
  // catalogue's view of what touches what) puts elsewhere or nowhere.
  const enemyDir = join(root, "assets/blender/enemies");
  const modelFrames = new Map();
  for (const [k, model] of grouped) {
    if (!modelFrames.has(model)) modelFrames.set(model, []);
    modelFrames.get(model).push(k);
  }
  if (existsSync(enemyDir)) {
    for (const f of readdirSync(enemyDir).filter((x) => /^assembly-.*\.py$/.test(x)).sort()) {
      const name = f.slice(0, -3);
      for (const mm of readFileSync(join(enemyDir, f), "utf8").matchAll(/"((?:newsh|tyrian)[^"\s/]*?-\d+(?:-f\d+)?)"/g)) {
        for (const k of modelFrames.get(`enemies/${mm[1]}`) ?? []) if (!assemblyOf.has(k)) assemblyOf.set(k, name);
      }
    }
  }
  // Concept/bake settings per script (D44, D50: "bake": "model" means a self-baked hard-surface model).
  const bake = new Map();
  const texDir = join(root, "assets/blender/textures");
  if (existsSync(texDir)) {
    for (const name of readdirSync(texDir).sort()) {
      const p = join(texDir, name, "maps.json");
      if (existsSync(p)) bake.set(name, readJson(p).bake === "model" ? "model" : "concept");
    }
  }
  // Flat art for shots and pickups (D42).
  const flat = new Set();
  const artPath = join(root, "public/art/sprites/manifest.json");
  if (existsSync(artPath)) {
    const art = readJson(artPath);
    for (const [sheet, s] of Object.entries(art.sheets ?? {})) for (const f of Object.keys(s.frames ?? {})) flat.add(`${sheet}|${f}`);
  }
  // HD terrain per tileset and layer (D57).
  const terrain = new Map();
  const terrainDir = join(root, "public/art/terrain");
  if (existsSync(terrainDir)) {
    for (const ts of readdirSync(terrainDir).sort()) {
      const p = join(terrainDir, ts, "manifest.json");
      if (!existsSync(p)) continue;
      const m = readJson(p);
      terrain.set(ts, Object.fromEntries(Object.entries(m.layers ?? {}).map(([l, v]) => [l, new Set(Object.keys(v.tiles ?? {}).map(Number))])));
    }
  }
  // Structure (tile) models (D34, D47).
  const tileModels = jsonFiles(join(root, "src/render/tileModels")).map((e) => {
    const info = glbInfo(join(root, "public/models", `${e.model}.glb`));
    return { ...e, tier: modelTier(info) };
  });
  // Music arrangements (D38, D40): public/tyrian-remaster/manifest.json, music[style][song].
  const music = {};
  const musicPath = join(root, "public/tyrian-remaster/manifest.json");
  if (existsSync(musicPath)) {
    const m = readJson(musicPath).music ?? {};
    for (const [style, songs] of Object.entries(m)) for (const [n, s] of Object.entries(songs)) (music[n] ??= { title: s.title, styles: [] }).styles.push(style);
  }
  // Redrawn pictures (D19).
  const picPath = join(root, "public/art/pictures.json");
  const pictures = existsSync(picPath) ? readJson(picPath) : {};
  // Damaged frames that still swap to sprites in level 1 (D54).
  const swapPath = join(root, "tests/render/modelSwap.test.ts");
  const knownDamageSwaps = [];
  if (existsSync(swapPath)) {
    for (const m of readFileSync(swapPath, "utf8").matchAll(/"([^"|]+)\|(\d)\|(\d+): damaged frames ([\d,]+) \(normal ([\d,]+)\)"/g)) {
      knownDamageSwaps.push({ sheet: m[1], size: Number(m[2]), type: Number(m[3]), frames: m[4].split(",").map(Number), normal: m[5].split(",").map(Number) });
    }
  }
  return { grouped, ungrouped, models, assemblyOf, bake, flat, terrain, tileModels, music, pictures, knownDamageSwaps };
}

// --- The episode script ---

/** Summarise a section's non-level commands: what plays between levels. */
function sectionCommands(lines) {
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i];
    if (s[0] !== "]") continue;
    const c = s[1];
    const n = parseInt(s.slice(3), 10);
    if (c === "P") out.push(n > 900 ? { cmd: "palette" } : { cmd: "picture", pic: n });
    else if (c === "U" || c === "V" || c === "R") out.push({ cmd: "pan", pic: n });
    else if (c === "A") out.push({ cmd: "anim", file: "tyrend.anm" });
    else if (c === "W") out.push({ cmd: "text" });
    else if (c === "M") out.push({ cmd: "song", song: n });
    else if (c === "Q") out.push({ cmd: "episode end" });
    else if (c === "I") out.push({ cmd: "shop" });
    else if (c === "G") out.push({ cmd: "map" });
    else if (c === "F" || c === "B" || c === "C") out.push({ cmd: "fade" });
    else if (c === "g") out.push({ cmd: "galaga mode" });
    else if (c === "e") out.push({ cmd: "engage mode" });
    else if (c === "x") out.push({ cmd: "bonus game" });
  }
  return out;
}

/** The shops' item lists (]I[ is followed by 9 lines; rows 1 front, 2 rear, 5 and 6 sidekicks). */
function shopItems(lines) {
  const rows = Array.from({ length: 9 }, () => new Set());
  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].startsWith("]I[")) continue;
    for (let r = 0; r < 9 && i + 1 + r < lines.length; r++) {
      const buf = lines[i + 1 + r].length > 8 ? lines[i + 1 + r].slice(8) : "";
      for (const t of buf.trim().split(/\s+/)) if (/^\d+$/.test(t) && Number(t) > 0) rows[r].add(Number(t));
    }
  }
  return rows;
}

/** Every `]L[` with its section, and which difficulty takes it (`]h[` skips the next line on hard; `]H[` jumps away below hard). */
function levelRefs(m, script) {
  const refs = [];
  for (const sec of script.sections) {
    let afterSkip = false;
    let jumpBelowHard = false;
    let prevWasNormalOnly = false;
    sec.lines.forEach((line, i) => {
      if (line.startsWith("]h[")) {
        afterSkip = true;
        return;
      }
      if (line.startsWith("]H[")) jumpBelowHard = true;
      const pl = m.data.parsePlayLevel(line);
      if (!pl) {
        if (line.startsWith("]")) afterSkip = false;
        return;
      }
      let difficulty = "any";
      if (afterSkip) difficulty = "below hard";
      else if (prevWasNormalOnly || jumpBelowHard) difficulty = "hard+";
      prevWasNormalOnly = afterSkip;
      afterSkip = false;
      refs.push({ ...pl, levelName: pl.levelName.trim(), section: sec.number, difficulty });
    });
  }
  return refs;
}

// --- Static analysis of one level ---

/**
 * An enemy type's frames: all `ani` of them (an enemy that doesn't animate on its own can be set
 * going by events 19 and 24, which can also raise `ani`; the bot run says which frames show), and
 * its damaged frames (game.ts: dani != 0 animates egraphic[dgr-1 .. |dani|-1], else dgr replaces it).
 */
function enemyFrames(dat, aniByEvents = 0) {
  const count = Math.max(1, dat.ani, aniByEvents);
  const normal = uniq(dat.eGraphic.slice(0, count).filter((f) => f > 0 && f !== 999));
  const damage = [];
  if (dat.dAni !== 0) for (let k = dat.dGr - 1; k < Math.abs(dat.dAni); k++) damage.push(dat.eGraphic[k]);
  else if (dat.dGr > 0) damage.push(dat.dGr);
  return { normal, damage: uniq(damage.filter((f) => f > 0 && f !== 999 && !normal.includes(f))) };
}

function enemyKind(dat) {
  if (dat.armor === 0) return dat.value !== 0 ? "pickup" : "decor";
  return (dat.explosionType & 1) === 0 ? "ground" : "air";
}

/** Shot frames of a weapon: sprite id -> true. `player` uses player_shot_create's animation rule. */
function weaponFrames(w, player) {
  const out = [];
  if (!w) return out;
  for (let k = 0; k < Math.max(1, Math.min(8, w.max)); k++) {
    let sg = w.sg[k];
    if (!sg) continue;
    const del = w.del[k];
    const frames = player ? (del > 100 && del < 120 ? del - 100 + 1 : w.weapAni + 1) : Math.max(1, w.weapAni);
    for (let a = 0; a < frames; a++) {
      let f = sg + a;
      if (player && f >= 60000) {
        out.push(`tyrian.shp#5|special|${f - 60001}`); // option shapes table (D31a)
        continue;
      }
      if (f > 1000) f %= 1000;
      out.push(f >= (player ? 501 : 500) ? `tyrian.shp#11|1|${f - 500}` : `tyrian.shp#7|1|${f}`);
    }
  }
  return out;
}

/** Count how many times each structure pattern of the tileset occurs whole in the level's map. */
function matchTileModels(level, shapesFile, tileModels) {
  const out = {};
  const widths = [14, 14, 15];
  const heights = [300, 600, 600];
  for (const e of tileModels) {
    if (e.shapes !== shapesFile) continue;
    const L = e.layer;
    const w = widths[L];
    const h = heights[L];
    const map = level.maps[L];
    const sh = level.mapSh[L];
    const tileAt = (r, c) => sh[map[r * w + c]] - 1;
    const rows = e.tiles.length;
    const cols = e.tiles[0].length;
    let n = 0;
    for (let r = 0; r + rows <= h; r++) {
      for (let c = 0; c + cols <= w; c++) {
        let ok = true;
        for (let i = 0; i < rows && ok; i++) for (let j = 0; j < cols && ok; j++) if (e.tiles[i][j] >= 0 && tileAt(r + i, c + j) !== e.tiles[i][j]) ok = false;
        if (ok) n++;
      }
    }
    if (n > 0) out[e.model] = n;
  }
  return out;
}

/** Static inventory of one level of a tyrian?.lvl. */
function analyseLevel(m, res, level, sheetData) {
  const events = level.events;
  const { shapeFile } = m.tyrian2;
  // Shape banks (event 5) and their sheets; 21 and 26 are always there.
  const banks = new Set([21, 26]);
  for (const ev of events) if (ev.eventType === 5) for (const t of [ev.eventDat, ev.eventDat2, ev.eventDat3, ev.eventDat4]) if (t > 0 && t <= shapeFile.length) banks.add(t);
  const bankSheet = (bank) => {
    if (bank === 21) return res.spriteSheet11.id;
    if (bank === 26) return res.spriteSheet10.id;
    if (bank < 1 || bank > shapeFile.length) return null;
    return `newsh${shapeFile[bank - 1].toLowerCase()}.shp`;
  };
  // Enemy types: how each gets in, and how many events name it.
  const types = new Map();
  const add = (t, via, count = 0, extra = {}) => {
    if (t <= 0 || t >= res.enemyDat.length) return;
    let e = types.get(t);
    if (!e) types.set(t, (e = { type: t, via: new Set(), events: 0, links: new Set() }));
    e.via.add(via);
    e.events += count;
    e.links.add(extra.link ?? 0);
    if (!extra.arcadeOnly) e.everyGame = true;
    if (!extra.twoPlayer) e.onePlayer = true;
    e.minDifficulty = Math.min(e.minDifficulty ?? Infinity, extra.minDifficulty ?? 0);
  };
  const custom = new Map();
  const bossLinks = new Set();
  const relinks = [];
  const songs = [];
  const special = {};
  const smoothies = new Set();
  /** Events 24 (enemy global animate) and 19 (global move): link number -> the frame count they set. */
  const animated = new Map();
  // Event 63 skips the next eventdat events unless two players play; 66 skips the next eventdat2
  // events when the difficulty is eventdat or lower.
  let twoPlayerUntil = -1;
  const harder = [];
  for (let i = 0; i < events.length; i++) {
    const ev = events[i];
    const twoPlayer = i <= twoPlayerUntil;
    const minDifficulty = Math.max(0, ...harder.filter(([until]) => i <= until).map(([, d]) => d));
    if (ev.eventType === 63) twoPlayerUntil = Math.max(twoPlayerUntil, i + ev.eventDat);
    if (ev.eventType === 66 && ev.eventDat2 > 0) harder.push([i + ev.eventDat2, ev.eventDat + 1]);
    const flags = { twoPlayer, minDifficulty };
    if (ev.eventType === 24) animated.set(ev.eventDat4, Math.max(animated.get(ev.eventDat4) ?? 0, ev.eventDat));
    if (ev.eventType === 19 && ev.eventDat6 > 0) animated.set(ev.eventDat4, Math.max(animated.get(ev.eventDat4) ?? 0, ev.eventDat6));
    const et = ev.eventType;
    if (SPAWN_EVENTS.has(et)) add(ev.eventDat, "event", 1, { link: ev.eventDat4, ...flags });
    else if (et === GROUP_EVENT) for (let k = 0; k < 4; k++) add(ev.eventDat + k, "event", 1, { link: ev.eventDat4, ...flags });
    else if (CUSTOM_EVENTS.has(et)) {
      // One entry per picture: a level can build a whole structure from these (TORM has 549).
      const bank = ev.eventDat3 > 0 ? ev.eventDat3 : res.enemyDat[0].shapeBank;
      const k = `${bank}|${ev.eventDat}`;
      const c = custom.get(k) ?? { graphic: ev.eventDat, bank, links: new Set(), events: 0, onePlayer: false };
      c.links.add(ev.eventDat4);
      c.events++;
      if (!flags.twoPlayer) c.onePlayer = true;
      custom.set(k, c);
    }
    else if (et === DROP_EVENT || et === ARCADE_DROP_EVENT) {
      const arcadeOnly = et === ARCADE_DROP_EVENT;
      add(ev.eventDat, "drop", 1, { arcadeOnly, ...flags });
      if (ev.eventDat === RANDOM_SPECIAL) for (const t of RANDOM_SPECIALS) add(t, "drop", 0, { arcadeOnly, ...flags });
    } else if (et === BOSS_EVENT) {
      if (ev.eventDat > 0) bossLinks.add(ev.eventDat);
      if (ev.eventDat2 > 0) bossLinks.add(ev.eventDat2);
      special["boss bar"] = (special["boss bar"] ?? 0) + 1;
    } else if (et === RELINK_EVENT) relinks.push([ev.eventDat, ev.eventDat2]);
    if (et === 35) songs.push(ev.eventDat);
    if (et === 64 && ev.eventDat2 !== 0) smoothies.add(SMOOTHIES[ev.eventDat] ?? `smoothie ${ev.eventDat}`);
    if (SPECIAL_EVENTS[et]) special[SPECIAL_EVENTS[et]] = (special[SPECIAL_EVENTS[et]] ?? 0) + 1;
  }
  for (const t of level.levelEnemy) add(t, "random");
  for (const t of m.levelSprites.ARMOR_SHIP_TYPES) add(t, "armour ship");
  // What they launch and leave behind, transitively.
  const queue = [...types.keys()];
  while (queue.length) {
    const t = queue.pop();
    const dat = res.enemyDat[t];
    for (const [next, via] of [[dat.eLaunchType % 1000, "launch"], [dat.eEnemyDie, "dies into"]]) {
      if (next <= 0 || next >= res.enemyDat.length) continue;
      const had = types.has(next);
      add(next, via);
      if (!had) queue.push(next);
    }
  }
  // Bosses: enemies created with a boss bar's link number (or one renamed to it).
  let grew = true;
  while (grew) {
    grew = false;
    for (const [from, to] of relinks) if (bossLinks.has(to) && !bossLinks.has(from)) bossLinks.add(from), (grew = true);
  }
  const enemies = [];
  for (const e of [...types.values()].sort((a, b) => a.type - b.type)) {
    const dat = res.enemyDat[e.type];
    const sheet = bankSheet(dat.shapeBank);
    const loaded = banks.has(dat.shapeBank);
    const size = dat.eSize === 1 ? 2 : 1;
    const { normal, damage } = enemyFrames(dat, Math.max(0, ...[...e.links].map((l) => animated.get(l) ?? 0)));
    const boss = [...e.links].some((l) => bossLinks.has(l));
    const shots = uniq(dat.tur.filter((w) => w > 0 && w < 250).flatMap((w) => weaponFrames(res.items.weapons[w], false)));
    enemies.push({
      type: e.type,
      kind: enemyKind(dat),
      via: [...e.via].sort(),
      events: e.events,
      sheet: loaded ? sheet : null,
      // The C draws an enemy of an unloaded bank with whatever sheet its slot last had.
      unloadedBank: loaded ? undefined : dat.shapeBank,
      size,
      normal,
      damage,
      boss: boss || undefined,
      arcadeOnly: e.everyGame ? undefined : true,
      twoPlayerOnly: e.onePlayer ? undefined : true,
      // The lowest initialDifficulty that spawns it, when above normal (2): 3 hard, 4 impossible...
      minDifficulty: e.minDifficulty > 2 ? e.minDifficulty : undefined,
      shots,
      sheetMissing: sheet && !sheetData(sheet) ? true : undefined,
    });
  }
  for (const c of [...custom.values()].sort((a, b) => a.bank - b.bank || a.graphic - b.graphic)) {
    const sheet = banks.has(c.bank) ? bankSheet(c.bank) : null;
    const size = res.enemyDat[0].eSize === 1 ? 2 : 1;
    enemies.push({ type: 0, kind: "custom", via: ["event"], events: c.events, sheet, unloadedBank: sheet ? undefined : c.bank, size, normal: [c.graphic], damage: [], boss: [...c.links].some((l) => bossLinks.has(l)) || undefined, twoPlayerOnly: c.onePlayer ? undefined : true, shots: [] });
  }
  return {
    banks: [...banks].sort(sortNum).map((b) => bankSheet(b)),
    enemies,
    bossLinks: [...bossLinks].sort(sortNum),
    songs: uniq(songs),
    special,
    smoothies: [...smoothies].sort(),
  };
}

// --- The bot run ---

/** Play every section that has a `]L[` with the test bot; per level (episode.lvlFileNum), ticks seen per frame/type/shot. */
async function playAll(m, files, episodes, log) {
  const { g } = m.state;
  const hdt = files.get("tyrian.hdt");
  const out = new Map();
  for (const ep of episodes) {
    const script = m.data.parseEpisodeScript(files.get(`levels${ep}.dat`));
    for (const sec of script.sections) {
      if (!sec.lines.some((l) => l.startsWith("]L["))) continue;
      const branches = sec.lines.some((l) => l.startsWith("]h[") || l.startsWith("]H["));
      for (const difficulty of branches ? [m.state.DIFFICULTY_NORMAL, m.state.DIFFICULTY_HARD] : [m.state.DIFFICULTY_NORMAL]) {
        m.mtrand.mt_srand(ep * 1000 + sec.number);
        g.res = m.resources.buildResources(files, ep);
        m.helptext.loadHelpText(hdt);
        m.newgame.newOnePlayerGame(ep, difficulty);
        let ok;
        try {
          ok = m.tyrian2.loadLevel(files, ep, sec.number);
        } catch (err) {
          log(`  ${ep}.${sec.number}: failed to load (${err.message})`);
          continue;
        }
        if (!ok || g.episodeNum !== ep) continue;
        const id = `${ep}.${g.lvlFileNum}`;
        if (out.has(id)) continue;
        g.player[0].items.weapon[0].power = 11;
        m.game.startLevel();
        m.input.clearSimInput();
        const r = { section: sec.number, difficulty: difficulty === m.state.DIFFICULTY_HARD ? "hard" : "normal", ticks: 0, completed: false, frames: new Map(), frameTypes: new Map(), types: new Map(), shots: new Map(), playerShots: new Map(), bossBars: new Set() };
        let result = { levelOver: false, completed: false };
        try {
        result = m.game.tick();
        for (let t = 0; t < 60000 && !result.levelOver; t++) {
          // Which enemy type shows which frame now (the frame drawn is egr[enemycycle - 1]).
          const typeOf = new Map();
          for (let i = 0; i < 100; i++) {
            if (g.enemyAvail[i] === 1) continue;
            const e = g.enemy[i];
            const sheet = m.tyrian2.enemySprite2s(e);
            const k = e.enemycycle >= 1 && e.enemycycle <= 20 ? e.egr[e.enemycycle - 1] : 0;
            if (sheet && k > 0) typeOf.set(frameKey(sheet.id, e.size === 1 ? 2 : 1, k), e.enemytype);
          }
          for (const d of m.draw.drawList.items) {
            if (d.kind !== "sprite2") continue;
            if (d.key >= m.draw.ENEMY_KEY_BASE) {
              if (d.groupIndex >= 0 && d.groupFirst) {
                const k = frameKey(d.sheet.id, d.groupSize, d.groupIndex);
                r.frames.set(k, (r.frames.get(k) ?? 0) + 1);
                const ty = typeOf.get(k);
                if (ty !== undefined) {
                  if (!r.frameTypes.has(k)) r.frameTypes.set(k, new Set());
                  r.frameTypes.get(k).add(ty);
                }
              }
            } else if (d.key >= m.shots.PLAYER_SHOT_KEY_BASE) {
              if (d.effect === "darken") continue;
              const k = frameKey(d.sheet.id, d.size, d.index);
              r.playerShots.set(k, (r.playerShots.get(k) ?? 0) + 1);
            } else if (d.key >= 20000 && d.key < 30000) {
              const k = frameKey(d.sheet.id, d.size, d.index);
              r.shots.set(k, (r.shots.get(k) ?? 0) + 1);
            }
          }
          for (let i = 0; i < 100; i++) {
            if (g.enemyAvail[i] === 1) continue;
            const ty = g.enemy[i].enemytype;
            r.types.set(ty, (r.types.get(ty) ?? 0) + 1);
          }
          for (const b of g.boss_bar) if (b.link_num !== 0) r.bossBars.add(b.link_num);
          m.bot.botTick(t);
          result = m.game.tick();
          r.ticks = t + 1;
        }
        } catch (err) {
          // The sim stopped (a port gap the episode route never reaches); keep what was seen.
          r.error = String(err.message ?? err);
        }
        r.completed = !!result.completed;
        out.set(id, r);
        log(`  played ${id} ${g.levelName.trim()} (section ${sec.number}, ${r.difficulty}): ${r.completed ? "completed" : "not completed"} in ${r.ticks} ticks${r.error ? ` (stopped: ${r.error})` : ""}`);
      }
    }
  }
  return out;
}

// --- The inventory ---

/**
 * Build the inventory. `m` holds the loaded modules (MODULES' keys), `files.get(name)` reads the
 * game data. Options: play (bot run), episodes (default every levels?.dat present), root (repo).
 */
export async function buildInventory(m, files, { play = true, episodes, root = ROOT, log = () => {} } = {}) {
  const repo = repoStatus(root);
  const eps = episodes ?? [1, 2, 3, 4, 5].filter((e) => files.get(`levels${e}.dat`) && files.get(`tyrian${e}.lvl`));
  const sheetCache = new Map();
  const sheetData = (id) => {
    if (!sheetCache.has(id)) {
      let bytes = null;
      const t = /^tyrian\.shp#(\d+)$/.exec(id);
      if (t) bytes = m.data.mainShapeTables(files.get("tyrian.shp"))[Number(t[1])];
      else bytes = files.get(id) ?? null;
      sheetCache.set(id, bytes);
    }
    return sheetCache.get(id);
  };
  const blankCache = new Map();
  /** Whether a frame draws nothing (all four 12x14 tiles of a 2x2 transparent). */
  const blank = (sheet, size, index) => {
    const k = frameKey(sheet, size, index);
    if (!blankCache.has(k)) {
      const data = sheetData(sheet);
      let b = false;
      if (data) b = (size === 1 ? [0] : [0, 1, 19, 20]).every((o) => m.data.decodeSprite2(data, index + o).pixels.every((c) => c < 0));
      blankCache.set(k, b);
    }
    return blankCache.get(k);
  };

  // Units: the work items. A frame belongs to an assembly (one script for a multi-piece object), else
  // to its model's script (model path without -fN), else it stands alone as a sprite.
  const unitOfFrame = (sheet, size, f) => {
    const k = frameKey(sheet, size, f);
    const asm = repo.assemblyOf.get(k);
    if (asm) return asm;
    const model = repo.grouped.get(k);
    if (model) return model.replace(/^enemies\//, "").replace(/-f\d+$/, "");
    return `${sheetSlug(sheet)}-${f}`;
  };
  /**
   * The unit of an enemy type: the assembly or model script most of its frames belong to (a model
   * can cover identical pictures on other sheets), else its first frame's own sprite unit.
   */
  const unitOfType = (sheet, size, frames) => {
    const votes = new Map();
    for (const f of frames) {
      const k = frameKey(sheet, size, f);
      if (!repo.assemblyOf.has(k) && !repo.grouped.has(k)) continue;
      const u = unitOfFrame(sheet, size, f);
      votes.set(u, (votes.get(u) ?? 0) + 1);
    }
    let best = null;
    for (const [u, n] of votes) if (!best || n > best[1]) best = [u, n];
    return best ? best[0] : unitOfFrame(sheet, size, frames[0]);
  };
  /** Status of one frame: blank, flat (art drawn instead of a model), flagship, concept, basic, sprite. */
  const frameStatus = (sheet, size, f) => {
    if (blank(sheet, size, f)) return "blank";
    if (repo.flat.has(`${sheet}|${f}`)) return "flat";
    const model = repo.grouped.get(frameKey(sheet, size, f));
    if (!model) return "sprite";
    return repo.models.get(model)?.tier ?? "missing";
  };

  const units = new Map();
  const unitFor = (id) => {
    let u = units.get(id);
    if (!u) units.set(id, (u = { id, kinds: new Set(), frames: new Set(), damageFrames: new Set(), seen: new Set(), types: new Set(), levels: new Set(), episodes: new Set(), botOnly: new Set(), events: 0, ticks: 0, boss: false, conditional: true }));
    return u;
  };
  const shotAssets = new Map();
  const shotFor = (k) => {
    let s = shotAssets.get(k);
    if (!s) shotAssets.set(k, (s = { id: k, enemyLevels: new Set(), playerEpisodes: new Set(), episodes: new Set(), ticks: 0 }));
    return s;
  };
  const tilesets = new Map();
  const songs = new Map();
  const modelledCache = new Map();
  /** Tiles of a tileset's layer that some structure model's pattern covers. */
  const modelledTiles = (shapesFile, layer) => {
    const k = `${shapesFile}|${layer}`;
    if (!modelledCache.has(k)) modelledCache.set(k, new Set(repo.tileModels.filter((e) => e.shapes === shapesFile && e.layer === layer).flatMap((e) => e.tiles.flat().filter((t) => t >= 0))));
    return modelledCache.get(k);
  };
  const levels = [];
  const episodesOut = [];
  const played = play ? await playAll(m, files, eps, log) : new Map();
  /** Objects the bot run drew that the level's static list doesn't name (an unloaded bank's borrowed sheet, say). */
  const botFound = [];

  for (const ep of eps) {
    const res = m.resources.buildResources(files, ep);
    const script = m.data.parseEpisodeScript(files.get(`levels${ep}.dat`));
    const lvlFile = files.get(`tyrian${ep}.lvl`);
    const { lvlPos } = m.data.readLevelPositions(lvlFile);
    const refs = levelRefs(m, script);
    // Player weapons the episode's shops offer: front (row 1), rear (row 2), sidekicks (rows 5, 6).
    const shop = shopItems(script.lines);
    const playerWeapons = new Map();
    for (const id of [...shop[1], ...shop[2]]) {
      const port = res.items.weaponPorts[id];
      if (!port) continue;
      for (let mode = 0; mode < Math.max(1, port.opNum); mode++) for (const w of port.op[mode]) if (w > 0) for (const f of weaponFrames(res.items.weapons[w], true)) playerWeapons.set(f, port.name);
    }
    for (const id of [...shop[5], ...shop[6]]) {
      const o = res.items.options[id];
      if (o && o.wPort > 0) for (const f of weaponFrames(res.items.weapons[o.wPort], true)) playerWeapons.set(f, o.name);
    }
    for (const f of playerWeapons.keys()) {
      const s = shotFor(f);
      s.playerEpisodes.add(ep);
      s.episodes.add(ep);
    }
    // Cutscenes and other between-level commands, per section.
    const cutscenes = [];
    for (const sec of script.sections) {
      const cmds = sectionCommands(sec.lines).filter((c) => !["shop", "map", "fade", "palette"].includes(c.cmd));
      for (const c of cmds) if (c.pic !== undefined) c.redrawn = repo.pictures[String(c.pic)] !== undefined;
      if (cmds.length) cutscenes.push({ section: sec.number, commands: cmds });
      for (const c of cmds) if (c.cmd === "song") songUse(c.song, `${ep}.s${sec.number}`, ep, "script");
    }

    // One row per distinct level (tyrian?.lvl entry); script refs listed with it.
    const byFile = new Map();
    for (const r of refs) {
      if (!byFile.has(r.lvlFileNum)) byFile.set(r.lvlFileNum, []);
      byFile.get(r.lvlFileNum).push(r);
    }
    const epLevels = [];
    for (const [fileNum, rs] of [...byFile].sort((a, b) => a[1][0].section - b[1][0].section || a[0] - b[0])) {
      const id = `${ep}.${fileNum}`;
      const level = m.data.parseLevel(lvlFile, lvlPos[(fileNum - 1) * 2]);
      const tileset = `shapes${level.shapeFile.toLowerCase()}`;
      const shapesFile = `${tileset}.dat`;
      const st = analyseLevel(m, res, level, sheetData);
      // Background layers: tiles used, and those with HD art.
      const hd = repo.terrain.get(tileset);
      const layers = [0, 1, 2].map((L) => {
        const used = new Set();
        for (const b of level.maps[L]) {
          const t = level.mapSh[L][b] - 1;
          if (t >= 0) used.add(t);
        }
        const art = hd?.[String(L)] ?? new Set();
        const modelled = modelledTiles(shapesFile, L);
        const n = (f) => [...used].filter(f).length;
        return { layer: L, tiles: used.size, hd: n((t) => art.has(t)), modelled: n((t) => modelled.has(t)), covered: n((t) => art.has(t) || modelled.has(t)), used };
      });
      let ts = tilesets.get(tileset);
      if (!ts) tilesets.set(tileset, (ts = { id: tileset, levels: new Set(), episodes: new Set(), used: [new Set(), new Set(), new Set()] }));
      ts.levels.add(id);
      ts.episodes.add(ep);
      layers.forEach((l) => l.used.forEach((t) => ts.used[l.layer].add(t)));
      const tileModels = matchTileModels(level, shapesFile, repo.tileModels);

      // Enemy units.
      const play = played.get(id);
      const levelUnits = new Map();
      const enemies = [];
      const shots = new Set();
      for (const e of st.enemies) {
        const sheet = e.sheet;
        const entry = { type: e.type, kind: e.kind, unit: null, via: e.via.join("+"), events: e.events || undefined, ticks: play ? play.types.get(e.type) ?? 0 : undefined, boss: e.boss, arcadeOnly: e.arcadeOnly, twoPlayerOnly: e.twoPlayerOnly, minDifficulty: e.minDifficulty };
        if (!sheet) {
          entry.unloadedBank = e.unloadedBank;
          enemies.push(entry);
          continue;
        }
        const live = e.normal.filter((f) => !blank(sheet, e.size, f));
        if (live.length === 0 && e.damage.every((f) => blank(sheet, e.size, f))) {
          entry.unit = null;
          entry.blank = true;
          enemies.push(entry);
          continue;
        }
        const unitId = unitOfType(sheet, e.size, live.length ? live : e.normal);
        entry.unit = unitId;
        enemies.push(entry);
        const u = unitFor(unitId);
        u.kinds.add(e.kind);
        u.sheet ??= sheet;
        u.size ??= e.size;
        for (const f of e.normal) u.frames.add(frameKey(sheet, e.size, f));
        for (const f of e.damage) u.damageFrames.add(frameKey(sheet, e.size, f));
        u.types.add(`${ep <= 3 ? "e1-3" : `e${ep}`}:${e.type}`);
        u.levels.add(id);
        u.episodes.add(ep);
        u.events += e.events;
        if (e.boss) u.boss = true;
        if (!e.twoPlayerOnly && !e.arcadeOnly) u.onePlayer = true;
        if (!e.via.every((v) => v === "armour ship" || v === "dies into") || !m.levelSprites.ARMOR_SHIP_TYPES.includes(e.type)) u.conditional = false;
        levelUnits.set(unitId, (levelUnits.get(unitId) ?? 0) + e.events);
        for (const s of e.shots) {
          shots.add(s);
          const sa = shotFor(s);
          sa.enemyLevels.add(id);
          sa.episodes.add(ep);
        }
      }
      // Bot run: ticks per unit; objects it drew that the static list doesn't name join the level.
      let playOut;
      if (play) {
        const unitTicks = {};
        for (const [k, n] of [...play.frames].sort((a, b) => a[0].localeCompare(b[0]))) {
          const [sheet, sizeS, fS] = k.split("|");
          const size = Number(sizeS);
          const f = Number(fS);
          if (blank(sheet, size, f)) continue;
          // A frame of a type the static list has on this sheet belongs to that type's unit (an
          // animation or damaged frame); otherwise it is its own unit (a borrowed sheet, say).
          const types = [...(play.frameTypes.get(k) ?? [])].sort(sortNum);
          // (enemies[i] is the output row of st.enemies[i]; type 0 has a row per custom picture.)
          const owner = st.enemies.findIndex((e) => types.includes(e.type) && e.sheet === sheet && e.size === size && (e.type !== 0 || e.normal.includes(f)));
          const ownerUnit = owner >= 0 ? enemies[owner].unit : null;
          const unitId = ownerUnit ?? unitOfFrame(sheet, size, f);
          unitTicks[unitId] = (unitTicks[unitId] ?? 0) + n;
          const u = unitFor(unitId);
          if (!u.sheet) {
            u.sheet = sheet;
            u.size = size;
            for (const t of types) u.kinds.add(enemyKind(res.enemyDat[t]));
            if (types.length === 0) u.kinds.add("unknown");
          }
          u.ticks += n;
          u.onePlayer = true;
          u.seen.add(k);
          const damaged = types.some((t) => enemyFrames(res.enemyDat[t]).damage.includes(f));
          if (damaged) u.damageFrames.add(k);
          else if (!u.damageFrames.has(k)) u.frames.add(k);
          if (!levelUnits.has(unitId)) {
            botFound.push(`${id} ${k} -> ${unitId} (${n} ticks${types.length ? `, type ${types.join("/")}` : ""})`);
            levelUnits.set(unitId, 0);
            u.levels.add(id);
            u.episodes.add(ep);
            u.botOnly.add(id);
            u.conditional = false;
          }
        }
        for (const [k, n] of play.shots) shotFor(k).ticks += n;
        for (const [k, n] of play.playerShots) shotFor(k).ticks += n;
        const seen = new Set(Object.keys(unitTicks));
        playOut = {
          section: play.section,
          difficulty: play.difficulty,
          completed: play.completed,
          error: play.error,
          ticks: play.ticks,
          unitsSeen: seen.size,
          unitsNotSeen: [...levelUnits.keys()].filter((u) => !seen.has(u)).sort(),
          unitsFoundByBot: [...levelUnits.keys()].filter((u) => units.get(u).botOnly.has(id)).sort(),
          typesNotListed: [...play.types.keys()].filter((t) => !st.enemies.some((e) => e.type === t)).sort(sortNum),
          bossBarsSeen: [...play.bossBars].sort(sortNum),
          enemyShotFrames: play.shots.size,
        };
      }
      // Songs.
      for (const r of rs) songUse(r.levelSong, id, ep, "level");
      for (const s of st.songs) songUse(s, id, ep, "event");

      const row = {
        id,
        episode: ep,
        lvlFileNum: fileNum,
        name: rs[0].levelName,
        mapFile: level.mapFile,
        refs: rs.map((r) => ({ section: r.section, name: r.levelName, song: r.levelSong, nextLevel: r.nextLevel, difficulty: r.difficulty, bonus: r.bonusLevelCurrent || undefined, normalBonus: r.normalBonusLevelCurrent || undefined })),
        tileset,
        layers: layers.map(({ used, ...rest }) => rest),
        tileModels,
        banks: st.banks,
        enemyTypes: enemies.length,
        enemies,
        units: [...levelUnits.keys()].sort(),
        bossBars: st.bossLinks,
        bossUnits: uniq(st.enemies.map((e, i) => (e.boss ? enemies[i].unit : null)).filter(Boolean)).sort(),
        enemyShots: [...shots].sort(),
        pickups: uniq(enemies.filter((e) => e.kind === "pickup" && e.unit).map((e) => e.unit)).sort(),
        songs: uniq([...rs.map((r) => r.levelSong), ...st.songs]),
        smoothies: st.smoothies,
        specialEvents: st.special,
        play: playOut,
      };
      levels.push(row);
      epLevels.push(id);
    }
    episodesOut.push({ episode: ep, levels: epLevels, cutscenes, playerWeaponFrames: playerWeapons.size, shopWeapons: { front: [...shop[1]].sort(sortNum), rear: [...shop[2]].sort(sortNum), sidekicks: uniq([...shop[5], ...shop[6]]).sort(sortNum) } });
  }

  function songUse(n, where, ep, how) {
    if (!(n > 0)) return;
    let s = songs.get(n);
    if (!s) songs.set(n, (s = { song: n, levels: new Set(), episodes: new Set(), script: new Set() }));
    if (how === "script") s.script.add(where);
    else s.levels.add(where);
    s.episodes.add(ep);
  }

  // --- Asset tables with status ---
  const keyStatus = (k) => {
    const [sheet, size, f] = k.split("|");
    return frameStatus(sheet, Number(size), Number(f));
  };
  // Status over the frames the bot run saw, when it saw the unit (static frames over-cover: an
  // enemy that event 24 animates from a later frame never shows its first), else the static ones.
  const unitStatus = (u) => {
    const frames = play && u.seen.size ? [...u.seen].filter((k) => !u.damageFrames.has(k)) : [...u.frames];
    const st = frames.map(keyStatus).filter((s) => s !== "blank");
    const dmg = [...u.damageFrames].map(keyStatus).filter((s) => s !== "blank");
    let status;
    if (st.length === 0) status = "blank";
    else if (st.every((s) => s === "flat")) status = "flat";
    else if (st.every((s) => s === "flagship")) status = "flagship";
    else if (st.every((s) => s === "flagship" || s === "concept" || s === "basic")) status = st.includes("basic") ? "basic" : "concept";
    else if (st.some((s) => s !== "sprite")) status = "partial";
    else status = "sprite";
    // A damaged frame without a model of its own is drawn with the unit's intact model, damaged by
    // the shader (D87): missing only while no intact frame has a model.
    const intactModel = st.some((s) => s === "flagship" || s === "concept" || s === "basic");
    const damageMissing = intactModel ? [] : [...u.damageFrames].filter((k) => keyStatus(k) === "sprite").sort(keySort);
    return { status, damage: dmg.length === 0 ? "none" : damageMissing.length ? "missing" : "modelled", damageMissing };
  };
  const unitList = [...units.values()].map((u) => {
    const s = unitStatus(u);
    const scriptName = u.id;
    const known = repo.knownDamageSwaps.filter((k) => k.frames.some((f) => u.damageFrames.has(frameKey(k.sheet, k.size, f))));
    return {
      id: u.id,
      kind: [...u.kinds].sort().join("+"),
      sheet: u.sheet,
      size: u.size,
      frames: byTile(u.frames),
      damageFrames: byTile(u.damageFrames),
      status: s.status,
      damage: s.damage,
      damageMissing: s.damageMissing.length ? byTile(s.damageMissing) : undefined,
      damageMissingCount: s.damageMissing.length || undefined,
      knownDamageSwap: known.length ? true : undefined,
      bake: repo.bake.get(scriptName),
      framesSeen: play ? byTile(u.seen) : undefined,
      unmodelledUnseen: play && u.seen.size ? byTile([...u.frames].filter((k) => !u.seen.has(k) && keyStatus(k) === "sprite")) : undefined,
      botOnlyLevels: u.botOnly.size ? [...u.botOnly].sort(levelSort) : undefined,
      boss: u.boss || undefined,
      conditional: u.conditional || undefined,
      twoPlayerOnly: u.onePlayer ? undefined : true,
      types: [...u.types].sort(),
      levels: [...u.levels].sort(levelSort),
      episodes: [...u.episodes].sort(sortNum),
      events: u.events,
      ticks: play ? u.ticks : undefined,
    };
  }).sort((a, b) => a.id.localeCompare(b.id));

  const shotList = [...shotAssets.values()].map((s) => {
    const [sheet, , f] = s.id.split("|");
    const status = sheet === "tyrian.shp#5" ? "special" : repo.flat.has(`${sheet}|${f}`) ? "flat" : "sprite";
    return { id: s.id, status, enemyLevels: s.enemyLevels.size, playerEpisodes: [...s.playerEpisodes].sort(sortNum), episodes: [...s.episodes].sort(sortNum), ticks: play ? s.ticks : undefined };
  }).sort((a, b) => a.id.localeCompare(b.id, "en", { numeric: true }));

  const tilesetList = [...tilesets.values()].map((t) => {
    const hd = repo.terrain.get(t.id);
    const models = repo.tileModels.filter((e) => e.shapes === `${t.id}.dat`);
    const art = (L) => hd?.[String(L)] ?? new Set();
    return {
      id: t.id,
      levels: [...t.levels].sort(levelSort),
      episodes: [...t.episodes].sort(sortNum),
      tiles: t.used.map((s) => s.size),
      hd: t.used.map((s, L) => [...s].filter((x) => art(L).has(x)).length),
      modelled: t.used.map((s, L) => [...s].filter((x) => modelledTiles(`${t.id}.dat`, L).has(x)).length),
      covered: t.used.map((s, L) => [...s].filter((x) => art(L).has(x) || modelledTiles(`${t.id}.dat`, L).has(x)).length),
      tileModels: models.length,
      tileModelTiers: countBy(models.map((e) => e.tier)),
    };
  }).sort((a, b) => b.levels.length - a.levels.length || a.id.localeCompare(b.id));

  const songList = [...songs.values()].map((s) => ({
    song: s.song,
    title: repo.music[String(s.song)]?.title,
    remaster: (repo.music[String(s.song)]?.styles ?? []).sort(),
    levels: [...s.levels].sort(levelSort),
    script: [...s.script].sort(),
    episodes: [...s.episodes].sort(sortNum),
  })).sort((a, b) => a.song - b.song);

  // --- Episode summaries ---
  const levelById = new Map(levels.map((l) => [l.id, l]));
  const unitById = new Map(unitList.map((u) => [u.id, u]));
  for (const e of episodesOut) {
    const ls = e.levels.map((id) => levelById.get(id));
    const us = uniq(ls.flatMap((l) => l.units)).map((id) => unitById.get(id));
    const frames = new Set();
    for (const u of us) for (const k of [...units.get(u.id).frames, ...units.get(u.id).damageFrames]) frames.add(k);
    // Enemy units: everything modelled but pickups (decor, armour 0, is boss and scenery pieces).
    const modelUnits = us.filter((u) => u.kind !== "pickup" && u.status !== "blank");
    const tss = uniq(ls.map((l) => l.tileset));
    e.summary = {
      levels: ls.length,
      uniqueSprites: frames.size,
      units: us.length,
      enemyUnits: modelUnits.length,
      enemyUnitsModelled: modelUnits.filter((u) => ["flagship", "concept", "basic"].includes(u.status)).length,
      enemyUnitsFlagship: modelUnits.filter((u) => u.status === "flagship").length,
      damageFramesMissing: us.reduce((n, u) => n + (u.damageMissingCount ?? 0), 0),
      tilesets: tss.length,
      tilesetsWithHd: tss.filter((t) => repo.terrain.has(t)).length,
      tilesetsWithModels: tss.filter((t) => repo.tileModels.some((x) => x.shapes === `${t}.dat`)).length,
      bossLevels: ls.filter((l) => l.bossBars.length > 0).length,
      bossUnits: uniq(ls.flatMap((l) => l.bossUnits)).length,
      songs: uniq(ls.flatMap((l) => l.songs)).length,
      songsRemastered: uniq(ls.flatMap((l) => l.songs)).filter((n) => repo.music[String(n)]).length,
      pictures: uniq(e.cutscenes.flatMap((c) => c.commands.filter((x) => x.pic !== undefined).map((x) => x.pic))).length,
      picturesRedrawn: uniq(e.cutscenes.flatMap((c) => c.commands.filter((x) => x.pic !== undefined && x.redrawn).map((x) => x.pic))).length,
    };
  }

  // --- Ranking: not-done assets used most widely first ---
  const isPickup = (u) => u.kind === "pickup";
  const unitRow = (u) => ({
    id: u.id,
    what: `${u.kind}${u.boss ? " (boss)" : ""}`,
    status: `${u.status}${u.damage === "missing" ? `, ${u.damageMissingCount} damaged frames unmodelled` : ""}`,
    levels: u.levels.length,
    episodes: u.episodes.length,
    events: u.events,
    ticks: u.ticks,
    conditional: u.conditional,
    twoPlayerOnly: u.twoPlayerOnly,
  });
  // Enemies (and decor, bosses' pieces): done is a flagship model with every damaged frame modelled.
  const rankUnits = unitList.filter((u) => !isPickup(u) && u.status !== "blank" && (u.status !== "flagship" || u.damage === "missing")).map(unitRow);
  // Pickups: done is flat art (D42); the armour crates are models by D56.
  const rankPickups = unitList.filter((u) => isPickup(u) && !["flat", "blank"].includes(u.status)).map(unitRow);
  const sum = (xs) => xs.reduce((a, b) => a + b, 0);
  const rankTilesets = tilesetList.filter((t) => sum(t.covered) < sum(t.tiles)).map((t) => ({
    id: t.id,
    what: `tiles ${t.tiles.join("/")} (layers 0/1/2)`,
    status: `HD art ${t.hd.join("/")}, in structure models ${t.modelled.join("/")}, ${t.tileModels} structure models`,
    uncovered: t.tiles.map((n, L) => n - t.covered[L]),
    levels: t.levels.length,
    episodes: t.episodes.length,
    events: 0,
    ticks: undefined,
  }));
  const rankShots = shotList.filter((s) => s.status === "sprite").map((s) => ({
    kind: "shot",
    id: s.id,
    what: s.playerEpisodes.length ? (s.enemyLevels ? "enemy and player shot" : "player shot") : "enemy shot",
    status: "no flat art",
    levels: s.enemyLevels,
    episodes: s.episodes.length,
    events: 0,
    ticks: s.ticks,
  }));
  const byLeverage = (a, b) => b.levels - a.levels || b.episodes - a.episodes || (b.ticks ?? 0) - (a.ticks ?? 0) || b.events - a.events || a.id.localeCompare(b.id);
  const ranking = {
    units: rankUnits.sort(byLeverage),
    pickups: rankPickups.sort(byLeverage),
    tilesets: rankTilesets.sort(byLeverage),
    shots: rankShots.sort(byLeverage),
    songs: songList.filter((s) => s.remaster.length === 0).map((s) => s.song),
  };

  return {
    version: 1,
    generator: "tools/inventory.mjs",
    regenerate: "npm run inventory",
    played: play,
    episodes: episodesOut,
    levels,
    units: unitList,
    shots: shotList,
    tilesets: tilesetList,
    songs: songList,
    ranking,
    notes: {
      foundByBot: botFound.sort(),
      maps: "structure-model counts scan the whole map, including rows a level may never scroll to",
    },
  };
}

/** JSON with the outer levels indented and anything deeper on one line, so a level's enemy or a unit's frames take a line each. */
export function stringify(v, depth = 0, maxDepth = 4) {
  if (depth >= maxDepth || v === null || typeof v !== "object") return JSON.stringify(v);
  const pad = " ".repeat(depth + 1);
  const end = " ".repeat(depth);
  if (Array.isArray(v)) return v.length ? `[\n${v.map((x) => pad + stringify(x, depth + 1, maxDepth)).join(",\n")}\n${end}]` : "[]";
  const entries = Object.entries(v).filter(([, x]) => x !== undefined);
  return entries.length ? `{\n${entries.map(([k, x]) => `${pad}${JSON.stringify(k)}: ${stringify(x, depth + 1, maxDepth)}`).join(",\n")}\n${end}}` : "{}";
}

function keySort(a, b) {
  const [sa, za, fa] = a.split("|");
  const [sb, zb, fb] = b.split("|");
  return sa.localeCompare(sb) || za - zb || fa - fb;
}

/** Frame keys ("sheet|size|frame") grouped as { "sheet|size": [frames] }, sorted. */
function byTile(keys) {
  const out = {};
  for (const k of [...keys].sort(keySort)) {
    const i = k.lastIndexOf("|");
    (out[k.slice(0, i)] ??= []).push(Number(k.slice(i + 1)));
  }
  return out;
}

function countBy(xs) {
  const o = {};
  for (const x of xs) o[x] = (o[x] ?? 0) + 1;
  return o;
}

function levelSort(a, b) {
  const [ea, la] = a.split(".").map(Number);
  const [eb, lb] = b.split(".").map(Number);
  return ea - eb || la - lb;
}

// --- Markdown ---

export function renderMarkdown(inv, top = 40) {
  const L = [];
  const p = (s = "") => L.push(s);
  const esc = (s) => String(s ?? "").replace(/\|/g, "\\|");
  const levelName = new Map(inv.levels.map((l) => [l.id, l.name]));
  const isEnemy = (u) => u.kind !== "pickup" && u.status !== "blank";
  const where = (ids, n = 8) => ids.slice(0, n).join(", ") + (ids.length > n ? ", ..." : "");
  p("# Tyrian 3D asset inventory");
  p();
  p("Every episode's levels and what each needs, with what the repo already has, so the remaster of");
  p("the rest of the game can go episode by episode with shared assets done first. Generated from");
  p("the game data and the repo by `tools/inventory.mjs`; the machine-readable version is");
  p("[`inventory.json`](inventory.json) (ids and counts; `levels[].enemies` has every enemy type per level).");
  p();
  p(`**Regenerate:** \`npm run inventory\` (static parse plus a bot run of every level, a few minutes; \`node tools/inventory.mjs --no-play\` for the static part only, a few seconds). Needs the Tyrian 2.1 data in \`data/\` or \`TYRIAN_DATA\`.${inv.played ? "" : " This copy was generated without the bot run."}`);
  p();
  p("## How to read it");
  p();
  p("- **Level** `E.N`: episode E, level N of `tyrianE.lvl` (the `]L[` command's level number). A level the");
  p("  script reaches from several sections (or on one difficulty only) lists each.");
  p("- **Unit**: one piece of modelling work, split the way the Blender scripts are: a multi-piece object");
  p("  (`assembly-*`, from `src/viewer/assemblies.json`), else one model script (`newshX-N`, with its");
  p("  animation frames `-f2`...), else a sprite with no model yet (`<sheet>-<frame>`). An enemy's damaged");
  p("  frames belong to its unit.");
  p("- **Status** of a unit: `flagship` = hard-surface model with the outline shell (D50-D53, D65);");
  p("  `concept` = concept-baked model (D44); `basic` = the first catalogue model (D15); `partial` = some");
  p("  frames have no model; `sprite` = no model; `flat` = flat painted art (D42); `blank` = empty frames.");
  p("  Done means `flagship` with every damaged frame modelled (enemies), `flat` (pickups, shots), and HD art");
  p("  or a structure model for every tile (tilesets).");
  p("- **Events**: level events that create it, summed over levels (static). **Ticks**: ticks on screen in");
  p("  the bot run (tests/sim/bot.ts: invulnerable, always firing, sweeping), summed over levels.");
  p("- **Conditional**: only the armour ship's chain, which comes to any level when armour is low (D56).\n- **2P only**: spawned only by events that two-player (or arcade) games run (event 63 skips them otherwise).");
  p();

  p("## Per-episode summary");
  p();
  p("| Episode | Levels | Unique sprites | Enemy units: flagship / older model / total | Damaged frames unmodelled | Tilesets: HD / structure models / total | Boss levels (boss units) | Songs (remastered) | Story pictures (redrawn) |");
  p("|---|---|---|---|---|---|---|---|---|");
  for (const e of inv.episodes) {
    const s = e.summary;
    p(`| ${e.episode} | ${s.levels} | ${s.uniqueSprites} | ${s.enemyUnitsFlagship} / ${s.enemyUnitsModelled - s.enemyUnitsFlagship} / ${s.enemyUnits} | ${s.damageFramesMissing} | ${s.tilesetsWithHd} / ${s.tilesetsWithModels} / ${s.tilesets} | ${s.bossLevels} (${s.bossUnits}) | ${s.songs} (${s.songsRemastered}) | ${s.pictures} (${s.picturesRedrawn}) |`);
  }
  p();
  const enemies = inv.units.filter(isEnemy);
  p(`Whole game: ${inv.levels.length} levels; ${enemies.length} enemy units (${enemies.filter((u) => u.status === "flagship").length} flagship, ${enemies.filter((u) => ["concept", "basic"].includes(u.status)).length} older-style models, ${enemies.filter((u) => ["sprite", "partial"].includes(u.status)).length} with frames still unmodelled), decor (indestructible boss and scenery pieces) included; ${inv.units.length - inv.units.filter(isEnemy).length} pickup and empty units; ${inv.tilesets.length} tilesets (${inv.tilesets.filter((t) => t.hd.some((n) => n > 0)).length} with HD art, ${inv.tilesets.filter((t) => t.tileModels > 0).length} with structure models); ${inv.shots.length} shot frames (${inv.shots.filter((s) => s.status === "flat").length} with flat art); ${inv.songs.length} songs used (${inv.songs.filter((s) => s.remaster.length).length} remastered).`);
  p();
  p("Unique sprites counts each enemy and pickup frame (normal and damaged) once per episode; boss units are");
  p("the units created with a boss bar's link number (event 79), pieces included.");
  p();

  p("## Highest-leverage work");
  p();
  p("Assets not done yet, those used by the most levels first (then episodes, then time on screen in the");
  p("bot run, then events). Doing these first means nothing is done twice for a later episode.");
  p();
  p("### Tilesets");
  p();
  p("A tileset is one shapes?.dat: HD terrain art (D57) and structure models (D34, D47) are per tileset,");
  p("so a tileset shared by many levels is the biggest single piece of terrain work.");
  p();
  p("| Tileset | Levels | Episodes | Tiles used (layers 0/1/2) | HD art (0/1/2) | In structure models (0/1/2) | Uncovered (0/1/2) | Levels using it |");
  p("|---|---|---|---|---|---|---|---|");
  for (const r of inv.ranking.tilesets) {
    const t = inv.tilesets.find((x) => x.id === r.id);
    p(`| ${esc(r.id)} | ${r.levels} | ${t.episodes.join(", ")} | ${t.tiles.join(" / ")} | ${t.hd.join(" / ")} | ${t.modelled.join(" / ")} | ${r.uncovered.join(" / ")} | ${t.levels.map((id) => `${id} ${esc(levelName.get(id))}`).join(", ")} |`);
  }
  p();
  p(`### Enemy models (top ${top})`);
  p();
  p("| # | Unit | Kind | Status | Levels | Episodes | Events | Ticks | Where |");
  p("|---|---|---|---|---|---|---|---|---|");
  const unitLevels = new Map(inv.units.map((u) => [u.id, u.levels]));
  inv.ranking.units.slice(0, top).forEach((r, i) => p(`| ${i + 1} | ${r.id}${r.conditional ? " (conditional)" : ""}${r.twoPlayerOnly ? " (2P only)" : ""} | ${esc(r.what)} | ${esc(r.status)} | ${r.levels} | ${r.episodes} | ${r.events} | ${r.ticks ?? "-"} | ${where(unitLevels.get(r.id))} |`));
  p();
  p(`${inv.ranking.units.length} enemy units are not done; the full list is \`ranking.units\` in inventory.json.`);
  p();
  p(`### Pickups without flat art (top ${Math.min(top, 20)})`);
  p();
  p("| # | Unit | Status | Levels | Episodes | Events | Ticks | Where |");
  p("|---|---|---|---|---|---|---|---|");
  inv.ranking.pickups.slice(0, Math.min(top, 20)).forEach((r, i) => p(`| ${i + 1} | ${r.id}${r.conditional ? " (conditional)" : ""}${r.twoPlayerOnly ? " (2P only)" : ""} | ${esc(r.status)} | ${r.levels} | ${r.episodes} | ${r.events} | ${r.ticks ?? "-"} | ${where(unitLevels.get(r.id))} |`));
  p();
  p(`${inv.ranking.pickups.length} pickup units have no flat art (\`ranking.pickups\`); ${inv.units.filter((u) => u.kind === "pickup" && u.status === "flat").length} do.`);
  p();
  p(`### Shots without flat art (top ${Math.min(top, 25)})`);
  p();
  p("Enemy shots are counted per level from each enemy type's turret weapons; player shots per episode from");
  p("every weapon and sidekick the episode's shops sell.");
  p();
  p("| # | Shot (sheet\\|size\\|frame) | Fired by | Levels (enemy) | Episodes | Ticks |");
  p("|---|---|---|---|---|---|");
  inv.ranking.shots.slice(0, Math.min(top, 25)).forEach((r, i) => p(`| ${i + 1} | ${esc(r.id)} | ${r.what} | ${r.levels} | ${r.episodes} | ${r.ticks ?? "-"} |`));
  p();
  p(`${inv.ranking.shots.length} shot frames have no flat art (\`ranking.shots\`); ${inv.shots.filter((s) => s.status === "flat").length} do.`);
  p();
  p("### Music and pictures");
  p();
  p(inv.ranking.songs.length ? `Songs without an arrangement: ${inv.ranking.songs.join(", ")}.` : "Every song a level or the script plays has an orchestral and a synth arrangement (public/tyrian-remaster/manifest.json, D40); nothing to do.");
  const pics = inv.episodes.flatMap((e) => e.cutscenes.flatMap((c) => c.commands.filter((x) => x.pic !== undefined && !x.redrawn).map((x) => x.pic)));
  p(pics.length ? `Story pictures without a redrawn version: ${[...new Set(pics)].join(", ")}.` : "Every story picture the scripts show is redrawn (public/art/pictures.json, D19). Episode 3's `]A[` plays tyrend.anm's original frames (src/app/episodeEnd.ts).");
  p();

  p("## Per-level rows");
  p();
  p("Units: enemy units total / flagship / older model / with unmodelled frames (pickups and empty");
  p("frames left out). Terrain: tiles with HD art or a structure model over tiles used, per layer.");
  p("Structures: structure models whose pattern occurs whole in the map. Bot: the bot run's result,");
  p("ticks, and units seen.");
  p();
  const unitById = new Map(inv.units.map((u) => [u.id, u]));
  for (const e of inv.episodes) {
    p(`### Episode ${e.episode}`);
    p();
    p("| Level | Name | Sections | Tileset | Terrain covered (0/1/2) | Structures | Enemy types | Units | Bosses | Songs | Special | Bot |");
    p("|---|---|---|---|---|---|---|---|---|---|---|---|");
    for (const id of e.levels) {
      const l = inv.levels.find((x) => x.id === id);
      const us = l.units.map((u) => unitById.get(u)).filter((u) => u && isEnemy(u));
      const fl = us.filter((u) => u.status === "flagship").length;
      const old = us.filter((u) => ["concept", "basic"].includes(u.status)).length;
      const secs = l.refs.map((r) => `${r.section}${r.difficulty !== "any" ? ` (${r.difficulty})` : ""}${r.bonus || r.normalBonus ? " bonus" : ""}`).join(", ");
      const terrain = l.layers.map((x) => `${x.covered}/${x.tiles}`).join(" ");
      const structures = Object.keys(l.tileModels).length;
      const special = [...l.smoothies, ...Object.keys(l.specialEvents).filter((k) => !["smoothie", "boss bar", "sound effect"].includes(k))].join(", ");
      const bot = l.play ? `${l.play.completed ? "done" : "unfinished"}, ${l.play.ticks} ticks, ${l.play.unitsSeen} seen` : "-";
      const bosses = l.bossUnits.length ? (l.bossUnits.length > 4 ? `${l.bossUnits.slice(0, 4).join(", ")} +${l.bossUnits.length - 4}` : l.bossUnits.join(", ")) : "-";
      p(`| ${id} | ${esc(l.name)} | ${secs} | ${esc(l.tileset)} | ${terrain} | ${structures} | ${l.enemyTypes} | ${us.length} / ${fl} / ${old} / ${us.length - fl - old} | ${bosses} | ${l.songs.join(", ")} | ${esc(special) || "-"} | ${bot} |`);
    }
    p();
    const cs = e.cutscenes.filter((c) => c.commands.some((x) => ["picture", "pan", "anim", "text", "episode end"].includes(x.cmd)));
    if (cs.length) {
      p(`Between levels (the episode ${e.episode} script): ` + cs.map((c) => `section ${c.section}: ${c.commands.map((x) => x.cmd + (x.pic !== undefined ? ` ${x.pic}` : x.song !== undefined ? ` ${x.song}` : "")).join(", ")}`).join("; ") + ".");
      p();
    }
  }

  p("## Not determined statically");
  p();
  p("- Whether a possible enemy shows depends on play: event 66 skips spawns below a difficulty, 61, 70");
  p("  and 75 branch on flags and on which enemies are alive, random spawns depend on");
  p("  `levelEnemyFrequency`, and an enemy that only animates when event 24 says so may never show its");
  p("  other frames. The static lists over-cover; each level's `play.unitsNotSeen` and the ticks show what");
  p("  one bot playthrough met.");
  p("- An enemy whose shape bank the level never loads is drawn from whatever sheet its enemy slot last");
  p("  had (the C's \"Ignoring sprite from unloaded shape table\"); statically it has `unloadedBank` and no");
  p(`  unit. The bot run adds what it actually drew to the level (\`play.unitsFoundByBot\`): ${inv.notes.foundByBot.length} level/frame finds, listed in \`notes.foundByBot\`.`);
  p("- Player shots depend on what the player buys, so they are per episode (everything its shops sell),");
  p("  not per level. Explosions (newsh6.shp, drawn as hot sprites on purpose, D35) are left out.");
  p("- Structure-model matches scan the whole map; a level may never scroll to some rows.");
  p("- Hard-only level variants are played at hard difficulty; other difficulties' event skips are not played.");
  p();
  return L.join("\n");
}

// --- Command line ---

async function loadModules() {
  const { createServer } = await import("vite");
  const server = await createServer({
    configFile: false,
    root: ROOT,
    logLevel: "error",
    server: { middlewareMode: true, hmr: false, ws: false, watch: null },
    appType: "custom",
    optimizeDeps: { noDiscovery: true, include: [] },
  });
  const m = {};
  for (const [k, path] of Object.entries(MODULES)) { const t = Date.now(); m[k] = await server.ssrLoadModule(`/${path}`); if (process.env.INV_TIMING) console.log(k, Date.now() - t); }
  return { m, close: () => server.close() };
}

function dataFiles(dir) {
  const cache = new Map();
  return {
    get(name) {
      if (!cache.has(name)) {
        const p = join(dir, name);
        cache.set(name, existsSync(p) ? new Uint8Array(readFileSync(p)) : undefined);
      }
      return cache.get(name);
    },
  };
}

async function main() {
  const args = process.argv.slice(2);
  const play = !args.includes("--no-play");
  const outIdx = args.indexOf("--out");
  const out = resolve(ROOT, outIdx >= 0 ? args[outIdx + 1] : "docs/roadmap");
  const epIdx = args.indexOf("--episodes");
  const episodes = epIdx >= 0 ? args[epIdx + 1].split(",").map(Number) : undefined;
  const dataDir = resolve(ROOT, process.env.TYRIAN_DATA ?? "data");
  const files = dataFiles(dataDir);
  if (!files.get("levels1.dat")) {
    console.error(`no Tyrian data in ${dataDir} (set TYRIAN_DATA)`);
    process.exit(1);
  }
  if (args.includes("--markdown-only")) {
    // Re-render inventory.md from inventory.json (after changing renderMarkdown, without replaying).
    const inv = readJson(join(out, "inventory.json"));
    writeFileSync(join(out, "inventory.md"), renderMarkdown(inv) + "\n");
    console.log(`wrote ${join(out, "inventory.md")}`);
    return;
  }
  const t0 = Date.now();
  const { m, close } = await loadModules();
  try {
    const inv = await buildInventory(m, files, { play, episodes, log: (s) => console.log(s) });
    mkdirSync(out, { recursive: true });
    writeFileSync(join(out, "inventory.json"), stringify(inv) + "\n");
    writeFileSync(join(out, "inventory.md"), renderMarkdown(inv) + "\n");
    console.log(`wrote ${join(out, "inventory.json")} and inventory.md: ${inv.levels.length} levels, ${inv.units.length} units in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  } finally {
    await close();
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
