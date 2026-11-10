"""Green dome pad (newsha.shp frames 17, 55): the green twin of newsha-93, same design and code.

Run: blender --background --python assets/blender/enemies/newsha-17.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsha93_lib", Path(__file__).resolve().parent / "newsha-93.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main(("newsha-17",))
