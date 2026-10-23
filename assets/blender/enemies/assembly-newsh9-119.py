"""Right armoured fist (newsh9.shp frames 81, 83, 119, 121): a 3D version of its sprites.

Seen in episode 4 (level 4.18). Four 2x2 ground pieces make the right of two grey armoured fists
that face each other across a gap (the left one is assembly-newsh9-115, its mirror image): a
big rounded hood with a light ridge down its inner edge and a step across its front, over a
dark body studded with four red knuckle domes, a light grey bridge between them and a white
lamp in the lower corner. Each piece has one frame.

The whole structure (both fists) is built in lib_b090.build and cut into pieces with
common.split_assembly; this script exports the right fist's four.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-119.py [-- --preview out.png]
(the preview is the whole structure; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b090 as lib  # noqa: E402

NAME = "assembly-newsh9-119"
PIECES = ["newsh9-81", "newsh9-83", "newsh9-119", "newsh9-121"]

if __name__ == "__main__":
    lib.export(NAME, PIECES)
