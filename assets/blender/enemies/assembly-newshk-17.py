"""Billowing fireball (newshk.shp frames 13, 15, 17, assembly of 3 pieces): a 3D version of its sprites.

Seen in episodes 3 (level 3.12) and 4 (level 4.4). Three 2x2 pieces side by side make one
72x28 px dome of fire bursting up out of the top of a machine (the newsho pieces below it,
modelled elsewhere): a lumpy red and orange rim, yellow billows and a white-hot heart. Its
bottom edge is where it meets the machine, so it is cut flat there; the top rounds off.

The fire is traced row by row from the sprite as nested glowing shells (red outside, then
orange, yellow and the white core, each a little taller than the one around it so it shows
through), built once in assembly coordinates and cut into the three pieces with
common.split_assembly. Each piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newshk-17.py [-- --preview out.png]
(the preview is the whole fireball; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b010 as lib  # noqa: E402

NAME = "assembly-newshk-17"
ROOT = common.repo_root(__file__)
# (piece, screen cx, cy) from sprite.json assemblyLayout.
PIECES = [("newshk-13", 92, 71), ("newshk-15", 116, 71), ("newshk-17", 140, 71)]
# (palette threshold, half height, palette index, emission strength), outermost first.
SHELLS = [
    (0, 0.15, 118, 2.5),  # red edges
    (121, 0.19, 121, 3.0),  # orange
    (124, 0.235, 124, 4.0),  # yellow
    (126, 0.3, 127, 5.0),  # white-hot core
]


def main():
    lib.fire_assembly(ROOT, __file__, NAME, PIECES, SHELLS, open_top=False, open_bottom=True)


if __name__ == "__main__":
    main()
