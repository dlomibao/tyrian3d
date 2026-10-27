// OpenTyrian's cheats and secret inputs, as rules on the game state (DECISIONS.md D32). The host
// turns keys into these calls (src/app/cheatKeys.ts in flight, src/app/titleCodes.ts on the title).
//
// - JE_mainKeyboardInput (mainint.c L2919-3161): the in-flight key chords. Ported: the Nort ship
//   (F2 F4 F6 F7 F9 \ /), invulnerability (F2 F3 F6), self-destruct (F2 F3 F4|F5), skipping the
//   level (F2 F6 F7|F8 without F9), and constantPlay's C. Not ported: the edited ships (Tab or Caps
//   Lock + 1..0), which need newsh$.shp from the ship editor, absent from Tyrian 2.1's data; F1 help;
//   the debug keys (F10 + Backspace) and the other Backspace "personal commands" (screenshot pause,
//   smoothies, filter cycling, hyper-speed, random music); pause and the menu, which the host owns.
// - titleScreen's specialName codes (tyrian2.c L3216, L3405-3445): typed on the title, they start
//   Super Arcade with one of seven ships, Destruct or Super Tyrian (SpecialNameMatcher).
// - difficultySelect's hidden difficulties (menus.c L551-600): Shift+G shows Impossible, then
//   Shift+] Suicide, then L O R D Lord of the Game (difficultySelectKey).
// - The LOOT command-line parameter (params.c): richMode, a new game's 1,000,000 credits.

import { JE_drawTextWindow } from "./mainint";
import {
  DIFFICULTY_EASY,
  DIFFICULTY_HARD,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_NORMAL,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_ZINGLON,
  g,
  SA_DESTRUCT,
  SA_ENGAGE,
  SA_NONE,
} from "./state";

/**
 * keysactive[]: the keys held down, by KeyboardEvent.code (SDL scancode -> code: SDL_SCANCODE_F2
 * -> "F2", SDL_SCANCODE_BACKSLASH -> "Backslash", SDL_SCANCODE_SLASH -> "Slash", SDL_SCANCODE_C
 * -> "KeyC"). `delete` is the C's `keysactive[x] = false`.
 */
export interface KeysActive {
  has(code: string): boolean;
  delete(code: string): unknown;
}

/**
 * The cheat part of JE_mainKeyboardInput (mainint.c L2919-3110). The C calls it from JE_main once
 * per frame in which a key went down (keyboardHasInput), with every key held then; the host does the
 * same before the next tick. Network play, two-player edited ships and the debug keys aren't ported
 * (see the file comment).
 */
export function JE_mainKeyboardInput(keysactive: KeysActive): void {
  const k = (code: string) => keysactive.has(code);

  /* {!Activate Nort Ship!} */
  if (k("F2") && k("F4") && k("F6") && k("F7") && k("F9") && k("Backslash") && k("Slash")) {
    // (isNetworkGame: nortShipRequest)
    g.player[0].items.ship = 12; // Nort Ship
    g.player[0].items.special = 13; // Astral Zone
    g.player[0].items.weapon[0].id = 36; // NortShip Super Pulse (FRONT_WEAPON)
    g.player[0].items.weapon[1].id = 37; // NortShip Spreader (REAR_WEAPON)
    g.shipGr = 1;
  }

  /* {Cheating} */
  if (!g.isNetworkGame && !g.twoPlayerMode && !g.superTyrian && g.superArcadeMode === SA_NONE) {
    if (k("F2") && k("F3") && k("F6")) {
      g.youAreCheating = !g.youAreCheating;
      keysactive.delete("F2");
    }

    if (k("F2") && k("F3") && (k("F4") || k("F5"))) {
      for (const p of g.player) p.armor = 0;

      g.youAreCheating = !g.youAreCheating;
      JE_drawTextWindow(g.miscText[63 - 1] ?? "");
    }

    if (g.constantPlay && k("KeyC")) {
      g.youAreCheating = !g.youAreCheating;
      keysactive.delete("KeyC");
    }
  }

  if (g.superTyrian) g.youAreCheating = false;

  /* {CHEAT-SKIP LEVEL} */
  if (k("F2") && k("F6") && (k("F7") || k("F8")) && !k("F9") && !g.superTyrian && g.superArcadeMode === SA_NONE) {
    // (isNetworkGame: skipLevelRequest)
    g.levelTimer = true;
    g.levelTimerCountdown = 0;
    g.endLevel = true;
    g.levelEnd = 40;
  }
}

/** The C's keyboardInput.sym for the title's codes: the key as uppercase ASCII, or '\0'. */
export function specialNameChar(key: string): string {
  // char ch = sym >= 0 && sym < 0x80 ? toupper((char)sym) : '\0';
  return key.length === 1 && key.charCodeAt(0) < 0x80 ? key.toUpperCase() : "\0";
}

/**
 * titleScreen's specialNameProgress (tyrian2.c L3216, L3405-3445): one counter per code; a key that
 * continues a code advances it, any other key sets it back to 0 (without starting it again, so
 * "SSTEALTH" doesn't count). `key` returns the code completed (0-based specialName index), or -1.
 * Code i + 1 is the Super Arcade mode it starts (SA_NONE + 1 .. SA_NORTSHIPZ), then SA_DESTRUCT
 * and SA_ENGAGE (Super Tyrian).
 */
export class SpecialNameMatcher {
  /** specialNameProgress[SA_ENGAGE]. */
  readonly progress: number[];

  /** @param specialName the nine codes from tyrian.hdt (helptext.c specialName[9][10]). */
  constructor(private readonly specialName: readonly string[]) {
    this.progress = new Array<number>(SA_ENGAGE).fill(0);
  }

  key(ch: string): number {
    for (let i = 0; i < SA_ENGAGE; i++) {
      // The C's char[10]: nine characters at most, zero-padded.
      const name = (this.specialName[i] ?? "").slice(0, 9);
      const at = (n: number) => name[n] ?? "\0";
      if (this.progress[i] >= 10 - 1 || ch !== at(this.progress[i])) {
        this.progress[i] = 0;
        continue;
      }

      this.progress[i]++;

      if (at(this.progress[i]) === "\0") {
        // The C returns here, leaving this code's counter at its end, where a key without a
        // character ('\0', such as an arrow) would complete it again once the title comes back. A
        // finished code starts over instead.
        this.progress.fill(0);
        return i;
      }
    }
    return -1;
  }

  /** Whether some code has two or more of its letters typed (so the next key is likely meant for it). */
  get typing(): boolean {
    return this.progress.some((p) => p >= 2);
  }
}

/** What a completed title code starts (tyrian2.c L3423-3443). */
export type TitleCode =
  /** newSuperArcadeGame(index): Super Arcade with SAShip[index], superArcadeMode = index + 1. */
  | { kind: "superArcade"; index: number }
  /** loadDestruct: JE_destructGame. */
  | { kind: "destruct" }
  /** JE_whoa, then newSuperTyrianGame. */
  | { kind: "superTyrian" };

export function titleCodeFor(index: number): TitleCode {
  if (index + 1 === SA_DESTRUCT) return { kind: "destruct" };
  if (index + 1 === SA_ENGAGE) return { kind: "superTyrian" };
  return { kind: "superArcade", index };
}

/** difficultySelect's menu items in order (menus.c L612-629): item i sets this difficultyLevel. */
export const difficultySelectLevels = [
  DIFFICULTY_EASY,
  DIFFICULTY_NORMAL,
  DIFFICULTY_HARD,
  DIFFICULTY_IMPOSSIBLE,
  DIFFICULTY_SUICIDE,
  DIFFICULTY_ZINGLON,
] as const;

/** difficulty_name[i + 1] is item i's label: as an array indexed by difficulty level. */
export function difficultyNamesByLevel(difficulty_name: readonly string[]): string[] {
  const out: string[] = [];
  difficultySelectLevels.forEach((level, i) => (out[level] = difficulty_name[i + 1] ?? ""));
  return out;
}

/** keyboard.c lordKeySyms. */
export const lordKeySyms = ["l", "o", "r", "d"] as const;

/** difficultySelect's locals: menuItemsVisibleCount (3 to 6) and lordProgress. */
export interface DifficultySelectState {
  visible: number;
  lordProgress: number;
}

export const newDifficultySelectState = (): DifficultySelectState => ({ visible: 3, lordProgress: 0 });

/**
 * One key on difficultySelect (menus.c L551-600). `sym` is the key's unshifted character in lower
 * case (SDL's keycode: Shift+] is still "]"), `shift` whether Shift was held, and `lordDown`
 * whether L, O, R and D are all held (lordKeySymsDown). Returns whether the key was taken by a code
 * that's under way (the host then gives it no other meaning).
 */
export function difficultySelectKey(s: DifficultySelectState, sym: string, shift: boolean, lordDown: boolean): boolean {
  switch (s.visible) {
    case 3:
      if (shift && sym === "g") {
        s.visible = 4;
        return true;
      }
      break;
    case 4:
      if (shift && sym === "]") {
        s.visible = 5;
        return true;
      }
      break;
    case 5: {
      if (lordDown) {
        s.visible = 6;
        return true;
      }
      // Due to key rollover, holding down 4 keys simultaneous may not always be possible,
      // so allow for typing them sequentially as well.
      if (s.lordProgress < lordKeySyms.length && sym === lordKeySyms[s.lordProgress]) {
        s.lordProgress += 1;
        if (s.lordProgress === lordKeySyms.length) s.visible = 6;
        return true;
      }
      s.lordProgress = 0;
      break;
    }
  }
  return false;
}

/** params.c: the LOOT parameter (richMode). Here a `?loot` in the page's address. */
export function applyCheatParams(search: string): void {
  const params = new URLSearchParams(search);
  if ([...params.keys()].some((k) => k.toUpperCase() === "LOOT")) g.richMode = true;
}
