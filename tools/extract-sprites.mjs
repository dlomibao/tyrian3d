// Render Tyrian's sprite sheets to PNG, as visual reference for the 3D models.
//
//   node tools/extract-sprites.mjs [dataDir] [outDir] [palette]
//
// Writes each sprite sheet, a transparent top view of each ship (`ship-<name>-top.png`, used as a
// reference image by the Blender scripts), and close-ups of every player ship's five banking frames
// (sprite shipGraphic + bank * 2, bank -2..2, each a 2x2 block of tiles: blit_sprite2x2).
//
// Output goes to reference/sprites/ by default, which is git-ignored: it's derived from the game
// data, whose licence is unresolved (#10). Formats ported from OpenTyrian src/sprite.c and
// src/palette.c.

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { crc32, deflateSync } from "node:zlib";

const [dataDir = "data", outDir = "reference/sprites", paletteArg = "0"] = process.argv.slice(2);
const SCALE = 4;
// Sprite2 tiles are 12 px wide; sheets are laid out 19 tiles per row (blit_sprite2x2 uses index+19).
const TILE_W = 12, TILE_H = 14, SHEET_COLS = 19;

/** palette.dat: 23 palettes of 256 6-bit RGB triples (loadPals). */
function loadPalette(index) {
  const buf = readFileSync(join(dataDir, "palette.dat"));
  const base = index * 768;
  const rgb = [];
  for (let i = 0; i < 256; i++) {
    const c = (v) => (v << 2) | (v >> 4);
    rgb.push([c(buf[base + i * 3]), c(buf[base + i * 3 + 1]), c(buf[base + i * 3 + 2])]);
  }
  return rgb;
}

/** tyrian.shp: u16 table count, u32 offsets; tables 7-11 are Sprite2 sheets (JE_loadMainShapeTables). */
function loadMainShapeTables(file) {
  const buf = readFileSync(join(dataDir, file));
  const count = buf.readUInt16LE(0);
  const pos = [];
  for (let i = 0; i < count; i++) pos.push(buf.readUInt32LE(2 + i * 4));
  pos.push(buf.length);
  return (i) => buf.subarray(pos[i], pos[i + 1]);
}

/** Decode Sprite2 #index (1-based) into a 12-wide grid of palette indices, -1 = transparent (blit_sprite2). */
function decodeSprite2(sheet, index) {
  const pixels = new Int16Array(TILE_W * 32).fill(-1);
  let p = sheet.readUInt16LE((index - 1) * 2);
  let x = 0, y = 0;
  for (; p < sheet.length && sheet[p] !== 0x0f; p++) {
    x += sheet[p] & 0x0f;
    let count = sheet[p] >> 4;
    if (count === 0) {
      y++;
      x = 0;
      continue;
    }
    while (count--) {
      p++;
      if (y < 32 && x < TILE_W) pixels[y * TILE_W + x] = sheet[p];
      x++;
    }
  }
  return pixels;
}

function writePng(path, width, height, rgba) {
  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) rgba.copy(raw, y * (width * 4 + 1) + 1, y * width * 4, (y + 1) * width * 4);
  const chunk = (type, data) => {
    const len = Buffer.alloc(4);
    len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type), data]);
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 6, 0, 0, 0], 8);
  writeFileSync(path, Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr),
    chunk("IDAT", deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]));
}

function checker(w, h) {
  const img = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const shade = ((x >> 3) + (y >> 3)) & 1 ? 40 : 28;
      img.set([shade, shade, shade + 6, 255], (y * w + x) * 4);
    }
  return img;
}

function drawSprite(img, w, sheet, index, palette, ox, oy, scale) {
  const px = decodeSprite2(sheet, index);
  for (let y = 0; y < TILE_H; y++)
    for (let x = 0; x < TILE_W; x++) {
      const c = px[y * TILE_W + x];
      if (c < 0) continue;
      const [r, g, b] = palette[c];
      for (let dy = 0; dy < scale; dy++)
        for (let dx = 0; dx < scale; dx++)
          img.set([r, g, b, 255], (((oy + y) * scale + dy) * w + (ox + x) * scale + dx) * 4);
    }
}

/** The five banking frames of a 24x28 player ship, side by side. */
function renderShip(sheet, shipGraphic, palette, outPath, scale = 10) {
  const frameW = TILE_W * 2 + 4;
  const w = frameW * 5 * scale, h = (TILE_H * 2 + 4) * scale;
  const img = checker(w, h);
  for (let bank = -2; bank <= 2; bank++) {
    const s = shipGraphic + bank * 2;
    const ox = (bank + 2) * frameW + 2, oy = 2;
    drawSprite(img, w, sheet, s, palette, ox, oy, scale);
    drawSprite(img, w, sheet, s + 1, palette, ox + TILE_W, oy, scale);
    drawSprite(img, w, sheet, s + SHEET_COLS, palette, ox, oy + TILE_H, scale);
    drawSprite(img, w, sheet, s + SHEET_COLS + 1, palette, ox + TILE_W, oy + TILE_H, scale);
  }
  writePng(outPath, w, h, img);
}

/** The level (unbanked) frame alone on a transparent background, 1 px = `scale` px: a modeling reference. */
function renderShipTop(sheet, shipGraphic, palette, outPath, scale = 10) {
  const w = TILE_W * 2 * scale, h = TILE_H * 2 * scale;
  const img = Buffer.alloc(w * h * 4);
  drawSprite(img, w, sheet, shipGraphic, palette, 0, 0, scale);
  drawSprite(img, w, sheet, shipGraphic + 1, palette, TILE_W, 0, scale);
  drawSprite(img, w, sheet, shipGraphic + SHEET_COLS, palette, 0, TILE_H, scale);
  drawSprite(img, w, sheet, shipGraphic + SHEET_COLS + 1, palette, TILE_W, TILE_H, scale);
  writePng(outPath, w, h, img);
}

/** Render a whole Sprite2 sheet in its 19-column layout, upscaled, on a dark checker. */
function renderSheet(sheet, palette, outPath) {
  const spriteCount = sheet.readUInt16LE(0) / 2;
  const rows = Math.ceil(spriteCount / SHEET_COLS);
  const w = SHEET_COLS * TILE_W * SCALE, h = rows * TILE_H * SCALE;
  const img = checker(w, h);
  for (let s = 1; s <= spriteCount; s++)
    drawSprite(img, w, sheet, s, palette, ((s - 1) % SHEET_COLS) * TILE_W, Math.floor((s - 1) / SHEET_COLS) * TILE_H, SCALE);
  writePng(outPath, w, h, img);
  return spriteCount;
}

mkdirSync(outDir, { recursive: true });
const palette = loadPalette(Number(paletteArg));
const table = loadMainShapeTables("tyrian.shp");
const sheets = { "shots": 7, "player-ships": 8, "powerups": 9, "coins-datacubes": 10 };
for (const [name, i] of Object.entries(sheets)) {
  const out = join(outDir, `${name}.png`);
  console.log(`${out}: ${renderSheet(table(i), palette, out)} sprites`);
}

// Player ship sprite indices (ships[].shipgraphic in tyrian.hdt, episode 1).
const SHIPS = { "usp-talon": 233, "supercarrot": 119, "gencore-phoenix": 157, "microcorp-stalker": 195,
  "u-ship": 271, "silver-ship": 81 };
for (const [name, gr] of Object.entries(SHIPS)) {
  const out = join(outDir, `ship-${name}.png`);
  renderShip(table(8), gr, palette, out);
  renderShipTop(table(8), gr, palette, join(outDir, `ship-${name}-top.png`));
  console.log(out);
}
