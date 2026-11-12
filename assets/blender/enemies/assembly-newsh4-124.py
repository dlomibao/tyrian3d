"""Bronze stag-beetle boss (newsh4.shp, 20 pieces, 120 x 112 px): a hard-surface 3D version of its sprite.

Seen in episode 1 (levels 1.28, 1.30, 1.36; the level-1 boss, enemy types 46-65). The whole
machine is built once in sprite pixels, cut into its twenty 24 x 28 px pieces
(common.split_assembly, sprite.json `assemblyLayout`) and, for the eye piece (newsh4-1), given
three animated eye models: closed (frames 1, 3), open and red (5, 7, 39), glowing (41, 43, 45).

The ORIGINAL SPRITE decides the plan (D52): every part's outline is the sprite's own mask inside
that part's region (a generous hand-drawn polygon), traced on the pixel edges and smoothed
(stair midpoints, Douglas-Peucker), so the top view follows the sprite row by row; round parts
(cables, claws, hooks) take their width from the region's distance field along a centreline;
the tower's lofts take each row's half width from the mask. Heights and sections are designed
(cross-sections first):

    part            rows       z (px)        section
    hull / belly    16-73      -5 .. 3.5     chamfered octagon, closed keel
    rear cap        5.5-13.5   ..16          squircle drum, domed rear end, tan crest + lamp
    brim flange     13.5-18.5  ..17          machined ring, chamfered faces, bolts
    drum            18.5-38    ..15 -> 13    squircle drum, axis rising to the rear, lengthwise
                                             steel straps, recessed ladder hatch, red beacon
    collar / neck   33-45      ..10          red ring, steel neck
    eye socket      44.5-54.5  ..8           black housing ring round the eye
    pod             54-70      ..11          red armour cheeks round a slot, vents cut in
    stinger         72.5-91.5  ..12          dome, raised red stripe, horns, fangs
    wings           20-53      -1.5 .. 3.5   armour plate on a core, drooping to the tip,
                                             lit leading-edge spar, panel seam, wingtip blocks
    pylons          3-38       -1 .. 9       ram (horizontal cylinder) + armour block, emblem
    cables          8-23       ..8           three-pipe bundle arcing to the wingtip, clamps
    chevron         43-72      1 .. 8.5      V armour plate, chamfered, lit outer bevel
    shoulders       56-86      -2.5 .. 7     blocks with recessed framed red windows, wrist
    claws / hooks   73-107     tusks         hexagonal blade section / round rod, tapering

Colours: palette materials (pal_<index>) per part (wing, ridge, bands, chevron, brim, drum, grey ring
and centre column, collar, pod, stripe, stinger bands...), each the median index of the sprite pixels
the part covers in the top view, the darkest shading and brightest sheen left out (SLOTS); satin
metal. The drum is the sprite's: a grey dome, a bronze brim, a dark band, a grey ring, then the
bronze barrel with steel straps and a grey centre column with bronze crossbars. The stinger is dark
grey above, a bronze band and a dark bronze lip below, with the red stripe. Twin thrusters and
strapped service panels break up the rear face.

No concept projection bake (maps.json says "bake": "model", so texture_bake.py skips it, D50-D53):
unless --no-bake, each piece gets its own baked occlusion/edge colour multiplier and
roughness/metallic map (the other pieces in place round it), multiplied into its own copies of the
palette materials. Faces no outside ray reaches are culled. Underside: closed, plain.

Export as before: twenty pieces cut from the whole machine (common.split_assembly), each to
enemies/<piece> with its spriteModels entry, the eye piece as three models (newsh4-1 frames 1, 3;
-f2 frames 5, 7, 39; -f3 frames 41, 43, 45), and an outline shell per piece (D51: one shell of the
whole machine, cut open at the piece boxes so no seams are outlined).

blender -b --factory-startup --python assets/blender/enemies/assembly-newsh4-124.py -- \
    [--no-bake] [--no-export] [--design-out whole.glb]
  --design-out  also writes one review .glb with every piece back in assembly space, the eye
                models' frame parts (custom property tyrian_model) and the outline shells.
"""

import bisect
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

GAME_ROOT = common.repo_root(__file__)
ROOT = GAME_ROOT
NAME = "assembly-newsh4-124"
PIECES = ["newsh4-124", "newsh4-126", "newsh4-128", "newsh4-86", "newsh4-88", "newsh4-90", "newsh4-130",
          "newsh4-1", "newsh4-48", "newsh4-50", "newsh4-132", "newsh4-92", "newsh4-94", "newsh4-54",
          "newsh4-56", "newsh4-10", "newsh4-12", "newsh4-14", "newsh4-16", "newsh4-18"]
CX0, CY0 = 185, 24
EYE = "newsh4-1"
EYE_MODELS = [("newsh4-1", [1, 3]), ("newsh4-1-f2", [5, 7, 39]), ("newsh4-1-f3", [41, 43, 45])]
TAG = "nsh4"
# Damaged frames that show the same picture as the normal one (280 = 128; 242 = 90 but for five
# pixels of one edge): drawn with the normal model. The other damaged frames have models of their
# own (assembly-newsh4-124-damaged.py).
EXTRA_FRAMES = {"newsh4-128": [280], "newsh4-90": [242]}
EX, EY, EZ = 60.5, 51.0, 7.4  # the eye's centre in its socket (px)
AX = 60.5  # mirror axis (centre of pixel column 60), in pixel-edge x
W, H = 120, 112
ZRAM = 14.4  # the pylon rams' axis height (px)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ----------------------------------------------------------------------------------------------
# The sprite
# ----------------------------------------------------------------------------------------------


def load_assembly():
    """The whole object's palette indices (H x W, -1 transparent) and the merged colours."""
    lay = json.loads((GAME_ROOT / "reference/models/newsh4-124/sprite.json").read_text())["assemblyLayout"]
    grid = [[-1] * W for _ in range(H)]
    colours = {}
    for e in lay:
        d = common.load_sprite(GAME_ROOT, e["model"])
        colours.update(d["colors"])
        fi = int(e["frame"].split("|")[-1])
        fr = next(f for f in d["frames"] if f["index"] == fi)
        x0, y0 = e["cx"] - CX0 + 48, e["cy"] - CY0 + 42
        for r, row in enumerate(fr["pixels"]):
            for c, v in enumerate(row):
                if v >= 0:
                    grid[y0 + r][x0 + c] = v
    return grid, colours, lay


GRID, COLOURS, LAYOUT = load_assembly()


def masked(c, r):
    return 0 <= c < W and 0 <= r < H and GRID[r][c] >= 0


def inside(poly, x, y):
    n, hit = len(poly), False
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                hit = not hit
    return hit


def region(poly):
    """The sprite's pixels whose centres lie in `poly` (pixel-edge coordinates)."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    out = set()
    for r in range(max(0, int(min(ys)) - 1), min(H, int(max(ys)) + 2)):
        for c in range(max(0, int(min(xs)) - 1), min(W, int(max(xs)) + 2)):
            if masked(c, r) and inside(poly, c + 0.5, r + 0.5):
                out.add((c, r))
    return out


def trace(pixels, tol=0.3):
    """The outer boundary of a pixel set as a smooth polygon: the pixel-edge contour, its unit
    edges replaced by their midpoints (1-px stairs become 45-degree lines), Douglas-Peucker."""
    edges = {}
    for c, r in pixels:
        # clockwise in screen (x right, y down) == counter-clockwise in Blender (y up)
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
        prev_dir = None
        while True:
            outs = edges[cur]
            if len(outs) > 1 and prev_dir is not None:
                # turn right first (keeps diagonal touches apart)
                def turn(o):
                    d = (o[0] - cur[0], o[1] - cur[1])
                    return prev_dir[0] * d[1] - prev_dir[1] * d[0]
                outs.sort(key=turn, reverse=True)
            nxt = outs.pop(0)
            if not outs:
                del edges[cur]
            prev_dir = (nxt[0] - cur[0], nxt[1] - cur[1])
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
    """Douglas-Peucker on a closed polygon."""
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
    # split at the two farthest points
    i0 = 0
    i1 = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    a = dp(pts[i0:i1 + 1])
    b = dp(pts[i1:] + [pts[0]])
    return a[:-1] + b[:-1]


def row_extent(pixels, r):
    cs = [c for c, rr in pixels if rr == r]
    return (min(cs), max(cs) + 1) if cs else None


class Field:
    """Distance (px) from a point inside a pixel set to its edge, on a 4x subgrid."""

    def __init__(self, pixels):
        import numpy as np
        self.np = np
        cs = [c for c, _ in pixels]
        rs = [r for _, r in pixels]
        c0, c1, r0, r1 = min(cs) - 2, max(cs) + 3, min(rs) - 2, max(rs) + 3
        pts = []
        for r in range(r0, r1):
            for c in range(c0, c1):
                if (c, r) not in pixels:
                    for i in range(4):
                        for j in range(4):
                            pts.append((c + (i + 0.5) / 4, r + (j + 0.5) / 4))
        self.out = np.array(pts)

    def __call__(self, x, y):
        d = self.np.sqrt(((self.out - (x, y)) ** 2).sum(axis=1)).min()
        return max(0.0, d - 0.125)


def centre_on(field, path, search=2.0):
    """Move each path point along the path's normal to the field's ridge (the region's middle)."""
    out = []
    for i, (x, y) in enumerate(path):
        a, b = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(tx, ty) or 1
        nx, ny = -ty / ln, tx / ln
        best = max((field(x + nx * s, y + ny * s), s) for s in [k * 0.125 - search for k in range(int(search * 16) + 1)])
        out.append((x + nx * best[1], y + ny * best[1]))
    return out


# ----------------------------------------------------------------------------------------------
# Curves
# ----------------------------------------------------------------------------------------------

def pchip(xs, ys):
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


def frange(a, b, step):
    n = max(1, int(math.ceil((b - a) / step - 1e-9)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def catmull(pts, per=4):
    """A smooth path through 2D/3D points (Catmull-Rom), `per` samples per span."""
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


def clip(poly, a, b, c):
    """Sutherland-Hodgman: the part of `poly` where a*x + b*y + c >= 0."""
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


def line_through(p, q, keep, off=0.0):
    """(a, b, c) of the line p-q, signed so `keep` is on the positive side, shifted by `off` px."""
    a, b = q[1] - p[1], -(q[0] - p[0])
    ln = math.hypot(a, b)
    a, b = a / ln, b / ln
    c = -(a * p[0] + b * p[1])
    if a * keep[0] + b * keep[1] + c < 0:
        a, b, c = -a, -b, -c
    return a, b, c - off


def offset_poly(poly, d):
    """Inset (d > 0) a polygon by moving each vertex along its miter."""
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    s = 1 if area > 0 else -1
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
        cos = max(0.4, mx * n2[0] + my * n2[1])
        out.append((p1[0] + mx * d / cos, p1[1] + my * d / cos))
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


def prism(P, outline, z0, z1, mat, ch=0.6, chb=0.25, tilt=None, side_mat=None):
    """A plate over `outline` (x, y px) from z0 to z1 (+ tilt(x, y)), top edges chamfered `ch`,
    bottom edges `chb` (45 degrees). z0 / z1 may be functions of (x, y) (a tapered plate)."""
    pts = outline
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    if area < 0:
        pts = list(reversed(pts))
    tz = (lambda x, y: tilt(x, y)) if tilt else (lambda x, y: 0.0)
    Z0 = z0 if callable(z0) else (lambda x, y, v=z0: v)
    Z1 = z1 if callable(z1) else (lambda x, y, v=z1: v)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    th = Z1(cx, cy) - Z0(cx, cy)
    ch = min(ch, th * 0.45)
    chb = min(chb, th * 0.3)
    inner_t = offset_poly(pts, ch) if ch > 0 else pts
    inner_b = offset_poly(pts, chb) if chb > 0 else pts
    levels = []  # (poly, base function, offset)
    if chb > 0:
        levels.append((inner_b, Z0, 0.0))
        levels.append((pts, Z0, chb))
    else:
        levels.append((pts, Z0, 0.0))
    if ch > 0:
        levels.append((pts, Z1, -ch))
        levels.append((inner_t, Z1, 0.0))
    else:
        levels.append((pts, Z1, 0.0))
    rings = []
    for poly, base, off in levels:
        rings.append([P.v((x, y, base(rx, ry) + off + tz(rx, ry))) for (x, y), (rx, ry) in zip(poly, pts)])
    sm = side_mat if side_mat is not None else mat
    for k, (a, b) in enumerate(zip(rings, rings[1:])):
        for i in range(n):
            j = (i + 1) % n
            P.f((a[i], a[j], b[j], b[i]), mat if (k == len(rings) - 2 and ch > 0) else sm)
    P.f(list(reversed(rings[0])), sm)
    P.f(rings[-1], mat)


def cup(P, cx, cy, rx, ry, rim, z0, z1, zf, mat, n=28, ch=0.35, floor_mat=None):
    """A closed bezel: outer wall z0..z1 (chamfered), a rim `rim` px wide, an inner wall down to a
    floor at zf (a socket, a well)."""
    def ell(ax, ay, z):
        return [(cx + ax * math.cos(2 * math.pi * (k + 0.5) / n), cy + ay * math.sin(2 * math.pi * (k + 0.5) / n), z)
                for k in range(n)]
    rings = [ell(rx - 0.3, ry - 0.3, z0), ell(rx, ry, z0 + 0.3), ell(rx, ry, z1 - ch), ell(rx - ch, ry - ch, z1),
             ell(rx - rim, ry - rim, z1), ell(rx - rim, ry - rim, zf), [(cx, cy, zf)]]
    fm = floor_mat if floor_mat is not None else mat
    loft(P, rings, [mat, mat, mat, mat, mat, fm], cap0=True, cap1=False)


def sec_loop(cx, y, hw, zc, hz, n=24, p=2.0, zfloor=None, zcap=None):
    """A superellipse section (|dx/hw|^p + |dz/hz|^p = 1) across x at row y."""
    pts = []
    for k in range(n):
        t = 2 * math.pi * (k + 0.5) / n
        c, s = math.cos(t), math.sin(t)
        x = cx + hw * math.copysign(abs(c) ** (2 / p), c)
        z = zc + hz * math.copysign(abs(s) ** (2 / p), s)
        if zfloor is not None:
            z = max(z, zfloor)
        if zcap is not None:
            z = min(z, zcap)
        pts.append((x, y, z))
    return pts


def loft(P, rings, mats, cap0=True, cap1=True):
    """Rings of equal count (or a single point) in order; mats per span (or one)."""
    if not isinstance(mats, (list, tuple)):
        mats = [mats] * (len(rings) - 1)
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


def sweep(P, path, radii, mat, profile=None, n=8, up=(0, 0, 1), cap=True):
    """A tube along a 3D path (px); radii[i] = (half width, half height) at each point; a zero
    radius closes to a point. `profile` is a list of unit (u, v) points (u across, v up)."""
    if profile is None:
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
    loft(P, rings, mat, cap0=cap, cap1=cap)


def hexblade(keel=0.55):
    """A blade section: flat-ish belly, chamfered flanks and a raised keel (u across, v up)."""
    pts = [(1.0, -0.15), (0.75, 0.45), (0.0, 1.0), (-0.75, 0.45), (-1.0, -0.15), (-0.55, -0.85), (0.55, -0.85)]
    out = []  # one Chaikin pass: rounded corners that shade smooth (no flat facets on the blades)
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        out += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
    k = 1.0 / max(abs(u) for u, _ in out)  # keep the full width (the top view)
    return [(u * k, v) for u, v in out][::-1]


def ellipsoid(P, x, y, z, rx, ry, rz, mat, seg=16, rings=8, zfloor=None):
    res = bmesh.ops.create_uvsphere(P.bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in res["verts"]:
        zz = z + v.co.z * rz
        if zfloor is not None:
            zz = max(zz, zfloor)
        v.co = Vector((x + v.co.x * rx, y + v.co.y * ry, zz))
    for f in {f for v in res["verts"] for f in v.link_faces}:
        f.material_index = mat


def cyl(P, x, y, z, r, h, mat, n=8, axis="z"):
    """A short cylinder (bolt head, lens, pin): centre of its base at (x, y, z)."""
    if axis == "z":
        a = [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
        b = [(px, py, z + h) for px, py, _ in a]
    else:  # along -y (pointing toward the front / bottom of the sprite)
        a = [(x + r * math.cos(2 * math.pi * k / n), y, z + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        b = [(px, y + h, pz) for px, _, pz in a]
    loft(P, [a, b], mat)


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


def mirror(P):
    """Add the mirror image (about the axis) of everything built so far."""
    bm = P.bm
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    dup = bmesh.ops.duplicate(bm, geom=geom)["geom"]
    for v in (e for e in dup if isinstance(e, bmesh.types.BMVert)):
        v.co.x = 2 * AX - v.co.x
    bmesh.ops.reverse_faces(bm, faces=[e for e in dup if isinstance(e, bmesh.types.BMFace)])


def to_object(P, name, mats, coll, smooth_angle=32.0):
    bm = P.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    for v in bm.verts:
        x, y, z = v.co
        v.co = Vector(((x - 60) / 12, (56 - y) / 12, z / 12))
    bmesh.ops.reverse_faces(bm, faces=bm.faces)  # the y flip mirrored the winding
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
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
# Materials
# ----------------------------------------------------------------------------------------------

# Material slots: (name, palette index, metallic, roughness, emission). Each index is the median of
# the sprite pixels the part covers in the top view, the darkest shading and the brightest sheen
# left out (tools: top ortho id pass vs the sprite). Satin metal (D53): painted bronze plates,
# machined steel; nothing mirror-like.
SLOTS = [
    ("DGREY", 5, 0.35, 0.5, 0),      # hull, dark plates
    ("GREY", 6, 0.4, 0.42, 0),       # pylons, shoulders, wrists
    ("LGREY", 7, 0.45, 0.36, 0),     # posts, straps, frames, rungs
    ("BLACK", 4, 0.2, 0.7, 0),       # recesses, socket
    ("WING", 22, 0.3, 0.45, 0),      # wing plates
    ("CHEV", 24, 0.38, 0.4, 0),     # the chevron (yoke)
    ("LTAN", 28, 0.35, 0.36, 0),     # crest
    ("BROWN", 164, 0.25, 0.55, 0),   # emblems, bands
    ("RED", 70, 0.25, 0.45, 0),      # red armour (wingtips, panels, pod)
    ("PINK", 72, 0.25, 0.4, 0),      # collar
    ("CLAW", 166, 0.2, 0.5, 0),      # horn claws
    ("LAMP", 79, 0.0, 0.3, 2.5),     # pink lights
    ("STEEL", 6, 0.55, 0.3, 0),      # cap, neck, collars
    ("WIN", 71, 0.25, 0.4, 0),       # red windows
    ("DRUM", 23, 0.3, 0.48, 0),      # tan drum body
    ("VENT", 20, 0.25, 0.6, 0),      # dark tan vent floors
    ("HOOK", 6, 0.45, 0.4, 0),       # grey hook rods
    ("STINGLOW", 163, 0.3, 0.5, 0),  # stinger lower lip (dark bronze)
    ("RIDGE", 22, 0.32, 0.4, 0),     # wing leading-edge spar
    ("WBAND", 22, 0.28, 0.5, 0),     # darker bronze bands across the wings
    ("BRIM", 25, 0.32, 0.42, 0),     # brim flange round the dome
    ("DRUMG", 6, 0.45, 0.38, 0),     # grey ring under the band, the drum's centre column
    ("STRIPE", 73, 0.25, 0.42, 0),   # red stripe down the stinger
    ("STING", 6, 0.45, 0.36, 0),     # stinger dome (dark grey)
    ("STINGMID", 22, 0.3, 0.45, 0),  # stinger's bronze band under the grey
    ("BLADE", 26, 0.32, 0.42, 0),    # tan blades under the shoulders
    ("PODRED", 72, 0.25, 0.45, 0),   # the pod's cheeks
    ("NOZZLE", 3, 0.5, 0.4, 0),      # thruster shrouds
    ("FLAME", 122, 0.0, 0.4, 1.6),   # thruster throats (a dim orange glow)
    ("CABLE", 22, 0.35, 0.45, 0),    # cable bundle
    ("DOME", 7, 0.5, 0.34, 0),       # the rear dome cap (the sprite's mid grey 7-9)
    ("CHEVL", 24, 0.45, 0.34, 0),      # the chevron's lit inner crease (the sprite's 27 line)
    ("LENS", 79, 0.0, 0.35, 0.7),    # flush pink lens on the dome crest (the sprite's 79 pair)
]
SLOT_NAMES = [s[0] for s in SLOTS]
(DGREY, GREY, LGREY, BLACK, WING, CHEV, LTAN, BROWN, RED, PINK, CLAW, LAMP, STEEL, WIN, DRUM, VENT, HOOK,
 DBROWN, RIDGE, WBAND, BRIM, DRUMG, STRIPE, STING, STINGMID, BLADE, PODRED, NOZZLE, FLAME, CABLE, DOME, CHEVL,
 LENS) = range(len(SLOTS))
N_MATS = len(SLOTS)


def materials(sprite):
    out = []
    for name, i, met, rough, emit in SLOTS:
        out.append(common.palette_material(sprite, i, f"{TAG}-{name.lower()}", metallic=met, roughness=rough,
                                           emission_strength=emit))
    return out


# ----------------------------------------------------------------------------------------------
# Regions (left half; pixel-edge polygons, generous: the sprite's mask decides the outline)
# ----------------------------------------------------------------------------------------------

R_WING = [(3.5, 21.5), (10, 21.5), (36.5, 33.5), (41.5, 33.5), (41.5, 38.5), (33.0, 38.5), (33.0, 53), (28, 53),
          (3.5, 38.5)]
R_TIP_RED = [(4.5, 25.5), (10.5, 25.5), (10.5, 37.5), (4.5, 37.5)]
R_TIP_GREY = [(10.0, 28.5), (16.0, 28.5), (16.0, 38.5), (10.0, 38.5)]
R_POST = [(18.5, 2.5), (26.5, 2.5), (26.5, 20.0), (18.5, 20.0)]
R_PYLON = [(26.5, 4.0), (44.6, 10.0), (44.6, 21.5), (43.0, 21.5), (43.0, 38.5), (41.5, 38.5), (41.5, 33.5),
           (37.5, 33.5), (22.0, 19.5), (22.0, 16.5), (26.5, 16.5)]
R_CABLE = [(3.0, 12), (13, 7.5), (20.5, 7.5), (20.5, 11.2), (13.5, 11.5), (9.8, 14.3), (8.8, 17), (8.6, 21.5),
           (8.0, 23.5), (3.0, 23.5)]
R_REDPANEL = [(36.5, 38.6), (44, 38.6), (54, 40.5), (54, 44.2), (36.5, 44.2)]
R_CHEV = [(58, 43.5), (46.5, 43.5), (46, 44.5), (36, 55.5), (34.5, 57.5), (30.5, 58.5), (30.5, 61), (32.5, 62.5),
          (34.5, 66.5), (36.3, 73.0), (41.7, 73.0), (43.6, 66), (43.6, 60), (44.5, 56), (46.5, 53), (49.5, 50),
          (56.0, 47.6), (58, 47.2)]
R_SHOULDER = [(13.5, 56.5), (36.0, 56.5), (37.0, 72.6), (24.5, 72.6), (24.5, 70.5), (13.5, 70.5)]
R_FOREARM = [(14.5, 69.5), (24.8, 69.5), (24.8, 80.5), (14.5, 80.5)]
R_BLADE = [(23.8, 67.6), (29.2, 67.6), (29.2, 72.8), (27.4, 75.8), (23.8, 76.4)]
R_WRIST = [(15.5, 78.5), (24.5, 78.5), (24.5, 87.0), (15.5, 87.0)]
R_CLAW = [(15.5, 84.0), (24.5, 84.0), (24.5, 93.0), (39.5, 104.5), (39.5, 107.5), (29.0, 107.5), (15.5, 94.0)]
R_HOOK = [(24.6, 72.5), (31.0, 72.5), (32.5, 79.5), (37.0, 84.0), (46.0, 87.5), (46.0, 90.5), (38.5, 90.5),
          (31.0, 87.0), (25.0, 82.0), (24.6, 78.0)]
R_HULLGAP = [(29.0, 44.0), (37.0, 44.0), (37.0, 57.5), (29.0, 57.5)]


def mirrored(poly):
    return [(2 * AX - x, y) for x, y in reversed(poly)]


# ----------------------------------------------------------------------------------------------
# The centre: tower, socket, pod, stinger, hull (symmetric)
# ----------------------------------------------------------------------------------------------

def half_widths(r0, r1, xlo, xhi):
    """Per-row (row centre, half width about the axis) of the mask between xlo and xhi."""
    out = []
    for r in range(r0, r1 + 1):
        cs = [c for c in range(int(xlo), int(xhi) + 1) if masked(c, r)]
        if cs:
            out.append((r + 0.5, max(AX - min(cs), max(cs) + 1 - AX)))
    return out


def tower_ring(y, hw, zc, hz, n=24, p=2.6, zfloor=-1.0):
    return sec_loop(AX, y, hw, zc, hz, n=n, p=p, zfloor=zfloor)


def build_centre(P):
    # --- hull: a chamfered keel box under everything (closed belly) ---
    # half width per row: the mask's contiguous run round the axis (min over +-1 row, 0.6 px in)
    run = {}
    for r in range(16, 76):
        c = 60
        while masked(c - 1, r):
            c -= 1
        run[r] = AX - c
    def hwr(r):
        return min(run.get(r + k, 99) for k in (-1, 0, 1)) - 0.6
    st = [(16.5, 11.5)] + [(r + 0.5, 31.7 if 51 < r < 56 else max(4.0, min(30.0, hwr(r)))) for r in range(18, 57, 2)] + [
        (57.5, 16.9), (62.4, 16.9), (63.0, 11.0), (69.5, 10.8), (70.6, 9.0), (72.5, 8.0), (74.5, 5.0)]
    rings = []
    for y, hw in st:
        # a deep keel, deepest under the drum and wings: the machine's mass from the side (plain)
        belly = max(0.0, min(1.0, (y - 18) / 10, (64 - y) / 12))
        top, bot = 6.5, -5.5 - 4.5 * belly
        if y > 62:
            top = 5.0
        ch = min(hw * 0.45, 4.6)
        pts = [(AX - hw, bot + ch), (AX - hw + ch, bot), (AX + hw - ch, bot), (AX + hw, bot + ch),
               (AX + hw, top - 1.2), (AX + hw - 1.2, top), (AX - hw + 1.2, top), (AX - hw, top - 1.2)]
        rings.append([(x, y, z) for x, z in pts])
    loft(P, rings, DGREY)

    # --- rear cap (rows 5.5-13.5) + brim + band + drum + front bulkhead ---
    hwc = dict(half_widths(5, 18, 44, 77))
    HC, HD = 10.0, 11.4  # dome cap / drum half heights: a tall crowned drum (mass from the side)
    # axis height: rises toward the rear
    zc = pchip([5.5, 14, 19, 37, 40], [9.6, 9.4, 8.6, 6.2, 5.4])
    cap_rows = [6.1, 6.4, 6.8, 7.5, 8.5, 9.5, 11.0, 12.5, 13.6]
    capw = pchip([5.5, 6.5, 7.5, 8.5, 9.5, 13.6], [4.5, hwc[6.5] - 0.2, hwc[7.5] - 0.2, hwc[8.5] - 0.1, 10.5, 10.5])
    rings = []
    for y in cap_rows:
        hw = capw(y)
        f = max(0.0, min(1.0, (y - 5.5) / 4.2))
        hz = HC * math.sqrt(max(0.05, 1 - (1 - f) ** 2))
        rings.append(tower_ring(y, hw, zc(y), hz, p=2.3, zfloor=-0.5))
    rings.insert(0, [(AX, 5.95, zc(5.5) + 1.2)])
    loft(P, rings, DOME)
    # rear service hatch on the dome's back face: a plate with louvres and a step ring round it
    # (below the dome's crown, so the top view is unchanged; it breaks up the rear view)
    z0 = zc(6.0)
    hull(P, cbox(AX - 4.0, AX + 4.0, 6.0, 8.0, z0 - 4.4, z0 + 1.4, 0.35), STEEL)
    for dz in (-3.4, -1.9, -0.4):
        hull(P, cbox(AX - 3.3, AX + 3.3, 5.85, 6.6, z0 + dz, z0 + dz + 0.75, 0.15), NOZZLE)
    for dx in (-4.6, 4.6):  # hinge lugs either side
        hull(P, cbox(AX + dx - 0.6, AX + dx + 0.6, 6.4, 8.0, z0 - 3.6, z0 + 0.6, 0.2), LGREY)
    # crest: a raised tan rib up the cap to the brim, with a lamp at its top
    crest = [(9.6, 0.0), (10.2, 1.4), (11.0, 2.0), (13.6, 2.2)]
    for i in range(len(crest) - 1):
        pass
    cr = []
    for y, w in crest:
        ztop = zc(y) + HC * math.sqrt(max(0.05, 1 - (1 - max(0, min(1, (y - 5.5) / 4.2))) ** 2))
        cr.append([(AX - w, y, ztop - 0.8), (AX - w * 0.7, y, ztop + 0.5), (AX + w * 0.7, y, ztop + 0.5),
                   (AX + w, y, ztop - 0.8)] if w > 0 else [(AX, y, ztop - 0.2)])
    cr = [ring if len(ring) == 4 else ring for ring in cr]
    cr[0] = [(AX - 0.4, 9.6, cr[1][0][2]), (AX - 0.3, 9.6, cr[1][1][2] - 0.4), (AX + 0.3, 9.6, cr[1][1][2] - 0.4),
             (AX + 0.4, 9.6, cr[1][0][2])]
    loft(P, cr, LTAN)
    cyl(P, AX - 1.5, 10.6, cr[1][1][2] - 0.25, 0.75, 0.33, LENS, n=10)  # flush lens (the sprite's 79 pair)

    # brim flange (rows 13.5-18.5): a machined ring, chamfered fore and aft
    bw = pchip([13.4, 14.5, 15.5, 16.5, 18.5], [10.4, 12.4, 14.4, 15.4, 15.4])
    b_rows = [13.4, 14.2, 15.0, 15.8, 16.6, 17.6, 18.2, 18.6]
    rings = [tower_ring(y, bw(y), zc(y), HD + 0.9 * min(1, (y - 13.4) / 2.0), p=2.4) for y in b_rows]
    loft(P, rings, BRIM)
    # bolts round the brim's top
    for dx in (-11, -7.5, -3.8, 3.8, 7.5, 11):
        y = 16.3
        zt = zc(y) + (HD + 0.9) * (1 - (abs(dx) / bw(y)) ** 2.4) ** (1 / 2.4)
        cyl(P, AX + dx, y, zt - 0.3, 0.55, 0.6, LGREY, n=6)
    # dark band (groove) under the brim
    loft(P, [tower_ring(18.4, 14.2, zc(18.4), HD - 0.4), tower_ring(19.8, 14.2, zc(19.8), HD - 0.4)], BROWN)
    # drum
    d_rows = [19.6, 20.6, 21.6, 22.5, 22.9, 23.3] + frange(24.4, 33.0, 1.6) + [34.2, 35.4, 36.4, 37.2]
    def drum_hw(y):
        return 14.4 if y <= 33.5 else 14.4 - (y - 33.5) * 0.45
    def drum_hz(y):
        return HD if y <= 33.0 else HD - (y - 33.0) ** 1.5 * 0.75
    rings = [tower_ring(y, drum_hw(y), zc(y), drum_hz(y), p=2.6) for y in d_rows]
    # the sprite's grey ring (rows 20-22) under the dark band, a machined step, then the bronze body
    loft(P, rings, [DRUMG] * 3 + [LGREY] * 2 + [DRUM] * (len(rings) - 9) + [BLACK] * 3)
    # front bulkhead face (dark), set back: closes the drum at row 37.2
    # lengthwise steel straps over the drum (cols 49-51 / 69-71)
    for side in (-1, 1):
        for x0 in (9.0,):
            ys = frange(20.2, 34.5, 1.2)
            rings = []
            for y in ys:
                hw, hz = drum_hw(y), drum_hz(y)
                ring = []
                for u in (-1.4, 1.4):
                    dx = x0 + u
                    zs = zc(y) + hz * max(0.0, 1 - (dx / hw) ** 2.6) ** (1 / 2.6)
                    ring.append((AX + side * dx, y, zs - 0.6))
                    ring.append((AX + side * dx, y, zs + 0.55))
                rings.append([ring[0], ring[1], ring[3], ring[2]] if side > 0 else [ring[2], ring[3], ring[1], ring[0]])
            loft(P, rings, LGREY)
            # strap bolts
            for y in (22.0, 28.0, 33.0):
                hw, hz = drum_hw(y), drum_hz(y)
                zs = zc(y) + hz * max(0.0, 1 - (x0 / hw) ** 2.6) ** (1 / 2.6)
                cyl(P, AX + side * x0, y, zs + 0.4, 0.5, 0.4, STEEL, n=6)
    # the centre column down the drum's top (cols 57-63, rows 23-34): a raised grey plate with a lit
    # steel spine and two bronze crossbars (the sprite's rows 25 and 28-29)
    def drum_top(y, dx=0.0):
        hw, hz = drum_hw(y), drum_hz(y)
        return zc(y) + hz * max(0.0, 1 - (abs(dx) / hw) ** 2.6) ** (1 / 2.6)
    zt = drum_top(26)
    col = [(AX - 3.5, 23.0), (AX + 3.5, 23.0), (AX + 3.5, 33.8), (AX - 3.5, 33.8)]
    prism(P, col, lambda x, y: drum_top(y, x - AX) - 1.0, lambda x, y: drum_top(y, x - AX) + 0.55, DRUMG,
          ch=0.35, chb=0.0)
    for y0, y1 in ((24.7, 25.9), (27.9, 29.8)):
        hull(P, cbox(AX - 3.9, AX + 3.9, y0, y1, drum_top((y0 + y1) / 2, 3.5) - 0.3,
                     drum_top((y0 + y1) / 2) + 0.95, 0.25), DRUM)
    for y0, y1 in ((23.3, 24.6), (26.0, 27.8), (29.9, 33.4)):  # the lit spine between them
        hull(P, cbox(AX - 1.1, AX + 1.1, y0, y1, drum_top((y0 + y1) / 2) + 0.2, drum_top((y0 + y1) / 2) + 0.8, 0.2),
             LGREY)
    # red beacon at the hatch's rear (rows 20-23, col 59-60)
    ellipsoid(P, AX - 0.3, 21.6, zt + 0.2, 1.2, 1.4, 1.0, RED, seg=10, rings=5)
    ellipsoid(P, AX - 0.6, 21.3, zt + 0.7, 0.55, 0.55, 0.5, LAMP, seg=8, rings=4)

    # collar (red ring) and neck (steel), coming out of the drum's front
    loft(P, [tower_ring(33.0, 5.6, 6.2, 4.2, n=20, p=2.2), tower_ring(34.0, 6.0, 6.2, 5.0, n=20, p=2.2),
             tower_ring(37.6, 6.0, 6.0, 4.9, n=20, p=2.2), tower_ring(38.4, 5.4, 5.9, 4.3, n=20, p=2.2)], PINK)
    loft(P, [tower_ring(38.0, 5.2, 5.8, 3.9, n=20, p=2.2), tower_ring(41.0, 5.4, 5.4, 3.6, n=20, p=2.2),
             tower_ring(44.0, 5.6, 4.8, 3.0, n=20, p=2.2), tower_ring(45.5, 5.6, 4.4, 2.6, n=20, p=2.2)], STEEL)
    # eye socket (rows 46.5-54.5, cols 55-66): an open black bezel round the eye, a steel lip on
    # its rim; the eye (separate frame models) sits on the socket floor and bulges above the rim
    loft(P, [tower_ring(y, 5.6, 2.5, 3.6, n=20, p=2.4, zfloor=-2.0) for y in (45.0, 54.0)], BLACK)
    cup(P, EX, EY, 6.0, 4.6, 0.9, 1.0, 8.2, 5.4, BLACK, n=24)
    cup(P, EX, EY + 0.1, 6.15, 4.7, 0.5, 7.6, 8.6, 7.8, STEEL, n=24)

    build_pod(P)

    # lower pod (black), rows 66-74, between the cheeks and the stinger
    hwp = dict(half_widths(66, 76, 49, 72))
    lp_rows = [66.0, 68.5, 70.5, 72.5, 74.5, 76.0]
    lpw = pchip([66.0, 68.5, 70.5, 72.5, 74.5, 76.0], [10.4, hwp.get(68.5, 10.5) - 0.2, hwp.get(70.5, 9.5) - 0.3,
                                                       hwp.get(72.5, 7.5) - 0.05, 6.2, 5.0])
    loft(P, [tower_ring(y, lpw(y), 2.0, 4.6 - (y - 66) * 0.12, n=20, p=2.4, zfloor=-3.0) for y in lp_rows], BLACK)

    build_stinger(P)


def build_pod(P):
    """Two red armour cheeks either side of a dark slot (cols 58-62), a tall inner ridge and a lower
    outer block each, a dark tan vent cut into each block in a red frame (as the old prisms, kept:
    they already followed the sprite)."""
    B = -2.5
    ZP = 2.6

    def prism_y(side, sections, mat):
        rings = [[(AX + side * dx, r, ZP + dz) for dx, dz in pts] for r, pts in sections]
        loft(P, rings if side > 0 else [list(reversed(rg)) for rg in rings], mat)

    def ridge(h):
        return [(2.5, B), (2.5, 7.9 * h), (3.1, 9.1 * h), (5.0, 9.1 * h), (5.6, 7.7 * h), (5.6, B)]

    def block(o, top=7.7, out=4.1):
        return [(5.4, B), (5.4, top), (max(o - 0.9, 5.5), top - 1.2), (o, out), (o, B)]

    # dark core in the slot and under the cheeks
    loft(P, [tower_ring(y, w, ZP, h, n=16, p=2.2, zfloor=-2.5) for y, w, h in
             ((54.0, 5.5, 3.0), (55.5, 9.0, 5.0), (58.0, 10.5, 5.8), (64.0, 10.5, 5.8), (67.5, 10.0, 5.0))], BLACK)
    for side in (-1, 1):
        prism_y(side, [(54.1, ridge(0.55)), (55.4, ridge(0.72)), (57.2, ridge(0.9)), (58.8, ridge(1.0)), (66.1, ridge(1.0)),
                       (67.3, ridge(0.85))], PODRED)
        prism_y(side, [(58.3, block(10.6, 5.3, 4.3)), (65.5, block(10.6, 5.3, 4.3))], VENT)
        prism_y(side, [(55.9, block(6.0)), (57.7, block(8.6)), (59.1, block(10.6)), (59.5, block(10.6))], PODRED)
        prism_y(side, [(65.1, block(11.2)), (66.7, block(11.2)), (67.8, block(10.4, 6.0, 3.6))], PODRED)
        prism_y(side, [(59.3, [(8.6, B), (8.6, 6.7), (9.6, 6.0), (10.6, 4.1), (10.6, B)]),
                       (62.6, [(8.6, B), (8.6, 6.7), (9.6, 6.0), (10.6, 4.1), (10.6, B)]),
                       (65.3, [(8.6, B), (8.6, 6.7), (9.6, 6.0), (11.2, 4.1), (11.2, B)])], PODRED)
        # inner red cheek strip: the vent is a narrow slot (cols 52-54 / 66-68), as the sprite
        prism_y(side, [(58.3, [(5.4, B), (5.4, 7.7), (6.3, 7.5), (6.3, B)]),
                       (65.5, [(5.4, B), (5.4, 7.7), (6.3, 7.5), (6.3, B)])], PODRED)
        for r in (60.7, 63.1):  # slats across the vent
            prism_y(side, [(r, [(6.3, 3.6), (6.3, 6.0), (8.6, 5.8), (8.6, 3.6)]),
                           (r + 0.7, [(6.3, 3.6), (6.3, 6.0), (8.6, 5.8), (8.6, 3.6)])], BROWN)
        prism_y(side, [(58.1, [(1.6, 3.6), (1.6, 7.4), (2.55, 7.4), (2.55, 3.6)]),
                       (61.9, [(1.6, 3.6), (1.6, 7.4), (2.55, 7.4), (2.55, 3.6)])], LGREY)


def build_stinger(P):
    hws = dict(half_widths(73, 92, 47, 74))
    rows = [72.6, 73.5, 74.5, 75.5, 76.5, 77.5, 79.0, 81.0, 83.0, 84.5, 85.5, 86.5, 87.5, 88.5, 89.5, 90.5,
            91.3, 91.8]
    # the mask's half width per row (the horns at rows 75-79 left out: they are built separately)
    raw = {72.6: 6.4, 73.5: 6.6, 74.5: 6.6, 75.5: 6.6, 76.5: 6.9}
    def hw_at(y):
        if y in raw:
            return raw[y]
        return hws.get(math.floor(y) + 0.5, 0.0)
    hz = pchip([72.6, 74.5, 76.5, 78.5, 81.5, 84.5, 87.5, 89.5, 91.0, 91.8], [3.0, 5.5, 9.0, 11.3, 12.0, 11.4, 9.2, 6.6, 3.6, 1.2])
    zc = -0.5
    rings = []
    for y in rows:
        hw = max(0.6, hw_at(y) - 0.05)
        rings.append(sec_loop(AX, y, hw, zc, hz(y), n=20, p=2.3, zfloor=-3.5))
    rings.append([(AX, 92.0, -0.5)])
    mats = []
    for y in rows:  # grey shell (the sprite's 3-7 flanks), the dark bronze lip, a dark tip (the 1-2 shade)
        mats.append(STING if y < 86.5 else DBROWN if y < 89.2 else BLACK)
    loft(P, rings, mats)
    # bronze saddle either side of the stripe (the sprite's 21-23 at cols 54-57 / 62-66, rows 81-86):
    # a thin raised plate on the shell, under the stripe
    sd_rows = frange(80.6, 86.8, 0.7)
    sdr = []
    for y in sd_rows:
        w = min(7.0, 3.0 + (y - 80.6) * 2.6)
        hw = max(0.6, hw_at(y) - 0.05)
        ring = []
        for u in (-w, -w * 0.5, 0.0, w * 0.5, w):
            zs = zc + hz(y) * max(0.0, 1 - (abs(u) / hw) ** 2.3) ** (1 / 2.3)
            ring.append((AX + u, y, zs + (0.2 if abs(u) < w else -0.2)))
        sdr.append([ring[0], ring[1], ring[2], ring[3], ring[4], (AX + w * 0.5, y, ring[4][2] - 0.5),
                    (AX - w * 0.5, y, ring[0][2] - 0.5)][::-1])
    loft(P, sdr, STINGMID)
    # raised red stripe down the stinger's front (cols 57-62, rows 78-89)
    st_rows = frange(78.0, 89.6, 0.9)
    srings = []
    for y in st_rows:
        w = 2.0 if y < 87 else 2.0 - (y - 87) * 0.45
        ring = []
        for u in (-w, -w * 0.6, w * 0.6, w):
            hw = max(0.6, hw_at(y) - 0.25)
            zs = zc + hz(y) * max(0.0, 1 - (abs(u) / hw) ** 2.3) ** (1 / 2.3)
            ring.append((AX + u, y, zs + (0.45 if abs(u) < w else -0.25)))
        srings.append([ring[0], ring[1], ring[2], ring[3], (AX + w * 0.5, y, ring[3][2] - 0.6), (AX - w * 0.5, y, ring[0][2] - 0.6)][::-1])
    loft(P, srings, STRIPE)
    # horns: crescent blades rising off the stinger's shoulders (cols 49-51 / 69-71, rows 75-79)
    for side in (-1, 1):
        path = [(AX + side * 8.0, 80.4, 7.4), (AX + side * 9.2, 78.4, 7.8), (AX + side * 10.3, 76.6, 8.4),
                (AX + side * 11.0, 75.4, 8.9), (AX + side * 11.6, 74.7, 9.2)]
        sweep(P, path, [(1.0, 0.55), (0.95, 0.5), (0.8, 0.42), (0.55, 0.3), (0.0, 0.0)], DGREY,
              profile=[(1, 0), (0, 1), (-1, 0), (0, -1)])
    # small fangs under the stinger's front rim (rows 89-91)
    for dx in (-4.2, -1.5, 1.5, 4.2):
        y0 = 89.0 if abs(dx) > 3 else 89.6
        hw = max(0.6, hw_at(y0) - 0.25)
        z0 = zc + hz(y0) * max(0.0, 1 - (abs(dx) / hw) ** 2.3) ** (1 / 2.3)
        sweep(P, [(AX + dx, y0, z0 - 1.0), (AX + dx * 0.97, y0 + 1.1, z0 - 2.4), (AX + dx * 0.94, y0 + 1.9, z0 - 3.6)],
              [(0.7, 0.6), (0.45, 0.4), (0.0, 0.0)], LGREY, profile=[(1, 0), (0, 1), (-1, 0), (0, -1)])


# ----------------------------------------------------------------------------------------------
# The left side (mirrored)
# ----------------------------------------------------------------------------------------------

def build_left(P):
    # --- wing: core plate + two armour panels + lit leading-edge spar, drooping to the tip ---
    wing = offset_poly(trace(region(R_WING), 0.55), 0.2)
    def droop(x, y):  # wing top: anhedral, high at the root, low at the tip (blueprint)
        t = max(0.0, min(1.0, (x - 5) / 36))
        return 6.4 + 4.2 * t + 0.6 * max(0.0, min(1.0, (40 - y) / 18)) - 0.3 * max(0.0, y - 37.0)
    def wbot(x, y):
        t = max(0.0, min(1.0, (x - 5) / 36))
        return droop(x, y) - 2.4 - 4.8 * t  # thick at the root, thin at the tip
    prism(P, wing, wbot, lambda x, y: droop(x, y) - 1.0, WING, ch=0.5, chb=0.4)
    # armour panels: split along a seam from the trailing edge to the root (a real gap)
    core_in = offset_poly(wing, 0.9)
    seam_p, seam_q = (16.0, 37.5), (31.5, 33.5)  # a seam across the wing near the root
    a = line_through(seam_p, seam_q, (10, 30), 0.3)
    panel_out = clip(core_in, *a)
    b = line_through(seam_p, seam_q, (30, 45), 0.3)
    panel_in = clip(core_in, *b)
    for poly in (panel_out, panel_in):
        if len(poly) >= 3:
            prism(P, poly, lambda x, y: droop(x, y) - 1.6, droop, WING, ch=0.45, chb=0.0)
    # darker bronze bands across the plates (the sprite's darker bronze lines down the wing)
    for (xa, ya), (xb, yb) in (((22.6, 28.4), (20.2, 43.6)), ((31.4, 35.2), (28.2, 49.4))):
        n = 8
        pts = [(xa + (xb - xa) * i / n, ya + (yb - ya) * i / n) for i in range(n + 1)]
        pts = [p for p in pts if inside(wing, *p)]
        if len(pts) >= 2:
            sweep(P, [(x, y, droop(x, y) + 0.02) for x, y in pts], [(0.85, 0.2)] * len(pts), WBAND,
                  profile=[(1.0, -1.0), (1.0, 0.4), (0.6, 1.0), (-0.6, 1.0), (-1.0, 0.4), (-1.0, -1.0)])
    # leading-edge spar (the sprite's light ridge along the wing's upper edge)
    lead = [(5.2, 22.6), (13.0, 25.0), (23.0, 29.6), (33.6, 34.6)]
    sweep(P, [(x, y, droop(x, y)) for x, y in catmull(lead, 3)], [(0.75, 0.55)] * len(catmull(lead, 3)), RIDGE, n=6)
    # bolts on the armour panels
    for x, y in ((14, 30.5), (20, 33.5), (26, 36.5), (22, 42.0), (27.5, 47.0), (30.0, 41.0)):
        if inside(wing, x, y):
            cyl(P, x, y, droop(x, y) - 0.15, 0.45, 0.4, LGREY, n=6)
    # wingtip: red knob outboard, grey block inboard
    tip = trace(region(R_TIP_RED))
    prism(P, tip, 1.0, 9.2, RED, ch=0.9, chb=0.5)
    hull(P, cbox(6.6, 9.4, 27.5, 34.5, 8.8, 9.6, 0.25), RED)
    grey = trace(region(R_TIP_GREY))
    prism(P, grey, 1.5, 8.8, GREY, ch=0.7, chb=0.4)
    hull(P, cbox(11.2, 14.6, 30.5, 36.2, 8.4, 9.2, 0.25), DGREY)

    # --- pylon: a hydraulic ram along y (the bright post) and an armour block ---
    post = region(R_POST)
    prism(P, trace(post), 8.0, 13.6, GREY, ch=0.6, chb=0.4)
    rows = sorted({r for _, r in post})
    rings = []
    for r in rows[1:]:
        ex = row_extent(post, r)
        if not ex:
            continue
        c0, c1 = ex
        cx, hw = (c0 + c1) / 2, (c1 - c0) / 2 - 0.1
        rings.append(sec_loop(cx, r + 0.5, hw, ZRAM, min(3.2, hw * 1.1), n=16, p=2.0, zfloor=ZRAM - 3.0))
    rings.insert(0, [(sum(p[0] for p in rings[0]) / len(rings[0]), rows[0] + 0.2, ZRAM + 0.8)])
    loft(P, rings, LGREY)
    # ram collar rings
    for y in (8.5, 15.5):
        ex = row_extent(post, int(y))
        cx, hw = (ex[0] + ex[1]) / 2, (ex[1] - ex[0]) / 2
        loft(P, [sec_loop(cx, y - 0.5, hw - 0.05, ZRAM, 3.4, n=16, zfloor=ZRAM - 3.0),
                 sec_loop(cx, y + 0.5, hw - 0.05, ZRAM, 3.4, n=16, zfloor=ZRAM - 3.0)], STEEL)
    pyl = offset_poly(trace(region(R_PYLON), 0.5), 0.2)
    def ptilt(x, y):  # the arm rises toward its outer rear end (blueprint)
        return 3.0 * max(0.0, min(1.0, (44 - x) / 25))
    prism(P, pyl, 5.0, 11.8, GREY, ch=0.8, chb=0.5, tilt=ptilt)
    # top armour slab with a seam, and the brown emblem (an inset L) and band
    top = offset_poly(pyl, 1.3)
    s1 = line_through((26, 17.0), (47, 17.0), (30, 10), 0.25)
    s2 = line_through((26, 17.0), (47, 17.0), (40, 30), 0.25)
    for poly in (clip(top, *s1), clip(top, *s2)):
        if len(poly) >= 3:
            prism(P, poly, 10.2, 12.6, GREY, ch=0.45, chb=0.0, tilt=ptilt)
    # the sprite's bronze L: a bar down cols 31-33 (rows 8-13) and a foot along rows 12-13 to col 27
    emblem = [(31.0, 8.0), (33.6, 8.6), (34.0, 14.0), (27.0, 14.0), (27.0, 12.0), (31.0, 12.0)]
    prism(P, emblem, 12.1, 12.95, BROWN, ch=0.25, chb=0.0, tilt=ptilt)
    band = [(28.0, 17.8), (45.0, 17.8), (45.6, 20.6), (29.5, 20.6)]
    prism(P, band, 11.0, 12.15, BROWN, ch=0.2, chb=0.0, tilt=ptilt)
    # bright bar down to the drum's side (col 37-38, rows 22-35)
    hull(P, cbox(36.8, 38.6, 21.5, 35.0, 10.2 + ptilt(37.5, 0), 13.1 + ptilt(37.5, 0), 0.35), LGREY)
    # lower bolts
    for x, y in ((40.5, 25.0), (40.5, 31.0), (33.0, 12.5), (42.0, 13.5)):
        cyl(P, x, y, 12.4 + ptilt(x, y) if y < 17 else 11.6 + ptilt(x, y), 0.45, 0.45, LGREY, n=6)

    # --- twin rear thrusters under the pylon: deep nozzles opening to the rear, set just inside
    # its slanted back edge (hidden from the top; they break up the rear face)
    NZ, NR = 3.2, 2.3
    for NX, Y0 in ((31.6, 8.8), (38.6, 10.8)):
        rings = [[(NX, Y0 + 7.2, NZ)], sec_loop(NX, Y0 + 6.8, NR - 0.4, NZ, NR - 0.4, n=16),
                 sec_loop(NX, Y0 + 6.2, NR, NZ, NR, n=16), sec_loop(NX, Y0 + 1.2, NR, NZ, NR, n=16),
                 sec_loop(NX, Y0 + 0.4, NR + 0.15, NZ, NR + 0.15, n=16), sec_loop(NX, Y0, NR - 0.15, NZ, NR - 0.15, n=16),
                 sec_loop(NX, Y0, NR - 0.6, NZ, NR - 0.6, n=16), sec_loop(NX, Y0 + 3.8, NR - 0.9, NZ, NR - 0.9, n=16),
                 [(NX, Y0 + 4.0, NZ)]]
        loft(P, rings, [STEEL, STEEL, DGREY, STEEL, STEEL, STEEL, NOZZLE, NOZZLE], cap0=False, cap1=False)
        loft(P, [sec_loop(NX, Y0 + 3.6, NR - 0.85, NZ, NR - 0.85, n=12),
                 sec_loop(NX, Y0 + 3.1, NR - 1.0, NZ, NR - 1.0, n=12)], FLAME, cap0=False, cap1=True)  # hot throat
        for y0 in (Y0 + 2.4, Y0 + 4.6):  # clamp bands
            loft(P, [sec_loop(NX, y0, NR + 0.25, NZ, NR + 0.25, n=16),
                     sec_loop(NX, y0 + 0.7, NR + 0.25, NZ, NR + 0.25, n=16)], LGREY)
        hull(P, cbox(NX - 1.8, NX + 1.8, Y0 + 1.4, Y0 + 6.8, NZ + 1.2, 7.6, 0.4), DGREY)  # pylon mount

    # rear face of the pylon block: inset service panels with steel straps over the thrusters
    # (the block's back edge runs from (26.5, 4) to (44.6, 10); its outward normal points to the rear)
    ex, ey = 18.1 / 19.07, 6.0 / 19.07
    nx, ny = ey, -ex
    for cxp in (31.2, 38.4):
        cyp = 4.0 + (cxp - 26.5) * 6.0 / 18.1 + 0.25
        zb = 6.4 + ptilt(cxp, cyp)

        def obox(u0, u1, d0, d1, z0, z1, mat):
            pts = []
            for u in (u0, u1):
                for d in (d0, d1):
                    for z in (z0, z1):
                        pts.append((cxp + ex * u + nx * d, cyp + ey * u + ny * d, z))
            hull(P, pts, mat)
        obox(-2.6, 2.6, -0.6, -0.1, zb, zb + 3.6, NOZZLE)
        for u in (-1.6, 0.0, 1.6):  # straps stay inside the block's back edge (no specks from the top)
            obox(u - 0.3, u + 0.3, -0.6, -0.02, zb - 0.2, zb + 3.4, LGREY)

    # --- cable bundle from the ram to the wingtip: three pipes with clamps ---
    cab = region(R_CABLE)
    field = Field(cab)
    guide = [(19.6, 9.6), (17.0, 9.6), (14.2, 10.0), (11.8, 11.2), (10.0, 12.8), (8.5, 14.6), (7.4, 16.6),
             (6.5, 18.6), (6.0, 20.6), (6.0, 22.6)]
    mid = centre_on(field, guide[1:-1], 1.2)
    guide = [guide[0]] + mid + [guide[-1]]
    # the sprite's cable lies a little further in along its curve (rows 10-17)
    guide = [(x + 0.25 * (1.0 if 9 < y < 18 else 0.0), y + 0.15 * (1.0 if 9 < y < 18 else 0.0)) for x, y in guide]
    path2 = catmull(guide, 2)
    zs = pchip([0, 0.25, 0.6, 1.0], [ZRAM, ZRAM + 1.0, 12.4, 8.6])
    L = len(path2) - 1
    path3 = [(x, y, zs(i / L)) for i, (x, y) in enumerate(path2)]
    hws = [max(1.0, min(2.2, field(x, y) + 0.5)) for x, y in path2]
    for k in (-1, 0, 1):
        pts = []
        rad = []
        for i, (x, y, z) in enumerate(path3):
            a, b = path3[max(i - 1, 0)], path3[min(i + 1, L)]
            tx, ty = b[0] - a[0], b[1] - a[1]
            ln = math.hypot(tx, ty) or 1
            nx, ny = -ty / ln, tx / ln
            r = hws[i] / 2.7
            off = k * (hws[i] - r)
            pts.append((x + nx * off, y + ny * off, z + (0.25 if k == 0 else 0.0)))
            rad.append((r, r))
        sweep(P, pts, rad, CABLE, n=6)
    for t in (0.18, 0.5, 0.8):
        i = int(t * L)
        seg = path3[max(i - 1, 0):i + 2]
        sweep(P, seg, [(hws[i] + 0.05, hws[i] * 0.55 + 0.25)] * len(seg), STEEL, n=8)

    # --- red panels (rows 39-44) and hull plates between the wing and the chevron ---
    prism(P, trace(region(R_REDPANEL), 0.5), 4.0, 10.6, RED, ch=0.6, chb=0.0)
    hull(P, cbox(37.5, 42.5, 44.5, 56.5, 4.5, 7.4, 0.4), DGREY)

    # --- chevron: the V armour plate, lit outer bevel ---
    chev = trace(region(R_CHEV), 0.6)
    def ctop(x, y):  # the yoke: highest over the neck, lower toward the shoulders (blueprint)
        return 11.8 + 1.4 * max(0.0, min(1.0, (x - 30) / 28)) - 1.2 * max(0.0, min(1.0, (y - 50) / 22))
    prism(P, chev, 5.0, ctop, CHEV, ch=1.1, chb=0.5)
    # outer-edge bright bevel strip along its upper-left edge
    edge = [(46.6, 44.6), (41.0, 50.2), (36.4, 55.0)]
    sweep(P, [(x + 0.7, y + 0.7, ctop(x, y) - 0.5) for x, y in edge], [(0.55, 0.45)] * 3, CHEV, n=6)
    # the lit crease along the arm's inner edge (the sprite's 27 line, cols 49 -> 42, rows 45 -> 56):
    # a raised ridge that splits the plate into its lighter and darker halves
    crease = [(49.4, 45.2), (47.0, 49.6), (44.4, 53.4), (42.2, 56.2)]
    sweep(P, [(x, y, ctop(x, y) + 0.05) for x, y in crease], [(0.55, 0.4)] * len(crease), CHEVL,
          profile=[(1.0, -1.0), (0.5, 0.6), (0.0, 1.0), (-0.5, 0.6), (-1.0, -1.0)])
    for x, y in ((50, 46.0), (44.0, 51.5), (39.5, 57.0), (38.5, 66.5)):
        if inside(chev, x, y):
            cyl(P, x, y, ctop(x, y) - 0.2, 0.5, 0.4, LGREY, n=6)

    # --- shoulder: a block with a recessed red window in a light frame ---
    sh = trace(region(R_SHOULDER), 0.5)
    prism(P, sh, -3.0, 10.0, GREY, ch=0.9, chb=2.6)  # undercut: the piston rides under it
    # window frame (proud) and recessed red glass (cols 16-21, rows 62-67)
    prism(P, [(14.9, 60.9), (23.1, 60.9), (23.1, 69.1), (14.9, 69.1)], 8.0, 10.8, LGREY, ch=0.4, chb=0.0)
    prism(P, [(15.9, 61.9), (22.1, 61.9), (22.1, 68.1), (15.9, 68.1)], 8.0, 10.85, BLACK, ch=0.0, chb=0.0)
    prism(P, [(16.2, 62.2), (21.8, 62.2), (21.8, 67.8), (16.2, 67.8)], 8.0, 11.0, WIN, ch=0.35, chb=0.0)
    # top light strip on the shoulder's rear edge (cols 18-23, rows 58-60)
    hull(P, cbox(17.8, 23.4, 57.8, 60.4, 9.2, 10.6, 0.35), LGREY)
    # forearm block with a triangular red window
    fa = trace(region(R_FOREARM), 0.5)
    prism(P, fa, -3.0, 7.4, GREY, ch=0.6, chb=2.2)
    prism(P, [(17.6, 72.1), (22.9, 72.1), (22.9, 74.0), (18.3, 77.5)], 6.0, 7.55, BLACK, ch=0.0, chb=0.0)
    prism(P, [(18.0, 72.5), (22.5, 72.5), (22.5, 73.6), (18.6, 76.9)], 6.0, 7.75, WIN, ch=0.25, chb=0.0)
    hull(P, cbox(15.2, 23.6, 70.3, 71.5, 6.8, 8.0, 0.3), LGREY)
    # wrist
    wr = trace(region(R_WRIST), 0.5)
    prism(P, wr, -3.0, 5.6, GREY, ch=0.6, chb=2.0)
    # hydraulic piston along the outer flank, shoulder to wrist (seen from the side)
    sweep(P, [(16.4, 60.0, -1.7), (17.6, 85.0, -1.7)], [(0.7, 0.7)] * 2, STEEL, n=8)
    sweep(P, [(16.5, 62.0, -1.7), (17.0, 73.0, -1.7)], [(1.05, 1.05)] * 2, DGREY, n=8)
    for y0 in (61.0, 83.0):  # clevis lugs
        hull(P, cbox(15.6, 18.6, y0, y0 + 2.0, -3.0, -0.4, 0.3), STEEL)
    # tan blade hanging below the shoulder (cols 24-28, rows 68-79), a standing fin
    bl = trace(region(R_BLADE), 0.5)
    prism(P, bl, -1.0, 10.6, BLADE, ch=0.7, chb=0.4)
    # the dark root block under the blade (cols 24-26, rows 76-80: the sprite's 1-5 shading)
    rb = trace(region([(23.6, 75.6), (27.0, 75.6), (27.0, 81.0), (23.6, 81.0)]), 0.5)
    prism(P, rb, -1.0, 8.4, DGREY, ch=0.5, chb=0.3)

    # --- claw: a horn tusk with a blade section, rooted in the wrist ---
    claw = region(R_CLAW)
    fc = Field(claw)
    guide = [(20.0, 82.0), (20.0, 85.5), (20.2, 89.0), (20.8, 92.5), (22.2, 95.8), (24.2, 98.8), (26.8, 101.8),
             (29.8, 104.0), (33.0, 105.5), (36.2, 106.0)]
    mid = centre_on(fc, guide[1:-1], 1.6)
    g2 = catmull([guide[0]] + mid + [guide[-1]], 3)
    tipx = (38.9, 105.9)
    hw = [max(0.2, fc(x, y)) for x, y in g2]
    hw[0] = hw[1]
    hw = [min(h + 0.6, 4.8) for h in hw]
    # the blade section sits a little outboard of the region's ridge on its outer curve (rows 88-101)
    # and lower toward the tip (the sprite's outer and lower edge pixels)
    def ramp(y, a, b, c, d):  # 0 below a, 1 between b and c, 0 above d
        return max(0.0, min(1.0, (y - a) / (b - a), (d - y) / (d - c)))
    hw = [h - 0.35 * ramp(y, 85, 87, 92, 94) for h, (x, y) in zip(hw, g2)]
    g2 = [(x - 0.15 * ramp(y, 85, 87, 92, 94) - 0.65 * ramp(y, 93, 96, 101, 104), y) for x, y in g2]
    L = len(g2)
    zcl = pchip([0, 0.3, 0.65, 1.0], [1.6, 0.6, -3.2, -6.6])  # mandibles reach down (blueprint)
    path = [(x, y, zcl(i / L)) for i, (x, y) in enumerate(g2)] + [(tipx[0], tipx[1], -7.0)]
    hw = [h * (1.0 - 0.15 * max(0.0, (i / L - 0.7) / 0.3)) for i, h in enumerate(hw)]
    rad = [(h, h * 0.95) for h in hw] + [(0.0, 0.0)]
    sweep(P, path, rad, CLAW, profile=hexblade())
    # a steel ferrule where the claw leaves the wrist
    sweep(P, [(20.0, 84.6, 1.6), (20.0, 86.4, 1.4)], [(hw[1] + 0.2, hw[1] * 0.95 + 0.2)] * 2, STEEL,
          profile=hexblade())

    # --- hook: a thin round rod curving in from under the blade ---
    hk = region(R_HOOK)
    fh = Field(hk)
    guide = [(27.0, 73.4), (27.2, 76.0), (27.7, 79.0), (28.8, 81.6), (30.6, 83.6), (33.4, 85.6), (36.5, 87.2),
             (39.5, 88.0), (42.4, 89.0)]
    mid = centre_on(fh, guide[1:-1], 1.0)
    g2 = catmull([guide[0]] + mid + [guide[-1]], 3)
    hw = [max(0.6, min(2.5, fh(x, y) + 0.55)) for x, y in g2]
    L = len(g2)
    zh = pchip([0, 0.5, 1.0], [3.4, 0.6, -3.6])
    path = [(x, y, zh(i / L)) for i, (x, y) in enumerate(g2)] + [(45.2, 89.4, -4.0)]
    rad = [(h, h * 0.9) for h in hw] + [(0.0, 0.0)]
    sweep(P, path, rad, HOOK, n=10)


# ----------------------------------------------------------------------------------------------
# Eye frames (newsh4-1): as the game script's, in px, in this socket
# ----------------------------------------------------------------------------------------------



def eye_materials(sprite, mats):
    pal = lambda i, part, **kw: common.palette_material(sprite, i, f"{TAG}-{part}", **kw)  # noqa: E731
    return mats + [
        pal(9, "shutter", metallic=0.6, roughness=0.3),
        pal(70, "slit", emission_strength=1.5),
        pal(74, "eye", emission_strength=1.5, frames={5: 71}),
        pal(122, "spark", emission_strength=3.0),
        pal(77, "glint", emission_strength=2.0),
        pal(117, "glow", emission_strength=4.0, frames={41: 116, 43: 117}),
        pal(122, "hot", emission_strength=5.0, frames={41: 121, 43: 123}),
        pal(127, "white", emission_strength=6.0),
    ]


SHUTTER, SLIT, EYE_A, SPARK, GLINT, GLOW_A, HOT_A, WHITE = range(N_MATS, N_MATS + 8)


def eye_frame(frame, P):
    if frame == 1:
        ellipsoid(P, EX, EY, EZ, 4.9, 3.8, 1.5, SHUTTER)
    elif frame == 3:
        for s in (-1, 1):
            ellipsoid(P, EX + s * 2.5, EY, EZ, 2.3, 3.8, 1.5, SHUTTER, seg=12, rings=8)
        ellipsoid(P, EX, EY + 0.4, EZ - 0.2, 0.6, 3.0, 1.2, SLIT, seg=8, rings=6)
    elif frame in (5, 7):
        ellipsoid(P, EX, EY, EZ - 0.1, 1.9, 2.5, 1.4, EYE_A, seg=12, rings=6)
        gap = 3.6 if frame == 5 else 4.3
        for s in (-1, 1):
            ellipsoid(P, EX + s * gap, EY, EZ, 1.2 if frame == 5 else 0.95, 3.7, 1.3, SHUTTER, seg=10, rings=6)
        if frame == 7:
            ellipsoid(P, EX - 1, EY - 0.5, EZ + 1.0, 0.6, 0.6, 0.4, SPARK, seg=8, rings=4)
    elif frame == 39:
        ellipsoid(P, EX, EY, EZ - 0.1, 3.1, 2.5, 1.5, EYE_A)
        ellipsoid(P, EX - 1, EY - 0.5, EZ + 1.0, 0.7, 0.7, 0.4, GLINT, seg=8, rings=4)
    else:
        ry = 2.5 if frame == 41 else 3.6
        ellipsoid(P, EX, EY, EZ, 4.3, ry, 1.8, GLOW_A)
        ellipsoid(P, EX - 0.4, EY - 0.2, EZ + 0.7, 2.3 if frame == 41 else 3.3, ry * (0.65 if frame == 41 else 0.8),
                  1.4, HOT_A, seg=12, rings=6)


def build_eye(frames, mats, coll, offset, model):
    groups = {}
    for f in frames:
        groups.setdefault(45 if f == 43 else f, []).append(f)
    parts = []
    for key, tagged in groups.items():
        P = Part()
        eye_frame(key, P)
        o = to_object(P, f"{model}-eye-{key}", mats, coll)
        o.location = (-offset[0], -offset[1], 0)
        bpy.context.view_layer.update()
        _apply_location(o)
        parts.append(common.frame_part(o, tagged))
    if 41 in frames:
        P = Part()
        ellipsoid(P, EX - 1, EY - 0.5, EZ + 1.6, 0.85, 0.7, 0.45, WHITE, seg=8, rings=4)
        o = to_object(P, f"{model}-eye-white", mats, coll)
        o.location = (-offset[0], -offset[1], 0)
        _apply_location(o)
        parts.append(o)
    return parts


def _apply_location(o):
    me = o.data
    for v in me.vertices:
        v.co.x += o.location.x
        v.co.y += o.location.y
        v.co.z += o.location.z
    o.location = (0, 0, 0)


# ----------------------------------------------------------------------------------------------

def build(sprite, coll):
    mats = materials(sprite)
    P = Part()
    build_left(P)
    mirror(P)
    build_centre(P)
    return to_object(P, NAME, mats, coll), mats


# ----------------------------------------------------------------------------------------------
# Finishing: cull hidden faces, split, bake per piece, outline shells, export
# ----------------------------------------------------------------------------------------------

def cull_hidden(obj, grid=3, ndirs=40):
    """Delete faces no ray from outside reaches (usp_talon.cull_hidden): the insides of stacked
    plates and the parts buried in the hull."""
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


def bake_piece(obj, out_dir, size=512, samples=48, colour_mul=None):
    """usp_talon.bake_maps for one piece: Smart UV, Cycles bake of an occlusion/edge colour
    multiplier and a roughness/metallic map (the other pieces stay in the scene, so the occlusion
    runs on across the cuts), wired into the piece's own copies of its palette materials (Base
    Color = map x palette colour; the game swaps the palette colour in). Emissive slots stay plain.
    No concept projection. `colour_mul(node_tree, new_node)`, if given, returns a socket the colour
    map is multiplied by (assembly-newsh4-124-damaged.py's scorch)."""
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
    # The piece's own material copies (same pal_<index> names, the piece as a suffix).
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
            if colour_mul is not None:
                v = math_("MULTIPLY", v, colour_mul(nt, node))
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


def whole_shell(obj, coll, voxel=0.016, faces=1300, smooth=4):
    """common.outline_shell for the whole machine (D51), keeping every outer island: a voxel
    remesh of the closed build (before the hidden faces are culled), smoothed and thinned. Islands
    that lie inside another island's box are inner shells and are dropped; the separate outer parts
    (cables, claws) stay."""
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

    def box(isl):
        return [min(v.co[k] for v in isl) for k in range(3)] + [max(v.co[k] for v in isl) for k in range(3)]
    boxes = [box(i) for i in islands]

    def within(a, b):
        return all(a[k] > b[k] + 1e-4 for k in range(3)) and all(a[k + 3] < b[k + 3] - 1e-4 for k in range(3))
    drop = set()
    for i, a in enumerate(boxes):
        if len(islands[i]) < 12 or any(within(a, b) for j, b in enumerate(boxes) if j != i):
            drop.update(v.index for v in islands[i])
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
    print(f"{NAME}: outline shell {len(shell.data.polygons)} faces, {len(islands) - 0} islands before culling")
    return shell


def split_open(obj, layout, coll, suffix):
    """split_assembly without capping the cuts (for the outline shells: no seams outlined)."""
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
    # The outline shell (D51) of the whole closed machine, cut open into the pieces later.
    shell = whole_shell(obj, coll)
    cull_hidden(obj)
    layout = [(e["model"], e["cx"] - CX0, e["cy"] - CY0) for e in LAYOUT if e["model"] in PIECES]
    eye_centre = next((cx / 12, -cy / 12) for name, cx, cy in layout if name == EYE)
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
    emats = eye_materials(sprite, mats)
    eyes = {m: build_eye(fr, emats, coll, eye_centre, m) for m, fr in EYE_MODELS}
    # Bake each piece with every other piece in place round it (the occlusion runs across the cuts).
    fmt = "AUTO"
    if "--no-bake" not in argv:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="nsh4a124_bake_")
        _cycles(48)
        for name, cx, cy in layout:
            pieces[name].location = (cx / 12, -cy / 12, 0)
        for o in eyes["newsh4-1-f3"]:
            o.location = eye_centre[0], eye_centre[1], 0
        for e in [o for m in eyes for o in eyes[m] if m != "newsh4-1-f3"]:
            e.hide_render = True
        for name, _, _ in layout:
            bake_piece(pieces[name], tmp)
        for o in list(pieces.values()) + [o for m in eyes for o in eyes[m]]:
            o.location = (0, 0, 0)
        fmt = "WEBP"
    for p in pieces.values():
        wn = p.modifiers.new("weighted", "WEIGHTED_NORMAL")
        wn.keep_sharp = True
        wn.weight = 50

    tri = 0
    for name, cx, cy in layout:
        pieces[name].data.calc_loop_triangles()
        tri += len(pieces[name].data.loop_triangles)
    for o in eyes["newsh4-1-f3"]:
        o.data.calc_loop_triangles()
        tri += len(o.data.loop_triangles)
    print(f"{NAME}: triangles (pieces + f3 eye, no shells) {tri}")

    if "--no-export" not in argv:
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            extra = [shells[name]] if name in shells and len(shells[name].data.polygons) else []
            if name != EYE:
                sprites = [dict(s, frames=s["frames"] + EXTRA_FRAMES.get(name, [])) for s in data["sprites"]]
                common.export_sprite_model(ROOT, [pieces[name]] + extra, f"enemies/{name}", sprites,
                                           image_format=fmt)
                continue
            for model, frames in EYE_MODELS:
                sprites = [dict(s, frames=[f for f in s["frames"] if f in frames]) for s in data["sprites"]]
                sprites = [s for s in sprites if s["frames"]]
                common.export_sprite_model(ROOT, [pieces[name]] + eyes[model] + extra, f"enemies/{model}", sprites,
                                           image_format=fmt)

    if "--design-out" in argv:
        # Review export: one .glb with every piece back in assembly space (render.py / analyze.py).
        out = Path(argv[argv.index("--design-out") + 1])
        export = []
        for name, cx, cy in layout:
            for o in [pieces[name]] + ([shells[name]] if len(shells[name].data.polygons) else []):
                o.location = (cx / 12, -cy / 12, 0)
                o["tyrian_piece"] = name
                export.append(o)
        for model, parts in eyes.items():
            for o in parts:
                o["tyrian_model"] = model
                o["tyrian_piece"] = EYE
                o.location = eye_centre[0], eye_centre[1], 0
                export.append(o)
        common.export_glb(export, out, image_format=fmt)
        for o in export:
            o.location = (0, 0, 0)
        print(f"design export {out}")


if __name__ == "__main__":
    main()
