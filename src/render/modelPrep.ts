// Getting a loaded model ready for the game's renderers (DECISIONS.md D51): its outline shell and
// the depth prepass that keeps it clean when it is drawn translucent.

import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** renderOrder of a translucent model (invulnerable ship), after the particles (1) and glows (2). */
export const BLENDED_MODEL_ORDER = 3;

/**
 * Get a loaded model ready for the game's renderers (DECISIONS.md D51):
 *
 * - **Outline shell.** A node with the extra `tyrian_outline: true` (common.outline_shell) is a
 *   smooth closed copy of the model for the ink outline only: it draws nothing itself (no colour,
 *   no depth, no shadow) but OutlineEffect outlines it, and the model's own materials are left out
 *   of the outline, whose inverted hull would break into whiskers along hard edges.
 * - **Depth prepass.** A depth-only mesh of the whole model (its frame-tagged parts left out),
 *   hidden until the model is drawn translucent (setModelBlended): then it draws just before the
 *   model, so only the outer surface shows through and not the layers inside.
 */
export function prepareModel(root: THREE.Object3D): THREE.Object3D {
  const shells: THREE.Mesh[] = [];
  const meshes: THREE.Mesh[] = [];
  root.updateMatrixWorld(true);
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (isOutlineShell(mesh)) shells.push(mesh);
    else if (!underFrameTag(mesh, root)) meshes.push(mesh);
  });
  for (const shell of shells) {
    shell.material = new THREE.MeshBasicMaterial({
      name: "outline_shell",
      colorWrite: false,
      depthWrite: false,
      userData: { outlineShell: true, outlineParameters: { visible: true } },
    });
    shell.castShadow = false;
    shell.receiveShadow = false;
  }
  if (shells.length > 0) {
    root.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh || isOutlineShell(mesh)) return;
      for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
        m.userData.outlineParameters = { ...(m.userData.outlineParameters ?? {}), visible: false };
      }
    });
  }
  if (meshes.length > 0) {
    const inverse = root.matrixWorld.clone().invert();
    const parts = meshes.map((mesh) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", mesh.geometry.getAttribute("position").clone());
      if (mesh.geometry.index) g.setIndex(mesh.geometry.index.clone());
      g.applyMatrix4(inverse.clone().multiply(mesh.matrixWorld));
      return g.index ? g.toNonIndexed() : g;
    });
    const merged = mergeGeometries(parts);
    for (const g of parts) g.dispose();
    if (merged) {
      const prepass = new THREE.Mesh(
        merged,
        new THREE.MeshBasicMaterial({
          name: "depth_prepass",
          colorWrite: false,
          depthWrite: true,
          transparent: true,
          userData: { depthPrepass: true, outlineParameters: { visible: false } },
        }),
      );
      prepass.name = "depth_prepass";
      prepass.userData.depthPrepass = true;
      prepass.visible = false;
      prepass.castShadow = false;
      prepass.receiveShadow = false;
      root.add(prepass);
    }
  }
  return root;
}

function isOutlineShell(o: THREE.Object3D): boolean {
  return o.userData?.tyrian_outline === true;
}

/** A mesh prepareModel added or set aside (outline shell, depth prepass): it casts no shadow. */
export function isModelHelper(o: THREE.Object3D): boolean {
  return isOutlineShell(o) || o.userData?.depthPrepass === true;
}

function underFrameTag(o: THREE.Object3D, root: THREE.Object3D): boolean {
  for (let p: THREE.Object3D | null = o; p && p !== root.parent; p = p.parent) {
    if (Array.isArray(p.userData?.tyrian_frames)) return true;
  }
  return false;
}

/**
 * Draw a prepared model (or a clone of one, with its own materials) translucent or opaque: the
 * depth prepass shows only while translucent, the model draws after the particles and glows (so
 * what lies under it shows through), and its outline is hidden (it would show through as a dark
 * husk). Other materials' transparency is the caller's.
 */
export function setModelBlended(root: THREE.Object3D, blended: boolean): void {
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (mesh.userData.depthPrepass) {
      mesh.visible = blended;
      mesh.renderOrder = BLENDED_MODEL_ORDER - 0.001;
    } else if (!isModelHelper(mesh)) {
      mesh.renderOrder = blended ? BLENDED_MODEL_ORDER : 0;
    }
  });
}
