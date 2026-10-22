// The game flow around the simulation: get the data, title, new game, then play levels in order.
// Each level runs the ported JE_main loop at the classic tick rate and hands each tick's draw
// list to the renderer, which interpolates between ticks (DECISIONS.md D2).

import { filesFromZip, loadDevFiles, type FileMap } from "../assets/files";
import { loadStoredZip } from "../assets/store";
import { SoundEffects } from "../audio/sfx";
import { Music } from "../audio/music";
import { CLASSIC_TICK_MS } from "../core/timing";
import { drawList } from "../sim/draw";
import { startLevel, tick } from "../sim/game";
import { loadHelpText } from "../sim/helptext";
import { clearSimInput } from "../sim/input";
import { JE_endLevelAni } from "../sim/mainint";
import { newOnePlayerGame } from "../sim/newgame";
import { copyPlayerItems } from "../sim/player";
import { buildResources, requireFile } from "../sim/resources";
import { g, SA_NONE, type PlayerItems } from "../sim/state";
import { EpisodeEndError, loadLevelAsync } from "../sim/tyrian2";
import type { View } from "../render/view";
import { Controls } from "./controls";
import { Hud } from "./hud";
import { askForData, showMessage, showStatus, showTitle } from "./screens";
import { runItemScreen } from "./shop";

/** OpenTyrian song numbers (0-based, as passed to play_song). */
const SONG_TITLE = 29;
const SONG_LEVEL_END = 9;
const SONG_GAME_OVER = 10;

/** Catch-up cap: after a stall, run at most this many ticks before rendering again. */
const MAX_TICKS_PER_FRAME = 8;

async function getFiles(): Promise<FileMap> {
  const dev = await loadDevFiles();
  if (dev) return dev;
  const stored = await loadStoredZip();
  if (stored) {
    try {
      return await filesFromZip(stored);
    } catch {
      // A bad cached copy: ask again.
    }
  }
  return askForData();
}

/**
 * What JE_saveGame(11, "LAST LEVEL") keeps (after JE_loadMap, so after the item screen) so a
 * failed level can be retried with JE_loadGame(11). The saved level is saveLevel: the section
 * JE_loadMap started from (or the last `]s[`), so a retry goes back through the item screen.
 */
interface LevelBackup {
  items: PlayerItems;
  last_items: PlayerItems;
  cash: number;
  level: number;
  difficultyLevel: number;
  cubes: number;
}

function saveLastLevel(): LevelBackup {
  const p = g.player[0];
  return {
    items: copyPlayerItems(p.items),
    last_items: copyPlayerItems(p.last_items),
    cash: p.cash,
    level: g.saveLevel,
    difficultyLevel: g.difficultyLevel,
    cubes: g.lastCubeMax,
  };
}

function loadLastLevel(b: LevelBackup): void {
  const p = g.player[0];
  g.superTyrian = false;
  g.onePlayerAction = false;
  g.extraGame = false;
  g.galagaMode = false;
  g.difficultyLevel = b.difficultyLevel;
  p.items = copyPlayerItems(b.items);
  p.last_items = copyPlayerItems(b.last_items);
  p.cash = b.cash;
  g.mainLevel = b.level;
  g.cubeMax = b.cubes;
  g.lastCubeMax = b.cubes;
}

/** `onPlay` fires once the first level starts, so the caller can stop its idle rendering. */
export async function runGame(view: View, onPlay: () => void = () => {}): Promise<void> {
  const files = await getFiles();
  const loading = showStatus("Loading…");
  g.res = buildResources(files, 1);
  loadHelpText(requireFile(files, "tyrian.hdt"));
  view.setPalettes(g.res.palettes);

  const audioContext = new AudioContext();
  const music = new Music(requireFile(files, "music.mus"), { context: audioContext });
  const sfx = new SoundEffects(requireFile(files, "tyrian.snd"), requireFile(files, "voices.snd"), audioContext);
  const controls = new Controls(() => view.gamePixelsPerScreenPixel);
  const hud = new Hud();
  loading();

  if (import.meta.env.DEV) Object.assign(window, { tyrian: { g, view, music, sfx } });

  for (;;) {
    music.play(SONG_TITLE);
    await showTitle();

    newOnePlayerGame(1);
    onPlay();
    let backup: LevelBackup | null = null;

    // start_level / start_level_first (tyrian2.c L586-905): JE_loadMap with the item screen at
    // each `]I[`, the backup save, the level, then where to go next.
    for (;;) {
      let loaded: boolean;
      try {
        loaded = await loadLevelAsync(files, g.episodeNum, g.mainLevel, () => runItemScreen({ files, sfx, music }));
      } catch (err) {
        if (!(err instanceof EpisodeEndError)) throw err;
        music.play(SONG_LEVEL_END);
        await showMessage("Episode complete", [`Final score ${g.player[0].cash}`], "Press Enter for the title");
        break;
      }
      if (!loaded) break; // quit from the item screen: back to the title
      if (!g.doNotSaveBackup) backup = saveLastLevel(); /*Save backup game*/
      startLevel();
      view.draws.resetInterpolation();
      music.play(g.levelSong - 1);
      clearSimInput();
      controls.clear();
      hud.visible = true;

      controls.active = true;
      const outcome = await playLevel(view, controls, sfx, music, hud);
      controls.active = false;
      controls.release();
      hud.visible = false;

      g.difficultyLevel = g.oldDifficultyLevel; /*Return difficulty to normal*/

      if (outcome === "completed") {
        g.mainLevel = g.nextLevel;
        JE_endLevelAni(); // its state changes; the summary is this screen
        music.play(SONG_LEVEL_END);
        await showMessage("Level complete", [
          `${g.levelName.trim()}`,
          `Score ${g.player[0].cash}`,
          `Enemies destroyed ${g.enemyKilled} of ${g.totalEnemy}`,
        ]);
        if (g.mainLevel === 0) break; // end of the episode
      } else {
        music.play(SONG_GAME_OVER);
        await showMessage("Game over", ["Your ship was destroyed."], "Press Enter to retry from the item screen");
        if (backup) loadLastLevel(backup); // JE_loadGame(11)
        if (g.doNotSaveBackup) {
          g.superTyrian = false;
          g.onePlayerAction = false;
          g.player[0].items.super_arcade_mode = SA_NONE;
        }
        if (g.bonusLevelCurrent && !g.playerEndLevel) g.mainLevel = g.nextLevel;
      }
      g.doNotSaveBackup = false;
    }
  }
}

type Outcome = "completed" | "died";

function playLevel(view: View, controls: Controls, sfx: SoundEffects, music: Music, hud: Hud): Promise<Outcome> {
  return new Promise((resolve) => {
    let last = performance.now();
    let acc = 0;
    let paused = false;
    let pauseEl: (() => void) | null = null;

    const frame = (now: number) => {
      if (controls.pauseRequested) {
        controls.pauseRequested = false;
        paused = !paused;
        if (paused) {
          controls.release();
          controls.active = false;
          pauseEl = showStatus("Paused · press Esc or P to continue");
          music.volume = 0.3;
        } else {
          pauseEl?.();
          controls.active = true;
          music.volume = 1;
        }
      }
      if (paused) {
        last = now;
        view.render(null, 1);
        requestAnimationFrame(frame);
        return;
      }

      acc += now - last;
      last = now;
      let steps = Math.floor(acc / CLASSIC_TICK_MS);
      if (steps > MAX_TICKS_PER_FRAME) {
        steps = MAX_TICKS_PER_FRAME;
        acc = 0;
      } else {
        acc -= steps * CLASSIC_TICK_MS;
      }

      for (let i = 0; i < steps; i++) {
        controls.sample();
        const result = tick();
        sfx.playQueue(g.soundQueue);
        view.setDrawList(drawList);

        // GAME OVER: the C waits for any input, then ends the level (tyrian2.c L1990-2011).
        if (result.gameOver && controls.anyInput()) g.reallyEndLevel = true;

        if (g.reallyEndLevel) {
          hud.update();
          view.render(null, 1);
          resolve(result.completed || !g.allPlayersGone ? "completed" : "died");
          return;
        }
      }

      hud.update();
      view.render(null, acc / CLASSIC_TICK_MS);
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  });
}
