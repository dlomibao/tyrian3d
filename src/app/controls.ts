// Keyboard, gamepad, mouse and touch → simInput (src/sim/input.ts), sampled once per sim tick.
//
// Mouse and touch use the original's relative mouse steering (mouseXR/mouseYR, which the C scales
// from window pixels to game pixels): click the game to lock the mouse pointer (left button fires,
// right button fires the sidekicks), or drag a finger to steer — the ship fires while touched.
//
// The keys are the player's bindings (src/app/bindings.ts, set on the settings screen); the
// defaults follow OpenTyrian's (arrows, Space = fire, Enter = change rear-weapon mode, Left Ctrl /
// Left Alt = sidekicks), plus WASD/J/K/L for laptops. Keys pressed and released between two
// ticks still count for one tick, so quick taps aren't lost.
//
// [two-player] In a two-player game player 2 gets their own keys (keys2, which win over player
// 1's), the gamepad `pads[1]` picks, and nothing from the mouse; player 1 gets the rest of their
// keys, `pads[0]`'s pad, the mouse and touch (DECISIONS.md D28).

import { joystick_analog_angle, joystick_axis_reduce, simInput, simInputs, type SimInput } from "../sim/input";
import { g } from "../sim/state";
import { ACTIONS, isBound, keys as KEYS, keys2 as KEYS2, pads as PADS, type Action } from "./bindings";

export class Controls {
  private readonly held = new Set<string>();
  private readonly tapped = new Set<string>();
  /** Set when the player asks to pause (Escape / P / Start), cleared by the reader. */
  pauseRequested = false;
  /** True while a level is being played: pointer lock and touch steering only apply then. */
  active = false;

  /** Pointer motion since the last sample, in CSS pixels. */
  private moveX = 0;
  private moveY = 0;
  private mouseButtons = 0;
  private touches = new Map<number, { x: number; y: number }>();
  /** Whether the last sample() saw any key held or tapped. */
  private sampledInput = false;
  private releasing = false;
  /** ui-framework: whether a pad's Start was down at the last sample, so holding it pauses once. */
  private startHeld = false;

  /** @param gamePixelsPerScreenPixel converts pointer motion to game pixels (from the view). */
  constructor(private readonly gamePixelsPerScreenPixel: () => number = () => 1) {
    const canvasTarget = () => document.querySelector("canvas");
    window.addEventListener("pointerdown", (e) => {
      if (!this.active || e.target !== canvasTarget()) return;
      if (e.pointerType === "mouse") {
        if (document.pointerLockElement !== canvasTarget()) void canvasTarget()?.requestPointerLock?.();
        this.mouseButtons = e.buttons;
      } else {
        this.touches.set(e.pointerId, { x: e.clientX, y: e.clientY });
      }
      e.preventDefault();
    });
    window.addEventListener("pointermove", (e) => {
      if (!this.active) return;
      if (e.pointerType === "mouse") {
        if (document.pointerLockElement) {
          this.moveX += e.movementX;
          this.moveY += e.movementY;
        }
        this.mouseButtons = e.buttons;
        return;
      }
      const t = this.touches.get(e.pointerId);
      if (!t) return;
      // Steer with the first finger only.
      if (e.pointerId === this.touches.keys().next().value) {
        this.moveX += e.clientX - t.x;
        this.moveY += e.clientY - t.y;
      }
      t.x = e.clientX;
      t.y = e.clientY;
    });
    const lift = (e: PointerEvent) => {
      if (e.pointerType === "mouse") this.mouseButtons = e.buttons;
      else this.touches.delete(e.pointerId);
    };
    window.addEventListener("pointerup", lift);
    window.addEventListener("pointercancel", lift);
    window.addEventListener("contextmenu", (e) => {
      if (this.active) e.preventDefault();
    });
    document.addEventListener("pointerlockchange", () => {
      if (document.pointerLockElement) return;
      this.mouseButtons = 0;
      // The browser takes Esc to leave pointer lock without telling the page: treat it as pause.
      if (this.active && !this.releasing) this.pauseRequested = true;
      this.releasing = false;
    });

    window.addEventListener("keydown", (e) => {
      if (isBound(e.code)) e.preventDefault();
      if (e.code === "Escape" || e.code === "KeyP") this.pauseRequested = true;
      this.held.add(e.code);
      this.tapped.add(e.code);
    });
    window.addEventListener("keyup", (e) => this.held.delete(e.code));
    window.addEventListener("blur", () => {
      this.held.clear();
      this.pauseRequested = true;
    });
  }

  /** Fill simInput (and in a two-player game player 2's, simInputs[1]) for the next tick. */
  sample(): SimInput {
    const two = g.twoPlayerMode;
    // [two-player] player 2's keys are theirs, even if player 1's table has them too
    const taken = two ? new Set(ACTIONS.flatMap((a) => KEYS2[a])) : null;
    const pressed = (c: string) => c !== "" && (this.held.has(c) || this.tapped.has(c));
    const fill = (input: SimInput, table: Record<Action, string[]>, skip: Set<string> | null) => {
      const down = (a: Action) => table[a].some((c) => pressed(c) && !skip?.has(c));
      input.up = down("up");
      input.down = down("down");
      input.left = down("left");
      input.right = down("right");
      input.fire = down("fire");
      input.changeFire = down("changeFire");
      input.leftSidekick = down("leftSidekick");
      input.rightSidekick = down("rightSidekick");
      input.analogX = 0;
      input.analogY = 0;
      input.analogAngle = null;
      input.mouseXR = input.mouseYR = 0;
      input.mouseLeft = input.mouseRight = input.mouseMiddle = false;
    };
    fill(simInput, KEYS, taken);
    if (two) fill(simInputs[1], KEYS2, null);
    // Remember whether this sample saw any key, so anyInput() still sees a tap after it's cleared.
    this.sampledInput = this.held.size > 0 || this.tapped.size > 0;
    this.tapped.clear();

    // Mouse / touch: relative steering in game pixels (the C's mouseGetRelativePosition).
    const scale = this.gamePixelsPerScreenPixel();
    simInput.mouseXR = Math.trunc(this.moveX * scale);
    simInput.mouseYR = Math.trunc(this.moveY * scale);
    // Keep the sub-pixel remainder so slow drags still move the ship.
    this.moveX -= simInput.mouseXR / scale;
    this.moveY -= simInput.mouseYR / scale;
    const locked = document.pointerLockElement !== null;
    const touching = this.touches.size > 0;
    simInput.mouseLeft = touching || (locked && (this.mouseButtons & 1) !== 0);
    simInput.mouseRight = locked && (this.mouseButtons & 2) !== 0;
    simInput.mouseMiddle = locked && (this.mouseButtons & 6) !== 0;

    // Standard-mapping gamepads: d-pad as keys, left stick as the C's analog joystick,
    // A/RT fire, X change fire, LB/RB sidekicks, Start pause. [two-player] Each player's own pad
    // in a two-player game; every pad is player 1's otherwise. Start on any pad pauses.
    let start = false;
    const connected = (navigator.getGamepads?.() ?? []).filter((p): p is Gamepad => !!p);
    connected.forEach((pad, n) => {
      const b = (i: number) => pad.buttons[i]?.pressed ?? false;
      start ||= b(9);
      const input = !two ? simInput : PADS[0] === n ? simInputs[0] : PADS[1] === n ? simInputs[1] : null;
      if (!input) return;
      input.up ||= b(12);
      input.down ||= b(13);
      input.left ||= b(14);
      input.right ||= b(15);
      input.fire ||= b(0) || b(7);
      input.changeFire ||= b(2);
      input.leftSidekick ||= b(4);
      input.rightSidekick ||= b(5);
      input.analogX += joystick_axis_reduce(pad.axes[0] ?? 0);
      input.analogY += joystick_axis_reduce(pad.axes[1] ?? 0);
      input.analogAngle ??= joystick_analog_angle(pad.axes[0] ?? 0, pad.axes[1] ?? 0);
    });
    // ui-framework: pause on the press only. Start also resumes on the pause screen, and a Start
    // still held after resuming must not pause again.
    if (start && !this.startHeld) this.pauseRequested = true;
    this.startHeld = start;
    return simInput;
  }

  /** Whether any key or pad button is down (the C's "press any key" after game over). */
  anyInput(): boolean {
    if (this.sampledInput || this.held.size > 0 || this.tapped.size > 0 || this.touches.size > 0) return true;
    return (navigator.getGamepads?.() ?? []).some((p) => p?.buttons.some((x) => x.pressed));
  }

  clear(): void {
    // ui-framework: a Start held through clear() (resuming with it) counts as already seen.
    this.startHeld = (navigator.getGamepads?.() ?? []).some((p) => p?.buttons[9]?.pressed);
    this.held.clear();
    this.tapped.clear();
    this.pauseRequested = false;
    this.moveX = this.moveY = 0;
    this.touches.clear();
    this.sampledInput = false;
  }

  /** Leave pointer lock (pauses, level ends). */
  release(): void {
    if (!document.pointerLockElement) return;
    this.releasing = true;
    document.exitPointerLock();
  }
}
