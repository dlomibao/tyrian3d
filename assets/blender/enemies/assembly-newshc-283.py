"""DELIANI's flamethrower towers (newshc.shp, assembly-newshc-283): two STANDING towers with a crane
between them, built as what they are and drawn the way the art draws them (D82's approach C, for
sprite models; D161's follow-up).

The pillar is a tower, not a column lying on the ground. Tyrian draws it from the south at a low
angle: its foot is the bottom of the sprite column (newshc-55, on the floor tiles) and it rises up
the screen through newshc-17 and newshc-115 to the ball head (newshc-77, its own enemy). Every round
rim in the sprite is an ellipse about a quarter as tall as it is wide: the art camera is an
orthographic one from the south, 15 deg up (lib_deliani_tower.py: screen row
s = VB + sin15 (v - VB) - cos15 z).

So the model is the true upright tower (lib_deliani_tower.py: a surface of revolution 93 px tall
on a 16 px disc; base drum with a west access hatch, drum 1 and drum 0 with red shoulder lamps, the
bolted shaft, the red flared vent bell, the vent cup the head retracts into), exported upright. Its
art view is never baked into the asset (D82's approach C, extended to sprite models by D165): each
piece carries the glTF extras `tyrian_oblique: [cos e, sin e, axis_z]` and `tyrian_depth_band: [lo,
hi, 0, Y_TOP]`, and the game's renderer (src/render/obliqueView.ts) puts each vertex, per frame, on
the camera ray through the point the art draws it at, (x, axis_z + sin e (z - axis_z) - cos e y),
with the depth of its height squeezed from [0, Y_TOP] into the pass budget [lo, hi]. Normals, light
and shadow are the real tower's. The viewer, Blender and anything else that loads the glb see the
real tower standing on its foot.

How it is built: the tower is made in the art's frame first (`lock`: the rigid turn that puts the
art camera overhead, which is the game's plan exactly), so the cut into the sprite's 24x28 pieces
is a cut along screen rows, and the outline shell and the AO bake (D50, D65: the model's own
occlusion over a ground disc, no projection) are made there; then each piece is turned back
upright (`stand`) and exported about its own centre. Measured on the game form: the exported
upright pieces put through the renderer's art view (`game_form`), top view against the sprite masks.

The crane (newshc-245 over newshc-283) is unchanged: a squat dome on the floor (grey cap, a blue
glass ring, grey band with a blue front window, dark skirt with blue trim and a dark hatch housing
standing out to the south), a blue boom raking north from a pivot boss on the dome's top up to a
grey U clevis, arms to the hammer-shaped grey head (upper and lower prongs pointing west, blue
glass on its body, a blue stripe on top, a dark back block) and a folded blue fin on a raked post
standing on the floor. Its floor (raised tiles 101/102, grout 99/100) is built only as the bake's
occluder and deleted before export (D130).

Crane coordinates: sprite px of the half assembly (c east, r south, h up; r 0 = assembly row 28,
under the newshc-77 head), X = (c - 48) / 12, Y = (28 - r) / 12, Z = h / 12 (whole machine 96x112,
origin screen (164, 24)); the right half repeats the pillar at +72 px and the crane at +24 px.

  blender --background --python assets/blender/enemies/assembly-newshc-283.py -- [--no-bake]
      [--measure dir] [--views dir]
(exports public/models/enemies/newshc-{115,17,55,245,283}.glb and their spriteModels entries, and
newshc-129.glb: frame 129, the top piece burnt once its head is destroyed (burnt_parts); newshc-77.py
exports the head frames, the wreck (frame 91) among them, with this file's tower helpers)
"""

import bisect
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_deliani_tower as TG  # noqa: E402
import os  # noqa: E402

# The ball's plan radius (px) in this file's builds: the sprite's ball is a touch fuller than the
# lib's 7.85 at its upper rim (top-view IoU, frames 77-81).
TG.RB = float(os.environ.get("T283_RB", "8.05"))
# Frame 81's ram lift (px): the sprite's row 27 under the hood is the ram's ink shadow there.
TG.HEAD[81]["lift"] = float(os.environ.get("T283_LIFT81", "1.0"))

NAME = "assembly-newshc-283"
ROOT = WT
HERE = Path(__file__).resolve().parent
PX = 1 / 12
PIECES = ["newshc-115", "newshc-17", "newshc-55", "newshc-245", "newshc-283"]
ORIGIN = {"newshc-115": (0, 0), "newshc-17": (0, 28), "newshc-55": (0, 56), "newshc-245": (24, 0),
          "newshc-283": (24, 28)}
SX0, SY0 = 164, 24
FLOOR_IDX = set(range(96, 103))


def export_model(*a, **k):
    """common.export_sprite_model, skipped with T283_NOEXPORT=1 (measuring without touching the
    shipped exports)."""
    if os.environ.get("T283_NOEXPORT") == "1":
        return None
    return common.export_sprite_model(*a, **k)

# Palette index -> (metallic, roughness, emission strength). The index is the sprite's median for
# the region (darkest shading and brightest highlights left out); satin metal, painted red.
PROPS = {
    1: (0.0, 0.9, 0), 7: (0.45, 0.4, 0), 55: (0.45, 0.4, 0), 68: (0.1, 0.5, 0.25), 2: (0.1, 0.8, 0), 3: (0.3, 0.6, 0), 4: (0.4, 0.5, 0), 5: (0.45, 0.42, 0),
    6: (0.45, 0.42, 0), 8: (0.45, 0.4, 0), 9: (0.45, 0.4, 0), 16: (0.2, 0.6, 0),
    54: (0.45, 0.4, 0), 56: (0.45, 0.4, 0), 57: (0.45, 0.4, 0),
    67: (0.1, 0.5, 0), 69: (0.1, 0.5, 0.25), 71: (0.1, 0.45, 1.0), 72: (0.15, 0.45, 0),
    97: (0.25, 0.75, 0), 98: (0.25, 0.75, 0), 99: (0.25, 0.7, 0), 100: (0.25, 0.7, 0),
    101: (0.3, 0.6, 0), 102: (0.3, 0.6, 0),
    131: (0.3, 0.15, 0), 133: (0.3, 0.15, 0), 134: (0.3, 0.15, 0), 158: (0.2, 0.2, 0.8),
}


# --- geometry in sprite px ---------------------------------------------------------------------

class PxMesh:
    """A bmesh in sprite px; faces carry palette indices until materials are assigned."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.pal = self.bm.faces.layers.int.new("pal")

    def v(self, c, r, h):
        return self.bm.verts.new((c, r, h))

    def f(self, verts, pal, smooth=True):
        if len({id(v) for v in verts}) < 3:
            return None
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face[self.pal] = pal
        face.smooth = smooth
        return face


def pchip(xs, ys):
    return T.pchip(list(xs), list(ys))


def superellipse(n, p):
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        co, si = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(co) ** (2 / p), co), math.copysign(abs(si) ** (2 / p), si)))
    return out


def loft_r(m, stations, n=28, p=2.3, cap0=True, cap1=True, cap_pal=None, smooth=True, zmin=None):
    """Loft along r. stations: (r, c, h, a, b, pal) - pal colours the band from this station to the
    next. a = 0 makes a point. Superellipse sections (exponent p)."""
    sec = superellipse(n, p)
    rings = []
    for r, c, h, a, b, _ in stations:
        if a <= 1e-6:
            rings.append([m.v(c, r, h)])
        else:
            rings.append([m.v(c + u * a, r, h + w * b if zmin is None else max(zmin, h + w * b)) for u, w in sec])
    for i in range(len(rings) - 1):
        r0, r1, pal = rings[i], rings[i + 1], stations[i][5]
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(n):
            j = (k + 1) % n
            if len(r0) == 1:
                m.f((r0[0], r1[j], r1[k]), pal, smooth)
            elif len(r1) == 1:
                m.f((r0[k], r0[j], r1[0]), pal, smooth)
            else:
                m.f((r0[k], r0[j], r1[j], r1[k]), pal, smooth)
    if cap0 and len(rings[0]) > 1:
        m.f(list(reversed(rings[0])), cap_pal if cap_pal is not None else stations[0][5], False)
    if cap1 and len(rings[-1]) > 1:
        m.f(rings[-1], cap_pal if cap_pal is not None else stations[-2][5], False)


class LoftSurf:
    """The top surface of a loft's stations. surf(c, r) is its height; surf.pt(c, r, lift) a point
    `lift` px out from it, offset in the section's own scale (so panels on steep flanks stand off
    the surface instead of sinking into it)."""

    def __init__(self, stations, p=2.3):
        self.st = stations
        self.rs = [s[0] for s in stations]
        self.p = p

    def section(self, r):
        st, rs = self.st, self.rs
        i = max(0, min(len(rs) - 2, bisect.bisect_right(rs, r) - 1))
        s0, s1 = st[i], st[i + 1]
        t = 0.0 if s1[0] == s0[0] else min(1.0, max(0.0, (r - s0[0]) / (s1[0] - s0[0])))
        return [s0[k] + (s1[k] - s0[k]) * t for k in (1, 2, 3, 4)]

    def pt(self, c, r, lift=0.0):
        cc, h, a, b = self.section(r)
        if a <= 0:
            return c, h + lift
        u = max(-1.0, min(1.0, (c - cc) / a))
        w = max(0.0, 1 - abs(u) ** self.p) ** (1 / self.p)
        return cc + u * (a + lift), h + w * (b + lift)

    def __call__(self, c, r):
        return self.pt(c, r)[1]


def surf_of(stations, p=2.3):
    return LoftSurf(stations, p)


def drape(m, r0, r1, cl, cr, surf, lift, pal, side_pal=None, nr=6, nc=6, depth=0.12):
    """A closed panel hugging a surface: top at surf + lift, sides down to surf - depth."""
    side_pal = pal if side_pal is None else side_pal
    top, bot = [], []
    for i in range(nr + 1):
        r = r0 + (r1 - r0) * i / nr
        a, b = cl(r), cr(r)
        rowt, rowb = [], []
        for j in range(nc + 1):
            c = a + (b - a) * j / nc
            if hasattr(surf, "pt"):
                ct, ht = surf.pt(c, r, lift)
                cb, hb = surf.pt(c, r, -depth)
            else:
                ct, ht = c, surf(c, r) + lift
                cb, hb = c, surf(c, r) - depth
            rowt.append(m.v(ct, r, ht))
            rowb.append(m.v(cb, r, hb))
        top.append(rowt)
        bot.append(rowb)
    for i in range(nr):
        for j in range(nc):
            m.f((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]), pal, True)
            m.f((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]), side_pal, True)
    ring_t = top[0] + [row[nc] for row in top[1:]] + top[nr][:nc][::-1] + [row[0] for row in top[1:nr]][::-1]
    ring_b = bot[0] + [row[nc] for row in bot[1:]] + bot[nr][:nc][::-1] + [row[0] for row in bot[1:nr]][::-1]
    k = len(ring_t)
    for i in range(k):
        j = (i + 1) % k
        m.f((ring_b[i], ring_b[j], ring_t[j], ring_t[i]), side_pal, False)


def inset(poly, d):
    if d <= 0:
        return [tuple(p) for p in poly]
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        ln = math.hypot(nx, ny)
        nx, ny = nx / ln, ny / ln
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if (cx - mx) * nx + (cy - my) * ny < 0:
            nx, ny = -nx, -ny
        lines.append((a[0] + nx * d, a[1] + ny * d, b[0] - a[0], b[1] - a[1]))
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


def prism(m, poly, h0, h1, ch, pal, top_pal=None, bottom=True):
    """A chamfered block: vertical sides h0..h1-ch, a 45-degree chamfer, a flat top."""
    top_pal = pal if top_pal is None else top_pal
    ch = min(ch, (h1 - h0) * 0.6)
    b0 = [m.v(c, r, h0) for c, r in poly]
    b1 = [m.v(c, r, h1 - ch) for c, r in poly]
    b2 = [m.v(c, r, h1) for c, r in inset(poly, ch)]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        m.f((b0[i], b0[j], b1[j], b1[i]), pal, False)
        if ch > 0:
            m.f((b1[i], b1[j], b2[j], b2[i]), top_pal, False)
    m.f(b2, top_pal, False)
    if bottom:
        m.f(list(reversed(b0)), pal, False)


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def tube(m, path, pal, n=12, caps=True, smooth=True):
    """A round tube along a 3D path of (c, r, h, radius)."""
    rings = []
    for i, (c, r, h, rad) in enumerate(path):
        q = Vector(path[min(i + 1, len(path) - 1)][:3])
        o = Vector(path[max(i - 1, 0)][:3])
        t = (q - o).normalized()
        u = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = (u - t * u.dot(t)).normalized()
        w = t.cross(u)
        p0 = Vector((c, r, h))
        rings.append([m.v(*(p0 + u * (math.cos(2 * math.pi * k / n) * rad) + w * (math.sin(2 * math.pi * k / n) * rad)))
                      for k in range(n)])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            m.f((a[k], a[j], b[j], b[k]), pal, smooth)
    if caps:
        m.f(list(reversed(rings[0])), pal, False)
        m.f(rings[-1], pal, False)


# --- the crane ---------------------------------------------------------------------------------

DC, DR, DA, DB = 36.0, 37.2, 8.0, 8.2
PROF = [(1.0, 0.0), (1.0, 1.4), (0.975, 1.95), (0.93, 2.45), (0.87, 3.05), (0.77, 4.2), (0.63, 5.2),
        (0.46, 6.0), (0.26, 6.5), (0.0, 6.7)]


def dome_h(c, r):
    k = math.hypot((c - DC) / DA, (r - DR) / DB)
    if k >= 1:
        return 0.0
    for (k0, h0), (k1, h1) in zip(PROF[1:][::-1], PROF[:-1][::-1]):
        pass
    for i in range(len(PROF) - 1, 0, -1):
        k0, h0 = PROF[i]
        k1, h1 = PROF[i - 1]
        if k0 <= k <= k1:
            return h0 + (h1 - h0) * (k - k0) / ((k1 - k0) or 1)
    return PROF[-1][1]


def dome_region(c, r, h):
    if h < 0.9:
        return 3
    if r < 31.8:
        return 5
    if r < 34.9:
        return 131
    if r < 39.8:
        return 133 if 34.7 < c < 37.7 else 5
    if 40.4 <= r < 46.3 and (c < 33.6 or c > 38.4):
        return 54
    return 3


def crane(m):
    # Dome: lofted along r so its colour bands (sprite rows) have clean straight edges: grey cap,
    # a recessed blue glass band, grey band, a ring groove, dark skirt. Plan a rounded superellipse
    # (wider at the front than an ellipse, as the sprite's rows 43-45), flat on the floor.
    # The plan's half-width and centre per row are the sprite's (newshc-283's inner mask, rows 29-47):
    # round at the back, full across the middle, the dark skirt flaring a little at rows 42-43 and
    # running on to row 47 at the front, where the hatch housing stands out of it.
    hw = pchip([29.0, 29.5, 30.5, 31.5, 32.5, 34.0, 41.0, 42.5, 43.5, 44.5, 45.5, 46.5, 47.3, 47.9, 48.1],
               [0.0, 4.3, 6.75, 7.65, 8.0, 8.05, 8.05, 8.45, 7.55, 6.55, 5.55, 4.6, 2.4, 1.4, 0.0])
    cen = pchip([29.0, 41.0, 42.5, 45.5, 46.5, 47.3, 47.9, 48.1], [36.0, 36.0, 36.5, 36.5, 35.8, 34.3, 33.6, 33.5])

    def dome_st(r, pal, shrink=0.0):
        t = (DR - r) / DB if r < DR else (r - DR) / 10.9
        kh = max(0.0, 1 - min(1.0, t) ** 2.2) ** (1 / 2.2)
        return (r, cen(r), 0.0, max(0.0, hw(r) - shrink), 6.7 * kh - shrink, pal)
    rs = [29.0, 29.15, 29.4, 29.8, 30.3, 31.0, 31.8]
    st = [dome_st(r, 5) for r in rs]
    st += [dome_st(31.85, 131, 0.18), dome_st(33.3, 131, 0.18), dome_st(34.85, 131, 0.18), dome_st(34.9, 5)]
    st += [dome_st(r, 5) for r in (36.0, 37.2, 38.5, 39.7)]
    st += [dome_st(39.75, 2, 0.25), dome_st(40.25, 2, 0.25), dome_st(40.3, 3)]
    st += [dome_st(r, 3) for r in (41.5, 42.5, 43.5, 44.5, 45.5, 46.3, 46.9, 47.3, 47.6, 47.9, 48.05)]
    st[-1] = (48.1, cen(48.1), 0.0, 0.0, 0.0, 3)
    st[0] = (29.0, DC, 0.0, 0.0, 0.0, 5)
    loft_r(m, st, n=40, p=2.6, zmin=0.3)
    dsurf = surf_of(st, 2.6)

    def edge(r, side, inset_px):
        return cen(r) + side * (hw(r) - inset_px)
    # blue trim panels on the skirt either side of the hatch (rows 41-46)
    drape(m, 40.7, 45.4, lambda r: edge(r, -1, 0.35), lambda r: 33.6, dsurf, 0.14, 56, side_pal=3, nr=6, nc=4)
    drape(m, 40.7, 45.4, lambda r: 38.4, lambda r: edge(r, 1, 0.35), dsurf, 0.14, 56, side_pal=3, nr=6, nc=4)
    # front window on the band (rows 35-39, cols 35-37) in a raised frame
    drape(m, 35.1, 39.5, lambda r: 34.8, lambda r: 37.6, dsurf, 0.06, 133, nr=3, nc=3)
    for r0, r1, c0, c1 in ((34.8, 35.1, 34.4, 38.0), (39.5, 39.8, 34.4, 38.0), (35.1, 39.5, 34.4, 34.8),
                           (35.1, 39.5, 37.6, 38.0)):
        drape(m, r0, r1, lambda r, a=c0: a, lambda r, b=c1: b, dsurf, 0.22, 4, nr=2, nc=2)
    # hatch housing standing out of the front skirt (cols 34-38, rows 40-46) and its door
    prism(m, [(34.0, 39.4), (39.0, 39.4), (39.0, 45.9), (38.3, 46.8), (34.7, 46.8), (34.0, 45.9)], 0.3, 4.1, 0.5, 3)
    prism(m, rect(35.0, 40.6, 38.0, 45.8), 3.0, 4.35, 0.25, 4)
    # equipment pods on the dome's back (rows 29-31, the grey blocks either side of the boom)
    prism(m, [(31.0, 29.0), (33.4, 29.0), (33.8, 29.6), (33.8, 32.0), (28.5, 32.0), (28.7, 31.0), (29.6, 30.0)], 1.0, 4.9, 0.45, 5)
    prism(m, [(38.0, 29.0), (39.6, 29.0), (41.3, 30.0), (42.7, 31.0), (42.7, 32.4), (38.0, 32.4)], 1.0, 4.7, 0.45, 5)
    # pivot boss on the dome's top and the boom raking north from it to the clevis
    tube(m, [(33.3, 34.4, 6.3, 1.25), (37.9, 34.4, 6.3, 1.25)], 54, n=14)
    tube(m, [(35.3, 35.0, 6.2, 1.35), (35.3, 29.0, 8.2, 1.35), (35.3, 22.6, 10.0, 1.35)], 56, n=14)  # sprite: 55-58 blue
    for r, h in ((30.6, 7.95), (26.2, 9.35)):
        tube(m, [(35.3, r - 0.3, h - 0.1, 1.5), (35.3, r + 0.3, h + 0.1, 1.5)], 54, n=14)
    # hydraulic line beside the boom (col 37)
    tube(m, [(37.3, 33.0, 6.0, 0.62), (37.3, 29.0, 7.9, 0.62), (37.3, 23.6, 9.7, 0.62)], 54, n=8)
    # U clevis (rows 19-24) and its arms north to the head
    yoke = [(34.0, 19.45), (36.0, 19.45), (36.0, 20.0), (36.9, 20.0), (36.9, 20.75), (38.1, 20.75),
            (38.1, 19.9), (40.9, 19.9), (40.9, 20.9), (40.0, 21.0), (40.0, 22.9), (38.9, 24.0), (34.0, 24.0)]
    prism(m, yoke, 8.9, 10.9, 0.35, 5)
    tube(m, [(33.9, 22.3, 9.9, 0.42), (40.3, 22.3, 9.9, 0.42)], 4, n=8)  # cross pin
    tube(m, [(35.2, 20.2, 10.3, 0.7), (33.4, 16.0, 10.6, 0.7)], 5, n=10)
    tube(m, [(39.6, 20.2, 10.3, 0.6), (39.5, 15.2, 10.6, 0.6)], 5, n=10)
    # bracket under the head (rows 15-16, the dark strip) and the hammer head
    prism(m, [(31.0, 14.6), (36.0, 14.6), (36.0, 16.2), (33.6, 16.6), (32.4, 16.6), (31.0, 15.8)], 8.8, 10.2, 0.3, 4)
    prism(m, [(31.0, 10.0), (37.2, 10.0), (38.0, 11.0), (38.0, 15.2), (31.0, 15.2), (31.0, 14.8), (30.2, 14.8), (30.2, 11.8), (31.0, 11.8)], 9.0, 11.7, 0.4, 7)
    prism(m, [(36.0, 6.9), (40.4, 6.9), (41.4, 7.6), (41.4, 11.2), (40.4, 12.6), (36.0, 12.6)], 9.4, 11.8, 0.35, 3)
    prism(m, [(28.2, 7.0), (36.6, 7.0), (36.6, 10.6), (29.9, 10.6), (29.9, 10.3), (28.4, 10.3)], 10.2, 11.5, 0.3, 7)
    prism(m, rect(33.0, 7.9, 36.0, 14.6), 10.8, 12.1, 0.25, 134)
    prism(m, [(26.1, 4.0), (37.8, 4.0), (40.2, 6.4), (40.2, 7.4), (28.0, 7.6), (26.9, 7.7), (25.0, 7.0), (25.0, 5.1)],
          11.6, 13.0, 0.55, 7)
    prism(m, rect(31.0, 4.9, 37.0, 6.0), 12.9, 13.12, 0.05, 134)
    for c in (26.6, 28.4):
        prism(m, rect(c, 4.6, c + 0.8, 5.4), 12.9, 13.3, 0.12, 9)
    # the fin: a raked post from a foot on the floor carrying a folded blade (crease along c 43.6)
    def post_top(r):
        return 12.4 - (r - 8.0) * (11.4 / 20.4)
    st = [(r, c, post_top(r) - 1.0, a, 0.8, 57) for r, c, a in ((8.6, 44.6, 1.4), (14.0, 44.6, 1.4), (21.0, 44.6, 1.4),
                                                                 (22.6, 45.0, 1.0), (28.4, 45.0, 1.0))]
    loft_r(m, st, n=16, p=4)
    prism(m, rect(43.9, 26.4, 46.0, 28.3), 0.3, 1.1, 0.25, 56)
    west = pchip([8.0, 8.5, 9.5, 10.5, 11.5, 12.3, 14.2, 15.2, 16.2, 18.5, 19.6, 20.4, 21.2, 23.0],
                 [42.2, 41.6, 40.9, 40.2, 38.9, 37.5, 37.5, 38.0, 38.9, 39.3, 40.6, 42.2, 42.7, 42.9])
    east_f = pchip([8.0, 8.9, 9.4, 23.0], [44.9, 45.0, 46.0, 46.0])
    rows = [8.03, 8.4, 8.9, 9.2, 9.6, 10.3, 11.0, 11.7, 12.4, 13.2, 14.2, 15.2, 16.2, 17.2, 18.2, 19.2, 20.0,
            20.8, 21.6, 23.0]

    def plate(r0, r1, split, pal_a, pal_b):
        """One folded plate; bands north of `split` take pal_a, the rest pal_b."""
        rs = [r for r in rows if r0 <= r <= r1]
        top = []
        for r in rs:
            h = post_top(r) + 0.5
            top.append([m.v(west(r), r, h - 1.1), m.v(min(43.6, east_f(r) - 1.0), r, h + 0.35), m.v(east_f(r), r, h - 0.45)])
        bot = [[m.v(v.co.x, v.co.y, v.co.z - 0.7) for v in row] for row in top]
        for i in range(len(rs) - 1):
            pal = pal_a if (rs[i] + rs[i + 1]) / 2 < split else pal_b
            for j in range(2):
                m.f((top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j]), pal, False)
                m.f((bot[i][j], bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1]), pal, False)
            m.f((top[i][0], top[i + 1][0], bot[i + 1][0], bot[i][0]), pal, False)
            m.f((top[i][2], bot[i][2], bot[i + 1][2], top[i + 1][2]), pal, False)
        for row_t, row_b, flip, pal in ((top[0], bot[0], False, pal_a), (top[-1], bot[-1], True, pal_b)):
            for j in range(2):
                q = (row_t[j], row_t[j + 1], row_b[j + 1], row_b[j])
                m.f(q[::-1] if flip else q, pal, False)

    plate(8.03, 23.0, 14.2, 134, 57)
    # the bright crease: a ridge strip along the fold (rows 10-13.6) and its return along row 13
    drape(m, 9.9, 13.6, lambda r: 43.1, lambda r: 44.1, lambda c, r: post_top(r) + 0.5 + 0.35 - abs(c - 43.6) * 0.3,
          0.06, 158, nr=3, nc=1)
    drape(m, 13.0, 13.8, lambda r: 39.6, lambda r: 43.1,
          lambda c, r: post_top(r) + 0.5 + 0.35 - (43.6 - c) * (1.45 / (43.6 - west(r))), 0.06, 158, nr=1, nc=3)


# --- the floor ---------------------------------------------------------------------------------

def load_grid():
    g = [[-1] * 48 for _ in range(84)]
    inner = [["."] * 48 for _ in range(84)]
    for name, (c0, r0) in ORIGIN.items():
        data = common.load_sprite(ROOT, name)
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                g[r0 + r][c0 + c] = v
        out = subprocess.check_output(["python3", str(ROOT / "tools" / "sprite_mask.py"), name, "--json"])
        for r, row in enumerate(json.loads(out)["masks"]):
            for c, ch in enumerate(row):
                inner[r0 + r][c0 + c] = ch
    return g, inner


def rects(cells):
    """Greedy merge of a set of (c, r) cells into rectangles (c0, r0, c1, r1)."""
    todo = set(cells)
    out = []
    for r in range(84):
        for c in range(48):
            if (c, r) not in todo:
                continue
            c1 = c
            while (c1 + 1, r) in todo:
                c1 += 1
            r1 = r
            while all((k, r1 + 1) in todo for k in range(c, c1 + 1)):
                r1 += 1
            for rr in range(r, r1 + 1):
                for k in range(c, c1 + 1):
                    todo.discard((k, rr))
            out.append((c, r, c1 + 1, r1 + 1))
    return out


def floor(m, g, inner, c0, r0):
    e = 0.002  # stay a hair inside the block so a neighbour's cut leaves no sliver
    slab = set()
    for r in range(r0, r0 + 28):
        for c in range(c0, c0 + 24):
            if inner[r][c] == "o" and g[r][c] in FLOOR_IDX:
                continue  # dark floor at the block's edge counts as ink: the slab stops inside it
            slab.add((c, r))
    for a, b, cc, d in rects(slab):
        prism(m, rect(max(a, c0 + e), max(b, r0 + e), min(cc, c0 + 24 - e), min(d, r0 + 28 - e)), 0.0, 0.28, 0.0, 97)
    for idx, (h, pal) in {99: (0.42, 99), 100: (0.42, 100), 101: (0.62, 101), 102: (0.62, 102)}.items():
        cells = [(c, r) for (c, r) in slab if g[r][c] == idx]
        for a, b, cc, d in rects(cells):
            prism(m, rect(max(a, c0 + e) + 0.04, max(b, r0 + e) + 0.04, min(cc, c0 + 24 - e) - 0.04,
                          min(d, r0 + 28 - e) - 0.04), 0.2, h, 0.08, pal, bottom=False)


def seams(m, which):
    """Dark floor seams where the sprite draws them (not the objects' outline rings)."""
    lists = {
        "floor55": [(12, 71, 13, 78), (11, 76, 12, 77), (13, 78, 18, 79), (9, 71, 10, 73), (16, 71, 17, 73),
                    (6, 71, 7, 72), (20, 79, 21, 80), (21, 61, 22, 62), (21, 64, 22, 65), (21, 67, 22, 68)],
        "floor283": [(34, 49, 35, 50), (34, 50, 45, 51), (34, 51, 35, 52), (42, 51, 43, 53), (36, 29, 37, 32)],
    }
    for c0, r0, c1, r1 in lists[which]:
        prism(m, rect(c0 + 0.1, r0 + 0.1, c1 - 0.1, r1 - 0.1), 0.18, 0.32, 0.0, 1)


# --- to Blender --------------------------------------------------------------------------------

def to_object(m, mats_by_pal, coll):
    bm = m.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    M = Matrix(((PX, 0, 0, -48 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pals = sorted({f[m.pal] for f in bm.faces})
    me = bpy.data.meshes.new(m.name)
    slots = {}
    for p in pals:
        slots[p] = len(me.materials)
        me.materials.append(mats_by_pal[p])
    for f in bm.faces:
        f.material_index = slots[f[m.pal]]
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(m.name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def materials(sprite):
    out = {}
    for idx, (met, rough, em) in PROPS.items():
        if str(idx) not in sprite["colors"]:
            continue
        out[idx] = common.palette_material(sprite, idx, "nshc283B", metallic=met, roughness=rough,
                                           emission_strength=em)
    return out


def merged_sprite():
    data = common.load_sprite(ROOT, "newshc-283")
    for name in PIECES + ["newshc-77"]:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    # sprite medians of regions that sit between the indices these frames draw (same palette ramps
    # as newsh5-270 and newsh-caret-208): the crane boom's 55 and the vent pads' 68.
    data["colors"].setdefault("55", [28, 69, 93])
    data["colors"].setdefault("68", [85, 28, 16])
    return data


def join(objs, name, coll):
    bm = bmesh.new()
    me = bpy.data.meshes.new(name)
    mats = []
    for o in objs:
        for mt in o.data.materials:
            if mt not in mats:
                mats.append(mt)
    for mt in mats:
        me.materials.append(mt)
    for o in objs:
        tmp = o.data.copy()
        remap = [mats.index(mt) for mt in o.data.materials]
        for p in tmp.polygons:
            p.material_index = remap[p.material_index]
        tmp.transform(o.matrix_world)
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def outline_shell_all(obj, collection, voxel=0.015, faces=8000, smooth=6):
    """common.outline_shell (D51) keeping EVERY outer island, not only the widest one (D189): the half
    machine is two separate objects (pillar, crane on its floor), and the stock shell kept the
    pillar only, so the crane pieces (newshc-245/-283) shipped an empty outline. Its own copy here
    dropped an island whose 3D bbox lay inside another's, which also took outer parts sitting in a
    ring's box (newshc-17's disc); "outer" drops only inner (negative volume) shells, flat sheets and
    lone voxels. min_new_px=0: the rings stacked on the tower keep their own ink, as they had."""
    return common.outline_shell(obj, collection, voxel=voxel, faces=faces, smooth=smooth, islands="outer",
                                min_new_px=0)


def bake_pieces(pieces, lay, coll, size=512):
    """AO / roughness / metallic bake per piece (D50), each into its own small atlas, so a piece's
    GLB carries only its own texels (one 1024 px half-machine atlas per piece was 255-425 KB each).
    Each piece gets its own copies of the palette materials (names still pal_<n>_..., D7). The
    pieces stand at their places in the machine while baking, so the occlusion still sees the
    neighbours; the half, the groups and the outline shells are left out of the bake."""
    flat = {158, 131, 133, 134, 71, 68, 69}
    keep_tex, keep_tint = T.TEXTURED, T.TINT
    scene = bpy.context.scene
    hidden = {o: o.hide_render for o in scene.objects}
    names = {n for n, _, _ in lay}
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o.name not in names
    for name, cx, cy in lay:
        pieces[name].location = (cx / 12, -cy / 12, 0)
    try:
        for name, cx, cy in lay:
            p = pieces[name]
            tag = name.split("-")[1]
            for i, mt in enumerate(list(p.data.materials)):
                cp = mt.copy()
                cp.name = f"{mt.name}_{tag}"
                p.data.materials[i] = cp
            T.TEXTURED = tuple(i for i, mt in enumerate(p.data.materials) if int(mt.name.split("_")[1]) not in flat)
            T.TINT = (1.0, 1.0, 1.0)
            T.bake_maps(p, Path(tempfile.mkdtemp(prefix=f"nshc283_bake_{tag}_")), size=size, samples=64)
            for img in bpy.data.images:
                if img.name.startswith(("talon_colour", "talon_rm")):
                    img.name = f"nshc{tag}_" + img.name.split(".")[0].split("_")[1]
    finally:
        T.TEXTURED, T.TINT = keep_tex, keep_tint
        for o, h in hidden.items():
            o.hide_render = h
        for name, _, _ in lay:
            pieces[name].location = (0, 0, 0)


def split_open(obj, layout, coll):
    """common.split_assembly's cut without capping (outline shells: no ink line at the seams)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-6)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_area() < 1e-12], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        if me.validate(clean_customdata=False):
            print(f"outline {name}: mesh validated and fixed")
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out



# --- measuring and views -----------------------------------------------------------------------

def setup_workbench(scene, flat=False):
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.color_type = "MATERIAL"
    if flat:
        sh.light = "FLAT"
        sh.show_cavity = False
        sh.show_object_outline = False
        sh.show_specular_highlight = False
        scene.display.render_aa = "OFF"
    else:
        sh.light = "STUDIO"
        sh.show_cavity = True
        sh.cavity_type = "BOTH"
        sh.show_object_outline = False
        sh.show_specular_highlight = True
        scene.display.render_aa = "8"
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0.02, 0.025, 0.035)


def setup_eevee(scene):
    """A look closer to the game's: one sun from the upper left (the sprites' light), soft ambient."""
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.view_settings.view_transform = "Standard"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.32, 0.34, 0.38, 1)
    bg.inputs["Strength"].default_value = 1.0
    if "v_sun" not in bpy.data.objects:
        sun = bpy.data.lights.new("v_sun", "SUN")
        sun.energy = 3.2
        sun.angle = math.radians(8)
        o = bpy.data.objects.new("v_sun", sun)
        scene.collection.objects.link(o)
        o.rotation_euler = (math.radians(38), math.radians(-22), math.radians(-30))
        fill = bpy.data.lights.new("v_fill", "SUN")
        fill.energy = 0.8
        f = bpy.data.objects.new("v_fill", fill)
        scene.collection.objects.link(f)
        f.rotation_euler = (math.radians(-50), math.radians(30), math.radians(150))


def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    data.clip_end = 500
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return cam


def render(scene, cam, objs, path, res, transparent=False):
    for o in scene.objects:
        if o.type == "MESH":
            o.hide_render = o not in objs
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


# --- the tower: built in the art's frame, exported upright ------------------------------------------

A, KT, VB = TG.A, TG.K, TG.VB      # sin and cos of the art camera's 15 deg; the axis's plan row
ART_ELEV = 15.0
HOFF = 8 * KT                      # rigid frame: the base's north foot at h = 0
Y_TOP = 100.0                      # px of true height mapped to the top of the depth band (the head reaches 98)
BAND = (0.0, 0.4)                  # units: the depth band (D165), under background 2 mid (0.45 above ground enemies, D5)
TOWER = {"newshc-115": 0, "newshc-17": 28, "newshc-55": 56}   # piece -> r0 (rows of this file's frame)
CRANE = {"newshc-245": (24, 0), "newshc-283": (24, 28)}
HEAD_FRAMES = [77, 79, 81, 83, 85, 87, 89, 91]
REF91 = Path("/Users/dlomibao/projects/tyrian-scratch/e1-enemies-2/newshc-77/blueprint/ref91")

# palette index -> (metallic, roughness) for the tower and head; satin steel, painted reds
TPROPS = {1: (0.0, 0.9), 2: (0.1, 0.8), 3: (0.3, 0.6), 4: (0.4, 0.5), 5: (0.45, 0.42), 6: (0.45, 0.42),
          7: (0.45, 0.4), 8: (0.45, 0.4), 9: (0.45, 0.4), 16: (0.2, 0.6), 66: (0.1, 0.55), 67: (0.1, 0.5),
          69: (0.1, 0.5), 70: (0.1, 0.45), 71: (0.12, 0.45), 72: (0.15, 0.45), 73: (0.15, 0.45),
          75: (0.1, 0.4), 97: (0.25, 0.75), 112: (0.0, 0.5), 114: (0.0, 0.5), 118: (0.0, 0.5)}


def head_name(fr):
    i = HEAD_FRAMES.index(fr)
    return "newshc-77" if i == 0 else f"newshc-77-f{i + 1}"


def lock(p):
    """True tower point (u, v, z) -> the art's frame in this file's sprite px (c, r, h): the rigid turn
    that puts the art camera overhead (its plan is the art's picture, its height the art's depth)."""
    u, v, z = p
    s = VB + A * (v - VB) - KT * z
    return (u, s - 28, KT * (v - VB) + A * z + HOFF)


M_CUR = Matrix(((PX, 0, 0, -48 * PX), (0, -PX, 0, 28 * PX), (0, 0, PX, 0), (0, 0, 0, 1)))


class Mats:
    def __init__(self, sprite, tag, props=None):
        self.sprite, self.tag, self.cache, self.props = sprite, tag, {}, props or {}

    def get(self, pal, glow=0.0, floor=False):
        key = (pal, round(glow, 2), floor)
        if key not in self.cache:
            met, rough = self.props.get(pal, TPROPS.get(pal, (0.3, 0.5)))
            t = self.tag + (f"g{int(glow * 100)}" if glow else "") + ("fl" if floor else "")
            mt = common.palette_material(self.sprite, pal, t, metallic=met, roughness=rough, emission_strength=glow)
            if glow:
                mt["flat"] = True
            if floor:
                mt["tyrian_floor"] = True
            self.cache[key] = mt
        return self.cache[key]


def parts_object(name, parts, mats, coll, xform, matrix, floor=False):
    """Triangle parts -> one mesh object (vertices welded per part, so lathes shade smooth)."""
    bm = bmesh.new()
    slots, mlist = {}, []
    for part in parts:
        mt = mats.get(part["pal"], part["glow"], floor)
        if mt.name not in slots:
            slots[mt.name] = len(mlist)
            mlist.append(mt)
        idx = slots[mt.name]
        vmap = {}

        def vert(p):
            q = xform(p)
            key = (round(q[0], 4), round(q[1], 4), round(q[2], 4))
            if key not in vmap:
                vmap[key] = bm.verts.new(q)
            return vmap[key]
        for tri in part["tris"]:
            vs = [vert(p) for p in tri]
            if len({id(v) for v in vs}) < 3:
                continue
            try:
                f = bm.faces.new(vs)
            except ValueError:
                continue
            f.material_index = idx
            f.smooth = part["smooth"]
    bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    for mt in mlist:
        me.materials.append(mt)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.set_sharp_from_angle(angle=math.radians(34))
    return obj


def ground_parts():
    """The tower's true ground (a disc round the foot): AO occluder only, deleted before export."""
    G = TG.Geo()
    n = 48
    ring = [TG.P(2 * math.pi * k / n, 15.0, -0.02) for k in range(n)]
    tris = []
    TG.Geo.cap_fan(tris, ring, (TG.CU, VB, -0.02))
    G.add("ground", 97, tris)
    return G.parts


def cut_bands(obj, bands, coll, cap=True, suffix=""):
    """Cut obj (art frame, Blender coords) into bands of rows [r0, r1) (None = open end), in place:
    the sprite's 24x28 pieces are bands of screen rows."""
    out = {}
    for name, (r0, r1) in bands.items():
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for r, keep_south in ((r0, True), (r1, False)):
            if r is None:
                continue
            y = (28 - r) * PX
            no = (0, 1, 0) if keep_south else (0, -1, 0)
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, y, 0), plane_no=no, clear_outer=True)
            if cap:
                edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
                if edges:
                    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def delete_floor(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    fl = {i for i, mt in enumerate(obj.data.materials) if mt and mt.get("tyrian_floor")}
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in fl], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()


def bake_tower(targets, occluders, size=512, samples=64):
    """AO / roughness bake from the model itself (D50, D65; no projection): each target into its own
    small atlas, the occluders visible. Each target gets its own copies of its materials."""
    scene = bpy.context.scene
    keep_tex, keep_tint = T.TEXTURED, T.TINT
    hidden = {o: o.hide_render for o in scene.objects}
    try:
        for tgt in targets:
            vis = [tgt] + [o for o in occluders if o is not tgt]
            for o in scene.objects:
                if o.type == "MESH":
                    o.hide_render = o not in vis
            tag = tgt.name.replace("newshc-", "")
            for i, mt in enumerate(list(tgt.data.materials)):
                cp = mt.copy()
                cp.name = f"{mt.name}_{tag}"
                tgt.data.materials[i] = cp
            T.TEXTURED = tuple(i for i, mt in enumerate(tgt.data.materials) if not mt.get("flat"))
            T.TINT = (1.0, 1.0, 1.0)
            T.bake_maps(tgt, Path(tempfile.mkdtemp(prefix=f"t283_{tag}_")), size=size, samples=samples)
            for img in bpy.data.images:
                if img.name.startswith(("talon_colour", "talon_rm")):
                    img.name = f"t283{tag}_" + img.name.split(".")[0].split("_")[1]
    finally:
        T.TEXTURED, T.TINT = keep_tex, keep_tint
        for o, h in hidden.items():
            o.hide_render = h


def art_view(r0):
    """The extras of a piece whose 24x28 block starts at row r0 (glTF/three coordinates: z south, y
    up, the piece's centre the origin): `tyrian_oblique` [k, squeeze, axis_z] and `tyrian_depth_band`
    [lo, hi, y0, y1] (src/render/obliqueView.ts). Every piece and head frame shares [y0, y1], so
    their depths agree where they meet."""
    e = math.radians(ART_ELEV)
    return {"tyrian_oblique": [math.cos(e), math.sin(e), (VB - 42 - r0) * PX],
            "tyrian_depth_band": [BAND[0], BAND[1], 0.0, Y_TOP * PX]}


def stand(obj, r0, c0=0, normals=True):
    """A copy of an art-frame piece turned back upright, about its own centre (the export): every
    vertex back to the true tower (u, v, z), and the art frame's corner normals turned with it."""
    me = obj.data.copy()
    name = obj.name
    obj.name = name + "_art"
    o = bpy.data.objects.new(name, me)
    for k in obj.keys():
        o[k] = obj[k]
    bpy.context.scene.collection.objects.link(o)
    cn = None
    if normals:
        me.set_sharp_from_angle(angle=math.radians(34))
        cn = []
        for c in me.corner_normals:
            nx, ny, nz = c.vector
            ns, nh = -ny, nz                       # art frame: south, up
            ndv, nzt = A * ns + KT * nh, -KT * ns + A * nh
            cn.append(Vector((nx, -ndv, nzt)))
    for v in me.vertices:
        x, y, zz = v.co
        c, s, h = 12 * x + 48, 28 - 12 * y + 28, 12 * zz
        ds, dh = s - VB, h - HOFF
        dv, z = A * ds + KT * dh, -KT * ds + A * dh
        v.co = ((c - (c0 + 12)) * PX, -(VB + dv - 42 - r0) * PX, z * PX)
    if cn is not None:
        me.normals_split_custom_set(cn)
    me.update()
    for k, v in art_view(r0).items():
        o[k] = v
    return o


def game_form(obj, name=None):
    """What the game draws for an upright piece, seen from straight above (src/render/obliqueView.ts,
    in Blender coordinates): a copy with each vertex at the art's point (x, axis_z + sin e (z -
    axis_z) - cos e y), at its height squeezed into the depth band, for measuring and the game-camera
    views. Normals stay the real tower's, as in the game."""
    k, sq, az = obj["tyrian_oblique"]
    lo, hi, y0, y1 = obj["tyrian_depth_band"]
    me = obj.data.copy()
    for v in me.vertices:
        X, Y, Z = v.co
        z3, y3 = -Y, Z
        t = min(1.0, max(0.0, (y3 - y0) / (y1 - y0)))
        v.co = (X, -(az + sq * (z3 - az) - k * y3), lo + t * (hi - lo))
    me.update()
    o = bpy.data.objects.new(name or obj.name + "_game", me)
    bpy.context.scene.collection.objects.link(o)
    o.location = obj.location
    return o


def centre_of(r0, c0=0):
    return ((c0 + 12 - 48) * PX, (28 - (r0 + 14)) * PX)


def tower_plan_trim(obj):
    """Two sub-pixel trims of the art's picture of the tower (art frame, so the upright model keeps
    them as slight in-plane squashes): the west access hatch's frame stands 0.3 px proud of the
    foot's silhouette, where the sprite draws the column's ink (col 3, rows 57-64), so its vertices
    stop at the column's edge; and the foot's front lip ends on its ink row (row 69, the sprite's
    s 97), not half a pixel into it."""
    west = float(os.environ.get("T283_WEST", "4.03"))
    foot = float(os.environ.get("T283_FOOT", "97.05"))
    for v in obj.data.vertices:
        c, srow = v.co.x / PX + 48, 56 - v.co.y / PX
        if 84.0 < srow < 93.5 and c < west:
            v.co.x = (west - 48) * PX
        if srow > foot:
            v.co.y = (56 - foot) * PX
    obj.data.update()


def build_tower(sprite, coll):
    """The tower body in the art frame (culled inside only), its ground disc (bake occluder), and
    the outline shell; cut into the three pieces."""
    mats = Mats(sprite, "t283")
    body = parts_object("tower_body", TG.build(None, True), mats, coll, lock, M_CUR)
    tower_plan_trim(body)
    T.cull_hidden(body)
    ground = parts_object("tower_ground", ground_parts(), mats, coll, lock, M_CUR, floor=True)
    body_g = join([body, ground], "tower_body_g", coll)
    bands = {"newshc-115": (None, 28), "newshc-17": (28, 56), "newshc-55": (56, None)}
    pieces = cut_bands(body_g, bands, coll, cap=True)
    shell = outline_shell_all(body, coll, voxel=0.015, faces=9000, smooth=6)
    shells = cut_bands(shell, bands, coll, cap=False, suffix="_outline")
    for s in shells.values():
        s["tyrian_outline"] = True
        s.data.shade_smooth()
    return mats, body, pieces, shells


REF129 = Path("/Users/dlomibao/projects/tyrian-scratch/demo-models/assembly-newshc-283/ref129")
SHEET129 = [{"sheet": "newshc.shp", "size": 2, "frames": [129]}]


def burnt_parts():
    """newshc.shp frame 129: the tower's top piece (newshc-115) once its head is destroyed (the
    piece's enemy record: dgr 129). Without a model of its own D87 drew it with the intact 115
    model, whose lit steel rim read light grey where the sprite draws a black burnt hull. The same
    tower, burnt where the sprite changes (rows 0-4 and 17-22 of the piece; screen row s = row +
    28): the cup's lip soot black (pal 2), the cup's top band down to the vents' middle scorched
    (pal 3; the vents' upper louvres buried under it, west 4 / east 2, the sprite's rows 2-3), and a
    blast scar on drum 0's west shoulder (pal 1 hole in a pal 3 halo; rows 19-22, cols 5-8). Thin
    skins over the lathe, inside its plan, so the outline is the intact piece's."""
    parts = TG.build(None, True)
    for p in parts:
        if p["name"] == "cup_rim":
            p["pal"] = 2
    G = TG.Geo()
    zt = TG.Z_TOP
    R = TG.Rcol

    def zrow(s, th, r=8.0):
        """The height whose point on the skin at azimuth th the art draws on screen row s."""
        return TG.zOf(s) + A * r * math.cos(th) / KT
    sb = float(os.environ.get("T129_SOOT", "31.8"))    # the soot's lower edge (screen row, front)
    G.patch("soot_band", 3, R, -1.38, 1.38, zrow(sb, 0.0), zt - 0.02, 0.12)
    G.patch("soot_vent_w", 4, R, -0.88, -0.26, zrow(sb, 0.57), zt - 0.3, 0.62)
    G.patch("soot_vent_e", 2, R, 0.18, 0.88, zrow(sb, 0.53), zt - 0.3, 0.62)
    G.patch("scar_halo", 3, R, -1.16, -0.30, zrow(51.0, 0.73), zrow(45.9, 0.73), 0.06)
    G.patch("scar_hole", 1, R, -1.02, -0.44, zrow(50.4, 0.73), zrow(46.8, 0.73), 0.12)
    return parts + G.parts


def burnt_lip_trim(obj):
    """Frame 129 draws the cup's burnt lip in ink (its row 0 and the corners of row 1 are pal 1 at
    the edge), where 115 draws it lit: the game's own ink goes there, so the model's picture ends a
    row lower. The art's rows above row 3 of the piece are pressed into [T129_TOP, 3] (art frame:
    the upright model keeps it as a slight squash of the lip, under a pixel)."""
    top = float(os.environ.get("T129_TOP", "0.9"))
    rows = [28 - v.co.y / PX for v in obj.data.vertices]
    r0 = min(rows)
    if r0 >= top:
        return
    for v, r in zip(obj.data.vertices, rows):
        if r < 3.0:
            r2 = 3.0 - (3.0 - r) * (3.0 - top) / (3.0 - r0)
            v.co.y = (28 - r2) * PX
    obj.data.update()


def build_burnt(sprite, coll):
    """Frame 129's piece: the burnt tower in the art frame cut to the top band, with its own outline
    shell (the same plan as newshc-115's)."""
    mats = Mats(sprite, "t129")
    body = parts_object("tower_body129", burnt_parts(), mats, coll, lock, M_CUR)
    tower_plan_trim(body)
    burnt_lip_trim(body)
    T.cull_hidden(body)
    piece = cut_bands(body, {"newshc-129": (None, 28)}, coll, cap=True)["newshc-129"]
    shell = outline_shell_all(body, coll, voxel=0.015, faces=9000, smooth=6)
    pshell = cut_bands(shell, {"newshc-129": (None, 28)}, coll, cap=False, suffix="_outline")["newshc-129"]
    pshell["tyrian_outline"] = True
    pshell.data.shade_smooth()
    return piece, pshell


WRECK_ROD_R = float(os.environ.get("T283_ROD", "0.56"))   # the wreck's feed rod: 1 px in the sprite (col 13)
BALL_P = float(os.environ.get("T283_BALLP", "2.0"))      # the ball's plan: superellipse exponent (2 = round)


# Frame 91's burnt hull (report #11): the sprite draws the collar black (pal 1 inside, rows 21-27)
# with grey edges only where the light catches it (the torn top, pal 8). The liner, the ram's stub,
# the torn hood scraps and the collar's outer wall were steel greys (pal 3-5) and read as a grey drum:
# the inside is now pal 1, the scraps pal 2, the burnt outer wall and its band pal 3, and the feed
# rod's lower leg inside the hull pal 3 (sprite cols 14-15, rows 20-24: 1-3); its upper leg stays 7.
WRECK_PAL = {"rod_lo": 3, "stump": 3, "collar_band-1": 3, "collar_band1": 3, "stump_rim": 8, "torn_liner": 1,
             "ram_stub": 1, "torn_plate0": 2, "torn_plate1": 2, "torn_plate2": 2}


def wreck_extra():
    """Frame 91 additions to the lib's wreck: the collar's burnt bore floor (pal 1: the sprite's dark
    interior, rows 24-26), which the torn-away front lets the art see; without it the plan has a
    hole there. And the bent feed rod's upper leg a little thicker (the sprite draws it 1 px wide)."""
    G = TG.Geo()
    cu, n, zb = 12.5, 36, 70.1
    dz = float(os.environ.get("T283_BORE_Z", "0.9"))   # its height over the collar's foot (px)
    rs = float(os.environ.get("T283_BORE_S", "0.6"))   # its south reach (px): it stops at the torn lip's ink row
    ring = []
    for k in range(n):
        t = 2 * math.pi * k / n
        ring.append((cu + 4.3 * math.sin(t), VB + (rs if math.cos(t) > 0 else 4.3) * math.cos(t), zb + dz))
    tris = []
    TG.Geo.cap_fan(tris, ring, (cu, VB, zb + dz))
    G.add("bore_floor", 1, tris)
    ru = float(os.environ.get("T283_ROD_U", "13.5"))
    kink = (ru, VB, float(os.environ.get("T283_KINK", "76.6")))
    rt = float(os.environ.get("T283_ROD_TOP", "81.0"))
    # the rod's kink and upper leg (replacing the lib's rod_kink / rod_hi): straight up sprite col 13
    d0 = (-0.5, 1.0, 4.8)
    ln = math.dist((0, 0, 0), d0)
    mid = tuple(a + b * 4.6 / ln for a, b in zip((15.0, VB - 1.0, 73.0), d0))
    G.tube("rod_kink", 7, mid, TG.sub(kink, mid), math.dist(kink, mid), 0.5, WRECK_ROD_R, n=10)
    G.tube("rod_hi", 7, kink, (0.0, 0.0, 1.0), rt - kink[2], WRECK_ROD_R, WRECK_ROD_R - 0.05, n=10)
    # the collar's lower band a hair fuller (the sprite's collar is 9 px across at rows 24-26)
    sr = float(os.environ.get("T283_SLEEVE", "4.5"))
    # a torn liner plate inside the collar's back: its jagged top is where the sprite's dark interior
    # starts (row 21 behind the rod, 22 to the west and east)
    if os.environ.get("T283_LINER", "1") == "1":
        tgt = TG.pchip([10.0, 11.0, 11.6, 12.2, 13.0, 14.0, 15.0, 15.6, 16.0, 16.3],
                       [22.3, 22.1, 21.8, 21.05, 20.8, 20.3, 20.5, 20.95, 21.5, 22.2])
        us = [10.3 + 5.6 * k / 16 for k in range(17)]
        tris = []
        for vv, flip in ((VB - 3.0, False), (VB - 3.3, True)):
            bot = [(u, vv, zb + 0.3) for u in us]
            top = [(u, vv, (VB + A * (vv - VB) - tgt(u)) / KT + (0.25 if k % 2 else -0.1)) for k, u in enumerate(us)]
            t = []
            TG.Geo.strip(t, bot, top, closed=False)
            tris += [[q[0], q[2], q[1]] for q in t] if flip else t
        G.add("torn_liner", 3, tris, smooth=False)
    b0 = float(os.environ.get("T283_BAND0", "0.6"))
    for side in (-1, 1):   # on its flanks only: its front is the torn lip (the ink row 27)
        a0 = float(os.environ.get("T283_BANDA", "1.0"))
        ts = [side * (a0 + (2.4 - a0) * k / 12) for k in range(13)]
        lo = [TG.P(t, sr, zb + b0, cu) for t in ts]
        hi = [TG.P(t, sr, zb + b0 + 1.8, cu) for t in ts]
        tris = []
        TG.Geo.strip(tris, lo, hi, closed=False)
        G.add(f"collar_band{side}", 5, tris if side > 0 else [[q[0], q[2], q[1]] for q in tris])
    return G.parts


def soot_normals(obj):
    """The wreck's soot (pal 1-3 faces of the upright export; frame 91 and frame 129's piece): shading normals bent up toward the
    sky by T91_UP (custom split normals; positions untouched). Inside the torn collar the faces
    stand upright facing south, which the game's overhead camera sees edge-on, where the lit
    material's Fresnel reflection turned the black hull mid grey; bent up, the soot stays black as
    the sprite draws it. The lit grey edges (pal 5-8) keep the tower's normals."""
    k = float(os.environ.get("T91_UP", "2.0"))
    if k <= 0:
        return
    me = obj.data
    dark = {i for i, mt in enumerate(me.materials) if mt and int(mt.name.split("_")[1]) in (1, 2, 3)}
    cn = [Vector(c.vector) for c in me.corner_normals]
    for poly in me.polygons:
        if poly.material_index in dark:
            for li in poly.loop_indices:
                cn[li] = (cn[li] + Vector((0, 0, k))).normalized()
    me.normals_split_custom_set(cn)
    me.update()


def ball_plan(obj, fr):
    """The ball's plan (the art's picture) a touch squarer than a circle, as the sprite draws it
    (superellipse exponent BALL_P): every vertex of the head within the ball's reach is pushed out
    radially in the plan about the ball's centre, the most on the diagonals."""
    if BALL_P <= 2.0 or fr == 91:
        return
    zc = TG.ZC0 + TG.HEAD[fr]["lift"] / KT
    c, r, _ = lock((TG.CU, TG.VB, zc))
    cx, cy = (c - 48) * PX, (28 - r) * PX
    R = TG.RB * PX
    for v in obj.data.vertices:
        dx, dy = v.co.x - cx, v.co.y - cy
        d = math.hypot(dx, dy)
        if d < 1e-6:
            continue
        ca, sa = abs(dx) / d, abs(dy) / d
        f = (ca ** BALL_P + sa ** BALL_P) ** (-1 / BALL_P)
        w = min(1.0, max(0.0, (d / R - 0.4) / 0.5)) * min(1.0, max(0.0, (R * 1.35 - d) / (R * 0.3)))
        k = 1 + (f - 1) * w
        v.co.x, v.co.y = cx + dx * k, cy + dy * k
    obj.data.update()


def build_heads(sprite, coll):
    mats = Mats(sprite, "t77")
    # the wreck's soot is matte: no metal, full roughness on its dark greys (in the game's overhead
    # view the hull's south faces are seen edge-on, and satin steel there reflected the sky as grey)
    mats91 = Mats(sprite, "t77w", {p: (0.0, 1.0) for p in (1, 2, 3)})
    heads, shells = {}, {}
    for fr in HEAD_FRAMES:
        parts = TG.build(fr, False)
        if fr == 91:
            # the lib's lugs under the collar poke out below its torn lip (the sprite's ink row 27)
            drop = ("rod_kink", "rod_hi") + tuple(os.environ.get("T283_DROP", "lug0,lug1").split(","))
            parts = [p for p in parts if p["name"] not in drop] + wreck_extra()
            for p in parts:   # the burnt hull: the sprite's black (rows 21-27 are pal 1 inside grey edges)
                p["pal"] = WRECK_PAL.get(p["name"], p["pal"])
        h = parts_object(head_name(fr), parts, mats91 if fr == 91 else mats, coll, lock, M_CUR)
        ball_plan(h, fr)
        T.cull_hidden(h)
        heads[fr] = h
        sh = outline_shell_all(h, coll, voxel=0.012 if fr != 91 else 0.01, faces=1800, smooth=6 if fr != 91 else 3)
        sh.name = sh.data.name = f"{h.name}_outline"
        sh["tyrian_outline"] = True
        shells[fr] = sh
    return heads, shells


def make_ref(outdir, name, rows_below=99, skip_top=()):
    """A piece's sprite without its floor (D130: the floor is the HD ground's, not the model's): the
    floor pixels (indices 96-102) reached from the piece's edge through floor pixels, and every row
    from `rows_below` (newshc-55: the tile's ground rows). A flood, not an index test: the crane
    shades its own steel with the same greys (99-101 inside its ink), which are the machine's.
    `skip_top`: top-edge columns where the machine runs on into the piece above (no seed there)."""
    d = json.loads((ROOT / f"reference/models/{name}/sprite.json").read_text())
    for f in d["frames"]:
        P = [[int(x) for x in row.split()] if isinstance(row, str) else list(row) for row in f["pixels"]]
        H, W = len(P), len(P[0])
        fl = [[False] * W for _ in range(H)]
        todo = [(r, c) for r in range(H) for c in range(W)
                if P[r][c] in FLOOR_IDX and (c in (0, W - 1) or r == H - 1 or (r == 0 and c not in skip_top))]
        while todo:
            r, c = todo.pop()
            if fl[r][c] or P[r][c] not in FLOOR_IDX:
                continue
            fl[r][c] = True
            todo += [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)) if 0 <= r + dr < H and 0 <= c + dc < W]
        rows = []
        for r, row in enumerate(f["pixels"]):
            vals = [-1 if (fl[r][c] or r >= rows_below) else P[r][c] for c in range(W)]
            rows.append(" ".join(str(v) for v in vals) if isinstance(row, str) else vals)
        f["pixels"] = rows
    p = Path(outdir) / "ref" / name
    p.mkdir(parents=True, exist_ok=True)
    (p / "sprite.json").write_text(json.dumps(d))
    return p.parent


def measure_items(items, outdir):
    """items: [(label, sprite name, frame or None, ref dir or None, obj at its own origin)]: top-view
    IoU (sprite_mask.py --measure) and the palette index per region seen from above."""
    import numpy as np
    scene = bpy.context.scene
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    k = 8
    mats = sorted({mt for it in items for mt in it[4].data.materials if mt}, key=lambda m: m.name)
    saved = {mt: tuple(mt.diffuse_color) for mt in mats}
    pal_of = {}
    for i, mt in enumerate(mats):
        idx = int(mt.name.split("_")[1])
        col = ((i * 37 % 256) / 255, (i * 91 % 256) / 255, ((i * 53 + 40) % 256) / 255)
        mt.diffuse_color = (*col, 1)
        enc = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in col]
        pal_of[tuple(round(v * 255) for v in enc)] = idx
    setup_workbench(scene, flat=True)
    keys = list(pal_of.keys())
    arr = np.array(keys, dtype=np.float32)
    results = {}
    for label, name, frame, ref, obj in items:
        loc = obj.location.copy()
        obj.location = (0, 0, 0)
        cam = camera(scene, "m_top", (0, 0, 20), (0, 0, 0), ortho=28 / 12)
        cam.rotation_euler = (0, 0, 0)
        path = render(scene, cam, [obj], outdir / f"top_{label}.png", (24 * k, 28 * k), transparent=True)
        obj.location = loc
        bpy.data.objects.remove(cam, do_unlink=True)
        cmd = ["python3", str(ROOT / "tools" / "sprite_mask.py"), name, "--measure", str(path), "--json"]
        if frame is not None:
            cmd += ["--frame", str(frame)]
        if ref:
            cmd += ["--ref", str(ref)]
        out = subprocess.check_output(cmd)
        res = json.loads(out) if out.strip().startswith(b"{") else out.decode()
        if isinstance(res, dict) and "measure" in res:
            res = res["measure"]
        img = bpy.data.images.load(str(path))
        px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[::-1]
        bpy.data.images.remove(img)
        idxmap = -np.ones((28, 24), dtype=int)
        for r in range(28):
            for c in range(24):
                cell = px[r * k:(r + 1) * k, c * k:(c + 1) * k].reshape(-1, 4)
                cell = cell[cell[:, 3] > 0.5]
                if len(cell) < k * k / 2:
                    continue
                rgb = np.clip(cell[:, :3] * 255, 0, 255)
                d = ((rgb[:, None, :] - arr[None, :, :]) ** 2).sum(-1).argmin(1)
                vals, cnt = np.unique(d, return_counts=True)
                idxmap[r, c] = pal_of[keys[vals[cnt.argmax()]]]
        if ref:
            sp = json.loads((Path(ref) / name / "sprite.json").read_text())
            fr = next(f for f in sp["frames"] if frame is None or f["index"] == frame)
            spr = np.array([[int(x) for x in row.split()] if isinstance(row, str) else row for row in fr["pixels"]])
        else:
            sp = common.load_sprite(ROOT, name)
            fr = next(f for f in sp["frames"] if frame is None or f["index"] == frame)
            spr = np.array(fr["pixels"])
        regions = []
        for p in sorted(set(idxmap.ravel()) - {-1}):
            vals = spr[(idxmap == p) & (spr >= 0)]
            if len(vals) < 3:
                continue
            same = vals[(vals // 16) == (p // 16)] if p not in FLOOR_IDX else vals[np.isin(vals, list(FLOOR_IDX))]
            core = np.sort(same)
            if len(core) > 10:
                core = core[len(core) // 10: len(core) - len(core) // 10]
            med = int(np.median(core)) if len(core) else -1
            regions.append((int(p), int(len(vals)), round(len(same) / len(vals), 2), med))
        results[label] = {"measure": res, "regions": regions, "idx": idxmap.tolist()}
    for mt, col in saved.items():
        mt.diffuse_color = col
    return results


def report(res, outdir):
    (Path(outdir) / "measure.json").write_text(json.dumps(res, indent=1))
    for lab, r in res.items():
        mm = r["measure"]
        print("IOU", lab, mm if isinstance(mm, str) else {k: mm.get(k) for k in ("iou_rule_grid", "iou_rule", "iou_inner")})
        for row in r["regions"]:
            print("   REGION", lab, row)


# --- main ----------------------------------------------------------------------------------------

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    do_bake = "--no-bake" not in argv
    coll = common.reset_collection(NAME)
    sprite = merged_sprite()

    # tower: art frame, cut, outlined
    tmats, body, tpieces, tshells = build_tower(sprite, coll)
    p129, s129 = build_burnt(sprite, coll)

    # crane (unchanged): with its floor as the bake occluder (D130)
    cmats = materials(sprite)
    g, inner = load_grid()
    m = PxMesh("crane")
    crane(m)
    crane_obj = to_object(m, cmats, coll)
    T.cull_hidden(crane_obj)
    fmats = {}
    for p, mt in cmats.items():
        cp = mt.copy()
        cp["tyrian_floor"] = True
        fmats[p] = cp
    m = PxMesh("floor283")
    floor(m, g, inner, 24, 28)
    seams(m, "floor283")
    floor283 = to_object(m, fmats, coll)
    crane_g = join([crane_obj, floor283], "crane_g", coll)
    crane_g.data.set_sharp_from_angle(angle=math.radians(34))
    clay = [(n, c0 + 12 - 48, r0 + 14 - 28) for n, (c0, r0) in CRANE.items()]
    cpieces = common.split_assembly(crane_g, clay, coll)
    cshell = outline_shell_all(crane_obj, coll, voxel=0.015, faces=8000, smooth=6)
    cshells = split_open(cshell, clay, coll)
    for name in CRANE:
        if len(cshells[name].data.polygons) == 0:
            raise SystemExit(f"empty outline shell on {name}")

    fmt = "AUTO"
    if do_bake:
        bake_tower(list(tpieces.values()), list(tpieces.values()))
        bake_tower([p129], [tpieces["newshc-17"], tpieces["newshc-55"]])
        bake_pieces(cpieces, clay, coll, size=512)
        fmt = "WEBP"
    for p in list(tpieces.values()) + list(cpieces.values()):
        delete_floor(p)

    # export: tower pieces upright about their own centres, the crane as before
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    upright, tris = {}, {}
    for n, r0 in TOWER.items():
        o = stand(tpieces[n], r0)
        s = stand(tshells[n], r0, normals=False)
        s["tyrian_outline"] = True
        upright[n] = (o, s)
        tris[n] = sum(len(p.vertices) - 2 for p in o.data.polygons)
        export_model(ROOT, [o, s], f"enemies/{n}", sprites[n]["sprites"], image_format=fmt)
    o = stand(p129, 0)
    soot_normals(o)   # the soot band, scar and burnt lip read black overhead, as the sprite's rows 0-3
    s = stand(s129, 0, normals=False)
    s["tyrian_outline"] = True
    upright["newshc-129"] = (o, s)
    tris["newshc-129"] = sum(len(p.vertices) - 2 for p in o.data.polygons)
    export_model(ROOT, [o, s], "enemies/newshc-129", SHEET129, image_format=fmt)
    for n in CRANE:
        p = cpieces[n]
        p.data.set_sharp_from_angle(angle=math.radians(34))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        tris[n] = sum(len(q.vertices) - 2 for q in p.data.polygons)
        export_model(ROOT, [p, cshells[n]], f"enemies/{n}", sprites[n]["sprites"], image_format=fmt)
    print("TRIS", json.dumps(tris))
    zr = {n: [round(min(v.co.z for v in o.data.vertices) * 12, 1), round(max(v.co.z for v in o.data.vertices) * 12, 1)]
          for n, (o, _) in upright.items()}
    print("TRUE HEIGHTS px", json.dumps(zr))

    if "--measure" in argv:
        md = Path(argv[argv.index("--measure") + 1])
        ref = make_ref(md, "newshc-55", 14)
        make_ref(md, "newshc-283", skip_top=range(8, 18))
        items = []
        for n, r0 in TOWER.items():
            items.append((n, n, None, ref if n == "newshc-55" else None, game_form(upright[n][0], n + "_m")))
        items.append(("newshc-129", "newshc-129", 129, REF129, game_form(upright["newshc-129"][0], "newshc-129_m")))
        for n in CRANE:
            items.append((n, n, None, ref if n == "newshc-283" else None, cpieces[n]))
        report(measure_items(items, md), md)

    if "--views" in argv:
        views(Path(argv[argv.index("--views") + 1]), upright, cpieces, coll, sprite)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
    for o in new:
        if o.get("tyrian_outline") or "outline" in o.name:
            o.hide_render = True
    return [o for o in new if not (o.get("tyrian_outline") or "outline" in o.name)]


def views(outdir, upright, cpieces, coll, sprite=None):
    """The true machine (both halves; the f83 head from its exported model) from the front, sides,
    rear, 3/4 and below, and the game's form under the 15 and 32 deg game cameras."""
    scene = bpy.context.scene
    outdir.mkdir(parents=True, exist_ok=True)
    true_objs, game_objs = [], []
    # the east tower (half 1) destroyed: frame 129's piece and the head's wreck (frame 91)
    wrecked = os.environ.get("T283_VIEW_WRECK") == "1" and "newshc-129" in upright
    for half, (dt, dc) in enumerate(((0, 0), (72, 24))):
        for n, r0 in TOWER.items():
            ctr = centre_of(r0, dt)
            src = upright["newshc-129" if wrecked and half == 1 and n == "newshc-115" else n][0]
            o = src.copy()
            o.data = src.data
            coll.objects.link(o)
            o.location = (ctr[0], ctr[1], 0)
            true_objs.append(o)
            gf = game_form(src, f"{n}_g{half}")
            gf.location = (ctr[0], ctr[1], 0)
            game_objs.append(gf)
        head = ROOT / "public" / "models" / "enemies" / ("newshc-77-f8.glb" if wrecked and half == 1 else "newshc-77-f4.glb")
        if head.exists():
            hc = centre_of(-28, dt)
            for o in import_glb(head):
                o.location = (hc[0], hc[1], 0)
                true_objs.append(o)
                gf = game_form(o, f"head_g{half}")
                gf.location = (hc[0], hc[1], 0)
                gf.data.materials.clear()
                for mt in o.data.materials:
                    gf.data.materials.append(mt)
                game_objs.append(gf)
        for n, (c0, r0) in CRANE.items():
            ctr = centre_of(r0, c0 + dc)
            o = cpieces[n].copy()
            o.data = cpieces[n].data
            coll.objects.link(o)
            o.location = (ctr[0], ctr[1], 0)
            true_objs.append(o)
            game_objs.append(o)
    setup_eevee(scene)
    D = 18
    gx, gy = 0.0, -0.2
    zc = 3.6
    t15, t32 = math.radians(15), math.radians(32)
    cams = {
        "front": ((gx, -D, zc), (gx, gy, zc), 11.0, (900, 900), true_objs),
        "sideW": ((-D, gy, zc), (gx, gy, zc), 11.0, (700, 900), true_objs),
        "rear": ((gx, D, zc), (gx, gy, zc), 11.0, (900, 900), true_objs),
        "q34": ((gx + 10, gy - 12, 9), (gx, gy, 2.6), None, (900, 900), true_objs),
        "q34rear": ((gx - 10, gy + 12, 8), (gx, gy, 2.6), None, (900, 900), true_objs),
        "under": ((gx + 4, gy - 9, -7), (gx, gy, 2.0), None, (800, 800), true_objs),
        "top": ((gx, gy, 40), (gx, gy, 0), 10.4, (800, 980), true_objs),
        "game15": ((gx, gy - 22 * math.sin(t15), 22 * math.cos(t15)), (gx, gy, 0), None, (800, 900), game_objs),
        "game32": ((gx, gy - 22 * math.sin(t32), 22 * math.cos(t32)), (gx, gy, 0), None, (800, 900), game_objs),
        "gametop": ((gx, gy, 40), (gx, gy, 0), 10.4, (800, 980), game_objs),
    }
    for key, (loc, look, ortho, res, objs) in cams.items():
        cam = camera(scene, f"v_{key}", loc, look, ortho=ortho, lens=60 if key.startswith("game") else 50)
        if key in ("top", "gametop"):
            cam.rotation_euler = (0, 0, 0)
        render(scene, cam, objs, outdir / f"{key}.png", res)
        bpy.data.objects.remove(cam, do_unlink=True)


# --- the head frames (newshc-77.py runs this) ------------------------------------------------------

def heads_main(argv):
    """newshc-77's eight frame models (77..89 and the wreck 91), each upright at the top of the true
    tower, baked with the tower as occluder, each with its outline shell and its frame tag."""
    do_bake = "--no-bake" not in argv
    coll = common.reset_collection("newshc-77")
    sprite = merged_sprite()
    try:
        sp91 = json.loads((REF91 / "newshc-77" / "sprite.json").read_text())
        sprite["colors"].update({k: v for k, v in sp91.get("colors", {}).items() if k not in sprite["colors"]})
    except OSError:
        pass
    _, body, tpieces, _ = build_tower(sprite, coll)
    heads, hshells = build_heads(sprite, coll)
    fmt = "AUTO"
    if do_bake:
        for fr, h in heads.items():
            bake_tower([h], list(tpieces.values()))
        fmt = "WEBP"
    sheet = common.load_sprite(ROOT, "newshc-77")["sprites"][0]
    exp, tris = {}, {}
    for fr in HEAD_FRAMES:
        o = stand(heads[fr], -28)
        if fr == 91:
            soot_normals(o)
        s = stand(hshells[fr], -28, normals=False)
        s["tyrian_outline"] = True
        common.frame_part(o, [fr])
        common.frame_part(s, [fr])
        exp[fr] = o
        tris[fr] = sum(len(p.vertices) - 2 for p in o.data.polygons)
        name = o.name
        export_model(ROOT, [o, s], f"enemies/{name}", [{**sheet, "frames": [fr]}], image_format=fmt)
    print("TRIS", json.dumps(tris))
    if "--measure" in argv:
        md = Path(argv[argv.index("--measure") + 1])
        items = [(f"newshc-77@{fr}", "newshc-77", fr, REF91 if fr == 91 else None, game_form(exp[fr], f"h{fr}_m"))
                 for fr in HEAD_FRAMES]
        report(measure_items(items, md), md)
    if "--views" in argv:
        vd = Path(argv[argv.index("--views") + 1])
        vd.mkdir(parents=True, exist_ok=True)
        scene = bpy.context.scene
        setup_eevee(scene)
        cup = stand(tpieces["newshc-115"], 0)
        c115 = centre_of(0)
        ch = centre_of(-28)
        cup.location = (c115[0] - ch[0], c115[1] - ch[1], 0)
        cupg = game_form(cup, "cup_g")
        cupg.location = cup.location
        t15 = math.radians(15)
        for fr in HEAD_FRAMES:
            o = exp[fr]
            gf = game_form(o, f"h{fr}_g")
            cam = camera(scene, f"hg_{fr}", (0, -0.4 - 4.6 * math.sin(t15), 4.6 * math.cos(t15)), (0, -0.4, 0), lens=60)
            render(scene, cam, [gf, cupg], vd / f"game_{fr}.png", (300, 380))
            bpy.data.objects.remove(cam, do_unlink=True)
            cam = camera(scene, f"hq_{fr}", (-3.2, -4.4 - 1.0, 9.0), (0, -1.6, 6.6), lens=50)
            render(scene, cam, [o, cup], vd / f"q34_{fr}.png", (360, 360))
            bpy.data.objects.remove(cam, do_unlink=True)


if __name__ == "__main__":
    main()
