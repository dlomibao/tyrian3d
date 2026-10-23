"""Gold gem block (newshm.shp frame 17): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 level 33, episode 4 level 27): the same glossy
rounded block as newshm-1 in gold, with a blue gem set in a raised octagonal bezel on its top.

Run: blender --background --python assets/blender/enemies/newshm-17.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b078 as lib  # noqa: E402

NAME = "newshm-17"
Z0, Z1 = lib.BLOCK_TOP - 0.01, lib.BLOCK_TOP + 0.035


def build(sprite):
    coll = common.reset_collection(NAME)
    mats, roles = lib.tile_materials(sprite, NAME, top=249, rim_light=252, rim=248, front=246, front_low=245, glint=251)
    bm = bmesh.new()
    lib.rounded_block(bm, roles)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats += [pal(251, metallic=0.5, roughness=0.25), pal(247, metallic=0.4, roughness=0.4),
             pal(156, metallic=0.2, roughness=0.1, emission_strength=2.5)]
    BEZEL, SEAT, GEM = len(mats) - 3, len(mats) - 2, len(mats) - 1
    import math
    lib.disc(bm, 12.0, 10.0, 5.3, 5.3, Z0, Z1, BEZEL, sides=8, top_scale=0.9, angle0=math.pi / 8)
    lib.disc(bm, 12.0, 10.0, 4.2, 4.2, Z1 - 0.005, Z1 + 0.006, SEAT, sides=8, top_scale=0.95, angle0=math.pi / 8)
    cx, cy = lib.P(12.0, 10.0)
    lib.dome(bm, cx, cy, 3.7 / 12, 3.7 / 12, 0.13, z=Z1, rings=4, sides=12, mat=GEM)
    return lib.finish(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
