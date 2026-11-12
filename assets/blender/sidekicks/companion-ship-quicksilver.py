"""Companion Ship Quicksilver (sidekick option 24, tyrian.shp#9 frame 47, 2x2 = 24x28 px): built from the blueprint's cross-sections first (scratch/.../blueprint/model.js + blueprint.json), as
a small silver-blue escort fighter that trails the player's ship (style 1 companion).

What it is, read from the sprite (symmetric about the middle of column 12):
- a central cockpit pod (columns 9-15, rows 7-17): pointed 45 degree nose, parallel flanks, a flat
  stern; median 59, its bright 61/62 shoulders are the lit rounded top (sheen);
- a dark-grey glass bubble canopy (rows 10-13, columns 10-14, 101); the 60/111 pixels are glint;
- a light-grey dorsal spine behind it (column 12, rows 14-17, 107) between two dark-brown engines
  (rows 15-16, 162) with darkest intake throats (161) and red heat-tinted nozzles (row 17, 117);
- side keel skirts down the pod flanks (column 9, rows 15-17, 53);
- twin side nacelles (columns 4-5, rows 7-17): red ogive nose (70), purple sensor collar (86),
  silver-blue tube (60) with an orange-red light lens on the outboard side (119/122), red tail (72);
- between nacelle and pod a gun spar (column 7, rows 11-14, 59) with a purple muzzle block (86) on
  a flat inner wing (55), a low dark forward strake (51) and an aft tie brace (50);
- outboard a short swept outer wing (columns 2-3, rows 12-15, 55) with a dark-red tip light (115).

Engineering (cross-sections first): every part is a loft of stations interpolated with pchip from the
blueprint's tables. The pod is one superellipse section law (E 2.4 over, 3.0 under) with two
lengthwise chine grooves and two transverse panel grooves; the canopy sits in a machined collar;
the spine is a chamfered trapezoid with joint grooves; the nacelles are round lofts with band grooves
at the collar and tail joints and the lens set proud into the tube; the spar has cooling grooves and
an octagonal bored muzzle; the wings are chamfered plates with a flap-gap groove. Underside: closed
bottoms only. Satin metal; AO/roughness bake only (no concept projection, D50/D65); outline shell (D51).

    Blender --background --factory-startup --python companion-ship-quicksilver_A.py -- [--out a.glb] [--no-bake]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "sidekick-companion-ship-quicksilver"
MODEL = "sidekicks/companion-ship-quicksilver"
AX = 12.5  # symmetry axis (column edge coords)
METAL = 0.3


def pchip(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    f = T.pchip(xs, ys)
    return lambda x: f(min(max(x, xs[0]), xs[-1]))


def lerp(a, b, t):
    return a + (b - a) * t


def sp(t, e):
    return math.copysign(abs(t) ** (2 / e), t)


# --- blueprint dimensions (sprite px; c = column edge, v = row edge, z up) ---------------------------
POD = dict(nose=6.95, tail=17.0, zc=1.35, E=2.4, EB=3.0)
HW = pchip([(6.95, 0.0), (7.5, 0.5), (8.5, 1.5), (9.5, 2.5), (10.25, 3.25), (10.8, 3.5), (16.6, 3.5), (17.0, 3.42)])
HT = pchip([(6.95, 0.15), (7.6, 0.55), (8.6, 1.0), (9.6, 1.4), (10.6, 1.7), (12.0, 1.9), (13.6, 1.85), (14.8, 1.55),
            (16.0, 1.35), (17.0, 1.22)])
HB = pchip([(6.95, 0.1), (7.8, 0.55), (9.0, 0.85), (10.5, 1.0), (16.0, 1.05), (17.0, 0.9)])
CAN = dict(cv=12.0, rx=2.45, ry=2.05, dome=0.9)
SPZ = pchip([(13.9, 3.55), (15.0, 3.3), (16.5, 2.95), (18.0, 2.55)])
ENG = dict(c=11.1, z=2.3, r=0.82, v0=15.05, v1=17.0)
NOZ = dict(c=10.5, z=2.05, r=0.48, v0=16.9, v1=18.0)
SKIRT = dict(c0=9.05, c1=9.9, v0=15.4, v1=18.0, zb=0.45, zt=1.75)
NST = [(6.95, 0.02, 4.5), (7.3, 0.34, 4.57), (7.7, 0.62, 4.68), (8.1, 0.83, 4.8), (8.6, 0.97, 4.93), (9.2, 1.0, 5.0),
       (16.2, 1.0, 5.0), (16.6, 0.93, 4.88), (17.0, 0.82, 4.74), (17.3, 0.6, 4.64), (17.65, 0.33, 4.55), (18.0, 0.04, 4.5)]
NR = pchip([(s[0], s[1]) for s in NST])
NC = pchip([(s[0], s[2]) for s in NST])
NZ = 1.55
SPAR = dict(c=7.5, z=1.85, r=0.47, v0=10.85, v1=14.95, muzzle=(9.9, 10.9), mr=0.55)
WING = dict(c0=5.7, c1=9.3, v0=11.55, v1=15.0, zb=1.05, zt=1.45)
STRAKE = dict(poly=[(5.7, 8.95), (6.0, 8.95), (9.3, 11.12), (9.3, 11.7), (5.7, 11.7)], zb=0.95, zt=1.25)
BRACE = dict(bar=[(5.7, 16.35), (8.3, 16.35), (8.3, 16.65), (5.7, 16.65)],
             gusset=[(8.0, 16.3), (8.05, 16.0), (9.3, 15.9), (9.3, 17.0), (8.05, 16.95), (8.0, 16.7)], zb=0.95, zt=1.3)
OUTER = dict(poly=[(4.3, 11.5), (2.0, 12.95), (1.98, 16.0), (4.3, 16.15)], zb=1.18, zt=1.5)
TIP = dict(c=2.45, v0=13.9, v1=15.95, rw=0.47, rh=0.3, z=1.34)

# --- materials ----------------------------------------------------------------------------------------
SLOTS = [  # (name, palette index, metallic, roughness, emission)
    ("pod", 59, 0.65, 0.4, 0),        # 0 pod hull (sprite pod median 59)
    ("collar", 59, 0.75, 0.32, 0),    # 1 canopy collar, machined
    ("glass", 101, 0.3, 0.1, 0),      # 2 canopy glass (median 101)
    ("spine", 107, 0.65, 0.36, 0),    # 3 dorsal spine (107)
    ("engine", 162, 0.55, 0.42, 0),   # 4 engine housings (162)
    ("throat", 161, 0.2, 0.75, 0),    # 5 intake throats (161)
    ("nozzle", 117, 0.55, 0.42, 0),   # 6 nozzles (117)
    ("core", 119, 0.2, 0.4, 0.7),     # 7 exhaust cores, glowing
    ("skirt", 53, 0.6, 0.42, 0),      # 8 keel skirts (53)
    ("nacnose", 70, 0.55, 0.4, 0),    # 9 nacelle nose cones (70)
    ("naccollar", 86, 0.55, 0.4, 0),  # 10 sensor collars, muzzle blocks (86)
    ("nacbody", 60, 0.7, 0.34, 0),    # 11 nacelle tubes (60)
    ("nactail", 72, 0.55, 0.4, 0),    # 12 nacelle tail cones (72)
    ("lens", 119, 0.2, 0.25, 0.6),    # 13 nacelle light lens (119)
    ("hot", 122, 0.2, 0.25, 1.0),     # 14 lens hot centre (122)
    ("spar", 59, 0.75, 0.3, 0),       # 15 gun spars (59)
    ("bore", 48, 0.2, 0.8, 0),        # 16 bores (48)
    ("wing", 55, 0.6, 0.42, 0),       # 17 inner/outer wings (55)
    ("strake", 51, 0.5, 0.5, 0),      # 18 forward strakes (51)
    ("brace", 50, 0.5, 0.5, 0),       # 19 aft braces (50)
    ("tip", 115, 0.3, 0.35, 0.5),     # 20 wingtip nav light (115)
    ("probe", 107, 0.7, 0.3, 0),      # 21 nose probe (107)
]
(POD_M, COLLAR, GLASS, SPINE, ENGINE, THROAT, NOZZLE, CORE, SKIRTM, NACNOSE, NACCOL, NACBODY, NACTAIL, LENS, HOT,
 SPARM, BORE, WINGM, STRAKEM, BRACEM, TIPM, PROBE) = range(len(SLOTS))
TEXTURED = (POD_M, COLLAR, SPINE, ENGINE, NOZZLE, SKIRTM, NACNOSE, NACCOL, NACBODY, NACTAIL, SPARM, WINGM, STRAKEM,
            BRACEM, PROBE)


def materials(sprite):
    """One pal_<index> material per palette index: slots sharing an index share the first one's look."""
    made, out = {}, []
    for n, i, m, ro, e in SLOTS:
        if i not in made:
            made[i] = common.palette_material(sprite, i, "quicksilver", metallic=m * METAL, roughness=ro,
                                              emission_strength=e)
        out.append(made[i])
    return out


# --- geometry helpers (c, v, z in sprite px; Part coords x = c - 12, y = v) ---------------------------

def V(P, c, v, z):
    return P.v((c - 12.0, v, z))


def mir(side, c):
    return c if side < 0 else 2 * AX - c


def centroid(pts):
    n = len(pts)
    return tuple(sum(p[i] for p in pts) / n for i in range(3))


def loft(P, rings, mats, cap0=True, cap1=True, inside=None, tip0=None, tip1=None):
    """Quads between rings of (c, v, z) points (equal counts); mats one per segment or an int.
    inside: segment indices whose faces point toward the axis (bores). tip0/tip1 close to a point."""
    nseg = len(rings) - 1
    if isinstance(mats, int):
        mats = [mats] * nseg
    inside = inside or set()
    vr = [[V(P, *p) for p in r] for r in rings]
    cs = [centroid(r) for r in rings]
    for k in range(nseg):
        a, b = vr[k], vr[k + 1]
        n = len(a)
        cax = tuple((cs[k][i] + cs[k + 1][i]) / 2 for i in range(3))
        for i in range(n):
            j = (i + 1) % n
            q = (a[i], a[j], b[j], b[i])
            if k in inside:
                fc = Vector(centroid([tuple(x.co) for x in q]))
                P.f(q, mats[k], out=tuple(Vector((cax[0] - 12, cax[1], cax[2])) - fc))
            else:
                P.f(q, mats[k], away=(cax[0] - 12, cax[1], cax[2]))

    def end(idx, nb, tip, mat):
        c0, c1 = Vector(cs[idx]), Vector(cs[nb])
        if tip is not None:
            t = V(P, *tip)
            r = vr[idx]
            for i in range(len(r)):
                P.f((t, r[i], r[(i + 1) % len(r)]), mat, away=(c1.x - 12, c1.y, c1.z))
        else:
            P.f(vr[idx], mat, out=tuple(c0 - c1))
    if tip0 is not None or cap0:
        end(0, 1, tip0, mats[0])
    if tip1 is not None or cap1:
        end(-1, -2, tip1, mats[-1])


def ringY(c, v, z, r, n=10, rot=0.0, rz=None):
    rz = r if rz is None else rz
    return [(c + r * math.cos(2 * math.pi * (k + rot) / n), v, z + rz * math.sin(2 * math.pi * (k + rot) / n))
            for k in range(n)]


def inset(poly, d):
    """Convex polygon (c, v) offset inward by d."""
    n = len(poly)
    ar = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sg = 1 if ar > 0 else -1
    lines = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L * sg, dx / L * sg
        lines.append((p[0] + nx * d, p[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        A, B = lines[(i - 1) % n], lines[i]
        den = A[2] * B[3] - A[3] * B[2]
        if abs(den) < 1e-9:
            out.append((B[0], B[1]))
            continue
        t = ((B[0] - A[0]) * B[3] - (B[1] - A[1]) * B[2]) / den
        out.append((A[0] + A[2] * t, A[1] + A[3] * t))
    return out


def slab(P, poly, zb, zt, bev, side, mat):
    """Chamfered plate: planform poly (left half, mirrored by side) from zb to zt, top edge chamfer."""
    m = [(mir(side, c), v) for c, v in poly]
    lift = lambda q, z: [(c, v, z) for c, v in q]  # noqa: E731
    rings = [lift(inset(m, bev * 0.6), zb), lift(m, zb + bev * 0.5), lift(m, zt - bev), lift(inset(m, bev), zt)]
    loft(P, rings, mat)


def pod_top(dx, v):
    w = HW(v)
    if abs(dx) >= w:
        return POD["zc"]
    return POD["zc"] + HT(v) * (1 - abs(dx / w) ** POD["E"]) ** (1 / POD["E"])


# --- pod ---------------------------------------------------------------------------------------------
A_GROOVE = math.degrees(math.acos(0.8 ** (POD["E"] / 2)))
DELTA = 2.4


def pod_angles():
    base = [360 * (k + 0.5) / 16 for k in range(16)]
    g = []
    for a0 in (A_GROOVE, 180 - A_GROOVE):
        g += [(a0 - DELTA, 0), (a0, 1), (a0 + DELTA, 0)]
    out = [(a, 0) for a in base if all(abs(a - a0) > DELTA * 1.6 for a0 in (A_GROOVE, 180 - A_GROOVE))] + g
    return sorted(out)


ANG = pod_angles()
CHINE = pchip([(9.4, 0.0), (9.8, 0.07), (16.5, 0.07), (16.85, 0.0)])


def pod_ring(v, sink=0.0):
    w, ht, hb = max(HW(v), 0.02), HT(v), HB(v)
    pts = []
    for a, g in ANG:
        r = math.radians(a)
        c, s = math.cos(r), math.sin(r)
        dx = w * sp(c, POD["E"])
        z = (ht * sp(s, POD["E"])) if s > 0 else (hb * sp(s, POD["EB"]))
        k = 1.0
        if g:
            k = max(0.0, 1 - CHINE(v) / max(math.hypot(dx, z), 0.3))
        if sink:
            k *= max(0.0, 1 - sink / max(math.hypot(dx, z), 0.3))
        pts.append((AX + dx * k, v, POD["zc"] + z * k))
    return pts


def build_pod(P):
    groove = lambda v0: [(v0 - 0.06, 0), (v0 - 0.03, 0.07), (v0 + 0.03, 0.07), (v0 + 0.06, 0)]  # noqa: E731
    vs = [(v, 0) for v in (7.3, 8.0, 8.6)] + groove(9.3) + [(v, 0) for v in (10.0, 10.6, 12.0, 13.5)]
    vs += groove(14.35) + [(v, 0) for v in (15.2, 16.2, 16.8)] + [(17.0, 0.05)]
    rings = [pod_ring(v, s) for v, s in vs]
    loft(P, rings, POD_M, tip0=(AX, POD["nose"], POD["zc"] + 0.05))
    # sensor probe on the nose tip (row 6, free ink pixel)
    loft(P, [ringY(AX, 6.45, 1.42, 0.06, 6), ringY(AX, 6.9, 1.42, 0.1, 6), ringY(AX, 7.4, 1.42, 0.14, 6)], PROBE)


# --- canopy ------------------------------------------------------------------------------------------

def build_canopy(P):
    C, n = CAN, 16

    def at(rr, k, dz):
        a = 2 * math.pi * k / n
        dx, dv = C["rx"] * rr * math.cos(a), C["ry"] * rr * math.sin(a)
        return (AX + dx, C["cv"] + dv, pod_top(dx, C["cv"] + dv) + dz)
    collar = [[at(rr, k, dz) for k in range(n)] for rr, dz in
              ((1.16, -0.12), (1.13, 0.13), (1.1, 0.19), (1.03, 0.19), (0.99, 0.0))]
    loft(P, collar, COLLAR, cap0=False, cap1=False)
    DR = [0.995, 0.93, 0.8, 0.6, 0.33]
    dome = [[at(rr, k, 0.1 + C["dome"] * math.sqrt(max(0.0, 1 - rr * rr))) for k in range(n)] for rr in DR]
    crown = (AX, C["cv"], pod_top(0, C["cv"]) + 0.1 + C["dome"])
    foot = [at(0.98, k, -0.08) for k in range(n)]
    loft(P, [foot] + dome, GLASS, cap0=False, cap1=False, tip1=crown)


# --- spine -------------------------------------------------------------------------------------------

def build_spine(P):
    hwB, hwT = 0.48, 0.28

    def sec(v, g=0.0, k=1.0):
        zt, zb = SPZ(v) - g, min(pod_top(0, v), 2.6) - 0.35
        b, t = hwB - g, hwT - g * 0.5
        return [(AX - b * k, v, zb), (AX + b * k, v, zb), (AX + b, v, zt - 0.25), (AX + t, v, zt),
                (AX - t, v, zt), (AX - b, v, zt - 0.25)]
    st = [(13.9, 0, 0.6), (14.2, 0, 1.0)]
    for gv in (15.4, 16.6):
        st += [(gv - 0.05, 0, 1), (gv - 0.025, 0.06, 1), (gv + 0.025, 0.06, 1), (gv + 0.05, 0, 1)]
    st += [(17.6, 0, 1), (17.85, 0, 0.95), (18.0, 0.06, 0.85)]
    loft(P, [sec(v, g, k) for v, g, k in st], SPINE)


# --- engines, nozzles, skirts --------------------------------------------------------------------------

def build_engines(P):
    E, N, K = ENG, NOZ, SKIRT
    for side in (-1, 1):
        c, z, r = mir(side, E["c"]), E["z"], E["r"]
        # housing: rolled intake lip (mouth faces in), barrel with a band groove, closed aft end
        prof = [(E["v0"] + 0.25, r * 0.45), (E["v0"], r * 0.6), (E["v0"] + 0.05, r * 0.85), (E["v0"] + 0.3, r),
                (E["v1"] - 0.1, r), (E["v1"], r * 0.88)]
        loft(P, [ringY(c, v, z, rad, 10) for v, rad in prof], ENGINE, inside={0}, cap0=False, cap1=True)
        # throat behind the lip
        loft(P, [ringY(c, E["v0"] + 0.25, z, r * 0.45, 8), ringY(c, E["v0"] + 0.5, z, r * 0.3, 8)], THROAT,
             inside={0}, cap0=False, cap1=True)
        # nozzle out of the flat stern: outer bell, rolled lip, bore inside, glowing core
        cn = mir(side, N["c"])
        bell = [ringY(cn, N["v0"], N["z"], N["r"] * 0.95, 8), ringY(cn, 17.4, N["z"], N["r"] * 0.9, 8),
                ringY(cn, N["v1"] - 0.05, N["z"], N["r"], 8), ringY(cn, N["v1"], N["z"], N["r"] * 0.92, 8),
                ringY(cn, N["v1"] - 0.03, N["z"], N["r"] * 0.7, 8)]
        loft(P, bell, NOZZLE, inside={3}, cap0=True, cap1=False)
        loft(P, [ringY(cn, N["v1"] - 0.03, N["z"], N["r"] * 0.7, 8), ringY(cn, N["v1"] - 0.4, N["z"], N["r"] * 0.45, 8)],
             CORE, inside={0}, cap0=False, cap1=True)
        # keel skirt: a fin plate down the pod flank past the stern
        kc0, kc1 = mir(side, K["c0"]), mir(side, K["c1"])
        rings = []
        for i, v in enumerate((K["v0"], 15.6, 16.4, 17.3, K["v1"])):
            zt = K["zt"] if i < 3 else lerp(K["zt"], 1.15, (v - 16.4) / (K["v1"] - 16.4))
            zt0 = K["zt"] - 0.5 if i == 0 else zt
            rings.append([(x, v, zz) for x, zz in ((kc0, K["zb"]), (kc0, zt0 - 0.12), (lerp(kc0, kc1, 0.3), zt0),
                                                    (kc1, zt0 - 0.1), (kc1, K["zb"] + 0.2))])
        loft(P, rings, SKIRTM)


# --- side nacelles --------------------------------------------------------------------------------------

def nac_ring(side, v, scale=1.0, n=10, dr=0.0):
    return ringY(mir(side, NC(v)), v, NZ, NR(v) * scale - dr, n)


def build_nacelles(P):
    for side in (-1, 1):
        # nose ogive, its needle tip at row 6 (free ink)
        nose = [nac_ring(side, v) for v in (7.2, 7.6, 8.1, 8.7, 9.3, 9.95)]
        loft(P, nose, NACNOSE, tip0=(mir(side, 4.5), 6.6, NZ), cap1=False)
        # joint groove nose|collar, raised collar band, joint groove collar|body
        loft(P, [nac_ring(side, 9.95), nac_ring(side, 10.0, 1.0), nac_ring(side, 10.1, 1.07),
                 nac_ring(side, 10.9, 1.07), nac_ring(side, 11.0, 1.0), nac_ring(side, 11.05)],
             [NACNOSE, NACCOL, NACCOL, NACCOL, NACBODY], cap0=False, cap1=False)
        loft(P, [nac_ring(side, v) for v in (11.05, 15.94)], NACBODY, cap0=False, cap1=False)
        loft(P, [nac_ring(side, 15.94), nac_ring(side, 15.97, dr=0.07), nac_ring(side, 16.03, dr=0.07),
                 nac_ring(side, 16.06)], [NACBODY, NACTAIL, NACTAIL], cap0=False, cap1=False)
        tail = [nac_ring(side, v) for v in (16.06, 16.6, 17.0, 17.4, 17.85)]
        loft(P, tail, NACTAIL, cap0=False, tip1=(mir(side, 4.5), 18.05, NZ))
        # light lens: an arc strip on the upper outboard quadrant, proud, rounded ends; hot centre
        def arc(v, rr, a0, a1, k=4):
            out = []
            for i in range(k):
                a = math.radians(lerp(a0, a1, i / (k - 1)))
                out.append((mir(side, 5.0 + rr * math.cos(a)), v, NZ + rr * math.sin(a)))
            return out
        rings = []
        for i, v in enumerate((12.05, 12.3, 14.7, 14.95)):
            e = i in (0, 3)
            am = 128.5
            a0, a1 = (lerp(am, 97, 0.6), lerp(am, 160, 0.6)) if e else (97, 160)
            rings.append(arc(v, 1.02 if e else 1.09, a0, a1) + arc(v, 0.97, a1, a0))
        loft(P, rings, LENS)
        rings = []
        for i, v in enumerate((12.9, 13.1, 13.9, 14.1)):
            e = i in (0, 3)
            a0, a1 = (112, 140) if e else (106, 148)
            rings.append(arc(v, 1.1 if e else 1.13, a0, a1) + arc(v, 1.07, a1, a0))
        loft(P, rings, HOT)


# --- spars, wings, strakes, braces, outer wings ------------------------------------------------------------

def build_spars(P):
    S = SPAR
    for side in (-1, 1):
        c, z, r = mir(side, S["c"]), S["z"], S["r"]
        prof = [(S["v0"], r)]
        for gv in (12.85,):
            prof += [(gv - 0.06, r), (gv - 0.03, r - 0.07), (gv + 0.03, r - 0.07), (gv + 0.06, r)]
        prof += [(14.4, r), (14.7, r * 0.9), (S["v1"], r * 0.72)]
        loft(P, [ringY(c, v, z, rad, 8) for v, rad in prof], SPARM)
        o8 = lambda v, rad: ringY(c, v, z, rad, 8, 0.5)  # noqa: E731
        m0, m1, mr = S["muzzle"][0], S["muzzle"][1], S["mr"]
        loft(P, [o8(m0 + 0.02, mr * 0.32), o8(m0, mr * 0.55), o8(m0 + 0.15, mr * 0.85), o8(m0 + 0.3, mr),
                 o8(m1 - 0.08, mr), o8(m1, mr * 0.9), o8(m1 + 0.1, r * 0.9)], [BORE] + [NACCOL] * 5, inside={0})


def build_wings(P):
    W = WING
    for side in (-1, 1):
        c0, c1 = sorted((mir(side, W["c0"]), mir(side, W["c1"])))
        ch = 0.12

        def sec(v, g=0.0, k=1.0):
            zt = W["zb"] + (W["zt"] - W["zb"]) * k - g
            return [(c0 + 0.07, v, W["zb"]), (c1 - 0.07, v, W["zb"]), (c1, v, W["zb"] + 0.06), (c1, v, zt - ch),
                    (c1 - ch, v, zt), (c0 + ch, v, zt), (c0, v, zt - ch), (c0, v, W["zb"] + 0.06)]
        st = [(W["v0"], 0, 0.7), (W["v0"] + 0.1, 0, 1.0), (13.0, 0, 1)]
        st += [(14.15, 0, 1), (14.2, 0.07, 1), (14.3, 0.07, 1), (14.35, 0, 1), (14.85, 0, 0.85), (W["v1"], 0, 0.6)]
        loft(P, [sec(v, g, k) for v, g, k in st], WINGM)
        slab(P, STRAKE["poly"], STRAKE["zb"], STRAKE["zt"], 0.1, side, STRAKEM)
        slab(P, BRACE["bar"], BRACE["zb"], BRACE["zt"], 0.06, side, BRACEM)
        slab(P, BRACE["gusset"], BRACE["zb"], BRACE["zt"] + 0.15, 0.08, side, BRACEM)
        slab(P, OUTER["poly"], OUTER["zb"], OUTER["zt"], 0.1, side, WINGM)
        # outer wing panel line: a thin raised hinge strip along the aileron
        slab(P, [(3.55, 12.4), (3.75, 12.3), (3.62, 15.95), (3.42, 15.95)], OUTER["zt"] - 0.1, OUTER["zt"] + 0.03,
             0.03, side, WINGM)
        # wingtip nav-light pod
        tc = mir(side, TIP["c"])
        sc = (0.45, 1.0, 1.0, 0.8)
        loft(P, [ringY(tc, v, TIP["z"], TIP["rw"] * s, 8, 0, TIP["rh"] * s)
                 for v, s in zip((TIP["v0"], TIP["v0"] + 0.3, TIP["v1"] - 0.2, TIP["v1"]), sc)], TIPM)


def build(sprite, coll):
    mats = materials(sprite)
    P = Part("quicksilver_body", smooth_angle=34)
    build_pod(P)
    build_canopy(P)
    build_spine(P)
    build_engines(P)
    build_nacelles(P)
    build_spars(P)
    build_wings(P)
    body = T.finish(P, mats, coll)
    # collapse slots sharing a palette material into one slot each
    uniq, names = [], []
    for m in mats:
        if m.name not in names:
            names.append(m.name)
            uniq.append(m)
    remap = [names.index(m.name) for m in mats]
    old = [poly.material_index for poly in body.data.polygons]
    body.data.materials.clear()
    for m in uniq:
        body.data.materials.append(m)
    for poly, k in zip(body.data.polygons, old):
        poly.material_index = remap[k]
    body.name = body.data.name = NAME
    return body


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):  # the factory scene's cube, camera and light
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    body = build(sprite, coll)
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"quicksilver: {len(body.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        # one texture slot per distinct material (slots may share a palette material)
        mats = list(body.data.materials)
        tex = {SLOTS[i][1] for i in TEXTURED}
        T.TEXTURED = tuple(k for k, m in enumerate(mats) if int(m.name.split("_")[1]) in tex)
        T.TINT = (0.98, 0.99, 1.0)
        T.bake_maps(body, tempfile.mkdtemp(prefix="quicksilver_bake_"), size=512, samples=64)
        fmt = "WEBP"
    shell = common.outline_shell(body, coll, voxel=0.01, faces=1500, inside=0.003)
    shell.name = shell.data.name = f"{NAME}_outline"
    print(f"quicksilver: outline shell {len(shell.data.polygons)} faces")
    common.export_sprite_model(ROOT, [body, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        frame = sprite["frames"][0]
        ref = ROOT / "reference" / "models" / NAME / frame["image"]
        common.render_preview([body, shell], argv[argv.index("--preview") + 1], ref, size=frame["size"])


if __name__ == "__main__":
    main()
