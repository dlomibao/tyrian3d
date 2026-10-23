import { runGame } from "./app/run";
import { loadSettings } from "./core/settings";
import { loadModel } from "./render/models";
import { spriteModels } from "./render/spriteModels";
import { View } from "./render/view";

const settings = loadSettings();
const view = new View(document.body, settings);
const debug = new URLSearchParams(location.search).get("debug");

view.draws.setSpriteModels(spriteModels(), loadModel);
loadModel("usp_talon")
  .then((model) => view.setShipModel(model))
  .catch((err) => console.error("player ship model failed to load; keeping placeholder", err));

if (debug === "models") {
  // Blender models beside their sprites, in the game's renderer.
  import("./debug/modelGallery")
    .then(({ runModelGallery }) => runModelGallery(view))
    .catch((err) => console.error("model gallery failed", err));
} else if (debug === "sprites") {
  // Renderer test bench on real game data, without the sim. Loaded on demand so it stays out of
  // the main bundle.
  import("./debug/spriteHarness")
    .then(({ runSpriteHarness }) => runSpriteHarness(view))
    .catch((err) => console.error("sprite harness failed", err));
} else {
  // Until the game starts, keep the idle scene moving behind the overlays.
  let idle = true;
  const idleFrame = () => {
    if (!idle) return;
    view.render(null, 1);
    requestAnimationFrame(idleFrame);
  };
  requestAnimationFrame(idleFrame);

  runGame(view, () => (idle = false)).catch((err) => {
    console.error(err);
    document.body.insertAdjacentHTML(
      "beforeend",
      `<pre style="position:fixed;inset:auto 1rem 1rem;color:#f88;white-space:pre-wrap">${String(err?.stack ?? err)}</pre>`,
    );
  });
}
