"""Red spiked mine (newsh5.shp frame 76): a 3D version of its sprite.

Seen in episode 4 (level 22). A small red ball with four spikes (up, down, left, right), short
studs between them and a hot orange-white core glowing through its top-left. One frame.

Run: blender --background --python assets/blender/enemies/newsh5-76.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b004 as lib  # noqa: E402

NAME = "newsh5-76"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
SIZE = 1


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(116, metallic=0.4, roughness=0.4),  # 0 red shell
        pal(118, metallic=0.5, roughness=0.3),  # 1 bright red spikes
        pal(122, metallic=0.3, roughness=0.3, emission_strength=2.0),  # 2 orange spike tips
        pal(123, emission_strength=3.5),  # 3 glowing core
        pal(127, emission_strength=5.0),  # 4 white-hot centre
        pal(113, metallic=0.3, roughness=0.6),  # 5 dark red studs and shadowed shell
        pal(120, metallic=0.3, roughness=0.35, emission_strength=1.5),  # 6 red-orange glow
    ]
    SHELL, SPIKE, TIP, CORE, HOT, DARK, WARM = range(7)
    bm = bmesh.new()

    # Body: columns 1-9, rows 2-10 (centre column 5, row 6).
    cx, cy = lib.px(5, SIZE), lib.row(6, SIZE)
    body = lib.Ellipsoid(cx, cy, 4.0 / 12, 4.0 / 12, 0.2)
    body.build(bm, segments=20, rings=12, mat_index=SHELL)
    # The shell glows where the sprite does: orange-yellow in the top-left, dark red lower right.
    def slot(i):
        if i < 0 or i == 1:
            return DARK
        if i >= 122:
            return CORE
        if i >= 119:
            return WARM
        return SHELL if i >= 115 else DARK
    lib.paint_from_sprite(bm, sprite["frames"][0]["pixels"], slot, size=SIZE, under_slot=DARK, min_nz=-0.3)

    # Spikes out to the tip pixels: up (column 4, row 0), down (5, 12), left (0, 6), right (10, 6).
    for tc, tr in ((4, 0.2), (5, 11.9), (0.1, 6), (9.9, 6)):
        tx, ty = lib.px(tc, SIZE), lib.row(tr, SIZE)
        dx, dy = tx - cx, ty - cy
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        base = 3.2 / 12
        lib.tube(bm, [(cx + ux * base, cy + uy * base, 0.0), (cx + ux * (ln - 0.12), cy + uy * (ln - 0.12), 0.0),
                      (tx, ty, 0.0)], [0.13, 0.06, 0.0], sides=8, mat_index=SPIKE)
        lib.tube(bm, [(cx + ux * (ln - 0.13), cy + uy * (ln - 0.13), 0.0), (tx, ty, 0.0)], [0.06, 0.0],
                 sides=8, mat_index=TIP)
    # Short studs on the diagonals (the square-ish corners of the body).
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        ux, uy = math.cos(a), math.sin(a)
        lib.tube(bm, [(cx + ux * 0.28, cy + uy * 0.28, 0.0), (cx + ux * 0.42, cy + uy * 0.42, 0.0)],
                 [0.06, 0.0], sides=6, mat_index=DARK)

    # The white-hot spot at column 5, row 5.
    lib.drape_cap(bm, body, lib.px(5.0, SIZE), lib.row(5.0, SIZE), 0.8 / 12, 0.8 / 12, lift=0.01,
                  dome=0.01, sink=0.0, sides=8, mat_index=HOT)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], sprite, ROOT, NAME)


if __name__ == "__main__":
    main()
