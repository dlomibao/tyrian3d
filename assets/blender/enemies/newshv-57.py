"""Small red gem (newshv.shp frame 57, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 2 (level 2.15). A faceted diamond, bright along a ridge just right of centre, with
a short stalk trailing below it. newshv-19 is the same gem in blue.

Run: blender --background --python assets/blender/enemies/newshv-57.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b003 as lib  # noqa: E402

NAME = "newshv-57"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objects = lib.small_gem(sprite, NAME, 0)
    common.export_sprite_model(ROOT, objects, MODEL, sprite["sprites"])
    lib.preview(objects, ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
