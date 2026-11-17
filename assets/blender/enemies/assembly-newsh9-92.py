"""TIME WAR's grey mothership, lower half, 48 x 56 px (newsh9 244|246 over 92|94): the bridge windows,
the lamps and the plated stern with its glowing channel.

The craft is built whole by lib_newsh9_mothership.py (see its docstring); this script exports only the
four lower pieces, assembly-newsh9-54.py the four upper ones.
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh9-92.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newsh9_mothership as lib  # noqa: E402

if __name__ == "__main__":
    lib.main(only=lib.LOW_PIECES)
