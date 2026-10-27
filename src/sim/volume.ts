// The music and sound-effect volumes: tyrMusicVolume and fxVolume (OpenTyrian src/config.c, saved
// in opentyrian.cfg), JE_changeVolume (nortsong.c L223-260) and set_volume (loudness.c L371-382).
// The item screen's Options menu and the settings screen change them; the host applies them to its
// audio through setVolumeHandler and keeps them between visits (src/app/prefs.ts).

import { S_CLINK } from "./sndmast";

/** config.c L709-710: both start at 223 when there's no config file. */
export const DEFAULT_VOLUME = 223;
/** The step the Options menu changes a volume by (game_menu.c L1416, L1509). */
export const VOLUME_STEP = 12;

export const volume = {
  /** JE_word, 0..255 */
  tyrMusicVolume: DEFAULT_VOLUME,
  /** JE_word, 0..255 */
  fxVolume: DEFAULT_VOLUME,
};

let handler: (musicVolume: number, sampleVolume: number) => void = () => {};

/** Where set_volume sends the volumes (the host's music and sound players). */
export function setVolumeHandler(fn: (musicVolume: number, sampleVolume: number) => void): void {
  handler = fn;
}

/** set_volume (loudness.c L371-382): the mixer's music and sample volumes, 0..255. */
export function set_volume(musicVolume: number, sampleVolume: number): void {
  handler(musicVolume & 0xff, sampleVolume & 0xff);
}

/**
 * JE_changeVolume (nortsong.c L223-260): add the deltas to tyrMusicVolume and fxVolume, clamped to
 * 0..255 with a clink (`playSample(S_CLINK)`) when a changed one hits a limit, then set_volume.
 */
export function JE_changeVolume(music_delta: number, sample_delta: number, playSample: (samplenum: number) => void): void {
  let music_temp = volume.tyrMusicVolume + music_delta,
    sample_temp = volume.fxVolume + sample_delta;

  if (music_delta) {
    if (music_temp > 255) {
      music_temp = 255;
      playSample(S_CLINK);
    } else if (music_temp < 0) {
      music_temp = 0;
      playSample(S_CLINK);
    }
  }

  if (sample_delta) {
    if (sample_temp > 255) {
      sample_temp = 255;
      playSample(S_CLINK);
    } else if (sample_temp < 0) {
      sample_temp = 0;
      playSample(S_CLINK);
    }
  }

  volume.tyrMusicVolume = music_temp;
  volume.fxVolume = sample_temp;

  set_volume(volume.tyrMusicVolume, volume.fxVolume);
}

/**
 * The Options menu's mouse rule for the volume bars (game_menu.c L1047-1080): a click `cells` bar
 * cells (4 pixels each) from the bar's start sets the volume to cells * 12, at most 255.
 */
export function volumeFromBarCells(cells: number): number {
  const v = Math.trunc(cells) * VOLUME_STEP;
  return v > 255 ? 255 : v < 0 ? 0 : v;
}

/**
 * The mixer's gain for a volume (loudness.c L123-125, volumeFactorTable): 0 is silent and 1..255
 * span 30 dB up to 1.
 */
export function volumeFactor(v: number): number {
  return v <= 0 ? 0 : 10 ** (((255 - Math.min(255, v)) * -30) / (20 * 255));
}
