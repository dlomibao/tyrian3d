"""Spinning red rod (newshf.shp frames 171, 190, 209, 228): a 3D version of its sprite.

Seen in episodes 1-4 (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16). A 12 px pink-red spindle lying
on the ground, round in section and pointed at both ends, brightest in the middle. Its four
frames turn it through 0, 45, 90 and 135 degrees, so each frame gets its own model (the same
spindle, turned and placed on that frame's pixels): newshf-171 (flat), -f2 (rising to the
right), -f3 (upright), -f4 (falling to the right).

Run: blender --background --python assets/blender/enemies/newshf-171.py [-- --preview out.png]
(the preview shows the first frame; the other frames get <name>-fN.png beside it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b095 as lib  # noqa: E402
import common  # noqa: E402

NAME = "newshf-171"
ROOT = common.repo_root(__file__)
G = lib.Grid(12, 14)
# Sprite frame -> the spindle's angle (degrees, counter-clockwise from sprite-right).
ANGLES = {171: 0, 190: 45, 209: 90, 228: 135}


def centroid(pixels):
    pts = [(c, r) for r, row in enumerate(pixels) for c, v in enumerate(row) if v >= 0]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def build(sprite, frame, name, coll):
    pal = lambda i, **kw: common.palette_material(sprite, i, "nshf171", **kw)  # noqa: E731
    mats = [
        pal(74, metallic=0.45, roughness=0.35),  # 0 rod
        pal(70, metallic=0.4, roughness=0.45),  # 1 darker tips
        pal(77, metallic=0.5, roughness=0.25),  # 2 bright middle band
    ]
    ROD, TIP, BAND = range(3)
    bm = bmesh.new()
    r = 1.5 / 12  # radius: the rod is 3 px across
    z = r  # it lies on the ground
    # Spindle along +Y (length 12 px), tips darker.
    common.loft(bm, [(-6.0 / 12, 0.0, 0.0, z), (-5.0 / 12, r * 0.55, r * 0.55, z), (-4.0 / 12, r * 0.8, r * 0.8, z)],
                sides=10, mat_index=TIP, cap_start=False, cap_end=False)
    common.loft(bm, [(-4.0 / 12, r * 0.8, r * 0.8, z), (-2.5 / 12, r * 0.95, r * 0.95, z), (-1.0 / 12, r, r, z),
                     (1.0 / 12, r, r, z), (2.5 / 12, r * 0.95, r * 0.95, z), (4.0 / 12, r * 0.8, r * 0.8, z)],
                sides=10, mat_index=ROD, cap_start=False, cap_end=False)
    common.loft(bm, [(4.0 / 12, r * 0.8, r * 0.8, z), (5.0 / 12, r * 0.55, r * 0.55, z), (6.0 / 12, 0.0, 0.0, z)],
                sides=10, mat_index=TIP, cap_start=False, cap_end=False)
    # A slightly proud band round the middle (the brightest pixels).
    common.loft(bm, [(-0.9 / 12, r * 1.08, r * 1.08, z), (0.9 / 12, r * 1.08, r * 1.08, z)], sides=10, mat_index=BAND)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    lib.rotate_since(bm, 0, math.radians(ANGLES[frame["index"]] - 90))
    c, rr = centroid(frame["pixels"])
    bmesh.ops.translate(bm, vec=(G.x(c), G.y(rr), 0), verts=bm.verts)
    return common.mesh_object(name, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    out = lib.preview_arg()
    for i, frame in enumerate(sprite["frames"]):
        name = NAME if i == 0 else f"{NAME}-f{i + 1}"
        obj = build(sprite, frame, name, coll)
        common.export_sprite_model(ROOT, [obj], f"enemies/{name}", lib.subset(sprite, [frame["index"]]))
        if out:
            path = out if i == 0 else str(Path(out).with_name(f"{name}.png"))
            lib.preview(ROOT, NAME, [obj], sprite, frame=i, out=path)


if __name__ == "__main__":
    main()
