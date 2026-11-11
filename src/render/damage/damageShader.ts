// An enemy's damaged frame drawn on its intact model by the model's shaders (DECISIONS.md D87).
//
// Every material of a model clone gets the same small patch (one shader program per material kind,
// shared by all enemies). Its uniforms say where the damage is, in the sprite's own pixels: each
// fragment is projected straight down onto the sprite (model-root x, z times PX_PER_UNIT, from the
// sprite's centre), so the damage lands where the damaged sprite shows it, whatever the model's shape.
// Off (uDmgOn = 0) the patch changes nothing. Three textures (damageFrames.ts) of the sprite's
// 24x28 or 12x14 pixels, upsampled 4x (the cut by a cubic, the rest by a slight blur, D128) and
// read bilinear, so nothing is blocky:
//
// - `mask`: r = the pixel is gone (the fragment is cut away, with a charred, glowing rim);
//   g = extra scorch where it got darker; b = it turned hot (embers glow); a = it changed colour.
// - `tint`: rgb = damaged / intact colour (halved, so up to 2x fits), a multiplier, so the model
//   keeps its own shading; a = how much to replace instead (a new colour no multiplier reaches,
//   like grey rock turning into a blue pool).
// - `paint`: the damaged sprite's colours, for that replacement.
//
// Seen from the side (Tilted, Steep) a top-down projection streaks down vertical faces, so paint
// and scorch fade on faces that don't look up (cuts and charred rims stay on every face). The cut
// is a vertical cookie-cutter: while anything is cut the materials are two-sided and draw their back
// faces as a charred inside, so a cut reads as a burnt-through wall rather than a hole into nothing.
// The ink outline (outlineEffect.js) and the shadow depth material use the same cut
// (DAMAGE_CUT_*), so cut parts lose their outline and their shadow with them.

import * as THREE from "three";
import { PX_PER_UNIT } from "../../game/playfield";

export interface DamageUniforms {
  uDmgOn: { value: number };
  uDmgInv: { value: THREE.Matrix4 };
  uDmgSize: { value: THREE.Vector2 };
  uDmgMask: { value: THREE.Texture | null };
  uDmgTint: { value: THREE.Texture | null };
  uDmgPaint: { value: THREE.Texture | null };
  /**
   * The player ship's wear (shipDamage.ts, D90): scorch coverage (0..1; < 0 = an enemy's damaged
   * frame, the textures above) and ember glow. In ship mode `mask` holds a scorch pattern (g: the
   * coverage each texel scorches at, b: where embers can glow), never a cut.
   */
  uDmgCover: { value: number };
  uDmgHot: { value: number };
  /**
   * World offset of the clone's shadow (D133): its shadow-map depth is drawn this far off, and its own
   * shadow lookups move with it, so it shades itself as before. Not part of the damage: these are the
   * clone's per-clone uniforms, which every model clone has.
   */
  uShadowShift: { value: THREE.Vector3 };
}

export function damageUniforms(): DamageUniforms {
  return {
    uDmgOn: { value: 0 },
    uDmgInv: { value: new THREE.Matrix4() },
    uDmgSize: { value: new THREE.Vector2(24, 28) },
    uDmgMask: { value: null },
    uDmgTint: { value: null },
    uDmgPaint: { value: null },
    uDmgCover: { value: -1 },
    uDmgHot: { value: 0 },
    uShadowShift: { value: new THREE.Vector3() },
  };
}

const PX = PX_PER_UNIT.toFixed(1);

/** Vertex declarations shared by the model, outline and depth materials. */
export const DAMAGE_CUT_VERTEX_PARS = /* glsl */ `
uniform mat4 uDmgInv;
varying vec3 vDmgPos;
`;
/** After `transformed` is set (begin_vertex and its morphs): the model-root position. */
export const DAMAGE_CUT_VERTEX = /* glsl */ `
vDmgPos = (uDmgInv * modelMatrix * vec4(transformed, 1.0)).xyz;
`;
export const DAMAGE_CUT_FRAGMENT_PARS = /* glsl */ `
uniform float uDmgOn;
uniform vec2 uDmgSize;
uniform sampler2D uDmgMask;
varying vec3 vDmgPos;
vec2 dmgUv() { return vec2(vDmgPos.x * ${PX} + uDmgSize.x * 0.5, vDmgPos.z * ${PX} + uDmgSize.y * 0.5) / uDmgSize; }
`;
/** Discards what the damaged frame cut away. Past the sprite's box, as its edge pixels (ClampToEdge). */
export const DAMAGE_CUT_FRAGMENT = /* glsl */ `
if (uDmgOn > 0.5 && texture2D(uDmgMask, dmgUv()).r > 0.5) discard;
`;

const VERTEX_PARS = /* glsl */ `${DAMAGE_CUT_VERTEX_PARS}
uniform vec3 uShadowShift;
varying float vDmgUp;
`;
/** The shadow lookup at the shifted position, so the clone's own shadow on itself lines up (D133). */
const SHADOW_VERTEX = /* glsl */ `
#ifdef USE_SHADOWMAP
worldPosition.xyz += uShadowShift;
#endif
#include <shadowmap_vertex>
#ifdef USE_SHADOWMAP
worldPosition.xyz -= uShadowShift;
#endif
`;
const VERTEX = /* glsl */ `${DAMAGE_CUT_VERTEX}
vDmgUp = normalize(mat3(uDmgInv) * (mat3(modelMatrix) * objectNormal)).y;
`;

const FRAGMENT_PARS = /* glsl */ `${DAMAGE_CUT_FRAGMENT_PARS}
uniform sampler2D uDmgTint;
uniform sampler2D uDmgPaint;
uniform float uDmgCover;
uniform float uDmgHot;
varying float vDmgUp;
vec3 dmgEmber = vec3(0.0);
// How much of the material's own glow is left, and the tint and replacement it takes.
float dmgKeep = 1.0;
vec3 dmgTintRgb = vec3(1.0);
float dmgTake = 0.0;
`;

// After map_fragment: diffuseColor is the palette colour times the baked map (D65).
const FRAGMENT_COLOUR = /* glsl */ `
if (uDmgOn > 0.5) {
  vec2 uv = dmgUv();
  vec4 m = texture2D(uDmgMask, uv);
  if (uDmgCover >= 0.0) {
    // The player ship's wear: scorch where the pattern is under the coverage, embers in the heavy.
    float s = 1.0 - smoothstep(uDmgCover - 0.08, uDmgCover, m.g);
    m = vec4(0.0, 0.85 * s, s * smoothstep(0.6, 0.9, m.b) * uDmgHot * 1.5, 0.0);
  }
  if (m.r > 0.5) discard;
  if (gl_FrontFacing) {
    // Faces that look up take the frame's paint; side faces less, so it doesn't streak down them.
    float up = mix(0.35, 1.0, smoothstep(0.25, 0.75, vDmgUp));
    float rim = smoothstep(0.12, 0.5, m.r);
    vec4 t = texture2D(uDmgTint, uv);
    vec3 tint = t.rgb * 2.0;
    vec3 paint = texture2D(uDmgPaint, uv).rgb;
    float lum0 = max(dot(diffuse, vec3(0.299, 0.587, 0.114)), 1e-3);
    float shade = clamp(dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114)) / lum0, 0.0, 1.6);
    vec3 changed = mix(diffuseColor.rgb * tint, paint * shade, t.a);
    float take = m.a * up;
    diffuseColor.rgb = mix(diffuseColor.rgb, changed, take);
    diffuseColor.rgb *= 1.0 - 0.9 * m.g * up;
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.03, 0.025, 0.02), rim);
    dmgKeep = (1.0 - 0.9 * m.g * up) * (1.0 - rim);
    dmgTintRgb = mix(tint * tint, vec3(dot(paint, vec3(0.333))), t.a);
    dmgTake = take;
    dmgEmber = vec3(1.0, 0.3, 0.05) * m.b * 1.2 * up + vec3(1.0, 0.35, 0.06) * rim * (1.0 - rim) * 3.0;
  } else {
    // The inside of the hull, seen through a cut: charred, faintly glowing.
    diffuseColor.rgb = vec3(0.035, 0.03, 0.025);
    dmgKeep = 0.0;
    dmgEmber = vec3(0.12, 0.03, 0.0);
  }
}
`;

// Glowing parts (glass, lights) take the damage too: dimmed and recoloured like the surface.
const FRAGMENT_EMISSIVE = /* glsl */ `
if (uDmgOn > 0.5) {
  totalEmissiveRadiance = mix(totalEmissiveRadiance, totalEmissiveRadiance * dmgTintRgb, dmgTake) * dmgKeep * dmgKeep + dmgEmber;
}
`;

/**
 * Patch `material` (a clone's own) to draw damage from `uniforms`; true if it was patched now. Lit
 * standard materials only (not the outline shell or the depth prepass). The uniforms are also left
 * in userData.damageUniforms for the outline pass (outlineEffect.js).
 *
 * A material with a shader patch of its own (the island rock's, rockMaterial.ts, D84) keeps it: the
 * damage goes in first and the material's own patch runs after it on the same source (the rock's
 * colour replaces `map_fragment`, and the damage colour follows it), and its program cache key is
 * kept as part of this one. Replacing it drew the rock's palette-data texture as colour (D88).
 */
export function patchDamage(material: THREE.Material, uniforms: DamageUniforms): boolean {
  const std = material as THREE.MeshStandardMaterial;
  if (!std.isMeshStandardMaterial || material.userData.damageUniforms) return false;
  material.userData.damageUniforms = uniforms;
  const own = material.onBeforeCompile;
  const ownKey = material.customProgramCacheKey.bind(material);
  material.onBeforeCompile = (shader, renderer) => {
    damageSource(shader, uniforms);
    own.call(material, shader, renderer);
  };
  material.customProgramCacheKey = () => `${ownKey()}|tyrian-damage-2`;
  material.needsUpdate = true;
  return true;
}

function damageSource(shader: THREE.WebGLProgramParametersWithUniforms, uniforms: DamageUniforms): void {
  Object.assign(shader.uniforms, uniforms);
  shader.vertexShader = shader.vertexShader
    .replace("#include <common>", `#include <common>\n${VERTEX_PARS}`)
    .replace("#include <project_vertex>", `#include <project_vertex>\n${VERTEX}`)
    .replace("#include <shadowmap_vertex>", SHADOW_VERTEX);
  shader.fragmentShader = shader.fragmentShader
    .replace("#include <common>", `#include <common>\n${FRAGMENT_PARS}`)
    .replace("#include <map_fragment>", `#include <map_fragment>\n${FRAGMENT_COLOUR}`)
    .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>\n${FRAGMENT_EMISSIVE}`);
}

/**
 * A shadow depth material that leaves out what the damage cut away (Mesh.customDepthMaterial), so cut
 * parts cast no shadow. One per clone mesh, sharing the clone's uniforms; uDmgOn = 0 is the plain one.
 */
export function damageDepthMaterial(uniforms: DamageUniforms): THREE.MeshDepthMaterial {
  const m = new THREE.MeshDepthMaterial(); // as WebGLShadowMap's own
  m.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${DAMAGE_CUT_VERTEX_PARS}\nuniform vec3 uShadowShift;`)
      // The shadow is drawn shifted (D133).
      .replace(
        "#include <project_vertex>",
        `#include <project_vertex>\n${DAMAGE_CUT_VERTEX}\ngl_Position = projectionMatrix * viewMatrix * (modelMatrix * vec4(transformed, 1.0) + vec4(uShadowShift, 0.0));`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${DAMAGE_CUT_FRAGMENT_PARS}`)
      .replace("void main() {", `void main() {\n${DAMAGE_CUT_FRAGMENT}`);
  };
  m.customProgramCacheKey = () => "tyrian-damage-depth-2";
  return m;
}
