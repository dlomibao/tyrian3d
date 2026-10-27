import { describe, expect, test } from "vitest";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";
import { botTick } from "./bot";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };

// Plays through a whole episode with an invulnerable, always-firing ship at full weapon power
// (tests/sim/bot.ts), following the episode script's route (the item screens pick the last map
// choice, as OpenTyrian's constantPlay does): every level must load, run and end as completed, and
// the episode must reach its end. Slow (a few seconds per episode), so it only runs when
// TYRIAN_EPISODE_TEST is set.
describe.skipIf(!hasData("tyrian1.lvl", "levels1.dat") || !process.env.TYRIAN_EPISODE_TEST)("episode playthrough", () => {
  test.each([1, 2, 3, 4])("episode %i: every level loads, runs and completes", (episode) => {
    mt_srand(episode);
    g.res = buildResources(files, episode);
    loadHelpText(readData("tyrian.hdt"));
    newOnePlayerGame(episode);
    const played: string[] = [];
    let ended = false;
    for (let level = 0; level < 40; level++) {
      try {
        loadLevel(files, episode, g.mainLevel);
      } catch (err) {
        throw new Error(`episode ${episode} section ${g.mainLevel} failed to load after ${played.join(", ")}: ${err}`);
      }
      // ]Q[ ends the episode and JE_loadMap goes on into the next one.
      if (g.episodeNum !== episode) {
        ended = true;
        break;
      }
      // There's no shop yet (#30): give the front weapon full power so boss levels can be won.
      g.player[0].items.weapon[0].power = 11;
      startLevel();
      clearSimInput();
      let result = tick();
      let t = 0;
      for (; t < 60000 && !result.levelOver; t++) {
        botTick(t);
        result = tick();
      }
      played.push(`${g.levelName.trim()}(${result.completed ? t : "unfinished"})`);
      if (!result.completed) break;
      g.mainLevel = g.nextLevel;
    }
    console.log(`episode ${episode}: ${played.join(" → ")}`);
    expect(played.length).toBeGreaterThan(3);
    expect(played.filter((p) => p.endsWith("(unfinished)"))).toEqual([]);
    expect(ended).toBe(true);
  }, 600000);
});
