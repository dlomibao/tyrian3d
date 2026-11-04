// tools/terrain_hd.py over several levels of one tileset (DECISIONS.md D83): runs the Python suite
// tests/tools/terrain_hd_test.py (the merge keeps the atlas's tiles byte for byte; the new tiles'
// seams hold; held edge strips). Needs the game data and a Python with numpy, scipy and PIL
// (TERRAIN_PY, else the remaster project's .venv named in CLAUDE.md, else python3); skips otherwise,
// as on CI, which has neither.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, test } from "vitest";
import { DATA_DIR, hasData } from "../data/dataDir";

function findPython(): string | undefined {
  const tries = [process.env.TERRAIN_PY, "/Users/dlomibao/projects/tyrian3d-remaster/.venv/bin/python", "python3"];
  for (const py of tries) {
    if (!py || (py.includes("/") && !existsSync(py))) continue;
    const r = spawnSync(py, ["-c", "import numpy, scipy, PIL"], { encoding: "utf8" });
    if (r.status === 0) return py;
  }
  return undefined;
}

const python = hasData("tyrian1.lvl", "shapesz.dat", "palette.dat") ? findPython() : undefined;

describe.skipIf(!python)("terrain_hd.py, several levels of one tileset", () => {
  test("merge keeps the atlas byte for byte, seams hold", () => {
    const r = spawnSync(python!, ["-m", "unittest", "-v", "tests/tools/terrain_hd_test.py"], {
      cwd: resolve(__dirname, "../.."),
      env: { ...process.env, TYRIAN_DATA: resolve(DATA_DIR) },
      encoding: "utf8",
      timeout: 600_000,
    });
    if (r.status !== 0) console.log(r.stdout, r.stderr);
    expect(r.status).toBe(0);
    expect(r.stderr).toMatch(/\nOK/);
  }, 600_000);
});
