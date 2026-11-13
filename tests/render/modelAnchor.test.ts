// D181: a glb's `tyrian_anchor` extra moves the plane placeModel puts on the camera ray (D6) up from the
// model's base; models without it, and models drawn in the art's view (D165), keep their base.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";

vi.stubGlobal("location", { search: "" });
const { sourceAnchor } = await import("../../src/render/drawListRenderer");

function model(extras: Record<string, unknown> | null): THREE.Object3D {
  const root = new THREE.Group();
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2.6, 2), new THREE.MeshBasicMaterial());
  mesh.position.y = 1.1;
  if (extras) mesh.userData = { ...extras };
  root.add(mesh);
  return root;
}

describe("model anchor", () => {
  test("no extra: the base", () => {
    expect(sourceAnchor(model(null))).toBe(0);
  });
  test("the extra's height, from any node", () => {
    expect(sourceAnchor(model({ tyrian_anchor: 2 }))).toBe(2);
  });
  test("a model drawn in the art's view keeps its base", () => {
    expect(sourceAnchor(model({ tyrian_anchor: 2, tyrian_oblique: [0.97, 0.26, 0.4], tyrian_depth_band: [0, 0.4] }))).toBe(0);
  });
  test("a malformed extra is ignored", () => {
    expect(sourceAnchor(model({ tyrian_anchor: "high" }))).toBe(0);
  });
});
