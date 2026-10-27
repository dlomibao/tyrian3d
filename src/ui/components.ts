// Base components of the remastered interface: small DOM builders styled by components.css. Each
// interactive one implements Navigable, so a screen hands it the intents it doesn't use itself
// (src/ui/README.md). Focus is drawn by the component (the is-focused class), not the browser's
// focus ring, so it looks the same whichever device moved it, and it is always scrolled into view.

import { firstFocusable, moveFocus } from "./focus";
import type { Intent } from "./nav";

/** Something that takes intents: return true when the intent was used. */
export interface Navigable {
  handle(intent: Intent): boolean;
}

type Child = Node | string | null | undefined | false;

export interface HProps {
  class?: string;
  text?: string;
  /** Trusted markup only (never text from the data files: use `text`). */
  html?: string;
  attrs?: Record<string, string>;
  on?: { [K in keyof HTMLElementEventMap]?: (e: HTMLElementEventMap[K]) => void };
}

/** Create an element: h("p", { class: "ui-text" }, "Hello", h("b", {}, "world")). */
export function h<K extends keyof HTMLElementTagNameMap>(tag: K, props: HProps = {}, ...children: Child[]): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (props.class) el.className = props.class;
  if (props.text !== undefined) el.textContent = props.text;
  if (props.html !== undefined) el.innerHTML = props.html;
  for (const [k, v] of Object.entries(props.attrs ?? {})) el.setAttribute(k, v);
  for (const [type, fn] of Object.entries(props.on ?? {})) el.addEventListener(type, fn as EventListener);
  for (const c of children) if (c !== null && c !== undefined && c !== false) el.append(c);
  return el;
}

/** Escape text for markup. */
export const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);

/** Keep an element inside its scrolling parents' view (the focused item is always visible). */
export function reveal(el: Element | null | undefined): void {
  el?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

// --- titles ---

/** The game's logo: TYRIAN with a 3D tag. */
export function logo(sub = "3D"): HTMLElement {
  return h("h1", { class: "ui-logo", attrs: { "aria-label": `Tyrian ${sub}` } }, h("span", { class: "ui-logo__word", text: "TYRIAN" }), h("span", { class: "ui-logo__tag", text: sub }));
}

/** A screen or section title in the display face, with an optional kicker line above it. */
export function title(text: string, kicker?: string, level: "h2" | "h3" = "h2"): HTMLElement {
  return h(level, { class: "ui-title" }, kicker ? h("small", { class: "ui-title__kicker", text: kicker }) : null, h("span", { text }));
}

// --- buttons and hints ---

export interface ButtonOptions {
  label: string;
  /** "primary" glows gold; "ghost" is quiet. */
  variant?: "primary" | "default" | "ghost";
  /** A key hint shown inside the button, e.g. { key: "Esc", pad: "B" }. */
  hint?: KeyHint;
  onPress?: () => void;
  class?: string;
}

export function button(opts: ButtonOptions): HTMLButtonElement {
  const b = h(
    "button",
    { class: `ui-button ui-button--${opts.variant ?? "default"} ${opts.class ?? ""}`, attrs: { type: "button", tabindex: "-1" } },
    h("span", { text: opts.label }),
    opts.hint ? keyGlyphs(opts.hint) : null,
  );
  if (opts.onPress) b.addEventListener("click", opts.onPress);
  return b;
}

export interface KeyHint {
  /** Keyboard key(s), e.g. "Enter" or "↑↓". */
  key?: string;
  /** Gamepad button, e.g. "A". */
  pad?: string;
  /** What to do on a touch screen, e.g. "Tap". Without it the hint hides on touch screens. */
  touch?: string;
  label?: string;
}

/** The key, pad button and touch glyphs of one hint; CSS shows the one for the last device used. */
export function keyGlyphs(hint: KeyHint): HTMLElement {
  const span = h("span", { class: "ui-glyphs" });
  if (hint.key) span.append(h("kbd", { class: "ui-key", attrs: { "data-dev": "keys" }, text: hint.key }));
  if (hint.pad) span.append(h("kbd", { class: "ui-key ui-key--pad", attrs: { "data-dev": "pad" }, text: hint.pad }));
  if (hint.touch) span.append(h("kbd", { class: "ui-key ui-key--touch", attrs: { "data-dev": "touch" }, text: hint.touch }));
  if (!hint.touch) span.dataset.noTouch = "";
  return span;
}

/** A row of key hints for the bottom of a panel. */
export function keyHints(hints: KeyHint[]): HTMLElement {
  return h(
    "div",
    { class: "ui-hints", attrs: { "aria-hidden": "true" } },
    ...hints.map((hint) => {
      const el = h("span", { class: "ui-hint" }, keyGlyphs(hint), hint.label ? h("span", { class: "ui-hint__label", text: hint.label }) : null);
      if (!hint.touch) el.dataset.noTouch = "";
      return el;
    }),
  );
}

// --- menu lists ---

export interface MenuItem {
  label: string;
  /** A second, smaller line (price, current item, level name). */
  detail?: string;
  /** An icon: an image URL or an element. */
  icon?: string | HTMLElement;
  /** A tag on the right, e.g. "OWNED". */
  badge?: string;
  /** Skipped by the focus and not selectable. */
  disabled?: boolean;
  /** Extra classes for the row. */
  class?: string;
}

export interface MenuListOptions {
  items: MenuItem[];
  focused?: number;
  /** "vertical" (up/down, the default) or "horizontal" (left/right, a row of choices). */
  orientation?: "vertical" | "horizontal";
  /** Wrap from the last item to the first (default: vertical lists wrap, rows don't). */
  wrap?: boolean;
  /** Accept on the focused item, or a tap/click on any item. */
  onSelect?: (index: number) => void;
  /** The focus moved (also on a tap). A row of choices can treat the focus as the value. */
  onFocus?: (index: number) => void;
  /** aria-label of the list. */
  label?: string;
  class?: string;
}

/**
 * A list of items with one focused. Up/down (or left/right in a row) move the focus, accept
 * selects; a tap focuses and selects. Rows of choices (difficulty, a volume level) are horizontal
 * lists whose onFocus sets the value.
 */
export class MenuList implements Navigable {
  readonly el: HTMLUListElement;
  private items: MenuItem[] = [];
  private _focused = 0;

  constructor(private readonly opts: MenuListOptions) {
    const horizontal = opts.orientation === "horizontal";
    this.el = h("ul", {
      class: `ui-menu ${horizontal ? "ui-menu--row" : ""} ${opts.class ?? ""}`,
      attrs: { role: "listbox", "aria-orientation": horizontal ? "horizontal" : "vertical", ...(opts.label ? { "aria-label": opts.label } : {}) },
    });
    this.el.addEventListener("click", (e) => {
      const li = (e.target as HTMLElement).closest<HTMLElement>("[data-index]");
      if (!li) return;
      const i = Number(li.dataset.index);
      if (this.items[i]?.disabled) return;
      this.focus(i);
      this.opts.onSelect?.(i);
    });
    this.setItems(opts.items, opts.focused ?? 0);
  }

  get focused(): number {
    return this._focused;
  }

  /** Replace the items (and optionally the focus). */
  setItems(items: MenuItem[], focused = this._focused): void {
    this.items = items;
    this.el.replaceChildren(...items.map((item, i) => this.row(item, i)));
    this._focused = firstFocusable(items.length, Math.min(Math.max(0, focused), items.length - 1), (i) => !!items[i].disabled);
    this.paint();
  }

  /** Focus an item (without selecting it). */
  focus(index: number): void {
    if (index < 0 || index >= this.items.length || index === this._focused) return;
    this._focused = index;
    this.paint();
    this.opts.onFocus?.(index);
  }

  handle(intent: Intent): boolean {
    const horizontal = this.opts.orientation === "horizontal";
    const back = horizontal ? "left" : "up";
    const fwd = horizontal ? "right" : "down";
    if (intent === back || intent === fwd) {
      const next = moveFocus(this.items.length, this._focused, intent === fwd ? 1 : -1, {
        wrap: this.opts.wrap ?? !horizontal,
        skip: (i) => !!this.items[i].disabled,
      });
      this.focus(next);
      return true;
    }
    if (intent === "accept" && this.opts.onSelect && this._focused >= 0) {
      this.opts.onSelect(this._focused);
      return true;
    }
    return false;
  }

  private row(item: MenuItem, i: number): HTMLLIElement {
    const icon = typeof item.icon === "string" ? h("img", { attrs: { src: item.icon, alt: "" } }) : item.icon;
    return h(
      "li",
      {
        class: `ui-menu__item ${item.disabled ? "is-disabled" : ""} ${item.class ?? ""}`,
        attrs: { role: "option", "data-index": String(i), "aria-disabled": String(!!item.disabled) },
      },
      icon ? h("span", { class: "ui-menu__icon" }, icon) : null,
      h("span", { class: "ui-menu__text" }, h("span", { class: "ui-menu__label", text: item.label }), item.detail ? h("small", { class: "ui-menu__detail", text: item.detail }) : null),
      item.badge ? h("span", { class: "ui-badge", text: item.badge }) : null,
    );
  }

  private paint(): void {
    [...this.el.children].forEach((li, i) => {
      li.classList.toggle("is-focused", i === this._focused);
      li.setAttribute("aria-selected", String(i === this._focused));
    });
    reveal(this.el.children[this._focused]);
  }
}

// --- stat bars ---

export interface StatBar {
  el: HTMLElement;
  /** Set the fill, 0..1. */
  set(fraction: number): void;
}

/** A labelled bar (armor, shield, power). `tone` picks the colour token. */
export function statBar(label: string, tone: "armor" | "shield" | "power" | "gold" | "cyan", fraction = 0): StatBar {
  const fill = h("i");
  const el = h("div", { class: `ui-stat ui-stat--${tone}` }, h("span", { class: "ui-stat__label", text: label }), h("span", { class: "ui-stat__bar" }, fill));
  const set = (f: number) => (fill.style.width = `${Math.round(Math.max(0, Math.min(1, f)) * 100)}%`);
  set(fraction);
  return { el, set };
}

// --- scrolling text ---

/** A scrollable text box: up/down scroll it a few lines at a time, and the wheel or a finger work too. */
export class ScrollBox implements Navigable {
  readonly el: HTMLDivElement;

  constructor(...content: Child[]) {
    this.el = h("div", { class: "ui-scroll", attrs: { tabindex: "-1" } }, ...content);
  }

  handle(intent: Intent): boolean {
    if (intent !== "up" && intent !== "down") return false;
    const line = parseFloat(getComputedStyle(this.el).lineHeight) || 20;
    this.el.scrollBy({ top: (intent === "down" ? 3 : -3) * line, behavior: "smooth" });
    return true;
  }
}

/** A panel: the framed box screens are made of. */
export function panel(...children: Child[]): HTMLDivElement {
  return h("div", { class: "ui-panel" }, ...children);
}
