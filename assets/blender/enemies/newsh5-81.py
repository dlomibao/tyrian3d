"""Grey diagonal craft (newsh5.shp frame 81): a 3D version of its sprite.

Seen in episode 4 (4.15 BRAINIAC): groundBottom spawns at the screen's right corner that fly up the diagonal along
their long axis, to the upper left, so it is a craft or missile with no foot and no ground contact, closed
all round. A faceted metal capsule: a big body at the upper left tapering to a flat nose, a darker band
between two grooves and a lighter rounded cap at the tail, a slot and a recess on top.
The mirror image of newsh5-83 (built by the same code, lib_b068.build_diagonal_pod, flipped).
Silhouette half widths come from the sprite's inner mask; the outline shell is made from a sealed copy.

Run: blender --background --python assets/blender/enemies/newsh5-81.py -- [--review DIR] [--no-export]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-81"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = L.build_diagonal_pod(sprite, NAME, mirror=True)
    L.export_frames(ROOT, NAME, sprite, [(obj, [f["index"] for f in sprite["frames"]])])


if __name__ == "__main__":
    main()
