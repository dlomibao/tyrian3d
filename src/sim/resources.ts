// Builds the simulation's Resources from the Tyrian data files (by lowercase filename).

import {
  ENEMY_NUM,
  loadItemDat,
  mainShapeTables,
  parsePalettes,
  parseSpriteTable,
  type EnemyDat,
} from "../data";
import type { Sprite2Sheet, SpriteTable } from "./draw";
import type { Resources } from "./state";

/** Read access to the Tyrian 2.1 files. */
export interface TyrianFiles {
  /** The file's bytes, or undefined if it's missing. Names are lowercase, e.g. "tyrian.shp". */
  get(name: string): Uint8Array | undefined;
}

export function requireFile(files: TyrianFiles, name: string): Uint8Array {
  const data = files.get(name);
  if (!data) throw new Error(`missing Tyrian data file: ${name}`);
  return data;
}

/** Load everything a level needs except the level itself (JE_loadMainShapeTables, loadPals, JE_loadItemDat). */
export function buildResources(files: TyrianFiles, episode = 1): Resources {
  const tables = mainShapeTables(requireFile(files, "tyrian.shp"));
  const sheet = (i: number): Sprite2Sheet => ({ id: `tyrian.shp#${i}`, data: tables[i] });

  // Sprite tables 0-6: fonts, small fonts, tiny fonts, planets, faces, option shapes, weapon shapes.
  const spriteTables: SpriteTable[] = tables.slice(0, 7).map((bytes, i) => ({
    id: `tyrian.shp#${i}`,
    sprites: parseSpriteTable(bytes).sprites,
  }));

  const items = loadItemDat(
    episode,
    requireFile(files, "tyrian.hdt"),
    episode === 4 ? requireFile(files, "tyrian4.lvl") : undefined,
  );
  // enemyDat is indexed by enemy type; items.enemies holds types 0..ENEMY_NUM.
  const enemyDat: EnemyDat[] = items.enemies;
  if (enemyDat.length !== ENEMY_NUM + 1) throw new Error(`expected ${ENEMY_NUM + 1} enemies, got ${enemyDat.length}`);

  const compShapes = new Map<string, Sprite2Sheet>();
  const loadCompShapes = (c: string): Sprite2Sheet => {
    const name = `newsh${c.toLowerCase()}.shp`;
    let s = compShapes.get(name);
    if (!s) {
      s = { id: name, data: requireFile(files, name) };
      compShapes.set(name, s);
    }
    return s;
  };

  return {
    palettes: parsePalettes(requireFile(files, "palette.dat")),
    items,
    enemyDat,
    spriteSheet8: sheet(7),
    spriteSheet9: sheet(8),
    spriteSheet10: sheet(9),
    spriteSheet11: sheet(10),
    spriteSheet12: sheet(11),
    explosionSpriteSheet: loadCompShapes("6"),
    spriteTables,
    loadCompShapes,
  };
}
