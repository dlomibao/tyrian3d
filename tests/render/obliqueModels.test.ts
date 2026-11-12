// Tall sprite and enemy models drawn in the art's view (DECISIONS.md D165, extending D82's approach C):
// a model whose glb carries `tyrian_oblique` and `tyrian_depth_band` is the real upright object, and
// the renderer puts each vertex on the camera ray through the point the art draws it at
// (src/render/obliqueView.ts). Models without the extras are never patched.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DAMAGE_CUT_VERTEX, damageUniforms, patchDamage } from "../../src/render/damage/damageShader";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { prepareModel } from "../../src/render/modelPrep";
import {
  bandHeight, depthBandOf, drawnBox, obliqueUniforms, obliqueVertexSource, patchOblique, placeVertex, prepareObliqueClone, rayPoint,
} from "../../src/render/obliqueView";
import { spriteModels, type SpriteModelEntry } from "../../src/render/spriteModels";
import { ENEMY_KEY_BASE, Pass, type DrawList, type Sprite2Sheet, type SpriteDraw } from "../../src/sim/draw";
import type { Palette } from "../../src/data/palette";

vi.stubGlobal("location", { search: "" });

const E = THREE.MathUtils.degToRad(15);
/** A DELIANI-like tower piece: a 0.6-unit drum 8 units tall, its axis at z = 1.2 of the piece. */
const AXIS = 1.2;
const VIEW = [Math.cos(E), Math.sin(E), AXIS];
const BAND = [0, 0.8, 0, 8];

function tower(extras: Record<string, unknown> = { tyrian_oblique: VIEW, tyrian_depth_band: BAND }, offset = new THREE.Vector3()) {
  const root = new THREE.Group();
  const node = new THREE.Group();
  node.position.copy(offset);
  const drum = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 8, 16).translate(0, 4, AXIS), new THREE.MeshStandardMaterial());
  Object.assign(drum.userData, extras);
  node.add(drum);
  root.add(node);
  return root;
}

const screen = (p: THREE.Vector3, camera: THREE.Camera) => p.clone().project(camera);

describe("the extras of a tall sprite model", () => {
  test("an orthographic art view from the south: [cos e, sin e, axis], and a shared height range", () => {
    expect(depthBandOf(tower({}))).toBeNull();
    const band = depthBandOf(tower())!;
    expect(band.oblique).toBeCloseTo(Math.cos(E));
    expect(band.squeeze).toBeCloseTo(Math.sin(E));
    expect(band.axisZ).toBeCloseTo(AXIS);
    // The range given, not the piece's own bounds: the pieces of one tower agree on their depths.
    expect(band).toMatchObject({ lo: 0, hi: 0.8, zMin: 0, zMax: 8 });
    expect(bandHeight(band, 4)).toBeCloseTo(0.4);
    // D82's form still reads as before: k alone, the range from the geometry.
    const d82 = depthBandOf(tower({ tyrian_oblique: 1, tyrian_depth_band: [0, 0.04] }))!;
    expect(d82).toEqual({ oblique: 1, lo: 0, hi: 0.04, zMin: expect.closeTo(0) as number, zMax: expect.closeTo(8) as number });
    expect(d82.squeeze).toBeUndefined();
    // Malformed: ignored.
    expect(depthBandOf(tower({ tyrian_oblique: [1, 0.5], tyrian_depth_band: [0, 0.8, 0] }))).toBeNull();
  });

  test("the art's picture: the foot stays, rims become flat ellipses, height goes up the screen", () => {
    const band = depthBandOf(tower())!;
    const foot = rayPoint(band, new THREE.Vector3(0.3, 0, AXIS));
    expect(foot.x).toBeCloseTo(0.3);
    expect(foot.z).toBeCloseTo(AXIS);
    // The rim's south point (0.6 nearer the camera) is drawn sin 15° of that below the axis.
    expect(rayPoint(band, new THREE.Vector3(0, 0, AXIS + 0.6)).z).toBeCloseTo(AXIS + 0.6 * Math.sin(E));
    // The top, cos 15° per unit of height up the screen (-z).
    expect(rayPoint(band, new THREE.Vector3(0, 8, AXIS)).z).toBeCloseTo(AXIS - 8 * Math.cos(E));
  });

  test("each vertex lands on the art's screen point at every tilt and place, with its squeezed depth", () => {
    const band = depthBandOf(tower())!;
    for (const tilt of [1e-7, 15, 32]) {
      const camera = new THREE.PerspectiveCamera(40, 264 / 184, 0.1, 500);
      const t = THREE.MathUtils.degToRad(tilt);
      camera.position.set(0, 20 * Math.cos(t), 20 * Math.sin(t));
      camera.lookAt(0, 0, 0);
      camera.updateMatrixWorld();
      for (const at of [new THREE.Vector3(-6, 0.45, -6), new THREE.Vector3(5, 0.45, 6)]) {
        const scale = 1 - at.y / camera.position.y;
        const toWorld = new THREE.Matrix4().compose(at, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale));
        const p = new THREE.Vector3(0.4, 6, AXIS + 0.3);
        const drawn = placeVertex(band, p, toWorld, camera.position);
        const a = screen(drawn, camera);
        const b = screen(rayPoint(band, p).applyMatrix4(toWorld), camera);
        expect(a.x).toBeCloseTo(b.x, 6);
        expect(a.y).toBeCloseTo(b.y, 6);
        expect(drawn.y - at.y).toBeCloseTo(bandHeight(band, p.y) * scale, 6);
      }
    }
  });

  test("its box is where it is drawn: the art's picture, its band's heights", () => {
    const box = drawnBox(prepareModel(tower()), depthBandOf(tower())!);
    expect(box.min.x).toBeCloseTo(-0.6, 2);
    expect(box.max.z).toBeCloseTo(AXIS + 0.6 * Math.sin(E), 2);
    expect(box.min.z).toBeCloseTo(AXIS - 0.6 * Math.sin(E) - 8 * Math.cos(E), 2);
    expect([box.min.y, box.max.y]).toEqual([0, 0.8]);
  });
});

describe("a clone of a tall sprite model", () => {
  test("every mesh, its outline shell and its depth prepass too, gets its own matrix to the root", () => {
    const source = tower(undefined, new THREE.Vector3(0.5, 0, -0.25));
    const shell = new THREE.Mesh(new THREE.CylinderGeometry(0.65, 0.65, 8.1, 16), new THREE.MeshBasicMaterial());
    shell.userData.tyrian_outline = true;
    source.children[0].add(shell);
    prepareModel(source);
    const clone = source.clone(true);
    clone.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.material = (m.material as THREE.Material).clone();
    });
    clone.position.set(3, 0.45, -2); // where the root is placed doesn't matter: only the parts' own matrices
    clone.scale.setScalar(0.97);
    prepareObliqueClone(clone, depthBandOf(source)!);
    const meshes: THREE.Mesh[] = [];
    clone.traverse((o) => void ((o as THREE.Mesh).isMesh && meshes.push(o as THREE.Mesh)));
    expect(meshes).toHaveLength(3); // the drum, the shell, the prepass
    for (const mesh of meshes) {
      const u = (mesh.material as THREE.Material).userData.obliqueUniforms;
      expect(u).toBeDefined();
      const expected = mesh.userData.depthPrepass ? new THREE.Vector3() : new THREE.Vector3(0.5, 0, -0.25);
      expect(new THREE.Vector3().setFromMatrixPosition(u.obliqueMeshToRoot.value).distanceTo(expected)).toBeLessThan(1e-9);
      expect(u.obliqueRootToMesh.value.clone().multiply(u.obliqueMeshToRoot.value).equals(new THREE.Matrix4())).toBe(true);
      expect(u.obliquePlan.value.x).toBeCloseTo(Math.sin(E));
      expect((mesh.material as THREE.Material).customProgramCacheKey()).toContain("|depth-band-squeeze");
    }
  });

  test("the shader: D82's sum for structures, the squeeze for the art's camera, the damage seen from the art", () => {
    const vertex = THREE.ShaderLib.standard.vertexShader;
    const d82 = obliqueVertexSource(vertex, obliqueUniforms({ oblique: 1, lo: 0, hi: 0.04, zMin: 0, zMax: 4 }));
    expect(d82).not.toContain("#define OBLIQUE_SQUEEZE");
    expect(d82).toContain("vec3 local = oblique > 0.0 ? vec3(q.x, 0.0, q.z - oblique * q.y) : q;");
    const squeezed = obliqueVertexSource(vertex, obliqueUniforms(depthBandOf(tower())!));
    expect(squeezed).toContain("#define OBLIQUE_SQUEEZE");
    // A damaged frame (D87) is projected onto the sprite from where the art draws the vertex.
    const m = new THREE.MeshStandardMaterial();
    patchDamage(m, damageUniforms());
    patchOblique(m, obliqueUniforms(depthBandOf(tower())!));
    const shader = { vertexShader: vertex, fragmentShader: THREE.ShaderLib.standard.fragmentShader, uniforms: {} } as unknown as THREE.WebGLProgramParametersWithUniforms;
    m.onBeforeCompile(shader, {} as THREE.WebGLRenderer);
    expect(shader.vertexShader).not.toContain(DAMAGE_CUT_VERTEX);
    expect(shader.vertexShader).toContain("vDmgPos = oblique > 0.0 ? obliqueArt");
    expect(Object.keys(shader.uniforms)).toEqual(expect.arrayContaining(["uDmgInv", "depthBand", "oblique", "obliquePlan", "obliqueMeshToRoot"]));
    // The ink outline (outlineEffect.js) pushes along the normal as drawn.
    const outline = obliqueVertexSource("#include <common>\nvec4 pos2 = projectionMatrix * modelViewMatrix * vec4( skinned.xyz + normal, 1.0 );", obliqueUniforms(depthBandOf(tower())!));
    expect(outline).toContain("obliquePlaced( skinned.xyz + normal )");
  });
});

describe("in the game's renderer", () => {
  // As modelPop.test.ts: a sheet of one-pixel sprites, an enemy of four quarters.
  const sprites = Array.from({ length: 30 }, () => [0x10, 5, 0x0f]);
  const bytes: number[] = [];
  let at = sprites.length * 2;
  for (const data of sprites) {
    bytes.push(at & 0xff, at >> 8);
    at += data.length;
  }
  const sheet: Sprite2Sheet = { id: "newshc.shp", data: Uint8Array.from([...bytes, ...sprites.flat()]) };
  const enemy = (serial: number, frame = 3, x = 100): SpriteDraw[] =>
    [0, 1, 19, 20].map((di, part) => ({
      kind: "sprite2", sheet, index: frame + di, x: x + (di % 19) * 12, y: 50 + (di >= 19 ? 14 : 0), size: 1, pass: Pass.GroundEnemies,
      key: ENEMY_KEY_BASE + serial * 4 + part, effect: "none", filter: 0, value: 0,
      groupIndex: frame, groupSize: 2, groupDx: 12 - (di % 19) * 12, groupDy: 14 - (di >= 19 ? 14 : 0), groupFirst: part === 0,
    }));

  test("a tagged model's clone is patched; an untagged one's is left exactly as it was", async () => {
    const entries: SpriteModelEntry[] = [{ model: "enemies/tower", sprites: [{ sheet: sheet.id, size: 2, frames: [3] }] }];
    const plain = () => {
      const g = new THREE.Group();
      g.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshStandardMaterial()));
      return prepareModel(g);
    };
    for (const tagged of [true, false]) {
      const r = new DrawListRenderer();
      r.setVfxMode("original");
      r.setPalettes([new Uint8Array(768) as unknown as Palette]);
      r.setSpriteModels(spriteModels(entries), async () => (tagged ? prepareModel(tower()) : plain()));
      await r.preloadLevel({ sprites: [{ sheet: sheet.id, size: 2, index: 3, grouped: true, time: 0 }] });
      const list: DrawList = { items: enemy(1), palette: 0, filter: -99, brightness: 0, screen: null };
      r.setDrawList(list);
      const camera = new THREE.PerspectiveCamera();
      camera.position.set(0, 30, 10);
      r.update(1, camera);
      const materials: THREE.Material[] = [];
      r.root.traverse((o) => {
        const m = o as THREE.Mesh;
        const mat = m.isMesh ? (m.material as THREE.Material) : null;
        if (mat && (mat.type === "MeshStandardMaterial" || mat.name === "depth_prepass")) materials.push(mat);
      });
      expect(materials.length).toBe(2); // the clone's drum and its depth prepass
      for (const m of materials) {
        expect(m.userData.obliqueUniforms !== undefined).toBe(tagged);
        expect(m.customProgramCacheKey().includes("depth-band")).toBe(tagged);
      }
    }
  });
});
