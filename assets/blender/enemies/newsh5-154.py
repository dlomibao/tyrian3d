"""Brown fingertip (newsh5.shp frame 154): a 3D version of its sprite.

Seen in episode 4 (level 4.25, the flying face). A rounded brown finger pointing up the screen,
running off the bottom of the sprite: a domed tip, a smooth oval nail down its middle with a
bright rim on its lit left side, and the next finger's knuckle peeking out on the right past a
dark crease.

Run: blender --background --python assets/blender/enemies/newsh5-154.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-154"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(22, metallic=0.0, roughness=0.55),  # 0 skin
        pal(19, metallic=0.0, roughness=0.65),  # 1 dark skin (the knuckle beside it)
        pal(23, metallic=0.05, roughness=0.3),  # 2 nail
        pal(27, metallic=0.05, roughness=0.25),  # 3 nail rim
    ]
    SKIN, DARK, NAIL, RIM = range(4)
    g = lib.Grid(24, 28, common.load_sprite(ROOT, NAME)["frames"][0]["pixels"])
    bm = bmesh.new()

    # The finger: a dome over the sprite's silhouette, highest along the nail.
    outline = lib.resample(lib.mask_outline(g, lambda v: v >= 0, rounds=3, inset=0.2), 40)
    f0 = lib.pillow(bm, outline, (g.x(11.5), g.y(15)), -0.04, 0.24, 0.16, rings=7, mat_index=SKIN)
    lib.set_smooth(bm, f0)

    # The knuckle on the right (columns 19-21, rows 16-27).
    f0 = lib.ellipsoid(bm, (g.x(19.0), g.y(21.2), -0.01), (2.3 * U, 4.8 * U, 0.13), segments=12, rings=6, mat_index=DARK)
    lib.set_smooth(bm, f0)

    # The nail: a smooth oval (columns 8-14, rows 7-23) with a bright rim on its left.
    f0 = lib.ellipsoid(bm, (g.x(10.3), g.y(15.2), 0.15), (2.9 * U, 8.6 * U, 0.075), segments=16, rings=8, mat_index=RIM)
    lib.set_smooth(bm, f0)
    f0 = lib.ellipsoid(bm, (g.x(10.9), g.y(15.0), 0.165), (2.6 * U, 8.0 * U, 0.07), segments=16, rings=8, mat_index=NAIL)
    lib.set_smooth(bm, f0)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
