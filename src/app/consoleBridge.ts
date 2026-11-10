// The debug console's hold on the running game (D109). The console itself (src/debug/console/) is
// loaded on demand; this small part stays in the main bundle: where the player is (title, shop,
// level), the game flow's hooks for the console's jumps, the sim speed and tick count the level loop
// reads, and the ways in: backtick, Options → Debug console, and `tyrianConsole` in the browser's
// devtools (open, or run one command).

import type { TyrianFiles } from "../sim/resources";
import type { View } from "../render/view";
import type { OptionsHost } from "./options";
import type { Screen } from "../ui/screen";

/** Where the console was opened: what its level commands can do there. */
export type ConsolePlace = "title" | "shop" | "level" | "menu";

/** A level (or item screen) the console asked for: episode, and section (null: the episode's start). */
export interface ConsoleJump {
  episode: number;
  section: number | null;
}

export interface ConsoleBridge {
  place: ConsolePlace;
  files: TyrianFiles | null;
  view: View | null;
  host: OptionsHost | null;
  /** The random seed the session started from (seedAtStartup), or the last `seed N`. */
  seed: number;
  /** Ticks played in this level (the console's `tick`). */
  ticks: number;
  /** Sim speed multiplier: the level loop runs this many fixed ticks per tick's worth of time. */
  speed: number;
  /** The jump the game flow carries out once the console and the menu under it close. */
  jump: ConsoleJump | null;
  /**
   * The menu to close for a jump to happen, and how: the title starts the game, the pause screen
   * resumes, the shop leaves (its JE_itemScreen_done test). Only when the console is right over
   * `screen` (not over a screen opened from it). Null where nothing needs to close.
   */
  leave: { screen: Screen; go(): void } | null;
  /** Redraw the screen under the console after a change to the game (the shop's credits and loadout). */
  refresh: (() => void) | null;
  /** While a level runs unpaused: pause it and open the console over it. */
  openInLevel: (() => void) | null;
  /** While the console is open: close it. */
  closeConsole: (() => void) | null;
}

export const consoleBridge: ConsoleBridge = {
  place: "menu",
  files: null,
  view: null,
  host: null,
  seed: 0,
  ticks: 0,
  speed: 1,
  jump: null,
  leave: null,
  refresh: null,
  openInLevel: null,
  closeConsole: null,
};

/** Take the pending jump, if any. */
export function takeConsoleJump(): ConsoleJump | null {
  const j = consoleBridge.jump;
  consoleBridge.jump = null;
  return j;
}

/** Set `place` while `run` goes on, then put the old one back. */
export async function inPlace<T>(place: ConsolePlace, run: () => Promise<T>): Promise<T> {
  const before = consoleBridge.place;
  consoleBridge.place = place;
  try {
    return await run();
  } finally {
    consoleBridge.place = before;
  }
}

const load = () => import("../debug/console");

/**
 * Open the console where the player is: in a running level, through the level loop (which pauses
 * first); anywhere else straight over the screen that's up. Resolves once it has closed.
 */
export function openDebugConsole(): Promise<void> {
  if (consoleBridge.closeConsole) return Promise.resolve(); // already open
  if (consoleBridge.openInLevel) {
    consoleBridge.openInLevel();
    return Promise.resolve();
  }
  return showDebugConsole();
}

/** Show the console screen now (the level loop calls this once it has paused). */
export async function showDebugConsole(): Promise<void> {
  const { showConsole } = await load();
  await showConsole(consoleBridge);
}

/** Whether a key event is typing into a text field (a save name), where backtick is a character. */
function typing(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement | null;
  return !!t && (t.isContentEditable || t.tagName === "TEXTAREA" || t.tagName === "INPUT");
}

/**
 * Backtick opens the console (and closes it, when its own field doesn't take the key first);
 * `tyrianConsole` is for devtools and scripted checks. A perf overlay left on comes back.
 */
export function installDebugConsole(): void {
  window.addEventListener(
    "keydown",
    (e) => {
      if (e.code !== "Backquote" || e.repeat || e.ctrlKey || e.metaKey || e.altKey || typing(e)) return;
      e.preventDefault();
      e.stopPropagation();
      if (consoleBridge.closeConsole) consoleBridge.closeConsole();
      else void openDebugConsole();
    },
    true,
  );
  Object.assign(window, {
    tyrianConsole: {
      open: () => openDebugConsole(),
      /** Run one command line without the overlay; resolves with its output lines. */
      run: async (line: string) => (await load()).runConsoleLine(consoleBridge, line),
    },
  });
  if (consoleStore().perf) void load().then(({ restorePerfOverlay }) => restorePerfOverlay(consoleBridge)).catch(() => {});
}

/** The console's own keepsakes in this browser: its history and whether the perf overlay is on. */
export const CONSOLE_STORAGE_KEY = "tyrian3d.console";

export interface ConsoleStore {
  history?: string[];
  perf?: boolean;
}

export function consoleStore(): ConsoleStore {
  try {
    const v = JSON.parse(localStorage.getItem(CONSOLE_STORAGE_KEY) ?? "{}");
    return v && typeof v === "object" ? v : {};
  } catch {
    return {};
  }
}

export function saveConsoleStore(patch: ConsoleStore): void {
  try {
    localStorage.setItem(CONSOLE_STORAGE_KEY, JSON.stringify({ ...consoleStore(), ...patch }));
  } catch {
    /* storage unavailable: kept until the page closes */
  }
}
