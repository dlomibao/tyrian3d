import { test } from "vitest";
import { readData, hasData } from "../data/dataDir";
const files = { get: (name: string) => (hasData(name) ? readData(name) : undefined) };
test("probe", async () => {
  const s = {
    ...(await import("../../src/sim/game")), ...(await import("../../src/sim/helptext")), ...(await import("../../src/sim/input")),
    ...(await import("../../src/sim/mtrand")), ...(await import("../../src/sim/newgame")), ...(await import("../../src/sim/resources")),
    ...(await import("../../src/sim/state")), ...(await import("../../src/sim/tyrian2")), ...(await import("../../src/sim/draw")),
    ...(await import("../sim/bot")),
  };
  const { g } = s;
  s.mt_srand(1);
  g.res = s.buildResources(files, 1);
  s.loadHelpText(readData("tyrian.hdt"));
  s.newOnePlayerGame(1);
  s.loadLevel(files, 1, g.mainLevel);
  g.player[0].items.weapon[0].power = 11;
  s.startLevel();
  s.clearSimInput();
  let r = s.tick();
  const first = new Map<number, [number, number]>();
  for (let t = 0; t < 60000 && !r.levelOver; t++) {
    for (const it of s.drawList.items as any[]) {
      if (it.kind === "sprite2" && it.sheet?.id === "newsh4.shp" && it.groupIndex >= 152) {
        const f = first.get(it.groupIndex);
        first.set(it.groupIndex, f ? [f[0], t] : [t, t]);
      }
    }
    s.botTick(t);
    g.player[0].armor = 5;
    r = s.tick();
  }
  console.log([...first].sort((a, b) => a[0] - b[0]).map(([k, v]) => `${k}:${v[0]}-${v[1]}`).join(" "));
}, 600000);
