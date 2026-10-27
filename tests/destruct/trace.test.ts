// Destruct against OpenTyrian's own C: tools/destruct-trace/build.sh runs the real destruct.c with
// the computer playing both sides and records a running digest of the whole game state (terrain,
// units, shots, explosions, walls, sounds) every 10 ticks, plus the RNG's next value at the end.
// The port must reproduce it exactly.
import { readFileSync } from "node:fs";
import { describe, expect, test } from "vitest";
import { hasData, readData } from "../data/dataDir";
import { destructTrace } from "./trace";

const fixture = readFileSync(new URL("./fixtures/destruct-trace.c.txt", import.meta.url), "utf8").trim().split("\n");

interface Case {
  seed: number;
  mode: number;
  ticks: number;
  lines: string[];
}

const cases: Case[] = [];
for (const line of fixture) {
  const m = /^C (\d+) (\d+) (\d+)$/.exec(line);
  if (m) cases.push({ seed: +m[1], mode: +m[2], ticks: +m[3], lines: [] });
  else cases[cases.length - 1].lines.push(line);
}

describe.skipIf(!hasData("tyrian.pic"))("destruct matches OpenTyrian's C", () => {
  test.each(cases)("seed $seed, mode $mode, $ticks ticks", ({ seed, mode, ticks, lines }) => {
    const ts = destructTrace(readData("tyrian.pic"), seed, mode, ticks);
    // Compare up to the first difference, so a failure names the tick to look at.
    const first = lines.findIndex((l, i) => l !== ts[i]);
    expect(first === -1 ? null : { line: first, c: lines[first], ts: ts[first] }).toBeNull();
    expect(ts.length).toBe(lines.length);
  });
});
