// The random seed a game session starts from (DECISIONS.md D37): opentyr.c main's
// mt_srand(time(NULL)), seconds since the epoch, unless `?seed=N` in the address fixes it (for
// debugging and for repeating a bug). Only the game itself seeds at start-up; the tests, the debug
// harnesses and the demos (beginPlayDemo) set their own seeds.

import { mt_srand } from "../sim/mtrand";

/** The start-up seed for a page's query string: `?seed=N` (0..2^32-1), else the clock in seconds. */
export function startupSeed(search: string, nowMs: number = Date.now()): number {
  const s = new URLSearchParams(search).get("seed")?.trim();
  if (s && /^\d+$/.test(s)) return Number(s) >>> 0;
  return Math.floor(nowMs / 1000) >>> 0;
}

/** Seed mt_rand once, as the C's main does before anything else. Returns the seed. */
export function seedAtStartup(search: string = location.search): number {
  const seed = startupSeed(search);
  mt_srand(seed);
  return seed;
}
