"""Caged spindle drone (newsh7.shp frames 13, 15, 17): a 3D version of its sprite.

Seen in episode 3 (level section 10). Symmetric top to bottom and left to right: a blue steel
spindle (two bulbs and a waist) between two ribbed grey engine blocks, each with a thruster
firing out of the end, and a grey bar cage that bends round both sides into blue chevron blades
held to the spindle's waist by short grey axles. The frames only grow the thruster flames, so
one model covers them all.

Run: blender --background --python assets/blender/enemies/newsh7-13.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
from lib_b007 import common, ex, ey, px, row  # noqa: E402

NAME = "newsh7-13"
CX = px(11)  # the sprite's centre column: everything is symmetric about it


def mirror_y(bm):
    """Mirror everything built so far across Y = 0 (the sprite's middle, between rows 13 and 14)."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.mirror(bm, geom=geom, matrix=Matrix.Identity(4), axis="Y", merge_dist=0.0)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(4, metallic=0.6, roughness=0.45),  # 0 dark grey engine block
        pal(10, metallic=0.7, roughness=0.3),  # 1 light grey ribs / cage
        pal(5, metallic=0.6, roughness=0.4),  # 2 mid-dark ribs
        pal(8, metallic=0.65, roughness=0.35),  # 3 grey nozzle
        pal(112, metallic=0.3, roughness=0.6),  # 4 scorched nozzle mouth
    ]
    BLOCK, RIB, RIB2, NOZZLE, MOUTH = range(5)

    # Engine blocks (rows 3-7, columns 7-15), ribbed, with a nozzle at the outer end.
    bm = bmesh.new()
    common.slab(bm, [(ex(7), ey(7)), (ex(16), ey(7)), (ex(16), ey(3.4)), (ex(7), ey(3.4))], 0.16, z=0.0,
                mat_index=BLOCK)
    for c, r0, m in ((7, 3, RIB), (9, 4.6, RIB2), (11, 4.6, RIB), (13, 4.6, RIB2), (15, 3, RIB)):
        common.slab(bm, [(ex(c) + 0.01, ey(6.9)), (ex(c + 1) - 0.01, ey(6.9)), (ex(c + 1) - 0.01, ey(r0)),
                         (ex(c) + 0.01, ey(r0))], 0.08, z=0.09, mat_index=m)
    mirror_y(bm)
    blocks = common.mesh_object(f"{NAME}_blocks", bm, mats, coll, smooth=False)

    # Smooth parts: nozzles, flames, the spindle, the cage and blades, the axles.
    smats = [
        pal(8, metallic=0.65, roughness=0.35),  # 0 grey nozzle
        pal(112, metallic=0.3, roughness=0.6),  # 1 scorched mouth
        pal(119, emission_strength=3.0),  # 2 red flame
        pal(124, emission_strength=5.0),  # 3 yellow flame core
        pal(9, metallic=0.7, roughness=0.3),  # 4 grey cage bars
        pal(56, metallic=0.5, roughness=0.3),  # 5 blue steel
        pal(62, metallic=0.6, roughness=0.2),  # 6 highlight
        pal(58, metallic=0.5, roughness=0.3),  # 7 blade blue
    ]
    NOZ, MOU, FLAME, CORE, BAR, BLUE, HI, BLADE = range(8)
    bm = bmesh.new()

    def at_cx(fn):
        start = len(bm.verts)
        fn()
        common.shift_x(bm, start, CX)

    # Nozzle (columns 9-13) pointing up out of the block, and its flame (rows 1-3 in the middle frame).
    at_cx(lambda: common.loft(bm, [(ey(4.5), 2.4 / 12, 0.075, 0.0), (ey(3.2), 2.5 / 12, 0.08, 0.0)],
                              sides=12, mat_index=NOZ, cap_end=False))
    at_cx(lambda: common.loft(bm, [(ey(3.25), 2.2 / 12, 0.065, 0.0), (ey(3.2), 0.0, 0.0, 0.0)],
                              sides=12, mat_index=MOU))
    at_cx(lambda: common.loft(bm, [(ey(3.6), 2.2 / 12, 0.06, 0.0), (ey(2.6), 2.0 / 12, 0.055, 0.0),
                                   (ey(1.6), 1.2 / 12, 0.04, 0.0), (ey(1.0), 0.0, 0.0, 0.0)],
                              sides=10, mat_index=FLAME))
    at_cx(lambda: common.loft(bm, [(ey(3.6), 1.2 / 12, 0.04, 0.04), (ey(2.8), 1.1 / 12, 0.04, 0.045),
                                   (ey(2.0), 0.0, 0.0, 0.04)], sides=8, mat_index=CORE))

    # Grey cage: from the block's corner out along row 4, round the corner and down columns 2 / 20.
    r = 0.6 / 12
    for side in (-1, 1):
        def sx(c, side=side):
            return px(c) if side < 0 else 2 * CX - px(c)
        path = [(sx(6.8), row(4), 0.0), (sx(4.2), row(4), 0.0), (sx(2.9), row(4.6), 0.0),
                (sx(2.2), row(5.8), 0.0), (sx(2), row(7.2), 0.0), (sx(2.1), row(9.6), 0.0)]
        lib.polyline_tube(bm, path, r, sides=8, mat_index=BAR)
        # The blue chevron blade (rows 10-13): thicker, bending in toward the spindle.
        blade = [(sx(2.1), row(9.3), 0.0), (sx(2.8), row(11), 0.01), (sx(4.0), row(12.4), 0.02),
                 (sx(4.6), row(13.5), 0.02)]
        lib.polyline_tube(bm, blade, 1.05 / 12, sides=8, mat_index=BLADE)
        lib.polyline_tube(bm, [(x, y, z + 0.07) for x, y, z in blade[:-1]], 0.4 / 12, sides=6, mat_index=HI)
        # Axle from the spindle's waist to the blade tip (rows 13-14, columns 7-8).
        lib.tube(bm, (sx(4.8), row(13.5), 0.02), (sx(9.6), row(13.5), 0.02), 0.9 / 12, sides=8,
                 mat_index=BAR)
    mirror_y(bm)

    # The spindle (rows 8-19, columns 8-14): two bulbs and a waist, with a bright ridge on top.
    spindle = [(7.4, 1.4), (8, 1.6), (9, 2.3), (10, 3.0), (11, 3.4), (12, 2.5), (13, 1.7)]
    spindle = spindle + [(26 - rr, w) for rr, w in reversed(spindle)]
    at_cx(lambda: common.loft(bm, [(row(rr), w / 12, w * 0.6 / 12, 0.0) for rr, w in spindle],
                              sides=12, mat_index=BLUE))
    at_cx(lambda: common.loft(bm, [(row(rr), 0.45 / 12, 0.3 / 12, w * 0.6 / 12 - 0.01)
                                   for rr, w in spindle[2:-2]], sides=6, mat_index=HI))
    parts = common.mesh_object(NAME, bm, smats, coll, smooth=True)

    return [(NAME, [parts, blocks], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
