"""TIME WAR's grey mothership, upper half, 48 x 56 px (newsh9 16|18 over 54|56): the blue canopy split
by the grey spine, the collar under its rim and the top of the bridge windows.

The craft is built whole by lib_newsh9_mothership.py (see its docstring); this script exports only the
four upper pieces, assembly-newsh9-92.py the four lower ones.
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh9-54.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newsh9_mothership as lib  # noqa: E402

if __name__ == "__main__":
    lib.main(only=lib.TOP_PIECES)
