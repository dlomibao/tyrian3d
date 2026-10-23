"""Grey ring on the ground (newsha.shp frame 127): a 3D version of its sprite.

Seen in episode 3 (levels 3.2 and 3.25). A big, thick light grey ring (columns 1-22, rows 3-24) lying flat on the ground,
lit from the upper left like a metal hoop, so it is a torus resting on z = 0. One frame, one model.

Run: blender --background --python assets/blender/enemies/newsha-127.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b107 as lib  # noqa: E402

NAME = "newsha-127"
ROOT = common.repo_root(__file__)


def main():
    # Centre (pixel edges), ring radius and tube half width in px, tube half height in units.
    lib.ring_model(NAME, ROOT, (12.0, 14.0), 9.25, 1.75, 0.13, 9)


if __name__ == "__main__":
    main()
