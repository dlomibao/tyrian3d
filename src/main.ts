import { Input } from "./core/input";
import { startLoop } from "./core/loop";
import { loadSettings } from "./core/settings";
import { Timing } from "./core/timing";
import { World } from "./game/world";
import { loadModel } from "./render/models";
import { View } from "./render/view";

const settings = loadSettings();
const timing = new Timing(settings.logicHz);
const world = new World(timing);
const input = new Input();
const view = new View(document.body, settings);

loadModel("usp_talon")
  .then((model) => view.setShipModel(model))
  .catch((err) => console.error("player ship model failed to load; keeping placeholder", err));

startLoop(timing.tickMs, {
  update: () => world.update(input.sample()),
  render: (alpha) => view.render(world, alpha),
});

// Expose state for debugging in the dev server.
if (import.meta.env.DEV) Object.assign(window, { tyrian: { world, timing, settings, view } });
