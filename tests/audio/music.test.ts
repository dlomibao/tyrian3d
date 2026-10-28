import { describe, expect, it, test, vi } from "vitest";
import { LdsPlayer } from "../../src/audio/lds";
import { MusicRenderer, parseMusicMus } from "../../src/audio/musicRenderer";
import { Opl } from "../../src/audio/opl";
import { DEFAULT_MUSIC_STYLE, type MusicPlayer, MusicSwitch } from "../../src/audio/remaster";
import { hasData, readData } from "../data/dataDir";

/** FNV-1a over the little-endian bytes of 16-bit samples. */
function fnv1a(samples: Int16Array): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < samples.length; i++) {
    const s = samples[i] & 0xffff;
    h = Math.imul(h ^ (s & 0xff), 0x01000193);
    h = Math.imul(h ^ (s >>> 8), 0x01000193);
  }
  return h >>> 0;
}

/** Raw OPL output (before the volume stage) of the first `seconds` of a song, in 128-sample blocks. */
function renderRaw(mus: Uint8Array, song: number, rate: number, seconds: number): Int16Array {
  const r = new MusicRenderer(rate, mus);
  r.play(song);
  const out = new Int16Array(Math.round(rate * seconds));
  for (let off = 0; off < out.length; off += 128) r.renderRaw(out, off, Math.min(128, out.length - off));
  return out;
}

describe("parseMusicMus", () => {
  it("splits a song table into slices", () => {
    // 2 songs: offsets 10 and 13, file length 15.
    const data = new Uint8Array([2, 0, 10, 0, 0, 0, 13, 0, 0, 0, 1, 2, 3, 4, 5]);
    const songs = parseMusicMus(data);
    expect(songs.map((s) => Array.from(s))).toEqual([[1, 2, 3], [4, 5]]);
  });

  it("rejects a truncated table", () => {
    expect(() => parseMusicMus(new Uint8Array([5, 0, 0]))).toThrow();
  });
});

describe.skipIf(!hasData("music.mus"))("music.mus", () => {
  it("holds Tyrian 2.1's 41 songs (MUSIC_NUM in musmast.h), all loadable", () => {
    const songs = parseMusicMus(readData("music.mus"));
    expect(songs).toHaveLength(41);
    const lds = new LdsPlayer(new Opl(44100));
    for (const song of songs) {
      expect(song.length).toBeGreaterThan(100);
      expect(lds.load(song)).toBe(true);
    }
  });

  it("renders song 0 as non-silent, finite output, deterministically", () => {
    const mus = readData("music.mus");
    const render = () => {
      const r = new MusicRenderer(48000, mus);
      r.play(0);
      const out = new Float32Array(48000 * 2);
      for (let off = 0; off < out.length; off += 128) r.render(out.subarray(off, off + 128));
      return out;
    };
    const a = render();
    expect(a.every((s) => Number.isFinite(s) && s >= -1 && s < 1)).toBe(true);
    const rms = Math.sqrt(a.reduce((sum, s) => sum + s * s, 0) / a.length);
    expect(rms).toBeGreaterThan(0.01);
    expect(render()).toEqual(a);
  });

  // Hashes of the first seconds of raw OPL output from OpenTyrian's own opl.c + lds_play.c,
  // compiled natively and driven like loudness.c's audio callback (see the PR for the harness).
  // The TypeScript port matches it sample for sample.
  it.each([
    [0, 44100, 2, 0x0a9fd964],
    [17, 44100, 2, 0x47c0be65],
    [36, 44100, 5, 0x603d8262],
    [29, 48000, 2, 0x2ff0b2c5],
  ])("song %i at %i Hz for %i s matches the C reference", (song, rate, seconds, hash) => {
    expect(fnv1a(renderRaw(readData("music.mus"), song, rate, seconds))).toBe(hash);
  });

  it("stop silences, play resumes, restart rewinds, fade lowers the level", () => {
    const r = new MusicRenderer(44100, readData("music.mus"));
    const block = new Float32Array(4410);
    const rms = () => Math.sqrt(block.reduce((s, x) => s + x * x, 0) / block.length);

    r.play(0);
    r.render(block);
    r.stop();
    r.render(block);
    expect(rms()).toBe(0);
    r.play(0);
    r.render(block);
    expect(r.stopped).toBe(false);

    // Restarting reproduces the song's opening.
    const fresh = new MusicRenderer(44100, readData("music.mus"));
    fresh.play(0);
    const first = new Float32Array(4410);
    fresh.render(first);
    const restarted = new MusicRenderer(44100, readData("music.mus"));
    restarted.play(0);
    for (let i = 0; i < 20; i++) restarted.render(block);
    restarted.restart();
    restarted.render(block);
    // The LDS tick phase carries over (as in OpenTyrian), so compare loudness, not samples.
    expect(Math.abs(rms() - Math.sqrt(first.reduce((s, x) => s + x * x, 0) / first.length))).toBeLessThan(0.05);

    // Fading: after ~4 s the level is far below the unfaded song at the same point.
    const loud = new MusicRenderer(44100, readData("music.mus"));
    const faded = new MusicRenderer(44100, readData("music.mus"));
    loud.play(1);
    faded.play(1);
    for (let i = 0; i < 10; i++) {
      loud.render(block);
      faded.render(block);
    }
    faded.fade();
    let loudSum = 0;
    let fadedSum = 0;
    for (let i = 0; i < 50; i++) {
      loud.render(block);
      if (i >= 40) loudSum += rms();
      faded.render(block);
      if (i >= 40) fadedSum += rms();
    }
    expect(fadedSum).toBeLessThan(loudSum * 0.2);
  });

  it("volume 0 is silent and lower volumes are quieter", () => {
    const level = (vol: number) => {
      const r = new MusicRenderer(44100, readData("music.mus"));
      r.setVolume(vol);
      r.play(0);
      const out = new Float32Array(44100);
      r.render(out);
      return Math.sqrt(out.reduce((s, x) => s + x * x, 0) / out.length);
    };
    expect(level(0)).toBe(0);
    expect(level(128)).toBeLessThan(level(255));
    expect(level(128)).toBeGreaterThan(0);
  });
});

describe("MusicSwitch's starting style", () => {
  const original: MusicPlayer = {
    songCount: 41, playing: false, volume: 1,
    play() {}, restart() {}, stop() {}, fade() {}, resume() {}, dispose() {},
  };
  const ctx = { destination: {}, currentTime: 0, createGain: () => ({ connect() {}, gain: { value: 1, cancelScheduledValues() {} } }) } as unknown as AudioContext;
  const song = { file: "x.ogg", title: "x", seconds: 1, loops: true };
  const manifest = { music: { orchestral: { "1": song }, synth: { "1": song } } };

  function start(search: string, stored: string | null, m: typeof manifest | null = manifest) {
    vi.stubGlobal("location", { search });
    vi.stubGlobal("localStorage", { getItem: () => stored, setItem() {} });
    try {
      return new MusicSwitch(ctx, original, m).style;
    } finally {
      vi.unstubAllGlobals();
    }
  }

  test("is synth until the player picks one", () => {
    expect(DEFAULT_MUSIC_STYLE).toBe("synth");
    expect(start("", null)).toBe("synth");
    expect(start("", "bogus")).toBe("synth");
  });

  test("a remembered choice or ?music= wins", () => {
    expect(start("", "original")).toBe("original");
    expect(start("", "orchestral")).toBe("orchestral");
    expect(start("?music=original", "orchestral")).toBe("original");
  });

  test("is the original without the remaster", () => {
    expect(start("", null, null)).toBe("original");
  });
});
