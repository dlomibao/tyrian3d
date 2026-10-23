"""Grey light capsule (tyrian.shp#10 frames 165, 167, 169): a 3D version of its sprite.

Seen in episode 2 (level section 2). The sprite draws a grey metal capsule lying across the
screen (columns 2-22, rows 8-22): rounded end caps, dark grooves at columns 5, 9 and 18, raised
bands at columns 6-8 and 15-17 and a plain centre section with a red lamp on its far side and a
green one on its near side. Red light strips cross the bands and end caps on the far (upper) side.
The three frames only brighten the lights, so one model covers them all: the capsule is lofted along
X with an elliptical cross-section, the strips and lamps are emissive bars following its surface.
Its mirror image with the lights on the near side is tyrian10-203 (same builder, lib_b106).

Run: blender --background --python assets/blender/enemies/tyrian10-165.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402

NAME = "tyrian10-165"


def build(sprite):
    return [(NAME, lib.build_light_capsule(sprite, NAME, near_lights=False), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
