import { describe, expect, test } from "vitest";
import { composeFrame, entryFrames } from "../../src/viewer/spriteFrames";

describe("entryFrames", () => {
  test("an enemy's frames, as listed", () => {
    const frames = entryFrames({ model: "enemies/a", sprites: [{ sheet: "newshf.shp", size: 2, frames: [1, 3, 5] }] });
    expect(frames.map((f) => [f.index, f.width, f.height, f.label])).toEqual([[1, 24, 28, "#1"], [3, 24, 28, "#3"], [5, 24, 28, "#5"]]);
  });

  test("a player ship's five banking frames, level in the middle", () => {
    const frames = entryFrames({ model: "usp_talon", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [233], bank: { step: 2, max: 2 } }] });
    expect(frames.map((f) => f.index)).toEqual([229, 231, 233, 235, 237]);
    expect(frames[2].label).toBe("level");
  });

  test("the Nort ship is its two halves side by side, 48 px wide", () => {
    const [f] = entryFrames({ model: "ships/ship-nort-ship", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [220] }] });
    expect(f).toMatchObject({ index: 220, rightHalf: 222, width: 48, height: 28 });
  });
});

describe("composeFrame", () => {
  test("places the 2x2 tiles at index, +1, +19, +20", () => {
    // A sheet whose sprites are all one row of 12 pixels of colour index (sprite number): offset
    // table, then per sprite: 0xc0 (12 pixels), the colours, 0x0f (end).
    const count = 30;
    const body: number[] = [];
    const offsets: number[] = [];
    for (let s = 1; s <= count; s++) {
      offsets.push(count * 2 + body.length);
      body.push(0xc0, ...Array(12).fill(s), 0x0f);
    }
    const sheet = new Uint8Array([...offsets.flatMap((o) => [o & 0xff, o >> 8]), ...body]);
    const pic = composeFrame(sheet, { sheet: "x", index: 1, size: 2, width: 24, height: 28, label: "" });
    expect([pic[0], pic[12], pic[14 * 24], pic[14 * 24 + 12]]).toEqual([1, 2, 20, 21]);
    expect(pic[1 * 24]).toBe(-1); // row 1 is empty
  });
});
