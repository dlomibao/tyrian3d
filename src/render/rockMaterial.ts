// The island rock's HD material (DECISIONS.md D84). The Blender builders (assets/blender/tiles/
// lib_tiles.py rock_material, lib_rock_hd.py) give every island rock tile, the rock round the
// structures on the islands and the rock round some enemies' machines a texture that holds no
// colour but palette data:
//   R  the shade within a palette ramp, 0..15 (continuous: smooth stones, not 16 steps)
//   G  the ramp code: 0 .. 1 steps through the material's `tyrian_rock_ramps` (grey, brass, tan and
//      an enemy's extra ramp), weights interpolating between neighbouring ramps
//   B  the height, as a bump map (the mortar lines and the stones' bevels; the geometry carries the
//      stones' cushions)
// Here that becomes a lit material whose colour is looked up in the live palette (as the pal_<index>
// materials' is, paletteMaterial.ts / modelFrames.ts): palette[ramp * 16 + shade], interpolated
// between the two nearest shades. So level palettes, fades, JE_filterScreen and, through `hue`, the
// enemy hit flash and the smoothies' hue apply exactly as on the palette materials.
//
// With the Options terrain look "original" (terrainStyle.ts) the same texture is drawn one colour per
// original 2x pixel, whole shades and ramps, without the bump: the pixel look of the islands, as the
// original look draws the ground from its MMPX tiles.

import * as THREE from "three";
import type { PaletteTexture } from "./paletteTexture";

/** Texels per 2x pixel of the original art in the rock textures (lib_rock_hd.TEX / 2). */
const TEXELS_PER_CELL = 4;
/** How far the texture's height raises the surface for the bump (three.js bumpScale). */
export const ROCK_BUMP = 5;
const MAX_RAMPS = 4;

/** What a rock material is made from (to clone it with its own hue). */
interface RockInfo {
  map: THREE.Texture;
  ramps: number[];
  /** The tile's edge bands (lib_rock_hd.band_texture), and their slot (index + 1) by "<side>:<tile>". */
  bands?: { map: THREE.Texture; slots: Map<string, number>; depth: number; fade: number };
  /** Whether the texture's alpha is the rock's coverage (an enemy's rock fading into the island under it). */
  fade?: boolean;
  /** A structure's cell (row, column in its pattern): its bands are those of that cell's neighbours. */
  cell?: [number, number];
  palette: PaletteTexture;
  source: THREE.MeshStandardMaterial;
  hue: { value: number };
}

const info = new WeakMap<THREE.Material, RockInfo>();

/** Shared by every rock material: 1 for the HD look, 0 for the original's pixels. */
const rockHd = { value: 1 };

/** Draw the island rock smooth (HD) or one colour per original 2x pixel ("original"). */
export function setRockLook(hd: boolean): void {
  rockHd.value = hd ? 1 : 0;
}

export function rockLookIsHd(): boolean {
  return rockHd.value > 0.5;
}

/** Whether a loaded glTF material is an HD rock source (lib_tiles.rock_material). */
export function isRockSource(m: THREE.Material): boolean {
  return Array.isArray(m.userData?.tyrian_rock_ramps) && (m as THREE.MeshStandardMaterial).map != null;
}

/** Whether a rock material fades out at its edges (an enemy's rock): it stays translucent. */
export function rockFades(m: THREE.Material): boolean {
  return info.get(m)?.fade === true;
}

/** Whether a material is one made here. */
export function isRockMaterial(m: THREE.Material): boolean {
  return info.has(m);
}

/** A rock material's palette-data texture (R: the shade / 15), for its own shade under the blends (underShade.ts, D204). */
export function rockShadeMap(m: THREE.Material): THREE.Texture | undefined {
  return info.get(m)?.map;
}

/** The sides of a tile, in the order of the `rockBands` instance attribute. */
export const ROCK_SIDES = ["left", "right", "up", "down"] as const;

/** Whether a rock material has edge bands (a per-tile island model, D84): its mesh needs `rockBands`. */
export function hasRockBands(m: THREE.Material): boolean {
  return info.get(m)?.bands !== undefined;
}

/** The cell (row, column) of a structure a rock material covers; a one-tile model's is (0, 0). */
export function rockCell(m: THREE.Material): readonly [number, number] {
  return info.get(m)?.cell ?? [0, 0];
}

/**
 * The `rockBands` value for a tile's side with neighbour `tile` on the map: its band's slot (index
 * + 1), or 0 (no band for that neighbour: the tile's own texture is drawn).
 */
export function rockBandSlot(m: THREE.Material, side: (typeof ROCK_SIDES)[number], tile: number): number {
  return info.get(m)?.bands?.slots.get(`${side}:${tile}`) ?? 0;
}

/** Give a rock material the enemy hit-flash / smoothie hue byte (hue & 0xf0 replaces every ramp), or -1. */
export function setRockHue(m: THREE.Material, hue: number): void {
  const i = info.get(m);
  if (i) i.hue.value = hue;
}

const ROCK_PARS = /* glsl */ `
uniform sampler2D paletteMap;
uniform float rockHd;
uniform float rockHue;
uniform float rockRamps[${MAX_RAMPS}];
uniform int rockRampCount;
vec3 rockPalette(float index) {
  return texture2D(paletteMap, vec2((index + 0.5) / 256.0, 0.5)).rgb;
}
vec3 rockShade(float ramp, float shade) {
  float lo = floor(shade);
  float hi = min(lo + 1.0, 15.0);
  return mix(rockPalette(ramp * 16.0 + lo), rockPalette(ramp * 16.0 + hi), shade - lo);
}
`;

// After map_pars_fragment (it reads `map`): the texture with the instance's edge bands over it.
// A band is drawn over its side's outer BAND_DEPTH texels, fading into the tile's own texture over
// its inner BAND_FADE (lib_rock_hd.pair_bands); in a corner, the nearer side's band wins.
const ROCK_TEXEL = /* glsl */ `
#ifdef ROCK_BANDS
uniform sampler2D rockBandMap;
uniform vec3 rockBandSize;
uniform float rockBandFade;
varying vec4 vRockBands;
// A side's band: adds it to the sum, weighted so the nearest side wins (at a seam, that seam's band:
// the one its neighbour draws too), and returns how far into the band this is (1 outer, 0 inner).
float rockBand(inout vec4 sum, float slot, float along, float depth) {
  if (slot < 0.5) return 0.0;
  float d = rockBandSize.z;
  float w = 1.0 - smoothstep(d - rockBandFade, d, depth);
  if (w <= 0.0) return 0.0;
  vec2 uv = vec2(along / rockBandSize.x, ((slot - 1.0) * d + clamp(depth, 0.5, d - 0.5)) / rockBandSize.y);
  float k = w / pow(max(depth, 0.0) + 0.5, 3.0);
  sum += k * vec4(texture2D(rockBandMap, uv).rgb, 1.0);
  return w;
}
#endif
vec3 rockTexel(vec2 uv) {
  vec3 t = texture2D(map, uv).rgb;
#ifdef ROCK_BANDS
  vec2 size = vec2(textureSize(map, 0));
  vec2 tx = clamp(uv, 0.0, 1.0) * size;
  vec4 sum = vec4(0.0);
  float w = rockBand(sum, vRockBands.x, tx.y, tx.x);
  w = max(w, rockBand(sum, vRockBands.y, tx.y, size.x - tx.x));
  w = max(w, rockBand(sum, vRockBands.z, tx.x, tx.y));
  w = max(w, rockBand(sum, vRockBands.w, tx.x, size.y - tx.y));
  if (sum.w > 0.0) t = mix(t, sum.rgb / sum.w, w);
#endif
  return t;
}
`;

const ROCK_COLOUR = /* glsl */ `
#ifdef USE_MAP
#ifdef ROCK_FADE
  diffuseColor.a *= texture2D(map, vMapUv).a; // an enemy's rock: its coverage (lib_tiles.sprite_rock)
#endif
  vec3 rockTex;
  if (rockHd > 0.5) {
    rockTex = rockTexel(vMapUv);
  } else {
    vec2 cells = vec2(textureSize(map, 0)) / ${TEXELS_PER_CELL.toFixed(1)};
    rockTex = textureLod(map, (floor(vMapUv * cells) + 0.5) / cells, 0.0).rgb;
  }
  float rockS = clamp(rockTex.r * 15.0, 0.0, 15.0);
  float rockCode = rockTex.g * float(rockRampCount - 1);
  if (rockHd < 0.5) {
    rockS = floor(rockS + 0.5);
    rockCode = floor(rockCode + 0.5);
  }
  vec3 rockCol = vec3(0.0);
  for (int j = 0; j < ${MAX_RAMPS}; j++) {
    if (j >= rockRampCount) break;
    float w = clamp(1.0 - abs(rockCode - float(j)), 0.0, 1.0);
    if (w <= 0.0) continue;
    float ramp = rockHue >= 0.0 ? floor(rockHue / 16.0) : rockRamps[j];
    rockCol += w * rockShade(ramp, rockS);
  }
  diffuseColor.rgb *= rockCol;
#endif
`;

/**
 * three.js's bump chunk with its height from the texture's B channel (with the edge bands), off in
 * the original look. At the tile's edge the forward difference would read past it (the clamped edge
 * texel: no slope, a lit line along every seam), so there it looks back instead.
 */
const BUMP_HEIGHT = /* glsl */ `
float rockBumpH(vec2 uv) { return bumpScale * rockHd * rockTexel(uv).z; }
bool rockInside(vec2 uv) { return all(greaterThanEqual(uv, vec2(0.0))) && all(lessThanEqual(uv, vec2(1.0))); }
vec2 dHdxy_fwd() {
  vec2 dSTdx = dFdx( vBumpMapUv );
  vec2 dSTdy = dFdy( vBumpMapUv );
  float Hll = rockBumpH( vBumpMapUv );
  float dBx = rockInside( vBumpMapUv + dSTdx ) ? rockBumpH( vBumpMapUv + dSTdx ) - Hll : Hll - rockBumpH( vBumpMapUv - dSTdx );
  float dBy = rockInside( vBumpMapUv + dSTdy ) ? rockBumpH( vBumpMapUv + dSTdy ) - Hll : Hll - rockBumpH( vBumpMapUv - dSTdy );
  return vec2( dBx, dBy );
}
`;
const BUMP_PARS = THREE.ShaderChunk.bumpmap_pars_fragment.replace(/vec2 dHdxy_fwd\(\) \{[\s\S]*?return vec2\( dBx, dBy \);\s*\}/, BUMP_HEIGHT);
if (BUMP_PARS === THREE.ShaderChunk.bumpmap_pars_fragment) throw new Error("rockMaterial: three.js's bump chunk has changed");

function makeRock(i: RockInfo): THREE.MeshStandardMaterial {
  const src = i.source;
  const m = new THREE.MeshStandardMaterial({
    name: src.name,
    map: i.map,
    bumpMap: i.map,
    bumpScale: ROCK_BUMP,
    roughness: src.roughness,
    metalness: src.metalness,
    envMapIntensity: 0.6,
  });
  m.userData = JSON.parse(JSON.stringify(src.userData ?? {}));
  // Its own hue: an enemy clone flashes on its own.
  const hue = { value: -1 };
  const ramps = i.ramps.slice(0, MAX_RAMPS);
  while (ramps.length < MAX_RAMPS) ramps.push(0);
  m.onBeforeCompile = (shader) => {
    shader.uniforms.paletteMap = { value: i.palette.texture };
    shader.uniforms.rockHd = rockHd;
    shader.uniforms.rockHue = hue;
    shader.uniforms.rockRamps = { value: ramps };
    shader.uniforms.rockRampCount = { value: Math.max(1, Math.min(MAX_RAMPS, i.ramps.length)) };
    shader.fragmentShader = shader.fragmentShader
      .replace("#include <common>", `#include <common>\n${ROCK_PARS}`)
      .replace("#include <map_pars_fragment>", `#include <map_pars_fragment>\n${ROCK_TEXEL}`)
      .replace("#include <map_fragment>", ROCK_COLOUR)
      .replace("#include <bumpmap_pars_fragment>", BUMP_PARS);
    if (i.bands) {
      const b = i.bands;
      shader.uniforms.rockBandMap = { value: b.map };
      const img = b.map.image as { width: number; height: number };
      shader.uniforms.rockBandSize = { value: new THREE.Vector3(img.width, img.height, b.depth) };
      shader.uniforms.rockBandFade = { value: b.fade };
      shader.vertexShader = shader.vertexShader
        .replace("#include <common>", "#include <common>\nattribute vec4 rockBands;\nvarying vec4 vRockBands;")
        .replace("#include <begin_vertex>", "#include <begin_vertex>\nvRockBands = rockBands;");
    }
  };
  if (i.bands) m.defines = { ROCK_BANDS: "" };
  if (i.fade) {
    // An enemy's rock fades out at the edge of its painted area into the island under it (D84).
    m.defines = { ...m.defines, ROCK_FADE: "" };
    m.transparent = true;
  }
  m.customProgramCacheKey = () => `rock-hd${i.bands ? "-bands" : ""}${i.fade ? "-fade" : ""}`;
  info.set(m, { ...i, hue });
  return m;
}

/** A rock material for a loaded source material (isRockSource), colours from `palette`. */
export function rockMaterial(source: THREE.MeshStandardMaterial, palette: PaletteTexture): THREE.MeshStandardMaterial {
  const map = source.map!;
  map.colorSpace = THREE.NoColorSpace;
  map.anisotropy = 4;
  let bands: RockInfo["bands"];
  const keys = source.userData.tyrian_rock_bands;
  if (Array.isArray(keys) && keys.length > 0 && source.emissiveMap) {
    // Data, read at full resolution (the bands sit in rows: no mipmaps to blend them together).
    const bm = source.emissiveMap;
    bm.colorSpace = THREE.NoColorSpace;
    bm.generateMipmaps = false;
    bm.minFilter = THREE.LinearFilter;
    bm.magFilter = THREE.LinearFilter;
    bands = {
      map: bm,
      slots: new Map(keys.map((k, n) => [String(k), n + 1])),
      depth: Number(source.userData.tyrian_rock_band_depth),
      fade: Number(source.userData.tyrian_rock_band_fade),
    };
  }
  const fade = source.userData.tyrian_rock_fade === true || source.userData.tyrian_rock_fade === 1;
  const c = source.userData.tyrian_rock_cell;
  const cell: [number, number] | undefined = Array.isArray(c) && c.length === 2 ? [Number(c[0]), Number(c[1])] : undefined;
  return makeRock({ map, ramps: (source.userData.tyrian_rock_ramps as number[]).map(Number), bands, fade, cell, palette, source, hue: { value: -1 } });
}

/** A copy of a rock material with its own hue (an enemy clone flashes on its own). */
export function cloneRockMaterial(m: THREE.Material): THREE.Material {
  const i = info.get(m);
  return i ? makeRock(i) : m.clone();
}

/**
 * Replace a loaded model's HD rock source materials (lib_tiles.rock_material) by rock materials
 * coloured from `palette`, one per source (meshes sharing a source share the replacement).
 */
export function adoptRockMaterials<T extends THREE.Object3D>(root: T, palette: PaletteTexture): T {
  const made = new Map<THREE.Material, THREE.Material>();
  const swap = (m: THREE.Material) => {
    if (!isRockSource(m) || isRockMaterial(m)) return m;
    let r = made.get(m);
    if (!r) made.set(m, (r = rockMaterial(m as THREE.MeshStandardMaterial, palette)));
    return r;
  };
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(swap) : swap(mesh.material);
  });
  return root;
}
