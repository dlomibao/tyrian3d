"""Right corner tower of the red newshf fortress (assembly of newshf-161, 163, 199, 201): a 3D
version of its sprites.

Seen in episode 1 (levels 1.10, 1.29, 1.38), 2 (2.2), 3 (3.21) and 4 (4.16). The mirror image of
the left tower (assembly-newshf-191): a 48 x 56 px block with a rounded drum on the outside (here
the right), three glowing red rods in slots reaching up the screen, light ribs between them and a
body with dark channels and a rounded hub below. Each piece has one frame. Built whole in
lib_b100.build_side (mirrored), then cut into the four pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshf-199.py [-- --preview out.png]
(the preview is the whole tower; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b100  # noqa: E402

NAME = "assembly-newshf-199"
PIECES = ["newshf-199", "newshf-201", "newshf-161", "newshf-163"]

if __name__ == "__main__":
    # The block's top-left corner is screen pixel (190, -31): newshf-161's centre (202, -17) less 12, 14.
    lib_b100.main(__file__, NAME, PIECES, 190, -31, mirror=True)
