"""Grey gunship (newshh.shp frame 284): a 3D version of its sprite.

Seen in episode 2 (levels 2.12 and 2.19). It flies nose down the screen: a broad grey wing the
full width of the sprite with a pale crest across its middle, two raised pods at the back
(top of the sprite) each with a long teal canopy, a dark slot between them, and a pointed keel
under the crest that ends in the nose. One frame.

Run: blender --background --python assets/blender/enemies/newshh-284.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b018 as lib  # noqa: E402
from lib_b018 import ex, ey, px, row  # noqa: E402

NAME = "newshh-284"
DARKS = (-1, 1, 3, 32, 80)  # outline and near-black edge pixels


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(102, metallic=0.55, roughness=0.45),  # 0 grey wing
        pal(100, metallic=0.5, roughness=0.55),  # 1 dark underside
        pal(107, metallic=0.6, roughness=0.3),  # 2 pale crest
        pal(104, metallic=0.55, roughness=0.4),  # 3 pods and keel
        pal(213, metallic=0.3, roughness=0.12),  # 4 teal canopy glass
        pal(50, metallic=0.3, roughness=0.5),  # 5 dark slot
        pal(218, metallic=0.3, roughness=0.1, emission_strength=1.0),  # 6 canopy highlight
    ]
    WING, DARK, CREST, POD, GLASS, SLOT, SHINE = range(7)
    pixels = sprite["frames"][0]["pixels"]
    bm = bmesh.new()

    # The wing: the whole silhouette from row 5 down, a flat-topped plate.
    keep = lambda r, c, v: v not in DARKS  # noqa: E731
    wing = lib.smooth_outline(pixels, keep, rows=range(5, 21), inset=-0.3, n=64)
    lib.pillow(bm, wing, (0.0, row(11)), 0.0, 0.08, 0.06, rings_top=3, rings_bottom=2, mat=WING,
               mat_bottom=DARK, power=3.5)

    # The pale crest across the middle (rows 10-11), sagging slightly to the tips.
    lib.tube(bm, [(ex(0.2), row(10.6), 0.05), (px(4), row(10.6), 0.075), (px(8), row(10.5), 0.085),
                  (0.0, row(10.5), 0.09), (px(15), row(10.5), 0.085), (px(19), row(10.6), 0.075),
                  (ex(23.8), row(10.6), 0.05)], 0.055, sides=6, mat=CREST, flat=0.6)

    # The keel and nose (rows 11-20, columns 7-16): a ridged hull narrowing to the point.
    keel = [(11, 4.8, 0.13), (13, 4.6, 0.13), (15, 4.0, 0.12), (17, 3.2, 0.1), (18.5, 2.3, 0.08),
            (19.6, 1.2, 0.05)]
    rings = [lib.section_ring(0.0, row(r), w / 12, 0.0, h, 0.07, sides=12, keel=1.3) for r, w, h in keel]
    rings.append([(0.0, row(20.4), 0.0)])
    lib.ring_loft(bm, rings, mat=POD)

    # The dark slot between the pods (columns 11-12, rows 2-10).
    lib.prism(bm, [(ex(10.6), ey(10.5)), (ex(13.4), ey(10.5)), (ex(13.4), ey(1.8)), (ex(10.6), ey(1.8))],
              -0.02, 0.1, mat=SLOT)

    # One pod (columns 6-10, rows 1-10) with its canopy (columns 7-8), mirrored.
    v0, f0 = len(bm.verts), len(bm.faces)
    pod = [(1.2, 1.5, 0.1), (1.8, 2.3, 0.16), (3, 2.6, 0.2), (6, 2.7, 0.21), (9, 2.6, 0.2),
           (10.5, 2.4, 0.17), (11.4, 1.6, 0.11)]
    rings = [lib.section_ring(px(8), row(r), w / 12, 0.0, h, 0.05, sides=12, keel=2.2, fullness=0.6)
             for r, w, h in pod]
    lib.ring_loft(bm, rings, mat=POD)
    lib.tube(bm, [(px(7.5), row(1.9), 0.17), (px(7.5), row(3.5), 0.2), (px(7.5), row(6.5), 0.215),
                  (px(7.5), row(9.4), 0.2), (px(7.5), row(10.2), 0.17)],
             [0.0, 0.1, 0.105, 0.1, 0.0], sides=10, mat=GLASS, flat=0.6)
    lib.ellipsoid(bm, (px(7.2), row(7.0), 0.255), (0.035, 0.07, 0.015), mat=SHINE, segments=8, rings=4)
    # Ribs across the wing's outer panel (columns 2 and 4, rows 7-15).
    for c, r0 in ((2.0, 7.2), (4.2, 7.6)):
        lib.tube(bm, [(px(c), row(r0), 0.05), (px(c), row(10.5), 0.07), (px(c), row(15.2), 0.045)],
                 0.05, sides=6, mat=POD, flat=0.45)
    lib.mirror_new(bm, v0, f0, axis_x=0.0)

    obj = lib.to_object(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
