"""Caged gunship (newsh7.shp frames 51, 89, 127): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4. A ribbed grey engine block fires a thruster
out of the top; a grey bar cage bends round its sides into blue blades that sweep down to a cross
wing; a glossy blue spindle sits on a yoke between them; below, a grey shield-shaped hull with a
keel, blue struts and a raised rim is the nose (it flies hull first, down the screen). The frames
only grow the thruster flame (tip to rows 2, 1, 0), so one model covers them all, with a flame per
frame (common.frame_part). Built by lib_e3_gunship (design A); newsh7-237 (the same sprite upside
down) shares it.

Run: blender --background --python assets/blender/enemies/newsh7-51.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
import lib_e3_gunship as gun  # noqa: E402

NAME = "newsh7-51"


def build(sprite):
    return [(NAME, gun.build_gunship(sprite, NAME, flames=(51, 89, 127)), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
