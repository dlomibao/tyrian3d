"""Rock shoulder (newsh3.shp frame 262): a 3D version of its sprite.

Seen in episode 4 (levels 2 and 29), beside the big rock arch. The upper-right end of a brown
rock: it fills the tile's lower left and breaks off along a ragged diagonal edge to the upper
right. The model is a faceted lump that falls to a thin edge along that outline and is cut off
square where it runs on past the tile's left and bottom edges; its pale ridges stand proud, its
dark cracks sink, and its facets take the sprite's browns under them. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-262.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common  # noqa: E402

NAME = "newsh3-262"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(17, metallic=0.05, roughness=0.9),  # 0 dark cracks and underside
        pal(19, metallic=0.05, roughness=0.9),  # 1 deep brown
        pal(21, metallic=0.05, roughness=0.85),  # 2 brown (the main face)
        pal(22, metallic=0.05, roughness=0.85),  # 3 warm brown
        pal(24, metallic=0.05, roughness=0.8),  # 4 light brown
        pal(26, metallic=0.05, roughness=0.75),  # 5 pale ridges
    ]
    pixels = sprite["frames"][0]["pixels"]

    def slot(v):
        if v < 0:
            return None
        if v <= 18:
            return 0
        if v <= 20:
            return 1
        if v == 21:
            return 2
        if v == 22:
            return 3
        if v <= 24:
            return 4
        return 5

    bm = bmesh.new()
    lib.rock_piece(bm, pixels, lambda v: v >= 0, slot, top=0.24, bottom=0.14, fall=6.0,
                   relief=lambda v: (v - 21.5) * 0.006, spacing=2.6, seed=262)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
