// The original-look renderer for `?compare=1` (DECISIONS.md D158): a smoke test of the replay.
import { expect, test } from "vitest";
import { ClassicRenderer, PLAY_X, SCREEN_W, Surface } from "../../src/render/classic/classicRenderer";
import { Pass, type DrawList } from "../../src/sim/draw";
import { COMPARE_HISTORY_TICKS } from "../../src/app/compareView";

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

// The play harness's `&skip` (D188): the smoothies mix each frame with game_screen's last one, so the
// original panel must draw the ticks before the one it shows. Drawn once, iced_blur_filter averages
// with an empty screen and the frame comes out half as bright.
test("a temporal smoothie needs the frames before: COMPARE_HISTORY_TICKS of them reach the steady frame", () => {
  const list: DrawList = {
    items: [{ kind: "rect", x1: PLAY_X, y1: 0, x2: PLAY_X + 99, y2: 99, color: 0x8e, pass: Pass.Background1 }],
    palette: 0,
    filter: -99,
    brightness: 0,
    screen: { stages: [{ kind: "iced", pass: Pass.Starfield, temporal: true }], showCode: 0, playerX: 0, playerY: 0, bars: [] },
  };
  const shade = (ticks: number) => {
    const r = new ClassicRenderer();
    const screen = new Surface();
    for (let i = 0; i < ticks; i++) r.render(list, screen);
    return screen.px[10 * SCREEN_W + 10] & 0x0f;
  };
  expect(shade(1)).toBe(7); // the old harness: half the steady value
  expect(shade(COMPARE_HISTORY_TICKS)).toBe(shade(400));
  expect(shade(400)).toBe(13); // the C's (old + new) >> 1 settles one shade under the drawn 14
});
