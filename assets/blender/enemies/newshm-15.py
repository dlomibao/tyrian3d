"""Green dollar block (newshm.shp frame 15): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 levels 1, 13, 14; episode 4 level 2): the same block in green with a raised gold dollar sign.
The block is built by lib_newshm_block.py, shared by the four tiles so they match.

Run: blender --background --python assets/blender/enemies/newshm-15.py [-- --no-bake] [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshm_block as block  # noqa: E402

NAME = "newshm-15"

if __name__ == "__main__":
    block.main(NAME)
