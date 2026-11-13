"""Panel satellite facing left (newshl.shp 11, 13, 49, 51): the exact mirror of assembly-newshl-45.

The build lives in lib_b020.py (shared by the four scripts of this station and its spindles); this script
builds and exports only the four pieces newshl-11, -13, -49, -51. Run: blender --background --python assets/blender/enemies/assembly-newshl-49.py
[-- --measure DIR] [--views DIR] [--no-bake]  (review output only behind a flag).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b020 as lib  # noqa: E402

if __name__ == "__main__":
    lib.run_station("assembly-newshl-49", ["newshl-11", "newshl-13", "newshl-49", "newshl-51"], (36, -3),
                    "newshl-34", True)
