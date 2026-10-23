"""Rock tip (newsh3.shp frame 180, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 4 (levels 2 and 29), beside the big rock arch. Just the point of a brown rock
poking into the tile's lower right corner: a pale face rimmed by a dark edge. The model is a small
faceted wedge that thins to an edge along its outline and is cut off square where it runs on past
the tile's right and bottom edges. One frame.

Run: blender --background --python assets/blender/enemies/newsh3-180.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b011 as lib  # noqa: E402
from lib_b011 import common  # noqa: E402

NAME = "newsh3-180"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(17, metallic=0.05, roughness=0.9),  # 0 dark edge and underside
        pal(18, metallic=0.05, roughness=0.9),  # 1 deep brown
        pal(25, metallic=0.05, roughness=0.8),  # 2 light brown
        pal(26, metallic=0.05, roughness=0.75),  # 3 pale face
    ]
    pixels = sprite["frames"][0]["pixels"]
    slot = {17: 0, 18: 1, 25: 2, 26: 3}.get

    bm = bmesh.new()
    lib.rock_piece(bm, pixels, lambda v: v >= 0, slot, top=0.16, bottom=0.1, fall=2.6,
                   relief=lambda v: (v - 21.5) * 0.004, spacing=1.0, smooth_rounds=1, seed=180)
    obj = common.mesh_object(NAME, bm, mats, coll, smooth=False)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
