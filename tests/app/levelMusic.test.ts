// The music of a level in play (src/app/levelMusic.ts, D157): the host plays each song the sim asks
// for (the secret-level warp's Zanac, event 35), the level's song again once a song that doesn't loop
// has ended (JE_main's `!playing`), and event 34's fade, one volume step per tick.
import { beforeEach, describe, expect, test } from "vitest";
import { LevelMusic } from "../../src/app/levelMusic";
import { g } from "../../src/sim/state";
import { play_song } from "../../src/sim/tyrian2";

class FakeMusic {
  playing = true;
  volume = 1;
  plays: number[] = [];
  play(n: number): void {
    this.plays.push(n);
    this.playing = true;
  }
}

describe("LevelMusic", () => {
  let music: FakeMusic;
  let level: LevelMusic;
  beforeEach(() => {
    g.levelSong = 18; // play_song(17) at the level's start, which the host plays itself
    g.song = 17;
    g.musicFade = false;
    g.firstGameOver = true;
    music = new FakeMusic();
    music.volume = 0.8;
    level = new LevelMusic(music, () => 0.8);
  });

  test("the level's own song isn't played again", () => {
    for (let i = 0; i < 5; i++) level.tick();
    expect(music.plays).toEqual([]);
  });

  test("the warp's play_song(30) plays Zanac once, then the level's song when it has ended", () => {
    play_song(30); // mainint.c L4701
    level.tick();
    level.tick();
    expect(music.plays).toEqual([30]);
    music.playing = false; // ZANAC3 doesn't loop
    level.tick();
    expect(music.plays).toEqual([30, 17]);
    expect(g.song).toBe(17);
    level.tick();
    expect(music.plays).toEqual([30, 17]);
  });

  test("an ended song is replayed only while firstGameOver holds (JE_main L1015)", () => {
    play_song(30);
    level.tick();
    g.firstGameOver = false;
    music.playing = false;
    level.tick();
    expect(music.plays).toEqual([30]);
  });

  test("event 34 fades one step of 255 per tick, to 10; event 35 plays its song at full volume", () => {
    g.musicFade = true;
    level.tick();
    expect(music.volume * 255).toBeCloseTo(0.8 * 255 - 1);
    for (let i = 0; i < 400; i++) level.tick();
    expect(music.volume * 255).toBeCloseTo(10);
    // Event 35: play_song(eventdat - 1), set_volume(tyrMusicVolume), musicFade = false.
    play_song(25);
    g.musicFade = false;
    level.tick();
    expect(music.plays).toEqual([25]);
    expect(music.volume).toBeCloseTo(0.8);
  });

  test("a fade still under way at the level's end gives the volume back", () => {
    g.musicFade = true;
    for (let i = 0; i < 30; i++) level.tick();
    expect(music.volume).toBeLessThan(0.8);
    level.end();
    expect(music.volume).toBeCloseTo(0.8);
  });
});
