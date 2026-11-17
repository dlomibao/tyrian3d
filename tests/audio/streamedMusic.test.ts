// StreamedMusic keeps only the current song's decoded recording and the last two (DECISIONS.md D234).
import { afterEach, describe, expect, test, vi } from "vitest";
import { SONGS_KEPT, StreamedMusic, type MusicPlayer } from "../../src/audio/remaster";

/** Just enough of an AudioContext for StreamedMusic: every decode is a 60 s buffer. */
function fakeContext() {
  const node = () => ({ connect() {}, disconnect() {} });
  const decoded: number[] = [];
  const ctx = {
    currentTime: 0,
    state: "running",
    destination: node(),
    createGain: () => ({ ...node(), gain: { value: 1, cancelScheduledValues() {}, setValueAtTime() {}, linearRampToValueAtTime() {} } }),
    createBufferSource: () => ({ ...node(), buffer: null, loop: false, onended: null, start() {}, stop() {} }),
    decodeAudioData: async (data: ArrayBuffer) => (decoded.push(new Uint8Array(data)[0]), { duration: 60 }),
  };
  return { ctx: ctx as unknown as AudioContext, decoded };
}

const silent: MusicPlayer = {
  songCount: 40, playing: false, volume: 1,
  play() {}, restart() {}, stop() {}, fade() {}, resume() {}, dispose() {},
};

const settle = () => new Promise((r) => setTimeout(r, 0));

afterEach(() => vi.unstubAllGlobals());

describe("StreamedMusic", () => {
  test(`keeps the current song and the last ${SONGS_KEPT - 1}; an older one is fetched and decoded again`, async () => {
    const fetched: string[] = [];
    vi.stubGlobal("fetch", async (url: string) => {
      fetched.push(url);
      const n = Number(/song(\d+)/.exec(url)![1]);
      return { ok: true, arrayBuffer: async () => new Uint8Array([n]).buffer };
    });
    const files = Object.fromEntries([1, 2, 3, 4, 5].map((n) => [String(n), { file: `song${n}.ogg`, loops: true }]));
    const { ctx, decoded } = fakeContext();
    const music = new StreamedMusic(ctx, silent, files);
    for (const song of [0, 1, 2]) {
      music.play(song);
      await settle();
    }
    expect(music.keptSongs).toEqual([0, 1, 2]);
    music.play(0); // back to an earlier one: kept, so no fetch, and now the most recent
    await settle();
    expect(fetched).toHaveLength(3);
    expect(music.keptSongs).toEqual([1, 2, 0]);
    music.play(3);
    await settle();
    expect(music.keptSongs).toEqual([2, 0, 3]);
    music.play(1); // dropped: fetched and decoded again
    await settle();
    expect(fetched.filter((u) => u.endsWith("song2.ogg"))).toHaveLength(2);
    expect(decoded).toEqual([1, 2, 3, 4, 2]);
    expect(music.keptSongs).toEqual([0, 3, 1]);
  });
});
