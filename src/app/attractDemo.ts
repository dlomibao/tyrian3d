// Attract mode: the title screen, left alone, plays the next of Tyrian's five recorded demos
// (src/sim/demo.ts), and any key, button or tap goes back to the title. The level runs as in play
// (the ported JE_main at the classic tick rate, interpolated by the renderer), with the recorded
// keys in place of the player's and "INSERT COIN" over it, as the C draws it (mainint.c L3752).

import "./attractDemo.css";
import type { SoundEffects } from "../audio/sfx";
import type { MusicPlayer } from "../audio/remaster";
import { CLASSIC_TICK_MS } from "../core/timing";
import type { View } from "../render/view";
import { demoState, finishDemo, loadDemoLevel } from "../sim/demo";
import { drawList } from "../sim/draw";
import { startLevel, tick } from "../sim/game";
import { clearSimInput } from "../sim/input";
import type { TyrianFiles } from "../sim/resources";
import { g } from "../sim/state";
import { BLACK, levelFade } from "./fade";
import type { Hud } from "./hud";

/** Catch-up cap after a stall, as in a level (run.ts). */
const MAX_TICKS_PER_FRAME = 8;

export interface AttractDemoContext {
  files: TyrianFiles;
  view: View;
  music: MusicPlayer;
  sfx: SoundEffects;
  hud: Hud;
}

/**
 * Play the next demo to its end, or until the player presses something. Resolves true if the
 * player stopped it (the C's stoppedDemo).
 */
export async function playAttractDemo(c: AttractDemoContext): Promise<boolean> {
  // JE_main: start_level_first's JE_loadMap (beginPlayDemo), then the rest of the level start.
  loadDemoLevel(c.files);
  c.view.setPalettes(g.res.palettes); // JE_initEpisode may have switched the item data
  startLevel();
  c.view.draws.resetInterpolation();
  c.music.play(g.levelSong - 1);
  clearSimInput();

  const banner = document.createElement("div");
  banner.className = "attract-demo";
  banner.setAttribute("role", "status");
  const coin = document.createElement("span");
  coin.className = "attract-demo__coin";
  coin.textContent = g.miscText[7]?.trim() || "INSERT COIN"; // miscText[7]: "INSERT COIN"
  const hint = document.createElement("span");
  hint.className = "attract-demo__hint";
  hint.textContent = "Demo · press any key";
  banner.append(coin, hint);
  document.body.appendChild(banner);
  c.hud.visible = true;

  // JE_main's fade_palette(colors, 50) into the level, as run.ts does.
  levelFade().set(1, BLACK);
  void levelFade().fade(0, 50, BLACK);

  const stopped = await runDemo(c);

  // start_level (tyrian2.c L613-618): endPlayDemo(), stop_song(), fade_black(10).
  banner.remove();
  c.music.stop();
  await levelFade().fade(1, 10, BLACK);
  c.hud.visible = false;
  finishDemo();
  return stopped;
}

/** level_loop until reallyEndLevel; input stops the demo (tyrian2.c L2077-2088). */
function runDemo(c: AttractDemoContext): Promise<boolean> {
  return new Promise((resolve) => {
    let pressed = false;
    // hasInput(INPUT_NO_MOTION): keys, mouse buttons, taps and pad buttons, but not motion.
    const press = (e: Event) => {
      pressed = true;
      e.preventDefault();
    };
    const opts = { capture: true } as const;
    window.addEventListener("keydown", press, opts);
    window.addEventListener("pointerdown", press, opts);
    // Pad buttons count on the press: one held from before the demo began doesn't stop it.
    let padHeld = padButtons();

    let last = performance.now();
    let acc = 0;
    const frame = (now: number) => {
      acc += now - last;
      last = now;
      let steps = Math.floor(acc / CLASSIC_TICK_MS);
      if (steps > MAX_TICKS_PER_FRAME) {
        steps = MAX_TICKS_PER_FRAME;
        acc = 0;
      } else {
        acc -= steps * CLASSIC_TICK_MS;
      }

      const pads = padButtons();
      if (pads.some((p, i) => p && !padHeld[i])) pressed = true;
      padHeld = pads;

      for (let i = 0; i < steps && !g.reallyEndLevel; i++) {
        tick();
        c.sfx.playQueue(g.soundQueue);
        c.view.setDrawList(drawList);
        if (pressed) {
          g.reallyEndLevel = true;
          demoState.stoppedDemo = true;
        }
      }
      // A press between ticks (or with no tick due this frame) still stops it at once.
      if (pressed && !g.reallyEndLevel) {
        g.reallyEndLevel = true;
        demoState.stoppedDemo = true;
      }

      c.hud.update();
      if (g.reallyEndLevel) {
        c.view.render(null, 1);
        window.removeEventListener("keydown", press, opts);
        window.removeEventListener("pointerdown", press, opts);
        resolve(demoState.stoppedDemo);
        return;
      }
      c.view.render(null, acc / CLASSIC_TICK_MS);
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  });
}

/** Each connected pad button's pressed state, flattened. */
function padButtons(): boolean[] {
  const out: boolean[] = [];
  for (const pad of navigator.getGamepads?.() ?? []) if (pad) for (const b of pad.buttons) out.push(b.pressed);
  return out;
}
