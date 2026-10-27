import { describe, expect, test } from "vitest";
import { ANIM_HEIGHT, ANIM_WIDTH, animFrames, parseAnim } from "../../src/data/anim";
import { CREDITS_LINES, parseCredits } from "../../src/data/credits";
import { hasData, readData } from "./dataDir";

describe.skipIf(!hasData("tyrend.anm"))("tyrend.anm (animlib.c playAnim)", () => {
  const anim = parseAnim(readData("tyrend.anm"));

  test("header, palette and page descriptors", () => {
    expect(anim.pageCount).toBe(51);
    expect(anim.recordCount).toBe(112);
    expect([...anim.palette.subarray(0, 3)]).toEqual([0, 0, 0]);
    // The pages cover every record once.
    const covered = anim.pageDescriptors.slice(0, anim.pageCount).flatMap((p) => Array.from({ length: p.recordCount }, (_, i) => p.firstRecord + i));
    expect(covered.sort((a, b) => a - b)).toEqual(Array.from({ length: anim.recordCount }, (_, i) => i));
  });

  test("plays recordCount - 1 frames of 320x200 that change as it goes", () => {
    const sums: number[] = [];
    for (const image of animFrames(anim, 0)) {
      expect(image.length).toBe(ANIM_WIDTH * ANIM_HEIGHT);
      let sum = 0;
      for (const p of image) sum += p;
      sums.push(sum);
    }
    expect(sums.length).toBe(anim.recordCount - 1);
    expect(sums[0]).toBeGreaterThan(0);
    expect(new Set(sums).size).toBeGreaterThan(sums.length / 2);
  });
});

describe.skipIf(!hasData("tyrian.cdt"))("tyrian.cdt (JE_playCredits)", () => {
  test("131 lines, each a colour letter and text, or a blank", () => {
    const lines = parseCredits(readData("tyrian.cdt"));
    expect(lines).toHaveLength(CREDITS_LINES);
    expect(lines[0]).toBe("* CREDITS *"); // '*' - 65 is the C's colour for it
    for (const l of lines.slice(1)) expect(l === "" || l[0] === "." || (l[0] >= "A" && l[0] <= "P")).toBe(true);
    expect(lines).toContain("PProgramming,");
  });
});
