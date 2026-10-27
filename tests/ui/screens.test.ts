// The backdrop's choice of ship model (src/ui/backdrop.ts) and the message screens' button labels
// (src/app/screens.ts).
import { describe, expect, test } from "vitest";
import { actionLabel } from "../../src/app/screens";
import { spriteModels } from "../../src/render/spriteModels";
import { buildResources } from "../../src/sim/resources";
import { shipModelForGraphic } from "../../src/ui/backdrop";
import { hasData, readData } from "../data/dataDir";

describe("actionLabel", () => {
  test("turns the callers' keyboard prompts into button labels", () => {
    expect(actionLabel("Press Enter to continue")).toBe("Continue");
    expect(actionLabel("Press Enter for the title")).toBe("Title screen");
    expect(actionLabel("Press Enter to retry from the item screen")).toBe("Retry from the item screen");
    expect(actionLabel("Next")).toBe("Next");
    expect(actionLabel("")).toBe("Continue");
  });
});

describe("shipModelForGraphic", () => {
  const models = spriteModels();

  test("finds the USP Talon by its banked sprite, and nothing for unknown sprites", () => {
    expect(shipModelForGraphic(models, 233)).toBe("usp_talon");
    expect(shipModelForGraphic(models, 9999)).toBeNull();
  });

  test.skipIf(!hasData("tyrian.shp", "tyrian.hdt", "palette.dat", "newsh6.shp"))("every story-mode ship that has a model is found from items.ships", () => {
    const res = buildResources({ get: (name) => (hasData(name) ? readData(name) : undefined) });
    const found = new Set<string>();
    for (const ship of res.items.ships.slice(1)) {
      const name = shipModelForGraphic(models, ship.shipGraphic);
      if (name) found.add(name);
    }
    // The Talon and the ship models in public/models/ships (the Nort ship's two-sprite graphic
    // isn't a banked sprite, so it's left out).
    expect(found).toContain("usp_talon");
    expect(found.size).toBeGreaterThanOrEqual(5);
  });
});
