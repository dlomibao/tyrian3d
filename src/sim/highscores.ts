// The high score tables: OpenTyrian keeps them in saveFiles[] (config.h JE_SaveFileType's
// highScore1/highScore2/highScoreName/highScoreDiff), three entries per table, one-player and
// two-player tables per episode: slot (episode - 1) * 6 (+ 3 for two players) + rank.
//
// Ported here without the drawing: the defaults loadSaves fills in when tyrian.sav is missing
// (config.c L838-862), JE_sort / JE_sortHighScores (mainint.c L2318-2345, L1063-1073), the rules
// of JE_highScoreCheck (mainint.c L1921-2156: which score, which table, which slot, the shift, what
// the name entry accepts, what is stored) and when JE_nextEpisode calls it (mainint.c L954-962).
// The host stores the table (src/app/highScores.ts) and draws the screens
// (src/app/highScoresScreen.ts).

import { s32 } from "./cint";
import { JE_totalScore } from "./mainint";
import { g } from "./state";

/** config.h SAVE_FILES_NUM: 11 save slots for each of 1 and 2 players. */
export const SAVE_FILES_NUM = 11 * 2;

/** episodes.h EPISODE_AVAILABLE: episode 4 has no high score table (see JE_nextEpisode). */
export const EPISODE_AVAILABLE = 4;

/** JE_highScoreScreen: "Save file only has space for scores for 3 episodes." */
export const HIGH_SCORE_EPISODES = 3;

/** The high score fields of one JE_SaveFileType (config.h L85-88). */
export interface HighScoreEntry {
  /** JE_longint highScore1: the score. */
  highScore1: number;
  /** JE_longint highScore2: unused, but the defaults fill it in for the team tables. */
  highScore2: number;
  /** char highScoreName[30]: string[29]. */
  highScoreName: string;
  /** JE_byte highScoreDiff: the difficulty level when the score was set (difficultyNameB's index). */
  highScoreDiff: number;
}

/** config.c defaultHighScoreNames[34]: one-player table defaults. */
export const defaultHighScoreNames = [
  /*TYR*/ "The Prime Chair", /*13*/
  "Transon Lohk",
  "Javi Onukala",
  "Mantori",
  "Nortaneous",
  "Dougan",
  "Reid",
  "General Zinglon",
  "Late Gyges Phildren",
  "Vykromod",
  "Beppo",
  "Borogar",
  "ShipMaster Carlos",

  /*OTHER*/ "Jill", /*5*/
  "Darcy",
  "Jake Stone",
  "Malvineous Havershim",
  "Marta Louise Velasquez",

  /*JAZZ*/ "Jazz Jackrabbit", /*3*/
  "Eva Earlong",
  "Devan Shell",

  /*OMF*/ "Crystal Devroe", /*11*/
  "Steffan Tommas",
  "Milano Angston",
  "Christian",
  "Shirro",
  "Jean-Paul",
  "Ibrahim Hothe",
  "Angel",
  "Cossette Akira",
  "Raven",
  "Hans Kreissack",

  /*DARE*/ "Tyler", /*2*/
  "Rennis the Rat Guard",
];

/** config.c defaultTeamNames[22]: two-player table defaults. */
export const defaultTeamNames = [
  "Jackrabbits",
  "Team Tyrian",
  "The Elam Brothers",
  "Dare to Dream Team",
  "Pinball Freaks",
  "Extreme Pinball Freaks",
  "Team Vykromod",
  "Epic All-Stars",
  "Hans Keissack's WARriors",
  "Team Overkill",
  "Pied Pipers",
  "Gencore Growlers",
  "Microsol Masters",
  "Beta Warriors",
  "Team Loco",
  "The Shellians",
  "Jungle Jills",
  "Murderous Malvineous",
  "The Traffic Department",
  "Clan Mikal",
  "Clan Patrok",
  "Carlos' Crawlers",
];

/**
 * loadSaves (config.c L838-862), when tyrian.sav is invalid or missing: random scores of
 * 1000..20000 in steps of 1000 and random names, the team names for the two-player tables
 * (i % 6 >= 3). `rand` stands in for mt_rand, which the C has seeded with the time (opentyr.c
 * L757), so the defaults differ from one install to the next. Unsorted, as in the C:
 * JE_sortHighScores runs before the title (opentyr.c L874).
 */
export function defaultHighScores(rand: () => number): HighScoreEntry[] {
  const saveFiles: HighScoreEntry[] = [];
  for (let i = 0; i < SAVE_FILES_NUM; ++i) {
    const e: HighScoreEntry = { highScore1: 0, highScore2: 0, highScoreName: "", highScoreDiff: 0 };
    e.highScore1 = ((rand() % 20) + 1) * 1000;
    if (i % 6 < 3) {
      e.highScore2 = 0;
      e.highScoreName = defaultHighScoreNames[rand() % defaultHighScoreNames.length];
    } else {
      e.highScore2 = ((rand() % 20) + 1) * 1000;
      e.highScoreName = defaultTeamNames[rand() % defaultTeamNames.length];
    }
    e.highScoreDiff = 0;
    saveFiles.push(e);
  }
  return saveFiles;
}

/** JE_sort (mainint.c L2318-2345): sort the three entries from slot `temp`, highest score first. */
export function JE_sort(saveFiles: HighScoreEntry[], temp: number): void {
  for (let a = 0; a < 2; a++) {
    for (let b = a + 1; b < 3; b++) {
      if (saveFiles[temp + a].highScore1 < saveFiles[temp + b].highScore1) {
        const x = saveFiles[temp + a];
        const y = saveFiles[temp + b];
        // Swaps highScore1, highScoreName and highScoreDiff (not highScore2).
        [x.highScore1, y.highScore1] = [y.highScore1, x.highScore1];
        [x.highScoreName, y.highScoreName] = [y.highScoreName, x.highScoreName];
        [x.highScoreDiff, y.highScoreDiff] = [y.highScoreDiff, x.highScoreDiff];
      }
    }
  }
}

/** JE_sortHighScores (mainint.c L1063-1073): sort the six tables of episodes 1-3. */
export function JE_sortHighScores(saveFiles: HighScoreEntry[]): void {
  let temp = 0;
  for (let x = 0; x < 6; x++) {
    JE_sort(saveFiles, temp);
    temp += 3;
  }
}

/**
 * Where JE_nextEpisode checks for a high score (mainint.c L954-962). initial_episode_num is the
 * episode the game was started on (menus.c L385); only that episode's table is checked.
 */
export function highScoreCheckDue(initial_episode_num: number): boolean {
  return (
    g.episodeNum === initial_episode_num &&
    !g.gameHasRepeated &&
    g.episodeNum !== EPISODE_AVAILABLE &&
    !g.isNetworkGame &&
    !g.constantPlay
  );
}

/**
 * JE_highScoreCheck's score (mainint.c L1940-1949), into a Sint32: in a two-player game, player
 * `p`'s cash; in a one-player game, JE_totalScore (cash plus the value of the ship and gear).
 */
export function highScoreCheckScore(p = 0): number {
  if (g.twoPlayerMode) return s32(g.player[p].cash);
  // single player highscore includes cost of upgrades
  return s32(JE_totalScore(g.player[0]));
}

/** The table JE_highScoreCheck fills: saveFiles[first_slot .. slot_limit - 1]. */
export interface HighScoreTable {
  first_slot: number;
  slot_limit: number;
}

/** JE_highScoreCheck (mainint.c L1951-1952): the table for an episode and player count. */
export function highScoreTable(initial_episode_num: number, twoPlayerMode: boolean): HighScoreTable {
  const first_slot = (initial_episode_num - 1) * 6 + (twoPlayerMode ? 3 : 0);
  return { first_slot, slot_limit: first_slot + 3 };
}

/**
 * The first half of JE_highScoreCheck for one player (mainint.c L1929-1967): sort the tables, find
 * the first entry `temp_score` beats in the episode's table, and if there is one, shift the entries
 * below it down to make room. Returns the slot for the name entry, or -1 for no high score.
 *
 * As in the C, the shift moves scores and names but not highScoreDiff (each rank keeps its old
 * difficulty until JE_highScoreCheckEnter writes the new one), and it happens before the name is
 * asked for, so cancelling the entry leaves the slot's old entry in two places.
 */
export function JE_highScoreCheckSlot(
  saveFiles: HighScoreEntry[],
  initial_episode_num: number,
  twoPlayerMode: boolean,
  temp_score: number,
): number {
  JE_sortHighScores(saveFiles);

  const { first_slot, slot_limit } = highScoreTable(initial_episode_num, twoPlayerMode);

  let slot: number;
  for (slot = first_slot; slot < slot_limit; ++slot) {
    if (temp_score > saveFiles[slot].highScore1) break;
  }

  // did you get a high score?
  if (slot >= slot_limit) return -1;

  // shift down old scores
  for (let i = slot_limit - 1; i > slot; --i) {
    saveFiles[i].highScore1 = saveFiles[i - 1].highScore1;
    saveFiles[i].highScoreName = saveFiles[i - 1].highScoreName;
  }
  return slot;
}

/** The name buffer the entry starts from: strcpy(stemp, "                             ") (29 spaces). */
export const HIGH_SCORE_NAME_BLANK = " ".repeat(29);
/** The entry takes characters while temp < 28. */
export const HIGH_SCORE_NAME_MAX = 28;

/** fonthand.c fontMap's CP437 codes 128-168 that have a glyph, as Unicode characters. */
const CP437_HIGH = "ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿";

/**
 * Whether the name entry accepts a typed character: `ch == ' ' || fontMap[ch] != -1`
 * (mainint.c L2096). fontMap has glyphs for ! " # $ % ' ( ) * + , - . / 0-9 : ; = ? A-Z [ \ ]
 * a-z { | } and the CP437 letters above; not & < > @ ^ _ ` ~.
 */
export function highScoreNameAccepts(ch: string): boolean {
  if (ch.length !== 1) return false;
  if (ch === " ") return true;
  if (CP437_HIGH.includes(ch)) return true;
  const c = ch.charCodeAt(0);
  return c >= 33 && c <= 125 && !"&<>@^_`".includes(ch);
}

/**
 * The typed name as the C stores it: the characters typed over the 29-space buffer
 * (strcpy(saveFiles[slot].highScoreName, stemp)), so it keeps its trailing spaces.
 */
export function highScoreStoredName(typed: string): string {
  const chars = [...typed].filter(highScoreNameAccepts).slice(0, HIGH_SCORE_NAME_MAX).join("");
  return chars + HIGH_SCORE_NAME_BLANK.slice(chars.length);
}

/** JE_highScoreCheck after the name entry (mainint.c L2106-2111): store it unless cancelled. */
export function JE_highScoreCheckEnter(
  saveFiles: HighScoreEntry[],
  slot: number,
  temp_score: number,
  typed: string | null,
  difficultyLevel: number,
): void {
  if (typed === null) return; // cancel
  saveFiles[slot].highScore1 = temp_score;
  saveFiles[slot].highScoreName = highScoreStoredName(typed);
  saveFiles[slot].highScoreDiff = difficultyLevel;
}

/** JE_highScoreScreen (mainint.c L1126): the difficulty column's name index. */
export function highScoreRank(highScoreDiff: number, difficultyNameBCount = 11): number {
  return Math.min(highScoreDiff, difficultyNameBCount - 1);
}
