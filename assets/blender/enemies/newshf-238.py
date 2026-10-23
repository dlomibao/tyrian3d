"""Red armour corner with a grey ball (newshf.shp frame 238): a 3D version of its sprite.

Seen in episodes 1-4 (levels 1.10, 1.29, 1.38, 2.2, 3.21, 4.16), with newshf-230 as its partner.
The bottom-right corner of a red armoured hull, nearly newshf-230 mirrored: a lower ledge on the
right, a flat dark red top with two raised ribs running down it (the inner one curving round to
the left along the bottom), the outer edge chamfered along the diagonal, and a grey ball half sunk
in a dark socket at the left edge (cut by the tile edge, as the sprite is). Ground object: base
at z = 0.

Run: blender --background --python assets/blender/enemies/newshf-238.py [-- --preview out.png]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b101 as lib  # noqa: E402

NAME = "newshf-238"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Outlines in sprite pixel-edge coordinates (column, row); rows grow down the sprite.
SPEC = {
    "ledge": [(20.5, 0), (24, 0), (24, 4.0), (22, 7.5), (20.5, 8.5)],
    "ledge_chamfer": [False, False, True, True, False],
    "hull": [(0.5, 0), (20.5, 0), (20.5, 8.5), (19, 11), (16, 14), (14, 16.5), (12, 18), (8, 20), (5, 21.5),
             (2, 23), (0.5, 23)],
    "chamfer": [False, False, True, True, True, True, True, True, True, True, False],
    "ribs": [
        ([(8, 0), (12, 0), (12, 17), (11, 18.5), (9.5, 19.3), (0.5, 19.3), (0.5, 13.6), (6, 13.6), (7.3, 12.8),
          (8, 11.5)], True),
        ([(13, 0), (16, 0), (16, 12.5), (13, 15.8)], False),
    ],
    "socket": [(0.5, 0.8), (7, 0.8), (8, 4), (8, 11.5), (7.3, 12.8), (6, 13.5), (0.5, 13.5)],
    "ball": (1.7, 7.2, 4.8, -1),
}


def main():
    sprite = common.load_sprite(ROOT, NAME)
    bm, mats, coll = lib.build_corner(sprite, NAME, SPEC)
    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
