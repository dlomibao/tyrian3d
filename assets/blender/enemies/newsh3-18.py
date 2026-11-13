"""Grey floor hatch raising a red-eyed turret (newsh3.shp frames 18, 56, 94, 284; DESERTRUN, level 4.10): newsh3-18, -f2 .. -f4.

The builder is shared by the newsh3.shp family (lib_b115.py, whose docstring has the flags); this script builds
and exports only its own models.

    blender -b --factory-startup -P assets/blender/enemies/newsh3-18.py -- [--views DIR] [--game DIR] [--nobake]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b115 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run("hatch")
