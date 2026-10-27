// The move from one episode to the next: JE_initEpisode, JE_scanForEpisodes and
// JE_findNextEpisode (OpenTyrian src/episodes.c L247-298) and JE_nextEpisode (src/mainint.c
// L954-1001), which the episode script's `]Q` (end of episode) runs from JE_loadMap.
//
// What carries over to the next episode is whatever JE_nextEpisode doesn't touch: the player's
// items, cash, last_items, the difficulty and the data cubes. JE_initEpisode only switches the
// files (levelsN.dat, tyrianN.lvl, cubetxtN.dat) and reloads the item data, whose prices and
// stats differ per episode (episode 4's are in tyrian4.lvl).
//
// The screens JE_nextEpisode shows (the credits, the next episode's title) are pauses of the
// JE_loadMapSteps generator (tyrian2.ts), which the host draws: see LoadMapPause there.

import { FRONT_WEAPON, REAR_WEAPON, g } from "./state";
import { mt_rand } from "./mtrand";
import { copyPlayerItems } from "./player";
import { buildResources, type TyrianFiles } from "./resources";
import { play_song, type LoadMapPause } from "./tyrian2";

/** episodes.h FIRST_LEVEL, EPISODE_MAX, EPISODE_AVAILABLE */
export const FIRST_LEVEL = 1;
export const EPISODE_MAX = 5;
export const EPISODE_AVAILABLE = 4;

/** The song JE_nextEpisode plays under the next episode's title (play_song(26)). */
export const SONG_NEXT_EPISODE = 26;

/**
 * JE_initEpisode (episodes.c L247-260). The C builds the file names from episodeNum (JE_loadMap and
 * loadLevelFile do that here), then analyzeLevel and JE_loadItemDat: buildResources reloads the
 * item data, and loadLevelFile reads the level positions when it needs them.
 */
export function JE_initEpisode(newEpisode: number, files: TyrianFiles): void {
  if (newEpisode === g.episodeNum) return;

  g.episodeNum = newEpisode;

  g.res = buildResources(files, newEpisode);
}

/**
 * JE_scanForEpisodes (episodes.c L262-270): an episode is available when its tyrianN.lvl exists.
 * The C runs it once at startup (opentyr.c L805); the files can't change while the game runs, so
 * JE_nextEpisode runs it here instead of the host keeping it up to date.
 */
export function JE_scanForEpisodes(files: TyrianFiles): void {
  for (let i = 0; i < EPISODE_MAX; ++i) g.episodeAvail[i] = files.get(`tyrian${i + 1}.lvl`) !== undefined;
}

/** JE_findNextEpisode (episodes.c L272-298): the next available episode, wrapping to episode 1. */
export function JE_findNextEpisode(): number {
  let newEpisode = g.episodeNum;

  g.jumpBackToEpisode1 = false;

  for (;;) {
    newEpisode++;

    if (newEpisode > EPISODE_MAX) {
      newEpisode = 1;
      g.jumpBackToEpisode1 = true;
      g.gameHasRepeated = true;
    }

    if (g.episodeAvail[newEpisode - 1] || newEpisode === g.episodeNum) {
      break;
    }
  }

  return newEpisode;
}

/**
 * JE_nextEpisode (mainint.c L954-1001): after the last episode, the credits and maybe the
 * SuperCarrot; then the next episode, from its first section. It yields where the C shows a screen:
 * "highScoreCheck" (JE_highScoreCheck), "credits" (JE_playCredits) and "nextEpisode" (the next
 * episode's name with miscText[4] under it, until a key is pressed). Like the C, the screens that
 * wait for the player are skipped with constantPlay.
 */
export function* JE_nextEpisode(files: TyrianFiles): Generator<LoadMapPause, void, void> {
  g.lastLevelName = "Completed";

  if (g.episodeNum === g.initial_episode_num && !g.gameHasRepeated && g.episodeNum !== EPISODE_AVAILABLE &&
      !g.isNetworkGame && !g.constantPlay) {
    yield "highScoreCheck"; // JE_highScoreCheck()
  }

  JE_scanForEpisodes(files);
  const newEpisode = JE_findNextEpisode();

  if (g.jumpBackToEpisode1) {
    if (g.episodeNum > 2 &&
        !g.constantPlay) {
      yield "credits"; // JE_playCredits()
    }

    // randomly give player the SuperCarrot
    if ((mt_rand() % 6) === 0) {
      const player = g.player;
      player[0].items.ship = 2; // SuperCarrot
      player[0].items.weapon[FRONT_WEAPON].id = 23; // Banana Blast
      player[0].items.weapon[REAR_WEAPON].id = 24; // Banana Blast Rear

      for (let i = 0; i < player[0].items.weapon.length; ++i) player[0].items.weapon[i].power = 1;

      player[1].items.weapon[REAR_WEAPON].id = 24; // Banana Blast Rear

      player[0].last_items = copyPlayerItems(player[0].items);
    }
  }

  if (newEpisode !== g.episodeNum) JE_initEpisode(newEpisode, files);

  g.gameLoaded = true;
  g.mainLevel = FIRST_LEVEL;
  g.saveLevel = FIRST_LEVEL;

  play_song(SONG_NEXT_EPISODE);

  // JE_clr256, palettes[6-1], episode_name[episodeNum] at y 130 and miscText[5-1] at y 185, faded in.
  if (!g.constantPlay) yield "nextEpisode"; // waitUntilGetInput()
}
