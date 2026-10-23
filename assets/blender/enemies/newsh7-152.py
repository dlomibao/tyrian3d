"""Small blue crystal (newsh7.shp frame 152, a 12x14 sprite): a 3D version of its sprite.

Seen in episode 3 (level section 10) and episode 4, the small cousin of newsh7-53: a cut gem
under a steel cap, with an octagonal girdle, a table split by a bright crease, sloped crown
facets and a pavilion underneath.

Run: blender --background --python assets/blender/enemies/newsh7-152.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b007 as lib  # noqa: E402
from lib_b007 import common  # noqa: E402

NAME = "newsh7-152"


def ex(c):
    return lib.ex(c, 12)


def ey(r):
    return lib.ey(r, 14)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    gem_mats = [
        pal(149, metallic=0.1, roughness=0.15),  # 0 deep blue pavilion
        pal(152, metallic=0.1, roughness=0.15),  # 1 girdle
        pal(154, metallic=0.1, roughness=0.12),  # 2 side crown
        pal(151, metallic=0.1, roughness=0.15),  # 3 front crown
        pal(156, metallic=0.1, roughness=0.12),  # 4 light crown, front table
        pal(147, metallic=0.1, roughness=0.15),  # 5 dark back table
        pal(153, metallic=0.1, roughness=0.12),  # 6 back crown
        pal(140, emission_strength=2.5),  # 7 white facet lines
    ]
    PAV, GIRD, SIDE, FRONT, LIGHT, BACK, TOPC, LINE = range(8)

    # Girdle and table outlines in pixel-edge coordinates (column, row), counter-clockwise from
    # the top-left; the third and eighth points sit on the crease at row 6.5.
    girdle = [(2, 3), (1, 4), (1, 6.5), (1, 11), (4, 14), (8, 14), (11, 11), (11, 6.5), (11, 4), (10, 3)]
    table = [(3.2, 3.5), (2.6, 4.5), (2.6, 6.5), (2.6, 8.8), (5, 11.5), (7, 11.5), (9.4, 8.8),
             (9.4, 6.5), (9.4, 4.5), (8.8, 3.5)]
    table_z = [0.1, 0.105, 0.13, 0.12, 0.115, 0.115, 0.12, 0.13, 0.105, 0.1]

    def pts(outline, zs):
        return [(ex(c), ey(r), z) for (c, r), z in zip(outline, zs)]

    bm = bmesh.new()
    rings = [
        [(0.0, ey(8.5), -0.16)],
        pts(girdle, [-0.015] * 10),
        pts(girdle, [0.015] * 10),
        pts(table, table_z),
    ]
    crown = [TOPC, SIDE, SIDE, FRONT, FRONT, LIGHT, SIDE, LIGHT, TOPC, TOPC]
    verts = lib.ring_loft(bm, rings, [PAV, GIRD, crown], cap_end=False)
    t = verts[-1]
    bm.faces.new([t[0], t[1], t[2], t[7], t[8], t[9]]).material_index = BACK
    bm.faces.new([t[2], t[3], t[4], t[5], t[6], t[7]]).material_index = LIGHT
    gem = common.mesh_object(NAME, bm, gem_mats, coll, smooth=False)

    # Bright facet lines: the crease across the gem, the table's sides and the diagonals that
    # meet at its front.
    bm = bmesh.new()
    tp = pts(table, table_z)
    gp = pts(girdle, [0.015] * 10)
    r = 0.016
    lift = lambda p: (p[0], p[1], p[2] + 0.005)  # noqa: E731
    lib.polyline_tube(bm, [lift(p) for p in (gp[2], tp[2], tp[7], gp[7])], r, mat_index=0)
    lib.polyline_tube(bm, [lift(p) for p in tp[1:9]], r, mat_index=0)
    lines = common.mesh_object(f"{NAME}_lines", bm, [gem_mats[LINE]], coll, smooth=True)

    # The steel cap (rows 0-2), lit from the left.
    cap_mats = [pal(57, metallic=0.65, roughness=0.3), pal(48, metallic=0.5, roughness=0.5),
                pal(62, metallic=0.7, roughness=0.25)]
    bm = bmesh.new()
    common.loft(bm, [(ey(3.4), 3.4 / 12, 0.04, 0.05), (ey(2.6), 3.1 / 12, 0.055, 0.06),
                     (ey(1.2), 2.8 / 12, 0.06, 0.06), (ey(0.5), 2.2 / 12, 0.05, 0.06)],
                sides=10, mat_index=0)
    common.loft(bm, [(ey(0.6), 2.3 / 12, 0.05, 0.06), (ey(0.0), 0.0, 0.0, 0.06)], sides=10, mat_index=1)
    start = len(bm.verts)
    common.loft(bm, [(ey(2.6), 0.0, 0.0, 0.1), (ey(2.3), 0.9 / 12, 0.025, 0.1), (ey(1.2), 0.9 / 12, 0.025, 0.1),
                     (ey(0.9), 0.0, 0.0, 0.1)], sides=8, mat_index=2)
    common.shift_x(bm, start, ex(5))
    cap = common.mesh_object(f"{NAME}_cap", bm, cap_mats, coll, smooth=True)

    return [(NAME, [gem, lines, cap], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
