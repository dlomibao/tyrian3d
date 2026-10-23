"""Claw, left-hand (newsh2.shp frame 49): a 3D version of its sprite.

Seen in episode 1 (levels 28-36) and episode 3, usually beside newsh2-51, its mirror image. A
grey arm hooks from a purple-capped bar along the top over to the left, where it becomes a purple
blade pointing down (grey along its back, a grey strap across it); a thin grey arm hangs from the
bar's right end, with a knuckle and a glowing red claw tip. One frame. The shape is shared with
newsh2-51 (lib_b009.claw).

Run: blender --background --python assets/blender/enemies/newsh2-49.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-49"
MIRROR = False


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.6, roughness=0.4),  # 0 grey arm
        pal(9, metallic=0.65, roughness=0.3),  # 1 light grey
        pal(90, metallic=0.35, roughness=0.4),  # 2 purple blade
        pal(87, metallic=0.35, roughness=0.45),  # 3 purple cap
        pal(119, emission_strength=3.5),  # 4 red claw tip
        pal(67, emission_strength=1.5),  # 5 dark red collar
        pal(171, metallic=0.4, roughness=0.35),  # 6 beige studs
        pal(109, metallic=0.6, roughness=0.25),  # 7 pale highlights
    ]
    bm = bmesh.new()
    lib.claw(bm, range(8))
    if MIRROR:
        lib.mirror_all_x(bm)
    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
