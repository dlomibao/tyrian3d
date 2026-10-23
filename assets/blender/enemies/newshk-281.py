"""Red-eye gun pod (newshk.shp frame 281): a 3D version of its sprite.

Seen in episode 3 (level 3.12). A grey armoured pod: a broad lower block with a slot set in a
raised frame, grey rails down its sides and a keel tapering underneath; above it, between two
bright struts that rise to a small red vent on top, a big red glass eye in a dark socket, glowing
white-hot at its lower left, with dark grey shoulders and light ledges either side.

Run: blender --background --python assets/blender/enemies/newshk-281.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b032 as lib  # noqa: E402

common = lib.common
NAME = "newshk-281"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
X, Y, PX = lib.X, lib.Y, lib.PX


def ex(c):
    """Column edge (the left edge of column c) to X."""
    return (c - 12) / 12


def ey(r):
    """Row edge (the top edge of row r) to Y."""
    return (14 - r) / 12


def outline(pts):
    return [(ex(c), ey(r)) for c, r in pts]


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(9, metallic=0.6, roughness=0.4),  # 0 grey armour
        pal(11, metallic=0.6, roughness=0.35),  # 1 light grey frame and rails
        pal(13, metallic=0.6, roughness=0.3),  # 2 bright ledges
        pal(6, metallic=0.5, roughness=0.5),  # 3 dark grey shoulders
        pal(5, metallic=0.4, roughness=0.6),  # 4 the slot
        pal(113, metallic=0.3, roughness=0.5),  # 5 dark red socket
        pal(116, metallic=0.2, roughness=0.15, emission_strength=0.8),  # 6 red glass eye
        pal(114, metallic=0.2, roughness=0.15, emission_strength=0.4),  # 7 its shadowed top
        pal(125, emission_strength=4.0),  # 8 eye glow
        pal(127, emission_strength=6.0),  # 9 white-hot centre
        pal(123, emission_strength=3.5),  # 10 vent glow
        pal(10, metallic=0.6, roughness=0.3),  # 11 bright struts
        pal(118, metallic=0.3, roughness=0.4, emission_strength=0.8),  # 12 red vent
        pal(8, metallic=0.5, roughness=0.45),  # 13 side columns, seam
    ]
    ARMOUR, LIGHT, BRIGHT, SHOULDER, SLOT, SOCKET, EYE, EYETOP, GLOW, HOT, VENTGLOW, STRUT, VENT, SIDE = range(14)
    bm = bmesh.new()

    # ---- lower block (rows 14-26) ----
    lib.bevel_plate(bm, outline([(0, 14), (24, 14), (24, 24), (18, 25), (16, 26), (14, 27), (10, 27), (8, 26),
                                 (6, 25), (0, 24)]), -0.2, 0.1, 0.035, mat=ARMOUR)
    # The slot in its raised frame (columns 7-16, rows 17-20).
    for c0, r0, c1, r1 in [(7, 17, 17, 18), (7, 20.4, 17, 21), (7, 18, 8, 20.4), (16, 18, 17, 20.4)]:
        lib.box(bm, ex(c0), ey(r0), ex(c1), ey(r1), 0.05, 0.15, mat=LIGHT)
    lib.box(bm, ex(8), ey(18), ex(16), ey(20.4), 0.05, 0.115, mat=SLOT)

    # Side rails and the darker outer columns (left half, mirrored).
    start = lib.nfaces(bm)
    lib.bevel_plate(bm, outline([(2, 15), (5, 15), (5, 23), (2, 23)]), 0.05, 0.14, 0.015, mat=LIGHT)
    lib.box(bm, ex(3.6), ey(17.6), ex(4.6), ey(18.8), 0.13, 0.15, mat=BRIGHT)  # the glint at row 18
    lib.box(bm, ex(0), ey(15), ex(2), ey(23.5), 0.0, 0.11, mat=SIDE)
    # The seam between block and upper works (row 14).
    lib.box(bm, ex(0), ey(13.6), ex(12), ey(14.8), 0.0, 0.115, mat=SIDE)

    # ---- upper works (rows 0-13), left half ----
    # Dark grey shoulder (columns 0-4, rows 5-9) and the light ledge under it (rows 10-12).
    lib.bevel_plate(bm, outline([(0, 5), (4, 5), (4.5, 10), (0, 10)]), -0.12, 0.06, 0.02, mat=SHOULDER)
    lib.bevel_plate(bm, outline([(0, 10), (6, 10), (6.5, 13.6), (0, 13.6)]), -0.12, 0.12, 0.03, mat=LIGHT,
                    top_mat=BRIGHT)
    # Bright strut from the vent down and out to the shoulder, then straight down to the ledge.
    lib.sweep(bm, [(X(8.6), Y(-0.2), 0.06, 1.1 * PX, 0.05), (X(7.2), Y(2.4), 0.08, 1.3 * PX, 0.06),
                   (X(5.4), Y(5.6), 0.1, 1.4 * PX, 0.065), (X(5.0), Y(8.0), 0.11, 1.3 * PX, 0.065),
                   (X(5.0), Y(10.2), 0.11, 1.3 * PX, 0.065)], sides=8, mat=STRUT)
    lib.mirror_x(bm, start)

    # Dark red socket behind the eye (columns 6-18, rows 3-14).
    lib.bevel_plate(bm, outline([(8, 3), (16, 3), (18.5, 5.5), (18.5, 13.5), (17, 14.2), (7, 14.2), (5.5, 13.5),
                                 (5.5, 5.5)]), -0.12, 0.05, 0.02, mat=SOCKET)

    # The red vent on top (columns 11-13, rows 0-3) with its glowing slit.
    lib.bevel_plate(bm, outline([(10.8, 0), (14.2, 0), (14.2, 4), (10.8, 4)]), -0.04, 0.14, 0.02, mat=VENT)
    lib.box(bm, ex(11.7), ey(0.6), ex(13.3), ey(2.8), 0.1, 0.152, mat=VENTGLOW)

    # The eye: a big red glass dome (columns 7-17, rows 4-13), dark across its top, glowing at its
    # lower left (columns 9-12, rows 10-12).
    centre = (X(12.0), Y(8.9), 0.03)
    radii = (5.6 * PX, 5.0 * PX, 0.26)
    faces, pole = lib.pole_ellipsoid(bm, centre, radii, (X(10.8), Y(10.9)), mat=EYE, segments=24, rings=20)
    for f in faces:
        p = f.calc_center_median()
        ang = lib.angle_from_pole(f, centre, radii, pole)
        if ang < 8:
            f.material_index = HOT
        elif ang < 19:
            f.material_index = GLOW
        elif ang < 32:
            f.material_index = VENT  # brighter red round the glow
        elif p.y > Y(7.4) and p.z > 0.03:
            f.material_index = EYETOP

    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
