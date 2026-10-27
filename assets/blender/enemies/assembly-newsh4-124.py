"""Bronze stag-beetle boss (newsh4.shp, assembly of 20 pieces): a 3D version of its sprites.

Seen in episode 1 (levels 1.28, 1.30, 1.36). Twenty 2x2 enemies side by side make one
120 x 112 px machine (sprite.json `assemblyLayout`): a central tower (a grey dome with a tan brim
and crest, a tan barrel with grey bars and a ladder, a pink collar, a dark neck, the eye, a red
pod and a grey and tan stinger), two big tan wings with red and grey wingtip blocks and a thin
cable to grey pylons behind the tower, a tan chevron across the body down to two shoulders with
red windows, and below them a brown claw and a thin grey hook on each side. It's symmetric about
pixel column 60 (the left half is built and mirrored).

newsh4-1, the piece with the eye, has eight frames in which a grey shutter opens on a red eye
that then flares yellow: three models, closed (frames 1, 3), open and red (5, 7, 39) and glowing
(41, 43, 45). Each animates (common.frame_part, palette_material frames=): the shutter cracks on a
red slit (3), its halves slide back as the eye widens and brightens (5, 7, 39), and the glow grows
taller and hotter (41, 43, 45). The other pieces have one frame each.

The whole machine is built once in assembly coordinates (lib_b015.X / Y), then cut into the
pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newsh4-124.py [-- --preview out.png]
(the preview is the whole machine; each piece also gets <piece>.png next to it) [--frames <dir>]
(each eye model's frames beside its sprite, <dir>/<model>.png).
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b015 import (box, composite_png, ellipsoid, loft_y, merged_sprite, mirror_all, plate,  # noqa: E402
                      sweep, to_object)

NAME = "assembly-newsh4-124"
ROOT = common.repo_root(__file__)
PIECES = ["newsh4-124", "newsh4-126", "newsh4-128", "newsh4-86", "newsh4-88", "newsh4-90", "newsh4-130",
          "newsh4-1", "newsh4-48", "newsh4-50", "newsh4-132", "newsh4-92", "newsh4-94", "newsh4-54",
          "newsh4-56", "newsh4-10", "newsh4-12", "newsh4-14", "newsh4-16", "newsh4-18"]
# The assembly's centre in screen pixels (its top-left corner is screen 125, -32).
CX0, CY0 = 185, 24
AXIS = 60  # mirror symmetric about the centre of pixel column 60
EYE = "newsh4-1"
# The eye piece's models: (model name, frames).
EYE_MODELS = [("newsh4-1", [1, 3]), ("newsh4-1-f2", [5, 7, 39]), ("newsh4-1-f3", [41, 43, 45])]
TAG = "nsh4"


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    return [
        pal(7, metallic=0.6, roughness=0.4),  # 0 grey pylons, stinger, shoulders
        pal(10, metallic=0.7, roughness=0.3),  # 1 light grey dome, bars, hook
        pal(4, metallic=0.5, roughness=0.5),  # 2 dark grey hull
        pal(2, metallic=0.4, roughness=0.6),  # 3 black socket and pod underside
        pal(26, metallic=0.45, roughness=0.4),  # 4 tan wings, chevron, brim
        pal(23, metallic=0.4, roughness=0.5),  # 5 darker tan emblems, stinger tip
        pal(28, metallic=0.5, roughness=0.3),  # 6 light tan ridges and crest
        pal(165, metallic=0.3, roughness=0.6),  # 7 dark brown bands
        pal(72, metallic=0.3, roughness=0.35),  # 8 red panels and windows
        pal(76, metallic=0.3, roughness=0.4),  # 9 pink collar
        pal(168, metallic=0.3, roughness=0.45),  # 10 brown claws
        pal(79, emission_strength=2.5),  # 11 pink lights
        pal(9, metallic=0.75, roughness=0.25),  # 12 grey eye shutter
        pal(74, emission_strength=1.5),  # 13 red eye
        pal(123, emission_strength=4.0),  # 14 eye glow
        pal(126, emission_strength=6.0),  # 15 eye hot core
        pal(25, metallic=0.45, roughness=0.4),  # 16 tan barrel
    ]


(GREY, LGREY, DGREY, BLACK, TAN, DTAN, LTAN, BROWN, RED, PINK, CLAW, LIGHT, SHUTTER, EYE_RED, GLOW,
 HOT, BARREL) = range(17)


def build_left(bm):
    """Everything off the centreline, on the left side (mirrored afterwards)."""

    def wing_tilt(c, r):
        """The wings droop toward their tips (anhedral): lit on the left, shaded on the right."""
        return -0.14 * max(0.0, 34 - c) / 30

    # Big tan wing: a slanted plate from the tip (columns 5-14) to the body (column 34), with a
    # light ridge along its upper edge and a strut on to the barrel (rows 34-38).
    plate(bm, [(4.5, 20.5), (13, 24), (23, 29.5), (34, 34), (34, 48.5), (29.5, 52), (15, 38), (5, 31)],
          -0.03, 0.05, mat=TAN, tilt=wing_tilt)
    sweep(bm, [(5.2, 21.6, 0.05 + wing_tilt(5, 21), 1.0, 0.03), (13, 25.2, 0.05 + wing_tilt(13, 25), 1.2, 0.035),
               (23, 30.2, 0.05 + wing_tilt(23, 30), 1.2, 0.035), (33.5, 34.8, 0.05, 1.2, 0.035)],
          sides=6, mat=LTAN)
    sweep(bm, [(15.5, 38.5, wing_tilt(15, 38) + 0.01, 0.8, 0.03), (29.5, 51, 0.01, 0.8, 0.03)], sides=6, mat=DTAN)
    box(bm, 33, 34, 43, 38, -0.02, 0.1, mat=TAN)
    # Wingtip block: a red face on the outside (columns 6-10) and a grey block inside it.
    box(bm, 6, 26, 10, 36, -0.24, 0.0, mat=RED)
    box(bm, 10, 29, 14, 36, -0.22, -0.02, mat=GREY)
    # Thin tan cable from the pylon's top round to the wing tip (rows 9-22).
    sweep(bm, [(20.5, 9.0, 0.1, 0.9, 0.035), (16, 9.2, 0.1, 1.0, 0.035), (12.5, 10.5, 0.08, 1.0, 0.035),
               (9.8, 12.8, 0.05, 1.0, 0.035), (7.5, 16, 0.02, 1.0, 0.035), (5.8, 19.5, -0.02, 1.1, 0.035),
               (5.6, 22.5, -0.04, 1.1, 0.035)], sides=6, mat=TAN)

    # Grey pylon behind the tower (columns 19-46, rows 3-35): a slanted block with a bright outer
    # post, a tan emblem and a dark brown band, and a bright bar down to the barrel's side.
    plate(bm, [(20.5, 2.5), (25, 2.5), (34, 7), (43, 11), (47, 13), (47, 30), (41, 35.5), (36.5, 34),
               (36, 30), (30, 22), (22.5, 19), (19.5, 17.5), (19.5, 7)], -0.1, 0.12, mat=GREY)
    plate(bm, [(20.5, 3.2), (24.5, 3.2), (25.5, 4), (25.5, 18.5), (21.5, 18.5), (20.5, 17)], 0.12, 0.17, mat=LGREY)
    plate(bm, [(27, 9.5), (31, 8), (36, 10.5), (36, 12.5), (31, 11), (29.5, 12), (29.5, 15.5), (27, 15.5)],
          0.12, 0.16, mat=DTAN)
    plate(bm, [(26.5, 17.5), (45, 17.5), (46, 20.5), (28, 20.5)], 0.12, 0.155, mat=BROWN)
    box(bm, 37, 22, 38, 34, 0.08, 0.17, mat=LGREY)

    # Arm root from the hull down to the shoulder (columns 28-40, rows 46-58).
    plate(bm, [(28, 52), (33, 46.5), (41, 45.5), (41, 53), (36, 58.5), (28, 58.5)], -0.14, 0.05, mat=GREY)
    # Red panel above the chevron (rows 39-43).
    plate(bm, [(38.5, 39.5), (45, 39.5), (54.5, 41.5), (54.5, 44), (38.5, 44)], 0.02, 0.12, mat=RED)

    # Tan chevron from the middle out and down to the shoulder, with a light outer edge.
    outer = [(58.5, 43.5), (47.5, 43.5), (45.5, 46), (43.5, 48), (41, 50), (39.5, 52), (37.5, 54), (35, 56),
             (33.5, 58), (30.5, 59), (31, 61), (32.5, 62), (34.5, 64), (35, 66), (35.5, 68), (36, 71),
             (37, 72.5)]
    inner = [(39.5, 72.5), (40, 68.5), (41, 64.5), (42.5, 62.5), (43.5, 58), (43, 56.5), (45, 54.5),
             (47, 52.5), (49, 50.5), (55, 49.5), (58.5, 48.5)]
    plate(bm, outer + inner, 0.1, 0.24, mat=TAN)
    sweep(bm, [(c + 0.6, r + 0.6, 0.24, 0.7, 0.025) for c, r in outer[1:9]], sides=6, mat=LTAN)
    # Tan blade hanging below the shoulder (columns 24-28, rows 68-79).
    plate(bm, [(23.5, 67.5), (29.5, 67.5), (28.5, 73), (25.5, 79), (23.5, 79)], -0.02, 0.12, mat=TAN)

    # Shoulder block (columns 14-33, rows 57-68) with a red window, and a smaller block under it
    # with a red triangular window, then the grey wrist.
    plate(bm, [(14, 60.5), (16, 59), (18, 58), (23, 58), (25, 59), (34, 59), (34, 69), (14, 69)],
          -0.14, 0.1, mat=GREY)
    plate(bm, [(18, 58), (23, 58), (23.5, 60.5), (17.5, 60.5)], 0.1, 0.15, mat=LGREY)
    box(bm, 16, 62, 21, 67, 0.06, 0.13, mat=RED)
    box(bm, 15, 70, 23, 76, -0.12, 0.06, mat=GREY)
    box(bm, 15, 70, 23, 71, 0.06, 0.09, mat=LGREY)
    plate(bm, [(18, 72.5), (22.5, 72.5), (22.5, 73.5), (18.5, 77)], 0.03, 0.1, mat=RED)
    plate(bm, [(16, 77), (24, 77), (24, 82), (22.5, 84.5), (16.5, 84.5)], -0.1, 0.05, mat=GREY)

    # Brown claw curving in to its tip (rows 84-106) and the thin grey hook inside it.
    sweep(bm, [(20.2, 83.5, -0.02, 3.6, 0.1), (20, 89.5, -0.03, 3.5, 0.1), (21, 95, -0.04, 3.4, 0.095),
               (24.6, 100, -0.05, 3.3, 0.09), (30, 103.8, -0.06, 2.9, 0.08), (34, 105.3, -0.065, 1.9, 0.06),
               (37.2, 105.9, -0.07, 0.0, 0.0)], sides=8, mat=CLAW)
    sweep(bm, [(26.8, 71.5, 0.02, 1.9, 0.06), (28.2, 77, 0.0, 2.0, 0.06), (30.6, 81, -0.01, 2.0, 0.06),
               (34.2, 84.6, -0.02, 1.9, 0.055), (38.4, 87, -0.03, 1.7, 0.05), (44, 88.6, -0.04, 1.4, 0.045),
               (50.2, 89.1, -0.05, 0.0, 0.0)], sides=8, mat=LGREY)


def build_centre(bm):
    """The tower down the middle and the hull under everything (symmetric about column 60)."""
    # Dark grey hull under the wings, chevron and shoulders.
    loft_y(bm, AXIS, [(16.5, 0.0, 0.0, -0.12), (18, 13, 0.12, -0.12), (22, 21, 0.16, -0.12),
                      (30, 26.5, 0.18, -0.12), (42, 27.5, 0.18, -0.12), (50, 25.5, 0.17, -0.12),
                      (56, 20, 0.15, -0.12), (61, 11, 0.12, -0.12), (63, 0.0, 0.0, -0.12)], sides=14, mat=DGREY)

    # Tower: grey dome, tan brim, dark band under it, tan barrel, pink collar, grey neck, black
    # eye socket, red pod with a black underside, grey stinger with a tan tip.
    loft_y(bm, AXIS, [(5.8, 0.0, 0.0, 0.06), (6.5, 4.0, 0.12, 0.05), (8, 7.2, 0.2, 0.03), (10, 9.6, 0.25, 0.02),
                      (12, 11.4, 0.28, 0.0), (13.5, 12.5, 0.29, 0.0)], sides=16, mat=LGREY)
    loft_y(bm, AXIS, [(12.8, 12.6, 0.29, 0.0), (13.8, 14.6, 0.31, 0.0), (15, 15.6, 0.33, 0.0),
                      (17.5, 15.6, 0.33, 0.0), (18.6, 14.8, 0.31, 0.0), (19.4, 13.6, 0.29, 0.0)], sides=16, mat=TAN)
    loft_y(bm, AXIS, [(19.2, 13.6, 0.29, 0.0), (21, 13.9, 0.3, 0.0)], sides=16, mat=BROWN)
    loft_y(bm, AXIS, [(20.8, 13.9, 0.3, 0.0), (27, 14.3, 0.31, 0.0), (32, 13.6, 0.3, 0.0),
                      (33.8, 11.5, 0.26, 0.0)], sides=16, mat=BARREL)
    loft_y(bm, AXIS, [(33.5, 11.2, 0.26, 0.0), (34.5, 9.4, 0.24, 0.0), (36, 8.8, 0.22, 0.0),
                      (37.6, 7.8, 0.2, 0.0)], sides=14, mat=PINK)
    loft_y(bm, AXIS, [(37.4, 7.6, 0.2, 0.0), (40, 7.2, 0.18, 0.0), (44, 7.0, 0.17, 0.0), (47, 6.6, 0.15, 0.0)],
           sides=12, mat=GREY)
    loft_y(bm, AXIS, [(46.8, 6.8, 0.15, 0.0), (48, 6.2, 0.14, 0.0), (53, 6.2, 0.14, 0.0), (54.5, 7.5, 0.15, 0.0)],
           sides=12, mat=BLACK)
    loft_y(bm, AXIS, [(54.2, 8.5, 0.16, 0.0), (55.5, 10.6, 0.2, 0.0), (58, 11.6, 0.22, 0.0), (64, 11.6, 0.22, 0.0),
                      (66.5, 10.8, 0.2, 0.0)], sides=14, mat=RED)
    loft_y(bm, AXIS, [(66.3, 10.9, 0.2, 0.0), (68, 10.2, 0.19, 0.0), (70, 9.4, 0.17, 0.0), (72.5, 7.0, 0.14, 0.0)],
           sides=14, mat=BLACK)
    loft_y(bm, AXIS, [(72.3, 6.8, 0.14, 0.0), (74, 8.6, 0.16, 0.0), (76.5, 10.8, 0.19, 0.0), (80, 11.2, 0.19, 0.0),
                      (81.5, 10.8, 0.185, 0.0)], sides=14, mat=GREY)
    loft_y(bm, AXIS, [(81.3, 10.9, 0.185, 0.0), (84, 9.8, 0.17, 0.0), (87, 8.0, 0.14, 0.0), (89.5, 5.5, 0.1, 0.0),
                      (91.3, 0.0, 0.0, 0.0)], sides=14, mat=DTAN)
    # Red stripe down the stinger's front and a grey stud at its top.
    loft_y(bm, AXIS, [(77, 0.0, 0.0, 0.17), (78, 1.9, 0.05, 0.17), (84, 1.9, 0.05, 0.15), (88, 1.7, 0.045, 0.11),
                      (90.6, 0.0, 0.0, 0.07)], sides=8, mat=RED)
    ellipsoid(bm, AXIS, 74.8, 0.15, 1.6, 1.4, 0.05, mat=LGREY, segments=10, rings=5)
    # Black spine between the pod's red panels, and dark brown seams across them.
    loft_y(bm, AXIS, [(54, 0.0, 0.0, 0.2), (55, 1.6, 0.04, 0.21), (65.5, 1.6, 0.04, 0.21), (67, 0.0, 0.0, 0.2)],
           sides=8, mat=BLACK)
    for side in (-1, 1):
        sweep(bm, [(AXIS + side * 6.5, 57.2, 0.2, 0.7, 0.025), (AXIS + side * 7.5, 64.5, 0.18, 0.7, 0.025)],
              sides=6, mat=BROWN)

    # Light tan crest up the dome from the brim, with a pink light at its top, and another pink
    # light under the brim.
    loft_y(bm, AXIS, [(9.4, 0.0, 0.0, 0.22), (10.2, 3.0, 0.05, 0.24), (12.5, 3.4, 0.05, 0.28),
                      (14.5, 3.6, 0.05, 0.31)], sides=8, mat=LTAN)
    ellipsoid(bm, AXIS - 1, 10.2, 0.25, 1.4, 1.2, 0.04, mat=LIGHT, segments=8, rings=4)
    ellipsoid(bm, AXIS + 0.5, 21.2, 0.3, 1.2, 1.4, 0.03, mat=LIGHT, segments=8, rings=4)

    # Barrel details: bright grey bars down its sides and a ladder down its middle.
    for side in (-1, 1):
        loft_y(bm, AXIS + side * 8.5, [(21.5, 1.6, 0.04, 0.235), (33, 1.6, 0.04, 0.235)], sides=8, mat=LGREY)
        loft_y(bm, AXIS + side * 2.5, [(21.8, 0.9, 0.03, 0.3), (33.5, 0.9, 0.03, 0.29)], sides=6, mat=LGREY)
    for r0, r1 in ((26, 27), (30, 32)):
        box(bm, 58, r0, 62, r1, 0.27, 0.33, mat=LGREY)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = bmesh.new()
    build_left(bm)
    mirror_all(bm, AXIS)
    build_centre(bm)
    return to_object(NAME, bm, mats, coll), mats, coll


def eye_materials(sprite, mats):
    """`mats` plus the eye's animated colours (their own names, so the other pieces keep theirs)."""
    pal = lambda i, part, **kw: common.palette_material(sprite, i, f"{TAG}-{part}", **kw)  # noqa: E731
    return mats + [
        pal(70, "slit", emission_strength=1.5),  # 17 red slit as the shutter cracks (frame 3)
        pal(74, "eye", emission_strength=1.5, frames={5: 71}),  # 18 red eye, dimmer on frame 5
        pal(122, "spark", emission_strength=3.0),  # 19 orange glint (frame 7)
        pal(77, "glint", emission_strength=2.0),  # 20 pink glint (frame 39)
        pal(116, "glow", emission_strength=4.0, frames={43: 117, 45: 119}),  # 21 glow, heating up
        pal(121, "hot", emission_strength=5.0, frames={43: 123, 45: 125}),  # 22 its hot core
        pal(127, "white", emission_strength=6.0),  # 23 white-hot centre
    ]


SLIT, EYE_A, SPARK, GLINT, GLOW_A, HOT_A, WHITE = range(17, 24)


def eye_frame(frame, bm):
    """The eye in its socket (columns 56-64, rows 47-54) on one sprite frame."""
    if frame == 1:  # shutter closed
        ellipsoid(bm, AXIS, 50.6, 0.12, 3.9, 3.4, 0.1, mat=SHUTTER)
    elif frame == 3:  # shutter cracked down the middle on a thin red slit (rows 49-53)
        for side in (-1, 1):
            ellipsoid(bm, AXIS + side * 2.5, 50.6, 0.12, 1.8, 3.4, 0.1, mat=SHUTTER, segments=12, rings=8)
        ellipsoid(bm, AXIS, 51.0, 0.1, 0.55, 2.5, 0.08, mat=SLIT, segments=8, rings=6)
    elif frame in (5, 7):  # a narrow red eye (columns 59-61) between the shutter's halves
        ellipsoid(bm, AXIS, 50.6, 0.11, 1.6, 2.1, 0.09, mat=EYE_A, segments=12, rings=6)
        gap = 3.5 if frame == 5 else 4.0
        for side in (-1, 1):
            ellipsoid(bm, AXIS + side * gap, 50.6, 0.11, 1.0 if frame == 5 else 0.8, 3.4, 0.08, mat=SHUTTER,
                      segments=10, rings=6)
        if frame == 7:
            ellipsoid(bm, AXIS - 1, 50.1, 0.19, 0.55, 0.55, 0.03, mat=SPARK, segments=8, rings=4)
    elif frame == 39:  # shutter gone: the eye is five pixels wide (columns 58-62)
        ellipsoid(bm, AXIS, 50.6, 0.11, 2.6, 2.1, 0.09, mat=EYE_A)
        ellipsoid(bm, AXIS - 1, 50.1, 0.19, 0.6, 0.6, 0.03, mat=GLINT, segments=8, rings=4)
    else:  # glowing: seven pixels wide, four rows tall on frame 41 and six on 43 and 45
        ry = 2.1 if frame == 41 else 3.0
        ellipsoid(bm, AXIS, 50.6, 0.12, 3.6, ry, 0.1, mat=GLOW_A)
        ellipsoid(bm, AXIS - 0.4, 50.4, 0.17, 1.9 if frame == 41 else 2.2, ry * 0.65, 0.07, mat=HOT_A,
                  segments=12, rings=6)


def build_eye(frames, mats, coll, offset):
    """One model's eye: a part per frame (shown only on it), moved by `offset` (the eye piece's
    centre) into the piece's own coordinates. Frames 43 and 45 share their shape (their colours
    differ), and the glowing model has a white-hot centre on every frame."""
    groups = {}
    for f in frames:
        groups.setdefault(45 if f == 43 else f, []).append(f)
    parts = []
    for key, tagged in groups.items():
        bm = bmesh.new()
        eye_frame(key, bm)
        bmesh.ops.translate(bm, vec=(-offset[0], -offset[1], 0), verts=bm.verts)
        parts.append(common.frame_part(to_object(f"newsh4-eye-{key}", bm, mats, coll), tagged))
    if 41 in frames:
        bm = bmesh.new()
        ellipsoid(bm, AXIS - 1, 50.1, 0.25, 0.7, 0.6, 0.03, mat=WHITE, segments=8, rings=4)
        bmesh.ops.translate(bm, vec=(-offset[0], -offset[1], 0), verts=bm.verts)
        parts.append(to_object("newsh4-eye-white", bm, mats, coll))
    return parts


def main():
    sprite = merged_sprite(ROOT, PIECES)
    obj, mats, coll = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    eye_centre = next((cx / 12, -cy / 12) for name, cx, cy in layout if name == EYE)
    eye_mats = eye_materials(sprite, mats)
    eyes = {}
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        if name != EYE:
            common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
            continue
        for model, frames in EYE_MODELS:
            eyes[model] = build_eye(frames, eye_mats, coll, eye_centre)
            sprites = [dict(s, frames=[f for f in s["frames"] if f in frames]) for s in data["sprites"]]
            sprites = [s for s in sprites if s["frames"]]
            common.export_sprite_model(ROOT, [pieces[name]] + eyes[model], f"enemies/{model}", sprites)
    if "--frames" in sys.argv:  # every frame of each eye model beside its sprite: <dir>/<model>.png
        out_dir = Path(sys.argv[sys.argv.index("--frames") + 1])
        data = common.load_sprite(ROOT, EYE)
        for model, frames in EYE_MODELS:
            sub = dict(data, frames=[f for f in data["frames"] if f["index"] in frames])
            common.render_frame_previews([pieces[EYE]] + eyes[model], out_dir / f"{model}.png", sub, ROOT)
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        tmp = Path(tempfile.mkdtemp())
        # The whole machine with the glowing eye (as the layout shows it), placed in assembly space.
        whole_eye = build_eye([41, 43, 45], eye_mats, coll, (0.0, 0.0))
        ref = composite_png(ROOT, layout, tmp / "assembly.png", 120, 140)
        common.render_preview([obj] + whole_eye, str(out), ref, size=10, view_px=640, frame=45)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            if name == EYE:
                for model, frames in EYE_MODELS:
                    frame = next(f for f in data["frames"] if f["index"] == frames[-1])
                    img = ROOT / "reference" / "models" / name / frame["image"]
                    common.render_preview([pieces[name]] + eyes[model], str(out.parent / f"{model}.png"), img,
                                          size=2, frame=frames[-1])
                continue
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
