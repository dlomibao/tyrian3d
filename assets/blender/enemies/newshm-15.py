"""Green dollar block (newshm.shp frame 15): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 level 33, episode 4 level 27): the same glossy
rounded block as newshm-1 in green, with a raised gold dollar sign on its flat top.

Run: blender --background --python assets/blender/enemies/newshm-15.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-15"
Z0, Z1 = lib.BLOCK_TOP - 0.01, lib.BLOCK_TOP + 0.035


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=39, rim_light=43, rim=38, front=36, front_low=35, glint=41)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats += [pal(125, metallic=0.6, roughness=0.3), pal(124, metallic=0.6, roughness=0.3)]
    GOLD, DARK_GOLD = len(mats) - 2, len(mats) - 1
    # The S, from its top-right end round to its bottom-left end.
    lib.ribbon(bm, [(14.6, 5.0), (9.4, 5.0), (7.8, 6.2), (7.2, 8.2), (8.0, 10.1), (10.0, 10.6), (13.5, 10.9),
                    (14.9, 12.0), (15.1, 14.0), (14.2, 15.4), (12.6, 16.0), (8.0, 16.0)], 2.0, Z0, Z1, GOLD)
    # The bar through it.
    lib.ribbon(bm, [(11.0, 2.8), (11.0, 18.0)], 1.4, Z0, Z1 + 0.01, DARK_GOLD)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
