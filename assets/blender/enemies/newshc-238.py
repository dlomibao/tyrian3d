"""Rifle muzzle tip (newshc.shp frame 238, a 1x1 unit at the left end of assembly-newshc-243).

It is cut from the same whole rifle as the three pieces so it lines up, so it is built and exported
by assets/blender/enemies/assembly-newshc-243.py (which writes enemies/newshc-238 and its
src/render/spriteModels entry together with newshc-239/241/243). This script runs that one, so
building either gives all four units; tools/build-models.sh with both listed builds twice, so list
only one of them.

Run: blender --background --python assets/blender/enemies/newshc-238.py
"""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "assembly-newshc-243.py"), run_name="__main__")
