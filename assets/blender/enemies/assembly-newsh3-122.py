"""Tan armoured crawler, the mirror twin (newsh3.shp frames 122 + 124, SURFACE, level 4.4): newsh3-122 and newsh3-124.

The builder is shared by the newsh3.shp family (lib_b115.py, whose docstring has the flags); this script builds
and exports only its own models.

    blender -b --factory-startup -P assets/blender/enemies/assembly-newsh3-122.py -- [--views DIR] [--game DIR] [--nobake]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b115 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run("b122")
