import { Input } from "./core/input";
import { startLoop } from "./core/loop";
import { loadSettings } from "./core/settings";
import { Timing } from "./core/timing";
import { World } from "./game/world";
import { loadModel, loadModelOverrides } from "./render/models";
import { View } from "./render/view";

const settings = loadSettings();
const view = new View(document.body, settings);
const debug = new URLSearchParams(location.search).get("debug");

loadModel("usp_talon")
  .then(async (model) => {
    view.setShipModel(model);
    await loadModelOverrides(view.draws, { usp_talon: model });
  })
  .catch((err) => console.error("player ship model failed to load; keeping placeholder", err));

if (debug === "sprites") {
  // Renderer test bench on real game data, without the sim. Loaded on demand so it stays out of
  // the main bundle.
  import("./debug/spriteHarness")
    .then(({ runSpriteHarness }) => runSpriteHarness(view))
    .catch((err) => console.error("sprite harness failed", err));
} else {
  const timing = new Timing(settings.logicHz);
  const world = new World(timing);
  const input = new Input();

  startLoop(timing.tickMs, {
    update: () => world.update(input.sample()),
    render: (alpha) => view.render(world, alpha),
  });

  // Expose state for debugging in the dev server.
  if (import.meta.env.DEV) Object.assign(window, { tyrian: { world, timing, settings, view } });
}
