"""Grey stone spire in a lava-rock mound (newsh3.shp frames 237 over 275, CORE, episode 4 level 4.5): newsh3-237 and newsh3-275.

The builder is shared by the newsh3.shp family (lib_b115.py, whose docstring has the flags); this script builds
and exports only its own models.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newsh3-275.py -- [--views DIR] [--game DIR] [--nobake]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b115 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run("spire")
