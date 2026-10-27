// Screens around the game: asking for the data, the title, and end-of-level messages, built with
// the interface framework (src/ui/README.md). Their behaviour is unchanged from the first overlays:
// the title still picks an episode with up/down, a difficulty with left/right and starts on
// Enter, a tap on an episode starts it, and messages wait for Enter, a pad button or a tap. The
// title also opens Load Game, Options and High Scores (src/app/options.ts, highScoresScreen.ts).

import "./overlay.css";
import "./screens.css";
import { filesFromZip, type FileMap } from "../assets/files";
import { storeZip } from "../assets/store";
import { button, h, keyHints, logo, MenuList, showScreen, title, ui, type Screen } from "../ui";

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
}

/** Standard-mapping pad buttons for the title's other entries (not intents in src/ui/nav.ts). */
const PAD_Y = 3;
const PAD_BACK = 8;

/**
 * Title screen: pick an episode and difficulty (keyboard, gamepad, click or tap), then start.
 * Load Game, Options and High Scores follow the episodes in the same list (so up/down reach them
 * and a tap opens them), with keys L, O, H and pad Back (Options) and Y (High Scores).
 */
export function showTitle(opts: TitleOptions): Promise<TitleChoice> {
  let ep = Math.max(0, opts.episodes.indexOf(opts.initial.episode));
  let diff = Math.max(0, opts.difficulties.indexOf(opts.initial.difficulty));
  const styles = opts.musicStyles ?? [];
  const hasMusic = styles.length > 1;

  let resolveFn: (c: TitleChoice) => void = () => {};
  const finish = (loaded = false) => {
    if (!screen.open) return;
    screen.close();
    resolveFn({ episode: opts.episodes[ep], difficulty: opts.difficulties[diff], ...(loaded ? { loaded } : {}) });
  };

  // [port-options] [high scores] The other entries, each its own screen over the title's backdrop.
  // Those screens read keys and pads themselves, so the title steps aside while one is open
  // (Screen.aside), then reads back the music style (Options can change it). A loaded game starts.
  // [high scores] A screen on the framework (`own`) opens over the title itself (ScreenOptions.over).
  const sub = async (fn: () => Promise<boolean | void>, own = false) => {
    if (screen.isAside || !screen.open || ui.current !== screen) return;
    const loaded = await (own ? fn() : screen.aside(fn));
    syncMusic();
    if (loaded === true) finish(true);
  };
  const more: { label: string; key: string; code: string; pad?: string; run: () => Promise<boolean | void>; own?: boolean }[] = [];
  if (opts.onLoadGame) more.push({ label: "Load Game", key: "L", code: "KeyL", run: opts.onLoadGame });
  if (opts.onOptions) more.push({ label: "Options", key: "O", code: "KeyO", pad: "Back", run: opts.onOptions });
  if (opts.onHighScores) more.push({ label: opts.highScoresLabel ?? "High Scores", key: "H", code: "KeyH", pad: "Y", run: opts.onHighScores, own: true });
  const padButtons = new Map<number, (typeof more)[number]>();
  for (const m of more) if (m.pad) padButtons.set(m.pad === "Y" ? PAD_Y : PAD_BACK, m);

  const screen = showScreen({
    id: "title",
    backdrop: "title",
    layout: "narrow",
    label: "Title",
    onKey: (e) => {
      if (e.code === "KeyM" && hasMusic) cycleMusic();
      else {
        const m = more.find((m) => m.code === e.code);
        if (!m || e.altKey || e.ctrlKey || e.metaKey) return false;
        void sub(m.run, m.own);
      }
      return true;
    },
    onPadButton: (button) => {
      const m = padButtons.get(button);
      if (m) void sub(m.run, m.own);
    },
    onIntent: (intent) => {
      if (intent === "start") finish();
      else if (intent === "alt" && hasMusic) cycleMusic();
      else return false;
      return true;
    },
  });

  const episodeCount = opts.episodes.length;
  const episodes = new MenuList({
    label: "Episode",
    items: [
      ...opts.episodes.map((n) => ({ label: opts.episodeNames[n]?.trim() || `Episode ${n}` })),
      ...more.map((m, i) => ({ label: m.label, class: `title-more${i === 0 ? " title-more--first" : ""}` })),
    ],
    focused: ep,
    onFocus: (i) => {
      if (i < episodeCount) ep = i;
    },
    onSelect: (i) => {
      if (i >= episodeCount) return void sub(more[i - episodeCount].run, more[i - episodeCount].own);
      ep = i;
      finish();
    },
  });
  const difficulty = new MenuList({
    label: "Difficulty",
    orientation: "horizontal",
    items: opts.difficulties.map((n) => ({ label: opts.difficultyNames[n]?.trim() || String(n) })),
    focused: diff,
    onFocus: (i) => (diff = i),
  });
  // Music style (local remaster packs only): M or X cycles it, a tap picks one. Not one of the
  // screen's controls, so left/right stay with the difficulty.
  const label = (s: string) => `${s[0].toUpperCase()}${s.slice(1)}`;
  let syncing = false;
  const music = new MenuList({
    label: "Music",
    orientation: "horizontal",
    class: "title-music",
    items: styles.map((s) => ({ label: label(s) })),
    focused: Math.max(0, styles.indexOf(opts.musicStyle ?? "original")),
    onFocus: (i) => {
      if (!syncing) opts.onMusicStyle?.(styles[i]);
    },
  });
  const cycleMusic = () => music.focus((music.focused + 1) % styles.length);
  /** Show the style the music plays now, without switching it again. */
  const syncMusic = () => {
    const i = styles.indexOf(opts.currentMusicStyle?.() ?? "");
    if (i < 0) return;
    syncing = true;
    music.focus(i);
    syncing = false;
  };

  screen.root.insertBefore(logo(), screen.panel);
  screen.add(h("span", { class: "ui-label", text: "Episode" }), episodes);
  screen.add(h("span", { class: "ui-label", text: "Difficulty" }), difficulty);
  if (hasMusic) screen.add(h("span", { class: "ui-label", text: "Music" }), music.el);
  screen.add(
    keyHints([
      { key: "↑↓", pad: "✛", label: "Episode" },
      { key: "←→", pad: "✛", label: "Difficulty" },
      { key: "Enter", pad: "A", touch: "Tap", label: "Start" },
      ...(hasMusic ? [{ key: "M", pad: "X", label: "Music" }] : []),
      // A hint without a pad glyph shows its key on a pad too; Load Game has no button of its own
      // (Y and Back are taken), so on a pad it's reached in the list.
      ...more.map((m) => ({ key: m.key, ...(m.pad ? { pad: m.pad } : {}), label: m.label })),
    ]),
    h("p", { class: "title-controls", text: "In flight: arrows or WASD move, Space fires. Mouse, touch and gamepads work too." }),
  );
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
  const screen = showScreen({ id: "status", backdrop: "title", layout: "narrow", passive: true, label: text });
  screen.add(h("p", { class: "ui-status" }, h("span", { class: "ui-spinner" }), text));
  return () => screen.close();
}
