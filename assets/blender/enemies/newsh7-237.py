"""Caged gunship, upside down (newsh7.shp frames 237, 239, 275): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4. The sprite is newsh7-51 flipped top to
bottom and moved one column right: the shield hull points up the screen and the engine block
fires its thruster out of the bottom. The frames only grow the flame (small on 237, middle on
275, big on 239), so one model covers them all, with a flame per frame (common.frame_part).
Built by lib_b007.build_gunship.

Run: blender --background --python assets/blender/enemies/newsh7-237.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402

NAME = "newsh7-237"


def build(sprite):
    return [(NAME, lib.build_gunship(sprite, NAME, flip=True, dc=1, flames=(237, 275, 239)), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
