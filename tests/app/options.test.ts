// The settings screen's rules (SettingsMenu in src/app/options.ts) and its volume sliders: what
// each intent, key and tap does, as the first, self-driven version of the screen did it.
import { beforeEach, describe, expect, test } from "vitest";
import { DEFAULT_KEYS, keys, resetKeys } from "../../src/app/bindings";
import { optionsRows, PAD_CHECK_HOLD_MS, SettingsMenu, VOLUME_CELLS, volumeCellsAt, volumeFill, type OptionsFocus } from "../../src/app/options";
import { S_CLICK, S_CLINK, S_CURSOR, S_SPRING } from "../../src/sim/sndmast";
import { DEFAULT_VOLUME, setVolumeHandler, volume, VOLUME_STEP } from "../../src/sim/volume";

beforeEach(() => {
  resetKeys();
  volume.tyrMusicVolume = DEFAULT_VOLUME;
  volume.fxVolume = DEFAULT_VOLUME;
  setVolumeHandler(() => {});
});

function setup(focus: OptionsFocus = "sound", styles: string[] = []) {
  const sounds: number[] = [];
  let style = styles[0];
  let closed = 0;
  const menu = new SettingsMenu(optionsRows(styles), focus, {
    sound: (n) => sounds.push(n),
    styles,
    style: () => style,
    setStyle: (s) => (style = s),
    close: () => closed++,
  });
  const rowOf = (kind: string) => menu.rows.findIndex((r) => r.kind === kind);
  return { menu, sounds, rowOf, style: () => style, closed: () => closed };
}

describe("volume sliders", () => {
  test("the bar lights the C's cells: volume / 12 of 21", () => {
    expect(VOLUME_CELLS).toBe(21);
    expect(volumeFill(0)).toBe(0);
    expect(volumeFill(DEFAULT_VOLUME)).toBeCloseTo(18 / 21);
    expect(volumeFill(255)).toBe(1);
  });

  test("a tap counts cells from the bar's start, and the far end is full volume", () => {
    expect(volumeCellsAt(0)).toBe(0);
    expect(volumeCellsAt(-0.2)).toBe(0);
    expect(volumeCellsAt(10 / 21)).toBe(10);
    expect(volumeCellsAt(1)).toBe(VOLUME_CELLS + 1);
  });
});

describe("SettingsMenu", () => {
  test("rows: volumes, a music style only with more than one, eight keys and reset per player, gamepad, done", () => {
    const keyRows = [...Array(8).fill("key"), "reset"];
    expect(optionsRows([]).map((r) => r.kind)).toEqual(["volume", "volume", ...keyRows, ...keyRows, "pad", "done"]);
    expect(optionsRows([]).flatMap((r) => ("player" in r ? [r.player] : []))).toEqual([...Array(9).fill(0), ...Array(9).fill(1)]);
    expect(optionsRows(["original", "remaster"]).map((r) => r.kind)).toContain("style");
  });

  test("where it opens: sound, keyboard, or the gamepad check", () => {
    expect(setup("sound").menu.row.kind).toBe("volume");
    expect(setup("keyboard").menu.row.kind).toBe("key");
    const pad = setup("joystick").menu;
    expect(pad.row.kind).toBe("pad");
    expect(pad.checking).toBe(true);
  });

  test("up and down wrap around the rows with a cursor sound", () => {
    const { menu, sounds } = setup();
    menu.intent("up", "keys");
    expect(menu.row.kind).toBe("done");
    menu.intent("down", "pad");
    expect(menu.cur).toBe(0);
    expect(sounds).toEqual([S_CURSOR, S_CURSOR]);
  });

  test("left and right change a volume by the C's step (JE_changeVolume), clinking at the ends", () => {
    const { menu, sounds } = setup();
    menu.intent("right", "keys");
    expect(volume.tyrMusicVolume).toBe(DEFAULT_VOLUME + VOLUME_STEP);
    menu.intent("right", "keys");
    menu.intent("right", "keys");
    expect(volume.tyrMusicVolume).toBe(255);
    expect(sounds).toEqual([S_CURSOR, S_CURSOR, S_CURSOR, S_CLINK]);
    menu.intent("down", "keys");
    menu.intent("left", "keys");
    expect(volume.fxVolume).toBe(DEFAULT_VOLUME - VOLUME_STEP);
  });

  test("a tap or drag on a bar sets the volume from its cell", () => {
    const { menu, sounds, rowOf } = setup("keyboard");
    menu.setVolumeCells(rowOf("volume") + 1, 10);
    expect(menu.cur).toBe(1);
    expect(volume.fxVolume).toBe(120);
    menu.setVolumeCells(0, VOLUME_CELLS + 1);
    expect(volume.tyrMusicVolume).toBe(255);
    expect(sounds).toEqual([S_CURSOR, S_CURSOR]);
  });

  test("music style: left/right and Enter cycle it, a tap picks one", () => {
    const { menu, rowOf, style } = setup("sound", ["original", "remaster", "orchestral"]);
    menu.cur = rowOf("style");
    menu.intent("left", "keys");
    expect(style()).toBe("orchestral");
    menu.intent("accept", "keys");
    expect(style()).toBe("original");
    menu.tap(rowOf("style"), { style: "remaster" });
    expect(style()).toBe("remaster");
  });

  test("binding a key: Enter waits, the next key binds that slot; reserved keys clink, Escape cancels", () => {
    const { menu, sounds } = setup("keyboard");
    menu.intent("right", "keys"); // the second slot
    menu.intent("accept", "keys");
    expect(menu.capturing).toBe(true);
    // Every key is taken while waiting, even the ones that are intents (Enter, arrows, Backspace).
    expect(menu.key("KeyQ")).toBe(true);
    expect(keys.up).toEqual(["ArrowUp", "KeyQ"]);
    expect(menu.capturing).toBe(false);
    menu.intent("accept", "keys");
    expect(menu.key("KeyQ", true)).toBe(true); // a repeat of the press is ignored
    expect(menu.capturing).toBe(true);
    menu.key("KeyP");
    expect(keys.up).toEqual(["ArrowUp", "KeyQ"]);
    menu.intent("accept", "keys");
    menu.key("Escape");
    expect(sounds).toEqual([S_CURSOR, S_CLICK, S_CLICK, S_CLICK, S_CLINK, S_CLICK, S_SPRING]);
  });

  test("binding a key used elsewhere swaps the two, as KEY CONFIG does", () => {
    const { menu } = setup("keyboard");
    menu.intent("accept", "keys");
    menu.key("ArrowDown");
    expect(keys.up[0]).toBe("ArrowDown");
    expect(keys.down[0]).toBe("ArrowUp");
  });

  test("while waiting for a key the pad's B cancels and its other buttons do nothing", () => {
    const { menu, sounds } = setup("keyboard");
    menu.intent("accept", "pad");
    menu.intent("down", "pad");
    expect(menu.capturing).toBe(true);
    expect(menu.row).toMatchObject({ kind: "key", action: "up" });
    menu.intent("back", "pad");
    expect(menu.capturing).toBe(false);
    expect(sounds.at(-1)).toBe(S_SPRING);
  });

  test("Delete or Backspace clears the slot on a key row; elsewhere Backspace is left to go back", () => {
    const { menu } = setup("keyboard");
    expect(menu.key("Backspace")).toBe(true);
    expect(keys.up).toEqual(["", DEFAULT_KEYS.up[1]]);
    menu.intent("right", "keys");
    expect(menu.key("Delete")).toBe(true);
    expect(keys.up).toEqual(["", ""]);
    menu.cur = 0;
    expect(menu.key("Backspace")).toBe(false);
  });

  test("Reset to Defaults restores every key", () => {
    const { menu, rowOf } = setup("keyboard");
    menu.key("Delete");
    menu.cur = rowOf("reset");
    menu.intent("accept", "keys");
    expect(keys.up).toEqual([...DEFAULT_KEYS.up]);
  });

  test("tapping a key slot waits for its key; a tap while waiting only cancels", () => {
    const { menu, rowOf } = setup();
    const right = rowOf("key") + 3;
    menu.tap(right, { slot: 1 });
    expect([menu.cur, menu.col, menu.capturing]).toEqual([right, 1, true]);
    menu.tap(0);
    expect([menu.cur, menu.capturing]).toEqual([right, false]);
    // A tap on a key row's label focuses it without waiting.
    menu.tap(right - 1);
    expect([menu.cur, menu.capturing]).toEqual([right - 1, false]);
  });

  test("the gamepad check: pad buttons are checked, not used; Esc or holding B ends it", () => {
    const { menu, sounds, rowOf } = setup();
    menu.cur = rowOf("pad");
    menu.intent("accept", "keys");
    expect(menu.checking).toBe(true);
    for (const i of ["up", "accept", "back"] as const) menu.intent(i, "pad");
    expect(menu.checking).toBe(true);
    expect(menu.padHold(true, 100)).toBe(false);
    expect(menu.padHold(false, 600)).toBe(false); // let go: start again
    expect(menu.padHold(true, 700)).toBe(false);
    expect(menu.padHold(true, 700 + PAD_CHECK_HOLD_MS)).toBe(false);
    expect(menu.padHold(true, 701 + PAD_CHECK_HOLD_MS)).toBe(true);
    expect(menu.checking).toBe(false);
    menu.intent("accept", "keys");
    menu.intent("back", "keys");
    expect(menu.checking).toBe(false);
    expect(sounds).toEqual([S_CLICK, S_SPRING, S_CLICK, S_SPRING]);
  });

  test("Escape, B and Done leave", () => {
    const a = setup();
    a.menu.intent("back", "pad");
    expect(a.closed()).toBe(1);
    expect(a.sounds).toEqual([S_SPRING]);
    const b = setup();
    b.menu.tap(b.rowOf("done"));
    expect(b.closed()).toBe(1);
    expect(b.sounds).toEqual([S_CLICK]);
  });
});

describe("sound style (local remaster packs)", () => {
  function setupBoth(music: string[], soundStyles: string[]) {
    const sounds: number[] = [];
    let musicStyle = music[0];
    let soundStyle = soundStyles[0];
    const menu = new SettingsMenu(optionsRows(music, soundStyles), "sound", {
      sound: (n) => sounds.push(n),
      styles: music,
      style: () => musicStyle,
      setStyle: (s) => (musicStyle = s),
      soundStyles,
      soundStyle: () => soundStyle,
      setSoundStyle: (s) => (soundStyle = s),
      close: () => {},
    });
    const rowOf = (which: string) => menu.rows.findIndex((r) => r.kind === "style" && r.which === which);
    return { menu, sounds, rowOf, music: () => musicStyle, sound: () => soundStyle };
  }

  test("a Sound style row follows the Music style row only when the pack has sound styles", () => {
    expect(optionsRows(["original", "synth"]).filter((r) => r.kind === "style")).toEqual([{ kind: "style", which: "music", label: "Music style" }]);
    const rows = optionsRows(["original", "synth"], ["original", "remaster"]);
    expect(rows.slice(0, 4).map((r) => (r.kind === "style" ? `style:${r.which}` : r.kind))).toEqual(["volume", "volume", "style:music", "style:sound"]);
    expect(optionsRows([], ["original", "remaster"]).filter((r) => r.kind === "style").map((r) => r.label)).toEqual(["Sound style"]);
    expect(optionsRows([], ["original"]).some((r) => r.kind === "style")).toBe(false);
  });

  test("left/right, Enter and taps switch the sound style, not the music's", () => {
    const { menu, rowOf, music, sound, sounds } = setupBoth(["original", "orchestral", "synth"], ["original", "remaster"]);
    menu.cur = rowOf("sound");
    menu.intent("right", "keys");
    expect(sound()).toBe("remaster");
    expect(music()).toBe("original");
    expect(sounds).toEqual([S_CURSOR]);
    menu.intent("accept", "keys");
    expect(sound()).toBe("original");
    menu.tap(rowOf("sound"), { style: "remaster" });
    expect(sound()).toBe("remaster");
    expect(menu.helpText()).toContain("sound effects");
    menu.cur = rowOf("music");
    menu.intent("left", "keys");
    expect(music()).toBe("synth");
    expect(sound()).toBe("remaster");
  });
});
