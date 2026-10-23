"""Rock wall with purple octagon plates, band along its bottom (newsh2.shp 279, 281, 283): a 3D
version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. Three 2x2 pieces in a row (sprite.json
`assemblyLayout`): newsh2-279 at the left end, newsh2-281 in the middle and newsh2-283 at the
right end. The same rock wall as assembly-newsh2-273 turned the other way: boulders (a beige one
top left) along the top, a raised purple octagon plate on each piece, and a band of purple panels
along the bottom between and below the plates. Built whole in assembly coordinates and cut into
the pieces with common.split_assembly; the middle piece is the same at both edges so it tiles.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-279.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048  # noqa: E402

if __name__ == "__main__":
    lib_b048.wall_main(__file__, "assembly-newsh2-279",
                       ["newsh2-279", "newsh2-281", "newsh2-283"],
                       ["left", "mid", "right"], "bottom")
