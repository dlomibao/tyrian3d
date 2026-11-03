// [proposal: damage frames] Which prototype draws enemies' damaged frames (docs/agents/DAMAGE-FRAMES.md).
//
//   (none)     as on main: a damaged frame without a model of its own is the extruded sprite (D54)
//   ?damage=a  the intact model, damaged by the difference between the intact and damaged sprite
//              frames: cut away where pixels vanish, scorched, recoloured and glowing where they change
//   ?damage=b  the intact model with a generic damage level picked from that difference: noise
//              scorch, noise holes, smoke and sparks
//   ?damage=c  a model per damaged frame (src/render/damage/cModels/*.json), as PR #95 did for the rocks

export type DamageMode = "off" | "a" | "b" | "c";

export function damageModeFromSearch(search: string | undefined = typeof location === "undefined" ? undefined : location.search): DamageMode {
  const v = search === undefined ? null : new URLSearchParams(search).get("damage");
  return v === "a" || v === "b" || v === "c" ? v : "off";
}
