import { CLASSIC_TICK_HZ } from "./timing";

export interface Settings {
  /** Logic tick rate. Classic (~34.8 Hz) by default; higher rates are for a future mode. */
  logicHz: number;
  /** Cap on device pixel ratio, trading sharpness for speed on high-DPI screens. */
  maxPixelRatio: number;
  /** Clip the draw-list view to the original's playfield (`?clip=0` shows everything drawn). */
  clip: boolean;
  /**
   * Backgrounds as the original's tiles, extruded (DECISIONS.md D8), or remastered: upscaled ground
   * and 3D structure models (D34). `?bg=remaster` or `?bg=original`.
   */
  background: "original" | "remaster";
}

/** Defaults, overridable from the URL for testing, e.g. `?hz=60&dpr=1&clip=0&bg=remaster`. */
export function loadSettings(search: string = location.search): Settings {
  const params = new URLSearchParams(search);
  const num = (key: string, fallback: number) => {
    const v = Number(params.get(key));
    return params.has(key) && Number.isFinite(v) && v > 0 ? v : fallback;
  };
  return {
    logicHz: num("hz", CLASSIC_TICK_HZ),
    maxPixelRatio: num("dpr", 2),
    clip: params.get("clip") !== "0",
    background: params.get("bg") === "remaster" ? "remaster" : "original",
  };
}
