"""Grey drilling machine (newsh2.shp frame 267, enemy type 17): a hard-surface 3D version of its sprite.

The sprite is authoritative for the top-down outline (row by row), the lights and the colours; the
concept (assets/blender/features/concepts/newsh2-267.jpg) and a side/front blueprint guide the side, front and
rear design and the detail.

Reading of the sprite (24 x 28, symmetric about the centre of column 11, x = 11.5):
  rows 2-7    a lying steel capsule end (the head, pal 8), round in section, with a clamp band at
              row 5 and a hub boss at its rear end
  row 5       a cross beam through the head (pal 4) out to the yoke, hubs where it enters the head
  rows 2-9    brass yoke arms (pal 23) either side, levers on the beam: their rear ends rise to tips
              at rows 2-3, their front ends come down and out to pivot blocks (pal 22) at row 9
  rows 9-18   twin hydraulic legs (pal 6, rods pal 9) lying from the pivot blocks to feet (pal 4)
              on the ground at cols 0-2 / 20-22
  rows 7-18   the drum (pal 6): a tall superelliptic body, its shoulders under brass armour (inner
              pads pal 27, outer pads pal 165 wrapping down the flanks), a dark spine plate (pal 3)
              with two glowing red slot lights (119 / 118, hot centres 121) at rows 9 and 11, a
              light cross strap at row 15 and a tan rib (pal 25) in a channel below it, steel side
              plates (pal 7) with rivets and vents
  rows 19-27  a groove ring (pal 4) and the conical drill bit (pal 5) with two serrated helical
              flights (pal 6) to the point at row 27
The underside is a plain closed hull (the drum's own lower half), no detail.

Units: everything is built in sprite px (x = column edge 0..24, y = row edge 0..28 with the drill
at +y, z up) and moved to Blender at the end (X = (x - 12) / 12, Y = (14 - y) / 12, Z = z / 12).
Satin metal palette materials (pal_<index>), AO/edge colour multiplier and roughness/metal bake
only (no concept projection: maps.json says "bake": "model", D50/D53), an outline shell
(common.outline_shell, D51). One frame, one model.

    blender --background --python assets/blender/enemies/newsh2-267.py -- [--out X.glb] [--no-bake] [--preview out.png]
"""

import bisect
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from usp_talon import cull_hidden  # noqa: E402

NAME = "newsh2-267"
TAG = "nsh2_267"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
PX = 1 / 12
AX = 11.5   # mirror axis (column edge units)
ZC = 5.6    # body axis height
N = 24      # hull sides
METAL = 0.3
TINT = (0.88, 0.93, 1.0)
# flights run down to the left across the top, as the sprite draws them; the phase puts their
# crests where the sprite's cone rows are widest
PHASE = math.pi - 2.4


# --- curves ---------------------------------------------------------------------------------------

def pchip(xs, ys):
    """Monotone cubic interpolation through (xs, ys): smooth, no overshoot."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def smooth01(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


# Plan half width of the body: the INNER mask's row half widths (D74; tools/sprite_mask.py), row centre
# y + 0.5 -> half width. The head is a dome from y = 3.0, a collar at row 6, a neck at row 7, the drum's
# shoulders at rows 8-10 and flanks 6.5 wide to row 17. The drum's armour stands 0.3 proud of the hull
# (BUMP) and the drill flights ride 0.3 * sc above it, so the hull is that much inside the target.
DOME_END, DOME_C, HEAD_R = 3.0, 4.5, 3.5
HW_ST = [(4.5, 3.5), (5.5, 3.5), (6.5, 3.45), (7.5, 3.5),
         (8.5, 4.6), (9.5, 5.6), (10.5, 6.62), (17.5, 6.62), (18.5, 6.12), (19.5, 5.6), (20.5, 4.6),
         (21.5, 4.6), (22.5, 4.1), (23.5, 3.6), (24.5, 2.6), (25.5, 1.55), (26.5, 0.5), (27.0, 0.0)]
_hw = pchip([a for a, _ in HW_ST], [b for _, b in HW_ST])
BUMP = 0.3


def hw_of(y):
    if y <= DOME_END or y >= 27.0:
        return 0.0
    if y < DOME_C:
        d = (DOME_C - y) / (DOME_C - DOME_END)
        return HEAD_R * math.sqrt(max(0.0, 1 - d * d))
    h = _hw(y)
    h -= BUMP * smooth01((y - 8.3) / 0.6) * (1 - smooth01((y - 18.85) / 0.4))
    h -= BUMP * min(1.0, h / 3.0) * smooth01((y - 19.1) / 0.5)
    return max(h, 0.0)


def hh_of(y):
    a, b, k = hw_of(y), ZC, 0.3
    if a <= 0:
        return 0.0
    return -k * math.log(math.exp(-a / k) + math.exp(-b / k))


def p_of(y):
    if y < 13:
        return 2.0 + 0.8 * smooth01((y - 7.0) / 2.6)
    return 2.8 - 0.8 * smooth01((y - 18.4) / 1.9)


def se(c, p):
    return math.copysign(abs(c) ** (2 / p), c)


def surf(y, t, off=0.0):
    """A point on the body at row y, angle t (0 = +x side, pi/2 = top), `off` px out."""
    hw, hh, p = hw_of(y), hh_of(y), p_of(y)
    return (AX + (hw + off) * se(math.cos(t), p), y, ZC + (hh + off) * se(math.sin(t), p))


def t_of_x(x, y):
    """Angle on the body's upper half whose plan x is `x` at row y."""
    hw, p = hw_of(y), p_of(y)
    dx = x - AX
    q = min(abs(dx) / max(hw, 1e-6), 1.0)
    return math.acos(math.copysign(q ** (p / 2), dx))


# --- mesh building (sprite px) --------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, vs, mat):
        if len({id(v) for v in vs}) < 3:
            return None
        try:
            face = self.bm.faces.new(vs)
        except ValueError:
            return None
        face.material_index = mat
        return face

    def strip(self, a, b, mat, closed=False):
        n = len(a)
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            self.f([a[i], a[j], b[j], b[i]], mat)

    def fan(self, ring, centre, mat):
        c = self.v(centre)
        n = len(ring)
        for i in range(n):
            self.f([ring[i], ring[(i + 1) % n], c], mat)


def loft_rings(M, rings, mats, cap0=True, cap1=True):
    """rings: list of point lists (equal length, closed loops) or single points; mats[i] for the
    band between ring i and i + 1."""
    vr = [[M.v(p) for p in r] for r in rings]
    for i in range(len(vr) - 1):
        a, b = vr[i], vr[i + 1]
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for k in range(len(b)):
                M.f([a[0], b[k], b[(k + 1) % len(b)]], mats[i])
        elif len(b) == 1:
            for k in range(len(a)):
                M.f([a[k], a[(k + 1) % len(a)], b[0]], mats[i])
        else:
            M.strip(a, b, mats[i], closed=True)
    if cap0 and len(vr[0]) > 2:
        M.f(list(reversed(vr[0])), mats[0])
    if cap1 and len(vr[-1]) > 2:
        M.f(vr[-1], mats[-1])
    return vr


def basis(d):
    d = Vector(d).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    w = d.cross(u).normalized()
    return d, u, w


def cyl(M, p0, p1, r, mat, n=12, ch=0.12, r1=None, phase=0.0, mats=None):
    """A chamfered cylinder (or truncated cone to r1) from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d, u, w = basis(p1 - p0)
    L = (p1 - p0).length
    r1 = r if r1 is None else r1
    ch = min(ch, L / 3, r * 0.4)

    def ring(c, rr):
        return [tuple(c + rr * (math.cos(phase + 2 * math.pi * k / n) * u + math.sin(phase + 2 * math.pi * k / n) * w))
                for k in range(n)]
    rings = [ring(p0, r - ch), ring(p0 + d * ch, r), ring(p1 - d * ch, r1), ring(p1, r1 - ch)]
    loft_rings(M, rings, mats or [mat] * 4)


def tube(M, p0, p1, r, r_in, depth, mat, mat_in, n=12, ch=0.1):
    """A pipe stub from p1 (closed, buried end) to p0 (open mouth) with a deep dark bore."""
    p0, p1 = Vector(p0), Vector(p1)
    d, u, w = basis(p0 - p1)

    def ring(c, rr):
        return [tuple(c + rr * (math.cos(2 * math.pi * k / n) * u + math.sin(2 * math.pi * k / n) * w)) for k in range(n)]
    rings = [ring(p1, r), ring(p0 - d * ch, r), ring(p0, r - ch), ring(p0, r_in), ring(p0 - d * depth, r_in * 0.9),
             tuple(p0 - d * (depth + 0.05))]
    rings[-1] = [rings[-1]]
    loft_rings(M, rings, [mat, mat, mat, mat_in, mat_in], cap0=True, cap1=False)


def octagon(x0, x1, z0, z1, c, y):
    return [(x0 + c, y, z0), (x1 - c, y, z0), (x1, y, z0 + c), (x1, y, z1 - c), (x1 - c, y, z1), (x0 + c, y, z1),
            (x0, y, z1 - c), (x0, y, z0 + c)]


def blockY(M, secs, mat, endch=0.25, mats=None):
    """A chamfered block lofted along y through sections (y, x0, x1, z0, z1, c), ends chamfered."""
    rings = []
    y0, *_ = secs[0]
    s = secs[0]
    rings.append(octagon(s[1] + endch, s[2] - endch, s[3] + endch, s[4] - endch, max(0.05, s[5] - endch * 0.4), s[0]))
    for i, s in enumerate(secs):
        y = s[0] + (endch if i == 0 else -endch if i == len(secs) - 1 else 0)
        rings.append(octagon(s[1], s[2], s[3], s[4], s[5], y))
    s = secs[-1]
    rings.append(octagon(s[1] + endch, s[2] - endch, s[3] + endch, s[4] - endch, max(0.05, s[5] - endch * 0.4), s[0]))
    loft_rings(M, rings, mats or [mat] * len(rings))


def blockX(M, x0, x1, y0, y1, z0, z1, c, mat, endch=0.2):
    """A chamfered block lofted along x."""
    def oct_x(x, a0, a1, b0, b1, cc):
        return [(x, a0 + cc, b0), (x, a1 - cc, b0), (x, a1, b0 + cc), (x, a1, b1 - cc), (x, a1 - cc, b1),
                (x, a0 + cc, b1), (x, a0, b1 - cc), (x, a0, b0 + cc)]
    e = endch
    rings = [oct_x(x0, y0 + e, y1 - e, z0 + e, z1 - e, max(0.05, c - e * 0.4)), oct_x(x0 + e, y0, y1, z0, z1, c),
             oct_x(x1 - e, y0, y1, z0, z1, c), oct_x(x1, y0 + e, y1 - e, z0 + e, z1 - e, max(0.05, c - e * 0.4))]
    loft_rings(M, rings, [mat] * 4)


def patch(M, y0, y1, tfun, mat, off=0.4, off_in=-0.12, ch=0.16, res=1.2, chy=None):
    """An armour plate on the body: rows y0..y1, angles tfun(y) -> (ta, tb), standing `off` px
    proud with chamfered edges (45 deg-ish), buried to off_in. A closed shell."""
    chy = ch if chy is None else chy
    ny = max(2, int(math.ceil((y1 - y0) / res)))
    ta, tb = tfun(0.5 * (y0 + y1))
    arc = sum((Vector(surf(0.5 * (y0 + y1), ta + (tb - ta) * (k + 1) / 16)) -
               Vector(surf(0.5 * (y0 + y1), ta + (tb - ta) * k / 16))).length for k in range(16))
    nt = max(2, int(math.ceil(arc / res)))

    def grid(yy0, yy1, cu, o):
        rows = []
        for i in range(ny + 1):
            y = yy0 + (yy1 - yy0) * i / ny
            a, b = tfun(y)
            row = []
            for j in range(nt + 1):
                uu = cu + (1 - 2 * cu) * j / nt
                row.append(surf(y, a + (b - a) * uu, o))
            rows.append(row)
        return rows
    cu = min(0.3, ch / max(arc, 1e-3))
    outer = grid(y0 + chy, y1 - chy, cu, off)
    inner = grid(y0, y1, 0.0, off_in)
    # a mid ring at the hull surface level, at the plate's full outline, gives the chamfer a crisp
    # foot instead of a slope from deep inside
    vo = [[M.v(p) for p in r] for r in outer]
    vi = [[M.v(p) for p in r] for r in inner]
    vf = [[M.v(p) for p in r] for r in grid(y0, y1, 0.0, 0.02)] if off_in < -0.01 else None
    for a, b in zip(vo, vo[1:]):
        M.strip(a, b, mat)
    for a, b in zip(vi, vi[1:]):
        M.strip(b, a, mat)

    def border(g):
        return [g[0][j] for j in range(nt + 1)] + [g[i][nt] for i in range(1, ny + 1)] + \
               [g[ny][j] for j in range(nt - 1, -1, -1)] + [g[i][0] for i in range(ny - 1, 0, -1)]
    bo, bi = border(vo), border(vi)
    if vf is None:
        M.strip(bo, bi, mat, closed=True)
    else:
        bf = border(vf)
        M.strip(bo, bf, mat, closed=True)
        M.strip(bf, bi, mat, closed=True)


def patch_x(M, y0, y1, xa, xb, mat, **kw):
    def tf(y):
        lo, hi = AX - 0.8 * hw_of(y), AX + 0.8 * hw_of(y)
        return t_of_x(min(max(xb, lo), hi), y), t_of_x(min(max(xa, lo), hi), y)
    return patch(M, y0, y1, tf, mat, **kw)


def patch_t(M, y0, y1, ta, tb, mat, **kw):
    return patch(M, y0, y1, lambda y: (math.radians(ta), math.radians(tb)), mat, **kw)


def bolt(M, y, t, mat, r=0.2, h=0.32, base=0.1):
    """A small hex bolt head standing on the body, along its normal."""
    p = Vector(surf(y, t, base))
    q = Vector(surf(y, t, base + 1.0))
    n = (q - p).normalized()
    _, u, w = basis(n)

    def ring(c, rr):
        return [tuple(c + rr * (math.cos(math.pi * k / 3) * u + math.sin(math.pi * k / 3) * w)) for k in range(6)]
    loft_rings(M, [ring(p - n * 0.2, r), ring(p + n * h, r * 0.72)], [mat] * 2)


# --- palette ---------------------------------------------------------------------------------------

def materials(sprite):
    def pal(i, tag, metallic, roughness, glow=0.0):
        return common.palette_material(sprite, i, f"{TAG}_{tag}", metallic=metallic * METAL if not glow else 0.0,
                                       roughness=roughness, emission_strength=glow)
    return [
        pal(10, "head", 0.7, 0.32),       # 0  head capsule (polished steel)
        pal(4, "band", 0.55, 0.45),       # 1  clamp band, beam, feet
        pal(6, "drum", 0.6, 0.42),        # 2  drum
        pal(5, "cone", 0.6, 0.4),         # 3  drill cone, hubs, glands
        pal(7, "plate", 0.6, 0.4),        # 4  drum side plates
        pal(9, "rivet", 0.65, 0.35),      # 5  bolts, rods, pins
        pal(3, "spine", 0.4, 0.5),        # 6  dark spine plate, bezels, vents
        pal(2, "bore", 0.2, 0.8),         # 7  bores, recesses
        pal(23, "arm", 0.55, 0.42),       # 8  brass yoke arms
        pal(22, "pivot", 0.5, 0.45),      # 9  pivot blocks
        pal(27, "pad_in", 0.55, 0.38),    # 10 light brass inner pads
        pal(165, "pad_out", 0.45, 0.48),  # 11 brown outer armour
        pal(25, "rib", 0.55, 0.4),        # 12 tan rib, arm ridge
        pal(119, "light_a", 0, 0.3, glow=2.6),   # 13 upper light
        pal(118, "light_b", 0, 0.3, glow=2.6),   # 14 lower light
        pal(121, "light_hot", 0, 0.3, glow=3.6),  # 15 hot centres
        pal(11, "strap", 0.6, 0.36),      # 16 light cross strap
    ]


HEAD, BAND, DRUM, CONE, PLATE, RIVET, SPINE, BORE, ARM_M, PIVOT, PAD_IN, PAD_OUT, RIB, LA, LB, HOT, STRAP = range(17)
GLOWING = (LA, LB, HOT)


# --- the machine -----------------------------------------------------------------------------------

def hull(M):
    """The body: one closed loft, head dome to drill tip, with modelled seams (V grooves), a raised
    clamp band, a front flange and a recessed groove ring before the cone."""
    st = []
    K = 7
    for k in range(K + 1):
        u = math.cos(0.5 * math.pi * k / K)
        st.append((DOME_C - (DOME_C - DOME_END) * u, 0.0))
    st += [(4.75, 0.0), (5.0, 0.0), (5.5, 0.0), (6.0, 0.0), (6.3, 0.0), (6.7, 0.0), (7.0, 0.0), (7.3, 0.0),
           (7.6, -0.12), (7.9, 0.0), (8.2, 0.0), (8.6, 0.0), (9.0, 0.0), (9.5, 0.0), (10.0, 0.0), (10.5, 0.0),
           (11.0, 0.0), (12.2, 0.0), (12.45, -0.2), (12.7, 0.0), (14.5, 0.0), (16.5, 0.0), (17.6, 0.0),
           (18.25, 0.0), (18.4, 0.28), (18.85, 0.28), (19.0, -0.15), (19.85, -0.15), (20.0, 0.0)]
    y = 20.6
    while y < 26.8:
        st.append((y, 0.0))
        y += 0.7
    st.append((27.0, 0.0))

    def mat(y):
        if y < 5.0 or 6.0 < y < 7.6:
            return HEAD
        if y <= 6.0:
            return BAND
        if y < 18.3:
            return DRUM
        if y < 19.0:
            return DRUM
        return CONE
    rings, mats = [], []
    for i, (y, off) in enumerate(st):
        if hw_of(y) < 1e-3:
            rings.append([(AX, y, ZC)])
        elif y >= 26.99:
            rings.append([(AX, 27.0, ZC)])
        else:
            rings.append([surf(y, 2 * math.pi * k / N, off) for k in range(N)])
        if i < len(st) - 1:
            mats.append(mat(0.5 * (y + st[i + 1][0])))
    mats.append(CONE)
    loft_rings(M, rings, mats, cap0=False, cap1=False)


def head_detail(M):
    # Hub boss at the rear end of the head.
    cyl(M, (AX, 3.7, ZC), (AX, 3.05, ZC), 0.5, CONE, n=10, ch=0.1)
    # Dome ribs: three pressed seams from the hub to the clamp band.
    for deg in (38, 90, 142):
        t = math.radians(deg)
        patch(M, 3.5, 4.9, lambda y, t=t: (t - 0.09, t + 0.09), PLATE, off=0.12, off_in=-0.1, ch=0.05, res=0.6)
    # A low dark collar flange behind the head at rows 6-7 (the sprite's ink between head and claws):
    # flat and wide, so the head stays a small dome over it.
    rings = []
    for y, a, b in ((6.0, 4.1, 1.2), (6.15, 4.5, 1.5), (6.9, 4.5, 1.5), (7.05, 4.1, 1.2)):
        rings.append([(AX + a * se(math.cos(2 * math.pi * k / N), 2.6), y,
                       ZC - 0.2 + b * se(math.sin(2 * math.pi * k / N), 2.6)) for k in range(N)])
    loft_rings(M, rings, [SPINE] * 4)
    # Bolts round the collar.
    for deg in (30, 60, 120, 150):
        bolt(M, 6.5, math.radians(deg), RIVET, r=0.2, h=0.22, base=0.05)


def beam(M):
    """The cross beam through the head at row 5 (one sprite px thick), out to both yoke arms, with hubs."""
    blockX(M, 3.05, 19.95, 5.05, 5.95, 6.0, 7.3, 0.25, BAND, endch=0.12)
    for s in (-1, 1):
        def X(x):
            return x if s < 0 else 2 * AX - x
        cyl(M, (X(6.0), 5.5, 6.65), (X(8.0), 5.5, 6.65), 0.47, CONE, n=10, ch=0.1)


def spine(M):
    """The dark spine plate with the two framed red slot lights, the cross strap, the channel and
    the tan rib."""
    patch_x(M, 8.55, 14.95, 9.0, 14.0, SPINE, off=0.5, ch=0.22)
    for (ya, yb), lens in (((9.05, 9.95), LA), ((11.05, 11.95), LB)):
        # bezel frame (proud of the lens, so the lens sits recessed in it)
        kw = dict(off=0.85, off_in=0.2, ch=0.08, res=0.6)
        patch_x(M, ya - 0.28, ya, 9.7, 13.3, SPINE, **kw)
        patch_x(M, yb, yb + 0.28, 9.7, 13.3, SPINE, **kw)
        patch_x(M, ya, yb, 9.7, 10.0, SPINE, **kw)
        patch_x(M, ya, yb, 13.0, 13.3, SPINE, **kw)
        lk = dict(off=0.66, off_in=0.2, ch=0.03, res=0.6)
        patch_x(M, ya, yb, 10.0, 11.05, lens, **lk)
        patch_x(M, ya, yb, 11.05, 11.95, HOT, **lk)
        patch_x(M, ya, yb, 11.95, 13.0, lens, **lk)
    # bolts at the spine plate's corners
    for yy in (8.95, 14.55):
        for xx in (9.45, 13.55):
            bolt(M, yy, t_of_x(xx, yy), RIVET, r=0.18, h=0.2, base=0.55)
    # cross strap (row 15) and the channel with the tan rib (rows 16-18)
    patch_x(M, 14.95, 15.9, 8.4, 14.6, STRAP, off=0.82, ch=0.2)
    patch_x(M, 15.9, 18.95, 9.9, 13.1, CONE, off=0.12, ch=0.08)
    patch_x(M, 15.9, 18.25, 11.05, 11.95, RIB, off=0.55, ch=0.15, res=0.5)
    # channel side rails
    patch_x(M, 15.9, 18.95, 9.6, 9.95, PLATE, off=0.4, ch=0.08)
    patch_x(M, 15.9, 18.95, 13.05, 13.4, PLATE, off=0.4, ch=0.08)


def armour(M):
    for s in (-1, 1):
        def X(x):
            return x if s < 0 else 2 * AX - x

        def px(y0, y1, xa, xb, mat, **kw):
            a, b = sorted((X(xa), X(xb)))
            patch_x(M, y0, y1, a, b, mat, **kw)

        def pt(y0, y1, ta_fn, tb_deg, mat, **kw):
            """From the angle over plan x = ta_fn's x down the flank to tb_deg (left side)."""
            if s < 0:
                patch(M, y0, y1, lambda y: (t_of_x(X(ta_fn), y), math.radians(tb_deg)), mat, **kw)
            else:
                patch(M, y0, y1, lambda y: (math.radians(180 - tb_deg), t_of_x(X(ta_fn), y)), mat, **kw)
        # inner (cream brass) pad over the shoulder's top corner, with a cream knob
        px(8.3, 10.8, 6.6, 9.0, PAD_IN, off=0.62, ch=0.24)
        # outer brown armour wrapping the shoulder down the flank
        pt(8.8, 12.9, 6.6, 152, PAD_OUT, off=BUMP, ch=0.24)
        lo2 = (154, 205) if s < 0 else (-25, 26)
        patch_t(M, 8.8, 12.9, *lo2, PAD_OUT, off=BUMP, ch=0.24)
        # lower lip of brown armour below the inner pad
        px(10.8, 11.95, 6.6, 9.0, PAD_OUT, off=0.45, ch=0.18)
        # bolts on the armour
        for yy, xx in ((9.35, 7.2), (10.3, 8.5), (12.3, 5.3)):
            bolt(M, yy, t_of_x(X(xx), yy), RIVET, r=0.2, h=0.25, base=0.6)
        # drum side plates: upper over the shoulder, lower on the flank, rivets, vents
        pt(12.75, 18.3, 7.3, 166, PLATE, off=BUMP, ch=0.16)
        lo = (192, 238) if s < 0 else (-58, -12)
        patch_t(M, 12.75, 18.3, *lo, PLATE, off=BUMP, ch=0.16)
        for yy in (13.3, 15.6, 17.75):
            for deg in ((124, 158) if s < 0 else (56, 22)):
                bolt(M, yy, math.radians(deg), RIVET, r=0.17, h=0.18, base=0.28)
        vd = (171, 189) if s < 0 else (-9, 9)
        for yy in (13.4, 14.7, 16.0, 17.3):
            patch_t(M, yy, yy + 0.55, *vd, BORE, off=0.06, off_in=-0.01, ch=0.04, res=2.0)
        # exhaust stubs low on the rear shoulder, facing back
        tube(M, (X(8.0), 8.7, 2.85), (X(8.0), 10.0, 2.85), 0.55, 0.35, 0.6, PLATE, BORE, n=10)


def drill(M):
    """Two helical flights round the cone with saw teeth on their crests."""
    y0, y1, pitch = 20.15, 26.4, 4.4
    for start in (PHASE, PHASE + math.pi):
        n = int((y1 - y0) / 0.32)
        rings = []
        for k in range(n + 1):
            y = y0 + (y1 - y0) * k / n
            t = start + 2 * math.pi * (y - y0) / pitch
            sc = min(1.0, hw_of(y) / 3.0)
            hgt = 0.42 * sc
            wb, wt = 0.28 * sc + 0.06, 0.1 * sc + 0.04
            rings.append([surf(y - wb, t, -0.15), surf(y + wb, t, -0.15), surf(y + wt, t, hgt), surf(y - wt, t, hgt)])
        loft_rings(M, rings, [DRUM] * len(rings))
        # saw teeth along the crest
        k = 0
        y = y0 + 0.5
        while y < y1 - 0.8:
            t = start + 2 * math.pi * (y - y0) / pitch
            sc = min(1.0, hw_of(y) / 3.0)
            hgt = 0.42 * sc
            a = Vector(surf(y, t, hgt - 0.05))
            b = Vector(surf(y, t, hgt + 0.25 * sc))
            tdir = Vector(surf(y, t + 0.12, hgt)) - Vector(surf(y, t - 0.12, hgt))
            tdir.normalize()
            nrm = (b - a).normalized()
            side = tdir.cross(nrm).normalized() * 0.07
            p0, p1 = a - tdir * 0.22, a + tdir * 0.22
            tip = b + tdir * 0.12
            v = [M.v(tuple(q)) for q in (p0 - side, p1 - side, tip - side, p0 + side, p1 + side, tip + side)]
            M.f([v[0], v[1], v[2]], RIVET)
            M.f([v[5], v[4], v[3]], RIVET)
            M.f([v[0], v[3], v[4], v[1]], RIVET)
            M.f([v[1], v[4], v[5], v[2]], RIVET)
            M.f([v[2], v[5], v[3], v[0]], RIVET)
            y += 0.95
            k += 1
    # hardened tip
    cyl(M, (AX, 25.8, ZC), (AX, 27.0, ZC), 0.42, RIVET, n=10, ch=0.03, r1=0.05)
    # bolt ring on the drum's front flange face
    for k in range(6):
        t = 2 * math.pi * (k + 0.5) / 6
        p = Vector(surf(18.85, t, -0.05))
        c = Vector((AX, 18.85, ZC))
        p = c + (p - c) * 0.9
        cyl(M, tuple(p + Vector((0, -0.1, 0))), tuple(p + Vector((0, 0.32, 0))), 0.22, RIVET, n=6, ch=0.05)


# The arm is a curved brass claw: a smooth sweep along the sprite's inner mask from its pointed tip at
# row 3 (col 4) down the shoulder (cols 3-4, rows 4-6) and out to the strut at col 1 (rows 7-9), where it
# meets the pivot block on top of the leg. CLAW: (y, centre x, half width, z bottom, z top) samples,
# interpolated monotonically so the claw's sides curve rather than step.
CLAW = [(2.85, 4.55, 0.25, 7.6, 8.3), (3.4, 4.5, 0.6, 7.05, 8.75), (4.4, 4.3, 1.12, 6.4, 8.8),
        (5.5, 4.05, 1.02, 6.0, 8.5), (6.4, 3.75, 0.98, 5.5, 8.0), (7.3, 2.62, 1.42, 4.85, 7.35),
        (8.0, 2.2, 1.0, 4.25, 6.8), (8.8, 1.7, 0.78, 3.7, 6.25), (9.4, 1.5, 0.62, 3.3, 5.8)]
_claw = [pchip([c[0] for c in CLAW], [c[k] for c in CLAW]) for k in range(1, 5)]
LEG_X = 1.5


def claw_at(y):
    return tuple(f(y) for f in _claw)


def leg_z(y):
    return 4.3 - (y - 9.5) * 0.375


def claw(M):
    """The claw: rounded octagonal sections lofted along y through the curved centre line, with a
    narrow lit ridge (pal 25, the sprite's bright edge) running up its outer crest to the tip."""
    ys = [CLAW[0][0] + (CLAW[-1][0] - CLAW[0][0]) * k / 26 for k in range(27)]
    secs = []
    for i, y in enumerate(ys):
        cx, w, z0, z1 = claw_at(y)
        c = min(0.42 * min(2 * w, z1 - z0), 0.55)
        secs.append((y, cx - w, cx + w, z0, z1, c))
    blockY(M, secs, ARM_M, endch=0.12)
    rsecs = []
    for y in ys[2:-3]:
        cx, w, z0, z1 = claw_at(y)
        rw = 0.28 * w
        rsecs.append((y, cx - 0.25 * w - rw, cx - 0.25 * w + rw, z1 - 0.1, z1 + 0.32, 0.08))
    blockY(M, rsecs, RIB, endch=0.1)


def yoke(M):
    """Left claw, pivot block, leg and foot (mirrored for the right)."""
    claw(M)
    # dark clamp where the beam meets the claw's inner face (the sprite's ink pixel at row 4, col 5)
    blockY(M, [(3.95, 4.6, 6.15, 6.0, 7.7, 0.3), (5.95, 4.6, 6.15, 6.0, 7.7, 0.3)], BAND, endch=0.15)
    # pivot block under the claw's foot, where the leg starts
    blockY(M, [(9.0, 0.9, 2.1, 3.2, 5.6, 0.35), (10.1, 0.9, 2.1, 3.2, 5.6, 0.35)], PIVOT, endch=0.2)
    # the leg: a strut sloping down to the foot, with a dark collar, the light ring and the rod
    for (ya, yb), m in (((10.1, 11.0), BAND), ((11.0, 12.0), STRAP), ((12.0, 13.0), RIVET), ((13.0, 17.1), PLATE)):
        cyl(M, (LEG_X, ya, leg_z(ya)), (LEG_X, yb, leg_z(yb)), 0.7, m, n=8, ch=0.1)
    # foot block on the ground
    blockY(M, [(16.9, 0.8, 2.2, 0.0, 1.7, 0.35), (18.0, 0.8, 2.2, 0.0, 1.5, 0.35)], CONE, endch=0.25)


def mirror_into(src, dst):
    """Copy src's geometry into dst mirrored about x = AX."""
    vm = {}
    for v in src.bm.verts:
        vm[v] = dst.v((2 * AX - v.co.x, v.co.y, v.co.z))
    for f in src.bm.faces:
        dst.f([vm[v] for v in reversed(f.verts)], f.material_index)


def build(sprite, coll):
    M = Mesh()
    hull(M)
    head_detail(M)
    beam(M)
    spine(M)
    armour(M)
    drill(M)
    L = Mesh()
    yoke(L)
    # copy the left side, then its mirror for the right
    vm = {}
    for v in L.bm.verts:
        vm[v] = M.v(tuple(v.co))
    for f in L.bm.faces:
        M.f([vm[v] for v in f.verts], f.material_index)
    mirror_into(L, M)
    L.bm.free()

    bm = M.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = Matrix(((PX, 0, 0, -12 * PX), (0, -PX, 0, 14 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for mat in materials(sprite):
        me.materials.append(mat)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(36))
    return obj


def check_normals(obj):
    """Outward normals: closed shells only, so recalc_face_normals is reliable; report open edges."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    n_open = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    print(f"newsh2-267: {n_open} non-manifold edges")


# --- bake (AO + edge lift colour multiplier, roughness/metal; no concept projection) -------------

def bake_maps(obj, out_dir, size=1024, samples=64):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(d.type == "METAL" for d in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:
        print("newsh2-267: no GPU bake", err)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.003, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{TAG}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{TAG}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
    mats = list(me.materials)
    saved = {}
    for m in mats:
        out = next(n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None

    def bake_shader(m, mode):
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        rough = bsdf.inputs["Roughness"].default_value
        metal = bsdf.inputs["Metallic"].default_value
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def math_(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.03
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.16
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.005
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = math_("MULTIPLY", math_("POWER", ao_s.outputs["AO"], 0.8),
                     math_("ADD", 0.65, math_("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.5, math_("MULTIPLY", occl, 0.6)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            tint = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(math_("MULTIPLY", v, TINT[k]), tint.inputs[k])
            nt.links.new(tint.outputs[0], em.inputs["Color"])
        else:
            r = math_("ADD", rough, math_("SUBTRACT", math_("MULTIPLY", math_("SUBTRACT", 1.0, occl), 0.3),
                                          math_("MULTIPLY", edge, 0.16)))
            r = math_("MAXIMUM", math_("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            nt.links.new(r, comb.inputs[1])
            comb.inputs[2].default_value = metal
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    for mode, img in (("colour", col_img), ("rm", rm_img)):
        tmps = {m.name: bake_shader(m, mode) for m in mats}
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        for m in mats:
            nt = m.node_tree
            for n in tmps[m.name]:
                nt.nodes.remove(n)
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if saved[m.name] is not None:
                nt.links.new(saved[m.name], out.inputs["Surface"])
        img.filepath_raw = str(Path(out_dir) / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()

    for i, m in enumerate(mats):
        if i in GLOWING:
            continue
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        ct = nt.nodes.new("ShaderNodeTexImage")
        ct.image = col_img
        nt.links.new(uvn.outputs["UV"], ct.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(ct.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Base Color"])
        rt = nt.nodes.new("ShaderNodeTexImage")
        rt.image = rm_img
        nt.links.new(uvn.outputs["UV"], rt.inputs["Vector"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(rt.outputs["Color"], sep.inputs[0])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    sprite = common.load_sprite(ROOT, NAME)
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    check_normals(obj)
    # The outline shell is made from the closed parts, before hidden faces are culled.
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    if "--no-cull" not in argv:
        cull_hidden(obj)
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"{NAME}: {len(obj.data.polygons)} faces, {tris} triangles")
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, Path(tempfile.mkdtemp(prefix="nsh2_267_bake_")))
        fmt = "WEBP"
    # The outline shell (D51), made after the bake so its occlusion rays never hit it.
    shell = common.outline_shell(closed, coll, faces=1500)
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
