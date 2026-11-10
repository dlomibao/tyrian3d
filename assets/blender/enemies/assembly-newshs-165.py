"""Grey tank with a red band, (newshs.shp 165|167 over 203|205 and the rolling-tread set
241|243 over 279|281: four 2x2 pieces, one 48 x 56 px tank seen from above).

Led by the blueprint's cross-sections (scratch blueprint/model.js) and rebuilt as a hard-surface
model fitted to the sprite's INNER mask (D74: the game's ink outline goes round the model).

The machine, in sprite px (c = column east, r = row south = the tank's front, h = up from the
ground; mirror plane c = 24.5):
- two tracks: a racetrack tread band (rear sprocket under the hull at r 13, front idler) with
  chamfered edges and cleats across its top run on a 2.125 px pitch; the cleats and the grille
  blades roll on by half a pitch / one pixel on the second frame set (241 set) as the sprite does.
  The right track is ~2 px shorter at the front than the left, as the sprite draws it.
- each track framed by an outer and an inner guard plate (flat top rounding down over the idler,
  bolt strips on top, road-wheel hub bosses on the faces);
- sloping fenders over the track's rear half with a rolled front lip and a raised inner flange;
  the red side skirts (sprite cols 3-9, rows 17-28) cut on a diagonal at the front;
- the hull: rear deck across the whole width with raised bolted access plates, the engine deck at
  the rear with two louvre grilles (dark well, side rims, five angled blades), a tail with exhaust
  boxes; the yoke towers and red ammunition-feed housing behind the turret;
- the turret: a grey mantlet plinth, the ball (r 6.3, the crown sheen is lighting) with a raised
  equator seam, a gun port and a short muzzle low on its face; the red band straps either side of
  it (the left one carries the dark vision port, palette 163);
- the red nose between the tracks: a crest (dark rear slope, bright top) and a glacis sloping
  down to a short dark front face with two towing eyes.
Each part takes the sprite's palette index for its region (median, darkest shading and brightest
highlights left out). The underside is a plain closed shape.

Run: blender -b --factory-startup -P assembly-newshs-165.py [-- --no-bake] [--no-export]
Writes public/models/enemies/<piece>.glb and src/render/spriteModels/<piece>.json for the four
pieces (each with its outline shell and its frame-tagged animated parts, both frame sets).
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WT / "assets" / "blender"), str(WT / "assets" / "blender" / "enemies")]
import common  # noqa: E402
import usp_talon as T  # noqa: E402

HERE = Path(__file__).resolve().parent
NAME = "assembly-newshs-165"
DEBUG_GLB = Path(tempfile.gettempdir()) / "assembly-newshs-165_all.glb"
TAG = "nshs165A"
PX = 1 / 12
PIECES = ["newshs-165", "newshs-167", "newshs-203", "newshs-205"]
# piece centre in screen px relative to the assembly centre (c 24, r 28)
LAYOUT = [("newshs-165", -12, -14), ("newshs-167", 12, -14), ("newshs-203", -12, 14), ("newshs-205", 12, 14)]
FRAMES = {"newshs-165": (165, 241), "newshs-167": (167, 243), "newshs-203": (203, 279), "newshs-205": (205, 281)}
MIRROR = 49.0  # c' = 49 - c
SMOOTH = 35.0

# ----------------------------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------------------------
MATS = []
SLOT = {}


def load_sprite():
    d = common.load_sprite(WT, PIECES[0])
    for n in PIECES[1:]:
        d["colors"].update(common.load_sprite(WT, n)["colors"])
    return d


def make_materials(sprite):
    def add(key, idx, metallic=0.35, roughness=0.5, tag=None):
        SLOT[key] = len(MATS)
        MATS.append(common.palette_material(sprite, idx, f"{TAG}{'-' + tag if tag else ''}",
                                            metallic=metallic, roughness=roughness))
    for i in (2, 3, 4, 5, 6, 7, 8, 9, 10):
        add(i, i)
    for i in (64, 66, 67, 68, 69, 70, 71, 72, 73):
        add(i, i, metallic=0.25, roughness=0.55)
    add(163, 163, metallic=0.1, roughness=0.4)
    add(162, 162, metallic=0.1, roughness=0.5)
    # animated parts keep their own materials (they are separate objects, not baked)
    add("cleat", 5, tag="cleat")
    add("blade", 6, tag="blade")


def M(key):
    return SLOT[key]


# ----------------------------------------------------------------------------------------------
# Geometry helpers (sprite px: c, r, h). finish() maps them to Blender.
# ----------------------------------------------------------------------------------------------

def area2(poly):
    a = 0.0
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        a += p[0] * q[1] - q[0] * p[1]
    return a


def inset(poly, d):
    """Inward miter offset of a simple polygon by d (orientation aware)."""
    if d <= 0:
        return [tuple(p) for p in poly]
    n = len(poly)
    s = 1.0 if area2(poly) > 0 else -1.0
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        nx, ny = -dy / ln * s, dx / ln * s
        lines.append((a[0] + nx * d, a[1] + ny * d, dx, dy))
    out = []
    for i in range(n):
        l1, l2 = lines[(i - 1) % n], lines[i]
        den = l1[2] * l2[3] - l1[3] * l2[2]
        if abs(den) < 1e-9:
            out.append((l2[0], l2[1]))
            continue
        t = ((l2[0] - l1[0]) * l2[3] - (l2[1] - l1[1]) * l2[2]) / den
        out.append((l1[0] + l1[2] * t, l1[1] + l1[3] * t))
    return out


def edge_out(poly, i):
    s = 1.0 if area2(poly) > 0 else -1.0
    a, b = poly[i], poly[(i + 1) % len(poly)]
    dx, dy = b[0] - a[0], b[1] - a[1]
    ln = math.hypot(dx, dy) or 1e-9
    return (dy / ln * s, -dx / ln * s)


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def prism(P, poly, h0, top, ch, mat, side=None, cham=None, bottom=True):
    """A chamfered prism over a (possibly concave) plan outline: vertical sides from h0 to top - ch,
    a 45-degree chamfer, a flat or sloped top (top: number or function (c, r))."""
    tf = top if callable(top) else (lambda c, r, t=top: t)
    side = mat if side is None else side
    cham = side if cham is None else cham
    n = len(poly)
    ip = inset(poly, ch)
    r0 = [P.v((c, r, h0)) for c, r in poly]
    r1 = [P.v((c, r, tf(c, r) - ch)) for c, r in poly]
    r2 = [P.v((c, r, tf(c, r))) for c, r in ip] if ch > 0 else r1
    P.f(r2, M(mat), out=(0, 0, 1))
    for i in range(n):
        j = (i + 1) % n
        ox, oy = edge_out(poly, i)
        P.f((r0[i], r0[j], r1[j], r1[i]), M(side), out=(ox, oy, 0))
        if ch > 0:
            P.f((r1[i], r1[j], r2[j], r2[i]), M(cham), out=(ox, oy, 1.0))
    if bottom:
        P.f(r0, M(side), out=(0, 0, -1))


def extrude_c(P, prof, c0, c1, ch, mats, end=None, cham=None):
    """Extrusion across c of a closed (r, h) profile from c0 to c1 with 45-degree chamfered end
    edges. mats: one key, or one per profile edge."""
    n = len(prof)
    mk = (lambda i: mats[i]) if isinstance(mats, (list, tuple)) else (lambda i: mats)
    end = mk(0) if end is None else end
    ip = inset(prof, ch) if ch > 0 else prof
    A = [P.v((c0, r, h)) for r, h in ip]
    B = [P.v((c0 + ch, r, h)) for r, h in prof] if ch > 0 else A
    C = [P.v((c1 - ch, r, h)) for r, h in prof] if ch > 0 else None
    D = [P.v((c1, r, h)) for r, h in ip]
    C = C or D
    for i in range(n):
        j = (i + 1) % n
        orr, oh = edge_out(prof, i)
        P.f((B[i], B[j], C[j], C[i]), M(mk(i)), out=(0, orr, oh))
        if ch > 0:
            m = M(cham if cham is not None else mk(i))
            P.f((A[i], A[j], B[j], B[i]), m, out=(-1, orr, oh))
            P.f((C[i], C[j], D[j], D[i]), m, out=(1, orr, oh))
    P.f(A, M(end), out=(-1, 0, 0))
    P.f(D, M(end), out=(1, 0, 0))


def obox(P, centre, u, v, w, lu, lv, lw, ch, mat):
    """A chamfered box with centre and unit axes u, v, w (sizes lu, lv, lw)."""
    ch = min(ch, lu / 2.05, lv / 2.05, lw / 2.05)
    pts = []
    for a, b, c in T.cbox(-lu / 2, lu / 2, -lv / 2, lv / 2, -lw / 2, lw / 2, ch):
        pts.append(tuple(centre[k] + a * u[k] + b * v[k] + c * w[k] for k in range(3)))
    T.hull(P, pts, M(mat))


def box(P, c0, c1, r0, r1, h0, h1, mat, ch=0.2):
    ch = min(ch, (c1 - c0) / 2.05, (r1 - r0) / 2.05, (h1 - h0) / 2.05)
    T.hull(P, T.cbox(c0, c1, r0, r1, h0, h1, ch), M(mat))


def cyl(P, p0, p1, rad, mat, n=12, ch=0.0, cap_mat=None):
    """A cylinder from p0 to p1 (the p1 end chamfered by ch)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    e1 = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
    e2 = d.cross(e1)

    def ring(p, rr):
        return [P.v(tuple(p + rr * (math.cos(2 * math.pi * k / n) * e1 + math.sin(2 * math.pi * k / n) * e2)))
                for k in range(n)]
    A = ring(p0, rad)
    B = ring(p1 - d * ch, rad) if ch > 0 else None
    Cc = ring(p1, rad - ch) if ch > 0 else ring(p1, rad)
    B = B or Cc
    cen = tuple((p0 + p1) / 2)
    for k in range(n):
        j = (k + 1) % n
        P.f((A[k], A[j], B[j], B[k]), M(mat), away=cen)
        if ch > 0:
            P.f((B[k], B[j], Cc[j], Cc[k]), M(mat), away=cen)
    P.f(A, M(mat), out=tuple(-d))
    P.f(Cc, M(cap_mat if cap_mat is not None else mat), out=tuple(d))


def ellipsoid(P, cen, a, b, z, mat, nu=40, nv=18, zcut=None):
    c0, r0, h0 = cen
    v0 = -math.pi / 2 if zcut is None else math.asin(max(-1.0, min(1.0, (zcut - h0) / z)))
    rings = []
    for j in range(nv):
        v = v0 + (math.pi / 2 - v0) * j / nv
        cv, sv = math.cos(v), math.sin(v)
        rings.append([P.v((c0 + a * cv * math.cos(2 * math.pi * i / nu), r0 + b * cv * math.sin(2 * math.pi * i / nu),
                           h0 + z * sv)) for i in range(nu)])
    pole = P.v((c0, r0, h0 + z))
    for j in range(nv - 1):
        for i in range(nu):
            k = (i + 1) % nu
            P.f((rings[j][i], rings[j][k], rings[j + 1][k], rings[j + 1][i]), M(mat), away=cen)
    for i in range(nu):
        P.f((rings[-1][i], rings[-1][(i + 1) % nu], pole), M(mat), away=cen)
    if zcut is not None:
        P.f(rings[0], M(mat), out=(0, 0, -1))


def ring_band(P, cen, r_out, r_in, h0, h1, mat, n=40):
    """A flat annular band (a raised seam ring round a ball)."""
    c0, r0 = cen

    def ring(rr, h):
        return [P.v((c0 + rr * math.cos(2 * math.pi * k / n), r0 + rr * math.sin(2 * math.pi * k / n), h)) for k in range(n)]
    oa, ob, ia, ib = ring(r_out, h0), ring(r_out, h1), ring(r_in, h0), ring(r_in, h1)
    for k in range(n):
        j = (k + 1) % n
        ang = 2 * math.pi * (k + 0.5) / n
        o = (math.cos(ang), math.sin(ang), 0)
        P.f((oa[k], oa[j], ob[j], ob[k]), M(mat), out=o)
        P.f((ia[k], ia[j], ib[j], ib[k]), M(mat), out=(-o[0], -o[1], 0))
        P.f((ob[k], ob[j], ib[j], ib[k]), M(mat), out=(0, 0, 1))
        P.f((oa[k], oa[j], ia[j], ia[k]), M(mat), out=(0, 0, -1))


def pchip_at(xk, yk, x):
    return T.pchip(list(xk), list(yk))(x)


def racetrack(rA, rB, hc, rad, n=14):
    pts = []
    for i in range(n + 1):
        t = -math.pi / 2 + math.pi * i / n
        pts.append((rB + rad * math.cos(t), hc - rad * math.sin(t)))
    for i in range(n + 1):
        t = math.pi / 2 + math.pi * i / n
        pts.append((rA + rad * math.cos(t), hc - rad * math.sin(t)))
    return pts


# ----------------------------------------------------------------------------------------------
# Parts
# ----------------------------------------------------------------------------------------------
TRACK = dict(c0=6.0, c1=16.0, rA=13.7, hc=2.65, rad=2.6)
SIDES = {  # per side: idler centre rB, guard nose rG, hub stations
    # rG: guard nose (outer plate, inner plate); fo: fender's outer edge column
    "L": dict(rB=52.35, rG=(53.9, 53.2), hubs=(36.5, 42.5, 48.5), fo=3.2),
    "R": dict(rB=51.3, rG=(52.4, 52.7), hubs=(36.5, 42.0, 47.6), fo=3.6),
}
PITCH = 2.125
DECK = 8.0


def mc(side):
    return (lambda c: c) if side == "L" else (lambda c: MIRROR - c)


def span(side, c0, c1):
    f = mc(side)
    a, b = f(c0), f(c1)
    return (min(a, b), max(a, b))


def mpoly(side, poly):
    f = mc(side)
    return [(f(c), r) for c, r in poly]


def guard_profile(rG):
    rk = [30.4, rG - 4.9, rG - 2.6, rG - 1.0, rG]
    hk = [6.1, 6.1, 5.6, 4.4, 2.6]
    f = T.pchip(rk, hk)
    rs = [30.4, rG - 4.9, rG - 3.9, rG - 3.1, rG - 2.4, rG - 1.7, rG - 1.0, rG - 0.5, rG]
    top = [(r, f(r)) for r in rs]
    return [(31.2, 0.7), (rG - 1.15, 0.7), (rG, 1.6)] + top[::-1][:-1] + [(31.2, 6.1)]


def track(P, side):
    S = SIDES[side]
    c0, c1 = span(side, TRACK["c0"], TRACK["c1"])
    prof = racetrack(TRACK["rA"], S["rB"], TRACK["hc"], TRACK["rad"], 14)
    extrude_c(P, prof, c0, c1, 0.6, 3)
    # sprocket / idler hubs inside the band ends (seen from the front between the guards)
    for rr in (S["rB"],):
        cyl(P, ((c0 + c1) / 2 - 5.25, rr, TRACK["hc"]), ((c0 + c1) / 2 + 5.25, rr, TRACK["hc"]), 1.3, 4, n=14)


def cleats(P, side, phase):
    S = SIDES[side]
    c0, c1 = span(side, TRACK["c0"], TRACK["c1"])
    cm = (c0 + c1) / 2
    rB, hc, rad = S["rB"], TRACK["hc"], TRACK["rad"]
    for k in range(-1, 14):
        r = 33.4 + k * PITCH + phase * PITCH / 2
        if r < 32.9:
            continue
        if r <= rB:
            obox(P, (cm, r, hc + rad + 0.17), (1, 0, 0), (0, 1, 0), (0, 0, 1), c1 - c0 - 1.1, 0.8, 0.42, 0.12, "cleat")
        else:
            ang = (r - rB) / rad
            if ang > math.pi * 0.8:
                continue
            nr, nh = math.sin(ang), math.cos(ang)
            obox(P, (cm, rB + (rad + 0.17) * nr, hc + (rad + 0.17) * nh), (1, 0, 0), (0, nh, -nr), (0, nr, nh),
                 c1 - c0 - 1.1, 0.8, 0.42, 0.12, "cleat")


def guards(P, side):
    S = SIDES[side]
    f = mc(side)
    for (a, b), face, rG in (((3.4, 6.1), 3.4, S["rG"][0]), ((15.9, 18.6), 18.6, S["rG"][1])):
        prof = guard_profile(rG)
        c0, c1 = span(side, a, b)
        extrude_c(P, prof, c0, c1, 0.35, 6)
        # bolt strip along the top
        cb = f((a + b) / 2)
        r = 32.2
        while r < rG - 4.6:
            cyl(P, (cb, r, 5.9), (cb, r, 6.32), 0.32, 8, n=8, ch=0.08)
            r += 4.0
        # road-wheel hub bosses on the outward face (outer plate) / the face over the glacis (inner)
        cf = f(face)
        out = (f(face) - f((a + b) / 2))
        sgn = 1.0 if out > 0 else -1.0
        for rh in S["hubs"]:
            cyl(P, (cf - sgn * 0.1, rh, 3.4), (cf + sgn * 0.28, rh, 3.4), 1.3, 7, n=16, ch=0.12)
            cyl(P, (cf + sgn * 0.2, rh, 3.4), (cf + sgn * 0.55, rh, 3.4), 0.55, 9, n=10, ch=0.1)
            for k in range(5):
                a5 = 2 * math.pi * k / 5 + 0.3
                cyl(P, (cf + sgn * 0.2, rh + 0.9 * math.cos(a5), 3.4 + 0.9 * math.sin(a5)),
                    (cf + sgn * 0.42, rh + 0.9 * math.cos(a5), 3.4 + 0.9 * math.sin(a5)), 0.16, 8, n=6)


def fen_top(c, r):
    return 8.0 - 1.3 * max(0.0, min(1.0, (r - 21.5) / 11.1))


def fender(P, side):
    fo = SIDES[side]["fo"]
    plan = [(9.4, 21.5), (19.0, 21.5), (19.0, 32.6), (fo, 32.6), (fo, 31.2), (4.2, 29.6)]
    prism(P, mpoly(side, plan), 1.0, fen_top, 0.5, 5, cham=7)
    # rolled front lip
    c0, c1 = span(side, fo + 0.1, 18.9)
    extrude_c(P, [(32.0, 6.1), (32.75, 6.1), (32.75, 6.75), (32.35, 7.05), (32.0, 6.95)], c0, c1, 0.15, 6)
    # raised inner flange along the fender's inner edge (the sprite's bright column 16)
    prism(P, mpoly(side, rect(15.6, 21.8, 17.8, 32.3)), 5.0, lambda c, r: fen_top(c, r) + 0.45, 0.3, 8, side=6, cham=9)


def skirt(P, side):
    plan = [(4.0, 17.0), (9.4, 17.0), (9.4, 21.4), (8.6, 21.9), (4.9, 28.0), (4.0, 28.6)]
    sk = 69 if side == "L" else 67  # the sprite's own index per side
    prism(P, mpoly(side, plan), 1.4, 7.7, 0.45, sk, cham=sk + 2)
    f = mc(side)
    # vertical stiffener on the outer face and two bolts on top
    c0, c1 = span(side, 3.78, 4.05)
    box(P, c0, c1, 18.5, 26.5, 2.0, 7.0, 66, ch=0.08)
    for r in (18.7, 20.4):
        cyl(P, (f(7.9), r, 7.6), (f(7.9), r, 7.95), 0.33, 66, n=8, ch=0.08)
    # lower armour strake on the outer face
    c0, c1 = span(side, 3.72, 4.05)
    box(P, c0, c1, 17.4, 27.2, 1.5, 2.2, 66, ch=0.1)


LV = dict(c0=7.0, c1=15.0, r0=9.0, r1=14.0)


def louvre(P, side):
    c0, c1 = span(side, LV["c0"], LV["c1"])
    # dark well (its floor is the grille's shadow)
    prism(P, rect(c0, LV["r0"], c1, LV["r1"]), 4.6, 7.2, 0.0, 3, side=5)
    # side rims and a low rear lip
    for a, b in ((LV["c0"] - 0.1, LV["c0"] + 0.55), (LV["c1"] - 0.55, LV["c1"] - 0.05)):
        s0, s1 = span(side, a, b)
        prism(P, rect(s0, LV["r0"], s1, LV["r1"]), 7.0, 8.6, 0.15, 5)
    prism(P, rect(c0, LV["r0"], c1, LV["r0"] + 0.3), 7.0, 7.9, 0.1, 4)
    # exhaust box on the rear face under the grille
    e0, e1 = span(side, 9.0, 13.0)
    box(P, e0, e1, 9.1, 9.8, 1.6, 4.4, 4, ch=0.2)
    box(P, e0 + 0.5, e1 - 0.5, 9.0, 9.3, 2.1, 3.9, 2, ch=0.08)
    for cc in (e0 + 0.9, e1 - 0.9):  # mounting straps
        box(P, cc - 0.25, cc + 0.25, 9.05, 9.75, 1.4, 4.6, 5, ch=0.08)


def blades(P, side, phase):
    c0, c1 = span(side, LV["c0"], LV["c1"])
    a = math.radians(58)
    for k in range(-1, 4):
        r = LV["r0"] + 1.5 + 2 * k - phase
        if r < LV["r0"] + 0.45 or r > LV["r1"] - 0.45:
            continue
        obox(P, ((c0 + c1) / 2, r, 7.95), (1, 0, 0), (0, math.cos(a), math.sin(a)), (0, -math.sin(a), math.cos(a)),
             c1 - c0 - 1.2, 1.5, 0.22, 0.06, "blade")


def hull(P):
    plan = [(4.0, 11.0), (7.0, 11.0), (7.0, 14.0), (15.0, 14.0), (15.0, 11.0), (34.0, 11.0), (34.0, 14.0), (42.0, 14.0),
            (42.0, 11.0), (44.2, 11.0), (46.0, 12.4), (46.0, 17.0), (39.6, 17.0), (39.6, 21.5), (30.0, 21.5), (30.0, 31.0),
            (19.0, 31.0), (19.0, 21.5), (9.4, 21.5), (9.4, 17.0), (3.0, 17.0), (3.0, 12.2)]
    prism(P, plan, 0.8, DECK, 0.5, 6)
    # engine deck: the rear extension carrying the grilles, a step lower
    prism(P, rect(7.0, 9.6, 42.0, 11.6), 0.8, 4.6, 0.2, 5)
    # raised bolted access plates on the rear deck (real panel edges)
    for c0, c1 in ((4.4, 15.0), (34.0, 44.6)):
        prism(P, rect(c0, 14.2, c1, 16.8), DECK - 0.2, DECK + 0.16, 0.1, 6)
        for c in (c0 + 0.7, c1 - 0.7):
            for r in (14.85, 16.15):
                cyl(P, (c, r, DECK + 0.1), (c, r, DECK + 0.34), 0.26, 8, n=8, ch=0.07)
        # lifting eye at the plate's inner end
        box(P, c0 + 4.6, c0 + 5.9, 15.2, 15.8, DECK + 0.1, DECK + 0.7, 7, ch=0.15)
    # rear-corner tie-down lugs
    for c in (4.0, 43.0):
        box(P, c, c + 1.0, 11.6, 12.6, DECK - 0.1, DECK + 0.45, 7, ch=0.15)
    # belly between the tracks (underside: plain closed box)
    prism(P, rect(19.0, 12.0, 30.0, 44.0), 0.6, 2.0, 0.0, 4)


def nose(P):
    # crest: dark rear slope, bright top, its front face buried in the glacis
    prof = [(31.0, 1.5), (35.5, 1.5), (35.5, 7.0), (34.8, 7.75), (33.0, 7.85), (31.0, 7.05)]
    # edges: bottom, front, top-front, top, rear slope, rear face
    extrude_c(P, prof, 19.0, 30.0, 0.35, [4, 67, 70, 70, 66, 66], end=66)
    gl = [(35.3, 1.0), (44.0, 1.0), (44.0, 1.9), (43.6, 2.3), (35.3, 7.1)]
    extrude_c(P, gl, 19.05, 29.95, 0.35, [4, 64, 67, 67, 67], end=67, cham=64)
    # cross weld bead where the crest meets the glacis
    extrude_c(P, [(35.2, 6.8), (35.75, 6.55), (35.75, 7.0), (35.3, 7.35)], 19.3, 29.7, 0.1, 68)
    for c in (21.0, 28.0):
        obox(P, (c, 43.85, 1.55), (1, 0, 0), (0, 1, 0), (0, 0, 1), 1.1, 0.5, 0.9, 0.12, 64)
        cyl(P, (c - 0.75, 43.95, 1.55), (c + 0.75, 43.95, 1.55), 0.22, 64, n=8)


BC = (24.6, 20.6, 10.2)
BR = 6.3


def turret(P):
    prism(P, [(19.4, 14.0), (30.4, 14.0), (30.4, 29.7), (19.4, 29.7)], 7.0, 8.9, 0.4, 6, side=5, cham=9)
    # mantlet front: a steep plate down to the nose crest (the sprite's darker row 30)
    extrude_c(P, [(29.4, 7.0), (31.0, 7.0), (31.0, 7.5), (29.75, 8.9), (29.4, 8.9)], 19.6, 30.2, 0.3, [5, 5, 6, 6, 5], end=5)


def ball(P):
    """The ball and what it carries: built as its own object and given whole to piece newshs-167
    (its centre is on that side), so no piece seam runs over the crown."""
    ellipsoid(P, BC, BR, BR, BR, 9, nu=44, nv=20, zcut=8.0)
    ring_band(P, BC[:2], BR + 0.09, BR - 0.4, BC[2] - 0.16, BC[2] + 0.16, 7, n=44)
    # gun port low on the south face and a short muzzle
    a = math.radians(-28)
    p = (BC[0], BC[1] + BR * math.cos(a), BC[2] + BR * math.sin(a))
    obox(P, (p[0], p[1] - 0.12, p[2]), (1, 0, 0), (0, -math.sin(a), math.cos(a)), (0, math.cos(a), math.sin(a)),
         2.4, 1.3, 0.5, 0.12, 2)
    d = (0, math.cos(math.radians(-8)), math.sin(math.radians(-8)))
    q0 = (p[0], p[1] - 0.2, p[2])
    cyl(P, q0, (q0[0], q0[1] + 1.25 * d[1], q0[2] + 1.25 * d[2]), 0.45, 4, n=12, ch=0.1, cap_mat=2)
    # small sight block above the port
    a2 = math.radians(-6)
    p2 = (BC[0] + 2.1, BC[1] + (BR - 0.05) * math.cos(a2) * 0.94, BC[2] + BR * math.sin(a2))
    obox(P, p2, (1, 0, 0), (0, 0, 1), (0, 1, 0), 0.9, 0.7, 0.7, 0.12, 2)


def yoke(P):
    prism(P, rect(16.0, 8.0, 22.6, 15.2), 0.8, 10.6, 0.6, 8, cham=9)
    prism(P, [(28.4, 8.0), (33.0, 8.0), (33.9, 8.9), (33.9, 15.2), (28.4, 15.2)], 0.8, 10.6, 0.6, 8, cham=9)
    prism(P, rect(22.6, 9.0, 28.6, 15.0), 0.8, 9.7, 0.4, 69, cham=70)
    for c in (23.3, 27.9):
        cyl(P, (c, 10.0, 9.6), (c, 10.0, 9.95), 0.3, 67, n=8, ch=0.08)
    # rear faces: bolted cover plates on the towers, an access hatch on the feed housing
    for c0, c1 in ((16.7, 21.9), (29.1, 33.2)):
        box(P, c0, c1, 7.75, 8.1, 3.0, 9.4, 8, ch=0.12)
        for c in (c0 + 0.6, c1 - 0.6):
            for h in (3.6, 8.8):
                cyl(P, (c, 7.85, h), (c, 7.6, h), 0.22, 9, n=8, ch=0.06)
    box(P, 23.3, 27.9, 8.75, 9.1, 4.0, 8.6, 70, ch=0.12)
    box(P, 25.2, 26.0, 8.6, 8.8, 6.0, 6.6, 67, ch=0.06)
    # feed chute lid seam across the housing
    box(P, 22.9, 28.3, 12.3, 12.55, 9.6, 9.78, 67, ch=0.05)
    # left tower: a round commander's hatch; right tower: a vent block
    cyl(P, (19.3, 11.4, 10.5), (19.3, 11.4, 10.82), 1.7, 8, n=20, ch=0.14)
    box(P, 18.9, 19.7, 9.4, 9.9, 10.75, 11.1, 9, ch=0.1)
    box(P, 29.4, 32.2, 9.0, 11.6, 10.5, 10.85, 7, ch=0.12)
    for k in range(3):
        box(P, 29.7, 31.9, 9.35 + 0.75 * k, 9.6 + 0.75 * k, 10.8, 10.9, 6, ch=0.0)
    # trunnion caps on the towers' inner faces (seen past the ball from the side and rear)
    obox(P, (22.75, 13.0, 9.0), (0, 1, 0), (0, 0, 1), (1, 0, 0), 1.6, 1.6, 0.3, 0.1, 7)
    obox(P, (28.45, 13.0, 9.0), (0, 1, 0), (0, 0, 1), (1, 0, 0), 1.6, 1.6, 0.3, 0.1, 7)
    # tail: tow pintle on the rear face between the towers
    box(P, 23.6, 27.6, 8.7, 9.05, 2.4, 3.6, 4, ch=0.12)


def band(P):
    prism(P, rect(10.0, 17.0, 19.2, 22.0), 7.5, 8.6, 0.3, 69, cham=72)
    prism(P, rect(29.8, 17.0, 39.0, 22.0), 7.5, 8.6, 0.3, 71, cham=73)
    prism(P, rect(15.0, 18.0, 18.0, 21.0), 8.0, 8.85, 0.18, 163, side=162)
    box(P, 15.3, 17.7, 20.55, 20.9, 8.7, 8.95, 162, ch=0.06)  # visor lip
    for c in (10.7, 12.6):
        for r in (17.75, 21.25):
            cyl(P, (c, r, 8.5), (c, r, 8.78), 0.22, 69, n=8, ch=0.06)
    for c in (32.0, 34.4, 36.8, 38.3):
        for r in (17.75, 21.25):
            cyl(P, (c, r, 8.5), (c, r, 8.78), 0.22, 72, n=8, ch=0.06)


def finish(P, coll):
    P.orient()
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, -24 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(P.name)
    bm.to_mesh(me)
    bm.free()
    for mat in MATS:
        me.materials.append(mat)
    obj = bpy.data.objects.new(P.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(P.smooth_angle))
    return obj


def split_open(obj, coll):
    """Cut the outline shell into the pieces without filling the cuts (no ink along the seams)."""
    out = {}
    for name, cx, cy in LAYOUT:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def weighted(o):
    o.data.shade_smooth()
    o.data.set_sharp_from_angle(angle=math.radians(SMOOTH))
    wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(o)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite = load_sprite()
    make_materials(sprite)
    coll = common.reset_collection(NAME + "_A")
    P = T.Part(NAME, smooth_angle=SMOOTH)
    for s in ("L", "R"):
        track(P, s)
        guards(P, s)
        fender(P, s)
        skirt(P, s)
        louvre(P, s)
    hull(P)
    nose(P)
    turret(P)
    yoke(P)
    band(P)
    obj = finish(P, coll)
    B = T.Part(NAME + "_ball", smooth_angle=SMOOTH)
    ball(B)
    bobj = finish(B, coll)
    # join the ball in so the bake, the outline shell and the piece cut see the whole tank
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bobj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    weighted(obj)
    anims = []
    for ph in (0, 1):
        A = T.Part(f"{NAME}_anim{ph}", smooth_angle=SMOOTH)
        for s in ("L", "R"):
            cleats(A, s, ph)
            blades(A, s, ph)
        anims.append(finish(A, coll))
    fmt = "AUTO"
    if "--no-bake" not in argv:
        T.TINT = (1.0, 1.0, 1.0)  # neutral AO (the Talon's cool tint is for its brass)
        T.TEXTURED = tuple(i for k, i in SLOT.items() if k not in ("cleat", "blade"))
        T.bake_maps(obj, tempfile.mkdtemp(prefix="nshs165A_bake_"), size=1024, samples=64)
        fmt = "WEBP"
    shell = common.outline_shell(obj, coll, voxel=0.012, faces=4000, smooth=6, inside=0.01)
    shell.hide_render = True
    pieces = common.split_assembly(obj, LAYOUT, coll)
    shells = split_open(shell, coll)
    anim_pieces = [common.split_assembly(a, LAYOUT, coll) for a in anims]
    export = []
    total = 0
    for name, cx, cy in LAYOUT:
        p = pieces[name]
        p.name = name
        weighted(p)
        group = [p, shells[name]]
        for ph in (0, 1):
            ap = anim_pieces[ph][name]
            if len(ap.data.polygons) == 0:
                bpy.data.objects.remove(ap, do_unlink=True)
                continue
            ap.name = f"{name}_anim{ph}"
            ap.data.shade_smooth()
            ap.data.set_sharp_from_angle(angle=math.radians(SMOOTH))
            common.frame_part(ap, [FRAMES[name][ph]])
            group.append(ap)
        t = sum(tris(o) for o in group if o is not shells[name])
        total += t
        print(f"built piece {name}: {t} tris (+ outline {tris(shells[name])}), objects {[o.name for o in group]}")
        if "--no-export" not in argv:
            sprites = [{"sheet": "newshs.shp", "size": 2, "frames": list(FRAMES[name])}]
            common.export_sprite_model(WT, group, f"enemies/{name}", sprites, image_format=fmt)
        for o in group:
            o.location = (cx / 12, -cy / 12, 0)
        export += group
    common.export_glb(export, DEBUG_GLB, image_format=fmt)
    print(f"built {NAME}: {total} triangles per frame set incl. both anim sets")


if __name__ == "__main__":
    main()
