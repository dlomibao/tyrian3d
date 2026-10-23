"""Red rocket lying sideways (newsh8.shp, assembly of newsh8-125 and newsh8-127): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Two 2x2 ground pieces side by side make one 48x28 px
rocket lying on the ground nose to the right: a glowing exhaust bell on the left, a grey housing
with a brown window and a brown collar with red-tipped fins (newsh8-125), then the bulging red
body with two glowing slits and a rounded nose (newsh8-127). It is the same rocket as
assembly-newsh8-191 turned a quarter turn, so it is built by lib_b082.build_rocket, rotated,
placed in assembly coordinates and cut into the two pieces.

Run: blender --background --python assets/blender/enemies/assembly-newsh8-125.py [-- --preview out.png]
(the preview is the whole rocket; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b082  # noqa: E402

NAME = "assembly-newsh8-125"
ROOT = common.repo_root(__file__)
# Pieces' centres in pixels from the assembly's centre (screen 146, 9; sprite.json assemblyLayout).
LAYOUT = [("newsh8-125", -12, 0), ("newsh8-127", 12, 0)]
# Assembly pixel column c (newsh8-125's columns 0-23, then newsh8-127's), row r sits at
# X = (c + 0.5 - 24) / 12, Y = (13.5 - r) / 12. The rocket's axis is row 11 and its rows R in the
# standing sprite are columns c = R - 4 here, so its frame is turned +90 degrees and moved.


def main():
    lib_b082.rocket_assembly(NAME, ROOT, LAYOUT, 90, -27.5 / 12, 2.5 / 12, rib_side=1)


if __name__ == "__main__":
    main()
