// Attract-mode demos (src/sim/demo.ts). The fixtures/demo-N.c.txt files were produced by
// tools/opentyrian-demo/run.sh, which plays each demo through OpenTyrian's own JE_main with
// playDemo set. The TypeScript port must replay them the same way, tick for tick.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, test, vi } from "vitest";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
// DEMO_FIXTURES: compare with traces made elsewhere, e.g. every tick (EVERY=1 FIXTURES=<dir> run.sh).
const fixtureDir = process.env.DEMO_FIXTURES ?? join(__dirname, "fixtures");
const fixture = (name: string) => readFileSync(join(fixtureDir, name), "utf8");
const haveData = hasData("demo.1", "demo.2", "demo.3", "demo.4", "demo.5", "levels1.dat", "tyrian1.lvl", "tyrian.hdt", "tyrian.shp");

/**
 * tools/opentyrian-demo/driver.c, in TypeScript: from a fresh start (each case in its own module
 * graph, as the C runs each demo in a new process), play demo `n` to its end. Without `fresh`, it
 * plays on whatever state the last run left.
 */
async function playDemo(n: number, every: number, fresh = true): Promise<string[]> {
  if (fresh) vi.resetModules();
  const { startLevel, tick } = await import("../../src/sim/game");
  const { loadHelpText } = await import("../../src/sim/helptext");
  const { clearSimInput } = await import("../../src/sim/input");
  const { mt_rand } = await import("../../src/sim/mtrand");
  const { buildResources } = await import("../../src/sim/resources");
  const { all_players_dead, FRONT_WEAPON, g, LEFT_SIDEKICK, REAR_WEAPON, RIGHT_SIDEKICK } = await import("../../src/sim/state");
  const { finishDemo, loadDemoLevel, setNextDemo } = await import("../../src/sim/demo");

  g.res = buildResources(files, 1);
  loadHelpText(readData("tyrian.hdt"));
  setNextDemo(n);
  loadDemoLevel(files);
  startLevel();
  clearSimInput();

  const p = g.player[0];
  const it = p.items;
  const out = [
    `LEVEL '${g.levelName}' episode ${g.episodeNum} file ${g.lvlFileNum} song ${g.levelSong} ship ${it.ship}` +
      ` front ${it.weapon[FRONT_WEAPON].id}/${it.weapon[FRONT_WEAPON].power} rear ${it.weapon[REAR_WEAPON].id}/${it.weapon[REAR_WEAPON].power}` +
      ` sidekicks ${it.sidekick[LEFT_SIDEKICK]} ${it.sidekick[RIGHT_SIDEKICK]} shield ${it.shield} generator ${it.generator}` +
      ` special ${it.special} armor ${p.armor}`,
  ];
  const line = (k: number) => {
    let enemies = 0;
    for (let i = 0; i < 100; i++) if (g.enemyAvail[i] !== 1) enemies++;
    return (
      `T ${k} ${g.curLoc} ${g.eventLoc} ${g.backMove} ${g.backMove2} ${g.enemyOnScreen} ${p.x} ${p.y} ${p.cash}` +
      ` ${g.enemyKilled} ${enemies} ${Number(g.endLevel)} ${g.levelEnd} ${p.armor} ${p.shield} ${Number(p.is_alive)} ${p.weapon_mode}`
    );
  };
  for (let k = 0; k < 100_000; k++) {
    const result = tick();
    if (result.levelOver) {
      out.push(line(k), `END ${k + 1} dead ${Number(all_players_dead())} R ${mt_rand()}`);
      finishDemo();
      expect(g.playDemo).toBe(false);
      return out;
    }
    if (k % every === 0) out.push(line(k));
  }
  throw new Error("the demo never ended");
}

describe("demo files", () => {
  test.skipIf(!haveData)("each header sets episode 1, a level and a loadout (beginPlayDemo's fields)", async () => {
    const { parseDemoHeader } = await import("../../src/sim/demo");
    const names = [1, 2, 3, 4, 5].map((n) => parseDemoHeader(readData(`demo.${n}`)));
    expect(names.map((h) => h.levelName.trim())).toEqual(["TYRIAN", "SAVARA", "SOH JIN", "MINES", "DELIANI"]);
    for (const h of names) {
      expect(h.episode).toBe(1);
      expect(h.superArcadeMode).toBe(0);
    }
    expect(names[0]).toMatchObject({ lvlFileNum: 9, frontWeapon: 7, rearWeapon: 29, ship: 1, shield: 6, levelSong: 18 });
  });

  test("playDemoKeys replays each mask for its wait, then reports the end", async () => {
    vi.resetModules();
    const { beginPlayDemo, DEMO_HEADER_SIZE, playDemoKeys, setNextDemo } = await import("../../src/sim/demo");
    const { g, newPlayer } = await import("../../src/sim/state");
    const { buildResources } = await import("../../src/sim/resources");
    if (!haveData) return;
    g.res = buildResources(files, 1);
    g.player = [newPlayer(), newPlayer()];
    // A made-up recording: demo.1's header, wait 2 with no keys, then right+fire for 3 ticks, then
    // up+left sidekick for 1, then the trailing wait endRecordDemo writes.
    const header = readData("demo.1").subarray(0, DEMO_HEADER_SIZE);
    const body = [0, 2, 0b1000 | 0b10000, 0, 3, 0b1 | 0b1000000, 0, 1, 0, 0];
    const file = new Uint8Array([...header, ...body]);
    setNextDemo(1);
    beginPlayDemo({ get: (n) => (n === "demo.1" ? file : files.get(n)) });
    g.player[0].x = 100;
    g.player[0].y = 100;
    const seen: string[] = [];
    while (playDemoKeys()) seen.push(`${g.player[0].x},${g.player[0].y},${g.button.map(Number).join("")}`);
    expect(seen).toEqual(["100,100,0000", "100,100,0000", "101,100,1000", "102,100,1000", "103,100,1000", "103,99,0100"]);
  });

  test("demos cycle 1 to 5 and back to 1", async () => {
    vi.resetModules();
    const { nextDemoNum, setNextDemo } = await import("../../src/sim/demo");
    expect(nextDemoNum()).toBe(1);
    setNextDemo(5);
    expect(nextDemoNum()).toBe(5);
    setNextDemo(1);
    expect(nextDemoNum()).toBe(1);
  });
});

describe.skipIf(!haveData)("demo playback matches OpenTyrian", () => {
  test.each([1, 2, 3, 4, 5])("demo.%i plays like the C does", async (n) => {
    const [header, ...expected] = fixture(`demo-${n}.c.txt`).trim().split("\n");
    const every = Number(header.split(" ")[4]);
    const actual = await playDemo(n, every);
    // Compare line by line so a failure names the first tick that differs.
    for (let i = 0; i < expected.length; i++) expect(actual[i], `line ${i + 2}`).toBe(expected[i]);
    expect(actual).toHaveLength(expected.length);
  }, 60000);

  test("demos play the same after a game and after each other as from a fresh start", async () => {
    const expected = [1, 2, 3, 4, 5].map((n) => fixture(`demo-${n}.c.txt`).trim().split("\n").slice(1));
    await playDemo(1, 10);
    // A game on hard in between, part played: its leftovers mustn't change the demos.
    const { newOnePlayerGame } = await import("../../src/sim/newgame");
    const { loadLevel } = await import("../../src/sim/tyrian2");
    const { startLevel, tick } = await import("../../src/sim/game");
    const { DIFFICULTY_HARD } = await import("../../src/sim/state");
    newOnePlayerGame(1, DIFFICULTY_HARD);
    loadLevel(files, 1, 1);
    startLevel();
    for (let k = 0; k < 500; k++) tick();
    for (const n of [3, 3, 5, 4, 2, 1, 4]) expect(await playDemo(n, 10, false), `demo.${n}`).toEqual(expected[n - 1]);
  }, 60000);
});
