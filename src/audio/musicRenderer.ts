/*
 * OpenTyrian: A modern cross-platform port of Tyrian
 * Copyright (C) The OpenTyrian Development Team
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 */

/*
 * The music half of OpenTyrian's src/loudness.c: music.mus parsing (load_song), the song
 * controls (play_song / restart_song / stop_song / fade_song / set_volume), and the audio
 * callback that steps the LDS player at 69.5 Hz and renders the OPL in between. Sample effects
 * (multiSamplePlay) are not part of this module.
 *
 * Pure computation, no Web Audio: it runs in the AudioWorklet, in the ScriptProcessor fallback,
 * and in tests.
 */

import { LdsPlayer } from "./lds";
import { Opl } from "./opl";

/**
 * Splits music.mus into its songs. Format (load_song): u16 song count, then a u32 file offset per
 * song; each song runs to the next song's offset, the last one to the end of the file.
 */
export function parseMusicMus(data: Uint8Array): Uint8Array[] {
  if (data.length < 2) throw new Error("music.mus: file too short");
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const songsCount = view.getUint16(0, true);
  if (data.length < 2 + songsCount * 4) throw new Error("music.mus: truncated song table");
  const songPositions: number[] = [];
  for (let i = 0; i < songsCount; i++) songPositions.push(view.getUint32(2 + i * 4, true));
  songPositions.push(data.length);

  const songs: Uint8Array[] = [];
  for (let i = 0; i < songsCount; i++) {
    const position = songPositions[i];
    const endPosition = songPositions[i + 1];
    const size = endPosition > position ? endPosition - position : 0;
    songs.push(data.subarray(Math.min(position, data.length), Math.min(position + size, data.length)));
  }
  return songs;
}

// Twice the Loudness update rate (in updates/second). In Tyrian, Loudness updates were performed
// at the same rate as the game timer, which varied depending on the game speed (~69.57 Hz at most
// game speeds). OpenTyrian keeps the update rate constant at 69.5 Hz to stick to integer math.
const ldsUpdate2Rate = 139; // 69.5 * 2

const volumeRange = 30.0; // dB

// Fixed point Q20.12; needs to be able to store (10 * INT16_MIN/MAX)
// volumeFactorTable[i] = TO_FIXED(powf(10, (255 - i) * (-volumeRange / (20.0f * 255)))), in float.
const volumeFactorTable = new Int32Array(256);
{
  const f = Math.fround;
  const step = f(-volumeRange / f(20.0 * 255));
  volumeFactorTable[0] = 0;
  for (let i = 1; i < 256; ++i) {
    volumeFactorTable[i] = Math.trunc(f(f(Math.pow(10, f((255 - i) * step))) * (1 << 12)));
  }
}

/** Commands understood by the renderer (shared by the worklet and the fallback). */
export type MusicCommand =
  | { type: "load"; data: Uint8Array }
  | { type: "play"; song: number; seq?: number }
  | { type: "restart" }
  | { type: "stop" }
  | { type: "fade" }
  | { type: "volume"; value: number };

/** What the worklet tells the main thread: lds `playing`, as of the play command numbered `seq`. */
export type MusicState = { type: "state"; playing: boolean; seq: number };

export class MusicRenderer {
  readonly opl: Opl;
  readonly lds: LdsPlayer;
  readonly sampleRate: number;

  private songs: Uint8Array[] = [];

  private musicStopped = true;
  /** song_playing; -1 until a song has been loaded (OpenTyrian starts at 0 with nothing loaded). */
  private songPlaying = -1;
  private musicVolume = 255;

  private readonly samplesPerLdsUpdate: number;
  private readonly samplesPerLdsUpdateFrac: number;
  private samplesUntilLdsUpdate = 0;
  private samplesUntilLdsUpdateFrac = 0;

  private scratch = new Int16Array(0);

  constructor(sampleRate: number, musicMus?: Uint8Array) {
    this.sampleRate = sampleRate;
    this.samplesPerLdsUpdate = 2 * Math.trunc(sampleRate / ldsUpdate2Rate);
    this.samplesPerLdsUpdateFrac = 2 * (sampleRate % ldsUpdate2Rate);
    this.opl = new Opl(sampleRate);
    this.lds = new LdsPlayer(this.opl);
    if (musicMus) this.setMusicFile(musicMus);
  }

  get songCount(): number {
    return this.songs.length;
  }

  get currentSong(): number {
    return this.songPlaying;
  }

  get stopped(): boolean {
    return this.musicStopped;
  }

  /**
   * lds_play.c's `playing`: true from play_song until the song ends by itself (or a hard fade),
   * whether or not it's stopped; looping songs never end. JE_highScoreCheck reads it to follow the
   * fanfare with song 31.
   */
  get playing(): boolean {
    return this.songPlaying >= 0 && this.lds.playing;
  }

  setMusicFile(musicMus: Uint8Array): void {
    this.songs = parseMusicMus(musicMus);
    this.songPlaying = -1;
    this.musicStopped = true;
  }

  /** load_song */
  private loadSong(songNum: number): boolean {
    if (songNum < 0 || songNum >= this.songs.length) {
      console.error(`Attempted to load song ${songNum}, which does not exist.`);
      return false;
    }
    if (!this.lds.load(this.songs[songNum])) {
      console.error(`Failed to load song ${songNum}.`);
      return false;
    }
    return true;
  }

  /** play_song: switch to (and rewind) a different song, or resume the current one. */
  play(songNum: number): void {
    if (songNum !== this.songPlaying) {
      this.musicStopped = true;
      if (!this.loadSong(songNum)) return;
      this.songPlaying = songNum;
    }
    this.musicStopped = false;
  }

  /** restart_song */
  restart(): void {
    if (this.songPlaying < 0) return;
    this.lds.rewind();
    this.musicStopped = false;
  }

  /** stop_song */
  stop(): void {
    this.musicStopped = true;
  }

  /** fade_song */
  fade(): void {
    this.lds.fade(1);
  }

  /** set_volume's music half: 0..255, mapped onto a 30 dB range like OpenTyrian. */
  setVolume(musicVolume: number): void {
    this.musicVolume = Math.max(0, Math.min(255, Math.round(musicVolume)));
  }

  apply(cmd: MusicCommand): void {
    switch (cmd.type) {
      case "load":
        this.setMusicFile(cmd.data);
        break;
      case "play":
        this.play(cmd.song);
        break;
      case "restart":
        this.restart();
        break;
      case "stop":
        this.stop();
        break;
      case "fade":
        this.fade();
        break;
      case "volume":
        this.setVolume(cmd.value);
        break;
    }
  }

  /**
   * The music part of audioCallback: steps the LDS player and renders raw OPL output (before the
   * volume stage) into `samples`. Writes zeros while the music is stopped.
   */
  renderRaw(samples: Int16Array, offset = 0, samplesCount = samples.length - offset): void {
    if (this.musicStopped) {
      samples.fill(0, offset, offset + samplesCount);
      return;
    }
    let remaining = offset;
    let remainingCount = samplesCount;
    while (remainingCount > 0) {
      if (this.samplesUntilLdsUpdate === 0) {
        this.lds.update();

        // The number of samples that should be produced per Loudness update is not an integer,
        // but we can only produce an integer number of samples, so we accumulate the fractional
        // samples until it amounts to a whole sample.
        this.samplesUntilLdsUpdate += this.samplesPerLdsUpdate;
        this.samplesUntilLdsUpdateFrac += this.samplesPerLdsUpdateFrac;
        if (this.samplesUntilLdsUpdateFrac >= ldsUpdate2Rate) {
          this.samplesUntilLdsUpdate += 1;
          this.samplesUntilLdsUpdateFrac -= ldsUpdate2Rate;
        }
      }

      const count = Math.min(this.samplesUntilLdsUpdate, remainingCount);

      this.opl.getSample(samples, remaining, count);

      remaining += count;
      remainingCount -= count;

      this.samplesUntilLdsUpdate -= count;
    }
  }

  /**
   * Full music output for one buffer: renderRaw, then the callback's music volume stage (Q20.12
   * factor, doubled because "OPL emulator is too quiet", clamped to 16 bits), as floats in [-1, 1).
   */
  render(out: Float32Array): void {
    const n = out.length;
    if (this.scratch.length < n) this.scratch = new Int16Array(n);
    const samples = this.scratch;
    this.renderRaw(samples, 0, n);

    const musicVolumeFactor = volumeFactorTable[this.musicVolume] * 2; // OPL emulator is too quiet
    for (let i = 0; i < n; i++) {
      let sample = (samples[i] * musicVolumeFactor) >> 12;
      if (sample < -32768) sample = -32768;
      else if (sample > 32767) sample = 32767;
      out[i] = sample / 32768;
    }
  }
}
