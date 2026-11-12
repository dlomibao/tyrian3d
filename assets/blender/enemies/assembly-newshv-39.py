"""Drilling machine (newshv.shp 1|3 over 39|41, assembly of 2 pieces, 24x56 px): cross-sections first.

What it is: a tracked tunnelling machine seen from above, crawling DOWN the screen (south = front). A blue
housing (a tall drive-motor block in the middle, a rounded hood at the rear left, a step with a valve block,
a support arm and a centre strut with hydraulic rams, a wedge gearbox on the right and a small grey side
motor behind it) rides on two crawler tracks. In front of it a big grey auger bit lies nose-down along the
direction of travel, its lower line on the ground and its point biting into it; the two sprite frames turn
the bit's two helical flights by half a pitch (the -f2 models).

Engineering first (design angle A): every part is a section stack in sprite px (c east, r south, h up).
- Auger: circular sections on a tilted axis (h = 10.4 - 0.275 (r - 24): 12.3 at the hub, 1.6 at the point,
  15 deg nose-down), half width pchip through the inner mask's row extents. Two helical flights 5 px apart
  as raised lands with steep machined flanks; the rounded shoulder (rows 17-21) is unthreaded; the last
  3 px are the hardened point (pal 5).
- Housing blocks: chamfered prisms built as ring stacks (inset, height), each with a modelled panel seam
  round its walls; rounded hood (3-segment fillet); beams as superellipse lofts; rams as two-stage tubes.
- Crawler: two stadium-section track pods with grouser plates and road wheels, under the deck.
Mapped to Blender as the current script: x = (c - 12) / 12, y = (28 - r) / 12, z = h / 12.

Silhouette: the sprite's INNER mask (D74), as the blueprint fitted it. Colours: the sprite's palette index
median per region (blueprint measure + prep.py), darkest ink and brightest sheen dropped.

Exports newshv-1, newshv-39, newshv-1-f2, newshv-39-f2 (common.export_sprite_model, each with its outline
shell, D51/D90) from a model-only AO/roughness bake (D50/D65). Run:
  tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshv-39.py
Debug: -- [--out x.glb] (design glb, -f2 pieces 3 units east) [--no-cull] [--no-bake] [--blend f.blend]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b081 as lib  # noqa: E402
import usp_talon as T  # noqa: E402

ROOT = common.repo_root(__file__)
NAME = "assembly-newshv-39"
PIECES = ["newshv-1", "newshv-39"]
LAYOUT = {"newshv-1": (0, -14), "newshv-39": (0, 14)}
F2_DX = 3.0  # design glb only: the -f2 pieces sit this far east


def P(c, r, h):
    return ((c - 12) / 12, (28 - r) / 12, h / 12)


# --- materials: (palette index, finish) ---------------------------------------------------------------
FINISH = {"paint": (0.35, 0.45), "steel": (0.75, 0.3), "drill": (0.5, 0.35), "grey": (0.6, 0.4), "track": (0.3, 0.7),
          "dark": (0.3, 0.6)}


class Mesh:
    def __init__(self, colors):
        self.bm = bmesh.new()
        self.colors = colors
        self.mats = []
        self.key = {}

    def m(self, idx, fin="paint"):
        k = (idx, fin)
        if k not in self.key:
            met, rough = FINISH[fin]
            self.key[k] = len(self.mats)
            self.mats.append(common.palette_material(self.colors, idx, f"nshv39a_{fin}", metallic=met,
                                                     roughness=rough))
        return self.key[k]

    def v(self, c, r, h):
        return self.bm.verts.new(P(c, r, h))

    def face(self, vs, mat):
        f = self.bm.faces.new(vs)
        f.material_index = mat
        return f


# --- 2D helpers ------------------------------------------------------------------------------------------

def area(poly):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) / 2


def normals(poly):
    """Inward unit normal of each edge i (poly[i] -> poly[i+1])."""
    sg = 1 if area(poly) > 0 else -1
    out = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        nx, ny = -(b[1] - a[1]), b[0] - a[0]
        ln = math.hypot(nx, ny)
        out.append((sg * nx / ln, sg * ny / ln))
    return out


def inset(poly, d):
    """Offset each edge inward by d (a number or one per edge) and intersect neighbours."""
    n, N = len(poly), normals(poly)
    dd = (lambda i: d[i]) if isinstance(d, (list, tuple)) else (lambda i: d)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        lines.append((a[0] + N[i][0] * dd(i), a[1] + N[i][1] * dd(i), b[0] - a[0], b[1] - a[1]))
    out = []
    for i in range(n):
        L1, L2 = lines[i - 1], lines[i]
        den = L1[2] * L2[3] - L1[3] * L2[2]
        if abs(den) < 1e-9:
            out.append((L2[0], L2[1]))
            continue
        t = ((L2[0] - L1[0]) * L2[3] - (L2[1] - L1[1]) * L2[2]) / den
        out.append((L1[0] + L1[2] * t, L1[1] + L1[3] * t))
    return out


def edge_pal(spec, n_in):
    if isinstance(spec, int):
        return spec
    ox, oy = -n_in[0], -n_in[1]
    k = ("E" if ox > 0 else "W") if abs(ox) > abs(oy) else ("S" if oy > 0 else "N")
    return spec.get(k, spec.get("def"))


def rect(c0, r0, c1, r1):
    return [(c0, r0), (c1, r0), (c1, r1), (c0, r1)]


def pchip(xk, yk, xs):
    n = len(xk)
    d = [(yk[i + 1] - yk[i]) / (xk[i + 1] - xk[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * (xk[i + 1] - xk[i]) + (xk[i] - xk[i - 1])
            w2 = (xk[i + 1] - xk[i]) + 2 * (xk[i] - xk[i - 1])
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    out = []
    for x in xs:
        i = 0
        while i < n - 2 and x > xk[i + 1]:
            i += 1
        h = xk[i + 1] - xk[i]
        t = (x - xk[i]) / h
        t2, t3 = t * t, t * t * t
        out.append((2 * t3 - 3 * t2 + 1) * yk[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * yk[i + 1]
                   + (t3 - t2) * h * m[i + 1])
    return out


# --- 3D primitives ---------------------------------------------------------------------------------------

def stack(M, poly, rings, side, chamfer, top, bottom=None, seam=None, fin="paint"):
    """A ring stack over `poly`: rings = [(inset (number or per edge), h)] bottom to top. A band between
    two rings at the same inset is a wall (palette `side`), else a chamfer/step (`chamfer`, or `seam`
    for a seam groove's ledges). Palettes may be {N,S,E,W,def} by the edge's outward direction."""
    N = normals(poly)
    loops = []
    for d, h in rings:
        pts = inset(poly, d) if (d if not isinstance(d, (list, tuple)) else max(d)) else poly
        loops.append(([M.v(c, r, h) for c, r in pts], d))
    n = len(poly)
    for k in range(len(loops) - 1):
        (a, da), (b, db) = loops[k], loops[k + 1]
        wall = da == db
        for i in range(n):
            j = (i + 1) % n
            spec = side if wall else (seam if (seam is not None and rings[k][1] == rings[k + 1][1]) else chamfer)
            M.face([a[i], a[j], b[j], b[i]], M.m(edge_pal(spec, N[i]), fin))
    M.face(list(reversed(loops[0][0])), M.m(edge_pal(bottom if bottom is not None else side, (0, 1)), fin))
    M.face(loops[-1][0], M.m(top, fin))


def prism(M, poly, h0, h1, ch=0.3, drop=None, round_=1, top=55, side=53, chamfer=None, seams=(), seam_pal=None,
          fin="paint"):
    """Chamfered (round_ > 1: filleted) prism h0..h1, walls carrying modelled panel seams: seams =
    [(h, depth, width)] grooves cut round the walls."""
    chm = max(ch) if isinstance(ch, (list, tuple)) else ch
    drop = chm if drop is None else drop
    rings = [(0.0, h0)]
    for hs, dep, w in seams:
        rings += [(0.0, hs), (dep, hs), (dep, hs + w), (0.0, hs + w)]
    rings.append((0.0, h1 - drop))
    for k in range(1, round_ + 1):
        t = k / round_ * math.pi / 2
        f = 1 - math.cos(t) if round_ > 1 else 1
        g = math.sin(t) if round_ > 1 else 1
        d = [v * f for v in ch] if isinstance(ch, (list, tuple)) else ch * f
        rings.append((d, h1 - drop + drop * g))
    sp = seam_pal if seam_pal is not None else 51
    # seam ledges: a groove's floor/ceiling are rings at the same h with differing inset
    stack(M, poly, rings, side, chamfer if chamfer is not None else side, top, seam=sp, fin=fin)


def section(n, p=2.0):
    out = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        co, si = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(co) ** (2 / p), co), math.copysign(abs(si) ** (2 / p), si)))
    return out


def loft(M, rings, pals, fin, cap0=None, cap1=None):
    """Quads between consecutive rings (lists of (c, r, h)); pals per band; caps as ngons."""
    vs = [[M.v(*p) for p in ring] for ring in rings]
    for k in range(len(vs) - 1):
        a, b = vs[k], vs[k + 1]
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            M.face([a[i], a[j], b[j], b[i]], M.m(pals[k] if isinstance(pals, list) else pals, fin))
    if cap0 is not None:
        M.face(list(reversed(vs[0])), M.m(cap0, fin))
    if cap1 is not None:
        M.face(vs[-1], M.m(cap1, fin))


def loft_r(M, st, pal, fin="paint", n=16, p=2.0, cap=None):
    """Loft along r: stations (r, c, h, a = half width in c, b = half height)."""
    sec = section(n, p)
    rings = [[(c + u * a, r, h + v * b) for u, v in sec] for r, c, h, a, b in st]
    loft(M, rings, pal, fin, cap0=cap if cap is not None else pal, cap1=cap if cap is not None else pal)


def loft_c(M, st, pal, fin="paint", n=20, p=2.0, cap=None):
    """Loft along c: stations (c, r, h, a = half length in r, b = half height)."""
    sec = section(n, p)
    rings = [[(c, r + u * a, h + v * b) for u, v in sec] for c, r, h, a, b in st]
    loft(M, rings, pal, fin, cap0=cap if cap is not None else pal, cap1=cap if cap is not None else pal)


def tube(M, a, b, rad, pal, fin="grey", n=10):
    """A closed round tube from a to b (points (c, r, h))."""
    d = [b[i] - a[i] for i in range(3)]
    L = math.sqrt(sum(x * x for x in d))
    w = [x / L for x in d]
    u = [w[1], -w[0], 0.0]
    ul = math.hypot(u[0], u[1])
    u = [1.0, 0.0, 0.0] if ul < 1e-6 else [x / ul for x in u]
    v = [w[1] * u[2] - w[2] * u[1], w[2] * u[0] - w[0] * u[2], w[0] * u[1] - w[1] * u[0]]
    ring = lambda o: [tuple(o[i] + rad * (x * u[i] + y * v[i]) for i in range(3)) for x, y in section(n)]  # noqa: E731
    loft(M, [ring(a), ring(b)], pal, fin, cap0=pal, cap1=pal)


def ram(M, p0, pm, p1, rb, rr, pb, pr):
    tube(M, p0, pm, rb, pb, "paint")
    tube(M, [pm[i] - (pm[i] - p0[i]) * 0.05 for i in range(3)], p1, rr, pr, "steel")


# --- the auger bit ---------------------------------------------------------------------------------------
AXC = 12.5


def axis_h(r):
    return 10.4 - 0.275 * (r - 24)


# Half widths (px) at row edges, pchip: the blueprint's fit to the inner mask, the shoulder starting at
# row 17.9 behind the hub collar (sprite row 17 is the collar's grey 5).
DK = [(17.9, 4.6), (18.2, 6.0), (18.6, 6.85), (19.5, 7.1), (20.5, 7.9), (21.5, 8.6), (22.5, 9.1), (24.5, 9.65),
      (26.5, 9.7), (28.5, 9.5), (30.5, 8.75), (33, 8.1), (35.5, 7.3), (38, 6.45), (40.5, 5.65), (43, 4.75),
      (45.5, 3.95), (48, 3.5), (50.5, 2.7), (52.5, 2.15), (54, 1.3), (55.3, 0.6), (56, 0)]
NCOL, STARTS, PITCH = 40, 2, 5.0
FLIGHT = 0.10  # flight height as a fraction of the radius (about 1 px at the widest)
CREST = 0.04  # the lands stand this far proud of the inner-mask row extent (they make the silhouette)
# Flight cross-profile per column within one start's period (NCOL / STARTS = 20 columns): a 2-column
# chamfered flank up, a 7-column land, a 2-column flank down, a 9-column root.
PERIOD = NCOL // STARTS
LAND = [0.0] * PERIOD
for _k in range(PERIOD):
    LAND[_k] = 0.5 if _k in (0, 13) else (1.0 if 1 <= _k <= 12 else 0.0)


RING = 0.34  # ring spacing along the bit (px)


def drill(M, phase, shell=False):
    """The auger on a helix-aligned grid: ring i at row rs[i] is turned so that column k stays on the
    same helix line (t = 2 pi (k + 0.5) / NCOL - 2 pi (r / PITCH + phase) / STARTS), so the flights'
    flanks run along mesh edges (no staircase) and frame 2 (phase 0.5) is the same bit turned."""
    rs = [17.9 + RING * i for i in range(int((55.9 - 17.9) / RING) + 1)] + [56.0]
    rs = sorted(set([round(r, 3) for r in rs] + [18.2, 18.6]))
    as_ = pchip([k[0] for k in DK], [k[1] for k in DK], rs)

    def amp(r):  # flights run out on the shoulder and at the point
        if r < 21:
            return 0.0
        if r < 23.5:
            return (r - 21) / 2.5
        if r > 53.5:
            return max(0.0, (55.8 - r) / 2.3)
        return 1.0

    rings = []
    for r, a in zip(rs, as_):
        a = max(0.0, a)
        if a < 1e-3:
            rings.append([M.v(AXC, r, axis_h(r))])
            continue
        ring = []
        for k in range(NCOL):
            # the grid only twists where the flights are (the shoulder keeps plain rings)
            t = 2 * math.pi * (k + 0.5) / NCOL - 2 * math.pi * (max(r, 21.0) / PITCH + phase) / STARTS
            rad = a * (1 + CREST * amp(r) - FLIGHT * amp(r) * (1.0 - LAND[k % PERIOD]))  # lands on the mask edge, root below it
            if shell:  # outline source: a smooth body of revolution through the lands, no grooves (see main)
                rad = a * (1 + CREST * amp(r))
            ring.append(M.v(AXC + rad * math.cos(t), r, axis_h(r) + rad * math.sin(t)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B, rm = rings[i], rings[i + 1], (rs[i] + rs[i + 1]) / 2
        for k in range(NCOL):
            j = (k + 1) % NCOL
            lk = min(LAND[k % PERIOD], LAND[j % PERIOD])
            if rm < 21.0:
                mat = M.m(8, "drill")  # unthreaded lit shoulder
            elif rm > 50.5:
                mat = M.m(5, "drill")  # hardened point
            elif lk >= 1.0:
                mat = M.m(7, "drill")  # flight lands
            else:
                mat = M.m(6, "drill")  # flanks and root
            if len(B) == 1:
                M.face([A[k], A[j], B[0]], mat)
            else:  # skewed helix quads: always split on A[k]-B[j], their short diagonal
                M.face([A[k], A[j], B[j]], mat)
                M.face([A[k], B[j], B[k]], mat)
    M.face(list(reversed(rings[0])), M.m(5, "grey"))
    # Hub: a collar ring where the bit meets the drive (sprite row 17), and the drive shaft.
    loft_r(M, [(r, AXC, axis_h(r), a, a) for r, a in ((16.3, 4.0), (16.5, 4.9), (17.8, 4.9), (18.05, 4.5))],
           5, "grey", n=24)
    loft_r(M, [(9.5, AXC, axis_h(9.5), 2.6, 2.6), (16.5, AXC, axis_h(16.5), 2.6, 2.6)], 6, "steel", n=16)


# --- crawler, chassis and housing ----------------------------------------------------------------------------

def stadium(r0, r1, R, hc, n=8):
    p = []
    for k in range(n + 1):
        t = -math.pi / 2 + math.pi * k / n
        p.append((r1 - R + R * math.cos(t), hc + R * math.sin(t)))
    for k in range(n + 1):
        t = math.pi / 2 + math.pi * k / n
        p.append((r0 + R + R * math.cos(t), hc + R * math.sin(t)))
    return p


def track(M, r0, r1, c0, c1, wheels, outer_c):
    """A crawler track pod: a stadium-section belt (pal 3) with grouser plates (2) and road wheels
    (6) on its outer face."""
    R, hc = 3.0, 3.0
    poly = stadium(r0, r1, R, hc)
    A = [(c0, r, h) for r, h in poly]
    B = [(c1, r, h) for r, h in poly]
    loft(M, [A, B], 3, "track", cap0=2, cap1=2)
    # grousers: thin bars across the belt, every 1.3 px along its path
    pts = poly + [poly[0]]
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = sum(math.dist(a, b) for a, b in segs)
    s, step = 0.4, 1.3
    while s < total:
        acc = 0.0
        for a, b in segs:
            L = math.dist(a, b)
            if acc + L >= s:
                t = (s - acc) / L
                rr, hh = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                tr, th = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                nr, nh = th, -tr  # outward normal (stadium runs clockwise in (r, h))
                cr, ch_ = rr - (rr - (r0 + r1) / 2) * 0, hh
                if (cr - (r0 + r1) / 2) * nr + (ch_ - hc) * nh < 0:
                    nr, nh = -nr, -nh
                w, d = 0.3, 0.32
                q = [(rr - tr * w, hh - th * w), (rr + tr * w, hh + th * w),
                     (rr + tr * w + nr * d, hh + th * w + nh * d), (rr - tr * w + nr * d, hh - th * w + nh * d)]
                loft(M, [[(c0 + 0.1, x, y) for x, y in q], [(c1 - 0.1, x, y) for x, y in q]], 2, "track", cap0=2,
                     cap1=2)
                break
            acc += L
        s += step
    for r in wheels:
        loft_c(M, [(outer_c, r, hc, 2.2, 2.2), (outer_c + (0.35 if outer_c > 12 else -0.35), r, hc, 2.2, 2.2)],
               6, "grey", n=16, cap=6)
        loft_c(M, [(outer_c + (0.35 if outer_c > 12 else -0.35), r, hc, 0.9, 0.9),
                   (outer_c + (0.6 if outer_c > 12 else -0.6), r, hc, 0.7, 0.7)], 4, "grey", n=10, cap=4)


def housing(M):
    # crawler + chassis (rows 1.5-17), hidden from straight above
    track(M, 2.6, 17.0, 2.4, 6.6, [5.6, 9.8, 14.0], 2.4)
    track(M, 6.6, 17.0, 17.6, 20.8, [9.6, 14.0], 20.8)
    prism(M, rect(6.6, 3.0, 17.6, 16.6), 1.4, 9.0, ch=0.4, top=52, side=52)
    prism(M, [(4.6, 1.6), (9, 1.6), (16.8, 1.6), (17.3, 3.0), (21.3, 7.0), (21.3, 16.4), (20.8, 17.2), (3.4, 17.2),
              (2.3, 16.2), (2.3, 6.6), (1.4, 6.0), (1.4, 4.6), (2.0, 4.0), (3.0, 2.8)], 6.4, 9.2, ch=0.35,
          top=53, side=52)
    # centre drive-motor block: top 56, lit west chamfer 60, rib 57 + groove 55 on the east, dark east
    # wall 53, front slope 52; a seam round its walls at h 16 and a top access panel with 4 bolts
    prism(M, [(9, 1), (16.8, 1), (18, 3.5), (18, 10), (9, 10)], 9.2, 24.0, ch=[0.6, 1.0, 1.0, 2.0, 0.9], drop=1.2,
          top=56, side={"N": 53, "S": 52, "E": 53, "W": 55}, chamfer={"N": 57, "S": 52, "E": 53, "W": 60},
          seams=[(15.6, 0.18, 0.5)])
    prism(M, rect(14.9, 1.9, 15.9, 7.9), 23.6, 24.05, ch=0.05, top=55, side=55)
    prism(M, rect(15.9, 1.9, 16.95, 8.0), 23.6, 24.6, ch=0.2, top=57, side=55)
    prism(M, rect(10.3, 2.4, 14.4, 6.8), 23.9, 24.14, ch=0.15, top=56, side=56, chamfer=55)
    for c, r in ((10.8, 2.9), (13.9, 2.9), (10.8, 6.3), (13.9, 6.3)):
        loft(M, [[(c + 0.27 * x, r + 0.27 * y, 24.1) for x, y in section(8)],
                 [(c + 0.22 * x, r + 0.22 * y, 24.4) for x, y in section(8)]], 58, "grey", cap0=58, cap1=58)
    # rear cap with cooling louvres (north face)
    prism(M, rect(9, -0.05, 14.05, 1.4), 13.0, 21.5, ch=0.35, top=55, side=54, chamfer={"N": 58, "def": 55})
    for i in range(4):
        prism(M, rect(9.6 + i * 1.15, -0.3, 10.3 + i * 1.15, 0.1), 14.5, 20.0, ch=0.1, top=52, side=52)
    # hood: rounded block, top 59, lit rib (col 7, 60) with a groove (col 6, 56), gap col 8 (53)
    prism(M, [(4.2, 1), (7.4, 1), (8.05, 1.8), (8.05, 6.6), (1, 6.6), (1, 4.2), (2.2, 3), (3.2, 2)], 9.2, 21.0,
          ch=1.2, drop=1.4, round_=3, top=59, side={"N": 52, "S": 55, "W": 53, "E": 53},
          chamfer={"N": 54, "S": 55, "W": 58, "E": 56}, seams=[(14.0, 0.15, 0.45)])
    prism(M, rect(5.9, 1.9, 6.9, 6.0), 20.6, 21.03, ch=0.05, top=56, side=56)
    prism(M, rect(6.9, 1.6, 7.95, 6.1), 20.4, 21.6, ch=0.25, top=60, side=57)
    prism(M, rect(8.0, 1.9, 9.05, 8.0), 9.2, 17.0, ch=0.2, top=53, side=53)
    # lower step: dark ledge with a valve block (lit west face 60) and its hand wheel
    prism(M, [(1.2, 6.5), (8.05, 6.5), (9.05, 8), (9.05, 10.2), (2.1, 10.2), (2.1, 7.2)], 9.2, 15.0, ch=0.35,
          top=51, side=51)
    prism(M, rect(4.9, 6.8, 8.0, 10.0), 14.8, 16.6, ch=0.4, top=55, side=55, chamfer={"W": 60, "def": 55})
    # left support arm (box beam, 53) to the bearing foot; ram barrel 58 / rod 60 on its outer edge
    loft_r(M, [(9.8, 4.0, 13.8, 1.75, 1.2), (14.4, 4.0, 12.6, 1.75, 1.2)], 53, n=16, p=5)
    ram(M, (3.4, 6.9, 15.5), (3.4, 10.3, 15.2), (3.4, 15.0, 14.2), 0.62, 0.42, 58, 60)
    prism(M, rect(3.9, 17.0, 6.1, 18.9), 6.6, 12.4, ch=0.4, top=53, side=53)
    prism(M, rect(2.6, 14.0, 8.0, 17.6), 6.6, 13.8, ch=0.5, top=55, side=53, chamfer={"W": 59, "N": 59, "def": 53},
          seams=[(10.0, 0.12, 0.4)])
    # grey reduction drum (transverse axis) with two bands
    loft_c(M, [(c, 13.0, 15.0, a, a) for c, a in ((6.0, 2.4), (6.15, 2.85), (6.55, 3.0), (11.6, 3.0), (12.1, 3.0))],
           7, "grey", n=24, cap=6)
    for c in (7.6, 9.6):
        loft_c(M, [(c, 13.0, 15.0, 3.14, 3.14), (c + 0.35, 13.0, 15.0, 3.14, 3.14)], 6, "grey", n=24)
    # centre strut (55 per the sprite's strut columns) with a ram (barrel and rod 59), dark recess beside it
    loft_r(M, [(9.4, 13.75, 18.2, 1.75, 1.4), (16.9, 13.75, 15.0, 1.75, 1.4)], 56, n=16, p=5)
    ram(M, (13.5, 9.2, 19.8), (13.5, 12.0, 18.9), (13.5, 16.6, 16.8), 0.62, 0.45, 59, 59)
    prism(M, rect(15.4, 9.0, 17.1, 17.3), 9.2, 13.0, ch=0.2, top=52, side=52)
    # wedge gearbox (right): top 55, lit west ridge 58 (57 per the sprite), NE chamfer 54, slot 51, bolts 57
    prism(M, [(17, 9.6), (19.2, 9.9), (23, 13.1), (23, 15.7), (21.8, 16.9), (21, 17.8), (17, 17.8)], 6.6, 17.6,
          ch=[0.9, 1.0, 0.6, 0.6, 0.6, 0.6, 0.9], drop=1.0, top=55, side={"def": 53},
          chamfer={"W": 57, "N": 54, "E": 54, "S": 53, "def": 54}, seams=[(12.0, 0.15, 0.45)])
    prism(M, rect(17.2, 15.05, 19.3, 16.0), 17.1, 17.65, ch=0.05, top=51, side=51)
    for r in (12.6, 14.0):
        loft(M, [[(20.45 + 0.27 * x, r + 0.27 * y, 17.5) for x, y in section(8)],
                 [(20.45 + 0.22 * x, r + 0.22 * y, 17.85) for x, y in section(8)]], 57, "grey", cap0=57, cap1=57)
    # side motor (grey): a cylinder along r with a domed rear end, a band, on a mount and cradle
    st = []
    for t in (0, 0.15, 0.35, 0.6, 0.85, 1):
        a = 1.65 * math.sqrt(1 - (1 - t) ** 2)
        st.append((6.2 + 1.6 * t, 20.0, 11.6, max(a, 0.05), max(a, 0.05)))
    st.append((10.6, 20.0, 11.6, 1.65, 1.65))
    loft_r(M, st, 5, "grey", n=18, cap=4)
    for k in range(5):  # cooling fins round the motor
        r = 8.4 + 0.42 * k
        loft_r(M, [(r, 20.0, 11.6, 1.8, 1.8), (r + 0.18, 20.0, 11.6, 1.8, 1.8)], 6, "grey", n=18)
    prism(M, [(17.6, 3.6), (18.6, 3.6), (20.3, 5.4), (20.3, 7.4), (17.6, 7.4)], 9.0, 10.8, ch=0.3, top=4, side=4,
          fin="grey")
    loft_r(M, [(7.4, 20.0, 11.6, 1.8, 1.8), (8.0, 20.0, 11.6, 1.8, 1.8)], 7, "grey", n=18)
    prism(M, rect(18.6, 6.6, 21.4, 10.4), 9.0, 10.6, ch=0.2, top=52, side=52)
    # bearing yoke across row 17, holding the bit's hub
    prism(M, rect(3.0, 16.6, 21.0, 18.05), 7.0, 13.4, ch=0.4, top=53, side=52, seams=[(10.0, 0.12, 0.4)])


def build(colors, phase, tag, coll, shell=False):
    M = Mesh(colors)
    drill(M, phase, shell)
    housing(M)
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new(f"{NAME}{tag}")
    bm.to_mesh(me)
    bm.free()
    for m in M.mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(f"{NAME}{tag}", me)
    coll.objects.link(obj)
    return obj


def sink_shell(sh, body, tol=0.01, inside=0.004, rmax=26.5):
    """Pull outline-shell vertices that stand outside the culled piece back under it. The sealed copy
    fills the gaps between the housing's blocks; where the cull then opened those gaps the shell stood
    up to 0.12 units proud of the model. Rows past rmax meet the drill piece's shell and stay."""
    from mathutils.bvhtree import BVHTree
    bm = bmesh.new()
    bm.from_mesh(body.data)
    tree = BVHTree.FromBMesh(bm)
    bm.free()
    n = 0
    for v in sh.data.vertices:
        if 28 - v.co.y * 12 - 14 > rmax:  # piece-local y -> sprite row within the 28-row piece
            continue
        loc, nor, _, _ = tree.find_nearest(v.co)
        if loc is None:
            continue
        s = (v.co - loc).dot(nor)
        if s > tol:
            v.co = loc - nor * inside
            n += 1
    print(f"{sh.name}: sank {n} shell vertices")


def split_open(obj, layout, coll):
    """split_assembly's cut without caps, for the outline shell: a capped shell inks every seam."""
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


def main():
    import tempfile
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    colors = {"name": NAME, "colors": {}}
    sprites = {n: common.load_sprite(ROOT, n) for n in PIECES}
    for n in PIECES:
        colors["colors"].update(sprites[n]["colors"])
    coll = common.reset_collection(NAME)
    bake = "--no-bake" not in argv
    export = []
    total = 0
    for fi, (phase, tag, dx) in enumerate(((0.0, "", 0.0), (0.5, "-f2", F2_DX))):
        whole = build(colors, phase, tag, coll)
        tris = sum(len(p.vertices) - 2 for p in whole.data.polygons)
        print(f"{NAME}{tag}: whole {tris} triangles")
        # the outline shell comes from a sealed copy made before the cull and the bake (D90/D118)
        # The drill's part of it is a smooth body of revolution through the flight lands: a copy with
        # the ~1 px helix grooves kept them half-filled in the voxel shell, and OutlineEffect's inverted
        # hull drew their back-facing flanks as black dashes along every groove in the game.
        closed = build(colors, phase, tag + "_shellsrc", coll, shell=True)
        shell = common.outline_shell(closed, coll, voxel=0.012, faces=3500, smooth=6, inside=0.004)
        bpy.data.objects.remove(closed)
        if bake:  # model-only AO / roughness bake, every material textured (D50, D65)
            tint, textured = T.TINT, T.TEXTURED
            # the helix drill's thin skewed faces unwrap into islands the bake leaves partly empty (black
            # patches in the game), so the drill keeps its plain palette materials; the housing is baked
            T.TINT = (1.0, 1.0, 1.0)
            T.TEXTURED = tuple(i for i, m in enumerate(whole.data.materials) if "drill" not in m.name)
            try:
                T.bake_maps(whole, tempfile.mkdtemp(prefix="nshv39_bake_"), size=1024, samples=48)
            finally:
                T.TINT, T.TEXTURED = tint, textured
            for img in bpy.data.images:
                if img.name.startswith("talon_"):
                    img.name = img.name.replace("talon_", f"{NAME}{tag}_")
        layout = [(p + tag, *LAYOUT[p]) for p in PIECES]
        pieces = common.split_assembly(whole, layout, coll)
        shells = split_open(shell, layout, coll)
        whole.hide_render = shell.hide_render = True
        for p in PIECES:
            name, (cx, cy) = p + tag, LAYOUT[p]
            o = pieces[name]
            if "--no-cull" not in argv:
                T.cull_hidden(o, grid=3, ndirs=40)
            o.data.set_sharp_from_angle(angle=math.radians(35))
            wn = o.modifiers.new("weighted", "WEIGHTED_NORMAL")
            wn.keep_sharp = True
            wn.weight = 50
            common._apply_modifiers(o)
            t = sum(len(q.vertices) - 2 for q in o.data.polygons)
            total += t
            print(f"piece {name}: {t} triangles, outline {len(shells[name].data.polygons)} faces")
            frame = sprites[p]["frames"][fi]
            num = int(frame["image"].split("-")[-1].split(".")[0])
            sh = shells[name]
            if p == "newshv-1":
                sink_shell(sh, o)
            if "--out" in argv:
                for ob in (o, sh):
                    ob.location = (cx / 12 + dx, -cy / 12, 0)
                    export.append(ob)
            else:
                common.export_sprite_model(ROOT, [o, sh], f"enemies/{name}",
                                           lib.frames_subset(sprites[p], {num}),
                                           image_format="WEBP" if bake else "AUTO")
    print(f"total {total} triangles over the 4 models")
    if "--out" in argv:
        out = common.export_glb(export, argv[argv.index("--out") + 1], image_format="WEBP" if bake else "AUTO")
        print(f"design export {out}")
    if "--blend" in argv:
        bpy.ops.wm.save_as_mainfile(filepath=argv[argv.index("--blend") + 1])


if __name__ == "__main__":
    main()
