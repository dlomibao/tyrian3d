"""Grey pod, right half (newsha.shp frame 163): the mirror of newsha-161 (nose +X).

Both halves are built by newsha-161.py (design: a twin-nosed patrol pod, see its docstring).

Run: blender --background --python assets/blender/enemies/newsha-163.py
"""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("newsha_161", Path(__file__).resolve().parent / "newsha-161.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main(only="newsha-163")
