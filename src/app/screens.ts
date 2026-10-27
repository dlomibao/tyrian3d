// Screens around the game: asking for the data, the title, and end-of-level messages, built with
// the interface framework (src/ui/README.md). Their behaviour is unchanged from the first overlays:
// the title still picks an episode with up/down, a difficulty with left/right and starts on
// Enter, a tap on an episode starts it, and messages wait for Enter, a pad button or a tap.

import "./overlay.css";
import "./screens.css";
import { filesFromZip, type FileMap } from "../assets/files";
import { storeZip } from "../assets/store";
import { button, h, keyHints, logo, MenuList, showScreen, title, type Screen } from "../ui";

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
}

/** Title screen: pick an episode and difficulty (keyboard, gamepad, click or tap), then start. */
export function showTitle(opts: TitleOptions): Promise<TitleChoice> {
  let ep = Math.max(0, opts.episodes.indexOf(opts.initial.episode));
  let diff = Math.max(0, opts.difficulties.indexOf(opts.initial.difficulty));
  const styles = opts.musicStyles ?? [];
  const hasMusic = styles.length > 1;

  let resolveFn: (c: TitleChoice) => void = () => {};
  const finish = () => {
    screen.close();
    resolveFn({ episode: opts.episodes[ep], difficulty: opts.difficulties[diff] });
  };

  const screen = showScreen({
    id: "title",
    backdrop: "title",
    layout: "narrow",
    label: "Title",
    onKey: (e) => {
      if (e.code !== "KeyM" || !hasMusic) return false;
      cycleMusic();
      return true;
    },
    onIntent: (intent) => {
      if (intent === "start") finish();
      else if (intent === "alt" && hasMusic) cycleMusic();
      else return false;
      return true;
    },
  });

  const episodes = new MenuList({
    label: "Episode",
    items: opts.episodes.map((n) => ({ label: opts.episodeNames[n]?.trim() || `Episode ${n}` })),
    focused: ep,
    onFocus: (i) => (ep = i),
    onSelect: (i) => {
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
  const music = new MenuList({
    label: "Music",
    orientation: "horizontal",
    class: "title-music",
    items: styles.map((s) => ({ label: label(s) })),
    focused: Math.max(0, styles.indexOf(opts.musicStyle ?? "original")),
    onFocus: (i) => opts.onMusicStyle?.(styles[i]),
  });
  const cycleMusic = () => music.focus((music.focused + 1) % styles.length);

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
