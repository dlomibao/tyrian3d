// The game view's sun, and where airborne models' shadows fall under it (DECISIONS.md D171).
//
// The sun shines from the left and from the camera's side, mostly from above. Draws are lifted along
// camera rays (D6), which by itself pushes a model's shadow down the screen by its height times the
// camera ray's slope at the aim point (D133). The sun's +z was set to cancel most of that under the
// 32° camera of the time; under the 15° and overhead cameras (D61) nothing cancels it, so the shadow of
// anything airborne rose up the screen. airShadowShift removes the camera's part: an airborne model's
// shadow falls the C's shadowYDist below it at the player's height under every camera, and the sun
// (and so every model's lighting, the ground enemies' and the structures' shadows) stays as it was.

import * as THREE from "three";
import { PX_PER_UNIT } from "../game/playfield";
import { Pass } from "../sim/draw";
import { shadowYDist } from "../sim/varz";
import { PASS_HEIGHT } from "./passHeights";

/** The sun's position; the light points from here at the origin. */
export const SUN_POSITION: Readonly<{ x: number; y: number; z: number }> = { x: -6, y: 20, z: 8.4 };

/**
 * How far down the screen (world +z) an airborne model's shadow falls per unit of its height: the
 * C's ship shadow, drawn shadowYDist (10) game pixels below the ship (JE_playerMovement), at the
 * Player pass's height.
 */
export const AIR_SHADOW_DROP = shadowYDist / PX_PER_UNIT / PASS_HEIGHT[Pass.Player];

/** Models drawn above the ground enemies' pass are airborne: their shadows get airShadowShift. */
export function isAirborne(height: number): boolean {
  return height > PASS_HEIGHT[Pass.GroundEnemies];
}

/**
 * The extra shadow shift, per unit of height, that makes an airborne model's shadow fall where the
 * camera doesn't move it: (sun x, AIR_SHADOW_DROP) per unit height from the model's screen point.
 * `aim` is where the camera's view meets the ground: D133 already draws each model's shadow as it
 * would fall there, lifted (camera - aim) * h / camera.y along the ray, so this cancels that lift and
 * the sun's z. Written into `out` as (x, z) world units per unit height.
 */
export function airShadowShift(camera: THREE.Vector3, aim: THREE.Vector3, out: THREE.Vector2): THREE.Vector2 {
  // Where the shadow falls now, per unit height, from the model's screen point: the sun's offset
  // (-sun.xz / sun.y) plus the lift at the aim point. Keep the sun's x; move z to AIR_SHADOW_DROP.
  const sunZ = -SUN_POSITION.z / SUN_POSITION.y;
  const liftX = camera.y > 1e-6 ? (camera.x - aim.x) / camera.y : 0;
  const liftZ = camera.y > 1e-6 ? (camera.z - aim.z) / camera.y : 0;
  return out.set(-liftX, AIR_SHADOW_DROP - (sunZ + liftZ));
}

/**
 * The roll a camera ray adds to a model at `position` seen from `camera`, as a rotation.z (radians):
 * the angle of the ray from straight up, in the x-y plane. A model at rotation.z = r + this looks
 * rolled by r anywhere on screen, as the banking sprites are drawn (D93's fit is orthographic).
 */
export function rayRoll(position: THREE.Vector3, camera: THREE.Vector3): number {
  return Math.atan2(position.x - camera.x, Math.max(1e-6, camera.y - position.y));
}
