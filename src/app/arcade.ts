// The arcade games' screens: what the codes typed at the title start (titleScreen's specialName,
// tyrian2.c L3402-3446; src/app/titleCodes.ts listens for them), the "Super Arcade Mode" card
// (newSuperArcadeGame), Super Tyrian's "Prepare to play..." (newSuperTyrianGame), the Trent message
// after beating Super Tyrian (JE_tyrianHalt), and the bits the item screen and HUD show in an
// arcade game. The rules are in src/sim/arcade.ts; screens.ts only places these on the title.

import "./arcade.css";
import type { NewGameChoice, TitleCode } from "../sim/arcade";
import { parseMenuText, type MenuText } from "../sim/helptext";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { V_DANGER, V_DATA_CUBE } from "../sim/sndmast";
import { g, SA, SA_NONE } from "../sim/state";
import { SAShip } from "../sim/varz";
import { button, h, showScreen, title, ui } from "../ui";

/** play_song(16): Super Tyrian's "Prepare to play..." (0-based, as run.ts's song numbers). */
const SONG_SUPER_TYRIAN = 16;

/** What the title needs for the arcade games (from tyrian.hdt and the host). */
export interface ArcadeTitleOptions {
  /** superShips[11]: "Super Arcade Mode", the seven ships, "Main Weapon:", "Special Weapon:", "Stalker 21.126". */
  superShips: string[];
  /** specialName[9]: the codes typed at the title (STEALTH .. NORTSHIPZ, DESTRUCT, ENGAGE). */
  specialName: string[];
  /** pName[0] ("Tyrian"): with miscTextB[4] ("SUPER"), Super Tyrian's name. */
  planetName0: string;
  /** The DESTRUCT code (loadDestruct): the Destruct game, or its notice (src/app/titleCodes.ts runDestruct). */
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
}

export interface ArcadeTitle {
  /** A smuggled ship, when a Super Arcade start was backed out of. */
  smuggledShip(): number | undefined;
  /** A code completed on the title (src/app/titleCodes.ts TitleCodeListener), by key `e`. */
  code(code: TitleCode, e: { shiftKey: boolean; getModifierState?: (key: string) => boolean }): void;
}

/**
 * The title's arcade part: what the codes typed at the title start. (The kind of game, gameplaySelect,
 * is asked after the title: src/app/gameplaySelect.ts.)
 */
export function arcadeTitle(opts: ArcadeTitleOptions, ctx: ArcadeTitleContext): ArcadeTitle {
  let smuggled: number | undefined;

  const code: ArcadeTitle["code"] = (code, e) => {
    if (code.kind === "destruct") {
      // loadDestruct = true: the Destruct game (not part of the arcade port).
      if (opts.onDestruct) ctx.open(opts.onDestruct, true, () => {});
    } else if (code.kind === "superTyrian") {
      opts.sound?.(V_DATA_CUBE);
      // keysactive[SDL_SCANCODE_SCROLLLOCK] when the code completes; Shift too, as Macs have no Scroll Lock.
      const suicide = Boolean(e.getModifierState?.("ScrollLock") || e.shiftKey);
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

  return { smuggledShip: () => smuggled, code };
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
