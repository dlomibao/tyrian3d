"""Broken brown pod (newshe.shp frame 235): a 3D version of its sprite.

A ground object: a round shell split open, seen from above. Its rim is a low ring wall, thin on
the left and top and thick at the front and right, where its shadowed inner wall shows; the
middle is open to the ground. A pink ball sits inside, held by a thin claw that rises from the
front of the rim and bends over the ball's top.

Run: blender --background --python assets/blender/enemies/newshe-235.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b070 as lib  # noqa: E402

NAME = "newshe-235"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def E(ec, er):
    """Pixel-edge coordinates (column, row edges) to Blender X, Y."""
    return ((ec - 12) / 12, (14 - er) / 12)


def build(sprite):
    coll = common.reset_collection(NAME)
    frame = sprite["frames"][0]
    grid = lib.Grid(24, 28, frame["pixels"])
    mats = lib.Mats(NAME, sprite["colors"])
    DARK = mats(65, metallic=0.2, roughness=0.75)  # shadowed inner wall, claw
    SHELL = mats(67, metallic=0.2, roughness=0.65)  # rim
    LIT = mats(70, metallic=0.25, roughness=0.55)  # lit front of the rim
    PALE = mats(74, metallic=0.3, roughness=0.45)  # highlights on the rim's front
    BALL = mats(76, metallic=0.35, roughness=0.3)  # pink ball
    BALL_DIM = mats(72, metallic=0.35, roughness=0.35)
    BALL_HI = mats(78, metallic=0.4, roughness=0.25)
    bm = bmesh.new()

    # Rim: outer outline edges cols 4-20, rows 7-22; the opening (cols 5-17, rows 8-18) sits up
    # and left of centre, so the wall is one pixel thin at the left and top and 3-4 px at the
    # right and front.
    n = 40
    ocx, ocy = E(12, 14.5)
    icx, icy = E(10.8, 13)
    outer, inner, heights = [], [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        outer.append((ocx + 8.1 / 12 * ca, ocy + 7.6 / 12 * sa))
        inner.append((icx + 5.6 / 12 * ca, icy + 5.0 / 12 * sa))
        thick = math.hypot(outer[-1][0] - inner[-1][0], outer[-1][1] - inner[-1][1]) * 12
        heights.append(0.13 + 0.045 * thick)
    first = lib.crater(bm, outer, inner,
                       [(0.0, 0.0), (0.15, [h * 0.5 for h in heights]), (0.33, [h * 0.9 for h in heights]),
                        (0.5, heights), (0.68, [h * 0.8 for h in heights]), (0.86, [h * 0.35 for h in heights]),
                        (1.0, 0.0)], mat_index=SHELL)

    def rim_slot(v):
        if v in (16, 64, 65):
            return DARK
        if v <= 68:
            return SHELL
        if v <= 72:
            return LIT
        return PALE
    lib.paint(bm, first, grid, rim_slot)

    # Pink ball inside (cols 7-10, rows 10-13), resting on the ground.
    bx, by = E(9, 12.1)
    first = lib.blob(bm, (bx, by, 0.2), (2.3 / 12, 2.2 / 12, 0.2), segments=16, rings=8, mat_index=BALL)

    def ball_slot(v):
        if v <= 72:
            return BALL_DIM
        if v <= 76:
            return BALL
        return BALL_HI
    lib.paint(bm, first, grid, ball_slot, skip=(-1, 16, 64, 65, 66, 67, 68))

    # The claw: from the front of the rim (col 12-13, row 17) up past the ball's right side and
    # over its top (the dark arc at cols 11-13, rows 9-13).
    path = [(12.8, 18.6, 0.18), (12.6, 16.2, 0.24), (13.3, 14.0, 0.3), (13.6, 12.0, 0.36),
            (13.0, 10.3, 0.4), (11.8, 9.6, 0.4), (10.8, 9.6, 0.36)]
    first = len(bm.faces)
    lib.tube(bm, [((E(c, r)[0], E(c, r)[1], z), 0.65 / 12 if i < len(path) - 1 else 0.3 / 12)
                  for i, (c, r, z) in enumerate(path)], sides=6, mat_index=DARK)

    def claw_slot(v):
        return LIT if 69 <= v <= 72 else PALE if v >= 73 else DARK
    lib.paint(bm, first, grid, claw_slot)

    return lib.to_object(NAME, bm, mats.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, NAME, [obj], sprite)


if __name__ == "__main__":
    main()
