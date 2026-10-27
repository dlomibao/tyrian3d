// The title screen's secret inputs: one key listener for all of them (DECISIONS.md D27, D32).
// - the codes typed on the title (titleScreen's specialName: STEALTH ... NORTSHIPZ for Super
//   Arcade, DESTRUCT, ENGAGE for Super Tyrian), matched by the arcade port's CodeMatcher
//   (src/sim/arcade.ts, the C's specialNameProgress loop). What a code starts is the title's
//   business (src/app/arcade.ts: the Super Arcade card and Super Tyrian's screen); DESTRUCT goes
//   to `destructHook`;
// - the hidden difficulties (difficultySelect, src/sim/cheats.ts): Shift+G, then Shift+], then
//   L O R D, which add Impossible, Suicide and Lord of the Game to the title's difficulty row.
//
// The C's title does nothing else with letters, but this one has shortcuts (L, O, H, M) and WASD
// moves the menus. So a key that continues a code already two letters in, or one of the hidden
// difficulty keys while its step is open, is taken by the listener; a code's first letter isn't (S
// and D still move, and the title puts its menus back once a code completes), and nor is a key that
// breaks a code off (H after "ST" still opens High Scores). Modifier keys alone and key repeats
// don't count (so Shift can be held for Shift+G or Super Tyrian's Suicide), and nor do keys with
// Ctrl, Alt or Cmd.

import type { FileMap } from "../assets/files";
import type { SoundEffects } from "../audio/sfx";
import { CodeMatcher, codeChar, titleCode, type TitleCode } from "../sim/arcade";
import { difficultySelectKey, lordKeySyms, newDifficultySelectState, type DifficultySelectState } from "../sim/cheats";
import { V_DATA_CUBE } from "../sim/sndmast";
import { button, h, showScreen, title } from "../ui";

export type { TitleCode } from "../sim/arcade";

/** What the Destruct game gets from the title. */
export interface DestructContext {
  files: FileMap;
  sfx: SoundEffects;
  /** specialName[9] from tyrian.hdt: [7] is "DESTRUCT". */
  specialName: string[];
}

/**
 * MERGE HOOK (destruct): JE_destructGame (destruct.c), opened by typing DESTRUCT on the title. The
 * Destruct module sets it, e.g. `destructHook.open = (ctx) => openDestruct(ctx)`; it resolves when
 * Destruct is over, back on the title. While it's null, the code shows a "not in this build yet"
 * notice.
 */
export const destructHook: { open: ((ctx: DestructContext) => Promise<void>) | null } = { open: null };

/** The DESTRUCT code (loadDestruct): the Destruct game, or the notice while there isn't one. */
export function runDestruct(ctx: DestructContext): Promise<void> {
  if (destructHook.open) return destructHook.open(ctx);
  return showDestructNotice(ctx);
}

/** A notice over the title: DESTRUCT was typed, but the Destruct game isn't in this build. */
function showDestructNotice(ctx: DestructContext): Promise<void> {
  ctx.sfx.playSampleNum(V_DATA_CUBE);
  const heading = ctx.specialName[7]?.trim() || "DESTRUCT";
  return new Promise((resolve) => {
    const done = () => {
      if (!screen.open) return;
      screen.close();
      resolve();
    };
    const screen = showScreen({
      id: "title-code",
      backdrop: "hangar",
      layout: "narrow",
      label: heading,
      over: true,
      onIntent: () => {
        done();
        return true;
      },
      onBack: done,
    });
    screen.add(
      title(heading, "Code accepted"),
      h("p", { class: "message-line", text: "This mode isn't in this build yet." }),
      h("div", { class: "ui-actions" }, button({ label: "Back", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
    );
  });
}

/** The keydown fields the listener reads. */
export type TitleKey = Pick<KeyboardEvent, "key" | "code" | "shiftKey" | "ctrlKey" | "metaKey" | "altKey" | "repeat"> & {
  getModifierState?: (key: string) => boolean;
};

export interface TitleCodeListenerOptions {
  /** specialName from tyrian.hdt. */
  specialName: readonly string[];
  /** How many difficulties the row shows now (3 to 6). */
  difficultyVisible: number;
  /** A code was completed, by this key (Super Tyrian reads Shift or Scroll Lock from it). */
  onCode: (code: TitleCode, e: TitleKey) => void;
  /** A hidden difficulty was revealed: the row should show `visible` of them. */
  onDifficultyVisible: (visible: number) => void;
  /**
   * The next key may start a code (none is under way): the title remembers its menus, to put them
   * back when a code completes, since a code's first letter can be a WASD move (STEALTH's S,
   * WEIRD's W, DESTRUCT's D).
   */
  onCodeMayStart?: () => void;
}

/** Keys that are only modifiers: they don't reset a code (a deviation from the C, so Shift can be held). */
const MODIFIER_KEYS = new Set(["Shift", "CapsLock", "ScrollLock", "NumLock", "Control", "Alt", "AltGraph", "Meta", "OS"]);

/** The title's secret keys: give it every key first (Screen onKey); true means it took the key. */
export class TitleCodeListener {
  readonly matcher: CodeMatcher;
  readonly difficulty: DifficultySelectState;
  /** keyboard.c lordKeySymsDown. */
  private readonly lordDown = new Set<string>();
  private readonly onKeyUp = (e: KeyboardEvent) => this.lordDown.delete(keySym(e));

  constructor(private readonly opts: TitleCodeListenerOptions) {
    // titleScreen's specialNameProgress: the nine codes (helptext.c specialName[9][10]).
    this.matcher = new CodeMatcher(opts.specialName.slice(0, 9));
    this.difficulty = newDifficultySelectState();
    this.difficulty.visible = Math.max(3, Math.min(6, opts.difficultyVisible));
    window.addEventListener("keyup", this.onKeyUp);
  }

  key(e: TitleKey): boolean {
    if (e.ctrlKey || e.metaKey || e.altKey || e.repeat || MODIFIER_KEYS.has(e.key)) return false;
    const sym = keySym(e);
    if ((lordKeySyms as readonly string[]).includes(sym)) this.lordDown.add(sym);

    const before = this.difficulty.visible;
    const tookDifficulty = difficultySelectKey(this.difficulty, sym, e.shiftKey, lordKeySyms.every((k) => this.lordDown.has(k)));
    if (this.difficulty.visible !== before) this.opts.onDifficultyVisible(this.difficulty.visible);

    if (this.matcher.progress.every((p) => p === 0)) this.opts.onCodeMayStart?.();
    const done = this.matcher.feed(codeChar(e.key));
    if (done >= 0) {
      // The C returns with this code's counter at its end, where a key without a character (an
      // arrow) would complete it again once the title comes back. A finished code starts over.
      this.matcher.reset();
      this.opts.onCode(titleCode(done), e);
      return true;
    }
    // A letter carrying on a code isn't also a shortcut (the codes hold L, O, H, M and WASD).
    return tookDifficulty || this.matcher.continuing();
  }

  dispose(): void {
    window.removeEventListener("keyup", this.onKeyUp);
  }
}

/** SDL's keycode for a key: its unshifted character, lower case (Shift+] is "]"). */
export function keySym(e: Pick<KeyboardEvent, "key" | "code">): string {
  if (e.code === "BracketRight") return "]";
  if (/^Key[A-Z]$/.test(e.code)) return e.key.length === 1 ? e.key.toLowerCase() : e.code.slice(3).toLowerCase();
  return e.key.length === 1 ? e.key.toLowerCase() : "";
}
