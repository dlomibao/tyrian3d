// The active palette as a 256x1 texture that every renderer shader looks colours up in.
//
// Meshes store palette indices, not colours (DECISIONS.md D7), so switching palettes, the enemy
// hit-flash filter and JE_filterScreen's whole-screen hue/brightness are all just index
// arithmetic plus this lookup. JE_filterScreen maps every pixel's index through a function of the
// index alone, so it is folded into the texture: entry i holds the colour of remapScreenIndex(i).

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

export class PaletteTexture {
  readonly texture: THREE.DataTexture;
  /** The smoothies' per-pass hue changes, for the materials that look colours up here (D31). */
  readonly screenHue = new ScreenHue();
  /** Goes up whenever the colours change, so things that copy colours out know to refresh. */
  version = 0;
  private readonly rgba = new Uint8Array(256 * 4);
  private palette: Palette | null = null;
  private filter = -99;
  private brightness = 0;

  constructor() {
    // Until a palette arrives: a grey ramp per 16-colour bank, so geometry is still visible.
    for (let i = 0; i < 256; i++) {
      const v = Math.round(((i & 15) / 15) * 255);
      this.rgba.set([v, v, v, 255], i * 4);
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
    this.palette = palette;
    this.filter = filter;
    this.brightness = brightness;
    for (let i = 0; i < 256; i++) {
      const j = remapScreenIndex(i, filter, brightness) * 3;
      this.rgba[i * 4] = vga6To8(palette[j]);
      this.rgba[i * 4 + 1] = vga6To8(palette[j + 1]);
      this.rgba[i * 4 + 2] = vga6To8(palette[j + 2]);
      this.rgba[i * 4 + 3] = 255;
    }
    this.texture.needsUpdate = true;
    this.version++;
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
