"""Large grey asteroid (newshd.shp frame 5): a 3D version of its sprite.

Seen in episodes 1-3. A big lumpy rock traced to the sprite's silhouette, its lit facets raised
and its dark cracks sunk, painted with the sprite's own grey ramp (see lib_b014.rock). One frame,
one model.

Run: blender --background --python assets/blender/enemies/newshd-5.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b014 as lib  # noqa: E402

NAME = "newshd-5"

if __name__ == "__main__":
    lib.rock_script(NAME, __file__, half_height=0.26, relief=0.07, seed=5, subdiv=3)
