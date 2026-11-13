"""Glowing core in the ice (newsh7.shp frames 55, 93, 131).

Built together with the mortar turret by assembly-newsh7-203.py (one script builds
newsh7-169, newsh7-203, -f2, -f3 and this core, sharing the ice and palette helpers; D65 design).
This file loads it and builds only the core (main("core")); run directly, the turret script builds
only the turret, so a full build writes each glb once.

Run: blender --background --python assets/blender/enemies/newsh7-55.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh7_203_build", Path(__file__).resolve().parent / "assembly-newsh7-203.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main("core")
