import * as THREE from "three";
import { expect, test } from "vitest";
import { colourFrame, paletteIndex, rigModel, showFrame } from "../../src/render/modelFrames";

function model() {
  const root = new THREE.Group();
  const hull = new THREE.MeshStandardMaterial({ name: "pal_8_x" });
  const glow = new THREE.MeshStandardMaterial({ name: "pal_120_x_glow", emissive: 0xff0000 });
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
  expect(glow.emissive.r).toBeCloseTo(glow.color.r);
});
