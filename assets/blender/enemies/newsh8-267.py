"""Tan claw craft (newsh8.shp 267/269/271): built and exported by newsh8-19.py, which holds both
designs (they share the tan/red family and helpers). Run: blender --background --python
assets/blender/enemies/newsh8-267.py"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsh8_19_build", Path(__file__).with_name("newsh8-19.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main("267")
