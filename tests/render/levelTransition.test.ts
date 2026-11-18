// A level that follows another in the same session draws every model it shows as a loaded model
// (DECISIONS.md D250): the bot plays a chain of levels on one renderer, each started as run.ts does
// (preloadLevel after startLevel, which also frees what the last level loaded and this one can't
// show, D236), and every sprite drawn as a model must find its model loaded. LAVA RUN → CORE →
// LAVA EXIT (episode 4) is the QA walkthrough's chain; episode 1's first three levels are the other.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DrawListRenderer } from "../../src/render/drawListRenderer";
import { Route } from "../../src/render/sprite2Route";
import { spriteModels } from "../../src/render/spriteModels";
import { hasData, readData } from "../data/dataDir";

vi.stubGlobal("location", { search: "" });

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

/** The renderer's insides this test reads. */
interface Insides {
  router: { route(d: unknown, art: null, empty: () => boolean): { route: Route; model?: string } };
  modelPools: Map<string, { source: THREE.Object3D | null; failed: boolean }>;
}

/**
 * Play `levels` levels of episode `ep` from section `first` (0: the episode's start) with the bot on
 * one renderer, each preloaded as a level start is. Lists each model drawn without being loaded,
 * and the levels played.
 */
async function transitions(ep: number, first: number, levels: number): Promise<{ played: string[]; unloaded: string[]; loads: number }> {
  const s = await sim();
  const { g } = s;
  let loads = 0;
  const loader = async () => {
    loads++;
    const m = new THREE.Group();
    m.add(new THREE.Mesh(new THREE.BoxGeometry(), new THREE.MeshBasicMaterial()));
    return m;
  };
  const r = new DrawListRenderer();
  r.setVfxMode("original"); // the original sprite look: no flat art standing in for a model
  r.setSpriteModels(spriteModels(), loader);
  const inside = r as unknown as Insides;
  s.mt_srand(1);
  g.res = s.buildResources(files, ep);
  s.loadHelpText(readData("tyrian.hdt"));
  s.newOnePlayerGame(ep);
  const played: string[] = [];
  const unloaded: string[] = [];
  let main = first > 0 ? first : g.mainLevel;
  while (played.length < levels && main > 0) {
    s.loadLevel(files, ep, main);
    g.player[0].items.weapon[0].power = 11;
    s.startLevel();
    s.clearSimInput();
    // As levelPreload.ts: what the level can show (its sprites and damaged frames), all waited for.
    await r.preloadLevel({ sprites: s.levelSprites(), damage: s.levelDamageFrames() });
    const name = g.levelName.trim();
    played.push(name);
    const told = new Set<string>();
    let res = s.tick();
    for (let t = 0; t < 30000 && !res.levelOver; t++) {
      for (const d of s.drawList.items) {
        if (d.kind !== "sprite2" || d.effect === "darken") continue;
        const x = inside.router.route(d, null, () => false);
        if (x.route !== Route.Group && x.route !== Route.Override && x.route !== Route.Ungrouped) continue;
        const pool = inside.modelPools.get(x.model!);
        if (pool?.source || told.has(x.model!)) continue;
        told.add(x.model!);
        unloaded.push(`E${ep} ${name} (after ${played.slice(-2, -1)[0] ?? "none"}): ${x.model} ${pool ? "loading" : "not asked for"} (${d.sheet.id} frame ${d.groupIndex >= 0 ? d.groupIndex : d.index}, tick ${t})`);
      }
      s.botTick(t);
      res = s.tick();
    }
    if (!res.completed || g.nextLevel <= 0 || g.nextLevel === main) break;
    main = g.nextLevel;
  }
  return { played, unloaded, loads };
}

describe.skipIf(!hasData("tyrian1.lvl", "tyrian4.lvl", "levels1.dat", "levels4.dat", "tyrian.hdt", "palette.dat", "tyrian.shp"))("a level after a level draws its models loaded (D250)", () => {
  test("episode 4: LAVA RUN → CORE → LAVA EXIT", async () => {
    const r = await transitions(4, 4, 3);
    expect(r.played).toEqual(["LAVA RUN", "CORE", "LAVA EXIT"]);
    expect(r.unloaded).toEqual([]);
  }, 600000);

  test("episode 1: its first three levels", async () => {
    const r = await transitions(1, 0, 3);
    expect(r.played.length).toBe(3);
    expect(r.unloaded).toEqual([]);
  }, 600000);
});
