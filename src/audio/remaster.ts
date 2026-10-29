// The remaster pack: new recordings of the music (orchestral and synth) and remade sound effects and
// voices, public in public/tyrian-remaster/ (DECISIONS.md D40, D41) and loaded by every build. They
// are made in the tyrian3d-remaster repo; `npm run dev` and `npm run play:local` serve its out/
// folder at tyrian-remaster/ in place of the public copy when it's there (vite.config.ts).

/** out/manifest.json: per style ("orchestral", "synth"), the song files by 1-based song number. */
export interface RemasterManifest {
  music: Record<string, Record<string, { file: string; title: string; seconds: number; loops: boolean }>>;
  /** Per style ("remaster"), the sound effects and voices by 1-based sound id (sndmast.ts). */
  sfx?: Record<string, Record<string, RemasterSfxEntry>>;
}

/** One remade sound (the private repo's tools/sfx.py). */
export interface RemasterSfxEntry {
  file: string;
  /**
   * Gain (dB, 0 or more) to play it at so it's as loud as the original: the file is kept below
   * full scale and Web Audio mixes in floating point.
   */
  gain_db?: number;
  title?: string;
  name?: string;
  seconds?: number;
}

/** Whether this build may look for local packs: the dev server, or a local build (VITE_LOCAL_DATA=1). */
export const localAssetsAllowed = (): boolean => import.meta.env.DEV || import.meta.env.VITE_LOCAL_DATA === "1";

export async function loadRemasterManifest(): Promise<RemasterManifest | null> {
  try {
    const r = await fetch("tyrian-remaster/manifest.json");
    if (!r.ok) return null;
    const m = (await r.json()) as Partial<RemasterManifest>;
    const music = m.music ?? {};
    const hasSfx = Object.values(m.sfx ?? {}).some((s) => Object.keys(s).length);
    return Object.keys(music).length || hasSfx ? { ...m, music } : null;
  } catch {
    return null;
  }
}

/** The music player the game talks to (src/audio/music.ts's Music has the same shape). */
export interface MusicPlayer {
  readonly songCount: number;
  play(songNum: number): void;
  restart(): void;
  stop(): void;
  fade(): void;
  /**
   * lds_play.c's `playing`: true from play() until a song that doesn't loop reaches its end (stop()
   * doesn't clear it). JE_highScoreCheck plays song 31 once the fanfare is over.
   */
  readonly playing: boolean;
  volume: number;
  resume(): void;
  dispose(): void;
}

/** OpenTyrian's music volume: 0..255 spans 30 dB, 0 is silent (musicRenderer.ts volumeFactorTable). */
const volumeGain = (v: number): number => (v <= 0 ? 0 : 10 ** ((-30 * (255 - Math.round(v * 255))) / (20 * 255)));
const FADE_SECONDS = 3.7;

/**
 * Plays a remaster style's recordings where it has one and the FM original otherwise, with the same
 * behaviour as Music: play() of the current, stopped song resumes it; fade() fades out over ~3.7 s.
 */
export class StreamedMusic implements MusicPlayer {
  readonly songCount: number;
  private readonly gain: GainNode;
  private readonly buffers = new Map<number, Promise<AudioBuffer | null>>();
  private source: AudioBufferSourceNode | null = null;
  private song = -1;
  /** Seconds into the current song's buffer where a stopped song resumes. */
  private offset = 0;
  private startedAt = 0;
  /** A recording is sounding now (not stopped, not ended). */
  private running = false;
  /** The current recording played to its end (it doesn't loop). */
  private ended = false;
  private token = 0;
  private volumeValue = 1;
  private usingFallback = false;

  constructor(
    private readonly ctx: AudioContext,
    private readonly fallback: MusicPlayer,
    private readonly files: Record<string, { file: string; loops: boolean }>,
  ) {
    this.songCount = fallback.songCount;
    this.gain = ctx.createGain();
    this.gain.connect(ctx.destination);
    this.gain.gain.value = volumeGain(1);
  }

  play(songNum: number): void {
    if (songNum === this.song && (this.running || this.usingFallback)) return;
    if (songNum === this.song && !this.running && !this.usingFallback) {
      void this.start(this.offset);
      return;
    }
    this.halt();
    this.song = songNum;
    this.offset = 0;
    this.ended = false;
    if (!this.files[String(songNum + 1)]) {
      this.usingFallback = true;
      this.fallback.play(songNum);
      return;
    }
    this.usingFallback = false;
    this.fallback.stop();
    void this.start(0);
  }

  restart(): void {
    if (this.usingFallback) return this.fallback.restart();
    this.halt();
    this.offset = 0;
    this.ended = false; // lds_rewind sets playing again
    void this.start(0);
  }

  stop(): void {
    if (this.usingFallback) return this.fallback.stop();
    if (this.running) this.offset = this.position();
    this.halt();
  }

  fade(): void {
    if (this.usingFallback) return this.fallback.fade();
    const g = this.gain.gain;
    const now = this.ctx.currentTime;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(0, now + FADE_SECONDS);
    const token = this.token;
    setTimeout(() => token === this.token && this.halt(), FADE_SECONDS * 1000);
  }

  get playing(): boolean {
    return this.usingFallback ? this.fallback.playing : !this.ended;
  }

  get volume(): number {
    return this.volumeValue;
  }

  set volume(v: number) {
    this.volumeValue = Math.max(0, Math.min(1, v));
    this.fallback.volume = this.volumeValue;
    this.gain.gain.cancelScheduledValues(this.ctx.currentTime);
    this.gain.gain.value = volumeGain(this.volumeValue);
  }

  resume(): void {
    this.fallback.resume();
    if (this.ctx.state === "suspended") void this.ctx.resume().catch(() => {});
  }

  /** Stops and releases this player (not the fallback, which MusicSwitch owns). */
  dispose(): void {
    this.halt();
    this.gain.disconnect();
  }

  private position(): number {
    const buf = this.source?.buffer;
    if (!buf) return this.offset;
    const t = this.offset + (this.ctx.currentTime - this.startedAt);
    return this.source!.loop ? t % buf.duration : Math.min(t, buf.duration);
  }

  private halt(): void {
    this.token++;
    this.running = false;
    if (this.source) {
      this.source.onended = null;
      try {
        this.source.stop();
      } catch {
        /* not started */
      }
      this.source.disconnect();
      this.source = null;
    }
  }

  private buffer(song: number): Promise<AudioBuffer | null> {
    let p = this.buffers.get(song);
    if (!p) {
      const entry = this.files[String(song + 1)];
      p = fetch(`tyrian-remaster/${entry.file}`)
        .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(`${entry.file}: HTTP ${r.status}`))))
        .then((data) => this.ctx.decodeAudioData(data))
        .catch((err) => {
          console.error("remaster music failed to load; playing the original", err);
          return null;
        });
      this.buffers.set(song, p);
    }
    return p;
  }

  private async start(offset: number): Promise<void> {
    const token = ++this.token;
    const song = this.song;
    const buf = await this.buffer(song);
    if (token !== this.token) return; // another command came first
    if (!buf) {
      this.usingFallback = true;
      this.fallback.play(song);
      return;
    }
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.loop = this.files[String(song + 1)].loops;
    src.connect(this.gain);
    this.gain.gain.cancelScheduledValues(this.ctx.currentTime);
    this.gain.gain.value = volumeGain(this.volumeValue);
    src.start(0, offset % buf.duration);
    src.onended = () => {
      if (this.source !== src) return;
      this.running = false;
      this.ended = true; // halt() clears onended first, so this is the recording's own end
    };
    this.source = src;
    this.startedAt = this.ctx.currentTime;
    this.offset = offset;
    this.running = true;
  }
}

const STYLE_KEY = "tyrian3d.musicStyle";
/** The style played until the player picks one, when the manifest has it (D38). */
export const DEFAULT_MUSIC_STYLE = "synth";

/**
 * The game's music: the FM original, or a remaster style's recordings (StreamedMusic), switchable
 * at any time; switching replays the current song in the new style. The style is remembered in
 * this browser; `?music=<style>` overrides it. With no choice made, it's DEFAULT_MUSIC_STYLE if
 * the manifest has it, else the original.
 */
export class MusicSwitch implements MusicPlayer {
  readonly songCount: number;
  /** "original" plus the manifest's styles. */
  readonly styles: string[];
  private player: MusicPlayer;
  private styleValue = "original";
  private song = -1;
  private volumeValue = 1;
  private readonly streams = new Map<string, StreamedMusic>();

  constructor(
    private readonly ctx: AudioContext,
    private readonly original: MusicPlayer,
    private readonly manifest: RemasterManifest | null,
  ) {
    this.songCount = original.songCount;
    this.player = original;
    this.styles = ["original", ...Object.keys(manifest?.music ?? {}).sort()];
    let wanted = new URLSearchParams(location.search).get("music");
    try {
      wanted ??= localStorage.getItem(STYLE_KEY);
    } catch {
      /* storage unavailable */
    }
    if (!wanted || !this.styles.includes(wanted)) wanted = DEFAULT_MUSIC_STYLE;
    if (this.styles.includes(wanted)) this.setStyle(wanted, false);
  }

  get style(): string {
    return this.styleValue;
  }

  setStyle(style: string, remember = true): void {
    if (!this.styles.includes(style) || style === this.styleValue) return;
    this.player.stop();
    this.styleValue = style;
    if (style === "original") this.player = this.original;
    else {
      let s = this.streams.get(style);
      if (!s) this.streams.set(style, (s = new StreamedMusic(this.ctx, this.original, this.manifest!.music[style])));
      this.player = s;
    }
    this.player.volume = this.volumeValue;
    if (remember) {
      try {
        localStorage.setItem(STYLE_KEY, style);
      } catch {
        /* storage unavailable */
      }
    }
    if (this.song >= 0) {
      this.player.play(this.song);
      this.player.restart();
    }
  }

  play(songNum: number): void {
    this.song = songNum;
    this.player.play(songNum);
  }

  restart(): void {
    this.player.restart();
  }

  stop(): void {
    this.player.stop();
  }

  fade(): void {
    this.player.fade();
  }

  get playing(): boolean {
    return this.player.playing;
  }

  get volume(): number {
    return this.volumeValue;
  }

  set volume(v: number) {
    this.volumeValue = v;
    this.player.volume = v;
  }

  resume(): void {
    this.player.resume();
  }

  dispose(): void {
    for (const s of this.streams.values()) s.dispose();
    this.original.dispose();
  }
}
