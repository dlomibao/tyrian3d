// tools/inventory.mjs (the whole-game asset inventory, docs/roadmap/) still runs on the game's own
// data and code, and still finds what is known about level 1 (TYRIAN): its tileset and buildings,
// the boss, and the 29 scripts rebuilt hard-surface by D65 (16 assemblies, 13 single sprites).
// Static parse of episode 1 only (no bot run), so it takes a few seconds.
import { describe, expect, test } from "vitest";
// @ts-expect-error -- a plain .mjs tool without type declarations
import { buildInventory, MODULES, renderMarkdown } from "../../tools/inventory.mjs";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

/** D65's models: level 1's enemies and boss, each built by one script with `"bake": "model"`. */
const LEVEL1_FLAGSHIP = [
  "assembly-newsh2-115", "assembly-newsh2-119", "assembly-newsh2-123", "assembly-newsh2-245", "assembly-newsh2-273",
  "assembly-newsh2-279", "assembly-newsh2-3", "assembly-newsh2-53", "assembly-newsh2-87", "assembly-newsh2-9",
  "assembly-newsh4-123", "assembly-newsh4-124", "assembly-newsh4-195", "assembly-newsh4-231", "assembly-newsh4-81",
  "assembly-newshe-39", "newsh2-127", "newsh2-153", "newsh2-159", "newsh2-171", "newsh2-191", "newsh2-229",
  "newsh2-267", "newsh2-269", "newsh2-271", "newsh2-49", "newsh2-51", "newsh2-89", "newshp-13",
];

interface Unit {
  id: string;
  status: string;
  knownDamageSwap?: boolean;
}

describe.skipIf(!hasData("levels1.dat", "tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "shapesz.dat"))("asset inventory", () => {
  test("episode 1's static inventory finds level 1's known assets", async () => {
    const m: Record<string, unknown> = {};
    for (const [k, path] of Object.entries(MODULES as Record<string, string>)) m[k] = await import(/* @vite-ignore */ `../../${path}`);
    const inv = await buildInventory(m, files, { play: false, episodes: [1] });

    const tyrian = inv.levels.find((l: { id: string }) => l.id === "1.9");
    expect(tyrian.name).toBe("TYRIAN");
    expect(tyrian.tileset).toBe("shapesz");
    expect(tyrian.refs[0].section).toBe(3);
    expect(tyrian.songs).toContain(18);
    // The hard-difficulty TYRIAN is level 15 of the same file.
    expect(inv.levels.find((l: { id: string }) => l.id === "1.15").name).toBe("TYRIAN");
    // Its buildings are matched in the map (D47).
    expect(Object.keys(tyrian.tileModels)).toEqual(expect.arrayContaining(["tiles/shapesz/tyrbld-fortress", "tiles/shapesz/tyrbld-bridge"]));
    // The boss has a bar and is the D65 boss assembly.
    expect(tyrian.bossBars.length).toBeGreaterThan(0);
    expect(tyrian.bossUnits).toContain("assembly-newsh4-124");

    const units = new Map<string, Unit>(inv.units.map((u: Unit) => [u.id, u]));
    expect(tyrian.units).toEqual(expect.arrayContaining(LEVEL1_FLAGSHIP));
    // newshp-13 also covers newsh2.shp 91, a first frame the level's animation never shows: only
    // the bot run (which this test skips) can say so, so statically it is partial.
    for (const id of LEVEL1_FLAGSHIP.filter((x) => x !== "newshp-13")) expect(units.get(id)?.status, id).toBe("flagship");
    // The damaged frames D54 lists as still swapping to sprites.
    expect(units.get("assembly-newsh4-124")?.knownDamageSwap).toBe(true);
    expect(units.get("assembly-newshe-39")?.knownDamageSwap).toBe(true);

    expect(renderMarkdown(inv)).toContain("| 1.9 | TYRIAN |");
  }, 120000);
});
