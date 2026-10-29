// A loaded model's outline shell and depth prepass (src/render/modelPrep.ts, DECISIONS.md D51), and
// the menu backdrop's engine glows from a model's `tyrian_engines` extras (src/ui/backdrop.ts).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { BLENDED_MODEL_ORDER, isModelHelper, prepareModel, setModelBlended } from "../../src/render/modelPrep";
import { engineGlows } from "../../src/ui/backdrop";

function model(withShell: boolean) {
  const root = new THREE.Group();
  const node = new THREE.Group();
  root.add(node);
  const hull = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial({ name: "pal_26_hull" }));
  const glow = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), new THREE.MeshStandardMaterial({ name: "pal_121_glow" }));
  glow.position.set(0, 0, 1);
  const flame = new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial({ name: "pal_122_flame" }));
  flame.userData.tyrian_frames = [91];
  node.add(hull, glow, flame);
  if (withShell) {
    const shell = new THREE.Mesh(new THREE.SphereGeometry(1), new THREE.MeshStandardMaterial({ name: "outline_shell" }));
    shell.userData.tyrian_outline = true;
    node.add(shell);
  }
  return { root, hull, glow, flame };
}

const meshes = (root: THREE.Object3D) => {
  const out: THREE.Mesh[] = [];
  root.traverse((o) => (o as THREE.Mesh).isMesh && out.push(o as THREE.Mesh));
  return out;
};

describe("prepareModel", () => {
  test("the shell draws only its outline and the model's own outline is off", () => {
    const { root, hull } = model(true);
    prepareModel(root);
    const shell = meshes(root).find((m) => m.userData.tyrian_outline)!;
    const mat = shell.material as THREE.Material;
    expect(mat.colorWrite).toBe(false);
    expect(mat.depthWrite).toBe(false);
    expect(mat.userData.outlineParameters.visible).toBe(true);
    expect(isModelHelper(shell)).toBe(true);
    expect((hull.material as THREE.Material).userData.outlineParameters.visible).toBe(false);
  });

  test("without a shell the model keeps its own outline", () => {
    const { root, hull } = model(false);
    prepareModel(root);
    expect((hull.material as THREE.Material).userData.outlineParameters).toBeUndefined();
  });

  test("a hidden depth prepass covers the untagged parts and shows only while translucent", () => {
    const { root } = model(false);
    prepareModel(root);
    const prepass = meshes(root).find((m) => m.userData.depthPrepass)!;
    expect(prepass.visible).toBe(false);
    expect((prepass.material as THREE.Material).colorWrite).toBe(false);
    // The hull (24 vertices as triangles: 36) and the glow (36); the frame-tagged flame is left out.
    expect(prepass.geometry.getAttribute("position").count).toBe(72);
    prepass.geometry.computeBoundingBox();
    expect(prepass.geometry.boundingBox!.max.z).toBeCloseTo(1.25);

    setModelBlended(root, true);
    expect(prepass.visible).toBe(true);
    for (const m of meshes(root).filter((m) => !isModelHelper(m))) expect(m.renderOrder).toBe(BLENDED_MODEL_ORDER);
    expect(prepass.renderOrder).toBeLessThan(BLENDED_MODEL_ORDER);
    setModelBlended(root, false);
    expect(prepass.visible).toBe(false);
    for (const m of meshes(root).filter((m) => !isModelHelper(m))) expect(m.renderOrder).toBe(0);
  });
});

describe("engineGlows", () => {
  test("one glow per engine the model names, in the pivot's space", () => {
    const { root } = model(false);
    root.children[0].userData.tyrian_engines = { color: "#ff8a2a", at: [[-0.3, 0, 1], [0.3, 0, 1]] };
    const pivot = new THREE.Group();
    root.scale.setScalar(2);
    root.position.set(0, 1, 0);
    pivot.add(root);
    const glows = engineGlows(root, pivot, 0.5);
    expect(glows).toHaveLength(2);
    expect(glows[1].position.toArray()).toEqual([0.6, 1, 2]);
    expect(glows[0].color).toBe("#ff8a2a");
  });

  test("otherwise one glow behind the centre", () => {
    const { root } = model(false);
    const glows = engineGlows(root, new THREE.Group(), 0.5);
    expect(glows).toHaveLength(1);
    expect(glows[0].position.toArray()).toEqual([0, 0, 0.5]);
  });
});
