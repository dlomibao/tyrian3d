"""The brain boss's middle (frames 233, 235, 237, 239) (newsh5.shp, BRAINIAC 4.15): a 3D version of its sprites.

The brain is one object built in lib_b029 (design notes there) and cut into its pieces; this script
exports only its own models: newsh5-233, newsh5-235, newsh5-237, newsh5-239. Run:
blender --background --python assets/blender/enemies/assembly-newsh5-233.py
(or tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh5-233.py).
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b029 as lib  # noqa: E402

MODELS = ["newsh5-233", "newsh5-235", "newsh5-237", "newsh5-239"]


def main():
    lib.export(MODELS)


if __name__ == "__main__":
    main()
