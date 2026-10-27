"""Belted orb (newshe.shp frames 13, 15, 17): a 3D version of its sprite.

Seen in episode 1 (level section 28). A glossy steel-blue ball (columns 3-20, rows 5-21) with a
bright highlight up and left and a reflected rim low and right, girdled at its equator (rows
12-14) by a glowing red-orange belt. The frames only cycle the belt's glow (it dims two palette
steps a frame), so one model covers them all, with the belt's colours changing per frame. Flattened to a squat ball so it stays within the height of a flying enemy.

Run: blender --background --python assets/blender/enemies/newshe-13.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b033 as lib  # noqa: E402
from lib_b033 import common, ex, ey, px, row  # noqa: E402

NAME = "newshe-13"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(57, metallic=0.55, roughness=0.25),  # 0 steel blue
        pal(55, metallic=0.55, roughness=0.3),  # 1 dark blue edge
        pal(60, metallic=0.55, roughness=0.2),  # 2 light blue
        pal(62, metallic=0.5, roughness=0.12),  # 3 highlight
        # The belt dims two palette steps a frame (13 bright, 15, 17 dark red).
        common.palette_material(sprite, 118, f"{NAME}_belt", emission_strength=2.5,
                                frames={15: 116, 17: 114}),  # 4 red belt edges
        common.palette_material(sprite, 123, f"{NAME}_core", emission_strength=4.0,
                                frames={15: 121, 17: 119}),  # 5 orange belt core
        pal(56, metallic=0.55, roughness=0.3),  # 6 underside
    ]
    BLUE, DARK, LIGHT, HI, BELT, CORE, UNDER = range(7)
    bm = bmesh.new()

    # The ball: columns 3-20 (half width 9 px), rows 5-21 (half height 8.5 px, centre row 13).
    a = (ex(21) - ex(3)) / 2
    b = (ey(5) - ey(22)) / 2
    cy = (ey(5) + ey(22)) / 2
    c = 0.26
    faces = lib.ellipsoid(bm, 0.0, cy, a, b, c, rings=18, sides=28)
    lib.paint(faces, lambda p: UNDER if p.z < -0.03 else None)
    ell = (0.0, cy, a, b, c)

    # The highlight up and left of centre (columns 8-11, rows 9-11) with a softer halo, and the
    # reflected rim low and right (rows 16-20, columns 14-18), lying on the ball's surface.
    hu, hv = px(9.8) / a, (row(10.6) - cy) / b
    lib.oval_on_ellipsoid(bm, ell, hu, hv, 3.4 / 12 / a, 2.6 / 12 / b, LIGHT, lift=1.004)
    lib.oval_on_ellipsoid(bm, ell, hu, hv + 0.02, 2.1 / 12 / a, 1.5 / 12 / b, HI, lift=1.008)
    lib.band_on_ellipsoid(bm, ell, 0.74, 0.97, -78, -22, LIGHT, lift=1.004, steps=3)
    lib.band_on_ellipsoid(bm, ell, 0.84, 0.95, -66, -38, HI, lift=1.008, n=8, steps=2)

    # The glowing belt round the equator (rows 12-14), standing a little proud of the ball, with
    # a brighter middle row.
    A, C = a * 1.035, c * 1.08
    edge = 0.012
    common.loft(bm, [(ey(12), A * 0.97, C * 0.97, 0.0), (ey(12) - edge, A, C, 0.0), (ey(13), A, C, 0.0)],
                sides=28, mat_index=BELT, cap_end=False)
    common.loft(bm, [(ey(13), A, C, 0.0), (ey(14), A, C, 0.0)], sides=28, mat_index=CORE,
                cap_start=False, cap_end=False)
    common.loft(bm, [(ey(14), A, C, 0.0), (ey(15) + edge, A, C, 0.0), (ey(15), A * 0.97, C * 0.97, 0.0)],
                sides=28, mat_index=BELT, cap_start=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
