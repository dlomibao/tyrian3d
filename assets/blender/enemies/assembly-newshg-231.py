"""Grey cannon emplacement in the grass (newshg.shp, assembly of newshg-229 and newshg-231): a 3D
version of their sprites.

Seen in episode 2 (levels 2.2, 2.21, 2.22 and 2.24), below the waterfall. Two 2x2 pieces side by
side make one 48x28 px gun lying in jungle grass: a long steel tube with a scope lens and a
sliding hatch on top, bending down into a capped elbow at its left end (newshg-229); a narrow
shaft through a collar to an end box on the right, propped on a diagonal strut, with an exhaust
slot glowing beside it (newshg-231). A dark deck with a grille runs along its front, with a
glowing port at the seam. The three frames of each piece only flicker the glows and slide the
small hatch, so one model covers each piece.

The machine is built whole in assembly coordinates (lib_b077.build_cannon, shared with its mirror
image assembly-newshg-267) and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshg-231.py [-- --preview out.png]
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
    L.cannon_main(ROOT, "newshg-229", "newshg-231", False, "assembly-newshg-231")
