"""Spinning red coin (tyrian.shp#10 frames 26-31): a 3D version of its sprite.

A bonus coin seen in episodes 1 and 4: a copper-red disc with a lighter rim. It spins about the screen's vertical axis in six frames (face on, turning, edge on and
back), so each frame gets its own model: the same thick coin, raised rim and bevelled edge, turned
to that frame's angle (lib_b021.COIN_ANGLES). The dark outline is left to the game's outline.

Run: blender --background --python assets/blender/enemies/tyrian10-26.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b021 as lib  # noqa: E402

NAME = "tyrian10-26"


def build(sprite):
    return lib.coin_models(sprite, NAME, face=73, rim=74, edge=71, metallic=0.8)


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
