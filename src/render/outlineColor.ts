import * as THREE from "three";

/**
 * An outline colour for OutlineEffect's `defaultColor`, from 0-255 sRGB bytes. OutlineEffect reads
 * the array as working-space (linear) values, so the bytes are converted; passing 16/255 straight
 * through renders as a lifted olive-brown instead of the sprites' near-black ink.
 */
export function outlineColor(r: number, g: number, b: number): number[] {
  return new THREE.Color().setRGB(r / 255, g / 255, b / 255, THREE.SRGBColorSpace).toArray();
}

/** The game-wide ink outline: palette entry 16, (16, 8, 0). */
export const INK_OUTLINE = outlineColor(16, 8, 0);
