// Keyboard and gamepad input, sampled once per logic tick.

export interface InputState {
  /** Horizontal direction, -1 (left) to 1 (right). */
  x: number;
  /** Vertical direction in Tyrian screen space, -1 (up) to 1 (down). */
  y: number;
  fire: boolean;
}

const KEYS = {
  left: ["ArrowLeft", "KeyA"],
  right: ["ArrowRight", "KeyD"],
  up: ["ArrowUp", "KeyW"],
  down: ["ArrowDown", "KeyS"],
  fire: ["Space", "KeyJ"],
};

const STICK_DEADZONE = 0.25;

export class Input {
  private readonly held = new Set<string>();
  /** Keys pressed since the last sample, so a tap shorter than one tick still registers. */
  private readonly tapped = new Set<string>();

  constructor(target: Window = window) {
    target.addEventListener("keydown", (e) => {
      if (Object.values(KEYS).some((codes) => codes.includes(e.code))) e.preventDefault();
      this.held.add(e.code);
      this.tapped.add(e.code);
    });
    target.addEventListener("keyup", (e) => this.held.delete(e.code));
    target.addEventListener("blur", () => this.held.clear());
  }

  sample(): InputState {
    const down = (codes: string[]) => codes.some((c) => this.held.has(c) || this.tapped.has(c));
    let x = (down(KEYS.right) ? 1 : 0) - (down(KEYS.left) ? 1 : 0);
    let y = (down(KEYS.down) ? 1 : 0) - (down(KEYS.up) ? 1 : 0);
    let fire = down(KEYS.fire);

    for (const pad of navigator.getGamepads?.() ?? []) {
      if (!pad) continue;
      const [sx = 0, sy = 0] = pad.axes;
      if (Math.abs(sx) > STICK_DEADZONE) x = sx;
      if (Math.abs(sy) > STICK_DEADZONE) y = sy;
      // Standard mapping: 12-15 are the d-pad, 0 is the bottom face button.
      const b = (i: number) => pad.buttons[i]?.pressed ?? false;
      if (b(14)) x = -1;
      if (b(15)) x = 1;
      if (b(12)) y = -1;
      if (b(13)) y = 1;
      fire ||= b(0) || b(7);
    }

    this.tapped.clear();
    return { x: clamp(x), y: clamp(y), fire };
  }
}

const clamp = (v: number) => Math.max(-1, Math.min(1, v));
