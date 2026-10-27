// JE_highScoreCheck's music (mainint.c L1972, L2051-2052): the fanfare (song 33), then, at the first
// input after it ends, song 31 (`if (!playing) play_song(31)`).
import { describe, expect, test } from "vitest";
import { highScoreEntryInput, SONG_HIGH_SCORE_AFTER } from "../../src/app/highScoresScreen";
import { MusicRenderer } from "../../src/audio/musicRenderer";
import { hasData, readData } from "../data/dataDir";

describe("the name entry's music", () => {
  test("song 31 starts at an input once the song playing has ended, not before", () => {
    const played: number[] = [];
    const music = { playing: true, play: (n: number) => void played.push(n) };
    highScoreEntryInput(music);
    expect(played).toEqual([]);
    music.playing = false;
    highScoreEntryInput(music);
    expect(played).toEqual([31]);
    expect(SONG_HIGH_SCORE_AFTER).toBe(31);
  });

  test.skipIf(!hasData("music.mus"))("the fanfare ends by itself after a few seconds; song 31 loops", () => {
    const r = new MusicRenderer(44100, readData("music.mus"));
    expect(r.playing).toBe(false); // nothing loaded
    r.apply({ type: "play", song: 33 });
    expect(r.playing).toBe(true);
    const buf = new Float32Array(4410); // 0.1 s
    let seconds = 0;
    for (; seconds < 30 && r.playing; seconds += 0.1) r.render(buf);
    expect(r.playing).toBe(false);
    expect(seconds).toBeGreaterThan(3);
    expect(seconds).toBeLessThan(15);

    r.apply({ type: "play", song: 31 });
    for (let t = 0; t < 120; t += 0.1) r.render(buf);
    expect(r.playing).toBe(true);
  });
});
