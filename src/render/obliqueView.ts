// Tall things drawn the way the art draws them (DECISIONS.md D82's approach C; extended to sprite and
// enemy models by D165). The model is the real, upright object: the viewer, Blender and every other
// loader see it standing. The game draws it in the art's fixed view, per vertex, from two glTF extras:
//
// - `tyrian_oblique` puts each vertex on the camera ray through the point of the model's base plane
//   (its root's y = 0) that the art draws it at. -z is up the screen. It is either
//   - `k` (D82's tall buildings): a point at height y is drawn k px up the screen per px of height,
//     its plan unchanged: (x, z - k y);
//   - `[k, squeeze, axisZ]` (D165, an orthographic art camera from the south at elevation e: k = cos e,
//     squeeze = sin e): the plan is also squeezed toward the row axisZ, so a round rim is drawn as the
//     art's flat ellipse: (x, axisZ + squeeze (z - axisZ) - k y).
//   This is D6's lift, applied per vertex: the object lands where the art draws it at every tilt and
//   scroll position, while normals, light and shadows are the real object's.
// - `tyrian_depth_band: [lo, hi]` or `[lo, hi, y0, y1]` (model units above its base): each vertex
//   writes the depth of the point on its ray at its height mapped from [y0, y1] (default: the model's
//   own height range) into [lo, hi]. A tall thing stays under everything the original drew over it.
//   The pieces of one tall object cut into several sprites give the same [y0, y1], so their depths
//   agree where they meet.
//
// Structures (remaster/structureInstances.ts) are instanced, with their node transforms baked into
// their parts. Sprite and enemy models (drawListRenderer.ts) are clones with a node hierarchy: each
// mesh gets its own matrices to and from the model's root (prepareObliqueClone). Models without the
// extras are never patched, so they draw exactly as before.

import * as THREE from "three";
import { DAMAGE_CUT_VERTEX } from "./damage/damageShader";
import { isModelHelper } from "./modelPrep";

/** A model's depth band: its `tyrian_depth_band` and `tyrian_oblique` extras. */
export interface DepthBand {
  /** `tyrian_oblique`: px up the screen per px of height, or 0 for the true perspective. */
  oblique: number;
  /** The plan's squeeze toward `axisZ` (1, or absent: none; D82's buildings). */
  squeeze?: number;
  /** The row (model z) the plan is squeezed toward. */
  axisZ?: number;
  /** The band its depth is squeezed into, in model units above its base. */
  lo: number;
  hi: number;
  /** The model's height range (the extra's, or its geometry's bounds), which maps onto the band. */
  zMin: number;
  zMax: number;
}

/** The depth band a loaded model asks for, or null (also when it already fits in the band). */
export function depthBandOf(source: THREE.Object3D): DepthBand | null {
  let asked: unknown = null;
  let view: unknown = null;
  source.traverse((o) => {
    if (asked === null && Array.isArray(o.userData?.tyrian_depth_band)) asked = o.userData.tyrian_depth_band;
    if (view === null && o.userData?.tyrian_oblique !== undefined) view = o.userData.tyrian_oblique;
  });
  if (!Array.isArray(asked) || (asked.length !== 2 && asked.length !== 4)) return null;
  const [lo, hi, y0, y1] = asked.map(Number);
  if (!(Number.isFinite(lo) && Number.isFinite(hi) && hi > lo)) return null;
  let oblique = 0;
  let squeeze: number | undefined;
  let axisZ: number | undefined;
  if (Array.isArray(view)) {
    const [k, s, a] = view.map(Number);
    if (view.length === 3 && Number.isFinite(k) && k > 0 && Number.isFinite(s) && s > 0 && Number.isFinite(a)) {
      oblique = k;
      squeeze = s;
      axisZ = a;
    }
  } else if (Number.isFinite(Number(view))) oblique = Number(view);
  const range = asked.length === 4 && Number.isFinite(y0) && Number.isFinite(y1) && y1 > y0 ? { zMin: y0, zMax: y1 } : null;
  source.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(source);
  if (box.isEmpty() || (!oblique && box.min.y >= lo && box.max.y <= hi)) return null;
  const band: DepthBand = { oblique, lo, hi, zMin: range?.zMin ?? box.min.y, zMax: range?.zMax ?? box.max.y };
  if (squeeze !== undefined) Object.assign(band, { squeeze, axisZ });
  return band;
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
 * drawn on: its own place with the true perspective, or the art's view's (the shader's sum, for
 * tests). Three's -z is up the screen.
 */
export function rayPoint(band: DepthBand, p: THREE.Vector3): THREE.Vector3 {
  if (!band.oblique) return p.clone();
  const a = band.axisZ ?? 0;
  const z = band.squeeze === undefined || band.squeeze === 1 ? p.z : a + band.squeeze * (p.z - a);
  return new THREE.Vector3(p.x, 0, z - band.oblique * p.y);
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
 * The box a banded model is drawn in, in its root's frame: x and z where the art draws its vertices
 * (rayPoint), y its depth band; prepareModel's helpers left out. For the blended sheets' lift (D129),
 * which needs where it is drawn.
 */
export function drawnBox(source: THREE.Object3D, band: DepthBand): THREE.Box3 {
  const box = new THREE.Box3();
  source.updateMatrixWorld(true);
  const toRoot = source.matrixWorld.clone().invert();
  const p = new THREE.Vector3();
  source.traverse((o) => {
    const mesh = o as THREE.Mesh;
    const pos = mesh.isMesh && !isModelHelper(mesh) ? (mesh.geometry.getAttribute("position") as THREE.BufferAttribute | undefined) : undefined;
    if (!pos) return;
    const m = toRoot.clone().multiply(mesh.matrixWorld);
    for (let i = 0; i < pos.count; i++) box.expandByPoint(rayPoint(band, p.fromBufferAttribute(pos, i).applyMatrix4(m)));
  });
  if (box.isEmpty()) return box;
  box.min.y = band.lo;
  box.max.y = band.hi;
  return box;
}

/** A mesh's uniforms for the oblique view: the band, and its matrices to and from its model's root. */
export interface ObliqueUniforms {
  depthBand: { value: THREE.Vector4 };
  oblique: { value: number };
  /** The plan's squeeze and the row it squeezes toward (1, 0: none). */
  obliquePlan: { value: THREE.Vector2 };
  obliqueMeshToRoot: { value: THREE.Matrix4 };
  obliqueRootToMesh: { value: THREE.Matrix4 };
}

export function obliqueUniforms(band: DepthBand, meshToRoot = new THREE.Matrix4()): ObliqueUniforms {
  return {
    depthBand: { value: new THREE.Vector4(band.lo, band.hi, band.zMin, band.zMax) },
    oblique: { value: band.oblique },
    obliquePlan: { value: new THREE.Vector2(band.squeeze ?? 1, band.axisZ ?? 0) },
    obliqueMeshToRoot: { value: meshToRoot.clone() },
    obliqueRootToMesh: { value: meshToRoot.clone().invert() },
  };
}

/**
 * The GLSL that places the vertex at mesh point `p`: sets `placed` (world) on the camera ray through
 * the base-plane point the art draws it at (`obliqueArt`, root frame), at the height its depth band
 * gives it. Instanced (structures), the vertex is already in the root's frame (D82's code as it was).
 */
const place = (p: string) => /* glsl */ `
#ifdef USE_INSTANCING
  mat4 toWorld = modelMatrix * instanceMatrix;
  vec3 q = ${p};
#else
  mat4 toWorld = modelMatrix * obliqueRootToMesh;
  vec3 q = (obliqueMeshToRoot * vec4(${p}, 1.0)).xyz;
#endif
#ifdef OBLIQUE_SQUEEZE
  vec3 local = oblique > 0.0 ? vec3(q.x, 0.0, obliquePlan.y + obliquePlan.x * (q.z - obliquePlan.y) - oblique * q.y) : q;
#else
  vec3 local = oblique > 0.0 ? vec3(q.x, 0.0, q.z - oblique * q.y) : q;
#endif
  obliqueArt = local;
  vec3 ray = (toWorld * vec4(local, 1.0)).xyz;
  vec3 base = (toWorld * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
  float scale = length((toWorld * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
  float t = clamp((q.y - depthBand.z) / max(1e-4, depthBand.w - depthBand.z), 0.0, 1.0);
  float squeezed = base.y + (depthBand.x + t * (depthBand.y - depthBand.x)) * scale;
#ifdef OBLIQUE_SINK
  squeezed -= OBLIQUE_SINK * (depthBand.y - depthBand.x) * scale;
#endif
  float k = (cameraPosition.y - squeezed) / max(1e-4, cameraPosition.y - ray.y);
  vec4 placed = vec4(cameraPosition + (ray - cameraPosition) * k, 1.0);`;

const VERTEX_PARS = /* glsl */ `
uniform vec4 depthBand;
uniform float oblique;
uniform vec2 obliquePlan;
#ifndef USE_INSTANCING
uniform mat4 obliqueMeshToRoot;
uniform mat4 obliqueRootToMesh;
#endif
// The art's point of the vertex, in its model root's frame (the base-plane point it is drawn on).
vec3 obliqueArt = vec3(0.0);
// Where a mesh point p is drawn (world). Sets obliqueArt.
vec4 obliquePlaced(vec3 p) {${place("p")}
  return placed;
}
`;

const VERTEX = /* glsl */ `#include <project_vertex>
{${place("transformed")}
  vec4 clip = projectionMatrix * viewMatrix * placed;
  if (oblique > 0.0) {
    mvPosition = viewMatrix * placed;
    gl_Position = clip;
  } else {
    gl_Position.z = clip.z / clip.w * gl_Position.w;
  }
}`;

/** The damage's projection onto the sprite (D87) from where the art draws a vertex, not from above it. */
const DAMAGE_CUT_VERTEX_OBLIQUE = /* glsl */ `
vDmgPos = oblique > 0.0 ? obliqueArt : (uDmgInv * modelMatrix * vec4(transformed, 1.0)).xyz;
`;

/** The ink outline (outlineEffect.js): its push along the normal, measured where the normal's tip is drawn. */
const OUTLINE_NORMAL = "vec4 pos2 = projectionMatrix * modelViewMatrix * vec4( skinned.xyz + normal, 1.0 );";
const OUTLINE_NORMAL_OBLIQUE =
  "vec4 pos2 = projectionMatrix * (oblique > 0.0 ? viewMatrix * obliquePlaced( skinned.xyz + normal ) : modelViewMatrix * vec4( skinned.xyz + normal, 1.0 ));";

/**
 * And its push keeps the vertex's depth: the outline pass pushes in clip space, depth too, by about
 * 0.05 units here, while the squeezed depth puts a tall model's far side only a few hundredths of a
 * unit behind its near side, so the far side's ink would show through.
 */
const OUTLINE_PUSH = "return pos + norm * thickness * pos.w * ratio;";
const OUTLINE_PUSH_OBLIQUE =
  "vec4 pushed = pos + norm * thickness * pos.w * ratio; if ( oblique > 0.0 ) pushed.z = pos.z / pos.w * pushed.w; return pushed;";

/**
 * The outline shell's ink sits this share of the depth band under the shell (outline pass only). The
 * band squeezes the true distances ten-fold or more, so where the shell's back faces line a hollow
 * of the model (a groove, under a rim) they lie a few depth-buffer steps from the model's surface
 * and its ink showed through it in blotches. Sunk, the ink stays round the silhouette only.
 */
export const OUTLINE_SINK = 0.05;

/**
 * A vertex shader drawn in the oblique view: a built-in material's (after any damage patch, D87), or
 * the outline pass's (outlineEffect.js, `outline`). Its uniforms are ObliqueUniforms.
 */
export function obliqueVertexSource(source: string, uniforms: ObliqueUniforms, outline = false): string {
  const squeeze = uniforms.obliquePlan.value.x !== 1 ? "#define OBLIQUE_SQUEEZE\n" : "";
  const sink = outline ? `#define OBLIQUE_SINK ${OUTLINE_SINK.toFixed(3)}\n` : "";
  return source
    .replace("#include <common>", `#include <common>\n${squeeze}${sink}${VERTEX_PARS}`)
    .replace("#include <project_vertex>", VERTEX)
    .replace(DAMAGE_CUT_VERTEX, DAMAGE_CUT_VERTEX_OBLIQUE)
    .replace(OUTLINE_NORMAL, OUTLINE_NORMAL_OBLIQUE)
    .replace(OUTLINE_PUSH, OUTLINE_PUSH_OBLIQUE);
}

/**
 * Draw `material` in the oblique view with `uniforms` (the shader's sums: rayPoint, bandHeight,
 * placeVertex). Normals, and so light, are the true geometry's, and so are shadows (the shadow pass
 * uses its own depth material). The uniforms are also left in userData.obliqueUniforms for the
 * outline pass (outlineEffect.js).
 */
export function patchOblique(material: THREE.Material, uniforms: ObliqueUniforms): void {
  if (material.userData.obliqueUniforms) return; // a material shared by several parts
  material.userData.obliqueUniforms = uniforms;
  const before = material.onBeforeCompile;
  material.onBeforeCompile = (shader, renderer) => {
    before.call(material, shader, renderer);
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = obliqueVertexSource(shader.vertexShader, uniforms);
  };
  const key = material.customProgramCacheKey.bind(material);
  const squeeze = uniforms.obliquePlan.value.x !== 1 ? "-squeeze" : "";
  material.customProgramCacheKey = () => `${key()}|depth-band${squeeze}`;
  material.needsUpdate = true;
}

/**
 * Patch a sprite or enemy model's clone (its own materials, drawListRenderer.ts cloneModel) to draw
 * in its oblique view: every mesh, the outline shell and the depth prepass too, with its own
 * matrices to and from the clone's root (its parts never move, D91).
 */
export function prepareObliqueClone(root: THREE.Object3D, band: DepthBand): void {
  root.updateMatrixWorld(true);
  const fromRoot = root.matrixWorld.clone().invert();
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const meshToRoot = fromRoot.clone().multiply(mesh.matrixWorld);
    for (const m of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) patchOblique(m, obliqueUniforms(band, meshToRoot));
  });
}
