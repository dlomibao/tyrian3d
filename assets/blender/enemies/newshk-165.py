"""Grey bar ends (newshk.shp frame 165): a 3D version of its sprite.

Seen in episode 3 (level 3.12). Only the right edge of its block is filled: the end of a thin grey
rod (row 9) and below it the end of a heavier grey beam (rows 15-20), two raised rails with a dark
groove between them on a darker base, closed by a small end cap at the block's right edge. Both
run on past the edge, so the model stops flush with it.

Run: blender --background --python assets/blender/enemies/newshk-165.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b045 as lib  # noqa: E402
from lib_b045 import U, common, ex, ey  # noqa: E402

NAME = "newshk-165"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.6, roughness=0.45),  # 0 dark base and sides
        pal(7, metallic=0.65, roughness=0.35),  # 1 rail tops
        pal(2, metallic=0.4, roughness=0.6),  # 2 groove
        pal(6, metallic=0.6, roughness=0.4),  # 3 thin rod
        pal(5, metallic=0.6, roughness=0.4),  # 4 end cap
        pal(10, metallic=0.7, roughness=0.3),  # 5 end cap highlight
    ]
    BASE, RAIL, GROOVE, ROD, CAP, HI = range(6)
    bm = bmesh.new()

    # Thin rod (row 9, columns 15-23), round, its end rounded off at column 15.
    f0 = len(bm.faces)
    lib.loft_x(bm, [(ex(15), 0.0, 0.0), (ex(15.6), 0.55 * U, 0.04), (ex(24), 0.55 * U, 0.04)], ey(9.5), 0.0,
               sides=8, mat_index=ROD)
    lib.set_smooth(bm, f0)

    # Beam (rows 15-20): darker base, two rails on top with the groove between them.
    lib.bevel_prism(bm, [(ex(15), ey(21)), (ex(24), ey(21)), (ex(24), ey(15)), (ex(15), ey(15))], -0.1, 0.03,
                    0.015, mat_index=GROOVE, side_mat=BASE)
    lib.bevel_prism(bm, [(ex(15.2), ey(17)), (ex(24), ey(17)), (ex(24), ey(15)), (ex(15.2), ey(15))], 0.0, 0.1,
                    0.02, mat_index=RAIL, side_mat=BASE)
    lib.bevel_prism(bm, [(ex(15.2), ey(19)), (ex(24), ey(19)), (ex(24), ey(18)), (ex(15.2), ey(18))], 0.0, 0.085,
                    0.015, mat_index=RAIL, side_mat=BASE)
    # End cap (columns 22-23, rows 16-20) with its lit edge.
    lib.bevel_prism(bm, [(ex(22), ey(20.5)), (ex(24), ey(20.5)), (ex(24), ey(15.6)), (ex(22), ey(15.6))], -0.08,
                    0.12, 0.02, mat_index=CAP, side_mat=BASE)
    lib.box(bm, ex(23), ey(19), ex(24), ey(17), 0.1, 0.13, HI)
    return [lib.mesh_object_mixed(NAME, bm, mats, coll)]


if __name__ == "__main__":
    lib.run(__file__, NAME, build)
