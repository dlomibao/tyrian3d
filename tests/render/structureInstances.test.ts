// The parts a structure model becomes when instanced (src/render/remaster/structureInstances.ts,
// DECISIONS.md D34, D142): its colour meshes only, never prepareModel's helpers (depth prepass,
// outline shell, D51).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { isModelHelper, prepareModel } from "../../src/render/modelPrep";
import { StructureInstances } from "../../src/render/remaster/structureInstances";

/**
 * A loaded tile model as loadModel returns it: two palette meshes (one under a node), and optionally a
 * D51 shell, tagged `tyrian_tile_outline` with `inked` (the asteroid rim's, D211).
 */
function structure(withShell: boolean, inked = false) {
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
    if (inked) shell.userData.tyrian_tile_outline = true;
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

  test("a shell tagged tyrian_tile_outline stays as an instanced part drawn only by the outline pass (D211)", () => {
    const structures = new StructureInstances();
    structures.add("rim", structure(true, true));
    const parts = structures.meshes("rim");
    expect(parts.map((m) => (m.material as THREE.Material).name).sort()).toEqual(["outline_shell", "pal_121_light", "pal_26_deck"]);
    const shell = parts.find((m) => (m.material as THREE.Material).name === "outline_shell")!;
    const mat = shell.material as THREE.Material;
    expect(mat.colorWrite).toBe(false); // prepareModel's: no colour, no depth
    expect(mat.depthWrite).toBe(false);
    expect(mat.userData.outlineParameters.visible).toBe(true);
    expect(shell.castShadow).toBe(false);
    for (const m of parts.filter((p) => p !== shell)) expect((m.material as THREE.Material).userData.outlineParameters.visible).toBe(false);
    // the heights stay the colour parts' (the shell is a sphere of radius 1.5)
    expect(structures.heights("rim")!.high).toBeLessThan(1);
    structures.begin();
    for (let i = 0; i < 3; i++) structures.place("rim", i * 2, 0, 0, 1);
    structures.end(1, (_i, c) => c.set(0xffffff));
    expect(shell.count).toBe(3);
  });

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

  test("a model's heights are its colour parts' (not the outline shell's), for the blended sheets over it (D129, D188)", () => {
    const structures = new StructureInstances();
    expect(structures.heights("tile")).toBeNull();
    structures.add("tile", structure(true));
    const h = structures.heights("tile")!;
    expect(h.low).toBeCloseTo(-0.25); // the deck, 0.5 tall round the origin
    expect(h.high).toBeCloseTo(0.6); // the light's top on its node 0.5 up; the shell's 1.5 is left out
  });

  test("a released model leaves the group, and its geometry, materials and textures are freed (D236)", () => {
    const si = new StructureInstances();
    const model = structure(true, true);
    const map = new THREE.Texture();
    model.traverse((o) => {
      const m = (o as THREE.Mesh).material as THREE.MeshStandardMaterial | undefined;
      if (m?.name === "pal_26_deck") m.map = map;
    });
    si.add("tiles/test/a", model);
    si.add("tiles/test/b", structure(false));
    const meshes = si.meshes("tiles/test/a");
    expect(meshes.length).toBeGreaterThan(0);
    const freed = new Set<object>();
    for (const m of meshes) {
      m.geometry.addEventListener("dispose", () => freed.add(m.geometry));
      (m.material as THREE.Material).addEventListener("dispose", () => freed.add(m.material as THREE.Material));
    }
    let mapFreed = false;
    map.addEventListener("dispose", () => (mapFreed = true));
    const forgot: THREE.Material[] = [];
    expect(si.release("tiles/test/a", (m) => forgot.push(m))).toBe(true);
    expect(si.has("tiles/test/a")).toBe(false);
    expect(meshes.every((m) => m.parent === null)).toBe(true);
    expect(meshes.every((m) => freed.has(m.geometry) && freed.has(m.material as THREE.Material))).toBe(true);
    expect(new Set(forgot)).toEqual(new Set(meshes.map((m) => m.material)));
    expect([mapFreed, map.userData.released]).toEqual([true, true]);
    expect(si.release("tiles/test/a")).toBe(false);
    // The other model is untouched, and a frame still draws it.
    expect(si.has("tiles/test/b")).toBe(true);
    si.begin();
    si.place("tiles/test/b", 0, 0, 0, 1);
    si.end(0, (_, c) => c);
    expect(si.stats().models).toBe(1);
  });
});
