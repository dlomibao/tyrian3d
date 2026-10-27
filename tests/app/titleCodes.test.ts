// The title's code keys (src/app/titleCodes.ts): which keys the codes take from the title's own
// shortcuts and menus, the hidden difficulties, and the hooks a completed code goes to.
import { afterEach, beforeAll, describe, expect, test } from "vitest";
import type { TitleCode } from "../../src/sim/cheats";

// TitleCodeListener listens for keyup on the window; node has none.
beforeAll(() => {
  const g = globalThis as { window?: unknown };
  g.window ??= { addEventListener() {}, removeEventListener() {} };
});

const SPECIAL_NAME = ["STEALTH", "STORMWIND", "TECHNO", "ENEMY", "WEIRD", "UNKNOWN", "NORTSHIPZ", "DESTRUCT", "ENGAGE"];

/** A keydown as the title's onKey gets it. */
const ev = (key: string, shiftKey = false) => ({
  key,
  code: key === "]" || key === "}" ? "BracketRight" : /^[a-z]$/i.test(key) ? `Key${key.toUpperCase()}` : key,
  shiftKey,
  ctrlKey: false,
  metaKey: false,
  altKey: false,
  repeat: false,
});

async function listener(visible = 3) {
  const { TitleCodeListener } = await import("../../src/app/titleCodes");
  const codes: TitleCode[] = [];
  const shown: number[] = [];
  const l = new TitleCodeListener({
    specialName: SPECIAL_NAME,
    difficultyVisible: visible,
    onCode: (c) => codes.push(c),
    onDifficultyVisible: (n) => shown.push(n),
  });
  return { l, codes, shown, typeKeys: (s: string) => [...s].map((c) => l.key(ev(c))) };
}

describe("TitleCodeListener", () => {
  test("a code's first letter still moves the menus; the rest of it is the code's", async () => {
    const { codes, typeKeys } = await listener();
    expect(typeKeys("STEALTH")).toEqual([false, true, true, true, true, true, true]);
    expect(codes).toEqual([{ kind: "superArcade", index: 0 }]);
    expect(typeKeys("DESTRUCT")[0]).toBe(false);
    expect(codes.at(-1)).toEqual({ kind: "destruct" });
    typeKeys("ENGAGE");
    expect(codes.at(-1)).toEqual({ kind: "superTyrian" });
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

describe("runTitleCode", () => {
  const ctx = () => ({
    files: {} as never,
    sfx: { playSampleNum: () => {} } as never,
    music: {} as never,
    superShips: ["Super Arcade Mode", "Ninja Star", "StormWind - The Elemental"],
    specialName: SPECIAL_NAME,
  });

  afterEach(async () => {
    const { titleCodeHooks } = await import("../../src/app/titleCodes");
    for (const k of Object.keys(titleCodeHooks)) delete titleCodeHooks[k as keyof typeof titleCodeHooks];
  });

  test("goes to the feature's hook, and starts a game when the hook set one up", async () => {
    const { runTitleCode, titleCodeHooks } = await import("../../src/app/titleCodes");
    const calls: string[] = [];
    titleCodeHooks.superArcade = async (i) => (calls.push(`arcade ${i}`), true);
    titleCodeHooks.superTyrian = async () => (calls.push("tyrian"), false);
    titleCodeHooks.destruct = async () => void calls.push("destruct");
    expect(await runTitleCode({ kind: "superArcade", index: 1 }, ctx())).toBe(true);
    expect(await runTitleCode({ kind: "superTyrian" }, ctx())).toBe(false);
    expect(await runTitleCode({ kind: "destruct" }, ctx())).toBe(false);
    expect(calls).toEqual(["arcade 1", "tyrian", "destruct"]);
  });

  test("the notice for a code names its ship or mode", async () => {
    const { titleCodeName } = await import("../../src/app/titleCodes");
    expect(titleCodeName({ kind: "superArcade", index: 1 }, ctx())).toEqual({ heading: "Super Arcade Mode", name: "StormWind - The Elemental" });
    expect(titleCodeName({ kind: "destruct" }, ctx()).heading).toBe("DESTRUCT");
    expect(titleCodeName({ kind: "superTyrian" }, ctx()).name).toBe("ENGAGE");
  });
});
