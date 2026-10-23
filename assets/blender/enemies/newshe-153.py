"""Cluster of brown bulbs (newshe.shp frame 153): a 3D version of its sprite.

A ground object: a heap of rounded brown lumps (rock or fungus) sitting on the ground: a big
lump at the back left and a round one at the back right, a long lump lying across the middle
from back left to front right, a small one on the right, a big one at the front left, one at
the front and a smaller one beside it.

Run: blender --background --python assets/blender/enemies/newshe-153.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "newshe-153"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)

# Lumps: (pixel col, row of the centre, half width px, half depth px, height, base z, angle in
# degrees from +X, counter-clockwise seen from above).
LUMPS = [
    (6.0, 7.4, 6.3, 5.2, 0.36, 0.0, -18),  # back left
    (18.3, 6.8, 4.7, 4.6, 0.32, 0.0, 0),  # back right
    (20.8, 12.4, 3.0, 2.6, 0.22, 0.0, 0),  # small, right
    (5.4, 17.8, 5.7, 4.9, 0.34, 0.0, 10),  # front left
    (13.8, 21.6, 4.5, 4.6, 0.3, 0.0, 0),  # front
    (16.4, 16.7, 3.4, 3.0, 0.26, 0.0, -20),  # beside the front one
    (13.4, 12.4, 7.6, 3.7, 0.3, 0.06, -38),  # the long one across the middle, on top of the others
]


def build(sprite):
    coll = common.reset_collection(NAME)
    grid = lib.Grid(24, 28, sprite["frames"][0]["pixels"])
    X, Y = grid.x, grid.y
    mats = lib.Mats(NAME, sprite["colors"])
    BASE = mats(70, metallic=0.1, roughness=0.6)
    LIGHT = mats(72, metallic=0.15, roughness=0.55)
    bm = bmesh.new()

    for c, r, rx, ry, h, z0, ang in LUMPS:
        first = lib.dome(bm, (X(c), Y(r), z0), ((rx + 0.5) / 12, (ry + 0.5) / 12, h), segments=18,
                         rings=5, mat_index=BASE, power=0.7, angle=math.radians(ang))
        # The lumps' lit tops (the sprite's 72-77 highlights) in a lighter brown.
        lib.paint(bm, first, grid, lambda v: LIGHT if v >= 72 else None)

    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
