"""Grey pod, left half (newsha.shp frame 161): a 3D version of its sprite.

Seen in episode 2 (level 2.10) and 3 (3.2). newsha-161 and newsha-163 are mirror images, the
two halves of a pod pair: a body of revolution lying across the screen with its hub against the
inner tile edge (red lights at its ends), a ringed light-grey collar, then a cone to the nose
with a dark glass canopy on its upper flank. One frame, one model. The builder is shared:
lib_b044.build_pod.

Run: blender --background --python assets/blender/enemies/newsha-161.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b044 as lib  # noqa: E402

NAME = "newsha-161"


def build(sprite):
    return [(NAME, [lib.build_pod(sprite, NAME, nose=-1)], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
