"""Red crab boss (newsht.shp, 12 pieces, 144 x 56 px): design B, a hard-surface 3D version of its sprite.

Seen in levels 1.5 DELIANI (1.19 in the catalogue), 3.11 New Deli and 4.1 HARVEST. Twelve 2x2 enemies
side by side make one machine: a red body with two dark glass orbs in U-shaped frames, a grey visor
and cannon between them, two glowing exhausts on its back, and two arms that reach out on a beam,
drop as thick round upper arms through an elbow drum into a claw pod with a glowing red eye
(newsht-39 / -49: frames 39 -> 77 -> 79 and 49 -> 87 -> 85 only brighten the eye, so the eye's
materials carry per-frame palette indices, D17).

Design B leads with silhouette and readability from the small tilted game camera: big simple
volumes first (the round arms and claws, the orbs, the U frames, the raised spine and shoulders),
then machined detail on what the camera sees (panel gaps cut through the plates, collars and
cuffs on the tubes, a raised brace, bolts, an exhaust grille with hot vanes, a recessed muzzle).

The ORIGINAL SPRITE decides the plan (D52, D74): every sprite pixel of the INNER mask (the sprite
less its ink ring, which the game's ink outline stands in for) is given to a named part by the
blueprint's ordered rules (blueprint/gen.py RULES: a shape in left-half columns plus a colour
class). Plates are prisms on the traced outline of their own pixels (pixel-edge contour, stair
midpoints, Douglas-Peucker), tubes take each row's (or column's) run of their pixels as their
width through pchip stations, hoses follow their region's distance field. Each side is built on
its own half of the sprite (the right as the left on the mirrored pixels, then flipped).
Heights follow the blueprint (px, 12 px = 1 unit): orbs 12.9, arms 11.6, canister 11.4, elbow
drum 10, hoses 10, spine 9, claws 9, shoulders 7.4 (+1 brace), U frames 8, housings 8.2,
cheeks 6.4, cannon 7.4, recess floor 1.6.

Colours: palette materials (pal_<index>), each the blueprint's median sprite index of the part
(darkest shading and brightest sheen trimmed); satin painted metal for the red, satin steel for
the grey, glossy dark glass for the orbs. Exhaust beds glow (117) with the sprite's own hot
streak pixels as flush lit vanes. No concept projection: an AO/edge + roughness bake only
("bake": "model"), and the outline shell (D51) of the whole closed machine cut open per piece.

Underside: closed and plain (flat plate bottoms, tubes closed below).

Run: blender -b --python assets/blender/enemies/assembly-newsht-39.py -- [--no-bake] [--no-export] [--design-out whole.glb]
Exports each piece to public/models/enemies/<piece>.glb + src/render/spriteModels/<piece>.json (the
same model also covers the cracked frames 117, 123, 157, 159 of newsht-3, -9, -43, -45: same
silhouette as the intact piece, D79).
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask  # noqa: E402

ROOT = WT
NAME = "assembly-newsht-39"
HERE = Path(__file__).resolve().parent
PIECES = ["newsht-1", "newsht-3", "newsht-5", "newsht-7", "newsht-9", "newsht-11",
          "newsht-39", "newsht-41", "newsht-43", "newsht-45", "newsht-47", "newsht-49"]
CX0, CY0 = 141, 33  # screen point of the assembly's centre (Blender origin)
W, H = 144, 56
AXIS = 71           # mirror: pixel c <-> 142 - c; pixel-edge x <-> 143 - x
TAG = "nsht39b"
# Cracked-armour frames (same silhouette as the intact piece, other pixels) ride on the intact model.
CRACKED = {"newsht-3": [117], "newsht-9": [123], "newsht-43": [157], "newsht-45": [159]}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ----------------------------------------------------------------------------------------------
# The sprite
# ----------------------------------------------------------------------------------------------


def load_assembly():
    layout = common.load_sprite(ROOT, "newsht-39")["assemblyLayout"]
    grid = [[-1] * W for _ in range(H)]
    colours = {}
    for e in layout:
        if e["model"] not in PIECES:
            continue
        d = common.load_sprite(ROOT, e["model"])
        colours.update(d["colors"])
        fr = d["frames"][0]
        x0, y0 = e["cx"] - CX0 + 60, e["cy"] - CY0 + 14
        for r, row in enumerate(fr["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid, colours, layout


GRID, COLOURS, LAYOUT = load_assembly()
_m = sprite_mask.masks(GRID, {int(k): tuple(v) for k, v in COLOURS.items()})
INNER = [[a or b for a, b in zip(ri, rf)] for ri, rf in zip(_m["inner"], _m["free"])]


def cls(v):
    if v < 0:
        return None
    if v == 1:
        return "ink"
    if v < 16:
        return "grey"
    if 64 <= v < 80:
        return "red"
    return "glow"


def R(c0, r0, c1, r1):
    return ("rect", c0, r0, c1, r1)


def CIRC(cx, cy, r):
    return ("circ", cx, cy, r)


def inshape(sh, c, r):
    if sh[0] == "rect":
        return sh[1] <= c <= sh[3] and sh[2] <= r <= sh[4]
    _, cx, cy, rad = sh
    return (c + 0.5 - cx) ** 2 + (r + 0.5 - cy) ** 2 <= rad * rad


# The blueprint's pixel -> part rules (blueprint/gen.py), first match wins; shapes in left-half columns.
RULES = [
    ("exhaust-glow", "L", [R(53, 1, 67, 9)], {"glow"}),
    ("claw-eye", "L", [R(10, 44, 18, 50)], {"glow"}),
    ("spine", "C", [R(66, 4, 76, 12)], {"red"}),
    ("upper-band", "L", [R(43, 8, 60, 12)], {"red", "ink"}),
    ("exhaust-housing", "L", [R(52, 1, 66, 12)], {"red", "ink", "grey"}),
    ("hose", "L", [R(33, 6, 44, 9), R(33, 10, 41, 13)], {"grey", "ink"}),
    ("orb", "L", [CIRC(59.5, 22.8, 6.7)], {"grey", "ink"}),
    ("visor", "C", [R(65, 16, 77, 19)], {"grey"}),
    ("slot", "C", [R(59, 13, 83, 15)], {"ink", "grey"}),
    ("stem", "C", [R(66, 19, 78, 24)], {"grey"}),
    ("cannon", "C", [R(67, 29, 75, 35)], {"grey"}),
    ("u-frame", "L", [R(46, 20, 51, 41), R(46, 30, 68, 41), R(60, 24, 68, 41)], {"red"}),
    ("cradle", "L", [R(51, 28, 62, 35), R(51, 23, 56, 28)], {"grey"}),
    ("bracket", "L", [R(42, 23, 46, 31)], {"red"}),
    ("cheek", "L", [R(39, 9, 64, 15), R(43, 16, 64, 24)], {"red"}),
    ("shoulder", "L", [R(25, 13, 41, 23)], {"red"}),
    ("beam", "L", [R(15, 19, 24, 23)], {"red"}),
    ("leg", "L", [R(26, 23, 31, 28)], {"red"}),
    ("foot", "L", [R(26, 29, 32, 31)], {"red"}),
    ("link-pipe", "L", [R(20, 16, 25, 19)], {"grey"}),
    ("canister", "L", [R(8, 10, 13, 19)], {"grey"}),
    ("gearbox", "L", [R(13, 10, 19, 19)], {"grey"}),
    ("arm-hose", "L", [R(15, 23, 22, 35)], {"grey"}),
    ("elbow", "L", [R(8, 36, 19, 39)], {"red"}),
    ("arm", "L", [R(3, 19, 17, 39)], {"red"}),
    ("claw-rim", "L", [R(11, 44, 17, 49)], {"ink"}),
    ("claw-vent", "L", [R(7, 44, 10, 49)], {"ink", "grey"}),
    ("claw", "L", [R(7, 40, 20, 53)], {"red"}),
    ("recess", "C", [R(0, 0, 143, 55)], {"ink"}),
]


def label():
    """{(base, side): set of (c, r)} in absolute sprite pixels; side L / R / C."""
    out = {}
    for r in range(H):
        for c in range(W):
            if not INNER[r][c]:
                continue
            k = cls(GRID[r][c])
            side = "L" if c <= AXIS else "R"
            cl = c if c <= AXIS else 2 * AXIS - c
            for base, s, shapes, fam in RULES:
                if k not in fam:
                    continue
                cc = c if s == "C" else cl
                if any(inshape(sh, cc, r) for sh in shapes):
                    out.setdefault((base, side if s == "L" else "C"), set()).add((c, r))
                    break
    return out


LAB = label()
CUR_SIDE = ["L"]


def pix(base):
    """The current side's pixels of a mirrored part, in left-half coordinates."""
    s = LAB.get((base, CUR_SIDE[0]), set())
    if CUR_SIDE[0] == "R":
        return {(2 * AXIS - c, r) for c, r in s}
    return set(s)


def cpix(base):
    return set(LAB.get((base, "C"), set()))


def inner_left(c, r):
    if CUR_SIDE[0] == "R":
        c = 2 * AXIS - c
    return 0 <= c < W and 0 <= r < H and INNER[r][c]


# ----------------------------------------------------------------------------------------------
# Outlines and curves
# ----------------------------------------------------------------------------------------------

def components(pixels):
    pixels = set(pixels)
    out = []
    while pixels:
        st = [pixels.pop()]
        comp = set(st)
        while st:
            c, r = st.pop()
            for q in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if q in pixels:
                    pixels.discard(q)
                    comp.add(q)
                    st.append(q)
        out.append(comp)
    return out


def trace(pixels, tol=0.3):
    """Outer boundary of a pixel set: pixel-edge contour, unit edges replaced by their midpoints
    (1-px stairs become 45-degree lines), Douglas-Peucker."""
    edges = {}
    for c, r in pixels:
        if (c, r - 1) not in pixels:
            edges.setdefault((c, r), []).append((c + 1, r))
        if (c + 1, r) not in pixels:
            edges.setdefault((c + 1, r), []).append((c + 1, r + 1))
        if (c, r + 1) not in pixels:
            edges.setdefault((c + 1, r + 1), []).append((c, r + 1))
        if (c - 1, r) not in pixels:
            edges.setdefault((c, r + 1), []).append((c, r))
    loops = []
    while edges:
        start = next(iter(edges))
        loop = [start]
        cur = start
        prev = None
        while True:
            outs = edges[cur]
            if len(outs) > 1 and prev is not None:
                def turn(o):
                    d = (o[0] - cur[0], o[1] - cur[1])
                    return prev[0] * d[1] - prev[1] * d[0]
                outs.sort(key=turn, reverse=True)
            nxt = outs.pop(0)
            if not outs:
                del edges[cur]
            prev = (nxt[0] - cur[0], nxt[1] - cur[1])
            cur = nxt
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)

    def area(lp):
        return sum(lp[i][0] * lp[(i + 1) % len(lp)][1] - lp[(i + 1) % len(lp)][0] * lp[i][1] for i in range(len(lp))) / 2
    loop = max(loops, key=lambda lp: abs(area(lp)))
    mids = [((loop[i][0] + loop[(i + 1) % len(loop)][0]) / 2, (loop[i][1] + loop[(i + 1) % len(loop)][1]) / 2)
            for i in range(len(loop))]
    return simplify(mids, tol)


def simplify(pts, tol):
    def dp(seq):
        if len(seq) < 3:
            return seq
        (x0, y0), (x1, y1) = seq[0], seq[-1]
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy) or 1e-9
        best, bi = -1, 0
        for i in range(1, len(seq) - 1):
            d = abs(dy * (seq[i][0] - x0) - dx * (seq[i][1] - y0)) / ln
            if d > best:
                best, bi = d, i
        if best <= tol:
            return [seq[0], seq[-1]]
        return dp(seq[:bi + 1])[:-1] + dp(seq[bi:])
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = dp(pts[0:i1 + 1])
    b = dp(pts[i1:] + [pts[0]])
    return a[:-1] + b[:-1]


def pchip(xs, ys):
    n = len(xs)
    if n == 1:
        return lambda x: ys[0]
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


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def poly_area(p):
    n = len(p)
    return sum(p[i][0] * p[(i + 1) % n][1] - p[(i + 1) % n][0] * p[i][1] for i in range(n)) / 2


def offset_poly(poly, d):
    """Inset (d > 0) a polygon by moving each vertex along its miter."""
    n = len(poly)
    s = 1 if poly_area(poly) > 0 else -1
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]

        def nrm(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(dx, dy) or 1e-9
            return (-dy / ln * s, dx / ln * s)
        n1, n2 = nrm(p0, p1), nrm(p1, p2)
        mx, my = n1[0] + n2[0], n1[1] + n2[1]
        ln = math.hypot(mx, my) or 1e-9
        mx, my = mx / ln, my / ln
        cos = max(0.5, mx * n2[0] + my * n2[1])
        out.append((p1[0] + mx * d / cos, p1[1] + my * d / cos))
    return out


def clip(poly, a, b, c):
    """Sutherland-Hodgman: the part of poly where a*x + b*y + c >= 0."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


class Field:
    """Distance (px) from a point to the edge of a pixel set (4x subgrid)."""

    def __init__(self, pixels):
        import numpy as np
        self.np = np
        cs = [c for c, _ in pixels]
        rs = [r for _, r in pixels]
        pts = []
        for r in range(min(rs) - 3, max(rs) + 4):
            for c in range(min(cs) - 3, max(cs) + 4):
                if (c, r) not in pixels:
                    for i in range(4):
                        for j in range(4):
                            pts.append((c + (i + 0.5) / 4, r + (j + 0.5) / 4))
        self.out = np.array(pts)

    def __call__(self, x, y):
        d = self.np.sqrt(((self.out - (x, y)) ** 2).sum(axis=1)).min()
        return max(0.0, d - 0.125)


def centre_on(field, path, search=2.0):
    out = []
    for i, (x, y) in enumerate(path):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1
        nx, ny = -ty / ln, tx / ln
        best = max((field(x + nx * s, y + ny * s), -abs(s), s) for s in
                   [k * 0.125 - search for k in range(int(search * 16) + 1)])
        out.append((x + nx * best[2], y + ny * best[2]))
    return out


def catmull(pts, per=4):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(len(p1))))
    out.append(tuple(pts[-1]))
    return out


# ----------------------------------------------------------------------------------------------
# Mesh building (sprite px: x right, y down the sprite, z up)
# ----------------------------------------------------------------------------------------------

class Part:
    def __init__(self):
        self.bm = bmesh.new()

    def v(self, p):
        return self.bm.verts.new(p)

    def f(self, verts, mat):
        try:
            face = self.bm.faces.new(verts)
        except ValueError:
            return None
        face.material_index = mat
        return face


def loft(P, rings, mats, cap0=True, cap1=True):
    """Rings of equal count (or a single point) in order; mats per span (or one)."""
    if not isinstance(mats, (list, tuple)):
        mats = [mats] * max(1, len(rings) - 1)
    vr = [[P.v(p) for p in ring] for ring in rings]
    for i, (a, b) in enumerate(zip(vr, vr[1:])):
        m = mats[min(i, len(mats) - 1)]
        if len(a) == 1 and len(b) == 1:
            continue
        n = max(len(a), len(b))
        for k in range(n):
            j = (k + 1) % n
            if len(a) == 1:
                P.f((a[0], b[k], b[j]), m)
            elif len(b) == 1:
                P.f((a[k], a[j], b[0]), m)
            else:
                P.f((a[k], a[j], b[j], b[k]), m)
    if cap0 and len(vr[0]) > 2:
        P.f(list(reversed(vr[0])), mats[0])
    if cap1 and len(vr[-1]) > 2:
        P.f(vr[-1], mats[-1])


def prism(P, outline, z0, z1, mat, r=0.6, chb=0.25, tilt=None, side_mat=None, steps=1):
    """A plate over `outline` from z0 to z1 (+ tilt(x, y)), its top edge rounded with radius r
    (`steps` facets: 1 = a 45-degree chamfer) and its bottom edge chamfered chb."""
    pts = outline if poly_area(outline) > 0 else list(reversed(outline))
    n = len(pts)
    tz = tilt or (lambda x, y: 0.0)
    th = z1 - z0
    r = min(r, th * 0.6)
    chb = min(chb, th * 0.25)
    levels = []
    if chb > 0:
        levels.append((offset_poly(pts, chb), z0))
        levels.append((pts, z0 + chb))
    else:
        levels.append((pts, z0))
    if r > 0:
        levels.append((pts, z1 - r))
        for k in range(1, steps + 1):
            a = math.pi / 2 * k / steps
            levels.append((offset_poly(pts, r * (1 - math.cos(a))), z1 - r + r * math.sin(a)))
    else:
        levels.append((pts, z1))
    rings = [[P.v((x, y, z + tz(rx, ry))) for (x, y), (rx, ry) in zip(poly, pts)] for poly, z in levels]
    sm = side_mat if side_mat is not None else mat
    top_from = len(rings) - 2 - (steps - 1 if r > 0 else 0)
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            P.f((a[i], a[j], b[j], b[i]), mat if k >= top_from else sm)
    P.f(list(reversed(rings[0])), sm)
    P.f(rings[-1], mat)


def plates(P, pixels, z0, z1, mat, r=0.6, chb=0.25, cuts=(), gap=0.45, depth=0.8, core_mat=None, tol=0.4,
           tilt=None, side_mat=None, steps=1, min_px=2):
    """Prisms on the traced outline of each component of `pixels`, split by panel lines.
    cuts: [(p, q)] straight lines (pixel-edge coords) through the plate; each splits the plates it
    crosses with a `gap` wide groove; a core prism `depth` lower fills the grooves' floor."""
    for comp in components(pixels):
        if len(comp) < min_px:
            continue
        outline = trace(comp, tol)
        if len(outline) < 3:
            continue
        polys = [outline]
        for p, q in cuts:
            a, b = q[1] - p[1], -(q[0] - p[0])
            ln = math.hypot(a, b)
            a, b = a / ln, b / ln
            c = -(a * p[0] + b * p[1])
            nxt = []
            for poly in polys:
                s = [a * x + b * y + c for x, y in poly]
                if min(s) > -gap or max(s) < gap:
                    nxt.append(poly)
                    continue
                for sg in (1, -1):
                    part = clip(poly, sg * a, sg * b, sg * c - gap / 2)
                    if len(part) >= 3 and abs(poly_area(part)) > 2.0:
                        nxt.append(part)
            polys = nxt
        for poly in polys:
            prism(P, poly, z0, z1, mat, r=min(r, 0.7), chb=chb, tilt=tilt, side_mat=side_mat, steps=steps)
        if cuts:
            prism(P, offset_poly(outline, 0.1), z0, z1 - depth, core_mat if core_mat is not None else mat,
                  r=0.0, chb=0.0, tilt=tilt)


def sec_loop(cx, y, hw, zc, hz, n=24, p=2.0, zfloor=None):
    """A superellipse section across x at row y."""
    pts = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        x = cx + hw * math.copysign(abs(c) ** (2 / p), c)
        z = zc + hz * math.copysign(abs(s) ** (2 / p), s)
        if zfloor is not None:
            z = max(z, zfloor)
        pts.append((x, y, z))
    return pts


def runs(pixels, axis):
    """{row: (lo, hi)} (axis 'y': stations along y, extent in x) or {col: (lo, hi)} (axis 'x')."""
    out = {}
    for c, r in pixels:
        k, v = (r, c) if axis == "y" else (c, r)
        lo, hi = out.get(k, (1e9, -1e9))
        out[k] = (min(lo, v), max(hi, v + 1))
    return out


def tube(P, pixels, axis, zc, hz, mat, n=12, p=2.2, zfloor=None, step=1.5, bands=(), band_mat=None,
         end_k=(0.82, 0.82), cap_ch=0.5, inset=0.0, bore=None, span=None, dome=True):
    """A tube lying along `axis` ('y' down the sprite or 'x' across) whose width at each station is
    its pixels' run there (pchip through the row / column centres), so its top view is the
    sprite's. zc / hz may be functions of the station. Ends: a chamfered cap (the last ring
    shrunk by end_k, then a flat face). bands: [(s0, s1, grow)] collars (grow > 0) or grooves
    (grow < 0) along the tube. bore: (mat, k, depth) recesses the far end's cap (a muzzle)."""
    rr = runs(pixels, axis)
    ks = sorted(rr)
    if span:
        ks = [k for k in ks if span[0] <= k <= span[1]]
    st = [k + 0.5 for k in ks]
    lo = pchip(st, [rr[k][0] + inset for k in ks])
    hi = pchip(st, [rr[k][1] - inset for k in ks])
    Z = zc if callable(zc) else (lambda s, v=zc: v)
    HZ = hz if callable(hz) else (lambda s, v=hz: v)
    s0, s1 = ks[0], ks[-1] + 1

    def ring(s, grow=0.0, k=1.0):
        a, b = lo(s), hi(s)
        c, hw = (a + b) / 2, max(0.05, (b - a) / 2 * k + grow)
        h = max(0.05, HZ(s) * k + grow)
        pts = sec_loop(c, 0.0, hw, Z(s), h, n=n, p=p, zfloor=zfloor)
        if axis == "y":
            return [(x, s, z) for x, _, z in pts]
        # across y at column s: map the section's x to y
        return [(s, x, z) for x, _, z in reversed(pts)]

    ss = frange(s0, s1, step)
    marks = []
    for b0, b1, g in bands:
        marks += [(b0, g), (b1, -g)]
    rings, mats = [], []
    bm = band_mat if band_mat is not None else mat
    # start cap
    ce = min(cap_ch, (s1 - s0) / 4)
    rings.append(ring(s0, k=end_k[0]))
    mats.append(mat)
    if dome:
        rings.append(ring(s0 + ce * 0.3, k=end_k[0] + (1 - end_k[0]) * 0.72))
        mats.append(mat)
    grow = 0.0
    events = sorted(set([s for s in ss[1:-1] if s0 + ce < s < s1 - ce] + [s0 + ce, s1 - ce] +
                        [b for b, _ in marks if s0 + ce < b < s1 - ce]))
    for s in events:
        hits = [g for b, g in marks if abs(b - s) < 1e-9]
        if hits:
            rings.append(ring(s, grow))
            mats.append(bm if grow > 0 else mat)
            grow += sum(hits)
            rings.append(ring(s, grow))
            mats.append(bm if grow > 0 else mat)
        else:
            rings.append(ring(s, grow))
            mats.append(bm if grow > 0 else mat)
    if dome:
        rings.append(ring(s1 - ce * 0.3, k=end_k[1] + (1 - end_k[1]) * 0.72))
        mats.append(mat)
    rings.append(ring(s1, k=end_k[1]))
    if bore:
        bmat, bk, bd = bore
        d = 1 if True else -1
        rings.append(ring(s1, k=end_k[1] * bk))
        mats.append(mat)
        inner = ring(s1 - bd, k=end_k[1] * bk)
        rings.append(inner)
        mats.append(bmat)
        loft(P, rings, mats + [bmat], cap0=True, cap1=True)
        return
    loft(P, rings, mats, cap0=True, cap1=True)


def sweep(P, path, radii, mat, n=12, up=(0, 0, 1), cap=True, mats=None):
    """A tube along a 3D path (px); radii[i] = (half width, half height)."""
    profile = [(math.cos(2 * math.pi * (k + 0.5) / n), math.sin(2 * math.pi * (k + 0.5) / n)) for k in range(n)]
    upv = Vector(up)
    rings = []
    for i, p in enumerate(path):
        a, b = Vector(path[max(i - 1, 0)]), Vector(path[min(i + 1, len(path) - 1)])
        t = (b - a).normalized()
        side = t.cross(upv)
        if side.length < 1e-6:
            side = Vector((1, 0, 0))
        side.normalize()
        u = side.cross(t).normalized()
        w, h = radii[i]
        if w <= 1e-6 and h <= 1e-6:
            rings.append([tuple(p)])
        else:
            rings.append([tuple(Vector(p) + side * (w * pu) + u * (h * pv)) for pu, pv in profile])
    loft(P, rings, mats or mat, cap0=cap, cap1=cap)


def ellipsoid(P, x, y, z, rx, ry, rz, mat, seg=32, rings=16, zfloor=None):
    res = bmesh.ops.create_uvsphere(P.bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = z + v.co.z * rz
        if zfloor is not None:
            zz = max(zz, zfloor)
        v.co = Vector((x + v.co.x * rx, y + v.co.y * ry, zz))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def cyl(P, x, y, z, r, h, mat, n=8):
    a = [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
    b = [(px, py, z + h) for px, py, _ in a]
    c = [(x + r * 0.7 * math.cos(2 * math.pi * k / n), y + r * 0.7 * math.sin(2 * math.pi * k / n), z + h + r * 0.3)
         for k in range(n)]
    loft(P, [a, b, c], mat)


def torus(P, cx, cy, z, R_, tube_r, mat, n=40, m=8, tube_h=None):
    th = tube_h or tube_r
    rings = []
    for i in range(n):
        a = 2 * math.pi * i / n
        ring = []
        for j in range(m):
            b = 2 * math.pi * j / m
            rr = R_ + tube_r * math.cos(b)
            ring.append((cx + rr * math.cos(a), cy + rr * math.sin(a), z + th * math.sin(b)))
        rings.append(ring)
    vr = [[P.v(p) for p in ring] for ring in rings]
    for i in range(n):
        a, b = vr[i], vr[(i + 1) % n]
        for k in range(m):
            j = (k + 1) % m
            P.f((a[k], a[j], b[j], b[k]), mat)


def hull(P, pts, mat):
    bm = P.bm
    verts = [bm.verts.new(p) for p in pts]
    res = bmesh.ops.convex_hull(bm, input=verts, use_existing_faces=False)
    junk = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    live = [v for v in verts if v.is_valid]
    faces = list({f for v in live for f in v.link_faces})
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(1), verts=live, edges=list({e for f in faces for e in f.edges}))
    for f in {f for v in live if v.is_valid for f in v.link_faces}:
        f.material_index = mat


def cbox(x0, x1, y0, y1, z0, z1, ch):
    pts = []
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            for z, sz in ((z0, 1), (z1, -1)):
                pts += [(x + sx * ch, y, z + sz * ch), (x, y + sy * ch, z + sz * ch), (x + sx * ch, y + sy * ch, z)]
    return pts


def strap(P, a, b, w, z0, z1, mat, ch=0.3):
    """A straight chamfered bar from a to b (x, y), w wide, z0..z1 (a raised brace or rib)."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy * w / 2, ux * w / 2
    out = [(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)]
    prism(P, out, z0, z1, mat, r=ch, chb=0.0, steps=1)


def flip(P):
    for v in P.bm.verts:
        v.co.x = 2 * AXIS + 1 - v.co.x
    bmesh.ops.reverse_faces(P.bm, faces=P.bm.faces[:])


def orient_islands(bm):
    """Each primitive is its own closed island (no shared verts yet): flip the ones whose signed
    volume is negative, so every face points out (recalc_face_normals gets confused once
    overlapping primitives are merged)."""
    bm.faces.index_update()
    seen = set()
    flips = 0
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        vol = 0.0
        for f in isl:
            p0 = f.verts[0].co
            for k in range(1, len(f.verts) - 1):
                vol += p0.dot(f.verts[k].co.cross(f.verts[k + 1].co)) / 6.0
        if vol < 0:
            bmesh.ops.reverse_faces(bm, faces=isl)
            flips += 1
    print(f"{NAME}: flipped {flips} islands")


def to_object(P, name, mats, coll, smooth_angle=34.0):
    bm = P.bm
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector(((x - 72) / 12, (28 - y) / 12, z / 12))
    orient_islands(bm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    return obj


# ----------------------------------------------------------------------------------------------
# Materials: (name, palette index, metallic, roughness, emission)
# ----------------------------------------------------------------------------------------------

SLOTS = [
    ("RED71", 71, 0.35, 0.42, 0),    # spine, housings, beams, elbow drums
    ("RED70", 70, 0.35, 0.42, 0),    # upper arms
    ("RED69", 69, 0.35, 0.45, 0),    # cheeks, shoulders, U frames, claws, upper bands, feet
    ("RED67", 67, 0.35, 0.48, 0),    # legs, brackets
    ("FLOOR", 1, 0.35, 0.6, 0),      # recess floor (the sprite's ink-dark gaps, index 1)
    ("INK", 1, 0.2, 0.6, 0),         # slot, claw rim, vents
    ("GREY5", 5, 0.6, 0.34, 0),      # gearbox, link pipes, cannon
    ("GREY4", 4, 0.6, 0.36, 0),      # hoses, canisters, visor, cradle
    ("GREY3", 3, 0.55, 0.4, 0),      # arm hoses
    ("STEM", 2, 0.5, 0.45, 0),       # visor stem
    ("ORB", 3, 0.0, 0.04, 0),        # dark glass orbs (glossy: the sprite's bright spot is a sheen)
    ("BED", 117, 0.0, 0.5, 2.2),     # exhaust beds
    ("VANE", 122, 0.0, 0.4, 3.5),    # hot vanes
    ("VANEHOT", 125, 0.0, 0.4, 4.5), # hottest vanes
    ("GLOW", 119, 0.0, 0.4, 3.0),    # eye lens (animated on the claw pieces)
    ("HOT", 125, 0.0, 0.4, 5.0),     # eye core (animated on the claw pieces)
    ("SOCKET", 113, 0.2, 0.5, 0.6),  # eye socket wall (animated on the claw pieces)
    ("RIM", 7, 0.65, 0.3, 0),        # bright steel collars, bolt heads, muzzle ring
]
SLOT_NAMES = [s[0] for s in SLOTS]
(RED71, RED70, RED69, RED67, FLOOR, INK, GREY5, GREY4, GREY3, STEM, ORB, BED, VANE, VANEHOT, GLOW, HOT,
 SOCKET, RIM) = range(len(SLOTS))


def materials(sprite):
    return [common.palette_material(sprite, i, f"{TAG}-{name.lower()}", metallic=met, roughness=rough,
                                    emission_strength=emit) for name, i, met, rough, emit in SLOTS]


def eye_materials(piece, sprite):
    """The claw's eye brightens: newsht-39 frames 39 -> 77 -> 79, newsht-49 49 -> 87 -> 85."""
    tag = f"{TAG}-eye"
    slots = {
        GLOW: common.palette_material(sprite, 119, tag, emission_strength=3.0,
                                      frames={77: 122, 79: 125, 85: 125, 87: 122}),
        HOT: common.palette_material(sprite, 125, tag, emission_strength=5.0,
                                     frames={77: 126, 79: 127, 85: 127, 87: 126}),
        SOCKET: common.palette_material(sprite, 113, tag, metallic=0.2, roughness=0.5, emission_strength=0.6,
                                        frames={77: 114, 79: 116, 85: 116, 87: 114}),
    }
    for slot, mat in slots.items():
        piece.data.materials[slot] = mat


# ----------------------------------------------------------------------------------------------
# One side (left-half coordinates; the right is built on its mirrored pixels and flipped)
# ----------------------------------------------------------------------------------------------

def centroid(pixels):
    return (sum(c for c, _ in pixels) / len(pixels) + 0.5, sum(r for _, r in pixels) / len(pixels) + 0.5)


def build_side(P):
    # --- the arm: a thick round upper arm (rows 19-39) out of the beam, with a raised spine strap
    # down its back, a cuff band and the elbow drum across its foot ---
    arm = pix("arm")
    ar = runs(arm, "y")
    tube(P, arm, "y", 6.0, lambda s: 5.6 if s > 22 else 5.6 - (22 - s) * 0.25, RED70, n=16, p=2.3,
         bands=[(24.2, 24.9, -0.25), (33.6, 35.2, 0.3)], band_mat=RED71, end_k=(0.75, 0.9), cap_ch=1.2)
    # spine strap down the arm's back (the sprite's lit rib between the grooves at col 10.5 / 12.5)
    zt = 6.0 + 5.6 - 0.15
    strap(P, (11.5, 25.4), (11.5, 33.3), 1.3, zt - 1.0, zt + 0.55, RED71, ch=0.35)
    for yb in (26.4, 32.3):
        cyl(P, 9.4, yb, zt - 0.6, 0.45, 0.75, RIM, n=6)
    # the beam from the shoulder into the arm's top, a steel collar where it meets the arm
    beam = pix("beam")
    tube(P, beam, "x", 6.4, 2.2, RED71, n=14, step=2.5, p=2.2, bands=[(16.0, 17.2, 0.3), (22.8, 23.6, -0.2)], band_mat=RIM,
         end_k=(0.95, 0.9), cap_ch=0.3)
    # elbow drum across the arm's foot (rows 36-39), its axis along x, steel caps
    elbow = pix("elbow")
    tube(P, elbow, "x", 5.6, lambda s: 4.4, RED71, n=16, p=2.0, step=2.0, bands=[(17.4, 18.4, -0.35)],
         end_k=(0.8, 0.82), cap_ch=0.8)
    # --- the claw: a round pod (rows 40-53) dipping where the eye looks out of its top ---
    claw = pix("claw") | pix("claw-rim") | pix("claw-eye") | pix("claw-vent")
    ex, ey = centroid(pix("claw-eye") or pix("claw-rim"))
    hz = pchip([40.0, 42.0, 43.4, 44.8, 49.6, 50.8, 53.0], [3.8, 4.6, 4.3, 2.8, 2.8, 4.1, 3.4])
    tube(P, claw, "y", 4.6, hz, RED69, n=18, p=2.1, bands=[(43.4, 44.0, -0.3), (50.2, 50.8, -0.25)],
         end_k=(0.85, 0.75), cap_ch=0.8)
    # a fin down the pod's outer flank (the lit ridge at cols 17-19)
    cr = runs(claw, "y")
    # the eye: a black bezel standing out of the dip, a socket wall that glows with the eye, the
    # lens at its floor and the hot core
    er = runs(pix("claw-eye"), "y")
    rex = (max(v[1] for v in er.values()) - min(v[0] for v in er.values())) / 2
    rey = (max(er) + 1 - min(er)) / 2
    rx, ry = rex + 1.0, rey + 1.0  # the black bezel round the lens (the sprite's ink rim)
    n = 28

    def ell(ax, ay, z):
        return [(ex + ax * math.cos(2 * math.pi * (k + 0.5) / n), ey + ay * math.sin(2 * math.pi * (k + 0.5) / n), z)
                for k in range(n)]
    rings = [ell(rx - 0.4, ry - 0.4, 3.0), ell(rx, ry, 3.6), ell(rx, ry, 8.1), ell(rx - 0.35, ry - 0.35, 8.6),
             ell(rex + 0.25, rey + 0.25, 8.6), ell(rex + 0.1, rey + 0.1, 8.25)]
    rings += [ell(rex - 0.05, rey - 0.05, 7.7), ell(rex - 0.2, rey - 0.2, 7.5),
              ell((rex - 0.2) * 0.6, (rey - 0.2) * 0.6, 8.05), [(ex, ey, 8.2)]]
    loft(P, rings, [INK, INK, INK, INK, INK, SOCKET, SOCKET, GLOW, GLOW], cap0=True, cap1=False)
    hot = [(c, r) for c, r in pix("claw-eye") if GRID[r][c if CUR_SIDE[0] == "L" else 2 * AXIS - c] >= 123]
    hx, hy = centroid(hot) if hot else (ex - 0.4, ey - 0.4)
    ellipsoid(P, hx, hy, 8.1, 0.9, 0.9, 0.3, HOT, seg=12, rings=6)
    # the vent on the pod's outer side: a dark louvred box
    vent = pix("claw-vent")
    if vent:
        vr = runs(vent, "y")
        y0, y1 = min(vr), max(vr) + 1
        x0 = min(v[0] for v in vr.values())
        x1 = max(v[1] for v in vr.values())
        hull(P, cbox(x0 + 0.2, x1 + 0.5, y0 + 0.2, y1 - 0.2, 1.0, 5.6, 0.35), INK)
        for k in range(3):
            yy = y0 + 1.0 + k * (y1 - y0 - 2.0) / 2
            hull(P, cbox(x0 + 0.1, x1 + 0.3, yy - 0.3, yy + 0.3, 4.6, 6.0, 0.15), GREY5)

    # --- grey works behind the arm's top: a ringed canister and a gearbox (rows 10-19) ---
    can = pix("canister")
    tube(P, can, "y", 8.4, 3.0, GREY4, n=12, step=2.0, p=2.0, zfloor=2.0,
         bands=[(12.6, 13.4, -0.35), (14.6, 15.4, -0.35), (17.6, 18.4, -0.35), (10.8, 11.4, 0.0)],
         end_k=(0.8, 0.9), cap_ch=0.6, inset=-0.1)
    gb = pix("gearbox")
    plates(P, gb, 1.0, 7.2, GREY5, r=0.7, chb=0.2, cuts=[((13, 14.5), (20, 14.5))], gap=0.4, depth=0.6)
    gr = runs(gb, "y")
    gx0 = min(v[0] for v in gr.values())
    gx1 = max(v[1] for v in gr.values())
    for yb in (12.0, 17.0):
        cyl(P, (gx0 + gx1) / 2 + 0.8, yb, 6.9, 0.55, 0.6, RIM, n=6)
    lp = pix("link-pipe")
    if lp:
        tube(P, lp, "x", 6.6, 1.6, GREY5, n=10, p=2.0, end_k=(1.0, 1.0), cap_ch=0.2,
             bands=[(21.0, 21.8, 0.25)], band_mat=RIM)
    # a round grey hose down the inside of the arm (rows 23-35), along its region's middle
    ah = pix("arm-hose")
    if ah:
        fld = Field(ah)
        path = centre_on(fld, [(21.6, 23.6), (20.3, 26.0), (19.0, 28.6), (18.0, 31.2), (17.4, 33.4), (17.2, 35.2)], 1.5)
        path = catmull(path, 3)
        rad = [max(0.6, min(1.9, fld(x, y) + 0.35)) for x, y in path]
        rad[0] *= 0.8
        rad[-1] *= 0.8
        pts3 = [(x, y, 4.2) for x, y in path]
        sweep(P, pts3, [(w, min(w, 1.7)) for w in rad], GREY3, n=10)
        for i in range(2, len(path) - 2, 2):  # ribs on the arm hose
            x, y = path[i]
            w = rad[i]
            a, b = path[i - 1], path[i + 1]
            sweep(P, [(a[0] * 0.2 + x * 0.8, a[1] * 0.2 + y * 0.8, 4.2), (b[0] * 0.2 + x * 0.8, b[1] * 0.2 + y * 0.8, 4.2)],
                  [(w + 0.14, min(w, 1.7) + 0.14)] * 2, GREY5, n=10)
        for t in (0.3, 0.7):
            i = int(len(path) * t)
            x, y = path[i]
            w = rad[i]
            a, b = path[i - 1], path[i + 1]
            sweep(P, [(a[0] * 0.25 + x * 0.75, a[1] * 0.25 + y * 0.75, 4.2), (b[0] * 0.25 + x * 0.75, b[1] * 0.25 + y * 0.75, 4.2)],
                  [(w + 0.25, min(w, 1.7) + 0.25)] * 2, RIM, n=10)

    # --- shoulder block (rows 13-23): plates split by panel lines, a raised diagonal brace ---
    sh = pix("shoulder")
    plates(P, sh, 0.5, 7.4, RED69, r=1.1, chb=0.3,
           cuts=[((20.0, 20.0), (44.0, 20.0)), ((28.5, 10.0), (28.5, 20.0))], gap=0.5, depth=0.9)
    strap(P, (30.5, 20.6), (37.6, 14.4), 1.2, 6.6, 8.4, RED71, ch=0.4)
    for bx, by in ((26.6, 15.0), (26.6, 18.6), (39.6, 21.6)):
        if inner_left(int(bx), int(by)):
            cyl(P, bx, by, 7.2, 0.45, 0.45, RIM, n=6)
    # strut under the shoulder and its foot
    leg = pix("leg")
    if leg:
        tube(P, leg, "y", 3.6, 1.9, RED67, n=10, step=2.0, p=2.0, end_k=(1.0, 0.95), cap_ch=0.2)
    foot = pix("foot")
    if foot:
        tube(P, foot, "x", 2.4, 1.6, RED69, n=10, step=2.0, p=2.4, end_k=(0.8, 0.8), cap_ch=0.4)
    # bracket under the cheek
    br = pix("bracket")
    if br:
        tube(P, br, "y", 3.2, 1.6, RED67, n=10, step=2.0, p=2.4, zfloor=0.5, end_k=(0.9, 0.85), cap_ch=0.4)

    # --- thick grey hose from the back of the body down to the shoulder (rows 6-13) ---
    hp = pix("hose")
    fld = Field(hp)
    path = centre_on(fld, [(44.1, 7.7), (41.9, 8.3), (39.6, 9.2), (37.4, 10.6), (35.8, 12.0), (35.0, 13.4)], 1.5)
    path = catmull(path, 3)
    rad = [max(1.0, min(3.3, fld(x, y) + 0.4)) for x, y in path]
    rad[0] *= 0.75
    zs = [6.8 + 0.4 * math.sin(math.pi * i / (len(path) - 1)) for i in range(len(path))]
    sweep(P, [(x, y, z) for (x, y), z in zip(path, zs)], [(w, min(w, 3.0)) for w in rad], GREY4, n=16)
    for i in range(2, len(path) - 2):  # corrugation ribs (visible from above and the sides)
        x, y = path[i]
        a, b = path[i - 1], path[i + 1]
        w = rad[i]
        if i % 2 == 0:
            sweep(P, [(a[0] * 0.2 + x * 0.8, a[1] * 0.2 + y * 0.8, zs[i]), (b[0] * 0.2 + x * 0.8, b[1] * 0.2 + y * 0.8, zs[i])],
                  [(w + 0.16, min(w, 3.0) + 0.16)] * 2, GREY5, n=16)
    for t in (0.12, 0.5, 0.88):
        i = max(1, min(len(path) - 2, int((len(path) - 1) * t)))
        x, y = path[i]
        a, b = path[i - 1], path[i + 1]
        w = rad[i]
        sweep(P, [(a[0] * 0.3 + x * 0.7, a[1] * 0.3 + y * 0.7, zs[i]), (b[0] * 0.3 + x * 0.7, b[1] * 0.3 + y * 0.7, zs[i])],
              [(w + 0.3, min(w, 3.0) + 0.3)] * 2, RIM, n=16)

    # --- upper band across the back (rows 8-12): a round tube, rounded at its outer end ---
    ub = pix("upper-band")
    tube(P, ub, "x", 6.0, 2.4, RED69, n=14, step=2.5, p=2.0, zfloor=0.5, end_k=(0.7, 1.0), cap_ch=1.0,
         bands=[(47.4, 48.2, -0.25), (54.4, 55.2, -0.25)])

    # --- cheek plates between the band and the orb's frame (rows 9-24) ---
    ck = pix("cheek")
    plates(P, ck, 0.5, 6.4, RED69, r=1.0, chb=0.3,
           cuts=[((50.5, 10.0), (50.5, 30.0)), ((38.0, 15.6), (66.0, 15.6))], gap=0.45, depth=0.8)
    for bx, by in ((41.2, 18.0), (47.0, 22.0), (53.0, 13.8)):
        if inner_left(int(bx), int(by)):
            cyl(P, bx, by, 6.2, 0.4, 0.4, RIM, n=6)

    # --- the U frame round the orb: rounded armour segments ---
    uf = pix("u-frame")
    plates(P, uf, 0.5, 2.6, RED69, r=0.5, chb=0.3)  # base flange on the frame's own outline
    fld = Field(uf)
    path = centre_on(fld, [(48.9, 20.6), (48.9, 25.0), (49.0, 30.0), (50.4, 34.4), (53.4, 36.4), (57.5, 37.0),
                           (61.5, 36.6), (64.0, 34.4), (64.9, 30.0), (64.9, 26.5), (64.8, 25.0)], 1.6)
    path = catmull(path, 2)
    wid = [max(1.8, fld(x, y) + 0.55) for x, y in path]
    wid = [sum(wid[max(0, i - 2):i + 3]) / len(wid[max(0, i - 2):i + 3]) for i in range(len(wid))]
    prof = []
    for k in range(16):
        t = 2 * math.pi * (k + 0.5) / 16
        c, s_ = math.cos(t), math.sin(t)
        prof.append((math.copysign(abs(c) ** (2 / 3.2), c), math.copysign(abs(s_) ** (2 / 3.2), s_)))
    L = [0.0]
    for a, b in zip(path, path[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    grooves = [0.27 * L[-1], 0.5 * L[-1], 0.73 * L[-1]]
    rings3, mats3 = [], []
    for i, ((x, y), w) in enumerate(zip(path, wid)):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        t = Vector((b[0] - a[0], b[1] - a[1], 0)).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        g = 1.0 - 0.09 * max([max(0.0, 1 - abs(L[i] - gl) / 0.5) for gl in grooves])
        k = g * (0.8 if i in (0, len(path) - 1) else 1.0)
        zc_, hz_ = 4.6, 3.4 * k
        ring3 = [Vector((x, y, zc_)) + side * (w * k * pu) + Vector((0, 0, hz_ * pv)) for pu, pv in prof]
        # the sprite's frame ends at row 40 (row 41 is its ink ring, which the outline shell stands in for)
        rings3.append([(v.x, min(v.y, 40.95), v.z) for v in ring3])
    loft(P, rings3, RED69, cap0=True, cap1=True)
    # the dark glass orb, on a steel bezel ring
    ox, oy, oz, orad = 59.5, 22.8, 6.2, 6.7
    ellipsoid(P, ox, oy, oz, orad, orad, orad, ORB, seg=24, rings=12, zfloor=0.4)
    torus(P, ox, oy, 2.9, 5.85, 0.75, RIM, n=32, m=6)
    # grey bezel ring where the sphere meets its mount (inside the sprite's orb outline)
    torus(P, ox, oy, 3.5, 5.7, 0.95, GREY5, n=40, m=8)
    # grey cradle (lip) under the orb
    cd = pix("cradle")
    if cd:
        plates(P, cd, 0.5, 2.8, GREY4, r=0.4, chb=0.2, min_px=3)
        bar = {(c, r) for c, r in cd if r >= 30}
        if bar:
            tube(P, bar, "x", 3.4, 1.7, GREY4, n=10, step=2.5, p=2.0, zfloor=0.5, end_k=(0.85, 0.85), cap_ch=0.4,
                 bands=[(55.6, 56.4, 0.25), (59.6, 60.4, 0.25)], band_mat=RIM)

    # --- exhaust on the back: a red housing round a sloping glowing bed with hot vanes ---
    hs = pix("exhaust-housing")
    plates(P, hs, 0.5, 8.2, RED71, r=0.9, chb=0.3, cuts=[((62.6, 5.0), (62.6, 13.0))], gap=0.45, depth=0.8)
    gl = pix("exhaust-glow")
    bed = lambda x, y: 2.4 + 0.38 * y  # noqa: E731
    for comp in components(gl):
        if len(comp) < 3:
            continue
        out = trace(comp)
        if poly_area(out) < 0:
            out = list(reversed(out))
        out = offset_poly(out, -0.15)
        loft(P, [[(x, y, 1.0) for x, y in out], [(x, y, bed(x, y)) for x, y in out]], BED)
        # the outlet's rear face: a dark louvred lip under the bed's back edge
        ys = min(y for _, y in out)
        xs = [x for x, y in out if y < ys + 1.2]
        if xs:
            hull(P, cbox(min(xs) + 0.4, max(xs) - 0.4, ys - 0.05, ys + 0.9, 1.1, bed(0, ys) - 0.3, 0.15), INK)
    # the sprite's hot streaks as lit vanes across the bed: one bar along each streak (8-connected
    # groups of its brightest pixels), the hottest ones in the brighter colour
    def val(c, r):
        return GRID[r][c if CUR_SIDE[0] == "L" else 2 * AXIS - c]
    hotpx = {(c, r) for c, r in gl if val(c, r) >= 120}
    while hotpx:
        st = [hotpx.pop()]
        grp = set(st)
        while st:
            c, r = st.pop()
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    q = (c + dc, r + dr)
                    if q in hotpx:
                        hotpx.discard(q)
                        grp.add(q)
                        st.append(q)
        pts = [(c + 0.5, r + 0.5) for c, r in grp]
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        if len(pts) == 1:
            ux, uy, half = 0.0, 1.0, 0.45
        else:
            sxx = sum((p[0] - mx) ** 2 for p in pts)
            syy = sum((p[1] - my) ** 2 for p in pts)
            sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
            ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
            ux, uy = math.cos(ang), math.sin(ang)
            proj = [(p[0] - mx) * ux + (p[1] - my) * uy for p in pts]
            half = max(0.45, (max(proj) - min(proj)) / 2 + 0.4)
        m = VANEHOT if max(val(c, r) for c, r in grp) >= 124 else VANE
        a, b = (mx - ux * half, my - uy * half), (mx + ux * half, my + uy * half)
        za, zb = bed(*a), bed(*b)
        zt = max(za, zb) + 0.25
        strap(P, a, b, 0.85, min(za, zb) - 0.6, zt, m, ch=0.2)

    # --- the recess floor: the sprite's dark gaps between the parts ---


def build_centre(P):
    # recess floor: every ink pixel inside the mask, grown 1 px under the parts round it
    rec = cpix("recess")
    grown = set(rec)
    for c, r in rec:
        for q in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if 0 <= q[0] < W and 0 <= q[1] < H and INNER[q[1]][q[0]]:
                grown.add(q)
    plates(P, grown, 0.3, 2.0, FLOOR, r=0.0, chb=0.0, min_px=1, tol=0.6)
    # raised spine between the exhausts (rows 4-12)
    sp = cpix("spine")
    plates(P, sp, 0.5, 9.0, RED71, r=1.4, chb=0.3, steps=3, cuts=[((60.0, 8.5), (84.0, 8.5))], gap=0.45, depth=0.8)
    strap(P, (AXIS + 0.5, 5.8), (AXIS + 0.5, 8.0), 1.4, 8.4, 9.5, RED69, ch=0.4)
    # dark slot under the spine's front edge
    sl = cpix("slot")
    plates(P, sl, 0.5, 3.0, INK, r=0.3, chb=0.15, min_px=1)
    # the grey visor bar between the orbs, on its stem
    vs = cpix("visor")
    tube(P, vs, "x", 7.6, 2.0, GREY4, n=14, p=2.4, zfloor=3.0, end_k=(0.85, 0.85), cap_ch=0.5,
         bands=[(AXIS - 1.5, AXIS + 2.5, 0.25)], band_mat=RIM)
    st = cpix("stem")
    plates(P, st, 0.5, 4.6, STEM, r=0.5, chb=0.2, min_px=1)
    # the cannon pointing down the screen, a steel muzzle ring and a dark bore
    cn = cpix("cannon")
    tube(P, cn, "y", 4.0, 3.4, GREY5, n=16, p=2.0, zfloor=0.5, end_k=(0.9, 0.95), cap_ch=0.3,
         bands=[(29.6, 30.4, -0.3), (33.4, 34.6, 0.3)], band_mat=RIM, bore=(INK, 0.55, 1.2))


def build(sprite, coll):
    mats = materials(sprite)
    P = Part()
    CUR_SIDE[0] = "L"
    build_side(P)
    Rt = Part()
    CUR_SIDE[0] = "R"
    try:
        build_side(Rt)
    finally:
        CUR_SIDE[0] = "L"
    flip(Rt)
    me = bpy.data.meshes.new("right_tmp")
    Rt.bm.to_mesh(me)
    Rt.bm.free()
    P.bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    build_centre(P)
    return to_object(P, NAME, mats, coll), mats


# ----------------------------------------------------------------------------------------------
# Finishing (as assembly-newsh4-124.py): cull hidden faces, split, bake, outline shells, export
# ----------------------------------------------------------------------------------------------

def cull_hidden(obj, grid=3, ndirs=40):
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
    eps = 2e-4
    dead = []
    for f in bm.faces:
        n = f.normal
        vs = [v.co for v in f.verts]
        c = f.calc_center_median()
        pts = [c]
        if len(vs) == 4:
            for i in range(grid):
                for j in range(grid):
                    u, v = (i + 0.5) / grid, (j + 0.5) / grid
                    pts.append(vs[0].lerp(vs[1], u).lerp(vs[3].lerp(vs[2], u), v))
        else:
            for vco in vs:
                for t in (0.35, 0.7, 0.92):
                    pts.append(c.lerp(vco, t))
        cand = [d for d in dirs if d.dot(n) > 0.05]
        seen = False
        for p in pts:
            o = p + n * eps
            for d in cand:
                if tree.ray_cast(o, d, 50.0)[0] is None:
                    seen = True
                    break
            if seen:
                break
        if not seen:
            dead.append(f)
    print(f"{NAME}: culled {len(dead)} hidden faces of {len(bm.faces)}")
    bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(me)
    bm.free()


def _cycles(samples):
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
        print(f"{NAME}: no GPU bake", err)


def bake_piece(obj, out_dir, size=512, samples=48):
    """AO/edge colour multiplier + roughness/metallic bake (usp_talon.bake_maps' recipe; no concept
    projection), wired into the piece's own copies of its palette materials; emissive slots plain."""
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    used = sorted({p.material_index for p in me.polygons})
    for k in used:
        m = me.materials[k]
        c = m.copy()
        c.name = f"{m.name}-{obj.name}"
        me.materials[k] = c
    mats = [me.materials[k] for k in used]
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
    rm_img.colorspace_settings.name = "Non-Color"
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

        def math_(op, a, bb=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, bb)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    nt.links.new(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 16
        ao_s.inputs["Distance"].default_value = 0.04
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 16
        ao_l.inputs["Distance"].default_value = 0.25
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
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
            v = math_("MINIMUM", math_("ADD", math_("ADD", 0.48, math_("MULTIPLY", occl, 0.62)),
                                       math_("MULTIPLY", edge, 0.2)), 1.0)
            nt.links.new(v, em.inputs["Color"])
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
        bpy.ops.object.bake(type="EMIT", margin=4, use_clear=True)
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
    for m in mats:
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        if bsdf.inputs["Emission Strength"].default_value > 0:
            continue
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


def whole_shell(obj, coll, voxel=0.016, faces=7000, smooth=4):
    """common.outline_shell for the whole machine (D51), keeping every outer island."""
    me = obj.data.copy()
    me.materials.clear()
    shell = bpy.data.objects.new(f"{obj.name}_outline", me)
    coll.objects.link(shell)
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
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

    def volume(isl):
        ids = {v.index for v in isl}
        fs = {f for v in isl for f in v.link_faces}
        vol = 0.0
        for f in fs:
            if f.verts[0].index not in ids:
                continue
            p0 = f.verts[0].co
            for k in range(1, len(f.verts) - 1):
                vol += p0.dot(f.verts[k].co.cross(f.verts[k + 1].co)) / 6.0
        return vol
    drop = set()
    for isl in islands:
        if len(isl) < 12 or volume(isl) < 1e-4:
            drop.update(v.index for v in isl)
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
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces")
    return shell


def split_open(obj, layout, coll, suffix):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co,
                                   plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + suffix)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(name + suffix, me)
        coll.objects.link(o)
        out[name] = o
    return out


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    sprite = {"name": NAME, "colors": COLOURS}
    obj, mats = build(sprite, coll)
    bpy.context.view_layer.update()
    shell = whole_shell(obj, coll)
    cull_hidden(obj)
    obj.data.calc_loop_triangles()
    big = sorted((len(pg.vertices) for pg in obj.data.polygons), reverse=True)[:8]
    print(f"{NAME}: whole after cull {len(obj.data.loop_triangles)} tris, biggest ngons {big}")
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in LAYOUT if e["model"] in PIECES]
    shells = split_open(shell, layout, coll, "_outline")
    shell.hide_render = True
    outline_mat = bpy.data.materials.get("outline_shell") or common.material("outline_shell", (0.0, 0.0, 0.0),
                                                                             roughness=1.0)
    for s in shells.values():
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        s.hide_render = True
    pieces = common.split_assembly(obj, layout)
    obj.hide_render = True
    for name in ("newsht-39", "newsht-49"):
        eye_materials(pieces[name], sprite)
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="nsht39b_bake_")
        _cycles(48)
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        for name, _, _ in layout:
            bake_piece(pieces[name], tmp)
        for o in pieces.values():
            o.location = (0, 0, 0)
        fmt = "WEBP"
    for p in pieces.values():
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50
    tri = 0
    for name, _, _ in layout:
        pieces[name].data.calc_loop_triangles()
        tri += len(pieces[name].data.loop_triangles)
    print(f"{NAME}: triangles (pieces, no shells) {tri}")
    if "--no-export" not in argv:
        for name, _, _ in layout:
            data = common.load_sprite(ROOT, name)
            sprites = json.loads(json.dumps(data["sprites"]))
            for sp in sprites:  # cracked frames share the intact piece's silhouette (D79)
                sp["frames"] = sp["frames"] + [f for f in CRACKED.get(name, []) if f not in sp["frames"]]
            extra = [shells[name]] if len(shells[name].data.polygons) else []
            common.export_sprite_model(ROOT, [pieces[name]] + extra, f"enemies/{name}", sprites,
                                       image_format=fmt)
    if "--design-out" in argv:
        out = Path(argv[argv.index("--design-out") + 1])
        export = []
        for name, cx, cy in layout:
            for o in [pieces[name]] + ([shells[name]] if len(shells[name].data.polygons) else []):
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        common.export_glb(export, out, image_format=fmt)
        for o in export:
            o.location = (0, 0, 0)
        print(f"design export {out}")


if __name__ == "__main__":
    main()
