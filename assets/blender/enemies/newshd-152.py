"""Small grey-blue asteroid (newshd.shp frame 152): a 3D version of its sprite.

Seen in episodes 1-3. A lumpy rock traced to the sprite's silhouette, its lit facets raised and
painted with the sprite's own blue-grey ramp (see lib_b014.rock). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-152.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

NAME = "newshd-152"

if __name__ == "__main__":
    lib.rock_script(NAME, __file__, half_height=0.17, relief=0.04, seed=152)
