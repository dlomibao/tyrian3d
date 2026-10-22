import { describe, expect, test } from "vitest";
import { decryptString } from "../../src/data/crypt";
import { atoi, episodeLevels, parseEpisodeScript, parsePlayLevel } from "../../src/data/episodeScript";
import { readLevelPositions } from "../../src/data/levels";
import { hasData, readData } from "./dataDir";

test("decryptString inverts the original encryption", () => {
  // Encrypt front to back (the inverse of decrypt_string), then decrypt.
  const key = [204, 129, 63, 255, 71, 19, 25, 62, 1, 99];
  const plain = new TextEncoder().encode("]L[ 9999 004 TYRIAN   18 09");
  const enc = new Uint8Array(plain.length);
  plain.forEach((c, i) => (enc[i] = c ^ key[i % 10]! ^ (i > 0 ? enc[i - 1]! : 0)));
  expect(new TextDecoder().decode(decryptString(enc))).toBe("]L[ 9999 004 TYRIAN   18 09");
});

test("atoi behaves like C", () => {
  expect(atoi(" 018 09")).toBe(18);
  expect(atoi("-5x")).toBe(-5);
  expect(atoi("")).toBe(0);
  expect(atoi("$")).toBe(0);
});

test("parsePlayLevel reads JE_loadMap's fixed columns", () => {
  expect(parsePlayLevel("]L[ 9999 008 ASTEROID?02 03 $")).toEqual({
    nextLevel: 8,
    levelName: "ASTEROID?",
    levelSong: 2,
    lvlFileNum: 3,
    bonusLevelCurrent: true,
    normalBonusLevelCurrent: false,
  });
  expect(parsePlayLevel("]L[ 9999 011 BONUS    18 10$$")).toMatchObject({
    levelName: "BONUS    ",
    bonusLevelCurrent: true,
    normalBonusLevelCurrent: true,
  });
  expect(parsePlayLevel("]J 002[")).toBeNull();
});

// Line, section and `]L[` counts from decoding each file; every level in the matching
// tyrianN.lvl is referenced exactly once.
const EPISODES = [
  { episode: 1, lines: 471, sections: 42, levels: 18 },
  { episode: 2, lines: 277, sections: 24, levels: 12 },
  { episode: 3, lines: 311, sections: 25, levels: 12 },
  { episode: 4, lines: 682, sections: 51, levels: 20 },
];

for (const { episode, lines, sections, levels } of EPISODES) {
  const name = `levels${episode}.dat`;
  const lvlName = `tyrian${episode}.lvl`;
  describe.skipIf(!hasData(name, lvlName))(name, () => {
    test("decrypts to whole lines and locates every level in the level file", () => {
      const script = parseEpisodeScript(readData(name));
      expect(script.lines).toHaveLength(lines);
      expect(script.sections).toHaveLength(sections);
      expect(script.sections.every((s) => s.header.startsWith("*"))).toBe(true);

      const refs = episodeLevels(script);
      expect(refs).toHaveLength(levels);
      const { lvlNum } = readLevelPositions(readData(lvlName));
      const nums = refs.map((r) => r.lvlFileNum).sort((a, b) => a - b);
      expect(nums).toEqual(Array.from({ length: Math.floor(lvlNum / 2) }, (_, i) => i + 1));
    });
  });
}

describe.skipIf(!hasData("levels1.dat"))("levels1.dat", () => {
  test("known content", () => {
    const script = parseEpisodeScript(readData("levels1.dat"));
    expect(script.sections[0]!.header).toMatch(/^\*\*1 SECTION - LEVEL #1/);
    expect(script.sections[0]!.lines[0]).toBe("]J 002[");
    // Section 3 holds the first level, Tyrian, at lvlFileNum 9.
    expect(episodeLevels(script)[0]).toEqual({
      nextLevel: 4,
      levelName: "TYRIAN   ",
      levelSong: 18,
      lvlFileNum: 9,
      bonusLevelCurrent: false,
      normalBonusLevelCurrent: false,
      section: 3,
      line: script.sections[2]!.start + 1,
    });
  });
});
