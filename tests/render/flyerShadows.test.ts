// D171: airborne models' shadows fall the same way under every camera (sun.ts), the camera ray's
// roll is taken out of a banking ship's (sun.ts rayRoll), and the ship's shadow is the C's darken
// draw as a decal (shadowDecals.ts).
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import { AIR_SHADOW_DROP, SUN_POSITION, airShadowShift, isAirborne, rayRoll } from "../../src/render/sun";
import { DARKEN, DECAL_HEIGHT, ShadowDecals, shadowMask, shadowPlayerOfKey } from "../../src/render/shadowDecals";
import { CAMERA_TILT, CAMERA_TILT_GENTLE, CAMERA_TILT_OVERHEAD, PLAYFIELD_RECT, fitCamera } from "../../src/render/view";
import { PASS_HEIGHT } from "../../src/render/passHeights";
import { Pass, type Sprite2Sheet } from "../../src/sim/draw";
import { PX_PER_UNIT } from "../../src/game/playfield";

/** The game camera fitted at `tilt`, and where its view meets the ground (as update() finds it). */
function camera(tilt: number) {
  const cam = new THREE.PerspectiveCamera(40, 264 / 184, 0.1, 500);
  fitCamera(cam, PLAYFIELD_RECT, tilt, 1);
  const dir = cam.getWorldDirection(new THREE.Vector3());
  const aim = cam.position.clone().addScaledVector(dir, -cam.position.y / dir.y);
  return { pos: cam.position, aim };
}

/** Where a model at height h over the aim point casts its shadow, relative to its screen point (world xz). */
function shadowOffset(tilt: number, h: number): THREE.Vector2 {
  const { pos, aim } = camera(tilt);
  const lift = new THREE.Vector2((pos.x - aim.x) / pos.y, (pos.z - aim.z) / pos.y).multiplyScalar(h);
  const sun = new THREE.Vector2(-SUN_POSITION.x / SUN_POSITION.y, -SUN_POSITION.z / SUN_POSITION.y).multiplyScalar(h);
  const air = airShadowShift(pos, aim, new THREE.Vector2()).multiplyScalar(isAirborne(h) ? h : 0);
  return lift.add(sun).add(air);
}

describe("airborne shadows (sun.ts)", () => {
  test("the ship's shadow falls shadowYDist (10 px) below it and as far right under every camera", () => {
    const h = PASS_HEIGHT[Pass.Player];
    for (const tilt of [CAMERA_TILT_OVERHEAD, CAMERA_TILT_GENTLE, CAMERA_TILT]) {
      const o = shadowOffset(tilt, h);
      expect(o.y * PX_PER_UNIT).toBeCloseTo(10, 5);
      expect(o.x * PX_PER_UNIT).toBeCloseTo((-SUN_POSITION.x / SUN_POSITION.y) * h * PX_PER_UNIT, 5);
    }
    expect(AIR_SHADOW_DROP * h * PX_PER_UNIT).toBeCloseTo(10, 6);
  });

  test("before the fix the overhead camera put it above the ship; ground enemies are not moved", () => {
    const { pos, aim } = camera(CAMERA_TILT_OVERHEAD);
    const h = PASS_HEIGHT[Pass.Player];
    // Without the shift: the sun's -z only, up the screen.
    expect(((pos.z - aim.z) / pos.y - SUN_POSITION.z / SUN_POSITION.y) * h).toBeLessThan(0);
    expect(isAirborne(PASS_HEIGHT[Pass.GroundEnemies])).toBe(false);
    expect(isAirborne(PASS_HEIGHT[Pass.SkyEnemies])).toBe(true);
  });
});

describe("rayRoll", () => {
  test("zero under the camera, leaning toward the side the model is on", () => {
    const cam = new THREE.Vector3(0, 21, 0);
    expect(rayRoll(new THREE.Vector3(0, 3.3, 2), cam)).toBeCloseTo(0, 9);
    const r = rayRoll(new THREE.Vector3(7.7, 3.3, 0), cam);
    expect(r).toBeCloseTo(Math.atan(7.7 / 17.7), 9);
    // A model at rotation.z = r has its up vector on the ray to the camera: it looks unrolled.
    const up = new THREE.Vector3(0, 1, 0).applyEuler(new THREE.Euler(0, 0, r));
    const ray = cam.clone().sub(new THREE.Vector3(7.7, 3.3, 0)).normalize();
    expect(up.dot(ray)).toBeCloseTo(1, 9);
  });
});

describe("ship shadow decals (shadowDecals.ts)", () => {
  test("the shadow draws' keys: playerKey(n, 2..5) only", () => {
    expect(shadowPlayerOfKey(10002)).toBe(0);
    expect(shadowPlayerOfKey(10005)).toBe(0);
    expect(shadowPlayerOfKey(10103)).toBe(1);
    expect(shadowPlayerOfKey(10000)).toBe(-1); // the ship itself
    expect(shadowPlayerOfKey(1000895)).toBe(-1); // a shot's shadow
    expect(shadowPlayerOfKey(-1)).toBe(-1);
  });

  test("the mask is opaque inside the silhouette, clear outside, soft at the edge", () => {
    // A 4x2 block in a 6x4 sprite.
    const pixels = new Int16Array(24).fill(-1);
    for (let y = 1; y < 3; y++) for (let x = 1; x < 5; x++) pixels[y * 6 + x] = 7;
    const m = shadowMask({ width: 6, height: 4, pixels });
    const at = (px: number, py: number) => m.data[(Math.floor((py + 1) * 4) * m.width + Math.floor((px + 1) * 4)) * 4 + 3];
    expect(m.width).toBe(8 * 4);
    expect(m.height).toBe(6 * 4);
    expect(at(2.5, 2)).toBe(255); // inside
    expect(at(0.2, 0.2)).toBe(0); // outside
    const edge = at(1.05, 2);
    expect(edge).toBeGreaterThan(0);
    expect(edge).toBeLessThan(255);
  });

  test("a darken draw becomes a half-dark decal at DECAL_HEIGHT, and marks its player", () => {
    // A one-sprite sheet: Sprite2 #1 is two opaque rows of 3 pixels (count nibble 3, skip 0).
    const data = Uint8Array.of(2, 0, 0x30, 1, 2, 3, 0x00, 0x30, 1, 2, 3, 0x0f);
    const sheet = { id: "test", data } as unknown as Sprite2Sheet;
    const decals = new ShadowDecals();
    decals.begin();
    decals.add(sheet, 1, 1, 10002, 100, 50, new THREE.Vector3(0, 21, 0));
    expect(decals.hasPlayer(0)).toBe(true);
    expect(decals.hasPlayer(1)).toBe(false);
    const mesh = decals.root.children[0] as THREE.Mesh;
    expect(mesh.visible).toBe(true);
    expect(mesh.position.y).toBe(DECAL_HEIGHT);
    const mat = mesh.material as THREE.MeshBasicMaterial;
    expect(mat.opacity).toBe(DARKEN);
    expect(mat.depthWrite).toBe(false);
    decals.begin();
    expect(mesh.visible).toBe(false);
    expect(decals.hasPlayer(0)).toBe(false);
  });
});
