"""Grey shield ship, 48x56 px (newsh9 92/94 over 244/246).

The model is built by the shared builder lib_b019.py (see its docstring); this script exports only
the four ship pieces.
Run: blender --background --python assets/blender/enemies/assembly-newsh9-92.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b019 as lib  # noqa: E402

ONLY = ["newsh9-92", "newsh9-94", "newsh9-244", "newsh9-246"]

if __name__ == "__main__":
    lib.main(only=ONLY)
