// The shot and explosion look: the original sprites extruded (D4, D9), or the remastered effects
// (DECISIONS.md D35). Remastered is the default; `?vfx=original` picks the original.

export type VfxMode = "remastered" | "original";

export const DEFAULT_VFX_MODE: VfxMode = "remastered";

/** The mode a page's query string asks for (`?vfx=original` or `?vfx=remastered`), else the default. */
export function vfxModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): VfxMode {
  const v = search === undefined ? null : new URLSearchParams(search).get("vfx");
  return v === "original" || v === "remastered" ? v : DEFAULT_VFX_MODE;
}
