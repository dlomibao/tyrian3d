import { expect, test } from "vitest";
import { mt_rand, mt_srand } from "../../src/sim/mtrand";

// MT19937 reference values for the default seed 5489: the 1st output and the 10000th output.
test("matches MT19937 for the default seed", () => {
  mt_srand(5489);
  expect(mt_rand()).toBe(3499211612);
  for (let i = 2; i < 10000; i++) mt_rand();
  expect(mt_rand()).toBe(4123659995);
});

test("reseeding restarts the sequence", () => {
  mt_srand(32402394);
  const a = [mt_rand(), mt_rand(), mt_rand()];
  mt_srand(32402394);
  expect([mt_rand(), mt_rand(), mt_rand()]).toEqual(a);
});
