"""Blue fortress (newsho.shp, an assembly of 24 pieces): a 3D version of its sprites.

Seen in episode 3 (level 3.12). Twenty-four 2x2 ground enemies, 8 across and 3 down, make one
192 x 84 px structure, mirror symmetric about pixel column 95 (sprite.json `assemblyLayout`):
a grey head in the middle (a hip-roofed hood with vent ribs on top, blue claws at its sides and a
big dark glass orb under it, cradled by a curved grey collar), blue shoulder plates sloping down
either side of the orb, two small barrels and a knob below each shoulder, and a dark recessed
screen with a blue lid at the bottom. Out to the sides are two wings: a sloped blue armour plate
with a grey pillar and a turret (two barrels and a domed cap) on top, a big dark screen in a grey
frame below it, a round grey column beside the screen and, at the bottom, a grey block with a
chamfered corner, a slatted vent and two blue ribs.

The whole structure is built once in assembly coordinates (the wing parts on the left, then again
mirrored; parts the sprite shades differently on each side keep each side's palette index), then
cut into the 24 pieces with common.split_assembly. Every piece has one frame.

Run: blender --background --python assets/blender/enemies/assembly-newsho-79.py [-- --preview out.png]
(the preview is the whole structure; add --pieces to also render each piece as <piece>.png beside it).
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b093 as lib  # noqa: E402

NAME = "assembly-newsho-79"
ROOT = common.repo_root(__file__)
PIECES = ["newsho-1", "newsho-3", "newsho-5", "newsho-7", "newsho-9", "newsho-11", "newsho-13", "newsho-15",
          "newsho-39", "newsho-41", "newsho-43", "newsho-45", "newsho-47", "newsho-49", "newsho-51", "newsho-53",
          "newsho-77", "newsho-79", "newsho-81", "newsho-83", "newsho-85", "newsho-87", "newsho-89", "newsho-91"]
# Assembly pixel (0, 0) is the top-left corner of newsho-1 (screen cx 32 - 12, cy 27 - 14). The
# assembly is 192 x 84 px; its centre (screen 116, 55) is the Blender origin.
CX0, CY0 = 116, 55
F = lib.Frame(192, 84)
AXIS = 95.5  # mirror axis in pixel edges (the sprite mirrors about the centre of column 95)
AX = F.X(AXIS)
ARM_Z, ARM_H, ARM_POW = 0.56, 0.54, 0.8  # arm tube: centre height, half height (units), section power
ORB_Z = 1.06  # height of the orb dome above the well floor


def arm_z(path, row, u):
    """Height on the arm tube's surface at `row`, at u (-1..1) of its half width from the centre
    line (negative is the left side of the path seen from above). Follows lib.sweep's section."""
    for (c0, r0, z0, w0, h0), (c1, r1, z1, w1, h1) in zip(path, path[1:]):
        if r0 <= row <= r1:
            t = (row - r0) / (r1 - r0)
            z, h = z0 + t * (z1 - z0), h0 + t * (h1 - h0)
            break
    else:
        z, h = path[-1][2], path[-1][4]
    a = abs(u) ** (1 / ARM_POW)
    return z + h * max(0.0, 1 - a * a) ** (ARM_POW / 2)


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = "nsho79"
    pal = lambda i, t=tag, **kw: common.palette_material(sprite, i, t, **kw)  # noqa: E731
    mats = [
        pal(7, metallic=0.5, roughness=0.4),  # 0 grey hull (also the cut faces)
        pal(8, metallic=0.5, roughness=0.35),  # 1 light grey (lit slopes, dome)
        pal(4, metallic=0.45, roughness=0.5),  # 2 dark grey frames, shaded slopes
        pal(5, metallic=0.45, roughness=0.45),  # 3 mid grey faces
        pal(6, metallic=0.45, roughness=0.45),  # 4 grey trim
        pal(2, metallic=0.2, roughness=0.8),  # 5 near-black recesses and screens
        pal(3, metallic=0.3, roughness=0.6),  # 6 dark grey bevels
        pal(9, metallic=0.6, roughness=0.3),  # 7 bright grey ribs
        pal(11, metallic=0.7, roughness=0.25),  # 8 bright knobs
        pal(58, metallic=0.35, roughness=0.35),  # 9 light blue armour
        pal(57, metallic=0.35, roughness=0.4),  # 10 blue armour
        pal(56, metallic=0.35, roughness=0.45),  # 11 deeper blue faces
        pal(131, metallic=0.35, roughness=0.35),  # 12 lit blue bevels
        pal(133, metallic=0.4, roughness=0.3),  # 13 blue highlight edges
        pal(2, "nsho79orb", metallic=0.8, roughness=0.12),  # 14 dark glass orb
        pal(15, metallic=0.2, roughness=0.2),  # 15 glint on the orb
        pal(1, metallic=0.2, roughness=0.85),  # 16 the near-black well round the orb
        pal(100, metallic=0.35, roughness=0.5),  # 17 dark navy (shadowed blue edges)
        pal(101, metallic=0.35, roughness=0.5),  # 18 navy
    ]
    (GREY, LIGHT, DARKGREY, MID, TRIM, BLACK, BEVEL, RIB, KNOB,
     BLUE_L, BLUE, BLUE_D, BLUE_V, BLUE_W, ORB, GLINT, VOID, NAVY, NAVY_L) = range(19)
    bm = bmesh.new()

    # ---- the parts on each side (built on the left, then mirrored) ----
    for side in (0, 1):
        pick = lambda left, right: left if side == 0 else right  # noqa: E731
        start = len(bm.verts)

        # Dark floor under the middle (shows in the jaws and the barrel bay).
        lib.prism(bm, F, [(66, 20), (AXIS, 20), (AXIS, 84), (61.5, 84), (61.5, 77.5), (57, 77.5),
                          (58.5, 75), (58.5, 22)], 0.0, 0.04, VOID)

        # Wing armour plate: top rows 22-36, a front face down to row 43 and a bevelled left end.
        plate_low = [(33.5, 21), (52, 21), (52, 43), (5.5, 43), (5.5, 37.5), (14, 28.4)]
        plate_top = [(34.5, 22), (52, 22), (52, 36.5), (10, 36.5), (9.5, 36), (16, 29.4)]
        plate_sides = pick({2: BLUE_D, 3: BLUE_V, 4: BLUE_V, 5: BLUE_W}, {2: BLUE_D, 3: NAVY_L, 4: NAVY_L, 5: BLUE_D})
        plate_ends = pick(BLUE_V, NAVY)
        lib.stack(bm, F, [(plate_low, 0.0), (plate_low, 0.40), (plate_top, 0.58)], top_mat=BLUE_L,
                  side_mat=lambda k, i: plate_sides.get(i, BLUE) if k == 1 else (plate_ends if i in (3, 4, 5) else BLUE_D))

        # Grey pillar on the plate (columns 41-47) with a rounded rib across it.
        pillar_sides = pick({1: BEVEL, 2: DARKGREY, 3: RIB}, {1: RIB, 2: DARKGREY, 3: NAVY_L})
        lib.stack(bm, F, [([(40.5, 21), (48.5, 21), (48.5, 38.5), (40.5, 38.5)], 0.40),
                          ([(41.5, 21), (47.5, 21), (47.5, 37), (41.5, 37)], 0.76)],
                  top_mat=GREY, side_mat=lambda k, i: pillar_sides.get(i, MID))
        lib.sweep(bm, F, [(41.6, 26, 0.76, 3.5, 0.05), (47.4, 26, 0.76, 3.5, 0.05)], sides=8, mat=RIB)

        # Grey hull between the plate and the shoulder (columns 52-69).
        body_low = [(52, 20.5), (70, 20.5), (70, 29), (58.5, 29.5), (58.5, 43), (52, 43)]
        body_top = [(52, 21), (69.5, 21), (69.5, 28.8), (57.5, 29.3), (57.5, 37), (52, 37)]
        lib.stack(bm, F, [(body_low, 0.0), (body_low, 0.30), (body_top, 0.42)], top_mat=GREY,
                  side_mat=lambda k, i: MID if i == 4 else GREY)

        # Turret on top of the wing: a block, a domed cap and two short barrels with bright ends.
        t_low = [(43, 11), (60, 11), (60, 21), (43, 21)]
        t_top = [(45, 11.5), (58.5, 11.5), (58.5, 19.8), (45, 19.8)]
        lib.stack(bm, F, [(t_low, 0.0), (t_low, 0.62), (t_top, 0.68)], top_mat=DARKGREY,
                  side_mat=lambda k, i: BEVEL if (k, i) == (1, 2) else MID)
        lib.ellipsoid(bm, F, 50.5, 11.6, 0.66, 5.0, 3.2, 0.16, mat=LIGHT, segments=12, rings=6, upper=True)
        for c in (50.5, 55.0):
            lib.sweep(bm, F, [(c, 14.6, 0.74, 0.0, 0.0), (c, 15.2, 0.74, 2.0, 0.09), (c, 19.9, 0.74, 2.2, 0.10)],
                      sides=8, mat=GREY)
            lib.ellipsoid(bm, F, c, 15.3, 0.76, 1.3, 1.1, 0.06, mat=KNOB, segments=8, rings=4)

        # A small bracket behind the plate (columns 31-41, rows 16-23).
        lib.box(bm, F, 31, 16, 42, 21, 0.0, 0.30, BEVEL)
        lib.box(bm, F, 27, 20.5, 33, 23.5, 0.0, 0.22, BEVEL)
        lib.sweep(bm, F, [(31.5, 18.5, 0.33, 1.6, 0.05), (42, 18.5, 0.33, 1.6, 0.05)], sides=6, mat=TRIM)
        lib.box(bm, F, 32.5, 17.5, 35, 22.5, 0.0, 0.40, LIGHT, side_mat=MID)

        # Round grey column beside the screen (column 56, rows 38-66).
        lib.sweep(bm, F, [(56.5, 37.5, 0.16, 2.8, 0.14), (56.5, 66.5, 0.16, 2.8, 0.14)], sides=10, mat=MID)

        # The big screen: a block with a bevelled left side, a grey frame and a dark face.
        # One solid: the bevelled outside up to the frame (0.36), the frame's top, then the inner
        # walls down to the dark face (0.14), sunk ~2.6 px.
        s_low = [(5.5, 43), (54, 43), (54, 64.5), (5.5, 64.5)]
        s_top = [(9.5, 43), (54, 43), (54, 64.5), (9.5, 64.5)]
        s_in = [(12, 45), (52, 45), (52, 62), (12, 62)]
        lib.stack(bm, F, [(s_low, 0.0), (s_top, 0.36), (s_in, 0.36), (s_in, 0.14)], top_mat=BLACK,
                  side_mat=lambda k, i: ((TRIM if i == 3 else DARKGREY) if k == 0 else
                                         (GREY if (k, i) == (1, 0) else DARKGREY)))
        # The stepped shape drawn on the screen, as low ridges.
        for c0, r0, c1, r1 in ((13, 47, 47, 47.7), (13, 47.7, 13.7, 60), (19, 50, 42, 50.7), (14, 53, 19, 53.7),
                               (19, 50, 19.7, 53.7), (41.3, 50, 42, 53.7), (37, 53, 47, 53.7), (14, 60, 47, 60.7)):
            lib.box(bm, F, c0, r0, c1, r1, 0.14, 0.18, BEVEL)

        # Lower block: a chamfered lower-left corner, a slatted vent and two blue ribs.
        l_low = [(5.5, 64.5), (58.5, 64.5), (58.5, 74.5), (48.5, 84), (24, 84), (5.5, 65.5)]
        l_top = [(14.5, 64.5), (58.5, 64.5), (58.5, 74.5), (48.5, 84), (33, 84), (14.5, 65)]
        lib.stack(bm, F, [(l_low, 0.0), (l_top, 0.24)], top_mat=MID,
                  side_mat=lambda k, i: BEVEL if i in (4, 5) else MID)
        lib.sweep(bm, F, [(14.8, 65.3, 0.24, 0.9, 0.03), (33.3, 84, 0.24, 0.9, 0.03)], sides=6, mat=LIGHT)
        lib.prism(bm, F, [(25, 65), (51, 65), (51, 76), (29, 76), (25, 72)], 0.24, 0.25, BLACK)
        lib.box(bm, F, 25, 65, 51, 66, 0.24, 0.285, TRIM)
        lib.box(bm, F, 25, 66, 26, 73, 0.24, 0.285, TRIM)
        lib.box(bm, F, 50, 66, 51, 68.5, 0.24, 0.285, TRIM)
        for r in (69, 71, 73):
            lib.sweep(bm, F, [(29.5, r, 0.255, 0.8, 0.025), (45, r, 0.255, 0.8, 0.025)], sides=6, mat=TRIM)
        for c in (29.5, 37.5):
            lib.box(bm, F, c, 76, c + 5, 84, 0.24, 0.29, BLUE, side_mat=TRIM)
        lib.prism(bm, F, [(48.5, 84), (58.5, 74.5), (58.5, 75.5), (56.5, 77.5), (56.5, 84)], 0.0, 0.10, VOID)

        # Blue arm beside the orb: a round tube standing on the floor, about as tall as it is wide,
        # rounded off at both ends, with the sprite's highlight stripe along its crest (left) or its
        # outer flank (right).
        arm = [(64.4, 28.8, ARM_Z - 0.10, 4.2, ARM_H - 0.16), (64.5, 29.8, ARM_Z, 6.3, ARM_H - 0.02),
               (67.5, 40.5, ARM_Z, 6.8, ARM_H), (69.5, 47.5, ARM_Z, 7.4, ARM_H), (71.5, 53, ARM_Z, 7.5, ARM_H),
               (72.6, 56.5, ARM_Z - 0.04, 6.0, ARM_H - 0.06), (73.2, 58.6, ARM_Z - 0.10, 3.8, ARM_H - 0.18)]
        lib.sweep(bm, F, arm, sides=12, mat=pick(BLUE_L, BLUE), power=ARM_POW)
        stripe = pick([(65.4, 31.5, 0.0), (68.4, 42, 0.0), (71.3, 52, 0.0)],
                      [(66.0, 44.5, -0.80), (66.5, 50, -0.80), (68.5, 55, -0.70)])
        lib.sweep(bm, F, [(c, r, arm_z(arm, r, u) - 0.012, 0.8, 0.025) for c, r, u in stripe], sides=6, mat=BLUE_W)

        # Blue claw beside the hood.
        # On the left the sprite draws the claw's lower lip dark navy; the right claw is all blue.
        if side == 0:
            lib.prism(bm, F, [(83, 25), (84.5, 25), (88, 28.2), (88, 36), (85, 38.5), (82.5, 38), (81.5, 33),
                              (82, 26)], 0.0, 0.46, BLUE_V, side_mat=BLUE)
            lib.prism(bm, F, [(81.5, 32), (82.5, 33), (83.5, 38.3), (81, 40), (79, 40), (78, 37), (78, 34)],
                      0.0, 0.34, NAVY, side_mat=NAVY)
        else:
            lib.prism(bm, F, [(83, 25), (84.5, 25), (88, 28.2), (88, 36), (85, 38.5), (81, 40), (79, 40), (78, 37),
                              (78, 34), (81, 32), (82, 26)], 0.0, 0.46, BLUE_D, side_mat=BLUE)
            # The right pillar's shadowed side shows as a navy strip on the plate.
            lib.box(bm, F, 39.2, 22, 41, 36.5, 0.575, 0.59, NAVY_L)

        # Hip of the hood's roof sloping down to the outline (columns 66-84, rows 10-20).
        a, b, c = (84, 10.5, 0.64), (84, 20.5, 0.64), (66, 20.5, 0.40)
        top = [bm.verts.new((F.X(x), F.Y(y), z)) for x, y, z in (a, b, c)]
        low = [bm.verts.new((F.X(x), F.Y(y), 0.0)) for x, y, _ in (a, b, c)]
        bm.faces.new(top).material_index = pick(LIGHT, DARKGREY)
        bm.faces.new(list(reversed(low))).material_index = GREY
        for i in range(3):
            j = (i + 1) % 3
            bm.faces.new((low[i], low[j], top[j], top[i])).material_index = GREY

        # A barrel slanting down and out under the shoulder, a bright knob on it and a stub below.
        lib.sweep(bm, F, [(71.2, 57.3, 0.38, 0.0, 0.0), (70, 58.5, 0.38, 3.6, 0.30), (56, 71.5, 0.38, 4.2, 0.33),
                          (55, 72.5, 0.36, 3.0, 0.24), (54.6, 72.9, 0.36, 0.0, 0.0)], sides=10, mat=MID)
        lib.ellipsoid(bm, F, 64.5, 62.5, 0.68, 1.8, 1.8, 0.08, mat=KNOB, segments=8, rings=4)
        lib.ellipsoid(bm, F, 65, 78.5, 0.0, 3.0, 3.2, 0.26, mat=DARKGREY, segments=10, rings=4, upper=True)

        if side:
            lib.mirror_since(bm, start, AX)

    # ---- the middle (symmetric about column 95) ----

    # Hood: a tall block with vent ribs on its roof.
    lib.prism(bm, F, [(84, 10.5), (107, 10.5), (107, 20.5), (111, 20.5), (111, 24.5), (102, 28.5), (102, 37),
                      (89, 37), (89, 28.5), (80, 24.5), (80, 20.5), (84, 20.5)], 0.0, 0.64, GREY)
    for c in range(89, 102, 2):
        lib.box(bm, F, c, 11, c + 1, 15.5, 0.64, 0.66, RIB)

    # The navy lip under the hood's front and the claws.
    lib.box(bm, F, 78, 37, 113, 40, 0.0, 0.26, NAVY)
    # The dark glass orb under the hood: a tall dome (top ~13 px) in the dark well, and its glint where
    # the sprite draws it.
    oc, orow, orx, ory, orz = AXIS, 47.5, 12.0, 8.5, ORB_Z
    lib.ellipsoid(bm, F, oc, orow, 0.04, orx, ory, orz, mat=ORB, segments=24, rings=12, upper=True)
    def orb_z(c, r):
        return 0.04 + orz * max(0.0, 1 - ((c - oc) / orx) ** 2 - ((r - orow) / ory) ** 2) ** 0.5

    decal(bm, 91.0, 45.0, 3.2, 2.7, orb_z, 0.012, KNOB)
    decal(bm, 90.8, 44.6, 1.3, 1.2, orb_z, 0.022, GLINT)

    # Grey block under the collar, and the curved collar cradling the orb: a round tube lying on the
    # floor (as tall as it is wide, top ~11.5 px), rising at its ends beside the arms.
    lib.box(bm, F, 73, 60, 118, 68.5, 0.0, 0.18, MID)
    half = [(70.8, 57.0, 0.42, 0.0, 0.0), (71.5, 58.0, 0.36, 3.5, 0.34), (74, 59.3, 0.42, 4.6, 0.42),
            (78, 60.8, 0.45, 5.0, 0.45), (84, 62, 0.48, 5.4, 0.48), (90, 62.5, 0.48, 5.5, 0.48)]
    path = half + [(AXIS, 62.6, 0.48, 5.5, 0.48)] + [(2 * AXIS - c, r, z, w, h) for c, r, z, w, h in reversed(half)]
    lib.sweep(bm, F, path, sides=12, mat=GREY)

    # Three barrels lying across the front (blue, grey, blue: the sprite's lid bands), ~8 px tall,
    # on a low navy pedestal.
    lib.box(bm, F, 72.5, 69.2, 118.5, 74, 0.0, 0.22, NAVY)
    for c0, c1, hw, m in ((72.5, 91.2, 2.6, BLUE_D), (91.6, 99.4, 2.3, MID), (99.8, 118.5, 2.6, BLUE_D)):
        lib.sweep(bm, F, [(c0, 71.6, 0.42, hw, 0.25), (c1, 71.6, 0.42, hw, 0.25)], sides=12, mat=m)
    # Bottom screen: blue bevelled sides, a grey top bar and a dark face sunk to ~0.7 px.
    for c0, c1, c_in, m in ((70, 75, 72.5, BLUE_L), (121, 116, 118.5, BLUE_D)):
        lo = [(c0, 73.5), (c1, 73.5), (c1, 84), (c0, 84)]
        hi = [(c_in, 73.5), (c1, 73.5), (c1, 84), (c_in, 84)]
        if c0 > c1:
            lo, hi = [lo[1], lo[0], lo[3], lo[2]], [hi[1], hi[0], hi[3], hi[2]]
        lib.stack(bm, F, [(lo, 0.0), (lo, 0.12), (hi, 0.30)], top_mat=DARKGREY,
                  side_mat=lambda k, i, m=m, c0=c0: BLUE if k == 0 else (m if i == (3 if c0 < 100 else 1) else DARKGREY))
    lib.box(bm, F, 75, 73.5, 116, 75.5, 0.0, 0.30, GREY, side_mat=DARKGREY)
    lib.box(bm, F, 75, 75.5, 116, 84, 0.0, 0.06, BLACK)
    for c0, r0, c1, r1 in ((77, 78, 114, 78.7), (77, 78.7, 77.7, 84), (113.3, 78.7, 114, 84), (85, 81, 106, 81.7)):
        lib.box(bm, F, c0, r0, c1, r1, 0.06, 0.10, BEVEL)

    return lib.to_object(NAME, bm, mats, coll)


def flatten_cut_faces(piece):
    """Shade the faces split_assembly fills along a piece's edges (its 24 x 28 px box) flat, so the
    smooth parts cut there (orb, collar, arms) keep their own normals instead of bending towards
    the cut and showing a crease where two pieces meet."""
    hx, hy, eps = 1.0, 14 / 12, 1e-4
    me = piece.data
    for p in me.polygons:
        cos = [me.vertices[i].co for i in p.vertices]
        on_x = all(abs(abs(c.x) - hx) < eps for c in cos) and abs(cos[0].x - cos[-1].x) < eps
        on_y = all(abs(abs(c.y) - hy) < eps for c in cos) and abs(cos[0].y - cos[-1].y) < eps
        if on_x or on_y:
            p.use_smooth = False


def decal(bm, c, r, rx, ry, surf, lift, mat, segments=12):
    """A thin patch hugging a surface z = surf(col, row): an elliptical disc `lift` above it (a little
    domed), closed underneath by a point sunk into the surface."""
    def v(cc, rr, dz):
        return bm.verts.new((F.X(cc), F.Y(rr), surf(cc, rr) + dz))
    centre = v(c, r, lift * 1.5)
    rings = [[v(c + rx * t * math.cos(a), r + ry * t * math.sin(a), lift * (1.5 - 0.5 * t * t))
              for a in (2 * math.pi * i / segments for i in range(segments))] for t in (0.5, 1.0)]
    under = v(c, r, -0.08)
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append(bm.faces.new((centre, rings[0][j], rings[0][i])))
        faces.append(bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i])))
        faces.append(bm.faces.new((rings[1][i], rings[1][j], under)))
    for f in faces:
        f.material_index = mat
        f.smooth = True


def main():
    sprite = lib.merged_sprite(common, ROOT, PIECES)
    obj = build(sprite)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    pieces = common.split_assembly(obj, layout)
    for piece in pieces.values():
        flatten_cut_faces(piece)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    if "--preview" in sys.argv:
        import tempfile
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        ref = lib.composite_png(common, ROOT, layout, 192, 84, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=16, view_px=800)
        if "--pieces" in sys.argv:
            for name in PIECES:
                data = common.load_sprite(ROOT, name)
                img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
                common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
