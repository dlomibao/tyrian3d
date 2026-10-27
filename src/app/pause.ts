// The pause screen during a level, and the on-screen pause button for touch screens.
//
// Escape, P or the pad's Start pause (src/app/controls.ts); here Escape, P, Start or B resume.
// "Quit to title" ends the game after a confirmation. (OpenTyrian's in-game menu, JE_inGameSetup in
// mainint.c, also has a Quit, but it sets reallyEndLevel and playerEndLevel, so start_level reloads
// the "LAST LEVEL" backup and goes back to the item screen; a way back to the title is what's
// missing here, and retrying is what a death already does: DECISIONS.md D14.)

import "./pause.css";
import { h, keyHints, MenuList, showScreen, title } from "../ui";

export type PauseChoice = "resume" | "quit";

/** Show the pause screen over the frozen game; resolves with the player's choice. */
export function showPause(): Promise<PauseChoice> {
  return new Promise((resolve) => {
    let asking = false;
    const done = (choice: PauseChoice) => {
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
      items: [{ label: "Resume" }, { label: "Quit to title" }],
      onSelect: (i) => (i === 0 ? done("resume") : void quit()),
    });
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
