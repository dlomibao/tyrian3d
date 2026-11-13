"""newshg-77: part of the merged item newshg-121 (claw drone, eye pod, stag beetle, lava crystal).

One design, one script: this builds only the crystal group of newshg-121.py.
Run: blender --background --python assets/blender/enemies/newshg-77.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newshg_121", Path(__file__).resolve().parent / "newshg-121.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main(["crystal"])
