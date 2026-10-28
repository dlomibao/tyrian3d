import { describe, expect, it } from "vitest";
import { modelHeightFromUrl } from "../../src/render/modelHeight";

describe("modelHeightFromUrl", () => {
  it("is 1 without ?height or with a bad value", () => {
    expect(modelHeightFromUrl("")).toBe(1);
    expect(modelHeightFromUrl("?height=abc")).toBe(1);
    expect(modelHeightFromUrl("?height=0")).toBe(1);
    expect(modelHeightFromUrl("?height=-2")).toBe(1);
  });

  it("reads ?height and clamps it to 0.5..4", () => {
    expect(modelHeightFromUrl("?viewer=x&height=2.5")).toBe(2.5);
    expect(modelHeightFromUrl("?height=0.1")).toBe(0.5);
    expect(modelHeightFromUrl("?height=10")).toBe(4);
  });
});
