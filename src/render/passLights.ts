// The scene's lights in the renders that draw only a camera layer of their own (DECISIONS.md D206).
//
// The under-shade pass (underShade.ts) and the screen filters' effects and mask draws
// (screenFilters.ts) render the scene with the camera on a spare layer, so only their own objects
// are drawn. The lights stayed on layer 0 and dropped out of those renders. three.js keys every
// lit material's program to the lights a render sees (WebGLLights' hash and version): a render
// without them, then the main render with them, changed the lights' state twice a frame, and the
// main render rebuilt every lit material's program parameters on each draw (getProgram), about a
// third of a frame's CPU time on GYGES's boss. The lights now join those renders too: they light
// nothing there (the passes' materials are unlit), and the lights' state stays the same all frame.

import type * as THREE from "three";

/**
 * Enable `layer` on every light in `lights` that `cameraLayers` sees; returns the masks to put back
 * with restoreLights.
 */
export function addLightsToLayer(lights: readonly THREE.Object3D[], cameraLayers: THREE.Layers, layer: number): number[] {
  const masks = lights.map((l) => l.layers.mask);
  for (const l of lights) if (l.layers.test(cameraLayers)) l.layers.enable(layer);
  return masks;
}

/** Put back the layer masks addLightsToLayer saved. */
export function restoreLights(lights: readonly THREE.Object3D[], masks: readonly number[]): void {
  lights.forEach((l, i) => (l.layers.mask = masks[i]));
}

/** Whether `o` is a light. */
export function isLight(o: THREE.Object3D): boolean {
  return (o as THREE.Light).isLight === true;
}
