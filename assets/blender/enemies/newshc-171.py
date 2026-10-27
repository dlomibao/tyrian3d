"""Small pod with a purple orb (newshc.shp frames 171-304, 1x1 tile): a 3D version of its sprite.

Seen in episodes 1 (level 1.19) and 3 (3.23, 3.6). A purple orb sits in a pale blue cup with two
long thin prongs and a short stem reaching up the screen from it, darkening as they go (they
slope down to the ground). Its eight frames run a pulse of light up the prongs (their lower part
brightest on frames 209-228, the middle on 228-247, the tips on 247-266, all dimming on 285-304),
make the stem a pixel longer on 228, 266 and 304 and brighten the orb's highlight on 266-304. One
model covers them all: each prong is three pieces whose palette colours change per frame
(palette_material frames=), and the stem comes in two lengths (common.frame_part).

Run: blender --background --python assets/blender/enemies/newshc-171.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b097 import PX, ellipsoid, frame_previews, frames_arg, preview, preview_args, sweep, to_object  # noqa: E402
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

    def anim(i, part, frames, **kw):
        return common.palette_material(sprite, i, f"{NAME}-{part}", frames=frames, **kw)
    mats = [
        pal(60, metallic=0.5, roughness=0.3),  # 0 pale blue cup
        pal(90, metallic=0.3, roughness=0.25, emission_strength=0.6),  # 1 purple orb
        anim(93, "hi", {266: 94, 285: 94, 304: 94}, metallic=0.3, roughness=0.2, emission_strength=1.5),  # 2 orb highlight
        anim(58, "low", {209: 61, 228: 61, 285: 56, 304: 54}, metallic=0.5, roughness=0.35),  # 3 prongs near the cup
        anim(53, "tip", {190: 54, 209: 54, 228: 54, 247: 55, 266: 55, 304: 52}, metallic=0.4, roughness=0.5),  # 4 prong tips
        pal(85, metallic=0.3, roughness=0.5),  # 5 dark rim round the orb
        anim(58, "mid", {190: 59, 209: 59, 228: 61, 247: 61, 266: 59, 304: 55}, metallic=0.5, roughness=0.35),  # 6 prong middles
        anim(53, "stem", {228: 54, 266: 54}, metallic=0.4, roughness=0.5),  # 7 stem
    ]
    CUP, ORB, ORB_HI, PRONG, TIP, RIM, MID, STEM = range(8)
    bm = bmesh.new()
    cx = X(6.5)  # the sprite's axis: between columns 6 and 7

    # Cup (columns 4-9, rows 6-12) and the orb in it (columns 5-8, rows 7-10).
    ellipsoid(bm, cx, Y(9.6), 0.0, 2.9 * PX, 3.3 * PX, 0.13, CUP, segments=14, rings=6, dome=True)
    ellipsoid(bm, cx, Y(8.9), 0.12, 2.15 * PX, 2.1 * PX, 0.07, RIM, segments=12, rings=4, dome=True)
    ellipsoid(bm, cx, Y(8.7), 0.12, 1.9 * PX, 1.9 * PX, 0.16, ORB, segments=14, rings=8)
    ellipsoid(bm, cx - 0.2 * PX, Y(8.1), 0.24, 0.8 * PX, 0.7 * PX, 0.04, ORB_HI, segments=8, rings=4)

    # Prongs (columns 4 and 9) from the cup's sides up the screen, sloping down to the ground: the
    # lower part (rows 7-10), the middle (rows 5-6) and the tip, each lit on its own frames.
    for c in (4, 9):
        sweep(bm, [(X(c), Y(10.6), 0.05, 0.0, 0.0), (X(c), Y(10.0), 0.08, 0.55 * PX, 0.045),
                   (X(c), Y(6.45), 0.08, 0.5 * PX, 0.04)], sides=6, mat=PRONG)
        sweep(bm, [(X(c), Y(6.55), 0.08, 0.5 * PX, 0.04), (X(c), Y(6.0), 0.08, 0.5 * PX, 0.04),
                   (X(c), Y(4.6), 0.07, 0.5 * PX, 0.035)], sides=6, mat=MID)
        sweep(bm, [(X(c), Y(4.7), 0.07, 0.48 * PX, 0.034), (X(c), Y(1.0), 0.03, 0.4 * PX, 0.025),
                   (X(c), Y(0.5), 0.02, 0.0, 0.0)], sides=6, mat=TIP)
    body = to_object(NAME, bm, mats, coll)

    # Short stem (columns 6-7, rows 3-6) out of the top of the orb, reaching a row further (row 2)
    # on frames 228, 266 and 304.
    parts = [body]
    for tip, frames in ((0.0, [171, 190, 209, 247, 285]), (1.0, [228, 266, 304])):
        sbm = bmesh.new()
        sweep(sbm, [(cx, Y(7.4), 0.16, 0.9 * PX, 0.05), (cx, Y(5.5), 0.1, 0.9 * PX, 0.045),
                    (cx, Y(3.0 - tip), 0.05, 0.75 * PX, 0.035), (cx, Y(2.6 - tip), 0.04, 0.0, 0.0)], sides=6, mat=STEM)
        parts.append(common.frame_part(to_object(f"{NAME}-stem-{frames[0]}", sbm, mats, coll), frames))
    return parts


def main():
    sprite = common.load_sprite(ROOT, NAME)
    objs = build(sprite)
    common.export_sprite_model(ROOT, objs, MODEL, sprite["sprites"])
    out = preview_args()
    if out:
        preview(ROOT, objs, out, sprite)
    if frames_arg():
        frame_previews(ROOT, objs, frames_arg(), sprite)


if __name__ == "__main__":
    main()
