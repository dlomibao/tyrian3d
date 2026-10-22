// AudioWorklet processor that renders Tyrian's music: the LDS player and OPL emulator run on the
// audio thread, stepped like OpenTyrian's audio callback (see musicRenderer.ts). The main thread
// (music.ts) only sends commands.
//
// Bundled by Vite through `?worker&url`, so its imports are inlined into one file. Nothing may
// import this module: it calls registerProcessor at load.

import { MusicRenderer, type MusicCommand } from "./musicRenderer";

// AudioWorkletGlobalScope isn't in TypeScript's DOM lib.
interface AudioWorkletProcessorInstance {
  readonly port: MessagePort;
}
declare const AudioWorkletProcessor: {
  prototype: AudioWorkletProcessorInstance;
  new (): AudioWorkletProcessorInstance;
};
declare const sampleRate: number;
declare function registerProcessor(name: string, ctor: typeof AudioWorkletProcessor): void;

/** Must match MUSIC_PROCESSOR_NAME in music.ts. */
const MUSIC_PROCESSOR_NAME = "tyrian-music";

class MusicProcessor extends AudioWorkletProcessor {
  private readonly renderer = new MusicRenderer(sampleRate);

  constructor() {
    super();
    this.port.onmessage = (e: MessageEvent<MusicCommand>) => {
      try {
        this.renderer.apply(e.data);
      } catch (err) {
        console.error("music worklet:", err);
      }
    };
  }

  process(_inputs: Float32Array[][], outputs: Float32Array[][]): boolean {
    const output = outputs[0];
    if (!output || output.length === 0) return true;
    this.renderer.render(output[0]);
    for (let ch = 1; ch < output.length; ch++) output[ch].set(output[0]);
    return true;
  }
}

registerProcessor(MUSIC_PROCESSOR_NAME, MusicProcessor);
