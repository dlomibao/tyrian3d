// A height multiplier for the Blender models (enemies and ships), to try taller or flatter models
// without rebuilding them: `?height=N` in the game or the model viewer (whose slider sets it).
// The models are stretched along their up axis as they're drawn; 1 is the models as built.

export const MODEL_HEIGHT_MIN = 0.5;
export const MODEL_HEIGHT_MAX = 4;

/** The multiplier from `?height=` (default 1), clamped to MODEL_HEIGHT_MIN..MODEL_HEIGHT_MAX. */
export function modelHeightFromUrl(search = location.search): number {
  const v = Number(new URLSearchParams(search).get("height"));
  return Number.isFinite(v) && v > 0 ? Math.min(MODEL_HEIGHT_MAX, Math.max(MODEL_HEIGHT_MIN, v)) : 1;
}
