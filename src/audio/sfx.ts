// Sound effects and voices, ported from OpenTyrian src/nortsong.c (loadSndFile, loadSounds) and
// src/loudness.c (multiSamplePlay): 8-bit signed mono PCM at 11025 Hz, mixed on 8 channels where a
// new sample replaces whatever its channel was playing, at gain (volume + 1) / 8.
//
// A local remaster pack (src/audio/remaster.ts) can also offer remade sounds: a sound style
// ("original", "remaster"). They play through the same channels, priorities and volumes; only the
// sample changes, sound by sound, and any sound the style lacks or that fails to load stays the
// original. The style is remembered in this browser; `?sound=<style>` overrides it.

import type { RemasterManifest, RemasterSfxEntry } from "./remaster";

export const SFX_COUNT = 29;
export const VOICE_COUNT = 9;
const SAMPLE_RATE = 11025;
const CHANNEL_COUNT = 8;
const CHANNEL_VOLUME_LEVELS = 8;
/** fxPlayVol (nortsong.c) */
const FX_PLAY_VOL = 4;
export const SOUND_STYLE_KEY = "tyrian3d.soundStyle";
/** The most gain_db a remade sound may ask for (tools/sfx.py stays at or under 6). */
const MAX_GAIN_DB = 12;

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

/** multiSamplePlay's gain for volume level `vol` (0..7). */
export const channelGain = (vol: number): number => (Math.min(vol, CHANNEL_VOLUME_LEVELS - 1) + 1) / CHANNEL_VOLUME_LEVELS;

/** JE_main's sound routine: the volume level a queued sound plays at on channel `chan`. */
export const queueVolume = (id: number, chan: number): number => (chan === 3 ? FX_PLAY_VOL : id === 15 ? FX_PLAY_VOL >> 2 : FX_PLAY_VOL >> 1);

/** A remade sound to play in place of the original: its file and linear gain. */
export interface SfxStyleEntry {
  file: string;
  gain: number;
}

/**
 * The sounds a manifest style replaces, by sound id (1..38). Entries with a bad id or no file are
 * skipped; gain_db is clamped to 0..MAX_GAIN_DB.
 */
export function sfxStyleEntries(styles: Record<string, Record<string, RemasterSfxEntry>> | undefined, style: string): Map<number, SfxStyleEntry> {
  const out = new Map<number, SfxStyleEntry>();
  for (const [key, e] of Object.entries(styles?.[style] ?? {})) {
    const id = Number(key);
    if (!Number.isInteger(id) || id < 1 || id > SFX_COUNT + VOICE_COUNT) continue;
    if (!e || typeof e.file !== "string" || !e.file) continue;
    const db = typeof e.gain_db === "number" && Number.isFinite(e.gain_db) ? Math.min(MAX_GAIN_DB, Math.max(0, e.gain_db)) : 0;
    out.set(id, { file: e.file, gain: 10 ** (db / 20) });
  }
  return out;
}

/**
 * Which sample each sound plays in the chosen style: "original", or a manifest style's remade
 * sounds, loaded (once) when the style is first chosen. Until a sound has loaded, or if it fails,
 * the original plays. `allowed` false keeps it to the original (no style is offered or loaded).
 * Generic over the buffer type so it's tested without Web Audio.
 */
export class SoundStyles<B> {
  /** "original" plus the manifest's styles that have sounds. */
  readonly styles: string[];
  private current = "original";
  private readonly buffers = new Map<string, Map<number, { buffer: B; gain: number }>>();
  private readonly pending = new Map<string, Promise<void>>();

  constructor(
    private readonly manifest: Record<string, Record<string, RemasterSfxEntry>> | undefined,
    private readonly load: (file: string) => Promise<B>,
    private readonly allowed: boolean = true,
  ) {
    const named = allowed ? Object.keys(manifest ?? {}).filter((s) => s !== "original" && sfxStyleEntries(manifest, s).size) : [];
    this.styles = ["original", ...named.sort()];
  }

  get style(): string {
    return this.current;
  }

  /** Choose a style (ignored if unknown); starts loading its sounds. True if it changed. */
  setStyle(style: string): boolean {
    if (!this.styles.includes(style) || style === this.current) return false;
    this.current = style;
    this.ensure(style);
    return true;
  }

  /** The remade sound `id` in the current style, or null to play the original. */
  sample(id: number): { buffer: B; gain: number } | null {
    if (this.current === "original") return null;
    return this.buffers.get(this.current)?.get(id) ?? null;
  }

  /** Settles once the current style's sounds have loaded or failed. */
  ready(): Promise<void> {
    return this.pending.get(this.current) ?? Promise.resolve();
  }

  private ensure(style: string): void {
    if (style === "original" || this.pending.has(style) || !this.allowed) return;
    const loaded = new Map<number, { buffer: B; gain: number }>();
    this.buffers.set(style, loaded);
    let failed = 0;
    const jobs = [...sfxStyleEntries(this.manifest, style)].map(([id, e]) =>
      this.load(e.file).then(
        (buffer) => void loaded.set(id, { buffer, gain: e.gain }),
        () => void failed++,
      ),
    );
    this.pending.set(
      style,
      Promise.all(jobs).then(() => {
        if (failed) console.warn(`sound style ${style}: ${failed} sound(s) failed to load; they play the original`);
      }),
    );
  }
}

/** The parts of the Web Audio API SoundEffects uses (an AudioContext, or a stand-in in tests). */
export type SfxContext = Pick<AudioContext, "createGain" | "createBuffer" | "createBufferSource" | "decodeAudioData" | "resume" | "state" | "destination">;

export class SoundEffects {
  private readonly ctx: SfxContext;
  private readonly out: GainNode;
  private readonly buffers: AudioBuffer[];
  private readonly channels: (AudioBufferSourceNode | null)[] = new Array(CHANNEL_COUNT).fill(null);
  private readonly sounds: SoundStyles<AudioBuffer>;

  /**
   * sfx = tyrian.snd, voices = voices.snd. Sound id n (1-based, sndmast.ts) is buffers[n - 1].
   * Pass the music's AudioContext to share one, and a local remaster manifest to offer its sound
   * styles.
   */
  constructor(sfx: Uint8Array, voices: Uint8Array, context?: SfxContext, remaster: RemasterManifest | null = null) {
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
    this.sounds = new SoundStyles(remaster?.sfx, (file) => this.fetchSound(file));
    let wanted: string | null = null;
    try {
      wanted = new URLSearchParams(globalThis.location?.search ?? "").get("sound") ?? globalThis.localStorage?.getItem(SOUND_STYLE_KEY) ?? null;
    } catch {
      /* storage unavailable */
    }
    if (wanted) this.sounds.setStyle(wanted);
    // Browsers start audio suspended until a user gesture.
    if (typeof window !== "undefined") {
      const resume = () => void this.ctx.resume();
      window.addEventListener("keydown", resume);
      window.addEventListener("pointerdown", resume);
      window.addEventListener("gamepadconnected", resume);
    }
  }

  set volume(v: number) {
    this.out.gain.value = v;
  }

  /** "original" plus the local remaster pack's sound styles. */
  get styles(): readonly string[] {
    return this.sounds.styles;
  }

  get style(): string {
    return this.sounds.style;
  }

  /** Switch the sound style (remembered in this browser); sounds already playing finish as they are. */
  setStyle(style: string, remember = true): void {
    if (!this.sounds.setStyle(style) || !remember) return;
    try {
      localStorage.setItem(SOUND_STYLE_KEY, style);
    } catch {
      /* storage unavailable */
    }
  }

  /** Settles once the current style's sounds have loaded (or failed). */
  ready(): Promise<void> {
    return this.sounds.ready();
  }

  /** multiSamplePlay: start sound `id` on channel `chan` at volume level `vol` (0..7). */
  multiSamplePlay(id: number, chan: number, vol: number): void {
    const remade = this.sounds.sample(id);
    const buffer = remade?.buffer ?? this.buffers[id - 1];
    if (!buffer || this.ctx.state !== "running") return;
    this.channels[chan]?.stop();
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    const gain = this.ctx.createGain();
    gain.gain.value = channelGain(vol) * (remade?.gain ?? 1);
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
      this.multiSamplePlay(id, chan, queueVolume(id, chan));
      soundQueue[chan] = 0;
    }
  }

  /** A remade sound from the remaster pack (public/tyrian-remaster/, or the private one locally). */
  private fetchSound(file: string): Promise<AudioBuffer> {
    return fetch(`tyrian-remaster/${file}`)
      .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(`${file}: HTTP ${r.status}`))))
      .then((data) => this.ctx.decodeAudioData(data));
  }
}
