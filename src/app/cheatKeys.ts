// The in-flight cheat keys (src/sim/cheats.ts JE_mainKeyboardInput): the keys held, and whether one
// went down since the last tick. The C runs JE_mainKeyboardInput at the end of a frame in which a
// key went down (keyboardHasInput), so poll() runs it before the next tick. Only while a level is
// being played (`active`); Escape and P stay the pause keys (src/app/controls.ts).

import { JE_mainKeyboardInput } from "../sim/cheats";

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
    if (this.active()) JE_mainKeyboardInput(this.held);
  }
}
