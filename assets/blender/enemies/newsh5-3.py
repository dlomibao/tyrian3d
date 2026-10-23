"""Purple bat-winged pod (newsh5.shp frames 3-17): a 3D version of its sprite.

Seen in episode 4 (level 4.12). A purple machine: a head of two round lobes on a ridged neck at
the top, a broad collar with two white eyes, a boxy body with a dark groove down its middle and
two glowing green strips, and ribbed bat wings drooping off each side. The eight frames only run
green lights: the rungs in the groove, a bar scanning down the body and the outer wing ribs
(green in seven frames), so one model covers them all, with the rungs and wing ribs lit and no
bar.

Run: blender --background --python assets/blender/enemies/newsh5-3.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b037 as L  # noqa: E402

NAME = "newsh5-3"
PX = 1 / 12
AX = 0.0  # mirror symmetric about pixel edge 12
E, R = L.EX, L.EY


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(87, metallic=0.35, roughness=0.4),  # 0 purple body
        pal(85, metallic=0.15, roughness=0.65),  # 1 darker purple wings and neck
        pal(90, metallic=0.4, roughness=0.3),  # 2 light purple ridges, ribs and collar
        pal(81, metallic=0.2, roughness=0.7),  # 3 dark groove and holes
        pal(93, metallic=0.2, roughness=0.3, emission_strength=2.0),  # 4 white eyes
        pal(199, metallic=0.1, roughness=0.4, emission_strength=4.0),  # 5 green lights
        pal(38, metallic=0.2, roughness=0.6),  # 6 dark green strip ends
    ]
    BODY, WING, RIDGE, GROOVE, EYE, GREEN, DGREEN = range(7)
    bm = bmesh.new()
    start = len(bm.verts)

    # ---- left half (mirrored about the axis) ----

    # Head lobe (columns 6-10, rows 0-5).
    L.ellipsoid(bm, (E(8.8), R(3.0), 0.08), (2.4 * PX, 2.8 * PX, 0.13), mat=BODY, segments=14, rings=7)
    # Light ridge down the neck (column 10, rows 2-10).
    L.loft_y(bm, L.X(10), [(R(2.0), 0.0, 0.0, 0.13), (R(2.8), 0.6 * PX, 0.04, 0.15), (R(9.5), 0.6 * PX, 0.04, 0.17),
                           (R(10.5), 0.0, 0.0, 0.17)], sides=6, mat=RIDGE)

    # Collar across the top of the body (rows 10-12) and an eye in it (column 10, row 12).
    L.loft_x(bm, R(11.6), [(E(5.8), 0.0, 0.0, 0.14), (E(6.3), 1.4 * PX, 0.07, 0.15), (AX, 1.6 * PX, 0.09, 0.16)],
             sides=8, mat=RIDGE, cap_end=False)
    L.ellipsoid(bm, (L.X(10), R(12.3), 0.2), (0.7 * PX, 0.7 * PX, 0.05), mat=EYE, segments=8, rings=4)
    # The hole under it (column 9, row 13).
    L.box(bm, E(9), R(14), E(10), R(13), 0.14, 0.205, mat=GROOVE)

    # Dark groove down the middle (columns 11-12, rows 13-24) with green rungs at rows 18, 20, 22.
    L.box(bm, E(11), R(24.6), AX, R(13.0), 0.15, 0.215, mat=GROOVE)
    for r in (18, 20, 22):
        L.box(bm, E(11), R(r + 1), AX, R(r), 0.15, 0.225, mat=GREEN)
    # Glowing green strip down the body (columns 7-8, rows 17-23) with dark ends (rows 24-25).
    L.loft_y(bm, E(8), [(R(16.6), 0.0, 0.0, 0.12), (R(17.0), 1.1 * PX, 0.07, 0.12), (R(23.8), 1.1 * PX, 0.07, 0.1)],
             sides=8, mat=GREEN, cap_end=False)
    L.loft_y(bm, E(8), [(R(23.8), 1.1 * PX, 0.07, 0.1), (R(25.6), 0.9 * PX, 0.05, 0.04), (R(26.0), 0.0, 0.0, 0.04)],
             sides=8, mat=DGREEN, cap_start=False)

    # Bat wing (columns 0-5, rows 11-22) with its scalloped trailing edge, two ribs, drooping outward.
    wing_start = len(bm.verts)
    outline = [(0, 11), (6.2, 11), (6.2, 23), (5.5, 22.4), (4.8, 22), (4.0, 21.8), (3.5, 20.6), (3.0, 20.7),
               (2.5, 21.0), (2.0, 20.8), (1.4, 20.0), (1.0, 19.7), (0.5, 18.6), (0, 18)]
    L.plate(bm, [(E(c), R(r)) for c, r in outline], -0.06, 0.05, mat=WING)
    L.loft_y(bm, L.X(2), [(R(11.3), 0.0, 0.0, 0.05), (R(12.0), 0.6 * PX, 0.04, 0.06), (R(19.6), 0.6 * PX, 0.04, 0.06),
                          (R(20.6), 0.0, 0.0, 0.05)], sides=6, mat=RIDGE)
    L.loft_y(bm, L.X(4), [(R(11.3), 0.0, 0.0, 0.05), (R(12.0), 0.6 * PX, 0.04, 0.06), (R(15.9), 0.6 * PX, 0.04, 0.06)],
             sides=6, mat=RIDGE, cap_end=False)
    L.loft_y(bm, L.X(4), [(R(15.9), 0.6 * PX, 0.04, 0.06), (R(21.0), 0.6 * PX, 0.04, 0.06), (R(21.8), 0.0, 0.0, 0.05)],
             sides=6, mat=GREEN, cap_start=False)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[wing_start:]:
        v.co.z -= 0.16 * (E(6.2) - v.co.x) / (6.2 * PX)

    L.mirror_since(bm, start, AX)

    # ---- centre parts ----

    # Neck between the lobes (columns 8-15, rows 1-10).
    L.loft_y(bm, AX, [(R(1.0), 1.0 * PX, 0.06, 0.07), (R(3.0), 2.4 * PX, 0.1, 0.08), (R(6.0), 3.0 * PX, 0.11, 0.08),
                      (R(9.0), 3.6 * PX, 0.12, 0.07), (R(10.5), 4.5 * PX, 0.12, 0.06)], sides=10, mat=WING)
    # Body (columns 6-17, rows 10-25).
    L.loft_y(bm, AX, [(R(10.0), 4.5 * PX, 0.12, 0.02), (R(10.8), 6.0 * PX, 0.19, 0.0), (R(23.5), 6.0 * PX, 0.19, 0.0),
                      (R(25.0), 5.2 * PX, 0.15, 0.0), (R(25.9), 3.8 * PX, 0.08, 0.0)], sides=14, mat=BODY)

    return L.to_object(NAME, bm, mats, coll)


if __name__ == "__main__":
    L.run(__file__, NAME, build)
