"""Flame bowl (newsh5.shp frames 156 and 158): a brief blaze, built as thin glowing fire.

What it is: an effect, not a machine. In NOSE DRIP (4.16) four of these pairs flare up on the top
layer, drift down 3 px/tick and are gone in 20-24 ticks. The 48x28 px sprite is a crescent heap of
fire, white-hot in its middle, with eight tongues licking up from it: tall curling horns at both
ends, a pair of shorter flames inside each, and two small flickers either side of the middle notch.

So the model is fire, not a plate: a low faired crescent heap and eight flame tongues.
- Heap: one loft left to right; each station a section from a raised back rim (north, where the
  flames leave it) over a crest south of the middle to the rounded south rim, swelling into the hot
  core and ridged by low strands that fan up from the core into each tongue's root.
- Tongues: lens-section flame blades lofted root to tip, rising off the back rim (the horns to
  about 9 px, the flickers about 4), curling higher toward the tip and twisting slightly. Each
  blade's foot stands just over the rim and dives into the heap past it, while the rim rises under
  it in a fillet, so the flame grows out of the heap with no collar, ledge or seam (D195). Their
  plan edges are fitted to the sprite's inner mask row by row.
- The underside is a plain closed shape.
Every face glows (D126) on a metallic 1 / rough surface (D173) with the sprite's own fire index under
it: the sprite's heat smoothed more along the flame than across it, on fine faces, and settled into
long bands, so the colour runs in streaks up the flames rather than in pixel cells (D130); no
per-face shading darkening (shading is lighting). Strengths stay at or under ~1 (D176) so the reds
stay red and only the core goes white.

The whole blaze is built in assembly coordinates. Its outline shell is remeshed from a sealed copy
without the strands (shell_source) and held just inside the model, so the ink falls on the
silhouette only (D51, D189: every outer island kept). Both are cut into newsh5-156 (left) and
newsh5-158 (right); each piece has one frame (156 / 158), as before.

Exports newsh5-156 and newsh5-158 (each at its own origin with its _outline shell) through
common.export_sprite_model. Review output (the whole blaze as one glb) only with --out FILE.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-156.py [-- --out whole.glb]
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


def _arg(flag, default=None):
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return a[a.index(flag) + 1] if flag in a else default


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "assets" / "blender")]
import common  # noqa: E402

NAME = "assembly-newsh5-156"
PIECES = ["newsh5-156", "newsh5-158"]
PX = 1 / 12
W, H = 48, 28  # the assembly's sprite grid (two 24x28 pieces side by side)


def P(x, y, z):
    """Pixel-edge column x, row y (grid of the whole blaze), height z px -> Blender (centre at 0)."""
    return Vector(((x - W / 2) * PX, (H / 2 - y) * PX, z * PX))


# --- plan (pixel edges, fitted to the inner mask of tools/sprite_mask.py) -----------------------

# Tongues: (row, left edge, right edge) from the tip down into the heap. A tip is a point.
TONGUES = [
    [(0.9, 3.65, 3.65), (1.5, 3.35, 4.0), (2.5, 3.0, 4.05), (3.5, 3.0, 4.9), (4.5, 3.0, 5.2), (5.5, 3.0, 6.0),
     (6.5, 3.0, 7.0), (7.0, 3.0, 7.5), (8.5, 3.0, 8.3), (11.0, 3.0, 8.6)],
    [(1.6, 9.2, 9.2), (2.5, 9.0, 9.6), (3.5, 9.0, 10.05), (4.5, 8.85, 11.0), (5.5, 8.15, 12.0), (6.5, 7.9, 13.0),
     (7.0, 7.5, 14.0), (8.5, 7.7, 14.2), (11.0, 8.0, 14.3)],
    [(5.2, 16.3, 16.3), (6.0, 15.4, 16.95), (6.5, 15.0, 17.0), (7.0, 14.0, 17.1), (7.5, 14.2, 17.3),
     (8.5, 14.4, 18.05), (9.0, 14.5, 19.0), (11.0, 14.7, 19.2), (13.0, 15.0, 19.3)],
    [(5.6, 21.75, 21.75), (6.5, 21.35, 22.05), (7.5, 20.95, 22.05), (8.5, 20.0, 22.1), (9.0, 19.0, 22.2),
     (10.5, 19.3, 23.0), (11.5, 19.5, 24.0), (12.0, 19.6, 24.5), (14.0, 19.8, 24.6)],
    [(5.6, 27.25, 27.25), (6.5, 26.95, 27.65), (7.5, 26.95, 28.05), (8.5, 26.9, 29.0), (9.0, 26.8, 30.0),
     (10.5, 26.0, 29.7), (11.5, 25.0, 29.5), (12.0, 24.5, 29.4), (14.0, 24.4, 29.2)],
    [(5.2, 33.0, 33.0), (6.0, 32.1, 33.7), (6.5, 32.0, 34.0), (7.0, 31.9, 35.0), (7.5, 31.8, 34.8),
     (8.5, 31.0, 34.6), (9.0, 30.0, 34.5), (11.0, 29.8, 34.4), (13.0, 29.7, 34.1)],
    [(1.6, 39.8, 39.8), (2.5, 39.4, 40.0), (3.5, 38.95, 40.05), (4.5, 38.0, 40.15), (5.5, 37.0, 40.85),
     (6.5, 36.0, 41.1), (7.0, 35.0, 41.5), (8.5, 35.4, 41.4), (11.0, 35.6, 41.2)],
    [(0.9, 45.35, 45.35), (1.5, 45.0, 45.65), (2.5, 44.95, 46.0), (3.5, 44.05, 46.0), (4.5, 43.95, 46.0),
     (5.5, 43.0, 46.0), (6.5, 42.0, 46.0), (7.0, 41.5, 46.0), (8.5, 41.0, 46.0), (11.0, 40.6, 46.0)],
]
# How high each tongue's tip stands (px) and which way it twists (+1: right edge up).
RISE = [9.0, 7.5, 4.4, 4.0, 4.0, 4.4, 7.5, 9.0]
TWIST = [-1, -0.6, -0.4, -0.3, 0.3, 0.4, 0.6, 1]

# Heap: north edge (notch line) and south rim, (column, row).
NORTH = [(3.0, 9.0), (7.5, 7.0), (14.0, 7.0), (19.0, 9.0), (24.5, 12.0), (30.0, 9.0), (35.0, 7.0),
         (41.5, 7.0), (46.0, 9.0)]
SOUTH = [(3.0, 15.6), (4.0, 17.0), (5.0, 18.5), (6.0, 19.5), (7.0, 20.5), (8.0, 21.5), (10.0, 22.5),
         (11.0, 23.5), (13.6, 24.45), (15.5, 25.0), (33.5, 25.0), (35.4, 24.45), (38.0, 23.5),
         (39.0, 22.5), (41.0, 21.5), (42.0, 20.5), (43.0, 19.5), (44.0, 18.5), (45.0, 17.0), (46.0, 15.6)]
CORE = (24.0, 20.5)  # the white-hot heart (rows 17-22, columns 18-27)
STRAND = {"amp": 0.8}  # strand ridge height (px); 0 while building the outline shell's source


def lerp_table(tab, x):
    if x <= tab[0][0]:
        return tab[0][1]
    for (x0, y0), (x1, y1) in zip(tab, tab[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return tab[-1][1]


def smooth_table(tab, x, k=0.8):
    """lerp_table smoothed by a small box average (round corners, keeps area)."""
    return sum(lerp_table(tab, x + d * k / 4) for d in (-2, -1, 0, 1, 2)) / 5


def catmull(pts, steps):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for s in range(steps):
            t = s / steps
            out.append(tuple(0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                                    + (-a + 3 * b - 3 * c + d) * t ** 3) for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(tuple(pts[-1]))
    return out


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# --- heap --------------------------------------------------------------------------------------

def heap_height(x):
    """Crest height (px) of the heap at column x: tallest over the core, low at the horns' roots."""
    d = abs(x - CORE[0])
    return 2.2 + 3.4 * math.exp(-(d / 10.0) ** 2) + 0.4 * smoothstep(17, 22, d)


def strands(x, y):
    """Flame strands: raised ridges (px of extra height) running from the hot south of the heap up
    into each tongue's root, the sprite's bright streaks rising into the flames."""
    out = 0.0
    for sp in TONGUES:
        rx = (sp[-1][1] + sp[-1][2]) / 2
        ry = sp[-1][0]
        # from a point on the south slope (pulled toward the middle) up to the tongue's root
        bx = rx + (CORE[0] - rx) * 0.35
        by = smooth_table(SOUTH, bx) - 3.0
        vx, vy = rx - bx, (ry - 1.0) - by
        t = max(0.0, min(1.0, ((x - bx) * vx + (y - by) * vy) / (vx * vx + vy * vy)))
        dx, dy = x - (bx + vx * t), y - (by + vy * t)
        amp = STRAND["amp"] * smoothstep(0.0, 0.25, t)
        out = max(out, amp * math.exp(-(dx * dx + dy * dy) / 1.6))
    return out


# section across the heap: (u north->south, height share); the top, then the underside back. The
# north edge is a raised back rim (0.42 of the crest), not a thin lip: the flames rise from it, and
# the ink outline (an inverted hull that pulls its back faces about a pixel toward the camera) would
# show the tongues' undersides through a thin lip as a dark line along the tongue roots.
HEAP_TOP = [(0.0, 0.42), (0.03, 0.55), (0.10, 0.66), (0.22, 0.78), (0.36, 0.90), (0.50, 0.98),
            (0.60, 1.00), (0.70, 0.96), (0.80, 0.82), (0.89, 0.60), (0.955, 0.36), (1.0, 0.12)]
HEAP_UNDER = [(0.97, -0.02), (0.6, -0.08), (0.25, -0.06), (0.04, -0.04), (0.005, -0.02)]
HEAP_PROFILE = HEAP_TOP + HEAP_UNDER


def heap_base(x, y):
    """Height (px) of the heap's top surface at (x, y) before the tongue fillets, or None outside."""
    yt, yb = smooth_table(NORTH, x), smooth_table(SOUTH, x)
    if not (yt <= y <= yb) or not (3.0 <= x <= 46.0):
        return None
    u = (y - yt) / (yb - yt)
    top = HEAP_TOP
    return heap_height(x) * lerp_table(top, u) + strands(x, y)


def heap_section():
    """HEAP_PROFILE with its top resampled (Catmull-Rom, 3 per span): fine faces, so the colour
    bands' edges run as smooth curves instead of a coarse grid."""
    return catmull(HEAP_TOP, 3) + HEAP_UNDER


def build_heap(bm):
    """The heap loft, 96 stations left to right. Returns (grid, caps): grid[i][k] = face between
    stations i and i+1 at section slot k (north edge first, over the top, back under)."""
    xs = [3.0 + 43.0 * k / 95 for k in range(96)]
    section = heap_section()
    rings = []
    for x in xs:
        yt, yb = smooth_table(NORTH, x), smooth_table(SOUTH, x)
        h = heap_height(x)
        end = min(x - 3.0, 46.0 - x)
        endk = 0.55 + 0.45 * smoothstep(0.0, 1.2, end)  # the ends round off low
        ring = []
        for u, s in section:
            y = yt + (yb - yt) * u
            if s >= 0:
                z = (h * s + strands(x, y)) * (1 + (endk - 1) * smoothstep(0.1, 0.3, s))
                z += fillet(x, y, z)
            else:
                z = s * 2.0
            ring.append(bm.verts.new(P(x, y, z)))
        rings.append(ring)
    n = len(section)
    grid = []
    for a, b in zip(rings, rings[1:]):
        grid.append([bm.faces.new((a[k], b[k], b[(k + 1) % n], a[(k + 1) % n])) for k in range(n)])
    caps = [bm.faces.new(list(reversed(rings[0]))), bm.faces.new(rings[-1])]
    return grid, caps


# --- tongues -----------------------------------------------------------------------------------

# section across a tongue, left edge u=0 to right edge u=1: (u, top share, bottom share)
TONGUE_U = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]


def lens(u, crest):
    """Top-surface share across the tongue: a chamfered lens with its crest at `crest`."""
    d = (u - crest) / (crest if u < crest else 1 - crest)
    d = abs(d)
    return max(0.0, 1 - d ** 1.7) * 0.85 + 0.15 * (1 - d) if d <= 1 else 0.0


class Tongue:
    """One flame tongue: its plan rows (Catmull-Rom through TONGUES, root -> tip) and the heights of
    its top and underside at any (x, y) of its plan.

    North of the heap's edge the blade is free: its middle stands at `z0`, just over the heap's back
    rim along the whole width (so the rim never stands in front of the flame and hides its foot),
    and curls up toward the tip. Past the edge, column by column, it dives into the heap 1 px per px
    while the heap's rim rises under it in a fillet (fillet()), so the flame grows out of the rim with
    no collar, step, ledge or occluding fold for the ink to catch (D195)."""

    def __init__(self, sp, rise, twist):
        self.rise, self.twist = rise, twist
        rows = catmull([(r, l, rr) for r, l, rr in reversed(sp)], 3)  # root -> tip
        self.y_root, self.y_tip = rows[0][0], rows[-1][0]
        asc = list(reversed(rows))
        self.l_tab = [(r[0], r[1]) for r in asc]
        self.r_tab = [(r[0], r[2]) for r in asc]
        mid = [(r[0], (r[1] + r[2]) / 2) for r in asc]
        # the row where the middle crosses the heap's north edge
        self.y_n = self.y_root
        for (y0, m0), (y1, m1) in zip(mid, mid[1:]):
            d0, d1 = y0 - smooth_table(NORTH, m0), y1 - smooth_table(NORTH, m1)
            if d0 <= 0 < d1:
                self.y_n = y0 + (y1 - y0) * (-d0) / (d1 - d0)
                break
        # the rim under the blade (its highest point along the heap's edge) and the cut, 1.5 px
        # inside the edge everywhere across the blade
        rim, deepest = 0.3, self.y_n
        for y, xl, xr in rows:
            for k in range(11):
                x = xl + (xr - xl) * k / 10
                yn = smooth_table(NORTH, x)
                if abs(y - yn) < 0.7 and 3.0 <= x <= 46.0:
                    rim = max(rim, heap_base(x, yn + 0.05) or 0.0)
                    deepest = max(deepest, yn)
        self.z0 = rim + 0.1
        self.y_cut = deepest + 1.5
        self.rows = [r for r in rows if r[0] <= self.y_cut]

    def span(self, y):
        return lerp_table(self.l_tab, y), lerp_table(self.r_tab, y)

    def frame(self, y):
        """(xl, xr, middle height before the dive, half thickness, s) at row y; s 0 at the heap's
        edge, 1 at the tip."""
        xl, xr = self.span(y)
        width = max(0.0, xr - xl)
        s_all = (self.y_root - y) / (self.y_root - self.y_tip)
        s = max(0.0, min(1.0, (self.y_n - y) / (self.y_n - self.y_tip)))
        zc = self.z0 + self.rise * (0.45 * s + 0.55 * s ** 2.2)  # curls up toward the tip
        th = (0.35 + 0.75 * min(1.0, width / 5.0)) * (1 - 0.55 * s_all) * (1 + 0.25 * (1 - s))
        return xl, xr, zc, th, s

    def top(self, x, y):
        xl, xr, zc, th, s = self.frame(y)
        u = (x - xl) / max(1e-6, xr - xl)
        tw = self.twist * (u - 0.5) * 1.2 * smoothstep(0.1, 1.0, s)
        dive = max(0.0, y - smooth_table(NORTH, x)) if 3.0 <= x <= 46.0 else 0.0
        z = zc + tw + th * (0.15 + 0.85 * lens(u, 0.5 - 0.12 * self.twist)) - dive
        return max(0.04, z)

    def bottom(self, x, y):
        xl, xr, zc, th, s = self.frame(y)
        u = (x - xl) / max(1e-6, xr - xl)
        tw = self.twist * (u - 0.5) * 1.2 * smoothstep(0.1, 1.0, s)
        dive = max(0.0, y - smooth_table(NORTH, x)) if 3.0 <= x <= 46.0 else 0.0
        return max(0.02, zc + tw - th * (0.15 + 0.75 * lens(u, 0.5)) - dive)


_TONGUES = []


def tongues():
    if not _TONGUES:
        _TONGUES.extend(Tongue(sp, rise, tw) for sp, rise, tw in zip(TONGUES, RISE, TWIST))
    return _TONGUES


def fillet(x, y, z):
    """Extra height (px) of the heap at (x, y), base height z: under each tongue the back rim rises
    to just under the blade's top where the blade leaves it (at the heap's edge), easing back to the
    plain heap 2.5 px in, so the heap's surface flows up into the flame."""
    yn = smooth_table(NORTH, x)
    dn = y - yn
    if dn > 2.5:
        return 0.0
    f = 1 - smoothstep(0.0, 2.5, dn)
    best = 0.0
    for t in tongues():
        if not (t.y_tip <= yn <= t.y_root):
            continue
        xl, xr = t.span(yn)
        if not (xl < x < xr):
            continue
        u = (x - xl) / (xr - xl)
        a = smoothstep(0.0, 0.18, u) * smoothstep(1.0, 0.82, u)
        best = max(best, a * f * max(0.0, t.top(x, yn) - 0.05 - z))
    return best


def build_tongue(bm, t):
    """The blade lofted root -> tip from its cut (already buried) out to the tip; a lens section
    with its crest line. Returns (grid, cap): grid[i][k] = face between rings i and i+1 at slot k."""
    rings = []
    n = len(t.rows)
    for i, (y, xl, xr) in enumerate(t.rows):
        width = max(0.0, xr - xl)
        if width < 1e-3 or i == n - 1:
            rings.append([bm.verts.new(P((xl + xr) / 2, y, t.frame(y)[2] + 0.1))])
            continue
        top = [bm.verts.new(P(xl + width * u, y, t.top(xl + width * u, y))) for u in TONGUE_U]
        bot = [bm.verts.new(P(xl + width * u, y, t.bottom(xl + width * u, y))) for u in reversed(TONGUE_U[1:-1])]
        rings.append(top + bot)
    grid = []
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        m = max(len(a), len(b))
        row = []
        for k in range(m):
            j = (k + 1) % m
            if len(b) == 1:
                row.append(bm.faces.new((a[k], a[j], b[0])))
            elif len(a) == 1:
                row.append(bm.faces.new((a[0], b[j], b[k])))
            else:
                row.append(bm.faces.new((a[k], a[j], b[j], b[k])))
        grid.append(row)
    cap = bm.faces.new(list(reversed(rings[0])))
    return grid, cap


# --- colour ------------------------------------------------------------------------------------

SLOTS = list(range(114, 128))
HEAP_SIG, TONGUE_SIG = (0.8, 1.3), (0.7, 1.3)  # heat smoothing (px) across / along the flame
HEAP_BIAS, TONGUE_BIAS = -1.0, -1.0  # the glow lifts the read; this keeps the region medians on the sprite's
GLOW = [0.5, 0.52, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.92, 0.95, 1.0, 1.0]


def heat_field(idx, sx, sy):
    """Sprite heat (palette index, fire bank) over the non-ink pixels, smoothed `sx` px across and
    `sy` px along the flame (up the sprite): the sprite's streaks run up its columns, so the colour
    keeps them as long bands instead of square pixel cells."""
    h, w = len(idx), len(idx[0])
    rx, ry = int(3 * sx) + 1, int(3 * sy) + 1
    def at(x, y):
        num = den = 0.0
        for r in range(max(0, int(y) - ry), min(h, int(y) + ry + 1)):
            for c in range(max(0, int(x) - rx), min(w, int(x) + rx + 1)):
                v = idx[r][c]
                if v < 114:
                    continue
                wt = math.exp(-((c + 0.5 - x) / sx) ** 2 / 2 - ((r + 0.5 - y) / sy) ** 2 / 2)
                num += wt * v
                den += wt
        return num / den if den > 1e-6 else None
    return at


def settle_runs(q, v, passes=2):
    """Along one strip of faces running with the flame: a face whose colour differs from both
    neighbours takes the nearer of theirs, so the bands come out long, not as single cells."""
    for _ in range(passes):
        for j in range(1, len(q) - 1):
            if q[j] is None or q[j - 1] is None or q[j + 1] is None:
                continue
            if q[j] != q[j - 1] and q[j] != q[j + 1]:
                q[j] = q[j - 1] if abs(v[j] - q[j - 1]) <= abs(v[j] - q[j + 1]) else q[j + 1]
    return q


def settle_grid(grid, val, slot, strips_along_rows):
    """Quantise the floats `val` (dict face -> heat) of a face grid and settle each strip along the
    flame (settle_runs), then drop lone cells across the strips the same way."""
    nr, nk = len(grid), len(grid[0])
    q = [[None if val.get(grid[i][k]) is None else slot(val[grid[i][k]]) for k in range(nk)] for i in range(nr)]
    v = [[val.get(grid[i][k], 0.0) for k in range(nk)] for i in range(nr)]
    if strips_along_rows:  # the strip runs over i (tongue rings, root -> tip) at a fixed k
        for k in range(nk):
            col = settle_runs([q[i][k] for i in range(nr)], [v[i][k] for i in range(nr)])
            for i in range(nr):
                q[i][k] = col[i]
        for i in range(nr):
            q[i] = settle_runs(q[i], v[i], 1)
    else:  # the strip runs over k (heap section, north -> south) at a fixed station i
        for i in range(nr):
            q[i] = settle_runs(q[i], v[i])
    return q


def face_xy(f):
    c = f.calc_center_median()
    return c.x / PX + W / 2, H / 2 - c.y / PX


def heap_heat(f, heat):
    """Heat of a heap face, or None for a face turned down (the underside's deep red)."""
    if f.normal.z < -0.3:
        return None
    x, y = face_xy(f)
    v = heat(x, y)
    v = 117 if v is None else v
    v += HEAP_BIAS + 1.5 * min(1.0, strands(x, y) / max(0.3, 0.8 * STRAND["amp"]))  # strands hotter
    yt, yb = smooth_table(NORTH, x), smooth_table(SOUTH, x)
    u = (y - yt) / max(0.5, yb - yt)
    v += max(0.0, v - 123.0)  # the smoothing dulls the sprite's white-hot pixels; lift them back
    return v - 2.0 * smoothstep(0.82, 1.0, u) - 1.5 * smoothstep(0.2, 0.0, u)  # rims deeper


def tongue_heat(f, heat, tongue):
    x0, y = face_xy(f)
    x = 0.5 * x0 + 0.5 * tongue["mid"](y)
    v = heat(x, y)
    v = (117 if v is None else v) + TONGUE_BIAS
    xl, xr = tongue["l"](y), tongue["r"](y)
    u = (x0 - xl) / max(0.3, xr - xl)
    sfrac = max(0.0, min(1.0, (tongue["root"] - y) / (tongue["root"] - tongue["tip"])))
    if f.normal.z > 0:  # the crest line runs hot (the sprite's bright spine pixels), fading to the tip
        v += 2.5 * math.exp(-((u - tongue["crest"]) / 0.2) ** 2) * (1 - 0.7 * sfrac)
    elif f.normal.z < -0.3:
        v -= 1.5  # a tongue's underside still glows, a step deeper
    return v


def paint(bm, idx, heap, tongues):
    """Paint every face its pal_114..127 slot (material index). The heap takes the sprite's heat
    smoothed 0.7 px across by 2.2 px along the flame, plus a step on the strands and deeper rims; a
    tongue its spine's heat (0.7 by 1.6 px) with a hot crest. Each strip of faces running with the
    flame is then settled into long bands (settle_grid). No per-face shading darkening: shading is
    the game's lighting (art rule 2)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    slot = lambda v: max(0, min(len(SLOTS) - 1, round(v) - SLOTS[0]))
    grid, caps = heap
    hheat = heat_field(idx, HEAP_SIG[0], HEAP_SIG[1])
    val = {f: heap_heat(f, hheat) for row in grid for f in row}
    q = settle_grid(grid, val, slot, False)
    for i, row in enumerate(grid):
        for k, f in enumerate(row):
            f.material_index = 1 if q[i][k] is None else q[i][k]
    for f in caps:
        v = heap_heat(f, hheat)
        f.material_index = 1 if v is None else slot(v)
    theat = heat_field(idx, TONGUE_SIG[0], TONGUE_SIG[1])
    for (tgrid, cap), info in tongues:
        val = {f: tongue_heat(f, theat, info) for row in tgrid for f in row}
        q = settle_grid(tgrid, val, slot, True)
        for i, row in enumerate(tgrid):
            for k, f in enumerate(row):
                f.material_index = q[i][k]
        cap.material_index = slot(tongue_heat(cap, theat, info))


# --- assembly ----------------------------------------------------------------------------------

def load_assembly():
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    lay = [e for e in sprites[PIECES[0]]["assemblyLayout"] if e["model"] in PIECES]
    left = min(e["cx"] - 12 for e in lay)
    top = min(e["cy"] - 14 for e in lay)
    idx = [[-1] * W for _ in range(H)]
    for e in lay:
        for r, row in enumerate(sprites[e["model"]]["frames"][0]["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    idx[e["cy"] - 14 - top + r][e["cx"] - 12 - left + c] = v
    cx0, cy0 = left + W / 2, top + H / 2
    layout = [(e["model"], e["cx"] - cx0, e["cy"] - cy0) for e in lay]
    merged = dict(sprites[PIECES[0]])
    merged["colors"] = {}
    for s in sprites.values():
        merged["colors"].update(s["colors"])
    return idx, layout, merged, sprites


def cut_open(obj, layout, coll):
    """The outline shell cut to each piece's box WITHOUT filling the cut (no ink across the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        for poly in me.polygons:
            poly.use_smooth = True
        sh["tyrian_outline"] = True
        out[name] = sh
    return out


def build_geometry(bm):
    heap = build_heap(bm)
    out = []
    for sp, tw, t in zip(TONGUES, TWIST, tongues()):
        info = {"mid": lambda y, t=[(r, (l + rr) / 2) for r, l, rr in sp]: lerp_table(t, y),
                "l": lambda y, t=[(r, l) for r, l, rr in sp]: lerp_table(t, y),
                "r": lambda y, t=[(r, rr) for r, l, rr in sp]: lerp_table(t, y),
                "root": sp[-1][0], "tip": sp[0][0], "crest": 0.5 - 0.12 * tw}
        out.append((build_tongue(bm, t), info))
    return heap, out


def build(coll, idx, sprite):
    mats = [common.palette_material(sprite, i, "nsh5_156", metallic=1.0, roughness=0.85, emission_strength=g)
            for i, g in zip(SLOTS, GLOW)]
    bm = bmesh.new()
    heap, tongues = build_geometry(bm)
    paint(bm, idx, heap, tongues)
    return common.mesh_object(NAME, bm, mats, coll, smooth=True)


def shell_source(coll):
    """The blaze without its strands (a smooth heap the tongues lie into): the outline shell is made
    from this, so it has no creases between the strands or at the tongue roots for the ink to catch."""
    amp = STRAND["amp"]
    STRAND["amp"] = 0.0
    bm = bmesh.new()
    build_geometry(bm)
    STRAND["amp"] = amp
    return common.mesh_object(f"{NAME}_shellsrc", bm, [], coll, smooth=True)


def apply_modifiers(obj):
    """common._apply_modifiers, copied (a private helper)."""
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def outline_shell_from(src, target, coll, voxel, faces, smooth, inside):
    """common.outline_shell, but remeshed from `src` (shell_source: the sealed, strand-free blaze)
    and held `inside` units under `target` (the model itself) wherever it would stand outside it:
    the inverted hull then only shows past the silhouette, never through the heap or at the tongue
    roots (D51, D189). Every outer island is kept (islands="outer")."""
    me = src.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{target.name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = target.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    common.keep_shell_islands(bm, "outer", 0.001, 2, shell.matrix_world, label=shell.name)
    bm.to_mesh(shell.data)
    bm.free()
    sm = shell.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    n = len(shell.data.polygons)
    if n > faces:
        dec = shell.modifiers.new("decimate", "DECIMATE")
        dec.ratio = faces / n
    apply_modifiers(shell)
    sw = shell.modifiers.new("inside", "SHRINKWRAP")
    sw.target = target
    sw.wrap_method = "NEAREST_SURFACEPOINT"
    sw.wrap_mode = "INSIDE"
    sw.offset = -inside
    apply_modifiers(shell)
    shell.data.shade_smooth()
    shell.data.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell["tyrian_outline"] = True
    return shell


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    idx, layout, sprite, _ = load_assembly()
    whole = build(coll, idx, sprite)
    bpy.context.view_layer.update()
    src = shell_source(coll)
    bpy.context.view_layer.update()
    shell = outline_shell_from(src, whole, coll, voxel=0.010, faces=5000, smooth=8, inside=0.012)
    bpy.data.objects.remove(src, do_unlink=True)
    assert len(shell.data.polygons) > 0, "empty outline shell"
    pieces = common.split_assembly(whole, layout, coll)
    shells = cut_open(shell, layout, coll)
    manifest = {}
    objs = []
    for name, cx, cy in layout:
        p, s = pieces[name], shells[name]
        assert len(p.data.polygons) > 0 and len(s.data.polygons) > 0, f"{name}: empty piece or shell"
        for poly in p.data.polygons:
            poly.use_smooth = True
        common.export_sprite_model(ROOT, [p, s], f"enemies/{name}", common.load_sprite(ROOT, name)["sprites"])
        manifest[name] = {"offset": [cx / 12, -cy / 12], "tris": sum(len(q.vertices) - 2 for q in p.data.polygons),
                          "shell_faces": len(s.data.polygons)}
        for o in (p, s):
            o.location.x += cx / 12
            o.location.y += -cy / 12
            o["design_model"] = name
        objs += [p, s]
    out = _arg("--out")
    if out:
        whole["design_model"] = "whole"
        shell["design_model"] = "whole"
        manifest["whole"] = {"tris": sum(len(q.vertices) - 2 for q in whole.data.polygons)}
        out = Path(out)
        common.export_glb(objs + [whole, shell], out)
        (out.parent / f"{out.stem}.manifest.json").write_text(json.dumps(manifest, indent=1))
    print("MANIFEST", json.dumps(manifest))


if __name__ == "__main__":
    main()
