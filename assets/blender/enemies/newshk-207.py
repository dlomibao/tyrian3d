"""Red-winged V ship (newshk.shp frame 207): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A grey U-shaped hull: two thin arms rising up the outer edges to
points, joined by a heavier bowl across the bottom with a framed recess in its middle. A red
armour plate lies along the inside of each arm, rising to an orange ridge on its inner edge with
a glowing yellow eye at the corner. The same ship pulled apart into two halves is the assembly
newshk-238 + newshk-242.

Run: blender --background --python assets/blender/enemies/newshk-207.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import common  # noqa: E402

NAME = "newshk-207"


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = lib.v_ship_materials(sprite, NAME)
    bm = bmesh.new()
    lib.v_ship_half(bm, 0.0, inner_edge=12.0)
    lib.mirror_x(bm, 0, axis=0.0)
    return [lib.mesh_object_mixed(NAME, bm, mats, coll)]


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
