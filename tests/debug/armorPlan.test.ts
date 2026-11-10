// `?debug=play&armor=` (src/debug/armorPlan.ts, D90, D119): without the parameter the harness holds
// nothing, so the bot's armour stays topped up and its ship is drawn clean.
import { describe, expect, test } from "vitest";
import { armorAt, parseArmorPlan } from "../../src/debug/armorPlan";

describe("parseArmorPlan", () => {
  test("absent or empty holds nothing (Number('') is 0: it used to hold the armour at 0)", () => {
    for (const p of [null, "", " ", ",", "@", "@5"]) {
      expect(parseArmorPlan(p)).toEqual([]);
      expect(armorAt(parseArmorPlan(p), 0)).toBe(-1);
      expect(armorAt(parseArmorPlan(p), 700)).toBe(-1);
    }
  });

  test("a single value holds from tick 0, including 0 itself", () => {
    expect(parseArmorPlan("4")).toEqual([{ n: 4, at: 0 }]);
    expect(armorAt(parseArmorPlan("0"), 12)).toBe(0);
    expect(armorAt(parseArmorPlan("28"), 12)).toBe(28);
  });

  test("a schedule, sorted, each value from its tick on", () => {
    const plan = parseArmorPlan("8@420,1@0,4@330");
    expect(plan).toEqual([{ n: 1, at: 0 }, { n: 4, at: 330 }, { n: 8, at: 420 }]);
    expect([0, 329, 330, 419, 420, 900].map((t) => armorAt(plan, t))).toEqual([1, 1, 4, 4, 8, 8]);
    expect(armorAt(parseArmorPlan("5@100"), 99)).toBe(-1);
  });

  test("malformed entries are dropped, the rest kept", () => {
    expect(parseArmorPlan("x,3@y,-1,,2@50")).toEqual([{ n: 3, at: 0 }, { n: 2, at: 50 }]);
  });
});
