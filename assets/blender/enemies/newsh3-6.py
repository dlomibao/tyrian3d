"""Four-pod spinner (newsh3.shp frame 6): a 3D version of its sprite.

Seen in episode 4 (levels 4 and 36). Four rounded steel pods on the diagonals, each a spoon of a
blade widening from a thin stem into a domed paddle, joined at a glowing red hub. Small bright
studs sit on the stems. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-6.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common, px, row  # noqa: E402

NAME = "newsh3-6"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(10, metallic=0.6, roughness=0.3),  # 0 steel pods
        pal(6, metallic=0.55, roughness=0.45),  # 1 dark stems
        pal(73, metallic=0.2, roughness=0.3, emission_strength=2.0),  # 2 red hub
        pal(79, roughness=0.2, emission_strength=3.0),  # 3 hub highlight
        pal(14, metallic=0.7, roughness=0.2),  # 4 bright studs
    ]
    POD, STEM, HUB, SHINE, STUD = range(5)
    bm = bmesh.new()
    # Hub: the red pixels at columns 10-13, rows 11-14 (centre column 11.5, row 12.5).
    cx, cy = px(11.5), row(12.5)

    # A pod along its axis from the hub: (distance px, half width px, half height units, material).
    pod = [(1.5, 1.5, 0.05), (3.4, 2.3, 0.07), (5.4, 3.5, 0.1), (7.8, 4.3, 0.13),
           (10.3, 4.1, 0.13), (12.0, 3.1, 0.1), (13.0, 1.7, 0.06), (13.4, 0.0, 0.0)]
    for angle in (45, -45, 135, -135):
        start = len(bm.verts)
        secs = [(d / 12, 0.0, w / 12, h, 0.0) for d, w, h in pod]
        lib.loft2(bm, secs, sides=12, mat_index=[STEM] + [POD] * (len(secs) - 2), power=0.9)
        # A stud on the stem (the bright pixels at columns 8 and 15, rows 9 and 16).
        lib.ellipsoid(bm, (0.0, 4.2 / 12, 0.085), (0.7 / 12, 0.7 / 12, 0.03), segments=6, rings=2,
                      mat_index=STUD)
        lib.rotate_new(bm, start, math.radians(angle), cx, cy)

    # The hub: a red ball with a pale highlight up and to the left.
    lib.ellipsoid(bm, (cx, cy, 0.0), (2.4 / 12, 2.4 / 12, 0.14), segments=12, rings=4, mat_index=HUB)
    lib.ellipsoid(bm, (cx - 0.3 / 12, cy + 0.3 / 12, 0.125), (0.8 / 12, 0.8 / 12, 0.03), segments=8,
                  rings=2, mat_index=SHINE)

    obj = common.mesh_object(NAME, bm, mats, coll, smooth=True)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
