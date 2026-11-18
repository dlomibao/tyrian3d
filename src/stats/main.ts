// The public play-stats page (stats/index.html, D263): GET /api/stats/summary drawn in the game's
// own look (src/ui tokens: umber glass panes in a bronze rim, copper for labels, phosphor for the
// numbers). Only builds with VITE_SCORES_API ship it (vite.config.ts); on any other server it says
// stats aren't collected there. Names come from the game data (names.ts); the shared top scores
// from GET /api/scores.

import "../ui/tokens.css";
import "./stats.css";
import { fetchTopScores, levelsText, SCORES_API, type SharedScore } from "../scores/api";
import { h } from "../ui/components";
import { barList, dailyColumns, deathGrid, fmt, installTooltip, outcomeBar, pct, scoreRange, splitBar, type BarRow } from "./charts";
import {
  branches,
  dailySeries,
  deathMaps,
  difficultiesIn,
  episodesPlayed,
  folded,
  funnel,
  headline,
  highlights,
  isEmpty,
  levelRows,
  openers,
  overall,
  purchases,
  ranked,
  sum,
  tradeCount,
} from "./model";
import { EPISODES, gameNames, loadGameNames, type GameNames, type ItemKind } from "./names";
import { asSummary, type StatsSummary } from "./summary";

const root = document.getElementById("stats") as HTMLElement;
/** The game, relative to this page (/stats/ → /). */
const GAME_URL = "../";
const DATA_DIR = "../tyrian-data/";
const SITE = "https://tyrian3d.lomibao.net/";

const regionNames = (() => {
  try {
    return new Intl.DisplayNames(["en"], { type: "region" });
  } catch {
    return null;
  }
})();
const countryName = (cc: string) => (cc === "ZZ" ? "Unknown" : (regionNames?.of(cc) ?? cc));

// --- page frame ---

function header(s: StatsSummary | null): HTMLElement {
  const asOf = s
    ? h("p", { class: "st-asof" }, "Updated every 10 minutes · as of ", h("time", { attrs: { datetime: s.generatedAt }, text: new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(s.generatedAt)) }))
    : null;
  return h(
    "header",
    { class: "st-hero" },
    h(
      "a",
      { class: "st-logo", attrs: { href: GAME_URL, "aria-label": "Tyrian 3D: play the game" } },
      h("img", { attrs: { src: "../art/title/tyrian-logo.svg", alt: "", width: "304", height: "121" } }),
      h("span", { class: "st-logo__tag", text: "3D" }),
    ),
    h("div", { class: "st-hero__text" }, h("h1", { class: "ui-title st-title" }, h("small", { class: "ui-title__kicker", text: "Play stats" }), h("span", { text: "Flight records" })), h("p", { class: "st-lead", text: "Every level flown in Tyrian 3D, summed up: how far pilots get, where ships go down, what they fly and where they fly from." }), asOf),
    h("a", { class: "st-play", attrs: { href: GAME_URL }, text: "Play Tyrian 3D" }),
  );
}

function footer(): HTMLElement {
  return h(
    "footer",
    { class: "st-foot" },
    h("p", { class: "st-privacy" }, h("b", { text: "Anonymous: " }), "a random ID kept in your browser and your country, never your IP address. Turn it off in Options → Share anonymous play stats."),
    h("p", {}, "Cheated or debug runs count as pilots, runs and countries but are left out of the gameplay figures. Scores are checked for plausibility, not replayed."),
    h(
      "p",
      { class: "st-credit" },
      h("a", { attrs: { href: "https://db-ip.com", rel: "noopener" }, text: "IP geolocation by DB-IP" }),
      " (",
      h("a", { attrs: { href: "https://creativecommons.org/licenses/by/4.0/", rel: "noopener license" }, text: "CC BY 4.0" }),
      ") · Tyrian 2.1 by Eclipse Software; Tyrian 3D builds on OpenTyrian · ",
      h("a", { attrs: { href: GAME_URL }, text: "Play" }),
    ),
  );
}

function pane(id: string, kicker: string, heading: string, ...children: (Node | null)[]): HTMLElement {
  return h("section", { class: "st-pane", attrs: { id, "aria-labelledby": `${id}-h` } }, h("h2", { class: "ui-title st-pane__title", attrs: { id: `${id}-h` } }, h("small", { class: "ui-title__kicker", text: kicker }), h("span", { text: heading })), ...children);
}

const label = (text: string) => h("h3", { class: "ui-label", text });
const note = (text: string, cls = "") => h("p", { class: `st-note ${cls}`, text });
const emptyNote = (text: string) => h("p", { class: "st-empty-note", text });

// --- sections ---

function tiles(s: StatsSummary): HTMLElement {
  const t = headline(s);
  const flown = t.cleared + t.lost + t.quit;
  const tile = (value: number, name: string, sub: string) => h("li", { class: "st-tile" }, h("span", { class: "st-tile__value ui-phos", text: fmt(value) }), h("span", { class: "st-tile__name", text: name }), h("span", { class: "st-tile__sub", text: sub }));
  return h(
    "ul",
    { class: "st-tiles", attrs: { "aria-label": "Totals" } },
    tile(t.players, "Pilots", "sharing anonymous stats"),
    tile(t.returning, "Came back", t.players ? `${pct(t.returning / t.players)} flew on another day` : "flew on another day"),
    tile(t.runs, "Games started", "new games, every mode"),
    tile(t.reports, "Levels flown", "attempts, retries included"),
    tile(t.cleared, "Levels cleared", flown ? `${pct(t.cleared / flown)} of attempts` : "of attempts"),
    tile(t.lost, "Ships lost", flown ? `${pct(t.lost / flown)} of attempts` : "of attempts"),
    tile(t.countries, t.countries === 1 ? "Country" : "Countries", "pilots flew from"),
    tile(t.submitted, "Scores sent", "to the global leaderboard"),
  );
}

function notable(s: StatsSummary, names: GameNames): HTMLElement | null {
  const hl = highlights(s);
  const items: HTMLElement[] = [];
  const fact = (big: string, text: string) => h("li", { class: "st-fact" }, h("b", { text: big }), h("span", { text }));
  if (hl.deadliest) items.push(fact(pct(hl.deadliest.rate), `of attempts at ${names.level(hl.deadliest.ep, hl.deadliest.lvl)} end with the ship lost: the deadliest level (${names.episode(hl.deadliest.ep)}, ${fmt(hl.deadliest.attempts)} attempts).`));
  if (hl.topScore) items.push(fact(fmt(hl.topScore.p50), `points is the median haul for clearing ${names.level(hl.topScore.ep, hl.topScore.lvl)}, the richest level (${names.episode(hl.topScore.ep)}).`));
  if (hl.topShip) items.push(fact(pct(hl.topShip.share), `of levels are flown in the ${names.item("ship", Number(hl.topShip.id))}, the favourite ship.`));
  if (hl.topWeapon) items.push(fact(pct(hl.topWeapon.share), `of levels are flown with the ${names.item("weapon", Number(hl.topWeapon.id))} up front, the favourite front gun.`));
  return items.length ? h("ul", { class: "st-facts", attrs: { "aria-label": "Notable" } }, ...items) : null;
}

function pilots(s: StatsSummary): HTMLElement {
  const today = s.generatedAt.slice(0, 10);
  const days = dailySeries(s.players.perDay, today).slice(-90);
  const chart = days.length
    ? h(
        "div",
        { class: "st-chart" },
        h("ul", { class: "st-legend" }, h("li", {}, h("span", { class: "st-key st-fill-new" }), "New pilots"), h("li", {}, h("span", { class: "st-key st-fill-returning" }), "Returning pilots")),
        dailyColumns(days),
      )
    : emptyNote("No pilots yet.");
  const dist = (title: string, c: Record<string, number>, unit: string) => {
    const rows = folded(c, 5);
    const total = sum(rows.map((r) => r.n));
    const max = Math.max(1, ...rows.map((r) => r.n));
    return h(
      "div",
      { class: "st-mini" },
      label(title),
      total
        ? barList(
            rows.map((r) => ({ label: `${r.label} ${r.label === "1" ? unit : `${unit}s`}`, n: r.n, scale: r.n / max, value: fmt(r.n), tip: `${fmt(r.n)} pilots (${pct(r.n / total)})` })),
            "st-bars--tight",
          )
        : emptyNote("Nothing yet."),
    );
  };
  return pane(
    "pilots",
    "Pilots",
    "Who's flying",
    h("div", { class: "st-split-cols" }, h("div", {}, label(days.length > 1 ? `Pilots per day · last ${days.length} days` : "Pilots per day"), chart), h("div", { class: "st-minis" }, dist("Games per pilot", s.players.runsPerPlayer, "game"), dist("Days per pilot", s.players.daysPerPlayer, "day"))),
  );
}

function episodes(s: StatsSummary, names: GameNames): HTMLElement {
  const played = episodesPlayed(s);
  if (played.length === 0) return pane("episodes", "Episodes", "The campaign", emptyNote("No levels flown yet."));
  const busiest = [...played].sort((a, b) => b.attempts - a.attempts)[0].ep;
  const body = h("div", { class: "st-episode" });
  const tabs = h("div", { class: "st-tabs", attrs: { role: "tablist", "aria-label": "Episode" } });
  let current = busiest;
  const draw = () => {
    tabs.replaceChildren(
      ...EPISODES.map((ep) => {
        const has = played.some((p) => p.ep === ep);
        const b = h("button", {
          class: `st-tab${ep === current ? " is-on" : ""}`,
          attrs: { type: "button", role: "tab", "aria-selected": String(ep === current), "aria-controls": "st-episode-body", ...(has ? {} : { disabled: "" }) },
        }, h("small", { text: `Episode ${ep}` }), h("span", { text: names.episode(ep) }));
        b.addEventListener("click", () => {
          current = ep;
          draw();
        });
        return b;
      }),
    );
    body.replaceChildren(episode(s, names, current));
  };
  body.id = "st-episode-body";
  body.setAttribute("role", "tabpanel");
  draw();
  return pane("episodes", "Episodes", "The campaign", tabs, body);
}

function episode(s: StatsSummary, names: GameNames, ep: number): HTMLElement {
  const out = h("div", { class: "st-ep" });
  // How far pilots get.
  const f = funnel(s, ep);
  if (f.length) {
    out.append(
      h(
        "div",
        { class: "st-block" },
        label("How far pilots get"),
        note(`Of ${fmt(f[0].players)} ${f[0].players === 1 ? "pilot" : "pilots"} who flew ${names.episode(ep)}, how many reached each level of their route.`),
        h(
          "ol",
          { class: "st-funnel", attrs: { style: `--cols:${f.length}` } },
          ...f.map((x) =>
            h(
              "li",
              { attrs: { "data-tip": `Level ${x.k} of the route: ${fmt(x.players)} ${x.players === 1 ? "pilot" : "pilots"} (${pct(x.share)})` } },
              h("span", { class: "st-funnel__track" }, h("span", { class: "st-funnel__pct", text: pct(x.share) }), h("span", { class: "st-funnel__bar", attrs: { style: `--h:${(x.share * 100).toFixed(2)}%` } })),
              h("span", { class: "st-funnel__k", text: String(x.k) }),
            ),
          ),
        ),
        h("p", { class: "st-axis-note", text: "Level of the route →" }),
      ),
    );
  }

  // Level by level, with a difficulty filter.
  const diffs = difficultiesIn(s, ep);
  let only: number | null = null;
  const tableWrap = h("div", {});
  const chips = h("div", { class: "st-chips", attrs: { role: "group", "aria-label": "Starting difficulty" } });
  const drawTable = () => {
    chips.replaceChildren(
      ...[null, ...diffs].map((d) => {
        const b = h("button", { class: `st-chip${d === only ? " is-on" : ""}`, attrs: { type: "button", "aria-pressed": String(d === only) }, text: d === null ? "All difficulties" : names.difficulty(d) });
        b.addEventListener("click", () => {
          only = d;
          drawTable();
        });
        return b;
      }),
    );
    tableWrap.replaceChildren(levelTable(s, names, ep, only));
  };
  drawTable();
  out.append(
    h(
      "div",
      { class: "st-block" },
      label("Level by level"),
      h(
        "div",
        { class: "st-table-head" },
        h("ul", { class: "st-legend" }, h("li", {}, h("span", { class: "st-key st-seg--finished" }), "Cleared"), h("li", {}, h("span", { class: "st-key st-seg--died" }), "Ship lost"), h("li", {}, h("span", { class: "st-key st-seg--quit" }), "Quit")),
        diffs.length > 1 ? chips : null,
      ),
      tableWrap,
      names.sharedNames(ep) ? note("(2) marks a second level of the same name, such as a hard-difficulty twin or a later visit.", "st-more-note") : null,
    ),
  );

  // Route choices.
  const br = branches(s, ep);
  const first = openers(s, ep);
  if (br.length || first.length > 1) {
    const blocks: HTMLElement[] = [];
    if (first.length > 1) {
      const total = sum(first.map((x) => x.n));
      blocks.push(h("div", { class: "st-branch" }, h("p", { class: "st-branch__from" }, "First level"), splitBar(first.map((x) => ({ label: names.level(ep, x.lvl), n: x.n, share: x.n / total })), "runs")));
    }
    for (const b of br.slice(0, 8))
      blocks.push(
        h(
          "div",
          { class: "st-branch" },
          h("p", { class: "st-branch__from" }, "After ", h("b", { text: names.level(ep, b.from) }), h("small", { text: ` · ${fmt(b.total)}` })),
          splitBar(b.to.map((t) => ({ label: names.level(ep, t.lvl), n: t.n, share: t.share })), "pilots went on"),
        ),
      );
    out.append(h("div", { class: "st-block" }, label("Which way pilots go"), note("Where the route splits (the item screen's next-level choice, a secret warp, or the starting difficulty), how pilots went on."), h("div", { class: "st-branches" }, ...blocks)));
  }

  // Where ships go down.
  const maps = deathMaps(s, ep);
  if (maps.length) {
    const grid = h("div", { class: "st-maps" });
    const LIMIT = 8;
    const drawMaps = (all: boolean) =>
      grid.replaceChildren(
        ...(all ? maps : maps.slice(0, LIMIT)).map((m) =>
          h("figure", { class: "st-map" }, deathGrid(m.cells, s.deathBucketPx, names.level(ep, m.lvl)) as unknown as HTMLElement, h("figcaption", {}, h("span", { text: names.level(ep, m.lvl) }), h("b", { class: "ui-phos", text: fmt(m.total) }))),
        ),
      );
    drawMaps(false);
    const more = maps.length > LIMIT ? h("button", { class: "ui-button st-more", attrs: { type: "button" }, text: `Show all ${maps.length} levels` }) : null;
    more?.addEventListener("click", () => {
      drawMaps(true);
      more.remove();
    });
    out.append(
      h(
        "div",
        { class: "st-block" },
        label("Where ships go down"),
        h("div", { class: "st-maps-head" }, note("Each box is the playfield, the way ahead at the top. A square is 16 game pixels; the brighter, the more ships lost there. Busiest levels first."), h("div", { class: "st-ramp", attrs: { "aria-hidden": "true" } }, h("span", { text: "fewer" }), h("i"), h("span", { text: "more" }))),
        grid,
        more,
      ),
    );
  }

  return out;
}

function levelTable(s: StatsSummary, names: GameNames, ep: number, only: number | null): HTMLElement {
  const rows = levelRows(s, ep, names.levelOrder(ep), only);
  if (!rows.length) return emptyNote("No levels flown at this difficulty yet.");
  const maxScore = scoreScale(rows.map((r) => r.score?.p75 ?? 0));
  return h(
    "div",
    { class: "st-levels", attrs: { role: "table", "aria-label": `${names.episode(ep)}: levels` } },
    h(
      "div",
      { class: "st-levels__row st-levels__head", attrs: { role: "row" } },
      h("span", { attrs: { role: "columnheader" }, text: "Level" }),
      h("span", { class: "st-num", attrs: { role: "columnheader" }, text: "Attempts" }),
      h("span", { attrs: { role: "columnheader" }, text: "Outcome" }),
      h("span", { class: "st-num", attrs: { role: "columnheader" }, text: "Cleared" }),
      h("span", { attrs: { role: "columnheader" }, text: "Points gained on a clear" }),
    ),
    ...rows.map((r) => {
      const name = names.level(ep, r.lvl);
      return h(
        "div",
        { class: "st-levels__row", attrs: { role: "row" } },
        h("span", { class: "st-levels__name", attrs: { role: "rowheader" }, text: name }),
        h("span", { class: "st-num st-levels__n ui-phos", attrs: { role: "cell" }, text: fmt(r.attempts) }),
        h("span", { class: "st-levels__bar", attrs: { role: "cell" } }, outcomeBar(r.outcome, name)),
        h("span", { class: "st-num st-levels__rate", attrs: { role: "cell" }, text: pct(r.clearRate) }),
        h(
          "span",
          { class: "st-levels__score", attrs: { role: "cell" } },
          r.score && r.score.p50 !== undefined ? scoreRange(r.score, maxScore, name) : h("span", { class: "st-dim", text: "no clears yet" }),
          r.score && r.score.p50 !== undefined ? h("b", { class: "ui-phos", text: fmt(r.score.p50) }) : null,
        ),
      );
    }),
  );
}

/**
 * The score column's shared scale: the largest middle half's top, unless one level dwarfs the rest
 * (ASTEROID?'s bonus haul): then the runner-up's, and that level's bar runs off the end.
 */
function scoreScale(p75s: number[]): number {
  const sorted = p75s.filter((v) => v > 0).sort((a, b) => b - a);
  if (sorted.length === 0) return 1;
  if (sorted.length > 1 && sorted[0] > 2.5 * sorted[1]) return sorted[1] * 1.25;
  return sorted[0] * 1.08;
}

const SLOT_KIND: Record<string, ItemKind> = { ship: "ship", front: "weapon", rear: "weapon", shield: "shield", generator: "generator", sidekick: "sidekick" };
const SLOT_TAG: Record<string, string> = { ship: "Ship", front: "Front", rear: "Rear", shield: "Shield", generator: "Generator", sidekick: "Sidekick" };

function rankedBars(c: Record<string, number>, kind: ItemKind, names: GameNames, limit: number, what: string): HTMLElement {
  const r = ranked(c, ["0"]);
  if (!r.length) return emptyNote("Nothing yet.");
  const top = r.slice(0, limit);
  const rows: BarRow[] = top.map((x) => ({ label: names.item(kind, Number(x.id)), n: x.n, scale: x.n / top[0].n, value: pct(x.share), tip: `${names.item(kind, Number(x.id))}: ${fmt(x.n)} ${what} (${pct(x.share)})` }));
  const rest = r.slice(limit);
  return h("div", {}, barList(rows), rest.length ? note(`and ${rest.length} more (${pct(sum(rest.map((x) => x.share)))})`, "st-more-note") : null);
}

function shop(s: StatsSummary, names: GameNames): HTMLElement {
  const ships = overall(s.ships);
  const weapons = overall(s.weapons);
  const bought = purchases(s);
  const max = bought[0]?.n ?? 1;
  const upgrades = tradeCount(s, "upgrade");
  const buys = tradeCount(s, "buy");
  const sells = tradeCount(s, "sell");
  return pane(
    "hangar",
    "Hangar",
    "Ships, guns and the shop",
    note("Every episode together. Ships and guns: share of all levels flown with each."),
    h(
      "div",
      { class: "st-cols-3" },
      h("div", {}, label("Ships flown"), rankedBars(ships, "ship", names, 8, "levels")),
      h("div", {}, label("Front guns"), rankedBars(weapons, "weapon", names, 8, "levels")),
      h(
        "div",
        {},
        label("Most bought"),
        bought.length
          ? barList(
              bought.slice(0, 8).map((b) => {
                const name = names.item(SLOT_KIND[b.slot], b.id);
                return { tag: SLOT_TAG[b.slot], label: name, n: b.n, scale: b.n / max, value: fmt(b.n), tip: `${SLOT_TAG[b.slot]}: ${name}, bought ${fmt(b.n)} ${b.n === 1 ? "time" : "times"}` };
              }),
            )
          : emptyNote("Nothing bought yet."),
        buys || upgrades
          ? h(
              "ul",
              { class: "st-shop-totals" },
              h("li", {}, h("b", { class: "ui-phos", text: fmt(buys) }), " items bought"),
              h("li", {}, h("b", { class: "ui-phos", text: fmt(sells) }), " sold to make room"),
              h("li", {}, h("b", { class: "ui-phos", text: fmt(upgrades) }), " weapon power-ups"),
            )
          : null,
      ),
    ),
  );
}

function countries(s: StatsSummary): HTMLElement {
  const r = ranked(s.countries.runs ?? {});
  const LIMIT = 12;
  const top = r.slice(0, LIMIT);
  const rest = r.slice(LIMIT);
  const body = r.length
    ? h(
        "div",
        {},
        barList(top.map((c) => ({ label: countryName(c.id), n: c.n, scale: c.n / top[0].n, value: fmt(c.n), tip: `${countryName(c.id)}: ${fmt(c.n)} ${c.n === 1 ? "game" : "games"} (${pct(c.share)})` })), "st-bars--countries"),
        rest.length ? note(`and ${rest.length} more ${rest.length === 1 ? "country" : "countries"}: ${fmt(sum(rest.map((c) => c.n)))} games`, "st-more-note") : null,
      )
    : emptyNote("No games yet.");
  return pane("countries", "Worldwide", "Where pilots fly from", note("Games started, by the country of the connection. Unknown: an address the geolocation table doesn't place."), body);
}

function topScores(names: GameNames): HTMLElement {
  const grid = h("div", { class: "st-scores" });
  const sec = pane("scores", "Global leaderboard", "Top pilots", note("The top five of each episode's global leaderboard, every difficulty. The full lists are on the game's High Scores screen."), grid);
  for (const ep of EPISODES) {
    const list = h("ol", { class: "st-score-list" }, h("li", { class: "st-dim", text: "Loading…" }));
    grid.append(h("div", { class: "st-score-card" }, h("h3", { class: "st-score-ep" }, h("small", { text: `Episode ${ep}` }), h("span", { text: names.episode(ep) })), list));
    void fetchTopScores(ep).then((scores: SharedScore[] | null) => {
      if (!scores) list.replaceChildren(h("li", { class: "st-dim", text: "Couldn't be loaded." }));
      else if (!scores.length) list.replaceChildren(h("li", { class: "st-dim", text: "No scores yet. Be the first." }));
      else
        list.replaceChildren(
          ...scores.slice(0, 5).map((x) =>
            h(
              "li",
              { class: "st-score" },
              h("span", { class: "st-score__rank", text: String(x.rank) }),
              h("span", { class: "st-score__name", text: x.name }),
              h("span", { class: "st-score__pts ui-phos", text: fmt(x.score) }),
              h("span", { class: "st-score__diff", text: `${names.difficulty(x.difficulty)} · ${levelsText(x.levels)}` }),
            ),
          ),
        );
    });
  }
  return sec;
}

// --- states ---

function emptyState(): HTMLElement {
  const item = (title: string, text: string) => h("li", {}, h("b", { text: title }), h("span", { text }));
  const ghostBars = h("div", { class: "st-ghost", attrs: { "aria-hidden": "true" } }, ...[100, 78, 61, 49, 40, 33, 27, 22, 18].map((v) => h("i", { attrs: { style: `--h:${v}%` } })));
  return h(
    "section",
    { class: "st-pane st-empty" },
    h("div", { class: "st-empty__art" }, ghostBars),
    h(
      "div",
      { class: "st-empty__text" },
      h("h2", { class: "ui-title" }, h("small", { class: "ui-title__kicker", text: "No flights logged yet" }), h("span", { text: "The records start with you" })),
      h("p", { text: "Stats appear here as people play. Every level a pilot clears, loses or quits adds to:" }),
      h(
        "ul",
        { class: "st-empty__list" },
        item("Pilots and games", "how many fly, how often they come back, games per pilot."),
        item("How far pilots get", "each episode's route, level by level, and the clear rates."),
        item("Where ships go down", "a heat map of losses on each level's playfield."),
        item("Hangar", "favourite ships and front guns, and what the shop sells most."),
        item("Worldwide", "the countries pilots fly from."),
        item("Top pilots", "each episode's global leaderboard."),
      ),
      h("a", { class: "st-play st-play--big", attrs: { href: GAME_URL }, text: "Fly the first mission" }),
    ),
  );
}

function message(title: string, text: string, action?: HTMLElement): HTMLElement {
  return h("section", { class: "st-pane st-message" }, h("h2", { class: "ui-title" }, h("span", { text: title })), h("p", { text }), action ?? null);
}

// --- boot ---

async function fetchSummary(): Promise<StatsSummary | null> {
  try {
    const r = await fetch(`${SCORES_API}/stats/summary`, { signal: AbortSignal.timeout(10000) });
    return r.ok ? asSummary(await r.json()) : null;
  } catch {
    return null;
  }
}

function render(nodes: (Node | null)[]): void {
  root.replaceChildren(...nodes.filter((n): n is Node => n !== null));
  root.setAttribute("aria-busy", "false");
}

async function main(): Promise<void> {
  installTooltip(root);
  if (!SCORES_API) {
    render([header(null), message("Stats aren't collected here", "This copy of Tyrian 3D doesn't share play stats. The public stats are on tyrian3d.lomibao.net.", h("a", { class: "st-play", attrs: { href: `${SITE}stats/` }, text: "Open the public stats" })), footer()]);
    return;
  }
  const namesP = loadGameNames(DATA_DIR).catch(() => gameNames(null, []));
  const s = await fetchSummary();
  if (!s) {
    const retry = h("button", { class: "st-play", attrs: { type: "button" }, text: "Try again" });
    retry.addEventListener("click", () => location.reload());
    render([header(null), message("The stats couldn't be loaded", "The stats service didn't answer. Try again in a minute.", retry), footer()]);
    return;
  }
  const names = await namesP;
  if (isEmpty(s)) {
    render([header(s), emptyState(), footer()]);
    return;
  }
  render([header(s), tiles(s), notable(s, names), pilots(s), episodes(s, names), shop(s, names), h("div", { class: "st-pair" }, countries(s), topScores(names)), footer()]);
}

void main();
