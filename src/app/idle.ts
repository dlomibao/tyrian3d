// The title screen's idle timer (titleScreen, tyrian2.c L3300-3311): when nothing has been pressed
// or moved for `ms`, it fires once. The C counts from when the menu was last drawn and stops at any
// input (hasInput(INPUT_ANY): keys, mouse buttons and motion, joysticks); here any key, pointer
// press or motion, wheel or gamepad button or stick restarts the count, and so does the page being
// hidden (the game doesn't run in a background tab).

/** How long the title waits before playing a demo (the C's 30000 ms). */
export const TITLE_IDLE_MS = 30_000;

/** Stick travel that counts as input (the C's joystick threshold is about this). */
const STICK_ACTIVE = 0.3;
/** How often the gamepads are polled and the deadline checked. */
const POLL_MS = 250;

const EVENTS = ["keydown", "pointerdown", "pointermove", "wheel", "touchstart"] as const;

export class IdleTimer {
  private last = performance.now();
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly onActivity = () => this.reset();
  private readonly onVisibility = () => this.reset();

  constructor(
    private readonly ms: number,
    private readonly onIdle: () => void,
  ) {
    for (const type of EVENTS) window.addEventListener(type, this.onActivity, { passive: true, capture: true });
    document.addEventListener("visibilitychange", this.onVisibility);
    this.timer = setInterval(() => this.check(), POLL_MS);
  }

  /** Start counting again from now. */
  reset(): void {
    this.last = performance.now();
  }

  /** Stop for good. */
  stop(): void {
    if (this.timer === null) return;
    clearInterval(this.timer);
    this.timer = null;
    for (const type of EVENTS) window.removeEventListener(type, this.onActivity, { capture: true });
    document.removeEventListener("visibilitychange", this.onVisibility);
  }

  private check(): void {
    if (document.hidden || padActive()) return this.reset();
    if (performance.now() - this.last > this.ms) {
      this.reset();
      this.onIdle();
    }
  }
}

/** Whether any gamepad has a button pressed or a stick pushed. */
export function padActive(): boolean {
  for (const pad of navigator.getGamepads?.() ?? []) {
    if (!pad) continue;
    if (pad.buttons.some((b) => b.pressed)) return true;
    if (pad.axes.some((a) => Math.abs(a) > STICK_ACTIVE)) return true;
  }
  return false;
}
