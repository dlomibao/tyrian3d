// The game view's lighting setup (src/render/lighting.ts, DECISIONS.md D205): the ground's share of the
// scene's lights sums to its palette colour, Neutral's toe is undone exactly, `?lighting=old` keeps the
// look before, and the shader patch finds three's chunks.
import { describe, expect, test } from "vitest";
import * as THREE from "three";
import {
  ENV_UP_IRRADIANCE,
  GROUND_LIGHT,
  GROUND_LIGHT_UNIFORMS,
  GROUND_SUN_SHARE,
  LIGHTING_RIGS,
  SUN_UP_COS,
  NO_SPECULAR_EDITS,
  applyGroundLight,
  groundLight,
  groundSpecularOff,
  lightingModeFromSearch,
  lightingRig,
  patchGroundLight,
  untoe,
} from "../../src/render/lighting";
import { neutralToneMap } from "../../src/render/screenFilters";
import { groundTileMaterial } from "../../src/render/paletteMaterial";
import type { PaletteTexture } from "../../src/render/paletteTexture";
import type { TileAtlas } from "../../src/render/tileAtlas";

describe("lighting mode", () => {
  test("?lighting=old selects the look before D205; anything else the new one", () => {
    expect(lightingModeFromSearch("?lighting=old")).toBe("old");
    expect(lightingModeFromSearch("?debug=play&lighting=old&main=3")).toBe("old");
    expect(lightingModeFromSearch("")).toBe("new");
    expect(lightingModeFromSearch("?lighting=new")).toBe("new");
    expect(lightingModeFromSearch(undefined)).toBe("new");
    expect(lightingRig("?lighting=old").ground).toEqual(LIGHTING_RIGS.old.ground);
    expect(lightingRig("").ground).toEqual(LIGHTING_RIGS.new.ground);
  });

  test("the models keep the sun and the hemisphere, with a little less environment; old is as before D205", () => {
    const { old, new: now } = LIGHTING_RIGS;
    expect(now.sun).toBe(old.sun);
    expect(now.hemi).toEqual(old.hemi);
    expect(now.environment).toBeLessThan(old.environment);
    expect(now.environment).toBeGreaterThanOrEqual(0.5); // the models' sheen stays
    expect(old.sun).toBe(2.5);
    expect(old.environment).toBe(0.7);
    expect(old.hemi).toEqual({ sky: 0x9fb8ff, ground: 0x20160c, intensity: 1.2 });
    // The old ground takes every light as the models do, and Neutral as it is.
    expect(old.ground).toEqual({ sun: 1, hemi: 1, environment: 1, specular: 1, untoe: 0 });
  });
});

describe("the ground's light", () => {
  test("sun and environment diffuse sum to GROUND_LIGHT facing up, the sun's part GROUND_SUN_SHARE", () => {
    const { sun, environment, ground } = LIGHTING_RIGS.new;
    const sunPart = ((sun * SUN_UP_COS) / Math.PI) * ground.sun;
    const envPart = environment * ENV_UP_IRRADIANCE * ground.environment;
    expect(sunPart + envPart).toBeCloseTo(GROUND_LIGHT, 6);
    expect(sunPart / GROUND_LIGHT).toBeCloseTo(GROUND_SUN_SHARE, 6);
    // No blue sky, no sheen on the paintings; the toe undone.
    expect(ground.hemi).toBe(0);
    expect(ground.specular).toBe(0);
    expect(ground.untoe).toBe(1);
    // The ground is lit less than the models: before D205 it took about 1.7x its colour.
    expect(ground.sun).toBeLessThan(1);
    expect(ground.environment).toBeLessThan(1);
  });

  test("groundLight scales with the rig: twice the sun, half the ground's share of it", () => {
    const a = groundLight(2.5, 0.7);
    const b = groundLight(5, 1.4);
    expect(b.sun).toBeCloseTo(a.sun / 2, 9);
    expect(b.environment).toBeCloseTo(a.environment / 2, 9);
    expect(groundLight(0, 0)).toMatchObject({ sun: 0, environment: 0 });
  });

  test("applyGroundLight sets the shared uniforms", () => {
    applyGroundLight(LIGHTING_RIGS.old);
    expect(GROUND_LIGHT_UNIFORMS.groundUntoe.value).toBe(0);
    expect(GROUND_LIGHT_UNIFORMS.groundSun.value).toBe(1);
    applyGroundLight(LIGHTING_RIGS.new);
    expect(GROUND_LIGHT_UNIFORMS.groundUntoe.value).toBe(1);
    expect(GROUND_LIGHT_UNIFORMS.groundSun.value).toBeCloseTo(LIGHTING_RIGS.new.ground.sun, 9);
    expect(GROUND_LIGHT_UNIFORMS.groundHemi.value).toBe(0);
  });
});

describe("Neutral's toe undone", () => {
  test("Neutral shows an untoed colour as the colour itself, below the shoulder", () => {
    const colours: [number, number, number][] = [
      [0, 0, 0],
      [0.001, 0.002, 0.0005],
      [0.02, 0.01, 0.005],
      [0.039, 0.05, 0.2],
      [0.04, 0.04, 0.04],
      [0.08, 0.3, 0.1],
      [0.2, 0.5, 0.7],
      [0.6, 0.65, 0.7],
    ];
    for (const c of colours) neutralToneMap(untoe(c)).forEach((v, i) => expect(v).toBeCloseTo(c[i], 6));
  });

  test("black stays black, and the shoulder still compresses what is past it", () => {
    expect(untoe([0, 0, 0])).toEqual([0, 0, 0]);
    const shown = neutralToneMap(untoe([1.5, 1.2, 1]));
    expect(Math.max(...shown)).toBeLessThan(1);
  });
});

describe("patchGroundLight", () => {
  test("finds three's chunks: scales the lights before and after lights_fragment_end, untoes before tone mapping", () => {
    const shader = {
      uniforms: {} as Record<string, THREE.IUniform>,
      vertexShader: THREE.ShaderLib.physical.vertexShader,
      fragmentShader: THREE.ShaderLib.physical.fragmentShader,
    } as THREE.WebGLProgramParametersWithUniforms;
    patchGroundLight(shader);
    const f = shader.fragmentShader;
    for (const name of ["groundSun", "groundHemi", "groundEnvironment", "groundSpecular", "groundUntoe"]) {
      expect(shader.uniforms[name]).toBe(GROUND_LIGHT_UNIFORMS[name as keyof typeof GROUND_LIGHT_UNIFORMS]);
      expect(f).toContain(`uniform float ${name};`);
    }
    const end = f.indexOf("#include <lights_fragment_end>");
    expect(f.indexOf("iblIrradiance *= groundEnvironment;")).toBeGreaterThan(0);
    expect(f.indexOf("iblIrradiance *= groundEnvironment;")).toBeLessThan(end);
    expect(f.indexOf("irradiance *= groundHemi;")).toBeLessThan(end);
    expect(f.indexOf("reflectedLight.directDiffuse *= groundSun;")).toBeGreaterThan(end);
    const untoeAt = f.indexOf("gl_FragColor.rgb = groundUntoed(gl_FragColor.rgb);");
    expect(untoeAt).toBeGreaterThan(f.indexOf("#include <opaque_fragment>"));
    expect(untoeAt).toBeLessThan(f.indexOf("#include <tonemapping_fragment>"));
  });

  test("the pixel ground's material takes it; its blended sheets (unlit) don't", () => {
    const palette = { texture: new THREE.DataTexture(), screenHue: { uniforms: {} } } as unknown as PaletteTexture;
    const atlas = { texture: new THREE.DataTexture(), tileUv: new THREE.Vector2(1, 1) } as unknown as TileAtlas;
    const compile = (m: THREE.Material) => {
      const shader = {
        uniforms: {} as Record<string, THREE.IUniform>,
        vertexShader: THREE.ShaderLib.physical.vertexShader,
        fragmentShader: THREE.ShaderLib.physical.fragmentShader,
      } as THREE.WebGLProgramParametersWithUniforms;
      m.onBeforeCompile(shader, {} as THREE.WebGLRenderer);
      return shader;
    };
    const ground = compile(groundTileMaterial(palette, atlas));
    expect(ground.fragmentShader).toContain("groundUntoed(gl_FragColor.rgb)");
    expect(ground.fragmentShader).toContain("reflectedLight.directSpecular *= groundSheen * groundSpecular;");
    expect(ground.uniforms.groundSun).toBe(GROUND_LIGHT_UNIFORMS.groundSun);
    const under = { uniforms: {} } as unknown as Parameters<typeof groundTileMaterial>[2];
    const blend = compile(groundTileMaterial(palette, atlas, under));
    expect(blend.fragmentShader).not.toContain("groundUntoed");
  });
});

describe("the ground without specular (D233)", () => {
  const physical = () =>
    ({
      uniforms: {} as Record<string, THREE.IUniform>,
      vertexShader: THREE.ShaderLib.physical.vertexShader,
      fragmentShader: THREE.ShaderLib.physical.fragmentShader,
    }) as THREE.WebGLProgramParametersWithUniforms;
  const chunks = THREE.ShaderChunk as unknown as Record<string, string>;

  test("three's chunks still have the lines it replaces", () => {
    for (const e of NO_SPECULAR_EDITS) expect(chunks[e.chunk]).toContain(e.from);
  });

  test("the current rig compiles the ground without the environment's reflection and the sun's highlight", () => {
    applyGroundLight(LIGHTING_RIGS.new);
    expect(groundSpecularOff()).toBe(true);
    const shader = physical();
    patchGroundLight(shader);
    const f = shader.fragmentShader;
    expect(f).toContain("#define GROUND_NO_SPECULAR");
    for (const e of NO_SPECULAR_EDITS) {
      expect(f).not.toContain(`#include <${e.chunk}>`);
      expect(f).toContain(e.to);
      expect(f).not.toContain(e.from);
    }
    // The indirect specular call stays: its multiscatter terms keep the diffuse as it was.
    expect(f).toContain("computeMultiscattering( material.dfg");
    expect(f).toContain("#include <lights_fragment_end>");
  });

  test("?lighting=old (ground specular 1) compiles as before, under another program key", () => {
    const palette = { texture: new THREE.DataTexture(), screenHue: { uniforms: {} } } as unknown as PaletteTexture;
    const atlas = { texture: new THREE.DataTexture(), tileUv: new THREE.Vector2(1, 1) } as unknown as TileAtlas;
    const m = groundTileMaterial(palette, atlas);
    applyGroundLight(LIGHTING_RIGS.new);
    const keyNew = m.customProgramCacheKey();
    applyGroundLight(lightingRig("?lighting=old"));
    try {
      expect(groundSpecularOff()).toBe(false);
      expect(m.customProgramCacheKey()).not.toBe(keyNew);
      const shader = physical();
      patchGroundLight(shader);
      expect(shader.fragmentShader).not.toContain("GROUND_NO_SPECULAR");
      for (const e of NO_SPECULAR_EDITS) expect(shader.fragmentShader).toContain(`#include <${e.chunk}>`);
    } finally {
      applyGroundLight(LIGHTING_RIGS.new);
    }
  });
});
