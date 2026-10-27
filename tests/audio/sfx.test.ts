import { describe, expect, test, vi } from "vitest";
import { channelGain, parseSoundBank, queueVolume, SFX_COUNT, sfxStyleEntries, SoundEffects, SoundStyles, VOICE_COUNT, type SfxContext } from "../../src/audio/sfx";
import { hasData, readData } from "../data/dataDir";

describe.skipIf(!hasData("tyrian.snd", "voices.snd"))("sound banks", () => {
  test("hold the counts loadSndFile asserts", () => {
    expect(parseSoundBank(readData("tyrian.snd"), false)).toHaveLength(SFX_COUNT);
    expect(parseSoundBank(readData("voices.snd"), true)).toHaveLength(VOICE_COUNT);
  });

  test("samples are normalised signed 8-bit", () => {
    for (const s of parseSoundBank(readData("tyrian.snd"), false)) {
      expect(s.length).toBeGreaterThan(0);
      for (const v of s) expect(v >= -1 && v < 1).toBe(true);
    }
  });
});

// --- Sound styles (a local remaster pack's remade sounds) ---

const manifestSfx = {
  remaster: {
    "1": { file: "sfx/remaster/01-scaledn2.ogg", gain_db: 0 },
    "4": { file: "sfx/remaster/04-explsm.ogg", gain_db: 6 },
    "38": { file: "sfx/remaster/38-voice9.ogg" },
    "39": { file: "out of range.ogg" },
    "x": { file: "not an id.ogg" },
    "5": { file: "" },
  },
  empty: {},
};

describe("sfxStyleEntries", () => {
  test("keeps ids 1..38 with a file, and turns gain_db into a linear gain", () => {
    const e = sfxStyleEntries(manifestSfx, "remaster");
    expect([...e.keys()].sort((a, b) => a - b)).toEqual([1, 4, 38]);
    expect(e.get(1)!.gain).toBe(1);
    expect(e.get(4)!.gain).toBeCloseTo(10 ** (6 / 20));
    expect(e.get(38)!.gain).toBe(1);
    expect(sfxStyleEntries(manifestSfx, "nope").size).toBe(0);
    expect(sfxStyleEntries(undefined, "remaster").size).toBe(0);
  });

  test("clamps a bad gain_db", () => {
    expect(sfxStyleEntries({ s: { "2": { file: "a.ogg", gain_db: -10 } } }, "s").get(2)!.gain).toBe(1);
    expect(sfxStyleEntries({ s: { "2": { file: "a.ogg", gain_db: 99 } } }, "s").get(2)!.gain).toBeCloseTo(10 ** (12 / 20));
    expect(sfxStyleEntries({ s: { "2": { file: "a.ogg", gain_db: NaN } } }, "s").get(2)!.gain).toBe(1);
  });
});

describe("SoundStyles", () => {
  test("offers original plus the styles that have sounds; plays the original until a sound loads", async () => {
    const asked: string[] = [];
    const s = new SoundStyles(manifestSfx, async (f) => (asked.push(f), `buf:${f}`), true);
    expect(s.styles).toEqual(["original", "remaster"]);
    expect(s.style).toBe("original");
    expect(asked).toEqual([]); // nothing loads until the style is chosen
    expect(s.setStyle("remaster")).toBe(true);
    expect(s.sample(1)).toBeNull(); // still loading
    await s.ready();
    expect(asked.sort()).toEqual(["sfx/remaster/01-scaledn2.ogg", "sfx/remaster/04-explsm.ogg", "sfx/remaster/38-voice9.ogg"]);
    expect(s.sample(1)).toEqual({ buffer: "buf:sfx/remaster/01-scaledn2.ogg", gain: 1 });
    expect(s.sample(4)!.gain).toBeCloseTo(2, 1);
    expect(s.sample(2)).toBeNull(); // not in the style: the original
    expect(s.setStyle("original")).toBe(true);
    expect(s.sample(1)).toBeNull();
    s.setStyle("remaster");
    await s.ready();
    expect(asked).toHaveLength(3); // loaded once
    expect(s.setStyle("bogus")).toBe(false);
    expect(s.style).toBe("remaster");
  });

  test("a sound that fails to load stays the original", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const s = new SoundStyles(manifestSfx, async (f) => (f.includes("04") ? Promise.reject(new Error("404")) : f), true);
    s.setStyle("remaster");
    await s.ready();
    expect(s.sample(4)).toBeNull();
    expect(s.sample(1)).not.toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  test("a build that may not use local packs offers no styles and loads nothing", async () => {
    const load = vi.fn(async (f: string) => f);
    const s = new SoundStyles(manifestSfx, load, false);
    expect(s.styles).toEqual(["original"]);
    expect(s.setStyle("remaster")).toBe(false);
    await s.ready();
    expect(load).not.toHaveBeenCalled();
  });
});

// A stand-in for the Web Audio API: records what each played source was and its gain.
function fakeContext() {
  const played: { buffer: unknown; gain: number; stopped: boolean }[] = [];
  const gainNode = () => ({ gain: { value: 1 }, connect: (n: unknown) => n });
  const ctx = {
    state: "running",
    destination: {},
    resume: async () => {},
    createGain: gainNode,
    createBuffer: (_c: number, length: number) => ({ length, tag: "original", copyToChannel() {} }),
    decodeAudioData: async (data: ArrayBuffer) => ({ tag: new TextDecoder().decode(data) }),
    createBufferSource: () => {
      const rec = { buffer: null as unknown, gain: 0, stopped: false };
      const src = {
        buffer: null as unknown,
        onended: null,
        connect: (g: { gain: { value: number } }) => ({ connect: () => ((rec.gain = g.gain.value), undefined) }),
        start: () => ((rec.buffer = src.buffer), played.push(rec)),
        stop: () => (rec.stopped = true),
      };
      return src;
    },
  };
  return { ctx: ctx as unknown as SfxContext, played };
}

/** A .snd bank of `count` sounds of `size` bytes each, sound i filled with byte i + 1. */
function bank(count: number, size: number): Uint8Array {
  const b = new Uint8Array(2 + 4 * count + count * size);
  const v = new DataView(b.buffer);
  v.setUint16(0, count, true);
  for (let i = 0; i < count; i++) {
    const at = 2 + 4 * count + i * size;
    v.setUint32(2 + 4 * i, at, true);
    b.fill(i + 1, at, at + size);
  }
  return b;
}

describe("SoundEffects with a sound style", () => {
  test("remade sounds play on the same channels and volumes, times their gain; the rest stay original", async () => {
    vi.stubGlobal("fetch", async (url: string) => ({ ok: true, arrayBuffer: async () => new TextEncoder().encode(url).buffer }));
    try {
      const { ctx, played } = fakeContext();
      const fx = new SoundEffects(bank(SFX_COUNT, 4), bank(VOICE_COUNT, 104), ctx, { music: {}, sfx: manifestSfx });
      expect(fx.styles).toEqual(["original", "remaster"]);
      expect(fx.style).toBe("original");
      fx.setStyle("remaster", false);
      await fx.ready();

      // JE_main's queue: channel 3 plays at fxPlayVol (gain 5/8), id 15 elsewhere at volume 1
      // (2/8), the rest at volume 2 (3/8).
      const queue = [0, 0, 0, 4, 0, 1, 2, 15];
      fx.playQueue(queue);
      expect(queue).toEqual([0, 0, 0, 0, 0, 0, 0, 0]);
      const tag = (p: { buffer: unknown }) => (p.buffer as { tag: string }).tag;
      expect(played.map(tag)).toEqual(["tyrian-remaster/sfx/remaster/04-explsm.ogg", "tyrian-remaster/sfx/remaster/01-scaledn2.ogg", "original", "original"]);
      expect(played[0].gain).toBeCloseTo((5 / 8) * 10 ** (6 / 20));
      expect(played[1].gain).toBeCloseTo(3 / 8);
      expect(played[2].gain).toBeCloseTo(3 / 8);
      expect(played[3].gain).toBeCloseTo(2 / 8);
      expect(played.map((p) => p.gain)).toEqual([channelGain(4) * 10 ** (6 / 20), channelGain(2), channelGain(2), channelGain(1)].map((g) => expect.closeTo(g)));

      // A new sound on a channel replaces what it was playing, remade or not.
      fx.multiSamplePlay(2, 3, 4);
      expect(played[0].stopped).toBe(true);
      expect(tag(played[4])).toBe("original");

      // Back to the original style: every sound is the original again.
      fx.setStyle("original", false);
      fx.playSampleNum(38);
      expect(tag(played[5])).toBe("original");
      expect(played[5].gain).toBeCloseTo(channelGain(4));
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("without a remaster pack there's only the original, and nothing is fetched", () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    try {
      const { ctx, played } = fakeContext();
      const fx = new SoundEffects(bank(SFX_COUNT, 4), bank(VOICE_COUNT, 104), ctx, null);
      expect(fx.styles).toEqual(["original"]);
      fx.setStyle("remaster", false);
      expect(fx.style).toBe("original");
      fx.playSampleNum(1);
      expect(played).toHaveLength(1);
      expect(fetchSpy).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test("queueVolume is JE_main's: fxPlayVol on channel 3, a quarter of it for sound 15, half otherwise", () => {
    expect(queueVolume(1, 3)).toBe(4);
    expect(queueVolume(15, 3)).toBe(4);
    expect(queueVolume(15, 5)).toBe(1);
    expect(queueVolume(4, 5)).toBe(2);
  });
});
