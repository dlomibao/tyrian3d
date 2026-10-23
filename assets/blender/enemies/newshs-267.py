"""Grey launcher bunker with a red roof spine (newshs.shp frame 267): a 3D version of its sprite.

A ground structure seen in level 3.15. A grey block with chamfered back corners: two grey
housings (each split by a groove) flank a raised red spine down the back half, and the front
deck carries two staggered rows of launch tubes (four, then three). One frame, one model.

Run: blender --background --python assets/blender/enemies/newshs-267.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b135 as lib  # noqa: E402

NAME = "newshs-267"
ROOT = common.repo_root(__file__)
U = 1 / 12  # one sprite pixel


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.4, roughness=0.55),  # 0 base block and deck
        pal(10, metallic=0.45, roughness=0.45),  # 1 left housing
        pal(8, metallic=0.45, roughness=0.5),  # 2 right housing
        pal(70, metallic=0.3, roughness=0.45),  # 3 red spine top
        pal(74, metallic=0.3, roughness=0.4),  # 4 red spine rim
        pal(13, metallic=0.5, roughness=0.3),  # 5 bright ribs
        pal(9, metallic=0.5, roughness=0.4),  # 6 launch tube rims
        pal(2, metallic=0.2, roughness=0.8),  # 7 tube bores
        pal(5, metallic=0.3, roughness=0.6),  # 8 dark slots
        pal(11, metallic=0.5, roughness=0.4),  # 9 light ribs
    ]
    BASE, LEFT, RIGHT, RED, RIM, BRIGHT, TUBE, BORE, SLOT, LIGHT = range(10)
    bm = bmesh.new()
    face0 = len(bm.faces)

    # Base block: the whole silhouette, chamfered at the back corners.
    base = lib.outline_px([(6, 2), (19, 2), (22, 5.5), (22, 24), (21, 25), (4, 25), (3, 24), (3, 5.5)])
    lib.bevel_prism(bm, base, 0.0, 0.2, 0.5 * U, 0.03, mat_index=BASE)

    # Side housings, each split by the groove at row 7.
    lib.bevel_prism(bm, lib.outline_px([(3, 5.5), (6, 2), (10, 2), (10, 7), (3, 7)]), 0.15, 0.33, 0.7 * U, 0.04,
                    mat_index=LEFT)
    lib.bevel_prism(bm, lib.rect_px(3, 8, 10, 16.5), 0.15, 0.33, 0.7 * U, 0.04, mat_index=LEFT)
    lib.bevel_prism(bm, lib.outline_px([(16, 2), (19, 2), (22, 5.5), (22, 7), (16, 7)]), 0.15, 0.31, 0.7 * U, 0.04,
                    mat_index=RIGHT)
    lib.bevel_prism(bm, lib.rect_px(16, 8, 22, 16.5), 0.15, 0.31, 0.7 * U, 0.04, mat_index=RIGHT)

    # The red spine between them, its light chamfer the sprite's pale rim.
    lib.bevel_prism(bm, lib.rect_px(10, 2, 15, 16), 0.15, 0.37, 1.0 * U, 0.06, mat_index=RIM, top_mat=RED)

    # Ribs and slots on the housings.
    lib.prism(bm, lib.rect_px(4.6, 11.8, 8.6, 12.9), 0.32, 0.35, BRIGHT)  # row 12 left
    lib.prism(bm, lib.rect_px(4.2, 14.8, 7.0, 15.9), 0.32, 0.35, BRIGHT)  # row 15 left
    lib.prism(bm, lib.rect_px(4.6, 7.9, 6.2, 9.0), 0.32, 0.345, BRIGHT)  # row 8 left light
    lib.prism(bm, lib.rect_px(7.9, 8.8, 9.0, 11.0), 0.32, 0.333, SLOT)  # dark slot col 8
    lib.prism(bm, lib.rect_px(17.0, 11.8, 20.0, 12.9), 0.30, 0.335, BRIGHT)  # row 12 right
    lib.prism(bm, lib.rect_px(17.0, 13.9, 20.0, 15.0), 0.30, 0.325, LIGHT)  # row 14 right
    lib.prism(bm, lib.rect_px(17.6, 8.8, 18.6, 11.0), 0.30, 0.325, LIGHT)  # col 18 right

    # Front deck: a low plate with a cross rib at row 20.
    lib.bevel_prism(bm, lib.outline_px([(3.4, 16.3), (21.6, 16.3), (21.6, 24.2), (20.8, 24.8), (4.2, 24.8),
                                        (3.4, 24.2)]), 0.15, 0.23, 0.5 * U, 0.02, mat_index=BASE)
    lib.prism(bm, lib.rect_px(4.0, 19.8, 21.0, 20.8), 0.22, 0.25, LIGHT)
    tube_face = len(bm.faces)
    # Launch tubes: four at row 18, three staggered at row 22.
    for c, r in [(6.2, 18.4), (10.2, 18.4), (14.2, 18.4), (18.2, 18.4), (8.2, 22.5), (12.2, 22.5), (16.2, 22.5)]:
        x, y = lib.ex(c), lib.ey(r)
        lib.annulus(bm, x, y, 1.7 * U, 1.2 * U, 0.2, 0.29, sides=12, mat_index=TUBE)
        lib.cylinder(bm, x, y, 1.25 * U, 0.2, 0.24, sides=12, mat_index=BORE)
    lib.set_smooth(bm, face0, False)
    lib.set_smooth(bm, tube_face, True)
    return lib.mesh_object_mixed(NAME, bm, mats, coll)


if __name__ == "__main__":
    lib.run(ROOT, NAME, build)
