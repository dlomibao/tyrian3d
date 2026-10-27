// keysactive for Destruct: the keys held on the keyboard (by KeyboardEvent.code), plus gamepads
// standing in for those keys. The game reads and clears them itself (DE_RunTickGetInput), so this
// only records what is held, as OpenTyrian's keyboard.c does (key repeats ignored).

import { KEY_CHANGE, KEY_CYDN, KEY_CYUP, KEY_DOWN, KEY_FIRE, KEY_LEFT, KEY_RIGHT, KEY_UP, PLAYER_LEFT, PLAYER_RIGHT, type KeysActive } from "./sim";

/** Keys the game uses besides the players' own (DE_RunTick): AI toggles, pause, help, quit, new map. */
export const CONTROL_KEYS = ["F10", "F11", "KeyP", "F1", "Escape", "Backspace"];

/**
 * Gamepad buttons (standard mapping) to Destruct's keys: the d-pad or left stick aims and sets
 * the power, A fires, X changes vehicle, LB and RB change weapon, Start pauses, Back leaves.
 * Pad 1 plays the right-hand side (the human one by default), pad 2 the left.
 */
const PAD_BUTTONS: [button: number, key: number][] = [
  [14, KEY_LEFT],
  [15, KEY_RIGHT],
  [12, KEY_UP],
  [13, KEY_DOWN],
  [0, KEY_FIRE],
  [2, KEY_CHANGE],
  [4, KEY_CYUP],
  [5, KEY_CYDN],
];
const PAD_PLAYERS = [PLAYER_RIGHT, PLAYER_LEFT];
const STICK = 0.5;

export class DestructKeys implements KeysActive {
  private readonly held = new Set<string>();
  /**
   * Keys pressed since the last tick: a tap let go before the game looked still counts for one
   * tick (SDL polls its events only in DE_RunTickGetInput, so the C misses taps shorter than a
   * tick; browser frames are coarser than its 14 ms ticks, which would miss more).
   */
  private readonly tapped = new Set<string>();
  /** Codes a pad is holding this tick. */
  private readonly pad = new Set<string>();
  /** Pad codes the game has released: ignored until the button comes up. */
  private readonly padReleased = new Set<string>();
  private listening = false;

  constructor(private readonly gameKeys: () => string[][][]) {}

  isDown(code: string): boolean {
    return this.held.has(code) || this.tapped.has(code) || (this.pad.has(code) && !this.padReleased.has(code));
  }

  release(code: string): void {
    this.held.delete(code);
    this.tapped.delete(code);
    if (this.pad.has(code)) this.padReleased.add(code);
  }

  /** Start taking the keyboard (while a round is played; menus have it otherwise). */
  listen(): void {
    if (this.listening) return;
    this.listening = true;
    this.clear();
    // Buttons already held (the A that chose the mode) wait to be let go.
    this.pollPads();
    for (const c of this.pad) this.padReleased.add(c);
    window.addEventListener("keydown", this.onKeyDown, true);
    window.addEventListener("keyup", this.onKeyUp, true);
    window.addEventListener("blur", this.clear);
  }

  stop(): void {
    if (!this.listening) return;
    this.listening = false;
    window.removeEventListener("keydown", this.onKeyDown, true);
    window.removeEventListener("keyup", this.onKeyUp, true);
    window.removeEventListener("blur", this.clear);
    this.clear();
  }

  readonly clear = (): void => {
    this.held.clear();
    this.tapped.clear();
  };

  /** After each tick: taps have been seen. */
  endTick(): void {
    this.tapped.clear();
  }

  /** Read the gamepads into keysactive (once a tick, before DE_RunTick). */
  pollPads(): void {
    this.pad.clear();
    const pads = typeof navigator !== "undefined" && navigator.getGamepads ? navigator.getGamepads() : [];
    const keys = this.gameKeys();
    let n = 0;
    for (const pad of pads) {
      if (!pad || n >= PAD_PLAYERS.length) continue;
      const config = keys[PAD_PLAYERS[n++]];
      const down = (b: number) => !!pad.buttons[b]?.pressed;
      const [ax = 0, ay = 0] = pad.axes;
      for (const [button, key] of PAD_BUTTONS) {
        const stick = key === KEY_LEFT ? ax < -STICK : key === KEY_RIGHT ? ax > STICK : key === KEY_UP ? ay < -STICK : key === KEY_DOWN ? ay > STICK : false;
        if ((down(button) || stick) && config[key][0]) this.pad.add(config[key][0]);
      }
      if (down(9)) this.pad.add("KeyP");
      if (down(8)) this.pad.add("Escape");
    }
    for (const c of [...this.padReleased]) if (!this.pad.has(c)) this.padReleased.delete(c);
  }

  private isGameKey(code: string): boolean {
    return CONTROL_KEYS.includes(code) || this.gameKeys().some((player) => player.some((slots) => slots.includes(code)));
  }

  private readonly onKeyDown = (e: KeyboardEvent): void => {
    if (!this.isGameKey(e.code)) return;
    // Space scrolls, Alt opens menus, Backspace navigates, F1 opens help: the game has them.
    e.preventDefault();
    e.stopPropagation();
    if (e.repeat) return;
    this.held.add(e.code);
    this.tapped.add(e.code);
  };

  private readonly onKeyUp = (e: KeyboardEvent): void => {
    if (!this.isGameKey(e.code)) return;
    e.preventDefault();
    e.stopPropagation();
    this.held.delete(e.code);
  };
}
