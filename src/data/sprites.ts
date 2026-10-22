// Sprite formats, ported from OpenTyrian src/sprite.c.
//
// - Sprite2 sheets (Sprite2_array): u16 offset table (1-based sprite index), then per sprite a
//   nibble-RLE stream 12 pixels wide: low nibble = transparent pixels to skip, high nibble = opaque
//   pixels that follow (0 = next row), 0x0f ends the sprite (blit_sprite2).
// - Sprite tables (Sprite_array, load_sprites): u16 count, then per sprite a bool "populated" and
//   u16 width, height, size plus `size` bytes of byte-RLE: 255 n = skip n, 254 = next row,
//   253 = skip 1, anything else = a pixel (blit_sprite).
// - tyrian.shp (JE_loadMainShapeTables): u16 table count, u32 offsets; tables 0-6 are sprite tables,
//   7-11 are Sprite2 sheets (shots, player ships, power-ups, coins, enemy shots).

import { BinaryReader, toBytes, type Bytes } from "./reader";

/** Decoded sprite: palette indices, -1 where transparent. */
export interface DecodedSprite {
  width: number;
  height: number;
  pixels: Int16Array;
}

export const SPRITE2_WIDTH = 12;

/** Decode Sprite2 #index (1-based) from a sheet. Height is however many rows the data covers. */
export function decodeSprite2(sheet: Uint8Array, index: number): DecodedSprite {
  const offsetPos = (index - 1) * 2;
  if (index < 1 || offsetPos + 1 >= sheet.length) return { width: SPRITE2_WIDTH, height: 0, pixels: new Int16Array(0) };
  const rows: Int16Array[] = [];
  let row = new Int16Array(SPRITE2_WIDTH).fill(-1);
  let p = sheet[offsetPos] | (sheet[offsetPos + 1] << 8);
  let x = 0;
  for (; p < sheet.length && sheet[p] !== 0x0f; p++) {
    x += sheet[p] & 0x0f;
    let count = sheet[p] >> 4;
    if (count === 0) {
      rows.push(row);
      row = new Int16Array(SPRITE2_WIDTH).fill(-1);
      x = 0;
      continue;
    }
    while (count--) {
      p++;
      if (x < SPRITE2_WIDTH) row[x] = sheet[p];
      x++;
    }
  }
  if (row.some((c) => c >= 0)) rows.push(row);
  const pixels = new Int16Array(rows.length * SPRITE2_WIDTH);
  rows.forEach((r, y) => pixels.set(r, y * SPRITE2_WIDTH));
  return { width: SPRITE2_WIDTH, height: rows.length, pixels };
}

/** Number of sprites a Sprite2 sheet's offset table declares. */
export function sprite2Count(sheet: Uint8Array): number {
  return sheet.length >= 2 ? (sheet[0] | (sheet[1] << 8)) >> 1 : 0;
}

export interface TableSprite {
  width: number;
  height: number;
  /** Raw RLE data. */
  data: Uint8Array;
}

/** load_sprites: parse a sprite table starting at `offset`. */
export function parseSpriteTable(data: Bytes, offset = 0): { sprites: (TableSprite | null)[]; end: number } {
  const r = new BinaryReader(data, offset);
  const count = r.u16();
  const sprites: (TableSprite | null)[] = [];
  for (let i = 0; i < count; i++) {
    if (!r.bool()) {
      sprites.push(null);
      continue;
    }
    const width = r.u16();
    const height = r.u16();
    const size = r.u16();
    sprites.push({ width, height, data: r.bytesCopy(size) });
  }
  return { sprites, end: r.pos };
}

/** Decode a table sprite's RLE into pixels (blit_sprite). */
export function decodeTableSprite(sprite: TableSprite): DecodedSprite {
  const { width, height, data } = sprite;
  const pixels = new Int16Array(width * height).fill(-1);
  let x = 0;
  let y = 0;
  for (let i = 0; i < data.length; i++) {
    const b = data[i];
    if (b === 255) x += data[++i];
    else if (b === 254) x = width;
    else if (b === 253) x++;
    else {
      if (y < height && x < width) pixels[y * width + x] = b;
      x++;
    }
    if (x >= width) {
      x = 0;
      y++;
    }
  }
  return { width, height, pixels };
}

/** JE_loadMainShapeTables: split tyrian.shp into its tables (byte ranges). */
export function mainShapeTables(data: Bytes): Uint8Array[] {
  const bytes = toBytes(data);
  const r = new BinaryReader(bytes);
  const count = r.u16();
  const positions: number[] = [];
  for (let i = 0; i < count; i++) positions.push(r.u32());
  positions.push(bytes.length);
  return positions.slice(0, count).map((start, i) => bytes.subarray(start, positions[i + 1]));
}
