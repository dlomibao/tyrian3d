import { Input } from "./core/input";
import { startLoop } from "./core/loop";
import { loadSettings } from "./core/settings";
import { Timing } from "./core/timing";
import { World } from "./game/world";
import { View } from "./render/view";

const settings = loadSettings();
const timing = new Timing(settings.logicHz);
const world = new World(timing);
const input = new Input();
const view = new View(document.body, settings);

startLoop(timing.tickMs, {
  update: () => world.update(input.sample()),
  render: (alpha) => view.render(world, alpha),
});
