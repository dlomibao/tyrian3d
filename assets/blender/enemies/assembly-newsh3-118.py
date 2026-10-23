"""Wall of fire, right flame column and left lava (newsh3.shp frames 44, 82, 118): a 3D version
of its sprites.

Seen in episode 4 (level 4.6). Six 2x2 enemies make one 48x84 px fire: two flame columns of
tongues licking up from a bed of bubbling lava. This assembly is three of them: newsh3-44 (the
top of the right column, a tall thin tongue and the tip of the small middle one), newsh3-82
(the right column's body) and newsh3-118 (the lava under the left column). The whole fire is
built once in lib_b049 and cut into pieces; assembly-newsh3-117 exports the other three.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-118.py [-- --preview out.png]
(the preview is the whole fire; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b049  # noqa: E402

if __name__ == "__main__":
    lib_b049.run("assembly-newsh3-118", ["newsh3-82", "newsh3-44", "newsh3-118"])
