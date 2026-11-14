// The active palette as a 256x1 texture that every renderer shader looks colours up in.
//
// Meshes store palette indices, not colours (DECISIONS.md D7), so switching palettes, the enemy
// hit-flash filter and JE_filterScreen's whole-screen hue/brightness are all just index
// arithmetic plus this lookup. JE_filterScreen maps every pixel's index through a function of the
// index alone, so it is folded into the texture: entry i holds the colour of remapScreenIndex(i).
//
// Painted art (HD terrain, D57) has colours, not indices; `indexLut` gives a colour the index of
// the raw palette's nearest entry, so index rules such as water_filter's exception for the
// (index & 0x30) == 0 banks can reach it (D111).

import * as THREE from "three";
import { vga6To8, type Palette } from "../data/palette";
import { ScreenHue } from "./screenHue";

/** JE_filterScreen's per-pixel effect (filterScreenHue then filterScreenValue, src/backgrnd.c). */
export function remapScreenIndex(index: number, filter: number, brightness: number): number {
  let i = index;
  if (filter !== -99) i = ((filter & 0x0f) << 4) | (i & 0x0f);
  if (brightness !== -99 && brightness !== 0) {
    // Value is the sum if it's 0x0..0xF, 0xF if it's 0x10..0x1E, and 0x0 otherwise.
    const v = (i & 0x0f) + brightness;
    i = (i & 0xf0) | (v >= 0 && v <= 0x0f ? v : v >= 0x10 && v <= 0x1e ? 0x0f : 0);
  }
  return i;
}

/** Cells per channel of the nearest-index lookup's sRGB cube. */
export const PALETTE_LUT_SIZE = 32;
/** The cube laid out as a 2D texture: blue slices side by side, 8 to a row (256 x 128). */
export const PALETTE_LUT_WIDTH = PALETTE_LUT_SIZE * 8;
export const PALETTE_LUT_HEIGHT = PALETTE_LUT_SIZE * (PALETTE_LUT_SIZE / 8);

/** The cube cell (0..31) of an sRGB channel value in 0..1, as the shaders compute it. */
export function paletteLutCell(srgb: number): number {
  return Math.min(PALETTE_LUT_SIZE - 1, Math.max(0, Math.floor(srgb * PALETTE_LUT_SIZE)));
}

/** The texel offset of cube cell (r, g, b) in the lookup's data. */
export function paletteLutOffset(r: number, g: number, b: number): number {
  return (g + PALETTE_LUT_SIZE * (b >> 3)) * PALETTE_LUT_WIDTH + r + PALETTE_LUT_SIZE * (b & 7);
}

const lutCache = new WeakMap<Palette, Uint8Array>();

/**
 * For each cell of the sRGB cube, the index of the palette entry nearest the cell's centre (the
 * "redmean" weighted RGB distance; the lowest index on a tie). Cached per palette.
 */
export function nearestIndexLut(palette: Palette): Uint8Array {
  const cached = lutCache.get(palette);
  if (cached) return cached;
  const n = PALETTE_LUT_SIZE;
  const pal = new Float32Array(256 * 3);
  for (let i = 0; i < 768; i++) pal[i] = vga6To8(palette[i] ?? 0);
  const lut = new Uint8Array(PALETTE_LUT_WIDTH * PALETTE_LUT_HEIGHT);
  for (let b = 0; b < n; b++) {
    const cb = ((b + 0.5) / n) * 255;
    for (let g = 0; g < n; g++) {
      const cg = ((g + 0.5) / n) * 255;
      for (let r = 0; r < n; r++) {
        const cr = ((r + 0.5) / n) * 255;
        let best = 0;
        let bestD = Infinity;
        for (let i = 0; i < 256; i++) {
          const pr = pal[i * 3], dr = cr - pr, dg = cg - pal[i * 3 + 1], db = cb - pal[i * 3 + 2];
          const mean = (cr + pr) * 0.5;
          const d = (2 + mean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - mean) / 256) * db * db;
          if (d < bestD) {
            bestD = d;
            best = i;
          }
        }
        lut[paletteLutOffset(r, g, b)] = best;
      }
    }
  }
  lutCache.set(palette, lut);
  return lut;
}

export class PaletteTexture {
  readonly texture: THREE.DataTexture;
  /** The smoothies' per-pass hue changes, for the materials that look colours up here (D31). */
  readonly screenHue = new ScreenHue();
  /** Goes up whenever the colours change, so things that copy colours out know to refresh. */
  version = 0;
  private readonly rgba = new Uint8Array(256 * 4);
  /**
   * The raw palette (sRGB RGBA bytes), before JE_filterScreen: the colours the indices were drawn
   * with, which the HD paintings' shades are read against (underShade.ts, D204).
   */
  readonly raw = new Uint8Array(256 * 4);
  private palette: Palette | null = null;
  private filter = -99;
  private brightness = 0;
  private lut: THREE.DataTexture | null = null;

  constructor() {
    // Until a palette arrives: a grey ramp per 16-colour bank, so geometry is still visible.
    for (let i = 0; i < 256; i++) {
      const v = Math.round(((i & 15) / 15) * 255);
      this.rgba.set([v, v, v, 255], i * 4);
      this.raw.set([v, v, v, 255], i * 4);
    }
    this.texture = new THREE.DataTexture(this.rgba, 256, 1, THREE.RGBAFormat, THREE.UnsignedByteType);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.magFilter = this.texture.minFilter = THREE.NearestFilter;
    this.texture.generateMipmaps = false;
    this.texture.needsUpdate = true;
  }

  /** Set the palette and screen filter. Cheap when nothing changed (called every tick). */
  set(palette: Palette, filter: number, brightness: number): void {
    if (palette === this.palette && filter === this.filter && brightness === this.brightness) return;
    if (palette !== this.palette && this.lut) this.fillLut(palette);
    this.palette = palette;
    this.filter = filter;
    this.brightness = brightness;
    for (let i = 0; i < 256; i++) {
      const j = remapScreenIndex(i, filter, brightness) * 3;
      this.rgba[i * 4] = vga6To8(palette[j]);
      this.rgba[i * 4 + 1] = vga6To8(palette[j + 1]);
      this.rgba[i * 4 + 2] = vga6To8(palette[j + 2]);
      this.rgba[i * 4 + 3] = 255;
      this.raw[i * 4] = vga6To8(palette[i * 3]);
      this.raw[i * 4 + 1] = vga6To8(palette[i * 3 + 1]);
      this.raw[i * 4 + 2] = vga6To8(palette[i * 3 + 2]);
      this.raw[i * 4 + 3] = 255;
    }
    this.texture.needsUpdate = true;
    this.version++;
  }

  /**
   * The raw palette's nearest index for an sRGB colour (nearestIndexLut, unfiltered: the screen
   * filter applies after), as a 256x128 R8 texture for texelFetch. Built on first use, then kept
   * up to date with the palette. Until a palette arrives every cell holds 16 (the hue ramp).
   */
  get indexLut(): THREE.DataTexture {
    if (!this.lut) {
      const data = new Uint8Array(PALETTE_LUT_WIDTH * PALETTE_LUT_HEIGHT).fill(16);
      this.lut = new THREE.DataTexture(data, PALETTE_LUT_WIDTH, PALETTE_LUT_HEIGHT, THREE.RedFormat, THREE.UnsignedByteType);
      this.lut.magFilter = this.lut.minFilter = THREE.NearestFilter;
      this.lut.generateMipmaps = false;
      this.lut.needsUpdate = true;
      if (this.palette) this.fillLut(this.palette);
    }
    return this.lut;
  }

  private fillLut(palette: Palette): void {
    (this.lut!.image.data as Uint8Array).set(nearestIndexLut(palette));
    this.lut!.needsUpdate = true;
  }

  /** JE_filterScreen's hue (-99: off) and brightness, as folded into the texture. */
  get screenFilter(): number {
    return this.filter;
  }

  get screenBrightness(): number {
    return this.brightness;
  }

  /** sRGB colour of an index in the current palette, for things drawn outside the shaders. */
  color(index: number, target = new THREE.Color()): THREE.Color {
    const o = (index & 0xff) * 4;
    return target.setRGB(this.rgba[o] / 255, this.rgba[o + 1] / 255, this.rgba[o + 2] / 255, THREE.SRGBColorSpace);
  }
}
