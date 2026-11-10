// The player ship's wear (D90) against what a level start really gives each ship (D119): the draw
// list's reference is the ship's own armour (`initial_armor`, its item's dmg) and its armour the
// level-start value (the C caps it at 28, D75), so every ship starts clean, wears light under 50%
// and heavy under 25% of its own maximum.
import { beforeAll, describe, expect, test } from "vitest";
import { ShipCondition } from "../../src/render/damage/shipDamage";
import { drawList } from "../../src/sim/draw";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

/** The wear level a fresh ship (clean, snapped) shows at `armor` of `reference`. */
function wear(armor: number, reference: number): number {
  const c = new ShipCondition();
  c.update(armor, reference, Infinity);
  return c.level;
}

describe.skipIf(!hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "levels1.dat"))("player ship wear at a level start, per ship", () => {
  let res: ReturnType<typeof buildResources>;
  beforeAll(() => {
    res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
  });

  // Every ship in episodes 1-3's item table (the 3D models: Talon 1, SuperCarrot 2, Phoenix 3,
  // Stalker 5, U-Ship 10, Silver Ship 11, Nort Ship 12; the rest share their graphics).
  for (let ship = 1; ship <= 13; ship++) {
    test(`ship ${ship}`, () => {
      mt_srand(1);
      g.res = res;
      newOnePlayerGame(1);
      loadLevel(files, 1, g.mainLevel);
      g.player[0].items.ship = ship;
      startLevel();
      clearSimInput();
      tick();

      const dmg = res.items.ships[ship].dmg;
      const s = drawList.ships?.[0];
      if (!s) throw new Error("no ship armour in the draw list");
      expect(s.reference).toBe(dmg);
      expect(s.armor).toBe(Math.min(dmg, 28));
      expect(wear(s.armor, s.reference)).toBe(0);
      // ~40% and ~20% of the ship's own maximum, as the integer armour the game holds.
      expect(wear(Math.floor(dmg * 0.4), dmg)).toBe(1);
      expect(wear(Math.floor(dmg * 0.2), dmg)).toBe(2);
      // Exactly half is still clean; one under it is light.
      if (dmg % 2 === 0) {
        expect(wear(dmg / 2, dmg)).toBe(0);
        expect(wear(dmg / 2 - 1, dmg)).toBe(1);
      }
    });
  }
});
