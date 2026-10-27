// The screen manager: one screen at a time, shown and hidden with a transition, with the 3D
// backdrop behind it and every input routed to it (src/ui/README.md).
//
// A screen is a full-window layer holding a panel. Showing one closes the one before (they cross-
// fade). Input goes, in order, to an open modal; else the screen's onKey (raw keys) and onIntent;
// else its controls in order (the first Navigable that uses the intent wins); else "back" calls
// onBack. With no screen up (a level is being played) nothing is routed and the backdrop sleeps.

import "./tokens.css";
import "./components.css";
import { button, h, MenuList, type Navigable } from "./components";
import { Nav, type InputDevice, type Intent, type NavTarget } from "./nav";

/** What the 3D backdrop shows behind a screen (src/ui/backdrop.ts); "none" leaves the game visible. */
export type BackdropMood = "title" | "hangar" | "space" | "none";

/** The part of the backdrop the manager drives. */
export interface BackdropControl {
  setMood(mood: BackdropMood): void;
  /** Show the player ship drawn by this sprite (items.ships[id].shipGraphic). */
  setShipGraphic?(shipGraphic: number): void;
}

export interface ScreenOptions {
  /** Names the screen: the root gets class ui-screen--<id>, for its own styles. */
  id: string;
  /** What the backdrop shows (default "space"). */
  backdrop?: BackdropMood;
  /** Panel width: "narrow" (messages), "center" (default, menus) or "wide" (the item screen). */
  layout?: "narrow" | "center" | "wide";
  /** Darken what's behind (default: only when the backdrop is "none", i.e. over the game). */
  scrim?: boolean;
  /** aria-label for the dialog. */
  label?: string;
  /** No input at all (a loading line). */
  passive?: boolean;
  /** Raw keys before intents, for screen-specific keys; return true if used. */
  onKey?: (e: KeyboardEvent) => boolean;
  /** First refusal on every intent; return true if used. */
  onIntent?: (intent: Intent, device: InputDevice) => boolean | void;
  /** Escape / B / the back button, when nothing else used "back". */
  onBack?: () => void;
}

export interface ModalAction<T> {
  label: string;
  value: T;
}

export interface ModalOptions<T> {
  title?: string;
  /** Text paragraphs or an element. */
  body?: string | string[] | HTMLElement;
  actions: ModalAction<T>[];
  /** Index of the focused action (default 0). */
  focused?: number;
  /** Value for back/Escape (default: no way out but the actions). */
  cancel?: T;
}

export class Screen implements NavTarget {
  /** The full-window layer. */
  readonly root: HTMLDivElement;
  /** The framed panel the screen's content goes in. */
  readonly panel: HTMLDivElement;
  /** Navigables that get the intents the screen doesn't use, in order. */
  controls: Navigable[] = [];
  /** Resolves once the screen has closed. */
  readonly closed: Promise<void>;
  private resolveClosed: () => void = () => {};
  private modalTarget: { handle(i: Intent): void } | null = null;
  private isClosed = false;

  constructor(
    readonly opts: ScreenOptions,
    private readonly manager: ScreenManager,
  ) {
    const scrim = opts.scrim ?? opts.backdrop === "none";
    this.panel = h("div", { class: `ui-panel ui-panel--${opts.layout ?? "center"}` });
    this.root = h(
      "div",
      { class: `ui-screen ui-screen--${opts.id} ${scrim ? "ui-screen--scrim" : ""}`, attrs: { role: "dialog", "aria-label": opts.label ?? opts.id } },
      this.panel,
    );
    this.closed = new Promise((r) => (this.resolveClosed = r));
  }

  /** Append content to the panel. Navigable components are also added to `controls`. */
  add(...items: (Node | Navigable & { el: HTMLElement })[]): this {
    for (const item of items) {
      if (item instanceof Node) this.panel.append(item);
      else {
        this.panel.append(item.el);
        this.controls.push(item);
      }
    }
    return this;
  }

  get open(): boolean {
    return !this.isClosed;
  }

  /** Close with the leaving transition. Safe to call twice. */
  close(): void {
    if (this.isClosed) return;
    this.isClosed = true;
    this.manager.closed(this);
    this.root.classList.remove("is-shown");
    this.root.classList.add("is-leaving");
    let removed = false;
    const remove = () => {
      if (removed) return;
      removed = true;
      this.root.remove();
    };
    this.root.addEventListener("transitionend", (e) => e.target === this.root && remove());
    setTimeout(remove, 600); // reduced motion, or no transition fired
    this.resolveClosed();
  }

  /**
   * A modal over this screen: a small panel with actions in a row, which takes all input until an
   * action is chosen. Resolves with the action's value.
   */
  modal<T>(opts: ModalOptions<T>): Promise<T> {
    return new Promise((resolve) => {
      const body =
        typeof opts.body === "string" ? [h("p", { text: opts.body })]
        : Array.isArray(opts.body) ? opts.body.map((t) => h("p", { text: t }))
        : opts.body ? [opts.body]
        : [];
      const done = (value: T) => {
        this.modalTarget = null;
        layer.classList.add("is-leaving");
        setTimeout(() => layer.remove(), 250);
        resolve(value);
      };
      const actions = new MenuList({
        items: opts.actions.map((a) => ({ label: a.label })),
        focused: opts.focused ?? 0,
        orientation: "horizontal",
        class: "ui-modal__actions",
        onSelect: (i) => done(opts.actions[i].value),
      });
      const box = h("div", { class: "ui-panel ui-panel--narrow ui-modal__box", attrs: { role: "alertdialog" } }, opts.title ? h("h3", { class: "ui-title", text: opts.title }) : null, ...body, actions.el);
      const layer = h("div", { class: "ui-modal" }, box);
      if ("cancel" in opts) {
        layer.addEventListener("click", (e) => {
          if (e.target === layer) done(opts.cancel as T);
        });
      }
      this.root.append(layer);
      requestAnimationFrame(() => layer.classList.add("is-shown"));
      this.modalTarget = {
        handle: (intent) => {
          if (actions.handle(intent)) return;
          if (intent === "start") actions.handle("accept");
          else if (intent === "back" && "cancel" in opts) done(opts.cancel as T);
        },
      };
    });
  }

  /** Yes/no question; back/Escape answers `cancel` (default no). */
  confirm(text: string, opts: { title?: string; yes?: string; no?: string; focusYes?: boolean } = {}): Promise<boolean> {
    return this.modal({
      title: opts.title,
      body: text,
      actions: [
        { label: opts.yes ?? "Yes", value: true },
        { label: opts.no ?? "No", value: false },
      ],
      focused: opts.focusYes ? 0 : 1,
      cancel: false,
    });
  }

  // NavTarget

  key(e: KeyboardEvent): boolean {
    if (this.modalTarget || this.opts.passive) return false;
    return this.opts.onKey?.(e) ?? false;
  }

  intent(intent: Intent, device: InputDevice): void {
    if (this.opts.passive || this.isClosed) return;
    if (this.modalTarget) return this.modalTarget.handle(intent);
    if (this.opts.onIntent?.(intent, device)) return;
    for (const c of this.controls) if (c.handle(intent)) return;
    if (intent === "back") this.opts.onBack?.();
  }
}

export class ScreenManager {
  private _current: Screen | null = null;
  private _backdrop: BackdropControl | null = null;
  private nav: Nav | null = null;

  /** The screen on top, or null during a level. */
  get current(): Screen | null {
    return this._current;
  }

  /** The 3D backdrop, once main.ts has attached it (null in tests and without WebGL). */
  get backdrop(): BackdropControl | null {
    return this._backdrop;
  }

  attachBackdrop(backdrop: BackdropControl): void {
    this._backdrop = backdrop;
    backdrop.setMood(this._current?.opts.backdrop ?? "none");
  }

  /** Show a screen (closing the current one) and route input to it. */
  show(opts: ScreenOptions): Screen {
    this.nav ??= new Nav();
    const prev = this._current;
    const screen = new Screen(opts, this);
    this._current = screen;
    prev?.close();
    document.body.append(screen.root);
    // Next frame, so the entering transition runs from the initial state.
    requestAnimationFrame(() => requestAnimationFrame(() => screen.root.classList.add("is-shown")));
    this.nav.setTarget(opts.passive ? null : screen);
    this._backdrop?.setMood(opts.backdrop ?? "space");
    return screen;
  }

  /** Called by Screen.close. */
  closed(screen: Screen): void {
    if (this._current !== screen) return;
    this._current = null;
    this.nav?.setTarget(null);
    this._backdrop?.setMood("none");
  }
}

/** The one screen manager. */
export const ui = new ScreenManager();

/** Show a screen: shorthand for ui.show. */
export function showScreen(opts: ScreenOptions): Screen {
  return ui.show(opts);
}

/** A back button for the panel's corner (for touch; Escape and B do the same). */
export function backButton(onPress: () => void, label = "Back"): HTMLButtonElement {
  return button({ label, variant: "ghost", class: "ui-back", hint: { key: "Esc", pad: "B" }, onPress });
}
