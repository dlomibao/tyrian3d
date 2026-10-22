import { describe, expect, test } from "vitest";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput, simInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { EpisodeEndError, loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

// Plays through a whole episode with an invulnerable, always-firing ship at full weapon power,
// following the episode script's default route: every level must load and run without throwing.
// Most levels also end as completed; a few wait on objectives a sweeping bot can't meet (episode 1
// "** ALE **", episode 4 "SQUADRON"), so those are logged rather than failed. Slow (a few seconds
// per level), so it only runs when TYRIAN_EPISODE_TEST is set.
describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat") || !process.env.TYRIAN_EPISODE_TEST)("episode playthrough", () => {
  test.each([1, 2, 3, 4])("episode %i: every level loads, runs and completes", (episode) => {
    mt_srand(episode);
    g.res = buildResources(files, episode);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(episode);
    const played: string[] = [];
    for (let level = 0; level < 40; level++) {
      try {
        loadLevel(files, episode, g.mainLevel);
      } catch (err) {
        if (err instanceof EpisodeEndError) break;
        throw new Error(`episode ${episode} section ${g.mainLevel} failed to load after ${played.join(", ")}: ${err}`);
      }
      // There's no shop yet (#30): give the front weapon full power so boss levels can be won.
      g.player[0].items.weapon[0].power = 11;
      startLevel();
      clearSimInput();
      let result = tick();
      let t = 0;
      for (; t < 60000 && !result.levelOver; t++) {
        g.player[0].invulnerable_ticks = 2;
        g.player[0].armor = Math.max(g.player[0].armor, 10);
        simInput.fire = true;
        simInput.left = Math.floor(t / 50) % 2 === 0;
        simInput.right = !simInput.left;
        result = tick();
      }
      played.push(`${g.levelName.trim()}(${result.levelOver ? t : "unfinished"})`);
      if (!result.levelOver) break;
      g.mainLevel = g.nextLevel;
    }
    console.log(`episode ${episode}: ${played.join(" → ")}`);
    expect(played.length).toBeGreaterThan(3);
  }, 600000);
});
