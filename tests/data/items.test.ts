import { describe, expect, test } from "vitest";
import {
  hdtItemDatOffset,
  loadItemDat,
  OPTION_NUM,
  PORT_NUM,
  POWER_NUM,
  SHIELD_NUM,
  SHIP_NUM,
  SPECIAL_NUM,
  WEAP_NUM,
} from "../../src/data/items";
import { readLevelPositions } from "../../src/data/levels";
import { hasData, readData } from "./dataDir";

// Known values below were cross-checked against OpenTyrian's own JE_loadItemDat, compiled and
// run against the same data. Names keep the trailing spaces stored in the file.
describe.skipIf(!hasData("tyrian.hdt"))("tyrian.hdt item data (episodes 1-3)", () => {
  test("header and table sizes; the block runs exactly to the end of the file", () => {
    const hdt = readData("tyrian.hdt");
    expect(hdtItemDatOffset(hdt)).toBe(16465);
    const items = loadItemDat(1, hdt);
    expect(items.counts).toEqual([780, 42, 6, 13, 30, 10, 850]);
    expect(items.weapons).toHaveLength(WEAP_NUM + 1);
    expect(items.weaponPorts).toHaveLength(PORT_NUM + 1);
    expect(items.specials).toHaveLength(SPECIAL_NUM + 1);
    expect(items.powerSys).toHaveLength(POWER_NUM + 1);
    expect(items.ships).toHaveLength(SHIP_NUM + 1);
    expect(items.options).toHaveLength(OPTION_NUM + 1);
    expect(items.shields).toHaveLength(SHIELD_NUM + 1);
    expect(items.end).toBe(hdt.length);
  });

  test("known items", () => {
    const items = loadItemDat(1, readData("tyrian.hdt"));
    expect(items.ships.map((s) => s.name.trimEnd())).toEqual([
      "None",
      "USP Talon   Light Fighter",
      "SuperCarrot",
      "Gencore Phoenix",
      "Gencore Maelstrom",
      "MicroCorp Stalker",
      "MicroCorp Stalker-B",
      "Prototype Stalker-C",
      "Stalker",
      "USP Fang    Light Fighter",
      "U-Ship",
      "Silver Ship",
      "Nort Ship",
      "The Stalker 21.126",
    ]);
    expect(items.ships[1]).toMatchObject({ shipGraphic: 233, itemGraphic: 277, ani: 2, dmg: 10, cost: 6000, bigShipGraphic: 32 });

    const pulse = items.weaponPorts[1]!;
    expect(pulse.name).toBe("Pulse-Cannon                  ");
    expect(pulse).toMatchObject({ opNum: 1, cost: 500, itemGraphic: 7, powerUse: 30 });
    expect(pulse.op[0]).toEqual([155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165]);

    // Pulse-Cannon at power 1: one shot, 2 damage, 10 px/frame upward, every 3 frames.
    expect(items.weapons[155]).toMatchObject({
      shotRepeat: 3,
      multi: 1,
      max: 1,
      sound: 25,
      attack: [2, 0, 0, 0, 0, 0, 0, 0],
      del: [255, 0, 0, 0, 0, 0, 0, 0],
      sy: [10, 0, 0, 0, 0, 0, 0, 0],
      sg: [59, 0, 0, 0, 0, 0, 0, 0],
    });

    expect(items.shields[1]).toMatchObject({ name: "Structural Integrity Field    ", tpwr: 5, mpwr: 2, cost: 100 });
    expect(items.powerSys[1]).toMatchObject({ name: "Standard MR-9                 ", power: 10, cost: 500 });
    expect(items.options[1]).toMatchObject({
      name: "Single Shot Option            ",
      option: 2,
      opSpd: 3,
      ani: 4,
      wPort: 16,
      wpNum: 1,
      stop: true,
    });
    expect(items.specials[1]).toMatchObject({ name: "Repulsor                      ", pwr: 1, sType: 2 });
  });
});

describe.skipIf(!hasData("tyrian.hdt", "tyrian4.lvl"))("tyrian4.lvl item data (episode 4)", () => {
  test("sits at lvlPos[lvlNum - 1] and runs exactly to the end of the file", () => {
    const lvl = readData("tyrian4.lvl");
    const { lvlNum, lvlPos } = readLevelPositions(lvl);
    expect(lvlPos[lvlNum - 1]).toBe(662814);
    const items = loadItemDat(4, readData("tyrian.hdt"), lvl);
    expect(items.counts).toEqual([780, 42, 6, 13, 30, 10, 850]);
    expect(items.end).toBe(lvl.length);
    expect(items.ships[13]!.name.trimEnd()).toBe("The Stalker 21.126");
  });

  test("episode 4 requires its level file", () => {
    expect(() => loadItemDat(4, readData("tyrian.hdt"))).toThrow();
  });
});
