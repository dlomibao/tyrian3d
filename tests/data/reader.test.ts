import { expect, test } from "vitest";
import { BinaryReader } from "../../src/data/reader";

test("reads little-endian, big-endian and signed values in sequence", () => {
  const r = new BinaryReader(
    new Uint8Array([0x01, 0x34, 0x12, 0x12, 0x34, 0xff, 0xfe, 0xff, 0x78, 0x56, 0x34, 0x12]),
  );
  expect(r.u8()).toBe(1);
  expect(r.u16()).toBe(0x1234);
  expect(r.u16be()).toBe(0x1234);
  expect(r.s8()).toBe(-1);
  expect(r.s16()).toBe(-2);
  expect(r.u32()).toBe(0x12345678);
  expect(r.remaining).toBe(0);
  expect(() => r.u8()).toThrow(RangeError);
});

test("respects the view of a Uint8Array into a larger buffer", () => {
  const buf = new Uint8Array([9, 9, 0x02, 0x01]);
  expect(new BinaryReader(buf.subarray(2)).u16()).toBe(0x0102);
});

test("pascalString clamps to the declared length and always skips the full storage", () => {
  const r = new BinaryReader(new Uint8Array([5, 65, 66, 67, 0, 7]));
  expect(r.pascalString(3)).toBe("ABC");
  expect(r.pos).toBe(4);
});
