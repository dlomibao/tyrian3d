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

/** The mode a page's query string asks for (`?vfx=original` or `?vfx=remastered`), else the default. */
export function vfxModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): VfxMode {
  const v = search === undefined ? null : new URLSearchParams(search).get("vfx");
  return v === "original" || v === "remastered" ? v : DEFAULT_VFX_MODE;
}
