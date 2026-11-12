"""Jungle bunker tower (newshj.shp 5/7 over 43/45, a 48 x 56 px 2x2 block).

WHAT IT IS: a fixed ground building in the jungle (types 745-748, armour 10, no fire, TORM and
BONUS). A concrete-and-steel pad with a sloped blast apron (glacis) carries three blocks that stand
side by side along its back edge:
- a tall armoured watch tower (cols 13-25) with three armoured windows that light in turn, set in a
  proud frame with drip sills, a base course with a double door, and a mono-pitch roof falling to
  the rear behind a flat front strip;
- a sloped-armour buttress on its west (cols 5-13): a framed recessed panel under a 45 deg armour
  roof plate falling to the west;
- a finned heat-exchanger housing on its east (cols 25.5-38.5): rounded east corners, horizontal
  cooling ribs wrapped round it, a raised duct panel, a finned hood rising to the rear, and an
  intake duct that elbows out of the panel and runs down the apron into a sump.

PROJECTION (D82 approach C as extended by D165): the art is an orthographic view from the south at
elevation e = 15 deg. A point at column c, plan row p (south +), height h (all sprite px) draws at
row r = A + sin e (p - A) - cos e h, A = 47 (the pad's front edge). The model is the real,
upright building; the glb carries tyrian_oblique [cos e, sin e, axis_z] and tyrian_depth_band
[0, 0.4, 0, top] so the renderer locks it to that view. Every height below is solved from the
sprite rows it must draw at (hf()).

EXPORT: one real building, cut into the four 24 x 28 pieces by bands of ART rows (the plane
S p - K h = const, so a tower's lower art rows stay in the lower pieces) and columns, each piece
about its own centre with tyrian_oblique axis_z = (A - r0 - 14) PX and the shared
tyrian_depth_band [0, 0.4, 0, top]. Shells are cut open (no ink line at the seams).

Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshj-43.py
(optional: -- --render <dir> with the workbench views, needs render_views.py beside the script)
"""

import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import lib_b126 as lib  # noqa: E402  (read-only: merged_sprite)

WT = common.repo_root(__file__)
ROOT = WT
NAME = "assembly-newshj-43"
TAG = "nshj43"
PIECES = [("newshj-5", 0, 0), ("newshj-7", 24, 0), ("newshj-43", 0, 28), ("newshj-45", 24, 28)]
PX = 1 / 12
E = math.radians(15.0)
S, K = math.sin(E), math.cos(E)
A = 47.0  # oblique axis: the pad's front edge, plan row 47
GL = math.tan(math.radians(10.0))  # glacis slope


def hf(r, p):
    """Height (px) at which a point on plan row p draws at sprite row r."""
    return (A + S * (p - A) - r) / K


def g(p):
    """Top of the glacis at plan row p."""
    return 3.0 + (A - p) * GL


# ---- plan layout (px) ----
P_FRONT = 29.5  # the blocks' front faces (their foot draws at row 36.6)
P_BACK = 17.5  # the blocks' (and the pad's) back
H_T = hf(5.0, P_FRONT - 3.0)  # tower: the roof strip's back edge draws at row 5 (inner mask top)
T_SLOPE = math.tan(math.radians(25.0))  # tower mono-pitch: steeper than 15 deg, so hidden in the art


def h_wing(c):
    """The buttress roof plate's top along its back edge: the silhouette's 45 deg diagonal (row 20 - c)."""
    return hf(20.0 - c, P_BACK)


H_HF = hf(14.5, P_FRONT)  # housing front-top edge (the dark eave line, row 14)
H_HB = hf(8.1, P_BACK)  # hood's back edge: the housing's top (row 8 inner)
HOOD = (H_HB - H_HF) / (P_FRONT - P_BACK)  # hood rise per px of depth


# ---- geometry helpers (sprite px: c, p, h) ----
def inset(poly, d):
    """Convex polygon moved inward by d (edge offset, corners re-intersected)."""
    n = len(poly)
    cx = sum(x for x, _ in poly) / n
    cy = sum(y for _, y in poly) / n
    lines = []
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        nx, ny = dy / ln, -dx / ln
        if nx * ((x0 + x1) / 2 - cx) + ny * ((y0 + y1) / 2 - cy) > 0:
            nx, ny = -nx, -ny
        lines.append(((x0 + nx * d, y0 + ny * d), (dx / ln, dy / ln)))
    out = []
    for i in range(n):
        (p0, d0), (p1, d1) = lines[i - 1], lines[i]
        den = d0[0] * d1[1] - d0[1] * d1[0]
        if abs(den) < 1e-9:
            out.append(p1)
            continue
        t = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / den
        out.append((p0[0] + d0[0] * t, p0[1] + d0[1] * t))
    return out


def corner_cut(poly, cuts):
    """Chamfer the corners of a polygon: cuts[i] is the cut length at vertex i (0 keeps it)."""
    out = []
    n = len(poly)
    for i, (x, y) in enumerate(poly):
        d = cuts[i] if isinstance(cuts, (list, tuple)) else cuts
        if d <= 0:
            out.append((x, y))
            continue
        for j in (i - 1, (i + 1) % n):
            ox, oy = poly[j]
            ln = math.hypot(ox - x, oy - y)
            t = min(d, ln * 0.45) / ln
            out.append((x + (ox - x) * t, y + (oy - y) * t))
        # keep the order: previous-side point then next-side point
    return out


def to3(axis, a, u, v):
    if axis == "c":
        return (a, u, v)  # poly in (p, h)
    if axis == "p":
        return (u, a, v)  # poly in (c, h)
    return (u, v, a)  # axis h: poly in (c, p)


def cprism(part, axis, poly, a0, a1, ch, mat):
    """A convex prism along `axis` over `poly`, every edge round both end caps chamfered by ch."""
    pts = []
    if ch > 0:
        for a in (a0, a1):
            pts += [to3(axis, a, u, v) for u, v in inset(poly, ch)]
        for a in (a0 + ch, a1 - ch):
            pts += [to3(axis, a, u, v) for u, v in poly]
    else:
        for a in (a0, a1):
            pts += [to3(axis, a, u, v) for u, v in poly]
    T.hull(part, pts, mat)


def cbox(part, c0, c1, p0, p1, h0, h1, ch, mat):
    T.hull(part, T.cbox(c0, c1, p0, p1, h0, h1, ch), mat)


def hull_pts(part, pts, mat):
    T.hull(part, pts, mat)


def tube(part, path, radius, mat, n=16, cap=True):
    """A round pipe along a polyline of (c, p, h) points (rings perpendicular to the path)."""
    rings = []
    m = len(path)
    for i in range(m):
        a = Vector(path[max(i - 1, 0)])
        b = Vector(path[min(i + 1, m - 1)])
        t = (b - a).normalized()
        ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 0, 1))
        u = t.cross(ref).normalized()
        w = t.cross(u).normalized()
        c = Vector(path[i])
        rings.append([part.v(tuple(c + (u * math.cos(2 * math.pi * k / n) + w * math.sin(2 * math.pi * k / n)) * radius))
                      for k in range(n)])
    for i in range(m - 1):
        cen = (Vector(path[i]) + Vector(path[i + 1])) / 2
        for k in range(n):
            part.f([rings[i][k], rings[i][(k + 1) % n], rings[i + 1][(k + 1) % n], rings[i + 1][k]], mat, away=tuple(cen))
    if cap:
        for ring, end, nxt in ((rings[0], path[0], path[1]), (rings[-1], path[-1], path[-2])):
            d = Vector(end) - Vector(nxt)
            part.f(list(ring), mat, out=tuple(d))


def finish(part, mats, coll, name, smooth_angle=35.0):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    # px to Blender: X = (c - 24) / 12, Y = (28 - p) / 12, Z = h / 12 (a reflection in p).
    m = Matrix(((PX, 0, 0, -24 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


# ---- the build ----
def build(sprite, coll):
    pal = lambda i, m=0.35, r=0.45: common.palette_material(sprite, i, TAG, metallic=m, roughness=r)  # noqa: E731
    mats = [
        pal(9),  # 0 tower body, deck plating, duct (grey)
        pal(10, 0.4, 0.4),  # 1 lit frame members, sills, deck lip
        pal(7),  # 2 buttress, housing body, door
        pal(5, 0.3, 0.5),  # 3 recessed panels, base course, pad front
        pal(3, 0.25, 0.6),  # 4 window reveals, hatch lids, grates
        pal(11, 0.45, 0.38),  # 5 housing ribs and hood fins, curb
        pal(6, 0.3, 0.5),  # 6 step top, hatch box
        pal(4, 0.3, 0.55),  # 7 east skirt slope
        pal(12, 0.45, 0.35),  # 8 bollards
    ]
    BODY, FRAME, ARM, PANEL, REVEAL, RIB, STEP, SKIRT, POST = range(len(mats))
    body = T.Part("body", smooth_angle=35.0)
    padp = T.Part("pad", smooth_angle=35.0)
    cut = T.Part("trench_cut", smooth_angle=35.0)

    # ---- pad: a glacis slab rising from the front edge (h 3) to the back (h 8.2), a narrow lit
    # chamfer on its west edge and a wide sloped skirt on its east ----
    pf, pb = A - 0.6, P_BACK
    pts = []
    for (p, h) in ((pf, 0.0), (pf, g(pf) - 0.7), (pf - 0.7, g(pf - 0.7)), (pb, g(pb)), (pb, 0.0)):
        top = h > 0.5
        pts += [(5.0 if not top else 5.9, p, h), (36.6, p, h)]
    hull_pts(padp, pts, BODY)
    # front face plate (rows 44-46): the pad's front course, a hair proud
    cbox(padp, 5.0, 39.4, A - 1.2, A, 0.0, g(A) - 0.55, 0.3, PANEL)
    # east skirt: from the deck's east edge down to column 39.5 at the ground
    sk = []
    for p, ce in ((A - 0.4, 39.3), (pb, 39.9)):
        sk += [(36.0, p, 0.0), (ce, p, 0.0), (36.0, p, g(p)), (36.6, p, g(p))]
    hull_pts(padp, sk, SKIRT)
    # the deck's T-trench, a real recess (sprite rows 37-39, cols 11-33, and the slot down col 15):
    # cutters that follow the glacis, subtracted from the pad below
    def slab(c0, c1, p0, p1, depth):
        pts = []
        for c in (c0, c1):
            for p in (p0, p1):
                pts += [(c, p, g(p) - depth), (c, p, g(p) + 6.0)]
        hull_pts(cut, pts, REVEAL)
    slab(11.4, 33.0, 30.4, 34.6, 1.0)
    slab(14.2, 15.4, 34.4, 40.8, 0.7)

    # ---- watch tower: side profile (p, h), extruded along c ----
    prof = [(P_FRONT - 0.8, 0.0), (P_FRONT - 0.8, H_T - 1.0), (P_FRONT - 1.8, H_T), (P_FRONT - 3.0, H_T),
            (P_BACK, H_T - (P_FRONT - 3.0 - P_BACK) * T_SLOPE), (P_BACK, 0.0)]
    cprism(body, "c", prof, 13.3, 25.0, 0.5, BODY)
    # roof: a flat front strip with a raised parapet lip and the coping (rows 5-6)
    cbox(body, 13.4, 24.6, P_FRONT - 3.2, P_FRONT - 0.9, H_T - 0.3, H_T + 0.15, 0.15, FRAME)
    # window frame, proud of the body to P_FRONT: stiles, sills, base course
    hw = lambda r: hf(r, P_FRONT)  # noqa: E731
    top_h = H_T - 1.0
    # left stile with the SW corner's 1 px bevel (col 13, pal 7) and the lit stile (col 14-15)
    cprism(body, "h", corner_cut([(13.0, P_FRONT - 1.2), (16.0, P_FRONT - 1.2), (16.0, P_FRONT), (13.0, P_FRONT)],
                                 [0, 0, 0, 1.0]), hw(36.0), top_h, 0.25, FRAME)
    cprism(body, "h", corner_cut([(23.0, P_FRONT - 1.2), (25.0, P_FRONT - 1.2), (25.0, P_FRONT), (23.0, P_FRONT)],
                                 [0, 0, 0.5, 0]), hw(36.0), top_h, 0.25, BODY)
    # head over the top window, then the sills with drip noses (rows 14, 22, 30)
    cbox(body, 15.8, 23.2, P_FRONT - 1.2, P_FRONT, hw(7.0), top_h + 0.2, 0.2, FRAME)
    for r in (14.0, 22.0, 30.0):
        sill = [(P_FRONT - 1.2, hw(r + 1.0)), (P_FRONT + 0.5, hw(r + 1.0)), (P_FRONT + 0.5, hw(r + 0.55)),
                (P_FRONT, hw(r)), (P_FRONT - 1.2, hw(r))]
        cprism(body, "c", sill, 15.8, 23.2, 0.15, FRAME)
    # window reveals: the dark L of each recess (top rows and column 16), 0.4 px behind the frame
    for head0, head1, p_top, p_bot in ((7.0, 8.0, 8.0, 14.0), (15.0, 16.0, 16.0, 22.0), (23.0, 25.0, 25.0, 30.0)):
        cbox(body, 16.0, 23.0, P_FRONT - 1.4, P_FRONT - 0.4, hw(head1), hw(head0), 0.05, REVEAL)
        cbox(body, 16.0, 16.8, P_FRONT - 1.4, P_FRONT - 0.4, hw(p_bot), hw(head1), 0.05, REVEAL)
    # base course (rows 31-36): proud plinth either side of a recessed double door (cols 17-20)
    for c0, c1 in ((13.0, 17.0), (20.5, 25.0)):
        cprism(body, "p", corner_cut([(c0, 0.0), (c1, 0.0), (c1, hw(31.0)), (c0, hw(31.0))], [0, 0, 0.3, 0.3]),
               P_FRONT - 1.0, P_FRONT + 0.4, 0.2, PANEL)
    cbox(body, 17.0, 20.5, P_FRONT - 1.0, P_FRONT - 0.2, 0.0, hw(31.0), 0.1, REVEAL)  # door jambs / recess
    cbox(body, 17.6, 19.9, P_FRONT - 1.0, P_FRONT, 0.0, hw(31.6), 0.1, ARM)  # door leaves
    cbox(body, 18.7, 18.8, P_FRONT - 0.5, P_FRONT + 0.05, 0.0, hw(31.8), 0.0, REVEAL)  # leaf split

    # string courses at each floor, round the sides and back (the front's sills carry them across)
    for r in (14.5, 22.5, 30.5):
        z = hw(r)
        cbox(body, 13.0, 25.3, P_BACK - 0.35, P_FRONT - 1.0, z - 0.35, z + 0.35, 0.15, FRAME)
    # rear: an access door at the foot and a caged ladder up to the roof
    cbox(body, 16.5, 21.5, P_BACK - 0.6, P_BACK + 0.5, 0.0, 9.5, 0.25, PANEL)
    cbox(body, 17.1, 20.9, P_BACK - 0.75, P_BACK, 0.0, 8.9, 0.1, ARM)
    lad_top = H_T - (P_FRONT - 3.0 - P_BACK) * T_SLOPE - 0.3
    for c in (22.2, 24.0):
        tube(body, [(c, P_BACK - 1.1, 9.0), (c, P_BACK - 1.1, lad_top + 1.2)], 0.22, FRAME, n=6)
        for z in (9.5, lad_top + 0.8):
            tube(body, [(c, P_BACK - 1.1, z), (c, P_BACK + 0.2, z)], 0.18, FRAME, n=6)
    z = 10.0
    while z < lad_top + 1.0:
        tube(body, [(22.2, P_BACK - 1.1, z), (24.0, P_BACK - 1.1, z)], 0.14, FRAME, n=6)
        z += 1.4
    # roof hatch on the rear pitch
    rz = lambda p: H_T - (P_FRONT - 3.0 - p) * T_SLOPE  # noqa: E731
    hatch = []
    for c in (16.0, 21.5):
        for p in (19.5, 23.5):
            hatch += [(c, p, rz(p) - 0.5), (c, p, rz(p) + 0.45)]
    hull_pts(body, hatch, PANEL)

    # ---- buttress (west): a framed panel under a 45 deg armour roof falling to the west ----
    wp0, wp1 = 5.3, 13.6
    core = [(wp0, 0.0), (wp1, 0.0), (wp1, h_wing(wp1) - 0.9), (wp0, h_wing(wp0) - 0.9)]
    cprism(body, "p", core, P_BACK, P_FRONT - 1.1, 0.3, PANEL)
    # roof plate: 0.9 thick, overhanging the front by 0.3
    roof = [(wp0 - 0.2, h_wing(wp0) - 1.0), (wp1, h_wing(wp1) - 1.0), (wp1, h_wing(wp1)), (wp0 - 0.2, h_wing(wp0))]
    cprism(body, "p", roof, P_BACK - 0.2, P_FRONT - 0.2, 0.3, ARM)
    # front frame (pal 7), 0.6 proud of the panel: left stile, top bar along the roof, the lower piece
    ww = lambda r: hf(r, P_FRONT - 0.5)  # noqa: E731
    fz0, fz1 = P_FRONT - 1.6, P_FRONT - 0.5
    cprism(body, "p", [(wp0, 0.0), (6.9, 0.0), (6.9, h_wing(6.9) - 1.0), (wp0, h_wing(wp0) - 1.0)], fz0, fz1, 0.35, ARM)
    cprism(body, "p", [(6.9, h_wing(6.9) - 3.0), (12.6, h_wing(12.6) - 3.0), (12.6, h_wing(12.6) - 1.0),
                       (6.9, h_wing(6.9) - 1.0)], fz0, fz1, 0.3, ARM)
    cprism(body, "p", [(6.9, 0.0), (12.6, 0.0), (12.6, ww(27.0)), (6.9, ww(32.2))], fz0, fz1, 0.3, ARM)
    # grafted from design B: the panel is a parallelogram with 45 deg top and bottom inside a raised
    # border: close it with a right stile and a lit sill along its lower edge
    cprism(body, "p", [(12.0, 0.0), (12.8, 0.0), (12.8, h_wing(12.8) - 1.0), (12.0, h_wing(12.0) - 1.0)], fz0, fz1, 0.2, ARM)
    cprism(body, "p", [(6.9, ww(32.2) - 0.3), (12.6, ww(27.0) - 0.3), (12.6, ww(27.0)), (6.9, ww(32.2))],
           fz0 - 0.1, fz1 + 0.15, 0.1, FRAME)
    # louvred vent in the buttress's west wall
    for i in range(5):
        z = 9.0 + i * 1.6
        cprism(body, "c", [(P_BACK + 3.0, z), (P_BACK + 9.0, z), (P_BACK + 9.0, z + 0.9), (P_BACK + 3.0, z + 0.5)],
               wp0 - 0.5, wp0 + 0.5, 0.1, FRAME)
    cbox(body, wp0 - 0.25, wp0 + 0.5, P_BACK + 2.6, P_BACK + 9.4, 8.4, 9.0 + 5 * 1.6, 0.1, REVEAL)
    # curb along the buttress foot (row 37, lit)
    cbox(body, 5.6, 12.6, P_FRONT - 1.0, P_FRONT + 2.2, 0.0, g(P_FRONT + 2.2) + 0.9, 0.3, RIB)

    # ---- heat-exchanger housing (east): rounded east corners, a hood rising to the rear ----
    R = 3.5
    EX = 37.8  # the housing's east face
    def ctr(grow=0.0, west=25.6):
        pts = [(west, P_BACK - grow), (west, P_FRONT + grow)]
        # front-east corner from facing south (+p) round to facing east (+c), then the back-east one
        for cp, a0, a1 in ((P_FRONT - R, 0.0, 90.0), (P_BACK + R, 90.0, 180.0)):
            for k in range(7):
                a = math.radians(a0 + (a1 - a0) * k / 6)
                pts.append((EX - R + (R + grow) * math.sin(a), cp + (R + grow) * math.cos(a)))
        return pts

    hood_h = lambda p: H_HF + (P_FRONT - p) * HOOD  # noqa: E731
    hb = []
    for c, p in ctr(west=25.9):
        hb += [(c, p, 0.0), (c, p, hood_h(p) - 0.8)]
    hull_pts(body, hb, ARM)
    # the dark seam against the tower (col 25): a recessed filler, set 1 px back
    cbox(body, 24.8, 26.2, P_BACK + 0.3, P_FRONT - 1.0, 0.0, hood_h(P_FRONT - 1.0) - 0.7, 0.1, REVEAL)
    # splayed foot on the east (the dark cradle, cols 36-39, rows 31-37)
    cprism(body, "p", [(35.5, 0.0), (39.9, 0.0), (38.6, hf(31.5, P_FRONT - 1.0)), (35.5, hf(31.5, P_FRONT - 1.0))],
           P_BACK + 0.5, P_FRONT - 1.0, 0.3, SKIRT)
    # hood plate: 0.8 thick, overhanging front and east by 0.7 (its lip shades the eave line, row 14)
    hp = []
    for c, p in ctr(1.0, west=25.0):
        c = min(c, 39.0)
        hp += [(c, p, hood_h(p) - 0.8 - 0.1), (c, p, hood_h(p) - 0.1)]
    hull_pts(body, hp, ARM)
    # three pairs of cooling fins running up the hood (bright cols 27, 30, 34-35)
    for c0, c1 in ((26.7, 28.5), (29.9, 31.7), (33.8, 35.6)):
        for cc0, cc1 in ((c0, c0 + 0.7), (c1 - 0.7, c1)):
            fin = [(P_FRONT + 0.3, hood_h(P_FRONT + 0.3) - 0.2), (P_FRONT + 0.3, hood_h(P_FRONT) + 0.5),
                   (P_BACK + 0.6, hood_h(P_BACK + 0.6) + 0.5), (P_BACK + 0.6, hood_h(P_BACK + 0.6) - 0.2)]
            cprism(body, "c", fin, cc0, cc1, 0.12, RIB)
    # raised duct panel (cols 30.6-35.8) up the front face
    cbox(body, 30.6, 35.8, P_FRONT - 0.5, P_FRONT + 0.45, 0.0, H_HF - 0.6, 0.2, BODY)
    # horizontal cooling ribs wrapped round the front and east (bright rows 15, 18, 20, 25, 29, 31)
    hh = lambda r: hf(r, P_FRONT)  # noqa: E731
    for r in (15.0, 18.0, 20.0, 25.0, 29.0, 31.0):
        z0, z1 = hh(r + 0.95), hh(r)
        rb = []
        for c, p in ctr(0.6, west=25.8):
            rb += [(c, p, z0 + 0.2), (c, p, z1 - 0.2)]
        for c, p in ctr(0.35, west=25.8):
            rb += [(c, p, z0), (c, p, z1)]
        hull_pts(body, rb, RIB)
    # louvred vent low on its west (dark cols 27-28, rows 33-35)
    cbox(body, 26.6, 29.4, P_FRONT - 0.3, P_FRONT + 0.25, hh(35.6), hh(32.6), 0.1, REVEAL)
    for r in (33.4, 34.4):
        cbox(body, 26.7, 29.3, P_FRONT, P_FRONT + 0.45, hh(r + 0.35), hh(r), 0.05, BODY)

    # ---- intake duct: out of the panel at h ~10, elbow down, along the apron into a sump ----
    cdx = 32.0
    rad = 1.25
    path = [(cdx, P_FRONT - 0.5, 10.6), (cdx, P_FRONT + 1.2, 10.6), (cdx, P_FRONT + 2.4, 10.1),
            (cdx, P_FRONT + 3.3, 9.2)]
    for p in (P_FRONT + 4.5, 36.0, 39.0, 41.4):
        path.append((cdx, p, g(p) + rad + 0.5))
    tube(body, path, rad, BODY)
    for p in (P_FRONT + 0.8, 38.0):  # flanges
        q = path[1] if p < 31 else (cdx, p, g(p) + rad + 0.5)
        d = Vector((0, 1, 0)) if p < 31 else Vector((0, 1, -GL)).normalized()
        tube(body, [tuple(Vector(q) - d * 0.3), tuple(Vector(q) + d * 0.3)], rad + 0.3, FRAME, n=16)
    cbox(body, 30.7, 33.3, 40.8, 43.6, 0.0, g(40.6) + 2.3, 0.3, BODY)  # sump
    cbox(body, 31.1, 32.9, 41.3, 43.1, g(40.6) + 2.2, g(40.6) + 2.45, 0.1, REVEAL)  # its grate

    # ---- apron details ----
    # deck plating: hairline-proud dark seams between the panels (modelled panel lines)
    def seam(c0, c1, p0, p1):
        q = []
        for c in (c0, c1):
            for p in (p0, p1):
                q += [(c, p, g(p) - 0.2), (c, p, g(p) + 0.05)]
        hull_pts(body, q, REVEAL)
    seam(5.8, 36.3, 44.1, 44.4)
    seam(10.3, 10.6, 35.6, 44.1)
    seam(24.3, 24.6, 35.6, 44.1)
    seam(5.8, 11.0, 36.4, 36.7)
    seam(33.5, 36.3, 36.0, 36.3)
    # lit lip along the trench's front edge (pal 6 step)
    st = []
    for c in (11.4, 25.4):
        for p in (34.6, 35.4):
            st += [(c, p, g(p) - 0.2), (c, p, g(p) + 0.35)]
    hull_pts(body, st, STEP)
    # service box (cols 18-23, rows 40-43), lit lid edge
    sb = []
    for c in (18.0, 23.6):
        for p in (38.6, 42.4):
            sb += [(c, p, 0.0), (c, p, g(p) + 2.2)]
    hull_pts(body, sb, BODY)
    # hatch box beside the duct (cols 25.5-30.5) with a dark hatch lid
    hb2 = []
    for c in (25.6, 29.2):
        for p in (35.6, 38.8):
            hb2 += [(c, p, 0.0), (c, p, g(p) + 2.2)]
    hull_pts(body, hb2, STEP)
    lid = []
    for c in (26.2, 28.6):
        for p in (36.2, 38.2):
            lid += [(c, p, g(p) + 2.1), (c, p, g(p) + 2.35)]
    hull_pts(body, lid, REVEAL)
    # bollards (cols 7 and 9, rows 39-42)
    for c in (7.5, 9.5):
        tube(body, [(c, 41.5, 0.0), (c, 41.5, g(41.5) + 2.9)], 0.55, POST, n=10)
        tube(body, [(c, 41.5, g(41.5) + 2.9), (c, 41.5, g(41.5) + 3.3)], 0.42, POST, n=10)

    padobj = finish(padp, mats, coll, f"{NAME}_pad")
    cutobj = finish(cut, mats, coll, f"{NAME}_cut")
    bo = padobj.modifiers.new("trench", "BOOLEAN")
    bo.operation, bo.solver, bo.object = "DIFFERENCE", "EXACT", cutobj
    bo.use_self = True
    bpy.context.view_layer.objects.active = padobj
    bpy.ops.object.modifier_apply(modifier="trench")
    bpy.data.objects.remove(cutobj, do_unlink=True)
    pbm = bmesh.new()
    pbm.from_mesh(padobj.data)
    bmesh.ops.recalc_face_normals(pbm, faces=pbm.faces)
    pbm.to_mesh(padobj.data)
    pbm.free()
    obj = finish(body, mats, coll, f"{NAME}_body")
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    padobj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    obj.name = f"{NAME}_body"

    # ---- glass: the three panes, set 0.6 px into the frame, each its own shade per frame ----
    panes = [(198, {9: 196, 11: 193}), (196, {9: 198}), (192, {9: 194, 11: 199, 47: 194, 49: 199})]
    gmats = [common.palette_material(sprite, base, f"{TAG}-w{i}", metallic=0.05, roughness=0.12,
                                     emission_strength=1.0, frames=frames)
             for i, (base, frames) in enumerate(panes)]
    glass = T.Part("glass", smooth_angle=10.0)
    for i, (r0, r1) in enumerate(((8.0, 14.0), (16.0, 22.0), (25.0, 30.0))):
        cbox(glass, 16.8, 23.0, P_FRONT - 1.4, P_FRONT - 0.6, hw(r1), hw(r0), 0.05, i)
    gobj = finish(glass, gmats, coll, f"{NAME}_glass")
    return obj, gobj


def oblique_extras(obj, top_px, r0):
    obj["tyrian_oblique"] = [K, S, (A - r0 - 14.0) * PX]
    obj["tyrian_depth_band"] = [0.0, 0.4, 0.0, top_px * PX]


def cut_piece(obj, name, c0, r0, coll, cap):
    """The part of an upright model whose ART rows [r0, r0 + 28) and columns [c0, c0 + 24) it draws
    (plane S Y + K Z = const: a screen row), about the piece's own centre."""
    f = lambda r: (A * (1 - S) + 28 * S - r) / 12  # noqa: E731
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    planes = []
    if r0 > 0:
        planes.append(((0, f(r0) / S, 0), (0, S, K)))
    if r0 + 28 < 56:
        planes.append(((0, f(r0 + 28) / S, 0), (0, -S, -K)))
    planes.append((((c0 - 24) / 12, 0, 0), (-1, 0, 0)))
    planes.append((((c0 + 24 - 24) / 12, 0, 0), (1, 0, 0)))
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        if cap:
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    if not bm.faces:
        bm.free()
        return None
    bmesh.ops.translate(bm, vec=(-(c0 + 12 - 24) / 12, (r0 + 14 - 28) / 12, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in obj.data.materials:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35.0))
    return o


def main():
    names = [n for n, _, _ in PIECES]
    sprite = lib.merged_sprite(WT, names)
    coll = common.reset_collection(NAME)
    body, glass = build(sprite, coll)
    # Outline shell from a sealed copy made before the hidden faces are culled (D90, D118).
    sealed = body.copy()
    sealed.data = body.data.copy()
    coll.objects.link(sealed)
    shell = common.outline_shell(sealed, coll, voxel=0.02, faces=5000)
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    T.cull_hidden(body, grid=3, ndirs=32)
    top_px = max((v.co.z for v in body.data.vertices)) * 12
    render_dir = Path(sys.argv[sys.argv.index("--render") + 1]) if "--render" in sys.argv else None
    if render_dir:
        sys.path.append(os.environ.get("TYRIAN_RENDER_VIEWS", str(Path(__file__).resolve().parent)))
        import render_views
        for o in (body, glass, shell):
            oblique_extras(o, top_px, 28)
        render_views.render_all(render_dir, body, glass, shell, S, K, A)
    tris = {}
    placed = []
    for n, c0, r0 in PIECES:
        objs = []
        for src, nm, cap in ((body, n, True), (glass, n + "_glass", True), (shell, n + "_outline", False)):
            o = cut_piece(src, nm, c0, r0, coll, cap)
            if o is None:
                continue
            oblique_extras(o, top_px, r0)
            if src is shell:
                o["tyrian_outline"] = True
            objs.append(o)
        tris[n] = sum(len(o.data.polygons) for o in objs)
        data = common.load_sprite(ROOT, n)
        common.export_sprite_model(ROOT, objs, f"enemies/{n}", data["sprites"])
        if render_dir:  # placed back only AFTER the export: the glb pieces stay about their centres
            for o in objs:
                if not o.get("tyrian_outline"):
                    o.location = ((c0 + 12 - 24) / 12, -(r0 + 14 - 28) / 12, 0)
                    placed.append(o)
    if render_dir:  # the pieces put back where they were cut: the art view must match the whole's
        for o in (body, glass, shell):
            o.hide_render = True
        for o in placed:
            o.hide_render = False
        scene = bpy.context.scene
        art = bpy.data.objects["art"]
        render_views._render(scene, art, render_dir / "art_mask_pieces.png", 480, 560, transparent=True)
    print("H_T", H_T, "top_px", top_px, "faces", tris)


if __name__ == "__main__":
    main()
