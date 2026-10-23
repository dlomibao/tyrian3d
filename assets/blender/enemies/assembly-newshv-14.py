"""Left twin cannon (newshv.shp 14 + 16, assembly of 2 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.18). Two cannons lie back to back, joined in the middle by their
couplings: newshv-14 is the left barrel with its end cap, bright ring and blue band, on a wedge
mount with two fins; newshv-16 is the back plate, a blue-grey half disc and the coupling (shaft,
bright ball joint, ring, dark socket). The right cannon (newshv-167 + 169, assembly-newshv-169)
is its mirror image; both scripts build the whole pair with lib_b081.build_cannon_pair and keep
their own pieces, so the halves meet at the seam.

Run: blender --background --python assets/blender/enemies/assembly-newshv-14.py [-- --preview out.png]
(the preview is the whole pair; each piece also gets out-<piece>.png).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b081 as lib  # noqa: E402

NAME = "assembly-newshv-14"
ROOT = common.repo_root(__file__)


if __name__ == "__main__":
    lib.export_cannon_pair(ROOT, NAME, ["newshv-14", "newshv-16"])
