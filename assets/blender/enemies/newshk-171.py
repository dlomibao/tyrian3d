"""Fireball with a blue eye (newshk.shp frame 171): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A small (12x14) red teardrop, its point trailing up the screen,
with a bright orange streak down its spine and a round blue glass eye set in its fat end, ringed
by orange glow and lit by a white glint.

Run: blender --background --python assets/blender/enemies/newshk-171.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import U, common  # noqa: E402

NAME = "newshk-171"
W, H = 12, 14


def ex(c):
    return lib.ex(c, W)


def ey(r):
    return lib.ey(r, H)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(116, metallic=0.2, roughness=0.5, emission_strength=1.0),  # 0 red body
        pal(120, emission_strength=2.5),  # 1 orange spine streak
        pal(121, emission_strength=3.0),  # 2 orange glow round the eye
        pal(59, metallic=0.4, roughness=0.15),  # 3 blue glass eye
        pal(63, emission_strength=5.0),  # 4 white glint
        pal(113, metallic=0.2, roughness=0.6),  # 5 dark red tail tip
    ]
    BODY, SPINE, GLOW, EYE, GLINT, TIP = range(6)
    bm = bmesh.new()
    cx = ex(5.5)

    # Teardrop body: (row edge, half width px), point at the top.
    body = [(0.2, 0.0), (1.0, 1.0), (3.0, 1.5), (5.0, 2.3), (6.4, 3.2), (7.6, 3.5), (10.6, 3.5), (12.0, 2.6),
            (13.3, 1.4), (14.0, 0.0)]
    start = len(bm.verts)
    common.loft(bm, [(ey(r), w * U, w * U * 0.6, 0.0) for r, w in body], sides=12, mat_index=BODY)
    lib.move(bm, start, dx=cx)
    # Dark tail tip.
    start = len(bm.verts)
    common.loft(bm, [(ey(0.0), 0.0, 0.0, 0.0), (ey(1.4), 0.7 * U, 0.5 * U, 0.0), (ey(2.0), 0.0, 0.0, 0.0)],
                sides=8, mat_index=TIP)
    lib.move(bm, start, dx=cx)
    # Orange streak down the spine (column 5, rows 3-6).
    lib.polyline_tube(bm, [(cx, ey(2.0), 1.0 * U * 0.6), (cx, ey(4.0), 1.8 * U * 0.6), (cx, ey(6.5), 3.0 * U * 0.6)],
                      [0.35 * U, 0.55 * U, 0.7 * U], sides=6, mat_index=SPINE)

    # The eye: an orange glowing ring round a blue glass dome (rows 7-11), with a glint.
    lib.ellipsoid(bm, (cx, ey(9.6), 0.08), (3.4 * U, 3.3 * U, 0.07), sides=16, rings=8, mat_index=GLOW)
    lib.ellipsoid(bm, (cx, ey(9.6), 0.1), (2.6 * U, 2.5 * U, 0.1), sides=16, rings=8, mat_index=EYE)
    lib.ellipsoid(bm, (ex(5.4), ey(9.3), 0.19), (0.7 * U, 0.7 * U, 0.025), sides=10, rings=6, mat_index=GLINT)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [obj]


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
