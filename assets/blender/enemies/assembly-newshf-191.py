"""Left corner tower of the red newshf fortress (assembly of newshf-153, 155, 191, 193): a 3D
version of its sprites.

Seen in episode 1 (levels 1.10, 1.29, 1.38), 2 (2.2), 3 (3.21) and 4 (4.16). Four 2x2 ground
enemies make one 48 x 56 px block at the fortress's upper left: a rounded drum on the outside,
three glowing red rods with yellow and orange markings lying in slots that reach up the screen,
light ribs between the slots, and below them a body with dark channels and a rounded hub. Each
piece has one frame. Built whole in lib_b100.build_side, then cut into the four pieces.

Run: blender --background --python assets/blender/enemies/assembly-newshf-191.py [-- --preview out.png]
(the preview is the whole tower; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b100  # noqa: E402

NAME = "assembly-newshf-191"
PIECES = ["newshf-191", "newshf-193", "newshf-153", "newshf-155"]

if __name__ == "__main__":
    # The block's top-left corner is screen pixel (70, -31): newshf-153's centre (82, -17) less 12, 14.
    lib_b100.main(__file__, NAME, PIECES, 70, -31, mirror=False)
