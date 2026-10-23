"""Wall of fire, left-hand side (newsh3.shp, assembly of 4 pieces): a 3D version of its sprites.

Seen in episode 4 (level 4.6). Four 2x2 enemies make one 48x84 px fire (sprite.json
`assemblyLayout`): a column of flame three pieces tall (newsh3-22 at the top with its tall spike,
newsh3-60, newsh3-98) and a tongue of fire curling out to the left of its foot (newsh3-96).
Its mirror-like partner on the right is assembly-newsh3-99. Each piece has one frame.

The fire is built whole (lib_b050: a rounded body on the flame's outline with a tongue of flame
along each bright streak, hotter cores standing higher), then cut into its pieces.

Run: blender --background --python assets/blender/enemies/assembly-newsh3-96.py [-- --preview out.png]
(the preview is the whole fire; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b050  # noqa: E402

NAME = "assembly-newsh3-96"
ROOT = common.repo_root(__file__)
# (model, screen cx, cy) from sprite.json assemblyLayout; the grid's top-left is screen (130, -29).
PIECES = [("newsh3-22", 166, -15), ("newsh3-60", 166, 13), ("newsh3-98", 166, 41), ("newsh3-96", 142, 41)]

if __name__ == "__main__":
    lib_b050.build_wall(ROOT, NAME, PIECES, 130, -29, 48, 84, sys.argv)
