"""Purple shield craft (newsh2.shp frame 127, 24 x 28 px, enemy type 31): a hard-surface machine
that is its sprite in 3D, built the way the player ships are (usp_talon.py, ships/*.py, D50-D53).

Seen in episode 1 (levels 1.25, 1.28, 1.3, 1.36) and episode 3. The sprite is authoritative (D52):
the top view follows its mask row by row (a pchip plan sampled back to the mask), the canopy / rear
glass / ports / nose block sit where its pixels are, and every part takes the sprite's own palette
index for its region (the median, dark shading and sheen pixels left out). The concept
(features/concepts/newsh2-127.jpg) only guides the side, front and rear design and the detail.

Layout (sprite px: x = column edge - 12.5 (the sprite's axis), y = row edge (aft 0 -> nose 28), z up;
finish() maps X = (x + 0.5) / 12 (the game centres the model on the 24 px frame, edge 12),
Y = (14 - y) / 12, Z = z / 12):
- core hull: one pchip loft of faceted sections in the sprite's plan, a dark rubbing strake along
  its widest line, a closed plain belly (no detail underneath, by design);
- two heavy pauldron plates over the back corners, rolling down over the flanks, a dark seam in
  front of them; a framed cyan glass housing between them at the back edge;
- a channel with the twin-rod yoke to the cockpit: a dark frame round a faceted blue glass canopy
  with a grey bar across it;
- light cheek plates curving in to the pale keel plate; flank armour with three deep turbine
  ports a side;
- a dark chin slot, a purple lip and the teal nose gun block with twin barrels;
- two deep engine nozzles under the rear housing (named in the extras `tyrian_engines`).

Texture: no concept projection (its maps.json says "bake": "model", as the player ships, D50): an
ambient occlusion / roughness bake only (usp_talon.bake_maps), Base Color = map x palette colour, so
pal_<index>, fades and the hit flash still apply. An outline shell (common.outline_shell, D51) is
made from the closed parts. One frame, one model.

Run: blender --background --factory-startup --python assets/blender/enemies/newsh2-127.py
     [-- --preview out.png] [--no-bake] [--out x.glb]
"""

import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.geometry import delaunay_2d_cdt

BLENDER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BLENDER_DIR))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
from usp_talon import Part, cbox, frange, hull, pchip  # noqa: E402

NAME = "newsh2-127"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12

# --- materials ---------------------------------------------------------------------------------
(FLANK, SHOULDER, CHEEK, KEEL, SEAM, RFRAME, RGLASS, MULL, YOKE, GAP, CHAN, CPF, GLASS, BAR, SLOT,
 LIP, NCHAMF, NOSE, NSIDE, VENT, PRIM, WELL, FAN, BARREL, BELT, GLOW, WALL, BOLT, NOZ) = range(29)
PAL_OF = {FLANK: 83, SHOULDER: 84, CHEEK: 87, KEEL: 89, SEAM: 82, RFRAME: 84, RGLASS: 59, MULL: 128,
          YOKE: 89, GAP: 82, CHAN: 85, CPF: 83, GLASS: 58, BAR: 102, SLOT: 80, LIP: 87, NCHAMF: 131,
          NOSE: 53, NSIDE: 54, VENT: 101, PRIM: 82, WELL: 1, FAN: 81, BARREL: 101, BELT: 82, GLOW: 136,
          WALL: 82, BOLT: 81, NOZ: 82}
# (metallic, roughness, emission): satin metal, not mirror (D52/D53).
LOOK = {FLANK: (0.3, 0.46), SHOULDER: (0.35, 0.4), CHEEK: (0.35, 0.38), KEEL: (0.38, 0.36),
        SEAM: (0.2, 0.6), RFRAME: (0.35, 0.4), RGLASS: (0.0, 0.08, 0.3), MULL: (0.4, 0.35),
        YOKE: (0.55, 0.3), GAP: (0.2, 0.6), CHAN: (0.3, 0.45), CPF: (0.35, 0.42), GLASS: (0.0, 0.06, 0.25),
        BAR: (0.5, 0.32), SLOT: (0.1, 0.7), LIP: (0.35, 0.38), NCHAMF: (0.35, 0.35), NOSE: (0.35, 0.42),
        NSIDE: (0.35, 0.42), VENT: (0.4, 0.45), PRIM: (0.4, 0.4), WELL: (0.1, 0.8), FAN: (0.4, 0.5),
        BARREL: (0.55, 0.32), BELT: (0.3, 0.5), GLOW: (0.0, 0.3, 2.0), WALL: (0.25, 0.55),
        BOLT: (0.5, 0.35), NOZ: (0.45, 0.4)}
TAGS = ["hull", "shoulder", "cheek", "keel", "seam", "rframe", "rglass", "mullion", "yoke", "gap",
        "channel", "cpframe", "glass", "bar", "slot", "lip", "nchamfer", "nose", "nside", "vent",
        "portrim", "well", "fan", "barrel", "belt", "glow", "wall", "bolt", "nozzle"]
TEXTURED = tuple(i for i in range(29) if i not in (RGLASS, GLASS, GLOW))
TINT = (1.0, 0.98, 0.95)


def materials(sprite):
    mats = []
    for i, tag in enumerate(TAGS):
        lk = LOOK[i]
        mats.append(common.palette_material(sprite, PAL_OF[i], f"n127_{tag}", metallic=lk[0], roughness=lk[1],
                                            emission_strength=lk[2] if len(lk) > 2 else 0.0))
    return mats


# --- plan, deck and belly (sprite px) ----------------------------------------------------------
# Plan half width by row edge: the blueprint's fit to the sprite mask (its black outline ring
# included): a rounded 45-degree shoulder at the back, straight sides r5-12.6, a straight taper of
# 1 px every 2 rows r14-26 (the sprite's staircase through its step midpoints), a rounded nose.
PLAN = pchip([0.75, 1.5, 2.5, 3.5, 4.4, 5.0, 12.6, 13.4, 14.0, 20.0, 26.0, 27.0, 27.6, 28.0],
             [7.6, 8.6, 9.6, 10.6, 11.32, 11.5, 11.5, 11.38, 11.0, 8.0, 5.0, 4.15, 3.45, 2.6])
Y0, Y1 = 0.75, 28.0
DECK = pchip([0.75, 4.0, 14.0, 22.0, 28.0], [2.6, 3.0, 3.0, 2.6, 1.5])
BELLY = pchip([0.75, 2.5, 6.0, 14.0, 22.0, 28.0], [-1.9, -2.4, -2.8, -3.0, -2.4, -0.9])
# The strake stands proud of the core along the widest line from r 3.5 to 23; the core is that
# much narrower there so the strake's outer face is the plan.
BELTK = pchip([0.75, 3.0, 4.5, 21.5, 23.5, 28.0], [0.0, 0.0, 1.0, 1.0, 0.0, 0.0])
BELT_W = 0.32
WAIST = 0.45  # z of the widest line
# Faceted hard-surface section: (u = fraction of the half width, f = fraction of the height above /
# below the waist). A flat deck, a shallow shoulder chamfer, a steep flank, a short chine.
TOPF = [(0.0, 1.0), (0.55, 1.0), (0.86, 0.62), (0.975, 0.25), (1.0, 0.0)]
BOTF = [(1.0, 0.0), (0.965, 0.32), (0.8, 0.82), (0.45, 1.0), (0.0, 1.0)]
CREASE_U = (0.55, 0.86, 0.975)


def WC(y):
    return PLAN(y) - BELT_W * BELTK(y)


U_TOP = [u for u, _ in TOPF]
U_BOT = [u for u, _ in BOTF[1:]]


def _lerp(tab, u):
    u = min(1.0, max(0.0, u))
    for (u0, f0), (u1, f1) in zip(tab, tab[1:]):
        lo, hi = min(u0, u1), max(u0, u1)
        if lo <= u <= hi:
            return f0 + (f1 - f0) * (u - u0) / (u1 - u0)
    return tab[-1][1]


def zt(u, d):
    return WAIST + (d - WAIST) * _lerp(TOPF, u)


def zb(u, b):
    return WAIST - (WAIST - b) * _lerp(BOTF, u)


def hull_creases():
    return [[(s * u * WC(y), y) for y in frange(Y0, Y1, 0.35)] for u in CREASE_U for s in (-1, 1)]


def core_loop(y):
    w, d, b = WC(y), DECK(y), BELLY(y)
    right = [(u * w, zt(u, d)) for u in U_TOP] + [(u * w, zb(u, b)) for u in U_BOT]
    left = [(-x, z) for x, z in right[1:-1]][::-1]
    pts = right + left
    return pts, (0.0, (d + b) / 2)


def hull_top(x, y):
    """Height of the core hull's top surface at (x, y)."""
    yy = min(Y1, max(Y0, y))
    w = WC(yy)
    u = abs(x) / w
    if u >= 1.0:
        return WAIST - (u - 1.0) * w * 3.0
    return zt(u, DECK(yy))


def surf_normal(f, x, y, h=0.05):
    dx = (f(x + h, y) - f(x - h, y)) / (2 * h)
    dy = (f(x, y + h) - f(x, y - h)) / (2 * h)
    return Vector((-dx, -dy, 1.0)).normalized()


# --- 2D polygon helpers ------------------------------------------------------------------------

def area(poly):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1])) / 2


def ccw(poly):
    return poly if area(poly) > 0 else poly[::-1]


def resample(poly, step):
    out = []
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        k = max(1, math.ceil(math.hypot(bx - ax, by - ay) / step - 1e-9))
        for j in range(k):
            t = j / k
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t))
    return out


def offset_poly(poly, d):
    """Offset a CCW polygon inwards by d (miter, clamped)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0), (p2 - p1)
        e0 = e0.normalized() if e0.length > 1e-9 else e1.normalized()
        e1 = e1.normalized() if e1.length > 1e-9 else e0
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        m = n0 + n1
        m = m.normalized() if m.length > 1e-9 else n1
        cosh = max(0.45, m.dot(n1))
        q = p1 + m * (d / cosh)
        out.append((q.x, q.y))
    return out


def inside(p, poly):
    x, y = p
    c = False
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def edge_dist(p, poly):
    px_, py_ = p
    best = 1e9
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px_ - x0) * dx + (py_ - y0) * dy) / L2))
        best = min(best, math.hypot(px_ - x0 - t * dx, py_ - y0 - t * dy))
    return best


def mirror(poly):
    return [(-x, y) for x, y in poly][::-1]


def spline(pts, n=6):
    """A smooth curve through pts (Catmull-Rom), n samples per span, ends kept."""
    out = []
    P = [Vector(p) for p in pts]
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for j in range(n):
            t = j / n
            t2, t3 = t * t, t * t * t
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((q.x, q.y))
    out.append(tuple(P[-1]))
    return out


# --- solid builders ------------------------------------------------------------------------------

def slab(P, outline, ztop, c, mt, mc=None, mw=None, zbase=None, depth=0.5, spacing=0.75, step=0.55,
         ck=0.85, bottom=False, creases=None):
    """A plate over `outline` (x, y): a top surface z = ztop(x, y) (triangulated over interior
    points, so it can curve), a 45-degree chamfer `c` wide round its edge and a wall down to
    zbase(x, y) (default: `depth` under the core hull's top, buried). Panel lines are the gaps
    between plates."""
    mc = mt if mc is None else mc
    mw = mc if mw is None else mw
    if zbase is None:
        zbase = lambda x, y: hull_top(x, y) - depth  # noqa: E731
    poly = ccw(resample(ccw(outline), step))
    inner = offset_poly(poly, c) if c > 0 else list(poly)
    n = len(inner)
    xs = [p[0] for p in inner]
    ys = [p[1] for p in inner]
    pts = []
    row = 0
    yy = min(ys) + spacing * 0.5
    while yy < max(ys):
        xx = min(xs) + spacing * (0.25 if row % 2 else 0.75)
        while xx < max(xs):
            if inside((xx, yy), inner) and edge_dist((xx, yy), inner) > spacing * 0.45:
                pts.append((xx, yy))
            xx += spacing
        yy += spacing * 0.866
        row += 1
    cpts, cedges = [], []
    for line in creases or []:
        prev = None
        for p in line:
            if inside(p, inner) and edge_dist(p, inner) > 0.12:
                cpts.append(p)
                if prev is not None:
                    cedges.append((n + len(cpts) - 2, n + len(cpts) - 1))
                prev = p
            else:
                prev = None
    if cpts:
        pts = [p for p in pts if min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in cpts) > spacing * 0.4]
    coords = [Vector(p) for p in inner + cpts + pts]
    res = delaunay_2d_cdt(coords, [(i, (i + 1) % n) for i in range(n)] + cedges, [list(range(n))], 1, 1e-7)
    vco, _, faces, orig = res[0], res[1], res[2], res[3]
    tv = [P.v((v.x, v.y, ztop(v.x, v.y))) for v in vco]
    ring = [None] * n
    for k, o in enumerate(orig):
        for j in o:
            if j < n:
                ring[j] = tv[k]
    for f in faces:
        P.f([tv[i] for i in f], mt, out=(0, 0, 1))
    if any(r is None for r in ring):
        raise ValueError("slab: ring vertex lost in triangulation")
    outer = [P.v((x, y, ztop(x, y) - c * ck)) for x, y in poly] if c > 0 else ring
    base = [P.v((x, y, zbase(x, y))) for x, y in poly]
    for i in range(n):
        j = (i + 1) % n
        (x0, y0), (x1, y1) = poly[i], poly[j]
        ln = math.hypot(x1 - x0, y1 - y0) or 1e-9
        ox, oy = (y1 - y0) / ln, -(x1 - x0) / ln
        if c > 0:
            P.f((ring[i], ring[j], outer[j], outer[i]), mc, out=(ox, oy, 1.0))
        P.f((outer[i], outer[j], base[j], base[i]), mw, out=(ox, oy, 0.0))
    if bottom:
        P.f(base, mw, out=(0, 0, -1))
    return poly


def frame_at(cx, cy, cz, n):
    n = Vector(n).normalized()
    a = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
    t1 = (a - n * a.dot(n)).normalized()
    t2 = n.cross(t1)
    return Vector((cx, cy, cz)), t1, t2, n


def lathe(P, origin, t1, t2, n, prof, mats, seg=16, phase=0.0):
    """Revolve prof [(radius, height)] round axis n at origin; mats[i] between point i and i+1.
    The profile runs with the solid on its right: outward = (dh, -dr)."""
    rings = []
    for r, h in prof:
        if r < 1e-6:
            rings.append([P.v(tuple(origin + n * h))] * seg)
        else:
            rings.append([P.v(tuple(origin + (t1 * math.cos(2 * math.pi * (k + phase) / seg)
                                              + t2 * math.sin(2 * math.pi * (k + phase) / seg)) * r + n * h))
                          for k in range(seg)])
    for i in range(len(prof) - 1):
        (r0, h0), (r1, h1) = prof[i], prof[i + 1]
        dr, dh = r1 - r0, h1 - h0
        for k in range(seg):
            j = (k + 1) % seg
            a = 2 * math.pi * (k + 0.5 + phase) / seg
            rad = t1 * math.cos(a) + t2 * math.sin(a)
            out = rad * dh - n * dr
            if out.length < 1e-9:
                out = n
            vs = [rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]]
            uniq = []
            for v in vs:
                if v not in uniq:
                    uniq.append(v)
            P.f(uniq, mats[i], out=tuple(out))


def tube(P, a, b, r, mat, seg=10, caps=True):
    a, b = Vector(a), Vector(b)
    n = (b - a).normalized()
    o, t1, t2, _ = frame_at(*a, n)
    L = (b - a).length
    lathe(P, a, t1, t2, n, [(0, 0), (r, 0), (r, L), (0, L)] if caps else [(r, 0), (r, L)],
          [mat] * 3, seg=seg)


def box(P, x0, x1, y0, y1, z0, z1, ch, mat, chz=None):
    hull(P, cbox(x0, x1, y0, y1, z0, z1, ch, chz), mat)


# --- the craft ---------------------------------------------------------------------------------

def shoulder_front(ax):
    """Row of the shoulder plate's front edge at |x| (curving down the flank, as the sprite's seam)."""
    return pchip([4.6, 6.0, 8.0, 9.6, 10.7, 11.6], [6.3, 6.4, 6.75, 7.25, 8.0, 8.8])(ax)


SH_IN = 4.65  # shoulder inner edge |x|
HOUSING = 4.4  # rear housing half width


def shoulder_top(x, y):
    """The pauldron follows the hull's facets 2.75 px proud, its outer rim held at the facets'
    u = 0.93 height so it overhangs the flank instead of crumpling down the chine."""
    yy = min(Y1, max(Y0, y))
    u = min(0.975, abs(x) / WC(yy))
    return zt(u, DECK(yy)) + 2.75 - 1.5 * max(0.0, (u - SH_ROLL) / (1.0 - SH_ROLL))


SH_ROLL = 0.72  # where the pauldron starts to thin and roll down over the flank


def shoulder_creases():
    return hull_creases() + [[(s * u * WC(y), y) for y in frange(Y0, 12.0, 0.35)] for u in (SH_ROLL,)
                             for s in (-1, 1)]


def build_hull(P):
    ys = sorted(set([0.75, 1.0, 1.3, 1.7, 2.1, 2.6, 3.1, 3.6, 4.1, 4.6] + frange(5.2, 24.4, 1.45)
                    + [25.0, 25.6, 26.2, 26.7, 27.1, 27.45, 27.75, 28.0]))
    T.loft(P, core_loop, ys, FLANK)


def build_belt(P):
    """The rubbing strake along the widest line (r 3.6-23.2): a chamfered box section whose outer
    face is the plan."""
    ys = frange(3.6, 23.2, 1.1)

    def loop(side):
        def f(y):
            k = BELTK(y)
            xo = PLAN(y) - 0.02
            xi = xo - max(0.05, BELT_W * k) - 0.25
            hh = 0.18 + 0.32 * k
            ch = min(0.12, hh * 0.4)
            pts = [(xi, WAIST - hh), (xo - ch, WAIST - hh), (xo, WAIST - hh + ch), (xo, WAIST + hh - ch),
                   (xo - ch, WAIST + hh), (xi, WAIST + hh)]
            pts = [(side * x, z) for x, z in pts]
            if side < 0:
                pts = pts[::-1]
            return pts, (side * (xi + xo) / 2, WAIST)
        return f
    for s in (-1, 1):
        T.loft(P, loop(s), ys, BELT)


def build_shoulders(P, D):
    for s in (-1, 1):
        # Outline: inner edge at the housing, round the back corner along the plan, the front
        # edge curving down the flank.
        back = [(-SH_IN, 0.82), (-7.45, 0.82)]
        rim = [(-(PLAN(y) - 0.04), y) for y in frange(0.85, shoulder_front(11.46) - 0.05, 0.4)]
        front = [(-ax, shoulder_front(ax)) for ax in frange(SH_IN, PLAN(8.7) - 0.05, 0.5)][::-1]
        out = back + rim + front
        if s > 0:
            out = mirror(out)
        slab(P, out, shoulder_top, 0.32, SHOULDER, SHOULDER, WALL, step=0.7, spacing=0.95, creases=shoulder_creases())
        # Its raised upper tier (the concept's stepped armour), a gap's width inside the edge.
        tier = ([(-5.7, y) for y in frange(1.75, shoulder_front(5.7) - 0.95, 0.7)]
                + [(-ax, shoulder_front(ax) - 0.95) for ax in frange(5.7, 9.2, 0.6)]
                + [(-(PLAN(y) - 1.35), y) for y in frange(shoulder_front(9.2) - 1.1, 1.95, -0.6)])
        if s > 0:
            tier = mirror(tier)
        slab(P, tier, lambda x, y: shoulder_top(x, y) + 0.28, 0.2, SHOULDER, SHOULDER, SHOULDER, step=0.7,
             spacing=0.95, creases=shoulder_creases(), zbase=lambda x, y: shoulder_top(x, y) - 0.3)
        # Seam: a dark recessed strip in front of the plate's front edge (the sprite's row 6-8 seam).
        seam_back = [(-ax, shoulder_front(ax) - 0.4) for ax in frange(3.85, PLAN(8.4) - 0.1, 0.5)]
        seam_front = [(-ax, shoulder_front(ax) + 0.95) for ax in frange(3.85, PLAN(9.4) - 0.1, 0.5)][::-1]
        so = seam_back + seam_front
        if s > 0:
            so = mirror(so)
        slab(P, so, lambda x, y: hull_top(x, y) + 0.12, 0.0, SEAM, SEAM, SEAM, spacing=1.0, step=0.8,
             creases=hull_creases())
        # Fasteners on the plate (concept): three hex bolts.
        for ax, y in ((6.1, 2.2), (8.6, 4.3), (6.0, 5.3)):
            x = s * ax
            z = shoulder_top(x, y)
            o, t1, t2, n = frame_at(x, y, z - 0.05, surf_normal(shoulder_top, x, y))
            lathe(D, o, t1, t2, n, [(0.3, -0.2), (0.3, 0.12), (0.2, 0.2), (0.0, 0.2)], [BOLT] * 3, seg=6)


def build_rear(P, D):
    # Housing block (frame 84) overhanging the hull's back edge, closed underneath.
    h = HOUSING
    slab(P, [(-h, 0.1), (h, 0.1), (h, 4.7), (-h, 4.7)], lambda x, y: 5.0, 0.35, RFRAME, RFRAME, RFRAME,
         zbase=lambda x, y: 0.95, bottom=True, spacing=1.0)
    # Raised frame rails round the glass (rows 0 and 4, cols 8 and 16).
    zr = 5.6
    for x0, x1, y0, y1 in ((-h + 0.1, h - 0.1, 0.18, 0.85), (-h + 0.1, h - 0.1, 3.85, 4.6),
                           (-h + 0.1, -3.45, 0.85, 3.85), (3.45, h - 0.1, 0.85, 3.85)):
        box(D, x0, x1, y0, y1, 4.7, zr, 0.12, RFRAME)
    # The cyan glass panel, just under the rails, and its two mullions (cols 10 and 14).
    box(D, -3.5, 3.5, 0.85, 3.85, 4.6, 5.38, 0.1, RGLASS)
    for c in (-2.0, 2.0):
        box(D, c - 0.33, c + 0.33, 0.85, 3.85, 4.8, 5.48, 0.08, MULL)
    # The glass wraps down the back face as a lamp strip (concept), seen from behind.
    box(D, -3.2, 3.2, 0.02, 0.2, 2.7, 4.5, 0.06, RGLASS)
    box(D, -3.7, 3.7, 0.0, 0.16, 2.35, 2.62, 0.05, RFRAME)
    # Engines: two deep nozzles in the hull's back wall under the housing overhang.
    for s in (-1, 1):
        o, t1, t2, n = frame_at(s * 3.55, 0.95, -0.55, (0, -1, 0))
        lathe(D, o, t1, t2, n,
              [(1.3, -0.6), (1.3, 0.4), (1.18, 0.55), (0.98, 0.55), (0.94, 0.35), (0.88, -1.2), (0.6, -1.25),
               (0.0, -1.25)],
              [NOZ, NOZ, NOZ, NOZ, WELL, WELL, GLOW], seg=16)
        lathe(D, o + n * (-0.6), t1, t2, n, [(0.55, 0.0), (0.12, 0.3), (0.0, 0.3)], [FAN, FAN], seg=8)
    # A vent grille in the back wall between the nozzles.
    for k in range(3):
        z = -1.15 + k * 0.62
        box(D, -1.7, 1.7, 0.55, 0.85, z, z + 0.3, 0.05, WELL)


def build_channel(P, D):
    # Floor between the shoulders, from the housing to the cockpit frame (85).
    slab(P, [(-3.95, 4.55), (3.95, 4.55), (3.95, 8.15), (-3.95, 8.15)], lambda x, y: 3.45, 0.2, CHAN,
         spacing=1.0)
    # The dark gap down the middle under the rods (col 12) and side tracks.
    box(D, -0.55, 0.55, 4.6, 8.05, 3.2, 3.62, 0.05, GAP)
    # Twin hydraulic rods (cols 11 and 13) from the housing to the cockpit, collars and clevises.
    for c in (-1.0, 1.0):
        tube(D, (c, 4.5, 4.35), (c, 8.4, 4.35), 0.46, YOKE, seg=10)
        tube(D, (c, 6.3, 4.35), (c, 6.9, 4.35), 0.56, BAR, seg=10)
        box(D, c - 0.55, c + 0.55, 4.55, 5.25, 3.35, 4.75, 0.12, CHAN)
        box(D, c - 0.55, c + 0.55, 7.7, 8.25, 3.35, 4.7, 0.12, CHAN)
    tube(D, (-1.75, 4.95, 4.3), (1.75, 4.95, 4.3), 0.22, BAR, seg=8)


def build_cockpit(P, D):
    # Dark frame (83): cols 9 / 15, rows 8 / 13.
    slab(P, [(-3.5, 8.05), (3.5, 8.05), (3.5, 13.0), (2.8, 14.0), (-2.8, 14.0), (-3.5, 13.0)],
         lambda x, y: 4.35, 0.35, CPF, CPF, WALL, spacing=0.9)
    # Faceted glass canopy (58): cols 10-14, rows 9-12, the highest point of the centre; its front
    # facet slopes to the nose (the sprite's bright row 12 is that facet's sheen).
    pts = []
    for x in (-2.5, 2.5):
        pts += [(x, 9.0, 3.9), (x, 13.05, 3.9)]
    for x in (-1.95, 1.95):
        pts += [(x, 9.15, 5.45), (x, 11.3, 5.6), (x, 12.95, 4.75)]
    for x in (-2.5, 2.5):
        pts += [(x, 9.0, 4.95), (x, 11.3, 5.05), (x, 13.05, 4.35)]
    hull(D, pts, GLASS)
    # The grey bar across the glass (row 10).
    box(D, -2.75, 2.75, 10.05, 10.95, 4.1, 5.82, 0.14, BAR)
    # The tab at the canopy's foot (row 13).
    box(D, -1.4, 1.4, 13.0, 13.85, 4.0, 4.62, 0.12, CPF)


def cheek_outline():
    inner = [(-3.75, 7.65), (-3.75, 13.9), (-3.38, 14.5), (-3.3, 17.0), (-3.6, 17.75)]
    outer = spline([(-3.6, 17.75), (-4.4, 17.45), (-5.3, 16.55), (-6.15, 15.45), (-6.65, 14.4),
                    (-6.95, 13.3), (-7.0, 12.0)], n=3)
    return inner + outer[1:] + [(-7.0, 7.9), (-6.7, 7.65)]


def cheek_top(x, y):
    return 4.12 - 0.06 * max(0.0, y - 12.5)


def build_cheeks(P, D):
    for s in (-1, 1):
        o = cheek_outline()
        slab(P, mirror(o) if s > 0 else o, cheek_top, 0.3, CHEEK, CHEEK, WALL, spacing=1.0, step=0.7)


def build_keel(P, D):
    o = [(-3.1, 14.15), (3.1, 14.15), (2.8, 19.95), (-2.8, 19.95)]
    slab(P, o, keel_top, 0.38, KEEL, KEEL, WALL, spacing=1.0)
    # A raised inner panel (machined layering, concept), a gap inside the edge.
    slab(D, [(-2.0, 15.0), (2.0, 15.0), (1.8, 18.9), (-1.8, 18.9)], lambda x, y: keel_top(x, y) + 0.2, 0.15,
         KEEL, KEEL, KEEL, zbase=lambda x, y: keel_top(x, y) - 0.3, spacing=1.2)


def keel_top(x, y):
    return 4.1 - 0.11 * (y - 14.15)


def flank_top(x, y):
    return hull_top(x, y) + 0.3


PORTS = [(8.3, 12.5, 0.8, 1.08), (7.35, 16.15, 0.72, 0.98), (4.15, 19.05, 0.62, 0.88)]


def build_flanks(P, D):
    for s in (-1, 1):
        # Upper flank plate (rows 7.6-14.6) between the cheek and the strake.
        edge = lambda y: -(WC(y) - 0.08)  # noqa: E731
        rear = [(-ax, shoulder_front(ax) + 0.95) for ax in frange(7.25, -edge(9.0) - 0.05, 0.5)]
        side = [(edge(y), y) for y in frange(rear[-1][1] + 0.2, 14.45, 0.6)]
        cheek_out = [p for p in spline([(-6.65, 14.4), (-6.95, 13.3), (-7.0, 12.0)], n=3)]
        up = [(-7.27, y) for y in frange(7.9, 12.0, 0.6)][::-1]
        o1 = rear + side + [(-6.95, 14.45)] + [(x - 0.27, y) for x, y in cheek_out[1:]] + up[1:]
        o1 = ccw(o1)
        # Lower flank plate (rows 14.75-21.8), round the cheek's curve to the keel.
        side2 = [(edge(y), y) for y in frange(14.75, 21.8, 0.6)]
        curve = spline([(-3.25, 17.95), (-4.4, 17.75), (-5.4, 16.85), (-6.3, 15.75), (-6.9, 14.75)], n=3)
        o2 = side2 + [(-3.6, 21.8), (-3.35, 20.2)] + [(-3.25, 18.3)] + curve
        for o in (o1, o2):
            slab(P, mirror(o) if s > 0 else o, flank_top, 0.22, FLANK, FLANK, WALL, spacing=1.15, step=0.75,
                 creases=hull_creases())
        # Turbine ports: a raised collar round a deep dark bore with a fan hub at its bottom.
        for ax, y, rb, R in PORTS:
            x = s * ax
            z = flank_top(x, y)
            o, t1, t2, n = frame_at(x, y, z, surf_normal(flank_top, x, y))
            lathe(D, o, t1, t2, n,
                  [(R + 0.08, -0.7), (R + 0.08, 0.18), (R - 0.12, 0.38), (rb + 0.12, 0.38), (rb, 0.22),
                   (rb, -0.75), (rb * 0.55, -0.75), (rb * 0.55, -0.55), (0.0, -0.45)],
                  [PRIM, PRIM, PRIM, PRIM, WELL, FAN, BAR, BAR], seg=10)
            # Fan blades in the bore.
            for k in range(5):
                a = 2 * math.pi * k / 5
                d = t1 * math.cos(a) + t2 * math.sin(a)
                e = n.cross(d)
                c0 = o - n * 0.62
                pts = []
                for rr in (rb * 0.5, rb * 0.97):
                    for hh in (-0.08, 0.08):
                        for ww in (-0.06, 0.06):
                            pts.append(tuple(c0 + d * rr + n * (hh + ww * 0.8) + e * (ww * 2.2)))
                hull(D, pts, FAN)


def build_nose(P, D):
    # Chin slot (rows 20-21): a dark recess between the keel and the lip, three vanes inside.
    box(D, -3.15, 3.15, 19.8, 22.1, 1.6, 2.9, 0.08, SLOT)
    for c in (-1.6, 0.0, 1.6):
        box(D, c - 0.22, c + 0.22, 20.15, 21.75, 2.0, 3.02, 0.06, FAN)
    # Purple lip (row 22).
    slab(P, [(-3.55, 21.95), (3.55, 21.95), (3.45, 22.95), (-3.45, 22.95)], lambda x, y: 3.1, 0.25, LIP,
         LIP, WALL, spacing=1.0)
    # Teal nose gun block (cols 9-14, rows 23-27), narrowing to the front, its top sloping down.
    nb = [(-3.45, 22.95), (3.45, 22.95), (3.4, 25.6), (2.75, 27.05), (1.95, 27.62), (-1.95, 27.62),
          (-2.75, 27.05), (-3.4, 25.6)]
    ntop = lambda x, y: 3.3 - (y - 22.95) * 0.25  # noqa: E731
    slab(P, nb, ntop, 0.42, NOSE, NSIDE, NSIDE, zbase=lambda x, y: -0.2, bottom=True, spacing=0.8)
    # The lit visor band across its back (row 23, 131).
    slab(D, [(-3.15, 23.0), (3.15, 23.0), (3.1, 24.0), (-3.1, 24.0)], lambda x, y: ntop(x, y) + 0.2, 0.15,
         NCHAMF, NCHAMF, NCHAMF, zbase=lambda x, y: ntop(x, y) - 0.4, bottom=True, spacing=1.0)
    # The small dark vent (col 12, row 25).
    box(D, -0.48, 0.48, 24.8, 26.0, 2.2, ntop(0, 25.4) + 0.1, 0.08, VENT)
    # Twin barrels in the block's front face, dark bores.
    for c in (-1.4, 1.4):
        o, t1, t2, n = frame_at(c, 27.15, 1.05, (0, 1, 0))
        lathe(D, o, t1, t2, n, [(0.74, -0.4), (0.74, 0.35), (0.6, 0.5), (0.56, 0.75), (0.47, 0.88),
                                (0.3, 0.88), (0.3, 0.4), (0.0, 0.4)],
              [BARREL, BARREL, BARREL, BARREL, BARREL, WELL, WELL], seg=12)


def finish(part, mats, coll):
    part.orient()
    bm = part.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    m = Matrix(((PX, 0, 0, 0.5 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    me = bpy.data.meshes.new(part.name)
    bm.to_mesh(me)
    bm.free()
    for mat in mats:
        me.materials.append(mat)
    obj = bpy.data.objects.new(part.name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(part.smooth_angle))
    return obj


def build(coll, sprite):
    mats = materials(sprite)
    H = Part("n127_hull", smooth_angle=12)
    build_hull(H)
    B = Part("n127_belt", smooth_angle=30)
    build_belt(B)
    P = Part("n127_plates", smooth_angle=12)
    D = Part("n127_detail", smooth_angle=35)
    build_shoulders(P, D)
    build_rear(P, D)
    build_channel(P, D)
    build_cockpit(P, D)
    build_cheeks(P, D)
    build_keel(P, D)
    build_flanks(P, D)
    build_nose(P, D)
    return [finish(p, mats, coll) for p in (H, B, P, D)]


def bake_maps(obj, out_dir):
    tint, textured = T.TINT, T.TEXTURED
    T.TINT, T.TEXTURED = TINT, TEXTURED
    try:
        T.bake_maps(obj, out_dir, size=1024, samples=96)
    finally:
        T.TINT, T.TEXTURED = tint, textured
    for img in bpy.data.images:
        if img.name.startswith("talon_"):
            img.name = img.name.replace("talon_", f"{NAME}_")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    objs = build(coll, sprite)
    obj = T.join(objs, NAME)
    # The outline shell is made from the closed parts, before hidden faces are culled (remeshing
    # the culled, open plates would wrap both sides of every one).
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    T.cull_hidden(obj)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    # Engine glows: just behind the two nozzles (sprite x -+3.55, exit row 0.95, axis z -0.55), in
    # glTF axes: x = (x + 0.5) / 12, y = z / 12 (up), z = (row - 14) / 12.
    obj["tyrian_engines"] = {"color": "#7db2ba", "at": [[round((s * 3.55 + 0.5) * PX, 4), round(-0.55 * PX, 4),
                                                          round((0.35 - 14) * PX, 4)] for s in (-1, 1)]}
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix=f"{NAME}_bake_"))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(closed, coll, voxel=0.016, faces=1500, smooth=16)
    shell.name = shell.data.name = f"{NAME}_outline"
    bpy.data.objects.remove(closed)
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    if out:
        common.export_glb([obj, shell], out, image_format=fmt)
        print(f"exported {out}")
    else:
        common.export_sprite_model(ROOT, [obj, shell], MODEL, sprite["sprites"], image_format=fmt)
    if "--preview" in argv:
        ref = ROOT / "reference" / "models" / NAME / sprite["frames"][0]["image"]
        common.render_preview([obj], argv[argv.index("--preview") + 1], ref, size=sprite["frames"][0]["size"])


if __name__ == "__main__":
    main()
