"""newshs-229 (design A): a glowing red crystal held in a grey two-jaw clamp, a tile of the stone
fortress (newshs.shp frames 229-235, 24 x 28 px), rebuilt hard-surface to the D65 standard.

Reading of the sprite (tools/calibration/rubric.md, "Reading a sprite"):
- The crystal: cols 4-18, rows 4-23 (x -8..7, y 4..24), a rounded rectangle with ~4 px corners
  (row 4 starts at col 6, row 5 at col 5). A cushion-cut gem: its lit upper-left rim (122-127 on
  231), the bright lower-right rim (119-122) and the dark outer row/column (112-114) are the
  lighting of a domed, glossy body, not paint. The swirl in its heart (116-118 on a 115 body) is
  the crystal's own inner pattern: painted as two smooth palette regions (crown faces split along
  the iso-contours of the blurred sprite), fading out over the rim band.
- The clamp: two C-shaped grey jaws grip it from left and right. Their claws (rows 5-7 and 19-22,
  palette ~6) hug the gem's rounded corners; inside each C a deep slot (cols 1-3 / 19-21, rows 8-18,
  palette 1-2, darkest by the gem) shows the floor far below. The outer walls of the C are col 0
  (left) and cols 22-23 (right; col 22 its lit edge). A faint lighter line down each slot (col 2 /
  col 21, palette 3-5) is a tension rod deep in the slot (a lit streak = a cylinder).
- Cross bars: a grey bar at the top edge (rows 0-1, cols 8-14, lit top edge on row 0) and a
  dimmer one at the bottom (rows 26-27), each with a dark gap (rows 2-3 / 24-25) between it and the
  gem: depth, so the gem stands proud of the floor there.
- Rows 0-3 / 24-27 and the rest: the fortress's stone floor. Built as a plate painted per pixel (as
  lib_b073 did) for the review renders only; not exported (D130: the game draws the tile's ground in HD, and the
  plate painted per pixel from the sprite showed as grey pixel cells on it).
- Frames only pulse the glow: every red index is one lower on 229 and +1 / +3 on 233 / 235 than on
  231. One model; the gem's materials follow the frame (palette_material frames=, D17).

Colours (trimmed median per region): gem body 116 (231; the median of all its pixels), the swirl's
dark arms 115 and bright cores 117, claws 6, outer walls 7,
top bar 7, bottom bar 4, slot rods 3, the deep floor in the slots and gaps 1, other floor tones
from the pixels.

Hard surface (D50-D53, D65): jaws are extruded C-plates with chamfered top edges, an inset panel
groove and hex bolts on each claw, bolted front faces with a groove; tension rods are cylinders
through the slots into the claws; the gem a lofted cushion (pchip crown profile over inset rounded
rectangles, vertical girdle with a chamfer) seated in a metal cup. Outline shell (D51) from a closed
proxy. Underside: closed, plain.

Units while building: sprite px (x = column edge - 12, y = row edge, down the screen, z up),
moved to Blender by usp_talon.finish (1/12, y flipped).

Run: Blender --background --factory-startup --python newshs-229.py -- [--out x.glb] [--render DIR]
"""

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

NAME = "newshs-229"
HERE = Path(__file__).resolve().parent
PX = 1 / 12

FLOOR = 0.36            # floor top (0.03 units, lib_b073's FLOOR, so the fortress tiles meet)
JZ = 3.2                # jaw top
BAR_Z = 1.7             # cross bar top
GX0, GX1 = -8.0, 7.0    # gem x extent (cols 4-18)
GY0, GY1 = 4.0, 24.0    # gem y extent (rows 4-23)
GCX, GCY = (GX0 + GX1) / 2, (GY0 + GY1) / 2
GR = 4.25               # gem corner radius (the sprite's rows 4-5 / 22-23 step in 2, 1 px)
CUP_Z = 1.4             # gem girdle bottom (the metal cup below)
GIRDLE_Z = 2.9          # girdle top
SLOT_Y0, SLOT_Y1 = 8.0, 19.0
JAW_Y0, JAW_Y1 = 5.0, 23.0

# Crown profile: inset from the girdle outline (px) -> height (px). pchip, so it never overshoots.
# Two pieces with a crease at the table's edge (TABLE_D): a cushion cut, crown facets sloping ~45
# degrees, then a nearly flat table, so the crystal reads as a hard cut stone, not a jelly pillow.
TABLE_D = 2.4
# Gem emission: none. In game src/render/modelFrames.ts colourFrame sets an emissive material's
# emissive to the full palette colour on every frame (the exported strength is lost), so any glow
# here renders at strength 1: a candy-bright plastic red. Lit only, the crystal reads deep crimson
# like the sprite (viewer: model gem median R 137 vs sprite 109, the same ratio as the grey
# parts), and the pulse still comes from the per-frame palette indices.
GLOW = 0.0
_crown = T.pchip([0.0, 0.25, 0.9, 1.6, TABLE_D], [GIRDLE_Z, 3.45, 4.25, 5.0, 5.75])
_table = T.pchip([TABLE_D, 3.5, 5.0, 6.6, 7.3], [5.75, 5.9, 6.0, 6.04, 6.05])


def crown_z(d):
    return _crown(d) if d <= TABLE_D else _table(d)


# --- materials ----------------------------------------------------------------------------------
class Mats:
    def __init__(self, sprite):
        self.sprite = sprite
        self.list = []
        self.slots = {}

    def __call__(self, index, part, frames=None, metallic=0.4, roughness=0.45, emission=0.0):
        key = (index, part)
        if key not in self.slots:
            self.slots[key] = len(self.list)
            self.list.append(common.palette_material(self.sprite, index, f"{NAME}_{part}", metallic=metallic,
                                                     roughness=roughness, emission_strength=emission,
                                                     frames=frames))
        return self.slots[key]


def glow_frames(i):
    """The gem's pulse: index i on 231, one lower on 229, +1 on 233, +3 on 235 (capped at 127)."""
    return {229: i - 1, 233: min(i + 1, 127), 235: min(i + 3, 127)}


# --- geometry helpers ---------------------------------------------------------------------------
def rrect(cx, cy, a, b, r, n_x=18, n_y=26, n_c=9):
    """A rounded rectangle (half sizes a, b, corner radius r) as a ring of points, always the same
    count and order (counter-clockwise in x, y-down = clockwise on screen), starting top middle."""
    r = max(0.05, min(r, a - 1e-3, b - 1e-3))
    pts = []
    # top edge, left to right... go round: top (y = cy - b) from left corner to right corner
    def edge(p0, p1, n):
        return [(p0[0] + (p1[0] - p0[0]) * k / n, p0[1] + (p1[1] - p0[1]) * k / n) for k in range(n)]

    def arc(ccx, ccy, a0, n):
        return [(ccx + r * math.cos(a0 + math.pi / 2 * k / n), ccy + r * math.sin(a0 + math.pi / 2 * k / n))
                for k in range(n)]
    x0, x1, y0, y1 = cx - a, cx + a, cy - b, cy + b
    pts += edge((x0 + r, y0), (x1 - r, y0), n_x)
    pts += arc(x1 - r, y0 + r, -math.pi / 2, n_c)
    pts += edge((x1, y0 + r), (x1, y1 - r), n_y)
    pts += arc(x1 - r, y1 - r, 0.0, n_c)
    pts += edge((x1 - r, y1), (x0 + r, y1), n_x)
    pts += arc(x0 + r, y1 - r, math.pi / 2, n_c)
    pts += edge((x0, y1 - r), (x0, y0 + r), n_y)
    pts += arc(x0 + r, y0 + r, math.pi, n_c)
    return pts


def gem_ring(d):
    """The gem's outline inset by d px (corner radius shrinking more slowly than a true offset, so
    the crown stays soft)."""
    a, b = (GX1 - GX0) / 2 - d, (GY1 - GY0) / 2 - d
    return rrect(GCX, GCY, a, b, max(GR - 0.6 * d, 0.5))


def gem_edge_x(y, side):
    """x of the gem's outline at row coordinate y on the left (side -1) or right (+1)."""
    xc = GX0 + GR if side < 0 else GX1 - GR
    if y < GY0 + GR:
        dy = GY0 + GR - y
    elif y > GY1 - GR:
        dy = y - (GY1 - GR)
    else:
        dy = 0.0
    dy = min(dy, GR)
    return xc + side * math.sqrt(max(0.0, GR * GR - dy * dy))


def signed_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def inset(poly, d):
    """Miter offset of a simple polygon by d inwards (small d only)."""
    n = len(poly)
    s = 1.0 if signed_area(poly) > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(poly[i - 1]), Vector(poly[i]), Vector(poly[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)) * s, Vector((-e1.y, e1.x)) * s  # inward normals
        m = (n0 + n1)
        if m.length < 1e-6:
            m = n0
        m.normalize()
        k = d / max(0.35, m.dot(n0))
        q = p1 + m * k
        out.append((q.x, q.y))
    return out


def prism(P, poly, z0, z1, mat, ch=0.25, top_mat=None, ch_mat=None):
    """Extrude a simple polygon from z0 to z1 with a chamfered top edge."""
    top_mat = mat if top_mat is None else top_mat
    ch_mat = top_mat if ch_mat is None else ch_mat
    s = 1.0 if signed_area(poly) > 0 else -1.0
    ins = inset(poly, ch)
    bot = [P.v((x, y, z0)) for x, y in poly]
    mid = [P.v((x, y, z1 - ch)) for x, y in poly]
    top = [P.v((x, y, z1)) for x, y in ins]
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        e = Vector(poly[j]) - Vector(poly[i])
        outn = (e.y * s, -e.x * s, 0.0)
        P.f([bot[i], bot[j], mid[j], mid[i]], mat, out=outn)
        P.f([mid[i], mid[j], top[j], top[i]], ch_mat, out=(outn[0], outn[1], 1.0))
    P.f(top, top_mat, out=(0, 0, 1))
    P.f(bot, mat, out=(0, 0, -1))


def cylinder_y(P, x, z, r, y0, y1, mat, n=12):
    pts = []
    for y in (y0, y1):
        for k in range(n):
            a = 2 * math.pi * (k + 0.5) / n
            pts.append((x + r * math.cos(a), y, z + r * math.sin(a)))
    T.hull(P, pts, mat)


def bolt_z(P, x, y, z, r, h, mat, n=6):
    """A hex bolt head standing on a horizontal face at height z."""
    pts = []
    for zz in (z - 0.05, z + h):
        for k in range(n):
            a = 2 * math.pi * k / n + math.pi / 6
            pts.append((x + r * math.cos(a), y + r * math.sin(a), zz))
    T.hull(P, pts, mat)


def bolt_y(P, x, z, y, r, h, sgn, mat, n=6):
    """A hex bolt head on a face of constant y (sgn: which way the face looks)."""
    pts = []
    for yy in (y - sgn * 0.05, y + sgn * h):
        for k in range(n):
            a = 2 * math.pi * k / n
            pts.append((x + r * math.cos(a), yy, z + r * math.sin(a)))
    T.hull(P, pts, mat)


# --- parts --------------------------------------------------------------------------------------
def jaw_poly(side):
    """The C-shaped jaw's plan outline. side -1: left (outer wall col 0, slot cols 1-3), +1: right
    (slot cols 19-21, outer wall cols 22-23)."""
    gap = 0.04
    if side < 0:
        xo, xs = -12.0, -11.0      # outer face, slot's outer side
        xi = GX0                   # slot's inner side (the gem's flank)
    else:
        xo, xs = 12.0, 10.0
        xi = GX1
    arc_top = [(gem_edge_x(y, side) + side * gap, y) for y in [JAW_Y0 + k * (GY0 + GR - JAW_Y0) / 6 for k in range(7)]]
    arc_bot = [(gem_edge_x(y, side) + side * gap, y) for y in [GY1 - GR + k * (JAW_Y1 - (GY1 - GR)) / 6 for k in range(7)]]
    poly = [(xo, JAW_Y0)] + arc_top + [(xi + side * gap, SLOT_Y0), (xs, SLOT_Y0), (xs, SLOT_Y1),
                                       (xi + side * gap, SLOT_Y1)] + arc_bot + [(xo, JAW_Y1)]
    # drop near-duplicate points
    out = []
    for p in poly:
        if not out or (Vector(p) - Vector(out[-1])).length > 1e-3:
            out.append(p)
    return out


def jaws(P, M):
    for side in (-1, 1):
        poly = jaw_poly(side)
        prism(P, poly, FLOOR - 0.02, JZ, M["jaw_wall"], ch=0.3, top_mat=M["claw"], ch_mat=M["lip"])
        xo = -12.0 if side < 0 else 12.0
        xs = -11.0 if side < 0 else 10.0
        xi = GX0 if side < 0 else GX1
        xm = (xo + xi) / 2
        # panel groove across each claw (a dark inset line a hair proud of the top) and a hex bolt
        for yc in ((JAW_Y0 + SLOT_Y0) / 2, (SLOT_Y1 + JAW_Y1) / 2):
            bolt_z(P, (xo + xi) / 2 - side * 0.3, yc, JZ, 0.42, 0.14, M["bolt"])
        for yg in (SLOT_Y0 - 0.45, SLOT_Y1 + 0.45):
            lo, hi = sorted((xo, xi))
            T.hull(P, T.cbox(lo + 0.4, hi - 0.4, yg - 0.09, yg + 0.09, JZ - 0.05, JZ + 0.02, 0.0), M["groove"])
        # front face (y = JAW_Y1, seen by the tilted camera): a groove and two bolts; rear the same groove
        x_lo, x_hi = sorted((xo, gem_edge_x(JAW_Y1, side)))
        for y_face, sgn in ((JAW_Y1, 1), (JAW_Y0, -1)):
            T.hull(P, T.cbox(x_lo + 0.3, x_hi - 0.5, y_face - sgn * 0.02 - 0.03, y_face + sgn * 0.06 + 0.03,
                             1.55, 1.72, 0.0), M["groove"])
            if sgn > 0:
                for xb in (x_lo + 0.9, x_hi - 1.1):
                    bolt_y(P, xb, 2.45, y_face, 0.34, 0.14, 1, M["bolt"])
                    bolt_y(P, xb, 0.95, y_face, 0.30, 0.12, 1, M["bolt"])
        # outer face (x = xo): two vertical grooves, a plate between
        for yg in (9.5, 17.5):
            T.hull(P, T.cbox(xo - 0.05 if side > 0 else xo - 0.06, xo + 0.06 if side < 0 else xo + 0.05,
                             yg - 0.09, yg + 0.09, FLOOR + 0.4, JZ - 0.45, 0.0), M["groove"])
        del xm
        # tension rod down the slot (sprite col 2 / col 21), into both claws
        xr = -9.5 if side < 0 else 9.3
        cylinder_y(P, xr, 1.25, 0.5, SLOT_Y0 - 0.6, SLOT_Y1 + 0.6, M["rod"])
        # rod collars where it leaves the claws
        for yc in (SLOT_Y0 + 0.2, SLOT_Y1 - 0.2):
            cylinder_y(P, xr, 1.25, 0.68, yc - 0.2, yc + 0.2, M["rod"], n=6)


def bars(P, M):
    """Cross bars at the top and bottom edges (rows 0-1 and 26-27, cols 8-14)."""
    for y0, y1, m in ((0.0, 2.0, M["bar_top"]), (26.0, 28.0, M["bar_bot"])):
        T.hull(P, T.cbox(-4.0, 3.0, y0 + 0.02, y1 - 0.02, FLOOR - 0.02, BAR_Z, 0.35, 0.3), m)
        # a raised rib along the bar's middle
        yc = (y0 + y1) / 2
        T.hull(P, T.cbox(-3.4, 2.4, yc - 0.32, yc + 0.32, BAR_Z - 0.1, BAR_Z + 0.22, 0.12), m)
        for xb in (-3.0, 2.0):
            bolt_z(P, xb + (0.0 if xb > 0 else 0.0), yc, BAR_Z + 0.2, 0.3, 0.1, M["bolt"])


def gem_field(sprite, sig=0.9, S=8):
    """Smooth gem palette field on 231 (the pulse frame used as the base), for painting the swirl:
    the red pixels upsampled S x and gaussian-blurred (sigma in sprite px), normalised by the red
    weight, so its iso-contours are smooth curves rather than pixel steps."""
    import numpy as np
    pix = next(f for f in sprite["frames"] if f["index"] == 231)["pixels"]
    a = np.array(pix, float)
    red = a >= 100
    vu = np.kron(np.where(red, a, 0.0), np.ones((S, S)))
    wu = np.kron(red.astype(float), np.ones((S, S)))
    rad = int(3 * sig * S)
    xk = np.arange(-rad, rad + 1) / S
    k = np.exp(-xk * xk / (2 * sig * sig))
    k /= k.sum()

    def blur(m):
        m = np.apply_along_axis(lambda q: np.convolve(np.pad(q, rad, mode="edge"), k, "valid"), 0, m)
        return np.apply_along_axis(lambda q: np.convolve(np.pad(q, rad, mode="edge"), k, "valid"), 1, m)
    f = blur(vu) / np.maximum(blur(wu), 1e-6)
    H, W = f.shape

    def at(x, y):
        u, v = (x + 12) * S - 0.5, y * S - 0.5
        c0, r0 = int(math.floor(u)), int(math.floor(v))
        tc, tr = u - c0, v - r0

        def g(rr, cc):
            return f[min(max(rr, 0), H - 1), min(max(cc, 0), W - 1)]
        return ((1 - tc) * (1 - tr) * g(r0, c0) + tc * (1 - tr) * g(r0, c0 + 1)
                + (1 - tc) * tr * g(r0 + 1, c0) + tc * tr * g(r0 + 1, c0 + 1))
    return at


SWIRL_LO, SWIRL_HI = 115.85, 116.6   # field below: the dark arms (115); at or above: bright cores (117)
SWIRL_NEUTRAL = 116.2                 # the body's value, which the rim band fades to


def _smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def gem(P, M, field):
    """The cushion-cut crystal: a vertical girdle with a chamfer, then a pchip crown over inset
    rounded rectangles to a flat table. The swirl is painted on the crown as smooth regions: each
    crown triangle is split along the iso-contours of the smoothed sprite field (marching
    triangles, the cut vertices shared between neighbours), so the arms have curved borders, not
    pixel steps. The rim band (the sprite's lit rim, lighting) fades to the body colour."""
    ds = [0.0, 0.25] + [0.25 + (TABLE_D - 0.25) * k / 6 for k in range(1, 7)]
    ds += [TABLE_D + 0.3 * k for k in range(1, 16) if TABLE_D + 0.3 * k < 6.9] + [7.0, 7.3]
    rings2 = [gem_ring(d) for d in ds]
    low = [P.v((x, y, CUP_Z)) for x, y in rings2[0]]
    rings = [[P.v((x, y, crown_z(d))) for x, y in r] for r, d in zip(rings2, ds)]
    n = len(low)
    cx, cy = GCX, GCY

    def val(co, d):
        w = _smoothstep(1.7, 2.9, d)
        return SWIRL_NEUTRAL + w * (field(co[0], co[1]) - SWIRL_NEUTRAL)

    vals = [[val(v.co, d) for v in r] for r, d in zip(rings, ds)]
    cut = {}

    def cut_vert(a, b, t):
        (pa, va), (pb, vb) = a, b
        s = (t - va) / (vb - va)
        p = Vector(pa) + (Vector(pb) - Vector(pa)) * s
        key = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
        if key not in cut:
            cut[key] = P.v(p)
        return (tuple(cut[key].co), t, cut[key])

    def split(poly, t):
        lo, hi = [], []
        m = len(poly)
        for i in range(m):
            a, b = poly[i], poly[(i + 1) % m]
            (lo if a[1] < t else hi).append(a)
            if (a[1] < t) != (b[1] < t):
                c = cut_vert((a[0], a[1]), (b[0], b[1]), t)
                lo.append(c)
                hi.append(c)
        return lo, hi

    def paint(tri, out):
        """tri: [(co, value, BMVert)]: emit the pieces of the triangle in each swirl region."""
        dark, rest = split(tri, SWIRL_LO)
        body, bright = split(rest, SWIRL_HI)
        for poly, m in ((dark, M["swirl0"]), (body, M["gem"]), (bright, M["swirl2"])):
            if len(poly) >= 3:
                P.f([q[2] for q in poly], m, out=out)

    for i in range(n):  # girdle wall
        j = (i + 1) % n
        P.f([low[i], low[j], rings[0][j], rings[0][i]], M["gem"], away=(cx, cy, 3.0))
    for k in range(len(rings) - 1):
        a, b, va, vb = rings[k], rings[k + 1], vals[k], vals[k + 1]
        for i in range(n):
            j = (i + 1) % n
            q = [(tuple(a[i].co), va[i], a[i]), (tuple(a[j].co), va[j], a[j]),
                 (tuple(b[j].co), vb[j], b[j]), (tuple(b[i].co), vb[i], b[i])]
            c = sum((Vector(e[0]) for e in q), Vector()) / 4
            out = (c.x - cx, c.y - cy, 6.0)
            if all(e[1] >= SWIRL_LO and e[1] < SWIRL_HI for e in q):
                P.f([e[2] for e in q], M["gem"], out=out)   # whole quad in the body: keep it a quad
                continue
            # split the quad on its shorter diagonal
            if (Vector(q[0][0]) - Vector(q[2][0])).length <= (Vector(q[1][0]) - Vector(q[3][0])).length:
                tris = ([q[0], q[1], q[2]], [q[0], q[2], q[3]])
            else:
                tris = ([q[0], q[1], q[3]], [q[1], q[2], q[3]])
            for t in tris:
                paint(t, out)
    # the table: a fan from the centre to the innermost (nearly a line) ring
    last, vl = rings[-1], vals[-1]
    cco = (cx, cy, crown_z(ds[-1]) + 0.005)
    centre = P.v(cco)
    cv = val(cco, 8.0)
    for i in range(n):
        j = (i + 1) % n
        paint([(tuple(last[i].co), vl[i], last[i]), (tuple(last[j].co), vl[j], last[j]), (cco, cv, centre)],
              (0, 0, 1))
    # bottom (closed, plain)
    cb = P.v((cx, cy, CUP_Z))
    for i in range(n):
        P.f([low[i], low[(i + 1) % n], cb], M["gem"], out=(0, 0, -1))


def cup(P, M):
    """The metal cup the gem sits in, just inside the gem's outline (hidden from above)."""
    ring = gem_ring(0.3)
    prism(P, ring, FLOOR - 0.02, CUP_Z + 0.05, M["cup"], ch=0.1)


def shell_proxy(coll):
    e = 0.15
    P = T.Part(f"{NAME}_proxy", smooth_angle=180)
    pts = []
    for d in (0.0, 1.5, 3.4, 6.6):
        for x, y in gem_ring(d)[::3]:
            pts.append((x, y, crown_z(d) + e))
    for x, y in gem_ring(-e)[::3]:
        pts.append((x, y, FLOOR + 0.3))
        pts.append((x, y, GIRDLE_Z))
    T.hull(P, pts, 0)
    for side in (-1, 1):
        xo = -12.0 if side < 0 else 12.0
        xs = -11.0 if side < 0 else 10.0
        xi = GX0 if side < 0 else GX1
        lo, hi = sorted((xo, xs))
        T.hull(P, T.cbox(lo - e, hi + e, JAW_Y0 - e, JAW_Y1 + e, FLOOR + 0.3, JZ + e, 0.2), 0)
        lo, hi = sorted((xo, xi))
        for y0, y1 in ((JAW_Y0, SLOT_Y0), (SLOT_Y1, JAW_Y1)):
            T.hull(P, T.cbox(lo - e, hi + e, y0 - e, y1 + e, FLOOR + 0.3, JZ + e, 0.2), 0)
    for y0, y1 in ((0.0, 2.0), (26.0, 28.0)):
        T.hull(P, T.cbox(-4.0 - e, 3.0 + e, y0 - e, y1 + e, FLOOR + 0.2, BAR_Z + 0.3, 0.2), 0)
    return T.finish(P, [], coll)


def floor(sprite, M):
    """Stone floor plate, 0..FLOOR, its top painted per pixel in four grey tones (as lib_b073)."""
    pix = sprite["frames"][0]["pixels"]
    colors = sprite["colors"]
    tones = ((1, 3), (4, 6), (7, 9), (10, 15))
    slots = []
    for lo, hi in tones:
        have = [i for i in range(lo, hi + 1) if str(i) in colors]
        mid = (lo + hi) / 2
        slots.append(M(min(have, key=lambda i: abs(i - mid)), f"stone{lo}", metallic=0.05, roughness=0.85)
                     if have else None)

    def slot_of(i):
        for (lo, hi), s in zip(tones, slots):
            if lo <= i <= hi:
                return s
        return slots[0]

    pit = M(1, "pit", metallic=0.0, roughness=0.9)

    def in_pit(r, c):
        """The deep floor seen down the jaw slots and the gaps by the bars (depth, palette 1)."""
        return ((8 <= r <= 18 and (1 <= c <= 3 or 19 <= c <= 21)) or
                ((2 <= r <= 3 or 24 <= r <= 25) and 8 <= c <= 14))

    def slot_at(r, c):
        return pit if in_pit(r, c) and pix[r][c] <= 3 else slot_of(pix[r][c])

    P = T.Part(f"{NAME}_floor", smooth_angle=5)
    T.hull(P, [(x, y, z) for x in (-12.0, 12.0) for y in (0.0, 28.0) for z in (0.0, FLOOR - 0.01)], slot_of(4))
    for r in range(28):
        c = 0
        while c < 24:
            s = slot_at(r, c)
            e = c + 1
            while e < 24 and slot_at(r, e) == s:
                e += 1
            vs = [P.v((xx, yy, FLOOR)) for xx, yy in ((c - 12, r), (e - 12, r), (e - 12, r + 1), (c - 12, r + 1))]
            P.f(vs, s, out=(0, 0, 1))
            c = e
    return P


def build():
    sprite = common.load_sprite(WT, NAME)
    for o in list(bpy.data.objects):  # factory startup: the default cube, camera and light
        if o.name in ("Cube", "Camera", "Light"):
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    coll = common.reset_collection(NAME)
    for o in list(bpy.data.objects):
        if o.name.startswith(NAME):
            bpy.data.objects.remove(o, do_unlink=True)
    Mt = Mats(sprite)
    M = {
        "claw": Mt(6, "claw", metallic=0.45, roughness=0.42),
        "lip": Mt(7, "lip", metallic=0.4, roughness=0.45),
        "jaw_wall": Mt(6, "jaw_wall", metallic=0.4, roughness=0.5),
        "groove": Mt(3, "groove", metallic=0.3, roughness=0.6),
        "bolt": Mt(7, "bolt", metallic=0.55, roughness=0.32),
        "rod": Mt(3, "rod", metallic=0.6, roughness=0.3),
        "bar_top": Mt(7, "bar_top", metallic=0.45, roughness=0.42),
        "bar_bot": Mt(4, "bar_bot", metallic=0.45, roughness=0.42),
        "cup": Mt(3, "cup", metallic=0.5, roughness=0.4),
        "gem": Mt(116, "gem", frames=glow_frames(116), metallic=0.3, roughness=0.3, emission=GLOW),
        "swirl0": Mt(115, "swirl0", frames=glow_frames(115), metallic=0.3, roughness=0.3, emission=GLOW),
        "swirl2": Mt(117, "swirl2", frames=glow_frames(117), metallic=0.3, roughness=0.3, emission=GLOW),
    }
    FP = floor(sprite, Mt)
    P = T.Part(NAME, smooth_angle=36)
    jaws(P, M)
    bars(P, M)
    cup(P, M)
    G = T.Part(f"{NAME}_gem", smooth_angle=24)
    gem(G, M, gem_field(sprite))
    body = T.finish(P, Mt.list, coll)
    gm = T.finish(G, Mt.list, coll)
    fl = T.finish(FP, Mt.list, coll)
    fl.data.shade_flat()
    fl["tyrian_ground"] = True
    # one mesh for the model proper (body + gem), as the game expects one node per model piece
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    gm.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = NAME
    proxy = shell_proxy(coll)
    shell = common.outline_shell(proxy, coll, faces=2500, islands="outer")
    shell.name = f"{NAME}_outline"
    bpy.data.objects.remove(proxy, do_unlink=True)
    return sprite, [body, fl, shell]


# --- review renders -----------------------------------------------------------------------------
def set_frame_colours(objs, frame):
    mats = {m for o in objs if o.type == "MESH" for m in o.data.materials if m}
    saved = []
    for m in mats:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        saved.append((m, tuple(m.diffuse_color), tuple(bsdf.inputs["Base Color"].default_value),
                      tuple(bsdf.inputs["Emission Color"].default_value)))
        rgb = m.get("tyrian_frame_rgb", {}).get(str(frame)) if frame is not None else None
        if rgb is not None:
            m.diffuse_color = (*rgb, 1.0)
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            if bsdf.inputs["Emission Strength"].default_value > 0:
                bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
    return saved


def restore(saved):
    for m, dc, bc, ec in saved:
        bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        m.diffuse_color = dc
        bsdf.inputs["Base Color"].default_value = bc
        bsdf.inputs["Emission Color"].default_value = ec


def camera(scene, name, loc, look, ortho=None, lens=50):
    data = bpy.data.cameras.new(name)
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    scene.collection.objects.link(cam)
    cam.location = loc
    d = Vector(look) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return cam


def renders(objs, sprite, out):
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    shell = objs[2]
    # 1) palette-index top views (flat colours, no AA), one per frame, 10 px per sprite px
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x, scene.render.resolution_y = 240, 280
    scene.render.resolution_percentage = 100
    shell.hide_render = True
    top = camera(scene, "cam_top", (0, 0, 10), (0, 0, 0), ortho=28 * PX)
    top.rotation_euler = (0, 0, 0)
    scene.camera = top
    for f in sprite["frames"]:
        saved = set_frame_colours(objs, f["index"])
        scene.render.filepath = str(out / f"index_{f['index']}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)
    # model-only mask (no floor): the jaws, bars and gem
    objs[1].hide_render = True
    scene.render.filepath = str(out / "mask_model.png")
    bpy.ops.render.render(write_still=True)
    objs[1].hide_render = False
    # 2) lit views (EEVEE)
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    vts = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in vts else "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.05, 0.055, 0.07, 1)
    bg.inputs["Strength"].default_value = 1.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.0
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(40), math.radians(-25), math.radians(-30))
    fill_d = bpy.data.lights.new("fill", "SUN")
    fill_d.energy = 1.0
    fill = bpy.data.objects.new("fill", fill_d)
    scene.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(-50), math.radians(30), math.radians(150))
    scene.render.resolution_x = scene.render.resolution_y = 480
    s = 2.9
    D = 6.0
    views = [
        ("top", (0, 0, 10), (0, 0, 0), s),
        ("game", (0, -D * 0.55, D * 0.85), (0, 0, 0.1), None),
        ("q34", (D * 0.62, -D * 0.62, D * 0.55), (0, 0, 0.1), None),
        ("q34rear", (-D * 0.62, D * 0.62, D * 0.55), (0, 0, 0.1), None),
        ("front", (0, -10, 0.25), (0, 0, 0.25), s),
        ("rear", (0, 10, 0.25), (0, 0, 0.25), s),
        ("side", (10, 0, 0.25), (0, 0, 0.25), s),
        ("under", (0.01, -0.01, -10), (0, 0, 0), s),
        ("close", (D * 0.3, -D * 0.38, D * 0.32), (0, 0, 0.25), None),
    ]
    saved = set_frame_colours(objs, 231)
    for name, loc, look, ortho in views:
        cam = camera(scene, f"cam_{name}", loc, look, ortho=ortho, lens=55)
        if name == "top":
            cam.rotation_euler = (0, 0, 0)
        if name == "under":
            cam.rotation_euler = (math.pi, 0, 0)
        scene.camera = cam
        scene.render.filepath = str(out / f"view_{name}.png")
        bpy.ops.render.render(write_still=True)
    restore(saved)
    cam = camera(scene, "cam_game2", (0, -D * 0.55, D * 0.85), (0, 0, 0.1), lens=55)
    scene.camera = cam
    scene.render.resolution_x = scene.render.resolution_y = 240
    for f in sprite["frames"]:
        saved = set_frame_colours(objs, f["index"])
        scene.render.filepath = str(out / f"game_{f['index']}.png")
        bpy.ops.render.render(write_still=True)
        restore(saved)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprite, objs = build()
    # the floor plate (tyrian_ground) stays out of the game's model (D130)
    common.export_sprite_model(WT, [o for o in objs if not o.get("tyrian_ground")], f"enemies/{NAME}",
                               sprite["sprites"])
    tris = 0
    for o in objs[:2]:
        o.data.calc_loop_triangles()
        tris += len(o.data.loop_triangles)
    print(f"built {NAME}: {tris} triangles (model + floor), shell {len(objs[2].data.polygons)} faces")
    if "--render" in argv:
        renders(objs, sprite, Path(argv[argv.index("--render") + 1]))
