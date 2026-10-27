// [arcade] Cross-check of the arcade games against the real OpenTyrian C code: the
// fixtures/bot-{arcade-tyrian,sa-*,supertyrian}.c.txt files were produced by
// tools/opentyrian-bot/run.sh, which runs OpenTyrian's own JE_loadMap and JE_main with the test bot
// in a 1 Player Arcade, Super Arcade or Super Tyrian game (set up as newGame(),
// newSuperArcadeGame() and newSuperTyrianGame() leave it). The port, started with startNewGame
// (src/sim/arcade.ts), must play them the same way: the same pickups arming the ship, the Super
// Arcade weapons taking turns, the same lives, cash and kills, tick for tick.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test, vi } from "vitest";
import type { NewGameChoice } from "../../src/sim/arcade";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const fixture = (name: string) => readFileSync(join(__dirname, "fixtures", name), "utf8");
const haveData = hasData("levels1.dat", "levels2.dat", "tyrian1.lvl", "tyrian2.lvl", "tyrian.hdt", "tyrian.shp");

/** driver.c's game modes, as the title would start them. */
function choiceFor(mode: string, episode: number): NewGameChoice {
  const choice: NewGameChoice = { mode: "fullGame", episode, difficulty: 2 }; // DIFFICULTY_NORMAL
  if (mode === "arcade") choice.mode = "arcade";
  else if (mode.startsWith("sa")) choice.superArcade = Number(mode.slice(2));
  else if (mode === "supertyrian") choice.superTyrian = { suicide: false };
  return choice;
}

type Sim = Awaited<ReturnType<typeof loadSim>>;

/**
 * The simulation's modules, fresh: the C driver is a new process per game, and some state lives
 * on between games in the port as in the C (the ship's friction ticks, the explosion follow), so
 * each game here starts from new module state too.
 */
async function loadSim() {
  vi.resetModules();
  return {
    ...(await import("../../src/sim/arcade")),
    ...(await import("../../src/sim/game")),
    ...(await import("../../src/sim/helptext")),
    ...(await import("../../src/sim/input")),
    ...(await import("../../src/sim/mtrand")),
    ...(await import("../../src/sim/resources")),
    ...(await import("../../src/sim/state")),
    ...(await import("../../src/sim/tyrian2")),
    ...(await import("./bot")),
  };
}

function tickLines({ g, FRONT_WEAPON, REAR_WEAPON }: Sim, k: number): string[] {
  let enemies = 0;
  for (let i = 0; i < 100; i++) if (g.enemyAvail[i] !== 1) enemies++;
  const p = g.player[0];
  const it = p.items;
  return [
    `T ${k} ${g.curLoc} ${g.eventLoc} ${g.backMove} ${g.backMove2} ${g.enemyOnScreen} ${p.x} ${p.y} ${p.cash}` +
      ` ${g.enemyKilled} ${enemies} ${Number(g.endLevel)} ${g.levelEnd}`,
    `A ${k} ${it.weapon[FRONT_WEAPON].id} ${it.weapon[FRONT_WEAPON].power} ${it.weapon[REAR_WEAPON].id} ${it.weapon[REAR_WEAPON].power}` +
      ` ${it.special} ${it.sidekick[0]} ${it.sidekick[1]} ${p.lives.value} ${p.purple_balls_needed} ${g.superArcadePowerUp} ${g.power}`,
  ];
}

/** driver.c's `play` mode with a game mode. */
function play(sim: Sim, episode: number, section: number, ticks: number, every: number, mode: string): string {
  const { all_players_dead, botTick, buildResources, clearSimInput, g, loadHelpText, loadLevel, mt_srand, startLevel, startNewGame, tick } = sim;
  g.res = buildResources(files, episode);
  loadHelpText(readData("tyrian.hdt"));
  startNewGame(choiceFor(mode, episode));
  mt_srand(1);
  loadLevel(files, episode, section);

  const p = g.player[0];
  const out = [
    `LEVEL '${g.levelName}' main ${g.mainLevel} next ${g.nextLevel} file ${g.lvlFileNum} galaga ${Number(g.galagaMode)}` +
      ` onePlayerAction ${Number(g.onePlayerAction)} superTyrian ${Number(g.superTyrian)} ship ${p.items.ship} weapon ${p.items.weapon[0].id}`,
  ];
  startLevel();
  clearSimInput();
  for (let k = 0; ; k++) {
    if (k > 0) botTick(k - 1);
    const result = tick();
    if (result.levelOver) {
      out.push(...tickLines(sim, k), `END ${k + 1} next ${g.nextLevel} dead ${Number(all_players_dead())}`);
      break;
    }
    if (k % every === 0 || k === ticks - 1) out.push(...tickLines(sim, k));
    if (k === ticks - 1) {
      out.push(`STOP ${ticks}`);
      break;
    }
  }
  return out.join("\n");
}

describe.skipIf(!haveData)("OpenTyrian arcade cross-check", () => {
  test.each(["arcade-tyrian", "sa-stealth", "sa-nortshipz", "supertyrian"])("the bot plays %s like the C does", async (name) => {
    const [header, ...expected] = fixture(`bot-${name}.c.txt`).trim().split("\n");
    const [episode, section, ticks, every] = header.split(" ").slice(2, 6).map(Number);
    const mode = header.split(" ")[6];
    const actual = play(await loadSim(), episode, section, ticks, every, mode).split("\n");
    // Compare line by line so a failure names the first tick that differs.
    for (let i = 0; i < expected.length; i++) expect(actual[i], `line ${i + 2}`).toBe(expected[i]);
    expect(actual).toHaveLength(expected.length);
  }, 60000);
});
