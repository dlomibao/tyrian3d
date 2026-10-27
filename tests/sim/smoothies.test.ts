// The screen filters the sim hands the renderer: the flare specials' colour filter and brightness
// (JE_doSpecialShot, varz.c L736-819), JE_filterScreen's level events, the smoothies
// (src/sim/smoothies.ts) and the Zinglon beam, checked against the C's rules over whole flares.
import { beforeEach, describe, expect, test } from "vitest";
import { drawList, Pass, type TableSpriteDraw } from "../../src/sim/draw";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput, simInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { screenFilterStages, updateStarShowVGASpecialCode } from "../../src/sim/smoothies";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { JE_initWeaponView, JE_weaponViewFrame } from "../../src/sim/weaponSim";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const HAVE = hasData("tyrian.hdt", "tyrian.shp", "levels1.dat", "tyrian1.lvl", "palette.dat", "levels4.dat", "tyrian4.lvl");

/** items.specials indices (tyrian.hdt). */
const FLARE = 6;
const BLADE_FIELD = 7;
const SANDSTORM = 8;
const MINEFIELD = 9;
/** items.options index of the Plasma Storm sidekick. */
const PLASMA_STORM = 9;

/** A level of `episode` from script section `main` (the first by default), with `setup` applied to the loadout. */
function playLevel(episode: number, main: number | null, setup: () => void = () => {}): void {
  mt_srand(1);
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  newOnePlayerGame(episode);
  if (main !== null) g.mainLevel = main;
  loadLevel(files, episode, g.mainLevel, setup);
  setup();
  startLevel();
  clearSimInput();
}

/** One tick, invulnerable. */
function step(): void {
  g.player[0].invulnerable_ticks = 2;
  tick();
}

/** Run until the level's opening brightness fade (tyrian2.c L806-811) is over. */
function settle(): void {
  for (let i = 0; i < 60; i++) step();
  // The fade leaves filterActive on, with levelFilter and levelBrightness both -99: nothing drawn.
  expect(g.filterFade).toBe(false);
  expect([g.levelFilter, g.levelBrightness]).toEqual([-99, -99]);
  expect(drawList.filter).toBe(-99);
  expect(drawList.brightness).toBe(0);
}

/** Fire the special once (the fire button's edge), then let go. */
function trigger(): void {
  simInput.fire = true;
  step();
  simInput.fire = false;
}

describe.skipIf(!HAVE)("flare specials", () => {
  beforeEach(() => {
    g.processorType = 4;
    g.filtrationAvail = true;
    g.explosionTransparent = true;
  });

  test("Flare: filter 7 and a brightness that wanders by one a tick within -7..7, for 50 ticks", () => {
    playLevel(1, null, () => (g.player[0].items.special = FLARE));
    settle();
    trigger();
    // JE_specialComplete sets flareDuration = 50; this tick's JE_doSpecialShot already used one.
    expect(g.flareDuration).toBe(49);
    expect(g.specialWeaponFilter).toBe(7);
    expect(g.levelFilter).toBe(7);
    expect(drawList.filter).toBe(7);
    expect(Math.abs(g.levelBrightness)).toBe(1); // starts at 0, then one step
    expect(drawList.brightness).toBe(g.levelBrightness);

    let ticks = 1;
    while (g.flareDuration > 1) {
      const before = g.levelBrightness;
      step();
      ticks++;
      const change = g.levelBrightness - before;
      // varz.c L761-772: +-1 at random, but always back toward 0 past +-6.
      expect(Math.abs(change)).toBe(1);
      if (before < -6) expect(change).toBe(1);
      if (before > 6) expect(change).toBe(-1);
      expect(g.levelBrightness).toBeGreaterThanOrEqual(-7);
      expect(g.levelBrightness).toBeLessThanOrEqual(7);
      expect(g.levelFilter).toBe(7);
      expect(drawList.filter).toBe(7);
      expect(drawList.brightness).toBe(g.levelBrightness);
    }
    expect(ticks).toBe(49);

    // flareDuration == 1: the else-branch (flareStart) ends it and clears the filter.
    step();
    expect(g.flareDuration).toBe(0);
    expect(g.levelFilter).toBe(-99);
    expect(g.levelBrightness).toBe(-99);
    expect(g.filterActive).toBe(false);
    expect(drawList.filter).toBe(-99);
    expect(drawList.brightness).toBe(0);
    // shotRepeat[SHOT_SPECIAL] = linkToPlayer ? 15 : 200; the countdown runs before the flare code.
    expect(g.shotRepeat[8]).toBe(200);
  });

  test("SandStorm: filter 1, no brightness change, for 200 + 25 * power ticks", () => {
    playLevel(1, null, () => (g.player[0].items.special = SANDSTORM));
    settle();
    const power = g.player[0].items.weapon[0].power;
    trigger();
    expect(g.flareDuration).toBe(200 + 25 * power - 1);
    let ticks = 1;
    while (g.flareDuration > 1) {
      expect(drawList.filter).toBe(1);
      expect(drawList.brightness).toBe(0); // levelBrightness stays -99: not drawn
      step();
      ticks++;
    }
    expect(ticks).toBe(200 + 25 * power - 1);
    step();
    expect(drawList.filter).toBe(-99);
  });

  test("MineField: filter 3 and the Zinglon beam's two bars around the ship", () => {
    playLevel(1, null, () => {
      g.player[0].items.special = MINEFIELD;
      g.player[0].items.shield = 10;
    });
    settle();
    g.player[0].armor = 50; // MineField costs armor (pwr 104)
    trigger();
    expect(g.specialWeaponFilter).toBe(3);
    expect(drawList.filter).toBe(3);
    let beams = 0;
    for (let i = 0; i < 60; i++) {
      const z = g.zinglonDuration;
      const x = g.player[0].x;
      step();
      const bars = drawList.screen?.bars ?? [];
      if (z > 1) {
        // varz.c L822-826: temp = 25 - |zinglonDuration - 25|, two JE_barBright calls.
        const temp = 25 - Math.abs(z - 25);
        expect(bars).toEqual([x + 7 - temp, 0, x + 7 + temp, 184, x + 7 - temp - 2, 0, x + 7 + temp + 2, 184]);
        beams++;
      } else {
        expect(bars).toEqual([]);
      }
    }
    expect(beams).toBe(48); // and one on the tick that fired it: 49 of zinglonDuration's 50
  });

  test("Blade Field: a flare without a filter leaves the screen alone", () => {
    playLevel(1, null, () => (g.player[0].items.special = BLADE_FIELD));
    settle();
    trigger();
    expect(g.flareDuration).toBeGreaterThan(1);
    expect(g.specialWeaponFilter).toBe(-99);
    let shots = 0;
    while (g.flareDuration > 1) {
      expect(drawList.filter).toBe(-99);
      step();
      shots = Math.max(shots, g.shotAvail.filter((s) => s !== 0).length);
    }
    expect(shots).toBeGreaterThan(0);
  });
});

describe.skipIf(!HAVE)("level filters and smoothies", () => {
  beforeEach(() => {
    g.processorType = 4;
    g.filtrationAvail = true;
  });

  test("BUBBLES' event 44s: hue 5, then a fade through dark to hue 2", () => {
    playLevel(1, 15);
    expect(g.levelName.trim()).toBe("BUBBLES");
    const seen: string[] = [];
    for (let i = 0; i < 4000 && g.curLoc < 3000 && !g.reallyEndLevel; i++) {
      step();
      const key = `${drawList.filter}`;
      if (seen.at(-1) !== key) seen.push(key);
      if (g.curLoc >= 2000 && g.filterFade) {
        // tyrian2.c L4703-4709 then JE_filterScreen: the fade goes down to -15, swaps to the new
        // hue and comes back up to 0.
        expect(g.levelBrightness).toBeGreaterThanOrEqual(-15);
        expect(g.levelBrightness).toBeLessThanOrEqual(0);
      }
    }
    // -99 (none), then 5 from t2000's event, then 2 once the fade bottoms out.
    expect(seen.slice(-3)).toEqual(["-99", "5", "2"]);
  });

  test("ASSASSIN: lava after the ground enemies, and the headlight", () => {
    playLevel(1, 34);
    expect(g.levelName.trim()).toBe("ASSASSIN");
    // starShowVGASpecialCode is worked out before the events (tyrian2.c L974-983), so the headlight
    // that curLoc 0's event switches on shows from the second tick.
    step();
    expect(drawList.screen?.showCode).toBe(0);
    step();
    expect(drawList.screen).toMatchObject({ stages: [{ kind: "lava", pass: Pass.GroundEnemies, temporal: true }], showCode: 2 });
    expect(drawList.screen?.playerX).toBe(g.player[0].x);
    expect(drawList.screen?.playerY).toBe(g.player[0].y);
  });

  test("DESERTRUN: the blur from curLoc 2590 to 4360, reading the previous frame", () => {
    playLevel(4, 28);
    expect(g.levelName.trim()).toBe("DESERTRUN");
    let on = -1;
    let off = -1;
    for (let i = 0; i < 4000 && g.curLoc < 4500 && !g.reallyEndLevel; i++) {
      const was = drawList.screen?.stages.length ?? 0;
      step();
      const now = drawList.screen?.stages ?? [];
      if (!was && now.length) {
        on = g.curLoc;
        expect(now).toEqual([{ kind: "blur", pass: Pass.Background3Under, temporal: true }]);
      }
      if (was && !now.length) off = g.curLoc;
    }
    expect(on).toBeGreaterThanOrEqual(2590);
    expect(on).toBeLessThan(2600);
    expect(off).toBeGreaterThanOrEqual(4360);
    expect(off).toBeLessThan(4370);
  });

  test("screenFilterStages follows JE_main's order and processorType checks", () => {
    g.smoothies.fill(false);
    g.smoothie_data.fill(0);
    expect(screenFilterStages()).toEqual([]);

    g.smoothies[5 - 1] = true; // iced, early
    g.smoothies[0] = true; // lava, smoothie_data[0] == 0: before the ground enemies
    g.smoothies[2 - 1] = true;
    g.smoothie_data[2 - 1] = 7; // water hue 0x70
    g.smoothies[3 - 1] = true;
    g.smoothies[4 - 1] = true;
    expect(screenFilterStages()).toEqual([
      { kind: "iced", pass: Pass.Starfield, temporal: true },
      { kind: "lava", pass: Pass.Background2Under, temporal: false },
      { kind: "water", pass: Pass.Background2Under, temporal: false, hue: 0x70 },
      { kind: "iced", pass: Pass.Background3Under, temporal: false },
      { kind: "blur", pass: Pass.Background3Under, temporal: false },
    ]);

    g.smoothie_data[0] = 3;
    expect(screenFilterStages()[2]).toEqual({ kind: "lava", pass: Pass.GroundEnemies, temporal: false });

    // A 486 (processorType 2) has no lava or water; a 386 none at all.
    g.processorType = 2;
    expect(screenFilterStages().map((s) => s.kind)).toEqual(["iced", "iced", "blur"]);
    g.processorType = 1;
    expect(screenFilterStages()).toEqual([]);

    g.smoothies.fill(false);
    g.smoothies[9 - 1] = true;
    updateStarShowVGASpecialCode();
    expect(g.starShowVGASpecialCode).toBe(1);
    g.smoothies[6 - 1] = true;
    updateStarShowVGASpecialCode();
    expect(g.starShowVGASpecialCode).toBe(3); // both: showNormal
    g.smoothies.fill(false);
    g.smoothie_data.fill(0);
  });
});

describe.skipIf(!HAVE)("Plasma Storm", () => {
  test("its shots are option shapes 22-24, drawn blended in a level and in the item screen's simulator", () => {
    playLevel(1, null, () => (g.player[0].items.sidekick = [PLASMA_STORM, PLASMA_STORM]));
    expect(g.res.items.options[PLASMA_STORM].name.trim()).toBe("Plasma Storm   Ammo 10");
    settle();
    const plasma = () =>
      drawList.items.filter((d): d is TableSpriteDraw => d.kind === "sprite" && d.table === g.res.spriteTables[5] && d.index >= 22 && d.index <= 24);
    simInput.leftSidekick = true;
    step();
    step();
    simInput.leftSidekick = false;
    const inLevel = plasma();
    expect(inLevel.length).toBeGreaterThan(0);
    expect(inLevel.every((d) => d.effect === "blend" && d.pass === Pass.PlayerShots)).toBe(true);

    // The item screen's simulator fires the sidekicks without ammo; the C's simulate_player_shots
    // doesn't draw these (D31a).
    JE_initWeaponView();
    let shown = 0;
    for (let i = 0; i < 10; i++) {
      JE_weaponViewFrame();
      shown += plasma().length;
    }
    expect(shown).toBeGreaterThan(0);
    expect(drawList.screen).toBeNull();
  });
});
