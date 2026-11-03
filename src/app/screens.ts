// Screens around the game: asking for the data, the title, and end-of-level messages, built with
// the interface framework (src/ui/README.md). The title is the original's two-step menu (D64: Start
// New Game, then the episode and difficulty; src/app/titleMenu.ts) and also opens Load Game, High
// Scores and Options (src/app/options.ts, highScoresScreen.ts); messages wait for Enter, a pad
// button or a tap.

import "./overlay.css";
import "./screens.css";
import { filesFromZip, type FileMap } from "../assets/files";
import { storeZip } from "../assets/store";
import { button, h, keyHints, logo, showScreen, title, ui, type Screen } from "../ui";
import { episodeLabel, TitleMenu, type TitleAction, type TitleRow } from "./titleMenu";
import { TitleCodeListener } from "./titleCodes"; // [cheats] [arcade]
import { IdleTimer } from "./idle"; // [demos]
import { arcadeTitle, type ArcadeTitleOptions } from "./arcade"; // [arcade]
import type { NewGameChoice } from "../sim/arcade"; // [arcade]

/** Ask the player for tyrian21.zip (DECISIONS.md D3). Resolves once valid data is loaded. */
export function askForData(): Promise<FileMap> {
  const screen = showScreen({ id: "data", backdrop: "title", layout: "center", label: "Game data" });
  const input = h("input", { attrs: { type: "file", accept: ".zip,application/zip", hidden: "" } });
  const drop = h(
    "label",
    { class: "ui-drop is-focused" },
    h("span", { class: "ui-drop__icon", attrs: { "aria-hidden": "true" } }),
    h("span", { class: "ui-drop__text", text: "Choose or drop tyrian21.zip" }),
    input,
  );
  const status = h("p", { class: "ui-status", attrs: { role: "status" } });
  screen.root.insertBefore(logo(), screen.panel);
  screen.add(
    title("Game data needed", "Tyrian 2.1"),
    h("p", { html: "This game runs on the original <b>Tyrian 2.1</b> data, which isn't included here." }),
    h(
      "p",
      {},
      "Download ",
      h("b", { text: "tyrian21.zip" }),
      " (the freeware release; OpenTyrian links to ",
      h("a", { class: "ui-link", text: "camanis.net/tyrian/tyrian21.zip", attrs: { href: "https://camanis.net/tyrian/tyrian21.zip", target: "_blank", rel: "noopener" } }),
      "), then choose or drop it below. It stays in your browser.",
    ),
    drop,
    status,
    keyHints([{ key: "Enter", pad: "A", label: "Choose file" }]),
  );

  return new Promise((resolve) => {
    const accept = async (file: File | undefined) => {
      if (!file) return;
      status.className = "ui-status";
      status.replaceChildren(h("span", { class: "ui-spinner" }), "Reading…");
      try {
        const zip = new Uint8Array(await file.arrayBuffer());
        const files = await filesFromZip(zip);
        await storeZip(zip);
        screen.close();
        resolve(files);
      } catch (err) {
        status.className = "ui-status ui-error";
        status.textContent = err instanceof Error ? err.message : String(err);
      }
    };
    input.addEventListener("change", () => accept(input.files?.[0]));
    // Enter / A open the file chooser (a key press counts as the user gesture it needs).
    screen.opts.onIntent = (intent) => {
      if (intent !== "accept" && intent !== "start") return false;
      input.click();
      return true;
    };
    // Drop anywhere on the screen.
    screen.root.addEventListener("dragover", (e) => {
      e.preventDefault();
      drop.classList.add("is-over");
    });
    screen.root.addEventListener("dragleave", (e) => {
      if (e.target === screen.root || !screen.root.contains(e.relatedTarget as Node)) drop.classList.remove("is-over");
    });
    screen.root.addEventListener("drop", (e) => {
      e.preventDefault();
      drop.classList.remove("is-over");
      accept(e.dataTransfer?.files[0]);
    });
  });
}

export interface TitleChoice {
  episode: number;
  difficulty: number;
  /** [port-options] A saved game was loaded (Load Game): continue it instead of starting a new one. */
  loaded?: boolean;
  /** [demos] The title sat idle (idleMs): play the next demo, then come back to the title. */
  demo?: boolean;
  /** [destruct] DESTRUCT was typed: play Destruct (it shows its own screens), then come back to the title. */
  destruct?: boolean;
  /** [arcade] A game started by a code typed at the title (src/sim/arcade.ts startNewGame). */
  superArcade?: NewGameChoice["superArcade"];
  superTyrian?: NewGameChoice["superTyrian"];
  smuggledShip?: number;
}

export interface TitleOptions {
  /** episode_name from the data: [0] is the menu title, [n] episode n. */
  episodeNames: string[];
  /** Episodes whose data is present. */
  episodes: number[];
  /** difficulty_name: [n] is difficulty level n. */
  difficultyNames: string[];
  /** Selectable difficulty levels. */
  difficulties: number[];
  initial: TitleChoice;
  /**
   * Music styles to choose from ("original" first) when a local remaster pack is present (only on
   * local builds); omitted otherwise. `onMusicStyle` switches as soon as one is picked.
   */
  musicStyles?: string[];
  musicStyle?: string;
  onMusicStyle?: (style: string) => void;
  /** [port-options] Load Game (JE_loadScreen): resolves true once a saved game is loaded. */
  onLoadGame?: () => Promise<boolean>;
  /** [port-options] Options: the settings screen; the title reads the music style back after it. */
  onOptions?: () => Promise<void>;
  currentMusicStyle?: () => string;
  // [high scores] The title menu's High Scores entry (tyrian2.c MENU_ITEM_HIGH_SCORES): its label
  // and the screen it opens (src/app/highScoresScreen.ts); the title waits while it's open.
  highScoresLabel?: string;
  onHighScores?: () => Promise<void>;
  // [cheats] The difficulty row shows the first `difficultiesShown` of `difficulties` (default
  // all); Shift+G, Shift+] and L O R D reveal the rest, one at a time, as difficultySelect does
  // (src/app/titleCodes.ts, which also listens for the codes in `arcade.specialName`).
  difficultiesShown?: number;
  /**
   * [destruct] Whether the Destruct game is in (src/app/titleCodes.ts destructHook): then DESTRUCT
   * closes the title, which resolves with `destruct`. Without it, the code's notice shows over the title.
   */
  destructReady?: () => boolean;
  /** [demos] titleScreen's idle timer: after this long without input, resolve with `demo`. */
  idleMs?: number;
  /** [arcade] What the codes typed at the title start (src/app/arcade.ts). */
  arcade?: ArcadeTitleOptions;
}

/**
 * Standard-mapping pad buttons for the title's other entries, with their hint glyphs. None is an
 * intent (src/ui/nav.ts PAD_BUTTONS): X is the title's alt (Music) and Start starts, so Load Game
 * takes LB, the next free button (the shoulders only steer sidekicks in flight).
 */
export const TITLE_PAD = {
  loadGame: { button: 4, glyph: "LB" },
  options: { button: 8, glyph: "Back" },
  highScores: { button: 3, glyph: "Y" },
} as const;

/**
 * Title screen (D64): the original's layout, the logo at the top and a copper menu centred below it
 * over the painted planet. Start New Game opens the second step, the episodes with the difficulty
 * row and Back; choosing an episode starts it. Load Game, High Scores and Options open their own
 * screens, also from any step with keys L, H and O and pad buttons LB, Y and Back (TITLE_PAD); M or
 * X cycles the music style, Start starts the chosen episode straight away.
 */
export function showTitle(opts: TitleOptions): Promise<TitleChoice> {
  const styles = opts.musicStyles ?? [];
  // [cheats] The hidden difficulties stay out of the row until their keys are typed.
  const initialDiff = Math.max(0, opts.difficulties.indexOf(opts.initial.difficulty));
  let shown = Math.min(opts.difficulties.length, Math.max(opts.difficultiesShown ?? opts.difficulties.length, initialDiff + 1));

  let resolveFn: (c: TitleChoice) => void = () => {};
  const finish = (extra: Partial<TitleChoice> = {}) => {
    if (!screen.open) return;
    idle?.stop(); // [demos]
    screen.close();
    // [arcade] a ship smuggled out of a Super Arcade start
    const smuggledShip = arcade?.smuggledShip();
    resolveFn({ episode: opts.episodes[menu.episode], difficulty: opts.difficulties[menu.difficulty], ...(smuggledShip ? { smuggledShip } : {}), ...extra });
  };
  // [demos] Play a demo after idling (tyrian2.c L3304-3311), only while the title itself is up.
  const idle = opts.idleMs
    ? new IdleTimer(opts.idleMs, () => {
        if (!busy && !screen.isAside && ui.current === screen) finish({ demo: true });
      })
    : null;

  // [port-options] [high scores] The other entries, each its own screen over the title's backdrop.
  // A screen that reads keys and pads itself gets the title stepped aside (Screen.aside); Load Game,
  // High Scores and Options are framework screens shown over the title (ScreenOptions.over), which
  // hand the input back themselves. Then the music style is read back (Options can change it), and
  // a loaded game starts.
  let busy = false;
  const sub = async <T,>(fn: () => Promise<T>, over = false, then: (result: T) => void = (loaded) => loaded === true && finish({ loaded: true })) => {
    if (busy || screen.isAside || !screen.open) return;
    busy = true;
    const result = await (over ? fn() : screen.aside(fn)).finally(() => {
      busy = false;
      idle?.reset(); // [demos] the C restarts the title loop, and its idle count, after a sub-menu
    });
    syncMusic();
    then(result);
  };
  // The original title's order: Load Game, High Scores, then (OpenTyrian's) Options.
  const more: { label: string; key: string; code: string; pad: { button: number; glyph: string }; over?: boolean; run: () => Promise<boolean | void> }[] = [];
  if (opts.onLoadGame) more.push({ label: "Load Game", key: "L", code: "KeyL", pad: TITLE_PAD.loadGame, over: true, run: opts.onLoadGame });
  if (opts.onHighScores) more.push({ label: opts.highScoresLabel ?? "High Scores", key: "H", code: "KeyH", pad: TITLE_PAD.highScores, over: true, run: opts.onHighScores });
  if (opts.onOptions) more.push({ label: "Options", key: "O", code: "KeyO", pad: TITLE_PAD.options, over: true, run: opts.onOptions });
  const padButtons = new Map(more.map((m) => [m.pad.button, m]));

  const menu = new TitleMenu({
    episodes: opts.episodes.length,
    more: more.length,
    musicStyles: styles.length,
    difficulties: shown,
    episode: Math.max(0, opts.episodes.indexOf(opts.initial.episode)),
    difficulty: initialDiff,
    musicStyle: Math.max(0, styles.indexOf(opts.musicStyle ?? "original")),
  });

  const screen = showScreen({
    id: "title",
    backdrop: "title",
    layout: "narrow",
    label: "Title",
    onKey: (e) => {
      if (codes?.key(e)) return true; // [cheats] [arcade] the typed codes and hidden difficulties
      if (e.code === "KeyM" && menu.hasMusic) act(menu.cycleMusic(1));
      else {
        const m = more.find((m) => m.code === e.code);
        if (!m || e.altKey || e.ctrlKey || e.metaKey) return false;
        void sub(m.run, m.over);
      }
      return true;
    },
    onPadButton: (button) => {
      const m = padButtons.get(button);
      if (m) void sub(m.run, m.over);
    },
    onIntent: (intent) => {
      if (intent === "start") finish();
      else if (intent === "alt") act(menu.cycleMusic(1));
      else act(menu.intent(intent));
      return true;
    },
  });

  /** Do what the menu asks, and redraw it. */
  const act = (a: TitleAction) => {
    switch (a.kind) {
      case "none":
        return;
      case "more":
        void sub(more[a.index].run, more[a.index].over);
        return;
      case "music":
        opts.onMusicStyle?.(styles[a.index]);
        break;
      case "start":
        finish();
        return;
      case "step":
        build(true);
        return;
    }
    paint();
  };

  /** Show the style the music plays now, without switching it again. */
  const syncMusic = () => {
    const i = styles.indexOf(opts.currentMusicStyle?.() ?? "");
    if (i < 0) return;
    menu.setMusicStyle(i);
    paint();
  };

  // --- the menu's lines ---
  const label = (s: string) => `${s[0].toUpperCase()}${s.slice(1)}`;
  const difficultyName = () => opts.difficultyNames[opts.difficulties[menu.difficulty]]?.trim() || String(opts.difficulties[menu.difficulty]);
  const tick = () => h("i", { class: "title-tick", attrs: { "aria-hidden": "true" } });
  const arrow = (d: number) => h("span", { class: "title-arrow", text: d < 0 ? "◀" : "▶", attrs: { "data-d": String(d), "aria-hidden": "true" } });
  const nav = h("nav", { class: "title-menu", attrs: { "aria-label": "Title menu" } });
  let list: HTMLUListElement = h("ul");
  /** Lines whose text changes as values do (the music style, the difficulty). */
  const live: (() => void)[] = [];

  const line = (row: TitleRow, i: number): HTMLLIElement => {
    const li = h("li", { class: `title-item title-item--${row.kind}`, attrs: { role: "option", "data-index": String(i) } });
    const text = h("span", { class: "title-text" });
    switch (row.kind) {
      case "start":
        text.textContent = "Start New Game";
        li.append(tick(), text, tick());
        break;
      case "more":
        text.textContent = more[row.index].label;
        li.append(tick(), text, tick());
        break;
      case "music":
        live.push(() => (text.textContent = `Music: ${label(styles[menu.musicStyle] ?? "")}`));
        li.append(tick(), arrow(-1), text, arrow(1), tick());
        break;
      case "episode": {
        const n = opts.episodes[row.index];
        const { mark, title } = episodeLabel(opts.episodeNames[n], n);
        text.textContent = title;
        li.append(tick(), h("span", { class: "title-mark", text: mark, attrs: { "aria-hidden": "true" } }), text, tick());
        li.setAttribute("aria-label", opts.episodeNames[n]?.trim() || `Episode ${n}`);
        break;
      }
      case "difficulty": {
        const pips = h("span", { class: "title-pips", attrs: { "aria-hidden": "true" } });
        live.push(() => {
          text.textContent = difficultyName();
          pips.replaceChildren(...Array.from({ length: menu.difficulties }, (_, k) => h("i", { class: k <= menu.difficulty ? "is-on" : "" })));
          li.setAttribute("aria-label", `Difficulty: ${difficultyName()}`);
        });
        li.append(tick(), arrow(-1), h("small", { class: "title-caption", text: "Difficulty" }), text, pips, arrow(1), tick());
        break;
      }
      case "back":
        text.textContent = "Back";
        li.append(tick(), text, tick());
        break;
    }
    return li;
  };

  /** Draw the current step's lines (`enter`: with their entrance). */
  const build = (enter: boolean) => {
    live.length = 0;
    list = h("ul", { class: `title-step title-step--${menu.step}${enter ? " is-entering" : ""}`, attrs: { role: "listbox", "aria-label": menu.step === "main" ? "Title menu" : "Select episode" } });
    list.append(...menu.rows().map(line));
    const kicker = menu.step === "episodes" ? h("p", { class: "title-kicker", text: "Select episode" }) : null;
    nav.replaceChildren(...(kicker ? [kicker] : []), list);
    screen.root.dataset.step = menu.step;
    paint();
  };

  const paint = () => {
    for (const update of live) update();
    [...list.children].forEach((li, i) => {
      li.classList.toggle("is-sel", i === menu.focus);
      li.setAttribute("aria-selected", String(i === menu.focus));
    });
  };

  // Pointer and touch: a mouse over a line focuses it; a click or tap chooses it (an arrow on the
  // music or difficulty line steps that way instead).
  nav.addEventListener("pointermove", (e) => {
    if (e.pointerType !== "mouse") return;
    const li = (e.target as HTMLElement).closest<HTMLElement>("[data-index]");
    if (li) act(menu.focusRow(Number(li.dataset.index)));
  });
  nav.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    const li = target.closest<HTMLElement>("[data-index]");
    if (!li) return;
    const i = Number(li.dataset.index);
    act(menu.focusRow(i));
    const d = Number(target.closest<HTMLElement>("[data-d]")?.dataset.d ?? 0);
    if (d && menu.row.kind === "music") act(menu.cycleMusic(d));
    else if (d && menu.row.kind === "difficulty") act(menu.stepDifficulty(d));
    else act(menu.select(i));
  });

  // [arcade] What the codes start (the kind of game is asked after the title: gameplaySelect).
  const arcade = opts.arcade
    ? arcadeTitle(opts.arcade, {
        episodeName: () => opts.episodeNames[opts.episodes[menu.episode]]?.trim() || `Episode ${opts.episodes[menu.episode]}`,
        difficultyName: (level) => opts.difficultyNames[level]?.trim() || String(level),
        difficulty: () => opts.difficulties[menu.difficulty],
        open: (run, over, then) => void sub(run, over, then),
        start: (choice) => finish(choice),
      })
    : null;
  // [cheats] [arcade] The title's one key listener for its secrets (src/app/titleCodes.ts): the
  // codes (titleScreen's specialNameProgress) and the hidden difficulties. A code's first letter
  // can be a WASD move, so the menu goes back to where it was before it once a code completes.
  let marked = menu.snapshot();
  const codes = opts.arcade
    ? new TitleCodeListener({
        specialName: opts.arcade.specialName,
        difficultyVisible: shown,
        onCodeMayStart: () => (marked = menu.snapshot()),
        onCode: (code, e) => {
          const step = menu.step;
          menu.restore(marked);
          if (menu.step !== step) build(false);
          else paint();
          if (code.kind === "destruct" && opts.destructReady?.()) return finish({ destruct: true }); // [destruct]
          arcade?.code(code, e);
        },
        onDifficultyVisible: (n) => {
          shown = Math.min(n, opts.difficulties.length);
          menu.setDifficulties(shown);
          paint();
        },
      })
    : null;
  void screen.closed.then(() => codes?.dispose());

  screen.root.insertBefore(logo(), screen.panel);
  screen.add(nav);
  screen.root.append(
    h(
      "footer",
      { class: "title-foot" },
      h(
        "div",
        { class: "title-foot__controls" },
        // The flight controls for the device used last (src/app/controls.ts); CSS picks one.
        h("p", { class: "title-controls", attrs: { "data-dev": "keys" }, text: "In flight: arrows or WASD move, Space fires. Mouse, touch and gamepads work too." }),
        h("p", { class: "title-controls", attrs: { "data-dev": "pad" }, text: "In flight: stick or d-pad moves, A or RT fires, X changes fire mode, LB and RB fire the sidekicks, Start pauses." }),
      ),
      keyHints([
        { key: "↑↓", pad: "✛", label: "Select" },
        { key: "Enter", pad: "A", touch: "Tap", label: "Confirm" },
        { key: "←→", pad: "✛", label: "Change" },
        ...(menu.hasMusic ? [{ key: "M", pad: "X", label: "Music" }] : []),
        ...more.map((m) => ({ key: m.key, pad: m.pad.glyph, label: m.label })),
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    ),
  );
  build(false);
  return new Promise((resolve) => (resolveFn = resolve));
}

/**
 * The continue button's label from a prompt such as "Press Enter to continue" (callers still pass
 * the keyboard wording; on a pad or a touch screen "Press Enter" would be wrong).
 */
export function actionLabel(prompt: string): string {
  const s = prompt.replace(/^press\s+(enter|any key)\s*(to|for)?\s*/i, "").trim();
  if (/^the title( screen)?$/i.test(s)) return "Title screen";
  return s ? s[0].toUpperCase() + s.slice(1) : "Continue";
}

/** A message screen (level complete, game over); resolves when the player continues. */
export function showMessage(heading: string, lines: string[], prompt = "Press Enter to continue"): Promise<void> {
  return new Promise((resolve) => {
    let screen: Screen;
    const done = () => {
      if (!screen.open) return;
      screen.close();
      resolve();
    };
    screen = showScreen({
      id: "message",
      backdrop: "space",
      layout: "narrow",
      label: heading,
      onIntent: (intent) => {
        if (intent === "accept" || intent === "start" || intent === "back") done();
        return true;
      },
    });
    screen.add(
      title(heading),
      ...lines.map((l) => h("p", { class: "message-line", text: l })),
      h("div", { class: "ui-actions" }, button({ label: actionLabel(prompt), variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
    );
    // A tap anywhere continues, as a click on the old overlay did.
    screen.root.addEventListener("click", done);
  });
}

/** A non-blocking status line (e.g. loading), removed by calling the returned function. */
export function showStatus(text: string): () => void {
  return showProgress(text).close;
}

/** showStatus whose text can change (e.g. a count of models loaded). */
export function showProgress(text: string): { set(text: string): void; close(): void } {
  const screen = showScreen({ id: "status", backdrop: "title", layout: "narrow", passive: true, label: text });
  const label = h("span", { text });
  screen.add(h("p", { class: "ui-status" }, h("span", { class: "ui-spinner" }), label));
  return { set: (t) => void (label.textContent = t), close: () => screen.close() };
}
