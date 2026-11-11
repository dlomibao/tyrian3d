// Sprite animation on models (DECISIONS.md D17). A model can cover several animation frames of its
// sprite and still animate: the Blender scripts tag parts and materials with glTF extras.
//
// - A node with extras `tyrian_frames: [89, 91]` is shown only while the sprite frame (the sprite
//   index of the frame's top-left tile) is one of those. Untagged nodes are always shown.
// - A material named pal_<index> with extras `tyrian_frame_pal: { "91": 122 }` takes palette colour
//   122 instead of <index> on frame 91 (a light that blinks, a glow that pulses).
// - A pal_<index> material that emits glows in its palette colour at the strength its Blender script
//   gave it (palette_material's emission_strength, below 1 too), and that light replaces its lit
//   colour: at strength 1 or more the part is all glow, the palette colour unlit (D126).
//
// GLTFLoader puts extras in userData; Object3D.clone and Material.clone copy it.

import type * as THREE from "three";
import { isRockMaterial, setRockHue } from "./rockMaterial";

export const PALETTE_MATERIAL = /^pal_(\d+)/;

/** A pal_<index> material: its colour follows the live palette. */
export interface PaletteMaterial {
  material: THREE.MeshStandardMaterial;
  index: number;
  /** Whether it glows, so its emissive colour follows too. */
  emissive: boolean;
  /** Its authored glow strength (glowStrength); 0 when it doesn't glow. */
  glow: number;
  /** Palette index per sprite frame, where it differs from `index`. */
  byFrame?: Map<number, number>;
}

/** What a model needs to follow its sprite's frames and the palette. */
export interface FrameRig {
  /** Nodes shown only on some frames. */
  nodes: { object: THREE.Object3D; frames: Set<number> }[];
  palette: PaletteMaterial[];
  /** HD rock materials (rockMaterial.ts): their colours come from the palette texture; only the hue is set. */
  rock: THREE.Material[];
  /** Whether anything depends on the frame. */
  animated: boolean;
}

/** Collect a model's frame-tagged nodes and palette materials (each material once). */
export function rigModel(root: THREE.Object3D): FrameRig {
  const nodes: FrameRig["nodes"] = [];
  const palette: PaletteMaterial[] = [];
  const rock: THREE.Material[] = [];
  const seen = new Set<THREE.Material>();
  root.traverse((o) => {
    const frames = o.userData?.tyrian_frames;
    if (Array.isArray(frames)) nodes.push({ object: o, frames: new Set(frames.map(Number)) });
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
      if (seen.has(m)) continue;
      seen.add(m);
      if (isRockMaterial(m)) {
        rock.push(m);
        continue;
      }
      const match = PALETTE_MATERIAL.exec(m.name);
      const std = m as THREE.MeshStandardMaterial;
      if (!match || !std.isMeshStandardMaterial) continue;
      const glow = glowStrength(std);
      const pm: PaletteMaterial = { material: std, index: Number(match[1]) & 0xff, emissive: glow > 0, glow };
      const byFrame = std.userData?.tyrian_frame_pal;
      if (byFrame && typeof byFrame === "object") {
        pm.byFrame = new Map(Object.entries(byFrame).map(([f, i]) => [Number(f), Number(i) & 0xff]));
      }
      palette.push(pm);
    }
  });
  return { nodes, palette, rock, animated: nodes.length > 0 || palette.some((p) => p.byFrame) };
}

/**
 * A pal_ material's authored glow strength: Blender's Emission Strength, its emission colour being its
 * base colour (palette_material). The glTF exporter writes colour × strength into emissiveFactor and
 * only what doesn't fit under 1 into KHR_materials_emissive_strength (emissiveIntensity), so the
 * strength is emissive / colour × emissiveIntensity. Read from the material as loaded and kept in
 * userData.tyrianGlow, since colourFrame rewrites the colours (and Material.clone copies userData);
 * emissiveIntensity becomes 1, the strength going into the emissive colour instead.
 */
export function glowStrength(m: THREE.MeshStandardMaterial): number {
  if (typeof m.userData.tyrianGlow !== "number") {
    const e = Math.max(m.emissive.r, m.emissive.g, m.emissive.b) * m.emissiveIntensity;
    const c = Math.max(m.color.r, m.color.g, m.color.b);
    m.userData.tyrianGlow = e > 0 ? (c > 1e-4 ? e / c : 1) : 0;
  }
  m.emissiveIntensity = 1;
  return m.userData.tyrianGlow;
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
    const { material } = pm;
    color(paletteIndex(pm, frame, hue), material.color);
    if (pm.glow > 0) {
      // The glow's light stands in for the lit colour (D126): palette × strength, plus the lit
      // palette colour for what's left under 1. Lit and glowing in full, a glow read pale (D121).
      material.emissive.copy(material.color).multiplyScalar(pm.glow);
      material.color.multiplyScalar(Math.max(0, 1 - pm.glow));
    }
  }
  for (const m of rig.rock) setRockHue(m, hue);
}
