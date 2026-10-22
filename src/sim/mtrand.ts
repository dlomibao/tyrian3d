// Mersenne Twister (MT19937), ported from OpenTyrian src/mtrand.c so random spawns, spreads and
// firing follow the same sequences as the original for a given seed.

const N = 624;
const M = 397;
const MATRIX_A = 0x9908b0df;
const UPPER_MASK = 0x80000000;
const LOWER_MASK = 0x7fffffff;

/** MT_RAND_MAX */
export const MT_RAND_MAX = 0xffffffff;

const x = new Uint32Array(N);
let p0 = -1;
let p1 = 0;
let pm = 0;

export function mt_srand(seed: number): void {
  x[0] = seed >>> 0;
  for (let i = 1; i < N; i++) {
    const prev = x[i - 1];
    x[i] = (Math.imul(1812433253, prev ^ (prev >>> 30)) + i) >>> 0;
  }
  p0 = 0;
  p1 = 1;
  pm = M;
}

/** A random number on [0, 0xffffffff]. */
export function mt_rand(): number {
  if (p0 < 0) mt_srand(5489);
  let y = (x[pm++] ^ (((x[p0] & UPPER_MASK) | (x[p1] & LOWER_MASK)) >>> 1) ^ (x[p1] & 1 ? MATRIX_A : 0)) >>> 0;
  x[p0] = y;
  p0 = p1++;
  if (pm === N) pm = 0;
  if (p1 === N) p1 = 0;
  y ^= y >>> 11;
  y ^= (y << 7) & 0x9d2c5680;
  y ^= (y << 15) & 0xefc60000;
  y ^= y >>> 18;
  return y >>> 0;
}

/** A random number on [0, 1]. */
export function mt_rand_1(): number {
  return Math.fround(Math.fround(mt_rand()) / Math.fround(MT_RAND_MAX));
}

/** A random number on [0, 1). */
export function mt_rand_lt1(): number {
  return Math.fround(Math.fround(mt_rand()) / (Math.fround(MT_RAND_MAX) + 1));
}
