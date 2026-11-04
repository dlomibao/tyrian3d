import { existsSync, readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { bankRoll, DEFAULT_FULL_ROLL, SPRITE_MODELS, spriteModelKey, spriteModels, type SpriteModelEntry } from "../../src/render/spriteModels";

const DIR = "src/render/spriteModels";

describe("sprite model entries (src/render/spriteModels/*.json)", () => {
  test("every file is loaded, is named after its model and has a .glb", () => {
    const files = readdirSync(DIR).filter((f) => f.endsWith(".json"));
    expect(SPRITE_MODELS).toHaveLength(files.length);
    for (const f of files) {
      const e = JSON.parse(readFileSync(join(DIR, f), "utf8")) as SpriteModelEntry;
      expect(e.model.split("/").pop() + ".json").toBe(f);
      expect(existsSync(join("public/models", `${e.model}.glb`)), `${e.model}.glb`).toBe(true);
      expect(e.sprites.length).toBeGreaterThan(0);
      for (const s of e.sprites) {
        expect([1, 2]).toContain(s.size);
        expect(s.frames.length).toBeGreaterThan(0);
        for (const frame of s.frames) expect(Number.isInteger(frame) && frame > 0).toBe(true);
      }
    }
  });

  test("no two models replace the same sprite", () => {
    expect(() => spriteModels()).not.toThrow();
  });
});

describe("spriteModels()", () => {
  test("indexes enemy frames and player ships' banking frames", () => {
    const m = spriteModels([
      { model: "enemies/a", sprites: [{ sheet: "newsh1.shp", size: 2, frames: [5, 7] }] },
      { model: "ship", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [233], bank: { step: 2, max: 2 } }] },
    ]);
    expect(m.grouped.get(spriteModelKey("newsh1.shp", 2, 7))).toBe("enemies/a");
    expect(m.grouped.has(spriteModelKey("newsh1.shp", 1, 7))).toBe(false);
    const deg = (v: number) => Math.round((v * 180) / Math.PI * 10) / 10;
    expect(m.banked.map((o) => ({ ...o, rolls: o.rolls.map(deg) }))).toEqual([
      { sheetId: "tyrian.shp#8", baseIndex: 233, bankStep: 2, maxBank: 2, rolls: [-35, -17.5, 0, 17.5, 35], size: 2, model: "ship" },
    ]);
  });

  // [two-player]
  test("a ship drawn in two halves (the dragonwing) is a grouped model that banks", () => {
    const m = spriteModels([{ model: "ships/dw", sprites: [{ sheet: "tyrian.shp#8", size: 2, frames: [13], bank: { step: 2, max: 2 }, group: true }] }]);
    expect([9, 11, 13, 15, 17].map((f) => m.grouped.get(spriteModelKey("tyrian.shp#8", 2, f)))).toEqual(Array(5).fill("ships/dw"));
    const full = (DEFAULT_FULL_ROLL * Math.PI) / 180;
    expect([9, 11, 13, 15, 17].map((f) => m.groupRoll.get(spriteModelKey("tyrian.shp#8", 2, f)))).toEqual([-1, -0.5, 0, 0.5, 1].map((b) => b * full));
    expect(m.banked).toEqual([]);
    // The real entry: player 2's ship, frames 13 +- 2 * bank.
    expect(spriteModels().groupRoll.get(spriteModelKey("tyrian.shp#8", 2, 13))).toBe(0);
  });

  // D92: a ship whose banking sprites draw another roll than the Talon's says so in its entry.
  test("a ship's bank.roll sets its roll per bank step, mirrored to the left", () => {
    const m = spriteModels([{ model: "u", sprites: [{ sheet: "s", size: 2, frames: [271], bank: { step: 2, max: 2, roll: [40, 55] } }] }]);
    expect(m.banked[0].rolls.map((r) => Math.round((r * 180) / Math.PI))).toEqual([-55, -40, 0, 40, 55]);
    expect(bankRoll({ max: 2 }, -1)).toBeCloseTo((-17.5 * Math.PI) / 180);
    expect(() => bankRoll({ max: 2, roll: [40] }, 1)).toThrow(/2 angles/);
    expect(m.banked[0].shifts).toBeUndefined();
  });

  test("a ship's bank.shift replaces bankShift's guess, one value per frame", () => {
    const bank = { step: 2, max: 2, roll: [17.5, 20], shift: [-0.5, -0.5, 0, 0.5, 2.5] };
    const m = spriteModels([{ model: "s", sprites: [{ sheet: "s", size: 2, frames: [195], bank }] }]);
    expect(m.banked[0].shifts).toEqual([-0.5, -0.5, 0, 0.5, 2.5]);
    expect(() => spriteModels([{ model: "s", sprites: [{ sheet: "s", size: 2, frames: [195], bank: { ...bank, shift: [1, 0, 1] } }] }])).toThrow(/5 values/);
  });

  test("every ship entry's bank.roll has one angle per bank step, rolling no less at a harder bank", () => {
    for (const e of SPRITE_MODELS) {
      for (const s of e.sprites) {
        const roll = s.bank?.roll;
        if (!roll) continue;
        expect(roll, e.model).toHaveLength(s.bank!.max);
        for (let i = 0; i < roll.length; i++) {
          expect(roll[i], e.model).toBeGreaterThan(0);
          expect(roll[i], e.model).toBeLessThan(90);
          if (i > 0) expect(roll[i], e.model).toBeGreaterThanOrEqual(roll[i - 1]);
        }
      }
    }
  });

  test("throws when two models claim a frame, including a ship's banking frames", () => {
    expect(() =>
      spriteModels([
        { model: "a", sprites: [{ sheet: "s", size: 2, frames: [5] }] },
        { model: "b", sprites: [{ sheet: "s", size: 2, frames: [5] }] },
      ]),
    ).toThrow(/b and a both replace/);
    expect(() =>
      spriteModels([
        { model: "a", sprites: [{ sheet: "s", size: 2, frames: [233], bank: { step: 2, max: 2 } }] },
        { model: "b", sprites: [{ sheet: "s", size: 2, frames: [229] }] },
      ]),
    ).toThrow();
  });
});
