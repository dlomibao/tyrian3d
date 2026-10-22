import { describe, expect, test } from "vitest";
import { parseSoundBank, SFX_COUNT, VOICE_COUNT } from "../../src/audio/sfx";
import { hasData, readData } from "../data/dataDir";

describe.skipIf(!hasData("tyrian.snd", "voices.snd"))("sound banks", () => {
  test("hold the counts loadSndFile asserts", () => {
    expect(parseSoundBank(readData("tyrian.snd"), false)).toHaveLength(SFX_COUNT);
    expect(parseSoundBank(readData("voices.snd"), true)).toHaveLength(VOICE_COUNT);
  });

  test("samples are normalised signed 8-bit", () => {
    for (const s of parseSoundBank(readData("tyrian.snd"), false)) {
      expect(s.length).toBeGreaterThan(0);
      for (const v of s) expect(v >= -1 && v < 1).toBe(true);
    }
  });
});
