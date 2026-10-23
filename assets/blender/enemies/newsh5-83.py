"""Grey diagonal pod (newsh5.shp frame 83): a 3D version of its sprite.

Seen in episode 4 (level 4.22) lying on the ground. A faceted metal capsule lying from the lower
left to the upper right: a big body whose end tapers square to the tile's axes, a darker middle
band between two grooves and a lighter rounded cap at the lower left, with a small dark foot under
it. Its lit facets face up-left, its shaded ones down-right. newsh5-81 is its mirror image (built
by the same code in lib_b068.build_diagonal_pod).

Run: blender --background --python assets/blender/enemies/newsh5-83.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b068 as L  # noqa: E402

common = L.common
NAME = "newsh5-83"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = L.build_diagonal_pod(sprite, NAME, mirror=False)
    L.export_frames(ROOT, NAME, sprite, [(obj, [f["index"] for f in sprite["frames"]])])


if __name__ == "__main__":
    main()
