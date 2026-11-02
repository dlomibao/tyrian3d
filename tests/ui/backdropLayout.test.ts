import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { freeSlot } from "../../src/ui/backdrop";
import { INK_OUTLINE } from "../../src/render/outlineColor";

describe("freeSlot", () => {
  const panel = { left: 340, top: 60, right: 786, bottom: 700 };
  it("puts the ship in the wider side, favouring the preferred one", () => {
    const right = freeSlot(1126, 720, panel, 1, 100, 60, 0.25)!;
    expect(right.cx).toBeGreaterThan(786);
    const left = freeSlot(1126, 720, panel, -1, 100, 60, 0.25)!;
    expect(left.cx).toBeLessThan(340);
  });
  it("sizes the ship to fit its gap", () => {
    const slot = freeSlot(1920, 1080, { left: 480, top: 60, right: 1440, bottom: 1060 }, -1, 200, 120, 0.25)!;
    expect(slot.fit).toBeCloseTo((480 / 2 - 14) / 200);
  });
  it("is null when the panel leaves no room (phones)", () => {
    expect(freeSlot(390, 760, { left: 8, top: 20, right: 382, bottom: 750 }, 1, 100, 60, 0.25)).toBeNull();
  });
});

describe("INK_OUTLINE", () => {
  it("renders as the sprites' near-black (16, 8, 0), not a lifted brown", () => {
    const c = new THREE.Color().fromArray(INK_OUTLINE);
    const srgb = c.getRGB({ r: 0, g: 0, b: 0 }, THREE.SRGBColorSpace);
    expect(Math.round(srgb.r * 255)).toBe(16);
    expect(Math.round(srgb.g * 255)).toBe(8);
    expect(Math.round(srgb.b * 255)).toBe(0);
  });
});
