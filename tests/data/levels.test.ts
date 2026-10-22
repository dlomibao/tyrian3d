import { beforeAll, describe, expect, test } from "vitest";
import {
  EVENT_MAXIMUM,
  MAP_SIZES,
  levelTiles,
  parseLevelFile,
  parseShapes,
  SHAPES_PER_FILE,
  TILE_HEIGHT,
  TILE_WIDTH,
  type LevelFile,
} from "../../src/data/levels";
import { hasData, readData } from "./dataDir";

// lvlNum and level counts read from each header; episode 4 has one extra entry for item data.
const EPISODES = [
  { episode: 1, lvlNum: 37, levels: 18 },
  { episode: 2, lvlNum: 25, levels: 12 },
  { episode: 3, lvlNum: 25, levels: 12 },
  { episode: 4, lvlNum: 41, levels: 20 },
];

for (const { episode, lvlNum, levels } of EPISODES) {
  const name = `tyrian${episode}.lvl`;
  describe.skipIf(!hasData(name))(name, () => {
    let bytes: Uint8Array;
    let file: LevelFile;
    beforeAll(() => {
      bytes = readData(name);
      file = parseLevelFile(bytes);
    });

    test("header", () => {
      expect(file.lvlNum).toBe(lvlNum);
      expect(file.lvlPos).toHaveLength(43);
      expect(file.levels).toHaveLength(levels);
      // analyzeLevel pads the unused entries with the file length.
      expect(file.lvlPos.slice(lvlNum).every((p) => p === bytes.length)).toBe(true);
    });

    test("each level's events end at the odd offset and its map ends at the next level", () => {
      file.levels.forEach((level, i) => {
        expect(level.start).toBe(file.lvlPos[i * 2]);
        expect(level.mapStart).toBe(file.lvlPos[i * 2 + 1]);
        expect(level.end).toBe(file.lvlPos[i * 2 + 2]);
        expect(level.end).toBeLessThanOrEqual(bytes.length);
      });
      // Episodes 1-3 end with the last map; episode 4's last entry is the item data.
      if (episode < 4) expect(file.levels.at(-1)!.end).toBe(bytes.length);
      else expect(file.levels.at(-1)!.end).toBe(file.lvlPos[lvlNum - 1]);
    });

    test("fields stay inside the limits JE_loadMap relies on", () => {
      for (const level of file.levels) {
        expect(level.levelEnemy.length).toBeLessThanOrEqual(40);
        expect(level.events.length).toBeLessThan(EVENT_MAXIMUM);
        expect(level.shapeFile).toMatch(/^[WXYZ)]$/);
        level.maps.forEach((map, layer) => {
          expect(map).toHaveLength(MAP_SIZES[layer]!.width * MAP_SIZES[layer]!.height);
          for (const b of new Set(map)) {
            // Only map bytes 0..71 get a tile, and each one used names a real shape.
            expect(b).toBeLessThanOrEqual(71);
            expect(level.mapSh[layer]![b]).toBeGreaterThanOrEqual(1);
            expect(level.mapSh[layer]![b]).toBeLessThanOrEqual(SHAPES_PER_FILE);
          }
        });
      }
    });
  });
}

describe.skipIf(!hasData("tyrian1.lvl"))("tyrian1.lvl level 1 (Tyrian)", () => {
  test("known values", () => {
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[0]!;
    expect(level.mapFile).toBe("E");
    expect(level.shapeFile).toBe("Z");
    expect([level.mapX, level.mapX2, level.mapX3]).toEqual([1, 1, 1]);
    expect(level.levelEnemy.slice(0, 4)).toEqual([317, 318, 319, 320]);
    expect(level.levelEnemy).toHaveLength(21);
    expect(level.events).toHaveLength(456);
    expect(level.events[1]).toEqual({
      eventTime: 0,
      eventType: 5,
      eventDat: 8,
      eventDat2: 23,
      eventDat3: 20,
      eventDat5: 0,
      eventDat6: 0,
      eventDat4: 17,
    });
    expect(level.mapSh[0].slice(0, 3)).toEqual([361, 362, 363]);
  });
});

const SHAPE_FILES = ["shapes).dat", "shapesw.dat", "shapesx.dat", "shapesy.dat", "shapesz.dat"];

for (const name of SHAPE_FILES) {
  describe.skipIf(!hasData(name))(name, () => {
    test("600 tile records; OpenTyrian leaves 520 trailing bytes unread", () => {
      const bytes = readData(name);
      const shapes = parseShapes(bytes);
      expect(shapes).toHaveLength(SHAPES_PER_FILE);
      const tiles = shapes.filter((s) => s !== null).length;
      expect(SHAPES_PER_FILE + tiles * TILE_WIDTH * TILE_HEIGHT).toBe(bytes.length - 520);
    });
  });
}

describe.skipIf(!hasData("tyrian1.lvl", "shapesz.dat"))("levelTiles", () => {
  test("resolves every map byte of tyrian1.lvl level 1 to a tile", () => {
    const level = parseLevelFile(readData("tyrian1.lvl")).levels[0]!;
    const shapes = parseShapes(readData("shapesz.dat"));
    const tiles = levelTiles(level, shapes, 0);
    for (const b of new Set(level.maps[0])) {
      expect(tiles[b]).toHaveLength(TILE_WIDTH * TILE_HEIGHT);
    }
  });
});
