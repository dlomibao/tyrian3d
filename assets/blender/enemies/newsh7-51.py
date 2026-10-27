"""Caged gunship (newsh7.shp frames 51, 89, 127): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4. The top half is newsh7-13's: a ribbed grey
engine block firing a thruster out of the top, a grey bar cage bending round into blue blades
and a blue spindle. Below, the blades run down to a cross wing, and a grey shield-shaped hull
with a keel, blue struts and a bright rim makes the bottom half. The frames only grow the
thruster flame (its tip reaches rows 2, 1 and 0, and it brightens), so one model covers them
all, with a flame per frame (common.frame_part). Built by lib_b007.build_gunship, which
newsh7-237 (the same sprite upside down) shares.

Run: blender --background --python assets/blender/enemies/newsh7-51.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402

NAME = "newsh7-51"


def build(sprite):
    return [(NAME, lib.build_gunship(sprite, NAME, flames=(51, 89, 127)), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
