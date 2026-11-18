// The How to play card (src/app/howToPlay.ts, D266): when it shows by itself, the flag that
// remembers it, the column it lights, and that its controls are the player's bindings.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, test } from "vitest";
import { bindKey, clearKey, resetKeys, keys } from "../../src/app/bindings";
import {
  HOW_TO_PLAY_STORAGE_KEY,
  howToPlayColumn,
  howToPlayDue,
  howToPlayParam,
  howToPlaySeen,
  keyboardRows,
  markHowToPlaySeen,
  moveKeys,
  touchRows,
  type FlagStorage,
  type HowToPlayDue,
} from "../../src/app/howToPlay";
import { PAUSE_ITEMS } from "../../src/app/pause";

class MemoryStorage implements FlagStorage {
  data = new Map<string, string>();
  getItem(k: string): string | null {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string): void {
    this.data.set(k, v);
  }
}

const fresh: HowToPlayDue = { seen: false, twoPlayer: false, param: null, automated: false, console: false };

beforeEach(() => resetKeys());

describe("shown once by itself", () => {
  test("the flag starts unset, is set once shown, and survives in storage", () => {
    const s = new MemoryStorage();
    expect(howToPlaySeen(s)).toBe(false);
    markHowToPlaySeen(s);
    expect(s.data.get(HOW_TO_PLAY_STORAGE_KEY)).toBe("1");
    expect(howToPlaySeen(s)).toBe(true);
  });

  test("storage that throws or is missing never nags and never breaks the game", () => {
    const broken: FlagStorage = {
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => {
        throw new Error("full");
      },
    };
    expect(howToPlaySeen(broken)).toBe(true);
    expect(() => markHowToPlaySeen(broken)).not.toThrow();
    expect(howToPlaySeen(null)).toBe(true);
  });

  test("due on a first one-player level only", () => {
    expect(howToPlayDue(fresh)).toBe(true);
    expect(howToPlayDue({ ...fresh, seen: true })).toBe(false);
    expect(howToPlayDue({ ...fresh, twoPlayer: true })).toBe(false);
    expect(howToPlayDue({ ...fresh, automated: true })).toBe(false); // headless captures, bots
    expect(howToPlayDue({ ...fresh, console: true })).toBe(false); // a debug-console start
  });

  test("?howtoplay=1 forces it, =0 turns it off", () => {
    expect(howToPlayParam("?howtoplay=1")).toBe(true);
    expect(howToPlayParam("?howtoplay=0")).toBe(false);
    expect(howToPlayParam("?debug=play")).toBe(null);
    expect(howToPlayDue({ ...fresh, seen: true, automated: true, param: true })).toBe(true);
    expect(howToPlayDue({ ...fresh, param: false })).toBe(false);
  });

  test("the level start waits for it before the first tick, and the pause menu opens it after Resume", () => {
    const run = readFileSync(join(__dirname, "..", "..", "src", "app", "run.ts"), "utf8");
    const at = run.indexOf("await showHowToPlay()");
    expect(at).toBeGreaterThan(run.indexOf("await preloadLevelModels(view)"));
    expect(at).toBeLessThan(run.indexOf("await playLevel("));
    expect(PAUSE_ITEMS).toEqual(["Resume", "How to play", "Options", "Quit to title"]);
  });
});

describe("what it shows", () => {
  test("lights the device used last; ?touchhud=1 lights touch", () => {
    expect(howToPlayColumn("keys", null)).toBe("keys");
    expect(howToPlayColumn("mouse", null)).toBe("keys");
    expect(howToPlayColumn(undefined, null)).toBe("keys");
    expect(howToPlayColumn("touch", null)).toBe("touch");
    expect(howToPlayColumn("pad", null)).toBe("pad");
    expect(howToPlayColumn("keys", true)).toBe("touch");
  });

  test("the default keys", () => {
    expect(keyboardRows()).toEqual([
      ["Move", [["←↑↓→"], ["WASD"]]],
      ["Fire", [["Space"], ["J"]]],
      ["Rear gun mode", [["Return"], ["L"]]],
      ["Sidekicks, bombs", [["Left Ctrl", "Left Alt"], ["K", ";"]]],
      ["Pause", [["Esc"], ["P"]]],
    ]);
  });

  test("the player's own bindings, not the defaults", () => {
    bindKey("fire", 0, "KeyZ");
    clearKey("fire", 1);
    bindKey("up", 1, "KeyI");
    expect(keyboardRows()[1]).toEqual(["Fire", [["Z"]]]);
    expect(moveKeys(keys)).toEqual(["←↑↓→", "I S A D"]);
  });

  test("touch targets only where the framed HUD has them (D100)", () => {
    expect(touchRows(true).map(([l]) => l)).toEqual(["Move", "Fire", "Rear gun mode", "Sidekicks, bombs", "Pause"]);
    expect(touchRows(false).map(([l]) => l)).toEqual(["Move", "Fire", "Pause"]);
  });
});
