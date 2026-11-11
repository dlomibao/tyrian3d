// The damage patch (src/render/damage/damageShader.ts, D87) keeps a material's own shader patch:
// the island rock's (rockMaterial.ts, D84) drew its palette-data texture as colour when the damage
// patch replaced it.
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { damageDepthMaterial, damageUniforms, patchDamage } from "../../src/render/damage/damageShader";

function source() {
  return {
    uniforms: {} as Record<string, unknown>,
    vertexShader: "#include <common>\nvoid main() {\n#include <begin_vertex>\n#include <project_vertex>\n}",
    fragmentShader: "#include <common>\nvoid main() {\n#include <map_fragment>\n#include <emissivemap_fragment>\n}",
  };
}

describe("patchDamage", () => {
  test("keeps the material's own patch and cache key, after the damage", () => {
    const m = new THREE.MeshStandardMaterial();
    m.onBeforeCompile = (shader) => {
      shader.uniforms.own = { value: 1 };
      shader.fragmentShader = shader.fragmentShader.replace("#include <map_fragment>", "OWN_COLOUR");
    };
    m.customProgramCacheKey = () => "own-key";
    expect(patchDamage(m, damageUniforms())).toBe(true);
    const s = source();
    m.onBeforeCompile(s as never, {} as never);
    expect(s.uniforms.own).toEqual({ value: 1 });
    expect(s.uniforms.uDmgOn).toBeDefined();
    // The material's colour replaced map_fragment; the damage colour follows it.
    expect(s.fragmentShader).toMatch(/OWN_COLOUR\n[\s\S]*uDmgOn/);
    expect(m.customProgramCacheKey()).toBe("own-key|tyrian-damage-2");
  });

  test("a plain material gets the damage alone, once", () => {
    const m = new THREE.MeshStandardMaterial();
    const u = damageUniforms();
    expect(patchDamage(m, u)).toBe(true);
    expect(patchDamage(m, u)).toBe(false);
    const s = source();
    m.onBeforeCompile(s as never, {} as never);
    expect(s.fragmentShader).toContain("#include <map_fragment>");
    expect(s.uniforms.uDmgOn).toBe(u.uDmgOn);
  });
});

// D133: a model clone's shadow is drawn shifted (its depth material) and its own shadow lookups move with it.
describe("shadow shift", () => {
  test("the lit material looks its shadow up at the shifted position, then puts worldPosition back", () => {
    const m = new THREE.MeshStandardMaterial();
    const u = damageUniforms();
    patchDamage(m, u);
    const s = source();
    s.vertexShader = s.vertexShader.replace("#include <project_vertex>", "#include <project_vertex>\n#include <worldpos_vertex>\n#include <shadowmap_vertex>");
    m.onBeforeCompile(s as never, {} as never);
    expect(s.vertexShader).toMatch(/worldPosition\.xyz \+= uShadowShift;[\s\S]*#include <shadowmap_vertex>[\s\S]*worldPosition\.xyz -= uShadowShift;/);
    expect(s.uniforms.uShadowShift).toBe(u.uShadowShift);
  });

  test("the shadow depth material draws the clone shifted", () => {
    const u = damageUniforms();
    u.uShadowShift.value.set(1, 0, -2);
    const d = damageDepthMaterial(u);
    const s = source();
    d.onBeforeCompile(s as never, {} as never);
    expect(s.vertexShader).toContain("uniform vec3 uShadowShift;");
    expect(s.vertexShader).toMatch(/#include <project_vertex>[\s\S]*gl_Position = projectionMatrix \* viewMatrix \* \(modelMatrix \* vec4\(transformed, 1\.0\) \+ vec4\(uShadowShift, 0\.0\)\);/);
    expect(s.uniforms.uShadowShift).toBe(u.uShadowShift);
  });
});
