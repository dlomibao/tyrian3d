// In-game music: Tyrian's Loudness (LDS) songs from music.mus, played through a port of
// OpenTyrian's OPL2 emulator and LDS player (opl.ts, lds.ts, musicRenderer.ts).
//
// Rendering happens in an AudioWorklet (musicWorklet.ts) at the AudioContext's sample rate. If
// AudioWorklet is unavailable (insecure http:// origins other than localhost, old browsers) or the
// module fails to load, it falls back to a ScriptProcessorNode on the main thread.
//
// Browsers only start audio after a user gesture, so the AudioContext is created or resumed on
// the first keydown/pointerdown/touchend. Calls made before that are queued and replayed in order.

import workletUrl from "./musicWorklet.ts?worker&url";
import type { MusicCommand } from "./musicRenderer";

/** Must match MUSIC_PROCESSOR_NAME in musicWorklet.ts. */
const MUSIC_PROCESSOR_NAME = "tyrian-music";

const GESTURE_EVENTS = ["keydown", "pointerdown", "touchend"] as const;

export interface MusicOptions {
  /** Render into this AudioContext instead of creating one (e.g. to share it with sound effects). */
  context?: AudioContext;
  /** Where to connect the music output. Defaults to the context's destination. */
  destination?: AudioNode;
}

type Sink = { post(cmd: MusicCommand): void; disconnect(): void };

export class Music {
  /** Number of songs in music.mus (41 in Tyrian 2.1). */
  readonly songCount: number;

  private readonly data: Uint8Array;
  private readonly ownsContext: boolean;
  private ctx: AudioContext | null;
  private readonly destination: AudioNode | null;
  private sink: Sink | null = null;
  private starting: Promise<void> | null = null;
  private pending: MusicCommand[] = [];
  private volumeValue = 1;
  private disposed = false;
  private watchingState = false;
  private readonly onGesture = (): void => {
    this.resume();
  };

  constructor(musicMus: Uint8Array, options: MusicOptions = {}) {
    if (musicMus.length < 2) throw new Error("music.mus: file too short");
    const count = musicMus[0] | (musicMus[1] << 8);
    if (musicMus.length < 2 + count * 4) throw new Error("music.mus: truncated song table");
    this.songCount = count;
    this.data = musicMus;
    this.ctx = options.context ?? null;
    this.ownsContext = !options.context;
    this.destination = options.destination ?? null;

    for (const ev of GESTURE_EVENTS) window.addEventListener(ev, this.onGesture, { capture: true });
    const activation = (navigator as Navigator & { userActivation?: { hasBeenActive: boolean } }).userActivation;
    if (activation?.hasBeenActive || this.ctx) this.resume();
  }

  /** The AudioContext, once created (after the first user gesture unless one was passed in). */
  get context(): AudioContext | null {
    return this.ctx;
  }

  /**
   * Starts a song, 0-based: OpenTyrian's play_song(n). A level plays play_song(levelSong - 1).
   * Playing the song that is already loaded resumes it where it was (as in OpenTyrian); use
   * restart() to rewind it.
   */
  play(songNum: number): void {
    if (!Number.isInteger(songNum) || songNum < 0 || songNum >= this.songCount) {
      console.error(`Music.play: song ${songNum} does not exist (0..${this.songCount - 1})`);
      return;
    }
    this.send({ type: "play", song: songNum });
  }

  /** Rewinds the current song and plays it (restart_song). */
  restart(): void {
    this.send({ type: "restart" });
  }

  /** Silences the music; play() with the same song resumes it (stop_song). */
  stop(): void {
    this.send({ type: "stop" });
  }

  /** Fades the current song out over about 3.7 seconds (fade_song). */
  fade(): void {
    this.send({ type: "fade" });
  }

  /**
   * Music volume, 0..1. Mapped to OpenTyrian's 0..255 setting, which spans 30 dB (0 is silent).
   */
  get volume(): number {
    return this.volumeValue;
  }

  set volume(v: number) {
    const clamped = Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));
    this.volumeValue = clamped;
    this.send({ type: "volume", value: Math.round(clamped * 255) });
  }

  /**
   * Creates/resumes the AudioContext. Called automatically on the first user gesture; call it
   * yourself from a gesture handler if you swallow those events before they reach `window`.
   */
  resume(): void {
    if (this.disposed) return;
    if (!this.ctx) this.ctx = new AudioContext();
    const ctx = this.ctx;
    if (ctx.state === "suspended") {
      ctx.resume().catch(() => {
        /* still waiting for a gesture */
      });
    }
    void this.start();
    if (ctx.state === "running") this.removeGestureListeners();
    else if (!this.watchingState) {
      this.watchingState = true;
      ctx.addEventListener("statechange", () => ctx.state === "running" && this.removeGestureListeners());
    }
  }

  /** Stops rendering and releases the audio nodes (and the AudioContext, if Music created it). */
  dispose(): void {
    this.disposed = true;
    this.removeGestureListeners();
    this.sink?.disconnect();
    this.sink = null;
    this.pending = [];
    if (this.ownsContext) void this.ctx?.close();
  }

  private send(cmd: MusicCommand): void {
    if (this.disposed) return;
    if (this.sink) this.sink.post(cmd);
    else this.pending.push(cmd);
  }

  private removeGestureListeners(): void {
    for (const ev of GESTURE_EVENTS) window.removeEventListener(ev, this.onGesture, { capture: true });
  }

  private start(): Promise<void> {
    if (!this.starting) {
      this.starting = this.connect().catch((err) => {
        console.error("music: failed to start audio", err);
      });
    }
    return this.starting;
  }

  private async connect(): Promise<void> {
    const ctx = this.ctx;
    if (!ctx) return;
    const dest = this.destination ?? ctx.destination;

    let sink: Sink | null = null;
    if (ctx.audioWorklet && typeof AudioWorkletNode !== "undefined") {
      try {
        await ctx.audioWorklet.addModule(workletUrl);
        const node = new AudioWorkletNode(ctx, MUSIC_PROCESSOR_NAME, {
          numberOfInputs: 0,
          numberOfOutputs: 1,
          outputChannelCount: [1],
        });
        node.onprocessorerror = (e) => console.error("music worklet error", e);
        node.connect(dest);
        sink = { post: (cmd) => node.port.postMessage(cmd), disconnect: () => node.disconnect() };
      } catch (err) {
        console.warn("music: AudioWorklet unavailable, falling back to ScriptProcessorNode", err);
      }
    }
    if (!sink) {
      const { MusicRenderer } = await import("./musicRenderer");
      const renderer = new MusicRenderer(ctx.sampleRate);
      const node = ctx.createScriptProcessor(2048, 0, 1);
      node.onaudioprocess = (e) => renderer.render(e.outputBuffer.getChannelData(0));
      node.connect(dest);
      sink = { post: (cmd) => renderer.apply(cmd), disconnect: () => node.disconnect() };
    }
    if (this.disposed) {
      sink.disconnect();
      return;
    }

    sink.post({ type: "load", data: this.data });
    for (const cmd of this.pending) sink.post(cmd);
    this.pending = [];
    this.sink = sink;
  }
}
