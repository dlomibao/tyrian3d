// The arcade games: how the title starts "1 Player Arcade" (gameplaySelect), a Super Arcade game
// (a ship's code typed at the title) and Super Tyrian (ENGAGE), and the title's code matching.
//
//   menus.c   L204-209     gameplaySelect: onePlayerAction / twoPlayerMode from the chosen mode
//   tyrian2.c L3529-3575   newGame(): the one-player arcade, two-player and full-game set-ups
//   tyrian2.c L3577-3622   newSuperArcadeGame(i)
//   tyrian2.c L3624-3675   newSuperTyrianGame()
//   tyrian2.c L3216, L3402-3446  titleScreen(): specialNameProgress, the typed codes
//
// The C asks for the episode and difficulty in between (episodeSelect, difficultySelect); here the
// title has already picked them, so they come in as arguments. What happens in flight (lives, the
// pickups that arm the ship, the Super Arcade weapons and specials) was ported with the level loop
// (src/sim/mainint.ts JE_playerMovement, JE_playerCollide; src/sim/game.ts).

import { newOnePlayerGame } from "./newgame";
import { newTwoPlayerGame } from "./twoplayer";
import { DIFFICULTY_SUICIDE, DIFFICULTY_ZINGLON, FRONT_WEAPON, g, SA_DESTRUCT, SA_ENGAGE, SA_NORTSHIPZ } from "./state";
import { SASpecialWeapon, SAShip, SAWeapon } from "./varz";

/** gameplaySelect's choices (menus.c MENU_ITEM_*; the network game isn't offered). src/app/gameplaySelect.ts shows them. */
export type GameplayMode = "fullGame" | "arcade" | "twoPlayerArcade";

/** What the title starts: a mode, or a game unlocked by a code typed at the title. */
export interface NewGameChoice {
  mode: GameplayMode;
  episode: number;
  difficulty: number;
  /** A Super Arcade ship, 1..SA (superArcadeMode): its code was typed at the title. */
  superArcade?: number;
  /** Super Tyrian (ENGAGE): `suicide` when the easier challenge was asked for (SCROLL LOCK). */
  superTyrian?: { suicide: boolean };
  /**
   * A Super Arcade ship whose start was backed out of: newSuperArcadeGame sets the ship before
   * episodeSelect, and nothing resets it before the next New Game, so a full game keeps it
   * ("allows player to smuggle arcade/super-arcade ships into full game", tyrian2.c L3564).
   */
  smuggledShip?: number;
}

/**
 * Start a new game for a title choice: the main loop's reset (opentyr.c L873-880) and newGame(),
 * newSuperArcadeGame() or newSuperTyrianGame(). Needs g.res for the choice's episode (Super
 * Tyrian's is 1) and the help text, as newOnePlayerGame does. Load the first level next.
 */
export function startNewGame(choice: NewGameChoice): void {
  if (choice.superTyrian) return newSuperTyrianGame(choice.superTyrian.suicide);
  if (choice.superArcade) return newSuperArcadeGame(choice.superArcade - 1, choice.episode, choice.difficulty);
  // [two-player] newGame()'s twoPlayerMode branch (tyrian2.c L3548-3559) with its own reset: both
  // players' cash 0, the Silver Ship, one step harder (src/sim/twoplayer.ts).
  if (choice.mode === "twoPlayerArcade") return newTwoPlayerGame(choice.episode, choice.difficulty);

  // JE_initPlayerData(), episodeSelect(), difficultySelect(), and newGame()'s full-game cash.
  newOnePlayerGame(choice.episode, choice.difficulty);
  if (choice.smuggledShip) g.player[0].items.ship = choice.smuggledShip;

  // gameplaySelect (menus.c L206-207)
  g.onePlayerAction = choice.mode === "arcade";
  g.twoPlayerMode = false;

  // newGame() (tyrian2.c L3542-3547)
  if (g.onePlayerAction) {
    g.player[0].cash = 0;

    g.player[0].items.ship = 8; // Stalker
  }
}

/**
 * newSuperArcadeGame(i) (tyrian2.c L3577-3622) once episodeSelect and difficultySelect have
 * returned `episode` and `difficulty`: Super Arcade ship `i` (0-based) with its first weapon and
 * special, one difficulty step harder, no cash.
 */
export function newSuperArcadeGame(i: number, episode: number, difficulty: number): void {
  newOnePlayerGame(episode, difficulty); // the main loop's reset, JE_initEpisode, the difficulty
  const player = g.player;

  player[0].items.ship = SAShip[i];

  // (the "Super Arcade Mode" card: the host shows it before starting)

  g.twoPlayerMode = false;
  g.onePlayerAction = true;
  g.superArcadeMode = i + 1;
  g.gameLoaded = true;
  g.initialDifficulty = ++g.difficultyLevel;

  player[0].cash = 0;

  player[0].items.weapon[FRONT_WEAPON].id = SAWeapon[i][0];
  player[0].items.special = SASpecialWeapon[i];
  if (g.superArcadeMode === SA_NORTSHIPZ) {
    for (let s = 0; s < player[0].items.sidekick.length; ++s) player[0].items.sidekick[s] = 24; // Companion Ship Quicksilver
  }
}

/**
 * newSuperTyrianGame() (tyrian2.c L3624-3675), after its "Prepare to play..." screen: episode 1 at
 * Lord of Game (DIFFICULTY_ZINGLON), or Suicide with SCROLL LOCK held, in the Stalker 21.126 with
 * the Atomic RailGun.
 */
export function newSuperTyrianGame(suicide: boolean): void {
  newOnePlayerGame(1); // the main loop's reset; JE_initEpisode(1)

  g.initialDifficulty = suicide ? DIFFICULTY_SUICIDE : DIFFICULTY_ZINGLON;

  g.constantDie = false;
  g.superTyrian = true;
  g.onePlayerAction = true;
  g.gameLoaded = true;
  g.difficultyLevel = g.initialDifficulty;

  g.player[0].cash = 0;

  g.player[0].items.ship = 13; // The Stalker 21.126
  g.player[0].items.weapon[FRONT_WEAPON].id = 39; // Atomic RailGun
}

/** What a completed title code starts (titleScreen's `i + 1`). */
export type TitleCode = { kind: "superArcade"; superArcadeMode: number } | { kind: "destruct" } | { kind: "superTyrian" };

/** The meaning of specialName[i] (0-based) once typed at the title (tyrian2.c L3421-3444). */
export function titleCode(i: number): TitleCode {
  if (i + 1 === SA_DESTRUCT) return { kind: "destruct" };
  if (i + 1 === SA_ENGAGE) return { kind: "superTyrian" };
  return { kind: "superArcade", superArcadeMode: i + 1 };
}

/**
 * A typed-code matcher: titleScreen's specialNameProgress loop (tyrian2.c L3402-3446), for any
 * list of codes (the title's specialName, or another screen's cheat codes). Feed it every key
 * press as an uppercase character ("" or "\0" for keys without one, which reset every code, as
 * the C's '\0' does).
 *
 * It keeps the C's quirks: a wrong letter resets a code to its start without trying that letter as
 * the code's first one (so "SSTEALTH" doesn't match), and a code longer than `maxLength` (the
 * C's COUNTOF(specialName[i]) - 1, 9) can never complete.
 */
export class CodeMatcher {
  readonly progress: number[];

  constructor(
    readonly codes: readonly string[],
    readonly maxLength = 9,
  ) {
    this.progress = codes.map(() => 0);
  }

  /** One key: the index of the code it completes, or -1. Several codes completing at once: the first. */
  feed(ch: string): number {
    const c = ch.length === 1 ? ch : "\0";
    let completed = -1;
    for (let i = 0; i < this.codes.length; i++) {
      const code = this.codes[i];
      // code[n] past the end is the C string's '\0', which no key matches.
      if (this.progress[i] >= this.maxLength || c !== (code[this.progress[i]] ?? "\0")) {
        this.progress[i] = 0;
        continue;
      }

      this.progress[i]++;

      if (this.progress[i] === code.length && completed < 0) completed = i;
    }
    return completed;
  }

  /** Whether the last key carried on a code already started (rather than starting one or none). */
  continuing(): boolean {
    return this.progress.some((p) => p >= 2);
  }

  reset(): void {
    this.progress.fill(0);
  }
}

/** The key's character as the C's titleScreen sees it: uppercase ASCII, or "\0". */
export function codeChar(key: string): string {
  return key.length === 1 && key.charCodeAt(0) < 0x80 ? key.toUpperCase() : "\0";
}
