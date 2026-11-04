// Types for outlineEffect.js: three.js's OutlineEffect with the damage cut (D87) and compileAsync (D91).
import type { Camera, Object3D, Scene } from "three";
import { OutlineEffect as ThreeOutlineEffect } from "three/addons/effects/OutlineEffect.js";
export type { OutlineEffectParameters } from "three/addons/effects/OutlineEffect.js";
export declare class OutlineEffect extends ThreeOutlineEffect {
  /** Compile the outline materials `scene` would draw with, without drawing (D91). */
  compileAsync(scene: Object3D, camera: Camera, targetScene?: Scene | null): Promise<unknown>;
}
