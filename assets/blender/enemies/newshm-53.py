"""Purple X block (newshm.shp frame 53): a 3D version of its sprite.

A wall tile of assembly-newshm-1 (episode 1 levels 1, 13, 14; episode 4 level 2): the same block in purple with a glowing red X with curled ends.
The block is built by lib_newshm_block.py, shared by the four tiles so they match.

Run: blender --background --python assets/blender/enemies/newshm-53.py [-- --no-bake] [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshm_block as block  # noqa: E402

NAME = "newshm-53"

if __name__ == "__main__":
    block.main(NAME)
