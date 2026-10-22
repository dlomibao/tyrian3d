import { expect, test } from "vitest";
import { FixedStepper } from "../../src/core/fixedStep";

test("runs whole ticks and carries the remainder", () => {
  const s = new FixedStepper(10);
  expect(s.advance(25)).toEqual({ steps: 2, alpha: 0.5 });
  expect(s.advance(5)).toEqual({ steps: 1, alpha: 0 });
});

test("caps catch-up after a long stall", () => {
  const s = new FixedStepper(10, 4);
  expect(s.advance(1000)).toEqual({ steps: 4, alpha: 0 });
});
