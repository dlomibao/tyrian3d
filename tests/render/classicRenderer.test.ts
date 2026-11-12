// The original-look renderer for `?compare=1` (DECISIONS.md D158): a smoke test of the replay.
import { expect, test } from "vitest";
import { ClassicRenderer, PLAY_X, SCREEN_W, Surface } from "../../src/render/classic/classicRenderer";
import { Pass, type DrawList } from "../../src/sim/draw";

test("draws the list on game_screen and shows its playfield at the screen's top left", () => {
  const list: DrawList = {
    items: [
      { kind: "rect", x1: PLAY_X, y1: 0, x2: PLAY_X + 9, y2: 9, color: 0x45, pass: Pass.Background1 },
      { kind: "pixel", x: PLAY_X + 2, y: 3, color: 0x12, pass: Pass.Effects },
    ],
    palette: 0,
    filter: -99,
    brightness: 0,
    screen: null,
  };
  const screen = new Surface();
  new ClassicRenderer().render(list, screen);
  expect(screen.px[0]).toBe(0x45);
  expect(screen.px[3 * SCREEN_W + 2]).toBe(0x12);
  expect(screen.px[20 * SCREEN_W]).toBe(0);
});
