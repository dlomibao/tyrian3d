// The pause screen during a level, and the on-screen pause button for touch screens.
//
// Escape, P or the pad's Start pause (src/app/controls.ts); here Escape, P, Start or B resume.
// "Quit to title" ends the game after a confirmation. (OpenTyrian's in-game menu, JE_inGameSetup in
// mainint.c, also has a Quit, but it sets reallyEndLevel and playerEndLevel, so start_level reloads
// the "LAST LEVEL" backup and goes back to the item screen; a way back to the title is what's
// missing here, and retrying is what a death already does: DECISIONS.md D14.)
//
// "Options" opens the full settings screen (the title's and the shop's, with the same host) over this
// one, so every setting is reachable from inside a level on any input (D102).

import "./pause.css";
import { h, keyHints, MenuList, showScreen, title } from "../ui";
import { showOptions, type OptionsHost } from "./options";
import { consoleBridge } from "./consoleBridge";

export type PauseChoice = "resume" | "quit";

/** The pause menu's rows, in order. */
export const PAUSE_ITEMS = ["Resume", "Options", "Quit to title"] as const;

/** Show the pause screen over the frozen game; resolves with the player's choice. */
export function showPause(host: OptionsHost): Promise<PauseChoice> {
  return new Promise((resolve) => {
    let asking = false;
    let inOptions = false;
    const done = (choice: PauseChoice) => {
      if (consoleBridge.leave?.screen === screen) consoleBridge.leave = null;
      screen.close();
      resolve(choice);
    };
    const quit = async () => {
      if (asking) return;
      asking = true;
      const sure = await screen.confirm("Your progress in this game will be lost.", { title: "Quit to title?", yes: "Quit", no: "Keep playing" });
      asking = false;
      if (sure) done("quit");
    };
    const options = async () => {
      if (inOptions) return;
      inOptions = true;
      await showOptions(host); // over this screen; the game stays paused underneath
      inOptions = false;
    };
    const screen = showScreen({
      id: "pause",
      backdrop: "none",
      layout: "narrow",
      label: "Paused",
      onKey: (e) => {
        if (e.code !== "KeyP") return false;
        done("resume");
        return true;
      },
      onIntent: (intent) => {
        if (intent !== "start") return false;
        done("resume");
        return true;
      },
      onBack: () => done("resume"),
    });
    const menu = new MenuList({
      label: "Paused",
      items: PAUSE_ITEMS.map((label) => ({ label })),
      onSelect: (i) => (i === 0 ? done("resume") : i === 1 ? void options() : void quit()),
    });
    // The debug console's jumps (D109) resume the game, which then leaves the level.
    consoleBridge.leave = { screen, go: () => done("resume") };
    screen.add(
      title("Paused"),
      menu,
      keyHints([
        // No touch glyph: on a touch screen the two buttons say it all (the hints hide there).
        { key: "Esc", pad: "Start", label: "Resume" },
        { key: "Enter", pad: "A", label: "Choose" },
      ]),
    );
  });
}

/** A pause button in the corner for touch screens (CSS hides it when a mouse or keys were used last). */
export class PauseButton {
  private readonly el: HTMLButtonElement;

  constructor(onPress: () => void) {
    this.el = h("button", { class: "pause-button", attrs: { type: "button", "aria-label": "Pause", tabindex: "-1" } }, h("span"), h("span"));
    // pointerdown, not click: the canvas's touch steering would otherwise see the finger first.
    this.el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      onPress();
    });
    this.el.hidden = true;
    document.body.append(this.el);
  }

  set visible(v: boolean) {
    this.el.hidden = !v;
  }
}
