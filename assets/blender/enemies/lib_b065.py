"""Batch b065: the horned bronze flagship of newsh4.shp, one model cut into two assemblies.

assembly-newsh4-81 (newsh4-81, -83, -85: the head, horns and shoulder pods) sits above
assembly-newsh4-123 (newsh4-119, -121, -123: the body, wings and gun pods), drawn 24 px lower and
overlapping it by 4 px. Both scripts build this one craft in a shared 72 x 52 px frame (column c and
row r are pixel edges; the frame's top-left is screen pixel (135, 159), the top-left of newsh4-81;
Blender X = 0 is column edge 30 and Y = 0 is row edge 26), bake it, and cut their own three
24 x 28 px pieces from it with common.split_assembly, so the overlap rows are drawn identically by
both. Enemy types 468-473 have no armour: an event-18 flyby in level 1, just before the boss.

A hard-surface build led by cross-sections (the player ships' treatment, PR #84, D50-D53):

The sprite decides the plan. A label map (LABELS below, one letter per sprite pixel, the dark
outline ring included) names the part each pixel belongs to; every part's plan outline is the
0.5 iso-line of its pixels (bilinear, so round where the sprite is round), smoothed and
simplified, and the solids are built from those outlines:

- hard plates (`slab`): the outline extruded between two planes, the top edge chamfered or rounded
  by inset rings, the bottom edge chamfered; panels and spars are smaller plates standing proud, so
  panel lines are real grooves;
- lofts along the rows (`row_loft`: the helm, the shoulder pods, the tail dome): sections whose
  width at each row is the outline's, so the plan is the sprite's;
- sweeps (`fit_sweep`: horns, claws, the wing-tip arcs): a section swept along a hand-drawn centre
  line whose centre and width at each station are fitted to the part's pixels.

Cross-sections (sprite px, z up from the sprite plane):
  helm        faceted arrowhead: flat belly z 0.8, steep flanks, cheeks, a 2 px flat ridge panel
              carrying the glowing slit; ridge 2.4 at the nose rising to 7.4 at row 15
  pods        machined superellipse (n 3.2) round a row-wise axis at z 2.7, radius = half the plan
              width (~2.7); collar, red ribbed ring, housing, red drum band, tapered blade end
  horns       rounded keel section, height 0.8 x width, rising from z 3.6 in the pod to 10.5 at
              the tip, which closes over several stations (no shading crease)
  claws       diamond blade, height 1.15 x width, z 3.4 -> 6.4
  wings       armour plate between two planes: top 3.4 at the root to 1.7 at the tip, belly -0.8 to
              0.0; raised forward panel, a lit spar across the middle, an aft panel split by
              grooves along the sprite's wing streaks
  torso       bay floor z 3.6, bronze side columns 6.3, grey hood sloping 6.8 -> 5.7 to the red
              chest light, chest stack 5.6 flanked by ribbed silver cylinders, bronze collar, round
              tail dome
  gun pods    chamfered block -0.9 .. 3.9 with a recessed grille and a tall bracket, nozzles aft

Colours are the sprite's own palette indices per part (the median of each part's pixels, its
darkest shading and brightest highlight left out), as satin metal (pal_<index> materials, so level
palettes, fades and the hit flash apply). The texture is baked here: occlusion and edge wear into a
grey colour multiplier and a roughness/metal map, no concept projection (maps.json says
"bake": "model"). Each piece is exported with its part of an outline shell (common.outline_shell,
D51). The underside is a closed, plain belly. Each piece has a single frame.

Options (after --): --no-bake, --no-export (build and measure only), --measure DIR (top ortho
silhouette and palette vs the sprite), --views DIR (lit angles), --preview PNG (tools/build-models.sh -p).
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)

NAME = "newsh4-flagship"
UPPER = ["newsh4-81", "newsh4-83", "newsh4-85"]
LOWER = ["newsh4-119", "newsh4-121", "newsh4-123"]
PX = 1 / 12
AXIS_X, MID_Y = 30.0, 26.0  # lib_b065's frame: column edge 30 is X = 0, row edge 26 is Y = 0
CX = 30.5  # the craft's design axis (column edge)
HORN_GROW, HORN_EXT = 1.06, 0.6  # horns: width margin over the fitted pixels, tip extension (px)
CLAW_GROW, CLAW_EXT = 1.05, 0.6

# One letter per sprite pixel (the outline ring included): the part it belongs to.
# H horn, P shoulder pod, C claw, S shoulder plate, A arm, B armour block, M helm, N neck,
# K core machinery, W wing, R wing-tip cap, X tip block, L tip arc, F wing-root frame,
# Z red shoulder armour, U strut, G gun pod, T torso, Q collar, D tail dome.
LABELS = """\


               HHHHH                      HHHHH
             HHHHHH                        HHHHH
            HHHHHH                          HHHHH
           HHHHHH                            HHHHH
          HHHHHH                              HHHHH
          HHHHH                                HHHHH
         HHHHH                                 HHHHH
         HHHHH              MMMM                HHHHH
         HHHHH     CCCCC   MMMMMM   CCCCCC      HHHHH
         HHHHH   CCCCCCC  MMMMMMMM   CCCCCCC    HHHHH
         HHHHH  CCCCCC   MMMMMMMMMM    CCCCCC   HHHHH
         PPPPP CCCCC     MMMMMMMMMMM     CCCCC  PPPPP
         PPPPPCCCC      MMMMMMMMMMMM       CCCC PPPPP
         PPPPPCCCC      MMMMMMMMMMMMM       CCCCPPPPP
        PPPPPSCCC       MMMMMMMMMMMMM       CCCCSPPPP
        PPPPPSCCC       MMMMMMMMMMMMM        CCCSPPPP
        PPPPPSSSS          NNNNNNN           CCCSPPPP
        PPPPPSSSS  BBB    NNNNNNNNN     BB  AASSSPPPP
         PPPPSSSAAABBBB  KKKKKKKKKK    BBBAAAASSSPPPP
        PPPPPSSSAAABBBB  KKKKKKKKKKK   BBBAAAASSSPPPPP
        PPPPPAAAAAABBBB KKKKKKKKKKKK   BBBAAAAAAAPPPPP
        PPPPPAAAAAABBBB KKKKKKKKKKKK  BBBBAAAAAAAPPPPP
        PPPPPAAAAAAAABBBKKKKKKKKKKKKBBBBBBAAAAAAAPPPPP
        PPPPPAAAAAAAABBBKKKKKKKKKKKKBBBBBBAAAAAAAPPPP
         PPPPWWWWFFFFFTTTTTKKKKKKKTTTTWWWFFFWWWWWPPPP
         PPPPWWWWFFFFFTTTTTKKKKKKKTTTTWWWFFFWWWWWPPPP
            WWWWWFFFFFTTTTTTTTTTTTTTTZZZZFFFWWWWWW
           WWWWWWFFFZZZZZZZTTTTTTTTTTZZZZFFFWWWWWWW
          WWWWWWWFFFZZZZZZZTTTTTTTTTTZZZZFFFWWWWWWWW
         WWWWWWWWFFFFFTTTTTTTTTTTTTTTTWWWFFFWWWWWWWWW
     RRXXWWWWWWWWWWWWWTTTTTTTTTTTTTTTTWWWWWWWWWWWWWWWXXRR
    RRRXXWWWWWWWWWWWWWTTTTTTTTTTTTTTTTWWWWWWWWWWWWWWWXXRRR
   RRRRXXWWWWWWWWWWUUUUTTTTTTTTTTTTTTTUUUUWWWWWWWWWWWXXRRR
   RRRRXXWWWWWWWW  UUUUTTTTTTTTTTTTTTTUUUU   WWWWWWWWXXRRR
   RRRRXXWWWWWW    UUUUTTTTTTTTTTTTTTTUUUUW    WWWWWWXXRRR
   RRRRWWWWWW     WUUUUTTTTTTTTTTTTTTTUUUUWW     WWWWWWRRR
   LLLLLLLL      GGGGGGGTTTTTTTTTTTTTTGGGGGGG      LLLLLLL
   LLLLLL       GGGGGGGGTTTTTTTTTTTTTTGGGGGGGG       LLLLLL
   LLLL      GGGGGGGGGGGTTTTTTTTTTTTTTGGGGGGGGGG       LLLL
   LLL      GGGGGGGGGGGQQQQQQQQQQQQQQQGGGGGGGGGGG       LL
   LLL     GGGGGGGGGGGGQQQQQQQQQQQQQQQGGGGGGGGGGGG     LLL
    LLL    GGGGGGGGGGGGQQQQQQQQQQQQQQ GGGGGGGGGGGG     LLL
     LLL   GGGGGGGGGGGGQQQQQQQQQQQQQ  GGGGGGGGGGGGG   LLL
      LLLLLGGGGGGGGGGGG  DDDDDDDDDDQ   GGGGGGGGGGGGLLLLL
       LLLLGGGGGGGGGG    DDDDDDDDDD      GGGGGGGGGGLLLL
        LLLGGGGGGGG       DDDDDDDD         GGGGGGGGLLL
           GGGGGG           DDDDD            GGGGG
            GGG                                GG


"""
LAB = np.array([list(line.ljust(72)[:72]) for line in LABELS.split("\n")[:52]])
assert LAB.shape == (52, 72), LAB.shape

# Palette index per material, from the sprite (median of each part's pixels, the darkest shading
# and the brightest highlights left out; both sides pooled where the part is mirrored).
MATS = [
    # name, index, metallic, roughness, emission
    ("horn", 165, 0.18, 0.42, 0),
    ("pod", 6, 0.2, 0.4, 0),
    ("red", 70, 0.12, 0.45, 0),
    ("claw", 5, 0.2, 0.38, 0),
    ("plate", 24, 0.18, 0.42, 0),     # shoulder plates
    ("arm", 6, 0.2, 0.42, 0),
    ("block", 23, 0.18, 0.44, 0),
    ("helm", 5, 0.2, 0.36, 0),
    ("cap", 21, 0.18, 0.4, 0),
    ("slit", 72, 0.0, 0.5, 2.4),
    ("core", 3, 0.15, 0.55, 0),
    ("pipe", 71, 0.15, 0.35, 0),
    ("wing", 21, 0.18, 0.46, 0),
    ("trim", 25, 0.2, 0.36, 0),       # lit spars and lips
    ("tipred", 70, 0.12, 0.45, 0),
    ("tipblk", 4, 0.2, 0.45, 0),
    ("arc", 22, 0.18, 0.42, 0),
    ("frame", 3, 0.18, 0.5, 0),
    ("armour", 69, 0.12, 0.45, 0),    # red shoulder armour
    ("strut", 4, 0.2, 0.45, 0),
    ("gun", 4, 0.2, 0.42, 0),
    ("grille", 3, 0.1, 0.65, 0),
    ("bay", 162, 0.1, 0.6, 0),        # dark bronze bay floor and recesses
    ("column", 22, 0.18, 0.44, 0),
    ("hood", 5, 0.2, 0.38, 0),
    ("rib", 9, 0.22, 0.34, 0),
    ("rail", 8, 0.22, 0.34, 0),
    ("light", 74, 0.0, 0.4, 3.0),
    ("hot", 77, 0.0, 0.4, 5.0),
    ("collar", 24, 0.18, 0.42, 0),
    ("pale", 27, 0.2, 0.38, 0),
    ("dome", 6, 0.22, 0.34, 0),
    ("deep", 2, 0.0, 0.8, 0),         # nozzle throats, grille slots
    ("glow", 72, 0.0, 0.5, 3.0),      # nozzle glow
    ("bronze_dk", 20, 0.15, 0.5, 0),  # wing-root and tip shading plates
]
M = {name: i for i, (name, *_rest) in enumerate(MATS)}


# ---------------------------------------------------------------------------------------------
# Plan outlines from the label map
# ---------------------------------------------------------------------------------------------

def part_mask(letters, cols=None, rows=None):
    m = np.isin(LAB, list(letters))
    if cols is not None:
        cc = np.arange(72)[None, :]
        m &= (cc >= cols[0]) & (cc < cols[1])
    if rows is not None:
        rr = np.arange(52)[:, None]
        m &= (rr >= rows[0]) & (rr < rows[1])
    return m


def grow(mask, into, n=1):
    """mask grown n px (4-neighbour) into the pixels of the parts `into` (letters)."""
    allow = np.isin(LAB, list(into))
    m = mask.copy()
    for _ in range(n):
        g = m.copy()
        g[1:, :] |= m[:-1, :]
        g[:-1, :] |= m[1:, :]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = m | (g & allow)
    return m


def contours(mask, step=0.25, smooth=0.6, tol=0.06):
    """Closed outlines [(x, y)] (column/row edges) of the 0.5 iso-line of the bilinear
    interpolation of the mask's pixel centres: round where the pixels are round."""
    H, W = mask.shape
    rr, cc = np.nonzero(mask)
    if len(rr) == 0:
        return []
    r0, r1 = rr.min() - 2, rr.max() + 3
    c0, c1 = cc.min() - 2, cc.max() + 3
    pad = np.zeros((H + 6, W + 6))
    pad[3:3 + H, 3:3 + W] = mask
    xs = np.arange(c0, c1 + 1e-9, step) + step / 2
    ys = np.arange(r0, r1 + 1e-9, step) + step / 2
    fx = xs - 0.5 + 3
    fy = ys - 0.5 + 3
    ix = np.floor(fx).astype(int)
    iy = np.floor(fy).astype(int)
    tx = fx - ix
    ty = fy - iy
    a = pad[np.ix_(iy, ix)]
    b = pad[np.ix_(iy, ix + 1)]
    c = pad[np.ix_(iy + 1, ix)]
    d = pad[np.ix_(iy + 1, ix + 1)]
    F = (1 - ty)[:, None] * ((1 - tx)[None, :] * a + tx[None, :] * b) + ty[:, None] * ((1 - tx)[None, :] * c + tx[None, :] * d)
    lev = 0.5
    ins = F > lev
    ny, nx = F.shape

    def pt(key):
        kind, i, j = key
        if kind == "h":
            v0, v1 = F[i, j], F[i, j + 1]
            t = (lev - v0) / (v1 - v0)
            return (xs[j] + t * (xs[j + 1] - xs[j]), ys[i])
        v0, v1 = F[i, j], F[i + 1, j]
        t = (lev - v0) / (v1 - v0)
        return (xs[j], ys[i] + t * (ys[i + 1] - ys[i]))

    segs = []
    for i in range(ny - 1):
        for j in range(nx - 1):
            k = (ins[i, j] * 1) | (ins[i, j + 1] * 2) | (ins[i + 1, j + 1] * 4) | (ins[i + 1, j] * 8)
            if k in (0, 15):
                continue
            T, R, B, L = ("h", i, j), ("v", i, j + 1), ("h", i + 1, j), ("v", i, j)
            centre = (F[i, j] + F[i, j + 1] + F[i + 1, j] + F[i + 1, j + 1]) / 4 > lev
            table = {1: [(L, T)], 2: [(T, R)], 3: [(L, R)], 4: [(R, B)], 6: [(T, B)], 7: [(L, B)],
                     8: [(B, L)], 9: [(T, B)], 11: [(R, B)], 12: [(L, R)], 13: [(T, R)], 14: [(L, T)],
                     5: [(T, R), (B, L)] if centre else [(L, T), (R, B)],
                     10: [(L, T), (R, B)] if centre else [(T, R), (B, L)]}
            segs += table[k]
    adj = {}
    for s in segs:
        for e in s:
            adj.setdefault(e, []).append(s)
    used = set()
    loops = []
    for s in segs:
        if id(s) in used:
            continue
        loop = [s[0]]
        cur, nxt = s, s[1]
        used.add(id(s))
        while True:
            loop.append(nxt)
            cand = [q for q in adj[nxt] if id(q) not in used]
            if not cand:
                break
            q = cand[0]
            used.add(id(q))
            nxt = q[1] if q[0] == nxt else q[0]
            if nxt == loop[0]:
                break
        pts = [pt(k) for k in loop[:-1] if True]
        if len(pts) >= 6:
            loops.append(pts)
    out = []
    for pts in loops:
        pts = taubin(pts, smooth)
        pts = simplify(pts, tol)
        if abs(area(pts)) > 0.3:
            out.append(pts)
    return out


def taubin(pts, sigma, ds=0.1):
    """Resample the loop every ds px and low-pass it with a circular Gaussian of `sigma` px
    (the sprite's 1-2 px staircases become straight runs and smooth curves)."""
    p = np.array(pts, dtype=float)
    q = np.vstack([p, p[:1]])
    seg = np.hypot(*np.diff(q, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    n = max(16, int(L / ds))
    t = np.linspace(0, L, n, endpoint=False)
    r = np.stack([np.interp(t, s, q[:, 0]), np.interp(t, s, q[:, 1])], 1)
    if sigma <= 0:
        return [tuple(v) for v in r]
    k = int(3 * sigma / ds) + 1
    off = np.arange(-k, k + 1)
    w = np.exp(-0.5 * (off * ds / sigma) ** 2)
    w /= w.sum()
    out = np.zeros_like(r)
    for o, wi in zip(off, w):
        out += wi * np.roll(r, -o, 0)
    return [tuple(v) for v in out]


def simplify(pts, tol):
    """Douglas-Peucker on a closed loop."""
    def dp(seq):
        if len(seq) < 3:
            return seq
        a, b = np.array(seq[0]), np.array(seq[-1])
        ab = b - a
        L = np.hypot(*ab) or 1e-9
        best, bi = -1, 0
        for i in range(1, len(seq) - 1):
            p = np.array(seq[i])
            d = abs(ab[0] * (p - a)[1] - ab[1] * (p - a)[0]) / L
            if d > best:
                best, bi = d, i
        if best > tol:
            return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])
        return [seq[0], seq[-1]]
    n = len(pts)
    far = max(range(n), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = dp(pts[:far + 1])
    b = dp(pts[far:] + [pts[0]])
    return a[:-1] + b[:-1]


def area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def inset(pts, d):
    """The loop offset inward by d (miter, clamped)."""
    n = len(pts)
    s = 1 if area(pts) > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        l0 = math.hypot(*e0) or 1e-9
        l1 = math.hypot(*e1) or 1e-9
        # inward normal for a CCW (area > 0 in x right, y down: clockwise on screen) loop
        n0 = (-e0[1] / l0 * s, e0[0] / l0 * s)
        n1 = (-e1[1] / l1 * s, e1[0] / l1 * s)
        mx, my = n0[0] + n1[0], n0[1] + n1[1]
        ml = math.hypot(mx, my) or 1e-9
        mx, my = mx / ml, my / ml
        cos_h = max(0.5, mx * n1[0] + my * n1[1])
        out.append((p1[0] + mx * d / cos_h, p1[1] + my * d / cos_h))
    return out


def clip(pts, a, b, c):
    """Sutherland-Hodgman: the part of the loop where a*x + b*y + c >= 0."""
    out = []
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def half(p, q):
    """Half-plane left of the directed line p -> q (x right, y down), as (a, b, c)."""
    a, b = q[1] - p[1], -(q[0] - p[0])
    return (-a, -b, a * p[0] + b * p[1])


def grooved(pts, lines, gap=0.3):
    """The loop cut into strips by grooves `gap` px wide along the half-plane lines (a, b, c)
    (each line's left side is its 'positive' side; strips are returned in order)."""
    out = []
    rest = pts
    for a, b, c in lines:
        n = math.hypot(a, b) or 1e-9
        neg = clip(rest, -a, -b, -c - gap / 2 * n)
        pos = clip(rest, a, b, c - gap / 2 * n)
        if len(neg) > 2 and abs(area(neg)) > 0.3:
            out.append(neg)
        rest = pos
        if len(rest) < 3:
            break
    if len(rest) > 2 and abs(area(rest)) > 0.3:
        out.append(rest)
    return out


def x_extent(pts, y):
    """Leftmost and rightmost crossings of the loop with the row line y."""
    xs = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
            xs.append(x0 + (y - y0) / (y1 - y0) * (x1 - x0))
    return (min(xs), max(xs)) if xs else None


def pchip(xs, ys):
    """Monotone cubic interpolation (no overshoot)."""
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


# ---------------------------------------------------------------------------------------------
# Mesh building (sprite px; converted to Blender at the end)
# ---------------------------------------------------------------------------------------------

class Part:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, x, y, z):
        return self.bm.verts.new(((x - AXIS_X) * PX, (MID_Y - y) * PX, z * PX))

    def f(self, verts, mat, smooth=None):
        if len({id(v) for v in verts}) < 3:
            return None
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        return face


def plane(z0, gx=0.0, gy=0.0, x0=0.0, y0=0.0):
    return lambda x, y: z0 + gx * (x - x0) + gy * (y - y0)


def slab(P, pts, zb, zt, mat, ch=0.45, chb=0.3, round_top=0, side_mat=None):
    """A hard plate on the plan loop `pts` from zb to zt (numbers or functions of (x, y), planes
    for crisp flat faces). Its top edge is chamfered by `ch` (45 degrees) or, with round_top=k,
    rounded by k rings over a quarter circle of radius ch; its bottom edge chamfered by chb."""
    zb_f = zb if callable(zb) else (lambda x, y, z=zb: z)
    zt_f = zt if callable(zt) else (lambda x, y, z=zt: z)
    rings = []  # (loop, z offset from base or top, which)
    if chb > 0:
        rings.append((inset(pts, chb), "b", 0.0))
        rings.append((pts, "b", chb))
    else:
        rings.append((pts, "b", 0.0))
    if round_top:
        k = round_top
        for i in range(k + 1):
            t = math.pi / 2 * i / k
            ins = ch * (1 - math.cos(t))
            dz = -ch * (1 - math.sin(t))
            rings.append((inset(pts, ins) if ins > 1e-4 else pts, "t", dz))
    elif ch > 0:
        rings.append((pts, "t", -ch))
        rings.append((inset(pts, ch), "t", 0.0))
    else:
        rings.append((pts, "t", 0.0))
    vrings = []
    for loop, which, dz in rings:
        if which == "b":
            vrings.append([P.v(x, y, zb_f(x, y) + dz) for x, y in loop])
        else:
            vrings.append([P.v(x, y, zt_f(x, y) + dz) for x, y in loop])
    n = len(pts)
    sm = side_mat if side_mat is not None else mat
    for k in range(len(vrings) - 1):
        r0, r1 = vrings[k], vrings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            P.f((r0[i], r0[j], r1[j], r1[i]), sm if 0 < k < len(vrings) - 2 else mat)
    P.f(list(reversed(vrings[0])), mat)
    P.f(vrings[-1], mat)


def rect(x0, y0, x1, y1, cut=0.0):
    if cut <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut), (x1 - cut, y1), (x0 + cut, y1),
            (x0, y1 - cut), (x0, y0 + cut)]


def mirror_pts(pts, axis=CX):
    return [(2 * axis - x, y) for x, y in reversed(pts)]


def loft(P, rings, mat_of, cap0=True, cap1=True, mat_cap0=None, mat_cap1=None):
    """Rings of (x, y, z) points (same count, or a single point for a tip) joined in order;
    mat_of(k) is the material between ring k and k + 1."""
    vr = [[P.v(*p) for p in ring] for ring in rings]
    for k in range(len(vr) - 1):
        a, b = vr[k], vr[k + 1]
        mat = mat_of(k)
        if len(a) == 1 and len(b) == 1:
            continue
        n = max(len(a), len(b))
        for i in range(n):
            j = (i + 1) % n
            if len(a) == 1:
                P.f((a[0], b[i], b[j]), mat)
            elif len(b) == 1:
                P.f((a[i], a[j], b[0]), mat)
            else:
                P.f((a[i], a[j], b[j], b[i]), mat)
    if cap0 and len(vr[0]) > 2:
        P.f(list(reversed(vr[0])), mat_cap0 if mat_cap0 is not None else mat_of(0))
    if cap1 and len(vr[-1]) > 2:
        P.f(vr[-1], mat_cap1 if mat_cap1 is not None else mat_of(len(vr) - 2))


def superellipse(n_pts, ex=3.0, start=0.0):
    out = []
    for k in range(n_pts):
        t = 2 * math.pi * k / n_pts + start
        c, s = math.cos(t), math.sin(t)
        out.append((math.copysign(abs(c) ** (2 / ex), c), math.copysign(abs(s) ** (2 / ex), s)))
    return out


def in_mask(mask, x, y):
    c, r = int(math.floor(x)), int(math.floor(y))
    return 0 <= r < mask.shape[0] and 0 <= c < mask.shape[1] and mask[r, c]


def fit_path(mask, path, step=0.03, reach=4.0, smooth_n=2):
    """Centre and half width of the mask across the path at each of its points [(x, y)],
    measured along the normal, smoothed along the path."""
    n = len(path)
    res = []
    for i in range(n):
        p = np.array(path[i], dtype=float)
        a = np.array(path[max(i - 1, 0)], dtype=float)
        b = np.array(path[min(i + 1, n - 1)], dtype=float)
        t = b - a
        t /= np.linalg.norm(t)
        nrm = np.array([-t[1], t[0]])
        ext = []
        for sgn in (1, -1):
            d = 0.0
            while d < reach and in_mask(mask, *(p + sgn * nrm * (d + step))):
                d += step
            ext.append(d)
        cen = p + nrm * (ext[0] - ext[1]) / 2
        res.append([cen[0], cen[1], (ext[0] + ext[1]) / 2])
    res = np.array(res)
    for _ in range(smooth_n):
        res[1:-1] = 0.25 * res[:-2] + 0.5 * res[1:-1] + 0.25 * res[2:]
    return res


def taper_tip(st, n_tip=5, ext=0.0, tip_w=0.08):
    """Stations [(x, y, z, w, h)] whose last one is the tip: the last segment (extended by `ext`
    px along the path) is replaced by `n_tip` stations whose width closes smoothly (a quarter
    narrowing faster towards the point) to a small ring, so the shading has no crease at the tip."""
    *body, (x1, y1, z1, _w1, _h1) = st
    x0, y0, z0, w0, h0 = body[-1]
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1e-9
    x1, y1 = x1 + dx / L * ext, y1 + dy / L * ext
    out = list(body)
    for k in range(1, n_tip + 1):
        t = k / n_tip
        f = max(1 - t ** 1.6, tip_w)
        out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t, w0 * f, h0 * f))
    return out


def sweep(P, stations, section, mat_of, cap0=True, cap1=True):
    """A section [(u, v)] (u across, v up, both in -1..1) swept through stations
    [(x, y, z, half_width, half_height)], each ring perpendicular to the path in plan. A station of
    zero size closes to a point."""
    rings = []
    n = len(stations)
    for i, (x, y, z, w, h) in enumerate(stations):
        if w <= 1e-4:
            rings.append([(x, y, z)])
            continue
        a = stations[max(i - 1, 0)]
        b = stations[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        L = math.hypot(tx, ty) or 1e-9
        nx, ny = -ty / L, tx / L
        rings.append([(x + nx * u * w, y + ny * u * w, z + v * h) for u, v in section])
    loft(P, rings, mat_of, cap0, cap1)


def row_loft(P, loop, ys, section_at, mat_of, cap0=True, cap1=True):
    """A loft down the rows: at each y the section_at(y, xl, xr) ring [(x, z)] fitted to the plan
    loop's extent [xl, xr] at that row."""
    rings = []
    for y in ys:
        ex = x_extent(loop, y)
        if ex is None:
            continue
        rings.append([(x, y, z) for x, z in section_at(y, ex[0], ex[1])])
    loft(P, rings, mat_of, cap0, cap1)


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def loops_of(letters, side=None, grow_into="", n=1, rows=None, smooth=None):
    m = part_mask(letters, rows=rows)
    if side == "L":
        m &= np.arange(72)[None, :] < 31
    elif side == "R":
        m &= np.arange(72)[None, :] >= 31
    if grow_into:
        m = grow(m, grow_into, n)
    if smooth is None:
        smooth = 0.9 if letters in ("W", "G", "Q", "T") else 0.55
    return contours(m, smooth=smooth)


# ---------------------------------------------------------------------------------------------
# The craft
# ---------------------------------------------------------------------------------------------

def side_x(x, s):
    """Column x of the left-hand design mirrored to side s (+1 left as drawn, -1 right)."""
    return x if s > 0 else 2 * CX - x


def build_upper(P):
    # ---- shoulder pods: machined cylinders along the rows ----
    sec = superellipse(20, 3.2, start=math.pi / 2)  # starts at the top

    for side in ("L", "R"):
        loop = loops_of("P", side, grow_into="SAH", n=1)[0]
        zc = 2.7

        def pod_sec(y, xl, xr, dr=0.0):
            cx, r = (xl + xr) / 2, (xr - xl) / 2 + dr
            rz = min(r, 2.9)
            return [(cx + u * r, zc + v * rz) for u, v in sec]

        # collar (rows 12.9-16.4) with two machined grooves, ribbed red ring, housing, red drum,
        # housing, tapered blade
        y0, y1 = 12.75, 27.95
        ys = [y0, 12.95, 13.3, 13.9, 14.0, 14.5, 15.2, 15.3, 16.0, 16.4, 16.5, 16.6, 18.6, 18.7, 18.8,
              21.4, 21.5, 21.6, 24.4, 24.5, 24.6, 25.2, 25.9, 26.6, 27.2, 27.6, y1]
        dr = {y0: -0.9, 12.95: -0.35, 13.3: -0.2, 13.9: -0.2, 14.0: -0.45, 14.5: -0.45, 15.2: -0.2,
              15.3: -0.2, 16.0: -0.2, 16.4: -0.2, 16.5: -0.5, 16.6: 0.15, 18.6: 0.15, 18.7: -0.5,
              18.8: -0.05, 21.4: -0.05, 21.5: -0.5, 21.6: 0.18, 24.4: 0.18, 24.5: -0.5, 24.6: -0.1,
              25.2: -0.1, 25.9: -0.15, 26.6: -0.15, 27.2: -0.25, 27.6: -0.4, y1: -0.85}
        rings = []
        for y in ys:
            ex = x_extent(loop, min(max(y, 13.0), 27.3))
            rings.append([(x, y, z) for x, z in pod_sec(y, ex[0], ex[1], dr[y])])
        red_spans = {ys.index(16.6), ys.index(21.6)}
        tip_from = ys.index(26.6)

        def pod_mat(k):
            if k in red_spans:
                return M["red"]
            if k >= tip_from:
                return M["block"]
            return M["pod"]
        loft(P, rings, pod_mat)
        # Rib grooves on the red ring: thin dark bands
        for yb in (17.3, 17.95):
            ex = x_extent(loop, yb)
            rr = [[(x, y, z) for x, z in pod_sec(yb, ex[0], ex[1], 0.2)] for y in (yb - 0.12, yb + 0.12)]
            rr = [[(x, yy, z) for (x, _y, z) in ring] for ring, yy in zip(rr, (yb - 0.12, yb + 0.12))]
            loft(P, rr, lambda k: M["deep"])

    # ---- horns: keel-section sweeps from inside the pod's collar up to the tip ----
    horn_sec = [(1.0, 0.0), (0.82, 0.55), (0.4, 0.92), (0.0, 1.08), (-0.4, 0.92), (-0.82, 0.55), (-1.0, 0.0),
                (-0.8, -0.5), (-0.35, -0.82), (0.35, -0.82), (0.8, -0.5)]
    hpath_L = [(11.0, 14.6), (11.1, 13.2), (11.2, 12.0), (11.3, 10.8), (11.5, 9.6), (11.9, 8.4), (12.5, 7.2),
               (13.3, 6.0), (14.3, 4.9), (15.4, 3.9), (16.7, 3.05), (18.2, 2.55), (19.6, 2.35)]
    hpath_R = [(50.6, 14.6), (50.4, 13.2), (50.2, 12.0), (50.0, 10.8), (49.7, 9.6), (49.3, 8.4), (48.8, 7.4),
               (48.2, 6.4), (47.4, 5.4), (46.4, 4.4), (45.3, 3.5), (44.0, 2.75), (42.6, 2.4)]
    for side, path in (("L", hpath_L), ("R", hpath_R)):
        mask = part_mask("H", cols=(0, 31) if side == "L" else (31, 72))
        fit = fit_path(mask | part_mask("P", rows=(13, 16)), path, smooth_n=2)
        n = len(fit)
        st = []
        for i, (x, y, w) in enumerate(fit):
            t = i / (n - 1)
            z = 3.6 + 6.9 * (t ** 1.35)
            w = min(w * HORN_GROW, 2.6)
            st.append((x, y, z, w, 0.8 * w))
        sweep(P, taper_tip(st, n_tip=6, ext=HORN_EXT), horn_sec, lambda k: M["horn"])

    # ---- claws: diamond blades curling in towards the helm ----
    claw_sec = [(1.0, 0.0), (0.45, 0.72), (0.0, 1.0), (-0.45, 0.72), (-1.0, 0.0), (-0.5, -0.65), (0.0, -0.85), (0.5, -0.65)]
    cpath_L = [(15.6, 19.0), (15.5, 17.6), (15.6, 16.4), (16.1, 15.0), (16.9, 13.8), (18.0, 12.6), (19.4, 11.6),
               (21.0, 11.0), (22.6, 10.7), (23.9, 10.6)]
    cpath_R = [(47.3, 18.9), (46.8, 17.6), (46.2, 16.3), (45.4, 15.0), (44.4, 13.8), (43.2, 12.7), (41.8, 11.7),
               (40.2, 11.0), (38.6, 10.65), (36.5, 10.6)]
    for side, path in (("L", cpath_L), ("R", cpath_R)):
        mask = part_mask("C", cols=(0, 31) if side == "L" else (31, 72))
        fit = fit_path(mask | part_mask("S"), path, smooth_n=2)
        n = len(fit)
        st = []
        for i, (x, y, w) in enumerate(fit):
            t = i / (n - 1)
            z = 3.4 + 3.0 * t ** 1.2
            w = min(w * CLAW_GROW, 1.75)
            st.append((x, y, z, w, 1.15 * w))
        sweep(P, taper_tip(st, n_tip=5, ext=CLAW_EXT), claw_sec, lambda k: M["claw"])

    # ---- shoulder plates, arms, armour blocks ----
    for side in ("L", "R"):
        s = 1 if side == "L" else -1
        # Bronze shoulder plate, its top sloping down outboard.
        for loop in loops_of("S", side, grow_into="PA", n=1):
            slab(P, loop, 0.4, plane(5.6, gx=0.18 * s, x0=side_x(14.5, s)), M["plate"], ch=0.5)
        # Arm: a grey beam from the pod to the block, chamfered, with an actuator on top.
        for loop in loops_of("A", side, grow_into="PBS", n=1):
            slab(P, loop, 0.2, 3.9, M["arm"], ch=0.55)
        xa, xb = side_x(12.6, s), side_x(19.6, s)
        sweep(P, [(xa, 22.5, 4.15, 0.62, 0.55), (xb, 22.5, 4.15, 0.62, 0.55)],
              superellipse(10, 2.0), lambda k: M["rail"])
        sweep(P, [(side_x(13.4, s), 23.9, 3.9, 0.42, 0.4), (side_x(18.6, s), 23.9, 3.9, 0.42, 0.4)],
              superellipse(8, 2.0), lambda k: M["core"])
        # Armour block over the wing root: tall chamfered bronze block, a slot in its face.
        for loop in loops_of("B", side, grow_into="AK", n=1):
            slab(P, loop, 0.2, plane(6.2, gy=-0.05, y0=22), M["block"], ch=0.7)
        slab(P, rect(side_x(19.9, s) - (0 if s > 0 else 1.6), 23.2, side_x(19.9, s) + (1.6 if s > 0 else 0), 23.8),
             5.6, plane(6.25, gy=-0.05, y0=22), M["deep"], ch=0.0, chb=0.0)

    # ---- helm: a faceted arrowhead down the middle ----
    loop = loops_of("M")[0]
    ztop = pchip([9.0, 10.0, 11.5, 13.0, 14.5, 15.6, 16.6, 17.4, 17.9], [2.4, 4.1, 5.5, 6.5, 7.2, 7.45, 7.3, 6.6, 5.6])
    zbelly = 0.8
    # (across as a fraction of the half width, up as a fraction of the ridge height above the belly)
    helm_sec = [(-1.0, 0.0), (-1.0, 0.18), (-0.9, 0.42), (-0.5, 0.86), (-0.17, 1.0), (0.17, 1.0), (0.5, 0.86),
                (0.9, 0.42), (1.0, 0.18), (1.0, 0.0)]

    def helm_at(y, xl, xr):
        cx, w = (xl + xr) / 2, (xr - xl) / 2
        h = ztop(y) - zbelly
        return [(cx + u * w, zbelly + v * h) for u, v in helm_sec]
    ys = [9.06, 9.3, 9.7] + frange(10.2, 17.85, 0.55)
    rings = []
    for y in ys:
        ex = x_extent(loop, y)
        rings.append([(x, y, z) for x, z in helm_at(y, *ex)])
    loft(P, rings, lambda k: M["helm"])
    # Bronze nose cap: a plate standing proud over the helm's front, following its facets.
    cap_ys = frange(9.25, 14.5, 0.45)
    cap = []
    for y in cap_ys:
        ex = x_extent(loop, y)
        cx, w = (ex[0] + ex[1]) / 2, (ex[1] - ex[0]) / 2
        h = ztop(y) - zbelly
        pts = [(cx + u * w * 1.02, zbelly + v * h + 0.22) for u, v in helm_sec[3:7]]
        cap.append(pts)
    rings = []
    for y, pts in zip(cap_ys, cap):
        rr = [(x, y, z) for x, z in pts]
        under = [(x, y, z - 0.4) for x, z in reversed(pts)]
        rings.append(rr + under)
    loft(P, rings, lambda k: M["cap"])
    # Glowing slit in a dark slot along the ridge (rows 11-16).
    slit_ys = frange(11.0, 16.4, 0.6)
    st = []
    for i, y in enumerate(slit_ys):
        w = 0.0 if i in (0, len(slit_ys) - 1) else 0.8
        st.append((CX - 0.1, y, ztop(y) + (0.24 if y < 14.5 else 0.02), w, 0.12))
    sweep(P, st, [(1, 0), (0.6, 1), (-0.6, 1), (-1, 0), (-0.6, -1), (0.6, -1)], lambda k: M["slit"])
    # Neck and the dark machinery block behind the helm.
    for lp in loops_of("N", grow_into="MK", n=1):
        slab(P, lp, 0.4, 5.2, M["hood"], ch=0.5)
    for lp in loops_of("K", grow_into="BT", n=1, rows=(0, 30)):
        slab(P, lp, 0.0, 4.4, M["core"], ch=0.45)
    # Grey cross plate at rows 23.6-26.4 (the hood's top) and the red pipes over the core.
    for s in (1, -1):
        x0 = side_x(25.6, s)
        x1 = side_x(28.1, s)
        rad = abs(x1 - x0) / 2
        cxp = (x0 + x1) / 2
        path = [(x0, 24.4, 4.3)]
        for i in range(9):
            a = math.pi * i / 8
            path.append((cxp - math.cos(a) * rad * (1 if s > 0 else -1), 21.9 + rad - math.sin(a) * rad, 5.0))
        path.append((x1, 24.4, 4.3))
        st = [(x, y, z, 0.48, 0.48) for x, y, z in path]
        sweep(P, st, superellipse(8, 2.0), lambda k: M["pipe"])
        # short outer pipe
        st = [(side_x(24.9, s), 20.8, 4.2, 0.4, 0.4), (side_x(24.9, s), 22.2, 4.7, 0.4, 0.4),
              (side_x(25.3, s), 23.0, 4.7, 0.4, 0.4), (side_x(26.0, s), 23.3, 4.5, 0.4, 0.4)]
        sweep(P, st, superellipse(8, 2.0), lambda k: M["pipe"])
    # Spine between the pipes.
    slab(P, rect(29.5, 19.8, 31.5, 24.2, 0.3), 3.8, 5.3, M["hood"], ch=0.35)


def build_lower(P):
    # ---- wings: panelled armour plates ----
    for side in ("L", "R"):
        s = 1 if side == "L" else -1
        root, tip = side_x(21.0, s), side_x(4.0, s)
        top = plane(1.7, gx=(3.4 - 1.7) / (root - tip), x0=tip)
        bot = plane(0.0, gx=(-0.8 - 0.0) / (root - tip), x0=tip)
        loops = loops_of("W", side, grow_into="TFZUGRXL", n=1)
        for lp in loops:
            slab(P, lp, bot, top, M["wing"], ch=0.5, chb=0.35)
        wl = max(loops, key=lambda q: abs(area(q)))
        base = inset(wl, 0.9)
        up = lambda d: (lambda x, y: top(x, y) + d)  # noqa: E731
        sub = lambda d: (lambda x, y: top(x, y) - d)  # noqa: E731

        def keep(a, b, c):
            """The half-plane a*x + b*y + c >= 0 of the left-hand design, on this side."""
            return (a, b, c) if s > 0 else (-a, b, c + 2 * CX * a)

        def line(p, q):
            """The line through p and q (left-hand design) as a half-plane for grooved()."""
            a, b = q[1] - p[1], -(q[0] - p[0])
            return keep(a, b, -(a * p[0] + b * p[1]))

        def cut(loop, *planes):
            for pl in planes:
                loop = clip(loop, *keep(*pl))
                if len(loop) < 3:
                    return []
            return loop if abs(area(loop)) > 0.3 else []
        # Forward panel: outboard of the wing-root frame, ahead of the spar; two grooves along the
        # sprite's wing streaks (swept back outboard like the leading edge) cut it into three plates.
        fwd = cut(base, (0, -1, 31.6), (-1, 0, 19.2))
        for strip in grooved(fwd, [line((16.6, 27.0), (13.4, 32.0)), line((12.9, 27.6), (9.8, 32.0))]):
            slab(P, strip, sub(0.3), up(0.4), M["wing"], ch=0.3, chb=0.0)
        # The spar: a lit bar across the wing's middle, rows 32.1-33.7.
        spar = cut(base, (0, 1, -32.1), (0, -1, 33.7), (1, 0, -7.8))
        if spar:
            slab(P, spar, sub(0.3), up(0.55), M["trim"], ch=0.3, chb=0.0)
        # Aft panel: from the spar back toward the tip, outboard of the strut; one groove.
        aft = cut(base, (0, 1, -34.2), (-1, 0, 16.8), (1, 0, -7.6))
        for strip in grooved(aft, [line((13.8, 33.8), (11.0, 38.0))]):
            slab(P, strip, sub(0.3), up(0.32), M["wing"], ch=0.25, chb=0.0)
        # Wing-root frame (dark grey) and the red shoulder armour.
        for lp in loops_of("F", side, grow_into="TW", n=1):
            slab(P, lp, -0.4, 3.9, M["frame"], ch=0.4)
        for lp in loops_of("Z", side, grow_into="TF", n=1):
            slab(P, lp, 2.0, 5.0, M["armour"], ch=0.45)
        # Wing-tip: a rounded red cap, the grey block inboard of it.
        for lp in loops_of("R", side, grow_into="XWL", n=1):
            slab(P, lp, -0.4, 3.7, M["tipred"], ch=1.1, round_top=3, chb=0.4)
        for lp in loops_of("X", side, grow_into="W", n=1):
            slab(P, lp, 0.0, 3.1, M["tipblk"], ch=0.45)
        # The arc: a hard bar from under the tip cap, down and in to the gun pod.
        mask = part_mask("L", cols=(0, 31) if side == "L" else (31, 72)) | part_mask("R", rows=(37, 38))
        # Its root under the cap: a chamfered wedge filling the arc's wide top rows (38-40).
        for lp in loops_of("L", side, rows=(38, 41)):
            slab(P, lp, 0.25, 2.35, M["arc"], ch=0.5, chb=0.3)
        apath = [(4.6, 37.6), (4.5, 39.2), (4.6, 40.8), (4.9, 42.2), (5.6, 43.6), (6.6, 44.8), (7.9, 45.8),
                 (9.4, 46.4), (10.9, 46.6), (12.2, 46.5)]
        if s < 0:
            apath = [(56.4, 37.6), (56.5, 39.2), (56.4, 40.6), (56.1, 42.0), (55.5, 43.4), (54.6, 44.6),
                     (53.4, 45.8), (52.2, 46.6), (50.8, 47.0), (49.4, 46.9)]
        fit = fit_path(mask, apath, smooth_n=1)
        st = [(x, y, 1.3, min(w, 1.6), 1.05) for x, y, w in fit]
        sweep(P, st, [(1, 0.55), (0.65, 1), (-0.65, 1), (-1, 0.55), (-1, -0.55), (-0.65, -1), (0.65, -1), (1, -0.55)],
              lambda k: M["arc"])
        # Pale point under the cap.
        slab(P, rect(side_x(3.9, s) - (0 if s > 0 else 2.0), 37.6, side_x(3.9, s) + (2.0 if s > 0 else 0), 39.4, 0.4),
             0.3, 2.8, M["pale"], ch=0.4)
        # Strut from the shoulder down to the gun pod.
        for lp in loops_of("U", side, grow_into="TGW", n=1):
            slab(P, lp, -0.3, 4.3, M["strut"], ch=0.45)
        sweep(P, [(side_x(21.9, s), 33.6, 4.5, 0.45, 0.45), (side_x(21.9, s), 39.4, 4.5, 0.45, 0.45)],
              superellipse(8, 2.0), lambda k: M["rail"])

        # ---- gun pod ----
        loops = loops_of("G", side, grow_into="TQ", n=1)
        for lp in loops:
            slab(P, lp, -0.9, 3.9, M["gun"], ch=0.55, chb=0.45)
        # Recessed grille on top: dark floor, slats.
        gx0, gx1 = sorted((side_x(15.0, s), side_x(21.4, s)))
        slab(P, rect(gx0, 41.2, gx1, 44.6, 0.25), 3.0, 4.15, M["grille"], ch=0.0, chb=0.0)
        frame_outer = rect(gx0 - 0.6, 40.6, gx1 + 0.6, 45.2, 0.5)
        for (a0, b0, a1, b1) in ((gx0 - 0.6, 40.6, gx1 + 0.6, 41.3), (gx0 - 0.6, 44.5, gx1 + 0.6, 45.2)):
            slab(P, rect(a0, b0, a1, b1), 3.5, 4.45, M["gun"], ch=0.25, chb=0.0)
        for k in range(6):
            x = gx0 + 0.55 + k * (gx1 - gx0 - 1.1) / 5
            slab(P, rect(x - 0.22, 41.3, x + 0.22, 44.5), 3.4, 4.25, M["rib"], ch=0.12, chb=0.0)
        # Tall bracket at the outer end.
        bx0, bx1 = sorted((side_x(11.3, s), side_x(14.4, s)))
        br = [(12.6, 41.0), (14.4, 41.0), (14.4, 48.0), (13.7, 48.7), (12.1, 48.7), (11.3, 47.9), (11.3, 42.3)]
        slab(P, br if s > 0 else mirror_pts(br), -0.6, 5.0, M["rail"], ch=0.5)
        slab(P, rect(bx0 + 0.6, 42.6, bx1 - 0.6, 46.4, 0.3), 4.6, 5.4, M["gun"], ch=0.3, chb=0.0)
        # Two deep nozzles in the slanted aft face, each lip just proud of it.
        for xn, ye in ((14.7, 49.3), (17.9, 48.1)):
            xn = side_x(xn, s)
            zc, r = 1.5, 1.05
            ring_o = [(xn + r * math.cos(2 * math.pi * k / 16), zc + r * math.sin(2 * math.pi * k / 16)) for k in range(16)]
            sc = lambda q, f: (xn + (q[0] - xn) * f, zc + (q[1] - zc) * f)  # noqa: E731
            rings = [[(x, ye - 2.2, z) for x, z in ring_o],
                     [(x, ye - 0.15, z) for x, z in ring_o],
                     [(*(lambda q: (q[0], ye))(sc((x, z), 0.97)), sc((x, z), 0.97)[1]) for x, z in ring_o],
                     [(sc((x, z), 0.74)[0], ye, sc((x, z), 0.74)[1]) for x, z in ring_o],
                     [(sc((x, z), 0.70)[0], ye - 1.6, sc((x, z), 0.70)[1]) for x, z in ring_o]]
            loft(P, rings, lambda k: M["deep"] if k >= 3 else M["rail"] if k == 2 else M["gun"], cap0=True,
                 cap1=True, mat_cap1=M["glow"])

    # ---- torso ----
    for lp in loops_of("T", grow_into="Q", n=1):
        slab(P, lp, -1.4, 3.6, M["bay"], ch=0.45, chb=0.5)
    for s in (1, -1):
        col = [(23.0, 26.2), (26.2, 26.2), (26.4, 26.6), (26.4, 40.2), (25.4, 41.2), (23.0, 41.2)]
        if s < 0:
            col = [(2 * CX - x - 0.3, y) for x, y in reversed(col)]
        slab(P, col, 1.0, 6.3, M["column"], ch=0.6)
        # vertical panel line strip on the column
    # Grey hood from the core down to the chest light, its top sloping forward.
    hood = [(26.6, 23.6), (34.3, 23.6), (34.3, 30.6), (33.1, 32.2), (31.8, 33.2), (29.2, 33.2), (27.8, 32.2), (26.6, 30.6)]
    slab(P, hood, 1.0, plane(6.8, gy=-0.11, y0=24.0), M["hood"], ch=0.6)
    # hood ridge plates
    slab(P, rect(28.6, 26.4, 32.3, 31.0, 0.4), 5.5, plane(7.15, gy=-0.11, y0=24.0), M["hood"], ch=0.35)
    # Red chest light set under the hood's lip.
    sec = superellipse(14, 2.0)
    rings = []
    for k, (rx, rz, dy) in enumerate(((1.75, 0.0, 0.0), (1.75, 0.5, 0.0), (1.2, 0.95, 0.0), (0.0, 1.15, 0.0))):
        if rx == 0:
            rings.append([(30.3, 32.9, 5.3 + rz)])
        else:
            rings.append([(30.3 + u * rx, 32.9 + v * rx * 0.62, 5.3 + rz) for u, v in sec])
    loft(P, rings, lambda k: M["light"])
    slab(P, rect(29.6, 32.5, 31.0, 33.3, 0.25), 5.9, 6.65, M["hot"], ch=0.2, chb=0.0)
    # Chest stack with two raised ribs and a small lamp.
    slab(P, rect(26.9, 33.6, 33.9, 41.0, 0.5), 1.0, 5.6, M["hood"], ch=0.5)
    for y0, y1 in ((35.0, 36.4), (37.7, 39.0)):
        slab(P, rect(27.3, y0, 33.5, y1, 0.3), 5.2, 6.05, M["rib"], ch=0.3, chb=0.0)
    slab(P, rect(29.9, 39.6, 31.0, 40.7, 0.2), 5.3, 6.0, M["light"], ch=0.2, chb=0.0)
    # Ribbed silver cylinders down the chest's edges (the sprite's bright grey columns).
    for xr in (26.75, 34.15):
        sweep(P, [(xr, 32.4, 5.2, 0.0, 0.0), (xr, 32.45, 5.2, 0.55, 0.55), (xr, 32.7, 5.2, 0.78, 0.78),
                  (xr, 40.3, 5.2, 0.78, 0.78), (xr, 40.55, 5.2, 0.55, 0.55), (xr, 40.6, 5.2, 0.0, 0.0)],
              superellipse(14, 2.0), lambda k: M["rail"])
        for yr in frange(33.6, 39.4, 1.45):
            sweep(P, [(xr, yr - 0.22, 5.2, 0.9, 0.9), (xr, yr + 0.22, 5.2, 0.9, 0.9)], superellipse(14, 2.0),
                  lambda k: M["rib"])
    # Collar closing the bay, its pale centre plate.
    for lp in loops_of("Q", grow_into="TD", n=1):
        slab(P, lp, -0.8, plane(5.5, gy=-0.12, y0=42.0), M["collar"], ch=0.6, chb=0.4)
    slab(P, [(28.0, 41.9), (33.0, 41.9), (33.0, 44.0), (32.2, 44.9), (28.8, 44.9), (28.0, 44.0)], 4.6,
         plane(5.95, gy=-0.12, y0=42.0), M["pale"], ch=0.35, chb=0.0)
    # Tail dome: a round loft down the rows, a nozzle in its aft end.
    loop = loops_of("D", grow_into="Q", n=1)[0]
    dome_sec = superellipse(18, 2.3, start=0.0)
    dome_sec = [(u, v) for u, v in dome_sec if v >= -0.05] + [(-1.0, -0.6), (1.0, -0.6)]
    dome_sec = sorted(dome_sec[:-2], key=lambda p: -math.atan2(p[1], p[0]) if p[1] >= 0 else 0)

    def dome_at(y, xl, xr):
        cx, w = (xl + xr) / 2, (xr - xl) / 2
        h = 4.4 * math.sqrt(max(0.0, 1 - ((y - 44.6) / 4.9) ** 2)) - 0.0
        pts = [(cx + u * w, 0.2 + max(v, 0) * (h - 0.2)) for u, v in superellipse(16, 2.4, start=0.0) if v >= -1e-6]
        pts = sorted(pts, key=lambda p: -p[0])
        return pts + [(cx - w * 0.9, -0.9), (cx + w * 0.9, -0.9)][::-1][::-1]
    ys = frange(44.4, 48.95, 0.5)
    rings = []
    for y in ys:
        ex = x_extent(loop, y)
        if ex:
            rings.append([(x, y, z) for x, z in dome_at(y, *ex)])
    loft(P, rings, lambda k: M["dome"])
    # nozzle on the dome's aft face
    nz = [(30.3 + 1.4 * math.cos(2 * math.pi * k / 14), 1.3 + 1.1 * math.sin(2 * math.pi * k / 14)) for k in range(14)]
    rings = [[(x, 47.6, z) for x, z in nz], [(x, 49.05, z) for x, z in nz],
             [(30.3 + (x - 30.3) * 0.7, 49.05, 1.3 + (z - 1.3) * 0.7) for x, z in nz],
             [(30.3 + (x - 30.3) * 0.7, 47.9, 1.3 + (z - 1.3) * 0.7) for x, z in nz]]
    loft(P, rings, lambda k: M["deep"] if k >= 2 else M["gun"], mat_cap1=M["glow"])


def materials(sprite):
    out = []
    for name, idx, metal, rough, emit in MATS:
        out.append(common.palette_material(sprite, idx, f"nsh4A_{name}", metallic=metal, roughness=rough,
                                           emission_strength=emit))
    return out


def finish(P, mats, coll, name):
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    return obj


def build(sprite, coll):
    mats = materials(sprite)
    up = Part()
    build_upper(up)
    lo = Part()
    build_lower(lo)
    a = finish(up, mats, coll, NAME + "_upper")
    b = finish(lo, mats, coll, NAME + "_lower")
    return join([a, b], NAME)


def join(objs, name):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


# ---------------------------------------------------------------------------------------------
# Splitting into the game's pieces
# ---------------------------------------------------------------------------------------------

def layout(sprite_of, pieces):
    """[(piece, x, y)] for common.split_assembly: each piece's centre in screen pixels relative to
    the frame's origin (column edge AXIS_X, row edge MID_Y; the frame's top-left is (135, 159))."""
    data = sprite_of(pieces[0])
    return [(e["model"], e["cx"] - 135 - AXIS_X, e["cy"] - 159 - MID_Y) for e in data["assemblyLayout"]
            if e["model"] in pieces]


# ---------------------------------------------------------------------------------------------
# Measuring and rendering
# ---------------------------------------------------------------------------------------------

def sprite_image(sprite_of):
    """The composite sprite: palette index per pixel (72 x 52), lower pieces drawn over upper."""
    idx = -np.ones((52, 72), dtype=int)
    colours = {}
    for names in (UPPER, LOWER):
        data = sprite_of(names[0])
        lay = {e["model"]: e for e in data["assemblyLayout"]}
        for n in names:
            d = sprite_of(n)
            colours.update({int(k): v for k, v in d["colors"].items()})
            e = lay[n]
            x0, y0 = e["cx"] - 12 - 135, e["cy"] - 14 - 159
            for r, row in enumerate(d["frames"][0]["pixels"]):
                for c, v in enumerate(row):
                    if v >= 0 and 0 <= y0 + r < 52 and 0 <= x0 + c < 72:
                        idx[y0 + r, x0 + c] = v
    return idx, colours


def set_engine(scene, want):
    try:
        scene.render.engine = want
    except TypeError as err:
        names = [w for w in str(err).replace("'", " ").replace(",", " ").replace("(", " ").replace(")", " ").split() if w.isupper()]
        scene.render.engine = next(n for n in names if want.split("_")[1] in n)


def ortho_top_camera(scene, ss):
    cam_d = bpy.data.cameras.new("measure_top")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 72 * PX
    cam = bpy.data.objects.new("measure_top", cam_d)
    scene.collection.objects.link(cam)
    cam.location = ((36 - AXIS_X) * PX, (MID_Y - 26) * PX, 5)
    cam.rotation_euler = (0, 0, 0)
    scene.render.resolution_x = 72 * ss
    scene.render.resolution_y = 52 * ss
    scene.render.resolution_percentage = 100
    return cam


def render_to_array(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], img.channels)
    bpy.data.images.remove(img)
    return px[::-1]


def measure(objs, sprite_of, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o not in objs]
    for o in hidden:
        o.hide_render = True
    set_engine(scene, "BLENDER_WORKBENCH")
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    scene.display.render_aa = "OFF"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("w")
    scene.world.color = (0, 0, 0)
    ss = 8
    cam = ortho_top_camera(scene, ss)
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sil = render_to_array(scene, cam, out_dir / "top_silhouette.png")[..., 0]
    cov = sil.reshape(52, ss, 72, ss).mean(axis=(1, 3))
    model = cov >= 0.5
    idx, colours = sprite_image(sprite_of)
    mask = idx >= 0
    inter = (model & mask).sum()
    union = (model | mask).sum()
    iou = inter / union
    rows = []
    for r in range(52):
        sc = np.nonzero(mask[r])[0]
        mc = np.nonzero(model[r])[0]
        if len(sc) or len(mc):
            rows.append({"row": r, "sprite": [int(sc.min()), int(sc.max())] if len(sc) else None,
                         "model": [int(mc.min()), int(mc.max())] if len(mc) else None,
                         "sprite_n": int(len(sc)), "model_n": int(len(mc)),
                         "miss": int((mask[r] & ~model[r]).sum()), "extra": int((model[r] & ~mask[r]).sum())})
    # Colour: each material's palette colour, flat, from above.
    sh.color_type = "MATERIAL"
    flat = render_to_array(scene, cam, out_dir / "top_flat.png")[..., :3]
    centre = flat[ss // 2::ss, ss // 2::ss]
    # nearest palette index among the materials' indices
    pal = {}
    for name, i, *_ in MATS:
        pal[i] = np.array(colours[i]) / 255
    keys = list(pal)
    arr = np.array([pal[k] for k in keys])
    d = ((centre[..., None, :] - arr[None, None]) ** 2).sum(-1)
    seen = np.array(keys)[d.argmin(-1)]
    seen[~model] = -1
    # per label: sprite median (trimmed, by colour ramp) vs the model's dominant index seen
    report = {}
    for L in sorted(set(LAB.ravel()) - {" "}):
        sel = (LAB == L) & (idx > 1)
        mod = (LAB == L) & model
        if not sel.any():
            continue
        vals, cnt = np.unique(seen[mod], return_counts=True)
        report[L] = {"sprite_indices": sorted(int(v) for v in idx[sel]),
                     "model_seen": {int(v): int(c) for v, c in zip(vals, cnt)}}
    (out_dir / "metrics.json").write_text(json.dumps({"iou": round(float(iou), 4), "rows": rows,
                                                       "colours": report}, indent=1))
    np.save(out_dir / "model_mask.npy", model)
    np.save(out_dir / "seen.npy", seen)
    np.save(out_dir / "sprite_idx.npy", idx)
    for o in hidden:
        o.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True)
    print(f"IOU {iou:.4f}  (sprite {mask.sum()} px, model {model.sum()} px, miss {(mask & ~model).sum()}, extra {(model & ~mask).sum()})")
    return iou


def render_views(objs, out_dir, size=720):
    """Lit renders (EEVEE): top, side, front, rear, 3/4 high front-left, 3/4 rear-right, the game
    camera (33 degrees from straight down, from the bottom of the screen) and one underside view."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    hidden = [o for o in scene.objects if o.type == "MESH" and o not in objs]
    for o in hidden:
        o.hide_render = True
    set_engine(scene, "BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.21, 0.24, 1)
    bg.inputs["Strength"].default_value = 1.0
    lights = []
    for name, rot, energy in (("key", (math.radians(40), math.radians(-28), math.radians(-30)), 3.6),
                              ("fill", (math.radians(60), math.radians(40), math.radians(150)), 0.9)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = energy
        ld.angle = math.radians(3)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        scene.collection.objects.link(lo)
        lights.append(lo)
    centre = Vector(((36 - AXIS_X) * PX, (MID_Y - 26) * PX, 0.25))
    views = {}

    def cam(name, loc, ortho=None, lens=60, up_y=False):
        cd = bpy.data.cameras.new(name)
        if ortho:
            cd.type = "ORTHO"
            cd.ortho_scale = ortho
        else:
            cd.lens = lens
        co = bpy.data.objects.new(name, cd)
        scene.collection.objects.link(co)
        co.location = centre + Vector(loc)
        direction = centre - co.location
        co.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return co
    d = 12.0
    specs = [
        ("top", (0, 0, 10), 6.4, True),
        ("side", (-10, 0, 0), 6.4, False),
        ("front", (0, 10, 0), 6.4, False),
        ("rear", (0, -10, 0), 6.4, False),
        ("high34", (-d * 0.5, d * 0.55, d * 0.55), None, False),
        ("rear34", (d * 0.55, -d * 0.55, d * 0.45), None, False),
        ("game", (0, -d * 0.545, d * 0.84), None, True),
        ("under", (d * 0.35, -d * 0.45, -d * 0.6), None, False),
    ]
    for name, loc, ortho, upy in specs:
        c = cam("view_" + name, loc, ortho=ortho, lens=62, up_y=upy)
        if name == "top":
            c.rotation_euler = (0, 0, 0)
        scene.camera = c
        p = out_dir / f"{name}.png"
        scene.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        views[name] = str(p)
        bpy.data.objects.remove(c, do_unlink=True)
    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    for o in hidden:
        o.hide_render = False
    return views


# ---------------------------------------------------------------------------------------------
# Bake (occlusion and edge wear only; no concept projection)
# ---------------------------------------------------------------------------------------------

def bake_maps(obj, out_dir, size=1024, samples=64):
    scene = bpy.context.scene
    set_engine(scene, "CYCLES")
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        if any(dv.type == "METAL" for dv in prefs.devices):
            scene.cycles.device = "GPU"
    except Exception as err:  # noqa: BLE001
        print("no GPU bake", err)
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
    col_img = bpy.data.images.new("nsh4A_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new("nsh4A_rm", size // 2, size // 2, alpha=False)
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

        def mth(op, a, b=None):
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
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.2
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bev.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
        edge = mth("MINIMUM", mth("MULTIPLY", mth("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = mth("MULTIPLY", mth("POWER", ao_s.outputs["AO"], 0.8),
                   mth("ADD", 0.65, mth("MULTIPLY", ao_l.outputs["AO"], 0.35)))
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = mth("MINIMUM", mth("ADD", mth("ADD", 0.5, mth("MULTIPLY", occl, 0.6)), mth("MULTIPLY", edge, 0.18)), 1.0)
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                nt.links.new(v, comb.inputs[k])
            nt.links.new(comb.outputs[0], em.inputs["Color"])
        else:
            r = mth("ADD", rough, mth("SUBTRACT", mth("MULTIPLY", mth("SUBTRACT", 1.0, occl), 0.3), mth("MULTIPLY", edge, 0.15)))
            r = mth("MAXIMUM", mth("MINIMUM", r, 1.0), 0.05)
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
    for name, idx, metal, rough, emit in MATS:
        if emit:
            continue
        m = mats[M[name]]
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


def cull_hidden(obj, grid=4, ndirs=40):
    """Delete faces no ray from outside reaches (buried walls of overlapping plates)."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    golden = math.pi * (3 - math.sqrt(5))
    dirs = []
    for i in range(ndirs):
        z = 1 - 2 * (i + 0.5) / ndirs
        r = math.sqrt(1 - z * z)
        dirs.append(Vector((r * math.cos(golden * i), r * math.sin(golden * i), z)))
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c] + [c.lerp(v, t) for v in vs for t in (0.5, 0.9)]
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * 2e-4
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    print(f"culled {len(dead)} hidden faces")


def outline_shell(obj, coll, voxel=0.016, faces=6000, smooth=8):
    """common.outline_shell (D51), but keeping every outer island of the voxel remesh: the horns,
    claws and wing-tip arcs stand free of the hull, and common's shell keeps only the largest
    island. Inner shells (cavities, negative volume) are dropped."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    shell.matrix_world = obj.matrix_world.copy()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    rm.use_smooth_shade = True
    common._apply_modifiers(shell)
    bm = bmesh.new()
    bm.from_mesh(shell.data)
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
        islands.append(isl)

    # An inner shell (a closed cavity) faces inward: its signed volume is negative.
    island_of = {}
    for i, isl in enumerate(islands):
        for v in isl:
            island_of[v.index] = i
    vol = [0.0] * len(islands)
    for f in bm.faces:
        cs = [v.co for v in f.verts]
        for k in range(1, len(cs) - 1):
            vol[island_of[f.verts[0].index]] += cs[0].dot(cs[k].cross(cs[k + 1])) / 6
    drop = {i for i, v in enumerate(vol) if v <= 0}
    dead = [v for i in drop for v in islands[i]]
    bmesh.ops.delete(bm, geom=dead, context="VERTS")
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
    print(f"outline shell: kept {len(islands) - len(drop)} of {len(islands)} islands, {len(shell.data.polygons)} faces")
    return shell


def tris(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def composite_png(sprite_of, out):
    """The whole 72 x 52 px sprite as a PNG (for render_preview)."""
    idx, colours = sprite_image(sprite_of)
    img = np.zeros((52, 72, 4), dtype=np.float32)
    for r in range(52):
        for c in range(72):
            if idx[r, c] >= 0:
                img[r, c] = [*(ch / 255 for ch in colours[int(idx[r, c])]), 1.0]
    im = bpy.data.images.new("assembly_sprite", 72, 52, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def run(pieces, argv):
    """Build the whole craft, bake it, and export `pieces` (UPPER or LOWER) to
    public/models/enemies/<piece>.glb with their spriteModels entries."""
    import tempfile
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa: E731
    cache = {}

    def sprite_of(n):
        if n not in cache:
            cache[n] = common.load_sprite(ROOT, n)
        return cache[n]
    sprite = json.loads(json.dumps(sprite_of(UPPER[0])))
    for n in UPPER[1:] + LOWER:
        sprite["colors"].update(sprite_of(n)["colors"])
    coll = common.reset_collection(NAME)
    obj = build(sprite, coll)
    print(f"model: {len(obj.data.polygons)} faces, {tris(obj)} triangles")
    if arg("--measure"):
        measure([obj], sprite_of, arg("--measure"))
    cull_hidden(obj)
    print(f"after cull: {tris(obj)} triangles")
    wn = obj.modifiers.new("weighted", "WEIGHTED_NORMAL")
    wn.keep_sharp = True
    wn.weight = 50
    common._apply_modifiers(obj)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        bake_maps(obj, tempfile.mkdtemp(prefix="nsh4_bake_"))
        fmt = "WEBP"
    if arg("--views"):
        render_views([obj], arg("--views"))
    if "--no-export" in argv:
        return obj
    # The outline shell of the whole craft, cut like the model, so the contour runs on across the
    # piece seams.
    shell = outline_shell(obj, coll, voxel=0.016, faces=6000, smooth=8)
    lay = layout(sprite_of, pieces)
    parts = common.split_assembly(obj, lay, coll)
    shells = common.split_assembly(shell, lay, coll)
    for name in pieces:
        p, sh = parts[name], shells[name]
        sh.name = f"{name}_outline"
        sh["tyrian_outline"] = True
        print(f"piece {name}: {tris(p)} triangles, outline {len(sh.data.polygons)} faces")
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", sprite_of(name)["sprites"], image_format=fmt)
    if arg("--preview"):
        out = Path(arg("--preview"))
        ref = composite_png(sprite_of, Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), str(ref), size=(72, 52), view_px=640)
    return obj
