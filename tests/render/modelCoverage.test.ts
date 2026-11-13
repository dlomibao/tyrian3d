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
  // Empty: newsh0.shp 13, the one-pixel filler piece of the GRYPHON (2.6) wing beside newsh0-15, has
  // been modelled since E2 batch 3 (a sunk wing-edge fragment, built by newsh0-119.py).
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
