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
import { all_players_dead, g, newPlayer } from "../../src/sim/state";
import { loadLevel } from "../../src/sim/tyrian2";
import { hasData, readData } from "../data/dataDir";
import { botTick, botTick2 } from "./bot";
import { newTwoPlayerGame } from "../../src/sim/twoplayer";
import { REAR_WEAPON } from "../../src/sim/state";

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

/**
 * The driver's new one-player game on `episode` (or play2's two-player one), then JE_loadMap from
 * `section`. With `seed` (BOT_SEED) mt_rand is seeded before the new game, as tools/inventory.mjs does.
 */
function newGameAt(episode: number, section: number, twoPlayers = false, seed?: number): void {
  // Each driver run is a fresh process: no player state (friction, mouse, sidekicks) left from the
  // case before, which JE_initPlayerData doesn't reset (in the C either).
  g.player[0] = newPlayer();
  g.player[1] = newPlayer();
  if (seed !== undefined) mt_srand(seed);
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  if (twoPlayers) newTwoPlayerGame(episode, undefined, { inputDevices: [1, 2] });
  else newOnePlayerGame(episode);
  if (seed === undefined) mt_srand(1);
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

function tickLine(k: number, twoPlayers = false): string {
  let enemies = 0;
  for (let i = 0; i < 100; i++) if (g.enemyAvail[i] !== 1) enemies++;
  const p = g.player[0];
  const line =
    `T ${k} ${g.curLoc} ${g.eventLoc} ${g.backMove} ${g.backMove2} ${g.enemyOnScreen} ${p.x} ${p.y} ${p.cash}` +
    ` ${g.enemyKilled} ${enemies} ${Number(g.endLevel)} ${g.levelEnd}`;
  if (!twoPlayers) return line;
  const q = g.player[1];
  return (
    line +
    `\nP ${k} ${q.x} ${q.y} ${q.cash} ${q.armor} ${q.lives.value} ${Number(q.is_alive)} ${q.exploding_ticks}` +
    ` ${Number(g.twoPlayerLinked)} ${Number(g.twoPlayerMode)} ${g.linkGunDirec.toFixed(4)} ${q.shield} ${p.shield}`
  );
}

/** driver.c's `play` mode (`play2` with twoPlayers; `seed` and `mortal` are BOT_SEED and BOT_MORTAL). */
function play(episode: number, section: number, ticks: number, every: number, twoPlayers = false, seed?: number, mortal = false): string {
  newGameAt(episode, section, twoPlayers, seed);
  const p = g.player[0];
  const out = [
    `LEVEL '${g.levelName}' main ${g.mainLevel} next ${g.nextLevel} file ${g.lvlFileNum} galaga ${Number(g.galagaMode)}` +
      ` onePlayerAction ${Number(g.onePlayerAction)} superTyrian ${Number(g.superTyrian)} ship ${p.items.ship} weapon ${p.items.weapon[0].id}`,
  ];
  p.items.weapon[0].power = 11;
  if (twoPlayers) {
    const q = g.player[1];
    out.push(
      `PLAYERS twoPlayerMode ${Number(g.twoPlayerMode)} difficulty ${g.difficultyLevel} input ${g.inputDevice[0]} ${g.inputDevice[1]}` +
        ` ship2 ${q.items.ship} rear2 ${q.items.weapon[REAR_WEAPON].id}`,
    );
    q.items.weapon[REAR_WEAPON].power = 3;
  }
  startLevel();
  clearSimInput();
  for (let k = 0; ; k++) {
    if (k > 0) botTick(k - 1, mortal);
    if (k > 0 && twoPlayers) botTick2(k - 1);
    const result = tick();
    if (result.levelOver) {
      out.push(tickLine(k, twoPlayers), `END ${k + 1} next ${g.nextLevel} dead ${Number(all_players_dead())}`);
      break;
    }
    if (k % every === 0 || k === ticks - 1) out.push(tickLine(k, twoPlayers));
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

  // ale-seed1041 is tools/inventory.mjs's ALE run, which crashed the port at tick 2815: the ship
  // touches an enemy whose galaga-doubled value (30720) reads past weaponPort (D75). squadron-mortal
  // is SQUADRON played to its only end, the ship out of lives (see tests/sim/galaga.test.ts).
  test.each(["tyrian", "squadron", "ale", "two-players", "ale-seed1041", "squadron-mortal"])("the bot plays %s like the C does", (name) => {
    const [header, ...expected] = fixture(`bot-${name}.c.txt`).trim().split("\n");
    const words = header.split(" ");
    const [episode, section, ticks, every] = words.slice(2, 6).map(Number);
    const seed = words.find((w) => w.startsWith("seed="))?.slice(5);
    const actual = play(episode, section, ticks, every, words[1] === "play2", seed === undefined ? undefined : Number(seed), words.includes("mortal")).split("\n");
    // Compare line by line so a failure names the first tick that differs.
    for (let i = 0; i < expected.length; i++) expect(actual[i], `line ${i + 2}`).toBe(expected[i]);
    expect(actual).toHaveLength(expected.length);
  }, 60000);
});
