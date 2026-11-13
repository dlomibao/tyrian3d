"""Armoured eye sphere, lower eye and lid, 72x28 px (newsh9 210/212/214).

The model is built by the shared builder lib_b019.py (see its docstring); this script exports only
the three lower pieces.
Run: blender --background --python assets/blender/enemies/assembly-newsh9-210.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b019 as lib  # noqa: E402

ONLY = ["newsh9-210", "newsh9-212", "newsh9-214"]

if __name__ == "__main__":
    lib.main(only=ONLY)
