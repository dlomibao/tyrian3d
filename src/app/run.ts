// The game flow around the simulation: get the data, title, new game, then play levels in order.
// Each level runs the ported JE_main loop at the classic tick rate and hands each tick's draw
// list to the renderer, which interpolates between ticks (DECISIONS.md D2).

import { filesFromZip, loadDevFiles, type FileMap } from "../assets/files";
import { loadStoredZip } from "../assets/store";
import { SoundEffects } from "../audio/sfx";
import { Music } from "../audio/music";
import { loadRemasterManifest, MusicSwitch, type MusicPlayer } from "../audio/remaster";
import { CLASSIC_TICK_MS } from "../core/timing";
import { drawList } from "../sim/draw";
import { startLevel, tick } from "../sim/game";
import { loadHelpText, parseMenuText } from "../sim/helptext";
import { clearSimInput } from "../sim/input";
import { JE_endLevelAni, JE_initPlayerData } from "../sim/mainint";
import { startNewGame, twoPlayerArcade } from "../sim/arcade"; // [arcade]
import { buildResources, requireFile } from "../sim/resources";
import { JE_loadGame, JE_loadScreen_select, JE_saveGame, loadSaves } from "../sim/savegame";
import { DIFFICULTY_EASY, DIFFICULTY_HARD, DIFFICULTY_NORMAL, g, SA_NONE } from "../sim/state";
import { loadLevelAsync } from "../sim/tyrian2";
import type { View } from "../render/view";
import { Controls } from "./controls";
import { episodeEndScreens } from "./episodeEnd";
import { Hud } from "./hud";
import { showLoadScreen, showOptions } from "./options";
import { connectVolumes, loadPrefs, musicLevel } from "./prefs";
import { highScoreCheck, showHighScoreScreen } from "./highScoresScreen"; // [high scores]
import { highScoreCheckDue } from "../sim/highscores"; // [high scores]
import { PauseButton, showPause } from "./pause"; // ui-framework: pause screen
import { askForData, showMessage, showStatus, showTitle, type TitleChoice } from "./screens";
import { runItemScreen } from "./shop";
// port-story: the screens between levels and the level fades.
import { BLACK, levelFade } from "./fade";
import { closeStoryScreens, playStoryScreens } from "./storyScreens";
import { showTrentWin } from "./arcade"; // [arcade]
import { takeStorySteps } from "../sim/story";

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
 * The "LAST LEVEL" backup: JE_saveGame(11, "LAST LEVEL    ") after JE_loadMap (so after the item
 * screen), and JE_loadGame(11) to retry a failed level (src/sim/savegame.ts). The saved level is
 * saveLevel: the section JE_loadMap started from (or the last `]s[`), so a retry goes back through
 * the item screen. It's the C's save slot 11, so the load lists show it too. [port-options]
 */
const lastLevelSlot = () => (g.twoPlayerMode ? 22 : 11);

/** `onPlay` fires once the first level starts, so the caller can stop its idle rendering. */
export async function runGame(view: View, onPlay: () => void = () => {}): Promise<void> {
  const files = await getFiles();
  const loading = showStatus("Loading…");
  g.res = buildResources(files, 1);
  loadHelpText(requireFile(files, "tyrian.hdt"));
  view.setPalettes(g.res.palettes);

  const audioContext = new AudioContext();
  // The FM original, or a local remaster pack's recordings when one is served (local builds only).
  const music = new MusicSwitch(audioContext, new Music(requireFile(files, "music.mus"), { context: audioContext }), await loadRemasterManifest());
  const sfx = new SoundEffects(requireFile(files, "tyrian.snd"), requireFile(files, "voices.snd"), audioContext);
  const controls = new Controls(() => view.gamePixelsPerScreenPixel);
  const hud = new Hud();
  const pauseButton = new PauseButton(() => (controls.pauseRequested = true)); // ui-framework
  loading();

  if (import.meta.env.DEV) Object.assign(window, { tyrian: { g, view, music, sfx } });

  // [port-options] The settings and saved games kept in this browser (opentyrian.cfg and tyrian.sav).
  loadPrefs();
  loadSaves();
  connectVolumes(music, sfx);

  const names = parseMenuText(requireFile(files, "tyrian.hdt"));
  const episodes = [1, 2, 3, 4, 5].filter((n) => files.get(`levels${n}.dat`) && files.get(`tyrian${n}.lvl`));
  let choice: TitleChoice = { episode: 1, difficulty: DIFFICULTY_NORMAL };

  for (;;) {
    music.play(SONG_TITLE);
    levelFade().set(0); // the title's backdrop draws under the level fade (port-story)
    choice = await showTitle({
      episodeNames: names.episodeName,
      episodes,
      difficultyNames: names.difficultyName,
      difficulties: [DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD],
      initial: choice,
      musicStyles: music.styles,
      musicStyle: music.style,
      onMusicStyle: (style) => music.setStyle(style),
      // [port-options] JE_loadScreen, after the main loop's reset before the title (opentyr.c L873-880).
      onLoadGame: async () => {
        const slot = await showLoadScreen({ sfx });
        if (slot === null) return false;
        JE_initPlayerData();
        g.playDemo = false;
        g.gameLoaded = false;
        g.jumpSection = false;
        return JE_loadScreen_select(slot, files);
      },
      onOptions: () => showOptions({ sfx, music }),
      currentMusicStyle: () => music.style,
      // [high scores] the title menu's High Scores (JE_highScoreScreen)
      highScoresLabel: g.miscText[50]?.trim() || undefined,
      onHighScores: () => showHighScoreScreen({ ...names, episodes, sfx, episode: choice.episode }),
      // [arcade] the Game row (gameplaySelect) and the codes typed at the title
      arcade: {
        gameplayName: names.gameplayName,
        superShips: names.superShips,
        specialName: names.specialName,
        planetName0: names.pName[0] ?? "Tyrian",
        twoPlayerArcade: twoPlayerArcade.newGame !== null,
        sound: (n) => sfx.playSampleNum(n),
        song: (n) => music.play(n),
      },
    });

    // JE_initEpisode: each episode has its own item data (episode 4's lives in tyrian4.lvl).
    // A loaded game is already set up, on its own episode (JE_loadGame). [port-options]
    g.res = buildResources(files, choice.loaded ? g.episodeNum : choice.episode);
    view.setPalettes(g.res.palettes);
    // [arcade] newGame() for the chosen mode, or a Super Arcade or Super Tyrian game (src/sim/arcade.ts).
    if (!choice.loaded) startNewGame({ mode: "fullGame", ...choice });
    onPlay();
    // port-story: JE_loadMap's pictures, text and fades play where the C would have drawn them.
    const story = (keepOpen = false) => playStoryScreens(takeStorySteps(), { files, sfx, music }, { keepOpen });

    // start_level / start_level_first (tyrian2.c L586-905): JE_loadMap with the item screen at
    // each `]I[`, the backup save, the level, then where to go next.
    for (;;) {
      // The episode script's other screens: an episode's end (]Q[) and the next episode's start.
      // port-story: the pictures, text and fades recorded before a pause play first.
      const screens = episodeEndScreens({ files, music });
      const loaded = await loadLevelAsync(
        files,
        g.episodeNum,
        g.mainLevel,
        async () => {
          await story(); // port-story
          // The item screen's backdrop draws in the game's canvas, under the level fade: clear it.
          levelFade().set(0);
          await runItemScreen({ files, sfx, music });
        },
        async (pause) => {
          await story(); // port-story: e.g. the screens before `]Q[`
          closeStoryScreens();
          // [high scores] JE_nextEpisode's JE_highScoreCheck (mainint.c L958-962)
          if (pause === "highScoreCheck") return highScoreCheck({ ...names, sfx, music }, g.initial_episode_num);
          await screens(pause);
        },
      );
      if (!loaded) {
        // [high scores] Quitting is how a game ends here, since a game over retries (D11, D14).
        if (highScoreCheckDue(choice.episode)) await highScoreCheck({ ...names, sfx, music }, choice.episode);
        break; // quit from the item screen: back to the title
      }
      await story(); // port-story: the screens after the item screen, and fade_black(50)
      if (!g.doNotSaveBackup) JE_saveGame(lastLevelSlot(), "LAST LEVEL    "); /*Save backup game*/
      startLevel();
      view.draws.resetInterpolation();
      music.play(g.levelSong - 1);
      clearSimInput();
      controls.clear();
      hud.visible = true;

      // port-story: JE_main's fade_palette(colors, 50) (tyrian2.c L716). The C fades in before the
      // first frame; here the level starts under the fade.
      levelFade().set(1, BLACK);
      void levelFade().fade(0, 50, BLACK);

      controls.active = true;
      pauseButton.visible = true; // ui-framework
      const outcome = await playLevel(view, controls, sfx, music, hud, pauseButton);
      controls.active = false;
      controls.release();
      hud.visible = false;
      pauseButton.visible = false; // ui-framework

      g.difficultyLevel = g.oldDifficultyLevel; /*Return difficulty to normal*/
      if (outcome === "quit") {
        // ui-framework: "Quit to title" on the pause screen (src/app/pause.ts). [high scores] As
        // quitting from the item screen, it ends the game, so its score is checked.
        if (highScoreCheckDue(choice.episode)) await highScoreCheck({ ...names, sfx, music }, choice.episode);
        break;
      }

      if (outcome === "completed") {
        g.mainLevel = g.nextLevel;
        JE_endLevelAni(); // its state changes; the summary is this screen
        music.play(SONG_LEVEL_END);
        await showMessage("Level complete", [
          `${g.levelName.trim()}`,
          `Score ${g.player[0].cash}`,
          `Enemies destroyed ${g.enemyKilled} of ${g.totalEnemy}`,
        ]);
        await levelFade().fade(1, 15, BLACK); // port-story: JE_endLevelAni's fade_black(15)
        if (g.mainLevel === 0) break; // end of the episode
      } else {
        music.play(SONG_GAME_OVER);
        await showMessage("Game over", ["Your ship was destroyed."], "Press Enter to retry from the item screen");
        await levelFade().fade(1, 10, BLACK); // port-story: fade_black(10) (tyrian2.c L639)
        JE_loadGame(lastLevelSlot(), files);
        if (g.doNotSaveBackup) {
          g.superTyrian = false;
          g.onePlayerAction = false;
          g.player[0].items.super_arcade_mode = SA_NONE;
        }
        if (g.bonusLevelCurrent && !g.playerEndLevel) g.mainLevel = g.nextLevel;
      }
      g.doNotSaveBackup = false;
    }
    // [arcade] Super Tyrian beaten at Lord of Game: the C quits with JE_tyrianHalt's message (opentyr.c L907-911).
    if (g.trentWin) {
      g.trentWin = false;
      await showTrentWin();
    }
  }
}

type Outcome = "completed" | "died" | "quit";

function playLevel(view: View, controls: Controls, sfx: SoundEffects, music: MusicPlayer, hud: Hud, pauseButton: PauseButton): Promise<Outcome> {
  return new Promise((resolve) => {
    let last = performance.now();
    let acc = 0;
    let paused = false;
    let quit = false;

    const frame = (now: number) => {
      // ui-framework: the pause screen (src/app/pause.ts) replaces the "Paused" status line.
      if (controls.pauseRequested && !paused) {
        controls.pauseRequested = false;
        paused = true;
        controls.release();
        controls.active = false;
        music.volume = musicLevel(0.3); // [port-options] relative to the music volume setting
        pauseButton.visible = false; // restyle-polish: not over the pause screen
        void showPause().then((choice) => {
          paused = false;
          pauseButton.visible = choice !== "quit"; // restyle-polish
          quit = choice === "quit";
          controls.clear();
          controls.active = true;
          music.volume = musicLevel();
        });
      }
      if (quit) {
        resolve("quit");
        return;
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
