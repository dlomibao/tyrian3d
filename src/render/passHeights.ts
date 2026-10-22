// Height above the ground of each draw pass (DECISIONS.md D5), in world units (12 px).
//
// Rising in JE_main's draw order keeps the original's occlusion. An extruded sprite stands about
// 0.5 units above its pass height and 0.08 below (SPRITE_EXTRUDE), and its rim is 0.125 units
// high, so with gaps of 0.4 or more a higher draw's top always covers a lower one's from above.
// Because every draw is projected along the camera ray back onto its original screen position
// (DECISIONS.md D6), these heights change depth, lighting and shadows, never layout. Lower is
// closer to the original's look (shadows near their casters); higher is more 3D.

import { Pass } from "../sim/draw";

export const PASS_HEIGHT: Readonly<Record<Pass, number>> = {
  [Pass.Background1]: 0,
  [Pass.Starfield]: 0.02,
  [Pass.Background2Under]: 0.05,
  [Pass.GroundEnemies]: 0.45,
  [Pass.Background2Mid]: 0.9,
  [Pass.Background3Under]: 1.25,
  [Pass.SkyEnemies]: 1.65,
  [Pass.Background3]: 2.1,
  [Pass.TopEnemies]: 2.5,
  [Pass.PlayerShots]: 2.9,
  [Pass.Player]: 3.3,
  [Pass.EnemyShots]: 3.75,
  [Pass.Background3Over]: 4.15,
  [Pass.TopEnemiesOver]: 4.55,
  [Pass.SkyEnemiesOver]: 4.95,
  [Pass.Explosions]: 5.35,
  [Pass.Background2Top]: 5.75,
  [Pass.Effects]: 6.15,
};

export function passHeight(pass: Pass): number {
  return PASS_HEIGHT[pass] ?? 0;
}
