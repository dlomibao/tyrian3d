"""Shared builder for the TORM abdomen segments assembly-newshh-230 (230+232) and -192 (192+194).

Design B (see the two entry scripts). Its own code: the old lib_b056 (once shared with newshh-155) is deleted.
Each segment is built at its own centre; the pieces are cut at the cell boundary, capped (D117), get
a sealed-copy outline shell (D90) and go out through common.export_sprite_model.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "tools")]
import common  # noqa: E402
import sprite_mask  # noqa: E402

ROOT = WT
AX = 25.5
SEGS = {"230": ["newshh-230", "newshh-232"], "192": ["newshh-192", "newshh-194"]}
ASM = {"230": "assembly-newshh-230", "192": "assembly-newshh-192"}
COLUMN_DY = {"230": 0.0, "192": 0.0}  # every segment is built at its own centre: the export origin is the piece cell centre
MIN_KEEP = 0.4
CROWN = 0.6  # px: extra dome on the chrome shells, so their sheen rolls across them at the game camera
CHROME_SPEC = 0.7  # Specular IOR Level on the chrome (D176: polished grey needs F0 or it reads dull)
CAP_STEP = 0.03


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
# Parts (copied from assembly-newshh-197, D170; loftY gains the blueprint's `tilt`)
# ---------------------------------------------------------------------------------------------------

class Part:
    def __init__(self, name, mat):
        self.name, self.mat = name, mat
        self.v, self.f = [], []

    def vert(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def face(self, idx, mat=None):
        self.f.append((tuple(idx), self.mat if mat is None else mat))


PARTS = []


def add(part):
    PARTS.append(part)
    return part


def ring_faces(P, rings, closed=True, matf=None, cap0=True, cap1=True):
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            P.face((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]), matf(k, i) if matf else None)
    for ring, rev, flag in ((rings[0], True, cap0), (rings[-1], False, cap1)):
        if not flag:
            continue
        cen = [sum(P.v[q][a] for q in ring) / n for a in range(3)]
        c = P.vert(cen)
        for i in range(n):
            j = (i + 1) % n
            P.face((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))


def loftY(name, mat, st, nseg=32, dy=0.4, grooves=(), matf=None):
    """Loft along screen y. Stations {y, hw, zt, zb, zm?, pt, pb, cx?, tilt?}: superellipse half sections
    above and below zm, the section sheared by `tilt` (dz per px of x - cx). `grooves`: (y, half width px,
    depth px) panel lines cut as real section steps (top and flanks)."""
    ys = [s["y"] for s in st]

    def f(k, default):
        return pchip(ys, [s.get(k, (s["zt"] + s["zb"]) / 2 if k == "zm" else default) for s in st])
    HW, ZT, ZB, ZM, PT, PB = f("hw", 1), f("zt", 1), f("zb", 0), f("zm", 0), f("pt", 2), f("pb", 2)
    CX, TL = f("cx", AX), f("tilt", 0.0)
    y0, y1 = ys[0], ys[-1]
    nr = max(2, math.ceil((y1 - y0) / dy))
    samples = {round(y0 + (y1 - y0) * k / nr, 4) for k in range(nr + 1)}
    for gy, gw, _ in grooves:
        for e in (gy - gw, gy - gw + 0.02, gy + gw - 0.02, gy + gw):
            samples.add(round(e, 4))
    samples = sorted(y for y in samples if y0 <= y <= y1)

    def depth(y):
        for gy, gw, gd in grooves:
            if gy - gw + 0.01 < y < gy + gw - 0.01:
                return gd
        return 0.0
    P = add(Part(name, mat))
    rings = []
    for y in samples:
        hw, zt, zb, zm, cx, tl = max(HW(y), 0.02), ZT(y), ZB(y), ZM(y), CX(y), TL(y)
        g = depth(y)
        ring = []
        for i in range(nseg):
            a = 2 * math.pi * i / nseg
            c, s = math.cos(a), math.sin(a)
            top = s >= 0
            p = PT(y) if top else PB(y)
            gg = g if top else 0.0
            dx = (hw - gg * abs(se(c, p))) * se(c, p)
            ring.append(P.vert((cx + dx, y, zm + tl * dx + ((zt - gg) - zm if top else zm - zb) * se(s, p))))
        rings.append(ring)
    ring_faces(P, rings, matf=(lambda k, i: matf(samples[k], samples[k + 1], i, nseg)) if matf else None)
    P.shape = dict(HW=HW, ZT=ZT, ZM=ZM, PT=PT, CX=CX, TL=TL)
    return P


def surfZ(L, x, y):
    s = L.shape
    hw = max(s["HW"](y), 0.05)
    dx = x - s["CX"](y)
    t = clamp(abs(dx) / hw, 0, 1)
    p = s["PT"](y)
    zm, zt = s["ZM"](y), s["ZT"](y)
    return zm + s["TL"](y) * dx + (zt - zm) * (1 - t ** p) ** (1 / p)


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


def tube(name, mat, ctrl, nseg=12, p=2.0, vs=1.0, per=3):
    """Tube along a Catmull-Rom path of [x, y, z, r] (sprite px); section a superellipse r wide, r*vs high,
    its side axis kept horizontal; capped ends."""
    P = add(Part(name, mat))
    dense = catmull([c[:3] for c in ctrl], per)
    path = []
    for q, u in dense:
        i = min(int(u), len(ctrl) - 2)
        path.append((q, lerp(ctrl[i][3], ctrl[i + 1][3], u - i)))
    m = len(path)
    rings = []
    for i in range(m):
        a = path[max(0, i - 1)][0]
        b = path[min(m - 1, i + 1)][0]
        T = (Vector(b) - Vector(a)).normalized()
        S = Vector((T.y, -T.x, 0))
        if S.length < 1e-4:
            S = Vector((1, 0, 0))
        S.normalize()
        U = S.cross(T)
        if U.z < 0:
            U = -U
        r = path[i][1]
        ring = []
        for j in range(nseg):
            ang = 2 * math.pi * (j + 0.5) / nseg
            q = Vector(path[i][0]) + S * (se(math.cos(ang), p) * r) + U * (se(math.sin(ang), p) * r * vs)
            ring.append(P.vert(q))
        rings.append(ring)
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


# ---------------------------------------------------------------------------------------------------
# The segments
# ---------------------------------------------------------------------------------------------------

# Carapace stations shared by both segments (z by row); the half widths are per segment.
CAR_Z = {  # y: (zt, zb, zm, pt)
    1.05: (5.82, 5.07, 5.19, 1.8), 1.5: (6.5, 4.62, 5.17, 1.75), 2.05: (6.8, 4.45, 5.12, 1.75),
    2.5: (7.0, 4.2, 5.07, 1.75), 3.5: (7.36, 3.67, 4.84, 1.75), 4.5: (7.6, 3.0, 4.33, 1.75),
    5.5: (7.75, 1.83, 4.17, 1.75), 6.5: (7.86, 1.0, 4.12, 1.75), 7.5: (7.9, 0.93, 4.09, 1.75),
    8.5: (7.87, 0.88, 4.06, 1.75), 9.5: (7.8, 0.85, 4.04, 1.75), 10.5: (7.7, 0.83, 4.03, 1.75),
    11.5: (7.46, 0.81, 4.01, 1.75), 12.5: (7.2, 0.8, 3.99, 1.75), 13.5: (7.08, 0.79, 3.98, 2.0),
    14.5: (7.0, 0.78, 3.97, 2.0), 15.5: (6.9, 0.77, 3.96, 2.0), 16.5: (6.77, 0.75, 3.95, 2.0),
    17.5: (6.61, 0.71, 3.94, 2.0), 18.5: (6.4, 0.67, 3.92, 2.0), 19.5: (6.0, 0.6, 3.82, 2.0),
    20.5: (5.5, -0.02, 3.42, 2.3), 21.5: (5.06, -0.6, 2.98, 2.3), 22.5: (4.6, -0.6, 2.5, 2.3),
    23.5: (4.11, -0.6, 2.13, 2.3), 24.5: (3.6, -0.6, 1.84, 2.3), 25.15: (3.25, -0.6, 1.69, 2.3),
}
CAR_HW = {
    "230": [(1.05, 0.35), (1.5, 2.5), (2.5, 5.5), (3.5, 7.5), (4.5, 8.5), (5.5, 10.1), (6.5, 11.1), (7.5, 12.1),
            (8.5, 13.1), (9.5, 14.1), (10.5, 13.1), (11.5, 12.1), (12.5, 8.1), (13.5, 7.1), (14.5, 6.1),
            (15.5, 6.1), (16.5, 6.1), (17.5, 6.1), (18.5, 7.1), (19.5, 10.1), (20.5, 12.1), (21.5, 13.5),
            (22.5, 15.5), (23.5, 16.5), (24.5, 16.5), (25.15, 15.9)],
    "192": [(2.05, 0.35), (2.5, 1.5), (3.5, 3.5), (4.5, 4.5), (5.5, 6.1), (6.5, 7.1), (7.5, 8.1), (8.5, 9.1),
            (9.5, 10.1), (10.5, 9.1), (11.5, 8.1), (12.5, 4.1), (13.5, 3.1), (14.5, 1.6), (15.5, 1.6),
            (16.5, 1.6), (17.5, 1.6), (18.5, 3.1), (19.5, 6.1), (20.5, 8.1), (21.5, 9.5), (22.5, 11.5),
            (23.5, 12.5), (24.5, 12.5), (25.15, 11.9)],
}
# 192's spine under the closed shell band (rows 14-17) is a low strip, not the crest.
CAR_192_BAND = {14.5: (4.4, 0.6, 3.0, 2.0), 15.5: (4.4, 0.6, 3.0, 2.0), 16.5: (4.4, 0.6, 3.0, 2.0), 17.5: (4.4, 0.6, 3.0, 2.0)}
CAR_192_TIP = {2.05: (6.4, 4.7, 5.12, 1.8)}

# The left chrome shell of the wide segment (230); 192's sits 4 px further in (and closes over the axis).
SHELL_230 = [  # y, cx, hw, zm, tilt, zt, zb
    (5.02, 14.5, 1.75, 1.6, 0.6, 2.0, 1.35), (5.2, 14.5, 2.3, 1.6, 0.6, 2.56, 1.0), (5.5, 14.5, 2.5, 1.6, 0.6, 3.2, 0.6),
    (6.5, 13.0, 3.0, 1.85, 0.6, 3.45, 0.85), (7.5, 11.5, 3.5, 2.08, 0.52, 3.68, 1.08),
    (8.5, 10.5, 3.5, 2.29, 0.54, 3.89, 1.29), (9.5, 9.5, 3.5, 2.46, 0.54, 4.06, 1.46),
    (10.5, 9.5, 4.5, 2.59, 0.43, 4.19, 1.59), (11.5, 9.5, 5.5, 2.67, 0.35, 4.27, 1.67),
    (12.5, 11.5, 7.5, 2.7, 0.26, 4.3, 1.7), (13.5, 11.5, 8.5, 2.12, 0.23, 3.72, 1.12),
    (14.5, 12.0, 9.0, 2.03, 0.21, 3.63, 1.03), (15.5, 12.0, 9.0, 1.9, 0.21, 3.5, 0.9),
    (16.5, 12.0, 9.0, 1.72, 0.21, 3.32, 0.72), (17.5, 12.0, 9.0, 1.51, 0.2, 3.11, 0.51),
    (18.5, 11.5, 8.5, 1.28, 0.21, 2.88, 0.28), (19.5, 10.5, 6.5, 1.05, 0.27, 2.65, 0.05),
    (20.5, 12.0, 3.0, 1.05, 0.58, 2.65, 0.05), (21.5, 11.5, 1.5, 1.05, 0.6, 2.41, 0.2),
    (21.8, 11.5, 1.35, 1.05, 0.6, 1.93, 0.5), (21.98, 11.5, 0.98, 1.05, 0.6, 1.37, 0.85),
]
SHELL_192_BAND = {14.5: (16.43, 9.43, 2.33, 0.24, 3.93, 1.33), 15.5: (16.43, 9.43, 2.2, 0.23, 3.8, 1.2),
                  16.5: (16.43, 9.43, 2.02, 0.23, 3.62, 1.02), 17.5: (16.43, 9.43, 1.81, 0.23, 3.41, 0.81)}
LIP_230 = [[12.55, 5.5, 1.33, 0.5], [8.55, 7.5, 1.3, 0.5], [6.55, 9.5, 1.62, 0.5], [4.55, 11.5, 1.53, 0.5],
           [3.55, 13.5, 0.77, 0.5], [3.55, 15.5, 0.57, 0.5], [3.55, 17.5, 0.25, 0.5], [4.55, 19.5, 0.0, 0.5],
           [10.55, 21.5, 1.38, 0.5]]
BELLY_Z = [(4, 2.1), (4.5, 1.2), (5.5, -0.2), (6.5, -1.6), (7.5, -3.8), (8.5, -3.89), (9.5, -3.97), (10.5, -4.05),
           (11.5, -4.11), (12.5, -4.16), (13.5, -4.19), (14.5, -4.2), (15.5, -4.19), (16.5, -4.16), (17.5, -4.11),
           (18.5, -4.05), (19.5, -3.97), (20.5, -3.32), (21.5, -2.74), (22.5, -2.16), (23.5, -1.58), (24.5, -1.0),
           (25.0, 0.6)]
BELLY_HW_230 = [3.16, 5.27, 8.37, 9.61, 10.85, 11.47, 12.09, 12.71, 13.33, 13.33, 13.5, 13.5, 13.5, 13.5, 13.5,
                13.5, 13.33, 10.23, 9.61, 9.61, 10.23, 10.23, 6.14]


def build_segment(seg, M):
    PARTS.clear()
    s = 4.0 if seg == "230" else 0.0  # the wide segment's shells and sides sit 4 px further out

    # 1. CARAPACE: green lacquered dorsal plate, raised hood at the tail tip, ridged crest, spine, skirt.
    st = []
    for y, hw in CAR_HW[seg]:
        zt, zb, zm, pt = CAR_Z[y]
        if seg == "192":
            zt, zb, zm, pt = CAR_192_BAND.get(y, CAR_192_TIP.get(y, (zt, zb, zm, pt)))
        st.append({"y": y, "hw": hw, "zt": zt, "zb": zb, "zm": zm, "pt": pt, "pb": 2.0})
    grooves = [(19.15, 0.18, 0.22), (22.4, 0.16, 0.16)]
    car = loftY("carapace", M["CARAPACE"], st, nseg=28, dy=0.45, grooves=grooves)

    # Ribs: machined ridges across the crest that follow its surface (the sprite's bright rib lines).
    ribs = {"230": [(4.5, 4.2), (6.5, 4.2), (8.5, 4.2), (12.5, 4.05), (14.5, 3.05)],
            "192": [(4.5, 2.25), (6.5, 3.55), (8.5, 4.2), (20.5, 4.05)]}[seg]
    for ry, rw in ribs:
        n = 7
        ctrl = []
        for k in range(n):
            x = AX - rw + 2 * rw * k / (n - 1)
            r = 0.42 if 0 < k < n - 1 else 0.15
            ctrl.append([x, ry, surfZ(car, x, ry) + 0.12, r])
        tube("rib", M["RIB"], ctrl, nseg=6, p=2.6, vs=0.85, per=2)

    # Toe lobes either side of the front, and 230's coupling tongue.
    for x in (14.5 + (4 - s), mir(14.5 + (4 - s))):
        blob("lobe", M["LOBE"], (x, 25.1, 1.8), (4.85, 2.1, 1.4), p=2.3, nu=16, nv=6)
    if seg == "230":
        blob("tongue", M["LOBE"], (AX, 25.4, 1.7), (2.4, 1.8, 1.2), p=2.4, nu=12, nv=6)

    # 2. CHROME SIDE SHELLS: tilted domed plates, stepped pauldron (rows 5-12) over the lower plate.
    for side in (1, -1):
        sh = []
        for y, cx, hw, zm, tl, zt, zb in SHELL_230:
            cx = cx + (4 - s)
            if seg == "192" and y in SHELL_192_BAND:
                cx, hw, zm, tl, zt, zb = SHELL_192_BAND[y]
            if side < 0:
                cx, tl = mir(cx), -tl
            sh.append({"y": y, "cx": cx, "hw": hw, "zm": zm, "tilt": tl, "zt": zt + CROWN * clamp((zt - zm) / 1.6, 0, 1), "zb": zb,
                       "pt": 2.2, "pb": 2.0})
        shell = loftY("shell", M["SHELL"], sh, nseg=22, dy=0.4, grooves=[(12.75, 0.14, 0.18)])
        lip = [[(c[0] + (4 - s)) if side > 0 else mir(c[0] + (4 - s))] + c[1:] for c in LIP_230]
        tube("shell_lip", M["LIP"], lip, nseg=6, p=2.0, per=3)
        for bx, by in ((10.38, 9.5), (13.63, 13.5)):
            x = bx + (4 - s)
            x = x if side > 0 else mir(x)
            blob("bolt", M["BOLT"], (x, by, surfZ(shell, x, by) + 0.05), (0.55, 0.55, 0.3), nu=8, nv=4)

    # 3. BELLY: closed round dark underside, no detail.
    bst = []
    for (y, zb), hw in zip(BELLY_Z, BELLY_HW_230):
        hw = hw - (4 - s) * (0.62 if hw > 4 else 0.45)
        bst.append({"y": y, "hw": hw, "zt": 2.2, "zb": zb, "pt": 2.0, "pb": 2.3})
    loftY("belly", M["BELLY"], bst, nseg=16, dy=1.2)
    return list(PARTS)


# ---------------------------------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------------------------------

def materials(sprite, tag):
    def pal(i, **kw):
        return common.palette_material(sprite, i, tag, **kw)
    mats = [
        ("CARAPACE", pal(37, metallic=0.25, roughness=0.3)),
        ("RIB", pal(40, metallic=0.25, roughness=0.28)),
        ("LOBE", pal(36, metallic=0.25, roughness=0.32)),
        ("SHELL", pal(105, metallic=0.45, roughness=0.35)),
        ("LIP", pal(104, metallic=0.5, roughness=0.3)),
        ("BOLT", pal(106, metallic=0.5, roughness=0.3)),
        ("BELLY", pal(101, metallic=0.4, roughness=0.6)),
    ]
    for key, m in mats:
        if key in ("SHELL", "LIP", "BOLT") and m.node_tree:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = CHROME_SPEC
    return {k: i for i, (k, _) in enumerate(mats)}, [m for _, m in mats]


def B(p, dy):
    return Vector(((p[0] - 24) / 12, (14 - p[1] + dy) / 12, p[2] / 12))


def part_bmesh(P, dy=0.0):
    bm = bmesh.new()
    vs = [bm.verts.new(B(p, dy)) for p in P.v]
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


def piece_mesh(name, k, parts, mats, dy):
    """Clip every part to the piece's box (x 0-24 or 24-48) and cap the cut (D117); overlapping caps on
    the cut line step CAP_STEP apart outward, the taller part outermost (as assembly-newshh-197)."""
    x0, x1 = 24.0 * k, 24.0 * k + 24.0
    items = []
    for P in parts:
        bm = part_bmesh(P, dy)
        xs = [v.co.x * 12 + 24 for v in bm.verts]
        if max(xs) - x0 < MIN_KEEP or x1 - min(xs) < MIN_KEEP:
            bm.free()
            continue
        ys = [v.co.y for v in bm.verts]
        zs = [v.co.z for v in bm.verts]
        items.append([P, bm, (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))])
    line = x1 if k == 0 else x0
    cut = [(n, it[3], it[4]) for n, it in enumerate(items) if it[2][0] < line < it[2][1]]
    cut.sort(key=lambda e: -e[2][1])
    ks = {}
    done = []
    for n, (t0, t1), (z0, z1) in cut:
        over = [ks[m] for m, (u0, u1), (w0, w1) in done if t0 < u1 and u0 < t1 and z0 < w1 and w0 < z1]
        ks[n] = min(max(over) + 1 if over else 0, 4)
        done.append((n, (t0, t1), (z0, z1)))
    out = bmesh.new()
    for n, (P, bm, *_rest) in enumerate(items):
        if n in ks:
            step = (4 - ks[n]) * CAP_STEP
            if k == 0:
                co, no = Vector(((x1 + step - 24) / 12, 0, 0)), Vector((1, 0, 0))
            else:
                co, no = Vector(((x0 - step - 24) / 12, 0, 0)), Vector((-1, 0, 0))
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
    mesh.set_sharp_from_angle(angle=math.radians(40))
    return mesh


def outline_shell_all(obj, coll, voxel=0.03, faces=3000, smooth=6, inside=0.004):
    """common.outline_shell, every outer island kept (copied from assembly-newshh-197, D170)."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    obj.users_collection[0].objects.link(shell)
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
                    bb_[2 * q] <= ba[2 * q] and ba[2 * q + 1] <= bb_[2 * q + 1] for q in range(3)):
                drop.add(a)
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
    data = common.load_sprite(ROOT, "newshh-230")
    for n in ("newshh-232", "newshh-192", "newshh-194"):
        data["colors"].update(common.load_sprite(ROOT, n)["colors"])
    return data


def to_origin(obj, centre):
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    obj.data.transform(Matrix.Translation((-centre.x, -centre.y, 0.0)))
    obj.location = centre


# ---------------------------------------------------------------------------------------------------
# Measuring (top-view raster at k image px per sprite px; no render needed)
# ---------------------------------------------------------------------------------------------------

def raster_top(objs, dy, k=10):
    """Top-view coverage (k px per sprite px) and the top-most material per sample of a segment."""
    import numpy as np
    W, H = 48 * k, 28 * k
    zbuf = np.full((H, W), -1e9)
    mat = -np.ones((H, W), int)
    for obj in objs:
        me = obj.data
        mw = obj.matrix_world
        co = np.array([tuple(mw @ v.co) for v in me.vertices])
        X = (co[:, 0] * 12 + 24) * k
        Y = (14 + dy - co[:, 1] * 12) * k
        Z = co[:, 2]
        for poly in me.polygons:
            vi = list(poly.vertices)
            for t in range(1, len(vi) - 1):
                a, b, c = vi[0], vi[t], vi[t + 1]
                xs, ys = (X[a], X[b], X[c]), (Y[a], Y[b], Y[c])
                x0, x1 = max(0, int(math.floor(min(xs) - 0.5))), min(W - 1, int(math.ceil(max(xs))))
                y0, y1 = max(0, int(math.floor(min(ys) - 0.5))), min(H - 1, int(math.ceil(max(ys))))
                if x1 < x0 or y1 < y0:
                    continue
                gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
                if abs(d) < 1e-12:
                    continue
                l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
                l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
                l2 = 1 - l0 - l1
                ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
                if not ins.any():
                    continue
                z = l0 * Z[a] + l1 * Z[b] + l2 * Z[c]
                sub = zbuf[y0:y1 + 1, x0:x1 + 1]
                upd = ins & (z > sub)
                sub[upd] = z[upd]
                mat[y0:y1 + 1, x0:x1 + 1][upd] = poly.material_index
    return zbuf > -1e8, mat


def sprite_idx(names):
    import numpy as np
    I = -np.ones((28, 48), int)
    pal = {}
    for q, n in enumerate(names):
        d = common.load_sprite(ROOT, n)
        I[:, 24 * q:24 * q + 24] = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in d["frames"][0]["pixels"]]
        pal.update({int(a): tuple(b) for a, b in d["colors"].items()})
    return I, pal


def measure(seg, objs, mats_names, dy, out_dir, k=10):
    import numpy as np
    cov, mat = raster_top(objs, dy, k)
    I, pal = sprite_idx(SEGS[seg])
    m = sprite_mask.masks(I.tolist(), pal)
    res = {"assembly": sprite_mask.measure(m, cov.tolist())["iou_rule_grid"], "pieces": {}}
    for q, n in enumerate(SEGS[seg]):
        d = common.load_sprite(ROOT, n)
        idx = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in d["frames"][0]["pixels"]]
        mo = sprite_mask.masks(idx, {int(a): tuple(b) for a, b in d["colors"].items()})
        t = cov[:, 24 * q * k:(24 * q + 24) * k].tolist()
        res["pieces"][n] = sprite_mask.measure(mo, t)["iou_rule_grid"]
    # region colour: sprite pixels under each material (sample at pixel centre), trimmed median of
    # their palette index within the ramp (darkest/brightest 15 % dropped: lighting)
    cm = mat[k // 2::k, k // 2::k]
    inner = np.array(m["inner"], bool)
    reg = {}
    for i, nm in enumerate(mats_names):
        v = np.sort(I[(cm == i) & inner & (I > 1)])
        if len(v) == 0:
            continue
        lo, hi = int(len(v) * 0.15), max(int(len(v) * 0.85), int(len(v) * 0.15) + 1)
        reg[nm] = {"px": int(len(v)), "median": int(np.median(v[lo:hi]))}
    res["regions"] = reg
    # masks for the sheet
    np.save(out_dir / f"cov_{seg}.npy", cov)
    np.save(out_dir / f"mat_{seg}.npy", cm)
    np.save(out_dir / f"inner_{seg}.npy", np.array(m["inner"], bool))
    return res


def build(seg, review_dir=None):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = merged_sprite()
    coll = common.reset_collection(ASM[seg])
    M, mats = materials(sprite, "nshh" + seg)
    names = list(M)
    pieces, shells, seg_objs, report = {}, {}, {}, {}
    for s, pns in SEGS.items():
        if s != seg and not review_dir:
            continue
        parts = build_segment(s, M)
        seg_objs[s] = []
        for q, pn in enumerate(pns):
            obj = bpy.data.objects.new(pn, piece_mesh(pn, q, parts, mats, 0.0))
            coll.objects.link(obj)
            pieces[pn] = obj
            seg_objs[s].append(obj)
        bpy.context.view_layer.update()
        for pn in pns:
            shells[pn] = outline_shell_all(pieces[pn], coll)
        report[s] = {"tris": {pn: sum(len(p.vertices) - 2 for p in pieces[pn].data.polygons) for pn in pns}}
    bpy.context.view_layer.update()
    if review_dir:
        rd = Path(review_dir)
        rd.mkdir(parents=True, exist_ok=True)
        for s in seg_objs:
            report[s].update(measure(s, seg_objs[s], names, 0.0, rd))
        (rd / "measure.json").write_text(json.dumps(report, indent=1))
        print("MEASURE", json.dumps(report))
    # one frame per piece; the origin of each piece is its cell centre (x symmetric about it)
    for pn in SEGS[seg]:
        q = SEGS[seg].index(pn)
        centre = Vector((((24 * q + 12) - 24) / 12, 0.0, 0))
        to_origin(pieces[pn], centre)
        to_origin(shells[pn], centre)
        pieces[pn].location = (0, 0, 0)
        shells[pn].location = (0, 0, 0)
        data = common.load_sprite(ROOT, pn)
        common.export_sprite_model(ROOT, [pieces[pn], shells[pn]], f"enemies/{pn}", data["sprites"])


def run(seg):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    build(seg, argv[argv.index("--review") + 1] if "--review" in argv else None)
