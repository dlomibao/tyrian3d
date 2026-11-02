// The terrain look the player chose (DECISIONS.md D57): the HD remastered terrain paintings where a
// tileset has them, or the terrain as it was (the 4x upscaled ground of D34; `?bg=original` still
// gives the original tiles). Options → Terrain sets it and the prefs keep it (app/prefs.ts);
// `?terrain=original|hd` overrides it for the page. The renderer listens and switches live.

export type TerrainStyle = "original" | "hd";

/** Offered in Options, in this order. */
export const TERRAIN_STYLES: readonly TerrainStyle[] = ["original", "hd"];

/** HD where available, unless the player says otherwise. */
export const DEFAULT_TERRAIN_STYLE: TerrainStyle = "hd";

export const isTerrainStyle = (v: unknown): v is TerrainStyle => v === "original" || v === "hd";

/** `?terrain=original|hd`, or undefined. */
export function terrainStyleFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): TerrainStyle | undefined {
  const v = search === undefined ? null : new URLSearchParams(search).get("terrain");
  return isTerrainStyle(v) ? v : undefined;
}

type Listener = (style: TerrainStyle) => void;

let stored: TerrainStyle | undefined;
let override: TerrainStyle | undefined = terrainStyleFromSearch();
const listeners = new Set<Listener>();

/** The look in effect: the URL's, else the stored choice, else the default. */
export function terrainStyle(): TerrainStyle {
  return override ?? stored ?? DEFAULT_TERRAIN_STYLE;
}

/** The stored choice (prefs), undefined if the player never chose. */
export function storedTerrainStyle(): TerrainStyle | undefined {
  return stored;
}

/** Set from the prefs at start-up; the URL's choice still wins. */
export function loadTerrainStyle(style: unknown): void {
  const before = terrainStyle();
  stored = isTerrainStyle(style) ? style : undefined;
  if (terrainStyle() !== before) notify();
}

/** The player's choice (Options): kept, and it replaces the URL's for the rest of the page. */
export function setTerrainStyle(style: TerrainStyle): void {
  const before = terrainStyle();
  stored = style;
  override = undefined;
  if (terrainStyle() !== before) notify();
}

/** For tests: forget the stored choice and set the URL's. */
export function resetTerrainStyle(urlStyle?: TerrainStyle): void {
  stored = undefined;
  override = urlStyle;
}

/** Call `fn` whenever the look changes; returns the unsubscribe. */
export function onTerrainStyle(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function notify(): void {
  const s = terrainStyle();
  for (const fn of listeners) fn(s);
}
