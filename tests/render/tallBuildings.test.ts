// Tall buildings (DECISIONS.md D67, docs/agents/TALL-BUILDINGS.md): a structure model with the extras
// `tyrian_oblique` and `tyrian_depth_band` is drawn in the art's oblique view with its depth squeezed
// (src/render/remaster/structureInstances.ts).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { bandHeight, depthBandOf, placeVertex, rayPoint } from "../../src/render/remaster/structureInstances";

function building(height: number, extras: Record<string, unknown>) {
  const root = new THREE.Group();
  const box = new THREE.Mesh(new THREE.BoxGeometry(2, height, 1).translate(0, height / 2, 0), new THREE.MeshStandardMaterial());
  Object.assign(box.userData, extras);
  root.add(box);
  return root;
}

/** The game camera at 15° (tools/tall_buildings.py CAMERAS), looking at the playfield's centre. */
function tiltedCamera() {
  const camera = new THREE.PerspectiveCamera(40, 264 / 184, 0.1, 500);
  camera.position.set(0, 19.47, 5.96);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();
  return camera;
}

const screen = (p: THREE.Vector3, camera: THREE.Camera) => p.clone().project(camera);

describe("tall buildings", () => {
  test("a model asks for its depth band and oblique view through its extras", () => {
    expect(depthBandOf(building(4.5, {}))).toBeNull();
    // Within its band and drawn with the true perspective: nothing to do.
    expect(depthBandOf(building(0.03, { tyrian_depth_band: [0, 0.04] }))).toBeNull();
    const band = depthBandOf(building(4.5, { tyrian_depth_band: [0, 0.04], tyrian_oblique: 1 }))!;
    expect(band).toMatchObject({ oblique: 1, lo: 0, hi: 0.04 });
    expect(band.zMin).toBeCloseTo(0);
    expect(band.zMax).toBeCloseTo(4.5);
    expect(bandHeight(band, 0)).toBeCloseTo(0);
    expect(bandHeight(band, 4.5)).toBeCloseTo(0.04);
    expect(bandHeight(band, 9)).toBeCloseTo(0.04);
  });

  test("oblique: a point is drawn where the art draws it, k px up the screen per px of height", () => {
    const band = { oblique: 1, lo: 0, hi: 0.04, zMin: 0, zMax: 4.5 };
    expect(rayPoint(band, new THREE.Vector3(1, 0, 2)).toArray()).toEqual([1, 0, 2]); // the foot stays
    const roof = rayPoint(band, new THREE.Vector3(1, 4.5, 2));
    expect(roof.toArray()).toEqual([1, 0, 2 - 4.5]); // -z is up the screen
  });

  test("the drawn vertex keeps the art's screen point at every tilt and place, and its squeezed depth", () => {
    const band = { oblique: 1, lo: 0, hi: 0.04, zMin: 0, zMax: 4.5 };
    for (const tilt of [1e-7, 15, 32]) {
      const camera = new THREE.PerspectiveCamera(40, 264 / 184, 0.1, 500);
      const t = THREE.MathUtils.degToRad(tilt);
      camera.position.set(0, 20 * Math.cos(t), 20 * Math.sin(t));
      camera.lookAt(0, 0, 0);
      camera.updateMatrixWorld();
      for (const at of [new THREE.Vector3(-6, 0, -6), new THREE.Vector3(0, 0, 0), new THREE.Vector3(5, 2.1, 6)]) {
        const scale = 1 - at.y / camera.position.y; // D6: lifted along the ray, scaled
        const toWorld = new THREE.Matrix4().compose(at, new THREE.Quaternion(), new THREE.Vector3(scale, scale, scale));
        const p = new THREE.Vector3(0.5, 3, -0.4);
        const drawn = placeVertex(band, p, toWorld, camera.position);
        const art = rayPoint(band, p).applyMatrix4(toWorld);
        const a = screen(drawn, camera);
        const b = screen(art, camera);
        expect(a.x).toBeCloseTo(b.x, 6);
        expect(a.y).toBeCloseTo(b.y, 6);
        expect(drawn.y - at.y).toBeCloseTo(bandHeight(band, p.y) * scale, 6);
      }
    }
  });

  test("with the true perspective only the depth changes", () => {
    const camera = tiltedCamera();
    const band = { oblique: 0, lo: 0, hi: 0.04, zMin: 0, zMax: 4.5 };
    const toWorld = new THREE.Matrix4().makeTranslation(-3, 0, -4);
    const p = new THREE.Vector3(1, 4, 0.5);
    const drawn = placeVertex(band, p, toWorld, camera.position);
    const a = screen(drawn, camera);
    const b = screen(p.clone().applyMatrix4(toWorld), camera);
    expect(a.x).toBeCloseTo(b.x, 6);
    expect(a.y).toBeCloseTo(b.y, 6);
    expect(drawn.y).toBeCloseTo(bandHeight(band, 4), 6);
    // Squeezed, it stays under ground enemies (0.45) and background 2's under pass (0.05).
    expect(drawn.y).toBeLessThan(0.05);
  });
});
