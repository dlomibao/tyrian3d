// The end of an episode (`]Q[` in levelsN.dat): the hint, JE_nextEpisode, and JE_loadMap going on
// into the next episode's first section with what the C carries over (tyrian2.c L2547-2659,
// mainint.c L954-1001, episodes.c L247-298).
import { beforeEach, describe, expect, test } from "vitest";
import { loadItemDat } from "../../src/data";
import { JE_itemScreenNonInteractive } from "../../src/sim/game_menu";
import { loadHelpText } from "../../src/sim/helptext";
import { JE_totalScore } from "../../src/sim/mainint";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { copyPlayerItems } from "../../src/sim/player";
import { buildResources, type TyrianFiles } from "../../src/sim/resources";
import { DIFFICULTY_HARD, g } from "../../src/sim/state";
import { loadLevelAsync, type LoadMapPause } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";

const cache = new Map<string, Uint8Array | undefined>();
const files: TyrianFiles = {
  get(name) {
    if (!cache.has(name)) cache.set(name, hasData(name) ? readData(name) : undefined);
    return cache.get(name);
  },
};

const NEEDED = [1, 2, 3, 4].flatMap((n) => [`levels${n}.dat`, `tyrian${n}.lvl`]).concat(["tyrian.hdt", "tyrian.shp", "palette.dat"]);

/** A new game on `episode`, with a loadout that isn't the starting one, so carrying it over shows. */
function newGame(episode: number): void {
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  newOnePlayerGame(episode, DIFFICULTY_HARD);
  g.constantPlay = false;
  const p = g.player[0];
  p.cash = 123456;
  p.items.ship = 3;
  p.items.weapon[0].id = 4;
  p.items.weapon[0].power = 5;
  p.items.weapon[1].id = 11;
  p.items.sidekick[0] = 6;
  p.last_items = copyPlayerItems(p.items);
  g.cubeMax = 2;
}

/** JE_loadMap from `section` with the C's unattended item screen, recording every pause. */
async function loadFrom(episode: number, section: number): Promise<{ loaded: boolean; pauses: LoadMapPause[]; texts: string[][] }> {
  const pauses: LoadMapPause[] = [];
  const texts: string[][] = [];
  const loaded = await loadLevelAsync(
    files,
    episode,
    section,
    async () => {
      pauses.push("itemScreen");
      JE_itemScreenNonInteractive();
    },
    async (pause) => {
      pauses.push(pause);
      if (pause === "displayText") texts.push([...g.levelWarningText]);
    },
  );
  return { loaded, pauses, texts };
}

describe.skipIf(!hasData(...NEEDED))("the end of an episode (]Q[, JE_nextEpisode)", () => {
  beforeEach(() => {
    g.constantPlay = false;
  });

  test("episode 1's end shows a hint, then goes on to episode 2's first level with the same ship, items and cash", async () => {
    newGame(1);
    g.secretHint = 2;
    mt_srand(7);
    const hintRow = (mt_rand() % 3) + 1; // temp = secretHint + (mt_rand() % 3) * 3
    mt_srand(7);
    const items = copyPlayerItems(g.player[0].items);
    const score = JE_totalScore(g.player[0]);

    // Section 26, END GAME: ]F[ ]M 031[ ]P 005[ ]Q[.
    const { loaded, pauses, texts } = await loadFrom(1, 26);

    expect(loaded).toBe(true);
    // JE_displayText, JE_highScoreCheck (first time through episode 1), the next episode's title,
    // then episode 2's script from section 1: its item screen, then the level.
    expect(pauses).toEqual(["displayText", "highScoreCheck", "nextEpisode", "itemScreen"]);
    expect(texts[0][0]).toBe(`${g.miscText[37]} ${score}`);
    expect(texts[0][1]).toBe("");
    expect(texts[0][2]).toBe(`Secret Hint 1-${hintRow}-2:`);

    expect(g.episodeNum).toBe(2);
    expect(g.jumpBackToEpisode1).toBe(false);
    expect(g.gameHasRepeated).toBe(false);
    expect(g.lastLevelName).toBe("Completed");
    expect(g.saveLevel).toBe(1); // JE_nextEpisode's FIRST_LEVEL; the loaded level came from section 1's item screen
    expect(g.levelName.trim()).toBe("TORM");
    // JE_initEpisode reloaded the item data for episode 2.
    expect(g.res.items).toEqual(loadItemDat(2, readData("tyrian.hdt")));
    // What carries over: the player's items, cash and difficulty, and the data cubes.
    expect(g.player[0].items).toEqual(items);
    expect(g.player[0].cash).toBe(123456);
    expect(g.initialDifficulty).toBe(DIFFICULTY_HARD);
    expect(g.cubeMax).toBe(2);
  });

  test("episode 3's end plays tyrend.anm (]A[) before its text, then goes on to episode 4", async () => {
    newGame(3);
    // Section 13, End of game: ]A[, the story (]W), ]F[ ]P 005[ ]Q[.
    const { loaded, pauses } = await loadFrom(3, 13);
    expect(loaded).toBe(true);
    expect(pauses).toEqual(["anim", "displayText", "highScoreCheck", "nextEpisode", "itemScreen"]);
    expect(g.episodeNum).toBe(4);
    expect(g.res.items).toEqual(loadItemDat(4, readData("tyrian.hdt"), readData("tyrian4.lvl")));
    expect(g.player[0].cash).toBe(123456);
  });

  test("after the last episode come the credits and the Super Arcade code, then episode 1 again", async () => {
    // Episode 4's ]Q[ uses one mt_rand for the hint, then JE_nextEpisode one for the SuperCarrot
    // (1 in 6). Find a seed for each outcome.
    const carrotAt = (seed: number) => {
      mt_srand(seed);
      mt_rand();
      return mt_rand() % 6 === 0;
    };
    const seeds = Array.from({ length: 200 }, (_, i) => i + 1);
    for (const carrot of [false, true]) {
      newGame(4);
      const items = copyPlayerItems(g.player[0].items);
      mt_srand(seeds.find((s) => carrotAt(s) === carrot)!);

      // Section 43, Ending: ]M 008[ ]P 005[ ]Q[ (then ]J 001[, which isn't reached).
      const { loaded, pauses } = await loadFrom(4, 43);

      expect(loaded).toBe(true);
      // No high score check at the end of episode 4 (EPISODE_AVAILABLE); credits after episode 2.
      expect(pauses).toEqual(["displayText", "credits", "nextEpisode", "superArcadeCode", "itemScreen"]);
      expect(g.episodeNum).toBe(1);
      expect(g.jumpBackToEpisode1).toBe(true);
      expect(g.gameHasRepeated).toBe(true);
      expect(g.trentWin).toBe(false); // SANextShip[SA_NONE] is ship 3, not the Nort-Ship Z
      expect(g.levelName.trim()).toBe("TYRIAN");
      expect(g.player[0].cash).toBe(123456);
      if (carrot) {
        expect(g.player[0].items.ship).toBe(2); // SuperCarrot
        expect(g.player[0].items.weapon.map((w) => [w.id, w.power])).toEqual([[23, 1], [24, 1]]);
        expect(g.player[0].last_items).toEqual(g.player[0].items);
      } else {
        expect(g.player[0].items).toEqual(items);
      }
    }
  });

  test("a Super Tyrian game goes back to the title after the last episode", async () => {
    newGame(4);
    g.superTyrian = true;
    const { loaded, pauses } = await loadFrom(4, 43);
    expect(loaded).toBe(false);
    expect(g.mainLevel).toBe(0);
    expect(g.superArcadeMode).toBe(1); // superArcadeMode = 1: SANextShip[1] is SA_ENGAGE
    expect(pauses).toEqual(["displayText", "credits", "nextEpisode", "superArcadeCode"]);
    g.superTyrian = false;
  });

  test("with constantPlay the screens that wait for a key are skipped, as in the C", async () => {
    newGame(1);
    g.constantPlay = true;
    const { loaded, pauses } = await loadFrom(1, 26);
    g.constantPlay = false;
    expect(loaded).toBe(true);
    expect(pauses).toEqual(["itemScreen"]);
    expect(g.episodeNum).toBe(2);
  });
});
