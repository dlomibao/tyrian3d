"""Grey missile-launcher module with a red roof spine and seven launch tubes (newshs.shp frame 267).

What it is (D123): type 550 is the launcher module that rides the link-45 tracked tank
(assembly-newshs-165) at a constant offset (+12, +4 from piece 548). It is neither a free hover
craft nor a ground bunker. It stands on the tank's ball-turret ring (Z0 = 10 px lift, turret
collar below the belly) so the tank's ball never shows through the deck or the rack. Boss of
1.2 ASTEROID2; its turret launches type 551 (newsh-caret-171). A heavy armoured box with a
rounded closed belly, a raised segmented red magazine spine with a sloped nose, two side
magazines with louvred rack cheeks, and a sloped rack of 4 + 3 loaded launch tubes at the
south (player-facing) end. One frame, one model.

Sprite px: c = column edge east, r = row edge south, h = up. Plan: row 2 c 6-19 widening to c 3-22
by row 6, to row 24, mirrored about c 12.5. Spine c 10-15 rows 2-16; tubes at (6.5, 18.5) (10.5,
18.5) (14.5, 18.5) (18.5, 18.5) (8.5, 22.5) (12.5, 22.5) (16.5, 22.5).

Run: blender --background --python assets/blender/enemies/newshs-267.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "newshs-267"
ROOT = common.repo_root(__file__)
MID = 12.5


# --- maths helpers (copied in; the blueprint's helpers.part.js in Python) ------------------------

def pchip(xk, yk, xs):
    n = len(xk)
    d = [(yk[i + 1] - yk[i]) / (xk[i + 1] - xk[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            m[i] = 3 * (xk[i + 1] - xk[i - 1]) / ((2 * xk[i + 1] - xk[i] - xk[i - 1]) / d[i - 1]
                                                  + (xk[i + 1] - 2 * xk[i] + xk[i - 1]) / d[i])
    out = []
    for x in xs:
        i = 0
        while i < n - 2 and x > xk[i + 1]:
            i += 1
        h = xk[i + 1] - xk[i]
        t = min(1.0, max(0.0, (x - xk[i]) / h))
        t2, t3 = t * t, t * t * t
        out.append((2 * t3 - 3 * t2 + 1) * yk[i] + (t3 - 2 * t2 + t) * h * m[i]
                   + (-2 * t3 + 3 * t2) * yk[i + 1] + (t3 - t2) * h * m[i + 1])
    return out


def stations(keys, rs):
    """Resample key dicts (keyed by r) with pchip on every other field at rs."""
    xk = [k["r"] for k in keys]
    out = [{"r": r} for r in rs]
    for f in keys[0]:
        if f == "r":
            continue
        for o, v in zip(out, pchip(xk, [k[f] for k in keys], rs)):
            o[f] = v
    return out


def frange(a, b, step):
    o, x = [], a
    while x < b - 1e-6:
        o.append(round(x, 4))
        x += step
    o.append(b)
    return o


def centroid(ring):
    n = len(ring)
    return tuple(sum(p[k] for p in ring) / n for k in range(3))


def fan(ring, c=None):
    if c is not None:
        return [(c, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]
    return [(ring[0], ring[i], ring[i + 1]) for i in range(1, len(ring) - 1)]


def band(a, b):
    n = len(a)
    return [q for i in range(n) for q in ((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]),)]


def vadd(a, b, s=1.0):
    return tuple(a[k] + b[k] * s for k in range(3))


def frame(axis):
    t = math.sqrt(sum(v * v for v in axis))
    a = [v / t for v in axis]
    ref = [0, 0, 1] if abs(a[2]) < 0.9 else [1, 0, 0]
    u = [a[1] * ref[2] - a[2] * ref[1], a[2] * ref[0] - a[0] * ref[2], a[0] * ref[1] - a[1] * ref[0]]
    lu = math.sqrt(sum(v * v for v in u))
    u = [v / lu for v in u]
    v = [a[1] * u[2] - a[2] * u[1], a[2] * u[0] - a[0] * u[2], a[0] * u[1] - a[1] * u[0]]
    return a, u, v


def ring_at(P, F, R, n, rot=0.0):
    _, u, v = F
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n + rot
        co, si = math.cos(t) * R, math.sin(t) * R
        out.append(tuple(P[i] + u[i] * co + v[i] * si for i in range(3)))
    return out


def inset(poly, d):
    """Inset a convex polygon (c, r) by d along its edge normals."""
    if d <= 0:
        return [tuple(p) for p in poly]
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    L = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        ln = math.hypot(nx, ny) or 1
        nx, ny = nx / ln, ny / ln
        if (cx - (a[0] + b[0]) / 2) * nx + (cy - (a[1] + b[1]) / 2) * ny < 0:
            nx, ny = -nx, -ny
        L.append((a[0] + nx * d, a[1] + ny * d, b[0] - a[0], b[1] - a[1]))
    out = []
    for i in range(n):
        L1, L2 = L[i - 1], L[i]
        den = L1[2] * L2[3] - L1[3] * L2[2]
        if abs(den) < 1e-9:
            out.append((L2[0], L2[1]))
            continue
        t = ((L2[0] - L1[0]) * L2[3] - (L2[1] - L1[1]) * L2[2]) / den
        out.append((L1[0] + L1[2] * t, L1[1] + L1[3] * t))
    return out


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


# --- the model as polygons in sprite px (c, r, h), grouped by piece and palette -----------------

class Model:
    def __init__(self):
        self.pieces = []  # [(element, [(pal, smooth, [polys])])]
        self.cur = None

    def piece(self, element):
        self.cur = (element, [])
        self.pieces.append(self.cur)

    def add(self, pal, polys, smooth=False):
        self.cur[1].append((pal, smooth, polys))


M = Model()


def loft_r(element, stns, section, pal, smooth=False, caps=True, cap_pal=None):
    """Loft rings along r. section(st) returns [(c, h, tag)] (closed; the tag names the segment
    from this point to the next); pal(tag, r) gives each strip's palette index."""
    M.piece(element)
    rings = [[((c, s["r"], h), tag) for c, h, tag in section(s)] for s in stns]
    groups = {}
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        n = len(a)
        rmid = (stns[i]["r"] + stns[i + 1]["r"]) / 2
        for k in range(n):
            j = (k + 1) % n
            P = pal(a[k][1], rmid)
            sm = smooth(a[k][1]) if callable(smooth) else smooth
            groups.setdefault((P, sm), []).append((a[k][0], a[j][0], b[j][0], b[k][0]))
    for (P, sm), polys in groups.items():
        M.add(P, polys, sm)
    if caps:
        for R in (rings[0], rings[-1]):
            ring = [q[0] for q in R]
            M.add(cap_pal if cap_pal is not None else pal("cap", R[0][0][1]), fan(ring, centroid(ring)))


def prism(element, poly, h0, h1, ch, pal, side=None, new_piece=True):
    """Chamfered prism: vertical walls h0..h1-ch, 45-degree chamfer ch, flat top; poly convex (c, r)."""
    if new_piece:
        M.piece(element)
    r0 = [(p[0], p[1], h0) for p in poly]
    r1 = [(p[0], p[1], h1 - ch) for p in poly]
    r2 = [(p[0], p[1], h1) for p in inset(poly, ch)]
    M.add(pal, [tuple(r2)])
    M.add(side if side is not None else pal, band(r0, r1) + (band(r1, r2) if ch > 0 else []) + [tuple(reversed(r0))])


def tube(element, O, axis, prof, pal, n=16, cap_a=True, cap_b=True, cap_pal_b=None, smooth=True, new_piece=True):
    if new_piece:
        M.piece(element)
    F = frame(axis)
    a = F[0]
    rings = [ring_at(vadd(O, a, q[0]), F, q[1], n) for q in prof]
    polys = []
    for i in range(len(rings) - 1):
        polys += band(rings[i], rings[i + 1])
    M.add(pal, polys, smooth)
    if cap_a:
        M.add(pal, fan(rings[0], centroid(rings[0])))
    if cap_b:
        M.add(cap_pal_b if cap_pal_b is not None else pal, fan(rings[-1], centroid(rings[-1])))
    return rings


# --- plan ----------------------------------------------------------------------------------------
LK = [(2.0, 6.6), (2.5, 6.05), (3.0, 5.55), (3.5, 5.0), (4.5, 4.25), (5.5, 3.75), (6.2, 3.12), (6.7, 3.0),
      (23.4, 3.0), (24.2, 3.35), (25.0, 4.1)]


def Lof(r):
    return pchip([k[0] for k in LK], [k[1] for k in LK], [r])[0]


HD, HS = 4.6, 2.6                        # deck height, belly start
# Mount height: the module rides the tracked carrier (types 546-549, assembly-newshs-165, linked to
# it by link 45 and moving with it rigidly), right over the carrier's ball turret (ball centre
# h 10.2, radius 6.3, top h 16.5; deck h 8). Its belly starts Z0 px up so the ball is inside the
# module's turret ring and nothing of it shows through the rack.
Z0 = 10.0


def faceH(r):
    """Height of the rack's sloped launch face (32 degrees) at row r."""
    return 7.4 if r < 16.4 else 7.4 - 5.4 * (r - 16.4) / 8.6


_l = math.hypot(5.4, 8.6)
NRM = (0.0, 5.4 / _l, 8.6 / _l)          # face normal (c, r, h): south and up


def mirror_polys(polys):
    return [tuple((2 * MID - p[0], p[1], p[2]) for p in reversed(q)) for q in polys]


def build_hull():
    rs = frange(2.0, 25.0, 0.25)
    deck_k = [15.5, 20.0, 24.6]
    deck_v = [HD, 3.4, 2.1]

    def deck(r):
        if r < 15.5:
            return HD
        if r > 24.6:
            return 2.1
        return pchip(deck_k, deck_v, [r])[0]

    st = [{"r": r, "L": Lof(r), "hd": deck(r)} for r in rs]
    KB, q = 16, 2.4

    def sec(s):
        L = s["L"]
        R = 2 * MID - L
        ch, half, I = 0.35, (R - L) / 2, 0.3
        hs = min(HS, s["hd"] - 0.6)
        pts = [(L + I, s["hd"] - ch, "chamfer"), (L + I + ch, s["hd"], "deck"), (R - I - ch, s["hd"], "chamfer"),
               (R - I, s["hd"] - ch, "wall"), (R - I, hs + 0.5, "rub"), (R, hs + 0.3, "rub"), (R, hs, "belly")]
        for k in range(1, KB):
            t = k / KB * math.pi
            co, si = math.cos(t), math.sin(t)
            pts.append((MID + half * math.copysign(abs(co) ** (2 / q), co), hs - hs * abs(si) ** (2 / q) * 0.98, "belly"))
        pts += [(L, hs, "rub"), (L, hs + 0.3, "rub"), (L + I, hs + 0.5, "wall")]
        return pts

    loft_r("hull", st, sec, lambda tag, r: {"deck": 3, "chamfer": 6, "wall": 6, "rub": 4, "belly": 5}.get(tag, 6),
           smooth=lambda tag: tag == "belly")


def build_west():
    """The west half (mirrored after): housings, groove, ridge, vent, rack cheek, rear nozzle, louvres."""
    start = len(M.pieces)

    def housing(r0, r1, ht1, rear_round):
        if rear_round:
            keys = [{"r": r0, "ht": 6.1}, {"r": r0 + 0.5, "ht": 6.75}, {"r": r0 + 1.0, "ht": 7.0}]
        else:
            keys = [{"r": r0, "ht": 6.6}, {"r": r0 + 0.35, "ht": 7.0}]
        keys += [{"r": r1 - 0.6, "ht": 7.0}, {"r": r1, "ht": ht1}]
        st = stations(keys, frange(r0, r1, 0.25))
        for s in st:
            s["L"] = Lof(s["r"])
        loft_r("housing", st, lambda s: [(s["L"], 3.8, "wall_outer"), (s["L"], s["ht"] - 0.6, "chamfer_outer"),
                                         (s["L"] + 0.6, s["ht"], "top"), (8.6, s["ht"], "chamfer_inner"),
                                         (9.0, s["ht"] - 0.4, "wall_inner"), (9.0, 3.8, "bottom")],
               lambda tag, r: {"top": 9, "chamfer_outer": 8, "chamfer_inner": 8, "wall_outer": 7,
                               "wall_inner": 5, "bottom": 5}.get(tag, 8))

    housing(2.0, 6.95, 6.7, True)
    housing(7.9, 16.0, 6.2, False)
    prism("groove", rect(3.05, 6.9, 9.0, 7.95), 3.8, 5.8, 0.0, 6)
    # Ridge across the housing at rows 12-13 (the sprite's bright 13 row over a darker 8 row).
    prism("ridge", rect(4.2, 12.6, 8.55, 13.6), 6.6, 7.25, 0.18, 9, side=8)
    # Vent at c 8, rows 8.4-10.9: a recessed dark well with four louvre slats.
    prism("vent", rect(7.75, 8.3, 8.85, 11.0), 6.5, 7.04, 0.0, 3)
    for i in range(4):
        prism("vent_louvre", rect(7.8, 8.6 + i * 0.6, 8.8, 8.85 + i * 0.6), 6.8, 7.1, 0.0, 6)
    # Bolt heads on the housing tops (machined detail; small, in the housing's own grey).
    for c, r in ((4.4, 3.9), (4.4, 9.0), (4.4, 15.2), (7.6, 15.2)):
        tube("bolt", (c, r, 6.9), (0, 0, 1), [(0, 0.28), (0.25, 0.28), (0.32, 0.18)], 8, n=8, cap_a=False)
    # Rack cheek plate (rows 16-24, c 3-4.6): the rack's side frame, proud of the face.
    st = [{"r": r, "L": Lof(r), "f": max(faceH(r), 2.2)} for r in frange(16.0, 24.9, 0.25)]
    loft_r("rack_cheek", st, lambda s: [(s["L"], 1.6, "wall_outer"), (s["L"], s["f"] + 0.15, "chamfer"),
                                        (s["L"] + 0.35, s["f"] + 0.5, "top"), (s["L"] + 1.6, s["f"] + 0.5, "wall_inner"),
                                        (s["L"] + 1.6, 1.6, "bottom")],
           lambda tag, r: {"top": 8, "chamfer": 8, "wall_outer": 7, "wall_inner": 6, "bottom": 5}.get(tag, 7))
    # Louvre slats on the rack cheek: crisp machined detail on its top face and outer wall.
    M.piece("cheek_louvre")
    for k in range(5):
        r = 17.1 + k * 1.15
        prism("cheek_louvre", rect(3.45, r, 4.45, r + 0.45), faceH(r + 0.2) + 0.2, faceH(r + 0.2) + 0.75, 0.08, 6,
              side=9, new_piece=False)
    for k in range(5):
        r = 17.3 + k * 1.2
        prism("cheek_louvre", rect(2.88, r, 3.0, r + 0.55), 2.1, min(faceH(r) - 0.3, 4.6), 0.0, 3, new_piece=False)
        prism("cheek_louvre", rect(2.85, r + 0.12, 3.03, r + 0.28), 2.3, min(faceH(r) - 0.5, 4.4), 0.0, 6,
              new_piece=False)
    # Panel seams on the housing's outer wall (access panels over the side magazine).
    M.piece("wall_seam")
    for r in (10.4, 13.9):
        prism("wall_seam", rect(2.93, r, 3.02, r + 0.16), 4.0, 6.25, 0.0, 5, new_piece=False)
    prism("wall_seam", rect(2.93, 8.1, 3.02, 15.8), 5.05, 5.2, 0.0, 5, new_piece=False)
    # Side intake louvres on the hull wall, between the rub strip and the deck.
    M.piece("side_intake")
    for i in range(4):
        prism("side_intake", rect(2.85, 9.0 + i * 1.1, 3.05, 9.7 + i * 1.1), 2.9, 4.0, 0.0, 3, new_piece=False)
    end = len(M.pieces)
    for i in range(start, end):
        el, groups = M.pieces[i]
        M.pieces.append((el + "_E", [(p, sm, mirror_polys(polys)) for p, sm, polys in groups]))


SPINE_SEAMS = (5.7, 11.3)   # panel seams between the magazine segments (narrow notches)


def build_spine():
    """Raised, segmented capsule: rounded two-step shoulders, a chamfered rear end, two notched seams
    between segments and a nose sloping down onto the rack."""
    ht = lambda r: pchip([2.0, 11.0, 13.5, 16.0], [8.5, 8.5, 7.7, 7.2], [r])[0]  # noqa: E731
    rs = [2.0, 2.2, 2.5] + frange(2.75, 16.0, 0.45)
    for g in SPINE_SEAMS:
        rs += [g - 0.16, g, g + 0.16]
    rs = sorted({round(r, 3) for r in rs if not any(0 < abs(r - g) < 0.16 for g in SPINE_SEAMS)})
    st = [{"r": r, "ht": ht(r)} for r in rs]

    def section(s):
        r = s["r"]
        g = max(0.0, 2.5 - r)
        for sm in SPINE_SEAMS:
            if abs(r - sm) < 0.16:
                g = max(g, 0.28 * (1 - abs(r - sm) / 0.16))
        xl, xr, zt = 10.0 + g, 15.0 - g, s["ht"] - g
        return [(xl, 3.8, "wall"), (xl, zt - 1.0, "wall"), (xl + 0.18, zt - 0.45, "chamfer"),
                (xl + 0.55, zt - 0.08, "chamfer"), (xl + 1.0, zt, "top"), (xr - 1.0, zt, "chamfer"),
                (xr - 0.55, zt - 0.08, "chamfer"), (xr - 0.18, zt - 0.45, "chamfer"), (xr, zt - 1.0, "wall"),
                (xr, 3.8, "bottom")]

    loft_r("spine", st, section,
           lambda tag, r: 70 if tag == "top" else 72 if tag == "chamfer" else 71 if tag == "cap" else 70)
    # Seam across the spine roof at row 6.5 (a modelled panel line between magazine roof plates).
    prism("spine_seam", rect(10.6, 8.0, 14.4, 8.3), 8.2, 8.6, 0.0, 70, side=70)
    # Reload hatch (rows 12-15, the sprite's lighter 71-73) with two hinge knuckles at its rear.
    prism("spine_hatch", rect(11.15, 11.9, 13.85, 14.4), 8.0, 8.1, 0.1, 71, side=72)
    for c in (11.5, 13.5):
        tube("hinge", (c, 11.55, 8.0), (0, 1, 0), [(0, 0.24), (0.7, 0.24)], 72, n=8)


def build_rack():
    st = [{"r": r, "L": Lof(r) + 1.6, "f": max(faceH(r), 2.2)} for r in frange(16.0, 24.9, 0.25)]
    loft_r("rack", st, lambda s: [(s["L"], 1.6, "wall"), (s["L"], s["f"], "face"), (2 * MID - s["L"], s["f"], "wall"),
                                  (2 * MID - s["L"], 1.6, "bottom")],
           lambda tag, r: (7 if r < 16.5 else 6) if tag == "face" else 5 if tag == "bottom" else 6)
    # Cross rib at row 20.4 between the two tube rows (the sprite's lighter band, 7-11).
    r0, r1 = 20.15, 20.75
    M.piece("rack_rib")
    lo = [(4.6, r0, faceH(r0) - 0.2), (20.4, r0, faceH(r0) - 0.2), (20.4, r1, faceH(r1) - 0.2), (4.6, r1, faceH(r1) - 0.2)]
    up = 0.32
    hi = [vadd(p, NRM, up) for p in lo]
    M.add(7, [tuple(hi)] + band(lo, hi) + [tuple(reversed(lo))])
    tubes = [(6.5, 18.5), (10.5, 18.5), (14.5, 18.5), (18.5, 18.5), (8.5, 22.5), (12.5, 22.5), (16.5, 22.5)]
    F = frame(NRM)
    for c, rtop in tubes:
        rb = rtop - NRM[1] * 1.1
        base = (c, rb, faceH(rb))
        O = vadd(base, NRM, -3.0)
        M.piece("launch_tube")
        # Barrel with a reinforcing band, then a flared muzzle collar.
        tube("launch_tube", O, NRM, [(0, 1.3), (3.0, 1.3), (3.05, 1.45), (3.3, 1.45), (3.35, 1.3), (3.75, 1.3),
                                             (3.8, 1.55), (4.1, 1.55)], 5, n=18, cap_a=True, cap_b=False, new_piece=False)
        top = vadd(base, NRM, 1.1)
        outer = ring_at(top, F, 1.55, 18)
        inner = ring_at(top, F, 1.22, 18)
        M.add(4, band(outer, inner))
        step = vadd(top, NRM, -0.35)
        inner_step = ring_at(step, F, 1.22, 18)
        ring_in = ring_at(step, F, 1.08, 18)
        deep = vadd(top, NRM, -1.6)
        inner_deep = ring_at(deep, F, 1.08, 18)
        M.add(1, band(inner, inner_step) + band(ring_in, inner_deep) + fan(inner_deep, deep), smooth=True)
        M.add(5, band(inner_step, ring_in))  # the bore's inner ring (step)
        # loaded missile: a small ogive tip (pal 2) at the bottom of the bore
        tip = [ring_at(vadd(deep, NRM, h), F, rr, 12) for h, rr in ((0.0, 0.62), (0.4, 0.58), (0.75, 0.36))]
        M.add(2, band(tip[0], tip[1]) + band(tip[1], tip[2]) + fan(tip[2], vadd(deep, NRM, 0.95)), smooth=True)


def build_mount():
    """The turret ring the module stands on: a collar from the carrier's deck up into the belly,
    with a bearing lip and a foot flange (it hides the carrier's ball turret, which the sprite
    covers too)."""
    M.piece("mount")
    c, r = MID, 16.6
    F = frame((0, 0, 1))
    R = [ring_at((c, r, h), F, rad, 40) for h, rad in ((-Z0 + 7.2, 7.5), (-Z0 + 7.9, 7.5), (-Z0 + 8.1, 7.0),
                                                       (-0.6, 7.0), (-0.6, 7.35), (-0.25, 7.35), (-0.25, 6.6), (0.9, 6.6))]
    M.add(6, band(R[0], R[1]) + band(R[1], R[2]) + fan(R[0], centroid(R[0])), smooth=True)
    M.add(5, band(R[2], R[3]), smooth=True)
    M.add(7, band(R[3], R[4]) + band(R[4], R[5]) + band(R[5], R[6]), smooth=True)
    M.add(5, band(R[6], R[7]) + fan(R[7], centroid(R[7])), smooth=True)
    # bolt heads round the foot flange
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        tube("mount_bolt", (c + 7.15 * math.cos(a), r + 7.15 * math.sin(a), -Z0 + 7.9), (0, 0, 1),
             [(0, 0.25), (0.22, 0.25)], 7, n=6, cap_a=False)


def build():
    build_mount()
    build_hull()
    build_west()
    build_spine()
    build_rack()


# --- Blender ----------------------------------------------------------------------------------------

def to_blender(sprite, coll):
    pals = sorted({p for _, groups in M.pieces for p, _, _ in groups})
    mats, slot = [], {}
    for p in pals:
        if p == 1:
            kw = dict(metallic=0.2, roughness=0.8)
        elif p == 2:
            kw = dict(metallic=0.3, roughness=0.7)
        elif p >= 70:
            kw = dict(metallic=0.3, roughness=0.45)
        elif p <= 5:
            kw = dict(metallic=0.4, roughness=0.6)
        else:
            kw = dict(metallic=0.45, roughness=0.5)
        slot[p] = len(mats)
        mats.append(common.palette_material(sprite, p, NAME, **kw))
    bm = bmesh.new()
    smooth_faces = []
    for el, groups in M.pieces:
        piece = bmesh.new()
        vmap = {}

        def V(p):
            key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
            v = vmap.get(key)
            if v is None:
                v = vmap[key] = piece.verts.new(key)
            return v
        for p, sm, polys in groups:
            for poly in polys:
                vs = []
                for q in poly:
                    v = V(q)
                    if v not in vs:
                        vs.append(v)
                if len(vs) < 3:
                    continue
                try:
                    f = piece.faces.new(vs)
                except ValueError:
                    continue
                f.material_index = slot[p]
                f.smooth = sm
        bmesh.ops.recalc_face_normals(piece, faces=piece.faces)
        me = bpy.data.meshes.new("tmp")
        piece.to_mesh(me)
        piece.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    # Sprite px (c, r, h) to Blender: X = (c - 12) / 12, Y = (14 - r) / 12, Z = h / 12 (a mirror in r).
    m = Matrix(((1 / 12, 0, 0, -1.0), (0, -1 / 12, 0, 14 / 12), (0, 0, 1 / 12, Z0 / 12), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # Hard surfaces flat-edged; round parts (belly, tubes) smooth inside their angle.
    me.set_sharp_from_angle(angle=math.radians(32))
    return obj


def main():
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    build()
    body = to_blender(sprite, coll)
    shell = common.outline_shell(body, coll, faces=3000, inside=0.003)
    common.export_sprite_model(ROOT, [body, shell], f"enemies/{NAME}", sprite["sprites"])
    tris = sum(len(p.vertices) - 2 for p in body.data.polygons)
    print(f"built {NAME}: {tris} tris (+ shell {sum(len(p.vertices) - 2 for p in shell.data.polygons)})")
    if "--preview" in sys.argv:
        out = sys.argv[sys.argv.index("--preview") + 1]
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([body, shell], out, ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
