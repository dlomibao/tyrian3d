// [two-player] gameplaySelect (menus.c L37-218): after the title's episode and difficulty, which
// kind of game to start. The C asks it first (gameplay, then episode, then difficulty); here the
// title already holds the episode and difficulty, so this screen follows it, and Escape goes back
// to the title. The names are the data's gameplay_name (tyrian.hdt): "1 Player Full Game",
// "1 Player Arcade", "2 Player Arcade" and "Network Game". A mode the port can't start yet is shown
// but can't be picked (the C's Network Game only plays a sound, too).

import { keyHints, MenuList, showScreen, title } from "../ui";

/** The C's MenuItemIndex. */
export type GameplayMode = "fullGame" | "arcade" | "twoPlayerArcade" | "network";

export const GAMEPLAY_MODES: readonly GameplayMode[] = ["fullGame", "arcade", "twoPlayerArcade", "network"];

const FALLBACK_NAMES = ["Select Gameplay", "1 Player Full Game", "1 Player Arcade", "2 Player Arcade", "Network Game"];

export interface GameplaySelectOptions {
  /** gameplay_name from the data: [0] the menu title, then the four modes. */
  names: readonly string[];
  /** The modes that can be started. */
  available: ReadonlySet<GameplayMode>;
  /** The mode the cursor starts on (the last one played). */
  initial?: GameplayMode;
}

/** The gameplay menu. Resolves with the chosen mode, or null to go back to the title. */
export function showGameplaySelect(opts: GameplaySelectOptions): Promise<GameplayMode | null> {
  const name = (i: number) => opts.names[i]?.trim() || FALLBACK_NAMES[i];
  return new Promise((resolve) => {
    const done = (mode: GameplayMode | null) => {
      if (!screen.open) return;
      screen.close();
      resolve(mode);
    };
    const screen = showScreen({
      id: "gameplay",
      backdrop: "title",
      layout: "narrow",
      label: name(0),
      onBack: () => done(null),
    });
    const first = Math.max(0, GAMEPLAY_MODES.indexOf(opts.initial ?? "fullGame"));
    const list = new MenuList({
      label: name(0),
      items: GAMEPLAY_MODES.map((mode, i) => ({
        label: name(i + 1),
        disabled: !opts.available.has(mode),
        ...(opts.available.has(mode) ? {} : { detail: "Not available yet" }),
      })),
      focused: opts.available.has(GAMEPLAY_MODES[first]) ? first : 0,
      onSelect: (i) => done(GAMEPLAY_MODES[i]),
    });
    screen.add(
      title(name(0), "New game"),
      list,
      keyHints([
        { key: "↑↓", pad: "✛", label: "Move" },
        { key: "Enter", pad: "A", touch: "Tap", label: "Start" },
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    );
  });
}
