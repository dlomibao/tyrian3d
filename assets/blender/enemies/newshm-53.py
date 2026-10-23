"""Purple X block (newshm.shp frame 53): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 level 33, episode 4 level 27): the same glossy
rounded block as newshm-1 in purple, with a glowing red X with curled ends across its top.

Run: blender --background --python assets/blender/enemies/newshm-53.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-53"
Z0, Z1 = lib.BLOCK_TOP - 0.01, lib.BLOCK_TOP + 0.035


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=87, rim_light=91, rim=86, front=84, front_low=83, glint=89)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats += [pal(119, emission_strength=2.5), pal(120, emission_strength=4.0)]
    RED, CORE = len(mats) - 2, len(mats) - 1
    # Down-right stroke, hooked at its top-left end and kinked up at the right.
    lib.ribbon(bm, [(6.0, 6.3), (7.4, 5.1), (8.6, 5.3), (10.2, 7.0), (12.0, 8.5), (13.6, 10.0), (15.2, 11.3),
                    (17.0, 12.6), (18.5, 13.1), (19.2, 12.0)], 1.4, Z0, Z1, RED)
    # Down-left stroke, curling round at the bottom.
    lib.ribbon(bm, [(18.2, 4.0), (16.6, 5.6), (14.6, 7.3), (13.0, 8.6), (11.5, 10.0), (9.6, 11.4), (8.2, 12.8),
                    (7.9, 14.3), (8.9, 15.8), (10.9, 16.1)], 1.5, Z0, Z1, RED)
    # The bright crossing.
    lib.disc(bm, 12.5, 9.2, 1.4, 1.4, Z0, Z1 + 0.012, CORE, sides=8)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
