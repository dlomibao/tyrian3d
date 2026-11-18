import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { freeSlot, shipRadius, shipReachPx } from "../../src/ui/backdrop";
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

describe("ship reach (D256)", () => {
  it("is the model's farthest point from its turning axis, a diagonal past half its length, and its glows'", () => {
    const pivot = new THREE.Group();
    // 2.4 long and 2.4 wide, centred: its corners reach sqrt(2) * 1.2.
    pivot.add(new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.4, 2.4)));
    expect(shipRadius(pivot)).toBeCloseTo(Math.SQRT2 * 1.2, 5);
    const glow = new THREE.Sprite();
    glow.position.set(0, 0, 1.9);
    glow.scale.setScalar(0.4);
    pivot.add(glow);
    expect(shipRadius(pivot)).toBeCloseTo(2.1, 5);
  });
  it("measures the circle on screen, its near side larger, and grows with the radius", () => {
    const cam = new THREE.PerspectiveCamera(40, 16 / 9);
    const at = new THREE.Vector3(0, 4.6, 4.4);
    const look = new THREE.Vector3();
    const r1 = shipReachPx(cam, at, look, 1.4, 0.4, 1920, 1080);
    const r2 = shipReachPx(cam, at, look, 1.8, 0.4, 1920, 1080);
    expect(r2.x).toBeGreaterThan(r1.x);
    expect(r2.y).toBeGreaterThan(r1.y);
    // Wider than tall: the camera looks down on the ground circle at about 46 degrees.
    expect(r1.x).toBeGreaterThan(r1.y);
    // The near side reaches further than the orthographic estimate the fit used before (D55).
    const dist = at.distanceTo(look);
    const pxPerUnit = 1080 / 2 / (dist * Math.tan(THREE.MathUtils.degToRad(20)));
    expect(r1.x).toBeGreaterThan(pxPerUnit * 1.4);
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
