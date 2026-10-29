// Materials that colour geometry by palette index (DECISIONS.md D7).
//
// Sprite meshes carry a `palIndex` per vertex. Each instance carries `instFx` = (mode, a, b, alpha)
// and the vertex shader applies the C blit's index arithmetic before the palette lookup:
//   mode 0  none                        index
//   mode 1  filter (blit_sprite2_filter) (a << 4) | (index & 15)     — a = filter >> 4
//   mode 2  hue/value (blit_sprite_hv)   (a << 4) | clampValue((index & 15) + b)
//   mode 3  solid colour (pixels, rects) a
// Ground tiles sample a palette-index atlas per fragment instead.

import * as THREE from "three";
import type { PaletteTexture } from "./paletteTexture";
import type { TileAtlas } from "./tileAtlas";
import { SCREEN_HUE_PARS } from "./screenHue";

export const enum FxMode {
  None = 0,
  Filter = 1,
  HueValue = 2,
  Solid = 3,
}

const PALETTE_LOOKUP = /* glsl */ `
uniform sampler2D paletteMap;
vec3 paletteColor(float index) {
  return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb;
}
`;

const FX_VERTEX_PARS = /* glsl */ `
attribute float palIndex;
attribute vec4 instFx;
varying vec4 vPal;
varying float vScreenWater;
${PALETTE_LOOKUP}
${SCREEN_HUE_PARS}
float fxIndex(float index, vec4 fx) {
  float lo = mod(index, 16.0);
  if (fx.x > 2.5) return fx.y;
  if (fx.x > 1.5) {
    float v = lo + fx.z;
    v = v < 0.0 ? 0.0 : (v > 15.0 ? (v >= 31.0 ? 0.0 : 15.0) : v);
    return fx.y * 16.0 + v;
  }
  if (fx.x > 0.5) return fx.y * 16.0 + lo;
  return index;
}
`;

// The smoothies' hue changes (screenHue.ts) apply to the draw's pass height, the instance's y.
const FX_VERTEX = /* glsl */ `
vScreenWater = 0.0;
float palFx = fxIndex(palIndex, instFx);
#ifdef USE_INSTANCING
  palFx = screenHueIndex(palFx, instanceMatrix[3][1], vScreenWater);
#endif
vPal = vec4(paletteColor(palFx), instFx.w);
`;

/** Marks water_filter's pixels in the screen filters' render target (opaque materials only). */
export const WATER_ALPHA = /* glsl */ `
#include <opaque_fragment>
if (vScreenWater > 0.5) gl_FragColor.a = 0.5;
`;

const PAL_FRAGMENT = /* glsl */ `
diffuseColor *= vPal;
`;

export interface PaletteMaterialOptions {
  /** Lit (MeshStandardMaterial) or unlit (MeshBasicMaterial). */
  lit: boolean;
  /** Alpha-blended, for "blend" draws; per-instance alpha comes from instFx.w. */
  transparent: boolean;
  /** Draw the dark outline (DECISIONS.md D4). */
  outline: boolean;
  /** Lit materials only: how much of the palette colour is emitted regardless of lighting (0..1). */
  glow?: number;
}

/** A material for sprite meshes, extruded tiles, pixels and rects. */
export function paletteMaterial(palette: PaletteTexture, opts: PaletteMaterialOptions): THREE.Material {
  const params = {
    transparent: opts.transparent,
    depthWrite: !opts.transparent,
    userData: opts.outline ? {} : { outlineParameters: { visible: false } },
  };
  const material = opts.lit
    ? new THREE.MeshStandardMaterial({ ...params, roughness: 0.55, metalness: 0.15, envMapIntensity: 0.6 })
    : new THREE.MeshBasicMaterial(params);
  material.onBeforeCompile = (shader) => {
    shader.uniforms.paletteMap = { value: palette.texture };
    Object.assign(shader.uniforms, palette.screenHue.uniforms);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", `#include <common>\n${FX_VERTEX_PARS}`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>\n${FX_VERTEX}`);
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", "#include <common>\nvarying vec4 vPal;\nvarying float vScreenWater;")
      .replace("#include <color_fragment>", PAL_FRAGMENT);
    if (!opts.transparent) shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", WATER_ALPHA);
    if (opts.lit && opts.glow) {
      shader.uniforms.glow = { value: opts.glow };
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", "#include <common>\nuniform float glow;")
        .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += vPal.rgb * glow;");
    }
  };
  material.customProgramCacheKey = () => `palette-fx-${opts.lit ? "lit" : "unlit"}${opts.lit && opts.glow ? "-glow" : ""}`;
  return material;
}

/**
 * The ground (background 1) material: tiles from the atlas, coloured per fragment. With `blend`
 * (an opacity), it draws the C's blended background-2 tiles (draw_background_2_blend) as flat
 * translucent sheets instead: index 0 is see-through and the rest is drawn at that opacity.
 */
export function groundTileMaterial(palette: PaletteTexture, atlas: TileAtlas, blend?: number): THREE.Material {
  const material = new THREE.MeshStandardMaterial({
    roughness: 0.95,
    metalness: 0,
    envMapIntensity: 0.2,
    transparent: blend !== undefined,
    depthWrite: blend === undefined,
    userData: { outlineParameters: { visible: false } },
  });
  material.onBeforeCompile = (shader) => {
    shader.uniforms.paletteMap = { value: palette.texture };
    Object.assign(shader.uniforms, palette.screenHue.uniforms);
    shader.uniforms.atlasMap = { value: atlas.texture };
    shader.uniforms.tileUv = { value: atlas.tileUv };
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nattribute vec2 tileUvIn;\nattribute vec2 instTile;\nuniform vec2 tileUv;\nvarying vec2 vAtlasUv;\nvarying vec2 vTileOrigin;\nvarying float vPassY;",
      )
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvTileOrigin = instTile.xy;\nvAtlasUv = instTile.xy + tileUvIn * tileUv;\nvPassY = 0.0;\n#ifdef USE_INSTANCING\nvPassY = instanceMatrix[3][1];\n#endif",
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>\nuniform sampler2D atlasMap;\nuniform vec2 tileUv;\nvarying vec2 vAtlasUv;\nvarying vec2 vTileOrigin;\nvarying float vPassY;\n${PALETTE_LOOKUP}\n${SCREEN_HUE_PARS}\nfloat vScreenWater = 0.0;`,
      )
      .replace(
        "#include <color_fragment>",
        [
          // Stay inside this tile's texels so neighbours in the atlas never bleed in at the seams.
          "vec2 halfTexel = vec2(0.5 / float(textureSize(atlasMap, 0).x));",
          "vec2 atlasUv = clamp(vAtlasUv, vTileOrigin + halfTexel, vTileOrigin + tileUv - halfTexel);",
          "float groundIndex = floor(texture2D(atlasMap, atlasUv).r * 255.0 + 0.5);",
          blend !== undefined ? `if (groundIndex < 0.5) discard;\ndiffuseColor.a = ${blend.toFixed(3)};` : "",
          // The smoothies' hue (screenHue.ts) for the instance's pass height: 0 for the ground, which
          // is under every filter; a blended background-2 sheet's own pass otherwise.
          "diffuseColor.rgb *= paletteColor(screenHueIndex(groundIndex, vPassY, vScreenWater));",
        ].join("\n"),
      );
    if (blend === undefined) shader.fragmentShader = shader.fragmentShader.replace("#include <opaque_fragment>", WATER_ALPHA);
  };
  material.customProgramCacheKey = () => (blend === undefined ? "palette-ground-tiles" : `palette-ground-tiles-blend-${blend}`);
  return material;
}
