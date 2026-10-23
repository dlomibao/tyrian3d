"""Strawberry (tyrian.shp#10 frame 75): a 3D version of its sprite.

Seen in episode 1 (level section 23). The 12x14 sprite draws a red berry lying on the ground,
stalk end up the screen: a glossy red body (rows 4-13, widest across rows 5-9 and narrowing to the
bottom) under a crown of green leaves (rows 0-3, spilling down the sides at columns 0-1 and 10-11)
with a short reddish-brown stalk in the middle (row 3, columns 5-6). In 3D the body is a rounded
egg lofted along Y, its leaves are flattened, tapering blades fanning out from the stalk over the
berry's top end. The dark red rim (index 112) is its outline and isn't modelled.

Run: blender --background --python assets/blender/enemies/tyrian10-75.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402
from lib_b106 import common, ex, ey  # noqa: E402

NAME = "tyrian10-75"
W, H = 12, 14  # a size-1 sprite


def X(c):
    return ex(c, W)


def Y(r):
    return ey(r, H)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(118, metallic=0.05, roughness=0.3),  # 0 red berry
        pal(40, metallic=0.0, roughness=0.6),  # 1 leaves
        pal(37, metallic=0.0, roughness=0.65),  # 2 darker leaves
        pal(72, metallic=0.0, roughness=0.6),  # 3 stalk
    ]
    BERRY, LEAF, LEAF_DARK, STALK = range(4)

    # The berry: (row, half width px); its height is half its width, resting on the ground.
    bm = bmesh.new()
    prof = [(3.6, 0.0), (3.75, 2.6), (4.2, 4.5), (5.0, 5.7), (7.0, 6.0), (9.5, 5.8), (11.0, 5.0), (12.4, 3.9),
            (13.4, 2.4), (13.9, 0.0)]
    sections = []
    for r, w in prof:
        hw = w / 12
        hh = hw * 0.5
        sections.append((Y(r), hw, hh, max(hh, 0.04) * 0.88))
    common.loft(bm, sections, sides=16, mat_index=BERRY)
    berry = common.mesh_object(NAME, bm, mats, coll, smooth=True)

    # The crown of leaves: flattened tapering blades from the stalk to their tips.
    bm = bmesh.new()
    base = (X(6), Y(4.2), 0.36)
    tips = [  # (tip column, row, material); each blade arches up from the stalk and droops to its tip
        (0.3, 3.9, LEAF_DARK), (0.4, 1.8, LEAF), (2.4, 0.4, LEAF_DARK), (4.6, 0.2, LEAF),
        (7.6, 0.3, LEAF_DARK), (9.6, 0.5, LEAF), (11.6, 2.2, LEAF_DARK), (11.6, 4.8, LEAF),
    ]
    for c, r, mat in tips:
        tip = (X(c), Y(r), 0.12)
        mid = (base[0] + (tip[0] - base[0]) * 0.55, base[1] + (tip[1] - base[1]) * 0.55, 0.33)
        lib.polyline_tube(bm, [base, mid, tip], [0.6 / 12, 1.7 / 12, 0.2 / 12], sides=6, mat_index=mat, flat=0.22)
    # The stalk: a short stub poking up the screen.
    lib.polyline_tube(bm, [(X(6), Y(4.0), 0.34), (X(6), Y(3.3), 0.42), (X(6), Y(2.7), 0.44)], 0.75 / 12,
                      sides=6, mat_index=STALK)
    crown = common.mesh_object(f"{NAME}_crown", bm, mats, coll, smooth=True)

    return [(NAME, [berry, crown], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
