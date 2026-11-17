"""Large grey asteroid (newshd.shp frame 5, a 22 x 20 px rock in its 24 x 28 block): a 3D version
of its sprite, on the crag builder (lib_crag_rock, D239). newshd-18 is this rock with a glowing vent.

What it is: a loose asteroid, the darkest and most broken of the family: a bright mass in the upper
middle with a small dark pit at its upper left, a bright lobe on the right, a lit patch on the left
and a smaller lit lobe low in the middle, dark crevices in from the left and down the middle, the
lower flanks in shadow. Round and closed underneath.

    blender -b --factory-startup -P assets/blender/enemies/newshd-5.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-5.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "newshd-5"
# The most broken of the family: its lit patches are two to four pixels wide, so the masses are let
# fall smaller than the builder's default (seven stones), each on a higher index of its own pixels
# (its dark half is crevice and shadow).
SPEC = {"seed": 5, "min_px": 6, "merge": 3.0, "blur": 0.5, "q": 0.82}

if __name__ == "__main__":
    lib.main(NAME, SPEC)
