// The keyboard bindings: which keys play each of the game's eight controls. The C has one key per
// control (keySettings[8], config.c L45-55, changed in the item screen's KEY CONFIG menu); here
// each control has two, so the arrow keys and WASD both work out of the box. Controls reads these
// live; src/app/prefs.ts keeps them in this browser.
//
// [two-player] Player 2 has a table of their own (keys2; the C gives player 2 the mouse or a
// joystick instead), and each player a gamepad (pads). In a two-player game a key bound for
// player 2 is player 2's, even if player 1's table has it too (DECISIONS.md D28).

/** The controls, in the C's KEY CONFIG order (menuInt[6][1..8]: UP ... RIGHT SIDEKICK). */
export const ACTIONS = ["up", "down", "left", "right", "fire", "changeFire", "leftSidekick", "rightSidekick"] as const;
export type Action = (typeof ACTIONS)[number];

/** Keys per control. */
export const BINDING_SLOTS = 2;

/**
 * OpenTyrian's defaultKeySettings (arrows, Space, Return, Left Ctrl, Left Alt) in the first slot,
 * and keys for laptops in the second (WASD, J fire, L change fire, K and ; sidekicks).
 */
export const DEFAULT_KEYS: Readonly<Record<Action, readonly string[]>> = {
  up: ["ArrowUp", "KeyW"],
  down: ["ArrowDown", "KeyS"],
  left: ["ArrowLeft", "KeyA"],
  right: ["ArrowRight", "KeyD"],
  fire: ["Space", "KeyJ"],
  changeFire: ["Enter", "KeyL"],
  leftSidekick: ["ControlLeft", "KeyK"],
  rightSidekick: ["AltLeft", "Semicolon"],
};

/**
 * [two-player] Player 2's defaults: W/A/S/D to move, F fire, R change fire, Q and E sidekicks (all
 * under the left hand), and the numeric keypad (8/5/4/6, 0 fire, . change fire, 7 and 9 sidekicks).
 */
export const DEFAULT_KEYS_2: Readonly<Record<Action, readonly string[]>> = {
  up: ["KeyW", "Numpad8"],
  down: ["KeyS", "Numpad5"],
  left: ["KeyA", "Numpad4"],
  right: ["KeyD", "Numpad6"],
  fire: ["KeyF", "Numpad0"],
  changeFire: ["KeyR", "NumpadDecimal"],
  leftSidekick: ["KeyQ", "Numpad7"],
  rightSidekick: ["KeyE", "Numpad9"],
};

/** KeyboardEvent.code values, BINDING_SLOTS per control; "" is an unused slot. */
export const keys: Record<Action, string[]> = copyKeys(DEFAULT_KEYS);

/** [two-player] Player 2's keys, as `keys`. */
export const keys2: Record<Action, string[]> = copyKeys(DEFAULT_KEYS_2);

/** A player's key table (0 = player 1, also the one-player table; 1 = player 2). */
export type PlayerIndex = 0 | 1;
export const playerKeys = (player: PlayerIndex = 0): Record<Action, string[]> => (player === 0 ? keys : keys2);
const defaultKeys = (player: PlayerIndex) => (player === 0 ? DEFAULT_KEYS : DEFAULT_KEYS_2);

/**
 * [two-player] Which gamepad each player uses in a two-player game: the n-th connected pad
 * (0-based), or -1 for none. In a one-player game every pad drives player 1.
 */
export const pads: [number, number] = [0, 1];

/** How many pads the item screen's input rows cycle through (none, then pads 1..MAX_PADS). */
export const MAX_PADS = 4;

/**
 * [two-player] The 2 Player Arcade menu's input row for `player`: the next pad (none, 1, 2, ...),
 * and if the other player had it, they take this player's old one (the C swaps devices the same
 * way, game_menu.c L2809-2823).
 */
export function cyclePad(player: PlayerIndex): void {
  const other = player === 0 ? 1 : 0;
  const old = pads[player];
  const next = old + 1 >= MAX_PADS ? -1 : old + 1;
  if (next >= 0 && pads[other] === next) pads[other] = old;
  pads[player] = next;
}

/** [two-player] Stored pad choices, if well formed (two distinct pads, or none). */
export function setPads(stored: unknown): boolean {
  if (!Array.isArray(stored) || stored.length !== 2) return false;
  const ok = (v: unknown) => Number.isInteger(v) && (v as number) >= -1 && (v as number) < MAX_PADS;
  if (!ok(stored[0]) || !ok(stored[1]) || (stored[0] === stored[1] && stored[0] !== -1)) return false;
  pads[0] = stored[0];
  pads[1] = stored[1];
  return true;
}

/**
 * Keys that can't be bound: Escape and P pause (the C keeps Escape for the menu and P for pause,
 * game_menu.c L2734-2736), and F11, which the C keeps for gamma and browsers for full screen.
 */
export const RESERVED_KEYS: ReadonlySet<string> = new Set(["Escape", "KeyP", "F11"]);

function copyKeys(from: Readonly<Record<Action, readonly string[]>>): Record<Action, string[]> {
  const out = {} as Record<Action, string[]>;
  for (const a of ACTIONS) out[a] = Array.from({ length: BINDING_SLOTS }, (_, i) => from[a][i] ?? "");
  return out;
}

/** Whether some control of either player uses `code` (so the page shouldn't scroll or type with it). */
export function isBound(code: string): boolean {
  return code !== "" && ACTIONS.some((a) => keys[a].includes(code) || keys2[a].includes(code));
}

/**
 * Bind `code` to slot `slot` of `action`, as the KEY CONFIG menu does (game_menu.c L2722-2741): if
 * another slot already has the key, that slot takes this slot's old key ("already used? then
 * swap"). Reserved keys are refused (returns false).
 */
export function bindKey(action: Action, slot: number, code: string, player: PlayerIndex = 0): boolean {
  if (RESERVED_KEYS.has(code) || code === "" || slot < 0 || slot >= BINDING_SLOTS) return false;
  const keys = playerKeys(player);
  for (const a of ACTIONS) {
    const i = keys[a].indexOf(code);
    if (i >= 0) {
      keys[a][i] = keys[action][slot];
      break;
    }
  }
  keys[action][slot] = code;
  return true;
}

/** Leave slot `slot` of `action` unused. */
export function clearKey(action: Action, slot: number, player: PlayerIndex = 0): void {
  if (slot >= 0 && slot < BINDING_SLOTS) playerKeys(player)[action][slot] = "";
}

/** KEY CONFIG's "Reset to Defaults" (memcpy(keySettings, defaultKeySettings, ...)), for one player's table. */
export function resetKeys(player: PlayerIndex = 0): void {
  Object.assign(playerKeys(player), copyKeys(defaultKeys(player)));
}

/**
 * Replace the bindings with stored ones. Anything malformed (an unknown shape, a reserved key, a key
 * bound twice) is ignored and the defaults stay, so a bad entry can't leave the game unplayable.
 */
export function setKeys(stored: unknown, player: PlayerIndex = 0): boolean {
  if (!stored || typeof stored !== "object") return false;
  const s = stored as Record<string, unknown>;
  const next = {} as Record<Action, string[]>;
  const seen = new Set<string>();
  for (const a of ACTIONS) {
    const v = s[a];
    if (!Array.isArray(v) || v.length > BINDING_SLOTS || !v.every((c) => typeof c === "string")) return false;
    const slots = Array.from({ length: BINDING_SLOTS }, (_, i) => (v[i] as string | undefined) ?? "");
    for (const c of slots) {
      if (c === "") continue;
      if (RESERVED_KEYS.has(c) || seen.has(c)) return false;
      seen.add(c);
    }
    next[a] = slots;
  }
  Object.assign(playerKeys(player), next);
  return true;
}

/** A key's name for the screen (the C shows SDL_GetScancodeName). */
export function keyName(code: string): string {
  if (code === "") return "—";
  const special: Record<string, string> = {
    ArrowUp: "Up",
    ArrowDown: "Down",
    ArrowLeft: "Left",
    ArrowRight: "Right",
    ControlLeft: "Left Ctrl",
    ControlRight: "Right Ctrl",
    AltLeft: "Left Alt",
    AltRight: "Right Alt",
    ShiftLeft: "Left Shift",
    ShiftRight: "Right Shift",
    MetaLeft: "Left Meta",
    MetaRight: "Right Meta",
    Enter: "Return",
    NumpadEnter: "Keypad Enter",
    Semicolon: ";",
    Quote: "'",
    Comma: ",",
    Period: ".",
    Slash: "/",
    Backslash: "\\",
    BracketLeft: "[",
    BracketRight: "]",
    Minus: "-",
    Equal: "=",
    Backquote: "`",
    NumpadDecimal: "Keypad .",
  };
  if (special[code]) return special[code];
  if (/^Key[A-Z]$/.test(code)) return code.slice(3);
  if (/^Digit\d$/.test(code)) return code.slice(5);
  if (code.startsWith("Numpad")) return `Keypad ${code.slice(6)}`;
  return code;
}
