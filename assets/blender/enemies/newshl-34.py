"""Twin-disc spindle facing left (newshl.shp 34): the exact mirror of newshl-24.

The build lives in lib_b020.py (shared by the four scripts of this station and its spindles); this script
builds and exports only newshl-34. Run: blender --background --python assets/blender/enemies/newshl-34.py
[-- --measure DIR] [--views DIR] [--no-bake]  (review output only behind a flag).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b020 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run_spindle("newshl-34", True)
