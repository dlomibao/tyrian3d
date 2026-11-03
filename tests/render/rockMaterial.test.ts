// The island rock's HD material (DECISIONS.md D84): a glTF material marked `tyrian_rock_ramps` with
// a data texture becomes a palette-coloured material; its edge bands are picked per copy from the
// tile's neighbours; an enemy clone flashes on its own; the Options terrain look switches it.
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { colourFrame, rigModel } from "../../src/render/modelFrames";
import { PaletteTexture } from "../../src/render/paletteTexture";
import {
  adoptRockMaterials,
  cloneRockMaterial,
  hasRockBands,
  isRockMaterial,
  rockBandSlot,
  rockLookIsHd,
  setRockLook,
} from "../../src/render/rockMaterial";
import { StructureInstances } from "../../src/render/remaster/structureInstances";

function source(bands?: string[]): THREE.MeshStandardMaterial {
  const m = new THREE.MeshStandardMaterial({ name: "rock_t131", map: new THREE.Texture() });
  m.userData = { tyrian_rock_ramps: [0, 10, 1], tyrian_plain: true };
  if (bands) {
    m.emissiveMap = new THREE.Texture({ width: 224, height: 24 * bands.length } as unknown as HTMLImageElement);
    Object.assign(m.userData, { tyrian_rock_bands: bands, tyrian_rock_band_depth: 24, tyrian_rock_band_fade: 8 });
  }
  return m;
}

function tile(bands?: string[]) {
  const root = new THREE.Group();
  const mat = source(bands);
  root.add(new THREE.Mesh(new THREE.PlaneGeometry(), mat), new THREE.Mesh(new THREE.PlaneGeometry(), mat));
  return { root, mat };
}

describe("rock material", () => {
  test("replaces the rock sources, one material per source, the texture read as data", () => {
    const { root, mat } = tile();
    const palette = new PaletteTexture();
    adoptRockMaterials(root, palette);
    const [a, b] = root.children.map((c) => (c as THREE.Mesh).material as THREE.MeshStandardMaterial);
    expect(a).toBe(b);
    expect(isRockMaterial(a)).toBe(true);
    expect(a.map).toBe(mat.map);
    expect(a.bumpMap).toBe(mat.map);
    expect(a.map!.colorSpace).toBe(THREE.NoColorSpace);
    expect(a.emissiveMap).toBeNull();
    expect(a.userData.tyrian_plain).toBe(true);
    // Palette materials are left alone.
    const other = new THREE.Mesh(new THREE.PlaneGeometry(), new THREE.MeshStandardMaterial({ name: "pal_8_x" }));
    root.add(other);
    adoptRockMaterials(root, palette);
    expect(isRockMaterial(other.material as THREE.Material)).toBe(false);
  });

  test("an edge band is found by side and neighbour; none is 0", () => {
    const { root } = tile(["down:141", "left:131", "right:121"]);
    adoptRockMaterials(root, new PaletteTexture());
    const m = (root.children[0] as THREE.Mesh).material as THREE.Material;
    expect(hasRockBands(m)).toBe(true);
    expect(rockBandSlot(m, "down", 141)).toBe(1);
    expect(rockBandSlot(m, "left", 131)).toBe(2);
    expect(rockBandSlot(m, "right", 121)).toBe(3);
    expect(rockBandSlot(m, "right", 131)).toBe(0);
    expect(rockBandSlot(m, "up", -1)).toBe(0);
    const band = (m as THREE.MeshStandardMaterial).defines;
    expect(band).toHaveProperty("ROCK_BANDS");
  });

  test("the hit flash's hue reaches the rock, each clone on its own", () => {
    const { root } = tile();
    adoptRockMaterials(root, new PaletteTexture());
    const m = (root.children[0] as THREE.Mesh).material as THREE.Material;
    const copy = cloneRockMaterial(m);
    expect(isRockMaterial(copy)).toBe(true);
    expect(copy).not.toBe(m);
    const rig = rigModel(root);
    expect(rig.rock).toEqual([m]);
    expect(rig.palette).toEqual([]);
    colourFrame(rig, -1, 0x70, (_i, t) => t);
    // The uniforms are applied at compile time; check what the shader would be given.
    const shader = { uniforms: {} as Record<string, { value: unknown }>, vertexShader: "#include <common>\n#include <begin_vertex>", fragmentShader: "#include <common>\n#include <map_pars_fragment>\n#include <map_fragment>\n#include <bumpmap_pars_fragment>" };
    (m.onBeforeCompile as (s: typeof shader, r: unknown) => void)(shader, null);
    expect(shader.uniforms.rockHue.value).toBe(0x70);
    const shaderCopy = { ...shader, uniforms: {} as Record<string, { value: unknown }> };
    (copy.onBeforeCompile as (s: typeof shader, r: unknown) => void)(shaderCopy, null);
    expect(shaderCopy.uniforms.rockHue.value).toBe(-1);
    expect(shader.fragmentShader).toContain("rockTexel(vMapUv)");
    expect(shader.fragmentShader).not.toContain("#include <bumpmap_pars_fragment>");
    expect(shader.fragmentShader).toContain("rockBumpH( vBumpMapUv + dSTdx )");
  });

  test("the terrain look switches between smooth and pixel rock", () => {
    setRockLook(false);
    expect(rockLookIsHd()).toBe(false);
    setRockLook(true);
    expect(rockLookIsHd()).toBe(true);
  });
});

describe("structure instances", () => {
  test("each copy of a rock tile draws the bands of its own neighbours", () => {
    const { root } = tile(["left:120", "right:122", "down:131"]);
    adoptRockMaterials(root, new PaletteTexture());
    root.remove(root.children[1]);
    const s = new StructureInstances();
    s.add("t121", root);
    s.begin();
    s.place("t121", 0, 0, 0, 1, () => [120, 121, 141, 131]);
    s.place("t121", 1, 0, 0, 1, () => [-1, 122, -1, 5]);
    s.end(0, (_i, t) => t);
    const mesh = s.group.children[0] as THREE.InstancedMesh;
    const bands = mesh.geometry.getAttribute("rockBands") as THREE.InstancedBufferAttribute;
    expect([...bands.array.slice(0, 8)]).toEqual([1, 0, 0, 3, 0, 2, 0, 0]);
    // More copies than it was made for: the bands grow with the instances.
    s.begin();
    for (let i = 0; i < 9; i++) s.place("t121", i, 0, 0, 1, () => [120, 122, -1, 131]);
    s.end(0, (_i, t) => t);
    const grown = (s.group.children[0] as THREE.InstancedMesh).geometry.getAttribute("rockBands") as THREE.InstancedBufferAttribute;
    expect(grown.count).toBeGreaterThanOrEqual(9);
    expect([...grown.array.slice(8 * 4, 9 * 4)]).toEqual([1, 2, 0, 3]);
  });

  test("a structure's rock cells each draw the bands of their own neighbours", () => {
    const root = new THREE.Group();
    const palette = new PaletteTexture();
    for (const [c, keys] of [[0, ["right:157", "left:131"]], [1, ["left:155", "right:153"]]] as const) {
      const m = source([...keys]);
      m.userData.tyrian_rock_cell = [0, c];
      root.add(new THREE.Mesh(new THREE.PlaneGeometry(), m));
    }
    adoptRockMaterials(root, palette);
    const s = new StructureInstances();
    s.add("purple", root);
    s.begin();
    // The map: 131 | 155 157 | 153 (the structure's two cells in the middle).
    const row = [131, 155, 157, 153];
    s.place("purple", 0, 0, 0, 1, (_r, c) => [row[c], row[c + 2], -1, -1]);
    s.end(0, (_i, t) => t);
    const bands = s.group.children.map((m) => [...((m as THREE.InstancedMesh).geometry.getAttribute("rockBands") as THREE.InstancedBufferAttribute).array.slice(0, 4)]);
    expect(bands).toEqual([
      [2, 1, 0, 0], // cell 0: left 131, right 157
      [1, 2, 0, 0], // cell 1: left 155, right 153
    ]);
  });
});
