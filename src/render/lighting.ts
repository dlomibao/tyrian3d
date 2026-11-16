// The game view's lights and image-based light, and how the ground takes them (DECISIONS.md D205).
//
// The original's pixels are palette colours shown as they are, so the ground (background 1), lit facing
// up, should come out at its palette colour. Before D205 it came out about 1.7x in linear light (1.3x in
// sRGB): the sun (0.71 of the albedo facing up), the hemisphere fill (0.18) and the RoomEnvironment (0.7,
// about 0.98; three applies scene.environment to every material whatever its envMapIntensity), and the
// environment's 4% Fresnel sheen on top, which Neutral's toe took most of off again.
//
// The models, the lit sprites and the rocks keep the sun and the hemisphere as they were (their art was
// made and reviewed under them, and their sheen is the sun's highlights and the environment's
// reflections, art rule 2), with a little less environment (MODEL_ENVIRONMENT). The ground materials
// take their own share of the same lights (GroundLight, as uniforms): the sun's diffuse and the
// environment's (white) diffuse summing to GROUND_LIGHT facing up, no hemisphere (its sky is blue), no
// specular (the paintings carry their own highlights), and Neutral's toe undone on their colour
// (GROUND_UNTOE), so a palette colour lit 1.0 shows as itself, darks included.
//
// `?lighting=old` draws everything as before D205, for comparison.

import * as THREE from "three";
import { SUN_POSITION } from "./sun";

export type LightingMode = "new" | "old";

export interface LightingRig {
  /** Sky and ground colours of the hemisphere fill (sRGB hex), and its intensity. */
  hemi: { sky: number; ground: number; intensity: number };
  /** The directional sun's intensity (white; its direction is SUN_POSITION, sun.ts). */
  sun: number;
  /** scene.environmentIntensity: the RoomEnvironment on the models, the lit sprites and the rocks. */
  environment: number;
  /** The ground's light (groundLight): shares of the sun, hemisphere, environment and specular, and its toe. */
  ground: GroundLight;
}

/** How the ground materials take the scene's lights, as scales of what the models get (1 = the same). */
export interface GroundLight {
  sun: number;
  hemi: number;
  environment: number;
  /** Specular (sun and environment); black space has none regardless (D188). */
  specular: number;
  /** 1: the ground undoes Neutral's toe on its colour (GROUND_UNTOE); 0: it doesn't. */
  untoe: number;
}

/** What the ground's lights sum to facing up, as a share of the albedo: its palette colour as it is. */
export const GROUND_LIGHT = 1.0;
/** The sun's part of GROUND_LIGHT; the rest is the environment's (white) diffuse, which fills the shadows. */
export const GROUND_SUN_SHARE = 0.55;
/** cos of the sun's angle to straight up. */
export const SUN_UP_COS = SUN_POSITION.y / Math.hypot(SUN_POSITION.x, SUN_POSITION.y, SUN_POSITION.z);
/**
 * The RoomEnvironment's diffuse light on an up-facing matte surface per unit of environmentIntensity,
 * as a share of the albedo: measured in the game's render (GYGES 2.2 and SAVARA 1.12 with only the
 * environment on, linear 3D/original 1.40 and 1.41; D205).
 */
export const ENV_UP_IRRADIANCE = 1.4;

/**
 * The ground's scales for a rig's sun and environment: the sun's part GROUND_SUN_SHARE of
 * GROUND_LIGHT (Lambert's 1/pi at SUN_UP_COS), the environment's diffuse the rest, no hemisphere (its
 * sky is blue, and the ground keeps the palette's hues), no specular, and Neutral's toe undone.
 */
export function groundLight(sun: number, environment: number): GroundLight {
  const sunUp = (sun * SUN_UP_COS) / Math.PI;
  const envUp = environment * ENV_UP_IRRADIANCE;
  return {
    sun: sunUp > 0 ? (GROUND_SUN_SHARE * GROUND_LIGHT) / sunUp : 0,
    hemi: 0,
    environment: envUp > 0 ? ((1 - GROUND_SUN_SHARE) * GROUND_LIGHT) / envUp : 0,
    specular: 0,
    untoe: 1,
  };
}

/** The hemisphere fill and the sun, as since D171. */
const HEMI = { sky: 0x9fb8ff, ground: 0x20160c, intensity: 1.2 } as const;
const SUN = 2.5;
/**
 * The environment on the models: 0.7 before D205, when models over black space measured 1.16-1.40x
 * their sprites (GYGES's boss, the DREAD-NOT hull, GAUNTLET's balls); at 0.55, 1.07-1.28x, the sun's
 * highlights and the reflections' sheen kept.
 */
const MODEL_ENVIRONMENT = 0.55;

export const LIGHTING_RIGS: Readonly<Record<LightingMode, Readonly<LightingRig>>> = {
  old: { hemi: HEMI, sun: SUN, environment: 0.7, ground: { sun: 1, hemi: 1, environment: 1, specular: 1, untoe: 0 } },
  new: { hemi: HEMI, sun: SUN, environment: MODEL_ENVIRONMENT, ground: groundLight(SUN, MODEL_ENVIRONMENT) },
};

/** `?lighting=old` selects the look before D205; anything else the current one. */
export function lightingModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): LightingMode {
  return search !== undefined && new URLSearchParams(search).get("lighting") === "old" ? "old" : "new";
}

/**
 * The rig for the page's `?lighting=`. In development, `&lt=key:value,...` overrides values for tuning:
 * sun, hemi, env (the new ground follows them), and g.sun, g.hemi, g.environment, g.specular, g.untoe.
 */
export function lightingRig(search: string | undefined = typeof location === "undefined" ? undefined : location.search): LightingRig {
  const base = LIGHTING_RIGS[lightingModeFromSearch(search)];
  const rig: LightingRig = { ...base, hemi: { ...base.hemi }, ground: { ...base.ground } };
  const tune = search === undefined ? null : new URLSearchParams(search).get("lt");
  if (tune && import.meta.env?.DEV) {
    const g: Partial<GroundLight> = {};
    for (const part of tune.split(",")) {
      const [k, v] = part.split(":");
      const n = Number(v);
      if (!Number.isFinite(n)) continue;
      if (k === "sun") rig.sun = n;
      else if (k === "hemi") rig.hemi.intensity = n;
      else if (k === "env") rig.environment = n;
      else if (k.startsWith("g.")) g[k.slice(2) as keyof GroundLight] = n;
    }
    if (lightingModeFromSearch(search) === "new") rig.ground = groundLight(rig.sun, rig.environment);
    Object.assign(rig.ground, g);
  }
  return rig;
}

/**
 * The ground's light (GroundLight as uniforms), shared by every ground material: the pixel ground, the
 * 4x ground, the HD terrain's ground and cutouts. applyGroundLight sets them from the View's rig.
 */
export const GROUND_LIGHT_UNIFORMS = {
  groundSun: { value: 1 },
  groundHemi: { value: 1 },
  groundEnvironment: { value: 1 },
  groundSpecular: { value: 1 },
  groundUntoe: { value: 0 },
};

export function applyGroundLight(rig: LightingRig): void {
  const u = GROUND_LIGHT_UNIFORMS;
  u.groundSun.value = rig.ground.sun;
  u.groundHemi.value = rig.ground.hemi;
  u.groundEnvironment.value = rig.ground.environment;
  u.groundSpecular.value = rig.ground.specular;
  u.groundUntoe.value = rig.ground.untoe;
}

/** Neutral's toe: it takes this off every colour whose darkest channel is above twice it. */
export const NEUTRAL_TOE = 0.04;

/**
 * The colour that three's NeutralToneMapping (exposure 1) shows as `c` below its shoulder: Neutral
 * subtracts x - x²/(4 toe) for a darkest channel x under 2 toe, else toe; this adds back what it will
 * take. The JS twin of GROUND_UNTOE's groundUntoed.
 */
export function untoe(c: readonly [number, number, number]): [number, number, number] {
  const y = Math.max(Math.min(c[0], c[1], c[2]), 0);
  const add = y >= NEUTRAL_TOE ? NEUTRAL_TOE : 2 * Math.sqrt(NEUTRAL_TOE * y) - y;
  return [c[0] + add, c[1] + add, c[2] + add];
}

const TOE = NEUTRAL_TOE.toFixed(2);
const GROUND_LIGHT_PARS = /* glsl */ `
uniform float groundSun;
uniform float groundHemi;
uniform float groundEnvironment;
uniform float groundSpecular;
uniform float groundUntoe;
vec3 groundUntoed(vec3 c) {
  float y = max(min(c.r, min(c.g, c.b)), 0.0);
  return c + groundUntoe * (y >= ${TOE} ? ${TOE} : 2.0 * sqrt(${TOE} * y) - y);
}
`;

/**
 * Scale the hemisphere's and the environment's light before they are added, and the sun's diffuse
 * after (its shadow already in it). The specular goes through GROUND_SHEEN or CUTOUT_SPECULAR.
 */
const GROUND_LIGHT_END = /* glsl */ `
irradiance *= groundHemi;
iblIrradiance *= groundEnvironment;
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
radiance *= groundEnvironment;
#endif
#include <lights_fragment_end>
reflectedLight.directDiffuse *= groundSun;
`;

/**
 * The ground's colour, before the canvas's Neutral (or the screen filters' present pass, which applies
 * it to their render target): Neutral's toe undone, so it shows as lit. Three skips the tone mapping
 * in a render target, so this runs either way.
 */
const GROUND_UNTOE = /* glsl */ `
gl_FragColor.rgb = groundUntoed(gl_FragColor.rgb);
#include <tonemapping_fragment>
`;

/** The HD terrain's cutouts (painted over the ground) take the ground's specular scale. */
export const CUTOUT_SPECULAR = /* glsl */ `
#include <aomap_fragment>
reflectedLight.directSpecular *= groundSpecular;
reflectedLight.indirectSpecular *= groundSpecular;
`;

/**
 * Give a ground material's shader (onBeforeCompile) the ground's light (GROUND_LIGHT_UNIFORMS): the
 * sun's, hemisphere's and environment's shares, and Neutral's toe undone. Its specular takes
 * `groundSpecular` through GROUND_SHEEN (paletteMaterial.ts) or CUTOUT_SPECULAR, which the caller puts in.
 */
export function patchGroundLight(shader: THREE.WebGLProgramParametersWithUniforms): void {
  Object.assign(shader.uniforms, GROUND_LIGHT_UNIFORMS);
  shader.fragmentShader = shader.fragmentShader
    .replace("#include <common>", `#include <common>\n${GROUND_LIGHT_PARS}`)
    .replace("#include <lights_fragment_end>", GROUND_LIGHT_END)
    .replace("#include <tonemapping_fragment>", GROUND_UNTOE);
}
