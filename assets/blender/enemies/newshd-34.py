"""Grey boulder, right half (newshd.shp frame 34, a 12x14 tile): a 3D version of its sprite.

Seen in episode 1 (level 1.5). Tiles 88 and 34 sit side by side as one grey boulder; this is its
right flank, the outline running down its right side. Both halves come from one rounded
height field (lib_b138.boulder) so they meet seamlessly, the lit areas of the sprite standing proud
and each facet painted with the sprite's own grey ramp. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-34.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b138 as lib  # noqa: E402

NAME = "newshd-34"

if __name__ == "__main__":
    lib.boulder(NAME, __file__)
