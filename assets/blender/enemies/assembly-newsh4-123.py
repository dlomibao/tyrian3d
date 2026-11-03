"""Horned bronze flagship, lower half (newsh4.shp 119, 121, 123): the body, wings and gun pods.

Three 2x2 enemies side by side, drawn 24 px under the head, horns and shoulder pods of
assembly-newsh4-81 (the six are enemy types 468-473, no armour: an event-18 flyby in level 1 just
before the boss). The whole craft is one hard-surface model built in lib_b065 (see its docstring);
this script cuts the three lower pieces from it with common.split_assembly and exports each to
public/models/enemies/<piece>.glb with its outline shell and its src/render/spriteModels entry.
Each piece has a single frame.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newsh4-123.py
     [-- --preview out.png] [--no-bake] [--measure DIR] [--views DIR] [--no-export]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b065 as lib  # noqa: E402

PIECES = lib.LOWER

if __name__ == "__main__":
    lib.run(PIECES, sys.argv)
