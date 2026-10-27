import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { EXPLOSION_DATA, ExplosionKind, explosionFrame } from "../../src/render/vfx/explosionFrames";
import { landingTime, ParticleSystem } from "../../src/render/vfx/particles";
import { GlowLayer } from "../../src/render/vfx/glowLayer";
import { measureSprite } from "../../src/render/vfx/remasteredFx";
import { vfxModeFromSearch } from "../../src/render/vfx/vfxMode";
import { extrudeSprite, SPRITE_EXTRUDE, toGeometry } from "../../src/render/spriteMesh";
import { JE_setupExplosion } from "../../src/sim/varz";
import { g, MAX_EXPLOSIONS } from "../../src/sim/state";

describe("explosion frames", () => {
  test("every moving type's frames have indices no other type draws", () => {
    const seen = new Map<number, number>();
    for (let type = 0; type <= 34; type++) {
      const [sprite, ttl] = EXPLOSION_DATA[type];
      for (let f = 0; f < ttl; f++) {
        const index = sprite + 2 + f;
        expect(seen.get(index), `index ${index} of type ${type}`).toBeUndefined();
        seen.set(index, type);
        expect(explosionFrame(index)).toMatchObject({ type, frame: f, ttl });
      }
    }
  });

  test("coin values (fixedPosition, drawn at sprite + 1) aren't mistaken for moving explosions", () => {
    for (let type = 35; type < EXPLOSION_DATA.length; type++) expect(explosionFrame(EXPLOSION_DATA[type][0] + 1)).toBeUndefined();
  });

  test("kinds", () => {
    const kind = (type: number) => explosionFrame(EXPLOSION_DATA[type][0] + 2)!.kind;
    expect(kind(0)).toBe(ExplosionKind.Hit);
    expect(kind(1)).toBe(ExplosionKind.Fireball);
    for (const t of [2, 3, 4, 5, 7, 8, 9, 10]) expect(kind(t)).toBe(ExplosionKind.Large);
    expect(kind(6)).toBe(ExplosionKind.Smoke);
    expect(kind(12)).toBe(ExplosionKind.Smoke);
    expect(kind(11)).toBe(ExplosionKind.Spark);
    expect(kind(20)).toBe(ExplosionKind.Spark);
  });

  test("the table matches the sim's JE_setupExplosion", () => {
    for (let type = 0; type < EXPLOSION_DATA.length; type++) {
      for (let i = 0; i < MAX_EXPLOSIONS; i++) g.explosions[i].ttl = 0;
      JE_setupExplosion(100, 100, 0, type, false, false);
      expect([g.explosions[0].sprite, g.explosions[0].ttl], `type ${type}`).toEqual([...EXPLOSION_DATA[type]]);
    }
  });
});

describe("vfx mode", () => {
  test("remastered by default; ?vfx= picks", () => {
    expect(vfxModeFromSearch("")).toBe("remastered");
    expect(vfxModeFromSearch("?vfx=original")).toBe("original");
    expect(vfxModeFromSearch("?vfx=remastered&clip=0")).toBe("remastered");
    expect(vfxModeFromSearch("?vfx=nonsense")).toBe("remastered");
    expect(vfxModeFromSearch(undefined)).toBe("remastered");
  });
});

describe("particle system", () => {
  test("spawns into a ring and uploads only what changed", () => {
    const ps = new ParticleSystem(8, THREE.AdditiveBlending);
    ps.spec.life = 1;
    for (let i = 0; i < 3; i++) ps.spawn();
    ps.flush();
    const attr = ps.mesh.geometry.getAttribute("aTime") as THREE.InstancedBufferAttribute;
    expect(attr.updateRanges).toEqual([{ start: 0, count: 12 }]);
    expect(ps.alive()).toBe(3);

    // Wrap around: 7 more fill slots 3..7 and 0..1.
    for (let i = 0; i < 7; i++) ps.spawn();
    ps.flush();
    expect(attr.updateRanges).toEqual([{ start: 12, count: 20 }, { start: 0, count: 8 }]);
    expect(ps.alive()).toBe(8);

    ps.advance(1.01);
    expect(ps.alive()).toBe(0);
    ps.dispose();
  });

  test("delayed particles aren't alive until their time", () => {
    const ps = new ParticleSystem(4, THREE.NormalBlending);
    ps.spec.life = 0.5;
    ps.spec.delay = 0.2;
    ps.spawn();
    expect(ps.alive()).toBe(0);
    ps.advance(0.3);
    expect(ps.alive()).toBe(1);
    ps.dispose();
  });

  test("landing time", () => {
    expect(landingTime(5, 0, 10)).toBeCloseTo(1);
    expect(landingTime(0, 4, 8)).toBeCloseTo(1);
    expect(landingTime(5, 0, 0)).toBeGreaterThan(1e6);
  });
});

describe("glow layer", () => {
  test("grows past its capacity and draws exactly what was added", () => {
    const layer = new GlowLayer(THREE.AdditiveBlending, 2);
    for (let i = 0; i < 5; i++) layer.add(i, 0, 0, i, 0, 1, 1, 1, 1, 1, 1);
    layer.commit();
    const geometry = layer.mesh.geometry as THREE.InstancedBufferGeometry;
    expect(geometry.instanceCount).toBe(5);
    expect((geometry.getAttribute("aHead").array as Float32Array)[12]).toBe(4);
    layer.commit();
    expect(geometry.instanceCount).toBe(0);
    expect(layer.mesh.visible).toBe(false);
    layer.dispose();
  });
});

describe("sprite measurements", () => {
  test("centre, radius and colours of a sprite mesh", () => {
    // A 4x4 block of index 7 at (2..6, 3..7) in a 12x14 sprite.
    const pixels = new Int16Array(12 * 14).fill(-1);
    for (let y = 3; y < 7; y++) for (let x = 2; x < 6; x++) pixels[y * 12 + x] = 7;
    const geometry = toGeometry(extrudeSprite({ width: 12, height: 14, pixels }, SPRITE_EXTRUDE)!);
    const info = measureSprite(geometry)!;
    expect(info.cx).toBeCloseTo(4, 0);
    expect(info.cy).toBeCloseTo(5, 0);
    expect(info.radius).toBeCloseTo(2, 0);
    expect([...info.indices]).toEqual([7]);
  });
});
