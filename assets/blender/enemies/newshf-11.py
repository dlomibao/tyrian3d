"""Grey swept-wing fighter (newshf.shp frame 11): a 3D version of its sprite.

Seen in episodes 1, 3 and 4. It flies nose down the screen: a round fuselage with a bright spine,
wings swept back to tips beside the tail, a small tailplane under an upright fin, a dark slot
canopy in front of the wings and two short guns poking forward from the wing roots. One frame,
one model.

Run: blender --background --python assets/blender/enemies/newshf-11.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-11"


def build(sprite):
    objects, coll, x0 = lib.build_swept(sprite, NAME)
    return [(NAME, objects, sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
