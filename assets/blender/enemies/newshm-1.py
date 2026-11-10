"""Red wall block (newshm.shp frame 1): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 levels 1, 13, 14; episode 4 level 2): the red glossy rounded block, tiled 19x into assembly-newshm-1.
The block is built by lib_newshm_block.py, shared by the four tiles so they match.

Run: blender --background --python assets/blender/enemies/newshm-1.py [-- --no-bake] [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshm_block as block  # noqa: E402

NAME = "newshm-1"

if __name__ == "__main__":
    block.main(NAME)
