// Keyboard and gamepad → simInput (src/sim/input.ts), sampled once per sim tick.
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

  constructor() {
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
  }
}
