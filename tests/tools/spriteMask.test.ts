// tools/sprite_mask.py (DECISIONS.md D74): the ink border, the inner mask a model's top view matches,
// the thin parts' free border, and --measure. Runs the tool with the system's python3 on small
// made-up sprites (reference/ is not in git), and skips if there is no python3.
import { describe, expect, test } from "vitest";
import { spawnSync } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const TOOL = join(__dirname, "../../tools/sprite_mask.py");
const hasPython = spawnSync("python3", ["--version"]).status === 0;

/** A reference/models folder with one sprite per entry (rows of palette indices, -1 transparent). */
function refDir(sprites: Record<string, number[][]>): string {
  const dir = mkdtempSync(join(tmpdir(), "sprite-mask-"));
  for (const [name, rows] of Object.entries(sprites)) {
    mkdirSync(join(dir, name));
    const doc = {
      sprites: [{ frames: [7] }],
      colors: { "1": [12, 12, 12], "5": [200, 150, 90], "18": [44, 24, 4] },
      frames: [{ index: 7, pixels: rows.map((r) => r.join(" ")) }],
    };
    writeFileSync(join(dir, name, "sprite.json"), JSON.stringify(doc));
  }
  return dir;
}

function run(args: string[]): string {
  const r = spawnSync("python3", [TOOL, ...args], { encoding: "utf8" });
  if (r.status !== 0) throw new Error(r.stderr);
  return r.stdout;
}

const _ = -1;
// A 2x3 body in ink (palette 1) with an arm one colour pixel thick reaching the picture's right edge.
const SHIP = [
  [_, _, _, _, _, _, _, _],
  [_, 1, 1, 1, 1, _, _, _],
  [_, 1, 5, 5, 1, _, _, _],
  [_, 1, 5, 5, 5, 1, 1, 1],
  [_, 1, 5, 5, 5, 5, 5, 1],
  [_, 1, 5, 5, 5, 1, 1, 1],
  [_, 1, 1, 1, 1, _, _, _],
];
// Colour to the edge, with a dark shading step (palette 18, luma 28) that isn't ink.
const BARE = [
  [_, 5, 5, _],
  [5, 5, 18, 5],
  [_, 18, 18, _],
];

describe.skipIf(!hasPython)("sprite_mask.py", { timeout: 60_000 }, () => {
  const ref = refDir({ ship: SHIP, bare: BARE });

  test("finds the ink border, the inner mask and the thin arm's free border", () => {
    const info = JSON.parse(run(["ship", "--ref", ref, "--json"]));
    expect(info.kind).toBe("closed");
    expect(info.ring_ink).toBe(1);
    expect(info.opaque_px).toBe(33);
    expect(info.border_px).toBe(20);
    expect(info.inner_px).toBe(13);
    // The arm's ink beyond the body (its inside is one pixel thick) may go either way.
    expect(info.free_px).toBe(5);
    expect(info.masks).toEqual(["........", ".oooo...", ".o##o...", ".o###ooo", ".o#####o", ".o###ooo", ".oooo..."]);
  });

  test("a sprite without ink keeps its whole outline", () => {
    const info = JSON.parse(run(["bare", "--ref", ref, "--json"]));
    expect(info.kind).toBe("none");
    expect(info.border_px).toBe(0);
    expect(info.inner_px).toBe(info.opaque_px);
  });

  test("--measure scores a top view against both masks", () => {
    const dir = mkdtempSync(join(tmpdir(), "sprite-mask-png-"));
    const inner = join(dir, "inner.png");
    const outer = join(dir, "outer.png");
    run(["ship", "--ref", ref, "--png", inner, "--inner", "--scale", "4"]);
    run(["ship", "--ref", ref, "--png", outer, "--scale", "4"]);
    const atInner = JSON.parse(run(["ship", "--ref", ref, "--json", "--measure", inner])).measure;
    expect(atInner).toMatchObject({ k: 4, iou_rule: 1, iou_rule_grid: 1, iou_inner: 1, edge_vs_inner_px: 0 });
    expect(atInner.iou_outer).toBeCloseTo(13 / 33, 3);
    const atOuter = JSON.parse(run(["ship", "--ref", ref, "--json", "--measure", outer])).measure;
    expect(atOuter.iou_outer).toBe(1);
    // The free arm border doesn't count against it; the body's ink does.
    expect(atOuter.iou_rule).toBeCloseTo(13 / 28, 3);
    expect(atOuter.edge_vs_inner_px).toBeGreaterThan(0.5);
  });
});
