"""Red chevron block (newshm.shp frame 153): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 4 level 27): newshm-1's glossy red rounded block
with three raised chevrons stacked on its top, pointing up the screen.

Run: blender --background --python assets/blender/enemies/newshm-153.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-153"
Z0, Z1 = lib.BLOCK_TOP - 0.01, lib.BLOCK_TOP + 0.035


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=71, rim_light=75, rim=70, front=68, front_low=67, glint=73)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats += [pal(74, metallic=0.35, roughness=0.3)]
    CHEVRON = len(mats) - 1
    for apex in (3.4, 7.6, 12.3):
        lib.ribbon(bm, [(7.4, apex + 4.1), (11.6, apex), (15.8, apex + 4.1)], 2.0, Z0, Z1, CHEVRON)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
