// The high score screens as HTML overlays: the table from the title screen (JE_highScoreScreen,
// mainint.c L1075-1285) and the name entry after a qualifying game (JE_highScoreCheck, mainint.c
// L1921-2156). The rules (which table, which slot, what a name may hold) are the C's, in
// src/sim/highscores.ts; the tables are stored by src/app/highScores.ts. Texts come from the
// game data (miscText, episode_name, difficultyNameB in tyrian.hdt).
//
// Table keys as in the C: Left/Right page through the episodes (wrapping), Enter, Space or Escape
// close; a right click closes too. Pad: d-pad left/right, A, B or Start close.

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
import { loadHighScores, saveHighScores } from "./highScores";

/** OpenTyrian song number (0-based, as passed to play_song) of the high score fanfare. */
const SONG_HIGH_SCORE = 33;

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

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

/** Tyrian's text toggles a highlight colour with '~' ("~#1:~  12000"). */
const highlight = (s: string) => esc(s).replace(/~([^~]*)~?/g, "<b>$1</b>");

/** miscText[i] (0-based, as the C indexes it), with a fallback when the data lacks it. */
const misc = (i: number, fallback: string) => g.miscText[i]?.trim() || fallback;

function overlay(html: string): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "overlay highscores";
  el.innerHTML = `<div class="panel">${html}</div>`;
  document.body.appendChild(el);
  return el;
}

/**
 * Gamepad presses (not holds; buttons held when the screen opens are ignored), polled each frame
 * until the returned function is called.
 */
function pollPad(onPress: (button: number) => void): () => void {
  let prev: boolean[] | null = null;
  let raf = 0;
  const poll = () => {
    const pad = (navigator.getGamepads?.() ?? []).find((p) => p);
    const now = pad ? pad.buttons.map((b) => b.pressed) : [];
    if (prev) now.forEach((down, i) => down && !prev![i] && onPress(i));
    prev = now;
    raf = requestAnimationFrame(poll);
  };
  raf = requestAnimationFrame(poll);
  return () => cancelAnimationFrame(raf);
}

/** One table row: "~#n:~  score", the name, and (on the title's table) the difficulty name. */
function row(rank: number, e: HighScoreEntry, difficultyNameB: string[] | null, cls = ""): string {
  const diff = difficultyNameB
    ? (() => {
        const r = highScoreRank(e.highScoreDiff, difficultyNameB.length);
        // JE_textShade(..., 15, rank + (rank == 0 ? 0 : -1)): higher ranks are brighter.
        const brightness = r + (r === 0 ? 0 : -1);
        return `<td class="hs-diff" style="--shade:${brightness}">${esc(difficultyNameB[r]?.trim() ?? "")}</td>`;
      })()
    : "";
  return `<tr class="${cls}"><td class="hs-score">${highlight(`~#${rank}:~  ${e.highScore1}`)}</td>
    <td class="hs-name">${esc(e.highScoreName.trimEnd())}</td>${diff}</tr>`;
}

export interface HighScoreScreenOptions extends HighScoreTexts {
  /** episodeAvail: which of episodes 1-3 have data (a missing one's header is dimmed). */
  episodes: number[];
  sfx?: SoundEffects;
  /** The episode to open on (1-3). */
  episode?: number;
}

/** JE_highScoreScreen (mainint.c L1075-1285): the tables of episodes 1-3, a page per episode. */
export function showHighScoreScreen(opts: HighScoreScreenOptions): Promise<void> {
  const saveFiles = loadHighScores();
  const episodeCount = HIGH_SCORE_EPISODES; // Save file only has space for scores for 3 episodes.
  let episodeIndex = Math.min(Math.max((opts.episode ?? 1) - 1, 0), episodeCount - 1);

  const el = overlay(`
    <h2>${esc(misc(50, "High Scores"))}</h2>
    <h3 class="hs-episode"></h3>
    <div class="hs-tables"></div>
    <div class="hs-paging">
      <button type="button" class="hs-prev" aria-label="Previous episode">◀</button>
      <p class="hs-help">${highlight(misc(56, "~Left~ or ~right~ to select episode."))}</p>
      <button type="button" class="hs-next" aria-label="Next episode">▶</button>
    </div>
    <p><button type="button" class="hs-done">${esc(misc(13, "DONE"))}</button></p>`);
  const episodeEl = el.querySelector<HTMLHeadingElement>(".hs-episode")!;
  const tablesEl = el.querySelector<HTMLDivElement>(".hs-tables")!;
  const prevEl = el.querySelector<HTMLButtonElement>(".hs-prev")!;
  const nextEl = el.querySelector<HTMLButtonElement>(".hs-next")!;

  const render = () => {
    const disabled = !opts.episodes.includes(episodeIndex + 1);
    episodeEl.textContent = opts.episodeName[episodeIndex + 1]?.trim() || `Episode ${episodeIndex + 1}`;
    episodeEl.classList.toggle("disabled", disabled);
    const table = (twoPlayer: boolean) => {
      const { first_slot } = highScoreTable(episodeIndex + 1, twoPlayer);
      return [0, 1, 2].map((i) => row(i + 1, saveFiles[first_slot + i], opts.difficultyNameB)).join("");
    };
    tablesEl.innerHTML = `
      <h4>${esc(misc(46, "One Player"))}</h4><table>${table(false)}</table>
      <h4>${esc(misc(47, "Two Player"))}</h4><table>${table(true)}</table>`;
    // Draw paging controls (the keys wrap around; the arrows only show where there's a page).
    prevEl.style.visibility = episodeIndex > 0 ? "visible" : "hidden";
    nextEl.style.visibility = episodeIndex < episodeCount - 1 ? "visible" : "hidden";
  };
  render();

  return new Promise((resolve) => {
    const left = () => {
      opts.sfx?.playSampleNum(S_CURSOR);
      episodeIndex = episodeIndex === 0 ? episodeCount - 1 : episodeIndex - 1;
      render();
    };
    const right = () => {
      opts.sfx?.playSampleNum(S_CURSOR);
      episodeIndex = episodeIndex === episodeCount - 1 ? 0 : episodeIndex + 1;
      render();
    };
    const done = () => {
      opts.sfx?.playSampleNum(S_SPRING);
      window.removeEventListener("keydown", onKey, true);
      stopPad();
      el.remove();
      resolve();
    };
    const onKey = (e: KeyboardEvent) => {
      const action: Record<string, () => void> = {
        ArrowLeft: left,
        KeyA: left,
        ArrowRight: right,
        KeyD: right,
        Space: done,
        Enter: done,
        NumpadEnter: done,
        Escape: done,
      };
      const f = action[e.code];
      if (!f) return;
      e.preventDefault();
      e.stopPropagation();
      f();
    };
    const stopPad = pollPad((b) => {
      if (b === 14) left();
      else if (b === 15) right();
      else if (b === 0 || b === 1 || b === 9) done();
    });
    prevEl.addEventListener("click", left);
    nextEl.addEventListener("click", right);
    el.querySelector(".hs-done")!.addEventListener("click", done);
    el.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      done();
    });
    window.addEventListener("keydown", onKey, true);
  });
}

/**
 * The name entry of JE_highScoreCheck (mainint.c L1978-2104): "Enter your name:" with the score.
 * Typing takes the characters the font has, up to 28; Enter (or OK) keeps the name, Escape (or
 * CANCEL) cancels. Resolves with the typed text, or null when cancelled.
 */
function askHighScoreName(score: number): Promise<string | null> {
  const el = overlay(`
    <h2>${esc(misc(51, "Congratulations!"))}</h2>
    <p>${esc(misc(52, "You have earned a high score!"))}</p>
    <div class="hs-entry">
      <p>${esc(misc(37, "Your total Score:"))} ${score}</p>
      <label for="hs-name">${esc(misc(53, "Enter your name:"))}</label>
      <input id="hs-name" type="text" maxlength="${HIGH_SCORE_NAME_MAX}" autocomplete="off" spellcheck="false" />
    </div>
    <div class="choices hs-buttons">
      <button type="button" class="hs-ok">${esc(misc(9, "OK"))}</button>
      <button type="button" class="hs-cancel">${esc(misc(10, "CANCEL"))}</button>
    </div>`);
  const input = el.querySelector<HTMLInputElement>("input")!;
  // Keep typing away from the game's key handlers (Controls cancels WASD, Space and the like).
  input.addEventListener("keydown", (e) => e.stopPropagation());
  input.addEventListener("input", () => {
    // ch == ' ' || fontMap[ch] != -1, while temp < 28
    const clean = [...input.value].filter(highScoreNameAccepts).slice(0, HIGH_SCORE_NAME_MAX).join("");
    if (clean !== input.value) input.value = clean;
  });

  return new Promise((resolve) => {
    const finish = (name: string | null) => {
      window.removeEventListener("keydown", onKey, true);
      stopPad();
      el.remove();
      resolve(name);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Enter" || e.code === "NumpadEnter") finish(input.value);
      else if (e.code === "Escape") finish(null);
      else return;
      e.preventDefault();
      e.stopPropagation();
    };
    // A pad can't type: A or Start keeps what's there (blank if nothing), B cancels.
    const stopPad = pollPad((b) => {
      if (b === 0 || b === 9) finish(input.value);
      else if (b === 1) finish(null);
    });
    el.querySelector(".hs-ok")!.addEventListener("click", () => finish(input.value));
    el.querySelector(".hs-cancel")!.addEventListener("click", () => finish(null));
    window.addEventListener("keydown", onKey, true);
    input.focus();
  });
}

/**
 * The end of JE_highScoreCheck (mainint.c L2113-2152): the episode's table with the new entry
 * glowing, until a key, click or pad button.
 */
function showHighScoreEntered(saveFiles: HighScoreEntry[], slot: number, first_slot: number, slot_limit: number, episodeName: string): Promise<void> {
  const rows: string[] = [];
  for (let i = first_slot; i < slot_limit; ++i) rows.push(row(i - first_slot + 1, saveFiles[i], null, i === slot ? "hs-new" : ""));
  const el = overlay(`
    <h2>${esc(misc(50, "High Scores"))}</h2>
    <h3 class="hs-episode">${esc(episodeName)}</h3>
    <div class="hs-tables"><table>${rows.join("")}</table></div>
    <p><span class="key">${esc(misc(4, "Press a key"))}</span></p>`);

  return new Promise((resolve) => {
    const done = () => {
      window.removeEventListener("keydown", onKey, true);
      el.removeEventListener("click", done);
      stopPad();
      el.remove();
      resolve();
    };
    const onKey = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
      done();
    };
    const stopPad = pollPad(done);
    el.addEventListener("click", done);
    window.addEventListener("keydown", onKey, true);
  });
}

/**
 * JE_highScoreCheck (mainint.c L1921-2156) for a one-player game: if the score beats an entry in
 * the starting episode's table, play the fanfare, ask for a name, store it, and show the table.
 * The caller decides when it's due (highScoreCheckDue).
 */
export async function highScoreCheck(host: HighScoreHost, initial_episode_num: number): Promise<void> {
  const saveFiles = loadHighScores();
  const temp_score = highScoreCheckScore();
  const slot = JE_highScoreCheckSlot(saveFiles, initial_episode_num, g.twoPlayerMode, temp_score);
  if (slot < 0) return;

  host.music.play(SONG_HIGH_SCORE);
  const name = await askHighScoreName(temp_score);
  JE_highScoreCheckEnter(saveFiles, slot, temp_score, name, g.difficultyLevel);
  saveHighScores(saveFiles);

  const { first_slot, slot_limit } = highScoreTable(initial_episode_num, g.twoPlayerMode);
  await showHighScoreEntered(saveFiles, slot, first_slot, slot_limit, host.episodeName[g.episodeNum]?.trim() ?? "");
}
