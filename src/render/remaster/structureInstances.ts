// Draws the remastered backgrounds' structure models (DECISIONS.md D34) as instances: every copy of
// one model on screen is one draw per material, however many tiles use it (a rock island repeats
// a few tile models dozens of times). Enemy models are cloned instead (drawListRenderer.ts),
// because each copy can flash or turn translucent on its own; background tiles don't, so the
// copies of a model share its materials and palette colours.
//
// Each model's meshes are flattened into parts (geometry with the node transforms baked in, and a
// material), and each part gets an InstancedMesh that grows as needed. prepareModel's helpers (the
// depth prepass, an outline shell: isModelHelper) are left out and dropped: a tile is never drawn
// translucent, so the prepass has no use here, and tiles carry no outline (D8). As parts they drew
// and cast shadows (D142).
//
// A part tagged with a cell of the model's pattern (`tyrian_cell: [row, col]` and `tyrian_when`, glTF
// extras on its node, D139) is drawn per copy by whether a ground enemy covers that cell: "open" parts
// (the building's own light or turret, which the enemy's opaque sprite hid) only while it doesn't,
// "covered" parts (a plain lid over the spot) only while it does, as the original's sprite hid the
// tile under it (D86's rule, per cell).
//
// A tall structure (DECISIONS.md D82, docs/agents/TALL-BUILDINGS.md) is a true building, with
// vertical walls and its real height, drawn the way its tiles draw it:
// - `tyrian_oblique: k` (extra): each vertex goes on the camera ray through the point of its base
//   plane that the art's oblique view puts it at, `k` px up the screen per px of height (the
//   building's foot stays where it is). This is D6's lift, applied per vertex: the roof and the wall
//   land where the tiles paint them at every tilt and scroll position, while normals, light and
//   shadows are the real building's;
// - `tyrian_depth_band: [lo, hi]` (model units above its base): each vertex writes the depth of the
//   point on its ray at its height squeezed into that band, so a tall building still stays under
//   everything the original drew over its tiles (`depthBand`).

import * as THREE from "three";
import { colourFrame, rigModel, type FrameRig } from "../modelFrames";
import { isModelHelper } from "../modelPrep";
import { hasRockBands, ROCK_SIDES, rockBandSlot, rockCell } from "../rockMaterial";

interface Part {
  mesh: THREE.InstancedMesh;
  capacity: number;
  /** Copies placed this frame. */
  count: number;
  /** The pattern cell (row, col) a cover part belongs to, and when it's drawn (D139). */
  cell?: readonly [number, number];
  when?: CellWhen;
  /** An island rock tile's edge bands per copy (rockMaterial.ts, D84): which band each side draws. */
  bands?: THREE.InstancedBufferAttribute;
}

interface Model {
  parts: Part[];
  rig: FrameRig;
  count: number;
  /** PaletteTexture.version its colours were set for. */
  paletteVersion: number;
  /** [filters] The smoothie hue its colours were set for (-1: none), and the height it was placed at. */
  hue: number;
  height: number;
}

/** When a cell's cover part is drawn: while no ground enemy covers the cell, or while one does (D139). */
export type CellWhen = "open" | "covered";

/** A mesh's cover cell from its node's (or a parent's, up to `root`) glTF extras, if it's tagged (D139). */
export function cellTag(o: THREE.Object3D, root: THREE.Object3D): { cell: [number, number]; when: CellWhen } | null {
  for (let n: THREE.Object3D | null = o; n; n = n === root ? null : n.parent) {
    const cell = n.userData?.tyrian_cell;
    if (Array.isArray(cell) && cell.length === 2 && cell.every((v) => Number.isInteger(v))) {
      return { cell: [cell[0], cell[1]], when: n.userData.tyrian_when === "covered" ? "covered" : "open" };
    }
  }
  return null;
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
    const band = depthBandOf(source);
    const parts: Part[] = [];
    const helpers: THREE.Mesh[] = [];
    source.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      if (isModelHelper(mesh)) {
        helpers.push(mesh);
        return;
      }
      const tag = cellTag(mesh, source);
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const geometry = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
      // A multi-material mesh becomes one part per group.
      const groups = Array.isArray(mesh.material) && geometry.groups.length > 0 ? geometry.groups : [{ start: 0, count: Infinity, materialIndex: 0 }];
      for (const g of groups) {
        const material = materials[g.materialIndex ?? 0];
        material.userData.outlineParameters = { visible: false }; // tiles join edge to edge (D8)
        const part = groups.length > 1 ? subGeometry(geometry, g.start, g.count) : geometry;
        if (band) depthBand(material, band);
        let bands: THREE.InstancedBufferAttribute | undefined;
        if (hasRockBands(material)) {
          bands = new THREE.InstancedBufferAttribute(new Float32Array(4 * 4), 4);
          bands.setUsage(THREE.DynamicDrawUsage);
          part.setAttribute("rockBands", bands);
        }
        const im = new THREE.InstancedMesh(part, material, 4);
        im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        im.frustumCulled = false;
        im.castShadow = true;
        im.receiveShadow = true;
        im.count = 0;
        this.group.add(im);
        parts.push({ mesh: im, capacity: 4, count: 0, bands, cell: tag?.cell, when: tag?.when });
      }
    });
    // The source is this model's own load (loaders parse afresh), kept only for its frame rig.
    for (const h of helpers) {
      h.removeFromParent();
      h.geometry.dispose();
      for (const m of Array.isArray(h.material) ? h.material : [h.material]) m.dispose();
    }
    this.models.set(name, { parts, rig: rigModel(source), count: 0, paletteVersion: -1, hue: -1, height: 0 });
  }

  /** A loaded model's instanced meshes (none if it isn't loaded), to compile ahead of its first draw (D91). */
  meshes(name: string): THREE.InstancedMesh[] {
    return this.models.get(name)?.parts.map((p) => p.mesh) ?? [];
  }

  /** Start a frame: no instances. */
  begin(): void {
    for (const m of this.models.values()) {
      m.count = 0;
      for (const p of m.parts) p.count = 0;
    }
  }

  /**
   * One copy of a model with its origin at (x, y, z) and uniform scale. `neighbours(row, col)`: the
   * tiles on the map left of, right of, above and below that cell of the model's pattern (-1: none),
   * so the island rock of each cell draws the edge band made for each (D84). `covered(row, col)`:
   * whether a ground enemy covers that cell, for the model's cover parts (D139; none: no cell is).
   */
  place(
    name: string, x: number, y: number, z: number, scale: number,
    neighbours?: (row: number, col: number) => readonly number[], covered?: (row: number, col: number) => boolean,
  ): void {
    const model = this.models.get(name);
    if (!model) return;
    model.count++;
    model.height = y;
    this.position.set(x, y, z);
    this.scale.setScalar(scale);
    this.matrix.compose(this.position, this.rotation, this.scale);
    for (const part of model.parts) {
      if (part.cell && (covered?.(part.cell[0], part.cell[1]) ?? false) !== (part.when === "covered")) continue;
      const slot = part.count++;
      if (slot >= part.capacity) grow(part, Math.max(slot + 1, part.capacity * 2));
      part.mesh.setMatrixAt(slot, this.matrix);
      if (part.bands) {
        const material = part.mesh.material as THREE.Material;
        const [row, col] = rockCell(material);
        const nb = neighbours?.(row, col);
        for (let k = 0; k < 4; k++) {
          const tile = nb?.[k] ?? -1;
          part.bands.array[slot * 4 + k] = tile < 0 ? 0 : rockBandSlot(material, ROCK_SIDES[k], tile);
        }
      }
    }
  }

  /**
   * Finish the frame: upload the instances and recolour models whose palette changed, or whose
   * smoothie hue did (`hueAt`: the hue byte a model at that height takes, or -1; D31).
   */
  end(paletteVersion: number, color: (index: number, target: THREE.Color) => THREE.Color, hueAt: (height: number) => number = () => -1): void {
    for (const model of this.models.values()) {
      const hue = model.count > 0 ? hueAt(model.height) : model.hue;
      if (model.count > 0 && (model.paletteVersion !== paletteVersion || model.hue !== hue)) {
        model.paletteVersion = paletteVersion;
        model.hue = hue;
        colourFrame(model.rig, -1, hue, color);
      }
      for (const part of model.parts) {
        part.mesh.count = part.count;
        part.mesh.visible = part.count > 0;
        if (part.count > 0) {
          part.mesh.instanceMatrix.needsUpdate = true;
          if (part.bands) part.bands.needsUpdate = true;
        }
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

/** A model's depth band: its `tyrian_depth_band` extra, and the height range it squeezes. */
export interface DepthBand {
  /** `tyrian_oblique`: px up the screen per px of height, or 0 for the true perspective. */
  oblique: number;
  /** The band its depth is squeezed into, in model units above its base. */
  lo: number;
  hi: number;
  /** The model's own height range (its geometry's bounds), which maps onto the band. */
  zMin: number;
  zMax: number;
}

/** The depth band a loaded structure asks for, or null (also when it already fits in the band). */
export function depthBandOf(source: THREE.Object3D): DepthBand | null {
  let asked: unknown = null;
  let oblique = 0;
  source.traverse((o) => {
    if (asked === null && Array.isArray(o.userData?.tyrian_depth_band)) asked = o.userData.tyrian_depth_band;
    if (!oblique && Number.isFinite(Number(o.userData?.tyrian_oblique))) oblique = Number(o.userData.tyrian_oblique);
  });
  if (!Array.isArray(asked) || asked.length !== 2) return null;
  const [lo, hi] = asked.map(Number);
  if (!(Number.isFinite(lo) && Number.isFinite(hi) && hi > lo)) return null;
  source.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(source);
  if (box.isEmpty() || (!oblique && box.min.y >= lo && box.max.y <= hi)) return null;
  return { oblique, lo, hi, zMin: box.min.y, zMax: box.max.y };
}

/**
 * The height on its camera ray whose depth a vertex at model height `z` writes: the band's
 * linear map of the model's range (the shader's sum, for tests).
 */
export function bandHeight(band: DepthBand, z: number): number {
  const t = (Math.min(Math.max(z, band.zMin), band.zMax) - band.zMin) / Math.max(1e-4, band.zMax - band.zMin);
  return band.lo + t * (band.hi - band.lo);
}

/**
 * The point of a model's base plane (model coordinates, y = 0) whose camera ray a vertex at `p` is
 * drawn on: its own place with the true perspective, or the art's oblique view's (the shader's sum,
 * for tests). Three's -z is up the screen.
 */
export function rayPoint(band: DepthBand, p: THREE.Vector3): THREE.Vector3 {
  return band.oblique ? new THREE.Vector3(p.x, 0, p.z - band.oblique * p.y) : p.clone();
}

/**
 * Where the shader puts a vertex at model point `p` of a copy placed by `toWorld`, seen from a camera
 * at `camera` (world): on the camera ray through rayPoint, at its band height. Its screen point is
 * rayPoint's; its depth is the squeezed copy's (the shader's sum, for tests).
 */
export function placeVertex(band: DepthBand, p: THREE.Vector3, toWorld: THREE.Matrix4, camera: THREE.Vector3): THREE.Vector3 {
  const ray = rayPoint(band, p).applyMatrix4(toWorld);
  const base = new THREE.Vector3().applyMatrix4(toWorld);
  const scale = new THREE.Vector3().setFromMatrixScale(toWorld).y;
  const squeezed = base.y + bandHeight(band, p.y) * scale;
  const k = (camera.y - squeezed) / Math.max(1e-4, camera.y - ray.y);
  return camera.clone().add(ray.sub(camera).multiplyScalar(k));
}

/**
 * Draw `material` on the camera rays rayPoint picks, with the depth of a squeezed copy: each
 * vertex's depth is that of the point on its ray at its band height (bandHeight). Normals, and so
 * light, are the true geometry's, and so are shadows (the shadow pass uses its own depth material).
 */
function depthBand(material: THREE.Material, band: DepthBand): void {
  if (material.userData.depthBand) return; // a material shared by several parts
  material.userData.depthBand = band;
  const before = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    before.call(material, shader, renderer);
    shader.uniforms.depthBand = { value: new THREE.Vector4(band.lo, band.hi, band.zMin, band.zMax) };
    shader.uniforms.oblique = { value: band.oblique };
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform vec4 depthBand;\nuniform float oblique;")
      .replace("#include <project_vertex>", DEPTH_BAND_VERTEX);
  };
  const key = material.customProgramCacheKey.bind(material);
  material.customProgramCacheKey = () => `${key()}|depth-band`;
  material.needsUpdate = true;
}

const DEPTH_BAND_VERTEX = `#include <project_vertex>
#ifdef USE_INSTANCING
{
  mat4 toWorld = modelMatrix * instanceMatrix;
  vec3 local = oblique > 0.0 ? vec3(transformed.x, 0.0, transformed.z - oblique * transformed.y) : transformed;
  vec3 ray = (toWorld * vec4(local, 1.0)).xyz;
  vec3 base = (toWorld * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  float scale = length((toWorld * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
  float t = clamp((transformed.y - depthBand.z) / max(1e-4, depthBand.w - depthBand.z), 0.0, 1.0);
  float squeezed = base.y + (depthBand.x + t * (depthBand.y - depthBand.x)) * scale;
  float k = (cameraPosition.y - squeezed) / max(1e-4, cameraPosition.y - ray.y);
  vec4 placed = vec4(cameraPosition + (ray - cameraPosition) * k, 1.0);
  vec4 clip = projectionMatrix * viewMatrix * placed;
  if (oblique > 0.0) {
    mvPosition = viewMatrix * placed;
    gl_Position = clip;
  } else {
    gl_Position.z = clip.z / clip.w * gl_Position.w;
  }
}
#endif`;

function grow(part: Part, capacity: number): void {
  const old = part.mesh;
  const mesh = new THREE.InstancedMesh(old.geometry, old.material, capacity);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.instanceMatrix.array.set(old.instanceMatrix.array);
  mesh.frustumCulled = false;
  mesh.castShadow = old.castShadow;
  mesh.receiveShadow = old.receiveShadow;
  if (part.bands) {
    const bands = new THREE.InstancedBufferAttribute(new Float32Array(capacity * 4), 4);
    bands.setUsage(THREE.DynamicDrawUsage);
    bands.array.set(part.bands.array);
    old.geometry.setAttribute("rockBands", bands);
    part.bands = bands;
  }
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
