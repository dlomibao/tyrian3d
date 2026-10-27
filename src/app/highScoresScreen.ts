// The high score screens, on the interface framework (src/ui/README.md): the tables from the
// title screen (JE_highScoreScreen, mainint.c L1075-1285) and the name entry after a qualifying
// game (JE_highScoreCheck, mainint.c L1921-2156). The rules (which table, which slot, what a name
// may hold) are the C's, in src/sim/highscores.ts; the tables are stored by src/app/highScores.ts.
// Texts come from the game data (miscText, episode_name, difficultyNameB in tyrian.hdt).
//
// Tables, as in the C: left/right page through the episodes (wrapping), Enter, Space or Escape
// close, and so do a right click, the pad's A, B or Start and the DONE button. The shoulders page
// too, and the arrows beside the episode name take a tap.
//
// Name entry: typing works as in the C (the characters the font has, up to 28; Backspace deletes,
// Enter keeps the name, Escape cancels). Pads and touch screens, which can't type, get a grid of
// characters (src/app/namePicker.ts): the d-pad moves, A types, B deletes (and cancels once the
// name is empty), X adds a space, Y or the shoulders change the character set, Start keeps the
// name; a tap types. CANCEL in the corner cancels.

import "./highScores.css";
import type { MusicPlayer } from "../audio/remaster";
import type { SoundEffects } from "../audio/sfx";
import {
  HIGH_SCORE_EPISODES,
  HIGH_SCORE_NAME_MAX,
  highScoreCheckScore,
  highScoreNameAccepts,
  highScoreRank,
  highScoreTable,
  JE_highScoreCheckEnter,
  JE_highScoreCheckSlot,
  type HighScoreEntry,
} from "../sim/highscores";
import { S_CURSOR, S_SPRING } from "../sim/sndmast";
import { g } from "../sim/state";
import { button, h, keyHints, lastDevice, reveal, showScreen, title, type Intent, type Navigable, type Screen } from "../ui";
import { loadHighScores, saveHighScores } from "./highScores";
import { nameAppend, nameDelete, pickerCell, pickerMove, pickerNextSet, pickerRows, PICKER_SETS, type PickerKey, type PickerState } from "./namePicker";

/** OpenTyrian song number (0-based, as passed to play_song) of the high score fanfare. */
const SONG_HIGH_SCORE = 33;

/** Standard-mapping pad buttons that aren't intents (src/ui/nav.ts PAD_BUTTONS). */
const PAD_Y = 3;
const PAD_LB = 4;
const PAD_RB = 5;

export interface HighScoreTexts {
  /** episode_name[6]: [n] is episode n. */
  episodeName: string[];
  /** difficultyNameB[11]: the difficulty column. */
  difficultyNameB: string[];
}

export interface HighScoreHost extends HighScoreTexts {
  sfx: SoundEffects;
  music: MusicPlayer;
}

/** miscText[i] (0-based, as the C indexes it), with a fallback when the data lacks it. */
const misc = (i: number, fallback: string) => g.miscText[i]?.trim() || fallback;

/**
 * One table row: the C's "~#n:~  score" in two columns, the name, and (on the title's table) the
 * difficulty name. Text from the data goes in as text, never markup.
 */
function row(rank: number, e: HighScoreEntry, difficultyNameB: string[] | null, isNew = false): HTMLElement {
  let diff: HTMLElement | null = null;
  if (difficultyNameB) {
    const r = highScoreRank(e.highScoreDiff, difficultyNameB.length);
    diff = h("span", { class: "hs-diff", text: difficultyNameB[r]?.trim() ?? "" });
    // JE_textShade(..., 15, rank + (rank == 0 ? 0 : -1)): higher ranks are brighter.
    diff.style.setProperty("--shade", String(r + (r === 0 ? 0 : -1)));
  }
  return h(
    "li",
    { class: `hs-row${isNew ? " hs-new" : ""}` },
    h("span", { class: "hs-rank", text: `#${rank}` }),
    h("span", { class: "hs-score", text: String(e.highScore1) }),
    h("span", { class: "hs-name", text: e.highScoreName.trimEnd() }),
    diff,
  );
}

/** Rows first_slot .. first_slot + 2 as an ordered list. */
function table(saveFiles: HighScoreEntry[], first_slot: number, difficultyNameB: string[] | null, newSlot = -1): HTMLElement {
  return h("ol", { class: "hs-table" }, ...[0, 1, 2].map((i) => row(i + 1, saveFiles[first_slot + i], difficultyNameB, first_slot + i === newSlot)));
}

export interface HighScoreScreenOptions extends HighScoreTexts {
  /** episodeAvail: which of episodes 1-3 have data (a missing one's header is dimmed). */
  episodes: number[];
  sfx?: SoundEffects;
  /** The episode to open on (1-3). */
  episode?: number;
}

/**
 * JE_highScoreScreen (mainint.c L1075-1285): the tables of episodes 1-3, a page per episode. It
 * opens over the screen that asked for it (the title) and that screen comes back when it closes.
 */
export function showHighScoreScreen(opts: HighScoreScreenOptions): Promise<void> {
  const saveFiles = loadHighScores();
  const episodeCount = HIGH_SCORE_EPISODES; // Save file only has space for scores for 3 episodes.
  let episodeIndex = Math.min(Math.max((opts.episode ?? 1) - 1, 0), episodeCount - 1);

  return new Promise((resolve) => {
    const done = () => {
      if (!screen.open) return;
      opts.sfx?.playSampleNum(S_SPRING);
      screen.close();
      resolve();
    };
    const page = (delta: number) => {
      opts.sfx?.playSampleNum(S_CURSOR);
      episodeIndex = (episodeIndex + delta + episodeCount) % episodeCount;
      render();
    };
    const screen = showScreen({
      id: "highscores",
      over: true,
      label: misc(50, "High Scores"),
      onIntent: (intent) => {
        if (intent === "left") page(-1);
        else if (intent === "right") page(1);
        else if (intent === "accept" || intent === "back" || intent === "start") done();
        else return false;
        return true;
      },
      onPadButton: (b) => {
        if (b === PAD_LB) page(-1);
        else if (b === PAD_RB) page(1);
      },
    });

    const prev = button({ label: "◀", variant: "ghost", class: "hs-page", onPress: () => page(-1) });
    const next = button({ label: "▶", variant: "ghost", class: "hs-page", onPress: () => page(1) });
    prev.setAttribute("aria-label", "Previous episode");
    next.setAttribute("aria-label", "Next episode");
    const episodeEl = h("h3", { class: "hs-episode", attrs: { "aria-live": "polite" } });
    const tablesEl = h("div", { class: "hs-tables" });

    const render = () => {
      episodeEl.textContent = opts.episodeName[episodeIndex + 1]?.trim() || `Episode ${episodeIndex + 1}`;
      episodeEl.classList.toggle("is-disabled", !opts.episodes.includes(episodeIndex + 1));
      tablesEl.replaceChildren(
        h("span", { class: "ui-label", text: misc(46, "One Player") }),
        table(saveFiles, highScoreTable(episodeIndex + 1, false).first_slot, opts.difficultyNameB),
        h("span", { class: "ui-label", text: misc(47, "Two Player") }),
        table(saveFiles, highScoreTable(episodeIndex + 1, true).first_slot, opts.difficultyNameB),
      );
      // Draw paging controls (the keys wrap around; the arrows only show where there's a page).
      prev.style.visibility = episodeIndex > 0 ? "visible" : "hidden";
      next.style.visibility = episodeIndex < episodeCount - 1 ? "visible" : "hidden";
    };
    render();

    screen.add(
      title(misc(50, "High Scores")),
      h("div", { class: "hs-paging" }, prev, episodeEl, next),
      tablesEl,
      h("div", { class: "ui-actions" }, button({ label: misc(13, "DONE"), variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done })),
      keyHints([
        { key: "←→", pad: "✛ LB RB", label: "Episode" },
        { key: "Esc", pad: "B", label: "Back" },
      ]),
    );
    // A right click closes, as in the C.
    screen.root.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      done();
    });
  });
}

/** The label of a picker key; the set key names the set it switches to. */
function pickerLabel(key: PickerKey, set: number): string {
  switch (key.kind) {
    case "char":
      return key.char;
    case "set":
      return PICKER_SETS[(set + 1) % PICKER_SETS.length].name;
    case "space":
      return "Space";
    case "delete":
      return "Del";
    case "ok":
      return misc(9, "OK");
  }
}

/**
 * The character grid: d-pad focus, A or a tap presses a key. Presses go to `press`; the grid only
 * draws and moves.
 */
class NamePicker implements Navigable {
  readonly el: HTMLDivElement;
  state: PickerState = { set: 0, row: 0, col: 0 };

  constructor(
    private readonly press: (key: PickerKey) => void,
    private readonly sfx?: SoundEffects,
  ) {
    this.el = h("div", { class: "hs-picker", attrs: { role: "grid", "aria-label": "Characters" } });
    // Keep the text field's focus (and the keyboard's typing) when a key is clicked.
    this.el.addEventListener("mousedown", (e) => e.preventDefault());
    this.el.addEventListener("click", (e) => {
      const b = (e.target as HTMLElement).closest<HTMLElement>("[data-row]");
      if (!b) return;
      this.state = { ...this.state, row: Number(b.dataset.row), col: Number(b.dataset.col) };
      this.paint();
      this.press(pickerCell(this.state).key);
    });
    this.render();
  }

  /** Switch the character set (the set key, Y, the shoulders). */
  nextSet(delta = 1): void {
    this.state = pickerNextSet(this.state, delta);
    this.render();
  }

  handle(intent: Intent): boolean {
    if (intent === "up" || intent === "down" || intent === "left" || intent === "right") {
      this.state = pickerMove(this.state, intent);
      this.sfx?.playSampleNum(S_CURSOR);
      this.paint();
      return true;
    }
    if (intent === "accept") {
      this.press(pickerCell(this.state).key);
      return true;
    }
    return false;
  }

  private render(): void {
    const { set } = this.state;
    this.el.dataset.set = PICKER_SETS[set].name;
    this.el.replaceChildren(
      ...pickerRows(set).flatMap((cells, r) =>
        cells.map((c) => {
          const b = h("button", {
            class: `hs-key hs-key--${c.key.kind}`,
            text: pickerLabel(c.key, set),
            attrs: { type: "button", tabindex: "-1", "data-row": String(r), "data-col": String(c.col) },
          });
          b.style.gridColumn = `${c.col + 1} / span ${c.span}`;
          if (c.key.kind === "delete") b.setAttribute("aria-label", "Delete");
          if (c.key.kind === "set") b.setAttribute("aria-label", `Characters ${pickerLabel(c.key, set)}`);
          return b;
        }),
      ),
    );
    this.paint();
  }

  private paint(): void {
    const cell = pickerCell(this.state);
    for (const b of this.el.querySelectorAll<HTMLElement>(".hs-key")) {
      const focused = Number(b.dataset.row) === this.state.row && Number(b.dataset.col) === cell.col;
      b.classList.toggle("is-focused", focused);
      if (focused) reveal(b);
    }
  }
}

/**
 * The name entry of JE_highScoreCheck (mainint.c L1978-2104): "Enter your name:" with the score.
 * Typing takes the characters the font has, up to 28; Enter (or OK) keeps the name, Escape (or
 * CANCEL) cancels. Resolves with the typed text, or null when cancelled.
 */
function askHighScoreName(score: number, episodeName: string, sfx?: SoundEffects, player: number | null = null): Promise<string | null> {
  return new Promise((resolve) => {
    const finish = (name: string | null) => {
      if (!screen.open) return;
      screen.close();
      resolve(name);
    };
    const ok = () => finish(input.value);
    const cancel = () => finish(null);
    const set = (name: string) => {
      if (input.value !== name) input.value = name;
      count.textContent = `${[...name].length}/${HIGH_SCORE_NAME_MAX}`;
    };
    const type = (ch: string) => set(nameAppend(input.value, ch));
    const del = () => set(nameDelete(input.value));

    const screen: Screen = showScreen({
      id: "highscore-entry",
      backdrop: "space",
      layout: "narrow",
      label: misc(53, "Enter your name:"),
      // Keys while the text field doesn't have the focus (a key of the grid was tapped, or a pad
      // was used): typing still types, as in the C, which reads every key. Enter keeps the name.
      onKey: (e) => {
        if (e.code === "Enter" || e.code === "NumpadEnter") ok();
        else if (e.code === "Escape") cancel();
        else if (e.code === "Backspace" || e.code === "Delete") del();
        else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) type(e.key);
        else return false;
        return true;
      },
      onIntent: (intent) => {
        if (intent === "start") ok();
        else if (intent === "alt") type(" ");
        else if (intent === "back") {
          // B deletes, like a console keyboard's; with nothing left to delete it cancels.
          if (input.value) del();
          else cancel();
        } else return false;
        return true;
      },
      onPadButton: (b) => {
        if (b === PAD_Y || b === PAD_RB) picker.nextSet(1);
        else if (b === PAD_LB) picker.nextSet(-1);
      },
    });

    const input = h("input", {
      class: "hs-input",
      attrs: { id: "hs-name", type: "text", maxlength: String(HIGH_SCORE_NAME_MAX), autocomplete: "off", autocapitalize: "words", spellcheck: "false", enterkeyhint: "done" },
    });
    const count = h("span", { class: "hs-count", attrs: { "aria-hidden": "true" } });
    set("");
    // Keep typing away from the game's key handlers (Controls cancels WASD, Space and the like).
    input.addEventListener("keydown", (e) => e.stopPropagation());
    input.addEventListener("input", () => {
      // ch == ' ' || fontMap[ch] != -1, while temp < 28
      const clean = [...input.value].filter(highScoreNameAccepts).slice(0, HIGH_SCORE_NAME_MAX).join("");
      set(clean);
    });

    const picker = new NamePicker((key) => {
      if (key.kind === "char") type(key.char);
      else if (key.kind === "space") type(" ");
      else if (key.kind === "delete") del();
      else if (key.kind === "set") picker.nextSet(1);
      else ok();
    }, sfx);

    const padHints = keyHints([
      { pad: "A", label: "Type" },
      { pad: "B", label: "Delete" },
      { pad: "X", label: "Space" },
      { pad: "Y", label: "Characters" },
      { pad: "Start", label: misc(9, "OK") },
    ]);
    padHints.classList.add("hs-hints--pad");
    screen.add(
      // Escape cancels; B only once the name is empty, so the button shows no glyph.
      button({ label: misc(10, "CANCEL"), variant: "ghost", class: "ui-back", onPress: cancel }),
      title(misc(51, "Congratulations!"), episodeName || undefined),
      // [two-player] "Player 1 has earned a high score!", "Player 1 Enter your name:" (mainint.c L1996-2005)
      h("p", { class: "hs-earned", text: player === null ? misc(52, "You have earned a high score!") : misc(57 + player, `Player ${player + 1} has earned a high score!`) }),
      h("p", { class: "hs-total" }, h("span", { text: misc(37, "Your total Score:") }), h("b", { text: String(score) })),
      h("label", { class: "ui-label", attrs: { for: "hs-name" }, text: player === null ? misc(53, "Enter your name:") : `${misc(48 + player, `Player ${player + 1}`)} ${misc(53, "Enter your name:")}` }),
      h("div", { class: "hs-field" }, input, count),
    );
    screen.add(picker);
    const keyHintsEl = keyHints([
      { key: "A–Z", label: "Type" },
      { key: "Enter", label: misc(9, "OK") },
      { key: "Esc", label: misc(10, "CANCEL") },
    ]);
    keyHintsEl.classList.add("hs-hints--keys");
    screen.add(keyHintsEl, padHints);
    // The keyboard types into the field; on a touch screen or a pad the grid does (a tap on the
    // field still brings up the phone's keyboard).
    const device = lastDevice();
    if (device === "keys" || device === "mouse") input.focus();
  });
}

/**
 * The end of JE_highScoreCheck (mainint.c L2113-2152): the episode's table with the new entry
 * glowing (the slot's entry, also when the name entry was cancelled), until a key, click, tap or
 * pad button.
 */
function showHighScoreEntered(saveFiles: HighScoreEntry[], slot: number, first_slot: number, episodeName: string): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      if (!screen.open) return;
      screen.close();
      resolve();
    };
    const screen = showScreen({
      id: "highscores",
      backdrop: "space",
      label: misc(50, "High Scores"),
      // waitUntilGetInput: any key (not one still repeating from the name entry's Enter).
      onKey: (e) => {
        if (!e.repeat) done();
        return true;
      },
      onIntent: () => {
        done();
        return true;
      },
      onPadButton: done,
    });
    screen.add(
      title(misc(50, "High Scores")),
      h("h3", { class: "hs-episode", text: episodeName }),
      h("div", { class: "hs-tables" }, table(saveFiles, first_slot, null, slot)),
      h("p", { class: "hs-press" }, h("span", { class: "hs-press__keys", text: misc(4, "Press a key") }), h("span", { class: "hs-press__touch", text: "Tap to continue" })),
    );
    screen.root.addEventListener("click", done);
  });
}

/**
 * JE_highScoreCheck (mainint.c L1921-2156) for a one-player game: if the score beats an entry in
 * the starting episode's table, play the fanfare, ask for a name, store it, and show the table.
 * The caller decides when it's due (highScoreCheckDue).
 */
export async function highScoreCheck(host: HighScoreHost, initial_episode_num: number): Promise<void> {
  // [two-player] Both players in a two-player game, the higher scorer first (mainint.c L1928-1941).
  const two = g.twoPlayerMode;
  for (let temp_p = 0; temp_p < (two ? 2 : 1); ++temp_p) {
    const p = two && g.player[0].cash < g.player[1].cash ? 1 - temp_p : temp_p;
    const saveFiles = loadHighScores();
    const temp_score = highScoreCheckScore(p);
    const slot = JE_highScoreCheckSlot(saveFiles, initial_episode_num, two, temp_score);
    if (slot < 0) continue;

    host.music.play(SONG_HIGH_SCORE);
    const episodeName = host.episodeName[g.episodeNum]?.trim() ?? "";
    const name = await askHighScoreName(temp_score, episodeName, host.sfx, two ? p : null);
    JE_highScoreCheckEnter(saveFiles, slot, temp_score, name, g.difficultyLevel);
    saveHighScores(saveFiles);

    const { first_slot } = highScoreTable(initial_episode_num, two);
    await showHighScoreEntered(saveFiles, slot, first_slot, episodeName);
  }
}
