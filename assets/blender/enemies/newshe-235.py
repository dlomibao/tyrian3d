"""The clear bubble (newshe.shp frame 235, 24 x 28 px, one frame): the lava bubbles' pale, see-through
kin, one smooth ball of film with its tones painted on it (D230; lib_bubble.py has the method).

WHAT IT IS: a bubble, not a machine (types 479 and 687: armour 1, no gun; they rise in swarms in
3.7 STARGATE and with the red bubbles in 1.4 BUBBLES, the BONUS levels, 2.9 MISTAKES and 3.6
FLEET). The sprite is the red bubbles' drawing in the pale ramp (palette 64-79), 16 px across, and
most of its inside is clear: 47 of the pixels its outline encloses are transparent, and the level
shows through them. What is drawn is the film: a ring one pixel wide (67, darker 64-65 on the
upper right), a broader crescent of film on the lower right (64-65 inside, 68-77 at the rim), a
pink-white glint (peak 79) with two small ones beside it, and the dark arcs of the far side.

So: the same ball as the others, its film cut out (alpha, at a half) where the sprite is clear.
The film is the dome alone (the sprite already draws the far side's arcs on it); the level shows
through the openings.

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshe-235.py
or: blender --background --factory-startup --python newshe-235.py -- [--out DIR]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_bubble  # noqa: E402

NAME = "newshe-235"


if __name__ == "__main__":
    lib_bubble.build(__file__, NAME, [(NAME, 0, 0)], (24, 28), base=64, black={16: 0.0}, crown=64,
                     crown_level=-99.0, clear=0.5, lean=0.0, texels=4, harmonics=5, h_top=3.5, h_bot=2.3,
                     n_theta=40, n_top=8, n_bot=3, soft=(0.33, 0.3, 1.8), rim=(0.75, 0.95, 0.8),
                     shell_faces=1000)
