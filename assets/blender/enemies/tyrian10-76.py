"""Red-brown gem (tyrian.shp#10 frame 76): a 3D version of its sprite.

A bonus gem seen in episode 4: a diamond-shaped stone, dark red-brown, lit from a bright
pink point at its centre with ridges running out to the four tips. The single dark pixel at the
left tip is outline.

Run: blender --background --python assets/blender/enemies/tyrian10-76.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402

NAME = "tyrian10-76"


def build(sprite):
    return lib.gem_model(sprite, NAME, body=67, crown=69, ridge=70, inner=72, core=77, facets=False, core_glow=2.5)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
