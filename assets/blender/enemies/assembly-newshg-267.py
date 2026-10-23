"""Grey cannon emplacement in the grass, facing right (newshg.shp, assembly of newshg-267 and
newshg-269): a 3D version of their sprites.

Seen in episode 2 (levels 2.2, 2.21, 2.22 and 2.24), below the waterfall, often stacked between
copies of its mirror image (assembly-newshg-231). Two 2x2 pieces side by side make one 48x28 px
gun lying in jungle grass, the mirror image of newshg-229 + newshg-231: the collar, end box,
diagonal strut and glowing exhaust slot on the left (newshg-267), the long tube with its scope
lens and sliding hatch bending down into a capped elbow on the right (newshg-269), a dark deck
with a grille along its front and a glowing port at the seam. The three frames of each piece
only flicker the glows and slide the small hatch, so one model covers each piece.

The machine is lib_b077.build_cannon mirrored, cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshg-267.py [-- --preview out.png]
(the preview is the whole gun; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b077 as L  # noqa: E402

ROOT = common.repo_root(__file__)

if __name__ == "__main__":
    L.cannon_main(ROOT, "newshg-267", "newshg-269", True, "assembly-newshg-267")
