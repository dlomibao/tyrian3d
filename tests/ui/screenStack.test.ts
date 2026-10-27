// Screens shown over another (ScreenOptions.over, src/ui/screen.ts): the one beneath stays open
// without input, gets it back when the one over it closes, and a screen shown normally closes
// them all. Run under node with a few stand-ins for the DOM the manager touches.
import { afterAll, beforeEach, describe, expect, test } from "vitest";
import { ScreenManager, type BackdropMood } from "../../src/ui/screen";

/** Just enough of an element for h() and the screen manager. */
class FakeElement {
  textContent = "";
  children: FakeElement[] = [];
  parent: FakeElement | null = null;
  attrs: Record<string, string> = {};
  private readonly classes = new Set<string>();
  get className(): string {
    return [...this.classes].join(" ");
  }
  set className(v: string) {
    this.classes.clear();
    for (const c of v.split(/\s+/)) if (c) this.classes.add(c);
  }
  readonly classList = {
    add: (...c: string[]) => c.forEach((x) => this.classes.add(x)),
    remove: (...c: string[]) => c.forEach((x) => this.classes.delete(x)),
    toggle: (c: string, on = !this.classes.has(c)) => (on ? this.classes.add(c) : this.classes.delete(c), on),
    contains: (c: string) => this.classes.has(c),
  };
  setAttribute(k: string, v: string): void {
    this.attrs[k] = v;
  }
  addEventListener(): void {}
  append(...nodes: unknown[]): void {
    for (const n of nodes) if (n instanceof FakeElement) (this.children.push(n), (n.parent = this));
  }
  remove(): void {
    if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this);
    this.parent = null;
  }
}

type Listener = (e: unknown) => void;
const listeners: Record<string, Listener[]> = {};
const body = new FakeElement();
const saved = { document: globalThis.document, window: globalThis.window, raf: globalThis.requestAnimationFrame };
Object.assign(globalThis, {
  document: { createElement: () => new FakeElement(), body, documentElement: { dataset: {} } },
  window: { addEventListener: (type: string, fn: Listener) => (listeners[type] ??= []).push(fn) },
  requestAnimationFrame: () => 0,
  cancelAnimationFrame: () => {},
});
afterAll(() => Object.assign(globalThis, { document: saved.document, window: saved.window, requestAnimationFrame: saved.raf }));

/** Press a key as the browser would: the Nav's window listener gets it. */
function press(code: string): void {
  const e = { code, key: "", target: null, preventDefault() {}, stopPropagation() {} };
  for (const fn of listeners.keydown ?? []) fn(e);
}

let manager: ScreenManager;
let moods: BackdropMood[];
beforeEach(() => {
  for (const k of Object.keys(listeners)) delete listeners[k];
  body.children = [];
  manager = new ScreenManager();
  moods = [];
  manager.attachBackdrop({ setMood: (m) => moods.push(m) });
});

describe("screens over screens", () => {
  test("the one beneath stays open, hidden, without input, and gets it back on close", () => {
    const got: string[] = [];
    const title = manager.show({ id: "title", backdrop: "title", onIntent: (i) => void got.push(`title ${i}`) });
    const options = manager.show({ id: "options", over: true, onIntent: (i) => void got.push(`options ${i}`) });
    expect(title.open).toBe(true);
    expect(title.root.classList.contains("is-under")).toBe(true);
    expect(manager.current).toBe(options);
    // The backdrop keeps the title's mood.
    expect(options.opts.backdrop).toBe("title");
    expect(moods.at(-1)).toBe("title");
    press("Enter");
    options.close();
    expect(manager.current).toBe(title);
    expect(title.root.classList.contains("is-under")).toBe(false);
    press("ArrowDown");
    expect(got).toEqual(["options accept", "title down"]);
    expect(moods.at(-1)).toBe("title");
  });

  test('"show" leaves the screen beneath in view; a mood of its own replaces the one beneath until it closes', () => {
    const shop = manager.show({ id: "shop", backdrop: "hangar" });
    const prompt = manager.show({ id: "save", over: "show", backdrop: "space" });
    expect(shop.root.classList.contains("is-under")).toBe(false);
    expect(moods.at(-1)).toBe("space");
    prompt.close();
    expect(moods.at(-1)).toBe("hangar");
    expect(manager.current).toBe(shop);
  });

  test("a screen shown normally closes the whole stack", () => {
    const a = manager.show({ id: "a" });
    const b = manager.show({ id: "b", over: true });
    const c = manager.show({ id: "c" });
    expect([a.open, b.open, c.open]).toEqual([false, false, true]);
    c.close();
    expect(manager.current).toBeNull();
    expect(moods.at(-1)).toBe("none");
  });

  test("over nothing, it is an ordinary screen", () => {
    const a = manager.show({ id: "a", over: true });
    expect(a.opts.backdrop).toBeUndefined();
    expect(moods.at(-1)).toBe("space");
    a.close();
    expect(manager.current).toBeNull();
  });
});
