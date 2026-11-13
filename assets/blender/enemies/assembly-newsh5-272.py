"""The brain boss's underside (frames 272, 274, 276) (newsh5.shp, BRAINIAC 4.15): a 3D version of its sprites.

The brain is one object built in lib_b029 (design notes there) and cut into its pieces; this script
exports only its own models: newsh5-272, newsh5-274, newsh5-276. Run:
blender --background --python assets/blender/enemies/assembly-newsh5-272.py
(or tools/build-models.sh -j 2 assets/blender/enemies/assembly-newsh5-272.py).
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import lib_b029 as lib  # noqa: E402

MODELS = ["newsh5-272", "newsh5-274", "newsh5-276"]


def main():
    lib.export(MODELS)


if __name__ == "__main__":
    main()
