"""Twin-pillar machine (newshc.shp, assembly-newshc-283): silhouette and game-camera
readability first, then detail.

Five 24x28 pieces of the machine's left half are modelled (newshc-115, -17, -55: the pillar;
newshc-245 over newshc-283: the crane on its tiled floor); the right half repeats the pillar at
+72 px and the crane at +24 px (same sprites, not mirrored). newshc-77, the pop-up ball turret on
each pillar's head, has its own model (imported read-only here for the context views).

What the sprite says (and this model keeps):
- The pillar is a segmented column lying north-south: a sleeve (the "cup") round the turret's stem
  with two red-lit vent bays either side of a grey guide rail, a dark neck, a red trumpet flange,
  drum 1 with a red lamp on its south shoulder, a dark gap, a long narrower shaft with bolt heads
  on its east flank, drum 2 behind a collar with its lamp, a gap, a collar and the long drum 3 with
  a red hatch on its west flank, its end skewed where it meets the floor. Widths follow the inner
  mask (D74) row by row; sections are flattened superellipses on one axis height, sitting in
  saddles on foot plates (side views).
- The crane: a squat dome on the floor (grey cap, a blue glass ring, grey band with a blue front
  window, dark skirt with blue trim and a dark hatch housing standing out to the south), a blue
  boom raking north from a pivot boss on the dome's top up to a grey U clevis, arms to the
  hammer-shaped grey head (upper and lower prongs pointing west, blue glass on its body, a blue
  stripe on top, a dark back block) and a folded blue fin on a raked post standing on the floor.
- The floor: base slab with raised tiles (101/102) and grout (99/100) traced pixel by pixel, dark
  seams where the sprite draws floor seams. Where the floor's edge pixels are dark enough to count
  as ink (sprite_mask.py), the slab stops at the inner edge (D74).

Built in sprite px of the half assembly (c east, r south, h up; pixel (c, r) covers [c,c+1]x[r,r+1];
r 0 = assembly row 28, under the newshc-77 head), moved to Blender at the end:
X = (c - 48) / 12, Y = (28 - r) / 12, Z = h / 12 (the current script's frame: whole machine 96x112,
origin screen (164, 24)). Cut into the five pieces with common.split_assembly; each piece gets the
part of one outline shell (D51) made from the whole half (every outer island: pillar and crane),
cut open at the seams, and its own small AO/roughness bake (bake_pieces).

  blender --background --python assets/blender/enemies/assembly-newshc-283.py -- [--no-bake]
      [--measure dir] [--views dir]
(exports public/models/enemies/newshc-{115,17,55,245,283}.glb and their spriteModels entries)
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

NAME = "assembly-newshc-283"
ROOT = WT
HERE = Path(__file__).resolve().parent
PX = 1 / 12
PIECES = ["newshc-115", "newshc-17", "newshc-55", "newshc-245", "newshc-283"]
ORIGIN = {"newshc-115": (0, 0), "newshc-17": (0, 28), "newshc-55": (0, 56), "newshc-245": (24, 0),
          "newshc-283": (24, 28)}
SX0, SY0 = 164, 24
FLOOR_IDX = set(range(96, 103))

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


# --- the pillar --------------------------------------------------------------------------------

CX, HA, K = 12.0, 5.0, 0.62


def S(r, a, pal, c=CX, h=HA, k=K):
    return (r, c, h, a, a * k, pal)


def groove(stations, r, a, w=0.36, d=0.32, pal=3, after=None):
    """A modelled panel line round a loft at r: the shell steps in by d for w px."""
    after = stations[-1][5] if after is None else after
    stations += [S(r - w / 2, a, pal), S(r - w / 2 + 0.06, a - d, pal), S(r + w / 2 - 0.06, a - d, pal),
                 S(r + w / 2, a, after)]


def segment(st, keys, pal, grooves=(), step=0.45, c=None):
    """Stations along a smooth (pchip) half-width profile `keys` [(r, a)], with modelled panel
    lines at `grooves` (r). `c` [(r, c)] optionally moves the axis (pchip too)."""
    f = pchip([k[0] for k in keys], [k[1] for k in keys])
    fc = pchip([k[0] for k in c], [k[1] for k in c]) if c else (lambda r: CX)
    r0, r1 = keys[0][0], keys[-1][0]
    rs = [k[0] for k in keys]
    for (ra, aa), (rb, ab) in zip(keys, keys[1:]):  # in-between stations only where the width changes
        if abs(ab - aa) > 0.02:
            n = max(1, int(round((rb - ra) / step)))
            rs += [ra + (rb - ra) * i / n for i in range(1, n)]
    if c:
        rs += [k[0] for k in c if r0 < k[0] < r1]
    rs = sorted(set(rs))
    w, d = 0.32, 0.26
    for g in grooves:
        rs = [r for r in rs if abs(r - g) > w / 2 + 0.05]
    out = [(r, None) for r in rs] + [(g, "g") for g in grooves]
    for r, kind in sorted(out):
        if kind == "g":
            a = f(r)
            st += [S(r - w / 2, a, pal, c=fc(r)), S(r - w / 2 + 0.06, a - d, 3, c=fc(r)),
                   S(r + w / 2 - 0.06, a - d, 3, c=fc(r)), S(r + w / 2, a, pal, c=fc(r))]
        else:
            st.append(S(r, f(r), pal, c=fc(r)))
    # the band leading into a groove is grooved: fix the pal of the station before each inset
    for i in range(1, len(st) - 1):
        if st[i][5] == 3 and st[i - 1][5] == pal and st[i - 1][3] > st[i][3] and abs(st[i][0] - st[i - 1][0]) < 0.1:
            st[i - 1] = st[i - 1][:5] + (3,)


def pillar(m):
    G, R, D, N = 5, 72, 3, 2  # grey drum, red flange, dark neck/groove, dark gap
    st = []
    # Sleeve (rows 0-11): the north rim leans west like the sprite's (row 0 is cols 6-15).
    segment(st, [(0.0, 4.3), (0.5, 5.3), (1.0, 6.3), (1.5, 7.0), (2.0, 7.6), (2.6, 7.95), (7.4, 7.95),
                 (8.0, 7.6), (8.5, 7.05), (9.0, 6.55), (9.5, 6.0), (10.0, 5.1), (10.5, 4.05), (10.85, 3.35)],
            G, c=[(0.0, 10.9), (0.5, 11.2), (1.0, 11.6), (1.6, 12.0), (11.0, 12.0)])
    st += [S(10.9, 3.0, D), S(12.0, 3.0, D)]
    # trumpet flange (rows 12-16, red), grooved where it meets drum 1
    segment(st, [(12.05, 3.4), (12.5, 4.0), (13.0, 4.5), (13.5, 5.1), (14.0, 6.0), (14.5, 6.9), (15.0, 7.6),
                 (15.5, 7.9), (16.0, 7.95), (16.75, 7.95)], R)
    st += [S(16.8, 7.95, D), S(16.86, 7.65, D), S(17.14, 7.65, D), S(17.2, 7.95, G)]
    # drum 1 (rows 17-22) rounding into its south shoulder (rows 23-26, the lamp sits on it)
    segment(st, [(17.25, 7.95), (22.3, 7.95), (22.8, 7.75), (23.5, 7.05), (24.2, 6.45), (24.8, 6.1),
                 (25.85, 5.95)], G, grooves=(21.8,))
    st += [S(25.9, 5.45, N, c=12.25), S(28.6, 5.45, N, c=12.25)]
    # shaft (rows 29-36) with panel lines, rounding into drum 2 (rows 37-48)
    st += [S(28.65, 5.95, 5)]
    segment(st, [(28.7, 5.95), (36.3, 5.95)], 5, grooves=(30.2, 35.0))
    st += [S(36.35, 5.95, D), S(36.4, 5.7, D), S(36.6, 5.7, D), S(36.65, 5.95, G)]
    segment(st, [(36.7, 6.0), (37.0, 6.4), (37.5, 6.85), (38.0, 7.15), (38.5, 7.4), (39.0, 7.65), (39.5, 7.85),
                 (40.0, 7.95), (45.4, 7.95), (45.9, 7.75), (46.5, 7.05), (47.1, 6.45), (47.6, 6.1),
                 (48.85, 5.95)], G, grooves=(44.9,))
    st += [S(48.9, 5.3, N), S(50.0, 5.3, N), S(50.05, 5.95, 5), S(50.85, 5.95, 5),
           S(50.9, 5.7, D), S(51.0, 5.7, D), S(51.05, 6.0, G)]
    # drum 3 (rows 51-69), its end skewed east where it meets the floor
    segment(st, [(51.1, 6.1), (51.5, 6.85), (52.0, 7.15), (52.5, 7.4), (53.0, 7.7), (53.5, 7.9), (54.0, 7.95),
                 (64.6, 7.95)], G, grooves=(54.6, 64.0))
    st += [(65.4, 12.3, HA, 7.85, 7.85 * K, G), (66.4, 12.6, HA - 0.15, 7.5, 7.5 * K * 0.97, G),
           (67.4, 13.0, HA - 0.35, 7.0, 7.0 * K * 0.92, G), (68.4, 13.4, HA - 0.6, 6.4, 6.4 * K * 0.86, G),
           (69.2, 13.6, HA - 0.9, 5.6, 5.6 * K * 0.8, G), (69.8, 13.7, HA - 1.1, 4.4, 4.4 * K * 0.72, G)]
    loft_r(m, st, n=28, p=2.3, cap_pal=4)
    surf = surf_of(st)

    # Cup: two red-lit vent bays either side of the grey guide rail, in raised frames (rows 2-7).
    for c0, c1, r0, r1 in ((5.9, 9.0, 2.0, 6.1), (13.9, 17.7, 2.0, 6.9)):
        drape(m, r0, r1, lambda r, a=c0: a, lambda r, b=c1: b, surf, 0.07, 68, side_pal=3, nr=4, nc=4)
        for fr0, fr1 in ((r0 - 0.45, r0), (r1, r1 + 0.45)):
            drape(m, fr0, fr1, lambda r, a=c0 - 0.4: a, lambda r, b=c1 + 0.4: b, surf, 0.28, 4, nr=1, nc=6)
    drape(m, 0.6, 9.4, lambda r: 9.3, lambda r: 13.6, surf, 0.3, 6, side_pal=4, nr=8, nc=3)  # guide rail
    drape(m, 12.4, 17.0, lambda r: 9.3, lambda r: 13.4, surf, 0.3, 5, side_pal=4, nr=6, nc=3)  # rail on flange

    # Lamps on the drums' south shoulders (rows 23-25, 46-48, cols 10-13): lens in a dark bezel.
    for r0 in (23.0, 46.0):
        drape(m, r0, r0 + 3.0, lambda r: 9.8, lambda r: 14.1, surf, 0.18, 16, nr=4, nc=4)
        drape(m, r0 + 0.3, r0 + 2.7, lambda r: 10.2, lambda r: 13.7, surf, 0.36, 71, side_pal=16, nr=4, nc=4)

    # Bolt heads down the shaft's east flank (rows 29-34, col 17).
    for r in (29.0, 31.0, 32.2, 34.0):
        s = surf(17.4, r + 0.5)
        prism(m, rect(16.95, r + 0.1, 17.85, r + 0.9), s - 0.6, s + 0.3, 0.15, 4)

    # The hatch on drum 3's west flank (rows 58-63), with two hinge knuckles on its north edge.
    hl = pchip([57.9, 61.6, 62.4, 63.2, 64.0], [3.9, 4.0, 4.6, 5.6, 6.2])
    hr = pchip([57.9, 59.0, 60.0, 61.0, 62.2, 63.2, 64.0], [6.0, 7.0, 8.0, 10.0, 10.2, 9.6, 8.6])
    drape(m, 57.9, 64.0, hl, hr, surf, 0.16, 67, side_pal=16, nr=12, nc=6)
    for c in (4.4, 5.8):
        s = surf(c + 0.4, 57.8)
        prism(m, rect(c, 57.4, c + 0.9, 58.2), s - 0.5, s + 0.35, 0.15, 5)

    # Saddles and foot plates under the drums (side views; hidden under the drums from above).
    for r, w in ((19.0, 2.4), (41.2, 2.4), (55.4, 2.4), (61.8, 2.4)):
        prof = []
        for k in range(9):
            x = -5.6 + 11.2 * k / 8
            hz = HA - 7.95 * K * max(0.0, 1 - abs(x / 7.95) ** 2.3) ** (1 / 2.3) + 0.15
            prof.append((CX + x, hz))
        ring = [(CX - 5.6, 0.5), (CX + 5.6, 0.5)] + prof[::-1]
        a = [m.v(c, r, h) for c, h in ring]
        b = [m.v(c, r + w, h) for c, h in ring]
        nn = len(ring)
        for i in range(nn):
            j = (i + 1) % nn
            m.f((a[i], a[j], b[j], b[i]), 4, False)
        m.f(a, 4, False)
        m.f(list(reversed(b)), 4, False)
        prism(m, rect(CX - 6.6, r - 0.6, CX + 6.6, r + w + 0.6), 0.05, 0.75, 0.2, 3)
    # Feet: chamfered blocks under each drum's ends, tucked inside its outline from above, so the
    # column stands on them instead of resting on the plate.
    for r, hw in ((17.6, 5.4), (21.2, 5.4), (30.6, 4.4), (34.0, 4.4), (37.8, 5.4), (43.2, 5.4),
                  (52.0, 5.4), (57.6, 5.4), (63.0, 5.2)):
        prism(m, rect(CX - hw, r, CX + hw, r + 1.1), 0.05, 1.7, 0.3, 4)


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
    def dome_st(r, pal, shrink=0.0):
        t = min(1.0, abs(r - DR) / DB)
        k = max(0.0, 1 - t ** 2.6) ** (1 / 2.6)
        kh = max(0.0, 1 - t ** 2.2) ** (1 / 2.2)
        return (r, DC, 0.0, DA * k - shrink, 6.7 * kh - shrink, pal)
    rs = [29.0, 29.15, 29.4, 29.8, 30.3, 31.0, 31.8]
    st = [dome_st(r, 5) for r in rs]
    st += [dome_st(31.85, 131, 0.18), dome_st(33.3, 131, 0.18), dome_st(34.85, 131, 0.18), dome_st(34.9, 5)]
    st += [dome_st(r, 5) for r in (36.0, 37.2, 38.5, 39.7)]
    st += [dome_st(39.75, 2, 0.25), dome_st(40.25, 2, 0.25), dome_st(40.3, 3)]
    st += [dome_st(r, 3) for r in (41.5, 42.8, 43.8, 44.6, 45.1, 45.3, 45.4)]
    st[-1] = (45.4, DC, 0.0, 0.0, 0.0, 3)
    st[0] = (29.0, DC, 0.0, 0.0, 0.0, 5)
    loft_r(m, st, n=40, p=2.6, zmin=0.3)
    dsurf = surf_of(st, 2.6)

    def edge(r, side, inset_px):
        t = min(1.0, abs(r - DR) / DB)
        return DC + side * (DA * max(0.0, 1 - t ** 2.6) ** (1 / 2.6) - inset_px)
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
    prism(m, [(28.6, 29.0), (33.4, 29.0), (33.8, 29.6), (33.8, 32.0), (28.6, 32.0)], 1.0, 4.9, 0.45, 5)
    prism(m, [(38.0, 29.0), (41.6, 29.0), (42.4, 30.0), (42.4, 32.4), (38.0, 32.4)], 1.0, 4.7, 0.45, 5)
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
    prism(m, rect(43.9, 26.4, 46.0, 29.4), 0.3, 1.1, 0.25, 56)
    west = pchip([7.6, 8.5, 9.5, 10.5, 11.5, 12.3, 14.2, 15.2, 16.2, 18.5, 19.6, 20.4, 21.2, 23.0],
                 [42.2, 41.6, 40.9, 40.2, 38.9, 37.5, 37.5, 38.0, 38.9, 39.3, 40.6, 42.2, 42.7, 42.9])
    east_f = pchip([7.6, 8.7, 9.2, 23.0], [45.2, 45.3, 46.0, 46.0])
    rows = [7.6, 8.2, 8.7, 9.2, 9.6, 10.3, 11.0, 11.7, 12.4, 13.2, 14.2, 15.2, 16.2, 17.2, 18.2, 19.2, 20.0,
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

    plate(7.6, 23.0, 14.2, 134, 57)
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
    """common.outline_shell (D51) keeping EVERY outer island, not only the widest one: the half
    machine is two separate objects (pillar, crane on its floor), and the stock shell kept the
    pillar only, so the crane pieces (newshc-245/-283) shipped an empty outline. An island is
    dropped only when its 3D bounding box lies inside another island's (an inner shell).
    (Candidate for common.py: an `islands="outer"` option.)"""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    collection.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    for mod in list(shell.modifiers):
        shell.modifiers.remove(mod)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
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
        lo = [min(q.co[k] for q in isl) for k in range(3)]
        hi = [max(q.co[k] for q in isl) for k in range(3)]
        islands.append((isl, lo, hi))

    def inside(a, b):
        return all(b[1][k] - 1e-4 <= a[1][k] and a[2][k] <= b[2][k] + 1e-4 for k in range(3)) and a is not b
    drop = set()
    for a in islands:
        if any(inside(a, b) and (len(b[0]) > len(a[0])) for b in islands):
            drop.update(v.index for v in a[0])
    print(f"outline shell: {len(islands)} islands, keeping {len(islands) - sum(1 for a in islands if a[0][0].index in drop)}")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index in drop], context="VERTS")
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
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


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


def build(coll):
    sprite = merged_sprite()
    mats = materials(sprite)
    g, inner = load_grid()
    groups = {}
    for gname, fn in (("pillar", pillar), ("crane", crane)):
        m = PxMesh(gname)
        fn(m)
        groups[gname] = to_object(m, mats, coll)
    for gname, c0, r0 in (("floor55", 0, 56), ("floor283", 24, 28)):
        m = PxMesh(gname)
        floor(m, g, inner, c0, r0)
        seams(m, gname)
        groups[gname] = to_object(m, mats, coll)
    return sprite, mats, groups, g, inner


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


def measure(pieces, sprite, outdir):
    """Top-view IoU per piece (sprite_mask.py --measure) and a palette-index map of the top view."""
    import numpy as np
    scene = bpy.context.scene
    outdir.mkdir(parents=True, exist_ok=True)
    k = 8
    results = {}
    mats = sorted({mt for p in pieces.values() for mt in p.data.materials}, key=lambda m: m.name)
    saved = {mt: tuple(mt.diffuse_color) for mt in mats}
    pal_of = {}
    for i, mt in enumerate(mats):  # unique flat colours to read the index map back
        idx = int(mt.name.split("_")[1])
        col = ((i * 37 % 256) / 255, (i * 91 % 256) / 255, (i * 53 % 256 + 40) % 256 / 255)
        mt.diffuse_color = (*col, 1)
        enc = [12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055 for v in col]
        pal_of[tuple(round(v * 255) for v in enc)] = idx
    setup_workbench(scene, flat=True)
    for name, obj in pieces.items():
        loc = obj.location.copy()
        obj.location = (0, 0, 0)
        cam = camera(scene, "m_top", (0, 0, 20), (0, 0, 0), ortho=28 / 12)
        cam.rotation_euler = (0, 0, 0)
        path = render(scene, cam, [obj], outdir / f"top_{name}.png", (24 * k, 28 * k), transparent=True)
        obj.location = loc
        bpy.data.objects.remove(cam, do_unlink=True)
        out = subprocess.check_output(["python3", str(ROOT / "tools" / "sprite_mask.py"), name, "--measure", str(path)])
        res = json.loads(out) if out.strip().startswith(b"{") else out.decode()
        img = bpy.data.images.load(str(path))
        px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[::-1]
        bpy.data.images.remove(img)
        keys = list(pal_of.keys())
        arr = np.array(keys, dtype=np.float32)
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
        results[name] = {"measure": res, "idx": idxmap.tolist()}
    for mt, col in saved.items():
        mt.diffuse_color = col
    return results


def region_table(results):
    """Per model palette index: the sprite's median over the pixels it covers from above."""
    import numpy as np
    rows = []
    for name, res in results.items():
        spr = np.array(common.load_sprite(ROOT, name)["frames"][0]["pixels"])
        idx = np.array(res["idx"])
        for p in sorted(set(idx.ravel()) - {-1}):
            vals = spr[(idx == p) & (spr >= 0)]
            ramp = (p // 16)
            same = vals[(vals // 16) == ramp] if p not in FLOOR_IDX else vals[np.isin(vals, list(FLOOR_IDX))]
            if len(vals) < 3:
                continue
            core = np.sort(same)
            if len(core) > 10:
                core = core[len(core) // 10: len(core) - len(core) // 10]
            med = int(np.median(core)) if len(core) else -1
            rows.append((name, int(p), int(len(vals)), round(len(same) / len(vals), 2), med))
    return rows


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    coll = common.reset_collection(NAME)
    sprite, mats, groups, g, inner = build(coll)
    half = join(list(groups.values()), NAME + "_half", coll)
    T.cull_hidden(half)
    half.data.set_sharp_from_angle(angle=math.radians(34))
    shell = outline_shell_all(half, coll, voxel=0.015, faces=8000, smooth=6)
    fmt = "AUTO"
    layout = [(e["model"], e["cx"] - SX0, e["cy"] - SY0) for e in sprite["assemblyLayout"]
              if e["model"] in PIECES]
    seen, lay = set(), []
    for name, cx, cy in sorted(layout, key=lambda t: t[1]):
        if name not in seen:
            seen.add(name)
            lay.append((name, cx, cy))
    pieces = common.split_assembly(half, lay, coll)
    shells = split_open(shell, lay, coll)
    for name, _, _ in lay:
        nf = len(shells[name].data.polygons)
        print(f"outline {name}: {nf} faces")
        if nf == 0:
            raise SystemExit(f"empty outline shell on {name}")
    if "--no-bake" not in argv:  # AO / roughness / metallic bake from the model itself (no projection)
        bake_pieces(pieces, lay, coll, size=512)
        fmt = "WEBP"
    total = 0
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    for name, cx, cy in lay:
        p = pieces[name]
        p.data.set_sharp_from_angle(angle=math.radians(34))
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
        t = sum(len(q.vertices) - 2 for q in p.data.polygons)
        total += t
        print(f"piece {name}: {t} triangles")
    print(f"total {total} triangles (half); whole machine {2 * total}")
    for name, cx, cy in lay:  # one model per sprite, centred on its own origin (the game contract)
        common.export_sprite_model(ROOT, [pieces[name], shells[name]], f"enemies/{name}",
                                   sprites[name]["sprites"], image_format=fmt)
    for name, cx, cy in lay:  # placed in the machine for the measure and view renders
        for o in (pieces[name], shells[name]):
            o.location = (cx / 12, -cy / 12, 0)
    if "--measure" in argv:
        outdir = Path(argv[argv.index("--measure") + 1])
        res = measure({n: pieces[n] for n, _, _ in lay}, sprite, outdir)
        table = region_table(res)
        summary = {n: r["measure"] for n, r in res.items()}
        (outdir / "measure.json").write_text(json.dumps({"iou": summary, "regions": table,
                                                         "idx": {n: r["idx"] for n, r in res.items()},
                                                         "tris_half": total}, indent=1))
        for n, r in summary.items():
            print("IOU", n, r if isinstance(r, str) else {k: r[k] for k in ("iou_rule_grid", "iou_rule", "edge_vs_inner_px")})
        for row in table:
            print("REGION", row)
    if "--views" in argv:
        views(argv[argv.index("--views") + 1], groups, pieces, shells, lay, coll)


def views(outdir, groups, pieces, shells, lay, coll):
    """Whole machine (both halves) from the six directions, the game camera, a crane close-up and
    one underside view; newshc-77 (its own model) imported read-only for context."""
    scene = bpy.context.scene
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    objs = []
    for name, cx, cy in lay:
        objs.append(pieces[name])
    # the right half: pillar pieces at +72 px, crane pieces at +24 px (same sprites)
    for name, cx, cy in lay:
        dc = 72 if name in ("newshc-115", "newshc-17", "newshc-55") else 24
        o = pieces[name].copy()
        o.data = pieces[name].data
        coll.objects.link(o)
        o.location = ((cx + dc) / 12, -cy / 12, 0)
        objs.append(o)
    glb = WT / "public" / "models" / "enemies" / "newshc-77.glb"
    if glb.exists():
        for cx in (128, 200):
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(glb))
            for o in set(bpy.data.objects) - before:
                if o.type == "MESH" and "outline" not in o.name:
                    o.location = ((cx - SX0) / 12, (SY0 + 18) / 12, 0)
                    objs.append(o)
                elif o.type == "MESH":
                    o.hide_render = True
    setup_eevee(scene)
    D = 14
    cams = {
        "top": ((0, 0, 30), (0, 0, 0), 10.2),
        "front": ((0, -D, 0.6), (0, 0, 0.6), 8.6),
        "rear": ((0, D, 0.6), (0, 0, 0.6), 8.6),
        "sideW": ((-D, 0, 0.6), (0, 0, 0.6), 10.2),
        "sideE": ((D, 0, 0.6), (0, 0, 0.6), 10.2),
        "q34": ((9, -10, 8), (0, 0.2, 0), None),
        "q34rear": ((-9, 10, 7), (0, 0.2, 0), None),
        "game": ((0, -16 * math.sin(math.radians(32)), 16 * math.cos(math.radians(32))), (0, 0, 0), None),
        "under": ((3, -9, -8), (0, 0.3, 0), None),
        "crane": ((-0.6, -3.2, 2.6), (-0.95, 1.1, 0.5), None),
        "tophalf": ((-2.0, -14 / 12, 30), (-2.0, -14 / 12, 0), 7.0),
    }
    res = {"top": (800, 920), "game": (800, 900), "crane": (700, 700), "tophalf": (480, 840)}
    for key, (loc, look, ortho) in cams.items():
        cam = camera(scene, f"v_{key}", loc, look, ortho=ortho, lens=60 if key == "game" else 50)
        if key in ("top", "tophalf"):
            cam.rotation_euler = (0, 0, 0)
        r = res.get(key, (900, 560))
        sel = objs
        if key == "crane":
            sel = [o for o in objs if o.name.startswith(("newshc-245", "newshc-283"))][:2]
        elif key == "tophalf":
            sel = objs[:5]
        render(scene, cam, sel, outdir / f"{key}.png", r)
        bpy.data.objects.remove(cam, do_unlink=True)


if __name__ == "__main__":
    main()
