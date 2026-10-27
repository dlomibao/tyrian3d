import { runGame } from "./app/run";
import { loadSettings } from "./core/settings";
import { loadModel } from "./render/models";
import { spriteModels } from "./render/spriteModels";
import { View } from "./render/view";
import { Backdrop, POSES } from "./ui/backdrop"; // ui-framework
import { showMessage } from "./app/screens"; // ui-framework
import { ui } from "./ui"; // ui-framework

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
  // ui-framework: without WebGL the game can't run, but say so on a real screen.
  let view: View;
  try {
    view = new View(document.body, settings);
  } catch (err) {
    console.error(err);
    ui.attachBackdrop(new Backdrop(null));
    void showMessage("WebGL needed", ["Tyrian 3D draws with WebGL, which this browser has turned off or doesn't support."], "Press Enter to try again").then(() => location.reload());
    return;
  }
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
  } else if (debug === "play") {
    // A real level played by the test bot, for weapons and effects (src/debug/playHarness.ts).
    import("./debug/playHarness")
      .then(({ runPlayHarness }) => runPlayHarness(view))
      .catch((err) => console.error("play harness failed", err));
  } else if (debug === "sprites") {
    // Renderer test bench on real game data, without the sim. Loaded on demand so it stays out of
    // the main bundle.
    import("./debug/spriteHarness")
      .then(({ runSpriteHarness }) => runSpriteHarness(view))
      .catch((err) => console.error("sprite harness failed", err));
  } else if (debug === "level") {
    // One level with a chosen loadout (src/debug/levelHarness.ts), on demand like the others.
    import("./debug/levelHarness")
      .then(({ runLevelHarness }) => runLevelHarness(view))
      .catch((err) => console.error("level harness failed", err));
  } else if (new URLSearchParams(location.search).has("destruct")) {
    // Destruct, the hidden artillery game (src/destruct/), straight away.
    ui.attachBackdrop(new Backdrop(view.renderer));
    import("./destruct/debug")
      .then(({ runDestructDebug }) => runDestructDebug(view))
      .catch((err) => console.error("destruct failed", err));
  } else {
    // ui-framework: the menus' 3D backdrop draws with the view's renderer whenever a screen is up
    // (src/ui/backdrop.ts); during levels no screen is, and the game draws.
    const backdrop = new Backdrop(view.renderer);
    ui.attachBackdrop(backdrop);
    if (import.meta.env.DEV) Object.assign(window, { tyrianUi: { ui, backdrop, poses: POSES } });

    runGame(view).catch((err) => {
      console.error(err);
      document.body.insertAdjacentHTML(
        "beforeend",
        `<pre style="position:fixed;inset:auto 1rem 1rem;color:#f88;white-space:pre-wrap">${String(err?.stack ?? err)}</pre>`,
      );
    });
  }
}
