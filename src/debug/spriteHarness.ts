// Renderer test bench: real game data, synthetic draw lists, no simulation. Open the dev server
// with `?debug=sprites`. Loaded by dynamic import, so it's not in the main bundle.
//
//   ?debug=sprites                     a scrolling level with enemies, the player, shots, explosions
//   &level=N&episode=E                 level N (1-based lvlFileNum) of tyrianE.lvl (default 1, 1)
//   &count=N                           N extra moving enemies (stress test)
//   &palette=N                         force palette N
//   &sheet=newsh1.shp&size=2&page=P    a static grid of one sheet's sprites instead
//   &clip=0                            show everything drawn, not just the original's playfield
//   &freeze=T                          stop at tick T (the same frame every time, for comparisons)
//   &bg=original                       the original's tiles instead of the remastered backgrounds
//                                      (the default, DECISIONS.md D34/D48); in the console,
//                                      tyrianHarness.view.draws.setBackgroundStyle("remaster") switches back
//
// The background emulates draw_background_1/2/3 (src/backgrnd.c): rows of 12 tiles from the
// level's maps, scrolling down as the original's map pointers move up.

import { startLoop } from "../core/loop";
import { CLASSIC_TICK_MS } from "../core/timing";
import { parseLevelFile, parseShapes, levelTiles, MAP_SIZES, type Level } from "../data/levels";
import { sprite2Count } from "../data/sprites";
import { loadDevFiles } from "../assets/files";
import {
  beginDrawList,
  blit_sprite,
  blit_sprite2,
  blit_sprite2_filter,
  blit_sprite2x2,
  blit_sprite2x2_blend,
  drawList,
  drawPixel,
  drawState,
  drawTile,
  fill_rectangle_xy,
  Pass,
  type Sprite2Sheet,
} from "../sim/draw";
import { BG_KEY_LAYER } from "../sim/backgrnd";
import { buildResources, requireFile } from "../sim/resources";
import type { Resources } from "../sim/state";
import { composeSprite2x2 } from "../render/spriteMesh";
import { decodeSprite2 } from "../data/sprites";
import type { View } from "../render/view";

const PLAYFIELD_X = 24;
const PLAYFIELD_W = 264;
const PLAYFIELD_H = 184;

export async function runSpriteHarness(view: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const overlay = makeOverlay();
  const files = await loadDevFiles();
  if (!files) {
    overlay.textContent = "?debug=sprites needs the dev server with TYRIAN_DATA pointing at the Tyrian 2.1 data.";
    return;
  }
  const res = buildResources(files);
  view.setPalettes(res.palettes);

  const sheetName = params.get("sheet");
  const build = sheetName
    ? sheetGrid(res, files.get(sheetName) ? { id: sheetName, data: requireFile(files, sheetName) } : sheetByName(res, sheetName), params)
    : levelScene(res, files, params);
  const palette = params.has("palette") ? Number(params.get("palette")) : null;
  const freeze = params.has("freeze") ? Number(params.get("freeze")) : Infinity;

  let tick = 0;
  const frameTimes: number[] = [];
  let frames = 0;
  let lastReport = performance.now();
  view.renderer.info.autoReset = false;

  startLoop(CLASSIC_TICK_MS, {
    update: () => {
      if (tick >= freeze) {
        view.setDrawList(drawList); // the same list again, so nothing moves
        return;
      }
      beginDrawList();
      build(tick++);
      if (palette !== null) drawList.palette = palette;
      view.setDrawList(drawList);
    },
    render: (alpha) => {
      const t0 = performance.now();
      view.renderer.info.reset();
      view.render(null, alpha);
      frameTimes.push(performance.now() - t0);
      frames++;
      const now = performance.now();
      if (now - lastReport > 500) {
        const s = view.draws.stats();
        const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
        const max = Math.max(...frameTimes);
        const info = view.renderer.info.render;
        overlay.textContent =
          `${((frames * 1000) / (now - lastReport)).toFixed(0)} fps · cpu ${avg.toFixed(2)} ms (max ${max.toFixed(1)}) · ` +
          `${s.items} draws → ${s.instances} instances · ${s.visiblePools}/${s.pools} pools · ` +
          `${info.calls} calls · ${(info.triangles / 1000).toFixed(0)}k tris · ${s.meshes} meshes · ${s.atlasTiles} atlas tiles`;
        frameTimes.length = 0;
        frames = 0;
        lastReport = now;
      }
    },
  });
  Object.assign(window, { tyrianHarness: { view, res } });
}

function sheetByName(res: Resources, name: string): Sprite2Sheet {
  const sheets = [res.spriteSheet8, res.spriteSheet9, res.spriteSheet10, res.spriteSheet11, res.spriteSheet12];
  return sheets.find((s) => s.id === name) ?? res.spriteSheet9;
}

/** A static grid of one sheet's sprites, 2x2 blocks (size=2) or single tiles. */
function sheetGrid(res: Resources, sheet: Sprite2Sheet, params: URLSearchParams): (tick: number) => void {
  const size = params.get("size") === "1" ? 1 : 2;
  const page = Number(params.get("page") ?? 0);
  const count = sprite2Count(sheet.data);
  const cellW = size * 12 + 2;
  const cellH = size * 14 + 2;
  const cols = Math.floor(PLAYFIELD_W / cellW);
  const rows = Math.floor(PLAYFIELD_H / cellH);
  // Sheets are laid out 19 tiles wide; a 2x2 block at (bx, by) starts at 1 + by*38 + bx*2.
  const indices: number[] = [];
  if (size === 2) {
    for (let by = 0; 1 + by * 38 <= count; by++) for (let bx = 0; bx < 9; bx++) indices.push(1 + by * 38 + bx * 2);
  } else {
    for (let i = 1; i <= count; i++) indices.push(i);
  }
  const shown = indices.slice(page * cols * rows, (page + 1) * cols * rows);
  console.info(`sheet ${sheet.id}: ${count} sprites; page ${page} shows ${shown[0]}..${shown[shown.length - 1]}`);
  void res;
  return () => {
    drawState.pass = Pass.SkyEnemies;
    shown.forEach((index, n) => {
      const x = PLAYFIELD_X + 2 + (n % cols) * cellW;
      const y = 2 + Math.floor(n / cols) * cellH;
      drawState.key = n;
      if (size === 2) blit_sprite2x2(x, y, sheet, index);
      else blit_sprite2(x, y, sheet, index);
    });
  };
}

interface Mover {
  sheet: Sprite2Sheet;
  index: number;
  size: 1 | 2;
  x: number;
  y: number;
  vx: number;
  vy: number;
  pass: Pass;
  hitTimer: number;
}

/** A level's backgrounds scrolling under enemies, the player ship, shots, explosions and sparks. */
function levelScene(res: Resources, files: { get(name: string): Uint8Array | undefined }, params: URLSearchParams): (tick: number) => void {
  const episode = Number(params.get("episode") ?? 1);
  const levelNum = Number(params.get("level") ?? 1);
  const lvl = parseLevelFile(requireFile(files, `tyrian${episode}.lvl`));
  const level: Level = lvl.levels[levelNum - 1] ?? lvl.levels[0];
  const shapes = parseShapes(requireFile(files, `shapes${level.shapeFile.toLowerCase()}.dat`));
  const layerTiles = ([0, 1, 2] as const).map((layer) => levelTiles(level, shapes, layer));
  const shapesFile = `shapes${level.shapeFile.toLowerCase()}.dat`;
  console.info(`level ${levelNum} of tyrian${episode}.lvl, ${shapesFile}`);

  // Background state, as JE_loadMap sets it: maps scroll from the bottom (row height - 8) upward.
  // `&row=N` starts N rows from the top of background 1's map instead (the others in proportion).
  const startRow = params.has("row") ? Number(params.get("row")) : null;
  const bg = MAP_SIZES.map(({ height }, layer) => ({
    mapY: startRow === null ? height - 8 : Math.round((startRow * height) / MAP_SIZES[0].height),
    backPos: 0,
    speed: [1, 2, 3][layer],
  }));

  // Enemies: non-empty 2x2 blocks from the level's first enemy sheet.
  const enemySheet = res.loadCompShapes("1");
  const blocks: number[] = [];
  for (let by = 0; by < 6; by++) {
    for (let bx = 0; bx < 9; bx++) {
      const index = 1 + by * 38 + bx * 2;
      if (composeSprite2x2(enemySheet.data, index).pixels.some((p) => p >= 0)) blocks.push(index);
    }
  }
  const nonEmpty = (sheet: Sprite2Sheet, from: number, n: number) => {
    const out: number[] = [];
    for (let i = from; out.length < n && i <= sprite2Count(sheet.data); i++) if (decodeSprite2(sheet.data, i).pixels.some((p) => p >= 0)) out.push(i);
    return out;
  };
  const shotIndices = nonEmpty(res.spriteSheet8, 1, 6);
  const explosionIndices = nonEmpty(res.explosionSpriteSheet, 1, 12);

  let seed = 12345;
  const rand = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
  const extra = Number(params.get("count") ?? 0);
  const movers: Mover[] = [];
  const spawn = (pass: Pass): Mover => ({
    sheet: enemySheet,
    index: blocks[Math.floor(rand() * blocks.length)] ?? 1,
    size: 2,
    x: PLAYFIELD_X + rand() * (PLAYFIELD_W - 24),
    y: -30 - rand() * 180,
    vx: (rand() - 0.5) * 2,
    vy: 1 + rand() * 2,
    pass,
    hitTimer: 0,
  });
  for (let i = 0; i < 10 + extra; i++) movers.push(spawn([Pass.GroundEnemies, Pass.SkyEnemies, Pass.TopEnemies][i % 3]));

  const shots: { x: number; y: number; index: number }[] = [];
  const explosions: { x: number; y: number; frame: number }[] = [];
  const sparks: { x: number; y: number; vx: number; vy: number; color: number; life: number }[] = [];
  let px = 150;
  let lastPx = px;

  return (tick) => {
    // Backgrounds (draw_background_1/2/3): 8 rows of 12 tiles, x from the parallax offset.
    const passes = [Pass.Background1, Pass.Background2Under, Pass.Background3];
    for (let layer = 0 as 0 | 1 | 2; layer < 3; layer = (layer + 1) as 0 | 1 | 2) {
      const b = bg[layer];
      b.backPos += b.speed;
      while (b.backPos > 27) {
        b.backPos -= 28;
        b.mapY--;
        if (b.mapY < 1) b.mapY = MAP_SIZES[layer].height - 8;
      }
      drawState.pass = passes[layer];
      const width = MAP_SIZES[layer].width;
      const ofs = [12, 24, 36][layer] + Math.round(((px - 150) / 110) * [-12, -24, -36][layer]);
      const firstCol = 2 - Math.floor(ofs / 24);
      for (let i = -1; i < 7; i++) {
        const row = b.mapY + i;
        if (row < 0 || row >= MAP_SIZES[layer].height) continue;
        for (let c = 0; c < 12; c++) {
          const col = firstCol + c;
          if (col < 0 || col >= width) continue;
          const tile = layerTiles[layer][level.maps[layer][row * width + col]];
          if (!tile) continue;
          const shape = level.mapSh[layer][level.maps[layer][row * width + col]];
          // Tile id and key as the sim's blitBackgroundRow makes them (backgrnd.ts).
          drawTile(layer, tile, `${shapesFile}:${shape - 1}`, ofs + (col - 2) * 24, i * 28 + b.backPos, BG_KEY_LAYER * layer + row * width + col);
        }
      }
    }

    // Enemies drift down; every so often one flashes (blit_sprite2_filter) as if hit.
    movers.forEach((m, n) => {
      m.x += m.vx;
      m.y += m.vy;
      if (m.x < PLAYFIELD_X - 10 || m.x > PLAYFIELD_X + PLAYFIELD_W - 14) m.vx = -m.vx;
      if (m.y > PLAYFIELD_H + 10) Object.assign(m, spawn(m.pass), { pass: m.pass });
      if (m.hitTimer > 0) m.hitTimer--;
      else if (rand() < 0.01) m.hitTimer = 4;
      drawState.pass = m.pass;
      drawState.key = 1000 + n;
      const x = Math.round(m.x);
      const y = Math.round(m.y);
      if (m.hitTimer > 0) {
        for (const [dx, dy, di] of [[0, 0, 0], [12, 0, 1], [0, 14, 19], [12, 14, 20]]) blit_sprite2_filter(x + dx, y + dy, m.sheet, m.index + di, 0xf0);
      } else blit_sprite2x2(x, y, m.sheet, m.index);
    });

    // The player: sweeping left and right, banking with its velocity (JE_playerMovement).
    lastPx = px;
    px = 150 + Math.sin(tick / 40) * 100;
    const py = 150 + Math.sin(tick / 23) * 15;
    const bank = Math.max(-2, Math.min(2, Math.round((px - lastPx) / 1.2)));
    drawState.pass = Pass.Player;
    drawState.key = 1;
    const invulnerable = Math.floor(tick / 100) % 4 === 3;
    (invulnerable ? blit_sprite2x2_blend : blit_sprite2x2)(Math.round(px) - 5, Math.round(py) - 7, res.spriteSheet9, 233 + bank * 2);

    // Shots fly up from the ship.
    if (tick % 4 === 0) shots.push({ x: Math.round(px) + 1, y: Math.round(py) - 14, index: shotIndices[(tick / 4) % shotIndices.length] ?? 1 });
    drawState.pass = Pass.PlayerShots;
    for (let s = shots.length - 1; s >= 0; s--) {
      shots[s].y -= 8;
      if (shots[s].y < -14) shots.splice(s, 1);
    }
    shots.forEach((s, n) => {
      drawState.key = 5000 + ((tick - n) % 1000);
      blit_sprite2(s.x, s.y, res.spriteSheet8, s.index);
    });

    // Explosions and their sparks (JE_drawSP superpixels).
    if (tick % 20 === 0) {
      const ex = PLAYFIELD_X + 20 + rand() * (PLAYFIELD_W - 60);
      const ey = 20 + rand() * 100;
      explosions.push({ x: ex, y: ey, frame: 0 });
      for (let k = 0; k < 12; k++) {
        const a = rand() * Math.PI * 2;
        sparks.push({ x: ex + 6, y: ey + 7, vx: Math.cos(a) * 2, vy: Math.sin(a) * 2, color: 0x70 + Math.floor(rand() * 15), life: 20 });
      }
    }
    drawState.pass = Pass.Explosions;
    for (let e = explosions.length - 1; e >= 0; e--) if (++explosions[e].frame >= explosionIndices.length) explosions.splice(e, 1);
    explosions.forEach((e) => {
      drawState.key = -1;
      blit_sprite2(Math.round(e.x), Math.round(e.y), res.explosionSpriteSheet, explosionIndices[e.frame] ?? 1);
    });
    drawState.pass = Pass.Effects;
    for (let s = sparks.length - 1; s >= 0; s--) {
      const p = sparks[s];
      p.x += p.vx;
      p.y += p.vy;
      if (--p.life <= 0) sparks.splice(s, 1);
      else drawPixel(Math.round(p.x), Math.round(p.y), p.color - (20 - p.life) / 2);
    }

    // A warning bar and an option (sidekick) shape from a sprite table.
    if (Math.floor(tick / 35) % 2 === 0) fill_rectangle_xy(PLAYFIELD_X + 4, 4, PLAYFIELD_X + 60, 6, 0x4c);
    drawState.pass = Pass.Player;
    drawState.key = 2;
    blit_sprite(Math.round(px) - 24, Math.round(py), res.spriteTables[5], 1);
  };
}

function makeOverlay(): HTMLDivElement {
  const div = document.createElement("div");
  Object.assign(div.style, {
    position: "fixed",
    left: "8px",
    top: "8px",
    font: "12px/1.4 ui-monospace, monospace",
    color: "#cfe3ff",
    background: "rgba(0,0,0,0.55)",
    padding: "4px 8px",
    borderRadius: "4px",
    pointerEvents: "none",
    maxWidth: "calc(100vw - 32px)",
  });
  div.textContent = "loading Tyrian data…";
  document.body.appendChild(div);
  return div;
}
