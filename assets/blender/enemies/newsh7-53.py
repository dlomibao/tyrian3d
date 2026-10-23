"""Blue crystal (newsh7.shp frames 53, 91, 129): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4. A cut gem hanging from a steel cap: an
octagonal girdle, a table split by a bright crease (darker back facet, lighter front facet),
sloped crown facets round it and a pavilion underneath. The frames only shimmer the blues and
the white facet lines, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newsh7-53.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
from lib_b007 import common, ex, ey  # noqa: E402

NAME = "newsh7-53"


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    gem_mats = [
        pal(150, metallic=0.1, roughness=0.15),  # 0 deep blue pavilion
        pal(153, metallic=0.1, roughness=0.15),  # 1 girdle / mid crown
        pal(155, metallic=0.1, roughness=0.12),  # 2 side crown
        pal(152, metallic=0.1, roughness=0.15),  # 3 front crown
        pal(157, metallic=0.1, roughness=0.12),  # 4 light crown, front table
        pal(148, metallic=0.1, roughness=0.15),  # 5 dark back table
        pal(154, metallic=0.1, roughness=0.12),  # 6 back crown
        pal(143, emission_strength=2.5),  # 7 white facet lines
    ]
    PAV, GIRD, SIDE, FRONT, LIGHT, BACK, TOPC, LINE = range(8)

    # Girdle and table outlines in pixel-edge coordinates (column, row), counter-clockwise from
    # the top-left; the third and eighth points sit on the crease at row 12.5.
    girdle = [(5, 7), (3, 9), (3, 12.5), (3, 20), (8, 25), (16, 25), (21, 20), (21, 12.5), (21, 9), (19, 7)]
    table = [(6.5, 8), (5.5, 9.5), (5.5, 12.5), (5.5, 16.5), (9, 20.5), (15, 20.5), (18.5, 16.5),
             (18.5, 12.5), (18.5, 9.5), (17.5, 8)]
    table_z = [0.19, 0.2, 0.25, 0.23, 0.22, 0.22, 0.23, 0.25, 0.2, 0.19]

    def pts(outline, zs):
        return [(ex(c), ey(r), z) for (c, r), z in zip(outline, zs)]

    bm = bmesh.new()
    rings = [
        [(0.0, ey(17), -0.3)],
        pts(girdle, [-0.03] * 10),
        pts(girdle, [0.03] * 10),
        pts(table, table_z),
    ]
    crown = [TOPC, SIDE, SIDE, FRONT, FRONT, LIGHT, SIDE, LIGHT, TOPC, TOPC]
    verts = lib.ring_loft(bm, rings, [PAV, GIRD, crown], cap_end=False)
    t = verts[-1]
    # The table: a darker back facet and a lighter front one, meeting at the crease.
    bm.faces.new([t[0], t[1], t[2], t[7], t[8], t[9]]).material_index = BACK
    bm.faces.new([t[2], t[3], t[4], t[5], t[6], t[7]]).material_index = LIGHT
    gem = common.mesh_object(NAME, bm, gem_mats, coll, smooth=False)

    # White facet lines: the crease across the whole gem, the table's outline and the two front
    # edges down to the girdle.
    bm = bmesh.new()
    tp = [p for p in pts(table, table_z)]
    gp = pts(girdle, [0.03] * 10)
    r = 0.024
    lift = lambda p: (p[0], p[1], p[2] + 0.008)  # noqa: E731
    lib.polyline_tube(bm, [lift(p) for p in (gp[2], tp[2], tp[7], gp[7])], r, mat_index=0)
    lib.polyline_tube(bm, [lift(p) for p in tp[1:9]], r, mat_index=0)
    lib.tube(bm, lift(tp[4]), lift(gp[4]), r, mat_index=0)
    lib.tube(bm, lift(tp[5]), lift(gp[5]), r, mat_index=0)
    lines = common.mesh_object(f"{NAME}_lines", bm, [gem_mats[LINE]], coll, smooth=True)

    # The steel cap at the top (rows 2-6): a rounded knob, lit from the left.
    cap_mats = [pal(58, metallic=0.65, roughness=0.3), pal(49, metallic=0.5, roughness=0.5),
                pal(61, metallic=0.7, roughness=0.25)]
    bm = bmesh.new()
    common.loft(bm, [(ey(7.6), 6.6 / 12, 0.07, 0.1), (ey(6.2), 6.4 / 12, 0.1, 0.11),
                     (ey(5), 5.2 / 12, 0.12, 0.12), (ey(3.2), 4.8 / 12, 0.11, 0.12),
                     (ey(2.6), 4.4 / 12, 0.09, 0.12)], sides=12, mat_index=0)
    common.loft(bm, [(ey(2.7), 4.5 / 12, 0.095, 0.12), (ey(2.1), 4.0 / 12, 0.07, 0.12),
                     (ey(2.0), 0.0, 0.0, 0.12)], sides=12, mat_index=1)
    # Highlight ridge on the knob's upper left (rows 3-6, columns 9-11).
    start = len(bm.verts)
    common.loft(bm, [(ey(6.5), 0.0, 0.0, 0.2), (ey(6), 1.2 / 12, 0.05, 0.2), (ey(3.5), 1.2 / 12, 0.05, 0.2),
                     (ey(3), 0.0, 0.0, 0.2)], sides=8, mat_index=2)
    common.shift_x(bm, start, ex(10.5))
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)

    return [(NAME, [gem, lines, cap], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
