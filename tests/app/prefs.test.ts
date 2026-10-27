// The settings kept in the browser (src/app/prefs.ts) and the key bindings (src/app/bindings.ts).
import { beforeEach, describe, expect, test } from "vitest";
import { ACTIONS, bindKey, clearKey, DEFAULT_KEYS, isBound, keyName, keys, resetKeys, setKeys } from "../../src/app/bindings";
import { connectVolumes, loadPrefs, musicLevel, PREFS_STORAGE_KEY, PREFS_VERSION, savePrefs, type PrefsStorage } from "../../src/app/prefs";
import { DEFAULT_VOLUME, JE_changeVolume, set_volume, setVolumeHandler, volume, volumeFactor } from "../../src/sim/volume";

class MemoryStorage implements PrefsStorage {
  data = new Map<string, string>();
  getItem(k: string): string | null {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string): void {
    this.data.set(k, v);
  }
}

beforeEach(() => {
  resetKeys();
  volume.tyrMusicVolume = DEFAULT_VOLUME;
  volume.fxVolume = DEFAULT_VOLUME;
  setVolumeHandler(() => {});
});

describe("key bindings", () => {
  test("the defaults are OpenTyrian's keys, then WASD and J/K/L/; for laptops", () => {
    expect(ACTIONS.map((a) => keys[a][0])).toEqual(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", "Enter", "ControlLeft", "AltLeft"]);
    expect(keys.fire).toEqual(["Space", "KeyJ"]);
    expect(isBound("KeyW")).toBe(true);
    expect(isBound("KeyQ")).toBe(false);
  });

  test("binding a key another control uses swaps them, as KEY CONFIG does", () => {
    expect(bindKey("fire", 0, "ArrowUp")).toBe(true);
    expect(keys.fire[0]).toBe("ArrowUp");
    expect(keys.up[0]).toBe("Space");
    expect(bindKey("fire", 1, "KeyQ")).toBe(true);
    expect(keys.fire[1]).toBe("KeyQ");
    expect(isBound("KeyJ")).toBe(false);
  });

  test("Escape, P and F11 can't be bound; slots can be cleared; reset puts the defaults back", () => {
    expect(bindKey("fire", 0, "Escape")).toBe(false);
    expect(bindKey("fire", 0, "KeyP")).toBe(false);
    expect(keys.fire[0]).toBe("Space");
    clearKey("up", 1);
    expect(keys.up).toEqual(["ArrowUp", ""]);
    expect(isBound("")).toBe(false);
    resetKeys();
    expect(keys.up).toEqual([...DEFAULT_KEYS.up]);
  });

  test("stored bindings with a reserved or doubled key are refused", () => {
    const good = { ...structuredClone(keys), fire: ["KeyZ", ""] };
    expect(setKeys(good)).toBe(true);
    expect(keys.fire).toEqual(["KeyZ", ""]);
    expect(setKeys({ ...good, fire: ["KeyP", ""] })).toBe(false);
    expect(setKeys({ ...good, fire: ["ArrowUp", ""] })).toBe(false);
    expect(setKeys({ up: ["KeyW"] })).toBe(false);
    expect(keys.fire).toEqual(["KeyZ", ""]);
  });

  test("key names", () => {
    expect(["ArrowUp", "KeyW", "Space", "ControlLeft", "Semicolon", "Digit4", "Numpad8", ""].map(keyName)).toEqual(["Up", "W", "Space", "Left Ctrl", ";", "4", "Keypad 8", "—"]);
  });
});

describe("settings storage", () => {
  test("volumes and bindings are saved as versioned JSON and read back", () => {
    const store = new MemoryStorage();
    volume.tyrMusicVolume = 120;
    volume.fxVolume = 36;
    bindKey("fire", 0, "KeyZ");
    savePrefs(store);
    const data = JSON.parse(store.getItem(PREFS_STORAGE_KEY)!);
    expect(data).toMatchObject({ version: PREFS_VERSION, musicVolume: 120, fxVolume: 36 });

    resetKeys();
    loadPrefs(store);
    expect([volume.tyrMusicVolume, volume.fxVolume]).toEqual([120, 36]);
    expect(keys.fire[0]).toBe("KeyZ");
  });

  test("missing, unreadable or newer settings keep the defaults; a bad field keeps its own", () => {
    const store = new MemoryStorage();
    loadPrefs(store);
    expect(volume.tyrMusicVolume).toBe(DEFAULT_VOLUME);
    store.setItem(PREFS_STORAGE_KEY, "nope");
    loadPrefs(store);
    expect(volume.fxVolume).toBe(DEFAULT_VOLUME);
    store.setItem(PREFS_STORAGE_KEY, JSON.stringify({ version: PREFS_VERSION + 1, musicVolume: 10 }));
    loadPrefs(store);
    expect(volume.tyrMusicVolume).toBe(DEFAULT_VOLUME);
    store.setItem(PREFS_STORAGE_KEY, JSON.stringify({ version: PREFS_VERSION, musicVolume: 400, fxVolume: 12, keys: 5 }));
    loadPrefs(store);
    expect([volume.tyrMusicVolume, volume.fxVolume]).toEqual([DEFAULT_VOLUME, 12]);
    expect(keys.up).toEqual([...DEFAULT_KEYS.up]);
    loadPrefs(null);
    expect(volume.fxVolume).toBe(DEFAULT_VOLUME);
  });
});

describe("volumes", () => {
  test("the volume curve is loudness.c's: 30 dB over 1..255, 0 silent", () => {
    expect(volumeFactor(0)).toBe(0);
    expect(volumeFactor(255)).toBe(1);
    expect(20 * Math.log10(volumeFactor(1))).toBeCloseTo((-30 * 254) / 255, 6);
  });

  test("set_volume reaches the music and sound players", () => {
    const music = { volume: 1 };
    const sfx = { volume: 1 };
    connectVolumes(music, sfx);
    expect(music.volume).toBeCloseTo(DEFAULT_VOLUME / 255);
    expect(sfx.volume).toBeCloseTo(0.8 * volumeFactor(DEFAULT_VOLUME));
    JE_changeVolume(-DEFAULT_VOLUME, 0, () => {});
    expect(music.volume).toBe(0);
    set_volume(255, 0);
    expect(sfx.volume).toBe(0);
    volume.tyrMusicVolume = 255;
    expect(musicLevel(0.3)).toBeCloseTo(0.3);
  });
});
