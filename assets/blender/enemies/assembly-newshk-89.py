"""Fireball head of the falling fire column (newshk.shp frames 89, 91, 93).

The model is built by assembly-newshk-51.py (one fire column and the heater share a build, D186-style
rebuild); this script exports only its own part. Run: blender --background --python assets/blender/enemies/assembly-newshk-89.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("assembly_newshk_51", Path(__file__).resolve().parent / "assembly-newshk-51.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main(only="assembly-newshk-89")
