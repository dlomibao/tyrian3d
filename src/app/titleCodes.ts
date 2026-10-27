// The title screen's secret inputs (DECISIONS.md D32), on the rules in src/sim/cheats.ts:
// - the codes typed on the title (titleScreen's specialName: STEALTH ... NORTSHIPZ for Super
//   Arcade, DESTRUCT, ENGAGE for Super Tyrian), which go to the features that own them through
//   `titleCodeHooks`;
// - the hidden difficulties (difficultySelect): Shift+G, then Shift+], then L O R D, which add
//   Impossible, Suicide and Lord of the Game to the title's difficulty row.
//
// The C's title does nothing else with letters, but this one has shortcuts (L, O, H, M) and WASD
// moves the menus. So a key that continues a code already two letters in, or one of the hidden
// difficulty keys while its step is open, is taken by the code; a code's first letter isn't (S and
// D still move), and nor is a key that breaks a code off (H after "ST" still opens High Scores).

import type { FileMap } from "../assets/files";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import {
  difficultySelectKey,
  lordKeySyms,
  newDifficultySelectState,
  specialNameChar,
  SpecialNameMatcher,
  titleCodeFor,
  type DifficultySelectState,
  type TitleCode,
} from "../sim/cheats";
import { V_DATA_CUBE } from "../sim/sndmast";
import { button, h, showScreen, title } from "../ui";

export type { TitleCode } from "../sim/cheats";

/** What a title code's feature gets from the game. */
export interface TitleCodeContext {
  files: FileMap;
  sfx: SoundEffects;
  music: MusicPlayer;
  /** superShips[11] from tyrian.hdt: [0] "Super Arcade Mode", [i + 1] code i's ship. */
  superShips: string[];
  /** specialName[9] from tyrian.hdt: the codes. */
  specialName: string[];
}

/**
 * MERGE HOOK (cheats): the features the title's codes start. Each is set by the module that builds
 * it (Super Arcade and Super Tyrian by the arcade modes, Destruct by its own module), for example
 * `titleCodeHooks.destruct = (ctx) => openDestruct(ctx)`. Until one is set, its code shows a short
 * notice and the title stays.
 */
export interface TitleCodeHooks {
  /**
   * newSuperArcadeGame(index) (tyrian2.c): choose the episode and difficulty, set up the game in
   * `g` (superArcadeMode = index + 1, SAShip[index], JE_initEpisode...) and resolve true to start
   * it the way a loaded game starts (TitleChoice.loaded), or false to stay on the title.
   */
  superArcade?: (index: number, ctx: TitleCodeContext) => Promise<boolean>;
  /** newSuperTyrianGame (tyrian2.c), after JE_whoa: as superArcade. */
  superTyrian?: (ctx: TitleCodeContext) => Promise<boolean>;
  /** JE_destructGame (destruct.c): play Destruct; resolves when it's over, back on the title. */
  destruct?: (ctx: TitleCodeContext) => Promise<void>;
}

export const titleCodeHooks: TitleCodeHooks = {};

/**
 * Run a completed code: its hook, or a notice when the feature isn't there. Resolves true when a
 * game was set up and should start.
 */
export async function runTitleCode(code: TitleCode, ctx: TitleCodeContext): Promise<boolean> {
  const hooks = titleCodeHooks;
  if (code.kind === "superArcade" && hooks.superArcade) return hooks.superArcade(code.index, ctx);
  if (code.kind === "superTyrian" && hooks.superTyrian) {
    ctx.sfx.playSampleNum(V_DATA_CUBE); // JE_playSampleNum(V_DATA_CUBE) before JE_whoa
    return hooks.superTyrian(ctx);
  }
  if (code.kind === "destruct" && hooks.destruct) {
    await hooks.destruct(ctx);
    return false;
  }
  await showCodeNotice(code, ctx);
  return false;
}

/** The name a code's notice shows: the ship for Super Arcade, else the code itself. */
export function titleCodeName(code: TitleCode, ctx: Pick<TitleCodeContext, "superShips" | "specialName">): { heading: string; name: string } {
  const t = (s: string | undefined, fallback: string) => s?.trim() || fallback;
  switch (code.kind) {
    case "superArcade":
      return { heading: t(ctx.superShips[0], "Super Arcade Mode"), name: t(ctx.superShips[code.index + 1], t(ctx.specialName[code.index], "")) };
    case "destruct":
      return { heading: t(ctx.specialName[7], "DESTRUCT"), name: "" };
    case "superTyrian":
      return { heading: "Super Tyrian", name: t(ctx.specialName[8], "ENGAGE") };
  }
}

/** A notice over the title for a code whose feature isn't in this build. */
function showCodeNotice(code: TitleCode, ctx: TitleCodeContext): Promise<void> {
  ctx.sfx.playSampleNum(V_DATA_CUBE);
  const { heading, name } = titleCodeName(code, ctx);
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
      ...(name ? [h("p", { class: "message-line", text: name })] : []),
      h("p", { class: "message-line", text: "This mode isn't in this build yet." }),
      h("div", { class: "ui-actions" }, button({ label: "Back", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
    );
  });
}

export interface TitleCodeListenerOptions {
  /** specialName from tyrian.hdt. */
  specialName: readonly string[];
  /** How many difficulties the row shows now (3 to 6). */
  difficultyVisible: number;
  onCode: (code: TitleCode) => void;
  /** A hidden difficulty was revealed: the row should show `visible` of them. */
  onDifficultyVisible: (visible: number) => void;
}

/** The title's code keys: give it every key first (Screen onKey); true means it took the key. */
export class TitleCodeListener {
  readonly matcher: SpecialNameMatcher;
  readonly difficulty: DifficultySelectState;
  /** keyboard.c lordKeySymsDown. */
  private readonly lordDown = new Set<string>();
  private readonly onKeyUp = (e: KeyboardEvent) => this.lordDown.delete(e.key.toLowerCase());

  constructor(private readonly opts: TitleCodeListenerOptions) {
    this.matcher = new SpecialNameMatcher(opts.specialName);
    this.difficulty = newDifficultySelectState();
    this.difficulty.visible = Math.max(3, Math.min(6, opts.difficultyVisible));
    window.addEventListener("keyup", this.onKeyUp);
  }

  key(e: Pick<KeyboardEvent, "key" | "code" | "shiftKey" | "ctrlKey" | "metaKey" | "altKey" | "repeat">): boolean {
    if (e.ctrlKey || e.metaKey || e.altKey) return false;
    const sym = keySym(e);
    if ((lordKeySyms as readonly string[]).includes(sym) && !e.repeat) this.lordDown.add(sym);

    const before = this.difficulty.visible;
    const tookDifficulty = difficultySelectKey(this.difficulty, sym, e.shiftKey, lordKeySyms.every((k) => this.lordDown.has(k)));
    if (this.difficulty.visible !== before) this.opts.onDifficultyVisible(this.difficulty.visible);

    const done = this.matcher.key(specialNameChar(e.key));
    if (done >= 0) {
      this.opts.onCode(titleCodeFor(done));
      return true;
    }
    return tookDifficulty || this.matcher.typing;
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
