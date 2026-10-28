"""Prototype, option 3: keep a hand-made model's geometry, reshape its heights from the analysis.

    blender --background --python assets/blender/proto/reshape_heights.py -- <name> [--lo 0.6] [--hi 3]

Each vertex's z is multiplied by (wanted height / current height) at its pixel: wanted is the
generator's target_height.npy (analysis + overrides) and current is the hand-made model's own
height there (.shape/<name>/views-current/height.npy, from `tools/review_sheet.py <name>`). Both
are blurred first so the ratio follows parts, not single pixels, and the ratio is clamped to
[lo, hi]. Writes public/models/proto-reshape/<model path>.glb (review with `--which reshape`).
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent))
ROOT = next(p for p in HERE.parents if (p / "package.json").exists())
import common  # noqa: E402
from review_render import clear_scene, import_model  # noqa: E402

PX = 1 / 12


def blur(a, r=2):
    """Box blur of radius r that ignores nan."""
    v = np.nan_to_num(a)
    w = (~np.isnan(a)).astype(float)
    for axis in (0, 1):
        k = np.ones(2 * r + 1)
        v = np.apply_along_axis(lambda x: np.convolve(x, k, "same"), axis, v)
        w = np.apply_along_axis(lambda x: np.convolve(x, k, "same"), axis, w)
    return np.where(w > 0, v / np.maximum(w, 1e-9), np.nan)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    name = argv[0]
    lo = float(argv[argv.index("--lo") + 1]) if "--lo" in argv else 0.6
    hi = float(argv[argv.index("--hi") + 1]) if "--hi" in argv else 3.0
    work = ROOT / ".shape" / name
    doc = json.loads((work / "regions.json").read_text())
    W, H = doc["size"]
    want = blur(np.load(work / "target_height.npy"))
    have = blur(np.load(work / "views-current" / "height.npy"))
    ratio = np.clip(np.where(have > 0.75, want / np.maximum(have, 0.75), 1.0), lo, hi)
    ratio = np.nan_to_num(ratio, nan=1.0)
    clear_scene()
    from shape_model import model_paths, piece_path  # noqa: E402
    paths = model_paths()
    out_root = ROOT / "public" / "models" / "proto-reshape"
    done = set()
    for p in doc["pieces"]:
        if p["model"] in done:
            continue
        done.add(p["model"])
        before = set(bpy.data.objects)
        one = dict(doc, pieces=[p])
        meshes, _ = import_model(name, "current", one)
        cx = (p["x0"] + p["w"] / 2 - W / 2) * PX
        cy = -(p["y0"] + p["h"] / 2 - H / 2) * PX
        for o in meshes:
            mw = o.matrix_world.copy()
            inv = mw.inverted()
            for v in o.data.vertices:
                w = mw @ v.co
                px = int(np.clip(w.x / PX + W / 2, 0, W - 1))
                py = int(np.clip(-w.y / PX + H / 2, 0, H - 1))
                w.z *= float(ratio[py, px])
                v.co = inv @ w
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:  # back to the piece's own origin for export
            if o.parent is None:
                o.location = Vector(o.location) - Vector((cx, cy, 0))
        path = piece_path(p["model"], p.get("frame"), paths) if name.startswith("assembly-") else \
            json.loads((ROOT / "src" / "render" / "spriteModels" / f"{name}.json").read_text())["model"]
        common.export_glb([o for o in new if o.type == "MESH"], out_root / f"{path}.glb")
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
    print(f"reshaped {name}: ratio {ratio.min():.2f}..{ratio.max():.2f}, mean {ratio.mean():.2f}")


if __name__ == "__main__":
    main()
