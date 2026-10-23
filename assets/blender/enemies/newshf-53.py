"""Green swept-wing fighter (newshf.shp frame 53): a 3D version of its sprite.

Seen in episodes 1 and 3. The same craft as newshf-11 in green: a round fuselage with a bright
spine, wings swept back to tips beside the tail, a small tailplane under an upright fin, a dark
slot canopy and two short guns at the wing roots. Its palette indices are newshf-11's plus 32.
One frame, one model.

Run: blender --background --python assets/blender/enemies/newshf-53.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-53"


def build(sprite):
    objects, coll, x0 = lib.build_swept(sprite, NAME, remap=lambda i: i + 32)
    return [(NAME, objects, sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
