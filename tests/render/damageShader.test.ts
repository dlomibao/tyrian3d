// The damage patch (src/render/damage/damageShader.ts, D87) keeps a material's own shader patch:
// the island rock's (rockMaterial.ts, D84) drew its palette-data texture as colour when the damage
// patch replaced it.
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { damageUniforms, patchDamage } from "../../src/render/damage/damageShader";

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
