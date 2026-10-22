// C float and unsigned-long helpers for the OpenTyrian port (added by the world port).

import { mt_rand } from "./mtrand";

/** C roundf: round half away from zero (JS Math.round rounds half toward +Infinity). */
export function roundf(x: number): number {
  const r = Math.floor(Math.abs(x) + 0.5);
  return x < 0 ? -r : r;
}

/** float (32-bit) multiply, as `a * b` on two floats in C. */
export const fmul = (a: number, b: number): number => Math.fround(Math.fround(a) * Math.fround(b));

/** float (32-bit) divide, as `a / b` on two floats in C. */
export const fdiv = (a: number, b: number): number => Math.fround(Math.fround(a) / Math.fround(b));

/**
 * `mt_rand() % n` where n is a signed int expression. mt_rand returns unsigned long (64-bit on
 * the platforms OpenTyrian targets), so a negative n converts to 2^64 + n and the modulo leaves
 * the 32-bit random value unchanged. n == 0 is undefined behaviour in C; it throws here.
 */
export function mt_rand_mod(n: number): number {
  if (n === 0) throw new Error("mt_rand() % 0");
  const r = mt_rand();
  return n > 0 ? r % n : r;
}
