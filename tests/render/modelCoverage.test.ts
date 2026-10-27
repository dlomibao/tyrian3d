// Every frame in the catalogue has a model (DECISIONS.md D15, D33), apart from the few listed in
// NOT_MODELLED with the reason. The catalogue (reference/models/, `npm run catalogue`) is derived
// from the game data and git-ignored, so this skips when it hasn't been generated.
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test } from "vitest";
import { spriteModelKey, spriteModels, type SpriteRef } from "../../src/render/spriteModels";

const CATALOGUE = process.env.CATALOGUE_OUT ?? "reference/models";

/** Catalogue frames deliberately left without a model (spriteModelKey -> why). They stay extruded. */
const NOT_MODELLED: Record<string, string> = {
  // A filler piece of the level 2.12 dragon, on screen for 13 ticks at the top edge as the dragon
  // enters: the whole 24x28 block is one near-black outline pixel (palette 1) in its bottom-right
  // corner, which lands on the neighbouring piece (newsh0-15). There is nothing to model.
  [spriteModelKey("newsh0.shp", 2, 13)]: "one stray outline pixel",
};

describe.skipIf(!existsSync(join(CATALOGUE, "catalogue.json")))("model coverage of the catalogue", () => {
  test("every catalogued enemy and ship frame has a model, or a reason it hasn't", () => {
    const models = JSON.parse(readFileSync(join(CATALOGUE, "catalogue.json"), "utf8")) as { name: string }[];
    const { grouped, banked } = spriteModels();
    const covered = new Set(grouped.keys());
    for (const b of banked)
      for (let n = -b.maxBank; n <= b.maxBank; n++) covered.add(spriteModelKey(b.sheetId, b.size, b.baseIndex + n * b.bankStep));
    const missing: string[] = [];
    let frames = 0;
    for (const { name } of models) {
      const { sprites } = JSON.parse(readFileSync(join(CATALOGUE, name, "sprite.json"), "utf8")) as { sprites: SpriteRef[] };
      for (const s of sprites)
        for (const f of s.frames) {
          frames++;
          const key = spriteModelKey(s.sheet, s.size, f);
          if (!covered.has(key) && !(key in NOT_MODELLED)) missing.push(`${key} (${name})`);
        }
    }
    expect(frames).toBeGreaterThan(0);
    expect(missing, "frames without a model: build one (assets/blender/README.md) or list it in NOT_MODELLED").toEqual([]);
  });

  test("NOT_MODELLED lists only frames that have no model", () => {
    const { grouped } = spriteModels();
    for (const key of Object.keys(NOT_MODELLED)) expect(grouped.has(key), key).toBe(false);
  });
});
