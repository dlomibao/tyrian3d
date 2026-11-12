// "Secret Level!" (tyrian2.c L1993-2000, DECISIONS.md D155): drawn while the secret-level timer
// (displayTime) runs, at the C's place on the playfield, in the level palette's bank 15 darkened by
// 8 - flash.
import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { secretLevelBanner, SECRET_TEXT_INDEX } from "../../src/app/secretLevel";
import { parseHelpText } from "../../src/sim/helptext";
import { g } from "../../src/sim/state";
import { hasData, readData } from "../data/dataDir";

/** A palette whose index i is (i % 64, 0, 0), so the colour names the index. */
function indexPalette(): Uint8Array {
  const p = new Uint8Array(256 * 3);
  for (let i = 0; i < 256; i++) p[i * 3] = i % 64;
  return p;
}

describe("secretLevelBanner", () => {
  let saved: { displayTime: number; flash: number; miscText: string[]; res: typeof g.res };
  beforeEach(() => {
    saved = { displayTime: g.displayTime, flash: g.flash, miscText: g.miscText, res: g.res };
    g.miscText = Array.from({ length: 70 }, (_, i) => (i === SECRET_TEXT_INDEX ? "Secret Level!" : `m${i}`));
    const palettes: Uint8Array[] = [0, 1, 2, 3, 4].map(() => new Uint8Array(768));
    palettes.push(indexPalette());
    g.res = { palettes } as unknown as typeof g.res;
  });
  afterEach(() => {
    Object.assign(g, saved);
  });

  test("nothing while the timer is 0", () => {
    g.displayTime = 0;
    expect(secretLevelBanner()).toBeNull();
  });

  test("miscText[59] while the timer is above 0, at the C's (90, 10)", () => {
    g.displayTime = 150;
    g.flash = 0;
    const b = secretLevelBanner();
    expect(b).not.toBeNull();
    expect(b!.text).toBe("Secret Level!");
    expect(b!.top).toBeCloseTo(10 / 184);
    // no font table here: 11 px per character from x 90
    expect(b!.centerX).toBeCloseTo((90 + (13 * 11) / 2 - 24) / 264);
    expect(secretLevelBanner()).not.toBeNull();
    g.displayTime = 1;
    expect(secretLevelBanner()).not.toBeNull();
  });

  test("the pulse: bank 15, shade 14 darkened by 8 - flash", () => {
    g.displayTime = 100;
    const red = (flash: number) => {
      g.flash = flash;
      return Number(/rgb\((\d+)/.exec(secretLevelBanner()!.color)![1]);
    };
    // index 240 + 14 + flash - 8; the test palette's red is index % 64, rescaled 6 -> 8 bit
    const expected = (i: number) => (((i % 64) << 2) | ((i % 64) >> 4)) & 0xff;
    expect(red(0)).toBe(expected(246));
    expect(red(5)).toBe(expected(251));
    expect(red(5)).toBeGreaterThan(red(0));
  });
});

describe.skipIf(!hasData("tyrian.hdt"))("the game's text", () => {
  test("miscText[59] is 'Secret Level!'", () => {
    expect(parseHelpText(readData("tyrian.hdt")).miscText[SECRET_TEXT_INDEX]).toBe("Secret Level!");
  });
});
