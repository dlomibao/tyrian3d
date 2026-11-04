// `?damage=off` draws enemies' damaged frames as before D86: a damaged frame without a model of its
// own is the extruded sprite. For comparing; the default draws them with the intact models.

export type DamageMode = "on" | "off";

export function damageModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): DamageMode {
  return search !== undefined && new URLSearchParams(search).get("damage") === "off" ? "off" : "on";
}
