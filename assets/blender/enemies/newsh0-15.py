"""Grey pillar on a blue block, right-hand twin (newsh0.shp frame 15): a 3D version of its sprite.

Seen in episode 2 (level 2.12), briefly, as one of a row of pieces along the edge of a big
structure. A grey pillar with a rounded top (bright along its crown) stands at the right of the
top of a ribbed blue block, with a rounded blue lump at the bottom left. The block and lump run
off the bottom of the tile and are cut there. It is newsh0-1 mirrored about column 12 (lib_b025.build_tower_block).

Run: blender --background --python assets/blender/enemies/newsh0-15.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-15"
ROOT = common.repo_root(__file__)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = lib.build_tower_block(sprite, NAME, mirrored=True)
    common.export_sprite_model(ROOT, [obj], f"enemies/{NAME}", sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite["frames"][0]["image"])


if __name__ == "__main__":
    main()
