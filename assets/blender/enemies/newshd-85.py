"""Free-flying asteroid (newshd.shp frame 85, random spawns only): a 3D version of its sprite, on
the crag builder (lib_crag_rock, D239).

What it is: the widest loose asteroid, a heap of six or seven stones: a pale one with a lit rim at
the top, smaller ones round it, one with a ring on the lower right, dark crevices between all of
them. Round and closed underneath (D122).

    blender -b --factory-startup -P assets/blender/enemies/newshd-85.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-85.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "newshd-85"
SPEC = {"seed": 85}

if __name__ == "__main__":
    lib.main(NAME, SPEC)
