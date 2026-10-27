// The settings kept in the browser (src/app/prefs.ts) and the key bindings (src/app/bindings.ts).
import { beforeEach, describe, expect, test } from "vitest";
import { ACTIONS, bindKey, clearKey, cyclePad, DEFAULT_KEYS, DEFAULT_KEYS_2, isBound, keyName, keys, keys2, pads, resetKeys, setKeys, setPads } from "../../src/app/bindings";
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
  resetKeys(1);
  setPads([0, 1]);
  volume.tyrMusicVolume = DEFAULT_VOLUME;
  volume.fxVolume = DEFAULT_VOLUME;
  setVolumeHandler(() => {});
});

describe("key bindings", () => {
  test("the defaults are OpenTyrian's keys, then WASD and J/K/L/; for laptops", () => {
    expect(ACTIONS.map((a) => keys[a][0])).toEqual(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Space", "Enter", "ControlLeft", "AltLeft"]);
    expect(keys.fire).toEqual(["Space", "KeyJ"]);
    expect(isBound("KeyW")).toBe(true);
    expect(isBound("KeyZ")).toBe(false);
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

  // [two-player]
  test("player 2 has a table of their own: W/A/S/D, F, R, Q, E and the keypad", () => {
    expect(ACTIONS.map((a) => keys2[a][0])).toEqual(["KeyW", "KeyS", "KeyA", "KeyD", "KeyF", "KeyR", "KeyQ", "KeyE"]);
    expect(keys2.fire).toEqual(["KeyF", "Numpad0"]);
    expect(isBound("Numpad8")).toBe(true);
    // Rebinding swaps within player 2's table and leaves player 1's alone.
    expect(bindKey("fire", 0, "KeyW", 1)).toBe(true);
    expect(keys2.fire[0]).toBe("KeyW");
    expect(keys2.up[0]).toBe("KeyF");
    expect(keys.up).toEqual([...DEFAULT_KEYS.up]);
    clearKey("left", 1, 1);
    expect(keys2.left).toEqual(["KeyA", ""]);
    resetKeys(1);
    expect(keys2.up).toEqual([...DEFAULT_KEYS_2.up]);
    expect(setKeys({ ...structuredClone(keys2), fire: ["KeyZ", ""] }, 1)).toBe(true);
    expect(keys2.fire).toEqual(["KeyZ", ""]);
    expect(keys.fire).toEqual([...DEFAULT_KEYS.fire]);
    resetKeys(1);
  });

  test("the input rows cycle a player's gamepad, swapping with the other player's", () => {
    expect(pads).toEqual([0, 1]);
    cyclePad(0); // player 1 takes pad 2 (index 1) from player 2, who gets pad 1
    expect(pads).toEqual([1, 0]);
    cyclePad(1);
    expect(pads).toEqual([0, 1]); // player 2 → pad 2, player 1 takes pad 1 back
    cyclePad(1);
    cyclePad(1);
    expect(pads).toEqual([0, 3]);
    cyclePad(1); // past the last pad: none
    expect(pads).toEqual([0, -1]);
    expect(setPads([2, 2])).toBe(false);
    expect(setPads([-1, -1])).toBe(true);
    expect(setPads(["x", 1])).toBe(false);
    expect(setPads([0, 1])).toBe(true);
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
    bindKey("fire", 1, "KeyX", 1); // [two-player]
    cyclePad(1);
    savePrefs(store);
    const data = JSON.parse(store.getItem(PREFS_STORAGE_KEY)!);
    expect(data).toMatchObject({ version: PREFS_VERSION, musicVolume: 120, fxVolume: 36 });

    resetKeys();
    resetKeys(1);
    setPads([0, 1]);
    loadPrefs(store);
    expect([volume.tyrMusicVolume, volume.fxVolume]).toEqual([120, 36]);
    expect(keys.fire[0]).toBe("KeyZ");
    expect(keys2.fire).toEqual(["KeyF", "KeyX"]);
    expect(pads).toEqual([0, 2]);
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
