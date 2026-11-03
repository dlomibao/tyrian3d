// [proposal: damage frames] Damage drawn on an intact model by its materials' shaders (?damage=a|b).
//
// Every material of a model clone gets the same small patch (one shader program per material kind,
// so no extra compiles per enemy). Its uniforms say where the damage is, in the sprite's own pixels:
// each fragment is projected straight down onto the sprite (model-root x, z times PX_PER_UNIT, from
// the sprite's centre), so the damage lands where the damaged sprite shows it, whatever the model's
// shape. Off (uDmgOn = 0) the patch changes nothing.
//
// - A (uDmgMode 0): two textures from the intact and damaged frames (damageFrames.ts). `mask`:
//   r = the pixel is gone (the fragment is cut away, with a charred, glowing rim), g = how much darker
//   it got (scorch), b = it turned hot (embers glow), a = how much of its colour to take from the
//   damaged sprite. `color`: per pixel the tint from the intact frame's colour to the damaged one's
//   (halved), bilinear, so the recolour isn't blocky.
// - B (uDmgMode 1): no textures. uDmgParams = (scorch, holes, embers, seed): value noise in model
//   space darkens the surface and cuts holes with glowing rims, the same for every model.

import * as THREE from "three";
import { PX_PER_UNIT } from "../../game/playfield";

export interface DamageUniforms {
  uDmgOn: { value: number };
  uDmgMode: { value: number };
  uDmgInv: { value: THREE.Matrix4 };
  uDmgSize: { value: THREE.Vector2 };
  uDmgMask: { value: THREE.Texture | null };
  uDmgColor: { value: THREE.Texture | null };
  uDmgParams: { value: THREE.Vector4 };
}

export function damageUniforms(): DamageUniforms {
  return {
    uDmgOn: { value: 0 },
    uDmgMode: { value: 0 },
    uDmgInv: { value: new THREE.Matrix4() },
    uDmgSize: { value: new THREE.Vector2(24, 28) },
    uDmgMask: { value: null },
    uDmgColor: { value: null },
    uDmgParams: { value: new THREE.Vector4() },
  };
}

const VERTEX_PARS = /* glsl */ `
uniform mat4 uDmgInv;
varying vec3 vDmgPos;
`;
const VERTEX = /* glsl */ `
vDmgPos = (uDmgInv * modelMatrix * vec4(transformed, 1.0)).xyz;
`;

const FRAGMENT_PARS = /* glsl */ `
uniform float uDmgOn;
uniform float uDmgMode;
uniform vec2 uDmgSize;
uniform sampler2D uDmgMask;
uniform sampler2D uDmgColor;
uniform vec4 uDmgParams;
varying vec3 vDmgPos;
float dmgHash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float dmgNoise(vec3 x) {
  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(dmgHash(i), dmgHash(i + vec3(1, 0, 0)), f.x), mix(dmgHash(i + vec3(0, 1, 0)), dmgHash(i + vec3(1, 1, 0)), f.x), f.y),
             mix(mix(dmgHash(i + vec3(0, 0, 1)), dmgHash(i + vec3(1, 0, 1)), f.x), mix(dmgHash(i + vec3(0, 1, 1)), dmgHash(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}
float dmgFbm(vec3 p) { return 0.55 * dmgNoise(p) + 0.3 * dmgNoise(p * 2.03 + 7.1) + 0.15 * dmgNoise(p * 4.1 + 3.3); }
vec3 dmgEmber = vec3(0.0);
// How much of the material's own glow is left, and (A) the colour it takes from the damaged sprite.
float dmgKeep = 1.0;
float dmgTake = 0.0;
vec3 dmgDc = vec3(1.0);
`;

// After map_fragment: diffuseColor is the palette colour times the baked map (D65).
const FRAGMENT_COLOUR = /* glsl */ `
if (uDmgOn > 0.5) {
  vec2 px = vec2(vDmgPos.x * ${PX_PER_UNIT.toFixed(1)} + uDmgSize.x * 0.5, vDmgPos.z * ${PX_PER_UNIT.toFixed(1)} + uDmgSize.y * 0.5);
  vec2 uv = px / uDmgSize;
  if (uDmgMode < 0.5) {
    // Past the sprite's box: as its edge pixels (ClampToEdge), as a model's overhang goes with them.
    {
      vec4 m = texture2D(uDmgMask, uv);
      if (m.r > 0.5) discard;
      float rim = smoothstep(0.12, 0.5, m.r);
      vec3 dc = texture2D(uDmgColor, uv).rgb * 2.0;
      diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * dc, m.a);
      diffuseColor.rgb *= 1.0 - 0.9 * m.g;
      diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.03, 0.025, 0.02), rim);
      dmgKeep = (1.0 - 0.9 * m.g) * (1.0 - rim);
      dmgTake = m.a;
      dmgDc = dc;
      dmgEmber = vec3(1.0, 0.3, 0.05) * m.b * 1.2 + vec3(1.0, 0.35, 0.06) * rim * (1.0 - rim) * 3.0;
    }
  } else {
    vec3 q = vDmgPos * 3.2 + uDmgParams.w;
    float n = dmgFbm(q);
    float hole = smoothstep(1.0 - uDmgParams.y, 1.0 - uDmgParams.y + 0.06, n);
    if (uDmgParams.y > 0.0 && n > 1.0 - uDmgParams.y + 0.06) discard;
    float scorch = smoothstep(0.62 - uDmgParams.x * 0.5, 0.78 - uDmgParams.x * 0.4, dmgFbm(q * 1.7 + 11.0)) * uDmgParams.x;
    diffuseColor.rgb *= 1.0 - 0.85 * max(scorch, hole);
    dmgKeep = 1.0 - 0.85 * max(scorch, hole);
    float ember = smoothstep(0.75, 0.95, dmgNoise(q * 5.0 + 2.0)) * scorch * uDmgParams.z;
    dmgEmber = vec3(1.0, 0.32, 0.05) * (ember * 1.5 + hole * (1.0 - hole) * 4.0 * step(0.001, uDmgParams.y));
  }
  // Seen through a cut: the inside of the hull, charred (the material is two-sided while cut).
  if (!gl_FrontFacing) {
    diffuseColor.rgb = vec3(0.035, 0.03, 0.025);
    dmgKeep = 0.0;
    dmgEmber = vec3(0.12, 0.03, 0.0);
  }
}
`;

// Glowing parts (glass, lights) take the damage too: their glow recoloured like the surface (A) and
// dimmed where scorched.
const FRAGMENT_EMISSIVE = /* glsl */ `
if (uDmgOn > 0.5) {
  totalEmissiveRadiance = mix(totalEmissiveRadiance, totalEmissiveRadiance * dmgDc * dmgDc, dmgTake) * dmgKeep * dmgKeep + dmgEmber;
}
`;

/**
 * Patch `material` (a clone's own) to draw damage from `uniforms`. Idempotent. Materials that
 * aren't lit standard materials (the outline shell, the depth prepass) are left alone.
 */
export function patchDamage(material: THREE.Material, uniforms: DamageUniforms): boolean {
  const std = material as THREE.MeshStandardMaterial;
  if (!std.isMeshStandardMaterial || material.userData.damagePatched) return false;
  material.userData.damagePatched = true;
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${VERTEX_PARS}`)
      .replace("#include <project_vertex>", `#include <project_vertex>\n${VERTEX}`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${FRAGMENT_PARS}`)
      .replace("#include <map_fragment>", `#include <map_fragment>\n${FRAGMENT_COLOUR}`)
      .replace("#include <emissivemap_fragment>", `#include <emissivemap_fragment>\n${FRAGMENT_EMISSIVE}`);
  };
  material.customProgramCacheKey = () => "tyrian-damage-1";
  material.needsUpdate = true;
  return true;
}
