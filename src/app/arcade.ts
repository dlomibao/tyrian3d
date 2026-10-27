// The arcade games' screens: the title's Game row (gameplaySelect, menus.c) and its typed codes
// (titleScreen's specialName, tyrian2.c L3402-3446), the "Super Arcade Mode" card
// (newSuperArcadeGame), Super Tyrian's "Prepare to play..." (newSuperTyrianGame), the Trent message
// after beating Super Tyrian (JE_tyrianHalt), and the bits the item screen and HUD show in an
// arcade game. The rules are in src/sim/arcade.ts; screens.ts only places these on the title.

import "./arcade.css";
import { CodeMatcher, codeChar, titleCode, type GameplayMode, type NewGameChoice } from "../sim/arcade";
import { parseMenuText, type MenuText } from "../sim/helptext";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { V_DANGER, V_DATA_CUBE } from "../sim/sndmast";
import { g, SA, SA_NONE } from "../sim/state";
import { SAShip } from "../sim/varz";
import { button, h, MenuList, showScreen, title, ui, type KeyHint } from "../ui";

/** play_song(16): Super Tyrian's "Prepare to play..." (0-based, as run.ts's song numbers). */
const SONG_SUPER_TYRIAN = 16;

/** What the title needs for the arcade games (from tyrian.hdt and the host). */
export interface ArcadeTitleOptions {
  /** gameplay_name[5]: [0] the menu title, then 1 Player Full Game, 1 Player Arcade, 2 Player Arcade, Network. */
  gameplayName: string[];
  /** superShips[11]: "Super Arcade Mode", the seven ships, "Main Weapon:", "Special Weapon:", "Stalker 21.126". */
  superShips: string[];
  /** specialName[9]: the codes typed at the title (STEALTH .. NORTSHIPZ, DESTRUCT, ENGAGE). */
  specialName: string[];
  /** pName[0] ("Tyrian"): with miscTextB[4] ("SUPER"), Super Tyrian's name. */
  planetName0: string;
  /** [two-player] Whether 2 Player Arcade can be chosen (src/sim/arcade.ts twoPlayerArcade). */
  twoPlayerArcade: boolean;
  /** [destruct] The DESTRUCT code (loadDestruct): the Destruct game, if there is one. */
  onDestruct?: () => Promise<void>;
  /** JE_playSampleNum and play_song, for the codes' sounds and Super Tyrian's song. */
  sound?: (sample: number) => void;
  song?: (song: number) => void;
}

/** What the title tells the arcade part: the episode and difficulty chosen now, by name. */
export interface ArcadeTitleContext {
  episodeName(): string;
  /** difficulty_name for a level (Super Arcade plays one step above the one chosen). */
  difficultyName(level: number): string;
  difficulty(): number;
  /**
   * Open a screen over the title (its sub-screen runner: one at a time, input handed back after),
   * then call `then` with what it resolved to.
   */
  open<T>(run: () => Promise<T>, over: boolean, then: (result: T) => void): void;
  /** Start the game: the title resolves with these. */
  start(choice: Partial<NewGameChoice>): void;
  /**
   * Remember the title's choices before a key that may start a code, and put them back once a code
   * is typed: a code's first letter can be a WASD move (STEALTH's S, WEIRD's W, DESTRUCT's D).
   */
  mark(): void;
  restore(): void;
}

/** The modes in the title's Game row, in gameplaySelect's order. */
export const GAME_MODES: readonly GameplayMode[] = ["fullGame", "arcade", "twoPlayerArcade"];

/** Pad button for the Game row: RB (standard mapping 5), free on the title (LB is Load Game). */
export const GAME_MODE_PAD = { button: 5, glyph: "RB" } as const;

export interface ArcadeTitle {
  /** The Game row's label and choices, for the panel. Not one of the screen's controls. */
  nodes: HTMLElement[];
  mode(): GameplayMode;
  /** A smuggled ship, when a Super Arcade start was backed out of. */
  smuggledShip(): number | undefined;
  /** The title's onKey: the codes and the Game row's key (Tab). True when the key was used. */
  key(e: KeyboardEvent): boolean;
  /** The title's onPadButton: true when used. */
  padButton(button: number): boolean;
  hints: KeyHint[];
}

/** Short labels for the Game row (the row is narrow): gameplay_name without "1 Player ", and "2 Player" for 2 Player Arcade. */
function modeLabel(name: string | undefined, fallback: string): string {
  const n = name?.trim();
  return n ? n.replace(/^1 Player\s+/i, "").replace(/^(2 Player)\s+Arcade$/i, "$1") : fallback;
}

/** The title's arcade part: the Game row and the codes. */
export function arcadeTitle(opts: ArcadeTitleOptions, initial: GameplayMode | undefined, ctx: ArcadeTitleContext): ArcadeTitle {
  const enabled = (m: GameplayMode) => m !== "twoPlayerArcade" || opts.twoPlayerArcade;
  const items = GAME_MODES.map((m, i) => ({
    label: modeLabel(opts.gameplayName[i + 1], ["Full Game", "Arcade", "2 Player"][i]),
    disabled: !enabled(m),
  }));
  const row = new MenuList({
    label: opts.gameplayName[0]?.trim() || "Game",
    orientation: "horizontal",
    class: "title-mode",
    items,
    focused: Math.max(0, GAME_MODES.indexOf(initial && enabled(initial) ? initial : "fullGame")),
  });
  const cycle = () => {
    let i = row.focused;
    do i = (i + 1) % GAME_MODES.length;
    while (!enabled(GAME_MODES[i]));
    row.focus(i);
  };

  // titleScreen's specialNameProgress (tyrian2.c L3216): one matcher for the whole title.
  const codes = new CodeMatcher(opts.specialName.slice(0, 9));
  let smuggled: number | undefined;

  const typed = (i: number, e: KeyboardEvent) => {
    const code = titleCode(i);
    if (code.kind === "destruct") {
      // loadDestruct = true: the Destruct game (not part of the arcade port).
      if (opts.onDestruct) ctx.open(opts.onDestruct, false, () => {});
    } else if (code.kind === "superTyrian") {
      opts.sound?.(V_DATA_CUBE);
      // keysactive[SDL_SCANCODE_SCROLLLOCK] when the code completes; Shift too, as Macs have no Scroll Lock.
      const suicide = e.getModifierState?.("ScrollLock") || e.shiftKey;
      ctx.open(() => showSuperTyrianIntro(opts, suicide), true, () => ctx.start({ superTyrian: { suicide }, episode: 1 }));
    } else {
      const m = code.superArcadeMode;
      ctx.open(
        () => showSuperArcadeIntro(opts, ctx, m),
        true,
        (go) => {
          if (go) ctx.start({ superArcade: m });
          else smuggled = SAShip[m - 1]; // player[0].items.ship stays set (newGame's "smuggle")
        },
      );
    }
  };

  return {
    nodes: [h("span", { class: "ui-label", text: "Game" }), row.el],
    mode: () => GAME_MODES[row.focused],
    smuggledShip: () => smuggled,
    key(e) {
      if (e.code === "Tab" && !e.altKey && !e.ctrlKey && !e.metaKey) {
        cycle();
        return true;
      }
      // Modifier keys alone don't reset a code (the C's would: a deviation so Shift can be held).
      if (e.repeat || e.ctrlKey || e.metaKey || e.altKey || ["Shift", "CapsLock", "ScrollLock", "Control", "Alt", "Meta"].includes(e.key)) return false;
      if (codes.progress.every((p) => p === 0)) ctx.mark(); // this key may start a code
      const done = codes.feed(codeChar(e.key));
      if (done >= 0) {
        codes.reset();
        ctx.restore();
        typed(done, e);
        return true;
      }
      // A letter carrying on a code isn't also a shortcut (the codes hold L, O, H, M and WASD).
      return codes.continuing();
    },
    padButton(b) {
      if (b !== GAME_MODE_PAD.button) return false;
      cycle();
      return true;
    },
    hints: [{ key: "Tab", pad: GAME_MODE_PAD.glyph, label: "Game" }],
  };
}

/**
 * newSuperArcadeGame's card (tyrian2.c L3584-3597): "Super Arcade Mode", the ship's name and the
 * ship. The C asks for the episode and difficulty first; here the title has them, so the card
 * names them and starts (true) or goes back to the title (false).
 */
export function showSuperArcadeIntro(opts: ArcadeTitleOptions, ctx: ArcadeTitleContext, superArcadeMode: number): Promise<boolean> {
  return new Promise((resolve) => {
    const ship = SAShip[superArcadeMode - 1];
    const done = (go: boolean) => {
      if (!screen.open) return;
      screen.close();
      if (!go) ui.backdrop?.setShipGraphic?.(g.res.items.ships[1]?.shipGraphic ?? -1);
      resolve(go);
    };
    const screen = showScreen({
      id: "super-arcade",
      backdrop: "hangar",
      layout: "narrow",
      over: true,
      label: opts.superShips[0] ?? "Super Arcade Mode",
      onBack: () => done(false),
      onIntent: (intent) => {
        if (intent !== "accept" && intent !== "start") return false;
        done(true);
        return true;
      },
    });
    // blit_sprite2x2(148, 70, spriteSheet9, ships[player[0].items.ship].shipgraphic): the backdrop's model.
    ui.backdrop?.setShipGraphic?.(g.res.items.ships[ship]?.shipGraphic ?? -1);
    screen.add(
      title(opts.superShips[superArcadeMode]?.trim() ?? "", opts.superShips[0]?.trim() || "Super Arcade Mode"),
      h("p", { class: "arcade-detail", text: `${ctx.episodeName()} · ${ctx.difficultyName(ctx.difficulty() + 1)}` }),
      h(
        "div",
        { class: "ui-actions" },
        button({ label: "Back", variant: "ghost", hint: { key: "Esc", pad: "B" }, onPress: () => done(false) }),
        button({ label: "Start", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: () => done(true) }),
      ),
    );
  });
}

/**
 * newSuperTyrianGame's screen (tyrian2.c L3628-3660): what Super Tyrian is, its song and warning,
 * until any key (there's no way back).
 */
export function showSuperTyrianIntro(opts: ArcadeTitleOptions, suicide: boolean): Promise<void> {
  opts.song?.(SONG_SUPER_TYRIAN);
  opts.sound?.(V_DANGER);
  return new Promise((resolve) => {
    const done = () => {
      if (!screen.open) return;
      screen.close();
      resolve();
    };
    const screen = showScreen({
      id: "super-tyrian",
      backdrop: "space",
      layout: "narrow",
      over: true,
      label: "Super Tyrian",
      onIntent: () => {
        done();
        return true;
      },
      onKey: () => {
        done();
        return true;
      },
    });
    const lines = [
      "Cheat codes have been disabled.",
      `Difficulty level has been set to ${suicide ? "Suicide" : "Lord of Game"}.`,
      "It is imperative that you discover the special codes.",
      ...(suicide ? [] : ["(Next time, for an easier challenge hold down Shift or Scroll Lock.)"]),
      "Prepare to play...",
    ];
    screen.add(
      ...lines.map((text) => h("p", { class: "message-line", text })),
      title(`${g.miscTextB[4] ?? "SUPER"} ${opts.planetName0.trim()}`),
      h("div", { class: "ui-actions" }, button({ label: "Continue", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
    );
    screen.root.addEventListener("click", done);
  });
}

/**
 * trentWin: Super Tyrian beaten at Lord of Game. The C quits to DOS with these lines
 * (JE_tyrianHalt, varz.c L457-463; "TODO: Show on screen rather than logging"); here they're on
 * screen, and the game goes back to the title.
 */
export function showTrentWin(): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      if (!screen.open) return;
      screen.close();
      resolve();
    };
    const screen = showScreen({
      id: "message",
      backdrop: "space",
      layout: "narrow",
      label: "Sleep well",
      onIntent: () => {
        done();
        return true;
      },
    });
    screen.add(
      h("p", { class: "message-line", text: "Sleep well, Trent, you deserve the rest." }),
      h("p", { class: "message-line", text: "You now have permission to borrow my ship on your next mission." }),
      h("div", { class: "ui-actions" }, button({ label: "Title screen", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
    );
    screen.root.addEventListener("click", done);
  });
}

let menuText: { hdt: Uint8Array; text: MenuText } | null = null;
function texts(files: TyrianFiles): MenuText {
  const hdt = requireFile(files, "tyrian.hdt");
  if (menuText?.hdt !== hdt) menuText = { hdt, text: parseMenuText(hdt) };
  return menuText.text;
}

/**
 * The item screen's left side in a Super Arcade or Super Tyrian game (game_menu.c L645-655): the
 * ship's name, "Main Weapon:" and "Special Weapon:", instead of the ship illustration. Null in
 * other games.
 */
export function superArcadeLoadout(files: TyrianFiles): { heading: string; ship: string; mainWeapon: string; specialWeapon: string; special: string } | null {
  if (g.superArcadeMode === SA_NONE && !g.superTyrian) return null;
  const { superShips, pName } = texts(files);
  return {
    // (the C shows no heading; Super Tyrian's is its name, miscTextB[4] and pName[0])
    heading: g.superTyrian ? `${g.miscTextB[4] ?? "SUPER"} ${pName[0]?.trim() ?? "Tyrian"}` : (superShips[0]?.trim() ?? ""),
    ship: (g.superTyrian ? superShips[SA + 3] : superShips[g.superArcadeMode])?.trim() ?? "",
    mainWeapon: superShips[SA + 1]?.trim() ?? "",
    specialWeapon: superShips[SA + 2]?.trim() ?? "",
    special: g.res.items.specials[g.player[0].items.special]?.name.trim() ?? "",
  };
}

/**
 * The HUD's lives in an arcade game (JE_inGameDisplays, mainint.c L2862-2893): the extra lives
 * (*lives - 1, the front weapon's power), as the C's ship icons. Empty in a full game.
 * [two-player] twoPlayerMode shows both players'.
 */
export function hudLives(): string {
  if (!g.onePlayerAction) return "";
  const extra = Math.max(0, g.player[0].lives.value - 1);
  return `Lives ${extra >= 5 ? `▲×${extra}` : "▲".repeat(extra) || "–"}`;
}
