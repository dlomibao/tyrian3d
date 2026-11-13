"""Purple gunship with a blue emblem (newshv.shp frame 161, 24x28, one frame), a hard-surface flyer.

Identity (brief): type 817, spawned from the bottom (groundBottom) in MARKERS, own motion (0,-2) px/tick
against a ground scroll of 1, ev20 swoops: it climbs the screen nose first. So the top of the sprite
is the NOSE and the red lamp at the bottom is the STERN light. Built flying free, round closed belly.

Reading of the sprite (inner mask: the ink ring is the game's own outline, D74):
- Hood (rows 3-14, pal 84-93, median 88): a purple crescent cowl wrapping the nose, split at the
  very front by a two-pixel V notch (rows 3-4). Its inner edge is a lit crest (91-93: sheen on the
  crest), its outer band darker (84-86). A red light strip (113-118) runs along each outer flank,
  rows 5-11, one pixel inside the edge.
- Side pods (rows 10-16, columns 0-3): the hood's flanks run back into two short nacelles whose
  tips stop at row 17, a notch (rows 13-16, column 4-6) between them and the hull.
- Glyph (rows 4-15): a chunky blue oval emblem (147 top, 148 chamfer) set between the hood halves,
  one crown with the hood from row 4 down, with a swirl slot cut through it at exactly the sprite's
  transparent pixels (the ground shows through). Its dark-blue pixels are the glyph's colour, not ink.
- Hull (rows 14-26, pal 99-111, median 104): blue-steel body, a raised centre spine (cols 11-12)
  between two dark seams (cols 10, 13), lit shoulder ridges (107-111 diagonals), widening to the
  claws. Struts at rows 20 and 23 (the grey pixels in column 3) tie the claws to the hull.
- Canopy (rows 20-25): a cyan glass dome (52-62, median 56) in a dark collar (52).
- Stern lamp (rows 24-27, columns 10-13): a red glowing tail light (115-117; its forward top 120),
  its hot head showing behind the canopy at row 24 and its tail nub at row 27.
- Claws (rows 18-27, columns 1-4 and 19-22, pal 88): chunky curved purple arms hugging the hull, tips
  curling in at row 27.
- Rear fins (row 25-26, columns 6-7 and 16-17).
- Underside: the parts' round closed bellies; nothing else.

Run: blender --background --factory-startup --python assets/blender/enemies/newshv-161.py -- [--views DIR] [--no-bake]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT

HERE = Path(__file__).resolve().parent
NAME = "newshv-161"
MODEL = "enemies/newshv-161"
PX = 1 / 12

pchip = T.pchip

# --- materials: slot name -> (palette index, metallic, roughness, emission) -------------------------
MATS = [
    ("hood", 88, 0.35, 0.42, 0.0),
    ("hood_flank", 85, 0.35, 0.46, 0.0),
    ("hood_crest", 91, 0.4, 0.38, 0.0),
    ("pod", 85, 0.35, 0.44, 0.0),
    ("red", 115, 1.0, 0.9, 1.0),
    ("lip", 148, 0.55, 0.28, 0.0),
    ("liner", 145, 0.4, 0.45, 0.0),
    ("vane", 147, 0.55, 0.3, 0.0),
    ("hull", 104, 0.55, 0.36, 0.0),
    ("hull_side", 102, 0.55, 0.4, 0.0),
    ("spine", 105, 0.6, 0.32, 0.0),
    ("seam", 100, 0.3, 0.6, 0.0),
    ("shoulder", 107, 0.6, 0.3, 0.0),
    ("dome", 56, 0.3, 0.12, 0.0),
    ("collar", 52, 0.4, 0.45, 0.0),
    ("lamp", 115, 1.0, 0.9, 1.0),
    ("lamp_hot", 120, 1.0, 0.9, 1.0),
    ("claw", 88, 0.35, 0.42, 0.0),
    ("strut", 102, 0.5, 0.45, 0.0),
    ("fin", 102, 0.55, 0.4, 0.0),
]
M = {n: i for i, (n, *_r) in enumerate(MATS)}
GLOW = {M["red"], M["lamp"], M["lamp_hot"]}


def W(p):
    """sprite px (x = column edge, y = row edge, z up px) -> Blender units (origin = sprite centre)."""
    return Vector(((p[0] - 12) * PX, (14 - p[1]) * PX, p[2] * PX))


class Part:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(W(p))

    def f(self, vs, mat):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def obj(self, coll, mats):
        bm = self.bm
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(self.name, me)
        coll.objects.link(o)
        return o


def tube(P, rings, mats, cap0=True, cap1=True):
    def mat(i, k):
        return mats(i, k) if callable(mats) else mats
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        n = len(r0)
        for k in range(n):
            j = (k + 1) % n
            P.f((r0[k], r0[j], r1[j], r1[k]), mat(i, k))
    if cap0:
        P.f(list(reversed(rings[0])), mat(0, 0))
    if cap1:
        P.f(rings[-1], mat(len(rings) - 2, 0))


def catmull(pts, per=8):
    """Densify a polyline with a Catmull-Rom spline through its points."""
    pts = [Vector(p) for p in pts]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def pair_stations(pairs, per=4):
    """Inner/outer edge pairs -> densified matching stations (both edges splined with one t)."""
    a = catmull([p[0] for p in pairs], per)
    b = catmull([p[1] for p in pairs], per)
    return list(zip(a, b))


def edge_loft(P, stations, prof, mats, cap0=True, cap1=True):
    """Loft sections spanning inner A -> outer B. prof(i, n) -> [(s, z), ...] closed loop."""
    rings = []
    n = len(stations)
    for i, (a, b) in enumerate(stations):
        ring = []
        for s, z in prof(i / (n - 1)):
            q = a.lerp(b, s)
            ring.append(P.v((q.x, q.y, z)))
        rings.append(ring)
    tube(P, rings, mats, cap0, cap1)
    return rings


def y_loft(P, ys, section, mats, cap0=True, cap1=True):
    """Loft along y: section(y) -> [(x, z), ...] closed loop."""
    rings = [[P.v((x, y, z)) for x, z in section(y)] for y in ys]
    tube(P, rings, mats, cap0, cap1)
    return rings


def path_tube(P, pts, rx, rz, sides, mat, z_of=None):
    """A tube along a plan path (x, y, z), its section an ellipse rx (plan) x rz (up)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        side = Vector((-t.y, t.x, 0))
        r1 = rx[i] if isinstance(rx, (list, tuple)) else rx
        r2 = rz[i] if isinstance(rz, (list, tuple)) else rz
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            q = p + side * (math.cos(ang) * r1) + Vector((0, 0, math.sin(ang) * r2))
            ring.append(P.v(tuple(q)))
        rings.append(ring)
    tube(P, rings, mat)
    return rings


def ellipsoid(P, c, rx, ry, rz, mat_of, nu=20, nv=8, zmin=0.0):
    """Upper half-ellipsoid (z >= c.z) closed by a flat base; mat_of(x, y, z) -> slot."""
    cx, cy, cz = c
    rings = []
    for j in range(nv):
        v = (math.pi / 2) * j / nv
        ring = []
        for k in range(nu):
            u = 2 * math.pi * k / nu
            ring.append((cx + rx * math.cos(v) * math.cos(u), cy + ry * math.cos(v) * math.sin(u), cz + rz * math.sin(v)))
        rings.append(ring)
    vr = [[P.v(p) for p in r] for r in rings]
    top = P.v((cx, cy, cz + rz))
    for j in range(nv - 1):
        for k in range(nu):
            kk = (k + 1) % nu
            pts = (rings[j][k], rings[j][kk], rings[j + 1][kk], rings[j + 1][k])
            ctr = [sum(p[i] for p in pts) / 4 for i in range(3)]
            P.f((vr[j][k], vr[j][kk], vr[j + 1][kk], vr[j + 1][k]), mat_of(*ctr))
    for k in range(nu):
        kk = (k + 1) % nu
        P.f((vr[-1][k], vr[-1][kk], top), mat_of(cx, cy, cz + rz))
    # skirt down to zmin and a flat base
    base = [P.v((p[0], p[1], zmin)) for p in rings[0]]
    for k in range(nu):
        kk = (k + 1) % nu
        P.f((base[k], base[kk], vr[0][kk], vr[0][k]), mat_of(rings[0][k][0], rings[0][k][1], cz))
    P.f(list(reversed(base)), mat_of(cx, cy, zmin))


def cbox_part(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    pts = T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)
    bm = P.bm
    vs = [bm.verts.new(W(p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in vs if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1.0), verts=live,
                             edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in vs if v.is_valid for f in v.link_faces}:
        f.material_index = mat


# --- the hood ----------------------------------------------------------------------------------------
# (inner, outer) plan pairs, rear -> front, left half. Inner = the duct lip / hull junction.
OUT_L = [(0.0, 12.4), (0.0, 10.6), (0.7, 9.95), (1.1, 8.85), (1.95, 7.55), (2.95, 6.5), (3.95, 5.5),
         (5.0, 4.5), (6.6, 3.85), (8.3, 3.0), (11.0, 3.0)]
IN_L = [(8.0, 15.2), (8.0, 13.4), (8.0, 11.6), (8.0, 10.2), (8.4, 9.1), (9.2, 8.2), (10.0, 7.4), (10.7, 6.6),
        (11.0, 5.8), (11.0, 5.1), (11.0, 4.9)]
# Right half: outer mirrored, inner follows the duct's right rim (the glyph is asymmetric).
IN_R = [(16.0, 15.2), (16.0, 13.4), (16.0, 11.6), (16.0, 10.2), (15.6, 9.2), (14.8, 8.3), (13.9, 7.4),
        (13.2, 6.6), (13.0, 5.8), (13.0, 5.1), (13.0, 4.9)]
HOOD_L = list(zip(IN_L, OUT_L))
HOOD_R = [(i, (24 - o[0], o[1])) for i, o in zip(IN_R, OUT_L)]
# The notch between each side pod and the hull (rows 13-16, columns 4-6), cut out of the hood.
NOTCH = [(4.05, 18.0), (4.05, 13.05), (4.5, 12.95), (4.95, 13.05), (5.2, 13.8), (5.85, 14.1), (6.15, 14.9),
         (7.1, 15.0), (7.1, 18.0)]


def hood_prof(t):
    zt = float(pchip([0.0, 0.3, 0.7, 1.0], [5.0, 5.9, 5.8, 4.9])(t))
    ze = float(pchip([0.0, 0.5, 1.0], [2.9, 2.8, 2.4])(t))
    return [(0.0, 1.2), (0.0, zt - 0.85), (0.05, zt - 0.14), (0.14, zt), (0.35, zt - 0.15),
            (0.55, zt - 0.7), (0.72, ze + 1.15), (0.86, ze + 0.6), (0.955, ze + 0.14),
            (1.0, ze - 0.4), (1.0, 1.1), (0.96, 0.55), (0.6, 0.25), (0.25, 0.3), (0.03, 0.65)]


def hood_mat(right):
    def m(i, k):
        # k indexes the profile points: 0-1 inner wall, 1-4 crest, 5-8 flank, 9-10 outer wall, rest belly
        if k == 0:
            return M["liner"] if right else M["hood"]
        if k in (1, 2):
            return M["hood_crest"]
        if k in (6, 7, 8, 9):
            return M["hood_flank"]
        return M["hood"]
    return m


def build_hood(P):
    for pairs, right in ((HOOD_L, False), (HOOD_R, True)):
        st = pair_stations(pairs, per=3)
        edge_loft(P, st, hood_prof, hood_mat(right))


# --- side pods ---------------------------------------------------------------------------------------
POD_XL = pchip([9.8, 14.75, 15.15, 16.0, 16.6, 17.0], [0.0, 0.0, 0.85, 1.3, 1.95, 2.6])
POD_XR = pchip([9.8, 16.2, 16.7, 17.0], [4.0, 4.0, 3.8, 3.45])


def pod_section(y):
    x0, x1 = float(POD_XL(y)), float(POD_XR(y))
    zt = float(pchip([9.8, 13.0, 16.0, 17.0], [3.6, 3.7, 3.3, 2.7])(y))
    w = x1 - x0
    c = min(0.5, w * 0.25)
    zb = 0.6
    return [(x0, zb + 0.35), (x0, zt - c), (x0 + c, zt), (x1 - c, zt), (x1, zt - c), (x1, zb + 0.35),
            (x1 - c, zb), (x0 + c, zb)]


def build_pods(P):
    ys = [9.8, 11.0, 12.5, 14.0, 14.7, 15.1, 15.5, 15.9, 16.3, 16.65, 16.9, 17.0]
    rings = [[(x, y, z) for x, z in pod_section(y)] for y in ys]
    for mirror in (False, True):
        vr = [[P.v(((24 - x) if mirror else x, y, z)) for x, y, z in r] for r in rings]
        tube(P, vr, M["pod"])


# --- the blue glyph: a chunky blue oval emblem between the hood halves, a swirl slot through it ----------
# Plan half-width about x = 12 per y (rows 4-6 cols 11-12, row 7 cols 10-13, row 8 cols 9-14, rows 9-13
# cols 8-15, row 14 cols 9-14, row 15 cols 10-13). It tucks 0.15 px under the hood's inner walls.
EMB_HW = pchip([3.95, 6.9, 7.6, 8.5, 9.3, 13.8, 14.6, 15.5, 16.05],
               [1.15, 1.15, 2.05, 3.05, 4.1, 4.1, 3.05, 2.05, 1.5])
EMB_ZC = pchip([3.95, 7.0, 10.0, 13.0, 14.5, 16.05], [4.45, 4.6, 4.9, 5.3, 5.85, 6.0])


def emb_section(y):
    hw, zc = float(EMB_HW(y)), float(EMB_ZC(y))
    ze = zc - 0.4
    c = min(0.28, hw * 0.25)
    xl, xr = 12 - hw, 12 + hw
    return [(xl, 1.0), (xl, ze - c), (xl + c, ze), (12 - hw * 0.5, zc - 0.1), (12.0, zc),
            (12 + hw * 0.5, zc - 0.1), (xr - c, ze), (xr, ze - c), (xr, 1.0), (12.0, 0.8)]


def emb_mat(i, k):
    if k in (3, 4):
        return M["vane"]
    if k in (1, 2, 5, 6):
        return M["lip"]
    return M["liner"]


def build_emblem(P):
    ys = [3.95 + 0.5 * i for i in range(24)] + [16.05]
    y_loft(P, ys, emb_section, emb_mat)


# The swirl slot (the sprite's own transparent pixels inside the glyph: (row,col) (7,12) (8,13) (9,14)
# (10-13,14) (14,10-13) (13,10) (12,11) (11,11-12) (10,12)), a 1.05 px band along their centres, cut
# through the emblem and the hull nose so the ground shows through it.
SLOT = [(12.15, 7.15), (12.5, 7.5), (14.5, 9.5), (14.5, 13.5), (13.5, 14.5), (10.5, 14.5), (10.5, 13.5),
        (11.5, 12.5), (11.5, 11.5), (12.5, 11.5), (12.5, 10.5), (12.5, 10.12)]


def band_poly(path, hw):
    """Mitred offset outline of a polyline (plan), as one closed polygon."""
    P = [Vector((x, y)) for x, y in path]
    L, R = [], []
    n = len(P)
    for i in range(n):
        d0 = (P[i] - P[i - 1]).normalized() if i > 0 else None
        d1 = (P[i + 1] - P[i]).normalized() if i < n - 1 else None
        if d0 is None:
            d0 = d1
        if d1 is None:
            d1 = d0
        t = (d0 + d1).normalized()
        nrm = Vector((-t.y, t.x))
        k = hw / max(0.35, nrm.dot(Vector((-d1.y, d1.x))))
        L.append(P[i] + nrm * k)
        R.append(P[i] - nrm * k)
    return [(v.x, v.y) for v in L + list(reversed(R))]


def prism_cutter(coll, mat, poly, smooth=True):
    P = Part("cutter")
    pts = catmull(poly + [poly[0]], 3)[:-1] if smooth else [Vector(p) for p in poly]
    lo = [P.v((p.x, p.y, -3.0)) for p in pts]
    hi = [P.v((p.x, p.y, 12.0)) for p in pts]
    n = len(pts)
    for k in range(n):
        j = (k + 1) % n
        P.f((lo[k], lo[j], hi[j], hi[k]), 0)
    P.f(list(reversed(lo)), 0)
    P.f(hi, 0)
    return P.obj(coll, [mat])


# --- hull ------------------------------------------------------------------------------------------
HULL_HW = pchip([13.9, 15.0, 16.0, 17.0, 18.5, 19.3, 20.0, 24.3, 25.2, 25.6, 25.95],
                [5.0, 5.0, 5.6, 6.6, 7.0, 7.7, 8.0, 8.0, 7.4, 7.0, 6.3])
HULL_ZT = pchip([13.9, 16.0, 18.0, 22.0, 25.0, 25.95], [4.6, 5.6, 6.0, 6.1, 5.4, 4.6])
HULL_ZS = pchip([13.9, 20.0, 24.0, 25.95], [3.4, 3.6, 3.4, 3.0])


def hull_section(y):
    hw = float(HULL_HW(y))
    zt, zs = float(HULL_ZT(y)), float(HULL_ZS(y))
    half = [(0.0, -0.3), (0.5, -0.05), (0.85, 0.45), (0.98, 1.05), (1.0, 1.7), (1.0, zs - 0.4), (0.93, zs),
            (0.75, zs + 0.5 * (zt - zs)), (0.45, zt - 0.1), (0.2, zt)]
    right = [(12 + f * hw, z) for f, z in half]
    left = [(12 - f * hw, z) for f, z in reversed(half[1:])]
    top = [(12.0, zt)]
    return right + top + left


def hull_mat(i, k):
    # ring order: 0 belly centre .. 4 lower wall, 5-6 wall/shoulder, 7-9 top, 10 crest, mirrored
    n = 20
    kk = k if k <= 10 else n - k
    if kk <= 4:
        return M["hull_side"]
    if kk in (5, 6):
        return M["hull_side"]
    return M["hull"]


def build_hull(P):
    ys = [13.9, 14.6, 15.4, 16.2, 17.0, 17.8, 18.6, 19.4, 20.2, 21.2, 22.2, 23.2, 24.2, 24.9, 25.4, 25.75, 25.95]
    y_loft(P, ys, hull_section, hull_mat)


# --- surface helpers (raycast onto parts built so far) -----------------------------------------------
def surface(objs):
    trees = []
    for o in objs:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        trees.append(BVHTree.FromBMesh(bm))
        bm.free()

    def z_at(x, y):
        best = None
        for tr in trees:
            hit = tr.ray_cast(W((x, y, 40.0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                z = hit[0].z / PX
                best = z if best is None else max(best, z)
        return best if best is not None else 0.0
    return z_at


def build_details(P, z_hood, z_hull):
    # Red light strips along the hood flanks, rows 5-11, one pixel inside the edge.
    strip = [(6.6, 5.4), (5.5, 6.5), (4.5, 7.5), (3.5, 8.5), (2.65, 9.5), (2.45, 10.5), (2.45, 11.55)]
    pts = catmull(strip, 3)
    for mirror in (False, True):
        pp = [((24 - p.x) if mirror else p.x, p.y) for p in pts]
        path_tube(P, [(x, y, z_hood(x, y) - 0.12) for x, y in pp], 0.48, 0.32, 8, M["red"])
    # Centre spine (cols 11-12) and the dark seams either side (cols 10, 13).
    ztop = max(z_hull(12, y) for y in (16.5, 18.0, 20.0))
    cbox_part(P, 11.0, 13.0, 16.2, 20.6, 2.0, ztop + 0.55, 0.3, M["spine"], chz=0.3)
    for x0 in (10.15, 13.15):
        pts = [(x0 + 0.35, y, z_hull(x0 + 0.35, y) - 0.05) for y in (16.5, 17.7, 19.0, 20.3)]
        path_tube(P, pts, 0.33, 0.12, 6, M["seam"])
    # Shoulder ridges (the lit 107-111 diagonals), raised armour strakes.
    ridge = catmull([(7.7, 16.3), (6.7, 17.5), (5.9, 18.9), (5.15, 20.6), (4.85, 22.4)], 3)
    for mirror in (False, True):
        pp = [((24 - p.x) if mirror else p.x, p.y) for p in ridge]
        n = len(pp)
        rx = [float(pchip([0, 0.2, 0.8, 1], [0.35, 0.65, 0.6, 0.35])(i / (n - 1))) for i in range(n)]
        path_tube(P, [(x, y, z_hull(x, y) - 0.05) for x, y in pp], rx, 0.4, 8, M["shoulder"])
    # Struts to the claws (rows 20 and 23, the grey pixels of column 3).
    for y in (20.5, 23.5):
        for mirror in (False, True):
            xa, xb = (2.95, 4.8) if not mirror else (21.05, 19.2)
            path_tube(P, [(xa, y, 3.4), (xb, y, 3.4)], 0.42, 0.55, 8, M["strut"])
    # Rear fins (rows 25-26, cols 6-7 / 16-17).
    for x0, x1 in ((5.9, 8.0), (16.0, 18.1)):
        cbox_part(P, x0, x1, 24.6, 27.0, 0.9, 3.4, 0.35, M["fin"], chz=0.3)


def build_claws(P):
    # chunky purple claws (cols 1-3 rows 19-25, curling to col 4 at row 27), rooted on the hull at row 18
    path = [(4.95, 18.75), (3.2, 19.6), (2.55, 20.5), (2.45, 22.0), (2.5, 23.5), (2.75, 24.8), (3.3, 25.8),
            (4.2, 26.75), (4.85, 27.62)]
    pts = catmull(path, 2)
    n = len(pts)
    ks = [k / 8 for k in range(9)]
    rx = [float(pchip(ks, [0.45, 0.8, 1.45, 1.5, 1.5, 1.6, 1.45, 0.88, 0.42])(i / (n - 1))) for i in range(n)]
    rz = [min(1.25, r * 0.9) for r in rx]
    zc = [float(pchip([0, 0.5, 1.0], [2.9, 2.8, 2.5])(i / (n - 1))) for i in range(n)]
    for mirror in (False, True):
        pp = [((24 - p.x) if mirror else p.x, p.y, z) for p, z in zip(pts, zc)]
        path_tube(P, pp, rx, rz, 10, M["claw"])


def build_canopy(P, z_hull):
    zb = z_hull(12, 22.4) - 0.35
    # collar ring (dark 52), then the cyan glass dome
    ellipsoid(P, (12.0, 23.0, zb), 5.0, 2.9, 0.6, lambda x, y, z: M["collar"], nu=20, nv=3, zmin=zb - 1.0)
    ellipsoid(P, (12.0, 22.4, zb + 0.4), 3.9, 2.0, 1.8, lambda x, y, z: M["dome"], nu=20, nv=6,
              zmin=zb - 0.8)
    # stern lamp: a capsule along y, its forward top hot (120)
    cz = 5.0
    r = 1.7
    lx = 12.0
    ys = [22.8, 23.6, 24.3, 25.0, 25.8, 26.6]
    rings = []
    secs = []
    for y in ys:
        secs.append((y, r))
    for j in range(1, 6):
        a = (math.pi / 2) * j / 6
        secs.append((26.6 + r * math.sin(a) * 0.74, r * math.cos(a)))
    nu = 12
    for y, rr in secs:
        rings.append([P.v((lx + rr * math.cos(2 * math.pi * k / nu), y, cz + rr * math.sin(2 * math.pi * k / nu)))
                      for k in range(nu)])
    tip = P.v((lx, 26.6 + r * 0.74, cz))

    def lm(i, k):
        y = secs[i][0]
        up = math.sin(2 * math.pi * (k + 0.5) / nu) > 0.35
        return M["lamp_hot"] if (y < 25.0 and up) else M["lamp"]
    tube(P, rings, lm, cap0=True, cap1=False)
    # grey bezel ring round the lens where it leaves the hull
    nb = 12
    bez = []
    for y in (24.75, 25.05, 25.35):
        rr = r + (0.28 if y == 25.05 else 0.12)
        bez.append([P.v((lx + rr * math.cos(2 * math.pi * k / nb), y, cz + rr * math.sin(2 * math.pi * k / nb)))
                    for k in range(nb)])
    tube(P, bez, M["hull_side"])
    for k in range(nu):
        P.f((rings[-1][k], rings[-1][(k + 1) % nu], tip), M["lamp"])


def materials(sprite):
    out = []
    for name, idx, metal, rough, glow in MATS:
        out.append(common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=metal, roughness=rough,
                                           emission_strength=glow))
    return out


def boolean(obj, cutter):
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "EXACT"
    try:
        mod.material_mode = "TRANSFER"
    except Exception:
        pass
    bpy.context.view_layer.update()
    common._apply_modifiers(obj)


def build(sprite, coll):
    mats = materials(sprite)
    hood = Part("hood")
    build_hood(hood)
    build_pods(hood)
    hood_o = hood.obj(coll, mats)
    notch_l = prism_cutter(coll, mats[M["hood_flank"]], NOTCH, smooth=False)
    boolean(hood_o, notch_l)
    bpy.data.objects.remove(notch_l, do_unlink=True)
    notch_r = prism_cutter(coll, mats[M["hood_flank"]], [(24 - x, y) for x, y in reversed(NOTCH)], smooth=False)
    boolean(hood_o, notch_r)
    bpy.data.objects.remove(notch_r, do_unlink=True)
    hull = Part("hull")
    build_hull(hull)
    hull_o = hull.obj(coll, mats)
    emb = Part("emblem")
    build_emblem(emb)
    emb_o = emb.obj(coll, mats)
    slot = band_poly(SLOT, 0.525)
    for o in (hull_o, emb_o):
        cutter = prism_cutter(coll, mats[M["liner"]], slot, smooth=False)
        boolean(o, cutter)
        bpy.data.objects.remove(cutter, do_unlink=True)
    z_hood = surface([hood_o])
    z_hull = surface([hull_o])
    det = Part("detail")
    build_details(det, z_hood, z_hull)
    build_claws(det)
    build_canopy(det, z_hull)
    det_o = det.obj(coll, mats)
    bpy.context.view_layer.update()
    obj = T.join([hood_o, hull_o, emb_o, det_o], NAME)
    common._apply_modifiers(obj)
    # materials can be duplicated by the boolean transfer; map slots back by name
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(35))
    return obj


def bake(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    names = [m.name for m in obj.data.materials]
    glow_names = {f"pal_{MATS[i][1]}_{NAME}_{MATS[i][0]}" for i in GLOW}
    T.TINT = (0.98, 0.98, 1.0)
    T.TEXTURED = tuple(i for i, n in enumerate(names) if n not in glow_names)
    try:
        T.bake_maps(obj, out_dir, size=512, samples=96)
    finally:
        T.TINT, T.TEXTURED = tint, textured


# --- views and measurements (scratch only) ---------------------------------------------------------

def pal_grid(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(deps)
    rows = []
    for r in range(28):
        row = []
        for c in range(24):
            hit, loc, nrm, fi = ev.ray_cast(W((c + 0.5, r + 0.5, 40.0)), Vector((0, 0, -1)))
            if not hit:
                row.append(-1)
                continue
            m = obj.data.materials[obj.data.polygons[fi].material_index]
            row.append(int(m.name.split("_")[1]))
        rows.append(row)
    return rows


def cam(scene, name, loc, look, ortho=None, lens=50):
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return c


def top_mask(obj, out):
    scene = bpy.context.scene
    for o in scene.objects:
        o.hide_render = o is not obj
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError:
        pass
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    K = 10
    scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
    scene.render.resolution_percentage = 100
    c = cam(scene, "top_mask", (0, 0, 10), (0, 0, 0), ortho=28 / 12)
    c.rotation_euler = (0, 0, 0)
    scene.camera = c
    scene.render.filepath = str(out / "top_mask.png")
    bpy.ops.render.render(write_still=True)


def lit_views(obj, out):
    scene = bpy.context.scene
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o is not obj
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.16, 0.18, 0.2, 1)
    bg.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(35), math.radians(-25), math.radians(20))
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "SUN"))
    fill.data.energy = 0.8
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-60), math.radians(40), 0)
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.25))
    g = bpy.context.active_object
    g.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.12, 0.1, 0.07, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    zc = 3.0 * PX
    tilt = math.radians(32)
    views = {
        "top": ((0, 0, d), 2.6, (0, 0, 0)),
        "side": ((d, 0, zc), 2.6, (0, 0, zc)),
        "front": ((0, d, zc), 2.6, (0, 0, zc)),
        "rear": ((0, -d, zc), 2.6, (0, 0, zc)),
        "q34": ((d * 0.6, d * 0.6, d * 0.65), None, (0, 0, zc)),
        "q34b": ((-d * 0.65, -d * 0.45, d * 0.55), None, (0, 0, zc)),
        "game": ((0, -d * math.sin(tilt), d * math.cos(tilt)), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        g.hide_render = name in ("under", "side", "front", "rear")
        c = cam(scene, f"v_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        scene.render.filepath = str(out / f"v_{name}.png")
        bpy.ops.render.render(write_still=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(WT, NAME)
    coll = common.reset_collection(NAME)
    views = Path(argv[argv.index("--views") + 1]) if "--views" in argv else None
    obj = build(sprite, coll)
    sh = common.outline_shell(obj, coll, voxel=0.012, faces=1000, smooth=8)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles, shell {len(sh.data.polygons)} faces")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask(obj, views)
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
        (views / "stats.json").write_text(json.dumps({"tris": tris}))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        sh.hide_render = True
        try:
            bake(obj, Path(tempfile.mkdtemp(prefix="nshv161A_bake_")))
        finally:
            sh.hide_render = False
        fmt = "WEBP"
    common.export_sprite_model(ROOT, [obj, sh], MODEL, sprite["sprites"], image_format=fmt)
    if views:
        sh.hide_render = True
        lit_views(obj, views)


if __name__ == "__main__":
    main()
