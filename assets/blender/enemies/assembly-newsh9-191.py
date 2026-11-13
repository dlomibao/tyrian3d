"""Armoured eye sphere, top 72x56 px (newsh9 153/155/157 over 191/193/195).

The model is built by the shared builder lib_b019.py (see its docstring); this script exports only
the six top pieces.
Run: blender --background --python assets/blender/enemies/assembly-newsh9-191.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b019 as lib  # noqa: E402

ONLY = ["newsh9-153", "newsh9-155", "newsh9-157", "newsh9-191", "newsh9-193", "newsh9-195"]

if __name__ == "__main__":
    lib.main(only=ONLY)
