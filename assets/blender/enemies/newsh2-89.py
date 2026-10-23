"""Purple armoured pod (newsh2.shp frame 89): a 3D version of its sprite.

Seen in episode 1 (levels 25-36) and episode 3. A boxy purple hull with chamfered corners filling
the block: a blue window at the top edge, raised armour plates over the upper half (two side
panels and a centre spine of two ridges), and a darker lower half with two rounded side pods and
two ribs between them. One frame. Built round column 12, the sprite's centre line.

Run: blender --background --python assets/blender/enemies/newsh2-89.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-89"
U = 1 / 12
X0 = lib.px(12)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(86, metallic=0.4, roughness=0.45),  # 0 upper hull
        pal(82, metallic=0.35, roughness=0.5),  # 1 lower hull
        pal(90, metallic=0.45, roughness=0.4),  # 2 armour plates
        pal(92, metallic=0.4, roughness=0.35),  # 3 bright ridges
        pal(59, metallic=0.2, roughness=0.1),  # 4 blue window
        pal(134, metallic=0.3, roughness=0.2),  # 5 window frame
        pal(85, metallic=0.25, roughness=0.5),  # 6 lower pods and ribs
        pal(80, metallic=0.2, roughness=0.6),  # 7 dark grooves
    ]
    UPPER, LOWER, PLATE, RIDGE, GLASS, FRAME, POD, DARK = range(8)
    bm = bmesh.new()

    # Hull: chamfered top corners, straight sides over rows 4-19, tapering to the bottom (row 24).
    hull = lib.Profile([(lib.ey(r), w * U, h, 0.0) for r, w, h in (
        (0.8, 5.0, 0.14), (1.5, 7.6, 0.2), (2.5, 9.3, 0.24), (3.5, 10.2, 0.26), (4.5, 10.5, 0.27),
        (19.5, 10.5, 0.27), (20.5, 9.6, 0.26), (21.5, 8.6, 0.24), (22.5, 7.8, 0.22), (23.5, 6.8, 0.19),
        (24.7, 5.6, 0.14))], power=4.0)
    f0 = len(bm.faces)
    hull.build(bm, sides=24, mat_index=UPPER, smooth=False, dx=X0)
    bm.faces.ensure_lookup_table()
    split = lib.ey(14)
    for f in bm.faces[f0:]:
        if f.calc_center_median().y < split:
            f.material_index = LOWER
    top = lambda x, y: hull.top(x - X0, y)  # noqa: E731

    # Armour over the upper half: side panels (columns 5-8 and 16-19) and the centre block
    # (columns 10-14), rows 5-13, with the hull showing in the grooves between them.
    for c0, c1 in ((5, 9), (16, 20), (10, 15)):
        lib.drape_patch(bm, top, lib.ex(c0), lib.ex(c1), lib.ey(14), lib.ey(5), nx=2, ny=3, lift=0.03,
                        depth=0.06, mat_index=PLATE, side_mat=UPPER)
    # The two ridges down the spine (columns 10-11 and 13-14), on to row 15.
    for c in (10.5, 13.5):
        x = lib.px(c)
        pts = [(x, lib.ey(r), top(x, lib.ey(r)) + 0.035) for r in (5.2, 9.0, 13.0, 15.8)]
        lib.polyline_tube(bm, pts, [0.8 * U, 1.0 * U, 1.0 * U, 0.7 * U], sides=8, mat_index=RIDGE, flat=0.7)
    # Ledge across row 16.
    lib.drape_patch(bm, top, lib.ex(4), lib.ex(20), lib.ey(17), lib.ey(16), nx=4, ny=1, lift=0.012,
                    depth=0.04, mat_index=PLATE, side_mat=LOWER)

    # Blue window at the top edge (rows 1-3, columns 9-15).
    lib.drape_patch(bm, top, lib.ex(9), lib.ex(16), lib.ey(4), lib.ey(1), nx=3, ny=2, lift=0.02,
                    depth=0.05, mat_index=GLASS, side_mat=FRAME)

    # Lower half: two rounded side pods, two ribs between them and dark grooves at columns 9, 12, 15.
    for c in (6.6, 17.4):
        x = lib.px(c)
        lib.ellipsoid(bm, (x, lib.row(20.0), top(x, lib.row(20.0)) - 0.03), (3.2 * U, 3.3 * U, 0.075),
                      segments=14, rings=8, mat_index=POD)
    for c in (10.5, 13.5):
        x = lib.px(c)
        pts = [(x, lib.ey(r), top(x, lib.ey(r)) + 0.01) for r in (17.3, 20.0, 22.5, 24.6)]
        lib.polyline_tube(bm, pts, [0.8 * U, 1.0 * U, 1.0 * U, 0.6 * U], sides=8, mat_index=POD, flat=0.8)
    for c in (9, 12, 15):
        lib.drape_patch(bm, top, lib.ex(c) + 0.15 * U, lib.ex(c + 1) - 0.15 * U, lib.ey(24.5), lib.ey(17),
                        nx=1, ny=3, lift=0.004, depth=0.03, mat_index=DARK)

    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
