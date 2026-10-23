"""Wall of fire, left flame column and right lava (newsh3.shp frames 39, 77, 117): a 3D version of
its sprites.

Seen in episode 4 (level 4.6). Six 2x2 enemies make one 48x84 px fire: two flame columns of
tongues licking up from a bed of bubbling lava. This assembly is three of them: newsh3-39 (the
top of the left column, a tall thin tongue), newsh3-77 (the left column's body) and newsh3-117
(the lava under the right column). The whole fire is built once in lib_b049 (flame tongues as
tubes along the bright streaks over a slab of the silhouette, lava as lumps on a slab, each face
coloured by the sprite pixel under it, the brightest glowing) and cut into pieces;
assembly-newsh3-118 exports the other three.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-117.py [-- --preview out.png]
(the preview is the whole fire; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b049  # noqa: E402

if __name__ == "__main__":
    lib_b049.run("assembly-newsh3-117", ["newsh3-77", "newsh3-39", "newsh3-117"])
