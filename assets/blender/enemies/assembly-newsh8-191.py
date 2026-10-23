"""Standing red rocket (newsh8.shp, assembly of newsh8-153 over newsh8-191): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Two 2x2 ground pieces stacked make one 24x56 px rocket
lying on the ground with its nose down the screen: a glowing exhaust bell on top (newsh8-153),
a grey housing with a brown window, a brown collar with red-tipped fins, then the bulging red
body with two glowing slits and a rounded nose (newsh8-191). The frames of each piece only
flicker the exhaust or the slits, so one model covers each piece's frames.

The rocket itself is built in lib_b082.build_rocket (shared with assembly-newsh8-125, the same
rocket lying sideways), placed in assembly coordinates and cut into the two pieces.

Run: blender --background --python assets/blender/enemies/assembly-newsh8-191.py [-- --preview out.png]
(the preview is the whole rocket; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b082  # noqa: E402

NAME = "assembly-newsh8-191"
ROOT = common.repo_root(__file__)
# Pieces' centres in pixels from the assembly's centre (screen 74, 1; sprite.json assemblyLayout).
LAYOUT = [("newsh8-153", 0, -14), ("newsh8-191", 0, 14)]
# Assembly pixel column c, row R (newsh8-153's rows 0-27, then newsh8-191's) sits at
# X = (c + 0.5 - 12) / 12, Y = (27.5 - R) / 12; the rocket's axis is column 11.


def main():
    lib_b082.rocket_assembly(NAME, ROOT, LAYOUT, 0, -0.5 / 12, 27.5 / 12)


if __name__ == "__main__":
    main()
