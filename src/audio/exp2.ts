// A correctly rounded 2^x for the OPL emulator.
//
// opl.c computes envelope and volume factors with pow(2.0, x) for non-integer x. JavaScript
// engines don't round Math.pow correctly (V8's is off by an ulp for about a quarter of the values
// the emulator uses), and those ulps occasionally flip an integer truncation downstream, which
// made the TypeScript port drift from the C by ±1 sample in a few songs. Evaluating 2^x in
// double-double precision and rounding once gives the correctly rounded result, which is what a
// good C libm (macOS, glibc) returns. It also makes the output identical across browsers.

const SPLITTER = 134217729; // 2^27 + 1, Veltkamp splitting constant

// ln 2 as a double-double.
const LN2_HI = 0.6931471805599453;
const LN2_LO = 2.3190468138462996e-17;

// Error-free transformations (Dekker / Knuth). Results are returned through these two slots to
// avoid allocating.
let rHi = 0;
let rLo = 0;

function twoSum(a: number, b: number): void {
  const s = a + b;
  const bb = s - a;
  rLo = a - (s - bb) + (b - bb);
  rHi = s;
}

function twoProd(a: number, b: number): void {
  const p = a * b;
  let t = SPLITTER * a;
  const aHi = t - (t - a);
  const aLo = a - aHi;
  t = SPLITTER * b;
  const bHi = t - (t - b);
  const bLo = b - bHi;
  rLo = aHi * bHi - p + aHi * bLo + aLo * bHi + aLo * bLo;
  rHi = p;
}

/** (aHi + aLo) * (bHi + bLo), normalized into rHi/rLo. */
function ddMul(aHi: number, aLo: number, bHi: number, bLo: number): void {
  twoProd(aHi, bHi);
  const pHi = rHi;
  const pLo = rLo + (aHi * bLo + aLo * bHi);
  twoSum(pHi, pLo);
}

/** (aHi + aLo) + (bHi + bLo), normalized into rHi/rLo. */
function ddAdd(aHi: number, aLo: number, bHi: number, bLo: number): void {
  twoSum(aHi, bHi);
  const sHi = rHi;
  const sLo = rLo + aLo + bLo;
  twoSum(sHi, sLo);
}

/** Correctly rounded 2^x for |x| well inside the normal range (|x| < 1000). */
export function exp2(x: number): number {
  const n = Math.round(x);
  if (x === n) return Math.pow(2, n); // exact
  const r = x - n; // exact, |r| <= 0.5

  // y = r * ln2 in double-double
  twoProd(r, LN2_HI);
  const yHi0 = rHi;
  const yLo0 = rLo + r * LN2_LO;
  twoSum(yHi0, yLo0);
  const yHi = rHi;
  const yLo = rLo;

  // e^y by Taylor series in double-double: sum y^k / k!. |y| <= 0.35, so 27 terms reach 2^-110.
  let sumHi = 1;
  let sumLo = 0;
  let termHi = 1;
  let termLo = 0;
  for (let k = 1; k <= 27; k++) {
    ddMul(termHi, termLo, yHi, yLo);
    // divide the term by k: q = term / k, corrected with the remainder
    const tHi = rHi;
    const tLo = rLo;
    const q1 = tHi / k;
    twoProd(q1, k);
    const rem = tHi - rHi - rLo + tLo;
    const q2 = rem / k;
    twoSum(q1, q2);
    termHi = rHi;
    termLo = rLo;
    ddAdd(sumHi, sumLo, termHi, termLo);
    sumHi = rHi;
    sumLo = rLo;
  }

  // Round the double-double once, then scale by 2^n (exact in the normal range).
  return (sumHi + sumLo) * Math.pow(2, n);
}
