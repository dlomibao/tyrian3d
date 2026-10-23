"""Red armour corner with a grey ball (newshf.shp frame 230): a 3D version of its sprite.

Seen in episodes 1-4 (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16), with newshf-238 as its partner.
The bottom-left corner of a red armoured hull: a lower ledge on the left, a flat dark red top
with two raised ribs running down it (the inner one curving round to the right along the
bottom), the outer edge chamfered along the diagonal, and a grey ball half sunk in a dark socket
at the right edge (cut by the tile edge, as the sprite is). Ground object: base at z = 0.

Run: blender --background --python assets/blender/enemies/newshf-230.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b101 as lib  # noqa: E402

NAME = "newshf-230"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Outlines in sprite pixel-edge coordinates (column, row); rows grow down the sprite.
SPEC = {
    "ledge": [(0, 0), (4.5, 0), (4.5, 9.0), (3, 7.5), (1, 4.0), (0, 2.2)],
    "ledge_chamfer": [False, False, True, True, True, True],
    "hull": [(4.5, 0), (24, 0), (24, 22.3), (19, 22.3), (16.5, 20.6), (13, 18.2), (9, 13.8), (5, 9.5),
             (4.5, 9.0)],
    "chamfer": [False, False, True, True, True, True, True, True, False],
    "ribs": [
        ([(9, 0), (12, 0), (12, 14.0), (9, 11.5)], False),
        ([(13, 0), (17, 0), (17, 12), (18.2, 13.4), (19.5, 14), (24, 14), (24, 19), (16, 19), (14.3, 18),
          (13, 16.5)], True),
    ],
    "socket": [(17.5, 1), (24, 1), (24, 13.6), (19.5, 13.6), (18, 12.5), (17.5, 11)],
    "ball": (22.5, 6.0, 4.6, 1),
}


def main():
    sprite = common.load_sprite(ROOT, NAME)
    bm, mats, coll = lib.build_corner(sprite, NAME, SPEC)
    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
