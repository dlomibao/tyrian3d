"""Horned green insect fighter (newshf.shp frame 55): a 3D version of its sprite.

Seen in episode 1. The same craft as newshf-47 (level frame) in green with brown shoulder pads
and blue eyes: two horns over a dark neck plate, a body tapering to a point with a dark mouth and
pale fang, and a wide delta wing whose lower edges show its darker underside. Its palette indices
are newshf-47's plus 16 (and blue 132 for the red eyes). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshf-55.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b023 as lib  # noqa: E402

NAME = "newshf-55"


def build(sprite):
    objects, coll, x0 = lib.build_insect(sprite, NAME, remap=lambda i: 132 if i == 116 else i + 16)
    return [(NAME, objects, sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
