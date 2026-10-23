"""Horned boss head (newsh4.shp 81, 83, 85): a 3D version of its three-piece sprite.

Seen in one level of episode 4. Three 2x2 enemies side by side make the upper half of a boss
whose body and wings are assembly-newsh4-123, drawn 24 px lower: a pointed head with a grey face,
a bronze cap and a red crest, two red pincers hanging under it, and on each side a grey shoulder
cylinder with a red band, from which a long curved horn rises and a thin grey feeler curls in
towards the head. A grey arm joins each cylinder to a bronze block over the wing root. Each piece
has a single frame.

The head is built once in the frame shared with assembly-newsh4-123 (lib_b065) and cut into the
three pieces with common.split_assembly. The sprite's right side is drawn 1-2 px further out than
its left, so the side parts are placed per side from their own pixels; the head and pincers are
mirrored about the craft's axis.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-81.py [-- --preview out.png]
(the preview is the whole head; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b065 as lib  # noqa: E402

NAME = "assembly-newsh4-81"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-81", "newsh4-83", "newsh4-85"]

# Per side: horn path (col, row, half width px), feeler path (col, row), shoulder cylinder column,
# grey arm (from col, to col), bronze block outline.
SIDES = [
    dict(horn=[(18.1, 2.6, 0.0), (17.0, 3.4, 1.1), (15.6, 4.4, 1.4), (14.3, 5.5, 1.5), (13.1, 6.5, 1.6),
               (12.3, 7.5, 1.6), (11.8, 8.6, 1.6), (11.6, 10.2, 1.6), (11.5, 13.0, 1.6)],
         feeler=[(22.6, 11.5), (21.2, 11.6), (19.2, 12.5), (17.6, 13.4), (16.4, 14.5), (15.6, 15.6), (15.4, 17.0),
                 (15.2, 18.6)],
         cyl=11.0, arm=(12.6, 18.6),
         block=[(19.0, 19.8), (22.2, 19.8), (23.2, 22.4), (23.2, 28.0), (19.8, 28.0), (17.0, 26.6), (17.0, 24.0),
                (18.6, 21.0)],
         plate=(12.8, 16.8, 16.4, 21.2)),
    dict(horn=[(43.8, 2.6, 0.0), (45.1, 3.4, 1.1), (46.5, 4.4, 1.4), (47.6, 5.5, 1.5), (48.6, 6.5, 1.6),
               (49.4, 7.5, 1.6), (49.9, 8.6, 1.6), (50.3, 10.2, 1.6), (50.5, 13.0, 1.6)],
         feeler=[(38.6, 11.5), (40.0, 11.6), (42.0, 12.5), (43.6, 13.4), (44.7, 14.5), (45.6, 15.6), (46.3, 16.8),
                 (46.6, 18.6)],
         cyl=50.5, arm=(42.8, 48.4),
         block=[(39.8, 19.8), (41.6, 19.8), (43.4, 21.2), (44.6, 24.2), (45.0, 26.4), (43.6, 28.0), (38.8, 28.0),
                (38.8, 21.6)],
         plate=(44.8, 17.8, 47.6, 20.6)),
]


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsh4h"
    pal = lambda i, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    mats = [
        pal(166, metallic=0.25, roughness=0.5),  # 0 horns
        pal(167, metallic=0.3, roughness=0.45),  # 1 horn ridge
        pal(5, metallic=0.6, roughness=0.4),  # 2 grey collars
        pal(7, metallic=0.65, roughness=0.35),  # 3 grey cylinders and arms
        pal(8, metallic=0.7, roughness=0.3),  # 4 grey feelers
        pal(70, metallic=0.35, roughness=0.4),  # 5 red bands
        pal(24, metallic=0.45, roughness=0.4),  # 6 bronze blocks
        pal(6, metallic=0.6, roughness=0.4),  # 7 grey face
        pal(22, metallic=0.45, roughness=0.4),  # 8 bronze cap
        pal(72, metallic=0.4, roughness=0.35),  # 9 red crest and pincers
        pal(2, metallic=0.3, roughness=0.7),  # 10 dark neck
        pal(73, metallic=0.4, roughness=0.3),  # 11 light red pincer edges
    ]
    HORN, HRIDGE, COLLAR, CYL, FEELER, RED, BLOCK, FACE, CAP, CREST, DARK, PINCER = range(12)
    bm = bmesh.new()

    for s in SIDES:
        # Curved horn rising from the shoulder, with a lighter ridge along its top.
        n = len(s["horn"])
        lib.sweep(bm, [(c, r, 0.06 + 0.04 * (n - 1 - i) / (n - 1), w * 0.85, w * 0.05) for i, (c, r, w) in enumerate(s["horn"])],
                  sides=8, mat=HORN)
        lib.sweep(bm, [(c, r, 0.06 + 0.04 * (n - 1 - i) / (n - 1) + w * 0.045, w * 0.4, w * 0.018)
                       for i, (c, r, w) in enumerate(s["horn"][1:-1], 1)], sides=6, mat=HRIDGE)
        # Grey collar at the horn's foot and the shoulder cylinder with its red band.
        c = s["horn"][-1][0]
        lib.loft_y(bm, c, [(12.6, 1.8, 0.09, 0.05), (16.2, 1.9, 0.1, 0.05)], sides=10, mat=COLLAR)
        lib.loft_y(bm, s["cyl"], [(15.8, 0.0, 0.0, 0.0), (16.3, 1.8, 0.1, 0.0), (17.5, 2.2, 0.12, 0.0),
                                  (26.6, 2.2, 0.12, 0.0), (27.6, 1.6, 0.09, 0.0), (28.0, 0.0, 0.0, 0.0)],
                   sides=12, mat=CYL)
        lib.loft_y(bm, s["cyl"], [(21.8, 2.35, 0.13, 0.0), (25.2, 2.35, 0.13, 0.0)], sides=12, mat=RED)
        # Bronze plate behind the cylinder, the grey arm and the bronze block over the wing root.
        c0, r0, c1, r1 = s["plate"]
        lib.box(bm, c0, r0, c1, r1, -0.04, 0.06, mat=BLOCK)
        a0, a1 = s["arm"]
        lib.sweep(bm, [(a0, 23.2, 0.02, 1.7, 0.09), (a1, 23.2, 0.02, 1.7, 0.09)], sides=10, mat=CYL)
        lib.prism(bm, s["block"], -0.06, 0.11, mat=BLOCK)
        # Thin grey feeler curling in towards the head.
        k = len(s["feeler"])
        lib.sweep(bm, [(c, r, 0.04, 0.0 if i == 0 else 0.8, 0.0 if i == 0 else 0.045)
                       for i, (c, r) in enumerate(s["feeler"])], sides=6, mat=FEELER)

    # ---- head, down the middle ----
    lib.loft_y(bm, 30.0, [(10.2, 0.0, 0.0, 0.05), (10.8, 2.2, 0.07, 0.05), (12.0, 3.7, 0.12, 0.05),
                          (13.2, 4.9, 0.15, 0.05), (14.5, 5.6, 0.16, 0.05), (16.4, 5.6, 0.15, 0.05),
                          (17.3, 4.0, 0.11, 0.05), (18.3, 2.2, 0.07, 0.05), (19.0, 0.0, 0.0, 0.05)],
               sides=14, mat=FACE)
    lib.loft_y(bm, 30.0, [(10.6, 0.0, 0.0, 0.1), (11.2, 2.4, 0.08, 0.1), (12.6, 3.4, 0.11, 0.1),
                          (14.6, 3.4, 0.1, 0.1), (15.4, 0.0, 0.0, 0.1)], sides=12, mat=CAP)
    lib.loft_y(bm, 30.0, [(10.8, 0.0, 0.0, 0.2), (11.4, 1.0, 0.04, 0.2), (15.6, 1.0, 0.04, 0.19),
                          (16.2, 0.0, 0.0, 0.19)], sides=8, mat=CREST)
    # Dark neck and the two red pincers under the head (left one built, then mirrored).
    lib.box(bm, 25.0, 18.8, 35.2, 22.2, -0.04, 0.08, mat=DARK)
    start = len(bm.verts)
    lib.box(bm, 25.2, 22.0, 29.0, 28.0, 0.04, 0.15, mat=DARK)
    lib.sweep(bm, [(25.6, 21.9, 0.15, 0.0, 0.0), (25.6, 22.3, 0.15, 0.75, 0.06), (25.6, 27.4, 0.15, 0.75, 0.06),
                   (25.6, 27.9, 0.15, 0.0, 0.0)], sides=8, mat=CREST)
    lib.sweep(bm, [(28.5, 22.6, 0.15, 0.0, 0.0), (28.5, 23.0, 0.15, 0.7, 0.06), (28.5, 27.6, 0.15, 0.7, 0.06),
                   (28.5, 28.0, 0.15, 0.0, 0.0)], sides=8, mat=PINCER)
    lib.sweep(bm, [(25.4, 22.4, 0.16, 0.7, 0.05), (28.6, 23.0, 0.16, 0.7, 0.05)], sides=8, mat=CREST)
    lib.mirror_since(bm, start)

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    lib.export_assembly(ROOT, obj, PIECES, sys.argv)


if __name__ == "__main__":
    main()
