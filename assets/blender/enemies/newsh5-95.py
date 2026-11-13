"""The green energy arrow (frames 95, 209, 247) (newsh5.shp, BRAINIAC 4.15): a 3D version of its sprites.

The brain is one object built in lib_b029 (design notes there) and cut into its pieces; this script
exports only its own models: newsh5-95. Run:
blender --background --python assets/blender/enemies/newsh5-95.py
(or tools/build-models.sh -j 2 assets/blender/enemies/newsh5-95.py).
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b029 as lib  # noqa: E402

MODELS = ["newsh5-95"]


def main():
    lib.export(MODELS)


if __name__ == "__main__":
    main()
