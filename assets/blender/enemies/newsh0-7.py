"""Left horn of the level 2.12 dragon (newsh0.shp frame 7): a 3D version of its sprite.

The dragon boss is built from many 2x2 sprites; this one is the tall left horn above its head,
a curved blue spike that leans right as it rises and widens into the head below. The base runs to
the tile's bottom edge so it meets the head piece. A dark groove runs down the lower half.

Run: blender --background --python assets/blender/enemies/newsh0-7.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b066  # noqa: E402

if __name__ == "__main__":
    lib_b066.run("newsh0-7", __file__, groove_col=13, groove_from=17)
