// The title's pad shortcuts (src/app/screens.ts TITLE_PAD): each entry has its own button, and none
// of them is a button the navigation already turns into an intent (src/ui/nav.ts).
import { describe, expect, test } from "vitest";
import { TITLE_PAD } from "../../src/app/screens";
import { PAD_BUTTONS } from "../../src/ui/nav";

describe("TITLE_PAD", () => {
  const entries = Object.values(TITLE_PAD);

  test("gives Load Game, Options and High Scores a button each", () => {
    expect(new Set(entries.map((e) => e.button)).size).toBe(entries.length);
    expect(TITLE_PAD.loadGame.glyph).toBe("LB");
  });

  test("uses no button that is already an intent (A, B, X, Start, the d-pad)", () => {
    const intents = new Set(PAD_BUTTONS.map(([i]) => i));
    for (const e of entries) expect(intents.has(e.button)).toBe(false);
  });
});
