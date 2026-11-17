"""The big lava bubble (newshe.shp 191/193/229/231, an assembly of 4 pieces): one smooth ball of dark
glass with its heat painted on it (D230; lib_bubble.py has the method).

WHAT IT IS: a free-flying bubble (types 682-685: one frame each, armour 20, no gun, no damaged
frame; it drifts down the screen over the ground in 2.9 MISTAKES, on the top layer in 3.6 FLEET,
on the sky layer and then the ground layers in 3.7 STARGATE, several overlapping). The flying kin
of the lava bubbles that level's ground is made of. Not a pod: the sprite has no cap, no lenses
and no belt, only a ball and a tone ramp, one palette step per pixel:
- a black crown (palette 1, 64 at its edge), about a third of the ball, toward the upper left;
- a dark red shoulder (112-113) to its right and below, rising to the rim: 112 to 119 over nine
  pixels on the south side, a thin 115-121 line on the west, 112-115 on the north;
- an orange to yellow crescent on the lower right (120-127), three pixels wide;
- four glints: a white one (127, 7 px, a 1 px halo down the ramp), a small white-yellow one, two
  dim red ones (peaks 117 and 120).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshe-229.py
or: blender --background --factory-startup --python assembly-newshe-229.py -- [--out DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_bubble  # noqa: E402

NAME = "assembly-newshe-229"
PIECES = [("newshe-191", 0, 0), ("newshe-193", 24, 0), ("newshe-229", 0, 28), ("newshe-231", 24, 28)]


if __name__ == "__main__":
    lib_bubble.build(__file__, NAME, PIECES, (48, 56))
