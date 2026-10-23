"""Rock wall with purple octagon plates, band along its top (newsh2.shp 273, 275, 277): a 3D
version of its sprites.

Seen in episode 1 (level 1.3) and episode 3. A row of 2x2 pieces (sprite.json `assemblyLayout`):
newsh2-273 at the left end, newsh2-275 repeated in the middle and newsh2-277 at the right end.
Each piece is a block of grey and beige boulders with a raised, chamfered purple octagon plate,
and a purple band of panels runs along the top behind the plates. The row is built whole (left,
two middles, right) in assembly coordinates and cut into the pieces with common.split_assembly;
the middle piece is the same at both of its edges so it tiles.

Run: blender --background --python assets/blender/enemies/assembly-newsh2-273.py [-- --preview out.png]
(the preview is the whole row; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b048  # noqa: E402

if __name__ == "__main__":
    lib_b048.wall_main(__file__, "assembly-newsh2-273",
                       ["newsh2-273", "newsh2-275", "newsh2-275", "newsh2-277"],
                       ["left", "mid", "mid", "right"], "top")
