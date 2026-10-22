import { describe, expect, it } from "vitest";
import { exp2 } from "../../src/audio/exp2";
import { Opl } from "../../src/audio/opl";

/** Programs channel 0 with a plain FM tone and keys it on. */
function keyOnTone(opl: Opl): void {
  opl.write(0x01, 0x20); // waveform select enable
  opl.write(0x20, 0x01); // modulator: multiplier 1
  opl.write(0x23, 0x01); // carrier: multiplier 1
  opl.write(0x40, 0x3f); // modulator silent: the carrier is a pure sine
  opl.write(0x43, 0x00); // carrier at full volume
  opl.write(0x60, 0xf0); // modulator: fast attack
  opl.write(0x63, 0xf0); // carrier: fast attack
  opl.write(0x80, 0x77);
  opl.write(0x83, 0x77);
  opl.write(0xa0, 0x44); // F-number 0x244 = 580: 580 * 49716 / 2^16 = 440 Hz at block 4
  opl.write(0xc0, 0x00);
  opl.write(0xb0, 0x32); // key on, block 4, F-number high bits
}

describe("OPL emulator", () => {
  it("is silent until a note is keyed on", () => {
    const opl = new Opl(44100);
    const buf = new Int16Array(4410);
    opl.getSample(buf, 0, buf.length);
    expect(buf.every((s) => s === 0)).toBe(true);
  });

  it("produces a tone after register writes", () => {
    const opl = new Opl(44100);
    keyOnTone(opl);
    const buf = new Int16Array(4410);
    opl.getSample(buf, 0, buf.length);
    const peak = buf.reduce((m, s) => Math.max(m, Math.abs(s)), 0);
    expect(peak).toBeGreaterThan(1000);

    // 440 Hz: about 44 rising zero crossings in 0.1 s.
    let crossings = 0;
    for (let i = 1; i < buf.length; i++) if (buf[i - 1] < 0 && buf[i] >= 0) crossings++;
    expect(crossings).toBeGreaterThanOrEqual(42);
    expect(crossings).toBeLessThanOrEqual(46);
  });

  it("releases to silence after key off", () => {
    const opl = new Opl(44100);
    keyOnTone(opl);
    const buf = new Int16Array(4410);
    opl.getSample(buf, 0, buf.length);
    opl.write(0xb0, 0x12); // key off
    const tail = new Int16Array(44100 * 3);
    opl.getSample(tail, 0, tail.length);
    expect(tail.subarray(tail.length - 1000).every((s) => s === 0)).toBe(true);
  });

  it("renders the same regardless of how the output is chunked", () => {
    const a = new Opl(48000);
    const b = new Opl(48000);
    keyOnTone(a);
    keyOnTone(b);
    const whole = new Int16Array(3000);
    a.getSample(whole, 0, whole.length);
    const chunked = new Int16Array(3000);
    for (let off = 0; off < chunked.length; off += 128) b.getSample(chunked, off, Math.min(128, chunked.length - off));
    expect(chunked).toEqual(whole);
  });
});

/** Parses C's printf("%a") output for a normal double, e.g. "0x1.8p-1". */
function hexFloat(s: string): number {
  const m = /^0x1\.([0-9a-f]*)p([+-]\d+)$/.exec(s);
  if (!m) throw new Error(s);
  const frac = m[1].padEnd(13, "0");
  const view = new DataView(new ArrayBuffer(8));
  view.setUint32(0, ((Number(m[2]) + 1023) << 20) | Number.parseInt(frac.slice(0, 5), 16));
  view.setUint32(4, Number.parseInt(frac.slice(5), 16));
  return view.getFloat64(0);
}

describe("exp2", () => {
  it("is exact for integer exponents", () => {
    expect(exp2(-14)).toBe(2 ** -14);
    expect(exp2(3)).toBe(8);
  });

  // pow(2, x) as printed by macOS libm (%a) for exponents opl.c uses, where V8's Math.pow is an
  // ulp off. opl.c's output depends on these bits.
  it.each([
    [-0.5, "0x1.6a09e667f3bcdp-1"],
    [-14.25, "0x1.ae89f995ad3adp-15"],
    [-14.375, "0x1.8ace5422aa0dbp-15"],
    [-14.53125, "0x1.6247eb03a5585p-15"],
  ])("2^%d is correctly rounded", (x, expected) => {
    expect(exp2(x)).toBe(hexFloat(expected));
  });
});
