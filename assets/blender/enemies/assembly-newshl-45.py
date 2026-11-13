"""Panel satellite (newshl.shp 7, 9, 45, 47), a 2x2 block: a 3D space station.

The build lives in lib_b020.py (shared by the four scripts of this station and its spindles); this script
builds and exports only the four pieces newshl-7, -9, -45, -47. Run: blender --background --python assets/blender/enemies/assembly-newshl-45.py
[-- --measure DIR] [--views DIR] [--no-bake]  (review output only behind a flag).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b020 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run_station("assembly-newshl-45", ["newshl-7", "newshl-9", "newshl-45", "newshl-47"], (286, -3),
                    "newshl-24", False)
