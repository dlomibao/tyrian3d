"""Green orb, small (newshh.shp frame 89): a closed glossy sphere. Built by lib_b063.

Run: blender --background --python assets/blender/enemies/newshh-89.py
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

if __name__ == "__main__":
    lib.export_orb("newshh-89")
