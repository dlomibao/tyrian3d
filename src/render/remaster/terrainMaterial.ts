// Draws HD terrain tiles (terrainArt.ts, DECISIONS.md D57): the renderer's flat ground quads (one
// instanced draw per atlas and kind), each instance picking its tile by the rect's origin in atlas
// texels (`instTile`). Three kinds:
// - "ground" (background 1): opaque, lit, with a little relief from the painting's brightness like
//   the 4x ground (D34), receiving shadows;
// - "blend" (draw_background_2_blend: TYRIAN's ice clouds, D45): translucent sheets at
//   BLEND_ALPHA times the art's coverage, no depth write;
// - "cutout" (background 3's islands and an opaque background 2 without models): the art's alpha
//   cut at one half, writing depth and casting island-shaped shadows (a depth material that cuts the
//   same way).
//
// Seam-free sampling: the texel position is clamped half a texel of the coarser mip level inside
// the tile's rect (clampTerrainTexel), and the level chosen here (textureLod) is at most
// TERRAIN_MAX_LOD, where the 16-aligned rects never share a texel. So each cell shows only its own
// tile, its edge texels right at the edge, whatever is beside it in the atlas or on the map.
//
// Palette effects work on the painting's brightness, as for the flat sprite art (D42): the
// smoothies' hues (D31) recolour each texel with the palette entry of the hue at the shade its
// brightness gives (water_filter's ripple mark included), and JE_filterScreen's level hue and
// brightness recolour or scale it. Each texel's bank is the one of the raw palette's nearest
// colour (PaletteTexture.indexLut), so water_filter leaves alone what the original's
// (index & 0x30) == 0 banks drew (greys, cloud blue, and whatever else a palette keeps there, like
// LAVA EXIT's salmon pink: D95, D111); untouched texels keep their painted colour. What can't reach
// the art: palette animation and swaps (its colours aren't palette indices).

import * as THREE from "three";
import { WATER_ALPHA } from "../paletteMaterial";
import { PALETTE_LUT_SIZE, type PaletteTexture } from "../paletteTexture";
import { SCREEN_HUE_PARS } from "../screenHue";
import { TERRAIN_MAX_LOD } from "./terrainArt";

export type TerrainKind = "ground" | "blend" | "cutout";

export interface TerrainMaterialOptions {
  kind: TerrainKind;
  /** Atlas texels per original pixel (the manifest's scale). */
  scale: number;
  /** Opacity of "blend" sheets (the renderer's BLEND_ALPHA). */
  blend?: number;
  /** How strongly brightness changes tilt the ground's normal (0 = flat). */
  relief?: number;
}

export const TERRAIN_RELIEF = 1.2;
/** The cutout kinds' alpha threshold. */
const CUT = 0.5;

const L = PALETTE_LUT_SIZE;
const LEVEL_PARS = /* glsl */ `
uniform float levelFilter;     // JE_filterScreen's hue, or -99
uniform float levelBrightness; // and its brightness (0 or -99: none)
uniform sampler2D paletteLut;  // PaletteTexture.indexLut: sRGB cube cell -> nearest raw index
${SCREEN_HUE_PARS}
float terrainClampValue(float v) {
  return v < 0.0 ? 0.0 : (v > 15.0 ? (v >= 31.0 ? 0.0 : 15.0) : v);
}
// The bank (index & 0xf0) of the raw palette's nearest colour to a linear RGB colour.
float terrainBank(vec3 rgb) {
  rgb = clamp(rgb, 0.0, 1.0);
  vec3 s = mix(1.055 * pow(rgb, vec3(1.0 / 2.4)) - 0.055, rgb * 12.92, step(rgb, vec3(0.0031308)));
  ivec3 c = clamp(ivec3(s * ${L}.0), 0, ${L - 1});
  float index = floor(texelFetch(paletteLut, ivec2(c.r + ${L} * (c.b & 7), c.g + ${L} * (c.b >> 3)), 0).r * 255.0 + 0.5);
  return floor(index / 16.0) * 16.0;
}
// The palette effects on a painted colour (linear RGB), by the shade (0..15) its brightness gives.
vec3 terrainPalette(vec3 rgb, float height, inout float water) {
  float lum = pow(max(dot(rgb, vec3(0.2126, 0.7152, 0.0722)), 0.0), 1.0 / 2.2);
  float shade = clamp(floor(lum * 15.0 + 0.5), 0.0, 15.0);
  // The index's bank is the nearest palette colour's, so water_filter leaves alone what the
  // original's exempt banks drew (LAVA EXIT's pink, 0x40, stays pink: D111); near-grey paintings
  // always take the grey bank (0), which water_filter leaves alone as it does the original's grey
  // bricks (D95). Only the bank matters: the hue filters replace it, and untouched texels keep
  // their painted colour.
  float chroma = max(rgb.r, max(rgb.g, rgb.b)) - min(rgb.r, min(rgb.g, rgb.b));
  float index = (chroma < 0.04 ? 0.0 : terrainBank(rgb)) + shade;
  float hued = screenHueIndex(index, height, water);
  if (hued != index || levelFilter > -98.5) {
    // The palette texture already holds the level filter and brightness (paletteTexture.ts).
    return texture2D(paletteMap, vec2((hued + 0.5) / 256.0, 0.5)).rgb;
  }
  if (levelBrightness > -98.5 && levelBrightness != 0.0) {
    float s = lum * 15.0;
    float k = terrainClampValue(floor(s + 0.5) + levelBrightness) / max(s, 0.5);
    rgb *= pow(k, 2.2);
  }
  return rgb;
}
`;

/** GLSL shared by the colour and depth shaders: the clamped, level-limited atlas read. */
const SAMPLE_PARS = /* glsl */ `
uniform sampler2D terrainMap;
uniform vec2 rectSize;
varying vec2 vTileTexel;
varying vec2 vRectOrigin;
// The mip level for this pixel's footprint, at most ${TERRAIN_MAX_LOD}.0 (16-aligned rects).
float terrainLod() {
  vec2 dx = dFdx(vTileTexel), dy = dFdy(vTileTexel);
  return clamp(0.5 * log2(max(max(dot(dx, dx), dot(dy, dy)), 1e-8)), 0.0, ${TERRAIN_MAX_LOD}.0);
}
// Texel position t (atlas texels) read at mip level lod, never outside this tile's rect.
vec4 terrainSample(vec2 t, float lod) {
  float margin = 0.5 * exp2(ceil(lod));
  t = clamp(t, vRectOrigin + margin, vRectOrigin + rectSize - margin);
  return textureLod(terrainMap, t / vec2(textureSize(terrainMap, 0)), lod);
}
`;

const VERTEX_PARS = /* glsl */ `
attribute vec2 tileUvIn;
attribute vec2 instTile;
uniform vec2 rectSize;
varying vec2 vTileTexel;
varying vec2 vRectOrigin;
`;

const VERTEX_MAIN = /* glsl */ `
vTileTexel = instTile + tileUvIn * rectSize;
vRectOrigin = instTile;
`;

/** The uniforms one material reads; `terrainMap` is set per atlas. */
function uniformsFor(texture: THREE.Texture, scale: number) {
  return {
    terrainMap: { value: texture },
    rectSize: { value: new THREE.Vector2(24 * scale, 28 * scale) },
  };
}

/**
 * The material for one atlas and kind. `levelUniforms` (levelFilter, levelBrightness) are shared
 * and updated by the renderer each frame from the palette texture.
 */
export function terrainMaterial(
  palette: PaletteTexture,
  texture: THREE.Texture,
  levelUniforms: { levelFilter: { value: number }; levelBrightness: { value: number } },
  opts: TerrainMaterialOptions,
): THREE.MeshStandardMaterial {
  const { kind, scale } = opts;
  const blended = kind === "blend";
  const premultiplied = kind !== "ground";
  const material = new THREE.MeshStandardMaterial({
    roughness: 0.9,
    metalness: 0,
    envMapIntensity: 0.25,
    transparent: blended,
    depthWrite: !blended,
    userData: { outlineParameters: { visible: false } },
  });
  const uniforms = {
    ...uniformsFor(texture, scale),
    paletteMap: { value: palette.texture },
    paletteLut: { value: palette.indexLut },
    relief: { value: kind === "ground" ? (opts.relief ?? TERRAIN_RELIEF) : 0 },
    // Relief is measured over a quarter of an original pixel either side, as the 4x ground's is.
    reliefStep: { value: Math.max(1, scale / 4) },
    ...levelUniforms,
  };
  material.userData.terrainUniforms = uniforms;
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms, palette.screenHue.uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${VERTEX_PARS}\nvarying float vPassY;`)
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>\n${VERTEX_MAIN}\nvPassY = 0.0;\n#ifdef USE_INSTANCING\nvPassY = instanceMatrix[3][1];\n#endif`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        /* glsl */ `#include <common>
uniform sampler2D paletteMap;
uniform float relief;
uniform float reliefStep;
varying float vPassY;
float vScreenWater = 0.0;
${SAMPLE_PARS}
${LEVEL_PARS}
float terrainLuma(vec2 t, float lod) {
  vec4 c = terrainSample(t, lod);
  return dot(c.rgb, vec3(0.299, 0.587, 0.114));
}`,
      )
      .replace(
        "#include <color_fragment>",
        /* glsl */ `
float lod = terrainLod();
vec4 tex = terrainSample(vTileTexel, lod);
float cover = tex.a;
vec3 painted = ${premultiplied ? "tex.rgb / max(cover, 1e-4)" : "tex.rgb"};
${kind === "cutout" ? `if (cover < ${CUT.toFixed(2)}) discard;` : ""}
${blended ? `if (cover < 0.004) discard;\ndiffuseColor.a = ${(opts.blend ?? 0.55).toFixed(3)} * cover;` : ""}
diffuseColor.rgb *= terrainPalette(painted, vPassY, vScreenWater);
vec2 reliefSlope = vec2(0.0);
if (relief > 0.0) {
  float d = max(reliefStep, exp2(lod));
  reliefSlope = relief * 0.5 * vec2(
    terrainLuma(vTileTexel + vec2(d, 0.0), lod) - terrainLuma(vTileTexel - vec2(d, 0.0), lod),
    terrainLuma(vTileTexel + vec2(0.0, d), lod) - terrainLuma(vTileTexel - vec2(0.0, d), lod));
}`,
      )
      .replace(
        "#include <normal_fragment_maps>",
        /* glsl */ `#include <normal_fragment_maps>
normal = normalize((viewMatrix * vec4(normalize(vec3(-reliefSlope.x, 1.0, -reliefSlope.y)), 0.0)).xyz);`,
      );
    if (kind === "ground") shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", WATER_ALPHA);
  };
  material.customProgramCacheKey = () => `terrain-hd-${kind}-${opts.blend ?? 0}`;
  return material;
}

/** The shadow pass's material for "cutout" tiles: only the art's opaque part casts a shadow. */
export function terrainDepthMaterial(texture: THREE.Texture, scale: number): THREE.MeshDepthMaterial {
  const material = new THREE.MeshDepthMaterial();
  const uniforms = uniformsFor(texture, scale);
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${VERTEX_PARS}`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>\n${VERTEX_MAIN}`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${SAMPLE_PARS}`)
      .replace("#include <clipping_planes_fragment>", `#include <clipping_planes_fragment>\nif (terrainSample(vTileTexel, terrainLod()).a < ${CUT.toFixed(2)}) discard;`);
  };
  material.customProgramCacheKey = () => "terrain-hd-depth";
  return material;
}

/** Texture settings for an atlas: no flip (v runs down the image like the rects), mipmapped, sRGB. */
export function prepareTerrainTexture(texture: THREE.Texture, premultiply: boolean): void {
  texture.flipY = false;
  texture.premultiplyAlpha = premultiply;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.wrapS = texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.needsUpdate = true;
}
