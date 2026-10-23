"""Glowing red gem (tyrian.shp#10 frames 14-18): a 3D version of its sprite.

A bonus gem seen in episodes 1, 3 and 4: a diamond-shaped cut stone, red at the edges and
yellow-white at the centre, with a ring of bright facets. The five frames only brighten it (the
palette indices step up by one each frame), so one model covers them all; the crown glows.

Run: blender --background --python assets/blender/enemies/tyrian10-14.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402

NAME = "tyrian10-14"


def build(sprite):
    return lib.gem_model(sprite, NAME, body=115, crown=117, ridge=120, inner=122, core=125, glow=2.0, core_glow=5.0)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
