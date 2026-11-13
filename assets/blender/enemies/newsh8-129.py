"""newsh8-129: the carrot prop, newsh8.shp.

Built by the shared batch script assembly-newsh8-229.py (one design for the four merged items,
D65); this file builds and exports only its own models.

Run: blender --background --python assets/blender/enemies/newsh8-129.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("b060_batch", Path(__file__).resolve().parent / "assembly-newsh8-229.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main("carrot")
