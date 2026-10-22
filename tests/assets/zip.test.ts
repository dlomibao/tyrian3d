import { existsSync, readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { filesFromZip } from "../../src/assets/files";
import { hasData, readData } from "../data/dataDir";

// Point TYRIAN_ZIP at a copy of tyrian21.zip to run this; it's skipped otherwise.
const ZIP = process.env.TYRIAN_ZIP ?? "";

describe.skipIf(!ZIP || !existsSync(ZIP))("filesFromZip", () => {
  test("extracts the game files with lowercase names", async () => {
    const files = await filesFromZip(new Uint8Array(readFileSync(ZIP)));
    expect(files.get("tyrian1.lvl")).toBeDefined();
    expect(files.get("TYRIAN.SHP")).toBeDefined();
    expect(files.get("tyrian.exe")).toBeUndefined();
    if (hasData("tyrian.hdt")) expect(files.get("tyrian.hdt")).toEqual(readData("tyrian.hdt"));
  });
});
