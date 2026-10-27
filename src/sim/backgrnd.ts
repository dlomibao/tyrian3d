// Port of OpenTyrian src/backgrnd.c: the three scrolling background layers, the starfield, and the
// screen filter state. The globals backgrnd.h declares live on `g` (state.ts).
//
// Tiles become drawTile records instead of pixels (DECISIONS.md D1). Each record carries:
// - x/y: the screen position the C would blit the 24x28 tile at (before its clipping to the
//   264x184 play area at (24, 0)); rows the C would clip away entirely are not recorded.
// - key: BG_KEY_LAYER * layer + the map cell's index in Level.maps[layer], stable while that
//   cell scrolls, so the renderer can interpolate. A background wrap (BKwrap, event 77) moves the
//   map pointer, so the same key can jump; the renderer should snap on large jumps.
// - tileId: `${shapesFile}:${shape}`, the tile graphic (0-based record in shapes?.dat).
//
// Pixel filters that read the screen (lava, water, blur, iced blur, the headlight and flip
// smoothies, JE_darkenBackground) aren't ported: there is no screen. Their switches (smoothies,
// smoothie_data, starShowVGASpecialCode) are still set by the sim for the renderer to use.

import { s8, u8, u16 } from "./cint";
import { drawList, drawPixel, drawTile } from "./draw";
import { mt_rand } from "./mtrand";
import { g } from "./state";

/** Key stride between background layers: layer * BG_KEY_LAYER + map index. */
export const BG_KEY_LAYER = 1_000_000;

/** Map widths in tiles (JE_MapType, JE_MapType2, JE_MapType3). */
const MAP_WIDTH = [14, 14, 15] as const;

/** Visible play area: x 24..287, y 0..183 (the C's blit routines clip rows to y < 184). */
const PLAY_BOTTOM = 184;

const tileIdCache = new Map<string, string[]>();

function tileIds(layer: 0 | 1 | 2): string[] {
  const lvl = g.lvl;
  const cacheKey = `${lvl.shapesFile}|${layer}|${lvl.level.mapSh[layer].join(",")}`;
  let ids = tileIdCache.get(cacheKey);
  if (!ids) {
    ids = lvl.level.mapSh[layer].map((sh) => `${lvl.shapesFile}:${sh - 1}`);
    tileIdCache.set(cacheKey, ids);
  }
  return ids;
}

/**
 * blitBackground1Row / blitBackgroundRow / blitBackgroundRowBlend (backgrnd.c L68-282): a row of
 * 12 tiles starting at map index `map`. Layer 0 tiles are opaque; null tiles are skipped (the C
 * asserts they don't occur on layer 0).
 */
function blitBackgroundRow(layer: 0 | 1 | 2, x: number, y: number, map: number, blend: boolean): void {
  // The C skips rows that end up fully clipped (y <= -28 or y >= 184).
  if (y <= -28 || y >= PLAY_BOTTOM) return;

  const cells = g.lvl.level.maps[layer];
  const tiles = g.lvl.tiles[layer];
  const ids = tileIds(layer);

  for (let ti = 0; ti < 12; ++ti) {
    const idx = map + ti;
    if (idx < 0 || idx >= cells.length) continue; // outside megaDataN.mainmap: undefined in C
    const mapByte = cells[idx];
    const tile = tiles[mapByte];
    if (!tile) continue; // transparent tile
    drawTile(layer, tile, ids[mapByte], x + ti * 24, y, BG_KEY_LAYER * layer + idx, blend);
  }
}

/** draw_background_1 (backgrnd.c L284-298) */
export function draw_background_1(): void {
  let map = g.mapYPos + g.mapXbpPos - 12;

  for (let i = -1; i < 7; i++) {
    blitBackgroundRow(0, g.mapXPos, i * 28 + g.backPos, map, false);

    map += MAP_WIDTH[0];
  }
}

/** Background 2's scroll step, shared by draw_background_2 and draw_background_2_blend. */
function moveBackground2(): void {
  /*Set Movement of background*/
  g.map2YDelay = u8(g.map2YDelay - 1);
  if (g.map2YDelay === 0) {
    g.map2YDelay = g.map2YDelayMax;

    g.backPos2 = u16(g.backPos2 + g.backMove2);

    if (g.backPos2 > 27) {
      g.backPos2 = u16(g.backPos2 - 28);
      g.mapY2 = u16(g.mapY2 - 1);
      g.mapY2Pos -= 14; /*Map Width*/
    }
  }
}

/** draw_background_2 (backgrnd.c L300-338) */
export function draw_background_2(): void {
  if (g.map2YDelayMax > 1 && g.backMove2 < 2) g.backMove2 = g.map2YDelay === 1 ? 1 : 0;

  if (g.background2) {
    // water effect combines background 1 and 2 by synchronizing the x coordinate
    const x = g.smoothies[1] ? g.mapXPos : g.mapX2Pos;

    let map = g.mapY2Pos + (g.smoothies[1] ? g.mapXbpPos : g.mapX2bpPos) - 12;

    for (let i = -1; i < 7; i++) {
      blitBackgroundRow(1, x, i * 28 + g.backPos2, map, false);

      map += MAP_WIDTH[1];
    }
  }

  moveBackground2();
}

/** draw_background_2_blend (backgrnd.c L340-372) */
export function draw_background_2_blend(): void {
  if (g.map2YDelayMax > 1 && g.backMove2 < 2) g.backMove2 = g.map2YDelay === 1 ? 1 : 0;

  let map = g.mapY2Pos + g.mapX2bpPos - 12;

  for (let i = -1; i < 7; i++) {
    blitBackgroundRow(1, g.mapX2Pos, i * 28 + g.backPos2, map, true);

    map += MAP_WIDTH[1];
  }

  moveBackground2();
}

/** draw_background_3 (backgrnd.c L374-398) */
export function draw_background_3(): void {
  /* Movement of background */
  g.backPos3 = u16(g.backPos3 + g.backMove3);

  if (g.backPos3 > 27) {
    g.backPos3 = u16(g.backPos3 - 28);
    g.mapY3 = u16(g.mapY3 - 1);
    g.mapY3Pos -= 15; /*Map Width*/
  }

  let map = g.mapY3Pos + g.mapX3bpPos - 12;

  for (let i = -1; i < 7; i++) {
    blitBackgroundRow(2, g.mapX3Pos, i * 28 + g.backPos3, map, false);

    map += MAP_WIDTH[2];
  }
}

/** JE_darkenBackground (backgrnd.c L45-61): a per-pixel screen effect ("super wild" detail); not ported. */
export function JE_darkenBackground(_neat: number): void {}

/**
 * JE_filterScreen (backgrnd.c L559-586): runs the filter fade, then records the hue filter and
 * brightness for the renderer in drawList.filter / drawList.brightness (-99 / 0 when not applied),
 * instead of rewriting the play area's pixels. JE_main only calls this while filterActive, so the
 * caller resets drawList.filter = -99 and drawList.brightness = 0 on ticks it doesn't call it.
 */
export function JE_filterScreen(col: number, brightness: number): void {
  if (g.filterFade) {
    g.levelBrightness = s8(g.levelBrightness + g.levelBrightnessChg);
    if ((g.filterFadeStart && g.levelBrightness < -14) || g.levelBrightness > 14) {
      g.levelBrightnessChg = s8(-g.levelBrightnessChg);
      g.filterFadeStart = false;
      g.levelFilter = g.levelFilterNew;
    }
    if (!g.filterFadeStart && g.levelBrightness === 0) {
      g.filterFade = false;
      g.levelBrightness = -99;
    }
  }

  drawList.filter = col !== -99 && g.filtrationAvail ? col : -99;
  drawList.brightness = brightness !== -99 && g.explosionTransparent ? brightness : 0;
}

/** JE_checkSmoothies (backgrnd.c L588-591) */
export function JE_checkSmoothies(): void {
  g.anySmoothies =
    (g.processorType > 2 && (g.smoothies[1 - 1] || g.smoothies[2 - 1])) ||
    (g.processorType > 1 && (g.smoothies[3 - 1] || g.smoothies[4 - 1] || g.smoothies[5 - 1]));
}

// --- Background starfield (backgrnd.c L1044-1101) ---

export interface StarfieldStar {
  /** Uint8 */
  color: number;
  /** JE_word: a pixel offset (y * 320 + x) that relies on 16-bit wrap-around. */
  position: number;
  speed: number;
}

const MAX_STARS = 100;
const STARFIELD_HUE = 0x90;
/** VGAScreen->pitch: the 320-pixel-wide game screen. */
const PITCH = 320;

const starfield_stars: StarfieldStar[] = Array.from({ length: MAX_STARS }, () => ({ color: 0, position: 0, speed: 0 }));

/** The stars' state (not in the C), so the item screen's weapon preview can borrow the starfield. */
export function starfield_save(): StarfieldStar[] {
  return starfield_stars.map((s) => ({ ...s }));
}

export function starfield_restore(saved: readonly StarfieldStar[]): void {
  saved.forEach((s, i) => Object.assign(starfield_stars[i], s));
}

/** initialize_starfield (backgrnd.c L1057-1065) */
export function initialize_starfield(): void {
  for (let i = MAX_STARS - 1; i >= 0; --i) {
    // `mt_rand() % 320 + mt_rand() % 200 * pitch`: C leaves the order of the two calls
    // unspecified; this assumes left to right.
    const px = mt_rand() % 320;
    const py = mt_rand() % 200;
    starfield_stars[i].position = u16(px + py * PITCH);
    starfield_stars[i].speed = (mt_rand() % 3) + 2;
    starfield_stars[i].color = u8((mt_rand() % 16) + STARFIELD_HUE);
  }
}

/** A pixel at screen offset p (y * 320 + x), as the C writes p[offset]. */
function drawStarPixel(p: number, color: number): void {
  drawPixel(p % PITCH, Math.trunc(p / PITCH), color);
}

/**
 * update_and_draw_starfield (backgrnd.c L1067-1101). The C only paints pixels that are still 0
 * (black) on the screen, so stars show only through gaps in background 1; the draw list has no
 * screen to test, so every star pixel is recorded and the renderer decides what hides them.
 */
export function update_and_draw_starfield(move_speed: number): void {
  for (let i = MAX_STARS - 1; i >= 0; --i) {
    const star = starfield_stars[i];

    star.position = u16(star.position + (star.speed + move_speed) * PITCH);

    if (star.position < 177 * PITCH) {
      drawStarPixel(star.position, star.color);

      // If star is bright enough, draw surrounding pixels
      if (star.color - 4 >= STARFIELD_HUE) {
        drawStarPixel(star.position + 1, star.color - 4);

        if (star.position > 0) drawStarPixel(star.position - 1, star.color - 4);

        drawStarPixel(star.position + PITCH, star.color - 4);

        if (star.position >= PITCH) drawStarPixel(star.position - PITCH, star.color - 4);
      }
    }
  }
}
