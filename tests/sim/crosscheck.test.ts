// Opt-in cross-check against the real OpenTyrian C code (tools/sim-crosscheck/run.sh): writes one
// trace per level that the C harness then reproduces. Runs only when CROSSCHECK_OUT is set.
import { describe, test, vi } from "vitest";
import { writeFileSync } from "node:fs";
import { parseEpisodeScript } from "../../src/data";
import { hasData, readData } from "../data/dataDir";

const DIR = process.env.CROSSCHECK_OUT ?? "";
const TICKS = Number(process.env.TICKS ?? 3000);

async function trace(ep: number, mainLevel: number, constantPlay: boolean): Promise<string> {
  vi.resetModules();
  const { mt_rand, mt_srand } = await import("../../src/sim/mtrand");
  const { DIFFICULTY_NORMAL, g, newPlayer } = await import("../../src/sim/state");
  const { initLevelWorld, loadLevel } = await import("../../src/sim/tyrian2");
  const { worldTick } = await import("./worldDriver");
  g.player = [newPlayer(), newPlayer()];
  g.difficultyLevel = DIFFICULTY_NORMAL;
  g.initialDifficulty = DIFFICULTY_NORMAL;
  g.background2 = true;
  g.constantPlay = constantPlay;
  const files = { get: (n: string) => (hasData(n) ? readData(n) : undefined) };
  mt_srand(1);
  loadLevel(files, ep, mainLevel);
  initLevelWorld();
  g.player[0].x = 100;
  g.player[0].y = 180;
  g.player[0].is_alive = true;
  const out: string[] = [];
  for (let tick = 0; tick < TICKS; tick++) {
    worldTick();
    out.push(`T ${tick} ${g.curLoc} ${g.eventLoc} ${g.backPos} ${g.backPos2} ${g.backPos3} ${g.mapYPos} ${g.mapY2Pos} ${g.mapY3Pos} ${g.backMove} ${g.backMove2} ${g.backMove3} ${g.enemyOnScreen} ${g.levelBrightness} ${g.levelFilter}`);
    for (let i = 0; i < 100; i++)
      if (g.enemyAvail[i] !== 1) {
        const e = g.enemy[i];
        out.push(`E ${i} ${e.enemytype} ${e.ex} ${e.ey} ${e.exc} ${e.eyc} ${e.armorleft} ${e.enemycycle} ${e.linknum} ${g.enemyAvail[i]} ${e.filter} ${e.mapoffset}`);
      }
    for (let z = 0; z < 60; z++)
      if (!g.enemyShotAvail[z]) {
        const s = g.enemyShot[z];
        out.push(`S ${z} ${s.sx} ${s.sy} ${s.sxm} ${s.sym} ${s.sgr}`);
      }
    for (let i = 0; i < 8; i++)
      if (g.soundQueue[i]) {
        out.push(`Q ${i} ${g.soundQueue[i]}`);
        g.soundQueue[i] = 0;
      }
  }
  out.push(`R ${mt_rand()}`);
  return out.join("\n") + "\n";
}

describe.skipIf(!DIR || !hasData("levels1.dat", "tyrian1.lvl"))("cross-check traces", () => test("traces", async () => {
  const cases: string[] = [];
  for (let ep = 1; ep <= 4; ep++) {
    const script = parseEpisodeScript(readData(`levels${ep}.dat`));
    for (const sec of script.sections) {
      // Sections that reach ]L[ without a shop, end of episode, animation or jump (the C harness
      // can't run those screens).
      let ok = false;
      for (const line of sec.lines) {
        if (line.startsWith("]I") || line.startsWith("]Q") || line.startsWith("]J") || line.startsWith("]A")) break;
        if (line.startsWith("]L")) {
          ok = true;
          break;
        }
      }
      if (!ok) continue;
      try {
        writeFileSync(`${DIR}/ts_${ep}_${sec.number}.txt`, await trace(ep, sec.number, true));
        cases.push(`${ep} ${sec.number}`);
      } catch (e) {
        console.log("TS failed", ep, sec.number, String(e));
        cases.push(`${ep} ${sec.number}`);
        writeFileSync(`${DIR}/ts_${ep}_${sec.number}.txt`, `ERROR ${String(e)}\n`);
      }
    }
  }
  writeFileSync(`${DIR}/cases.txt`, cases.join("\n") + "\n");
  console.log(cases.length, "cases");
}, 600_000));
