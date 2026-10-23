"""Green orb, medium (newshh.shp frame 127): a 3D version of its sprite.

Seen in episode 2 (level 2.4). A glossy green ball lit from the top left, darker toward its lower
rim, with a bright reflection along the bottom right. Its sprite is 16 x 15 px. The model is a squashed
sphere filling the sprite's disc whose facets take the green of the sprite pixels under them, so
the highlight and the reflection sit where the sprite draws them. One frame.

Run: blender --background --python assets/blender/enemies/newshh-127.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b063 as lib  # noqa: E402

NAME = "newshh-127"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = lib.green_orb(sprite, NAME, coll)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
