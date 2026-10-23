"""Grey organism on a tube wall (newshh.shp 85, 87, 123, 125): a 3D version of its sprites.

Seen in level 2.4. Four 2x2 enemies make one 48 x 56 px block: a wall of ribbed grey tubes with
a smooth grey creature lying on it: a thick neck coming down from the top with a ribbed purple
sleeve, a round ball at the bottom of the neck, and a fat curved body below that sweeps from a
purple tip at the left out to a purple cap at the right.

The block is built once in assembly coordinates and cut into its four pieces with
common.split_assembly. The wall's tubes are traced from the sprite's texture (lib_b059) and
every part is coloured from the sprite pixel under it.

Run: blender --background --python assets/blender/enemies/assembly-newshh-125.py [-- --preview out.png]
(the preview is the whole block; each piece also gets <piece>.png next to it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b059 as lib  # noqa: E402

NAME = "assembly-newshh-125"
ROOT = common.repo_root(__file__)
# Each piece's top-left pixel in the 48 x 56 block (from sprite.json assemblyLayout: screen
# centres 149/173, 45/73).
PIECES = [("newshh-85", 0, 0), ("newshh-87", 24, 0), ("newshh-123", 0, 28), ("newshh-125", 24, 28)]

WALL = [97, 100, 103, 106]
FLESH = [99, 101, 103, 104, 106]
PURPLE = [81, 84, 87, 89, 91]

# The creature's parts, in assembly pixels.
NECK = [(23.0, -2.0, -0.12, 7.0, 0.2), (23.0, 6.0, -0.12, 7.0, 0.2), (23.2, 14.0, -0.12, 7.2, 0.2),
        (24.0, 20.0, -0.12, 8.0, 0.2), (25.5, 25.0, -0.13, 9.0, 0.19), (27.0, 30.0, -0.14, 8.0, 0.16)]
BODY = [(3.6, 29.0, -0.1, 3.4, 0.12), (6.0, 33.0, -0.1, 5.4, 0.18), (10.0, 36.5, -0.1, 7.0, 0.24),
        (16.0, 38.2, -0.1, 7.6, 0.26), (23.0, 39.0, -0.1, 7.0, 0.25), (30.0, 39.6, -0.1, 5.8, 0.22),
        (36.5, 40.6, -0.1, 5.0, 0.2)]
BALL = (16.5, 28.3, 8.0, 7.8)  # col, row, rx, ry
LEFT_TIP = (6.0, 27.6, 4.6, 2.4, math.radians(40))  # col, row, rx (long axis), ry, angle
RIGHT_CAP = (36.6, 41.0, 5.0, 4.2)


def sleeve_path():
    """The ribbed purple sleeve down the neck (rows 9-24): bulging rings where the sprite has
    its light bands (rows 10, 14 and 18), pinched between them."""
    rows = [(8.6, 0.0), (9.4, 2.0), (10.6, 3.4), (12.0, 2.6), (12.8, 3.0), (14.2, 3.6), (15.8, 2.8),
            (17.0, 2.9), (18.4, 3.8), (19.8, 3.4), (21.5, 2.8), (23.0, 2.3), (24.4, 1.4), (25.0, 0.0)]
    path = []
    for r, w in rows:
        col = 20.6 + max(0.0, r - 17.0) * 0.3
        path.append((col, r, 0.05, w, 0.0 if w == 0 else 0.03 + w * 0.018))
    return path


def build(grid, sprite):
    coll = common.reset_collection(NAME)
    tag = "nshh125"
    mats, wslot, fslot, pslot = [], {}, {}, {}
    for i in WALL:
        wslot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag + "w", metallic=0.25, roughness=0.5))
    for i in FLESH:
        fslot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag + "f", metallic=0.15, roughness=0.3))
    for i in PURPLE:
        pslot[i] = len(mats)
        mats.append(common.palette_material(sprite, i, tag + "p", metallic=0.15, roughness=0.3))
    wall, flesh = lib.nearest(wslot), lib.nearest(fslot)
    # The purple parts are mostly the ramp's dark end (83-85) and would read as black in 3D:
    # colour them a step up the same ramp, which the sprite uses for their lit sides.
    purple_ramp = lib.nearest(pslot)
    purple = lambda idx: purple_ramp(idx + 2 if 80 <= idx <= 93 else idx)  # noqa: E731
    DARK = wslot[97]
    bm = bmesh.new()

    # The wall's backing plate: the whole block, dark (the grooves between the tubes).
    lib.plate(bm, [(0, 0), (48, 0), (48, 56), (0, 56)], -0.25, -0.16, mat=DARK)

    neck = lib.smooth_path(NECK, 2)
    body = lib.smooth_path(BODY, 2)

    def creature(c, r):
        return (lib.in_path(c, r, neck) or lib.in_path(c, r, body)
                or lib.in_ellipse(c, r, BALL[0], BALL[1], BALL[2], BALL[3])
                or lib.in_ellipse(c, r, *LEFT_TIP[:4], angle=LEFT_TIP[4])
                or lib.in_ellipse(c, r, *RIGHT_CAP))

    # The tube wall wherever the creature isn't.
    lib.tube_wall(bm, grid, lambda c, r: not creature(c, r), -0.16, wall, DARK)

    # The creature: neck, body and ball, in its smooth greys.
    first = len(bm.faces)
    lib.sweep(bm, neck + [(27.6, 33.0, -0.14, 0.0, 0.0)], sides=12, mat=0)
    lib.sweep(bm, [(BODY[0][0] - 2.0, BODY[0][1] - 2.4, -0.1, 0.0, 0.0)] + body
              + [(BODY[-1][0] + 3.0, BODY[-1][1] + 0.4, -0.1, 0.0, 0.0)], sides=12, mat=0)
    lib.ellipsoid(bm, BALL[0], BALL[1], -0.1, BALL[2], BALL[3], 0.34, z_bottom=-0.15, segments=20, rings=10)
    lib.paint(bm, first, grid, flesh, under=fslot[99])

    # Purple: the sleeve, the tip at the left and the cap at the right.
    first = len(bm.faces)
    lib.sweep(bm, sleeve_path(), sides=10, mat=0)
    lib.ellipsoid(bm, LEFT_TIP[0], LEFT_TIP[1], -0.05, LEFT_TIP[2], LEFT_TIP[3], 0.15, angle=LEFT_TIP[4],
                  z_bottom=-0.12, segments=14, rings=7)
    lib.ellipsoid(bm, RIGHT_CAP[0], RIGHT_CAP[1], -0.08, RIGHT_CAP[2], RIGHT_CAP[3], 0.27, z_bottom=-0.14,
                  segments=16, rings=8)
    lib.paint(bm, first, grid, purple, under=pslot[81])

    return lib.to_object(NAME, bm, mats, coll)


def main():
    grid, sprite = lib.load_grid(ROOT, PIECES)
    obj = build(grid, sprite)
    lib.export_assembly(ROOT, obj, PIECES, grid, sprite)


if __name__ == "__main__":
    main()
