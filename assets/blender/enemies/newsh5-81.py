"""Grey diagonal pod (newsh5.shp frame 81): a 3D version of its sprite.

Seen in episode 4 (level 4.22) lying on the ground. The mirror image of newsh5-83 (built by the
same code, lib_b068.build_diagonal_pod, flipped left to right): a faceted metal capsule lying from
the lower right to the upper left, a big body at the upper left, a darker middle band between two
grooves and a lighter rounded cap at the lower right, with a small dark foot under it.

Run: blender --background --python assets/blender/enemies/newsh5-81.py [-- --preview out.png]
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
