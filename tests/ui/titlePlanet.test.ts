// The title backdrop's shot (src/ui/titlePlanet.ts, D64): the planet's framing by aspect, the push-in
// and sunrise over time, the paint's resolution caps and the Talon flights' timing; and the logo
// art (public/art/title/), whose shapes must stay the traced outline.
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { FLIGHT_PERIOD, FLIGHTS, flightProgress, landscapeAmount, paintSize, STILL_TIME, titleShot } from "../../src/ui/titlePlanet";

describe("titleShot", () => {
  test("landscape screens frame the planet from the top left down the right; portrait ones smaller", () => {
    expect(landscapeAmount(0.46)).toBe(0);
    expect(landscapeAmount(1.6)).toBe(1);
    const land = titleShot(0, 1.6);
    const port = titleShot(0, 0.46);
    expect(land.planet[0]).toBeLessThan(0); // centre left of the middle
    expect(land.planet[1]).toBeLessThan(0); // and below it
    expect(port.planet[2]).toBeLessThan(land.planet[2]);
  });

  test("the sun starts behind the limb and climbs clear of it; the push-in settles", () => {
    const at = (t: number) => {
      const s = titleShot(t, 1.6);
      const [cx, cy, r] = s.planet;
      return { alt: Math.hypot(s.sun[0] - cx, s.sun[1] - cy) - r, vis: s.sun[2], dawn: s.sun[3], r };
    };
    expect(at(0).alt).toBeLessThan(0);
    expect(at(0).vis).toBe(0);
    expect(at(STILL_TIME).alt).toBeGreaterThan(0.03);
    expect(at(STILL_TIME).vis).toBe(1);
    expect(at(200).r).toBeGreaterThan(at(0).r);
    expect(at(400).r - at(200).r).toBeLessThan(0.01);
    // The sun stays on screen (x within the half-width, y within the half-height).
    for (const aspect of [0.46, 1, 1.6, 2.33]) {
      const [sx, sy] = titleShot(STILL_TIME, aspect).sun;
      expect(Math.abs(sx)).toBeLessThan(aspect / 2);
      expect(Math.abs(sy)).toBeLessThan(0.5);
    }
  });

  test("the light is a unit vector from the sun's side", () => {
    const [x, y, z] = titleShot(10, 1.6).light;
    expect(Math.hypot(x, y, z)).toBeCloseTo(1, 6);
    expect(x).toBeGreaterThan(0);
  });
});

describe("paintSize", () => {
  test("never above CSS pixels, under 0.9 MP, and a quarter of that on the half-resolution path", () => {
    const desk = paintSize(1920, 1080, 1, false);
    expect(desk.width * desk.height).toBeLessThanOrEqual(0.9e6 * 1.01);
    const phone = paintSize(390, 844, 3, false);
    expect(phone.width).toBeLessThanOrEqual(390);
    const small = paintSize(800, 500, 1, false);
    expect(small.width).toBe(600); // 0.75 of CSS pixels at dpr 1
    const half = paintSize(1920, 1080, 1, true);
    expect(half.width).toBeCloseTo(desk.width / 2, -1);
  });
});

describe("flights", () => {
  test("each pass fits in the period, and they don't overlap", () => {
    for (const f of FLIGHTS) expect(f.start + f.duration).toBeLessThanOrEqual(FLIGHT_PERIOD);
    const sorted = [...FLIGHTS].sort((a, b) => a.start - b.start);
    for (let i = 1; i < sorted.length; i++) expect(sorted[i].start).toBeGreaterThanOrEqual(sorted[i - 1].start + sorted[i - 1].duration);
  });

  test("progress runs 0 to 1 during a pass and repeats every period", () => {
    const f = FLIGHTS[0];
    expect(flightProgress(f, f.start - 0.5)).toBeNull();
    expect(flightProgress(f, f.start)).toBe(0);
    expect(flightProgress(f, f.start + f.duration / 2)).toBeCloseTo(0.5);
    expect(flightProgress(f, f.start + FLIGHT_PERIOD + 1)).toBeCloseTo(1 / f.duration);
  });
});

describe("the logo art", () => {
  const read = (name: string) => readFileSync(new URL(`../../public/art/title/${name}`, import.meta.url), "utf8");
  test("the copper logo and the silhouette are the same traced outline, and nothing in them animates", () => {
    const logo = read("tyrian-logo.svg");
    const mask = read("tyrian-logo-mask.svg");
    const d = (svg: string) => /<path[^>]* d="([^"]+)"/.exec(svg)?.[1];
    expect(d(logo)).toBeTruthy();
    expect(d(logo)).toBe(d(mask));
    expect(logo).toContain('viewBox="0 0 304 121"');
    expect(logo).not.toMatch(/<animate/);
    expect(logo).not.toMatch(/<image|href="(?!#)/); // no embedded or linked bitmaps
  });
});
