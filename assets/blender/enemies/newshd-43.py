"""Three-lobed asteroid (newshd.shp frame 43): a 3D version of its sprite, on the crag builder
(lib_crag_rock, D239).

What it is: a loose asteroid with a notch on its right: an upper lobe with a bright ridge running
down-left, a bright cluster low in the middle, a lobe on the left, dark crevices between them.
Round and closed underneath.

    blender -b --factory-startup -P assets/blender/enemies/newshd-43.py -- [--no-bake] [--out file.glb]
    (or tools/build-models.sh -j 2 assets/blender/enemies/newshd-43.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_crag_rock as lib  # noqa: E402

NAME = "newshd-43"
# Its lobes are dim and its lit patches small: at the builder's default it fell into four big even
# stones (the game's render a median of 123 against the sprite's 84 on the bench), so the masses are
# let fall smaller, as newshd-5's: seven stones on indices 5 to 10.
SPEC = {"seed": 43, "min_px": 6, "merge": 3.0, "blur": 0.5}

if __name__ == "__main__":
    lib.main(NAME, SPEC)
