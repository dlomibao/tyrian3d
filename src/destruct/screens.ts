// Destruct's screens, on the interface framework (src/ui/) over the battlefield: the title
// (JE_introScreen), the mode select (JE_modeSelect), the help (JE_helpScreen) and the pause
// (JE_pauseScreen). Their texts are the game data's (helptext.c destructHelp, destructModeName,
// specialName[7], miscText[22], [64], [65]).

import { h, keyHints, MenuList, showScreen, title, type Screen, type ScreenOptions } from "../ui";
import { DESTRUCT_MODES, MODE_CUSTOM, MODE_NONE, PLAYER_LEFT, PLAYER_RIGHT, type DestructGame } from "./sim";

export interface DestructTexts {
  /** specialName[7]: "DESTRUCT". */
  name: string;
  /** destructHelp[25]: the help screen's lines. */
  help: string[];
  /** weaponNames[17] */
  weaponNames: string[];
  /** destructModeName[5] */
  modeNames: string[];
  /** miscText[22] "PAUSED", [64] "Press F1 for help.", [65] "F10 toggles left CPU/Human player." */
  paused: string;
  pressF1: string;
  f10Toggles: string;
}

/**
 * A screen that any key, pad button or tap closes (the C's `keyboardGetInput(NULL)` waits).
 * Key repeats don't count, so a key still held from the game doesn't close it at once.
 */
function anyKeyScreen(opts: Omit<ScreenOptions, "onKey" | "onIntent" | "onPadButton">, fill: (screen: Screen) => void): Promise<void> {
  return new Promise((resolve) => {
    let open = true;
    const close = () => {
      if (!open) return;
      open = false;
      screen.close();
      resolve();
    };
    const screen = showScreen({
      ...opts,
      onKey: (e) => {
        if (!e.repeat) close();
        return true;
      },
      onIntent: () => {
        close();
        return true;
      },
      onPadButton: close,
    });
    screen.root.addEventListener("pointerdown", close);
    fill(screen);
  });
}

/** JE_introScreen: the name and two hints over the black field; any key goes on. */
export function showIntro(t: DestructTexts): Promise<void> {
  return anyKeyScreen({ id: "destruct-intro", backdrop: "none", layout: "narrow" }, (screen) =>
    screen.add(
      h("div", { class: "destruct-intro" }, h("h1", { class: "destruct-intro__name", text: t.name }), h("p", { text: t.pressF1 }), h("p", { text: t.f10Toggles })),
      keyHints([{ key: "Any key", pad: "A", touch: "Tap", label: "Continue" }]),
    ),
  );
}

/**
 * JE_modeSelect: the modes (Custom only with allow_custom), Escape to leave. Below them, who plays
 * each side (the C's F10/F11 toggles, as rows too) and the help.
 */
export function showModeSelect(game: DestructGame, t: DestructTexts, initial: number, onHelp: () => Promise<void>): Promise<number> {
  return new Promise((resolve) => {
    const modes = t.modeNames.slice(0, DESTRUCT_MODES);
    if (game.config.allow_custom) modes.push("Custom");
    const extra = ["left", "right", "help", "quit"] as const;
    const side = (p: number) => (game.destruct_player[p].is_cpu ? "Computer" : "Human");
    const items = () => [
      ...modes.map((label) => ({ label, class: "destruct-mode" })),
      { label: "Left player", detail: `${side(PLAYER_LEFT)} · F10`, class: "destruct-side" },
      { label: "Right player", detail: `${side(PLAYER_RIGHT)} · F11`, class: "destruct-side" },
      { label: "Help", detail: "F1" },
      { label: "Leave Destruct", detail: "Esc" },
    ];
    let busy = false;
    const done = (mode: number) => {
      screen.close();
      resolve(mode);
    };
    const toggle = (p: number) => {
      game.destruct_player[p].is_cpu = !game.destruct_player[p].is_cpu;
      list.setItems(items());
    };
    const help = () => {
      if (busy) return;
      busy = true;
      void screen.aside(onHelp).finally(() => (busy = false));
    };
    const list = new MenuList({
      items: items(),
      focused: Math.min(Math.max(0, initial), modes.length - 1),
      label: "Mode",
      onSelect: (i) => {
        if (i < modes.length) return done(i === DESTRUCT_MODES ? MODE_CUSTOM : i);
        const what = extra[i - modes.length];
        if (what === "left") toggle(PLAYER_LEFT);
        else if (what === "right") toggle(PLAYER_RIGHT);
        else if (what === "help") help();
        else done(MODE_NONE);
      },
    });
    const screen = showScreen({
      id: "destruct-modes",
      backdrop: "none",
      layout: "narrow",
      onBack: () => done(MODE_NONE),
      onKey: (e) => {
        if (e.type !== "keydown") return false;
        if (e.code === "F10" || e.code === "F11") {
          e.preventDefault();
          toggle(e.code === "F10" ? PLAYER_LEFT : PLAYER_RIGHT);
          return true;
        }
        if (e.code === "F1") {
          e.preventDefault();
          help();
          return true;
        }
        return false;
      },
    });
    screen.add(
      title(t.name, "Choose a game"),
      list,
      keyHints([
        { key: "↑↓", pad: "✛", label: "Move" },
        { key: "Enter", pad: "A", touch: "Tap", label: "Play" },
        { key: "Esc", pad: "B", label: "Leave" },
      ]),
    );
  });
}

/** JE_helpScreen: each side's keys from destructHelp, as the C lays them out in pairs. */
export function showHelp(t: DestructTexts): Promise<void> {
  const side = (i: number) => {
    const rows: HTMLElement[] = [];
    // destructHelp[i * 12 + 2 .. 11]: key, action, key, action...
    for (let j = 2; j < 12; j += 2) rows.push(h("dt", { text: t.help[i * 12 + j] ?? "" }), h("dd", { text: t.help[i * 12 + j + 1] ?? "" }));
    return h(
      "section",
      { class: "destruct-help__side" },
      h("h3", { text: t.help[i * 12] ?? "" }),
      h("p", { class: "destruct-help__note", text: t.help[i * 12 + 1] ?? "" }),
      h("dl", {}, ...rows),
    );
  };
  return anyKeyScreen({ id: "destruct-help", backdrop: "none", layout: "center", over: true }, (screen) =>
    screen.add(
      title("Help", t.name),
      h("div", { class: "destruct-help" }, side(0), side(1)),
      h("p", { class: "destruct-help__foot", text: `${t.help[24] ?? ""} · P pauses · Esc chooses another game · F10 / F11 switch a side between computer and human` }),
      keyHints([{ key: "Any key", pad: "A", touch: "Tap", label: "Back" }]),
    ),
  );
}

/** JE_pauseScreen: "PAUSED" over the field until any key. */
export function showPaused(t: DestructTexts): Promise<void> {
  return anyKeyScreen({ id: "destruct-paused", backdrop: "none", layout: "narrow" }, (screen) =>
    screen.add(h("h2", { class: "destruct-paused", text: t.paused }), keyHints([{ key: "Any key", pad: "A", touch: "Tap", label: "Resume" }])),
  );
}
