"""Green armoured crawler (newshj.shp frame 117, 24x28, one frame), .

WHAT IT IS: a tracked ground vehicle of the TORM jungle (types 760/761, armour 40). Events move it
along the ground layer faster than the scroll ('swooping (0,+1)', ev20 y +1..+5), so it drives DOWN
the screen: the keel point at the bottom of the sprite is the NOSE, the crossbar is the REAR. It
stands on the HD ground at z 0 on two track units (no pixel floor plate, D130).

Reading the sprite (row/col = sprite pixel; the mask is near-borderless, so inner ~ outer):
- Rear transverse housing ("crossbar", rows 2-8, cols 2-22, pal 33-47, median 38): a wide drum
  across the back, rounded ends, its crown lit (rows 2-5) and its front darker (rows 6-8): a
  crowned section. The bright column at col 6 rows 2-5 is the lit face of a raised band (rib)
  round the drum; the matching rib at col 18 faces away from the light. Its front edge drops to
  row 9 only at the very ends (cols 3 and 21), hugging the side pods' rear corners.
- Hull (rows 4-26, cols 8-16, median 37): keel-shaped, a crowned roof rising out of the housing
  (the light spine col 12 rows 5-10 is a single crest) that splits into two lit rails (cols 11 and
  13, rows 10-17) with a channel between them; it tapers to a point at row 26 (the nose, lower).
- Side pods (rows 8-21, cols 4-7 and 17-20, red 113-118, median 115-117 -> 116): armoured red
  sponsons over the tracks, their front ends swept in toward the hull (rows 20-21). On top of each
  a glowing vent slot (rows 13-17, col 6 / col 18-19: 118-124, hot 124/255 at row 15-16) and a
  small glowing port at row 10 (123 / 122). Dark 240 seams at col 17 are the pod/hull crease in
  shadow (lighting, not paint).
- Exhaust housing (rows 0-1, cols 6-17, red, median 117) behind the drum, with two glowing exhaust
  ports (row 1, cols 8-10 and 14-15: 120-124) angled up and back.
- Underside: a closed belly, the tracks below the pods; nothing else.

Mirror axis x = 12.5 (column edges): drum 2..23, hull 8..17, pods 4..8 / 17..21; the exhaust
housing is drawn 7..17 / 6..18 (centre 12), so it sits at 12.2.

Run: blender --background --python assets/blender/enemies/newshj-117.py [-- --views DIR]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

NAME = "newshj-117"
WT = common.repo_root(__file__)
MODEL = f"enemies/{NAME}"
PX = 1 / 12
AX = 12.5          # mirror axis (column edge)
CAPX = 12.2        # exhaust housing centre
pchip = T.pchip

# slot name -> (palette index, metallic, roughness, emission)
MATS = [
    ("drum", 38, 0.35, 0.45, 0.0),
    ("hull", 37, 0.35, 0.45, 0.0),
    ("crest", 40, 0.4, 0.4, 0.0),
    ("seam", 33, 0.2, 0.7, 0.0),
    ("rib", 38, 0.45, 0.38, 0.0),
    ("pod", 116, 0.35, 0.45, 0.0),
    ("pod_dk", 114, 0.3, 0.5, 0.0),
    ("cap", 117, 0.35, 0.45, 0.0),
    ("nozzle", 115, 0.45, 0.4, 0.0),
    ("glow", 122, 1.0, 0.9, 1.0),
    ("hot", 124, 1.0, 0.9, 1.0),
    ("port", 123, 1.0, 0.9, 1.0),
    ("track", 240, 0.2, 0.75, 0.0),
    ("wheel", 35, 0.4, 0.5, 0.0),
]
M = {n: i for i, (n, *_r) in enumerate(MATS)}


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


def path_tube(P, pts, rx, rz, sides, mat, closed=False):
    """A tube along a path (x, y, z); section an ellipse rx (sideways, in plan) x rz (up)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    for i, p in enumerate(pts):
        if closed:
            a, b = pts[(i - 1) % n], pts[(i + 1) % n]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
        t = Vector((b.x - a.x, b.y - a.y, 0))
        t = t.normalized() if t.length > 1e-9 else Vector((0, 1, 0))
        side = Vector((-t.y, t.x, 0))
        r1 = rx[i] if isinstance(rx, (list, tuple)) else rx
        r2 = rz[i] if isinstance(rz, (list, tuple)) else rz
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            q = p + side * (math.cos(ang) * r1) + Vector((0, 0, math.sin(ang) * r2))
            ring.append(P.v(tuple(q)))
        rings.append(ring)
    if closed:
        rings.append(rings[0])
        tube(P, rings, mat, cap0=False, cap1=False)
    else:
        tube(P, rings, mat)
    return rings


def ellipsoid(P, c, rx, ry, rz, mat, nu=16, nv=6, zmin=None):
    """Upper half-ellipsoid on centre c, skirted down to zmin and closed by a flat base."""
    cx, cy, cz = c
    zmin = cz if zmin is None else zmin
    vr = []
    for j in range(nv):
        v = (math.pi / 2) * j / nv
        vr.append([P.v((cx + rx * math.cos(v) * math.cos(2 * math.pi * k / nu),
                        cy + ry * math.cos(v) * math.sin(2 * math.pi * k / nu),
                        cz + rz * math.sin(v))) for k in range(nu)])
    top = P.v((cx, cy, cz + rz))
    for j in range(nv - 1):
        for k in range(nu):
            kk = (k + 1) % nu
            P.f((vr[j][k], vr[j][kk], vr[j + 1][kk], vr[j + 1][k]), mat)
    for k in range(nu):
        P.f((vr[-1][k], vr[-1][(k + 1) % nu], top), mat)
    base = [P.v((cx + rx * math.cos(2 * math.pi * k / nu), cy + ry * math.sin(2 * math.pi * k / nu), zmin))
            for k in range(nu)]
    for k in range(nu):
        kk = (k + 1) % nu
        P.f((base[k], base[kk], vr[0][kk], vr[0][k]), mat)
    P.f(list(reversed(base)), mat)


def cbox_part(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    pts = T.cbox(x0, x1, y0, y1, z0, z1, ch, chz)
    bm = P.bm
    vs = [bm.verts.new(W(p)) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    for f in {f for v in vs if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def mirror_pts(pts):
    return [(2 * AX - p[0], p[1], p[2]) for p in pts]


# --- hull (keel) --------------------------------------------------------------------------------
HULL_HW = pchip([3.0, 21.5, 22.5, 23.5, 24.5, 25.5, 26.5, 27.0], [4.6, 4.6, 4.45, 3.75, 3.3, 2.6, 1.6, 0.55])
HULL_ZR = pchip([3.0, 6.5, 10.0, 16.0, 20.0, 23.0, 25.5, 27.0], [7.0, 8.8, 8.8, 8.2, 7.4, 6.0, 4.4, 3.0])
HULL_ZC = pchip([3.0, 20.0, 23.0, 25.5, 27.0], [6.0, 6.3, 5.0, 3.6, 2.4])
HULL_ZB = pchip([3.0, 22.0, 27.0], [1.4, 1.4, 1.9])
ROOF_F = [0.96, 0.82, 0.66, 0.5, 0.34, 0.2, 0.08]


def roof_k(f):
    return 1.0 - min(1.0, f / 0.96) ** 1.6


def roof_z(xoff, y):
    hw, zr, zc = float(HULL_HW(y)), float(HULL_ZR(y)), float(HULL_ZC(y))
    return zc + (zr - zc) * roof_k(abs(xoff) / hw)


def hull_section(y):
    hw, zr, zc, zb = float(HULL_HW(y)), float(HULL_ZR(y)), float(HULL_ZC(y)), float(HULL_ZB(y))
    half = [(0.0, zb), (0.7, zb), (0.92, zb + 0.3), (1.0, zb + 0.8), (1.0, zc - 0.4)]
    half += [(f, zc + (zr - zc) * roof_k(f)) for f in ROOF_F]
    right = [(AX + f * hw, z) for f, z in half]
    left = [(AX - f * hw, z) for f, z in reversed(half[1:])]
    return right + [(AX, zr)] + left


def build_hull(P):
    ys = [3.0, 4.0, 5.0, 6.0, 7.5, 9.0, 10.5, 12.0, 13.5, 15.0, 16.5, 18.0, 19.5, 21.0, 22.0, 22.8, 23.5,
          24.2, 24.9, 25.5, 26.0, 26.5, 26.85, 27.0]
    rings = [[P.v((x, y, z)) for x, z in hull_section(y)] for y in ys]
    tube(P, rings, M["hull"])


def build_hull_detail(P):
    # Crest down the roof from the housing (rows 4-10), splitting into two rails (cols 11, 13, rows 10-17).
    ys = [4.0, 5.0, 6.5, 8.0, 9.5, 10.8, 11.4]
    crest = [(AX, y, roof_z(0, y)) for y in ys]
    rx = [0.25, 0.55, 0.6, 0.6, 0.6, 0.5, 0.25]
    rz = [0.25, 0.5, 0.55, 0.55, 0.55, 0.45, 0.25]
    path_tube(P, crest, rx, rz, 10, M["crest"])
    for s in (-1, 1):
        pts = catmull([(AX + s * 0.25, 10.0), (AX + s * 0.7, 10.9), (AX + s * 1.0, 12.0), (AX + s * 1.0, 15.0),
                       (AX + s * 1.0, 17.6)], 3)
        path = [(p.x, p.y, roof_z(p.x - AX, p.y)) for p in pts]
        n = len(path)
        rxl = [0.42 if 0 < i < n - 1 else 0.2 for i in range(n)]
        rzl = [0.42 if 0 < i < n - 1 else 0.2 for i in range(n)]
        path_tube(P, path, rxl, rzl, 8, M["crest"])
    # Transverse panel seams on the roof and the nose glacis line.
    for y in (12.0, 18.0, 22.0):  # on pixel edges: thin lines, no row of seam colour
        hw = float(HULL_HW(y))
        xs = [AX + hw * (-0.9 + 1.8 * i / 10) for i in range(11)]
        path_tube(P, [(x, y, roof_z(x - AX, y) - 0.02) for x in xs], 0.13, 0.1, 6, M["seam"])
    # Longitudinal chine bead along each side of the roof (where the roof meets the walls).
    for s in (-1, 1):
        ys2 = [9.0, 12.0, 15.0, 18.0, 21.0, 23.0, 24.8]
        path = [(AX + s * float(HULL_HW(y)) * 0.97, y, float(HULL_ZC(y)) + 0.05) for y in ys2]
        path_tube(P, path, 0.16, 0.16, 6, M["seam"])
    # Rivet rows along the chine beads (machined detail the tilted camera sees on the flanks).
    for s in (-1, 1):
        for i in range(6):
            y = 10.0 + 2.0 * i  # on pixel edges
            x = AX + s * float(HULL_HW(y)) * 0.86
            z = roof_z(x - AX, y)
            ellipsoid(P, (x, y, z - 0.05), 0.14, 0.14, 0.13, M["seam"], nu=6, nv=2)


# --- rear housing (crossbar) ---------------------------------------------------------------------
DX0, DX1 = 2.0, 23.0
DY0 = 2.0
DZB, DZT = 2.4, 7.6
DR = 2.0
FRONT = pchip([2.0, 3.6, 4.4, 5.3, 12.5, 19.7, 20.6, 21.4, 23.0], [9.85, 9.8, 8.9, 8.05, 8.05, 8.05, 8.9, 9.8, 9.85])
SEC = [(0.12, 0.0), (0.0, 0.16), (0.0, 0.5), (0.05, 0.76), (0.16, 0.92), (0.32, 1.0), (0.5, 1.02), (0.68, 1.0),
       (0.84, 0.92), (0.95, 0.76), (1.0, 0.5), (1.0, 0.16), (0.88, 0.0)]


def drum_span(x):
    d = min(x - DX0, DX1 - x)
    cut = DR - math.sqrt(max(0.0, DR * DR - (DR - d) ** 2)) if d < DR else 0.0
    zt = DZT
    if d < 1.4:
        zt = DZB + (DZT - DZB) * (0.5 + 0.5 * math.sqrt(max(0.0, 1 - (1 - d / 1.4) ** 2)))
    return DY0 + cut, float(FRONT(x)) - cut, zt


def drum_section(x, grow=0.0):
    y0, y1, zt = drum_span(x)
    y0, y1 = y0 - grow, y1 + grow
    zb, zt = DZB - grow * 0.5, zt + grow
    return [(x, y0 + u * (y1 - y0), zb + v * (zt - zb)) for u, v in SEC]


def drum_z(x, y):
    y0, y1, zt = drum_span(x)
    u = (y - y0) / (y1 - y0)
    us = [p[0] for p in SEC[3:10]]
    vs = [p[1] for p in SEC[3:10]]
    u = min(max(u, us[0]), us[-1])
    for i in range(len(us) - 1):
        if us[i] <= u <= us[i + 1]:
            t = (u - us[i]) / (us[i + 1] - us[i])
            v = vs[i] + t * (vs[i + 1] - vs[i])
            return DZB + v * (zt - DZB)
    return zt


def build_drum(P):
    xs = [2.0, 2.06, 2.2, 2.45, 2.8, 3.2, 3.7, 4.2, 4.8, 5.4, 6.0, 7.0, 8.5, 10.5, 12.5]
    xs = xs + [2 * AX - x for x in reversed(xs[:-1])]
    rings = [[P.v(p) for p in drum_section(x)] for x in xs]
    tube(P, rings, M["drum"])
    # raised bands round the drum (the lit edge at col 6, the shadowed one at col 18)
    for xc in (6.5, 2 * AX - 6.5):
        xs2 = [xc - 0.32, xc - 0.26, xc + 0.26, xc + 0.32]
        gs = [0.05, 0.2, 0.2, 0.05]
        rings = [[P.v(p) for p in drum_section(x, g)] for x, g in zip(xs2, gs)]
        tube(P, rings, M["rib"])
    # hatch plates on the end segments, and bolt heads
    for s in (-1, 1):
        xa, xb = (3.1, 5.7) if s < 0 else (2 * AX - 5.7, 2 * AX - 3.1)
        z = drum_z(0.5 * (xa + xb), 5.2)
        cbox_part(P, xa, xb, 3.5, 7.0, z - 0.7, z + 0.22, 0.2, M["drum"], 0.12)
        for bx in (xa + 0.35, xb - 0.35):
            for by in (3.85, 6.65):
                ellipsoid(P, (bx, by, z + 0.2), 0.16, 0.16, 0.12, M["seam"], nu=6, nv=2, zmin=z)
    # louvre grille on the drum's rear face (seen from behind), each side of the exhaust housing
    for xs3 in ((2.9, 6.0), (2 * AX - 6.0, 2 * AX - 2.9)):
        for i in range(4):
            zz = 3.6 + 0.85 * i
            cbox_part(P, xs3[0], xs3[1], DY0 - 0.12, DY0 + 0.35, zz, zz + 0.32, 0.08, M["seam"])


# --- exhaust housing ---------------------------------------------------------------------------
CAP_HW = pchip([0.0, 0.15, 0.45, 0.9, 1.5, 2.2, 3.2], [3.6, 4.4, 5.4, 5.75, 5.95, 5.95, 5.95])
CAP_ZT = pchip([0.0, 0.15, 0.45, 0.9, 1.5, 2.2, 3.2], [3.3, 3.9, 4.5, 5.0, 5.35, 5.5, 5.5])
CSEC = [(-1.0, 0.0), (-1.0, 0.6), (-0.93, 0.88), (-0.75, 1.0), (0.75, 1.0), (0.93, 0.88), (1.0, 0.6), (1.0, 0.0)]


def build_cap(P):
    ys = [0.0, 0.15, 0.45, 0.9, 1.5, 2.2, 3.2]
    rings = []
    for y in ys:
        hw, zt = float(CAP_HW(y)), float(CAP_ZT(y))
        rings.append([P.v((CAPX + u * hw, y, 1.2 + v * (zt - 1.2))) for u, v in CSEC])
    tube(P, rings, M["cap"])
    # two exhaust nozzles angled up and back (row 1, cols 8-10 and 14-15)
    axis = Vector((0, -0.55, 1.0)).normalized()
    for s in (-1, 1):
        c = Vector((CAPX + s * 2.8, 1.45, 4.35))
        side = Vector((1, 0, 0))
        up = axis.cross(side).normalized()

        def ring(t, r, n=14):
            return [P.v(tuple(c + axis * t + side * (r * math.cos(2 * math.pi * k / n))
                              + up * (r * math.sin(2 * math.pi * k / n)))) for k in range(n)]
        rs = [ring(-0.4, 1.2), ring(0.85, 1.2), ring(1.05, 1.08), ring(1.05, 0.8), ring(0.75, 0.8)]
        tube(P, rs[:4], M["nozzle"], cap0=True, cap1=False)
        tube(P, rs[3:], M["nozzle"], cap0=False, cap1=False)
        P.f(rs[4][::-1], M["glow"])
        hot = ring(0.78, 0.42, 10)
        P.f(hot[::-1], M["hot"])


# --- side pods ----------------------------------------------------------------------------------
POD_XI = 8.02
POD_YS = [7.5, 8.0, 8.5, 9.0, 9.4, 10.5, 12.0, 14.0, 16.0, 18.0, 19.4, 20.0, 20.5, 21.0, 21.5, 21.8, 22.0]
POD_XO = pchip([7.5, 8.5, 9.3, 19.4, 20.0, 20.5, 21.0, 21.5, 22.0],
               [5.0, 4.45, 4.2, 4.2, 4.35, 4.9, 5.45, 6.1, 7.2])
POD_ZT = pchip([7.5, 9.5, 18.5, 20.5, 22.0], [5.7, 6.3, 6.3, 5.4, 3.6])
POD_ZB = pchip([7.5, 20.0, 22.0], [1.7, 1.7, 2.3])
PSEC = [(0.12, 0.0), (0.0, 0.22), (0.0, 0.55), (0.07, 0.8), (0.22, 0.95), (0.45, 1.0), (0.72, 0.98), (0.9, 0.92),
        (1.0, 0.82), (1.0, 0.0)]


def pod_z(x, y):
    """Top of the left pod at (x, y)."""
    xo = float(POD_XO(y))
    u = (x - xo) / (POD_XI - xo)
    us = [p[0] for p in PSEC[2:9]]
    vs = [p[1] for p in PSEC[2:9]]
    u = min(max(u, us[0]), us[-1])
    zb, zt = float(POD_ZB(y)), float(POD_ZT(y))
    for i in range(len(us) - 1):
        if us[i] <= u <= us[i + 1]:
            t = (u - us[i]) / (us[i + 1] - us[i])
            return zb + (vs[i] + t * (vs[i + 1] - vs[i])) * (zt - zb)
    return zt


def pod_parts(P, mirror):
    mx = (lambda x: 2 * AX - x) if mirror else (lambda x: x)
    rings = []
    for y in POD_YS:
        xo, zt, zb = float(POD_XO(y)), float(POD_ZT(y)), float(POD_ZB(y))
        rings.append([P.v((mx(xo + u * (POD_XI - xo)), y, zb + v * (zt - zb))) for u, v in PSEC])

    def pm(i, k):
        y = POD_YS[i]
        return M["pod_dk"] if (y >= 20.5 or k in (0, 1)) else M["pod"]
    tube(P, rings, pm)
    # armour joint across the pod top (rows 11-12 and 18-19)
    for y in (11.9, 18.6):
        xo = float(POD_XO(y))
        xs = [xo + 0.15 + (POD_XI - 0.4 - xo) * i / 6 for i in range(7)]
        path_tube(P, [(mx(x), y, pod_z(x, y) - 0.02) for x in xs], 0.12, 0.09, 6, M["pod_dk"])
    # glowing vent slot (rows 13-17): a raised frame, a glowing bed, louvres, a hot core
    vx, vy, a, b = 6.2, 15.3, 1.0, 2.55
    ring = []
    for k in range(20):
        t = 2 * math.pi * k / 20
        x, y = vx + a * math.cos(t), vy + b * math.sin(t)
        ring.append((mx(x), y, pod_z(x, y) + 0.02))
    path_tube(P, ring, 0.26, 0.24, 6, M["pod_dk"], closed=True)
    ellipsoid(P, (mx(vx), vy, pod_z(vx, vy) - 0.3), a * 0.92, b * 0.95, 0.42, M["glow"], nu=18, nv=5)
    ellipsoid(P, (mx(6.4), 16.1, pod_z(6.4, 16.1) - 0.1), 0.5, 0.95, 0.26, M["hot"], nu=12, nv=4)
    for y in (13.6, 14.6, 17.3):
        half = a * math.sqrt(max(0.0, 1 - ((y - vy) / b) ** 2)) * 0.95
        xs = [vx - half + 2 * half * i / 4 for i in range(5)]
        path_tube(P, [(mx(x), y, pod_z(x, y) + 0.08) for x in xs], 0.1, 0.11, 6, M["pod"])
    # glowing port at row 10, in a collar
    px_, py_ = 5.55, 10.55
    z = pod_z(px_, py_)
    ellipsoid(P, (mx(px_), py_, z - 0.25), 0.78, 0.78, 0.4, M["pod_dk"], nu=14, nv=4)
    ellipsoid(P, (mx(px_), py_, z - 0.05), 0.5, 0.5, 0.32, M["port"], nu=12, nv=4)
    # track unit under the pod: a stadium belt with road wheels on its outer face
    x0, x1 = 4.75, 7.7
    yc0, yc1, r = 10.6, 19.0, 1.25
    loop = []
    for k in range(10):
        t = math.pi / 2 + math.pi * k / 9
        loop.append((yc0 + r * math.cos(t), r + r * math.sin(t)))
    for k in range(10):
        t = -math.pi / 2 + math.pi * k / 9
        loop.append((yc1 + r * math.cos(t), r + r * math.sin(t)))
    rings = [[P.v((mx(x), y, z)) for y, z in loop] for x in (x0, x1)]
    tube(P, rings, M["track"])
    # skirt bead along the pod's outer flank, where the armour skirt meets the track
    ys = [9.6, 12.0, 14.5, 17.0, 19.3, 20.3]
    path = [(mx(float(POD_XO(y)) + 0.12), y, float(POD_ZB(y)) + 0.9) for y in ys]
    path_tube(P, path, 0.14, 0.14, 6, M["pod_dk"])
    for yc in (10.6, 12.7, 14.8, 16.9, 19.0):
        n = 12
        xa, xb = x0 - 0.18, x0 + 0.05
        ra = [P.v((mx(xa), yc + 0.85 * math.cos(2 * math.pi * k / n), 1.25 + 0.85 * math.sin(2 * math.pi * k / n)))
              for k in range(n)]
        rb = [P.v((mx(xb), yc + 0.95 * math.cos(2 * math.pi * k / n), 1.25 + 0.95 * math.sin(2 * math.pi * k / n)))
              for k in range(n)]
        tube(P, [ra, rb], M["wheel"])


def build_pods(P):
    pod_parts(P, False)
    pod_parts(P, True)


# --- assembly -----------------------------------------------------------------------------------
def materials(sprite):
    return [common.palette_material(sprite, idx, f"{NAME}_{name}", metallic=me, roughness=ro, emission_strength=em)
            for name, idx, me, ro, em in MATS]


def build(sprite, coll):
    mats = materials(sprite)
    parts = []
    for nm, fn in (("hull", build_hull), ("hulldet", build_hull_detail), ("drum", build_drum),
                   ("cap", build_cap), ("pods", build_pods)):
        P = Part(nm)
        fn(P)
        parts.append(P.obj(coll, mats))
    bpy.context.view_layer.update()
    obj = T.join(parts, NAME)
    me = obj.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


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
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.002))
    g = bpy.context.active_object
    g.name = "ground"
    gm = bpy.data.materials.new("ground")
    gm.use_nodes = True
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.1, 0.13, 0.06, 1)
    g.data.materials.append(gm)
    V = 400
    scene.render.resolution_x = scene.render.resolution_y = V
    d = 4.0
    zc = 4.0 * PX
    tilt = math.radians(32)
    views = {
        "top": ((0, 0, d), 2.6, (0, 0, 0)),
        "side": ((d, 0, zc), 2.6, (0, 0, zc)),
        "front": ((0, -d, zc), 2.6, (0, 0, zc)),   # nose = sprite bottom = Blender -Y
        "rear": ((0, d, zc), 2.6, (0, 0, zc)),
        "q34": ((d * 0.6, -d * 0.6, d * 0.65), None, (0, 0, zc)),
        "q34b": ((-d * 0.65, d * 0.45, d * 0.55), None, (0, 0, zc)),
        "game": ((0, -d * math.sin(tilt), d * math.cos(tilt)), None, (0, 0, zc)),
        "under": ((d * 0.4, -d * 0.5, -d * 0.55), None, (0, 0, zc)),
    }
    for name, (loc, ortho, look) in views.items():
        g.hide_render = name in ("under", "front", "rear", "side")
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
    # outline shell from a sealed pre-cull copy (D51, D90, D118)
    seal = bpy.data.objects.new(f"{NAME}_seal", obj.data.copy())
    coll.objects.link(seal)
    bpy.context.view_layer.update()
    sh = common.outline_shell(seal, coll, voxel=0.01, faces=1600, smooth=5, inside=0.003)
    sh.name = sh.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(seal, do_unlink=True)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {tris} triangles, shell {len(sh.data.polygons)} faces")
    if views:
        views.mkdir(parents=True, exist_ok=True)
        top_mask(obj, views)
        (views / "pal.json").write_text(json.dumps(pal_grid(obj)))
        (views / "stats.json").write_text(json.dumps({"tris": tris, "shell": len(sh.data.polygons)}))
    common.export_sprite_model(WT, [obj, sh], MODEL, sprite["sprites"])
    if views:
        sh.hide_render = True
        lit_views(obj, views)


if __name__ == "__main__":
    main()
