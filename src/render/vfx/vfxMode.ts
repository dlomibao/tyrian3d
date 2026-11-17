// The shot and explosion look: the original sprites extruded (D4, D9), or the remastered effects
// (DECISIONS.md D35). Remastered is the default; `?vfx=original` picks the original.

export type VfxMode = "remastered" | "original";

export const DEFAULT_VFX_MODE: VfxMode = "remastered";

/**
 * The camera layer the remastered effects' particles, glows and puffs draw on. The screen filters
 * (D31) draw it after their post pass, so the smoothies leave it alone, as the C's filters leave
 * the shots and explosions drawn after them.
 */
export const VFX_LAYER = 1;

/**
 * The shots' flat art (spriteArtLayer.ts) is also on this layer. The main render draws the shot
 * halos under it (D169); the screen filters draw the effects over the filtered frame in a render of
 * their own (ScreenFilterPass.renderOver), and draw this layer there too, after the halos, so the
 * halos stay under the paintings on the smoothie levels as well (D215).
 */
export const SHOT_ART_LAYER = 2;

/** The mode a page's query string asks for (`?vfx=original` or `?vfx=remastered`), else the default. */
export function vfxModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): VfxMode {
  const v = search === undefined ? null : new URLSearchParams(search).get("vfx");
  return v === "original" || v === "remastered" ? v : DEFAULT_VFX_MODE;
}
