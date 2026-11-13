"""EYESPY's (4.13) right grey robot arm (newsh9-5, newsh9-7, newsh9-45), the left one mirrored: the builder is lib_b028.

Run: blender --background --python assets/blender/enemies/assembly-newsh9-45.py
Exports only the right arm's three pieces (the left arm is assembly-newsh9-39.py).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b028  # noqa: E402

if __name__ == "__main__":
    lib_b028.run(__file__, "right")
