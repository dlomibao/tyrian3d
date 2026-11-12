"""Insectoid craft (newshh.shp 159/161/163 over 197/199/201): one 72x52 px free-flying craft, design A.

WHAT IT IS: a grey insectoid gunship seen from above, flying toward screen bottom beak first. A round
armoured thorax carries a big glass sensor lens in a machined bezel; two antennae and two segmented
feeler arms ("whips") rise off its rear; green glass capsules sit on its shoulders and the armoured
legs come out of them, arch up over an elbow knuckle and down to a knee ball, then run on as long
tapering horns that curve down and in beside the head. The head: a brow crest over two red eyes in
dark-red sockets, wide cheek plates, a face plate with a raised green skull emblem and jaw bar, and a
long keeled beak; green prongs hang outside the cheeks and green fangs beside the face. The
two 3-piece rows (assembly-newshh-159 on top, assembly-newshh-197 under it, 4 px overlap) are one
drawing, so the craft is built whole in one frame and then cut into the six pieces.

Blueprint geometry first, engineered as
sections: superellipse lofts with pchip stations (body, head), rounded-square tubes for the
legs, modelled panel grooves (real section steps, sharp by angle), machined bezel with bolt heads,
segmented feelers with collars, pin-housing knuckles. Closed round belly, no underside detail.

Frame: parts are written in sprite edge coordinates of the 72x52 merged picture (x right, y down,
px; z up, px), mirror axis x 36.5. Blender: X = (x - 36) / 12, Y = (26 - y) / 12, Z = z / 12.

Pieces: every closed part is clipped to each piece's 24x28 box (top row y 0-28, head row y 24-52)
and capped before any join (D117), parts reaching < 0.4 px into a box are dropped; the shared rows
24-28 are in both rows' pieces, the top row 0.003 units lower so the head row draws over it as in
the original. Outline shell per piece from its sealed clipped copy (D90: 0.03 voxels, 0.004 inside;
every outer island kept).

Export: each of the six pieces (origin at its cell centre) plus its outline shell goes to
public/models/enemies/<piece>.glb with its src/render/spriteModels entry (both rows; assembly-newshh-159
is merged into this script).

    tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshh-197.py
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_mask  # noqa: E402

ROOT = WT
NAME = "assembly-newshh-197"
AX = 36.5
TOP_ROW = ["newshh-159", "newshh-161", "newshh-163"]
HEAD_ROW = ["newshh-197", "newshh-199", "newshh-201"]
PIECES = TOP_ROW + HEAD_ROW
TOP_DROP = 0.003  # units: the top row sits this much lower, so the head row wins the shared rows
MIN_KEEP = 0.4    # px: a part reaching less than this into a piece box is dropped
CAP_STEP = 0.03   # px between overlapping caps on one cut line
MASKS = {}


def box_of(name):
    i = PIECES.index(name)
    x0 = 24 * (i % 3)
    y0 = 0 if i < 3 else 24
    return x0, y0, x0 + 24, y0 + 28


def B(p):
    """Sprite px -> Blender units."""
    return Vector(((p[0] - 36) / 12, (26 - p[1]) / 12, p[2] / 12))


def mir(x):
    return 2 * AX - x


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, a, b):
    return max(a, min(b, v))


def se(c, p):
    return math.copysign(abs(c) ** (2 / p), c)


def pchip(xs, ys):
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m[0] = m[1] = d[0]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        m[0] = ((2 * h[0] + h[1]) * d[0] - h[0] * d[1]) / (h[0] + h[1])
        if math.copysign(1, m[0]) != math.copysign(1, d[0]):
            m[0] = 0.0
        m[-1] = ((2 * h[-1] + h[-2]) * d[-1] - h[-1] * d[-2]) / (h[-1] + h[-2])
        if math.copysign(1, m[-1]) != math.copysign(1, d[-1]):
            m[-1] = 0.0

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = 0
        while x > xs[i + 1]:
            i += 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


# ---------------------------------------------------------------------------------------------------
# Parts: each is one closed mesh (verts in sprite px, faces as (indices, material slot, smooth)).
# ---------------------------------------------------------------------------------------------------

class Part:
    def __init__(self, name, mat, sharp=40.0):
        self.name, self.mat, self.sharp = name, mat, sharp
        self.v, self.f = [], []
        self.only = None  # 'top' / 'head': kept only in that row's pieces (two drawings of the shared rows)

    def vert(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def face(self, idx, mat=None):
        self.f.append((tuple(idx), self.mat if mat is None else mat))


PARTS = []


def add(part):
    PARTS.append(part)
    return part


def ring_faces(P, rings, closed=True, matf=None, cap0=True, cap1=True, caps_at=None):
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            P.face((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]),
                   matf(k, i) if matf else None)
    for ring, rev, flag in ((rings[0], True, cap0), (rings[-1], False, cap1)):
        if not flag:
            continue
        cen = [sum(P.v[q][a] for q in ring) / n for a in range(3)]
        if caps_at is not None:
            cen = caps_at(ring is rings[0], cen)
        c = P.vert(cen)
        for i in range(n):
            j = (i + 1) % n
            P.face((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))


def loftY(name, mat, st, nseg=32, dy=0.4, grooves=(), matf=None, extra_ys=()):
    """Loft along screen y. Stations {y, hw, zt, zb, zm?, pt, pb}; superellipse half sections above and
    below zm. `grooves`: (y, half width px, depth px) panel lines cut as real section steps."""
    ys = [s["y"] for s in st]

    def f(k, default=None):
        vals = []
        for s in st:
            if k in s:
                vals.append(s[k])
            elif k == "zm":
                vals.append((s["zt"] + s["zb"]) / 2)
            elif k == "cx":
                vals.append(AX)
            else:
                vals.append(default)
        return pchip(ys, vals)
    HW, ZT, ZB, ZM, PT, PB, CX = f("hw"), f("zt"), f("zb"), f("zm"), f("pt"), f("pb"), f("cx")
    y0, y1 = ys[0], ys[-1]
    nr = math.ceil((y1 - y0) / dy)
    samples = {round(y0 + (y1 - y0) * k / nr, 4) for k in range(nr + 1)}
    for gy, gw, _ in grooves:
        for e in (gy - gw, gy - gw + 0.02, gy + gw - 0.02, gy + gw):
            samples.add(round(e, 4))
    samples |= {round(y, 4) for y in extra_ys}
    samples = sorted(y for y in samples if y0 <= y <= y1)

    def depth(y):
        for gy, gw, gd in grooves:
            if gy - gw + 0.01 < y < gy + gw - 0.01:
                return gd
        return 0.0
    P = add(Part(name, mat))
    rings = []
    for y in samples:
        hw, zt, zb, zm = max(HW(y), 0.02), ZT(y), ZB(y), ZM(y)
        g = depth(y)
        ring = []
        for i in range(nseg):
            a = 2 * math.pi * i / nseg
            c, s = math.cos(a), math.sin(a)
            top = s >= 0
            p = PT(y) if top else PB(y)
            gg = g if top else 0.0  # grooves on the top and flanks only
            ring.append(P.vert((CX(y) + (hw - gg * abs(se(c, p))) * se(c, p), y,
                                zm + ((zt - gg) - zm if top else zm - zb) * se(s, p))))
        rings.append(ring)
    ring_faces(P, rings, matf=(lambda k, i: matf(samples[k], samples[k + 1], i, nseg)) if matf else None)
    P.shape = dict(HW=HW, ZT=ZT, ZB=ZB, ZM=ZM, PT=PT, CX=CX)
    return P


def surfZ(L, x, y):
    s = L.shape
    hw = max(s["HW"](y), 0.05)
    t = clamp(abs(x - s["CX"](y)) / hw, 0, 1)
    p = s["PT"](y)
    zm, zt = s["ZM"](y), s["ZT"](y)
    return zm + (zt - zm) * (1 - t ** p) ** (1 / p)


def catmull(pts, per):
    out = []
    n = len(pts)

    def at(i):
        return pts[clamp(i, 0, n - 1)]
    for i in range(n - 1):
        p0, p1, p2, p3 = at(i - 1), at(i), at(i + 1), at(i + 2)
        for s in range(per):
            t = s / per
            out.append((tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                                     + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in range(3)), i + t))
    out.append((tuple(pts[-1][:3]), n - 1))
    return out


def tube(name, mat, ctrl, nseg=12, p=2.0, vs=1.0, per=3, collars=(), closed=False, cap_tip=True):
    """Tube along a Catmull-Rom path of [x, y, z, r] (sprite px); section a superellipse r wide, r*vs high,
    its side axis kept horizontal. `collars`: (param, half length in params, radius factor) rings."""
    P = add(Part(name, mat))
    if closed:
        pts = [c[:3] for c in ctrl[:-1]]
        rad = [c[3] for c in ctrl[:-1]]
        n = len(pts)
        path = []
        for i in range(n):
            p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            for s in range(per):
                t = s / per
                path.append((tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                                          + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t ** 3) for k in range(3)),
                             lerp(rad[i], rad[(i + 1) % n], t)))
    else:
        dense = catmull([c[:3] for c in ctrl], per)
        path = []
        for q, u in dense:
            i = min(int(u), len(ctrl) - 2)
            path.append((q, lerp(ctrl[i][3], ctrl[i + 1][3], u - i), u))
    # collars: extra stations
    if collars and not closed:
        newpath = []
        for k in range(len(path) - 1):
            newpath.append(path[k])
            u0, u1 = path[k][2], path[k + 1][2]
            for cu, cw, _ in collars:
                for e in (cu - cw, cu - cw + 0.03, cu + cw - 0.03, cu + cw):
                    if u0 < e < u1:
                        t = (e - u0) / (u1 - u0)
                        newpath.append((tuple(lerp(path[k][0][a], path[k + 1][0][a], t) for a in range(3)),
                                        lerp(path[k][1], path[k + 1][1], t), e))
        newpath.append(path[-1])
        newpath.sort(key=lambda e: e[2])
        path = newpath
    m = len(path)
    rings = []
    for i in range(m):
        a = path[(i - 1) % m if closed else max(0, i - 1)][0]
        b = path[(i + 1) % m if closed else min(m - 1, i + 1)][0]
        T = Vector(b) - Vector(a)
        T.normalize()
        S = Vector((T.y, -T.x, 0))
        if S.length < 1e-4:
            S = Vector((1, 0, 0))
        S.normalize()
        U = S.cross(T)
        if U.z < 0:
            U = -U
        r = path[i][1]
        if not closed:
            for cu, cw, cf in collars:
                if cu - cw + 0.015 < path[i][2] < cu + cw - 0.015:
                    r *= cf
        ring = []
        for j in range(nseg):
            ang = 2 * math.pi * (j + 0.5) / nseg
            c, s = se(math.cos(ang), p) * r, se(math.sin(ang), p) * r * vs
            q = Vector(path[i][0]) + S * c + U * s
            ring.append(P.vert(q))
        rings.append(ring)
    if closed:
        rings.append(rings[0])
        ring_faces(P, rings, cap0=False, cap1=False)
    else:
        ring_faces(P, rings)
    return P


def blob(name, mat, c, r, p=2.0, pz=None, nu=20, nv=10):
    """Superellipsoid with real poles."""
    P = add(Part(name, mat))
    pz = pz or p
    bot = P.vert((c[0], c[1], c[2] - r[2]))
    rings = []
    for j in range(1, nv):
        b = -math.pi / 2 + math.pi * j / nv
        ring = []
        for i in range(nu):
            a = 2 * math.pi * i / nu
            ring.append(P.vert((c[0] + r[0] * se(math.cos(b), p) * se(math.cos(a), p),
                                c[1] + r[1] * se(math.cos(b), p) * se(math.sin(a), p),
                                c[2] + r[2] * se(math.sin(b), pz))))
        rings.append(ring)
    top = P.vert((c[0], c[1], c[2] + r[2]))
    for k in range(len(rings) - 1):
        for i in range(nu):
            j = (i + 1) % nu
            P.face((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    for i in range(nu):
        j = (i + 1) % nu
        P.face((rings[0][j], rings[0][i], bot))
        P.face((rings[-1][i], rings[-1][j], top))
    return P


def cyl(name, mat, a, b, r, nseg=12, chamfer=0.15):
    """A chamfered cylinder (pin housing) from a to b (sprite px)."""
    A, Bv = Vector(a), Vector(b)
    T = (Bv - A).normalized()
    S = T.cross(Vector((0, 0, 1)))
    if S.length < 1e-4:
        S = Vector((1, 0, 0))
    S.normalize()
    U = S.cross(T)
    P = add(Part(name, mat, sharp=30))
    L = (Bv - A).length
    rings = []
    for t, rr in ((0, r - chamfer), (chamfer, r), (L - chamfer, r), (L, r - chamfer)):
        ring = []
        for j in range(nseg):
            ang = 2 * math.pi * j / nseg
            ring.append(P.vert(A + T * t + S * (rr * math.cos(ang)) + U * (rr * math.sin(ang))))
        rings.append(ring)
    ring_faces(P, rings)
    return P


# ---------------------------------------------------------------------------------------------------
# The craft
# ---------------------------------------------------------------------------------------------------

def build_parts(M):
    PARTS.clear()
    # 1. THORAX: round armoured shell, rows 8-24; a dome top carrying the lens; closed round belly.
    BODY = [
        {"y": 7.9, "hw": 2.5, "zt": 3.4, "zb": 1.4, "pt": 2.2, "pb": 2},
        {"y": 8.5, "hw": 4.6, "zt": 4.6, "zb": -0.6, "pt": 2.4, "pb": 2},
        {"y": 9.2, "hw": 9.0, "zt": 5.8, "zb": -2.6, "pt": 2.6, "pb": 2.2},
        {"y": 10.5, "hw": 10.8, "zt": 6.6, "zb": -4.0, "pt": 2.6, "pb": 2.2},
        {"y": 14, "hw": 11.3, "zt": 7.0, "zb": -5.0, "pt": 2.6, "pb": 2.2},
        {"y": 19, "hw": 11.5, "zt": 6.9, "zb": -5.0, "pt": 2.6, "pb": 2.2},
        {"y": 22.5, "hw": 11.6, "zt": 6.4, "zb": -4.2, "pt": 2.6, "pb": 2.2},
        {"y": 24.0, "hw": 10.5, "zt": 5.0, "zb": -3.0, "pt": 2.6, "pb": 2.2},
    ]

    def body_mat(y0, y1, i, n):
        a = 2 * math.pi * (i + 0.5) / n
        if math.sin(a) < -0.35:
            return M["UNDER"]
        return M["BODY"]
    body = loftY("body", M["BODY"], BODY, nseg=18, dy=0.9, grooves=[(10.9, 0.22, 0.28), (21.6, 0.22, 0.28)], matf=body_mat)

    # lens bezel (machined ring, chamfered square section) + bolt heads + the glass lens
    LX, LY, RX, RY = AX, 16.6, 5.7, 4.9
    ring = []
    for i in range(25):
        t = 2 * math.pi * i / 24
        ring.append([LX + (RX + 0.55) * math.cos(t), LY + (RY + 0.55) * math.sin(t), 7.35, 0.8])
    tube("lens_bezel", M["BEZEL"], ring, nseg=8, p=3.2, vs=0.85, per=2, closed=True)
    blob("lens", M["LENS"], (LX, LY, 7.2), (RX, RY, 2.4), nu=16, nv=6)
    for k in range(8):
        t = 2 * math.pi * (k + 0.5) / 8
        blob("bezel_bolt", M["STUD"], (LX + (RX + 0.6) * math.cos(t), LY + (RY + 0.6) * math.sin(t), 8.0),
             (0.35, 0.35, 0.22), nu=8, nv=4)

    # 2. HEAD: brow crest over the eyes, wide cheek plates, face plate, keeled beak to the point.
    HEAD = [
        {"y": 20.8, "hw": 11.4, "zt": 6.2, "zb": -3.0, "pt": 3.2, "pb": 2.2},
        {"y": 22.6, "hw": 11.6, "zt": 7.3, "zb": -3.4, "pt": 3.2, "pb": 2.2},
        {"y": 24.0, "hw": 12.4, "zt": 6.0, "zb": -3.6, "pt": 3.0, "pb": 2.2},
        {"y": 24.6, "hw": 12.7, "zt": 5.7, "zb": -3.6, "pt": 3.0, "pb": 2.2, "zm": 0.3},
        {"y": 25.6, "hw": 12.9, "zt": 5.35, "zb": -3.6, "pt": 3.0, "pb": 2.2, "zm": 0.4, "cx": 36.6},
        {"y": 26.8, "hw": 13.0, "zt": 5.1, "zb": -3.4, "pt": 3.0, "pb": 2.2, "zm": 0.6, "cx": 36.9},
        {"y": 27.7, "hw": 13.0, "zt": 5.0, "zb": -3.2, "pt": 3.0, "pb": 2.2, "zm": 0.8, "cx": 36.9},
        {"y": 28.0, "hw": 12.0, "zt": 4.95, "zb": -3.15, "pt": 2.9, "pb": 2.2, "zm": 0.85, "cx": 36.7},
        {"y": 28.4, "hw": 10.6, "zt": 4.9, "zb": -3.1, "pt": 2.8, "pb": 2.2},
        {"y": 29.1, "hw": 8.8, "zt": 4.8, "zb": -3.0, "pt": 2.6, "pb": 2.2},
        {"y": 29.7, "hw": 8.6, "zt": 4.78, "zb": -2.98, "pt": 2.6, "pb": 2.2},
        {"y": 30.3, "hw": 7.5, "zt": 4.75, "zb": -2.95, "pt": 2.6, "pb": 2.2},
        {"y": 30.7, "hw": 7.4, "zt": 4.7, "zb": -2.9, "pt": 2.6, "pb": 2.2},
        {"y": 31.4, "hw": 6.8, "zt": 4.65, "zb": -2.8, "pt": 2.6, "pb": 2.2},
        {"y": 34.5, "hw": 6.6, "zt": 4.45, "zb": -2.5, "pt": 2.4, "pb": 2.2},
        {"y": 35.3, "hw": 7.5, "zt": 4.4, "zb": -2.4, "pt": 2.2, "pb": 2.2},
        {"y": 41.5, "hw": 7.5, "zt": 3.4, "zb": -1.6, "pt": 1.7, "pb": 2.2},
        {"y": 42.2, "hw": 6.9, "zt": 3.2, "zb": -1.45, "pt": 1.6, "pb": 2.2},
        {"y": 43.1, "hw": 5.4, "zt": 2.95, "zb": -1.3, "pt": 1.6, "pb": 2.2},
        {"y": 44.2, "hw": 3.9, "zt": 2.6, "zb": -1.1, "pt": 1.6, "pb": 2.2},
        {"y": 45.6, "hw": 3.4, "zt": 2.15, "zb": -0.9, "pt": 1.6, "pb": 2.2},
        {"y": 47.0, "hw": 2.6, "zt": 1.7, "zb": -0.7, "pt": 1.6, "pb": 2.2},
        {"y": 48.3, "hw": 1.8, "zt": 1.2, "zb": -0.4, "pt": 1.6, "pb": 2.2},
        {"y": 49.3, "hw": 0.9, "zt": 0.8, "zb": -0.15, "pt": 1.6, "pb": 2.2},
        {"y": 50.0, "hw": 0.15, "zt": 0.45, "zb": 0.1, "pt": 1.6, "pb": 2.2},
    ]
    NS = 20

    def head_mat(y0, y1, i, n):
        a = 2 * math.pi * (i + 0.5) / n
        s, c = math.sin(a), math.cos(a)
        y = (y0 + y1) / 2
        if s < -0.3:
            return M["UNDER"]
        if y >= 35.2 and abs(c) < 0.09 and s > 0:
            return M["KEEL"]
        if y >= 35.2:
            return M["BEAK"]
        return M["HEAD"]
    head = loftY("head", M["HEAD"], HEAD, nseg=NS, dy=0.8,
                 grooves=[(23.5, 0.2, 0.25), (28.6, 0.2, 0.2), (35.2, 0.22, 0.28), (38.6, 0.3, -0.16), (41.0, 0.18, 0.2),
                          (44.2, 0.28, -0.12), (46.4, 0.14, 0.12)],
                 matf=head_mat)

    def hz(x, y):
        return surfZ(head, x, y)

    for x in (29.6, mir(29.6)):
        blob("eye_socket", M["SOCKET"], (x, 25.0, hz(x, 25.0) - 0.15), (2.0, 1.35, 0.6), nu=16, nv=6)
        blob("eye", M["EYE"], (x, 25.05, hz(x, 25.0) + 0.05), (1.35, 0.9, 0.55), nu=16, nv=6)
    zs = hz(AX, 30.0)
    blob("skull_emblem", M["SKULL"], (AX, 30.0, zs - 0.2), (3.1, 2.9, 0.6), p=3.0, nu=24, nv=6)
    # the skull's eye holes and nose notch (dark), set into the plate's top
    for x in (AX - 1.2, AX + 1.2):
        blob("skull_eye", M["DARK"], (x, 29.5, zs + 0.33), (0.6, 0.55, 0.1), p=2.6, nu=10, nv=4)
    blob("skull_nose", M["DARK"], (AX, 31.0, zs + 0.3), (0.3, 0.45, 0.08), nu=8, nv=4)
    # teeth: dark slots across the jaw bar
    for x in (AX - 1.5, AX - 0.5, AX + 0.5, AX + 1.5):
        blob("skull_eye", M["DARK"], (x, 34.4, hz(AX, 34.4) + 0.35), (0.12, 0.6, 0.1), p=3, nu=8, nv=4)
    blob("skull_jaw", M["SKULL"], (AX, 34.4, hz(AX, 34.4) - 0.1), (3.0, 0.85, 0.5), p=3.2, nu=20, nv=4)
    for x in (33.0, mir(33.0)):
        blob("brow_lamp", M["LAMP"], (x, 23.3, hz(x, 23.3) - 0.1), (0.9, 0.55, 0.4), nu=12, nv=4)
    for x in (31.0, mir(31.0)):
        blob("beak_vent", M["DARK"], (x, 37.7, hz(x, 37.7) - 0.18), (0.75, 1.3, 0.32), p=3, nu=12, nv=4)

    # 3. SHOULDER CAPSULES: green glass pods on grey mount collars, the legs' root sockets.
    for s in (1, -1):
        x = 25.6 if s > 0 else mir(25.6)
        blob("pod", M["POD"], (x, 17.2, 2.6), (3.9, 4.6, 3.0), p=2.6, nu=20, nv=8)
        col = []
        for i in range(19):
            t = 2 * math.pi * i / 18
            col.append([x + 3.4 * math.cos(t), 17.2 + 4.2 * math.sin(t), 0.6, 0.55])
        tube("pod_collar", M["COLLAR"], col, nseg=6, p=3, per=2, closed=True)

    # 4. LEGS: shoulder -> upper leg out and up -> elbow knuckle -> down to the knee ball -> horn
    LEG = [[23.4, 17.4, 2.0, 1.9], [22.6, 16.8, 2.2, 2.0], [19.5, 13.4, 3.3, 2.9], [16.5, 12.9, 4.2, 3.0], [13.9, 13.0, 4.4, 3.0],
           [13.4, 16.0, 3.7, 3.2], [11.8, 18.6, 2.4, 2.35], [10.3, 20.6, 1.0, 2.0], [9.4, 22.3, 0.2, 1.5],
           [9.0, 23.6, -0.2, 1.6]]
    # the top row's own drawing of the shared rows 24-28: the leg running on down and out (no knee)
    LEG_TOP = [[9.6, 22.0, 0.3, 1.5], [9.0, 23.5, -0.2, 1.5], [8.3, 25.0, -0.5, 1.5], [7.2, 26.5, -0.9, 1.7],
               [6.2, 28.3, -1.3, 2.2]]
    HORN = [[8.12, 24.98, -0.6, 1.72], [6.6, 26.38, -1.2, 2.3], [7.0, 28.77, -1.7, 2.18], [7.5, 31.44, -2.1, 1.6],
            [7.8, 34.0, -2.4, 1.25], [9.07, 36.65, -2.6, 1.19], [10.1, 39.2, -2.7, 1.06], [11.93, 40.42, -2.6, 0.84],
            [13.4, 41.9, -2.5, 0.4]]
    WHIP = [[27.86, 9.41, 5.0, 2.15], [25.96, 7.01, 6.4, 1.75], [23.7, 5.0, 7.1, 1.5], [20.6, 3.9, 7.2, 1.13],
            [17.0, 3.5, 6.7, 0.82], [13.4, 3.5, 5.8, 0.65], [10.88, 4.19, 4.8, 0.55], [9.2, 4.7, 3.8, 0.55],
            [8.4, 5.6, 3.0, 0.35]]
    ANT = [[33.83, 9.06, 6.4, 0.75], [33.6, 6.57, 7.5, 0.7], [32.5, 4.6, 8.5, 0.6], [31.16, 3.18, 9.3, 0.55],
           [30.43, 2.45, 9.6, 0.5]]
    PRONG = [[24.0, 24.5, 2.9, 0.7], [22.6, 26.0, 2.4, 1.1], [21.6, 27.4, 1.8, 1.1], [20.1, 29.5, 1.0, 0.9], [19.5, 32.6, 0.1, 0.4]]
    FANG = [[26.7, 28.4, 2.0, 1.5], [26.5, 30.5, 1.4, 1.45], [26.0, 31.7, 1.0, 1.0], [25.5, 33.0, 0.5, 0.6],
            [25.4, 35.2, -0.1, 0.3]]

    def side(ctrl, s):
        return [[c[0] if s > 0 else mir(c[0])] + list(c[1:]) for c in ctrl]
    for s in (1, -1):
        sx = (lambda x: x) if s > 0 else mir
        # armoured leg, rounded-square section, armour joints as grooves (collars < 1)
        tube("leg", M["LEG"], side(LEG, s), nseg=10, p=2.8, vs=1.05,
             collars=[(1.55, 0.08, 0.9), (4.6, 0.08, 0.9), (5.9, 0.08, 0.9)])
        tube("horn", M["LEG"], side(HORN, s), nseg=10, p=2.2, vs=0.9, collars=[(1.9, 0.07, 0.9)]).only = "head"
        tube("leg_top", M["LEG"], side(LEG_TOP, s), nseg=10, p=2.8, vs=1.05).only = "top"
        # elbow pin housing across the joint, its pin caps
        ex, ey, ez = 13.6, 13.4, 4.4
        cyl("elbow", M["JOINT"], (sx(ex - 0.2), ey - 1.0, ez + 0.4), (sx(ex - 0.2), ey + 1.0, ez + 0.4), 0.95, nseg=10)
        blob("knee", M["KNEE"], (sx(6.6), 25.2, -0.8), (2.3, 2.4, 1.9), nu=12, nv=6).only = "head"
        # segmented feeler arm with collars at its joints
        tube("whip", M["WHIP"], side(WHIP, s), nseg=8, p=2.2,
             collars=[(1.0, 0.12, 1.15), (2.6, 0.12, 1.15), (4.2, 0.12, 1.18), (5.8, 0.12, 1.2)])
        blob("whip_mount", M["JOINT"], (sx(28.4), 8.9, 4.7), (1.5, 1.2, 1.1), nu=14, nv=6)
        tube("antenna", M["ANT"], side(ANT, s), nseg=8)
        blob("antenna_tip", M["ANT"], (sx(30.7), 2.0, 9.7), (0.6, 0.6, 0.6), nu=10, nv=5)
        tube("prong", M["PRONG"], side(PRONG, s), nseg=10, p=2.2)
        tube("fang", M["FANG"], side(FANG, s), nseg=10, p=2.2)
    return PARTS


# ---------------------------------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------------------------------

def materials(sprite):
    tag = "nshh197A"

    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    mats = [
        ("BODY", pal(103, metallic=0.4, roughness=0.42)),
        ("UNDER", pal(100, metallic=0.4, roughness=0.6)),
        ("BEZEL", pal(103, metallic=0.5, roughness=0.32)),
        ("LENS", pal(107, metallic=0.35, roughness=0.12)),
        ("STUD", pal(106, metallic=0.5, roughness=0.3)),
        ("HEAD", pal(103, metallic=0.4, roughness=0.42)),
        ("BEAK", pal(103, metallic=0.4, roughness=0.4)),
        ("KEEL", pal(106, metallic=0.45, roughness=0.32)),
        ("SOCKET", pal(115, metallic=0.3, roughness=0.5)),
        ("EYE", pal(120, metallic=0.0, roughness=0.25, emission_strength=1.2)),
        ("SKULL", pal(43, metallic=0.3, roughness=0.35)),
        ("DARK", pal(99, metallic=0.3, roughness=0.6)),
        ("LAMP", pal(41, metallic=0.1, roughness=0.2, emission_strength=0.35)),
        ("POD", pal(40, metallic=0.25, roughness=0.15)),
        ("COLLAR", pal(101, metallic=0.45, roughness=0.4)),
        ("LEG", pal(105, metallic=0.4, roughness=0.4)),
        ("JOINT", pal(103, metallic=0.45, roughness=0.35)),
        ("KNEE", pal(106, metallic=0.5, roughness=0.3)),
        ("WHIP", pal(105, metallic=0.4, roughness=0.4)),
        ("ANT", pal(106, metallic=0.45, roughness=0.35)),
        ("PRONG", pal(39, metallic=0.3, roughness=0.4)),
        ("FANG", pal(40, metallic=0.3, roughness=0.4)),
    ]
    M = {k: i for i, (k, _) in enumerate(mats)}
    return M, [m for _, m in mats]


def part_bmesh(P):
    bm = bmesh.new()
    vs = [bm.verts.new(B(p)) for p in P.v]
    for idx, mat in P.f:
        uniq = []
        for i in idx:
            if not uniq or uniq[-1] != i:
                uniq.append(i)
        if len(uniq) > 2 and uniq[0] == uniq[-1]:
            uniq.pop()
        if len(set(uniq)) < 3:
            continue
        try:
            f = bm.faces.new([vs[i] for i in uniq])
            f.material_index = mat
            f.smooth = True
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


HEAD_ONLY = {"prong", "fang", "eye", "eye_socket", "skull_emblem", "skull_eye", "skull_nose", "skull_jaw",
             "brow_lamp", "beak_vent"}


def bm_px(bm):
    """Vertex positions in sprite px (x, y, z)."""
    return [(v.co.x * 12 + 36, 26 - v.co.y * 12, v.co.z * 12) for v in bm.verts]


def vote(name, pts, row):
    """D117's shared-row vote: the part's columns on that row of the piece's own sprite, colour inside the
    ink +1, ink or nothing -1, free 0. Returns True to keep the row."""
    x0, y0, _, _ = box_of(name)
    xs = [p[0] for p in pts if row + y0 - 0.0 <= p[1] <= row + y0 + 1.0]
    if not xs:
        return True
    m = MASKS[name]
    c0, c1 = max(0, int(min(xs) - x0)), min(23, int(max(xs) - x0))
    sc = 0
    for c in range(c0, c1 + 1):
        if m["free"][row][c]:
            continue
        sc += 1 if m["inner"][row][c] else -1
    return sc >= 0


def piece_box(name, P, pts):
    x0, y0, x1, y1 = box_of(name)
    if (P.only == "head" and name in TOP_ROW) or (P.only == "top" and name in HEAD_ROW):
        return None
    if name in TOP_ROW:
        if P.name in HEAD_ONLY:
            y1 = min(y1, 24.0)
        elif not vote(name, pts, 27):
            y1 = 27.0
    else:
        if not vote(name, pts, 0):
            y0 = 25.0
    return x0, y0, x1, y1


def piece_mesh(name, parts, mats):
    """Clip every closed part to the piece's box (per part: HEAD_ONLY parts and the shared-row vote), cap
    the cuts; overlapping caps on one line are stepped CAP_STEP apart, outward (into the neighbour piece,
    inside its copy of the same part), the taller part outermost."""
    items = []
    for P in parts:
        bm = part_bmesh(P)
        pts = bm_px(bm)
        bx = piece_box(name, P, pts)
        if bx is None:
            bm.free()
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # dropped if it reaches less than MIN_KEEP into the box on any side
        if (max(xs) - bx[0] < MIN_KEEP or bx[2] - min(xs) < MIN_KEEP or max(ys) - bx[1] < MIN_KEEP
                or bx[3] - min(ys) < MIN_KEEP):
            bm.free()
            continue
        items.append([P, bm, pts, bx])
    # sides: (axis, which bound, sign of the kept side in px)
    offs = {}
    for side in range(4):
        ax = 0 if side < 2 else 1
        cut = []
        for n, (P, bm, pts, bx) in enumerate(items):
            line = bx[side if side < 2 else side]
            line = bx[0] if side == 0 else bx[2] if side == 1 else bx[1] if side == 2 else bx[3]
            lo, hi = min(p[ax] for p in pts), max(p[ax] for p in pts)
            if lo < line < hi:
                ts = [p[1 - ax] for p in pts]
                zs = [p[2] for p in pts]
                cut.append((n, line, (min(ts), max(ts)), (min(zs), max(zs))))
        cut.sort(key=lambda e: -e[3][1])
        ks = []
        for i, (n, line, (t0, t1), (z0, z1)) in enumerate(cut):
            over = [ks[j] for j, (_n, l2, (u0, u1), (w0, w1)) in enumerate(cut[:i])
                    if l2 == line and t0 < u1 and u0 < t1 and z0 < w1 and w0 < z1]
            ks.append(max(over) + 1 if over else 0)
        for (n, *_), k in zip(cut, ks):
            offs[(n, side)] = min(k, 4)
    out = bmesh.new()
    for n, (P, bm, pts, bx) in enumerate(items):
        for side in range(4):
            k = offs.get((n, side))
            if k is None:
                continue
            step = (4 - k) * CAP_STEP  # tallest outermost
            if side == 0:
                co, no = Vector(((bx[0] - step - 36) / 12, 0, 0)), Vector((-1, 0, 0))
            elif side == 1:
                co, no = Vector(((bx[2] + step - 36) / 12, 0, 0)), Vector((1, 0, 0))
            elif side == 2:  # y0 (screen top) -> Blender +Y
                co, no = Vector((0, (26 - (bx[1] - step)) / 12, 0)), Vector((0, 1, 0))
            else:
                co, no = Vector((0, (26 - (bx[3] + step)) / 12, 0)), Vector((0, -1, 0))
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
            res = bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
            for f in res["faces"]:
                f.smooth = False
        if len(bm.faces):
            me = bpy.data.meshes.new("tmp")
            bm.to_mesh(me)
            out.from_mesh(me)
            bpy.data.meshes.remove(me)
        bm.free()
    mesh = bpy.data.meshes.new(name)
    out.to_mesh(mesh)
    out.free()
    for m in mats:
        mesh.materials.append(m)
    return mesh


def whole_mesh(parts, mats):
    out = bmesh.new()
    for P in parts:
        bm = part_bmesh(P)
        me = bpy.data.meshes.new("tmp")
        bm.to_mesh(me)
        bm.free()
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
    mesh = bpy.data.meshes.new(NAME)
    out.to_mesh(mesh)
    out.free()
    for m in mats:
        mesh.materials.append(m)
    return mesh


def finish_mesh(mesh):
    mesh.set_sharp_from_angle(angle=math.radians(40))


def outline_shell_all(obj, coll, voxel=0.03, faces=3000, smooth=6, inside=0.004):
    """common.outline_shell, but every outer island kept (horns, whips, antennae; cf. lib_b065)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.verts.ensure_lookup_table()
    seen, islands = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append(x)
            stack.extend(e.other_vert(x) for e in x.link_edges)
        islands.append(isl)

    def bb(isl):
        xs = [v.co.x for v in isl]
        ys = [v.co.y for v in isl]
        zs = [v.co.z for v in isl]
        return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    boxes = [bb(i) for i in islands]
    drop = set()
    for a, ba in enumerate(boxes):
        for b, bb_ in enumerate(boxes):
            if a != b and len(islands[b]) > len(islands[a]) and all(
                    bb_[2 * k] <= ba[2 * k] and ba[2 * k + 1] <= bb_[2 * k + 1] for k in range(3)):
                drop.add(a)  # an inner shell (cavity) inside another island
                break
    dead = [v for a in drop for v in islands[a]]
    if dead:
        bmesh.ops.delete(bm, geom=dead, context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    common._apply_modifiers(shell)
    sw = shell.modifiers.new("inside", "SHRINKWRAP")
    sw.target = obj
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = -inside
    common._apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def merged_sprite():
    data = common.load_sprite(ROOT, PIECES[0])
    for n in PIECES[1:]:
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def piece_centre(name):
    """The piece's cell centre in the whole frame (Blender units): the model's origin (contract)."""
    x0, y0, x1, y1 = box_of(name)
    return Vector((((x0 + x1) / 2 - 36) / 12, (26 - (y0 + y1) / 2) / 12, 0.0))


def to_origin(obj, centre):
    """Bake the object's transform, then move its centre to the origin (x, y only)."""
    from mathutils import Matrix
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.transform(Matrix.Translation((-centre.x, -centre.y, 0.0)))


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = merged_sprite()
    for n in PIECES:
        idx, colors = sprite_mask.load(n, None, str(sprite_mask.REF))
        partners = sprite_mask.pulse_partners(idx, sprite_mask.load_frames(n, str(sprite_mask.REF)))
        MASKS[n] = sprite_mask.masks(idx, colors, partners)
    M, mats = materials(sprite)
    parts = build_parts(M)
    coll = common.reset_collection(NAME)
    pieces, shells = {}, {}
    for name in PIECES:
        mesh = piece_mesh(name, parts, mats)
        finish_mesh(mesh)
        obj = bpy.data.objects.new(name, mesh)
        coll.objects.link(obj)
        if name in TOP_ROW:
            obj.location.z = -TOP_DROP
        pieces[name] = obj
    bpy.context.view_layer.update()
    for name, obj in pieces.items():
        shells[name] = outline_shell_all(obj, coll)
        shells[name].parent = None
    bpy.context.view_layer.update()
    tris = {n: sum(len(p.vertices) - 2 for p in o.data.polygons) for n, o in pieces.items()}
    print("TRIS", json.dumps(tris), "total", sum(tris.values()))
    for name in PIECES:
        c = piece_centre(name)
        to_origin(pieces[name], c)
        to_origin(shells[name], c)
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data["sprites"])


if __name__ == "__main__":
    main()
