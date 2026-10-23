"""Bronze ball (newsha.shp frame 281): a 3D version of its sprite.

Seen in episode 1 (levels 1.13 and 1.23). The same ball as newsha-283 in polished bronze: lit
from the top left with a pale highlight and a rim of reflected light along its lower right edge
(both shading, so the model is just the ball).

The sprite covers columns 3-20 and rows 5-21 (centre at column 12, row 13.5). The ball sits on
the ground (base at z = 0), a little squashed so it stays low.

Run: blender --background --python assets/blender/enemies/newsha-281.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b113 as lib  # noqa: E402

NAME = "newsha-281"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = lib.ball(NAME, sprite, 181, 12.0, 13.5, 9.0, 8.5, 0.6, metallic=0.65, roughness=0.25)
    lib.export_single(ROOT, NAME, obj, sprite)


if __name__ == "__main__":
    main()
