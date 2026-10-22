import { describe, expect, test } from "vitest";
import { drawList } from "../../src/sim/draw";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput, simInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

describe.skipIf(!hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "levels1.dat"))("JE_main level loop", () => {
  test("plays episode 1 level 1 with fire held: shots fly, enemies die, nothing throws", () => {
    mt_srand(1);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1);
    loadLevel(files, 1, g.mainLevel);
    expect(g.levelName.trim()).toBe("TYRIAN");
    startLevel();

    clearSimInput();
    let maxShots = 0;
    let maxDraws = 0;
    for (let t = 0; t < 4000 && !g.reallyEndLevel; t++) {
      // Sweep left and right while firing.
      simInput.fire = true;
      simInput.left = Math.floor(t / 60) % 2 === 0;
      simInput.right = !simInput.left;
      const r = tick();
      if (r.gameOver) g.reallyEndLevel = true;
      maxShots = Math.max(maxShots, g.shotAvail.filter((s) => s !== 0).length);
      maxDraws = Math.max(maxDraws, drawList.items.length);
    }

    expect(maxShots).toBeGreaterThan(0);
    expect(maxDraws).toBeGreaterThan(100);
    expect(g.enemyKilled).toBeGreaterThan(0);
    expect(g.player[0].cash).toBeGreaterThan(10000);
    expect(g.curLoc).toBeGreaterThan(500);
  });
});

describe.skipIf(!hasData("tyrian1.lvl", "tyrian.hdt", "tyrian.shp", "levels1.dat"))("finishing a level", () => {
  test("level 1 ends as completed when the ship survives (invulnerable for the test)", () => {
    mt_srand(2);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1);
    loadLevel(files, 1, g.mainLevel);
    startLevel();
    clearSimInput();

    let ticks = 0;
    let result = tick();
    for (; ticks < 40000 && !result.levelOver; ticks++) {
      g.player[0].invulnerable_ticks = 2;
      simInput.fire = true;
      simInput.left = Math.floor(ticks / 50) % 2 === 0;
      simInput.right = !simInput.left;
      result = tick();
    }

    expect(result.levelOver).toBe(true);
    expect(result.completed).toBe(true);
    expect(g.nextLevel).toBeGreaterThan(0);
    console.log(`level 1 finished after ${ticks} ticks (${(ticks / 34.78).toFixed(0)} s); killed ${g.enemyKilled}/${g.totalEnemy}; nextLevel ${g.nextLevel}`);
  });

  test("an idle ship gets destroyed and the level ends as not completed", () => {
    mt_srand(3);
    g.res = buildResources(files, 1);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(1);
    loadLevel(files, 1, g.mainLevel);
    startLevel();
    clearSimInput();

    let result = tick();
    let gameOverAt = -1;
    for (let t = 0; t < 20000 && !result.levelOver; t++) {
      result = tick();
      if (result.gameOver && gameOverAt < 0) gameOverAt = t;
      // The host ends the level on any input once game over is showing.
      if (result.gameOver && t > gameOverAt + 30) g.reallyEndLevel = true;
    }
    expect(gameOverAt).toBeGreaterThan(0);
    expect(g.player[0].is_alive).toBe(false);
  });
});
