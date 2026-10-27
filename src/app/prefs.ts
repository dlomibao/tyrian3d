// The player's settings, kept in this browser: the music and sound-effect volumes (the C keeps
// them in opentyrian.cfg) and the keyboard bindings (keySettings there), with player 2's keys and
// both players' gamepads for two-player games ([two-player]). The music style is kept
// by MusicSwitch itself (src/audio/remaster.ts). Stored as versioned JSON under PREFS_STORAGE_KEY.

import { keys, keys2, pads, setKeys, setPads } from "./bindings";
import { DEFAULT_VOLUME, set_volume, setVolumeHandler, volume, volumeFactor } from "../sim/volume";

export const PREFS_STORAGE_KEY = "tyrian3d.settings";
export const PREFS_VERSION = 1;

/** The part of the Web Storage API the settings use (localStorage, or a stand-in in tests). */
export interface PrefsStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function defaultStorage(): PrefsStorage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

const isVolume = (v: unknown): v is number => Number.isInteger(v) && (v as number) >= 0 && (v as number) <= 255;

/**
 * Read the settings into `volume` and the key bindings. A missing store, or one from an unknown
 * version, keeps the defaults; a bad field keeps its own default.
 */
export function loadPrefs(storage: PrefsStorage | null = defaultStorage()): void {
  volume.tyrMusicVolume = DEFAULT_VOLUME;
  volume.fxVolume = DEFAULT_VOLUME;
  let text: string | null = null;
  try {
    text = storage?.getItem(PREFS_STORAGE_KEY) ?? null;
  } catch {
    /* storage unavailable */
  }
  if (!text) return;
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(text);
  } catch {
    return;
  }
  if (data?.version !== PREFS_VERSION) return;
  if (isVolume(data.musicVolume)) volume.tyrMusicVolume = data.musicVolume;
  if (isVolume(data.fxVolume)) volume.fxVolume = data.fxVolume;
  setKeys(data.keys);
  setKeys(data.keys2, 1); // [two-player]
  setPads(data.pads);
}

/** The settings as stored. */
export function serializePrefs(): string {
  return JSON.stringify({ version: PREFS_VERSION, musicVolume: volume.tyrMusicVolume, fxVolume: volume.fxVolume, keys, keys2, pads });
}

export function savePrefs(storage: PrefsStorage | null = defaultStorage()): void {
  try {
    storage?.setItem(PREFS_STORAGE_KEY, serializePrefs());
  } catch {
    /* storage full or unavailable: the settings last until the page closes */
  }
}

/** The sound effects' output gain at full volume (src/audio/sfx.ts). */
const SFX_GAIN = 0.8;

/**
 * Make set_volume drive the music and sound players and remember each change, then apply the
 * current volumes. Music.volume takes the C's 0..255 scaled to 0..1 (its renderer applies the
 * 30 dB curve); the sound effects get the curve here.
 */
export function connectVolumes(music: { volume: number }, sfx: { volume: number }): void {
  setVolumeHandler((musicVolume, sampleVolume) => {
    music.volume = musicVolume / 255;
    sfx.volume = SFX_GAIN * volumeFactor(sampleVolume);
    savePrefs();
  });
  set_volume(volume.tyrMusicVolume, volume.fxVolume);
}

/** The music volume as MusicPlayer.volume (0..1), times `scale` (the pause screen quietens it). */
export const musicLevel = (scale = 1): number => (volume.tyrMusicVolume / 255) * scale;
