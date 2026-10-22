// Keyboard, gamepad, mouse and touch → simInput (src/sim/input.ts), sampled once per sim tick.
//
// Mouse and touch use the original's relative mouse steering (mouseXR/mouseYR, which the C scales
// from window pixels to game pixels): click the game to lock the mouse pointer (left button fires,
// right button fires the sidekicks), or drag a finger to steer — the ship fires while touched.
//
// Defaults follow OpenTyrian's (arrows, Space = fire, Enter = change rear-weapon mode, Left Ctrl /
// Left Alt = sidekicks), plus WASD/J/K/L for laptops. Keys pressed and released between two
// ticks still count for one tick, so quick taps aren't lost.

import { joystick_axis_reduce, simInput, type SimInput } from "../sim/input";

type Action = "up" | "down" | "left" | "right" | "fire" | "changeFire" | "leftSidekick" | "rightSidekick";

const KEYS: Record<Action, string[]> = {
  up: ["ArrowUp", "KeyW"],
  down: ["ArrowDown", "KeyS"],
  left: ["ArrowLeft", "KeyA"],
  right: ["ArrowRight", "KeyD"],
  fire: ["Space", "KeyJ"],
  changeFire: ["Enter", "KeyL"],
  leftSidekick: ["ControlLeft", "KeyK"],
  rightSidekick: ["AltLeft", "Semicolon"],
};

const ALL_CODES = new Set(Object.values(KEYS).flat());

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
  private releasing = false;

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
      if (ALL_CODES.has(e.code)) e.preventDefault();
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

  /** Fill simInput for the next tick. */
  sample(): SimInput {
    const down = (a: Action) => KEYS[a].some((c) => this.held.has(c) || this.tapped.has(c));
    simInput.up = down("up");
    simInput.down = down("down");
    simInput.left = down("left");
    simInput.right = down("right");
    simInput.fire = down("fire");
    simInput.changeFire = down("changeFire");
    simInput.leftSidekick = down("leftSidekick");
    simInput.rightSidekick = down("rightSidekick");
    simInput.analogX = 0;
    simInput.analogY = 0;
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
    // A/RT fire, X change fire, LB/RB sidekicks, Start pause.
    for (const pad of navigator.getGamepads?.() ?? []) {
      if (!pad) continue;
      const b = (i: number) => pad.buttons[i]?.pressed ?? false;
      simInput.up ||= b(12);
      simInput.down ||= b(13);
      simInput.left ||= b(14);
      simInput.right ||= b(15);
      simInput.fire ||= b(0) || b(7);
      simInput.changeFire ||= b(2);
      simInput.leftSidekick ||= b(4);
      simInput.rightSidekick ||= b(5);
      if (b(9)) this.pauseRequested = true;
      simInput.analogX += joystick_axis_reduce(pad.axes[0] ?? 0);
      simInput.analogY += joystick_axis_reduce(pad.axes[1] ?? 0);
    }
    return simInput;
  }

  /** Whether any key or pad button is down (the C's "press any key" after game over). */
  anyInput(): boolean {
    if (this.held.size > 0 || this.tapped.size > 0) return true;
    return (navigator.getGamepads?.() ?? []).some((p) => p?.buttons.some((x) => x.pressed));
  }

  clear(): void {
    this.held.clear();
    this.tapped.clear();
    this.pauseRequested = false;
    this.moveX = this.moveY = 0;
    this.touches.clear();
  }

  /** Leave pointer lock (pauses, level ends). */
  release(): void {
    if (!document.pointerLockElement) return;
    this.releasing = true;
    document.exitPointerLock();
  }
}
