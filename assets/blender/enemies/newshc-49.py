"""newshc-49: blue armoured core pod (newshc.shp 49/51/53, 24x28, boss part).

Silhouette first. From the small tilted game camera the sprite reads as three things: a thick
light-blue armour hood curling over the north edge and down the whole west side, a glowing core
sitting in a dark socket in the crook of that hood, and a stack of flat machine blocks (rib,
buttress, rail, deck, vents) filling the east and south. So the model is built in that order of
weight: (1) the base casting traced from the D74 inner mask (top IoU = 1 on every frame), (2) the
hood as one pchip-heighted loft of chamfered closed sections with a crest ridge on the line of the
sprite's 60-62 streak (sheen, not paint) and three modelled segment joints, (3) the core: one
sphere whose pole axis points at the hot kernel, so the hot window is a round cap of the same
surface (no bump), seated in a dark machined collar, (4) the machine blocks as chamfered prisms
at the blueprint's places, then the small machined detail (rivets, hex bolts, locking pins,
louvres, vanes, lugs). Underside: the flat chamfered base, closed, nothing else.

Units: sprite px, x = c - 12, y = 14 - r for pixel-edge (c, r), z up; 1 px = 1/12 Blender unit.
Colours: palette index of each sprite region (median, darkest/brightest 15 % dropped = lighting);
the frames only change the core (49:115 51:120 53:123) and its hot kernel (122/126/127), D17.

Run: Blender -b --factory-startup -P newshc-49.py -- [--no-bake]
Exports public/models/enemies/newshc-49.glb and the src/render/spriteModels entry; AO/roughness bake ("bake": "model").
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path[:0] = [str(Path(__file__).resolve().parents[1])]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "newshc-49"
PX = 1 / 12


def E(c, r):
    return (c - 12.0, 14.0 - r)


# ---------- blueprint dims (sprite px) ----------
HULL_TOP, HULL_CH, HULL_BCH = 2.0, 0.4, 0.35
SHELL_H = [4.7, 6.4, 6.6, 6.4, 5.9]       # hood crest height, east end -> corner -> south end
SHELL_UC = 0.58                           # crest across the band (0 outer edge, 1 inner edge)
SHELL_FOOT = 0.12
SHELL_OUT = 0.07                          # hood outer wall stands this far proud of the base wall
CORE_C, CORE_R, CORE_RAD, CORE_Z = 12.5, 13.5, 3.35, 2.55
HOT_C, HOT_R, HOT_RAD = 12.05, 12.95, 1.25
CORE_SQ = 0.76                            # dome height scale: a flush glowing core, not a button
COLLAR_RO, COLLAR_RI, COLLAR_Z1 = 3.95, 3.2, 2.85
LH = 3.8                                  # header + mount rib top
PIL = dict(x0=20.0, x1=23.0, r0=5.0, r1=16.0, z=4.6, step=20.9, zs=3.9)

LEFT = [(1, 12.6), (1.6, 11.7), (2.05, 10.6), (2.6, 9.4), (3.2, 8.3), (4.0, 7.45), (5.0, 6.5), (6.0, 5.5),
        (7.0, 4.5), (8.0, 3.5), (9.0, 2.55), (10.4, 1.75), (11.4, 1.0)]
OUTER = [(19.0, 1.0), (15.0, 1.0), (11.4, 1.0)] + LEFT[::-1][1:] + [(1.0, 15.0), (1.0, 19.0)]
INNER = [(19.0, 3.3), (15.0, 3.35), (12.9, 3.45), (12.05, 4.3), (11.6, 6.2), (10.4, 7.9), (9.0, 9.1),
         (8.45, 10.6), (8.4, 13.5), (8.4, 16.5), (8.2, 19.0)]


# ---------- 2D helpers ----------
def cr_smooth(P, per):
    out = []
    n = len(P)
    for i in range(n - 1):
        p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(n - 1, i + 2)]
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)))
    out.append(tuple(P[-1]))
    return out


def resample(P, n):
    L = [0.0]
    for i in range(1, len(P)):
        L.append(L[-1] + math.hypot(P[i][0] - P[i - 1][0], P[i][1] - P[i - 1][1]))
    out, j = [], 0
    for k in range(n):
        s = L[-1] * k / (n - 1)
        while j < len(P) - 2 and L[j + 1] < s:
            j += 1
        t = (s - L[j]) / ((L[j + 1] - L[j]) or 1)
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out


def area(P):
    return sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P))) / 2


def ccw(P):
    return list(P) if area(P) > 0 else list(P)[::-1]


def offset(P, d):
    """Inward miter offset of a CCW polygon by d (clamped at sharp corners)."""
    n = len(P)
    out = []
    for i, p in enumerate(P):
        a, b = P[(i - 1) % n], P[(i + 1) % n]
        e1 = (p[0] - a[0], p[1] - a[1])
        e2 = (b[0] - p[0], b[1] - p[1])
        l1 = math.hypot(*e1) or 1
        l2 = math.hypot(*e2) or 1
        n1 = (-e1[1] / l1, e1[0] / l1)
        n2 = (-e2[1] / l2, e2[0] / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        ml = math.hypot(*m) or 1
        m = (m[0] / ml, m[1] / ml)
        s = min(3.0, 1 / max(0.35, m[0] * n1[0] + m[1] * n1[1]))
        out.append((p[0] + m[0] * d * s, p[1] + m[1] * d * s))
    return out


def rectE(c0, r0, c1, r1):
    return [E(c0, r1), E(c1, r1), E(c1, r0), E(c0, r0)]


# ---------- mesh kit (px in, Blender units out) ----------
class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new((p[0] * PX, p[1] * PX, p[2] * PX))

    def face(self, vs, mat, smooth):
        f = self.bm.faces.new(vs)
        f.material_index = mat
        f.smooth = smooth
        return f

    def rings(self, R, mat, closed=True, cap0=True, cap1=True, smooth=False, loop=False):
        """Quads between consecutive rings of 3D points; loop joins the last ring back to the first."""
        V = [[self.v(p) for p in r] for r in R]
        n = len(V[0])
        m = n if closed else n - 1
        pairs = list(zip(V, V[1:])) + ([(V[-1], V[0])] if loop else [])
        for a, b in pairs:
            for k in range(m):
                self.face((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]), mat, smooth)
        if not loop:
            if cap0:
                self.face(list(reversed(V[0])), mat, False)
            if cap1:
                self.face(V[-1], mat, False)
        return V

    def prism(self, P, z0, z1, mat, ct=0.3, cb=0.0):
        P = ccw(P)
        R = []
        if cb > 0:
            R += [[(x, y, z0) for x, y in offset(P, cb)], [(x, y, z0 + cb) for x, y in P]]
        else:
            R.append([(x, y, z0) for x, y in P])
        if ct > 0:
            R += [[(x, y, z1 - ct) for x, y in P], [(x, y, z1) for x, y in offset(P, ct)]]
        else:
            R.append([(x, y, z1) for x, y in P])
        self.rings(R, mat)

    def boxE(self, c0, r0, c1, r1, z0, z1, mat, ct=0.25):
        self.prism(rectE(c0, r0, c1, r1), z0, z1, mat, ct)

    def cyl(self, base, axis, rad, h, mat, sides=8, ch=0.06, dome=0.0, smooth=False):
        """Cylinder from base along axis; chamfered at both ends, or a domed head."""
        ax = Vector(axis).normalized()
        base = Vector(base)
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        w = ax.cross(u)

        def ring(rr, t):
            return [base + ax * t + (u * math.cos(2 * math.pi * (k + 0.5) / sides) +
                                     w * math.sin(2 * math.pi * (k + 0.5) / sides)) * rr for k in range(sides)]
        if dome:
            R = [ring(rad, 0), ring(rad, h)]
            for k in (1, 2, 3):
                ph = k / 3 * math.pi / 2
                R.append(ring(rad * math.cos(ph) * 0.999 + 0.02, h + dome * math.sin(ph)))
        else:
            R = [ring(rad - ch, 0), ring(rad, ch), ring(rad, h - ch), ring(rad - ch, h)]
        self.rings(R, mat, smooth=smooth)

    def revolve(self, cx, cy, prof, mat, sides=32, smooth=True):
        """A closed (r, z) profile revolved about the vertical through (cx, cy)."""
        R = [[(cx + r * math.cos(2 * math.pi * k / sides), cy + r * math.sin(2 * math.pi * k / sides), z)
              for k in range(sides)] for r, z in prof]
        self.rings(R, mat, smooth=smooth, loop=True)


# ---------- materials ----------
def materials(sprite):
    pal = lambda i, tag=NAME, **kw: common.palette_material(sprite, i, tag, **kw)  # noqa: E731
    return [
        pal(52, metallic=0.45, roughness=0.5),                         # 0 base casting, socket floor
        pal(57, metallic=0.5, roughness=0.38),                         # 1 armour hood
        pal(58, metallic=0.55, roughness=0.34),                        # 2 rivets, sill, lock pins
        pal(56, metallic=0.5, roughness=0.42),                         # 3 mount casting, deck
        pal(51, metallic=0.45, roughness=0.5),                         # 4 core collar
        common.palette_material(sprite, 120, f"{NAME}-core", metallic=0.0, roughness=0.3,
                                emission_strength=1.6, frames={49: 115, 53: 123}),   # 5 core
        common.palette_material(sprite, 126, f"{NAME}-hot", metallic=0.0, roughness=0.25,
                                emission_strength=3.0, frames={49: 122, 53: 127}),   # 6 hot kernel
        pal(55, metallic=0.5, roughness=0.4),                          # 7 buttress
        pal(53, metallic=0.45, roughness=0.46),                        # 8 buttress step, actuator
        pal(54, metallic=0.55, roughness=0.4),                         # 9 bolts, strut, vanes, lugs
        pal(48, metallic=0.2, roughness=0.7),                          # 10 bore
        pal(49, metallic=0.3, roughness=0.65),                         # 11 exhaust throat
        pal(50, metallic=0.35, roughness=0.6),                         # 12 intake louvres and their dark bed
        common.palette_material(sprite, 123, f"{NAME}-mid", metallic=0.0, roughness=0.3,
                                emission_strength=2.2, frames={49: 118, 53: 125}),   # 13 core mid ring
    ]


HULL, HOOD, LIGHT, MOUNT, COLLAR, CORE, HOT, PILLAR, STEP, BOLT, BORE, VENT, LOUVRE, MID = range(14)


# ---------- parts ----------
def build_hull(M):
    curve = cr_smooth(LEFT, 4)[:-1]
    hullE = [(11.4, 1.0), (19.0, 1.0), (19.0, 4.0), (20.0, 4.0), (20.0, 5.0), (22.7, 5.0), (23.0, 5.3),
             (23.0, 23.8), (21.0, 24.0), (21.0, 25.0), (20.0, 25.2), (20.0, 28.0), (16.0, 28.0), (16.0, 27.0),
             (9.0, 27.0), (9.0, 28.0), (3.0, 28.0), (3.0, 26.0), (2.0, 25.9), (1.9, 25.0), (1.0, 24.8),
             (1.0, 12.9)] + curve
    M.prism([E(c, r) for c, r in hullE], 0.0, HULL_TOP, HULL, ct=HULL_CH, cb=HULL_BCH)


def hood_section(Os, Is, t, end=0.0, shrink=0.0, inset=0.0):
    """Closed section of the hood at station t (0 east end, 1 south end), in model px."""
    n = len(Os) - 1
    f = t * n
    i = min(int(f), n - 1)
    a = f - i
    O = (Os[i][0] + (Os[i + 1][0] - Os[i][0]) * a, Os[i][1] + (Os[i + 1][1] - Os[i][1]) * a)
    I = (Is[i][0] + (Is[i + 1][0] - Is[i][0]) * a, Is[i][1] + (Is[i + 1][1] - Is[i][1]) * a)
    H = T.pchip([0, 0.25, 0.47, 0.75, 1], SHELL_H)(t)
    uc, zi, zf = SHELL_UC, HULL_TOP + 0.35, HULL_TOP + 0.1
    u0 = -SHELL_OUT / (math.hypot(I[0] - O[0], I[1] - O[1]) or 1)   # the outer wall, just proud of the base

    def zOf(u):
        if u <= uc:
            return zf + (H - zf) * math.sin(u / uc * math.pi / 2) ** 0.85
        return H - (H - zi) * ((u - uc) / (1 - uc)) ** 1.9

    def pt(u, z):
        c, r = O[0] + (I[0] - O[0]) * u, O[1] + (I[1] - O[1]) * u
        x, y = E(c, r)
        return [x, y, z]
    us = [0, 0.04, 0.1, 0.18, 0.27, 0.36, 0.45, uc - 0.045, uc, uc + 0.045, 0.68, 0.76, 0.84, 0.91, 0.965, 1]
    S = [pt(u0, SHELL_FOOT)]
    for u in us:
        z = zOf(u)
        u = u0 if u == 0 else u
        if abs(abs(u - uc) - 0.045) < 1e-9:
            z -= 0.12
        S.append(pt(u, max(SHELL_FOOT, z - end)))
    S.append(pt(1.0, HULL_TOP - 0.05))
    S.append(pt(0.6, SHELL_FOOT))
    if shrink or inset:
        cx = sum(p[0] for p in S) / len(S)
        cy = sum(p[1] for p in S) / len(S)
        cz = sum(p[2] for p in S) / len(S)
        for p in S:
            p[0] += (cx - p[0]) * shrink
            p[1] += (cy - p[1]) * shrink
            if inset:   # a groove: pull the visible skin in by `inset` px toward the section centre
                d = Vector((cx - p[0], cy - p[1], cz - p[2]))
                if d.length > 1e-6 and p[2] > SHELL_FOOT + 0.05:
                    d = d.normalized() * inset
                    p[0] += d.x
                    p[1] += d.y
                    p[2] += d.z
    return S


def build_hood(M):
    Os = resample(cr_smooth(OUTER, 6), 401)
    Is = resample(cr_smooth(INNER, 6), 401)
    NS = 72
    joints = [9 / 43, 20 / 43, 33 / 43]
    ends = {0: (0.55, 0.06), 1: (0.18, 0.0), NS - 2: (0.18, 0.0), NS - 1: (0.55, 0.06)}
    st = []
    for k in range(NS):
        t = 0.012 * k if k <= 1 else 1 - 0.012 * (NS - 1 - k) if k >= NS - 2 else 0.012 + (k - 1) / (NS - 3) * 0.976
        if any(abs(t - j) < 0.009 for j in joints):
            continue
        end, sh = ends.get(k, (0.0, 0.0))
        st.append((t, end, sh, 0.0))
    for j in joints:
        st += [(j - 0.006, 0, 0, 0), (j - 0.0035, 0, 0, 0.26), (j + 0.0035, 0, 0, 0.26), (j + 0.006, 0, 0, 0)]
    st.sort()
    R = [hood_section(Os, Is, t, end, sh, ins) for t, end, sh, ins in st]
    M.rings(R, HOOD, smooth=True)
    return Os, Is


def build_rivets(M, hood_bvh):
    for c, r in [(10.5, 6.5), (8.6, 8.6), (7.55, 11.5), (7.55, 14.5), (7.55, 17.3)]:
        x, y = E(c, r)
        hit = hood_bvh.ray_cast(Vector((x * PX, y * PX, 20 * PX)), Vector((0, 0, -1)))
        z = hit[0].z / PX if hit[0] else 4.5
        M.cyl((x, y, z - 0.3), (0, 0, 1), 0.42, 0.38, LIGHT, sides=10, dome=0.22, smooth=True)


def build_core(M):
    cx, cy = E(CORE_C, CORE_R)
    # dark machined collar the core sits in
    ro, ri, z0, z1 = COLLAR_RO, COLLAR_RI, 1.6, COLLAR_Z1
    M.revolve(cx, cy, [(ro, z0), (ro, z1 - 0.2), (ro - 0.2, z1), (ri + 0.15, z1), (ri, z1 - 0.15), (ri, z0)],
              COLLAR, sides=32, smooth=False)
    # the core: a sphere whose pole points at the hot kernel; the hot window is its polar cap
    hx, hy = E(HOT_C, HOT_R)
    dx, dy = hx - cx, hy - cy
    dz = math.sqrt(max(0.0, CORE_RAD ** 2 - dx * dx - dy * dy))
    ax = Vector((dx, dy, dz)).normalized()
    ref = Vector((1, 0, 0))
    u = ax.cross(ref).normalized()
    w = ax.cross(u)
    centre = Vector((cx, cy, CORE_Z))
    cap = math.asin(min(1.0, HOT_RAD / CORE_RAD))
    sides = 32
    lats = [cap * k / 3 for k in range(1, 4)] + [cap + (math.pi - cap) * k / 12 for k in range(1, 12)]
    V = []
    for th in lats:
        ring = []
        for k in range(sides):
            ph = 2 * math.pi * k / sides
            p = centre + (ax * math.cos(th) + (u * math.cos(ph) + w * math.sin(ph)) * math.sin(th)) * CORE_RAD
            p.z = 1.8 + max(0.0, p.z - 1.8) * CORE_SQ   # a low dome seated in the collar; flat underneath
            ring.append(M.v(p))
        V.append(ring)
    t_ = centre + ax * CORE_RAD
    t_.z = 1.8 + (t_.z - 1.8) * CORE_SQ
    top = M.v(t_)
    b = centre - ax * CORE_RAD
    b.z = max(b.z, 1.8)
    bot = M.v(b)
    for k in range(sides):
        M.face((top, V[0][k], V[0][(k + 1) % sides]), HOT, True)
    for i in range(len(V) - 1):
        mat = HOT if i < 2 else MID if i < 4 else CORE
        for k in range(sides):
            M.face((V[i][k], V[i + 1][k], V[i + 1][(k + 1) % sides], V[i][(k + 1) % sides]), mat, True)
    for k in range(sides):
        M.face((V[-1][k], bot, V[-1][(k + 1) % sides]), CORE, True)


def build_blocks(M):
    # L-shaped mount casting: header under the hood band (rows 3-7) and the rib down the socket's east side
    L = [E(12.6, 3.3), E(19.0, 3.3), E(19.0, 16.0), E(15.8, 16.0), E(15.8, 6.9), E(12.6, 6.9)]
    M.prism(L, 0.5, LH, MOUNT, ct=0.45)
    # two cross grooves on the rib (rows 9.3 and 12.6): thin dark strips sunk flush into its top
    for r in (9.3, 12.6):
        M.boxE(16.2, r - 0.12, 18.75, r + 0.12, LH - 0.2, LH + 0.015, HULL, ct=0.0)
    # yoke arms clamping the core collar to the rib
    M.boxE(14.9, 10.1, 16.2, 11.5, 1.8, 3.35, HOOD, ct=0.25)
    M.boxE(14.9, 14.9, 16.2, 16.0, 1.8, 3.15, HOOD, ct=0.25)
    # light sill bar under the core
    M.boxE(9.0, 17.0, 15.3, 18.0, 1.6, 3.0, LIGHT, ct=0.35)
    # east buttress (two tiers) and its hex bolts on the mounting face
    P = PIL
    M.boxE(P["step"], P["r0"], P["x1"], P["r1"], 0.3, P["z"], PILLAR, ct=0.5)
    M.boxE(P["x0"], P["r0"] + 0.6, P["step"] + 0.1, P["r1"], 0.3, P["zs"], STEP, ct=0.25)
    for r in (6.0, 9.0, 12.0, 15.0):
        x, y = E(P["x1"], r)
        M.cyl((x - 0.05, y, 2.4), (1, 0, 0), 0.5, 0.4, BOLT, sides=6, ch=0.08)
    # low ledge south of rib and buttress, two locking pins and the bore
    M.boxE(15.6, 16.0, 23.0, 19.0, 0.3, 2.6, HULL, ct=0.25)
    for c in (18.5, 20.5):
        x, y = E(c, 17.9)
        M.cyl((x, y, 2.4), (0, 0, 1), 0.55, 0.9, LIGHT, sides=12, dome=0.35, smooth=True)
    x, y = E(19.5, 16.55)
    M.cyl((x, y, 2.5), (0, 0, 1), 0.5, 0.16, BORE, sides=12, ch=0.02)
    # rail, deck plate (two plates), west strut and intake louvres
    M.boxE(8.8, 20.0, 23.0, 21.0, 1.6, 3.05, HOOD, ct=0.4)
    M.boxE(6.9, 22.0, 14.4, 24.0, 1.6, 2.85, MOUNT, ct=0.3)
    M.boxE(14.6, 22.0, 23.0, 24.0, 1.6, 2.85, MOUNT, ct=0.3)
    M.boxE(5.0, 18.9, 6.05, 24.6, 1.6, 3.25, BOLT, ct=0.3)
    M.boxE(1.6, 20.1, 4.9, 25.0, 1.6, 2.15, LOUVRE, ct=0.1)   # dark vent bed: the gaps between slats read pal 50
    for r in (20.3, 21.6, 22.9, 24.2):
        M.boxE(1.6, r, 4.9, r + 0.7, 1.7, 2.35, LOUVRE, ct=0.15)
    # south exhaust: dark throat, three vanes, actuator box
    M.boxE(9.0, 25.7, 16.0, 27.1, 0.2, 1.7, VENT, ct=0.1)
    for c in (10, 12, 14):
        M.boxE(c + 0.05, 25.7, c + 0.95, 28.0, 0.35, 1.75, BOLT, ct=0.2)
    M.boxE(16.0, 25.3, 20.0, 28.0, 0.25, 2.55, STEP, ct=0.3)
    # seam band across the body on row 19 (the sprite's 53-54 row) and the dark groove floor at col 19
    M.boxE(5.9, 19.0, 15.6, 19.95, 1.6, 2.3, STEP, ct=0.15)
    M.boxE(19.0, 4.6, 20.0, 16.0, 1.6, 2.06, COLLAR, ct=0.0)
    # dark exhaust grille slot across the south skirt (row 26): a sunk dark strip with fine bars
    M.boxE(3.3, 26.05, 16.0, 26.95, 1.0, 2.02, VENT, ct=0.0)
    for c in range(4, 16):
        M.boxE(c + 0.32, 26.1, c + 0.68, 26.9, 1.0, 2.1, LOUVRE, ct=0.06)
    # lifting lugs on the north face
    for c in (13.5, 17.0):
        x, y = E(c, 1.0)
        M.prism([(x - 0.7, y - 0.1), (x + 0.7, y - 0.1), (x + 0.7, y + 0.3), (x - 0.7, y + 0.3)], 0.6, 2.2, BOLT, ct=0.15)


def build(coll, sprite):
    mats = materials(sprite)
    # hood first on its own, for the rivet height probe
    Mh = Mesh()
    build_hood(Mh)
    bvh = BVHTree.FromBMesh(Mh.bm)
    M = Mesh()
    build_hull(M)
    build_rivets(M, bvh)
    build_core(M)
    build_blocks(M)
    me_h = bpy.data.meshes.new("hood_tmp")
    Mh.bm.to_mesh(me_h)
    Mh.bm.free()
    M.bm.from_mesh(me_h)
    bpy.data.meshes.remove(me_h)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    for m in mats:
        me.materials.append(m)
    flat = [p.index for p in me.polygons if not p.use_smooth]
    me.shade_smooth()
    for i in flat:
        me.polygons[i].use_smooth = False
    me.set_sharp_from_angle(angle=math.radians(40))
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    return obj, mats


def bake_maps(obj, out_dir, size=1024, samples=64):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT = (1.0, 1.0, 1.0)
    T.TEXTURED = tuple(i for i in range(14) if i not in (CORE, HOT, MID))   # the glowing core stays unbaked
    try:
        T.bake_maps(obj, out_dir, size=size, samples=samples)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name in ("talon_colour", "talon_rm"):
            img.name = img.name.replace("talon", "pod49")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj, mats = build(coll, sprite)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"B {NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        bake_maps(obj, Path(tempfile.mkdtemp(prefix="newshc49_bake_")), size=512)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.01, faces=2500, smooth=6)
    shell.name = shell.data.name = f"{NAME}_outline"
    common.export_sprite_model(ROOT, [obj, shell], "enemies/newshc-49", sprite["sprites"], image_format=fmt)


if __name__ == "__main__":
    main()
