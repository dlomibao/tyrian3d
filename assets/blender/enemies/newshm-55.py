"""Blue question-mark block (newshm.shp frame 55): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 level 33, episode 4 level 27): the same glossy
rounded block as newshm-1 in steel blue, with a question mark embossed on its top. (The sprite's
near-black corners, index 64, are background, not part of the block.)

Run: blender --background --python assets/blender/enemies/newshm-55.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-55"
Z0, Z1 = lib.BLOCK_TOP - 0.01, lib.BLOCK_TOP + 0.035


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=57, rim_light=61, rim=56, front=54, front_low=53, glint=59)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats += [pal(60, metallic=0.35, roughness=0.3)]
    MARK = len(mats) - 1
    lib.ribbon(bm, [(8.6, 8.4), (8.7, 6.9), (9.8, 5.6), (11.2, 5.1), (13.0, 5.3), (14.4, 6.6), (14.6, 8.6),
                    (13.5, 10.0), (12.3, 11.2), (11.7, 12.5), (11.7, 13.7)], 1.8, Z0, Z1, MARK)
    lib.disc(bm, 11.6, 15.6, 1.1, 1.1, Z0, Z1, MARK, sides=8)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
