// The player ship's wear by armour (src/render/damage/shipDamage.ts, D90): it follows the current
// armour both ways, with a hysteresis band, never latched; the reference is the ship's maximum
// (`initial_armor`); anything at or over it, or without a usable reference, is healthy. Ships drawn
// without armour (menus, the item screen's preview) are clean.
import * as THREE from "three";
import { describe, expect, test, vi } from "vitest";
import { DamageFrames } from "../../src/render/damage/damageFrames";
import { armourRatio, COVER, HEAVY, HYSTERESIS, LIGHT, ShipCondition, shipLevel, type ShipLevel } from "../../src/render/damage/shipDamage";
import { DrawListRenderer, playerOfKey } from "../../src/render/drawListRenderer";
import { PaletteTexture } from "../../src/render/paletteTexture";
import type { DrawList } from "../../src/sim/draw";

/** Levels along a run of armour values (of a reference of 100), from clean. */
function levels(armours: number[]): ShipLevel[] {
  let level: ShipLevel = 0;
  return armours.map((a) => (level = shipLevel(armourRatio(a, 100), level)));
}

describe("armourRatio", () => {
  test("armour over the reference is full, never more", () => {
    expect(armourRatio(150, 100)).toBe(1);
    expect(armourRatio(28, 20)).toBe(1);
    expect(armourRatio(100, 100)).toBe(1);
  });
  test("at 0 it's 0, never negative", () => {
    expect(armourRatio(0, 20)).toBe(0);
    expect(armourRatio(-5, 20)).toBe(0);
  });
  test("a missing or zero reference is healthy", () => {
    expect(armourRatio(3, 0)).toBe(1);
    expect(armourRatio(3, Number.NaN)).toBe(1);
    expect(armourRatio(3, undefined as unknown as number)).toBe(1);
    expect(armourRatio(Number.NaN, 20)).toBe(1);
  });
});

describe("shipLevel", () => {
  test("exactly at a threshold, going down, it stays the level above", () => {
    expect(shipLevel(LIGHT, 0)).toBe(0);
    expect(shipLevel(HEAVY, 1)).toBe(1);
    expect(shipLevel(LIGHT - 0.01, 0)).toBe(1);
    expect(shipLevel(HEAVY - 0.01, 1)).toBe(2);
  });

  test("down through the thresholds, then back up through them, with the hysteresis band", () => {
    const down = levels([100, 60, 51, 50, 49, 30, 26, 25, 24, 10, 0]);
    expect(down).toEqual([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2]);
    // From heavy at 0: up through 25% only past 25 + 3, through 50% only past 50 + 3.
    let level: ShipLevel = 2;
    const up = [10, 25, 26, 27, 28, 40, 50, 52, 53, 80, 100].map((a) => (level = shipLevel(armourRatio(a, 100), level)));
    expect(up).toEqual([2, 2, 2, 2, 1, 1, 1, 1, 0, 0, 0]);
  });

  test("hovering at a threshold doesn't flicker", () => {
    expect(levels([60, 49, 51, 49.5, 52, 49])).toEqual([0, 1, 1, 1, 1, 1]);
    let level: ShipLevel = 2;
    expect([24, 26, 24.5, 27, 24].map((a) => (level = shipLevel(armourRatio(a, 100), level)))).toEqual([2, 2, 2, 2, 2]);
  });

  test("a pickup from under 25% to over 50% goes straight to clean", () => {
    expect(shipLevel(armourRatio(60, 100), 2)).toBe(0);
    expect(shipLevel(armourRatio(LIGHT * 100 + HYSTERESIS * 100, 100), 2)).toBe(0);
    // Over the reference too.
    expect(shipLevel(armourRatio(150, 100), 2)).toBe(0);
  });

  test("never latched: the same armour gives the same level whichever way it came, outside the bands", () => {
    for (const a of [5, 20, 35, 45, 70, 100, 140]) {
      const fromClean = shipLevel(armourRatio(a, 100), 0);
      const fromHeavy = shipLevel(armourRatio(a, 100), 2);
      const inBand = (a / 100 >= HEAVY && a / 100 < HEAVY + HYSTERESIS) || (a / 100 >= LIGHT && a / 100 < LIGHT + HYSTERESIS);
      if (!inBand) expect(fromHeavy, `armour ${a}`).toBe(fromClean);
    }
  });
});

describe("ShipCondition", () => {
  test("eases toward each level and back, never past its range", () => {
    const c = new ShipCondition();
    c.update(100, 100, 0.016);
    expect(c.damaged).toBe(false);
    for (let i = 0; i < 200; i++) c.update(10, 100, 0.05);
    expect(c.level).toBe(2);
    expect(c.cover).toBeCloseTo(COVER[2]);
    // A pickup to 60%: back to clean, eased.
    c.update(60, 100, 0.05);
    expect(c.level).toBe(0);
    expect(c.cover).toBeGreaterThan(0);
    for (let i = 0; i < 200; i++) c.update(60, 100, 0.05);
    expect(c.cover).toBe(0);
    expect(c.damaged).toBe(false);
  });

  test("huge, zero and negative steps stay in range", () => {
    const c = new ShipCondition();
    c.update(0, 20, Infinity);
    expect(c.cover).toBe(COVER[2]);
    c.update(0, 20, -5);
    expect(c.cover).toBe(COVER[2]);
    c.update(30, 20, Infinity); // over the reference
    expect([c.level, c.cover]).toEqual([0, 0]);
    c.update(5, 0, Infinity); // no reference
    expect(c.damaged).toBe(false);
  });

  test("at 0 armour (the ship dying) it is heavy", () => {
    const c = new ShipCondition();
    c.update(0, 20, Infinity);
    expect(c.level).toBe(2);
  });
});

describe("where ships wear", () => {
  const list = (ships?: DrawList["ships"]): DrawList => ({ items: [], palette: 0, filter: -99, brightness: 0, screen: null, ships });
  const shipsOf = (r: DrawListRenderer) => (r as unknown as { ships: ShipCondition[] }).ships;

  test("a healthy ship, and ships drawn without armour (menus, the item screen), are clean", () => {
    vi.stubGlobal("location", { search: "" });
    const r = new DrawListRenderer();
    r.setDrawList(list([{ armor: 20, reference: 20 }, { armor: 28, reference: 20 }]));
    r.update(1, new THREE.PerspectiveCamera());
    expect(shipsOf(r).map((c) => c.damaged)).toEqual([false, false]);
    r.setDrawList(list([{ armor: 3, reference: 20 }, { armor: 15, reference: 20 }]));
    r.update(1, new THREE.PerspectiveCamera());
    // Two players, each by their own armour: the first heavy, the second clean.
    expect(shipsOf(r).map((c) => c.level)).toEqual([2, 0]);
    // The menus' and the item screen's draw lists carry no armour: clean at once.
    r.setDrawList(list());
    r.update(1, new THREE.PerspectiveCamera());
    expect(shipsOf(r).every((c) => !c.damaged)).toBe(true);
  });

  test("a clean ship's materials draw no damage; only a worn one's do", () => {
    const frames = new DamageFrames(new PaletteTexture());
    const material = new THREE.MeshStandardMaterial({ name: "pal_5" });
    const ship = new THREE.Mesh(new THREE.BoxGeometry(), material);
    const clean = new ShipCondition();
    frames.applyShip(ship, [material], clean, 2);
    const u = material.userData.damageUniforms;
    expect(u.uDmgOn.value).toBe(0);
    frames.applyShip(ship, [material], null, 2);
    expect(u.uDmgOn.value).toBe(0);
    const worn = new ShipCondition();
    worn.update(8, 20, Infinity);
    frames.applyShip(ship, [material], worn, 2);
    expect(u.uDmgOn.value).toBe(1);
    expect(u.uDmgCover.value).toBeCloseTo(COVER[1]);
    // Never a cut: the pattern's cut channel is empty.
    const data = (u.uDmgMask.value as THREE.DataTexture).image.data as Uint8Array;
    expect(data.filter((_, i) => i % 4 === 0).every((v) => v === 0)).toBe(true);
    // An enemy's damage after it (pooled clones) turns ship mode off.
    frames.apply(ship, [material], null);
    expect(u.uDmgOn.value).toBe(0);
    expect(u.uDmgCover.value).toBe(-1);
  });

  test("player ship draw keys", () => {
    expect([10000, 10001, 10002, 10100, 10101, 10140, 9999, 10200].map(playerOfKey)).toEqual([0, 0, -1, 1, 1, -1, -1, -1]);
  });
});
