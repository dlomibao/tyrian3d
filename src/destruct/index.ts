// Destruct: Tyrian's hidden two-player artillery game (OpenTyrian src/destruct.c), as its own
// screen. openDestruct() is JE_destructGame: it loads Destruct's shapes, picture and texts, runs
// the title, mode select and rounds, and resolves when the player leaves.
//
//   sim.ts       the game: a transliteration of destruct.c (terrain, units, weapons, AI, input)
//   renderer.ts  the battlefield in 3D
//   screens.ts   title, mode select, help and pause, on the interface framework
//   hud.ts       each side's weapon, damage and points
//   input.ts     keysactive: the shared keyboard (and gamepads) for both sides

import "./destruct.css";
import * as THREE from "three";
import type { SoundEffects } from "../audio/sfx";
import type { MusicPlayer } from "../audio/remaster";
import { CLASSIC_TICK_MS } from "../core/timing";
import { decodePicture, parsePalettes } from "../data";
import { BLACK, FadeLayer } from "../app/fade";
import { parseHelpText, parseMenuText } from "../sim/helptext";
import { requireFile, type TyrianFiles } from "../sim/resources";
import { DestructHud } from "./hud";
import { DestructKeys } from "./input";
import { DestructRenderer } from "./renderer";
import { showHelp, showIntro, showModeSelect, showPaused, type DestructTexts } from "./screens";
import { de_state_t, DestructGame, MODE_5CARDWAR, MODE_NONE } from "./sim";

export { DestructGame } from "./sim";

/** JE_loadPic(VGAScreen, 11): Destruct's picture, and its palette pcxpal[10]. */
const DESTRUCT_PICTURE = 11;
const DESTRUCT_PALETTE = 21;
/**
 * One DE_RunTick: setFrameCount(1) at the Normal speed (0x4300) the game runs outside levels,
 * ~14.4 ms (~70 ticks a second), half a level's logic frame.
 */
export const DESTRUCT_TICK_MS = CLASSIC_TICK_MS / 2;
/** Catch-up cap after a stall. */
const MAX_TICKS_PER_FRAME = 8;
/** fxPlayVol (nortsong.c): DE_RunTickPlaySounds plays channel 7 at it, the others at half. */
const FX_PLAY_VOL = 4;

export interface DestructOptions {
  /** The Tyrian data (newsh~.shp, tyrian.pic, palette.dat and tyrian.hdt are read). */
  files: TyrianFiles;
  /**
   * The game's View, whose renderer (and canvas) Destruct borrows while it runs. Without one,
   * Destruct puts its own canvas over the page and removes it afterwards.
   */
  view?: { readonly renderer: THREE.WebGLRenderer } | null;
  sfx?: SoundEffects | null;
  music?: MusicPlayer | null;
  /** A song to play when Destruct closes (e.g. the title's), since its own songs would go on. */
  exitSong?: number;
}

/**
 * Play Destruct (JE_destructGame / JE_destructMain): the title, then the mode select and rounds
 * until the player leaves it with Escape. It closes whatever interface screen is up and shows its
 * own; when it resolves, no screen is up and the caller shows its own again.
 */
export async function openDestruct(opts: DestructOptions): Promise<void> {
  const { files, sfx, music } = opts;
  // JE_loadCompShapes(&destructSpriteSheet, '~'), JE_loadPic(VGAScreen, 11), the help texts.
  const sheet = requireFile(files, "newsh~.shp");
  const palette = parsePalettes(requireFile(files, "palette.dat"))[DESTRUCT_PALETTE];
  const picture = decodePicture(requireFile(files, "tyrian.pic"), DESTRUCT_PICTURE) ?? undefined;
  const hdt = requireFile(files, "tyrian.hdt");
  const menu = parseMenuText(hdt);
  const misc = parseHelpText(hdt).miscText;
  const texts: DestructTexts = {
    name: menu.specialName[7] || "DESTRUCT",
    help: menu.destructHelp,
    weaponNames: menu.weaponNames,
    modeNames: menu.destructModeName,
    paused: misc[22] || "PAUSED",
    pressF1: misc[64] ?? "",
    f10Toggles: misc[65] ?? "",
  };

  const own = opts.view?.renderer ? null : ownRenderer();
  const renderer = opts.view?.renderer ?? own!.renderer;

  const game = new DestructGame();
  const view = new DestructRenderer(renderer, palette, sheet);
  const hud = new DestructHud(sheet, palette, texts.weaponNames);
  const keys = new DestructKeys(() => game.destruct_player.map((p) => p.keys));
  const fade = new FadeLayer("level-fade destruct-fade");
  document.body.appendChild(fade.el);

  // The field draws every frame, under the menus too; a round draws its own frames as it ticks.
  let open = true;
  let ticking = false;
  let raf = 0;
  const idle = () => {
    if (!open) return;
    if (!ticking) view.render(1);
    raf = requestAnimationFrame(idle);
  };
  raf = requestAnimationFrame(idle);

  const playSounds = () => {
    // DE_RunTickPlaySounds
    const q = game.soundQueue;
    for (let i = 0; i < q.length; i++) if (q[i] !== 0) sfx?.multiSamplePlay(q[i], i, i === 7 ? FX_PLAY_VOL : FX_PLAY_VOL / 2);
  };

  /** Run DE_RunTick until it says the round is over. */
  const playRound = async (): Promise<de_state_t> => {
    ticking = true;
    hud.visible = true;
    keys.listen();
    try {
      let last = performance.now();
      let acc = DESTRUCT_TICK_MS; // the first tick at once
      for (;;) {
        const now = await nextFrame();
        acc += now - last;
        last = now;
        let steps = Math.floor(acc / DESTRUCT_TICK_MS);
        if (steps > MAX_TICKS_PER_FRAME) {
          steps = MAX_TICKS_PER_FRAME;
          acc = 0;
        } else acc -= steps * DESTRUCT_TICK_MS;

        for (let i = 0; i < steps; i++) {
          const firstTime = game.destructFirstTime;
          keys.pollPads();
          const state = game.DE_RunTick(keys);
          keys.endTick();
          playSounds();
          view.tick(game);
          hud.update(game);
          let waited = false;
          if (firstTime) {
            // fade_palette(colors, 25, 0, 255): the C fades in after drawing the first tick.
            view.render(1);
            await fade.fade(0, 25, BLACK);
            waited = true;
          }
          if (game.pauseRequested || game.helpRequested) {
            keys.stop();
            if (game.pauseRequested) {
              // JE_pauseScreen: the music at half volume until a key.
              game.pauseRequested = false;
              const volume = music?.volume ?? 0;
              if (music) music.volume = volume / 2;
              await showPaused(texts);
              if (music) music.volume = volume;
            }
            if (game.helpRequested) {
              game.helpRequested = false;
              await showHelp(texts);
            }
            keys.listen();
            waited = true;
          }
          if (state !== de_state_t.STATE_CONTINUE) return state;
          if (waited) {
            last = performance.now();
            acc = 0;
            break;
          }
        }
        view.render(acc / DESTRUCT_TICK_MS);
      }
    } finally {
      keys.stop();
      hud.visible = false;
      ticking = false;
    }
  };

  try {
    await showIntro(texts);
    // JE_destructMain
    game.startSession();
    let mode = MODE_5CARDWAR;
    for (;;) {
      const chosen = await showModeSelect(game, texts, mode, () => showHelp(texts));
      if (chosen === MODE_NONE) break; /* User is quitting */
      mode = chosen;
      let state: de_state_t;
      do {
        fade.set(1, BLACK);
        game.startRound(mode, picture);
        if (game.song >= 0) music?.play(game.song);
        view.tick(game);
        state = await playRound();
        await fade.fade(1, 25, BLACK); // fade_black(25)
      } while (state === de_state_t.STATE_RELOAD);
      fade.set(0);
    }
  } finally {
    open = false;
    cancelAnimationFrame(raf);
    keys.stop();
    hud.dispose();
    fade.el.remove();
    view.dispose();
    own?.dispose();
    if (opts.exitSong !== undefined) music?.play(opts.exitSong);
  }
}

const nextFrame = () => new Promise<number>((resolve) => requestAnimationFrame(resolve));

/** A full-window canvas of Destruct's own, when there's no View to borrow. */
function ownRenderer(): { renderer: THREE.WebGLRenderer; dispose(): void } {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.domElement.className = "destruct-canvas";
  document.body.appendChild(renderer.domElement);
  const resize = () => {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);
  };
  resize();
  window.addEventListener("resize", resize);
  return {
    renderer,
    dispose() {
      window.removeEventListener("resize", resize);
      renderer.domElement.remove();
      renderer.dispose();
    },
  };
}
