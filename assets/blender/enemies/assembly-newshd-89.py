"""Big rock heap (newshd.shp 13, 49, 51, 53, 89, 91, six 2 x 2 pieces, and its four 1 x 1 edge
pieces 15, 31, 34, 88): a 3D version of its sprites, on the crag builder (lib_crag_rock, D239).

What it is: the biggest rock of ASTEROID1, drifting on the ground layer, drawn there through a blue
hue filter (the ice-blue heap the level opens on): a 72 x 84 px heap of some twenty-five angular
stones with its corners missing, dark crevices between them, a big stone with a lit rim near the
top and another on the lower right. The four 1 x 1 enemies (types 444, 446 and the two of
lib_b138's batch) spawn with it and fill the concave corners of its outline: 31 left of piece 13's
lower half, 15 and 34 right of it, 88 left of piece 89's upper half. They are stones of the same
heap, so the heap is built whole from all ten sprites and cut into the ten models; newshd-15, -31,
-34 and -88's scripts run this one. Round and closed underneath (D122).

    blender -b --factory-startup -P assets/blender/enemies/assembly-newshd-89.py -- [--no-bake] [--review DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "assembly-newshd-89"
# (model, left, top, size): each piece's top-left corner in screen px as the level draws them
# (ASTEROID1 tick 80) and its size (2: 24 x 28, 1: 12 x 14).
TILES = [
    ("newshd-13", 127, 57, 2), ("newshd-31", 115, 71, 1), ("newshd-15", 151, 57, 1), ("newshd-34", 151, 71, 1),
    ("newshd-49", 103, 85, 2), ("newshd-51", 127, 85, 2), ("newshd-53", 151, 85, 2),
    ("newshd-88", 115, 113, 1), ("newshd-89", 127, 113, 2), ("newshd-91", 151, 113, 2),
]
# Ten lofts make its core (one per piece) and thirty-six stones stand on it: a coarser loft and
# only the sprite's own dark spots as pits keep it near the triangles of the heap it replaces.
# Its stones are big and packed tight, as assembly-newshd-45's: steeper sides and a narrower gap.
SPEC = {"seed": 89, "sectors": 28, "pits": 0, "side_el": (8.0, 16.0), "gap": 0.8, "lap": 0.0}

if __name__ == "__main__":
    lib.main_heap(NAME, TILES, SPEC)
