"""Domed gunboat (newshg.shp frame 201): a 3D version of its sprite.

Seen in episode 2 (level section 12). A steel-blue body with a big glossy dome at the front (top
of the sprite), a square hole through the body just behind the dome between two pillars, short
square wings at the sides and two brown engine nozzles at the back corners. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshg-201.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b034 as lib  # noqa: E402
from lib_b034 import common, ex, ey, px, row  # noqa: E402

NAME = "newshg-201"
CX = px(11)  # the sprite is symmetric about column 11


def ccw(poly):
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))
    return poly if area > 0 else list(reversed(poly))


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(55, metallic=0.5, roughness=0.4),  # 0 body blue
        pal(58, metallic=0.55, roughness=0.3),  # 1 light ridges
        pal(52, metallic=0.5, roughness=0.5),  # 2 dark panels / under wing
        pal(50, metallic=0.4, roughness=0.6),  # 3 grooves, hole walls
        pal(160, metallic=0.4, roughness=0.6),  # 4 dark brown nozzle
        pal(168, metallic=0.5, roughness=0.35),  # 5 brown nozzle
        pal(54, metallic=0.5, roughness=0.45),  # 6 keel
    ]
    BODY, RIDGE, DARK, GROOVE, BROWN_D, BROWN, KEEL = range(7)
    bm = bmesh.new()

    # Pillars either side of the hole (rows 8-13), the bridge in front of it, the lower body.
    lib.bevel_prism(bm, ccw([(ex(5.7), ey(8.8)), (ex(10.5), ey(8.8)), (ex(10.5), ey(13.5)), (ex(5.7), ey(13.5))]),
                    -0.11, 0.11, 0.035, mat_index=BODY)
    lib.bevel_prism(bm, ccw([(ex(13.5), ey(8.8)), (ex(17.3), ey(8.8)), (ex(17.3), ey(13.5)), (ex(13.5), ey(13.5))]),
                    -0.11, 0.11, 0.035, mat_index=BODY)
    lib.bevel_prism(bm, ccw([(ex(7.0), ey(8.0)), (ex(16.0), ey(8.0)), (ex(16.0), ey(10.6)), (ex(7.0), ey(10.6))]),
                    -0.09, 0.10, 0.03, mat_index=BODY)
    lower = [(ex(5.7), ey(13.0)), (ex(17.3), ey(13.0)), (ex(17.3), ey(19.6)), (ex(16.0), ey(22.5)),
             (ex(14.0), ey(25.3)), (ex(9.0), ey(25.3)), (ex(7.0), ey(22.5)), (ex(5.7), ey(19.6))]
    lib.bevel_prism(bm, ccw(lower), -0.12, 0.10, 0.04, mat_index=DARK, top_mat=BODY)
    # Hole walls: a dark sleeve lining the hole so it reads as a recess from any angle.
    hole = ccw([(ex(10.5), ey(10.6)), (ex(13.5), ey(10.6)), (ex(13.5), ey(13.0)), (ex(10.5), ey(13.0))])
    common.slab(bm, lib.inset_outline(hole, -0.004), 0.2, z=0.0, mat_index=GROOVE)
    # Open the sleeve (drop its top and bottom caps, slab's first two faces) and turn its walls inward.
    bm.faces.ensure_lookup_table()
    caps, walls = bm.faces[-6:-4], bm.faces[-4:]
    bmesh.ops.reverse_faces(bm, faces=list(walls))
    for f in caps:
        bm.faces.remove(f)

    # Light ridges down the pillars (columns 8 and 14, rows 9-18).
    for c in (8, 14):
        lib.polyline_tube(bm, [(px(c), row(9.0), 0.10), (px(c), row(18.4), 0.10)], 0.6 / 12, sides=6,
                          mat_index=RIDGE, flat=0.6)
    # Recessed centre panel with two grooves (rows 14-18, columns 9-13).
    lib.box(bm, ex(9.2), ey(18.8), ex(13.8), ey(13.8), 0.08, 0.112, mat_index=KEEL)
    for r in (15, 17):
        lib.box(bm, ex(9.4), ey(r + 0.8), ex(13.6), ey(r + 0.2), 0.10, 0.118, mat_index=GROOVE)
    # Keel converging to the tail (rows 19-25): a raised V with a dark centre seam.
    keel = ccw([(ex(7.6), ey(19.2)), (ex(15.4), ey(19.2)), (ex(13.4), ey(24.8)), (ex(9.6), ey(24.8))])
    lib.bevel_prism(bm, keel, 0.05, 0.13, 0.03, mat_index=KEEL)
    lib.polyline_tube(bm, [(CX, row(19.3), 0.13), (CX, row(24.5), 0.11)], 0.45 / 12, sides=6, mat_index=GROOVE,
                      flat=0.5)

    # Square wings (rows 14-18, columns 1-4): a light upper part and a darker trailing part.
    for side in (-1, 1):
        x0, x1 = CX + side * 5.6 / 12, CX + side * 10.6 / 12
        lo, hi = min(x0, x1), max(x0, x1)
        lib.bevel_prism(bm, ccw([(lo, ey(13.9)), (hi, ey(13.9)), (hi, ey(17.0)), (lo, ey(17.0))]),
                        -0.05, 0.05, 0.02, mat_index=BODY)
        lib.bevel_prism(bm, ccw([(lo, ey(16.9)), (hi, ey(16.9)), (hi, ey(19.0)), (lo, ey(19.0))]),
                        -0.07, 0.02, 0.015, mat_index=DARK)
        lib.polyline_tube(bm, [(lo + 0.01, row(14.1), 0.05), (hi - 0.01, row(14.1), 0.05)], 0.5 / 12, sides=6,
                          mat_index=RIDGE, flat=0.6)

    # Brown engine nozzles at the back corners (rows 20-24, columns 3-6 and 16-19).
    for side in (-1, 1):
        start = len(bm.verts)
        common.loft(bm, [(row(19.6), 1.5 / 12, 1.4 / 12, -0.03), (row(20.5), 1.9 / 12, 1.7 / 12, -0.03),
                         (row(23.2), 1.8 / 12, 1.6 / 12, -0.03), (row(24.4), 1.3 / 12, 1.2 / 12, -0.03)],
                    sides=10, mat_index=BROWN)
        common.loft(bm, [(row(24.3), 1.0 / 12, 0.9 / 12, -0.03), (row(24.6), 0.0, 0.0, -0.03)], sides=10,
                    mat_index=BROWN_D)
        common.shift_x(bm, start, CX + side * 6.5 / 12)
    body = common.mesh_object(f"{NAME}_body", bm, mats, coll, smooth=False)

    # The glossy dome at the front (rows 1-8, columns 7-15) and its bright highlight.
    dmats = [
        pal(59, metallic=0.3, roughness=0.15),  # 0 dome rim
        pal(60, metallic=0.25, roughness=0.12),  # 1 dome
        pal(63, metallic=0.1, roughness=0.05),  # 2 highlight
        pal(55, metallic=0.5, roughness=0.4),  # 3 collar
    ]
    bm = bmesh.new()
    lib.ellipsoid(bm, (CX, row(4.4), 0.04), (4.6 / 12, 4.2 / 12, 0.24), segments=20, rings=10, mat_index=1,
                  bottom=0.5)
    lib.ellipsoid(bm, (CX - 0.3 / 12, row(4.4), 0.165), (3.0 / 12, 2.6 / 12, 0.13), segments=14, rings=7,
                  mat_index=2, bottom=0.3)
    # A collar where the dome meets the body.
    lib.polyline_tube(bm, [(px(7.2), row(7.4), 0.03), (px(9), row(8.4), 0.05), (px(13), row(8.4), 0.05),
                           (px(14.8), row(7.4), 0.03)], 0.9 / 12, sides=8, mat_index=0, flat=0.8)
    dome = common.mesh_object(NAME, bm, dmats, coll, smooth=True)
    return [(NAME, [dome, body], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
