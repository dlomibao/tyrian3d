// The music of a level in play (DECISIONS.md D157): what JE_main does with the songs the sim asks for,
// which the host plays. The sim records play_song(n) in `g.song` (tyrian2.ts play_song) and event
// 34's fade in `g.musicFade`; this follows them after every tick, through the game's music player, so
// a song plays in whatever style is selected (the FM original or a remaster, D38, D40).
//
// - A new `g.song`: play it. The secret-level warp's play_song(30), Zanac (mainint.c L4701), and
//   event 35's "Play new song" (tyrian2.c L4643-4648).
// - JE_main L1015-1018: `else if (!playing && firstGameOver) play_song(levelSong - 1)`: once a song
//   that doesn't loop has ended (Zanac is a 5-second jingle), the level's own song starts again.
// - JE_main L997-1008, event 34 (L4634-4639): while `musicFade` holds, the volume steps down one
//   step of OpenTyrian's 0..255 per tick from the music volume setting, to no lower than 10; event 35
//   clears the fade and sets the volume back (set_volume(tyrMusicVolume, ...)).
//
// L1010-1014 (`play_song(9)` once the level is won) stays the host's level-end screen (run.ts), and
// the next level's start plays its own song (start_level's play_song(levelSong - 1)).

import { play_song } from "../sim/tyrian2";
import { g } from "../sim/state";
import type { MusicPlayer } from "../audio/remaster";

/** OpenTyrian's set_volume floor for the fade (`tempVolume > 10`), of 255. */
const FADE_FLOOR = 10;

export class LevelMusic {
  /** The song last handed to the player (the level's, played by the host at the start). */
  private song: number;
  /** Ticks of event 34's fade so far (0: not fading). */
  private fadeTicks = 0;

  /**
   * `music`: the game's player, already playing the level's song. `level()`: the music volume
   * setting, 0..1 (prefs.ts musicLevel).
   */
  constructor(
    private readonly music: Pick<MusicPlayer, "play" | "playing" | "volume">,
    private readonly level: () => number,
  ) {
    this.song = g.song;
  }

  /** After each tick. */
  tick(): void {
    if (g.musicFade) {
      this.fadeTicks++;
      const full = this.level() * 255;
      const v = Math.max(Math.min(full, FADE_FLOOR), full - this.fadeTicks);
      this.music.volume = v / 255;
    } else if (this.fadeTicks > 0) {
      this.fadeTicks = 0;
      this.music.volume = this.level();
    }

    if (!this.music.playing && g.firstGameOver && g.levelSong - 1 !== this.song) play_song(g.levelSong - 1);

    if (g.song !== this.song) {
      this.song = g.song;
      if (g.song >= 0) this.music.play(g.song);
    }
  }

  /** The level is over: a fade still under way gives the volume back. */
  end(): void {
    if (this.fadeTicks > 0) this.music.volume = this.level();
    this.fadeTicks = 0;
  }
}
