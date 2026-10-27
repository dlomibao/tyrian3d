// Level bench: the real sim and renderer on one level with a chosen loadout, no title or item
// screen. Open the dev server with `?debug=level`. Loaded by dynamic import, so it's not in the main
// bundle. Keys and pads drive the ship as in the game (src/app/controls.ts).
//
//   ?debug=level                   episode 1's first level
//   &episode=E                     episode 1-4
//   &main=N                        mainLevel: the episode script's section to load (default: the first)
//   &front=ID:POWER &rear=ID:POWER weapon ports (item ids) and power 1-11
//   &special=N                     special weapon (items.specials index), e.g. 6 = Flare
//   &sidekick=L,R                  sidekicks (items.options index), e.g. 9,9 = Plasma Storm
//   &ship=N &shield=N &generator=N
//   &skip=N                        run N ticks headless first (invulnerable), to reach a level event
//   &god=1                         stay invulnerable
//
// In the console, `tyrianLevel` holds g and simInput; `tyrianLevel.hold.fire = true` keeps a
// button pressed (for scripted checks).

import { loadDevFiles } from "../assets/files";
import { startLoop } from "../core/loop";
import { CLASSIC_TICK_MS } from "../core/timing";
import { Controls } from "../app/controls";
import { drawList } from "../sim/draw";
import { startLevel, tick } from "../sim/game";
import { loadHelpText } from "../sim/helptext";
import { clearSimInput, simInput, type SimInput } from "../sim/input";
import { mt_srand } from "../sim/mtrand";
import { newOnePlayerGame } from "../sim/newgame";
import { buildResources, requireFile } from "../sim/resources";
import { g } from "../sim/state";
import { loadLevel } from "../sim/tyrian2";
import type { View } from "../render/view";

export async function runLevelHarness(view: View): Promise<void> {
  const params = new URLSearchParams(location.search);
  const files = await loadDevFiles();
  if (!files) {
    document.body.insertAdjacentHTML("beforeend", "<pre style='color:#f88'>?debug=level needs the dev server with the game data.</pre>");
    return;
  }
  const num = (key: string, fallback: number) => (params.has(key) ? Number(params.get(key)) : fallback);
  const episode = num("episode", 1);

  mt_srand(1);
  g.res = buildResources(files, episode);
  loadHelpText(requireFile(files, "tyrian.hdt"));
  view.setPalettes(g.res.palettes);
  newOnePlayerGame(episode);
  if (params.has("main")) g.mainLevel = num("main", g.mainLevel);

  const loadout = () => {
    const items = g.player[0].items;
    const port = (key: string, slot: number) => {
      const v = params.get(key);
      if (!v) return;
      const [id, power] = v.split(":").map(Number);
      items.weapon[slot] = { id, power: power || 1 };
    };
    port("front", 0);
    port("rear", 1);
    if (params.has("special")) items.special = num("special", 0);
    if (params.has("sidekick")) {
      const [l, r] = (params.get("sidekick") ?? "").split(",").map(Number);
      items.sidekick[0] = l || 0;
      items.sidekick[1] = r ?? l ?? 0;
    }
    if (params.has("ship")) items.ship = num("ship", items.ship);
    if (params.has("shield")) items.shield = num("shield", items.shield);
    if (params.has("generator")) items.generator = num("generator", items.generator);
  };
  loadout();
  loadLevel(files, g.episodeNum, g.mainLevel, loadout);
  loadout();
  startLevel();
  clearSimInput();

  const god = params.get("god") === "1";
  for (let i = num("skip", 0); i > 0 && !g.reallyEndLevel; i--) {
    g.player[0].invulnerable_ticks = 2;
    tick();
  }
  view.setDrawList(drawList);
  view.draws.resetInterpolation();

  const controls = new Controls(() => view.gamePixelsPerScreenPixel);
  controls.active = true;
  const hold: Partial<SimInput> = {};
  if (import.meta.env.DEV) Object.assign(window, { tyrianLevel: { g, simInput, hold, view } });

  startLoop(CLASSIC_TICK_MS, {
    update: () => {
      if (g.reallyEndLevel) return;
      controls.sample();
      Object.assign(simInput, hold);
      if (god) g.player[0].invulnerable_ticks = 2;
      tick();
      view.setDrawList(drawList);
    },
    render: (alpha) => view.render(null, alpha),
  });
}
