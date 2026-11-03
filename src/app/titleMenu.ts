// The title menu's two steps (DECISIONS.md D64), as state without the DOM: src/app/screens.ts draws
// it and does what it asks. The top step is the original title's list (Start New Game, Load Game,
// High Scores, Options, and the music style); Start New Game opens the second, the episodes with
// the difficulty row and Back, where choosing an episode starts.

import type { Intent } from "../ui/nav";

export type TitleStep = "main" | "episodes";

/** One line of a step. */
export type TitleRow =
  | { kind: "start" }
  | { kind: "more"; index: number }
  | { kind: "music" }
  | { kind: "episode"; index: number }
  | { kind: "difficulty" }
  | { kind: "back" };

/** What the screen should do after an input. */
export type TitleAction =
  | { kind: "none" }
  /** Only the focus or a value moved: repaint. */
  | { kind: "paint" }
  /** The step changed: redraw it (with its entrance). */
  | { kind: "step" }
  /** Open one of the other entries (Load Game, High Scores, Options). */
  | { kind: "more"; index: number }
  /** The music style changed to `index`. */
  | { kind: "music"; index: number }
  /** Start the chosen episode at the chosen difficulty. */
  | { kind: "start" };

export interface TitleMenuConfig {
  /** How many episodes there are. */
  episodes: number;
  /** How many of the other entries (Load Game, High Scores, Options) follow Start New Game. */
  more: number;
  /** How many music styles (fewer than 2: no Music line). */
  musicStyles: number;
  /** How many difficulties the row offers now (more appear as their keys are typed). */
  difficulties: number;
  episode: number;
  difficulty: number;
  musicStyle: number;
}

export interface TitleMenuSnapshot {
  step: TitleStep;
  focus: number;
  episode: number;
  difficulty: number;
}

/** The title's menu state: which step, which line has the focus, and the values chosen. */
export class TitleMenu {
  step: TitleStep = "main";
  focus = 0;
  episode: number;
  difficulty: number;
  musicStyle: number;
  difficulties: number;

  constructor(private readonly cfg: TitleMenuConfig) {
    this.episode = clamp(cfg.episode, 0, cfg.episodes - 1);
    this.difficulties = Math.max(1, cfg.difficulties);
    this.difficulty = clamp(cfg.difficulty, 0, this.difficulties - 1);
    this.musicStyle = clamp(cfg.musicStyle, 0, Math.max(0, cfg.musicStyles - 1));
  }

  get hasMusic(): boolean {
    return this.cfg.musicStyles > 1;
  }

  /** The lines of a step, top to bottom. */
  rows(step: TitleStep = this.step): TitleRow[] {
    if (step === "main") {
      return [
        { kind: "start" },
        ...Array.from({ length: this.cfg.more }, (_, index) => ({ kind: "more" as const, index })),
        ...(this.hasMusic ? [{ kind: "music" as const }] : []),
      ];
    }
    return [...Array.from({ length: this.cfg.episodes }, (_, index) => ({ kind: "episode" as const, index })), { kind: "difficulty" }, { kind: "back" }];
  }

  get row(): TitleRow {
    return this.rows()[this.focus];
  }

  /** Go to a step, the focus on its first line (the episodes step: on the chosen episode). */
  open(step: TitleStep): TitleAction {
    this.step = step;
    this.focus = step === "episodes" ? this.episode : 0;
    return { kind: "step" };
  }

  /** Move the focus to a line (a pointer over it). */
  focusRow(i: number): TitleAction {
    const n = this.rows().length;
    if (i < 0 || i >= n || i === this.focus) return { kind: "none" };
    this.focus = i;
    this.syncEpisode();
    return { kind: "paint" };
  }

  /** The framework's intents (keys, pads); "start" and "alt" are the screen's own. */
  intent(intent: Intent): TitleAction {
    const n = this.rows().length;
    switch (intent) {
      case "up":
      case "down":
        this.focus = (this.focus + (intent === "down" ? 1 : -1) + n) % n;
        this.syncEpisode();
        return { kind: "paint" };
      case "left":
      case "right": {
        const d = intent === "right" ? 1 : -1;
        if (this.row.kind === "music") return this.cycleMusic(d);
        // On the episodes step left and right always pick the difficulty, as the old title's row did.
        if (this.step === "episodes") return this.stepDifficulty(d);
        return { kind: "none" };
      }
      case "accept":
        return this.select(this.focus);
      case "back":
        if (this.step === "episodes") return this.open("main");
        return { kind: "none" };
      default:
        return { kind: "none" };
    }
  }

  /** Choose a line (Enter, A, or a tap): what it does. */
  select(i: number): TitleAction {
    const row = this.rows()[i];
    if (!row) return { kind: "none" };
    this.focus = i;
    switch (row.kind) {
      case "start":
        return this.open("episodes");
      case "more":
        return { kind: "more", index: row.index };
      case "music":
        return this.cycleMusic(1);
      case "episode":
        this.episode = row.index;
        return { kind: "start" };
      case "difficulty":
        // A tap or Enter steps through the levels and wraps; left and right stop at the ends.
        this.difficulty = (this.difficulty + 1) % this.difficulties;
        return { kind: "paint" };
      case "back":
        return this.open("main");
    }
  }

  /** The next (or previous) music style. */
  cycleMusic(d: number): TitleAction {
    if (!this.hasMusic) return { kind: "none" };
    const n = this.cfg.musicStyles;
    this.musicStyle = (this.musicStyle + d + n) % n;
    return { kind: "music", index: this.musicStyle };
  }

  /** One difficulty up or down, stopping at the ends. */
  stepDifficulty(d: number): TitleAction {
    const next = clamp(this.difficulty + d, 0, this.difficulties - 1);
    if (next === this.difficulty) return { kind: "none" };
    this.difficulty = next;
    return { kind: "paint" };
  }

  /** More difficulties are on offer (a hidden one was revealed). */
  setDifficulties(n: number): void {
    this.difficulties = Math.max(1, n);
    this.difficulty = clamp(this.difficulty, 0, this.difficulties - 1);
  }

  /** Show the music style playing now, without switching it. */
  setMusicStyle(i: number): void {
    if (i >= 0 && i < this.cfg.musicStyles) this.musicStyle = i;
  }

  snapshot(): TitleMenuSnapshot {
    return { step: this.step, focus: this.focus, episode: this.episode, difficulty: this.difficulty };
  }

  restore(s: TitleMenuSnapshot): void {
    this.step = s.step;
    this.focus = clamp(s.focus, 0, this.rows().length - 1);
    this.episode = s.episode;
    this.difficulty = clamp(s.difficulty, 0, this.difficulties - 1);
  }

  /** On the episodes step the focused episode is the one Start would start. */
  private syncEpisode(): void {
    const row = this.row;
    if (row.kind === "episode") this.episode = row.index;
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}

/** Roman numerals for the episode marks (I to X is all Tyrian needs). */
export function roman(n: number): string {
  const numerals = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];
  return numerals[n] ?? String(n);
}

/**
 * An episode's name from the data ("Episode 1: Escape") as its numeral and title ("I", "Escape").
 * Names in another form are kept whole, with the episode's own number.
 */
export function episodeLabel(name: string | undefined, episode: number): { mark: string; title: string } {
  const text = name?.trim() || `Episode ${episode}`;
  const m = /^episode\s+(\d+)\s*[:.\-–]\s*(.+)$/i.exec(text);
  if (m) return { mark: roman(Number(m[1])), title: m[2].trim() };
  return { mark: roman(episode), title: text };
}
