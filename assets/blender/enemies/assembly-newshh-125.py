"""Grey organism on a tube wall (newshh.shp 85, 87, 123, 125): a 3D version of its sprites.

Seen in level 2.4. Four 2x2 enemies make one 48 x 56 px block: a creature (stalk, curled abdomen, egg gland,
purple vein sleeve and siphons) lying on the GYGES tube wall. Built and cut into its four pieces by lib_b063.

Run: blender --background --python assets/blender/enemies/assembly-newshh-125.py
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b063 as lib  # noqa: E402

if __name__ == "__main__":
    lib.export_block()
