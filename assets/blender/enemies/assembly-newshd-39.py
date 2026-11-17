"""Drifting rock cluster (newshd.shp 1, 3, 39, 41: an assembly of 4 pieces, one 48 x 56 cell): a 3D
version of its sprites, on the crag builder (lib_crag_rock, D239).

What it is: a heap of about a dozen angular grey stones drifting in space (ASTEROID1, spawned on the
ground, sky and top layers; ASTEROID?), round and closed underneath, no base. The sprite draws a big
pale stone with a lit rim on the upper left, a white-edged slab low in the middle, smaller stones
round them going darker to the right and the bottom, and dark crevices one or two pixels wide
between all of them.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newshd-39.py -- [--no-bake] [--review DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "assembly-newshd-39"
PIECES = ["newshd-39", "newshd-1", "newshd-41", "newshd-3"]
SPEC = {"seed": 39}

if __name__ == "__main__":
    lib.main_assembly(NAME, PIECES, SPEC)
