"""Dark steel ball (newsha.shp frame 283): a 3D version of its sprite.

Seen in episode 1 (level 1.13). A plain gunmetal ball lying on the ground, lit from the top left
with a bright highlight and a pale rim of reflected light along its lower right edge (both are
shading, so the model is just the polished ball).

The sprite covers columns 3-20 and rows 5-21 (centre at column 12, row 13.5). The ball sits on
the ground (base at z = 0), a little squashed so it stays low.

Run: blender --background --python assets/blender/enemies/newsha-283.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b113 as lib  # noqa: E402

NAME = "newsha-283"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = lib.ball(NAME, sprite, 5, 12.0, 13.5, 9.0, 8.5, 0.6, metallic=0.7, roughness=0.2)
    lib.export_single(ROOT, NAME, obj, sprite)


if __name__ == "__main__":
    main()
