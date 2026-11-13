"""Twin-disc spindle (newshl.shp 24): the station's end spindle.

The build lives in lib_b020.py (shared by the four scripts of this station and its spindles); this script
builds and exports only newshl-24. Run: blender --background --python assets/blender/enemies/newshl-24.py
[-- --measure DIR] [--views DIR] [--no-bake]  (review output only behind a flag).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b020 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run_spindle("newshl-24", False)
