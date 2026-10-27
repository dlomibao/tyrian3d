// The interface framework's navigation model (src/ui/nav.ts) and focus movement (src/ui/focus.ts):
// keys and pad snapshots become intents, held directions repeat, buttons held when a screen
// appears are ignored, and the focus skips disabled items.
import { describe, expect, test } from "vitest";
import { firstFocusable, moveFocus } from "../../src/ui/focus";
import { keyIntent, PadReader, REPEAT_DELAY_MS, REPEAT_RATE_MS, type PadState } from "../../src/ui/nav";

const pad = (pressed: number[] = [], axes: number[] = [0, 0]): PadState => {
  const buttons = Array.from({ length: 17 }, (_, i) => pressed.includes(i));
  return { buttons, axes };
};

describe("keyIntent", () => {
  test("arrows and WASD move, Enter/Space accept, Escape/Backspace back, / is alt", () => {
    expect(["ArrowUp", "KeyW"].map((c) => keyIntent(c))).toEqual(["up", "up"]);
    expect(["ArrowDown", "KeyS"].map((c) => keyIntent(c))).toEqual(["down", "down"]);
    expect(["ArrowLeft", "KeyA", "ArrowRight", "KeyD"].map((c) => keyIntent(c))).toEqual(["left", "left", "right", "right"]);
    expect(["Enter", "NumpadEnter", "Space"].map((c) => keyIntent(c))).toEqual(["accept", "accept", "accept"]);
    expect(["Escape", "Backspace"].map((c) => keyIntent(c))).toEqual(["back", "back"]);
    expect(keyIntent("Slash")).toBe("alt");
    // '/' typed on a layout where it isn't the Slash key.
    expect(keyIntent("Digit7", "/")).toBe("alt");
    expect(keyIntent("KeyM")).toBeUndefined();
  });
});

describe("PadReader", () => {
  test("ignores buttons held when it is (re)armed, until they are released", () => {
    const r = new PadReader();
    expect(r.update([pad([0])], 0)).toEqual([]);
    expect(r.update([pad([0])], 500)).toEqual([]);
    expect(r.update([pad()], 600)).toEqual([]);
    expect(r.update([pad([0])], 700)).toEqual(["accept"]);
    r.rearm();
    expect(r.update([pad([0])], 800)).toEqual([]);
  });

  test("buttons fire once per press; A, B, X and Start map to accept, back, alt and start", () => {
    const r = new PadReader();
    r.update([pad()], 0);
    expect(r.update([pad([0, 1, 2, 9])], 10)).toEqual(["accept", "back", "alt", "start"]);
    expect(r.update([pad([0, 1, 2, 9])], 10 + REPEAT_DELAY_MS * 3)).toEqual([]);
    expect(r.update([pad()], 2000)).toEqual([]);
    expect(r.update([pad([1])], 2010)).toEqual(["back"]);
  });

  test("held directions repeat after a delay, then at the repeat rate", () => {
    const r = new PadReader();
    r.update([pad()], 0);
    const t0 = 100;
    expect(r.update([pad([13])], t0)).toEqual(["down"]);
    expect(r.update([pad([13])], t0 + REPEAT_DELAY_MS - 1)).toEqual([]);
    expect(r.update([pad([13])], t0 + REPEAT_DELAY_MS)).toEqual(["down"]);
    expect(r.update([pad([13])], t0 + REPEAT_DELAY_MS + REPEAT_RATE_MS - 1)).toEqual([]);
    expect(r.update([pad([13])], t0 + REPEAT_DELAY_MS + REPEAT_RATE_MS)).toEqual(["down"]);
  });

  test("the left stick counts as the d-pad past the threshold, and pads merge", () => {
    const r = new PadReader();
    r.update([pad()], 0);
    expect(r.update([pad([], [0.3, -0.2])], 10)).toEqual([]);
    expect(r.update([pad([], [-0.9, 0])], 20)).toEqual(["left"]);
    expect(r.update([pad([], [-0.9, 0]), pad([15])], 30)).toEqual(["right"]);
    expect([...PadReader.active([pad([], [0, 0.8])])]).toEqual(["down"]);
  });
});

describe("moveFocus", () => {
  test("wraps by default and stops at the ends without wrap", () => {
    expect(moveFocus(4, 3, 1)).toBe(0);
    expect(moveFocus(4, 0, -1)).toBe(3);
    expect(moveFocus(4, 3, 1, { wrap: false })).toBe(3);
    expect(moveFocus(4, 0, -1, { wrap: false })).toBe(0);
    expect(moveFocus(4, 1, 2)).toBe(3);
  });

  test("skips disabled items, and stays put when nothing else can take the focus", () => {
    const off = new Set([1, 2]);
    const skip = (i: number) => off.has(i);
    expect(moveFocus(5, 0, 1, { skip })).toBe(3);
    expect(moveFocus(5, 3, -1, { skip })).toBe(0);
    expect(moveFocus(3, 0, 1, { skip: (i) => i !== 0 })).toBe(0);
    expect(moveFocus(4, 0, 1, { wrap: false, skip: (i) => i > 0 })).toBe(0);
    expect(moveFocus(0, 0, 1)).toBe(-1);
  });

  test("firstFocusable finds the first item that can take the focus", () => {
    expect(firstFocusable(4, 1, (i) => i === 1)).toBe(2);
    expect(firstFocusable(4, 3, (i) => i === 3)).toBe(0);
    expect(firstFocusable(2, 0, () => true)).toBe(-1);
  });
});
