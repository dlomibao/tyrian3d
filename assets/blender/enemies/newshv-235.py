"""newshv-235 (newshv.shp, palette 5): built by lib_b111.py (car newshv-163, rockets newshv-237 / newshv-235).

Run: blender --background --python assets/blender/enemies/newshv-235.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b111 as lib  # noqa: E402

if __name__ == "__main__":
    lib.main("r235")
