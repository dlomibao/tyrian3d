"""Caged spindle drone (newsh7.shp frames 13, 15, 17): a 3D version of its sprite.

Seen in episode 3 (level section 10). Symmetric top to bottom and left to right: a blue steel
spindle (two bulbs and a waist) between two ribbed grey engine blocks, each with a thruster
firing out of the end, and a grey bar cage that bends round both sides into blue chevron blades
held to the spindle's waist by short grey axles. The frames only grow the thruster flames (their
tips reach rows 2, 1 and 0 from each end, and they brighten), so one model covers them all, with
a pair of flames per frame (common.frame_part). Built by lib_e3_gunship (design A).

Run: blender --background --python assets/blender/enemies/newsh7-13.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
import lib_e3_gunship as gun  # noqa: E402

NAME = "newsh7-13"


def build(sprite):
    return [(NAME, gun.build_drone(sprite, NAME, flames=(13, 15, 17)), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
