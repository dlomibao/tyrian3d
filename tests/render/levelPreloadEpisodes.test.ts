// Every sprite model a level shows is one its preload lists (sim/levelSprites.ts, D54), beyond
// episode 1 (tests/render/modelSwap.test.ts plays that): with each level start freeing the last
// level's models (D236), a model left off the list is no longer in memory from an earlier level.
//
// By default TIME WAR (episode 4), whose turrets are of a shape bank the level never loads and draw
// from the sheet of their slot's last enemy (D236). PRELOAD_EPISODES=2,3,4 plays each episode with the
// test bot from its first level, level after level, as far as the bot gets (a few minutes).
import { describe, expect, test } from "vitest";
import { Route, Sprite2Router } from "../../src/render/sprite2Route";
import { spriteModels } from "../../src/render/spriteModels";
import { hasData, readData } from "../data/dataDir";

const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
const sim = async () => ({
  ...(await import("../../src/sim/game")),
  ...(await import("../../src/sim/helptext")),
  ...(await import("../../src/sim/input")),
  ...(await import("../../src/sim/mtrand")),
  ...(await import("../../src/sim/newgame")),
  ...(await import("../../src/sim/resources")),
  ...(await import("../../src/sim/state")),
  ...(await import("../../src/sim/tyrian2")),
  ...(await import("../../src/sim/draw")),
  ...(await import("../../src/sim/levelSprites")),
  ...(await import("../sim/bot")),
});

/**
 * Play episode `ep` from section `first` with the bot (one level, or on through g.nextLevel with
 * `chain`), and list each model a level shows that its preload doesn't.
 */
async function missing(ep: number, first: number, chain: boolean): Promise<{ levels: number; missing: string[] }> {
  const s = await sim();
  const { g } = s;
  const router = new Sprite2Router(spriteModels());
  s.mt_srand(1);
  g.res = s.buildResources(files, ep);
  s.loadHelpText(readData("tyrian.hdt"));
  s.newOnePlayerGame(ep);
  const out: string[] = [];
  let levels = 0;
  let main = first > 0 ? first : g.mainLevel;
  const seen = new Set<number>();
  while (main > 0 && !seen.has(main)) {
    seen.add(main);
    s.loadLevel(files, ep, main);
    g.player[0].items.weapon[0].power = 11;
    s.startLevel();
    s.clearSimInput();
    const listed = router.modelsOf(s.levelSprites());
    const told = new Set<string>();
    let r = s.tick();
    for (let t = 0; t < 30000 && !r.levelOver; t++) {
      for (const d of s.drawList.items) {
        if (d.kind !== "sprite2" || d.effect === "darken") continue;
        const x = router.route(d, null, () => false);
        if (x.route !== Route.Group && x.route !== Route.Override && x.route !== Route.Ungrouped) continue;
        if (listed.has(x.model) || told.has(x.model)) continue;
        told.add(x.model);
        out.push(`E${ep} main ${main} ${g.levelName.trim()}: ${x.model} (${d.sheet.id} frame ${d.groupIndex >= 0 ? d.groupIndex : d.index}, tick ${t})`);
      }
      s.botTick(t);
      r = s.tick();
    }
    levels++;
    if (!chain || !r.completed || g.nextLevel <= 0 || g.nextLevel === main) break;
    main = g.nextLevel;
  }
  return { levels, missing: out };
}

describe.skipIf(!hasData("tyrian4.lvl", "levels4.dat", "tyrian.hdt", "palette.dat", "tyrian.shp"))("sprite models a level shows are preloaded", () => {
  test("TIME WAR: its turrets of a bank it never loads (drawn from another sheet) are preloaded", async () => {
    const r = await missing(4, 40, false);
    expect(r.missing).toEqual([]);
  }, 600000);

  const episodes = (process.env.PRELOAD_EPISODES ?? "").split(",").filter(Boolean).map(Number);
  test.skipIf(episodes.length === 0).each(episodes)("episode %i, level after level", async (ep) => {
    const r = await missing(ep, 0, true);
    expect(r.levels).toBeGreaterThan(2);
    expect(r.missing).toEqual([]);
  }, 2400000);
});
