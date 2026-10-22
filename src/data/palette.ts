// palette.dat: 23 VGA palettes of 256 RGB triplets. Port of loadPals (OpenTyrian src/palette.c).

import { toBytes, type Bytes } from "./reader";

/** Palettes in palette.dat (COUNTOF(palettes) in palette.c). */
export const PALETTE_COUNT = 23;
const PALETTE_BYTES = 256 * 3;

/** One palette: 256 × [r, g, b], raw 6-bit VGA DAC values (0..63). */
export type Palette = Uint8Array;

/**
 * Parse palette.dat. The count comes from the file length (fileGetLength / 768), as in
 * loadPals; trailing bytes short of a whole palette are ignored. Values stay 6-bit.
 */
export function parsePalettes(data: Bytes): Palette[] {
  const bytes = toBytes(data);
  const count = Math.floor(bytes.length / PALETTE_BYTES);
  const palettes: Palette[] = [];
  for (let p = 0; p < count; p++) {
    palettes.push(bytes.slice(p * PALETTE_BYTES, (p + 1) * PALETTE_BYTES));
  }
  return palettes;
}

/** loadPals' 6→8-bit rescale: (c << 2) | (c >> 4), so 63 maps to 255. */
export function vga6To8(c: number): number {
  return ((c << 2) | (c >> 4)) & 0xff;
}

/** A palette as 256 × RGBA8 (alpha 255), ready for a texture lookup table. */
export function paletteToRgba8(palette: Palette): Uint8Array {
  const out = new Uint8Array(256 * 4);
  for (let i = 0; i < 256; i++) {
    out[i * 4] = vga6To8(palette[i * 3]);
    out[i * 4 + 1] = vga6To8(palette[i * 3 + 1]);
    out[i * 4 + 2] = vga6To8(palette[i * 3 + 2]);
    out[i * 4 + 3] = 255;
  }
  return out;
}
