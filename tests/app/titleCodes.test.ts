// The title's code keys (src/app/titleCodes.ts): which keys the codes take from the title's own
// shortcuts and menus, the hidden difficulties, and the Destruct hook.
import { afterEach, beforeAll, describe, expect, test } from "vitest";
import type { TitleCode } from "../../src/sim/arcade";

// TitleCodeListener listens for keyup on the window; node has none.
beforeAll(() => {
  const g = globalThis as { window?: unknown };
  g.window ??= { addEventListener() {}, removeEventListener() {} };
});

const SPECIAL_NAME = ["STEALTH", "STORMWIND", "TECHNO", "ENEMY", "WEIRD", "UNKNOWN", "NORTSHIPZ", "DESTRUCT", "ENGAGE"];

/** A keydown as the title's onKey gets it. */
const ev = (key: string, shiftKey = false, repeat = false) => ({
  key,
  code: key === "]" || key === "}" ? "BracketRight" : /^[a-z]$/i.test(key) ? `Key${key.toUpperCase()}` : key,
  shiftKey,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  repeat,
});

async function listener(visible = 3) {
  const { TitleCodeListener } = await import("../../src/app/titleCodes");
  const codes: TitleCode[] = [];
  const shown: number[] = [];
  let marks = 0;
  const l = new TitleCodeListener({
    specialName: SPECIAL_NAME,
    difficultyVisible: visible,
    onCode: (c) => codes.push(c),
    onDifficultyVisible: (n) => shown.push(n),
    onCodeMayStart: () => marks++,
  });
  return { l, codes, shown, marks: () => marks, typeKeys: (s: string) => [...s].map((c) => l.key(ev(c))) };
}

describe("TitleCodeListener", () => {
  test("a code's first letter still moves the menus; the rest of it is the code's", async () => {
    const { codes, typeKeys } = await listener();
    expect(typeKeys("STEALTH")).toEqual([false, true, true, true, true, true, true]);
    expect(codes).toEqual([{ kind: "superArcade", superArcadeMode: 1 }]);
    expect(typeKeys("DESTRUCT")[0]).toBe(false);
    expect(codes.at(-1)).toEqual({ kind: "destruct" });
    typeKeys("ENGAGE");
    expect(codes.at(-1)).toEqual({ kind: "superTyrian" });
  });

  test("the title is told before each key that may start a code, to put its menus back after", async () => {
    const { marks, typeKeys } = await listener();
    typeKeys("XST"); // X: may start; S: may start (nothing under way); T continues
    expect(marks()).toBe(2);
  });

  test("modifier keys and key repeats don't break a code; an arrow does, and a finished code doesn't re-fire", async () => {
    const { l, codes, typeKeys } = await listener();
    typeKeys("ENGA");
    expect(l.key(ev("Shift", true))).toBe(false);
    expect(l.key(ev("A", false, true))).toBe(false);
    typeKeys("GE");
    expect(codes).toEqual([{ kind: "superTyrian" }]);
    expect(l.key(ev("ArrowUp"))).toBe(false);
    expect(codes).toHaveLength(1);
    typeKeys("ENE");
    l.key(ev("ArrowUp"));
    typeKeys("MY");
    expect(codes).toHaveLength(1);
  });

  test("the shortcuts (L, O, H, M) keep working outside a code, and when a code breaks off", async () => {
    const { l, codes, typeKeys } = await listener();
    expect(typeKeys("LOHM")).toEqual([false, false, false, false]);
    expect(typeKeys("ST")).toEqual([false, true]);
    expect(l.key(ev("H"))).toBe(false); // "STH" isn't a code: H opens High Scores
    expect(codes).toEqual([]);
  });

  test("Shift+G, Shift+] and L O R D reveal the hidden difficulties, taking their keys", async () => {
    const { l, shown, typeKeys } = await listener();
    expect(l.key(ev("G", true))).toBe(true);
    expect(l.key(ev("}", true))).toBe(true);
    expect(shown).toEqual([4, 5]);
    expect(typeKeys("LORD")).toEqual([true, true, true, true]);
    expect(shown).toEqual([4, 5, 6]);
    // Once all are shown, L is Load Game again.
    expect(l.key(ev("L"))).toBe(false);
  });

  test("a row already showing a hidden difficulty starts from there", async () => {
    const { l, shown } = await listener(5);
    expect(l.key(ev("G", true))).toBe(false);
    expect(shown).toEqual([]);
  });

  test("keys with Ctrl, Alt or Cmd aren't codes", async () => {
    const { l, codes } = await listener();
    for (const c of "TECHNO") l.key({ ...ev(c), ctrlKey: true });
    expect(codes).toEqual([]);
  });

  test("keySym: the unshifted key, lower case", async () => {
    const { keySym } = await import("../../src/app/titleCodes");
    expect(keySym({ key: "G", code: "KeyG" })).toBe("g");
    expect(keySym({ key: "}", code: "BracketRight" })).toBe("]");
    expect(keySym({ key: "ArrowUp", code: "ArrowUp" })).toBe("");
  });
});

describe("the DESTRUCT code", () => {
  afterEach(async () => {
    const { destructHook } = await import("../../src/app/titleCodes");
    destructHook.open = null;
  });

  test("opens the Destruct game through destructHook once it's set", async () => {
    const { destructHook, runDestruct } = await import("../../src/app/titleCodes");
    const calls: string[] = [];
    destructHook.open = async (ctx) => void calls.push(ctx.specialName[7]);
    await runDestruct({ files: {} as never, sfx: { playSampleNum: () => {} } as never, specialName: SPECIAL_NAME });
    expect(calls).toEqual(["DESTRUCT"]);
  });
});
