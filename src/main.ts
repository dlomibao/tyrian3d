import { runGame } from "./app/run";
import { loadSettings } from "./core/settings";
import { loadModel } from "./render/models";
import { spriteModels } from "./render/spriteModels";
import { View } from "./render/view";

if (new URLSearchParams(location.search).has("viewer")) {
  // Model viewer: each Blender model beside its sprite (src/viewer/). Its own page, so the game's
  // view isn't created; loaded on demand to stay out of the main bundle.
  import("./viewer/modelViewer")
    .then(({ runModelViewer }) => runModelViewer())
    .catch((err) => console.error("model viewer failed", err));
} else {
  startGame();
}

/** The game itself: the 3D view, then the title screen, shop and levels (or a ?debug bench). */
function startGame(): void {
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
}
