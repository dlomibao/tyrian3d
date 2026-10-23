"""Blue ground rocket (newshv.shp frame 235): a 3D version of its sprite.

Seen in episode 2 (level section 17). A finned blue rocket lying on the ground, pointing
right: a rounded nose, small swept fins at the front, a dark joint ring, big square fins
mid-body, a narrow dark rear section between two housings with blue lights, and a wide engine
flange at the back. newshv-237 is the same rocket facing the other way; both are built by
lib_b111.build_rocket.

Run: blender --background --python assets/blender/enemies/newshv-235.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b111 as lib  # noqa: E402

NAME = "newshv-235"
ROOT = common.repo_root(__file__)


def build(sprite):
    return lib.build_rocket(sprite, NAME, flip=True)


if __name__ == "__main__":
    lib.run(ROOT, NAME, build)
