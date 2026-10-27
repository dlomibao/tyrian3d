// The stage for the screens between levels (src/app/cinema.ts) and the episode's end
// (src/app/episodeEnd.ts): how JE_outCharGlow's glow values look, the text's colours and layout,
// and the credits' lines and roll.
import { describe, expect, test } from "vitest";
import { bankTint, glowLook, isSoftBreak, parseStoryLine } from "../../src/app/cinema";
import { creditLine, creditsRoll, splitEpisodeName } from "../../src/app/episodeEnd";

describe("glowLook", () => {
  test("follows JE_outCharGlow's glow: dark at -8, full at 0, hottest at 10, settled at 0", () => {
    // Each character's values over its 29 steps: -8 up to 10, then back down to 0.
    const values = [...Array.from({ length: 19 }, (_, i) => i - 8), ...Array.from({ length: 10 }, (_, i) => 9 - i)];
    expect(values[0]).toBe(-8);
    expect(values[18]).toBe(10);
    expect(values.at(-1)).toBe(0);
    const looks = values.map(glowLook);
    expect(looks[0].opacity).toBeGreaterThan(0);
    expect(looks[0].opacity).toBeLessThan(0.2);
    // Opacity rises to full and stays; heat rises to its peak at 10 and falls back to none.
    for (let i = 1; i < 9; i++) expect(looks[i].opacity).toBeGreaterThan(looks[i - 1].opacity);
    expect(looks.slice(8).every((l) => l.opacity === 1)).toBe(true);
    expect(looks[18].heat).toBe(1);
    expect(looks.at(-1)).toEqual({ opacity: 1, heat: 0 });
  });

  test("clamps values outside the glow's range", () => {
    expect(glowLook(-20)).toEqual({ opacity: 0, heat: 0 });
    expect(glowLook(15)).toEqual({ opacity: 1, heat: 1 });
  });
});

describe("bankTint", () => {
  test("takes the bank's shade 12 lightened a quarter, and shade 15 for the glow", () => {
    const colors = new Uint8Array(768);
    colors.set([200, 40, 0], (14 * 16 + 12) * 3);
    colors.set([255, 255, 255], (14 * 16 + 15) * 3);
    expect(bankTint(colors, 14)).toEqual({ ink: "rgb(214 94 64)", hot: "rgb(255 255 255)" });
  });
});

describe("parseStoryLine", () => {
  test("drops ~ and marks the highlighted characters, keeping each one's index in the line", () => {
    const line = parseStoryLine("a ~BUT~ b");
    expect(line.centered).toBe(false);
    expect(line.chars.map((c) => c.ch).join("")).toBe("a BUT b");
    expect(line.chars.filter((c) => c.highlight).map((c) => c.ch).join("")).toBe("BUT");
    expect(line.chars.map((c) => c.z)).toEqual([0, 1, 3, 4, 5, 7, 8]);
  });

  test("centres a line indented to the middle of the original's screen", () => {
    const line = parseStoryLine("                     MICROSOL!  ");
    expect(line.centered).toBe(true);
    expect(line.chars.map((c) => c.ch).join("")).toBe("MICROSOL!");
    expect(line.chars[0].z).toBe(21);
    expect(parseStoryLine("  slightly indented").centered).toBe(false);
    expect(parseStoryLine("                ").centered).toBe(false);
  });
});

describe("isSoftBreak", () => {
  test("joins a paragraph's wrapped lines, not short lines, blank lines or centred ones", () => {
    expect(isSoftBreak("Now that you've saved the crisis on Savara and earned the", "help of Transon Lohk, you head back")).toBe(true);
    expect(isSoftBreak("more about this new power.", "")).toBe(false);
    expect(isSoftBreak("Warning:", "Trajectory heading intercepts minefield surrounding Deliani.")).toBe(false);
    expect(isSoftBreak("Looks like a fairly substantial... oh no! And then some more", "                     MICROSOL!")).toBe(false);
    expect(isSoftBreak("The last line of the text, long enough to be wrapped", undefined)).toBe(false);
  });
});

describe("the credits", () => {
  test("each line's first character is its colour bank; '.' and empty lines are blank", () => {
    expect(creditLine("MJason Emery")).toEqual({ bank: 12, text: "Jason Emery" });
    expect(creditLine("PProgramming,")).toEqual({ bank: 15, text: "Programming," });
    expect(creditLine(".")).toBeNull();
    expect(creditLine("")).toBeNull();
  });

  test("roll a line every 60 ticks, as the C's 20-pixel lines move a pixel every 3 ticks", () => {
    expect(creditsRoll(0)).toBe(0);
    expect(creditsRoll(60)).toBe(1);
    expect(creditsRoll(30)).toBe(0.5);
    // The C's line L is at y = 220 + 20 L - floor(ticks / 3): (11 + L - roll) lines down.
    const ticks = 1234;
    const L = 15;
    const cY = 220 + 20 * L - Math.trunc(ticks / 3);
    expect(Math.abs((11 + L - creditsRoll(ticks)) * 20 - cY)).toBeLessThan(1);
  });
});

test("splitEpisodeName: the episode number becomes the title's kicker", () => {
  expect(splitEpisodeName("Episode 2: Treachery ")).toEqual({ kicker: "Episode 2", title: "Treachery" });
  expect(splitEpisodeName("Episode 3: Mission: Suicide")).toEqual({ kicker: "Episode 3", title: "Mission: Suicide" });
  expect(splitEpisodeName("Bonus")).toEqual({ title: "Bonus" });
});
