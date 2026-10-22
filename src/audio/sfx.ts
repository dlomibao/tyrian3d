// Sound effects and voices, ported from OpenTyrian src/nortsong.c (loadSndFile, loadSounds) and
// src/loudness.c (multiSamplePlay): 8-bit signed mono PCM at 11025 Hz, mixed on 8 channels where a
// new sample replaces whatever its channel was playing, at gain (volume + 1) / 8.

export const SFX_COUNT = 29;
export const VOICE_COUNT = 9;
const SAMPLE_RATE = 11025;
const CHANNEL_COUNT = 8;
const CHANNEL_VOLUME_LEVELS = 8;
/** fxPlayVol (nortsong.c) */
const FX_PLAY_VOL = 4;

/** Parse a .snd bank (loadSounds): u16 count, u32 offsets, raw s8 samples. Voices drop 100 bad trailing bytes. */
export function parseSoundBank(data: Uint8Array, trim: boolean): Float32Array[] {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const count = view.getUint16(0, true);
  const positions: number[] = [];
  for (let i = 0; i < count; i++) positions.push(view.getUint32(2 + i * 4, true));
  positions.push(data.length);
  return positions.slice(0, count).map((start, i) => {
    let size = Math.max(0, positions[i + 1] - start);
    if (trim) size = size >= 100 ? size - 100 : 0;
    const out = new Float32Array(size);
    for (let j = 0; j < size; j++) out[j] = ((data[start + j] << 24) >> 24) / 128;
    return out;
  });
}

export class SoundEffects {
  private readonly ctx: AudioContext;
  private readonly out: GainNode;
  private readonly buffers: AudioBuffer[];
  private readonly channels: (AudioBufferSourceNode | null)[] = new Array(CHANNEL_COUNT).fill(null);

  /**
   * sfx = tyrian.snd, voices = voices.snd. Sound id n (1-based, sndmast.ts) is buffers[n - 1].
   * Pass the music's AudioContext to share one.
   */
  constructor(sfx: Uint8Array, voices: Uint8Array, context?: AudioContext) {
    this.ctx = context ?? new AudioContext();
    this.out = this.ctx.createGain();
    this.out.gain.value = 0.8;
    this.out.connect(this.ctx.destination);
    const samples = [...parseSoundBank(sfx, false), ...parseSoundBank(voices, true)];
    this.buffers = samples.map((s) => {
      const buf = this.ctx.createBuffer(1, Math.max(1, s.length), SAMPLE_RATE);
      buf.copyToChannel(s.length ? (s as Float32Array<ArrayBuffer>) : new Float32Array(1), 0);
      return buf;
    });
    // Browsers start audio suspended until a user gesture.
    const resume = () => void this.ctx.resume();
    window.addEventListener("keydown", resume);
    window.addEventListener("pointerdown", resume);
    window.addEventListener("gamepadconnected", resume);
  }

  set volume(v: number) {
    this.out.gain.value = v;
  }

  /** multiSamplePlay: start sound `id` on channel `chan` at volume level `vol` (0..7). */
  multiSamplePlay(id: number, chan: number, vol: number): void {
    const buffer = this.buffers[id - 1];
    if (!buffer || this.ctx.state !== "running") return;
    this.channels[chan]?.stop();
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    const gain = this.ctx.createGain();
    gain.gain.value = (Math.min(vol, CHANNEL_VOLUME_LEVELS - 1) + 1) / CHANNEL_VOLUME_LEVELS;
    src.connect(gain).connect(this.out);
    src.onended = () => {
      if (this.channels[chan] === src) this.channels[chan] = null;
    };
    src.start();
    this.channels[chan] = src;
  }

  /** JE_playSampleNum (nortsong.c): a menu sound, on channel 0 at fxPlayVol. */
  playSampleNum(id: number): void {
    this.multiSamplePlay(id, 0, FX_PLAY_VOL);
  }

  /** JE_main's sound routine: play each queued sound on its channel, then clear the queue. */
  playQueue(soundQueue: number[]): void {
    for (let chan = 0; chan < soundQueue.length; chan++) {
      const id = soundQueue[chan];
      if (id === 0) continue;
      const vol = chan === 3 ? FX_PLAY_VOL : id === 15 ? FX_PLAY_VOL >> 2 : FX_PLAY_VOL >> 1;
      this.multiSamplePlay(id, chan, vol);
      soundQueue[chan] = 0;
    }
  }
}
