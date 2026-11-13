"""Green thorn (newshh.shp frames 77 and 115, an assembly of 2 pieces): a fast free-flying pod, nose down.
Built and cut into its two pieces by lib_b063.

Run: blender --background --python assets/blender/enemies/assembly-newshh-77.py
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

if __name__ == "__main__":
    lib.export_thorn()
