import { describe, expect, test } from "vitest";
import { ENEMY_NUM, readEnemyDat } from "../../src/data/enemies";
import { loadItemDat } from "../../src/data/items";
import { BinaryReader } from "../../src/data/reader";
import { hasData, readData } from "./dataDir";

test("readEnemyDat reads a 77-byte record with signed fields", () => {
  const bytes = new Uint8Array(77);
  bytes[7] = 0xfd; // xmove (s8) = -3
  bytes[13] = 0xf3; // startx (s16 LE, bytes 13-14) = 243
  bytes[15] = 0xf3; // starty (s16 LE, bytes 15-16) = -13
  bytes[16] = 0xff;
  const r = new BinaryReader(bytes);
  const e = readEnemyDat(r);
  expect(r.pos).toBe(77);
  expect(e.xMove).toBe(-3);
  expect(e.startX).toBe(0xf3);
  expect(e.startY).toBe(-13);
});

// Values below were cross-checked against OpenTyrian's own JE_loadItemDat, compiled and
// run against the same data.
describe.skipIf(!hasData("tyrian.hdt", "tyrian4.lvl"))("enemy definitions", () => {
  test("tables have ENEMY_NUM + 1 entries in both sources", () => {
    expect(loadItemDat(1, readData("tyrian.hdt")).enemies).toHaveLength(ENEMY_NUM + 1);
    expect(loadItemDat(4, readData("tyrian.hdt"), readData("tyrian4.lvl")).enemies).toHaveLength(ENEMY_NUM + 1);
  });

  test("known entry: enemy 1 in episodes 1-3", () => {
    const e = loadItemDat(1, readData("tyrian.hdt")).enemies[1]!;
    expect(e).toMatchObject({
      ani: 8,
      tur: [127, 59, 9],
      freq: [60, 0, 0],
      armor: 254,
      eSize: 1,
      explosionType: 36,
      animate: 2,
      shapeBank: 2,
      dGr: 1,
      dLevel: 40,
      eLaunchFreq: 90,
      eLaunchType: 2,
      value: 2250,
    });
    expect(e.eGraphic.slice(0, 8)).toEqual([1, 3, 5, 7, 39, 41, 43, 45]);
  });

  test("episode 4 has its own enemy table", () => {
    const e = loadItemDat(4, readData("tyrian.hdt"), readData("tyrian4.lvl")).enemies[1]!;
    expect(e).toMatchObject({
      ani: 12,
      yMove: 3,
      xAccel: 94,
      yCAccel: -8,
      startX: 150,
      startY: -13,
      startXC: 100,
      armor: 2,
      value: 5,
    });
  });
});
