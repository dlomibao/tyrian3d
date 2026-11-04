// The player ship's wear by armour (DECISIONS.md D90). The ship has no damaged frames, so unlike an
// enemy (D87) its look follows its CURRENT armour, both ways, never latched:
//
//   ratio = armor / reference, clamped to [0, 1]; reference = the ship's own maximum armour
//   (`initial_armor`, set from the ship's data when the ship is fitted). Armour above it (pickups
//   and the armour ship's crates can take it over) counts as full; a missing or zero reference
//   (edge cases of two-player and arcade setups) counts as healthy.
//
//   level 0 (clean)  ratio >= LIGHT
//   level 1 (light)  ratio <  LIGHT: a light scorch
//   level 2 (heavy)  ratio <  HEAVY: heavier scorch and embers
//
// Going down a level happens as soon as the ratio is under the threshold; going back up needs the
// ratio HYSTERESIS above it, so armour hovering at a threshold doesn't flicker. A pickup that jumps
// from below HEAVY to above LIGHT + HYSTERESIS goes straight to clean. The look then eases toward the
// level's (FADE_PER_S), always within its range.
//
// Only the game draws ships with armour (DrawList.ships, filled by sim/game.ts tick); the menus,
// the shop's preview, the title flights and the model viewer never do, so they always show the ship
// clean.

export const LIGHT = 0.5;
export const HEAVY = 0.25;
/** About 3% of the ship's maximum armour. */
export const HYSTERESIS = 0.03;
/** Scorch coverage (share of the ship's top, damageShader.ts ship mode) per level. */
export const COVER = [0, 0.28, 0.55] as const;
/** Ember glow per level. */
export const HOT = [0, 0, 1] as const;
/** How fast the look follows the level: coverage and glow per second. */
export const FADE_PER_S = 0.8;

export type ShipLevel = 0 | 1 | 2;

/** armor / reference in [0, 1]; 1 (healthy) without a usable reference. */
export function armourRatio(armor: number, reference: number): number {
  if (!Number.isFinite(reference) || reference <= 0 || !Number.isFinite(armor)) return 1;
  return Math.min(1, Math.max(0, armor / reference));
}

/** The level for `ratio`, given the level before (the hysteresis band only delays going up). */
export function shipLevel(ratio: number, prev: ShipLevel): ShipLevel {
  const down: ShipLevel = ratio < HEAVY ? 2 : ratio < LIGHT ? 1 : 0;
  if (down >= prev) return down;
  // Recovering: up past each threshold only with the margin.
  const up: ShipLevel = ratio >= LIGHT + HYSTERESIS ? 0 : ratio >= HEAVY + HYSTERESIS ? 1 : 2;
  return Math.min(prev, Math.max(down, up)) as ShipLevel;
}

/** One ship's look: its level and the eased coverage and glow the shader draws. */
export class ShipCondition {
  level: ShipLevel = 0;
  cover = 0;
  hot = 0;

  /** Follow `armor` of `reference` over `dt` seconds (0: no easing, e.g. paused). */
  update(armor: number, reference: number, dt: number): void {
    this.level = shipLevel(armourRatio(armor, reference), this.level);
    const step = Math.max(0, dt) * FADE_PER_S;
    this.cover = approach(this.cover, COVER[this.level], step);
    this.hot = approach(this.hot, HOT[this.level], step);
  }

  /** Clean at once (a new level, or no ship armour to follow). */
  reset(): void {
    this.level = 0;
    this.cover = 0;
    this.hot = 0;
  }

  get damaged(): boolean {
    return this.cover > 1e-3 || this.hot > 1e-3;
  }
}

function approach(v: number, target: number, step: number): number {
  const out = v < target ? Math.min(target, v + step) : Math.max(target, v - step);
  return Math.min(1, Math.max(0, out));
}
