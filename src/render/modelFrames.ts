// Sprite animation on models (DECISIONS.md D17). A model can cover several animation frames of its
// sprite and still animate: the Blender scripts tag parts and materials with glTF extras.
//
// - A node with extras `tyrian_frames: [89, 91]` is shown only while the sprite frame (the sprite
//   index of the frame's top-left tile) is one of those. Untagged nodes are always shown.
// - A material named pal_<index> with extras `tyrian_frame_pal: { "91": 122 }` takes palette colour
//   122 instead of <index> on frame 91 (a light that blinks, a glow that pulses).
//
// GLTFLoader puts extras in userData; Object3D.clone and Material.clone copy it.

import type * as THREE from "three";

export const PALETTE_MATERIAL = /^pal_(\d+)/;

/** A pal_<index> material: its colour follows the live palette. */
export interface PaletteMaterial {
  material: THREE.MeshStandardMaterial;
  index: number;
  /** Whether it glows, so its emissive colour follows too. */
  emissive: boolean;
  /** Palette index per sprite frame, where it differs from `index`. */
  byFrame?: Map<number, number>;
}

/** What a model needs to follow its sprite's frames and the palette. */
export interface FrameRig {
  /** Nodes shown only on some frames. */
  nodes: { object: THREE.Object3D; frames: Set<number> }[];
  palette: PaletteMaterial[];
  /** Whether anything depends on the frame. */
  animated: boolean;
}

/** Collect a model's frame-tagged nodes and palette materials (each material once). */
export function rigModel(root: THREE.Object3D): FrameRig {
  const nodes: FrameRig["nodes"] = [];
  const palette: PaletteMaterial[] = [];
  const seen = new Set<THREE.Material>();
  root.traverse((o) => {
    const frames = o.userData?.tyrian_frames;
    if (Array.isArray(frames)) nodes.push({ object: o, frames: new Set(frames.map(Number)) });
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      if (seen.has(m)) continue;
      seen.add(m);
      const match = PALETTE_MATERIAL.exec(m.name);
      const std = m as THREE.MeshStandardMaterial;
      if (!match || !std.isMeshStandardMaterial) continue;
      const pm: PaletteMaterial = { material: std, index: Number(match[1]) & 0xff, emissive: std.emissive.getHex() !== 0 };
      const byFrame = std.userData?.tyrian_frame_pal;
      if (byFrame && typeof byFrame === "object") {
        pm.byFrame = new Map(Object.entries(byFrame).map(([f, i]) => [Number(f), Number(i) & 0xff]));
      }
      palette.push(pm);
    }
  });
  return { nodes, palette, animated: nodes.length > 0 || palette.some((p) => p.byFrame) };
}

/** Show the nodes that belong to sprite frame `frame` (-1: none of the tagged ones). */
export function showFrame(rig: FrameRig, frame: number): void {
  for (const n of rig.nodes) n.object.visible = n.frames.has(frame);
}

/**
 * The palette index a material shows on `frame`, after the enemy hit flash: blit_sprite2_filter
 * draws (hue & 0xf0) | (index & 0x0f); hue < 0 is no flash.
 */
export function paletteIndex(pm: PaletteMaterial, frame: number, hue: number): number {
  const index = pm.byFrame?.get(frame) ?? pm.index;
  return hue < 0 ? index : (hue & 0xf0) | (index & 0x0f);
}

/** Colour every palette material for `frame` with `color(index, target)` (e.g. PaletteTexture.color). */
export function colourFrame(rig: FrameRig, frame: number, hue: number, color: (index: number, target: THREE.Color) => THREE.Color): void {
  for (const pm of rig.palette) {
    color(paletteIndex(pm, frame, hue), pm.material.color);
    if (pm.emissive) pm.material.emissive.copy(pm.material.color);
  }
}
