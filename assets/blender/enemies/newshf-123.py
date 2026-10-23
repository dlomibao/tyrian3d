"""Grey straight-winged fighter (newshf.shp frames 123, 125, 127): a 3D version of its sprite.

Seen in episodes 1, 3 and 4. It flies nose down the screen: a thin fuselage with a needle nose,
a straight wing with chamfered leading tips, a tailplane and an upright fin at the back, and a
dark canopy where the wing meets the fuselage. The frames rock it side to side (frame 123 rolled
with its right wing up, 125 level, 127 left wing up: the wings narrow and the fin leans a pixel),
so each frame gets the level model turned about its long axis (newshf-123, -f2, -f3).

Run: blender --background --python assets/blender/enemies/newshf-123.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-123"
ROLL = math.radians(26)  # the wings' span shrinks from 19 px to 17 px


def build(sprite):
    objects, coll, x0 = lib.build_tailplane(sprite, NAME)
    return lib.rocking_models(NAME, sprite, objects, x0, [-ROLL, 0.0, ROLL], coll)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
