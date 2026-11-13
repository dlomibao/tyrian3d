"""TORM tail spike (newshh.shp frame 155): a 3D version of its sprite..

Seen in episode 2 (level 2.2): the top of the TORM insect column (155 over the abdomen segments
assembly-newshh-192/-230 and the D170 head assembly-newshh-159/-197). The last abdominal segment of
the insect craft drawn out into a steel stinger: a long hardened needle up the screen, a faired nose
cone, a broad rounded body of plain plates, a raised spine down the centre (a narrow rail on the nose
widening to a flat chamfered keel plate over the rear body with four machined rib bars, the sprite's
bright 107-109 ladder), a crisp chamfered chine round the plan edge from the nose to the lobes with
rivets along it, panel seams at the nose collar (row 13) and the rear plate (rows 23-24), and two tail
lobes that carry the hull's top and chine on either side of a dark recessed coupling notch. It flies free: one closed
round keel underneath, no floor plate.

Sprite px coordinates: x right, y down (24 x 28 edges), mirror axis x 12.5; Blender X = (x - 12) / 12,
Y = (14 - y) / 12, Z = z / 12 (z in px). Helpers copied from lib_torm_abdomen / D170 (script-local).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshh-155.py   (or blender --background --python this [-- --review outdir])
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

NAME = "newshh-155"
ROOT = WT
AX = 12.5
STEEL_SPEC = 0.65  # Specular IOR Level (D176: a polished grey needs F0 or it reads dull)


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, a, b):
    return max(a, min(b, v))


def se(c, p):
    return math.copysign(abs(c) ** (2 / p), c)


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


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


def table(pts):
    return pchip([p[0] for p in pts], [p[1] for p in pts])


# ---------------------------------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------------------------------

class Part:
    def __init__(self, name, mat):
        self.name, self.mat = name, mat
        self.v, self.f = [], []
        self.sharp = []  # vertex index pairs: crisp edges (chines, chamfer lines)

    def vert(self, p):
        self.v.append(tuple(p))
        return len(self.v) - 1

    def face(self, idx, mat=None):
        self.f.append((tuple(idx), self.mat if mat is None else mat))


PARTS = []


def add(part):
    PARTS.append(part)
    return part


def ring_faces(P, rings, closed=True, cap0=True, cap1=True):
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            P.face((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
    for ring, rev, flag in ((rings[0], True, cap0), (rings[-1], False, cap1)):
        if not flag:
            continue
        cen = [sum(P.v[q][a] for q in ring) / n for a in range(3)]
        c = P.vert(cen)
        for i in range(n):
            j = (i + 1) % n
            P.face((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))


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


def tube(name, mat, ctrl, nseg=12, p=2.0, vs=1.0, per=3, cap=True):
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
        r = max(path[i][1], 0.004)
        ring = []
        for j in range(nseg):
            ang = 2 * math.pi * (j + 0.5) / nseg
            q = Vector(path[i][0]) + S * (se(math.cos(ang), p) * r) + U * (se(math.sin(ang), p) * r * vs)
            ring.append(P.vert(q))
        rings.append(ring)
    ring_faces(P, rings, cap0=cap, cap1=cap)
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
# The spike
# ---------------------------------------------------------------------------------------------------

# Plan half width by row (the sprite's inner mask, rows 0.75 nose tip to 25.32 rear). The nose runs one
# faired curve through the middles of the sprite's 1 px steps (a stepped table rippled the cone).
HW = table([(0.75, 0.0), (1.0, 0.2), (2.0, 0.62), (4.5, 1.6), (7.5, 2.62), (10.0, 3.55), (12.0, 4.45),
            (13.9, 5.45), (15.4, 6.45), (16.9, 7.4), (17.75, 7.75), (18.2, 8.45), (19.5, 8.55), (24.2, 8.55),
            (24.7, 8.1), (25.0, 6.9), (25.2, 4.8), (25.32, 2.0)])
# Crown (centreline top), widest line and keel, px above the model's floor plane z 0.
CROWN = table([(0.75, 3.12), (2.0, 3.55), (5.0, 4.15), (9.0, 4.85), (13.0, 5.5), (16.5, 5.9),
               (19.0, 5.8), (21.0, 5.3), (22.5, 4.6), (24.0, 3.85), (24.8, 3.3), (25.32, 2.8)])
ZM = table([(0.75, 3.1), (5.0, 3.05), (12.0, 2.9), (19.0, 2.75), (24.0, 2.5), (25.32, 2.4)])
KEEL = table([(0.75, 3.08), (2.0, 2.65), (5.0, 2.05), (10.0, 1.3), (15.0, 0.85), (21.0, 0.7), (24.0, 0.95),
              (24.8, 1.3), (25.32, 1.75)])
RIBS = [14.5, 16.5, 18.5, 21.5]  # the spine's bright rib bars (sprite rows 14, 16, 18, 21: 107-109)
ZT = CROWN
# Panel seams cut across the top as real section steps (y, half width, depth px): the nose/body collar at
# row 13 and the rear plate seam on the sprite's dark 101/102 band across rows 23-24.
SEAMS = [(13.0, 0.16, 0.2), (23.45, 0.16, 0.22)]
QD = 1.7  # top dome exponent (flat-ish plates, a firm edge slope into the chine)
CH_SLOPE = 0.7  # chamfer run per rise (about 55 degrees down from the top to the widest line)


def chine_dims(y):
    """Body section at row y: half width, crown, widest-line z, keel, chamfer run, chine z."""
    hw, zt, zm, zb = max(HW(y), 0.02), ZT(y), ZM(y), KEEL(y)
    cv = clamp(0.35 * (zt - zm), 0.0, 1.1)
    ch = min(cv * CH_SLOPE, 0.3 * hw)
    return hw, zt, zm, zb, ch, zm + cv


def dome(u, zt, zc):
    return zc + (zt - zc) * (1 - min(abs(u), 1.0) ** QD)


def body_top(x, y, clamp_dome=False):
    """Top surface z of the hull at (x, y): the dome inside the chine, the chamfer outside it."""
    hw, zt, zm, zb, ch, zc = chine_dims(y)
    w = hw - ch
    d = abs(x - AX)
    if d <= w or clamp_dome:
        return dome(d / max(w, 1e-6), zt, zc)
    return zc - (zc - zm) * min((d - w) / max(ch, 1e-6), 1.0)


def seam_depth(y):
    for gy, gw, gd in SEAMS:
        if gy - gw + 0.01 < y < gy + gw - 0.01:
            return gd
    return 0.0


def section_loft(name, mat, ys, ring_fn, sharp=(), matf=None):
    """Loft through rings ring_fn(y) -> [(x, z)] (same count per station, sprite px), closed and capped.
    `sharp`: ring indices whose lines along y are crisp edges (chines). matf(y0, y1, j) may give face
    (segment j of the ring between stations y0 and y1) another material."""
    P = add(Part(name, mat))
    rings = []
    for y in ys:
        rings.append([P.vert((x, y, z)) for x, z in ring_fn(y)])
    n = len(rings[0])
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            m = matf(ys[k], ys[k + 1], i) if matf else None
            P.face((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]), m)
        for i in sharp:
            P.sharp.append((rings[k][i], rings[k + 1][i]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        cen = [sum(P.v[q][a] for q in ring) / n for a in range(3)]
        c = P.vert(cen)
        for i in range(n):
            j = (i + 1) % n
            P.face((ring[j], ring[i], c) if rev else (ring[i], ring[j], c))
    return P


NT, NB = 16, 12  # body ring: top points between the chines, keel points


def body_ring(y):
    hw, zt, zm, zb, ch, zc = chine_dims(y)
    w = hw - ch
    g = seam_depth(y)
    if g:
        zt, zc, w = zt - g, zc - 0.8 * g, max(w - 0.5 * g, 0.01)
    pts = [(AX + hw, zm), (AX + w, zc)]
    for i in range(1, NT):
        u = math.sin(math.pi / 2 * (1 - 2 * i / NT))
        pts.append((AX + u * w, dome(u, zt, zc)))
    pts += [(AX - w, zc), (AX - hw, zm)]
    for i in range(1, NB):
        a = math.pi + math.pi * i / NB
        pts.append((AX + hw * se(math.cos(a), 2.1), zm - (zm - zb) * se(-math.sin(a), 2.1)))
    return pts


def stations(y0, y1, step, extra=()):
    ys = {round(y0, 4), round(y1, 4)}
    y = y0
    while y < y1:
        ys.add(round(y, 4))
        y += step(y)
    for e in extra:
        ys.add(round(e, 4))
    return sorted(v for v in ys if y0 <= v <= y1)


def body(M):
    extra = [24.85, 25.0, 25.1, 25.2, 25.27]
    for gy, gw, _ in SEAMS:
        extra += [gy - gw, gy - gw + 0.02, gy + gw - 0.02, gy + gw]
    ys = stations(0.75, 25.32, lambda y: 0.5 if y < 13 else 0.6, extra)

    def matf(y0, y1, j):
        if j < NT + 2 and seam_depth(0.5 * (y0 + y1)):
            return M["SEAM"]
        return None
    return section_loft("body", M["BODY"], ys, body_ring, sharp=(0, 1, NT + 1, NT + 2), matf=matf)


# Spine: one raised machined ridge down the centre from the collar to row 23 (the sprite's light centre
# column), flat-topped with ~42 degree chamfers: a narrow rail on the nose (105 -> 107) widening over the
# rear body to a 4.8 px keel plate (106) that carries four rib bars (107; the sprite's 107-109 ladder).
SP = [(3.0, 0.24, 0.32), (4.5, 0.4, 0.42), (7.0, 0.5, 0.48), (10.0, 0.55, 0.5), (11.8, 0.7, 0.5),
      (13.2, 1.8, 0.5), (14.2, 2.4, 0.48), (19.5, 2.45, 0.46), (21.5, 2.3, 0.42), (22.4, 1.7, 0.3),
      (22.95, 0.6, 0.1), (23.1, 0.05, 0.0)]
SPF = [pchip([q[0] for q in SP], [q[k] for q in SP]) for k in (1, 2)]
CHAMF = 0.9  # chamfer rise per run (about 42 degrees)


def spine_dims(y):
    hw, h = max(SPF[0](y), 0.02), max(SPF[1](y), 0.0)
    # The chamfers run down into the hull (no standing wall), so the plate reads as one hard ridge.
    c = min(0.4 * hw, (h + 0.35) / CHAMF)
    return hw, CROWN(y) + h, c


def spine_top(x, y):
    hw, zt, c = spine_dims(y)
    d = abs(x - AX)
    return zt if d <= hw - c else zt - CHAMF * (d - (hw - c))


def spine_ring(y):
    hw, zt, c = spine_dims(y)
    zb = CROWN(y) - 0.9
    zc = zt - CHAMF * c
    return [(AX + hw, zb), (AX + hw, zc), (AX + hw - c, zt), (AX, zt), (AX - hw + c, zt), (AX - hw, zc), (AX - hw, zb)]


# Tail lobes either side of the notch: the rear plates drawn out past the coupling. Their tops carry the
# hull's own section on (its dome as it stands at the rear seam, lifted a hair so the seam reads as a plate
# step), chamfered at both edges like the hull's chine, round plan ends from the sprite. Plan: y, cx, hw;
# zb is the round keel under them.
LOBE = [  # y, cx, hw, zb
    (21.5, 8.2, 2.3, 1.0), (22.8, 7.85, 3.2, 1.0), (24.0, 7.75, 3.5, 1.0), (25.2, 7.8, 3.2, 1.2),
    (26.2, 7.8, 2.1, 1.5), (26.8, 7.85, 1.4, 1.85), (27.05, 7.9, 0.05, 2.3)]
LOBEF = [pchip([q[0] for q in LOBE], [q[k] for q in LOBE]) for k in (1, 2, 3)]
LOBE_YF = 23.62  # the row whose hull section the lobe tops carry on
NTL, NBL = 12, 10


def lobe_ring(y, side):
    cx, hw, zb = (f(y) for f in LOBEF)
    hw = max(hw, 0.02)
    if side < 0:
        cx = 2 * AX - cx
    lift = lerp(-0.25, 0.1, smooth((y - 23.32) / 0.3)) - 0.38 * smooth((y - 25.3) / 1.75)
    zm = ZM(min(y, 25.32))

    def top(x):
        return body_top(x, LOBE_YF, clamp_dome=True) + lift
    chl = min(0.3, 0.3 * hw)
    xo, xi = cx + hw, cx - hw  # +x edge, -x edge
    pts = []
    zo, zi = top(xo - chl), top(xi + chl)
    cvo, cvi = min(0.45, 0.6 * (zo - zm)), min(0.45, 0.6 * (zi - zm))
    pts += [(xo, zm), (xo, zo - cvo), (xo - chl, zo)]
    for i in range(1, NTL):
        x = lerp(xo - chl, xi + chl, i / NTL)
        pts.append((x, top(x)))
    pts += [(xi + chl, zi), (xi, zi - cvi), (xi, zm)]
    for i in range(1, NBL):
        a = math.pi + math.pi * i / NBL
        pts.append((cx + hw * se(math.cos(a), 2.1), zm - (zm - zb) * se(-math.sin(a), 2.1)))
    return pts


def build_parts(M):
    PARTS.clear()
    body(M)

    # Needle: a hardened tip held level along the nose line (D163), with a machined collar.
    tube("needle", M["NEEDLE"], [[AX, 0.1, 3.12, 0.0], [AX, 0.7, 3.14, 0.13], [AX, 1.6, 3.2, 0.25],
                                 [AX, 2.55, 3.28, 0.36]], nseg=10, per=2)
    tube("collar", M["RAIL"], [[AX, 2.2, 3.3, 0.38], [AX, 2.45, 3.34, 0.58], [AX, 2.9, 3.42, 0.6],
                               [AX, 3.2, 3.48, 0.42]], nseg=14, per=2)

    def spine_mat(y0, y1, j):
        y = 0.5 * (y0 + y1)
        return M["NEEDLE"] if y < 6.5 else (M["SPINE"] if y < 12.6 else M["RIDGE"])
    section_loft("spine", M["RIDGE"], stations(3.0, 23.1, lambda y: 0.4), spine_ring, sharp=(1, 2, 4, 5),
                 matf=spine_mat)

    # Rib bars across the keel plate: squared machined bars over its flat top and down its chamfers.
    for ry in RIBS:
        hw, zt, c = spine_dims(ry)
        ctrl = []
        n = 7
        for k in range(n):
            u = -1 + 2 * k / (n - 1)
            x = AX + u * hw * 0.96
            r = 0.3 if abs(u) < 0.7 else 0.2
            ctrl.append([x, ry, spine_top(x, ry) + 0.06, r])
        tube("rib", M["RIB"], ctrl, nseg=8, p=2.6, vs=0.85, per=2)

    # Rivets along the chine, three a side between the seams (the abdomen's bolt heads, scaled).
    for ry in (15.2, 18.2, 21.2):
        hw, zt, zm, zb, ch, zc = chine_dims(ry)
        for side in (1, -1):
            x = AX + side * (hw - ch - 0.55)
            blob("rivet", M["RIDGE"], (x, ry, body_top(x, ry) + 0.02), (0.36, 0.36, 0.2), nu=10, nv=4)

    ly = stations(23.32, 27.05, lambda y: 0.25, (23.47, 23.62))
    for side in (1, -1):
        section_loft("lobe", M["LOBE"], ly, (lambda y, s=side: lobe_ring(y, s)),
                     sharp=(0, 1, 2, NTL + 2, NTL + 3, NTL + 4))
    # Coupling socket in the notch, sunk below the lobes' tops: the sprite's dark 97/98 cavity.
    blob("coupling", M["COUPLING"], (AX, 24.95, 2.45), (1.95, 0.42, 0.55), p=2.4, nu=12, nv=6)
    return list(PARTS)


# ---------------------------------------------------------------------------------------------------
# Blender side
# ---------------------------------------------------------------------------------------------------

def materials(sprite):
    def pal(i, **kw):
        return common.palette_material(sprite, i, NAME, **kw)
    mats = [
        ("BODY", pal(104, metallic=0.5, roughness=0.42)),
        ("NEEDLE", pal(105, metallic=0.55, roughness=0.34)),
        ("SPINE", pal(107, metallic=0.55, roughness=0.38)),
        ("RIDGE", pal(106, metallic=0.55, roughness=0.42)),
        ("RIB", pal(107, metallic=0.55, roughness=0.34)),
        ("RAIL", pal(104, metallic=0.5, roughness=0.4)),
        ("LOBE", pal(102, metallic=0.45, roughness=0.44)),
        ("COUPLING", pal(98, metallic=0.4, roughness=0.6)),
        ("SEAM", pal(101, metallic=0.4, roughness=0.6)),
    ]
    for key, m in mats:
        if key in ("BODY", "NEEDLE", "SPINE", "RIDGE", "RIB") and m.node_tree:
            bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = STEEL_SPEC
    return {k: i for i, (k, _) in enumerate(mats)}, [m for _, m in mats]


def B(p):
    return Vector(((p[0] - 12) / 12, (14 - p[1]) / 12, p[2] / 12))


def part_bmesh(P, bm):
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
    for a, b in P.sharp:
        if a != b:
            e = bm.edges.get((vs[a], vs[b]))
            if e is not None:
                e.smooth = False


def model_mesh(parts, mats):
    out = bmesh.new()
    for P in parts:
        bm = bmesh.new()
        part_bmesh(P, bm)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-6)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new("tmp")
        bm.to_mesh(me)
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
        bm.free()
    mesh = bpy.data.meshes.new(NAME)
    out.to_mesh(mesh)
    out.free()
    for m in mats:
        mesh.materials.append(m)
    tagged = [e.use_edge_sharp for e in mesh.edges]
    mesh.set_sharp_from_angle(angle=math.radians(40))
    for e, t in zip(mesh.edges, tagged):
        if t:
            e.use_edge_sharp = True
    return mesh


def outline_shell_sealed(obj, coll, voxel=0.02, faces=1500, smooth_it=6, inside=0.004):
    """D90/D118: the outline shell from a sealed copy (voxel remesh closes every part into one hull)
    taken before any culling, outer island only, smoothed, held a hair inside the model."""
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
    keep = max(islands, key=len)
    ids = {v.index for v in keep}
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in ids], context="VERTS")
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth_it
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


# ---------------------------------------------------------------------------------------------------
# Measuring (top-view raster at k image px per sprite px; no render needed)
# ---------------------------------------------------------------------------------------------------

def raster_top(obj, k=10):
    import numpy as np
    W, H = 24 * k, 28 * k
    zbuf = np.full((H, W), -1e9)
    mat = -np.ones((H, W), int)
    me = obj.data
    co = np.array([tuple(obj.matrix_world @ v.co) for v in me.vertices])
    X = (co[:, 0] * 12 + 12) * k
    Y = (14 - co[:, 1] * 12) * k
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


def measure(obj, names, sprite, out_dir, k=10):
    import numpy as np
    import sprite_mask
    cov, mat = raster_top(obj, k)
    colors = {int(a): tuple(b) for a, b in sprite["colors"].items()}
    res = {}
    for fr in sprite["frames"]:
        idx = fr["pixels"]
        m = sprite_mask.masks(idx, colors)
        r = sprite_mask.measure(m, cov.tolist())
        res[str(fr["index"])] = {k2: r[k2] for k2 in ("iou_rule", "iou_rule_grid", "iou_outer_grid", "iou_inner_grid", "edge_vs_inner_px")}
        I = np.array(idx)
        inner = np.array(m["inner"], bool)
        grid = cov.reshape(28, k, 24, k).mean(axis=(1, 3)) >= 0.5
        rows = []
        for y in range(28):
            mo = [x for x in range(24) if grid[y, x] and not inner[y, x] and not m["free"][y][x]]
            so = [x for x in range(24) if inner[y, x] and not grid[y, x]]
            if mo or so:
                rows.append([y, mo, so])
        res[str(fr["index"])]["rows_off"] = rows
        cm = mat[k // 2::k, k // 2::k]
        reg = {}
        for i, nm in enumerate(names):
            v = np.sort(I[(cm == i) & inner & (I > 1)])
            if len(v) == 0:
                continue
            lo, hi = int(len(v) * 0.15), max(int(len(v) * 0.85), int(len(v) * 0.15) + 1)
            reg[nm] = {"px": int(len(v)), "median": int(np.median(v[lo:hi]))}
        res[str(fr["index"])]["regions"] = reg
        np.save(out_dir / "cov.npy", cov)
        np.save(out_dir / "mat.npy", cm)
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    review = Path(argv[argv.index("--review") + 1]) if "--review" in argv else None
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    M, mats = materials(sprite)
    parts = build_parts(M)
    obj = bpy.data.objects.new(NAME, model_mesh(parts, mats))
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    # Outline shell from a sealed copy of the whole model (D90/D118).
    src = bpy.data.objects.new(NAME + "_src", model_mesh(build_parts(M), mats))
    coll.objects.link(src)
    bpy.context.view_layer.update()
    shell = outline_shell_sealed(src, coll)
    shell.name = NAME + "_outline"
    bpy.data.objects.remove(src, do_unlink=True)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    report = {"tris": tris, "shell_tris": sum(len(p.vertices) - 2 for p in shell.data.polygons)}
    if review:
        review.mkdir(parents=True, exist_ok=True)
        report["frames"] = measure(obj, list(M), sprite, review)
        (review / "report.json").write_text(json.dumps(report, indent=1))
    print("REPORT", json.dumps(report))
    if out:
        common.export_glb([obj, shell], out)
        print("exported", out)
    else:
        common.export_sprite_model(ROOT, [obj, shell], f"enemies/{NAME}", sprite["sprites"])


if __name__ == "__main__":
    main()
