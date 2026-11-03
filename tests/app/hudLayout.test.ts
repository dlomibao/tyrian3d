// The remastered HUD frame (DECISIONS.md D61): the gauges' arithmetic, the frame's layout at the
// usual window shapes (the playfield always inside the opening, all four corners on screen), the
// camera fit behind it, and the Interface and Camera settings.
import * as THREE from "three";
import { describe, expect, test } from "vitest";
import {
  ammoSegments,
  BAR_H,
  CONSOLE_H,
  GAUGE_ROWS,
  gaugeRows,
  hudLayout,
  MAX_PIPS,
  OPENING_H,
  OPENING_MIN_W,
  pipCount,
  POWER_ROWS,
  powerPercent,
  powerRows,
  SIDEBAR_W,
  toFrameUnits,
} from "../../src/app/hudLayout";
import { CAMERA_TILT, CAMERA_TILT_GENTLE, CAMERA_TILT_OVERHEAD, fitCamera, PLAYFIELD_RECT, playfieldScreenAspect } from "../../src/render/view";
import { cameraStyle, DisplayChoice, interfaceStyle } from "../../src/core/displayStyle";
import { optionsRows, SettingsMenu } from "../../src/app/options";
import { cameraTilt } from "../../src/app/hud";
import { loadPrefs, PREFS_STORAGE_KEY, PREFS_VERSION, savePrefs, type PrefsStorage } from "../../src/app/prefs";

describe("gauges", () => {
  test("shield and armor: one 2-unit row per point, as JE_dBar3, clamped to the gauge", () => {
    expect(gaugeRows(0)).toBe(0);
    expect(gaugeRows(-3)).toBe(0);
    expect(gaugeRows(14)).toBe(14);
    expect(gaugeRows(28)).toBe(28);
    expect(gaugeRows(99)).toBe(GAUGE_ROWS);
  });

  test("power: power / 10 rows of the C's 90-pixel column, and a percent read-out", () => {
    expect(powerRows(0)).toBe(0);
    expect(powerRows(9)).toBe(0);
    expect(powerRows(455)).toBe(45);
    expect(powerRows(900)).toBe(POWER_ROWS);
    expect(powerRows(2000)).toBe(POWER_ROWS);
    expect(powerPercent(450)).toBe(50);
    expect(powerPercent(900)).toBe(100);
    expect(powerPercent(-5)).toBe(0);
  });

  test("weapon pips: one per power level, 11 at most, none without a weapon", () => {
    expect(pipCount(1, true)).toBe(1);
    expect(pipCount(5, true)).toBe(5);
    expect(pipCount(11, true)).toBe(MAX_PIPS);
    expect(pipCount(14, true)).toBe(MAX_PIPS);
    expect(pipCount(5, false)).toBe(0);
  });

  test("sidekick ammo: draw_segmented_gauge's tenths, the last one partial", () => {
    expect(ammoSegments(0, 0)).toEqual({ slots: 0, full: 0, partial: 0 });
    expect(ammoSegments(100, 100)).toEqual({ slots: 10, full: 10, partial: 0 });
    expect(ammoSegments(55, 100)).toEqual({ slots: 10, full: 5, partial: 0.5 });
    expect(ammoSegments(3, 5)).toEqual({ slots: 5, full: 3, partial: 0 });
    expect(ammoSegments(-2, 30)).toEqual({ slots: 10, full: 0, partial: 0 });
  });
});

describe("camera fit", () => {
  test("straight down, the playfield is 264x184 on screen; the more tilted, the wider", () => {
    expect(playfieldScreenAspect(CAMERA_TILT_OVERHEAD)).toBeCloseTo(264 / 184, 3);
    const gentle = playfieldScreenAspect(CAMERA_TILT_GENTLE);
    const steep = playfieldScreenAspect(CAMERA_TILT);
    expect(gentle).toBeGreaterThan(264 / 184 + 0.1);
    expect(steep).toBeGreaterThan(gentle + 0.4);
    // The gentle tilt leaves under a seventh of a 264x184 opening's height above the playfield.
    expect(184 - 264 / gentle).toBeLessThan(184 / 7);
  });

  test("the camera choices: Overhead 0°, Tilted 15° (the default), Steep 32°", () => {
    expect(cameraTilt("overhead")).toBeLessThan(1e-6);
    expect(THREE.MathUtils.radToDeg(cameraTilt("tilted"))).toBeCloseTo(15, 6);
    expect(THREE.MathUtils.radToDeg(cameraTilt("steep"))).toBeCloseTo(32, 6);
    expect(cameraStyle.values).toEqual(["overhead", "tilted", "steep"]);
    expect(cameraStyle.fallback).toBe("tilted");
  });

  test("at the playfield's own aspect, the fitted corners touch all four edges", () => {
    for (const tilt of [CAMERA_TILT, CAMERA_TILT_GENTLE, CAMERA_TILT_OVERHEAD]) {
      const camera = new THREE.PerspectiveCamera(40, playfieldScreenAspect(tilt), 0.1, 500);
      fitCamera(camera, PLAYFIELD_RECT, tilt, 1);
      const r = PLAYFIELD_RECT;
      const pts = [[r.x0, r.z0], [r.x1, r.z0], [r.x1, r.z1], [r.x0, r.z1]].map(([x, z]) => new THREE.Vector3(x, 0, z).project(camera));
      expect(Math.min(...pts.map((p) => p.x))).toBeCloseTo(-1, 2);
      expect(Math.max(...pts.map((p) => p.x))).toBeCloseTo(1, 2);
      expect(Math.min(...pts.map((p) => p.y))).toBeCloseTo(-1, 2);
      expect(Math.max(...pts.map((p) => p.y))).toBeCloseTo(1, 2);
    }
  });
});

describe("frame layout", () => {
  const tilted = playfieldScreenAspect(CAMERA_TILT_GENTLE);
  const steep = playfieldScreenAspect(CAMERA_TILT);
  const overhead = playfieldScreenAspect(CAMERA_TILT_OVERHEAD);
  const inside = (a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }) =>
    a.x >= b.x - 1e-6 && a.y >= b.y - 1e-6 && a.x + a.w <= b.x + b.w + 1e-6 && a.y + a.h <= b.y + b.h + 1e-6;
  const screens: [string, number, number][] = [
    ["16:10", 1600, 1000],
    ["16:9", 1920, 1080],
    ["21:9", 2560, 1080],
    ["4:3", 1024, 768],
    ["phone", 390, 844],
    ["phone landscape", 844, 390],
  ];

  for (const [name, W, H] of screens) {
    for (const [cam, aspect] of [["tilted", tilted], ["steep", steep], ["overhead", overhead]] as const) {
      test(`${name}, ${cam}: the playfield keeps its aspect, inside the opening, inside the window`, () => {
        const l = hudLayout(W, H, aspect);
        expect(l.playfield.w / l.playfield.h).toBeCloseTo(aspect, 6);
        expect(inside(l.playfield, l.opening)).toBe(true);
        expect(inside(l.opening, { x: 0, y: 0, w: W, h: H })).toBe(true);
        expect(l.originX + l.blockW * l.scale).toBeLessThanOrEqual(W + 1e-6);
        expect(l.originY + l.blockH * l.scale).toBeLessThanOrEqual(H + 1e-6);
        // The playfield sits on the opening's floor (the message bar, or the console).
        expect(l.playfield.y + l.playfield.h).toBeCloseTo(l.opening.y + l.opening.h, 6);
      });
    }
  }

  test("16:10 keeps the original's grid: a 264-unit opening, the 61-unit sidebar, the 16-unit bar", () => {
    const l = hudLayout(1600, 1000, tilted);
    expect(l.mode).toBe("landscape");
    expect(l.openingW).toBeCloseTo(OPENING_MIN_W, 6);
    expect(l.blockW).toBeCloseTo(OPENING_MIN_W + SIDEBAR_W, 6);
    expect(l.blockH).toBe(OPENING_H + BAR_H);
    expect(l.scale).toBeCloseTo(1600 / 325, 6);
  });

  test("overhead fills the opening exactly", () => {
    for (const [, W, H] of screens.filter(([n]) => n !== "phone")) {
      const l = hudLayout(W, H, overhead);
      expect(l.playfield.w).toBeCloseTo(l.opening.w, 4);
      expect(l.playfield.h).toBeCloseTo(l.opening.h, 4);
    }
  });

  test("a wide window widens the opening up to the tilted playfield's width", () => {
    for (const aspect of [tilted, steep]) {
      const l = hudLayout(2560, 1080, aspect);
      expect(l.openingW).toBeCloseTo(OPENING_H * aspect, 4);
      expect(l.playfield.w).toBeCloseTo(l.opening.w, 4);
    }
  });

  test("portrait: the playfield across the width, the console under it, the block centred", () => {
    const l = hudLayout(390, 844, tilted, { top: 47, right: 0, bottom: 34, left: 0 });
    expect(l.mode).toBe("portrait");
    expect(l.opening.w).toBeCloseTo(390, 6);
    expect(l.blockH - l.openingH).toBeCloseTo(CONSOLE_H, 9);
    expect(l.opening.y).toBeGreaterThanOrEqual(47);
    const above = l.originY - 47;
    const below = 844 - 34 - (l.originY + l.blockH * l.scale);
    expect(above).toBeCloseTo(below, 6);
  });

  test("frame units map back to window pixels", () => {
    const l = hudLayout(1920, 1080, tilted);
    expect(toFrameUnits(l, { x: l.originX, y: l.originY })).toEqual({ x: 0, y: 0 });
    const p = toFrameUnits(l, { x: l.opening.x + l.opening.w, y: l.opening.y + l.opening.h });
    expect(p.x).toBeCloseTo(l.openingW, 6);
    expect(p.y).toBeCloseTo(OPENING_H, 6);
    expect(l.viewBox.w * l.scale).toBeCloseTo(1920, 6);
  });
});

describe("Interface and Camera settings", () => {
  const memory = (): PrefsStorage & { data: Map<string, string> } => {
    const data = new Map<string, string>();
    return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
  };

  test("defaults: the remastered frame and the tilted camera; the URL overrides", () => {
    const c = new DisplayChoice("interface", ["frame", "minimal"] as const, "frame", "");
    expect(c.get()).toBe("frame");
    expect(new DisplayChoice("interface", ["frame", "minimal"] as const, "frame", "?interface=minimal").get()).toBe("minimal");
    expect(new DisplayChoice("interface", ["frame", "minimal"] as const, "frame", "?interface=bogus").get()).toBe("frame");
    expect(new DisplayChoice("camera", ["overhead", "tilted", "steep"] as const, "tilted", "?camera=steep").get()).toBe("steep");
  });

  test("a choice is kept, replaces the URL's, and tells its listeners", () => {
    const c = new DisplayChoice("camera", ["tilted", "overhead"] as const, "tilted", "?camera=overhead");
    const heard: string[] = [];
    c.listen((v) => heard.push(v));
    c.load("tilted"); // stored, but the URL still wins
    expect(c.get()).toBe("overhead");
    c.set("tilted");
    expect(c.get()).toBe("tilted");
    expect(c.storedValue()).toBe("tilted");
    expect(heard).toEqual(["tilted"]);
    c.load("nonsense");
    expect(c.storedValue()).toBeUndefined();
  });

  test("Options offers both under Graphics and switches them with left/right", () => {
    interfaceStyle.reset();
    cameraStyle.reset();
    const rows = optionsRows([], [], [], { interface: interfaceStyle.values, camera: cameraStyle.values });
    expect(rows.filter((r) => r.kind === "style").map((r) => r.label)).toEqual(["Interface", "Camera"]);
    expect(optionsRows([], [], [], { interface: ["frame"] }).some((r) => r.kind === "style")).toBe(false);
    const display = {
      interface: { styles: interfaceStyle.values, current: () => interfaceStyle.get(), set: (s: string) => interfaceStyle.is(s) && interfaceStyle.set(s) },
      camera: { styles: cameraStyle.values, current: () => cameraStyle.get(), set: (s: string) => cameraStyle.is(s) && cameraStyle.set(s) },
    };
    const menu = new SettingsMenu(rows, "sound", { sound: () => {}, styles: [], style: () => undefined, setStyle: () => {}, display, close: () => {} });
    menu.cur = rows.findIndex((r) => r.kind === "style" && r.which === "interface");
    menu.intent("right", "keys");
    expect(interfaceStyle.get()).toBe("minimal");
    expect(menu.helpText()).toMatch(/Remastered frame/);
    menu.cur = rows.findIndex((r) => r.kind === "style" && r.which === "camera");
    menu.intent("left", "keys");
    expect(cameraStyle.get()).toBe("overhead");
    menu.intent("left", "keys");
    expect(cameraStyle.get()).toBe("steep");
    interfaceStyle.reset();
    cameraStyle.reset();
  });

  test("the prefs keep both", () => {
    interfaceStyle.reset();
    cameraStyle.reset();
    const store = memory();
    interfaceStyle.set("minimal");
    cameraStyle.set("overhead");
    savePrefs(store);
    const saved = JSON.parse(store.data.get(PREFS_STORAGE_KEY)!);
    expect(saved).toMatchObject({ version: PREFS_VERSION, interface: "minimal", camera: "overhead" });
    interfaceStyle.reset();
    cameraStyle.reset();
    loadPrefs(store);
    expect(interfaceStyle.get()).toBe("minimal");
    expect(cameraStyle.get()).toBe("overhead");
    interfaceStyle.reset();
    cameraStyle.reset();
  });

  test("a camera saved as \"tilted\" before the gentle tilt (when it meant 32°) gets the new default", () => {
    cameraStyle.reset();
    const store = memory();
    store.setItem(PREFS_STORAGE_KEY, JSON.stringify({ version: PREFS_VERSION, camera: "tilted" }));
    loadPrefs(store);
    expect(cameraStyle.get()).toBe("tilted");
    expect(cameraTilt(cameraStyle.get())).toBe(CAMERA_TILT_GENTLE);
    cameraStyle.reset();
  });
});
