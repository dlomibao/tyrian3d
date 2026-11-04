// The HUD's touch targets (DECISIONS.md D99): the rear gun's box and MODE lamps change the rear
// mode, a sidekick box fires that sidekick while held. Their geometry, the switch that turns them
// on, and the Controls input they set.
import { afterEach, describe, expect, test, vi } from "vitest";
import { Controls } from "../../src/app/controls";
import { growTarget, hudTargets, TARGET_MIN_PX, type HudTarget } from "../../src/app/hudFrame";
import { hudLayout, SIDEBAR_W } from "../../src/app/hudLayout";
import { touchHudParam, touchHudWanted } from "../../src/app/touchHud";
import { simInput } from "../../src/sim/input";

const ASPECT = 1.3;
const PHONES: [string, number, number][] = [
  ["390x844", 390, 844],
  ["375x667", 375, 667],
  ["844x390", 844, 390],
  ["667x375", 667, 375],
];
const px = (t: HudTarget, l: ReturnType<typeof hudLayout>) => ({
  x: t.x * l.scale + l.originX,
  y: t.y * l.scale + l.originY,
  w: t.w * l.scale,
  h: t.h * l.scale,
});
const overlap = (a: { x: number; y: number; w: number; h: number }, b: { x: number; y: number; w: number; h: number }) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

describe("growTarget", () => {
  test("grows a small box evenly to the minimum", () => {
    expect(growTarget({ x: 10, y: 10, w: 4, h: 4 }, 10)).toEqual({ x: 7, y: 7, w: 10, h: 10 });
  });
  test("leaves a big box alone", () => {
    expect(growTarget({ x: 0, y: 0, w: 20, h: 30 }, 10)).toEqual({ x: 0, y: 0, w: 20, h: 30 });
  });
  test("a neighbour's limit stops it, and the room it lacked is taken from the other side", () => {
    expect(growTarget({ x: 0, y: 10, w: 20, h: 4 }, 10, { top: 10 })).toEqual({ x: 0, y: 10, w: 20, h: 10 });
    expect(growTarget({ x: 0, y: 10, w: 20, h: 4 }, 10, { top: 9, bottom: 16 })).toEqual({ x: 0, y: 9, w: 20, h: 7 });
  });
});

describe.each(PHONES)("targets at %s", (_name, w, h) => {
  const layout = hudLayout(w, h, ASPECT);
  const targets = hudTargets(layout);
  const pxs = targets.map((t) => ({ t, p: px(t, layout) }));

  test("a rear-mode target and both sidekicks, on the window", () => {
    expect(new Set(targets.map((t) => t.id))).toEqual(new Set(["rearMode", "sk0", "sk1"]));
    for (const { p } of pxs) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.x + p.w).toBeLessThanOrEqual(w + 0.5);
      expect(p.y + p.h).toBeLessThanOrEqual(h + 0.5);
    }
  });

  test("none covers the playfield, and different targets never overlap", () => {
    const opening = layout.opening;
    for (const { p } of pxs) expect(overlap(p, opening)).toBe(false);
    for (const a of pxs) for (const b of pxs) if (a !== b && a.t.id !== b.t.id) expect(overlap(a.p, b.p)).toBe(false);
  });

  test("each is about a finger wide and tall (44 px, a little less where a neighbour is in the way)", () => {
    for (const { t, p } of pxs) {
      expect(p.w, `${t.id} wide`).toBeGreaterThanOrEqual(TARGET_MIN_PX * 0.85);
      // Portrait's MODE row has the score box under it: ~33 px there, but the rear box beside it is 44.
      expect(p.h, `${t.id} tall`).toBeGreaterThanOrEqual(TARGET_MIN_PX * 0.7);
    }
    for (const id of ["rearMode", "sk0", "sk1"]) expect(Math.max(...pxs.filter(({ t }) => t.id === id).map(({ p }) => p.h)), id).toBeGreaterThanOrEqual(TARGET_MIN_PX * 0.85);
    if (layout.mode === "portrait") for (const { t, p } of pxs) if (t.id !== "rearMode") expect(p.h).toBeGreaterThanOrEqual(TARGET_MIN_PX - 0.5);
  });

  test("landscape: all in the sidebar, right of the opening", () => {
    if (layout.mode !== "landscape") return;
    const sidebarLeft = layout.originX + (layout.openingW - 259 + 284) * layout.scale;
    for (const { p } of pxs) {
      expect(p.x).toBeGreaterThanOrEqual(sidebarLeft - 0.5);
      expect(p.x + p.w).toBeLessThanOrEqual(layout.originX + (layout.openingW + SIDEBAR_W) * layout.scale + 0.5);
    }
  });
});

test("targets are placed again for each layout (the sidebar follows the opening's width)", () => {
  const a = hudTargets(hudLayout(844, 390, 1.0));
  const b = hudTargets(hudLayout(844, 390, 1.6));
  expect(a[0].x).not.toBe(b[0].x);
});

describe("turning them on", () => {
  test("the URL forces them either way", () => {
    expect(touchHudParam("?touchhud=1")).toBe(true);
    expect(touchHudParam("?touchhud=0")).toBe(false);
    expect(touchHudParam("?debug=play")).toBeNull();
  });
  test("a coarse pointer, or a finger as the last input, wants them; a mouse or keys don't", () => {
    expect(touchHudWanted(null, true, "keys")).toBe(true);
    expect(touchHudWanted(null, false, "touch")).toBe(true);
    expect(touchHudWanted(null, false, "mouse")).toBe(false);
    expect(touchHudWanted(null, false, "keys")).toBe(false);
    expect(touchHudWanted(false, true, "touch")).toBe(false);
    expect(touchHudWanted(true, false, undefined)).toBe(true);
  });
});

describe("Controls: what a target presses", () => {
  afterEach(() => vi.unstubAllGlobals());
  const make = () => {
    vi.stubGlobal("window", { addEventListener: () => {} });
    vi.stubGlobal("document", { addEventListener: () => {}, pointerLockElement: null });
    vi.stubGlobal("navigator", { getGamepads: () => [] });
    return new Controls();
  };

  test("a sidekick is held while the finger is, and a tap shorter than a tick still counts once", () => {
    const c = make();
    c.touchAction("leftSidekick", true);
    expect(c.sample().leftSidekick).toBe(true);
    expect(c.sample().leftSidekick).toBe(true);
    c.touchAction("leftSidekick", false);
    expect(c.sample().leftSidekick).toBe(false);
    c.touchAction("rightSidekick", true);
    c.touchAction("rightSidekick", false); // down and up between two ticks
    expect(c.sample().rightSidekick).toBe(true);
    expect(c.sample().rightSidekick).toBe(false);
  });

  test("a target never steers or fires: touches that began on one aren't the canvas's", () => {
    const c = make();
    c.touchAction("changeFire", true);
    const s = c.sample();
    expect(s.changeFire).toBe(true);
    expect(s.mouseLeft).toBe(false);
    expect(s.mouseXR).toBe(0);
    expect(s.mouseYR).toBe(0);
    c.touchAction("changeFire", false);
    expect(simInput.changeFire).toBe(true); // this tick's sample; the next one clears it
    expect(c.sample().changeFire).toBe(false);
  });
});
