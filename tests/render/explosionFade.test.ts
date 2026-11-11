// D131: a fireball's last three frames (newsh6.shp 131-133, type 1) fade out when drawn as flat art,
// so its last ring doesn't linger as a red hollow square; every other explosion frame is drawn as before.
import { describe, expect, test } from "vitest";
import { flatExplosionFade } from "../../src/render/vfx/explosionFrames";

describe("flat explosion fade", () => {
  test("the fireball's last frames fade, the rest are whole", () => {
    expect(flatExplosionFade(133)).toBe(0.15);
    expect(flatExplosionFade(132)).toBe(0.45);
    expect(flatExplosionFade(131)).toBe(0.8);
    for (const i of [122, 125, 129, 130]) expect(flatExplosionFade(i)).toBe(1);
  });

  test("big explosions, smoke, sparks and coin values are untouched", () => {
    for (const i of [3, 14, 154, 165, 135, 141, 300]) expect(flatExplosionFade(i)).toBe(1);
  });
});
