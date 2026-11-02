// Load the models a level can show before it starts (DECISIONS.md D54), so its enemies don't
// appear as sprites and pop into their models when the models arrive (a cold cache on the deployed
// site takes seconds). Called after loadLevel and startLevel, before the first tick.

import type { LevelModelInfo, PreloadResult } from "../render/drawListRenderer";
import type { View } from "../render/view";
import { levelSprites, levelTiles } from "../sim/levelSprites";
import { g } from "../sim/state";
import { showProgress } from "./screens";

/**
 * How long a level start waits for its models. On a network too slow for that the level starts
 * anyway; what's still loading is drawn by DrawListRenderer.objectLook's rule (held back briefly,
 * then the sprite for that enemy's life), and later enemies get their models as they arrive.
 */
export const PRELOAD_TIMEOUT_MS = 20000;

/**
 * The level starts once the models needed this soon (curLoc units, about a tick each: some 30 s of
 * play) have loaded; the rest load in the background, earliest needed first, while it plays.
 * TYRIAN (level 1): about 10 of its 32 MB of models (enemies 16, structures 16) are due by then.
 */
export const PRELOAD_WAIT_LOC = 1000;

/** Don't flash a loading line for a preload this quick (a warm cache). */
const SHOW_AFTER_MS = 200;

/** What the current level (g.lvl, g.player) can show. */
export function levelModelInfo(): LevelModelInfo {
  return { sprites: levelSprites(), tileShapes: g.lvl?.shapesFile, tiles: levelTiles(), maps: levelTileMaps() };
}

/** The current level's three maps as tile numbers (-1: none), for the HD terrain's variants (D57). */
export function levelTileMaps(): LevelModelInfo["maps"] {
  const level = g.lvl?.level;
  if (!level) return undefined;
  const map = (layer: 0 | 1 | 2) => Int16Array.from(level.maps[layer], (b) => (level.mapSh[layer][b] ?? 0) - 1);
  return [map(0), map(1), map(2)];
}

/**
 * Preload the current level's models. `report(text)` shows progress (null: done); by default a
 * status line on the screens' overlay, shown only if the wait is long enough to notice.
 */
export async function preloadLevelModels(view: View, report?: (text: string | null) => void): Promise<PreloadResult> {
  let status: ReturnType<typeof showProgress> | null = null;
  let text = "Loading models…";
  const timer = report ? undefined : setTimeout(() => (status = showProgress(text)), SHOW_AFTER_MS);
  const show = (t: string | null) => {
    if (report) report(t);
    else if (t !== null) {
      text = t;
      status?.set(t);
    }
  };
  try {
    const result = await view.draws.preloadLevel(levelModelInfo(), {
      timeoutMs: PRELOAD_TIMEOUT_MS,
      waitUntil: PRELOAD_WAIT_LOC,
      progress: (done, total) => show(`Loading models… ${done} / ${total}`),
    });
    if (result.timedOut) console.warn(`level models: started after ${PRELOAD_TIMEOUT_MS} ms with ${result.done} of ${result.total} loaded`);
    return result;
  } finally {
    clearTimeout(timer);
    (status as ReturnType<typeof showProgress> | null)?.close();
    show(null);
  }
}
