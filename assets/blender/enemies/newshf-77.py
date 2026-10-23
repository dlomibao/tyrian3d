"""Blue-grey straight-winged fighter (newshf.shp frames 77, 79): a 3D version of its sprite.

Seen in episodes 1 and 3. The same craft as newshf-123 in blue-grey steel: thin fuselage with a
needle nose, straight wing with chamfered leading tips, tailplane, upright fin and a dark canopy.
Its palette indices are newshf-123's plus 99. Frame 77 is rolled with the right wing up and 79 is
level, so each gets its own model (newshf-77, newshf-77-f2).

Run: blender --background --python assets/blender/enemies/newshf-77.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-77"
ROLL = math.radians(26)


def build(sprite):
    objects, coll, x0 = lib.build_tailplane(sprite, NAME, remap=lambda i: i + 99)
    return lib.rocking_models(NAME, sprite, objects, x0, [-ROLL, 0.0], coll)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
