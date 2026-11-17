"""Asteroid (newshd.shp frame 123, a 22 x 22 px rock in its 24 x 28 block): a 3D version of its
sprite, on the crag builder (lib_crag_rock, D239).

What it is: a loose asteroid drifting through ASTEROID1/2, ASTEROID? and AST. CITY: a heap of four
or five big pale stones with flat lit tops (the big one upper left, the knob on the upper right,
two below), parted by dark crevices that meet near the middle, the lower rim in shadow. Round and
closed underneath.

    blender -b --factory-startup -P assets/blender/enemies/newshd-123.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-123.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "newshd-123"
SPEC = {"seed": 123}

if __name__ == "__main__":
    lib.main(NAME, SPEC)
