"""Horned brown insect fighter (newshf.shp frames 47, 49, 51): a 3D version of its sprite.

Seen in episodes 1 and 3. It flies tail point down the screen: two horns over a dark neck plate,
grey shoulder pads, a brown body with two red eyes and a dark mouth with a pale fang, and a wide
delta wing whose lower edges show its grey underside. The frames rock it side to side (47 rolled
with its right side up, 49 level, 51 left side up: the wing narrows a pixel each side and the
horns lean a pixel), so each frame gets the level model turned about its long axis (newshf-47,
-f2, -f3).

Run: blender --background --python assets/blender/enemies/newshf-47.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-47"
ROLL = math.radians(22)  # the wing's span shrinks from 18 px to 16-17 px


def build(sprite):
    objects, coll, x0 = lib.build_insect(sprite, NAME)
    return lib.rocking_models(NAME, sprite, objects, x0, [-ROLL, 0.0, ROLL], coll)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
