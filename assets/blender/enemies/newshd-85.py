"""Grey asteroid (newshd.shp frame 85): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.5, 1.6, 1.21, 2.8 and 3.15). A grey boulder, 24 x 25 px, made of
a few lumps: a big pale one on top, a small one jutting out on the left, two below it and two on
the lower right (the last trailing off to the bottom right corner), split by dark cracks. The rock follows the sprite's outline; its top rises in
those lumps (and a little with the sprite's shading, so the cracks sink), and each face takes the
grey of the sprite pixel under it. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-85.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b036 as lib  # noqa: E402
from lib_b036 import common  # noqa: E402

NAME = "newshd-85"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(24, 28, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    under = mats(4, metallic=0.1, roughness=0.9)
    bm = bmesh.new()
    lumps = [
        (11.0, 7.0, 6.5, 0.08),  # big pale lump on top
        (4.0, 12.0, 4.5, 0.04),  # jutting out on the left
        (8.5, 16.0, 5.0, 0.06),  # middle left, below
        (6.5, 20.5, 3.5, 0.02),  # dim, bottom left
        (19.0, 16.0, 5.0, 0.06),  # right
        (20.0, 21.5, 4.0, 0.03),  # bottom right corner
    ]
    first = lib.rock(bm, grid, (12.0, 13.0), top=0.22, bottom=0.16, lumps=lumps, shade=0.03,
                     colors=sprite["colors"], n=12, mat_index=under)
    lib.paint(bm, first, grid, lambda i: mats(i, metallic=0.1, roughness=0.85), min_nz=-0.3)
    return common.mesh_object(NAME, bm, mats.list, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
