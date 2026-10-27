// [integration] The game's start-up seed (src/app/seed.ts, DECISIONS.md D37).
import { describe, expect, test } from "vitest";
import { startupSeed } from "../../src/app/seed";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";

describe("startupSeed", () => {
  test("is the clock in seconds, as opentyr.c's mt_srand(time(NULL))", () => {
    expect(startupSeed("", 1_700_000_123_456)).toBe(1_700_000_123);
    expect(startupSeed("?loot", 1_700_000_999_999)).toBe(1_700_000_999);
  });

  test("?seed=N fixes it; anything else in it is ignored", () => {
    expect(startupSeed("?seed=42", 1e12)).toBe(42);
    expect(startupSeed("?demo&seed=0", 1e12)).toBe(0);
    expect(startupSeed("?seed=abc", 1_000_000)).toBe(1000);
    expect(startupSeed("?seed=-3", 1_000_000)).toBe(1000);
  });

  test("different seeds give different mt_rand sequences, the same seed the same one", () => {
    const run = (seed: number) => (mt_srand(seed), Array.from({ length: 5 }, () => mt_rand()));
    expect(run(1_700_000_000)).not.toEqual(run(1_700_000_001));
    expect(run(7)).toEqual(run(7));
  });
});
