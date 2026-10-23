"""Grey gun works, upper right window: the thin barrel pointing right, the sloped housing and the column (newsh9.shp frame 239): a 3D version of its sprite.

Seen in episode 4 (level 4.18). The sprite is a window onto the right gun works drawing that
the assembly-newsh9-276 pieces also show, so the whole gun works is built
(lib_b089) and this sprite's 24x28 window cut out of it, keeping overlapping windows identical.

Run: blender --background --python assets/blender/enemies/newsh9-239.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b089  # noqa: E402

if __name__ == "__main__":
    lib_b089.run("right", ["newsh9-239"], "newsh9-239")
