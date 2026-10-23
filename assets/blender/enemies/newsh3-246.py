"""Spiked mine (newsh3.shp frame 246): a 3D version of its sprite.

Seen in episode 4 (levels 4, 10, 22, 36, 50). A dark steel ball with four long ridged spikes
(up, down, left, right), four red rods sticking out on the diagonals and a red grille of two
rounded pads either side of a steel rib on its face. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-246.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, px, row  # noqa: E402

NAME = "newsh3-246"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.4),  # 0 dark steel ball
        pal(11, metallic=0.65, roughness=0.3),  # 1 lit spike faces
        pal(5, metallic=0.6, roughness=0.45),  # 2 shaded spike faces
        pal(72, metallic=0.3, roughness=0.45),  # 3 red rods and pads
        pal(75, metallic=0.3, roughness=0.35),  # 4 pale red rod ends
        pal(12, metallic=0.7, roughness=0.25),  # 5 bright steel rib
        pal(67, metallic=0.2, roughness=0.6),  # 6 dark red grille slots
        pal(8, metallic=0.6, roughness=0.4),  # 7 mid spike faces
    ]
    BALL, LIT, SHADE, RED, PALE, RIB, SLOT, MID = range(8)
    bm = bmesh.new()
    cx, cy = px(12), row(14)

    # The ball: sprite columns 7-17, rows 9-19.
    lib.ellipsoid(bm, (cx, cy, 0.0), (5.4 / 12, 5.2 / 12, 0.22), segments=16, rings=5, mat_index=BALL)
    lib.set_smooth(bm, 0)

    # Four spikes (tips at row 2.6, row 25.6, column 1.4, column 22.6), ridged on top.
    f0 = len(bm.faces)
    tips = [(cx, row(2.4)), (cx, row(25.6)), (px(1.2), cy), (px(22.8), cy)]
    for tx, ty in tips:
        lib.diamond_spike(bm, (cx, cy, 0.0), (tx, ty, 0.0), 2.6 / 12, 0.15,
                          mats=(MID, LIT, SHADE, SHADE),
                          steps=[(0.25, 1.0), (0.55, 0.62)])
    lib.set_smooth(bm, f0, False)

    # Red rods on the diagonals: outer ends at columns 4.6 / 19.4, rows 6.4 / 21.6.
    f0 = len(bm.faces)
    for sx in (-1, 1):
        for sy in (-1, 1):
            ox, oy = cx + sx * 7.4 / 12, cy + sy * 7.6 / 12
            ix, iy = cx + sx * 3.4 / 12, cy + sy * 3.6 / 12
            lib.tube(bm, (ix, iy, 0.02), (ox, oy, 0.0), 1.2 / 12, sides=8, mat_index=RED)
            lib.ellipsoid(bm, (ox, oy, 0.0), (1.1 / 12, 1.1 / 12, 1.0 / 12), segments=8, rings=3,
                          mat_index=PALE)
    # Red grille on the ball's face: pads at columns 9-11 and 13-14, rows 11-16, a steel rib between.
    for c0, c1 in ((8.8, 11.6), (12.6, 14.9)):
        start = len(bm.verts)
        w = (c1 - c0) / 24
        lib.loft2(bm, [(row(10.6), 0, 0.0, 0.0, 0.19), (row(11.2), 0, w * 0.8, 0.05, 0.19),
                       (row(13.5), 0, w, 0.07, 0.2), (row(15.8), 0, w * 0.85, 0.05, 0.18),
                       (row(16.6), 0, 0.0, 0.0, 0.17)], sides=10, mat_index=RED)
        common.shift_x(bm, start, (px(c0) + px(c1)) / 2 - 1 / 24)
    lib.loft2(bm, [(row(9.4), cx, 0.0, 0.0, 0.2), (row(10.2), cx, 0.45 / 12, 0.04, 0.21),
                   (row(14), cx, 0.5 / 12, 0.05, 0.24), (row(16.8), cx, 0.0, 0.0, 0.18)],
              sides=6, mat_index=RIB)
    # A dark slot in the left pad (column 11) reads as the grille's gap.
    lib.loft2(bm, [(row(11.5), px(11.1), 0.0, 0.0, 0.24), (row(12.2), px(11.1), 0.3 / 12, 0.02, 0.255),
                   (row(15), px(11.1), 0.3 / 12, 0.02, 0.245), (row(15.6), px(11.1), 0.0, 0.0, 0.235)],
              sides=6, mat_index=SLOT)
    lib.set_smooth(bm, f0)

    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
