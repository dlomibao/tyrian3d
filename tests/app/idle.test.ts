// The title screen's idle timer, which starts the attract-mode demos (src/app/idle.ts).
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { IdleTimer, TITLE_IDLE_MS } from "../../src/app/idle";

let pads: { buttons: { pressed: boolean }[]; axes: number[] }[] = [];
const win = new EventTarget();
const doc = Object.assign(new EventTarget(), { hidden: false });

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "setTimeout", "performance"] });
  vi.stubGlobal("window", win);
  vi.stubGlobal("document", doc);
  vi.stubGlobal("navigator", { getGamepads: () => pads });
  pads = [];
  doc.hidden = false;
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("IdleTimer", () => {
  test("the title waits 30 seconds, as the C does", () => expect(TITLE_IDLE_MS).toBe(30_000));

  test("fires once the time passes without input, then counts again", () => {
    const onIdle = vi.fn();
    const t = new IdleTimer(1000, onIdle);
    vi.advanceTimersByTime(900);
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(400);
    expect(onIdle).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(600);
    expect(onIdle).toHaveBeenCalledTimes(1);
    t.stop();
  });

  test("a key, a pointer, a pad or a hidden page restarts the count; stop ends it", () => {
    const onIdle = vi.fn();
    const t = new IdleTimer(1000, onIdle);
    for (const type of ["keydown", "pointermove", "pointerdown"]) {
      vi.advanceTimersByTime(800);
      win.dispatchEvent(new Event(type));
    }
    pads = [{ buttons: [{ pressed: false }], axes: [0.8, 0] }];
    vi.advanceTimersByTime(2000);
    pads = [];
    doc.hidden = true;
    vi.advanceTimersByTime(2000);
    doc.hidden = false;
    expect(onIdle).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1300);
    expect(onIdle).toHaveBeenCalledTimes(1);
    t.stop();
    vi.advanceTimersByTime(5000);
    expect(onIdle).toHaveBeenCalledTimes(1);
  });
});
