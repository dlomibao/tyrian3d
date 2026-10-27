import { describe, expect, test } from "vitest";
import { assemblyFrame, composeFrame, entryFrames } from "../../src/viewer/spriteFrames";
import assemblies from "../../src/viewer/assemblies.json";
import { spriteModelKey, spriteModels } from "../../src/render/spriteModels";

const firstIndex = (f: { parts: { index: number }[] }) => f.parts[0].index;

describe("entryFrames", () => {
  test("an enemy's frames, as listed", () => {
    const frames = entryFrames({ model: "enemies/a", sprites: [{ sheet: "newshf.shp", size: 2, frames: [1, 3, 5] }] });
    expect(frames.map((f) => [firstIndex(f), f.width, f.height, f.label])).toEqual([[1, 24, 28, "#1"], [3, 24, 28, "#3"], [5, 24, 28, "#5"]]);
  });

  test("a player ship's five banking frames, level in the middle", () => {
    const frames = entryFrames({ model: "usp_talon", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [233], bank: { step: 2, max: 2 } }] });
    expect(frames.map(firstIndex)).toEqual([229, 231, 233, 235, 237]);
    expect(frames[2].label).toBe("level");
  });

  test("the Nort ship is its two halves side by side, 48 px wide", () => {
    const [f] = entryFrames({ model: "ships/ship-nort-ship", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [220] }] });
    expect(f).toMatchObject({ width: 48, height: 28 });
    expect(f.parts.map((p) => [p.index, p.x])).toEqual([[220, 0], [222, 24]]);
  });
});

describe("assemblyFrame", () => {
  test("places each 2x2 piece around the object's centre, which is the frame's centre", () => {
    const f = assemblyFrame({
      name: "a",
      pieces: [
        { sheet: "s", size: 2, index: 1, x: -12, y: 0 },
        { sheet: "s", size: 2, index: 3, x: 12, y: 0 },
      ],
    });
    expect([f.width, f.height]).toEqual([48, 28]);
    expect(f.parts.map((p) => [p.index, p.x, p.y])).toEqual([[1, 0, 0], [3, 24, 0]]);
  });

  test("every assembly in assemblies.json has two or more pieces, each with a model", () => {
    const models = spriteModels().grouped;
    expect(assemblies.length).toBeGreaterThan(100);
    for (const a of assemblies) {
      expect(a.pieces.length).toBeGreaterThanOrEqual(2);
      for (const p of a.pieces) expect(models.has(spriteModelKey(p.sheet, p.size, p.index)), `${a.name} ${p.sheet} ${p.index}`).toBe(true);
    }
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
    const frame = entryFrames({ model: "x", sprites: [{ sheet: "x", size: 2, frames: [1] }] })[0];
    const pic = composeFrame(() => sheet, frame)!;
    expect([pic[0], pic[12], pic[14 * 24], pic[14 * 24 + 12]]).toEqual([1, 2, 20, 21]);
    expect(pic[1 * 24]).toBe(-1); // row 1 is empty
    expect(composeFrame(() => null, frame)).toBeNull();
  });
});
