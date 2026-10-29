// The remastered ground's material (DECISIONS.md D34): the 4x MMPX index atlas (groundAtlas.ts),
// coloured per fragment from the live palette like the original ground (D7), with two additions:
//
// - Filtering in colour, not index: the four nearest texels are each looked up in the palette and
//   blended, so the 4x pixels join smoothly while fades and filters still apply. `sharpness` above 1
//   narrows the blend toward each texel's edge (1 = plain bilinear).
// - Relief: the brightness of the blended texels is treated as height and tilts the normal, so the
//   painted rocks, ridges and foliage catch the light. Instances have no rotation, so the tile's u
//   and v run along world X and Z.
//
// With `blend` (an opacity) it draws the C's blended background-2 tiles (draw_background_2_blend,
// TYRIAN's ice clouds) from the same atlas as flat translucent sheets: index 0 is see-through, and
// the four texels are blended weighted by coverage, so the upscaled outline comes out smooth.

import * as THREE from "three";
import { WATER_ALPHA } from "../paletteMaterial";
import type { PaletteTexture } from "../paletteTexture";
import { SCREEN_HUE_PARS } from "../screenHue";
import type { RemasterGroundAtlas } from "./groundAtlas";

export interface RemasterGroundOptions {
  /** How strongly brightness changes tilt the normal (0 = flat). */
  relief: number;
  /** 1 = bilinear between texels; higher keeps more of the pixels' edges. */
  sharpness: number;
}

export const REMASTER_GROUND_DEFAULTS: RemasterGroundOptions = { relief: 2.2, sharpness: 1.6 };

export function remasterGroundMaterial(
  palette: PaletteTexture,
  atlas: RemasterGroundAtlas,
  options: RemasterGroundOptions = REMASTER_GROUND_DEFAULTS,
  blend?: number,
): THREE.MeshStandardMaterial {
  const blended = blend !== undefined;
  const material = new THREE.MeshStandardMaterial({
    roughness: 0.9,
    metalness: 0,
    envMapIntensity: 0.25,
    transparent: blended,
    depthWrite: !blended,
    userData: { outlineParameters: { visible: false } },
  });
  const uniforms = {
    paletteMap: { value: palette.texture },
    atlasMap: { value: atlas.texture },
    tileUv: { value: atlas.tileUv },
    relief: { value: options.relief },
    sharpness: { value: options.sharpness },
  };
  material.userData.remasterUniforms = uniforms;
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    // [filters] The smoothies' hue (D31) applies to the remastered ground too: it's background 1,
    // under every filter (height 0), and water_filter's pixels are marked for its ripple.
    Object.assign(shader.uniforms, palette.screenHue.uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nattribute vec2 tileUvIn;\nattribute vec2 instTile;\nuniform vec2 tileUv;\nvarying vec2 vAtlasUv;\nvarying float vPassY;")
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvAtlasUv = instTile + tileUvIn * tileUv;\nvPassY = 0.0;\n#ifdef USE_INSTANCING\nvPassY = instanceMatrix[3][1];\n#endif",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        /* glsl */ `#include <common>
uniform sampler2D atlasMap;
uniform sampler2D paletteMap;
uniform float relief;
uniform float sharpness;
varying vec2 vAtlasUv;
varying float vPassY;
${SCREEN_HUE_PARS}
float vScreenWater = 0.0;
float texelCover = 1.0;
// The palette colour of an atlas texel at the instance's pass height (0 for the ground, under every
// smoothie). For blended sheets, texelCover is set to 0 for index 0 (see-through).
vec3 groundTexel(ivec2 p) {
  float index = floor(texelFetch(atlasMap, p, 0).r * 255.0 + 0.5);
  ${blended ? "texelCover = index < 0.5 ? 0.0 : 1.0;" : ""}
  index = screenHueIndex(index, vPassY, vScreenWater);
  return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb;
}`,
      )
      .replace(
        "#include <color_fragment>",
        /* glsl */ `
// Texel centres sit at +0.5; each slot has a one-texel border, so the four texels around any point
// of the tile are inside the slot.
vec2 tp = vAtlasUv * vec2(textureSize(atlasMap, 0)) - 0.5;
ivec2 t0 = ivec2(floor(tp));
vec2 f = clamp((fract(tp) - 0.5) * sharpness + 0.5, 0.0, 1.0);
vec3 c00 = groundTexel(t0);
float a00 = texelCover;
vec3 c10 = groundTexel(t0 + ivec2(1, 0));
float a10 = texelCover;
vec3 c01 = groundTexel(t0 + ivec2(0, 1));
float a01 = texelCover;
vec3 c11 = groundTexel(t0 + ivec2(1, 1));
float a11 = texelCover;
// Weights of the four texels; for blended sheets only covered texels lend their colour.
float w00 = (1.0 - f.x) * (1.0 - f.y) * a00, w10 = f.x * (1.0 - f.y) * a10;
float w01 = (1.0 - f.x) * f.y * a01, w11 = f.x * f.y * a11;
float cover = w00 + w10 + w01 + w11;
${blended ? `if (cover < 0.02) discard;\ndiffuseColor.a = ${blend.toFixed(3)} * smoothstep(0.02, 0.6, cover);` : ""}
vec3 mixed = (c00 * w00 + c10 * w10 + c01 * w01 + c11 * w11) / max(cover, 1e-4);
diffuseColor.rgb *= mixed;
const vec3 LUMA = vec3(0.299, 0.587, 0.114);
// A see-through texel takes the mixed brightness, so a sheet's outline adds no false relief.
float lm = dot(mixed, LUMA);
float l00 = a00 > 0.5 ? dot(c00, LUMA) : lm, l10 = a10 > 0.5 ? dot(c10, LUMA) : lm;
float l01 = a01 > 0.5 ? dot(c01, LUMA) : lm, l11 = a11 > 0.5 ? dot(c11, LUMA) : lm;
vec2 reliefSlope = relief * vec2(mix(l10 - l00, l11 - l01, f.y), mix(l01 - l00, l11 - l10, f.x));`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        /* glsl */ `#include <normal_fragment_maps>
normal = normalize((viewMatrix * vec4(normalize(vec3(-reliefSlope.x, 1.0, -reliefSlope.y)), 0.0)).xyz);`,
      );
    if (!blended) shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", WATER_ALPHA);
  };
  material.customProgramCacheKey = () => (blended ? `palette-ground-remaster-blend-${blend}` : "palette-ground-remaster");
  return material;
}
