import * as THREE from "three";
import { expect, test } from "vitest";
import { colourFrame, paletteIndex, rigModel, showFrame } from "../../src/render/modelFrames";

function model() {
  const root = new THREE.Group();
  const hull = new THREE.MeshStandardMaterial({ name: "pal_8_x" });
  const glow = new THREE.MeshStandardMaterial({ name: "pal_120_x_glow", color: 0xff0000, emissive: 0xff0000 });
  glow.userData.tyrian_frame_pal = { "91": 122 };
  const body = new THREE.Mesh(new THREE.BoxGeometry(), [hull, glow]);
  const flame91 = new THREE.Mesh(new THREE.BoxGeometry(), hull);
  flame91.userData.tyrian_frames = [91];
  root.add(body, flame91);
  return { root, body, flame91, glow };
}

test("rigModel finds frame-tagged parts and per-frame palette colours, through a clone", () => {
  const { root } = model();
  const clone = root.clone(true);
  const rig = rigModel(clone);
  expect(rig.animated).toBe(true);
  expect(rig.nodes.map((n) => [...n.frames])).toEqual([[91]]);
  expect(rig.palette.map((p) => [p.index, p.emissive, p.byFrame ? [...p.byFrame] : null])).toEqual([[8, false, null], [120, true, [[91, 122]]]]);
});

test("showFrame shows tagged parts only on their frames", () => {
  const { root, body, flame91 } = model();
  const rig = rigModel(root);
  showFrame(rig, 89);
  expect([body.visible, flame91.visible]).toEqual([true, false]);
  showFrame(rig, 91);
  expect([body.visible, flame91.visible]).toEqual([true, true]);
});

test("colours follow the frame, and the hit flash keeps the shade in its hue", () => {
  const { root, glow } = model();
  const rig = rigModel(root);
  const glowRig = rig.palette[1];
  expect(paletteIndex(glowRig, 89, -1)).toBe(120);
  expect(paletteIndex(glowRig, 91, -1)).toBe(122);
  expect(paletteIndex(glowRig, 91, 0x70)).toBe(0x7a);
  const seen: number[] = [];
  colourFrame(rig, 91, -1, (i, t) => (seen.push(i), t.setRGB(i / 255, 0, 0)));
  expect(seen).toEqual([8, 122]);
  // An emissive authored at strength 1 (emissive = colour): all glow, its lit colour gone (D126).
  expect(glow.emissive.r).toBeCloseTo(122 / 255);
  expect(glow.color.r).toBe(0);
});

/** A pal_ material as GLTFLoader builds it from Blender's export of palette_material(emission_strength=s). */
function exported(name: string, rgb: [number, number, number], strength: number): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ name });
  m.color.setRGB(...rgb);
  // The exporter writes colour × strength into emissiveFactor, and what doesn't fit under 1 into
  // KHR_materials_emissive_strength (GLTFLoader: emissiveIntensity).
  const peak = Math.max(...rgb) * strength;
  const intensity = Math.max(1, peak);
  m.emissive.setRGB(...(rgb.map((c) => (c * strength) / intensity) as [number, number, number]));
  m.emissiveIntensity = intensity;
  return m;
}

test("a glow takes its authored strength, below 1 too, in the live palette colour (D126)", () => {
  const ember = exported("pal_121_lens", [0.8, 0.12, 0.004], 0.4); // newshm-7's lens: emissiveFactor only
  const dark = exported("pal_117_vent", [0.34, 0.002, 0], 3); // dark colour: 1.02 fits in emissiveFactor
  const hot = exported("pal_118_nav", [0.49, 0.004, 0], 5); // the Talon's nav light: extension 2.45
  const hull = new THREE.MeshStandardMaterial({ name: "pal_8_hull" });
  const root = new THREE.Mesh(new THREE.BoxGeometry(), [ember, dark, hot, hull]);
  const rig = rigModel(root);
  expect(rig.palette.map((p) => [p.emissive, Number(p.glow.toFixed(3))])).toEqual([[true, 0.4], [true, 3], [true, 5], [false, 0]]);

  // The palette may be any colour (a fade, another level's palette, the hit flash's hue).
  colourFrame(rig, -1, -1, (_i, t) => t.setRGB(0.5, 0.25, 0.1));
  // The emitted light is palette × strength, with the strength no longer in emissiveIntensity...
  for (const [m, s] of [[ember, 0.4], [dark, 3], [hot, 5]] as const) {
    expect(m.emissiveIntensity).toBe(1);
    expect(m.emissive.r).toBeCloseTo(0.5 * s);
    expect(m.emissive.g).toBeCloseTo(0.25 * s);
    expect(m.emissive.b).toBeCloseTo(0.1 * s);
  }
  // ...and stands in for the lit colour: the rest of 1 below it, none from 1 up.
  expect(ember.color.r).toBeCloseTo(0.5 * 0.6);
  expect(ember.color.g).toBeCloseTo(0.25 * 0.6);
  expect(dark.color.getHex()).toBe(0);
  expect(hot.color.getHex()).toBe(0);
  expect(hull.color.r).toBeCloseTo(0.5);
  expect(hull.emissive.getHex()).toBe(0);
});

test("the authored strength survives recolouring and material clones", () => {
  const ember = exported("pal_121_lens", [0.8, 0.12, 0.004], 0.4);
  const rig = rigModel(new THREE.Mesh(new THREE.BoxGeometry(), ember));
  colourFrame(rig, -1, -1, (_i, t) => t.setRGB(1, 0, 0));
  colourFrame(rig, -1, 0x70, (_i, t) => t.setRGB(0, 1, 0)); // the hit flash
  expect(ember.emissive.g).toBeCloseTo(0.4);
  expect(ember.color.g).toBeCloseTo(0.6);
  // A clone of a coloured material (a pool's clone of a used source) rigs to the same strength.
  const clone = ember.clone();
  const cloneRig = rigModel(new THREE.Mesh(new THREE.BoxGeometry(), clone));
  expect(cloneRig.palette[0].glow).toBeCloseTo(0.4);
  colourFrame(cloneRig, -1, -1, (_i, t) => t.setRGB(0, 0, 1));
  expect([clone.emissive.b, clone.color.b]).toEqual([expect.closeTo(0.4), expect.closeTo(0.6)]);
});
