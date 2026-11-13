"""TIME WAR's left edge cannon (4.17), a 3D version of its sprites: the mount and its muzzle
with the flash frames. Each script builds both cannons with lib_newshl_cannon (the right is the left's
mirror) and exports only its own two models, so no model is written twice. See lib_newshl_cannon.py.

Run: blender --background --python assets/blender/enemies/assembly-newshl-153.py [-- --measure DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_newshl_cannon as lib  # noqa: E402

# This cannon's pieces, mount and muzzle (the inventory reads the unit from these names).
PIECES = ("newshl-153", "newshl-155")
assert [lib.LEFT["mount"], lib.LEFT["muzzle"]] == list(PIECES)

if __name__ == "__main__":
    lib.main("left")
