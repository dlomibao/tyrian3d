import { describe, expect, test } from "vitest";
import { buildResources } from "../../src/sim/resources";
import { hasData, readData } from "../data/dataDir";

describe.skipIf(!hasData("tyrian.shp", "tyrian.hdt", "palette.dat", "newsh6.shp"))("buildResources", () => {
  test("loads episode 1 resources", () => {
    const res = buildResources({ get: (name) => (hasData(name) ? readData(name) : undefined) });
    expect(res.palettes).toHaveLength(23);
    expect(res.items.ships[1].name.trim()).toBe("USP Talon   Light Fighter");
    expect(res.spriteTables).toHaveLength(7);
    expect(res.spriteSheet9.id).toBe("tyrian.shp#8");
    expect(res.explosionSpriteSheet.id).toBe("newsh6.shp");
    expect(res.loadCompShapes("1")).toBe(res.loadCompShapes("1"));
  });
});
