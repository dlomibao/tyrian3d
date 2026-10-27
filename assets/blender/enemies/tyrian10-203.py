"""Grey light capsule (tyrian.shp#10 frames 203, 205, 207): a 3D version of its sprite.

Seen in episode 3 (level section 2). The sprite draws a grey metal capsule lying across the
screen (columns 2-22, rows 8-22): rounded end caps, dark grooves at columns 5, 9 and 18, raised
bands at columns 6-8 and 15-17 and a plain centre section with a green lamp on its far side and a
red one on its near side. Red light strips cross the bands and end caps on the near (lower) side.
The three frames only brighten the lights, so one model covers them all: the capsule is lofted along
X with an elliptical cross-section, the strips and lamps are emissive bars following its surface,
and each light's material changes colour with the frame (palette_material frames=; the end-cap
strips are a little dimmer than the band strips).
It is the mirror image of tyrian10-165, which has the lights on the far side (same builder, lib_b106).

Run: blender --background --python assets/blender/enemies/tyrian10-203.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b106 as lib  # noqa: E402

NAME = "tyrian10-203"
# Each light's palette index on each frame (first frame, {other frames}): its brightest pixel, or
# for the long strips (a red-to-white gradient) the colour of most of the strip.
LIGHTS = {"strip": (117, {205: 120, 207: 124}), "cap_strip": (115, {205: 118, 207: 121}),
          "red": (115, {205: 122, 207: 126}), "green": (195, {205: 201, 207: 207})}


def build(sprite):
    return [(NAME, lib.build_light_capsule(sprite, NAME, near_lights=True, lights=LIGHTS), sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
