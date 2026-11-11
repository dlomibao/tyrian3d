// The parts a structure model becomes when instanced (src/render/remaster/structureInstances.ts,
// DECISIONS.md D34, D142): its colour meshes only, never prepareModel's helpers (depth prepass,
// outline shell, D51).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { isModelHelper, prepareModel } from "../../src/render/modelPrep";
import { StructureInstances } from "../../src/render/remaster/structureInstances";

/** A loaded tile model as loadModel returns it: two palette meshes (one under a node), and optionally a D51 shell. */
function structure(withShell: boolean) {
  const root = new THREE.Group();
  const node = new THREE.Group();
  node.position.set(0, 0.5, 0);
  root.add(node);
  const deck = new THREE.Mesh(new THREE.BoxGeometry(2, 0.5, 2), new THREE.MeshStandardMaterial({ name: "pal_26_deck" }));
  const light = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.2, 0.2), new THREE.MeshStandardMaterial({ name: "pal_121_light" }));
  root.add(deck);
  node.add(light);
  if (withShell) {
    const shell = new THREE.Mesh(new THREE.SphereGeometry(1.5), new THREE.MeshStandardMaterial({ name: "shell" }));
    shell.userData.tyrian_outline = true;
    root.add(shell);
  }
  return prepareModel(root);
}

const helpers = (root: THREE.Object3D) => {
  const out: THREE.Object3D[] = [];
  root.traverse((o) => (o as THREE.Mesh).isMesh && isModelHelper(o) && out.push(o));
  return out;
};

describe("StructureInstances", () => {
  test("prepareModel gives a loaded model a hidden depth prepass (the helper the instancer must skip)", () => {
    const model = structure(false);
    const prepass = helpers(model);
    expect(prepass).toHaveLength(1);
    expect(prepass[0].visible).toBe(false);
    expect((prepass[0] as THREE.Mesh).castShadow).toBe(false);
  });

  for (const withShell of [false, true]) {
    test(`a model's parts are its colour meshes only, not its prepass${withShell ? " or outline shell" : ""} (D142)`, () => {
      const structures = new StructureInstances();
      const model = structure(withShell);
      structures.add("tile", model);
      const parts = structures.meshes("tile");
      expect(parts.map((m) => (m.material as THREE.Material).name).sort()).toEqual(["pal_121_light", "pal_26_deck"]);
      for (const m of parts) {
        const mat = m.material as THREE.Material;
        expect(mat.colorWrite).toBe(true);
        expect(mat.userData.depthPrepass).toBeUndefined();
        expect(mat.userData.outlineShell).toBeUndefined();
        expect(mat.userData.outlineParameters.visible).toBe(false); // tiles join edge to edge (D8)
        expect(m.castShadow).toBe(true);
        expect(m.receiveShadow).toBe(true);
      }
      expect(structures.group.children).toHaveLength(2);
      expect(helpers(model)).toHaveLength(0); // dropped from the kept source, its geometry freed
    });
  }

  test("placed copies draw one instanced mesh per colour part, and nothing else", () => {
    const structures = new StructureInstances();
    structures.add("tile", structure(true));
    structures.begin();
    for (let i = 0; i < 6; i++) structures.place("tile", i * 2, 0, 0, 1);
    structures.end(1, (_i, c) => c.set(0xffffff));
    const drawn = structures.group.children.filter((o) => o.visible) as THREE.InstancedMesh[];
    expect(drawn).toHaveLength(2);
    for (const m of drawn) expect(m.count).toBe(6);
    expect(structures.stats()).toEqual({ models: 1, instances: 6, parts: 2 });
  });
});
