"""Grey gun works, upper left window: the thin barrel pointing left, the sloped housing and the column (newsh9.shp frame 235): a 3D version of its sprite.

Seen in episode 4 (level 4.18). The sprite is a window onto the left gun works drawing that
the assembly-newsh9-274 pieces also show, so the whole gun works is built
(lib_b089) and this sprite's 24x28 window cut out of it, keeping overlapping windows identical.

Run: blender --background --python assets/blender/enemies/newsh9-235.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b089  # noqa: E402

if __name__ == "__main__":
    lib_b089.run("left", ["newsh9-235"], "newsh9-235")
