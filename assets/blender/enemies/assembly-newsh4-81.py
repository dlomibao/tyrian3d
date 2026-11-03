"""Horned bronze flagship, upper half (newsh4.shp 81, 83, 85): the head, horns and shoulder pods.

Three 2x2 enemies side by side over the body, wings and gun pods of assembly-newsh4-123 (the six are
enemy types 468-473, no armour: an event-18 flyby in level 1 just before the boss). The whole craft
is one hard-surface model built in lib_b065 (see its docstring); this script cuts the three upper
pieces from it with common.split_assembly and exports each to public/models/enemies/<piece>.glb with
its outline shell and its src/render/spriteModels entry. Each piece has a single frame.

Run: blender --background --factory-startup --python assets/blender/enemies/assembly-newsh4-81.py
     [-- --preview out.png] [--no-bake] [--measure DIR] [--views DIR] [--no-export]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b065 as lib  # noqa: E402

PIECES = lib.UPPER

if __name__ == "__main__":
    lib.run(PIECES, sys.argv)
