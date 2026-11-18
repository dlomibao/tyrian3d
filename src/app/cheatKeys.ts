// The in-flight cheat keys (src/sim/cheats.ts JE_mainKeyboardInput): the keys held, and whether one
// went down since the last tick. The C runs JE_mainKeyboardInput at the end of a frame in which a
// key went down (keyboardHasInput), so poll() runs it before the next tick. Only while a level is
// being played (`active`); Escape and P stay the pause keys (src/app/controls.ts).

import { JE_mainKeyboardInput, type KeysActive } from "../sim/cheats";
import { taintRun } from "../sim/runRecord";

/**
 * Whether the keys held make one of JE_mainKeyboardInput's cheat chords (the Nort ship,
 * invulnerability, self-destruct, skip level), whatever the game then does with it: any of them
 * taints the run for the shared high-score list.
 */
export function isCheatChord(keys: Pick<KeysActive, "has">): boolean {
  const k = (c: string) => keys.has(c);
  return (
    (k("F2") && k("F4") && k("F6") && k("F7") && k("F9") && k("Backslash") && k("Slash")) ||
    (k("F2") && k("F3") && (k("F6") || k("F4") || k("F5"))) ||
    (k("F2") && k("F6") && (k("F7") || k("F8")) && !k("F9"))
  );
}

/** F-keys the chords use: the browser's own meaning (help, reload, caret browsing...) is held off in flight. */
const CHORD_KEYS = new Set(["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10"]);

export class CheatKeys {
  /** keysactive[], by KeyboardEvent.code. */
  readonly held = new Set<string>();
  private pressed = false;

  /** @param active whether a level is being played now (the C only reads these keys in JE_main). */
  constructor(private readonly active: () => boolean) {
    window.addEventListener("keydown", (e) => {
      if (!this.active()) return;
      if (CHORD_KEYS.has(e.code)) e.preventDefault();
      // keyboard.c: a key-repeat event is still input (keyboardInputs) but doesn't set keysactive.
      if (!e.repeat) this.held.add(e.code);
      this.pressed = true;
    });
    // Always, so a key let go during a pause or a menu isn't held for ever.
    window.addEventListener("keyup", (e) => this.held.delete(e.code));
    window.addEventListener("blur", () => this.held.clear());
  }

  /** Before each tick: JE_mainKeyboardInput, if a key went down since the last one. */
  poll(): void {
    if (!this.pressed) return;
    this.pressed = false;
    if (!this.active()) return;
    if (isCheatChord(this.held)) taintRun("cheat-keys");
    JE_mainKeyboardInput(this.held);
  }
}
