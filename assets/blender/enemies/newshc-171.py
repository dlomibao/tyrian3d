"""Small pod with a purple orb (newshc.shp frames 171-304, 1x1 tile): a 3D version of its sprite.

Seen in episodes 1 (level 1.19) and 3 (3.23, 3.6). A purple orb sits in a pale blue cup with two
long thin prongs and a short stem reaching up the screen from it, darkening as they go (they
slope down to the ground). Its eight frames only flicker the prongs' shading and nudge the stem
by a pixel, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshc-171.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b097 import PX, ellipsoid, preview, preview_args, sweep, to_object  # noqa: E402
from lib_b097 import X as X24, Y as Y28  # noqa: E402

NAME = "newshc-171"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)


def X(c):
    return X24(c, 12)


def Y(r):
    return Y28(r, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(60, metallic=0.5, roughness=0.3),  # 0 pale blue cup
        pal(90, metallic=0.3, roughness=0.25, emission_strength=0.6),  # 1 purple orb
        pal(93, metallic=0.3, roughness=0.2, emission_strength=1.5),  # 2 orb highlight
        pal(58, metallic=0.5, roughness=0.35),  # 3 prongs near the cup
        pal(53, metallic=0.4, roughness=0.5),  # 4 prong tips
        pal(85, metallic=0.3, roughness=0.5),  # 5 dark rim round the orb
    ]
    CUP, ORB, ORB_HI, PRONG, TIP, RIM = range(6)
    bm = bmesh.new()
    cx = X(6.5)  # the sprite's axis: between columns 6 and 7

    # Cup (columns 4-9, rows 6-12) and the orb in it (columns 5-8, rows 7-10).
    ellipsoid(bm, cx, Y(9.6), 0.0, 2.9 * PX, 3.3 * PX, 0.13, CUP, segments=14, rings=6, dome=True)
    ellipsoid(bm, cx, Y(8.9), 0.12, 2.15 * PX, 2.1 * PX, 0.07, RIM, segments=12, rings=4, dome=True)
    ellipsoid(bm, cx, Y(8.7), 0.12, 1.9 * PX, 1.9 * PX, 0.16, ORB, segments=14, rings=8)
    ellipsoid(bm, cx - 0.2 * PX, Y(8.1), 0.24, 0.8 * PX, 0.7 * PX, 0.04, ORB_HI, segments=8, rings=4)

    # Prongs (columns 4 and 9) from the cup's sides up the screen, sloping down to the ground.
    for c in (4, 9):
        sweep(bm, [(X(c), Y(10.6), 0.05, 0.0, 0.0), (X(c), Y(10.0), 0.08, 0.55 * PX, 0.045),
                   (X(c), Y(6.0), 0.08, 0.5 * PX, 0.04), (X(c), Y(4.6), 0.07, 0.5 * PX, 0.035)],
              sides=6, mat=PRONG)
        sweep(bm, [(X(c), Y(4.7), 0.07, 0.48 * PX, 0.034), (X(c), Y(1.0), 0.03, 0.4 * PX, 0.025),
                   (X(c), Y(0.5), 0.02, 0.0, 0.0)], sides=6, mat=TIP)
    # Short stem (columns 6-7, rows 3-6) out of the top of the orb.
    sweep(bm, [(cx, Y(7.4), 0.16, 0.9 * PX, 0.05), (cx, Y(5.5), 0.1, 0.9 * PX, 0.045),
               (cx, Y(3.0), 0.05, 0.75 * PX, 0.035), (cx, Y(2.6), 0.04, 0.0, 0.0)], sides=6, mat=TIP)
    return to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    out = preview_args()
    if out:
        preview(ROOT, [obj], out, sprite)


if __name__ == "__main__":
    main()
