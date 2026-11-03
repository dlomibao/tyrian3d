// What an explosion draw is, read from its sprite index alone.
//
// The sim draws each explosion as one frame of the explosion sheet (newsh6.shp) per tick
// (JE_main's "Draw Explosions", src/sim/game.ts): JE_setupExplosion picks a start sprite and a
// lifetime (ttl) by type, and every tick a moving explosion advances one sprite and draws
// sprite + 1. Each moving type's frames are a run of indices no other type uses, so the index
// says which type is drawing and how far through its life it is, with no state carried between
// ticks. Coin and gem values (fixedPosition) never advance and keep their first sprite.

/** explosion_data in JE_setupExplosion (varz.c L844-901), as in src/sim/varz.ts: [sprite, ttl]. */
export const EXPLOSION_DATA: readonly (readonly [number, number])[] = [
  [144, 7], [120, 12], [190, 12], [209, 12], [152, 12], [171, 12], [133, 7],
  [1, 12], [20, 12], [39, 12], [58, 12], [110, 3], [76, 7], [91, 3],
  [227, 3], [230, 3], [233, 3], [252, 3], [246, 3],
  [249, 3], [265, 3], [268, 3], [271, 3], [236, 3],
  [239, 3], [242, 3], [261, 3], [274, 3], [277, 3],
  [280, 3], [299, 3], [284, 3], [287, 3], [290, 3],
  [293, 3], [165, 8], [184, 8], [203, 8], [222, 8],
  [168, 8], [187, 8], [206, 8], [225, 10], [169, 10], [188, 10], [207, 20], [226, 14], [170, 14],
  [189, 14], [208, 14], [246, 14], [227, 14], [265, 14],
];

/** The sheet the sim draws explosions from (resources.ts loadCompShapes("6")). */
export const EXPLOSION_SHEET_ID = "newsh6.shp";

/** How the remastered effects treat an explosion type. */
export const enum ExplosionKind {
  /** Not an explosion frame the effects know: drawn as the original. */
  Other = 0,
  /** Type 0: a shot hitting something (game.ts, the player's and the enemies' shots). */
  Hit,
  /** Type 1: a small fireball (small enemies, hits on big ones, sequenced explosions). */
  Fireball,
  /** Types 2-5 (ground) and 7-10 (air): one quarter of JE_setupExplosionLarge's big explosion. */
  Large,
  /** Types 6 and 12: smoke puffs (missile trails, burning ground objects). */
  Smoke,
  /** Types 11, 13 and 23-34: shot trails; drawn as the original, glowing. */
  Spark,
  /** Types 14-22: the nine arcs JE_playerDamage draws round a ship whose shield took a hit. */
  Shield,
}

export interface ExplosionFrame {
  type: number;
  kind: ExplosionKind;
  /** 0 on the explosion's first drawn tick, up to ttl - 1. */
  frame: number;
  ttl: number;
}

function kindOf(type: number): ExplosionKind {
  if (type === 0) return ExplosionKind.Hit;
  if (type === 1) return ExplosionKind.Fireball;
  if ((type >= 2 && type <= 5) || (type >= 7 && type <= 10)) return ExplosionKind.Large;
  if (type === 6 || type === 12) return ExplosionKind.Smoke;
  if (type >= SHIELD_FIRST && type <= SHIELD_LAST) return ExplosionKind.Shield;
  if (type <= 34) return ExplosionKind.Spark;
  return ExplosionKind.Other; // 35+: coin and gem values, drawn as they are
}

const SHIELD_FIRST = 14;
const SHIELD_LAST = 22;

/**
 * Where JE_playerDamage (varz.c) puts each shield arc, from the player's x and y: a 4x3 grid of
 * 12x14 tiles (the bottom right one left out), types 14-22 in order.
 */
const SHIELD_ARC_AT: readonly (readonly [number, number])[] = [
  [-17, -12], [-5, -12], [7, -12], [19, -12],
  [-17, 2], [19, 2],
  [-17, 16], [-5, 16], [7, 16],
];

/** The middle of the arcs' grid, from the player's x and y (the ship's sprite is drawn at x - 5, y - 7, 24x28). */
const SHIELD_MIDDLE_X = (-17 + 19 + 12) / 2;
const SHIELD_MIDDLE_Y = (-12 + 16 + 14) / 2;

/**
 * For a shield arc (types 14-22), the offset from its tile's top-left to the middle of the ring
 * its type belongs to, so every arc of one hit gives the same point; otherwise undefined.
 */
export function shieldArcCentre(type: number): readonly [number, number] | undefined {
  return SHIELD_CENTRES[type - SHIELD_FIRST];
}
const SHIELD_CENTRES: readonly (readonly [number, number])[] = SHIELD_ARC_AT.map(([x, y]) => [SHIELD_MIDDLE_X - x, SHIELD_MIDDLE_Y - y]);

/** Frame table by sprite index (1-based, as drawn). Moving types only. */
const FRAMES: (ExplosionFrame | undefined)[] = [];
for (let type = 0; type <= 34; type++) {
  const [sprite, ttl] = EXPLOSION_DATA[type];
  // drawExplosions: sprite++ then blit sprite + 1, once per tick of the ttl.
  for (let frame = 0; frame < ttl; frame++) FRAMES[sprite + 2 + frame] = { type, kind: kindOf(type), frame, ttl };
}

/** The explosion type and frame a draw of `index` on the explosion sheet shows, if it's a moving one. */
export function explosionFrame(index: number): ExplosionFrame | undefined {
  return FRAMES[index];
}
