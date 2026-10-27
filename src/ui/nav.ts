// One navigation model for every screen: keyboard, gamepad and pointer all become the same few
// intents, which the screen manager hands to the screen on top (src/ui/screen.ts).
//
// Keyboard: arrows / WASD move, Enter / Space accept, Escape / Backspace back, '/' alt.
// Gamepad (standard mapping): d-pad / left stick move, A accept, B back, X alt, Start start.
// Pointer: components handle taps and clicks themselves; there are no swipes or drags to learn.
//
// Directions repeat while held (the item screen's 380 ms delay, then every 110 ms). Buttons still
// held when a screen appears are ignored until they're let go, so the fire button held through a
// death or the A press that opened a screen don't act on the next one.

export type Intent = "up" | "down" | "left" | "right" | "accept" | "back" | "start" | "alt";

export type InputDevice = "keys" | "pad" | "mouse" | "touch";

export const DIRECTIONS: ReadonlySet<Intent> = new Set(["up", "down", "left", "right"]);

/** KeyboardEvent.code → intent. */
export const KEY_INTENTS: Readonly<Record<string, Intent>> = {
  ArrowUp: "up",
  KeyW: "up",
  ArrowDown: "down",
  KeyS: "down",
  ArrowLeft: "left",
  KeyA: "left",
  ArrowRight: "right",
  KeyD: "right",
  Enter: "accept",
  NumpadEnter: "accept",
  Space: "accept",
  Escape: "back",
  Backspace: "back",
  Slash: "alt",
  NumpadDivide: "alt",
};

/** The intent for a key, or undefined. `key` catches '/' on layouts where it isn't the Slash key. */
export function keyIntent(code: string, key = ""): Intent | undefined {
  return KEY_INTENTS[code] ?? (key === "/" ? "alt" : undefined);
}

/** Standard-mapping gamepad buttons → intents. */
export const PAD_BUTTONS: readonly (readonly [number, Intent])[] = [
  [0, "accept"],
  [1, "back"],
  [2, "alt"],
  [9, "start"],
  [12, "up"],
  [13, "down"],
  [14, "left"],
  [15, "right"],
];

/** How far the left stick must lean to count as a direction. */
export const STICK_THRESHOLD = 0.5;
export const REPEAT_DELAY_MS = 380;
export const REPEAT_RATE_MS = 110;

export interface PadState {
  buttons: readonly boolean[];
  axes: readonly number[];
}

/**
 * Turns gamepad snapshots into intents: edge-triggered buttons, held directions repeating, and
 * nothing at all until every mapped input has been released once after rearm(). Pure, so it's
 * tested without a browser.
 */
export class PadReader {
  private armed = false;
  /** Intent → time it next fires while held. */
  private readonly held = new Map<Intent, number>();

  /** Ignore whatever is held now until it's released (call when a screen appears). */
  rearm(): void {
    this.armed = false;
    this.held.clear();
  }

  /** The intents active in these pads (several pads merge). */
  static active(pads: readonly PadState[]): Set<Intent> {
    const on = new Set<Intent>();
    for (const pad of pads) {
      for (const [i, intent] of PAD_BUTTONS) if (pad.buttons[i]) on.add(intent);
      const [x = 0, y = 0] = pad.axes;
      if (x <= -STICK_THRESHOLD) on.add("left");
      if (x >= STICK_THRESHOLD) on.add("right");
      if (y <= -STICK_THRESHOLD) on.add("up");
      if (y >= STICK_THRESHOLD) on.add("down");
    }
    return on;
  }

  /** The intents to act on at time `now` (ms). */
  update(pads: readonly PadState[], now: number): Intent[] {
    const on = PadReader.active(pads);
    if (!this.armed) {
      if (on.size === 0) this.armed = true;
      return [];
    }
    for (const intent of [...this.held.keys()]) if (!on.has(intent)) this.held.delete(intent);
    const out: Intent[] = [];
    for (const intent of on) {
      const next = this.held.get(intent);
      if (next === undefined) {
        this.held.set(intent, now + REPEAT_DELAY_MS);
        out.push(intent);
      } else if (DIRECTIONS.has(intent) && now >= next) {
        this.held.set(intent, now + REPEAT_RATE_MS);
        out.push(intent);
      }
    }
    return out;
  }
}

/** Whether a key event belongs to a text field (typing a name), not to navigation. */
function typing(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement | null;
  if (!t || !(t instanceof HTMLElement)) return false;
  const field = t.isContentEditable || t.tagName === "TEXTAREA" || (t.tagName === "INPUT" && !["button", "checkbox", "radio", "range", "file"].includes((t as HTMLInputElement).type));
  return field && e.code !== "Enter" && e.code !== "NumpadEnter" && e.code !== "Escape";
}

export interface NavTarget {
  /** A raw key first (screen-specific keys such as M for music); true if it was used. */
  key(e: KeyboardEvent): boolean;
  intent(intent: Intent, device: InputDevice): void;
  /** A pad button that isn't an intent (PAD_BUTTONS), newly pressed. */
  button?(index: number): void;
}

/** Pad buttons that are intents. */
const INTENT_BUTTONS: ReadonlySet<number> = new Set(PAD_BUTTONS.map(([i]) => i));

/**
 * The browser side: listens for keys, polls gamepads while a target is set, and records the last
 * device used on <html data-input="…"> so key hints can show the right glyphs.
 */
export class Nav {
  private target: NavTarget | null = null;
  private readonly pad = new PadReader();
  /** The other buttons' state last frame (null: just set a target, so whatever is held now is ignored). */
  private buttons: boolean[] | null = null;
  private raf = 0;

  constructor() {
    setDevice(window.matchMedia?.("(pointer: coarse)").matches ? "touch" : "keys");
    // Capture phase, so a screen's keys never reach the game's Controls (Escape on the pause screen
    // must not pause again).
    window.addEventListener(
      "keydown",
      (e) => {
        setDevice("keys");
        const t = this.target;
        if (!t || typing(e)) return;
        if (t.key(e)) {
          e.preventDefault();
          e.stopPropagation();
          return;
        }
        const intent = keyIntent(e.code, e.key);
        if (!intent) return;
        e.preventDefault();
        e.stopPropagation();
        t.intent(intent, "keys");
      },
      true,
    );
    window.addEventListener("pointerdown", (e) => setDevice(e.pointerType === "mouse" ? "mouse" : "touch"), true);
  }

  /** Route input to `target` (null: nothing, e.g. during a level). Held pad buttons are ignored. */
  setTarget(target: NavTarget | null): void {
    this.target = target;
    this.pad.rearm();
    this.buttons = null;
    cancelAnimationFrame(this.raf);
    if (target) this.raf = requestAnimationFrame(this.poll);
  }

  private readonly poll = (now: number) => {
    const t = this.target;
    if (!t) return;
    const pads: PadState[] = [];
    for (const p of navigator.getGamepads?.() ?? []) {
      if (p) pads.push({ buttons: p.buttons.map((b) => b.pressed), axes: p.axes });
    }
    const intents = this.pad.update(pads, now);
    if (intents.length) setDevice("pad");
    for (const intent of intents) {
      if (this.target !== t) break; // the screen changed under us
      t.intent(intent, "pad");
    }
    // The buttons that aren't intents, edge-triggered, for a screen's own shortcuts.
    const buttons: boolean[] = [];
    for (const p of pads) p.buttons.forEach((b, i) => (buttons[i] ||= b));
    const before = this.buttons;
    this.buttons = buttons;
    if (before && t.button) {
      for (let i = 0; i < buttons.length; i++) {
        if (!buttons[i] || before[i] || INTENT_BUTTONS.has(i)) continue;
        if (this.target !== t) break;
        setDevice("pad");
        t.button(i);
      }
    }
    if (this.target) this.raf = requestAnimationFrame(this.poll);
  };
}

let device: InputDevice = "keys";

/** The last input device used. */
export function lastDevice(): InputDevice {
  return device;
}

function setDevice(d: InputDevice): void {
  if (d === device && document.documentElement.dataset.input === d) return;
  device = d;
  document.documentElement.dataset.input = d;
}
