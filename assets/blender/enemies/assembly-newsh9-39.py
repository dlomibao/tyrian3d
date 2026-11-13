"""EYESPY's (4.13) left grey robot arm (newsh9-1, newsh9-3, newsh9-39): the builder is lib_b028.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-39.py
Exports only the left arm's three pieces (the right arm is assembly-newsh9-45.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b028  # noqa: E402

if __name__ == "__main__":
    lib_b028.run(__file__, "left")
