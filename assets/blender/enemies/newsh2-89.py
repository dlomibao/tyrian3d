"""Purple armoured pod (newsh2.shp frame 89): a 3D version of its sprite.

Seen in episode 1 (levels 25-36) and episode 3. A boxy purple hull with chamfered corners filling
the block: a blue window at the top edge, raised armour plates over the upper half (two side
panels and a centre spine of two ridges), and a darker lower half with two rounded side pods and
two ribs between them. One frame. Built round column 12, the sprite's centre line.

Run: blender --background --python assets/blender/enemies/newsh2-89.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b009 as lib  # noqa: E402

NAME = "newsh2-89"
U = 1 / 12
X0 = lib.px(12)


def nacelle(bm, cx, cz, r, mat, dark):
    """A round engine nacelle along Y (sprite rows): ribbed housing, nozzle opening at the rear."""
    ring = lambda row, k: [(cx + k * r * math.cos(a), lib.row(row), cz + k * r * math.sin(a))  # noqa: E731
                           for a in (2 * math.pi * (i + 0.5) / 12 for i in range(12))]
    spec = [(16.7, 0.86), (17.2, 1.0), (18.9, 1.0), (19.0, 1.05), (19.5, 1.05), (19.6, 1.0), (21.6, 1.0),
            (21.8, 1.08), (23.4, 1.08), (23.4, 0.78), (22.6, 0.72)]
    rings = [ring(rw, k) for rw, k in spec]
    mats = [mat] * (len(rings) - 3) + [mat, dark]
    lib.ring_loft(bm, rings, mats, cap_mats=(mat, dark), smooth=True)


def bar(bm, top, pts, radius, mat, lift, flat=0.85):
    """A straight bar of constant chamfered cross-section lying on the hull top."""
    lib.polyline_tube(bm, [(x, y, top(x, y) + lift) for x, y in pts], radius, sides=8, mat_index=mat,
                      smooth=False, flat=flat)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(86, metallic=0.4, roughness=0.45),  # 0 upper hull
        pal(82, metallic=0.35, roughness=0.5),  # 1 lower hull / bay
        pal(90, metallic=0.45, roughness=0.4),  # 2 armour plates, belt lip
        pal(91, metallic=0.5, roughness=0.35),  # 3 cage bars
        pal(59, metallic=0.2, roughness=0.1),  # 4 blue window
        pal(134, metallic=0.3, roughness=0.2),  # 5 window sill
        pal(85, metallic=0.45, roughness=0.4),  # 6 engine nacelles
        pal(80, metallic=0.2, roughness=0.6),  # 7 dark grooves, nozzle interiors
        pal(84, metallic=0.4, roughness=0.45),  # 8 keel ribs, waist band
        pal(93, metallic=0.5, roughness=0.3),  # 9 spine bars
    ]
    UPPER, LOWER, PLATE, BAR, GLASS, FRAME, POD, DARK, KEEL, SPINE = range(10)
    bm = bmesh.new()

    # Hull: a deep box (flat top, steep sides) with chamfered corners; the upper half (rows 1-16)
    # stands about 7 px tall, then it steps down to the engine bay (rows 17-24, about 4 px).
    hull = lib.Profile([(lib.ey(r), w * U, h, z) for r, w, h, z in (
        (0.8, 5.0, 0.38, 0.10), (1.5, 7.6, 0.42, 0.13), (2.5, 9.3, 0.44, 0.14), (3.5, 10.2, 0.45, 0.15),
        (4.5, 10.5, 0.45, 0.15), (16.4, 10.5, 0.45, 0.15), (16.9, 10.5, 0.31, 0.01), (19.5, 10.5, 0.31, 0.01),
        (20.5, 9.6, 0.31, 0.01), (21.5, 8.6, 0.30, 0.0), (22.5, 7.8, 0.29, 0.0), (23.5, 6.8, 0.27, -0.01),
        (24.7, 5.6, 0.22, -0.03))], power=5.0)
    f0 = len(bm.faces)
    hull.build(bm, sides=24, mat_index=UPPER, smooth=False, dx=X0)
    bm.faces.ensure_lookup_table()
    split = lib.ey(16.6)
    for f in bm.faces[f0:]:
        if f.calc_center_median().y < split:
            f.material_index = LOWER
    top = lambda x, y: hull.top(x - X0, y)  # noqa: E731

    # Blue window at the top edge (rows 1-3, columns 9-15) in a raised housing, with a light sill.
    lib.drape_patch(bm, top, lib.ex(8.4), lib.ex(16.6), lib.ey(4.3), lib.ey(0.9), nx=4, ny=2, lift=0.035,
                    depth=0.08, mat_index=UPPER)
    lib.drape_patch(bm, top, lib.ex(9), lib.ex(16), lib.ey(3), lib.ey(1.05), nx=3, ny=2, lift=0.075,
                    depth=0.06, mat_index=GLASS, side_mat=FRAME)
    lib.drape_patch(bm, top, lib.ex(9), lib.ex(16), lib.ey(4), lib.ey(3), nx=3, ny=1, lift=0.065,
                    depth=0.05, mat_index=FRAME)

    # Armour plates either side (columns 6-8 and 16-18, rows 6-12), framed by bars.
    for c0, c1 in ((5.6, 9.4), (15.6, 19.4)):
        lib.drape_patch(bm, top, lib.ex(c0), lib.ex(c1), lib.ey(13.4), lib.ey(5.6), nx=2, ny=3, lift=0.05,
                        depth=0.09, mat_index=PLATE, side_mat=UPPER)
    # Cage: bars across rows 5 and 13 (columns 5-19) and down columns 5 and 19.
    r_bar = 0.62 * U
    for rw in (5.5, 13.5):
        y = lib.row(rw)
        bar(bm, top, [(lib.ex(c), y) for c in (4.6, 8.0, 12.5, 17.0, 20.4)], r_bar, BAR, 0.07)
    for c in (5.5, 19.5):
        x = lib.ex(c)
        bar(bm, top, [(x, lib.row(r)) for r in (5.5, 9.5, 13.5)], r_bar, BAR, 0.07)
    # The two spine bars (columns 10-11 and 13-14), from the top bar down over the waist (row 16).
    for c in (11.0, 14.0):
        x = lib.ex(c)
        bar(bm, top, [(x, lib.row(r)) for r in (4.9, 16.2)], 1.0 * U, SPINE, 0.13, flat=0.9)
    # Dark seam down column 12 between the spine bars.
    lib.drape_patch(bm, top, lib.ex(12.15), lib.ex(12.85), lib.ey(15.5), lib.ey(5.5), nx=1, ny=3,
                    lift=0.003, depth=0.02, mat_index=LOWER)

    # Waist: a darker band (rows 14-15) and the lit lip of the step down (row 16).
    lib.drape_patch(bm, top, lib.ex(1.6), lib.ex(23.4), lib.ey(15.6), lib.ey(14.0), nx=6, ny=1, lift=0.012,
                    depth=0.04, mat_index=KEEL, side_mat=LOWER)
    lib.drape_patch(bm, top, lib.ex(1.6), lib.ex(23.4), lib.ey(16.6), lib.ey(15.6), nx=6, ny=1, lift=0.04,
                    depth=0.08, mat_index=PLATE, side_mat=UPPER)

    # Engine bay: two round ribbed nacelles pointing back, nozzles at row 23.
    rz = lib.row(20.0)
    for c in (6.8, 17.2):
        x = lib.px(c)
        nacelle(bm, x, top(x, rz) - 0.01, 2.35 * U, POD, DARK)
    # Keel between them: two raised ribs (columns 10-11 and 13-14) with dark grooves at 9, 12, 15.
    for c0, c1 in ((10, 12), (13, 15)):
        lib.drape_patch(bm, top, lib.ex(c0) + 0.08 * U, lib.ex(c1) - 0.08 * U, lib.ey(24.8), lib.ey(16.6),
                        nx=1, ny=4, lift=0.13, depth=0.2, mat_index=KEEL, side_mat=LOWER)
    for c in (9, 12, 15):
        lib.drape_patch(bm, top, lib.ex(c) + 0.1 * U, lib.ex(c + 1) - 0.1 * U, lib.ey(24.6), lib.ey(16.8),
                        nx=1, ny=3, lift=0.004, depth=0.03, mat_index=DARK)

    return [(NAME, [lib.finish(NAME, bm, mats, coll)], sprite["sprites"])]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
