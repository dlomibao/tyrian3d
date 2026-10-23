"""Grey robot arm (newsh9.shp, assembly of 3 pieces: newsh9-5, newsh9-7, newsh9-45): a 3D version of its sprites.

Seen in episode 4 (level 4.20). The right-hand arm: the left one (assembly-newsh9-39) mirrored and shifted
one pixel, as its sprites are. Three 2x2 enemies in an L make one
48x56 px arm: a rounded shoulder housing with two knuckles at the top, a jaw block under it, a
big grey upper arm with a socket ring round a dark opening, and a forearm ending in a looped claw
holding a glowing blue gem. Each piece is one frame, so one model per piece.

Built whole in assembly coordinates by lib_b028.build_arm, then cut into the pieces with
common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-45.py [-- --preview out.png]
(the preview is the whole arm; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b028  # noqa: E402

PIECES = ["newsh9-5", "newsh9-7", "newsh9-45"]

if __name__ == "__main__":
    lib_b028.run_assembly(__file__, "assembly-newsh9-45", PIECES, mirror=True)
