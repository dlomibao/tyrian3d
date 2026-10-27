// [arcade] The title's Game row (src/app/arcade.ts): its pad button is free on the title, and the
// row lists gameplaySelect's modes in its order.
import { describe, expect, test } from "vitest";
import { GAME_MODE_PAD, GAME_MODES } from "../../src/app/arcade";
import { TITLE_PAD } from "../../src/app/screens";
import { PAD_BUTTONS } from "../../src/ui/nav";

describe("the title's Game row", () => {
  test("its pad button is neither an intent nor another title entry's", () => {
    const taken = new Set([...PAD_BUTTONS.map(([i]) => i), ...Object.values(TITLE_PAD).map((e) => e.button)]);
    expect(taken.has(GAME_MODE_PAD.button)).toBe(false);
  });

  test("lists the modes in gameplaySelect's order", () => {
    expect(GAME_MODES).toEqual(["fullGame", "arcade", "twoPlayerArcade"]);
  });
});
