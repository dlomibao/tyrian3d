"""Twisted fire column (newsh5.shp frames 53 over 91): a 3D version of its sprites.

Seen in episode 4 (level 25). Two 2x2 enemies stacked make one 24x56 px column of fire: two
burning strands wound round each other like a rope, a thin flickering tip at the top and a
thicker, knotted mass below that narrows to a point. Where the strands part, the sprite shows
small gaps between them (rows 10 and 16-19 of the top piece).

The whole column is built once in assembly coordinates as two helical tubes whose radius and
thickness follow the sprite's width, each face takes the fire colour of the pixel under it
(glowing more the brighter it is), and common.split_assembly cuts it into newsh5-53 (top) and
newsh5-91 (bottom). One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-91.py [-- --preview out.png]
(the preview is the whole column; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b051 as lib  # noqa: E402

NAME = "assembly-newsh5-91"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-53", "newsh5-91"]
AXIS = 12.0  # the column's centre line (pixel column of the composed 24x56 sprite)

# Down the column (composed sprite rows): (row, strand radius px, helix radius px).
PROFILE = [(-0.6, 0.0, 0.0), (0.5, 0.6, 0.2), (2.5, 0.9, 0.4), (5.0, 1.4, 1.0), (7.5, 1.8, 1.9),
           (10.0, 1.7, 2.8), (14.0, 2.2, 3.1), (18.0, 2.2, 4.3), (22.0, 2.8, 3.6), (26.0, 3.0, 2.6),
           (30.0, 3.6, 3.6), (34.0, 4.0, 4.5), (38.0, 3.7, 3.6), (42.0, 3.8, 3.7), (46.0, 3.2, 2.9),
           (50.0, 2.6, 2.0), (52.0, 1.8, 1.2), (53.2, 0.9, 0.5), (54.0, 0.0, 0.0)]


def profile(r):
    for (r0, a0, b0), (r1, a1, b1) in zip(PROFILE, PROFILE[1:]):
        if r0 <= r <= r1:
            t = (r - r0) / (r1 - r0)
            t = t * t * (3 - 2 * t)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return 0.0, 0.0


def build(g, sprite):
    coll = common.reset_collection(NAME)
    mats = lib.fire_materials(sprite, "nsh5_91")
    bm = bmesh.new()

    rows = [PROFILE[0][0]] + [r + 0.25 for r in range(0, 54)] + [PROFILE[-1][0]]
    for phase in (0.0, math.pi):
        pts, radii = [], []
        for r in rows:
            rad, R = profile(r)
            # The strands are furthest apart at rows 10, 18, 26, ... (half a turn every 8 rows).
            th = math.pi / 2 + math.pi * (r - 10.0) / 8.0 + phase
            pts.append((g.X(AXIS + R * math.sin(th)), g.Y(r), R * math.cos(th) * lib.PX))
            radii.append(rad * lib.PX)
        lib.tube3d(bm, pts, radii, sides=8, mat=1)

    lib.paint_soft(bm, g, lib.fire_slot, len(mats))
    obj = lib.to_object(NAME, bm, mats, coll)
    lib.scale_z(obj, 0.5)  # keep it a fairly flat flyer
    return obj


def main():
    g, layout, sprite = lib.assembly(ROOT, PIECES)
    obj = build(g, sprite)
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    lib.preview_assembly(ROOT, obj, pieces, g, sprite, size=4)


if __name__ == "__main__":
    main()
