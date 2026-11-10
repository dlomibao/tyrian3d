"""newshp-171: built by newshp-237.py (the three share one design, D120/D121 lessons).

Run: blender --background --python assets/blender/enemies/newshp-171.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newshp_237_build", Path(__file__).resolve().parent / "newshp-237.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main({"newshp-171"})
