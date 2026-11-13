"""Grey dome (newshh.shp frame 79): the silver cap on the organism's stalk, a 3D version of its sprite.
The damaged frame 41 is drawn with this intact model (D87). Built by lib_b063.

Run: blender --background --python assets/blender/enemies/newshh-79.py
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

if __name__ == "__main__":
    lib.export_cap()
