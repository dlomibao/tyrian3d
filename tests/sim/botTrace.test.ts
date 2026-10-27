// Cross-check against the real OpenTyrian C code: the fixtures/bot-*.c.txt files were produced by
// tools/opentyrian-bot/run.sh, which runs OpenTyrian's own JE_loadMap and JE_main (the whole level
// loop) with the bot of episode.test.ts. The TypeScript port must land on the same levels and play
// them the same way, tick for tick.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test, vi } from "vitest";
import { startLevel, tick } from "../../src/sim/game";
import { loadHelpText } from "../../src/sim/helptext";
import { clearSimInput } from "../../src/sim/input";
import { mt_srand } from "../../src/sim/mtrand";
import { newOnePlayerGame } from "../../src/sim/newgame";
import { buildResources } from "../../src/sim/resources";
import { all_players_dead, g } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";
import { botTick } from "./bot";

/** The C driver stops at JE_nextEpisode (bot_episode_end); this stands in for it here. */
class EpisodeEndError extends Error {}
vi.mock("../../src/sim/episodes", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../src/sim/episodes")>()),
  JE_nextEpisode: function* () {
    throw new EpisodeEndError();
  },
}));

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const fixture = (name: string) => readFileSync(join(__dirname, "fixtures", name), "utf8");
const haveData = hasData("levels1.dat", "levels4.dat", "tyrian1.lvl", "tyrian4.lvl", "tyrian.hdt", "tyrian.shp");

/** The driver's new one-player game on `episode`, then JE_loadMap from `section`. */
function newGameAt(episode: number, section: number): void {
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  newOnePlayerGame(episode);
  mt_srand(1);
  loadLevel(files, episode, section);
}

function route(episode: number, section: number): string {
  g.constantPlay = true;
  try {
    newGameAt(episode, section);
    return `ROUTE ${episode} ${section} -> episode ${g.episodeNum} main ${g.mainLevel} level '${g.levelName}' next ${g.nextLevel} file ${g.lvlFileNum}`;
  } catch (err) {
    if (!(err instanceof EpisodeEndError)) throw err;
    return `ROUTE ${episode} ${section} -> episode ${g.episodeNum} ends: ]Q[ in section ${g.mainLevel}`;
  } finally {
    g.constantPlay = false;
  }
}

function tickLine(k: number): string {
  let enemies = 0;
  for (let i = 0; i < 100; i++) if (g.enemyAvail[i] !== 1) enemies++;
  const p = g.player[0];
  return (
    `T ${k} ${g.curLoc} ${g.eventLoc} ${g.backMove} ${g.backMove2} ${g.enemyOnScreen} ${p.x} ${p.y} ${p.cash}` +
    ` ${g.enemyKilled} ${enemies} ${Number(g.endLevel)} ${g.levelEnd}`
  );
}

/** driver.c's `play` mode. */
function play(episode: number, section: number, ticks: number, every: number): string {
  newGameAt(episode, section);
  const p = g.player[0];
  const out = [
    `LEVEL '${g.levelName}' main ${g.mainLevel} next ${g.nextLevel} file ${g.lvlFileNum} galaga ${Number(g.galagaMode)}` +
      ` onePlayerAction ${Number(g.onePlayerAction)} superTyrian ${Number(g.superTyrian)} ship ${p.items.ship} weapon ${p.items.weapon[0].id}`,
  ];
  p.items.weapon[0].power = 11;
  startLevel();
  clearSimInput();
  for (let k = 0; ; k++) {
    if (k > 0) botTick(k - 1);
    const result = tick();
    if (result.levelOver) {
      out.push(tickLine(k), `END ${k + 1} next ${g.nextLevel} dead ${Number(all_players_dead())}`);
      break;
    }
    if (k % every === 0 || k === ticks - 1) out.push(tickLine(k));
    if (k === ticks - 1) {
      out.push(`STOP ${ticks}`);
      break;
    }
  }
  return out.join("\n");
}

describe.skipIf(!haveData)("OpenTyrian bot cross-check", () => {
  test("the item screen leaves for the same level as the C's (constantPlay picks the last map choice)", () => {
    const lines = fixture("bot-routes.c.txt").trim().split("\n");
    expect(lines.length).toBeGreaterThan(50);
    for (const line of lines) {
      const [, ep, sec] = line.split(" ").map(Number);
      expect(route(ep, sec)).toBe(line);
    }
  });

  test.each(["tyrian", "squadron", "ale"])("the bot plays %s like the C does", (name) => {
    const [header, ...expected] = fixture(`bot-${name}.c.txt`).trim().split("\n");
    const [episode, section, ticks, every] = header.split(" ").slice(2).map(Number);
    const actual = play(episode, section, ticks, every).split("\n");
    // Compare line by line so a failure names the first tick that differs.
    for (let i = 0; i < expected.length; i++) expect(actual[i], `line ${i + 2}`).toBe(expected[i]);
    expect(actual).toHaveLength(expected.length);
  }, 60000);
});
