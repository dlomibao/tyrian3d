"""Brown tusked crawler (newshd.shp frame 16): a 3D version of its sprite.

Seen in episode 1 (level 1.21). A brown, wood-and-flesh ground creature seen from above: two tall
side pods framed in light tan, each holding two recessed red panels; a ribbed brown spine between
them, notched at the top with a red V; a pink arched mouth at the spine's foot over a crossbar
with two small red-tipped fangs; and two curved tusks with a green stripe sweeping out and back in
below. One frame, one model.

Run: blender --background --python assets/blender/enemies/newshd-16.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b138 as lib  # noqa: E402
from lib_b138 import common, ex, ey  # noqa: E402

NAME = "newshd-16"

POD_TOP = 0.30
# Left pod and its panels as pixel-edge outlines (column, row), counter-clockwise seen from above.
POD = [(3, 4), (3, 15), (5, 17), (9, 17), (9, 1), (6, 1)]
PANEL_UP = [(4, 5), (4, 9), (8, 9), (8, 2), (7, 2)]
PANEL_LOW = [(4, 10), (4, 14), (6, 16), (8, 16), (8, 10)]
FRAME = [(3.5, 4.2), (3.5, 14.8), (5.2, 16.5), (8.5, 16.5), (8.5, 1.5), (6.2, 1.5), (3.5, 4.2)]
# Left tusk: centre line (column edge, row) and radius (px).
TUSK = [(7.0, 17.3, 1.6), (6.0, 18.5, 1.6), (5.0, 19.5, 1.6), (4.5, 20.5, 1.5), (4.5, 21.5, 1.5),
        (4.7, 22.5, 1.45), (5.5, 23.5, 1.4), (6.5, 24.5, 1.35), (7.5, 25.5, 1.2), (8.1, 26.4, 0.9),
        (8.6, 27.4, 0.45)]


def outline(pts, mirror=False):
    out = [(ex(24 - c if mirror else c), ey(r)) for c, r in pts]
    return list(reversed(out)) if mirror else out


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(24, metallic=0.1, roughness=0.75),  # 0 pod sides
        pal(27, metallic=0.15, roughness=0.6),  # 1 light tan frames
        pal(70, metallic=0.1, roughness=0.55),  # 2 red panels
        pal(23, metallic=0.1, roughness=0.7),  # 3 spine
        pal(26, metallic=0.15, roughness=0.6),  # 4 spine's lit rib
        pal(20, metallic=0.1, roughness=0.8),  # 5 dark grooves, crossbar and fangs
        pal(116, metallic=0.2, roughness=0.5),  # 6 red trim and fang tips
        pal(73, metallic=0.1, roughness=0.5),  # 7 pink mouth
        pal(25, metallic=0.1, roughness=0.65),  # 8 tusks
        pal(35, metallic=0.2, roughness=0.5),  # 9 green stripe
    ]
    SIDE, FRAMEM, RED, SPINE, RIB, DARK, TRIM, PINK, TUSKM, GREEN = range(10)
    bm = bmesh.new()

    for m in (False, True):
        # Pod body, its two red panels a little proud of it and the light frame round them.
        lib.prism(bm, outline(POD, m), 0.0, POD_TOP - 0.03, SIDE)
        lib.prism(bm, outline(PANEL_UP, m), POD_TOP - 0.05, POD_TOP, RED)
        lib.prism(bm, outline(PANEL_LOW, m), POD_TOP - 0.05, POD_TOP, RED)
        sx = (lambda c: 24 - c) if m else (lambda c: c)  # noqa: E731
        first = len(bm.faces)
        lib.polyline_tube(bm, [(ex(sx(c)), ey(r), POD_TOP + 0.005) for c, r in FRAME], 0.045, sides=6,
                          mat_index=FRAMEM)
        lib.polyline_tube(bm, [(ex(sx(3.6)), ey(9.5), POD_TOP + 0.005), (ex(sx(8.4)), ey(9.5), POD_TOP + 0.005)],
                          0.045, sides=6, mat_index=FRAMEM)

        # Tusk with its green stripe along the top.
        lib.polyline_tube(bm, [(ex(sx(c)), ey(r), 0.05 + rad / 12 * 0.8) for c, r, rad in TUSK],
                          [rad / 12 for _, _, rad in TUSK], sides=8, mat_index=TUSKM)
        lib.polyline_tube(bm, [(ex(sx(c)), ey(r), 0.05 + rad / 12 * 1.55) for c, r, rad in TUSK[:-1]],
                          [rad / 12 * 0.42 for _, _, rad in TUSK[:-1]], sides=6, mat_index=GREEN)

        # Fang under the crossbar, red-tipped.
        fx = ex(sx(10.5))
        lib.polyline_tube(bm, [(fx, ey(18.3), 0.12), (fx, ey(20.2), 0.08), (fx, ey(21.0), 0.06)],
                          [0.045, 0.04, 0.035], sides=6, mat_index=DARK)
        lib.dome(bm, fx, ey(21.4), 0.045, 0.06, 0.07, z=0.02, rings=3, sides=8, mat_index=TRIM)
        lib.mark_smooth(bm, first)

    # Spine: a rounded ridge down the middle with a lit rib and a dark groove.
    first = len(bm.faces)
    rings = []
    for r, h in ((4.6, 0.25), (5.4, 0.29), (12.6, 0.29), (14.0, 0.23)):
        rings.append([(3.0 / 12 * math.cos(math.pi * k / 8), ey(r), h * math.sin(math.pi * k / 8)) for k in range(9)])
    lib.ring_loft(bm, rings, SPINE)
    lib.mark_smooth(bm, first)
    lib.box(bm, ex(10.1), ex(10.9), ey(13.6), ey(4.8), 0.0, 0.262, RIB)
    lib.box(bm, ex(12.15), ex(12.75), ey(13.6), ey(5.0), 0.0, 0.29, DARK)
    # The red V notch at its top.
    first = len(bm.faces)
    lib.polyline_tube(bm, [(ex(9.4), ey(3.1), 0.26), (ex(11.0), ey(5.2), 0.28), (ex(13.0), ey(5.2), 0.28),
                           (ex(14.6), ey(3.1), 0.26)], 0.05, sides=6, mat_index=TRIM)
    lib.mark_smooth(bm, first)

    # Pink arched mouth at the spine's foot, and the crossbar under it.
    mouth = [(9, 13.6), (9, 17.6), (11, 17.6), (11, 15), (13, 15), (13, 17.6), (15, 17.6), (15, 13.6)]
    lib.prism(bm, [(ex(c), ey(r)) for c, r in mouth], 0.0, 0.2, PINK)
    first = len(bm.faces)
    lib.polyline_tube(bm, [(ex(7.8), ey(18.5), 0.12), (ex(16.2), ey(18.5), 0.12)], 0.07, sides=8, mat_index=DARK)
    lib.mark_smooth(bm, first)

    obj = lib.mesh_object_mixed(NAME, bm, mats, coll)
    return [(NAME, [obj], sprite["sprites"], 0)]


if __name__ == "__main__":
    lib.run(NAME, build, __file__)
