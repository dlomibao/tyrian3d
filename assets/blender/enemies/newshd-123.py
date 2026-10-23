"""Grey asteroid (newshd.shp frame 123): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.5, 1.6, 1.21, 2.8 and 3.15). A grey boulder, 23 x 23 px, made of
a few lumps: a big pale one on the left, one on top right, a bright knob in the middle and two
smaller ones below, split by dark cracks. The rock follows the sprite's outline; its top rises in
those lumps (and a little with the sprite's shading, so the cracks sink), and each face takes the
grey of the sprite pixel under it. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-123.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b036 as lib  # noqa: E402
from lib_b036 import common  # noqa: E402

NAME = "newshd-123"
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
        (7.5, 10.5, 6.5, 0.07),  # big pale lump, left
        (17.0, 6.5, 5.5, 0.06),  # top right
        (14.5, 12.5, 3.5, 0.05),  # bright knob in the middle
        (7.0, 18.0, 5.0, 0.05),  # lower left
        (17.5, 16.5, 4.5, 0.04),  # lower right
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
