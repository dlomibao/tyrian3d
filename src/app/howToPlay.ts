// "How to play": one card with the goal and the controls (D266). The pause menu opens it over itself;
// a one-player game shows it once by itself, before its first level starts (run.ts), and this browser
// remembers that it did.
//
// Every control on it is the game's own: the player's current key bindings (bindings.ts), the fixed
// pause keys (Escape and P, controls.ts), the mouse and touch steering (controls.ts), the HUD's touch
// targets (D100: the REAR GUN box and MODE lamps, the SIDEKICK boxes, only in the framed HUD), the
// touch pause button (pause.ts) and the standard-mapping gamepad (controls.ts).

import "./howToPlay.css";
import { button, h, showScreen, title } from "../ui";
import { keyName, keys as KEYS, type Action } from "./bindings";
import { interfaceStyle } from "../core/displayStyle";
import { touchHudParam } from "./touchHud";

export const HOW_TO_PLAY_STORAGE_KEY = "tyrian3d.howToPlaySeen";

/** The part of the Web Storage API the flag uses (localStorage, or a stand-in in tests). */
export interface FlagStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function defaultStorage(): FlagStorage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

/** Whether this browser has shown the card by itself before. Unreadable storage counts as seen (never nag). */
export function howToPlaySeen(storage: FlagStorage | null = defaultStorage()): boolean {
  try {
    return storage ? storage.getItem(HOW_TO_PLAY_STORAGE_KEY) === "1" : true;
  } catch {
    return true;
  }
}

export function markHowToPlaySeen(storage: FlagStorage | null = defaultStorage()): void {
  try {
    storage?.setItem(HOW_TO_PLAY_STORAGE_KEY, "1");
  } catch {
    /* storage full or unavailable: it may show once more next time */
  }
}

/** `?howtoplay=1` shows the card before every level whatever else holds (captures), `=0` never. */
export function howToPlayParam(search: string): boolean | null {
  const v = new URLSearchParams(search).get("howtoplay");
  return v === "1" ? true : v === "0" ? false : null;
}

export interface HowToPlayDue {
  /** The browser already showed it. */
  seen: boolean;
  twoPlayer: boolean;
  /** The URL's ?howtoplay. */
  param: boolean | null;
  /** The browser is driven by automation (navigator.webdriver: headless captures, test bots). */
  automated: boolean;
  /** The debug console started this game (D109). */
  console: boolean;
}

/** Whether a level about to start should wait for the card first. */
export function howToPlayDue(d: HowToPlayDue): boolean {
  if (d.param !== null) return d.param;
  return !d.seen && !d.twoPlayer && !d.automated && !d.console;
}

/** Which column the card lights: the device used last (<html data-input>), or touch when ?touchhud=1 forces the targets. */
export type HowToPlayColumn = "keys" | "touch" | "pad";
export function howToPlayColumn(input: string | undefined, touchParam: boolean | null): HowToPlayColumn {
  if (touchParam === true || input === "touch") return "touch";
  return input === "pad" ? "pad" : "keys";
}

/** The goal, in the game's terms. */
export const HOW_TO_PLAY_GOAL = [
  "Survive to the end of each level.",
  "Shoot everything, grab credits and power-ups. Between levels, buy guns, shields, generators and sidekicks in the shop.",
] as const;

const ARROWS = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
const WASD = ["KeyW", "KeyS", "KeyA", "KeyD"];

/** The move keys of each binding slot, as one cap each: "←↑↓→", "WASD", or the four keys' names. */
export function moveKeys(table: Record<Action, string[]>): string[] {
  const out: string[] = [];
  const slots = table.up.length;
  for (let s = 0; s < slots; s++) {
    const four = (["up", "down", "left", "right"] as const).map((a) => table[a][s] ?? "");
    if (four.every((c) => c === "")) continue;
    if (four.every((c, i) => c === ARROWS[i])) out.push("←↑↓→");
    else if (four.every((c, i) => c === WASD[i])) out.push("WASD");
    else out.push(four.map(keyName).join(" "));
  }
  return out;
}

/** One control's keys, by name ("" slots left out). */
export function actionKeys(table: Record<Action, string[]>, action: Action): string[] {
  return table[action].filter((c) => c !== "").map(keyName);
}

/** A row: its label, then groups of caps ("·" between groups; the sidekicks' left and right keys share one). */
export type HowToPlayRow = [label: string, groups: string[][]];
const each = (caps: string[]) => caps.map((c) => [c]);

/** The keyboard column's rows. */
export function keyboardRows(table: Record<Action, string[]> = KEYS): HowToPlayRow[] {
  const sidekicks: string[][] = [];
  const slots = table.leftSidekick.length;
  for (let s = 0; s < slots; s++) {
    const pair = [table.leftSidekick[s], table.rightSidekick[s]].filter((c) => c);
    if (pair.length) sidekicks.push(pair.map(keyName));
  }
  return [
    ["Move", each(moveKeys(table))],
    ["Fire", each(actionKeys(table, "fire"))],
    ["Rear gun mode", each(actionKeys(table, "changeFire"))],
    // Either sidekick key also drops a superbomb when the ship carries one (mainint.c's SUPER BOMB).
    ["Sidekicks, bombs", sidekicks],
    ["Pause", each(["Esc", "P"])], // controls.ts: fixed, not bindable (RESERVED_KEYS)
  ];
}

/** The touch column's rows. The HUD's targets exist only in the framed interface (D100). */
export function touchRows(framed: boolean): HowToPlayRow[] {
  const targets: HowToPlayRow[] = [
    ["Rear gun mode", [["Tap REAR GUN"]]],
    ["Sidekicks, bombs", [["Hold SIDEKICK"]]],
  ];
  return [["Move", [["Drag anywhere"]]], ["Fire", [["Auto while touching"]]], ...(framed ? targets : []), ["Pause", [["❚❚ top right"]]]];
}

/** The gamepad line: standard mapping, as controls.ts reads it. */
export const PAD_ROW: [string, string][] = [
  ["Stick ✛", "move"],
  ["A RT", "fire"],
  ["X", "mode"],
  ["LB RB", "sidekicks"],
  ["Start", "pause"],
];

function rows(list: HowToPlayRow[], capClass: string): HTMLElement {
  const dl = h("dl", { class: "htp-rows" });
  for (const [label, groups] of list) {
    const dd = h("dd");
    groups.forEach((caps, i) => {
      if (i > 0) dd.append(h("span", { class: "htp-or", text: "·" }));
      dd.append(h("span", { class: "htp-group" }, ...caps.map((c) => h("kbd", { class: `ui-key ${capClass}`, text: c }))));
    });
    dl.append(h("dt", { text: label }), dd);
  }
  return dl;
}

export interface HowToPlayOptions {
  /** Over another screen (the pause menu), which gets its input back when this closes. */
  over?: boolean;
}

/** Show the card; resolves once the player dismisses it (any accept, back or Start, a tap, or Got it). */
export function showHowToPlay(opts: HowToPlayOptions = {}): Promise<void> {
  return new Promise((resolve) => {
    let closed = false;
    const done = () => {
      if (closed) return;
      closed = true;
      watch.disconnect();
      screen.close();
      resolve();
    };
    const screen = showScreen({
      id: "howtoplay",
      // Over the pause menu: the frozen game under the scrim. Before a level: the menus' dimmed planet.
      backdrop: opts.over ? "none" : "space",
      over: opts.over,
      layout: "center",
      label: "How to play",
      onIntent: (intent) => {
        if (intent === "accept" || intent === "back" || intent === "start") done();
        return true;
      },
      onBack: done,
    });
    const keysCol = h("section", { class: "htp-col", attrs: { "data-col": "keys" } }, h("h3", { class: "ui-label", text: "Keyboard" }), rows(keyboardRows(), ""));
    keysCol.append(h("p", { class: "htp-note", text: "Mouse: click the game to steer; left button fires, right the sidekicks." }));
    const touchCol = h("section", { class: "htp-col", attrs: { "data-col": "touch" } }, h("h3", { class: "ui-label", text: "Touch" }), rows(touchRows(interfaceStyle.get() === "frame"), "ui-key--touch"));
    const pad = h(
      "p",
      { class: "htp-pad", attrs: { "data-col": "pad" } },
      h("span", { class: "htp-pad__name", text: "Gamepad" }),
      ...PAD_ROW.map(([cap, what]) => h("span", { class: "htp-pad__item" }, h("kbd", { class: "ui-key ui-key--pad", text: cap }), h("span", { text: what }))),
    );
    const card = h(
      "div",
      { class: "htp" },
      h("p", { class: "htp-goal" }, h("b", { text: HOW_TO_PLAY_GOAL[0] }), " ", HOW_TO_PLAY_GOAL[1]),
      h("div", { class: "htp-cols" }, keysCol, touchCol),
      pad,
    );
    const touchParam = touchHudParam(location.search);
    const light = () => (card.dataset.lit = howToPlayColumn(document.documentElement.dataset.input, touchParam));
    light();
    const watch = new MutationObserver(light);
    watch.observe(document.documentElement, { attributes: true, attributeFilter: ["data-input"] });
    const got = button({ label: "Got it", variant: "primary", hint: { key: "Enter", pad: "A" }, onPress: done, class: "htp-ok" });
    screen.add(title("How to play"), card, h("div", { class: "htp-foot" }, got));
    // A tap or click anywhere dismisses it (click, not pointerdown, so the tap ends here and doesn't
    // land on the pause menu coming back underneath).
    screen.root.addEventListener("click", done);
  });
}
