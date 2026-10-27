// The keyboard bindings: which keys play each of the game's eight controls. The C has one key per
// control (keySettings[8], config.c L45-55, changed in the item screen's KEY CONFIG menu); here
// each control has two, so the arrow keys and WASD both work out of the box. Controls reads these
// live; src/app/prefs.ts keeps them in this browser.

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

/** KeyboardEvent.code values, BINDING_SLOTS per control; "" is an unused slot. */
export const keys: Record<Action, string[]> = copyKeys(DEFAULT_KEYS);

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

/** Whether some control uses `code` (so the page shouldn't scroll or type with it). */
export function isBound(code: string): boolean {
  return code !== "" && ACTIONS.some((a) => keys[a].includes(code));
}

/**
 * Bind `code` to slot `slot` of `action`, as the KEY CONFIG menu does (game_menu.c L2722-2741): if
 * another slot already has the key, that slot takes this slot's old key ("already used? then
 * swap"). Reserved keys are refused (returns false).
 */
export function bindKey(action: Action, slot: number, code: string): boolean {
  if (RESERVED_KEYS.has(code) || code === "" || slot < 0 || slot >= BINDING_SLOTS) return false;
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
export function clearKey(action: Action, slot: number): void {
  if (slot >= 0 && slot < BINDING_SLOTS) keys[action][slot] = "";
}

/** KEY CONFIG's "Reset to Defaults" (memcpy(keySettings, defaultKeySettings, ...)). */
export function resetKeys(): void {
  Object.assign(keys, copyKeys(DEFAULT_KEYS));
}

/**
 * Replace the bindings with stored ones. Anything malformed (an unknown shape, a reserved key, a key
 * bound twice) is ignored and the defaults stay, so a bad entry can't leave the game unplayable.
 */
export function setKeys(stored: unknown): boolean {
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
  Object.assign(keys, next);
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
  };
  if (special[code]) return special[code];
  if (/^Key[A-Z]$/.test(code)) return code.slice(3);
  if (/^Digit\d$/.test(code)) return code.slice(5);
  if (code.startsWith("Numpad")) return `Keypad ${code.slice(6)}`;
  return code;
}
