"""Jungle rocket launcher (newshj-17/-55/-127/-129) and the green hover tank (newshj-245/-283, mirrored as
newshj-169/-207), built as one structure: blueprint geometry first, engineering realism (D50-D53, D65).

Two objects in one script (they shared lib_b118):

1. THE JUNGLE ROCKET LAUNCHER (assembly-newshj-127: newshj-17 / -55 / -127 / -129, 72x56 px). A fixed
   ground emplacement standing on the HD ground (D130: no jungle plate). Cross-sections first:
   - launch tube: a round 5.3 px tube, its axis on the plan diagonal (t = c + r along, muzzle at small t,
     s = c - r across), elevated 13 deg toward the north-west. Section stations: muzzle lip + bore,
     a conical muzzle shroud (r 2.4 -> 5.3), front collar, barrel with a groove ring, a mid band
     carrying the two lamps, the rear barrel with two raised access panels and a crest seam, a rear
     collar, then a conical tail that steps down to the boom (r 2.9);
   - boom: the narrow breech section from the rear cone to the trunnion, with a clamp band and a
     ram lug on its north-east side; a trunnion pin crosses it between the two yoke cheeks;
   - pedestal: a chamfered octagonal base (3.2 px) with a turntable ring (bolt circle) and the two
     yoke cheeks carrying the trunnion;
   - breech block: the box south-east of the pedestal, its exhaust grille glowing red to white on top
     (newshj-129's frames 129 / 279 / 281 only recolour it: frame-animated palette materials, D17);
   - hydraulic ram (the strut): cylinder + gland + rod from the boom's lug down to a clevis on a
     foot plate;
   - frame states of newshj-55: f55 long flame (tip = newshj-17 f17), f89 rocket nose in the muzzle,
     f93 short flame (tip f91); the lamps take each frame's brightness.

2. THE GREEN HOVER TANK (assembly-newshj-245 = newshj-245 + -283, 48x28 px, nose LEFT) and its mirror
   assembly-newshj-207 (newshj-169 + -207, nose RIGHT: c' = 49 - c). A long hull of superellipse
   sections (n 2.6: hard-surface rounded box) lofted from plan stations, tapering to a blunt banded
   nose, a big glossy canopy on the north half, a rounded tail with a red tail light, a red thruster
   pod with a glowing nozzle at the tail's south corner, an outrigger leg with a red shoe. The sprite's
   surface detail is modelled: a framed louvre vent ahead of the canopy (three north-south slats), four
   strakes along the dark ribbed south flank (its rows 18-23), raised panel steps on the lighter 42/43
   blocks and dark seams. Hovers
   1.6 px over the ground; the shoe and leg feet reach the ground. Underside: closed, plain.

Coordinates while building: sprite px (c east, r south, h up). Blender: X = (c - W/2)/12,
Y = (H/2 - r)/12, Z = h/12.

Run: blender --background --python assets/blender/enemies/assembly-newshj-127.py
Measure (plain python with numpy; IoU per frame, region colours): python3 assembly-newshj-127.py
Exports every piece (the launcher's newshj-17, -17-f2, -55, -55-f2, -55-f3, -127, -129; the tank's
newshj-245, -283, -169, -207). It replaces assembly-newshj-245.py, -207.py and lib_b118 (removed).
"""

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE.parents[2]
REF = WT / "reference" / "models"
NAME = "assembly-newshj-127"
SCRATCH = Path("/Users/dlomibao/projects/tyrian-scratch/e2-enemies-1/assembly-newshj-127/final")
TAU = 2 * math.pi
Q = math.sqrt(0.5)


# ------------------------------------------------------------------------------------------------
# small vector maths
# ------------------------------------------------------------------------------------------------
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def lerp(a, b, t): return a + (b - a) * t


def norm(a):
    ln = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / ln, a[1] / ln, a[2] / ln)


def frame(d):
    """Two unit vectors across axis d: u horizontal, v up-ish."""
    d = norm(d)
    u = cross(d, (0, 0, 1))
    if math.sqrt(dot(u, u)) < 1e-6:
        u = (1, 0, 0)
    u = norm(u)
    v = norm(cross(u, d))
    return u, (mul(v, -1) if v[2] < 0 else v)


def interp(table, x):
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            return lerp(y0, y1, (x - x0) / (x1 - x0))


# ------------------------------------------------------------------------------------------------
# geometry container (pure Python so it can be measured without Blender)
# ------------------------------------------------------------------------------------------------
class Geo:
    def __init__(self):
        self.v, self.f = [], []   # f: (idx tuple, pal, part)

    def vid(self, p):
        self.v.append(tuple(float(x) for x in p))
        return len(self.v) - 1

    def face(self, idx, pal, part):
        self.f.append((tuple(idx), pal, part))

    def loft(self, rings, pal, part, cap0=True, cap1=True, closed=True):
        ids = [[self.vid(p) for p in r] for r in rings]
        n = len(rings[0])
        for k in range(len(ids) - 1):
            pa = pal[k] if isinstance(pal, (list, tuple)) else pal
            a, b = ids[k], ids[k + 1]
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                self.face((a[i], a[j], b[j], b[i]), pa, part)
        p0 = pal[0] if isinstance(pal, (list, tuple)) else pal
        p1 = pal[-1] if isinstance(pal, (list, tuple)) else pal
        if cap0:
            self._cap(ids[0], p0, part)
        if cap1:
            self._cap(ids[-1], p1, part)

    def _cap(self, ring, pal, part):
        c = tuple(sum(self.v[i][a] for i in ring) / len(ring) for a in range(3))
        ci = self.vid(c)
        n = len(ring)
        for i in range(n):
            self.face((ring[i], ring[(i + 1) % n], ci), pal, part)

    def merge(self, other):
        off = len(self.v)
        self.v += other.v
        self.f += [(tuple(i + off for i in idx), pa, pt) for idx, pa, pt in other.f]

    def mirrored(self, axis_c):
        g = Geo()
        g.v = [(axis_c - x, y, z) for x, y, z in self.v]
        g.f = [(tuple(reversed(idx)), pa, pt) for idx, pa, pt in self.f]
        return g

    def tris(self):
        return sum(len(i) - 2 for i, _, _ in self.f)


def sweep(g, pts, pal, part, n=16, caps=True, phase=0.5, fixed_dir=None):
    """Tube along a polyline of (point, r or (ru, rv)); `fixed_dir`: every ring square to that axis
    (an eccentric cone keeps parallel ring planes)."""
    rings = []
    for k, (p, r) in enumerate(pts):
        d = fixed_dir or sub(pts[min(k + 1, len(pts) - 1)][0], pts[max(k - 1, 0)][0])
        u, v = frame(d)
        ru, rv = r if isinstance(r, (tuple, list)) else (r, r)
        rings.append([add(p, add(mul(u, math.cos(TAU * (i + phase) / n) * ru), mul(v, math.sin(TAU * (i + phase) / n) * rv)))
                      for i in range(n)])
    g.loft(rings, pal, part, caps, caps)


def prism(g, poly, z0, z1, pal, part, ch=0.0, chb=0.0, top_pal=None):
    """Extruded plan polygon (star-shaped about its centroid), chamfered round the top (ch) and the
    bottom (chb)."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)

    def inset(p, d):
        dx, dy = cx - p[0], cy - p[1]
        ln = math.hypot(dx, dy) or 1.0
        return (p[0] + dx / ln * d, p[1] + dy / ln * d)

    rings, pals = [], []
    if chb > 0:
        rings.append([(*inset(p, chb), z0) for p in poly])
        rings.append([(p[0], p[1], z0 + chb) for p in poly])
        pals.append(pal)
    else:
        rings.append([(p[0], p[1], z0) for p in poly])
    rings.append([(p[0], p[1], z1 - ch) for p in poly])
    pals.append(pal)
    if ch > 0:
        rings.append([(*inset(p, ch), z1) for p in poly])
        pals.append(top_pal if top_pal is not None else pal)
    g.loft(rings, pals, part, True, False)
    g._cap([len(g.v) - len(poly) + i for i in range(len(poly))], top_pal if top_pal is not None else pal, part)


def ellipsoid(g, c, rx, ry, rz, pal, part, n=16, m=6, zcut=-1.0):
    lo = math.asin(max(-1.0, min(1.0, zcut)))
    rings = []
    for j in range(m + 1):
        phi = lerp(lo, math.pi / 2 - 0.03, j / m)
        rings.append([(c[0] + math.cos(TAU * (i + 0.5) / n) * math.cos(phi) * rx,
                       c[1] + math.sin(TAU * (i + 0.5) / n) * math.cos(phi) * ry,
                       c[2] + math.sin(phi) * rz) for i in range(n)])
    g.loft(rings, pal, part, True, True)


def box_along(g, centre, d, half_len, half_w, z0, z1, pal, part, ch=0.2):
    """A chamfered plan box centred at `centre` (c, r), long axis along plan direction d."""
    dl = math.hypot(*d)
    ux, uy = d[0] / dl, d[1] / dl
    vx, vy = -uy, ux
    poly = []
    for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        poly.append((centre[0] + ux * half_len * a + vx * half_w * b, centre[1] + uy * half_len * a + vy * half_w * b))
    prism(g, poly, z0, z1, pal, part, ch=ch)


# ================================================================================================
# 1. LAUNCHER (72 x 56)
# ================================================================================================
LW, LH = 72, 56
ELEV = math.radians(13.0)
Z_PIVOT, T_PIVOT = 4.6, 96.0
R_TUBE, S_BOOM, R_BOOM = 5.3, 12.7, 2.9
TUBE_PROFILE = [(42.6, 2.2), (44.6, 2.4), (46.0, 3.2), (47.0, 4.1), (48.0, 4.4), (50.0, 4.9), (51.0, 4.9), (53.0, 5.3),
                (71.8, 5.3), (73.0, 4.9), (74.0, 4.3), (75.0, 3.9), (76.0, 3.6), (77.0, 3.2), (78.0, 3.2), (79.0, 2.95),
                (80.0, 2.9)]
S_PROFILE = [(42, 11), (46, 11), (47, 10.6), (48, 10.5), (51, 10.5), (53, 11), (72, 11), (73, 12), (74, 12.4), (75, 13),
             (76, 13.6), (77, 14), (78, 13), (79, 12.8), (80, 12.7)]


def zAxis(t): return Z_PIVOT + (T_PIVOT - t) * Q * math.tan(ELEV)
def tsweep(g, pts, pal, part, **kw):
    """A sweep round the tube's axis: rings square to the tube, centres may step across (eccentric)."""
    sweep(g, pts, pal, part, fixed_dir=AXIS, **kw)


def tubeR(t): return interp(TUBE_PROFILE, t)
def sAt(t): return interp(S_PROFILE, t)
def TS(t, s, dz=0.0): return ((t + s) / 2, (t - s) / 2, zAxis(t) + dz)


AXIS = (0.5, 0.5, -Q * math.tan(ELEV))   # the tube's axis direction (t growing)
def ringPt(t, R, s=None): return (TS(t, sAt(t) if s is None else s), R)


def tubeTop(c, r):
    t, s = c + r, c - r
    d = abs(s - sAt(t)) * Q
    R = tubeR(t)
    return zAxis(t) + math.sqrt(max(0.0, R * R - d * d)) / math.cos(ELEV)


def tube_point(t, ang, rr, s=None):
    """A point on a ring round the tube's axis at t: ang 0 = the north-east side, pi/2 = top."""
    s = sAt(t) if s is None else s
    u, v = frame(sub(TS(t + 1, s), TS(t, s)))
    ax = TS(t, s)
    return add(ax, add(mul(u, -math.cos(ang) * rr), mul(v, math.sin(ang) * rr)))


# The parts' palette indices: the sprite's median per region (lighting excluded), from the blueprint.
LP = dict(LIP=4, BORE=2, SHROUD=5, COLLAR=6, BARREL=7, BAND=6, REARC=6, PANEL=5, SEAM=4, GROOVE=4, BOOM=7,
          LUG=7, BASE=4, TURN=6, CHEEK=3, PIN=9, BOLT=6, HOUSING=6, BAR=3, CYL=7, GLAND=5, ROD=9, FOOT=2,
          CLEVIS=5, NOSE=117)
VENT = dict(hot=127, mid=122, low=115)        # frame 281 (the layout frame); 129 and 279 recolour it
VENT_FRAMES = dict(hot={129: 116, 279: 122}, mid={129: 115, 279: 120}, low={129: 114, 279: 115})
LAMPS = {55: (127, 118), 89: (116, 116), 93: (120, 120)}   # (lamp a, lamp b): each frame's pixel medians
BIG_FLAME = [(45.5, 2.6, 11), (44, 2.8, 12), (42, 3.6, 12.3), (39, 3.7, 12), (37, 4.3, 11.6), (33.5, 4.3, 11.5),
             (32, 3.0, 11.6), (29, 2.8, 12), (26, 2.2, 11.5), (23, 2.2, 11.8), (21, 1.4, 12), (18.5, 1.3, 12),
             (16.6, 0.2, 12)]
SMALL_FLAME = [(45.5, 1.9, 12.3), (43, 2.1, 12), (42, 3.0, 11.6), (37.5, 3.0, 11.4), (35, 2.1, 11.3), (32, 1.4, 11.4),
               (30.2, 0.6, 11), (29.6, 0.1, 11)]
N_TUBE = 24


def band(g, t0, t1, R, e, pal, part, ch=0.2):
    """A raised ring band round the tube (chamfered edges): radius R + e between t0 and t1."""
    tsweep(g, [ringPt(t0, R - 0.05), ringPt(t0 + ch, R + e), ringPt(t1 - ch, R + e), ringPt(t1, R - 0.05)],
          pal, part, n=N_TUBE, caps=True)


def launcher_base():
    g = Geo()
    # ---- launch tube ------------------------------------------------------------------------------
    # muzzle lip (a turned ring with a rounded front) and the bore inside it
    tsweep(g, [ringPt(42.35, 1.75), ringPt(42.5, 2.2), ringPt(42.9, 2.45), ringPt(44.4, 2.45), ringPt(44.7, 2.35)],
          LP["LIP"], "tube_muzzle_lip", n=N_TUBE, caps=False)
    tsweep(g, [ringPt(45.0, 1.75), ringPt(42.36, 1.75)], LP["BORE"], "tube_bore", n=16, caps=True)
    # muzzle shroud cone, front collar
    tsweep(g, [ringPt(t, tubeR(t) + (0.05 if t < 45 else 0)) for t in (44.6, 46.0, 47.0, 48.0, 50.0, 51.0, 52.8)],
          LP["SHROUD"], "tube_muzzle_shroud", n=N_TUBE, caps=False)
    band(g, 52.8, 54.1, R_TUBE, 0.18, LP["COLLAR"], "tube_front_collar")
    # barrel shell (one closed tube from the front collar to the rear collar; bands sit on it)
    tsweep(g, [ringPt(t, R_TUBE) for t in (53.5, 57.0, 60.5, 66.0, 71.6)], LP["BARREL"], "tube_barrel", n=N_TUBE, caps=True)
    # panel-line grooves (dark rings, modelled as a thin ring just proud with a dark index)
    for t in (56.0, 66.4):
        tsweep(g, [ringPt(t - 0.18, R_TUBE + 0.04), ringPt(t + 0.18, R_TUBE + 0.04)], LP["GROOVE"], "tube_groove",
              n=N_TUBE, caps=True)
    band(g, 57.6, 60.2, R_TUBE, 0.22, LP["BAND"], "tube_mid_band")
    band(g, 71.2, 72.0, R_TUBE, 0.14, LP["BARREL"], "tube_rear_collar")
    # rear cone
    tsweep(g, [ringPt(t, tubeR(t)) for t in (71.8, 73.0, 74.0, 75.0, 76.0, 77.0, 78.0, 79.0, 80.2)],
          LP["REARC"], "tube_rear_cone", n=N_TUBE, caps=True)
    # raised access panels on the upper south-west face (a plate proud of the barrel, chamfered rim)
    for name, t0, t1 in (("tube_panel_front", 54.4, 57.2), ("tube_panel_rear", 60.8, 70.8)):
        a0, a1, N = 0.20 * math.pi, 0.62 * math.pi, 8
        rings = []
        for t, rr in ((t0, R_TUBE + 0.02), (t0 + 0.25, R_TUBE + 0.16), (t1 - 0.25, R_TUBE + 0.16), (t1, R_TUBE + 0.02)):
            rings.append([tube_point(t, lerp(a0, a1, k / N), rr) for k in range(N + 1)])
        # close the strip's long edges by giving it side walls at a0 / a1
        g.loft(rings, LP["PANEL"], name, cap0=False, cap1=False, closed=False)
        for a in (a0, a1):
            side = [tube_point(t, a, rr) for t, rr in ((t0, R_TUBE + 0.02), (t0 + 0.25, R_TUBE + 0.16),
                                                       (t1 - 0.25, R_TUBE + 0.16), (t1, R_TUBE + 0.02))]
            ids = [g.vid(p) for p in side]
            g.face(ids, LP["PANEL"], name)
        # four fastener heads at the panel's corners
        for t in (t0 + 0.6, t1 - 0.6):
            for a in (a0 + 0.08, a1 - 0.08):
                p = tube_point(t, a, R_TUBE + 0.18)
                ellipsoid(g, p, 0.28, 0.28, 0.12, LP["BOLT"], "tube_fastener", n=6, m=2, zcut=0)
    # seam along the barrel's crest (the sprite's dark line at s = 12)
    pts = []
    for t in (51.6, 61.0, 71.2):
        c, r, _ = TS(t, 12.2)
        pts.append(((c, r, tubeTop(c, r) - 0.08), 0.26))
    sweep(g, pts, 2, "tube_crest_seam", n=6, caps=True)
    # bolts round the mid band
    for k in range(10):
        a = TAU * k / 10
        p = tube_point(58.9, a, R_TUBE + 0.24)
        ellipsoid(g, p, 0.24, 0.24, 0.12, LP["BOLT"], "tube_band_bolt", n=6, m=2, zcut=0)

    # ---- boom (breech section) --------------------------------------------------------------------
    tsweep(g, [ringPt(79.5, R_BOOM, S_BOOM), ringPt(97.0, R_BOOM, S_BOOM)], LP["BOOM"], "boom", n=20, caps=True)
    # end cap chamfer at the breech end
    tsweep(g, [ringPt(96.9, R_BOOM, S_BOOM), ringPt(97.5, R_BOOM - 0.6, S_BOOM)], LP["BOOM"], "boom", n=20, caps=True)
    for t0 in (84.0,):
        tsweep(g, [ringPt(t0, R_BOOM, S_BOOM), ringPt(t0 + 0.2, R_BOOM + 0.25, S_BOOM), ringPt(t0 + 1.4, R_BOOM + 0.25, S_BOOM),
                  ringPt(t0 + 1.6, R_BOOM, S_BOOM)], LP["BOOM"], "boom_band", n=20, caps=True)
    # trunnion lug (ram attachment) on the north-east side
    lug = TS(91.5, 18.4, 0.2)
    prism(g, [(lug[0] - 1.1, lug[1] - 0.5), (lug[0] + 0.2, lug[1] - 1.0), (lug[0] + 0.9, lug[1] + 0.2),
              (lug[0] - 0.4, lug[1] + 0.8)], lug[2] - 1.8, lug[2] + 0.8, LP["LUG"], "boom_lug", ch=0.3)
    # trunnion pin across the boom, through the yoke cheeks (t 88.7)
    zt = zAxis(88.7)
    sweep(g, [(TS(88.7, S_BOOM - 4.6, 0), 0.75), (TS(88.7, S_BOOM + 4.6, 0), 0.75)], LP["PIN"], "pedestal_trunnion",
          n=12, caps=True)

    # ---- pedestal ----------------------------------------------------------------------------------
    PED = [(46.0, 38.6), (43.0, 40.0), (40.6, 41.2), (39.6, 42.2), (39.6, 46.2), (40.3, 46.6), (42.4, 48.0),
           (44.2, 49.8), (45.6, 52.0), (46.8, 52.0), (47.8, 51.4), (49.6, 50.4), (49.9, 49.0), (50.6, 48.6),
           (51.0, 40.6), (47.6, 38.6)]
    prism(g, PED, 0.0, 3.2, LP["BASE"], "pedestal_base", ch=0.5)
    YOKE = [(42.6, 40.6), (40.6, 42.6), (41.0, 46.0), (44.4, 49.6), (48.6, 48.6), (50.0, 44.0), (48.6, 40.6)]
    prism(g, YOKE, 3.2, 4.0, LP["TURN"], "pedestal_turntable", ch=0.3)
    # bolt circle on the turntable
    tc = (sum(p[0] for p in YOKE) / len(YOKE), sum(p[1] for p in YOKE) / len(YOKE))
    for k in range(8):
        a = TAU * (k + 0.5) / 8
        ellipsoid(g, (tc[0] + 3.4 * math.cos(a), tc[1] + 3.4 * math.sin(a), 4.0), 0.3, 0.3, 0.18, LP["BOLT"],
                  "pedestal_bolt", n=6, m=2, zcut=0)
    # yoke cheeks either side of the boom (they carry the trunnion)
    for ds in (-3.7, 3.7):
        c0, c1 = TS(87.0, S_BOOM + ds), TS(90.5, S_BOOM + ds)
        w = 0.65
        n = (Q, -Q)
        quad = [(c0[0] - n[0] * w, c0[1] - n[1] * w), (c1[0] - n[0] * w, c1[1] - n[1] * w),
                (c1[0] + n[0] * w, c1[1] + n[1] * w), (c0[0] + n[0] * w, c0[1] + n[1] * w)]
        prism(g, quad, 3.6, zt + 1.1, 2, "pedestal_yoke_cheek", ch=0.3)
        # pin boss on the cheek's outer face
        p = TS(88.7, S_BOOM + ds * 1.13, 0)
        ellipsoid(g, p, 0.75, 0.75, 0.75, LP["PIN"], "pedestal_pin_boss", n=10, m=3, zcut=-1)

    # ---- breech block with the glowing exhaust grille ---------------------------------------------
    BRE = [(50.6, 40.6), (56.2, 40.6), (56.2, 48.2), (55.0, 50.0), (51.0, 50.0), (50.6, 49.4)]
    prism(g, BRE, 0.0, 5.4, LP["HOUSING"], "breech_housing", ch=0.45)
    # side cooling ribs on the housing's east face
    for r0 in (42.2, 44.0, 45.8):
        prism(g, [(56.1, r0), (56.55, r0), (56.55, r0 + 0.7), (56.1, r0 + 0.7)], 0.8, 4.4, LP["CHEEK"], "breech_rib", ch=0.1)

    def slot(r0, r1):
        return [(52.9, r0), (55.0, r0), (55.0, r1), (52.9, r1)]
    prism(g, slot(41.6, 45.6), 5.0, 5.55, VENT["hot"], "breech_vent_hot")
    prism(g, slot(45.6, 47.8), 5.0, 5.55, VENT["mid"], "breech_vent_mid")
    prism(g, slot(47.8, 49.8), 5.0, 5.55, VENT["low"], "breech_vent_low")
    for r0 in (45.6, 47.8):
        prism(g, [(52.8, r0 - 0.12), (55.1, r0 - 0.12), (55.1, r0 + 0.12), (52.8, r0 + 0.12)], 5.0, 5.7, LP["BAR"], "breech_grille_bar")

    # ---- hydraulic ram ------------------------------------------------------------------------------
    foot = (59.6, 41.6, 1.6)
    top = (lug[0] + 0.1, lug[1] + 0.1, lug[2] - 0.3)
    mid = add(top, mul(sub(foot, top), 0.48))
    sweep(g, [(top, 1.0), (mid, 1.0)], LP["CYL"], "ram_cylinder", n=12, caps=True)
    gl0, gl1 = add(top, mul(sub(foot, top), 0.44)), add(top, mul(sub(foot, top), 0.52))
    sweep(g, [(gl0, 1.2), (gl1, 1.2)], LP["GLAND"], "ram_gland", n=12, caps=True)
    sweep(g, [(mid, 0.65), (foot, 0.65)], LP["ROD"], "ram_rod", n=10, caps=True)
    prism(g, [(56.6, 40.6), (60.0, 40.2), (61.0, 41.2), (61.0, 44.0), (60.0, 45.2), (59.0, 46.0), (58.0, 47.0),
              (56.4, 45.2)], 0.0, 0.9, LP["FOOT"], "ram_foot_plate", ch=0.3)
    for c0 in (57.0, 59.4):
        prism(g, [(c0, 41.2), (c0 + 1.5, 41.2), (c0 + 1.5, 45.2), (c0, 45.2)], 0.9, 2.6, LP["CLEVIS"], "ram_clevis_cheek", ch=0.25)
    return g


def launcher_lamps(frame_no):
    g = Geo()
    a, b = LAMPS[frame_no]
    c, r = 35.0, 25.4
    ellipsoid(g, (c, r, tubeTop(c, r) - 0.35), 0.95, 1.15, 0.8, a, "lamp_a", n=10, m=4, zcut=0)
    c, r = 40.4, 23.4
    ellipsoid(g, (c, r, tubeTop(c, r) - 0.4), 1.5, 0.75, 0.7, b, "lamp_b", n=10, m=4, zcut=0)
    return g


def launcher_nose():
    g = Geo()
    tsweep(g, [ringPt(44.0, 1.7), ringPt(42.2, 1.75), ringPt(41.6, 1.4), ringPt(41.1, 0.9), ringPt(40.75, 0.15)],
          LP["NOSE"], "rocket_nose", n=14, caps=True)
    return g


def launcher_flame(F):
    g = Geo()
    for k, pal, region in ((1.0, 116, "flame_outer"), (0.66, 118, "flame_orange"), (0.42, 121, "flame_yellow"),
                           (0.22, 123, "flame_white")):
        pts = [(TS(t, s, 0.55 * r * (1 - k) + 0.12 * (1 - k)), (max(0.05, r * k), max(0.03, 0.4 * r * k))) for t, r, s in F]
        sweep(g, pts, pal, region, n=12, caps=True)
    return g


# ================================================================================================
# 2. HOVER TANK (48 x 28), nose LEFT
# ================================================================================================
TW, TH = 48, 28
HULL = [(3.0, 11.0, 19.0), (3.6, 10.7, 19.3), (5.0, 10.3, 19.7), (8.5, 9.7, 20.7), (12.5, 8.8, 21.7), (17.5, 7.8, 22.7),
        (22.5, 6.8, 23.6), (28.5, 5.6, 24.0), (35.8, 5.1, 24.0), (37.4, 5.1, 23.0), (39.0, 5.1, 22.0), (40.5, 5.2, 19.2),
        (41.6, 5.5, 16.9), (42.6, 5.9, 16.4), (43.5, 7.0, 16.2), (44.3, 8.6, 15.9), (45.2, 9.8, 15.2), (45.8, 11.4, 13.8),
        (46.0, 12.4, 13.0)]
# The hull's south edge steps in behind col 36: the red thruster pod (cols 40.5-44.5, rows 15.5-23.5) and its
# low fairing (cols 37-41.6, rows 21.6-24) hang outside the green there, as the sprite draws them.
CLEAR = 1.6
N_SEC, SE = 28, 2.6


def hullAt(c):
    k = 0
    while k + 2 < len(HULL) and c > HULL[k + 1][0]:
        k += 1
    (c0, t0, b0), (c1, t1, b1) = HULL[k], HULL[k + 1]
    f = max(0.0, min(1.0, (c - c0) / (c1 - c0)))
    T, B = lerp(t0, t1, f), lerp(b0, b1, f)
    y, w = (T + B) / 2, (B - T) / 2
    hw = min(w, 9.5)
    ht = 0.55 * hw + 0.6
    hb = 0.42 * hw
    if c > 41:
        ht *= max(0.35, 1 - ((c - 41) / 5.4) ** 2 * 0.65)
    return dict(T=T, B=B, y=y, w=w, ht=ht, hb=hb, zc=CLEAR + 0.42 * 9.5)


def section(c, scale=1.0, dz=0.0):
    h = hullAt(c)
    R = []
    for i in range(N_SEC):
        a = TAU * (i + 0.5) / N_SEC
        ca, sa = math.cos(a), math.sin(a)
        ux = math.copysign(abs(ca) ** (2 / SE), ca)
        uz = math.copysign(abs(sa) ** (2 / SE), sa)
        R.append((c, h["y"] - ux * h["w"] * scale, h["zc"] + dz + uz * (h["ht"] if uz >= 0 else h["hb"]) * scale))
    return R


def hullTop(c, r):
    h = hullAt(c)
    u = min(1.0, abs(r - h["y"]) / h["w"])
    return h["zc"] + h["ht"] * (1 - u ** SE) ** (1 / SE)


def bar(g, path, hw, lo, hi, pal, part, ch=0.1, taper=False):
    """A conformal bar on the hull top: plan path [(c, r)], a chamfered rectangular section hw wide
    (half), from lo to hi above the hull surface. `taper`: the ends pinch down to the surface."""
    fine = [path[0]]
    for p, q in zip(path, path[1:]):
        m = max(1, int(math.ceil(math.hypot(q[0] - p[0], q[1] - p[1]) / 0.7)))
        fine += [(lerp(p[0], q[0], i / m), lerp(p[1], q[1], i / m)) for i in range(1, m + 1)]
    path = fine
    rings = []
    for k, (c, r) in enumerate(path):
        a, b = path[max(k - 1, 0)], path[min(k + 1, len(path) - 1)]
        dl = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        px, py = -(b[1] - a[1]) / dl, (b[0] - a[0]) / dl
        top = hi if not (taper and k in (0, len(path) - 1)) else lo + 0.05
        ring = []
        for s, dz in ((-hw, lo), (-hw, top - ch), (-hw + ch, top), (hw - ch, top), (hw, top - ch), (hw, lo)):
            cc, rr = c + px * s, r + py * s
            ring.append((cc, rr, hullTop(cc, rr) + dz))
        rings.append(ring)
    g.loft(rings, pal, part, True, True)


def plate(g, c0, c1, r0, r1, lift, pal, part, ch=0.15, n=6):
    """A chamfered panel plate following the hull top, standing `lift` proud of it (a panel step)."""
    rs = [r0, r0 + ch] + [lerp(r0 + ch, r1 - ch, i / (n - 1)) for i in range(1, n - 1)] + [r1 - ch, r1]
    cs = [c0, c0 + ch] + [lerp(c0 + ch, c1 - ch, i / 3) for i in range(1, 3)] + [c1 - ch, c1]
    rings = []
    for k, c in enumerate(cs):
        end = k in (0, len(cs) - 1)
        ring = []
        for i, r in enumerate(rs):
            edge = i in (0, len(rs) - 1)
            rr = min(max(r, r0 + ch), r1 - ch) if end else r
            ring.append((c, rr, hullTop(c, rr) + lift - (ch if (edge or end) else 0.0)))
        ring.append((c, r1 - ch, hullTop(c, r1 - ch) - 0.5))
        ring.append((c, r0 + ch, hullTop(c, r0 + ch) - 0.5))
        rings.append(ring)
    g.loft(rings, pal, part, True, True)


def flank_point(c, a, out=0.0, along=0.0):
    """Point on the hull section at station c, superellipse angle a (pi/2 = top, pi = south equator),
    pushed `out` along the surface normal and `along` the section tangent (towards the top)."""
    h = hullAt(c)
    ca, sa = math.cos(a), math.sin(a)
    ux = abs(ca) ** (2 / SE)
    uz = abs(sa) ** (2 / SE)
    y, z = h["y"] + ux * h["w"], h["zc"] + uz * h["ht"]
    ny, nz = max(ux, 1e-3) ** (SE - 1) / h["w"], max(uz, 1e-3) ** (SE - 1) / h["ht"]
    ln = math.hypot(ny, nz)
    ny, nz = ny / ln, nz / ln
    ty, tz = -nz, ny                     # tangent, pointing up the flank (towards the hull top)
    return (c, y + ny * out + ty * along, z + nz * out + tz * along)


# South-flank strakes: the sprite's rows 18-23 alternate a light rib and a dark groove (38 / 33 / 36 / 33 /
# 35 / 33) along the whole dark lower hull. Superellipse angles chosen to land on rows 18.5, 20.5, 22.5 at
# mid hull (plan offset u 0.41, 0.66, 0.91); the fourth strake sits low on the steep side (side view only).
STRAKES = [(math.pi - math.radians(71.7), 38, 0.42, 0.24), (math.pi - math.radians(54.3), 36, 0.45, 0.24),
           (math.pi - math.radians(30.0), 35, 0.5, 0.2), (math.pi - math.radians(13.0), 35, 0.5, 0.1)]
FLANK_U = 0.36                         # south of this plan offset the hull is the dark lower hull (33)


def strakes(g):
    cs = [6.0 + i for i in range(32)] + [37.6]
    for a, pal, hw, top in STRAKES:
        rings = []
        for k, c in enumerate(cs):
            hh = top if 0 < k < len(cs) - 1 else 0.03
            chf = min(0.1, hh)
            ring = [flank_point(c, a, -0.15, -hw), flank_point(c, a, hh - chf, -hw), flank_point(c, a, hh, -hw + chf),
                    flank_point(c, a, hh, hw - chf), flank_point(c, a, hh - chf, hw), flank_point(c, a, -0.15, hw)]
            rings.append(ring)
        g.loft(rings, pal, "hull_strake", True, True)


def tank():
    g = Geo()
    STA = [3.0, 3.6, 5.0, 6.5, 8.5, 10.5, 12.5, 15, 17.5, 20, 22.5, 25.5, 28.5, 32, 35.8, 37.4, 39.0, 40.5, 41.6, 42.6, 43.4, 44.0,
           44.6, 45.0, 45.4, 45.7, 46.0]
    rings = [section(c) for c in STA]

    def region(c, p):
        h = hullAt(c)
        off = (p[1] - h["y"]) / h["w"]
        if p[2] < h["zc"] - 0.2 * h["hb"]:
            return ("hull_belly", 33)          # underside: plain dark
        if off > 0.48 and p[2] < h["zc"] + 0.35 * h["ht"]:
            return ("hull_south_flank", 33)
        if off > FLANK_U and 5.0 < c < 37.8:
            return ("hull_south_flank", 33)    # the ribbed lower hull: grooves between the strakes
        if off > 0.15 and p[2] < h["zc"] + 0.75 * h["ht"] and c < 39:
            return ("hull_south_shoulder", 35)
        if c >= 39:
            return ("hull_tail", 40)
        if c < 15.5:
            return ("hull_nose", 40)
        return ("hull_body", 40)

    # one loft, faces coloured by region
    ids = [[g.vid(p) for p in r] for r in rings]
    for k in range(len(ids) - 1):
        for i in range(N_SEC):
            j = (i + 1) % N_SEC
            quad = (ids[k][i], ids[k][j], ids[k + 1][j], ids[k + 1][i])
            m = tuple(sum(g.v[q][a] for q in quad) / 4 for a in range(3))
            part, pal = region(m[0], m)
            g.face(quad, pal, part)
    g._cap(ids[0], 40, "hull_nose")
    g._cap(ids[-1], 40, "hull_tail")

    # raised bands round the nose and the tail seam (chamfered: three-ring lofts)
    for c0, c1, pal, name in ((3.0, 4.6, 42, "band_nose"), (10.8, 12.6, 42, "band_1"), (13.6, 14.6, 42, "band_2"),
                              (38.4, 39.4, 41, "band_tail_seam")):
        cm = (c0 + c1) / 2
        g.loft([section(c0, 1.0), section(c0 + 0.2, 1.05), section(c1 - 0.2, 1.05), section(c1, 1.0)], pal, name)
        _ = cm
    # panel steps where the sprite shows lighter 42/43 blocks: the nose's lower panel (rows 14-15, cols 5-10),
    # its upper strip (row 12, cols 6-9) and the small panel aft of the vent (rows 16-17, cols 26-27)
    plate(g, 5.0, 10.6, 13.7, 16.0, 0.22, 42, "detail_panel")
    plate(g, 5.8, 10.0, 11.8, 12.9, 0.18, 42, "detail_panel")
    plate(g, 25.9, 28.1, 15.7, 17.9, 0.2, 42, "detail_panel")
    # dark seams: the recess south of the vent (rows 13-14, cols 24-28) and a seam aft of the nose panel
    bar(g, [(24.0, 13.6), (26.0, 13.7), (28.4, 14.2)], 0.45, -0.3, 0.06, 36, "detail_seam", ch=0.05)
    bar(g, [(5.2, 13.25), (10.4, 13.25)], 0.22, -0.3, 0.05, 38, "detail_seam", ch=0.04)
    # upright seam at col 15.5
    pts = []
    for r in (8.8, 11.0, 13.5, 16.0, 18.0):
        pts.append(((15.5, r, hullTop(15.5, r) + 0.02), (0.15, 0.3)))
    sweep(g, pts, 40, "detail_panel_line", n=6)
    # hatch: a raised chamfered plate with a dark seam round it
    z = hullTop(19, 15)
    prism(g, [(17.4, 12.6), (20.8, 12.6), (20.8, 17.6), (17.4, 17.6)], z - 1.4, z + 0.02, 41, "detail_hatch_seam", ch=0.0)
    prism(g, [(17.6, 12.8), (20.6, 12.8), (20.6, 17.4), (17.6, 17.4)], z - 1.2, z + 0.4, 43, "detail_hatch", ch=0.25)
    # louvre vent ahead of the canopy (sprite cols 20-26, rows 8-12: pale 44-47 slats on cols 21/23/25 between
    # darker 40-42 gaps): a framed recess, a dark floor and three slats running north-south
    plate(g, 20.5, 26.5, 8.7, 12.7, 0.03, 40, "detail_louvre_gap", ch=0.03)
    for path in ([(20.35, 8.55), (26.65, 8.55)], [(20.35, 12.85), (26.65, 12.85)]):
        bar(g, path, 0.2, -0.3, 0.32, 41, "detail_louvre_frame", ch=0.08)
    for path in ([(20.35, 8.55), (20.35, 12.85)], [(26.65, 8.55), (26.65, 12.85)]):
        bar(g, path, 0.2, -0.3, 0.32, 41, "detail_louvre_frame", ch=0.08)
    for c in (21.5, 23.5, 25.5):
        bar(g, [(c, 8.8), (c, 9.9), (c, 11.0), (c, 12.6)], 0.42, -0.3, 0.3, 46, "detail_louvre_slat", ch=0.12)
    strakes(g)
    # canopy: glossy bubble with a framed rim
    c, r = 33.0, 10.2
    z = hullTop(c, r) - 2.2
    ellipsoid(g, (c, r, z), 5.4, 4.8, 4.4, 45, "canopy_glass", n=28, m=9, zcut=0.05)
    sweep(g, [((c + math.cos(TAU * i / 24) * 5.45, r + math.sin(TAU * i / 24) * 4.85, z + 0.35), 0.35) for i in range(25)],
          42, "canopy_frame", n=6, caps=False)
    # tail light
    c, r = 42.3, 6.9
    ellipsoid(g, (c, r, hullTop(c, r) - 0.6), 1.4, 0.95, 0.9, 119, "light_tail", n=10, m=4, zcut=0)
    # thruster pod at the tail's south corner, its glowing nozzle on top
    # a lift-thruster nacelle slung across the tail's south flank (axis north-south), its nozzle on top
    pod = [((42.3, 14.6, 4.6), (1.1, 1.2)), ((42.3, 15.4, 4.6), (1.8, 1.9)), ((42.3, 16.4, 4.6), (1.95, 2.05)),
           ((42.3, 21.4, 4.1), (1.85, 1.95)), ((42.2, 22.5, 3.8), (1.5, 1.6)), ((42.1, 23.0, 3.7), (0.6, 0.8))]
    sweep(g, pod, 114, "thruster_pod", n=16, caps=True)
    for r0 in (17.2, 21.0):
        sweep(g, [((42.3, r0, 4.6 - (r0 - 16.4) * 0.1), (2.0, 2.15)), ((42.3, r0 + 0.45, 4.6 - (r0 - 16.0) * 0.1), (2.0, 2.15))],
              114, "thruster_ring", n=16)
    ellipsoid(g, (42.3, 19.3, 6.1), 1.15, 1.8, 0.55, 114, "thruster_nozzle_ring", n=12, m=3, zcut=0)
    ellipsoid(g, (42.3, 19.3, 6.4), 0.6, 0.9, 0.45, 124, "thruster_nozzle_core", n=10, m=3, zcut=0)
    # low fairing running back from the nacelle along the hull's bottom edge
    sweep(g, [((41.4, 22.8, 2.6), (1.0, 0.9)), ((39.4, 22.9, 2.4), (1.15, 0.9)), ((37.4, 23.0, 2.3), (1.0, 0.85)),
              ((36.2, 23.2, 2.3), (0.3, 0.3))], 113, "thruster_fairing", n=10)
    # outrigger leg (south) and its red shoe; a hidden north leg for a plausible stance
    sweep(g, [((32.6, 17.0, 3.6), 1.05), ((32.6, 21.5, 2.5), 1.0), ((32.6, 24.6, 1.5), 0.95)], 38, "leg_strut", n=8)
    prism(g, [(31.0, 23.6), (34.8, 23.6), (34.2, 25.2), (33.9, 27.0), (31.0, 27.0)], 0.0, 1.3, 36, "leg_foot", ch=0.35)
    prism(g, [(26.2, 24.0), (31.2, 24.0), (31.0, 26.0), (27.4, 26.0), (26.4, 25.0)], 0.0, 1.1, 113, "leg_shoe", ch=0.35)
    sweep(g, [((32.9, 10.5, 3.2), 0.9), ((32.9, 10.5, 0.5), 0.9)], 38, "leg_north", n=8)
    prism(g, [(30.8, 9.2), (34.6, 9.2), (34.6, 11.8), (30.8, 11.8)], 0.0, 0.6, 36, "leg_north_foot", ch=0.2)
    return g


# ================================================================================================
# measuring
# ================================================================================================
GREEN = {32, 33, 34, 35} | set(range(192, 208))


def load_frame(name, idx):
    d = json.loads((REF / name / "sprite.json").read_text())
    fr = next(f for f in d["frames"] if f["index"] == idx)
    rows = [[int(v) for v in (row.split() if isinstance(row, str) else row)] for row in fr["pixels"]]
    return rows, {int(k): tuple(v) for k, v in d["colors"].items()}


def compose(pieces, W, H, ox, oy):
    """pieces: (name, frame, cx, cy) -> idx grid W x H, origin screen (ox, oy)."""
    grid = [[-1] * W for _ in range(H)]
    colors = {}
    for name, fi, cx, cy in pieces:
        rows, col = load_frame(name, fi)
        colors.update(col)
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[cy - 14 - oy + r][cx - 12 - ox + c] = v
    return grid, colors


def dejungle(grid, rmin=0):
    return [[(-1 if (v in GREEN and r >= rmin) else v) for v in row] for r, row in enumerate(grid)]


def rasterise(g, W, H, k=8):
    import numpy as np
    cov = np.zeros((H * k, W * k), bool)
    depth = np.full((H * k, W * k), -1e9)
    pal = np.full((H * k, W * k), -1, int)
    prt = np.full((H * k, W * k), -1, int)
    names = sorted({f[2] for f in g.f})
    pid = {n: i for i, n in enumerate(names)}
    V = np.array(g.v)
    for idx, pa, part in g.f:
        for t in range(1, len(idx) - 1):
            tri = V[[idx[0], idx[t], idx[t + 1]]]
            xs, ys = tri[:, 0] * k, tri[:, 1] * k
            x0, x1 = max(0, int(math.floor(xs.min()))), min(W * k - 1, int(math.ceil(xs.max())))
            y0, y1 = max(0, int(math.floor(ys.min()))), min(H * k - 1, int(math.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay), (bx, by), (cx, cy) = zip(xs, ys)
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-12:
                continue
            l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
            l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
            l3 = 1 - l1 - l2
            m = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
            if not m.any():
                continue
            d = l1 * tri[0, 2] + l2 * tri[1, 2] + l3 * tri[2, 2]
            cov[y0:y1 + 1, x0:x1 + 1] |= m
            sd = depth[y0:y1 + 1, x0:x1 + 1]
            win = m & (d > sd)
            sd[win] = d[win]
            pal[y0:y1 + 1, x0:x1 + 1][win] = pa
            prt[y0:y1 + 1, x0:x1 + 1][win] = pid[part]
    return cov, pal, prt, names


LAUNCH_PIECES = {"newshj-17": (0, 0), "newshj-55": (24, 0), "newshj-127": (24, 28), "newshj-129": (48, 28)}
TANK245_PIECES = {"newshj-245": (0, 0), "newshj-283": (24, 0)}
TANK207_PIECES = {"newshj-169": (0, 0), "newshj-207": (24, 0)}


def launcher_state(key):
    """(geo, composite pieces, piece frames) for a launcher frame state."""
    g = launcher_base()
    f17, f55, f129 = {"L55": (17, 55, 281), "L89": (None, 89, 281), "L93": (91, 93, 281),
                      "V129": (17, 55, 129), "V279": (17, 55, 279)}[key]
    g.merge(launcher_lamps(f55))
    if f55 == 55:
        g.merge(launcher_flame(BIG_FLAME))
    elif f55 == 93:
        g.merge(launcher_flame(SMALL_FLAME))
    else:
        g.merge(launcher_nose())
    pieces = [("newshj-55", f55, 224, 93), ("newshj-127", 127, 224, 121), ("newshj-129", f129, 248, 121)]
    if f17:
        pieces.append(("newshj-17", f17, 200, 93))
    frames = {"newshj-55": f55, "newshj-127": 127, "newshj-129": f129}
    if f17:
        frames["newshj-17"] = f17
    return g, pieces, frames


def measure_one(g, W, H, grid, colors, piece_map, piece_frames, jungle):
    import numpy as np
    sys.path.insert(0, str(WT / "tools"))
    import sprite_mask as SM
    k = 8
    cov, pal, prt, names = rasterise(g, W, H, k)
    sgrid = dejungle(grid, 28) if jungle else grid
    m = SM.masks(sgrid, colors)
    res = {"composite": SM.measure(m, cov.tolist())}
    res["pieces"] = {}
    for name, (c0, r0) in piece_map.items():
        if name not in piece_frames:
            continue
        rows, col = load_frame(name, piece_frames[name])
        if jungle:
            rows = dejungle(rows)
        pm = SM.masks(rows, col)
        top = cov[r0 * k:(r0 + 28) * k, c0 * k:(c0 + 24) * k]
        res["pieces"][f"{name}|{piece_frames[name]}"] = SM.measure(pm, top.tolist())
    # region colours: front-most model palette per sprite pixel centre vs the sprite index
    inner = np.array(m["inner"])
    covg = cov.reshape(H, k, W, k).mean(axis=(1, 3)) >= 0.5
    idx = np.array(sgrid)
    cen_pal = pal[k // 2::k, k // 2::k]
    cen_prt = prt[k // 2::k, k // 2::k]
    table = []
    for i, n in enumerate(names):
        sel = (cen_prt == i) & inner & covg & (idx >= 0)
        if sel.sum() < 2:
            continue
        sp = np.sort(idx[sel])
        lo, hi = int(len(sp) * 0.15), int(len(sp) * 0.85)
        core = sp[lo:max(hi, lo + 1)]
        mp = int(np.bincount(cen_pal[sel]).argmax())
        table.append((n, int(sel.sum()), int(np.median(core)), mp))
    res["regions"] = sorted(table, key=lambda r: -r[1])
    # overlay image data
    res["cov"], res["pal"], res["inner"], res["free"] = cov, pal, inner, np.array(m["free"])
    res["sgrid"] = sgrid
    return res


def overlay_png(res, colors, W, H, out, k=8):
    import numpy as np
    from PIL import Image
    covg = res["cov"].reshape(H, k, W, k).mean(axis=(1, 3)) >= 0.5
    inner, free = res["inner"], res["free"]
    img = np.zeros((H, W, 3), np.uint8) + 18
    img[inner & covg] = (60, 170, 110)
    img[inner & ~covg] = (235, 60, 60)
    img[~inner & covg & ~free] = (90, 120, 255)
    img[free & covg] = (60, 110, 90)
    img[free & ~covg] = (90, 50, 50)
    Image.fromarray(img).resize((W * 10, H * 10), Image.NEAREST).save(out)
    pal = res["pal"]
    im2 = np.zeros(pal.shape + (3,), np.uint8) + 18
    for pi in np.unique(pal):
        if pi >= 0:
            im2[pal == pi] = colors.get(int(pi), (255, 0, 255))
    Image.fromarray(im2).save(str(out).replace(".png", "_pal.png"))


def measure_all(write=True):
    out = {}
    lines = []
    worst = 1.0
    for key in ("L55", "L89", "L93", "V129", "V279"):
        g, pieces, frames = launcher_state(key)
        grid, colors = compose(pieces, LW, LH, 188, 79)
        if key == "L89":
            pass  # no newshj-17 piece shown on frame 89
        r = measure_one(g, LW, LH, grid, colors, LAUNCH_PIECES, frames, True)
        out[key] = r
        if write:
            overlay_png(r, colors, LW, LH, SCRATCH / f"iou_{key}.png")
    tg = tank()
    for key, gg, pieces, pmap in (
            ("T245", tg, [("newshj-245", 245, 210, 96), ("newshj-283", 283, 234, 96)], TANK245_PIECES),
            ("T207", tg.mirrored(49.0), [("newshj-169", 169, 130, 77), ("newshj-207", 207, 154, 77)], TANK207_PIECES)):
        ox = min(cx for _, _, cx, _ in pieces) - 12
        oy = min(cy for _, _, _, cy in pieces) - 14
        grid, colors = compose(pieces, TW, TH, ox, oy)
        frames = {n: f for n, f, _, _ in pieces}
        r = measure_one(gg, TW, TH, grid, colors, pmap, frames, False)
        out[key] = r
        if write:
            overlay_png(r, colors, TW, TH, SCRATCH / f"iou_{key}.png")
    for key, r in out.items():
        c = r["composite"]
        worst = min(worst, c["iou_rule_grid"])
        lines.append(f"{key}: composite rule IoU {c['iou_rule_grid']:.4f} (fine {c['iou_rule']:.4f}) outer {c['iou_outer_grid']:.4f} edge {c['edge_vs_inner_px']:+.2f}px")
        for pn, pm in r["pieces"].items():
            lines.append(f"    piece {pn:15s} rule {pm['iou_rule_grid']:.4f}  inner_px {pm['inner_px']}")
    lines.append(f"WORST composite rule IoU: {worst:.4f}")
    for key in ("L89", "L55", "T245"):
        lines.append(f"regions {key} (part, px, sprite median, model pal):")
        for n, px, sm, mp in out[key]["regions"]:
            flag = "" if sm == mp or (sm >> 4 == mp >> 4 and abs(sm - mp) <= 1) else "  <-- differs"
            lines.append(f"    {n:26s} {px:4d}  sprite {sm:3d}  model {mp:3d}{flag}")
    zl = max(v[2] for v in launcher_state("L55")[0].v)
    zt = max(v[2] for v in tank().v)
    lines.append(f"heights: launcher max {zl:.2f}px ({zl / 12:.3f} u), tank max {zt:.2f}px ({zt / 12:.3f} u)")
    lines.append(f"tris: launcher base {launcher_base().tris()}, flame long {launcher_flame(BIG_FLAME).tris()}, tank {tank().tris()}")
    out["worst"] = worst
    return out, lines


# ================================================================================================
# Blender: objects, materials, outline shells, export, views
# ================================================================================================

# ================================================================================================
# Blender: objects, materials, outline shells, split into pieces, export
# ================================================================================================
def blender_main(argv):
    import bpy
    import bmesh
    sys.path.insert(0, str(HERE.parent))
    import common
    ROOT = common.repo_root(__file__)

    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": {}}
    ALL = ("newshj-17", "newshj-55", "newshj-127", "newshj-129", "newshj-245", "newshj-283", "newshj-169", "newshj-207")
    for n in ALL:
        sprite["colors"].update(common.load_sprite(ROOT, n)["colors"])

    EMIT = {115: 1.0, 118: 1.0, 121: 1.1, 123: 1.0, 127: 1.0, 124: 1.0, 120: 1.0, 119: 1.0, 116: 1.0}
    cache = {}
    TAG = "nshj127"

    def mat_for(pa, part):
        key = (pa, part if part.startswith("breech_vent") else
               part.split("_")[0] if part.startswith(("flame", "lamp", "light", "thruster_nozzle")) else "")
        if key in cache:
            return cache[key]
        pm = common.palette_material
        if part.startswith("breech_vent"):
            which = part.split("_")[-1]
            m = pm(sprite, pa, f"{TAG}{which}", emission_strength={"hot": 1.2, "mid": 1.0, "low": 0.9}[which],
                   frames=VENT_FRAMES[which])
        elif part.startswith(("flame", "lamp", "light", "thruster_nozzle")):
            m = pm(sprite, pa, f"{TAG}{key[1]}", emission_strength=EMIT.get(pa, 1.0))
        elif part == "rocket_nose":
            m = pm(sprite, pa, TAG, metallic=0.3, roughness=0.4, emission_strength=0.3)
        elif part.startswith("canopy_glass"):
            m = pm(sprite, pa, TAG, metallic=0.1, roughness=0.12)
        elif pa in range(32, 48):
            m = pm(sprite, pa, TAG, metallic=0.25, roughness=0.45)
        elif pa >= 112:
            m = pm(sprite, pa, TAG, metallic=0.35, roughness=0.42)
        else:  # greys: satin steel
            m = pm(sprite, pa, TAG, metallic=0.4, roughness=0.42)
        cache[key] = m
        return m

    def to_obj(name, g, W, H):
        mats, mi = [], {}
        bm = bmesh.new()
        verts = [bm.verts.new(((x - W / 2) / 12, (H / 2 - y) / 12, z / 12)) for x, y, z in g.v]
        for idx, pa, part in g.f:
            m = mat_for(pa, part)
            if m.name not in mi:
                mi[m.name] = len(mats)
                mats.append(m)
            try:
                f = bm.faces.new([verts[i] for i in idx])
            except ValueError:
                continue
            f.material_index = mi[m.name]
            f.smooth = True
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        me.set_sharp_from_angle(angle=math.radians(35))
        return o

    def split_open(obj, layout, suffix):
        """split_assembly without capping the cuts (for the outline shells)."""
        out = {}
        for name, cx, cy in layout:
            x0, y0 = cx / 12, -cy / 12
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                           ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                       clear_outer=True)
            bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
            me = bpy.data.meshes.new(name + suffix)
            bm.to_mesh(me)
            bm.free()
            o = bpy.data.objects.new(name + suffix, me)
            coll.objects.link(o)
            out[name] = o
        return out

    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)

    def make_shells(obj, layout, tag):
        # D90/D118: the outline shell comes from the sealed whole model, before it is cut into pieces,
        # and is held inside it.
        sh = common.outline_shell(obj, coll, voxel=0.03, faces=4000, smooth=6, inside=0.004)
        sh.hide_render = True
        parts = split_open(sh, layout, f"_{tag}_outline")
        bpy.data.objects.remove(sh)
        for p in parts.values():
            p.data.shade_smooth()
            p.data.materials.clear()
            p.data.materials.append(outline_mat)
            p["tyrian_outline"] = True
            p.hide_render = True
        return parts

    def cut(obj, names_layout, suffix):
        parts = common.split_assembly(obj, names_layout)
        for n, o in parts.items():
            o.name = o.data.name = f"{n}{suffix}"
        return parts

    def nonempty(o):
        return len(o.data.polygons) > 0

    def subset(data, frames):
        return [{**s, "frames": [f for f in s["frames"] if f in frames]} for s in data["sprites"]]

    # ---- the launcher -------------------------------------------------------------------------
    L_LAYOUT = [("newshj-17", 200 - 224, 93 - 107), ("newshj-55", 0, 93 - 107), ("newshj-127", 0, 121 - 107),
                ("newshj-129", 248 - 224, 121 - 107)]
    base = to_obj("launcher", launcher_base(), LW, LH)
    lamps = {f: to_obj(f"launcher_lamps_f{f}", launcher_lamps(f), LW, LH) for f in (55, 89, 93)}
    nose = to_obj("launcher_nose_f89", launcher_nose(), LW, LH)
    big = to_obj("launcher_flame_f55", launcher_flame(BIG_FLAME), LW, LH)
    small = to_obj("launcher_flame_f93", launcher_flame(SMALL_FLAME), LW, LH)
    base_shell = make_shells(base, L_LAYOUT, "launcher")
    base_p = cut(base, L_LAYOUT, "")
    lamp_p = {f: cut(o, [L_LAYOUT[1]], f"-lamps-{f}")["newshj-55"] for f, o in lamps.items()}
    nose_p = cut(nose, [L_LAYOUT[1]], "-nose")["newshj-55"]
    big_p = cut(big, L_LAYOUT[:2], "-flame")
    small_p = cut(small, L_LAYOUT[:2], "-flame-short")

    def body(piece):
        out = [base_p[piece]] if nonempty(base_p[piece]) else []
        sh = base_shell[piece]
        if out and nonempty(sh):
            out.append(sh)
        return out

    data = {n: common.load_sprite(ROOT, n) for n in ALL}
    models = [
        ("newshj-17", body("newshj-17") + [big_p["newshj-17"]], 17),
        ("newshj-17-f2", body("newshj-17") + [small_p["newshj-17"]], 91),
        ("newshj-55", body("newshj-55") + [big_p["newshj-55"], lamp_p[55]], 55),
        ("newshj-55-f2", body("newshj-55") + [lamp_p[89], nose_p], 89),
        ("newshj-55-f3", body("newshj-55") + [small_p["newshj-55"], lamp_p[93]], 93),
        ("newshj-127", body("newshj-127"), None),
        ("newshj-129", body("newshj-129"), None),
    ]
    for model, objs, frame in models:
        piece = model.split("-f")[0] if "-f" in model else model
        sprites = data[piece]["sprites"] if frame is None else subset(data[piece], [frame])
        common.export_sprite_model(ROOT, objs, f"enemies/{model}", sprites)

    # ---- the hover tank, built once and mirrored ------------------------------------------------
    tg = tank()
    for tag, g, layout in (("245", tg, [("newshj-245", 210 - 222, 0), ("newshj-283", 234 - 222, 0)]),
                           ("207", tg.mirrored(49.0), [("newshj-169", 130 - 142, 0), ("newshj-207", 154 - 142, 0)])):
        obj = to_obj(f"tank{tag}", g, TW, TH)
        shells = make_shells(obj, layout, f"tank{tag}")
        pieces = cut(obj, layout, "")
        for name, _, _ in layout:
            common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}", data[name]["sprites"])
        print("tank", tag, "tris", sum(len(p.vertices) - 2 for p in obj.data.polygons))


if __name__ == "__main__":
    if "bpy" in sys.modules:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
        blender_main(argv)
    else:
        res, lines = measure_all()
        print("\n".join(lines))
