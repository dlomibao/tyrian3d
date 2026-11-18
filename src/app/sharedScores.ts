// The shared high-score list on the high-score screens (src/app/highScoresScreen.ts), in builds
// with VITE_SCORES_API: the episode's top 20 beside the local tables, and after a name is entered,
// whether it went on the shared list (and where) or why it can't. Without the API, or when it
// can't be reached, these screens are exactly as before.

import { fetchTopScores, scoresEnabled, type SharedScore, type SubmitResult } from "../scores/api";
import { ineligibleReason, submitHighScore } from "../scores/session";
import { DIFFICULTIES } from "../../server/scores/lib/plausibility.mjs";
import { h } from "../ui";

/** What the name entry needs from the shared list for one high-score check. */
export interface SharedHighScoreHost {
  /** Why this run can't go on the list (shown under the table), or null. */
  ineligible: string | null;
  /** Submit the entered name's score. */
  submit(name: string, score: number): Promise<SubmitResult | null>;
}

/** The shared list's part in a high-score check, or undefined without the list. */
export function sharedHighScores(episode: number, ended: "quit" | "episode"): SharedHighScoreHost | undefined {
  if (!scoresEnabled()) return undefined;
  return {
    ineligible: ineligibleReason(episode),
    submit: (name, score) => submitHighScore(name, score, episode, ended),
  };
}

const REJECTED = "The global leaderboard didn't accept this score.";

/** The line under the entered table: the submission's outcome, filled in when it arrives. */
export function sharedResultLine(shared: SharedHighScoreHost, pending: Promise<SubmitResult | null> | null): HTMLElement {
  const p = h("p", { class: "hs-shared-note", attrs: { "aria-live": "polite" } });
  if (shared.ineligible) {
    p.textContent = shared.ineligible;
    return p;
  }
  p.textContent = "Sending to the global leaderboard…";
  void pending?.then((r) => {
    if (!r) p.textContent = "The global leaderboard couldn't be reached.";
    else if (r.ok) p.textContent = `Global leaderboard: rank ${r.rank}${r.total ? ` of ${r.total}` : ""}.`;
    else p.textContent = REJECTED;
  });
  return p;
}

/**
 * The shared top 20 for an episode, with a difficulty filter (All and the six the game offers).
 * `names[d]` is difficulty d's name. Returns the panel and how to show another episode.
 */
export function sharedListPanel(names: string[], difficultyNameB: string[]): { el: HTMLElement; show(episode: number): void; cycle(delta: number): void } | null {
  if (!scoresEnabled()) return null;
  const filters = [0, ...DIFFICULTIES];
  let filter = 0;
  let episode = 1;
  let seq = 0;
  const label = (d: number) => (d === 0 ? "All" : names[d]?.trim() || difficultyNameB[d]?.trim() || `Level ${d}`);
  const tabs = h("div", { class: "hs-shared-tabs", attrs: { role: "tablist" } });
  const list = h("ol", { class: "hs-table hs-shared-table" });
  const status = h("p", { class: "hs-shared-status", attrs: { "aria-live": "polite" } });
  // The public play stats (stats/index.html, D263), built alongside the game in these builds only.
  // A new tab, so following it never ends the game in this one.
  const stats = h("a", { class: "hs-shared-stats", text: "Play stats from every pilot ›", attrs: { href: "stats/", target: "_blank", rel: "noopener" } });
  const el = h("section", { class: "hs-shared", attrs: { "aria-label": "Global leaderboard" } }, h("span", { class: "ui-label", text: "Global leaderboard" }), tabs, list, status, stats);

  const drawTabs = () =>
    tabs.replaceChildren(
      ...filters.map((d, i) => {
        const b = h("button", { class: `hs-shared-tab${i === filter ? " is-on" : ""}`, text: label(d), attrs: { type: "button", role: "tab", "aria-selected": String(i === filter) } });
        b.addEventListener("click", () => {
          filter = i;
          load();
        });
        return b;
      }),
    );
  const row = (s: SharedScore) =>
    h(
      "li",
      { class: "hs-row" },
      h("span", { class: "hs-rank", text: String(s.rank) }),
      h("span", { class: "hs-score", text: String(s.score) }),
      h("span", { class: "hs-name", text: s.name }),
      h("span", { class: "hs-diff", text: label(s.difficulty) }),
    );
  const load = () => {
    drawTabs();
    const mine = ++seq;
    list.replaceChildren();
    status.textContent = "Loading…";
    void fetchTopScores(episode, filters[filter] || undefined).then((scores) => {
      if (mine !== seq) return;
      if (!scores) status.textContent = "The global leaderboard couldn't be reached.";
      else {
        list.replaceChildren(...scores.map(row));
        status.textContent = scores.length ? "" : "No scores yet.";
      }
    });
  };
  return {
    el,
    show(ep: number) {
      episode = ep;
      load();
    },
    cycle(delta: number) {
      filter = (filter + delta + filters.length) % filters.length;
      load();
    },
  };
}
