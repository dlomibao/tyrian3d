// D254: the level's fade-in leaves the playfield to the sim's levelBrightness, as the original's does.
import { describe, expect, it } from "vitest";
import { holeClipPath } from "../../src/app/fade";

describe("level fade hole (D254)", () => {
  it("covers the window but for the playfield's quad, even-odd", () => {
    const quad = [{ x: 100, y: 50 }, { x: 900, y: 50 }, { x: 950.04, y: 700 }, { x: 60, y: 700 }];
    expect(holeClipPath(1920, 1080, quad)).toBe('path(evenodd, "M0 0 H1920 V1080 H0 Z M100 50 L900 50 L950 700 L60 700 Z")');
  });
});
