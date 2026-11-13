"""newsh5-154 (the bridge of the giant nose, NOSE DRIP): built together with the nose in
assembly-newsh5-191.py (one object, D177/D182) and exported here as its own piece only.

Run: blender --background --python assets/blender/enemies/newsh5-154.py
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("assembly_newsh5_191", Path(__file__).resolve().parent / "assembly-newsh5-191.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main(only=["newsh5-154"])
