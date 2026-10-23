"""Spinning blade (newshs.shp frames 171, 190, 209, 228): a 3D version of its sprites.

A small grey ground object (levels 1.21, 1.23, 1.25, 2.6, 3.15): a pointed, double-edged steel
blade, widest in the middle with a ridge down its length, on a short pin. Its four frames turn it
in 45 degree steps, so each angle is its own model: newshs-171 (top-left to bottom-right),
-f2 (upright), -f3 (bottom-left to top-right) and -f4 (level).

Run: blender --background --python assets/blender/enemies/newshs-171.py [-- --preview out.png]
(the preview is the first frame; the others go next to it as <name>-f2.png ...).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b080 as L  # noqa: E402
import common  # noqa: E402

NAME = "newshs-171"
ROOT = common.repo_root(__file__)
U = L.U

# frame -> (model suffix, angle of the blade from upright, centre offset in pixels)
FRAMES = [(171, "", 45, (0.0, 0.0)), (190, "-f2", 0, (0.5, 0.0)),
          (209, "-f3", -45, (0.0, 0.0)), (228, "-f4", 90, (0.0, 0.5))]


def build(sprite, name, angle, offset):
    coll = common.reset_collection(name)
    m = L.Mats(name, sprite["colors"])
    BLADE = m(11, metallic=0.85, roughness=0.25)
    PIN = m(6, metallic=0.6, roughness=0.4)
    bm = bmesh.new()

    zc, hz = 0.11, 0.05
    # Half widths (px) along the blade, from tip to tip: pointed ends, a broad flat middle.
    prof = [(6.1, 0.0), (5.0, 0.5), (3.6, 1.0), (2.2, 1.7), (0.7, 2.1), (-0.7, 2.1), (-2.2, 1.7),
            (-3.6, 1.0), (-5.0, 0.5), (-6.1, 0.0)]
    rings = []
    for y, w in prof:
        if w == 0:
            rings.append([(0.0, y * U, zc)])
        else:
            h = hz * min(1.0, w / 1.4)
            rings.append([(w * U, y * U, zc), (0.0, y * U, zc + h), (-w * U, y * U, zc), (0.0, y * U, zc - h)])
    L.ring_loft(bm, rings, BLADE, smooth=True)
    # The pin it spins on.
    L.tube_z(bm, [(0.0, 0.0, 0.0, 0.05, 0.05), (zc, 0.0, 0.0, 0.04, 0.04)], sides=8, mat=PIN)

    L.rotate_z(bm, 0, math.radians(angle))
    bm.verts.ensure_lookup_table()
    for v in bm.verts:
        v.co.x += offset[0] * U
        v.co.y += offset[1] * U
    return L.to_object(name, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    out = sys.argv[sys.argv.index("--preview") + 1] if "--preview" in sys.argv else None
    for i, (frame, suffix, angle, offset) in enumerate(FRAMES):
        name = NAME + suffix
        obj = build(sprite, name, angle, offset)
        sprites = [dict(s, frames=[frame]) for s in sprite["sprites"]]
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", sprites)
        if out:
            path = out if i == 0 else str(Path(out).with_name(f"{name}.png"))
            L.preview([obj], ROOT, NAME, sprite, frame=i, out=path)


if __name__ == "__main__":
    main()
