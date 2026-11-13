"""Mace chain ring (newsha.shp frame 87): forged round-link steel ring, design A. See lib_b107.py.

Run: blender --background --python assets/blender/enemies/newsha-87.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_b107 as lib  # noqa: E402

NAME = "newsha-87"

if __name__ == "__main__":
    lib.main(NAME)
