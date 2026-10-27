// Draws the remastered backgrounds' structure models (DECISIONS.md D34) as instances: every copy of
// one model on screen is one draw per material, however many tiles use it (a rock island repeats
// a few tile models dozens of times). Enemy models are cloned instead (drawListRenderer.ts),
// because each copy can flash or turn translucent on its own; background tiles don't, so the
// copies of a model share its materials and palette colours.
//
// Each model's meshes are flattened into parts (geometry with the node transforms baked in, and a
// material), and each part gets an InstancedMesh that grows as needed.

import * as THREE from "three";
import { colourFrame, rigModel, type FrameRig } from "../modelFrames";

interface Part {
  mesh: THREE.InstancedMesh;
  capacity: number;
}

interface Model {
  parts: Part[];
  rig: FrameRig;
  count: number;
  /** PaletteTexture.version its colours were set for. */
  paletteVersion: number;
}

export class StructureInstances {
  readonly group = new THREE.Group();
  private readonly models = new Map<string, Model>();
  private readonly matrix = new THREE.Matrix4();
  private readonly position = new THREE.Vector3();
  private readonly scale = new THREE.Vector3();
  private readonly rotation = new THREE.Quaternion();

  constructor() {
    this.group.name = "background-structures";
  }

  /** Whether a model has been added (loaded). */
  has(name: string): boolean {
    return this.models.has(name);
  }

  /** Add a loaded model (a glTF scene from assets/blender/tiles/). */
  add(name: string, source: THREE.Object3D): void {
    if (this.models.has(name)) return;
    source.updateMatrixWorld(true);
    const parts: Part[] = [];
    source.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const geometry = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
      // A multi-material mesh becomes one part per group.
      const groups = Array.isArray(mesh.material) && geometry.groups.length > 0 ? geometry.groups : [{ start: 0, count: Infinity, materialIndex: 0 }];
      for (const g of groups) {
        const material = materials[g.materialIndex ?? 0];
        material.userData.outlineParameters = { visible: false }; // tiles join edge to edge (D8)
        const part = groups.length > 1 ? subGeometry(geometry, g.start, g.count) : geometry;
        const im = new THREE.InstancedMesh(part, material, 4);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        im.frustumCulled = false;
        im.castShadow = true;
        im.receiveShadow = true;
        im.count = 0;
        this.group.add(im);
        parts.push({ mesh: im, capacity: 4 });
      }
    });
    this.models.set(name, { parts, rig: rigModel(source), count: 0, paletteVersion: -1 });
  }

  /** Start a frame: no instances. */
  begin(): void {
    for (const m of this.models.values()) m.count = 0;
  }

  /** One copy of a model with its origin at (x, y, z) and uniform scale. */
  place(name: string, x: number, y: number, z: number, scale: number): void {
    const model = this.models.get(name);
    if (!model) return;
    const slot = model.count++;
    this.position.set(x, y, z);
    this.scale.setScalar(scale);
    this.matrix.compose(this.position, this.rotation, this.scale);
    for (const part of model.parts) {
      if (slot >= part.capacity) grow(part, Math.max(slot + 1, part.capacity * 2));
      part.mesh.setMatrixAt(slot, this.matrix);
    }
  }

  /** Finish the frame: upload the instances and recolour models whose palette changed. */
  end(paletteVersion: number, color: (index: number, target: THREE.Color) => THREE.Color): void {
    for (const model of this.models.values()) {
      if (model.count > 0 && model.paletteVersion !== paletteVersion) {
        model.paletteVersion = paletteVersion;
        colourFrame(model.rig, -1, -1, color);
      }
      for (const part of model.parts) {
        part.mesh.count = model.count;
        part.mesh.visible = model.count > 0;
        if (model.count > 0) part.mesh.instanceMatrix.needsUpdate = true;
      }
    }
  }

  /** Models with copies this frame, and the draws they take. */
  stats(): { models: number; instances: number; parts: number } {
    let models = 0, instances = 0, parts = 0;
    for (const m of this.models.values()) {
      if (m.count === 0) continue;
      models++;
      instances += m.count;
      parts += m.parts.length;
    }
    return { models, instances, parts };
  }
}

function grow(part: Part, capacity: number): void {
  const old = part.mesh;
  const mesh = new THREE.InstancedMesh(old.geometry, old.material, capacity);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.instanceMatrix.array.set(old.instanceMatrix.array);
  mesh.frustumCulled = false;
  mesh.castShadow = old.castShadow;
  mesh.receiveShadow = old.receiveShadow;
  old.parent?.add(mesh);
  old.parent?.remove(old);
  old.dispose();
  part.mesh = mesh;
  part.capacity = capacity;
}

/** The triangles [start, start + count) of an indexed or non-indexed geometry, as a new geometry. */
function subGeometry(geometry: THREE.BufferGeometry, start: number, count: number): THREE.BufferGeometry {
  const sub = new THREE.BufferGeometry();
  for (const name of Object.keys(geometry.attributes)) sub.setAttribute(name, geometry.attributes[name]);
  if (geometry.index) {
    const end = Math.min(geometry.index.count, start + count);
    sub.setIndex(Array.from(geometry.index.array.slice(start, end)));
  } else {
    sub.setDrawRange(start, count);
  }
  return sub;
}
