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

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from lib_b015 import (PX, box, composite_png, ellipsoid, loft_y, merged_sprite, mirror_all, plate,  # noqa: E402
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
# The eye sits in the raised socket: every eye part is built at its old height and lifted by this.
EYE_DZ = 0.40


def materials(sprite):
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    return [
        pal(8, metallic=0.1, roughness=0.35),  # 0 light grey pylons, neck, shoulders
        pal(10, metallic=0.1, roughness=0.3),  # 1 light grey dome, bars, hook
        pal(4, metallic=0.4, roughness=0.5),  # 2 dark grey hull
        pal(2, metallic=0.4, roughness=0.6),  # 3 black socket and pod underside
        pal(24, metallic=0.0, roughness=0.6),  # 4 gold wings, chevron, brim (the sprite's saturated mid gold)
        pal(22, metallic=0.0, roughness=0.45),  # 5 darker tan emblems
        pal(28, metallic=0.0, roughness=0.4),  # 6 bright gold ridges, crest, barrel and blades
        pal(165, metallic=0.3, roughness=0.6),  # 7 dark brown bands
        pal(72, metallic=0.15, roughness=0.35),  # 8 red panels and windows
        pal(76, metallic=0.15, roughness=0.4),  # 9 pink collar
        pal(167, metallic=0.25, roughness=0.45),  # 10 brown claws
        pal(79, emission_strength=2.5),  # 11 pink lights
        pal(9, metallic=0.75, roughness=0.25),  # 12 grey eye shutter
        pal(74, emission_strength=1.5),  # 13 red eye
        pal(123, emission_strength=4.0),  # 14 eye glow
        pal(126, emission_strength=6.0),  # 15 eye hot core
        pal(25, metallic=0.0, roughness=0.55),  # 16 gold barrel (lit a step brighter than the wings)
        pal(75, metallic=0.15, roughness=0.3),  # 17 lit red ribs on the pod
        pal(8, metallic=0.1, roughness=0.35),  # 18 grey hooks (the same material as the pylons)
        pal(7, metallic=0.1, roughness=0.4),  # 19 grey stinger dome
        pal(73, metallic=0.0, roughness=0.4),  # 20 bright red shoulder windows
        pal(164, metallic=0.0, roughness=0.55),  # 21 dark brown-orange lower band of the stinger
    ]


(GREY, LGREY, DGREY, BLACK, TAN, DTAN, LTAN, BROWN, RED, PINK, CLAW, LIGHT, SHUTTER, EYE_RED, GLOW,
 HOT, BARREL, RIB, HOOK, BALLG, WIN, DBROWN) = range(22)
N_MATS = 22


def bplate(bm, outline, z0, z1, mat=0, bevel=0.6, tilt=None):
    """`plate` with a bevelled top: the top face is inset by `bevel` px and the outer rim is
    `bevel` * 0.7 px lower, so the edges catch the light like the sprite's lit and dark rims."""
    bm.faces.ensure_lookup_table()
    n0 = len(bm.faces)
    drop = bevel * PX * 0.7
    plate(bm, outline, z0, z1 - drop, mat=mat, tilt=tilt)
    bm.faces.ensure_lookup_table()
    top = bm.faces[n0]
    top.normal_update()
    if top.normal.z < 0:
        top.normal_flip()
    bmesh.ops.inset_region(bm, faces=[top], thickness=bevel * PX, depth=drop, use_even_offset=True)


def surf(sections, row, dx=0.0):
    """The top of a loft_y (sections of (row, half_width_px, half_height, z)) at `row`, `dx` px off its
    axis: for placing details on it."""
    rows = [s[0] for s in sections]
    row = min(max(row, rows[0]), rows[-1])
    for a, b in zip(sections, sections[1:]):
        if a[0] <= row <= b[0]:
            t = (row - a[0]) / max(b[0] - a[0], 1e-6)
            hw, hh, z = (a[i] + (b[i] - a[i]) * t for i in (1, 2, 3))
            break
    if hw <= 0:
        return z
    u = min(1.0, abs(dx) / hw)
    return z + 0.98 * hh * math.sqrt(max(0.0, 1 - u * u))


def build_left(bm):
    """Everything off the centreline, on the left side (mirrored afterwards). Heights stack like
    the sprite's plates: wings about 3 px, the hull and arm roots 4 px, the chevron (body plate)
    and the shoulder blocks about 6 px, the grey pylons thinner plates (about 5 px), each with a
    bevelled top."""

    def wing_tilt(c, r):
        """The wings droop toward their tips (anhedral): lit on the left, shaded on the right."""
        return -0.14 * max(0.0, 34 - c) / 30

    # Big tan wing: a slanted plate from the tip (columns 5-14) to the body (column 34), with a
    # light ridge along its upper edge and a strut on to the barrel (rows 34-38).
    plate_outline = [(4.0, 19.8), (13, 23.3), (23, 28.8), (34, 33.3), (34, 48.5), (29.5, 52.7), (15, 38.7),
                     (5.0, 31.5), (4.6, 24.0)]
    bplate(bm, plate_outline, -0.04, 0.25, mat=TAN, bevel=0.7, tilt=wing_tilt)
    sweep(bm, [(4.8, 21.0, 0.24 + wing_tilt(5, 21), 1.0, 0.04), (13, 24.6, 0.24 + wing_tilt(13, 25), 1.2, 0.045),
               (23, 29.6, 0.24 + wing_tilt(23, 30), 1.2, 0.045), (33.5, 34.2, 0.24, 1.2, 0.045)], sides=6, mat=LTAN)
    sweep(bm, [(15.5, 38.9, wing_tilt(15, 38) + 0.2, 0.8, 0.04), (29.5, 51.6, 0.2, 0.8, 0.04)], sides=6, mat=DTAN)
    box(bm, 33, 34, 43, 38, 0.0, 0.3, mat=TAN)
    # Wingtip block: a red knob on the outside (columns 6-10), lit on top, and a grey block inside it.
    box(bm, 6, 26, 10, 36, -0.12, 0.2, mat=RED)
    sweep(bm, [(8.5, 25.4, 0.2, 0.0, 0.0), (8.5, 26.4, 0.2, 2.2, 0.24), (8.5, 30.5, 0.2, 2.6, 0.31),
               (8.3, 35.4, 0.2, 2.2, 0.24), (8.3, 36.5, 0.2, 0.0, 0.0)], sides=10, mat=RED)
    bplate(bm, [(10, 29), (15, 29), (15, 38), (10, 38)], -0.12, 0.44, mat=GREY, bevel=0.6)
    # Thin tan cable from the pylon's top round to the wing tip (rows 9-22).
    sweep(bm, [(20.5, 9.0, 0.38, 1.4, 0.06), (16, 9.2, 0.37, 1.4, 0.06), (12.5, 10.5, 0.35, 1.4, 0.06),
               (9.8, 12.8, 0.33, 1.4, 0.06), (7.5, 16, 0.3, 1.4, 0.06), (5.6, 19.5, 0.22, 1.5, 0.06),
               (5.2, 22.5, 0.16, 1.5, 0.06)], sides=6, mat=TAN)

    # Grey pylon behind the tower (columns 19-46, rows 3-35): a raised slanted block with a bevelled
    # top, a bright outer post, a tan emblem and a dark brown band, and a bright bar down to the
    # barrel's side.
    # Its inner edge stops at column 43 (the sprite's dark gap beside the barrel is cut in after the
    # mirror, see build_recesses).
    bplate(bm, [(20.5, 2.5), (25, 2.5), (34, 7), (43.5, 11.5), (43.5, 18), (46.5, 18.5), (46.5, 21.5),
                (43, 22), (43, 31), (41, 35.5), (36.5, 34), (36, 30), (30, 22), (22.5, 19), (20, 17.5),
                (20, 7)], -0.1, 0.4, mat=GREY, bevel=1.0)
    bplate(bm, [(20.5, 3.2), (24.5, 3.2), (25.5, 4), (25.5, 18.5), (21.5, 18.5), (20.5, 17)], 0.25, 0.46,
           mat=LGREY, bevel=0.5)
    plate(bm, [(27, 9.5), (31, 8), (36, 10.5), (36, 12.5), (31, 11), (29.5, 12), (29.5, 15.5), (27, 15.5)],
          0.3, 0.408, mat=BROWN)
    plate(bm, [(26.5, 17.5), (45, 17.5), (46, 20.5), (28, 20.5)], 0.3, 0.415, mat=BROWN)
    box(bm, 37, 22, 38, 34, 0.25, 0.45, mat=LGREY)

    # Arm root from the hull down to the shoulder (columns 28-40, rows 46-58).
    bplate(bm, [(28, 52), (33, 46.5), (41, 45.5), (41, 53), (36, 58.5), (28, 58.5)], -0.12, 0.34, mat=GREY)

    # Tan chevron from the middle out and down to the shoulder, with a light outer edge: the body
    # plate, above the wings.
    outer = [(58.5, 43.5), (47.5, 43.5), (45.5, 46), (43.5, 48), (41, 50), (39.5, 52), (37.5, 54), (35, 56),
             (33.5, 58), (30.5, 59), (31, 61), (32.5, 62), (34.5, 64), (35, 66), (35.5, 68), (36, 71),
             (37, 72.5)]
    inner = [(42.0, 72.5), (42.6, 68.5), (43.2, 64.5), (44.2, 62.5), (44.5, 58), (43.5, 56.5), (45, 54.5),
             (47, 52.5), (49, 50.5), (55, 49.5), (58.5, 48.5)]
    bplate(bm, outer + inner, 0.2, 0.58, mat=TAN, bevel=0.7)
    sweep(bm, [(c + 0.6, r + 0.6, 0.555, 0.7, 0.03) for c, r in outer[1:9]], sides=6, mat=LTAN)
    # Light tan blade hanging below the shoulder (columns 24-28, rows 68-78), standing over the
    # shoulder's lower edge (about 7 px).
    bplate(bm, [(23.5, 68), (29.5, 68), (28.5, 73), (25.5, 78.5), (23.5, 78.5)], -0.04, 0.56, mat=TAN,
           bevel=0.6)

    # Shoulder block (columns 14-33, rows 57-69): a 6 px box whose red window is set 1 px into its
    # top inside a dark frame (the top is built as a rim round the window). Under it a smaller
    # block with a red triangular window, then the grey wrist.
    top, rim = 0.5, 0.42
    plate(bm, [(14, 60.5), (16, 59), (18, 58), (23, 58), (25, 59), (35, 59), (35, 70), (14, 70)],
          -0.12, rim, mat=GREY)
    plate(bm, [(14, 60.5), (16, 59), (18, 58), (23, 58), (25, 59), (35, 59), (35, 62), (14, 62)], rim, top,
          mat=GREY)
    box(bm, 22, 62, 34, 69, rim, top, mat=GREY)
    box(bm, 14, 62, 15, 69, rim, top, mat=GREY)
    box(bm, 16, 68, 21, 69, rim, top, mat=GREY)
    plate(bm, [(18, 58), (23, 58), (23.5, 60.5), (17.5, 60.5)], top, top + 0.06, mat=LGREY)
    box(bm, 16, 62, 21, 67, rim - 0.02, top - 0.03, mat=BLACK)
    plate(bm, [(16.05, 62.05), (21.95, 62.05), (21.95, 67.95), (16.05, 67.95)], rim, top - 0.01, mat=WIN)
    plate(bm, [(14, 69.9), (24, 69.9), (24, 70.9), (14, 70.9)], -0.12, 0.3, mat=BLACK)
    bplate(bm, [(15, 70.8), (24, 70.8), (24, 77), (15, 77)], -0.12, 0.42, mat=GREY, bevel=0.5)
    box(bm, 15, 70.8, 23, 70.8, 0.4, 0.45, mat=LGREY)
    # The grey arm-root strip under the shoulder's inner half (columns 24-35, rows 70-71).
    bplate(bm, [(24, 69.5), (36.5, 69.5), (36.5, 71), (32, 72), (29, 72.5), (24, 72.5)], -0.12, 0.3, mat=GREY,
           bevel=0.4)
    plate(bm, [(17.6, 72.1), (22.9, 72.1), (22.9, 73.9), (18.3, 77.5)], 0.39, 0.425, mat=BLACK)
    plate(bm, [(18, 72.5), (22.5, 72.5), (22.5, 73.5), (18.5, 77)], 0.39, 0.44, mat=WIN)
    bplate(bm, [(16, 77), (24, 77), (24, 82), (22.5, 84.5), (16.5, 84.5)], -0.08, 0.32, mat=GREY, bevel=0.5)

    # Brown claw curving in to its tip (rows 84-106): a round tube, as tall as it is wide, rooted in
    # the wrist and tapering to the point; and the thin grey hook inside it, rooted in the blade's tip.
    sweep(bm, [(19.8, 81.5, 0.25, 4.0, 0.44), (19.5, 84.5, 0.25, 4.5, 0.47), (19.5, 90, 0.26, 4.5, 0.47),
               (21.0, 96, 0.25, 4.3, 0.46), (24.6, 100.5, 0.22, 3.8, 0.41), (30, 104, 0.17, 3.1, 0.32),
               (34.4, 105.6, 0.1, 2.0, 0.19), (38.4, 106.5, 0.05, 0.0, 0.0)], sides=10, mat=CLAW)
    sweep(bm, [(27.0, 73.0, 0.18, 2.0, 0.15), (27.6, 75.5, 0.24, 2.5, 0.24), (28.4, 78.2, 0.3, 2.8, 0.3),
               (29.6, 81.2, 0.3, 2.8, 0.3),
               (31.9, 84.5, 0.28, 2.6, 0.3), (35.8, 86.8, 0.24, 2.2, 0.26), (40.8, 88.3, 0.18, 1.7, 0.19),
               (45.0, 89.0, 0.12, 1.1, 0.12), (48.0, 89.2, 0.08, 0.0, 0.0)], sides=10, mat=HOOK)


# The tower down the middle: (row, half width px, half height, z) sections of each loft. A round
# column of round parts: the dome (about 6 px above the brim's base), the brim, the barrel lying
# along the body (about 10 px above the hull plane), the pink collar on its front, the neck under
# the chevron, the eye socket, the ribbed red pod (a 12 px barrel) and the stinger (a dome 23 px
# wide and about 13 px tall standing on the plane), as the sprite shades them.
Z_TOWER = 0.25
DOME = [(5.4, 0.0, 0.0, Z_TOWER), (5.7, 4.6, 0.3, Z_TOWER), (6.3, 6.4, 0.45, Z_TOWER), (7.2, 7.9, 0.56, Z_TOWER),
        (8.2, 8.9, 0.64, Z_TOWER), (9.4, 9.7, 0.7, Z_TOWER), (11.0, 10.4, 0.74, Z_TOWER), (13.4, 11.0, 0.76, Z_TOWER)]
BRIM = [(12.8, 10.4, 0.68, Z_TOWER), (14, 11.8, 0.72, Z_TOWER), (15.5, 13.6, 0.75, Z_TOWER),
        (17.5, 15.2, 0.75, Z_TOWER), (18.6, 15.0, 0.73, Z_TOWER), (19.4, 13.8, 0.68, Z_TOWER)]
BAND = [(19.2, 13.7, 0.66, Z_TOWER), (21, 13.9, 0.66, Z_TOWER)]
BARREL_S = [(20.8, 13.9, 0.66, Z_TOWER), (27, 14.3, 0.68, Z_TOWER), (33, 14.0, 0.66, Z_TOWER),
            (36.5, 13.2, 0.6, Z_TOWER), (38.8, 11.0, 0.46, Z_TOWER)]
COLLAR = [(33.4, 5.0, 0.62, Z_TOWER), (34.5, 6.2, 0.72, Z_TOWER), (36.5, 6.2, 0.7, Z_TOWER),
          (38.2, 5.4, 0.6, Z_TOWER)]
NECK = [(37.4, 7.4, 0.52, Z_TOWER), (40, 7.2, 0.48, Z_TOWER), (42.5, 7.0, 0.38, Z_TOWER), (44, 6.8, 0.26, Z_TOWER),
        (47, 6.6, 0.22, Z_TOWER)]
SOCKET = [(46.8, 6.8, 0.22, Z_TOWER), (48, 6.4, 0.3, Z_TOWER), (53, 6.4, 0.3, Z_TOWER), (54.5, 7.5, 0.32, Z_TOWER)]
Z_POD = 0.22
POD = [(54.0, 6.0, 0.4, Z_POD), (55.2, 9.0, 0.6, Z_POD), (57, 11.0, 0.72, Z_POD), (59, 11.5, 0.76, Z_POD),
       (64, 11.5, 0.76, Z_POD), (66.5, 10.8, 0.7, Z_POD)]
UNDER = [(66.3, 10.9, 0.7, Z_POD), (68, 10.2, 0.6, Z_POD), (70, 9.4, 0.48, Z_POD), (72.8, 7.6, 0.34, Z_POD),
         (75.6, 6.4, 0.26, Z_POD)]
# The stinger: a half-ellipsoid centred on the body plane (its lower half is cut off at BALL_FLOOR),
# about 13 px tall.
Z_BALL = -0.06
BALL_TOP = [(72.3, 3.5, 0.36, Z_BALL), (74, 4.6, 0.54, Z_BALL), (75.8, 6.8, 0.74, Z_BALL), (76.7, 10.9, 0.96, Z_BALL),
            (78.0, 11.7, 1.06, Z_BALL), (81.5, 11.7, 1.1, Z_BALL), (83.6, 11.2, 1.05, Z_BALL), (85.5, 10.3, 0.97, Z_BALL)]
BALL_BOTTOM = [(85.3, 10.4, 0.98, Z_BALL), (86.5, 9.8, 0.92, Z_BALL), (87.6, 8.8, 0.84, Z_BALL),
               (88.6, 7.8, 0.75, Z_BALL), (89.6, 6.8, 0.63, Z_BALL), (90.5, 5.7, 0.5, Z_BALL), (91.2, 4.6, 0.36, Z_BALL),
               (91.7, 2.6, 0.18, Z_BALL), (91.9, 0.0, 0.0, Z_BALL)]
BALL = BALL_TOP + BALL_BOTTOM[1:]
BALL_FLOOR = -0.08
CENTRE_FLOOR = -0.1


def on(sections, rows_hw_hh, dx=0.0, sink=0.02):
    """Sections for a thin loft lying on another loft's top: (row, half width, half height)."""
    return [(r, w, h, surf(sections, r, dx) - sink) for r, w, h in rows_hw_hh]


def build_centre(bm):
    """The tower down the middle and the hull under everything (symmetric about column 60). Every
    loft here is centred on its z, so its lower half is cut flat at CENTRE_FLOOR afterwards: the pod,
    its black underside and the hull sit on the body plane instead of hanging below it."""
    n_start = len(bm.verts)
    # Dark grey hull under the wings, chevron and shoulders, out to the dark gaps beside the pod.
    loft_y(bm, AXIS, [(16.5, 0.0, 0.0, 0.0), (18, 13, 0.24, 0.0), (22, 21, 0.3, 0.0), (30, 26.5, 0.36, 0.0),
                      (42, 27.5, 0.38, 0.0), (50, 25.5, 0.38, 0.0), (56, 20.5, 0.36, 0.0), (62.4, 17.4, 0.33, 0.0),
                      (63.3, 12.0, 0.29, 0.0), (65, 11.0, 0.28, 0.0), (68.5, 0.0, 0.0, 0.0)], sides=14, mat=DGREY)

    # Tower: grey dome, tan brim, dark band under it, tan barrel, pink collar, grey neck, black
    # eye socket, red pod with a black underside, grey and tan stinger ball.
    loft_y(bm, AXIS, DOME, sides=16, mat=GREY)
    loft_y(bm, AXIS, BRIM, sides=16, mat=TAN)
    loft_y(bm, AXIS, BAND, sides=16, mat=BROWN)
    loft_y(bm, AXIS, BARREL_S, sides=16, mat=BARREL)
    loft_y(bm, AXIS, COLLAR, sides=14, mat=PINK)
    loft_y(bm, AXIS, NECK, sides=12, mat=GREY)
    loft_y(bm, AXIS, SOCKET, sides=12, mat=BLACK)
    loft_y(bm, AXIS, POD, sides=16, mat=RED)
    loft_y(bm, AXIS, UNDER, sides=16, mat=BLACK)
    # The stinger is a dome standing on the body plane (its underside cut flat at BALL_FLOOR), not a
    # ball hanging under it: grey upper half, near-black lower band.
    n0 = len(bm.verts)
    loft_y(bm, AXIS, BALL_TOP, sides=16, mat=BALLG)
    loft_y(bm, AXIS, BALL_BOTTOM, sides=16, mat=DBROWN)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[n0:]:
        v.co.z = max(v.co.z, BALL_FLOOR)
    # The red stripe wrapped down the stinger's front (one raised strip), and a grey stud at its top.
    loft_y(bm, AXIS, on(BALL, [(77.5, 0.0, 0.0), (78.5, 2.0, 0.09), (84, 2.0, 0.09), (88, 1.8, 0.08),
                               (90.8, 0.0, 0.0)], sink=0.03), sides=8, mat=RED)
    ellipsoid(bm, AXIS, 75.4, surf(BALL, 75.4) - 0.02, 1.6, 1.4, 0.08, mat=LGREY, segments=10, rings=5)
    # The small dark horns at the stinger's upper corners (columns 49-51 and 69-71, rows 75-77).
    for side in (-1, 1):
        sweep(bm, [(AXIS + side * 9.6, 78.2, 0.3, 1.1, 0.12), (AXIS + side * 10.8, 75.8, 0.27, 0.7, 0.08),
                   (AXIS + side * 11.1, 74.6, 0.25, 0.0, 0.0)], sides=6, mat=DGREY)
    # The pod's dark spine down the middle, raised ribs either side (lit inner ribs, red outer ones)
    # and dark brown grooves between them, all following its round top.
    loft_y(bm, AXIS, on(POD, [(54.2, 0.0, 0.0), (55, 2.0, 0.06), (65.5, 2.0, 0.06), (66.8, 0.0, 0.0)],
                        sink=0.02), sides=8, mat=BLACK)
    for side in (-1, 1):
        for dx, w, mat in ((4.2, 0.9, RIB), (9.0, 0.9, RED)):
            rows = [(55.6 if dx < 6 else 57.2, 0.0, 0.0), (56.4 if dx < 6 else 58, w, 0.05), (62, w, 0.05),
                    (65.6, w, 0.05), (66.3, 0.0, 0.0)]
            loft_y(bm, AXIS + side * dx, on(POD, rows, dx, sink=0.0), sides=6, mat=mat)
        sweep(bm, [(AXIS + side * 6.5, 57.6, surf(POD, 57.6, 6.5), 0.7, 0.03),
                   (AXIS + side * 7.0, 64.5, surf(POD, 64.5, 7.0), 0.7, 0.03)], sides=6, mat=BROWN)

    # Light tan crest up the dome from the brim, with a pink light at its top, and another pink
    # light under the brim.
    loft_y(bm, AXIS, on(DOME, [(9.4, 0.0, 0.0), (10.2, 3.0, 0.05), (12.5, 3.4, 0.05)], sink=0.03)
           + on(BRIM, [(14.5, 3.6, 0.05)], sink=0.03), sides=8, mat=LTAN)
    ellipsoid(bm, AXIS - 1, 10.2, surf(DOME, 10.2, 1) + 0.0, 1.4, 1.2, 0.05, mat=LIGHT, segments=8, rings=4)
    ellipsoid(bm, AXIS + 0.5, 21.2, surf(BARREL_S, 21.2, 0.5) - 0.01, 1.2, 1.4, 0.05, mat=LIGHT, segments=8,
              rings=4)

    # Barrel details: bright grey bars down its sides and a ladder down its middle.
    for side in (-1, 1):
        loft_y(bm, AXIS + side * 8.5, on(BARREL_S, [(21.5, 1.6, 0.05), (33, 1.6, 0.05)], 8.5), sides=8, mat=LGREY)
        loft_y(bm, AXIS + side * 2.5, on(BARREL_S, [(21.8, 0.9, 0.04), (33.5, 0.9, 0.04)], 2.5), sides=6, mat=LGREY)
    for r0, r1 in ((26, 27), (30, 32)):
        zt = surf(BARREL_S, (r0 + r1) / 2, 2.5)
        box(bm, 58, r0, 62, r1, zt - 0.04, zt + 0.04, mat=LGREY)
    bm.verts.ensure_lookup_table()
    for v in bm.verts[n_start:]:
        v.co.z = max(v.co.z, CENTRE_FLOOR)


def build_recesses(bm):
    """The parts that aren't mirror images (built after mirror_all, in sprite columns): the sprite is
    lit from the upper left, so the gaps right of the barrel and of the neck are near-black and the
    right red panel starts further out. The gaps are low floors, 3-4 px under the pylons and the
    neck around them."""
    # Dark gap between the barrel and each pylon (left: dark brown, right: black, r8/r9).
    plate(bm, [(43, 21.5), (47, 21.5), (47, 36.5), (43, 36.5)], 0.1, 0.32, mat=BROWN)
    plate(bm, [(73.5, 17.5), (78, 17.5), (78, 21.5), (81, 21.5), (81, 36.5), (73.5, 36.5)], 0.1, 0.32, mat=BLACK)
    # Black pit right of the neck (r11, columns 66-73, rows 37-43), and a smaller one on the left.
    plate(bm, [(66.5, 36.5), (74, 36.5), (74, 41), (73, 44), (66.5, 44)], 0.1, 0.38, mat=BLACK)
    plate(bm, [(50, 36.5), (54, 36.5), (54, 40.5), (50, 40.5)], 0.1, 0.38, mat=BLACK)
    # Red panels above the chevron (rows 39-43): the left one reaches in to column 53, the right one
    # only to column 74 (with a strip up its outer side, rows 35-39).
    bplate(bm, [(38.5, 39.5), (45, 39.5), (54, 41.5), (54, 44), (38.5, 44)], 0.1, 0.46, mat=RED, bevel=0.5)
    bplate(bm, [(74, 41.5), (78, 39.5), (78, 34.5), (80, 34.5), (80, 39.5), (83, 39.5), (83, 44), (74, 44)],
           0.1, 0.46, mat=RED, bevel=0.5)


def build(sprite):
    coll = common.reset_collection(NAME)
    mats = materials(sprite)
    bm = bmesh.new()
    build_left(bm)
    mirror_all(bm, AXIS)
    build_recesses(bm)
    build_centre(bm)
    return to_object(NAME, bm, mats, coll), mats, coll


def eye_materials(sprite, mats):
    """`mats` plus the eye's animated colours (their own names, so the other pieces keep theirs)."""
    pal = lambda i, part, **kw: common.palette_material(sprite, i, f"{TAG}-{part}", **kw)  # noqa: E731
    return mats + [
        pal(70, "slit", emission_strength=1.5),  # red slit as the shutter cracks (frame 3)
        pal(74, "eye", emission_strength=1.5, frames={5: 71}),  # red eye, dimmer on frame 5
        pal(122, "spark", emission_strength=3.0),  # orange glint (frame 7)
        pal(77, "glint", emission_strength=2.0),  # pink glint (frame 39)
        # The glow heats up over frames 41, 43, 45; its base colour is the hottest (frame 45, the one
        # the assembly layout shows), the cooler frames are listed.
        pal(119, "glow", emission_strength=4.0, frames={41: 116, 43: 117}),  # glow, heating up
        pal(125, "hot", emission_strength=5.0, frames={41: 121, 43: 123}),  # its hot core
        pal(127, "white", emission_strength=6.0),  # white-hot centre
    ]


SLIT, EYE_A, SPARK, GLINT, GLOW_A, HOT_A, WHITE = range(N_MATS, N_MATS + 7)


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
        ellipsoid(bm, AXIS - 0.4, 50.4, 0.17, 1.9 if frame == 41 else 2.8, ry * (0.65 if frame == 41 else 0.8), 0.08, mat=HOT_A,
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
        bmesh.ops.translate(bm, vec=(-offset[0], -offset[1], EYE_DZ), verts=bm.verts)
        parts.append(common.frame_part(to_object(f"newsh4-eye-{key}", bm, mats, coll), tagged))
    if 41 in frames:
        bm = bmesh.new()
        ellipsoid(bm, AXIS - 1, 50.1, 0.25, 0.7, 0.6, 0.03, mat=WHITE, segments=8, rings=4)
        bmesh.ops.translate(bm, vec=(-offset[0], -offset[1], EYE_DZ), verts=bm.verts)
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
