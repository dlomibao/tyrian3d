"""The small lava bubble (newshe.shp frame 195, 24 x 28 px, one frame): one smooth ball of dark glass
with its heat painted on it (D230; lib_bubble.py has the method), the big bubble's
(assembly-newshe-229) small kin.

WHAT IT IS: a bubble, not a pod (types 477, 686 and episode 4's 287: armour 8-15, no gun; sprayed in
rings in 3.7 STARGATE, flying beside the big bubbles in 3.6 FLEET, and in 1.4 BUBBLES, the BONUS
levels, 2.9 MISTAKES and 4.9 LAVA EXIT). The sprite is the big bubble's drawing at 21 px: a black
crown (palette 1, 64 at its edge) over the upper half, the red body below it rising 113 to 119
toward the rim, the orange-yellow crescent on the lower right (120-127), a white glint (127, 2 x 2,
a halo down the ramp) and a dim one beside it (peak 121). No visor, no lenses, no armour petals.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshe-195.py
or: blender --background --factory-startup --python newshe-195.py -- [--out DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_bubble  # noqa: E402

NAME = "newshe-195"


if __name__ == "__main__":
    lib_bubble.build(__file__, NAME, [(NAME, 0, 0)], (24, 28), harmonics=2, h_top=4.5, h_bot=3.0,
                     n_theta=48, n_top=10, n_bot=3, rim=(0.7, 0.9, 1.0), shell_faces=500)
