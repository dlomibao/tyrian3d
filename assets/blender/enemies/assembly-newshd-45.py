"""Big asteroid (newshd.shp 7, 9, 45, 47: an assembly of 4 pieces, one 48 x 56 cell): a 3D version
of its sprites, on the crag builder (lib_crag_rock, D239).

What it is: the biggest loose asteroid of ASTEROID1 (spawned on the ground, sky and top layers) and
ASTEROID?: a boulder of about nine fractured stones parted by dark cracks: a big pale flat-topped
stone on the upper left, a knob on top, a ridged crown on the upper right, a small slab in the
middle with a white lit edge, a dark flank on the right, rounded stones on the lower left and lower
right and a dark keel along the bottom. Round and closed underneath.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newshd-45.py -- [--no-bake] [--review DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "assembly-newshd-45"
PIECES = ["newshd-7", "newshd-9", "newshd-45", "newshd-47"]
# The stones' centres (sprite px in the 48 x 56 cell): the lit point the sprite draws on each. The
# lower stones and the keel are dim and the sprite parts them with faint cracks only, so the
# watershed's own peaks ran them together.
SEEDS = [(33.5, 7.5),    # the knob on top
         (38.0, 15.0),   # the ridged crown, upper right
         (21.5, 19.0),   # the big pale flat-topped stone
         (31.0, 26.0),   # the small slab with the white lit edge
         (40.0, 27.0),   # the dark flank on the right
         (19.0, 36.0),   # the rounded stone, lower left
         (35.0, 36.0),   # lower right
         (16.0, 45.0),   # the keel, left
         (33.0, 45.0)]   # and right
# Its stones are big, flat-faced and packed tight (the sprite parts them with hairline cracks, and
# its faces are an even mid grey: in game, lit, the default index came out a step and a half lighter
# than the sprite, median 115 against 93), so: steeper sides, a narrower gap, flatter crowns, and
# every stone one index down.
SPEC = {"seed": 45, "seeds": SEEDS, "side_el": (8.0, 16.0), "gap": 0.9, "tops": (8.0, 22.0), "tone": -1}

if __name__ == "__main__":
    lib.main_assembly(NAME, PIECES, SPEC)
