"""Raised-block bunker (newshp.shp frame 53): a 3D version of its sprite.

Seen in episode 1 (level 1.21), listed with the newshp-191 stone block. The same rounded grey
stone housing on rubbly ground as newshp-237 (whose ground rows 14-27 it repeats exactly), but
instead of a shutter and lens its well holds a stone block pushed up out of the top of the well
(columns 8-15, rows 0-6), leaving a dark slot below it. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshp-53.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b067 as lib  # noqa: E402
from lib_b067 import common  # noqa: E402

NAME = "newshp-53"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = lib.Grid(24, 28)
    m = lib.Mats(sprite, NAME)
    bm = bmesh.new()
    lib.terrain(bm, g, m)
    lib.housing(bm, g, m)
    # The block pushed up out of the well, standing above the rim (lit top and left like the sprite).
    lib.frustum(bm, g, 7.6, 0, 16.4, 6.6, 0.12, 0.4, m[9], sides=(m[14], m[12], m[7], m[6]), inset=0.4)
    # The dark slot under it (rows 7-9) and the lighter step at the well's foot (rows 10-11).
    lib.frustum(bm, g, 8, 6.6, 16, 10, 0.12, 0.125, m[2], inset=0.0)
    lib.frustum(bm, g, 8, 10, 16, 12, 0.12, 0.16, m[4], sides=(m[5], m[4], m[4], m[3]), inset=0.3)
    obj = lib.to_object(NAME, bm, m.list, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
