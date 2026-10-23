"""Red wall block (newshm.shp frame 1): a 3D version of its sprite.

Seen in episode 1 (levels 31 and 33) and episode 4 (level 27), laid side by side into walls
(assembly-newshm-1: every piece of that layout is this same tile, and each tile is a whole
block on its own, so each piece is modelled by itself; newshm-15, -17, -53, -55 and -153 are the
same block with an emblem). A glossy rounded block: flat top, lit north-west bevel, and the
south edge rolling down toward the viewer (the dark lower third of the sprite).

Run: blender --background --python assets/blender/enemies/newshm-1.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-1"


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=71, rim_light=75, rim=70, front=68, front_low=67, glint=73)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
