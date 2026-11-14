"""Giant nose of the flying face (NOSE DRIP, 4.16): newsh5 191 + 193 side by side, plus newsh5-154 above
them, as ONE object. 

What it is: a human nose, the centre of the flying face boss (the blue eye orbs, newsh5-270, sit either
side of the bridge; the tongue and a red pod are other items). newsh5-154 was catalogued as a "brown
fingertip", but it is the nose's BRIDGE: it spawns rigid with the nose at dx +-12, dy -28, so its
24x28 box sits centred over the two nose pieces; its bottom row (cols 14-34) meets the nose's top row
(cols 13-35) edge to edge; the lit ridge (palette 26-30, its cols 8-10 = assembly cols 20-22) runs on
unbroken into the nose's lit stripe at the same columns, and its dark right flank (17) runs on into
the nose's shaded right side. Composed whole (48 x 52 px) it is unmistakably a nose seen from the
front: a long bridge with a rounded root between the eyes, a broad round tip, two round alae (wings),
two dark nostrils under them and a short columella.

Sprite reading (rubric "Reading a sprite"): the light comes from the upper left; the bright stripe down
the left of the bridge and the spots on the tip and left ala are sheen on skin, the dark right half
and the outline ring are lighting. Only the nostrils (palette 1) are real dark paint. Region medians
(ignoring <= 17 and >= 27): bridge 21, tip 22, left ala 21, columella 19 (it faces down, shaded) ->
skin pal 21 throughout (the tip's 22 is its sheen; a separate tip paint read as a ball, QA E4), nostrils pal 1.

Seams (fix round 1): the piece cuts (r = 28 across, c = 24 down the nose) are constraint edges of the
triangulation, so the split adds no slivers on the top surface, and every piece carries the unsplit
mesh's smooth corner normals (carry_normals) so no shading break shows along the cuts.

Build: flesh, faired, a height field over the sprite's inner mask (the face is the screen plane, the
nose stands out of it towards the camera): smooth union of a dorsum ridge that levels off over the
supratip, the tip (QA re-review: the sprite's biggest form, a broad round dome ~40% of the nose's
width standing well above the alae, blended into the dorsum with no trench and no separate paint),
rounded alae domes with a soft alar groove, a short low columella tucked under the tip and a low
base, rounded over the last 2.8 px down to a short upright side (0.7 px) at the silhouette. The
nostrils are broad, low kidney-shaped shadows (pal 1) recessed into the lower slope, their wide inner
ends down by the columella at the bottom edge (not almond slits, not holes on top); flat closed
underside. One sealed outline shell from the whole (D51, D90/D118), sunk under the top surface so the
ink stays on the silhouette, cut open at the piece seams; the upright side keeps the voxel shell's
silhouette even (a knife edge left it ragged).

Units: c, r = assembly px edges, (0, 0) = top left of the 48 x 56 box (bridge rows 0-27, nose rows
28-55); X = (c - 24) / 12, Y = (26 - r) / 12, Z = h / 12. Piece centres (split_assembly):
newsh5-191 (-12, +16), newsh5-193 (+12, +16), newsh5-154 (0, -12).

Run: blender --background --python assets/blender/enemies/assembly-newsh5-191.py -- [--out x.glb] [--review DIR]
(exports newsh5-191 and newsh5-193; newsh5-154.py exports the bridge from the same build)
Exports each piece to public/models/enemies/<piece>.glb + its spriteModels entry; --out x.glb also writes the whole.
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector, geometry

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

ROOT = common.repo_root(__file__)
WT = ROOT
sys.path.insert(0, str(ROOT / "tools"))
import sprite_mask as S  # noqa: E402

NAME = "assembly-newsh5-191"
HERE = Path(__file__).resolve().parent
TAG = "n5a191"
PX = 1 / 12
W, H = 48, 56
C0, R0 = 24, 26  # assembly origin (edge coords)
XA = 24.5  # mirror axis (centre of column 24)
# piece name, top-left (c, r) of its 24 x 28 box in the composite
PLACE = [("newsh5-154", 12, 0), ("newsh5-191", 0, 28), ("newsh5-193", 24, 28)]
LAYOUT = [(n, c + 12 - C0, r + 14 - R0) for n, c, r in PLACE]

SKIN, HOLE = 21, 1
ROUGH = {SKIN: 0.42, HOLE: 1.0}  # skin with a satin sheen (the sprite's highlights)

STEP = 0.5  # lattice spacing, px
RINGS = (0.12, 0.35, 0.7, 1.15, 1.7, 2.3, 2.9)  # px in from the silhouette
RIM = 2.8  # px over which the top rounds down to the silhouette
GROW = 0.0  # px the traced outline is pushed out (corner cutting eats the convex corners)
SMAX_K = 3.0  # px blend of the smooth union
SIGMA = 1.1  # px: Gaussian smoothing of the traced outline
BRIDGE_SIGMA = 1.9  # px: extra fairing of the bridge's sides


def X(c):
    return (c - C0) * PX


def Y(r):
    return (R0 - r) * PX


# ------------------------------------------------------------------------------------------------
# Sprite
# ------------------------------------------------------------------------------------------------

def composite():
    idx = [[-1] * W for _ in range(H)]
    colors = {}
    for name, c0, r0 in PLACE:
        data = json.loads((ROOT / "reference" / "models" / name / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in data["colors"].items()})
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(int(t) for t in row.split()):
                if v >= 0:
                    idx[r0 + r][c0 + c] = v
    return idx, colors


def trace(mask, rounds=3):
    """Outline of the largest region of `mask`, CCW in (c, r) edge coords (r down), corner-cut."""
    h, w = len(mask), len(mask[0])
    ins = lambda c, r: 0 <= r < h and 0 <= c < w and mask[r][c]  # noqa: E731
    edges = {}
    for r in range(h):
        for c in range(w):
            if not ins(c, r):
                continue
            if not ins(c, r - 1):
                edges[(c + 1, r)] = (c, r)
            if not ins(c, r + 1):
                edges[(c, r + 1)] = (c + 1, r + 1)
            if not ins(c - 1, r):
                edges[(c, r)] = (c, r + 1)
            if not ins(c + 1, r):
                edges[(c + 1, r + 1)] = (c + 1, r)
    loops, seen = [], set()
    for s in list(edges):
        if s in seen:
            continue
        loop, p = [], s
        while p not in seen and p in edges:
            seen.add(p)
            loop.append(p)
            p = edges[p]
        loops.append(loop)
    pts = [Vector(p) for p in max(loops, key=len)]
    for _ in range(rounds):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out += [p * 0.75 + q * 0.25, p * 0.25 + q * 0.75]
        pts = out
    return [(p.x, p.y) for p in pts]


def signed_area(poly):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def offset(poly, d):
    """Push every vertex `d` outward (poly orientation-agnostic)."""
    sgn = 1 if signed_area(poly) > 0 else -1
    out = []
    n = len(poly)
    for i, (x, y) in enumerate(poly):
        ax, ay = poly[i - 1]
        bx, by = poly[(i + 1) % n]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        # for a CCW polygon (in a y-up frame) the outward normal is (ty, -tx); r is down here
        nx, ny = ty / ln, -tx / ln
        out.append((x + sgn * nx * d, y + sgn * ny * d))
    return out


def taubin(poly, iters=40, lam=0.5, mu=-0.53):
    """Smooth a closed polygon without shrinking it (Taubin lambda/mu): the pixel stairs go, the
    curves stay where the sprite puts them."""
    pts = list(poly)
    n = len(pts)
    for _ in range(iters):
        for f in (lam, mu):
            pts = [(x + f * ((pts[i - 1][0] + pts[(i + 1) % n][0]) / 2 - x),
                    y + f * ((pts[i - 1][1] + pts[(i + 1) % n][1]) / 2 - y)) for i, (x, y) in enumerate(pts)]
    return pts


def gauss_smooth(poly, sigma):
    """Smooth a closed, evenly sampled polygon with a Gaussian of `sigma` px along its length."""
    n = len(poly)
    step = sum(math.dist(poly[i], poly[(i + 1) % n]) for i in range(n)) / n
    rad = int(3 * sigma / step) + 1
    wts = [math.exp(-0.5 * (k * step / sigma) ** 2) for k in range(-rad, rad + 1)]
    tw = sum(wts)
    out = []
    for i in range(n):
        x = y = 0.0
        for k, wk in zip(range(-rad, rad + 1), wts):
            px, py = poly[(i + k) % n]
            x += wk * px
            y += wk * py
        out.append((x / tw, y / tw))
    return out


def perimeter(poly):
    return sum(math.dist(a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def resample(poly, step):
    segs = list(zip(poly, poly[1:] + poly[:1]))
    total = sum(math.dist(a, b) for a, b in segs)
    n = max(8, int(total / step))
    out, i, acc = [], 0, 0.0
    for k in range(n):
        t = total * k / n
        while acc + math.dist(*segs[i]) < t:
            acc += math.dist(*segs[i])
            i += 1
        a, b = segs[i]
        ln = math.dist(a, b) or 1
        f = (t - acc) / ln
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out


def inside(poly, x, y):
    c = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def seg_dist_open(line, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(line, line[1:]):
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L))
        best = min(best, math.hypot(ax + t * dx - x, ay + t * dy - y))
    if len(line) == 1:
        best = math.dist(line[0], (x, y))
    return best


def seg_dist(poly, x, y):
    best = 1e9
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L))
        d = math.hypot(ax + t * dx - x, ay + t * dy - y)
        if d < best:
            best = d
    return best


# ------------------------------------------------------------------------------------------------
# Shape (px)
# ------------------------------------------------------------------------------------------------

def pchip(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
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
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


NEG = -50.0
FALL = 40.0  # px per unit of the normalised radius: how fast a part's field drops outside it
# dorsum (bridge) ridge: height and half-width down the face
# (rises into the tip ball so the ridge runs on into it as one surface)
# levels off over the supratip (r 28-32) so the tip dome stands clearly above it, then fades to 0
# under the tip (no step where it ends)
DH = pchip([(1.5, 3.0), (4, 5.8), (8, 8.0), (14, 9.8), (20, 11.4), (26, 12.9), (30, 13.4), (33, 12.6), (36, 8.0), (39.0, 0.0)])
# half-width: the bridge's own (faired) footprint down to row 25 (no flat shelf beside the ridge), then
# narrowing into the tip
DWL = pchip([(25, 9.6), (31, 8.0), (36, 7.0), (38.5, 6.0)])
SPAN = {}  # row (0.25 px steps) -> (centre, half-width) of the faired footprint, set by set_span()
# columella: height and half-width
# short and tucked under the tip: low from the tip's lower slope on, no lit peg below the nostrils
CH = pchip([(37, 0.0), (39, 7.5), (42, 5.6), (45, 3.6), (48, 2.1), (50.5, 1.1), (51.8, 0.5)])
CW = pchip([(37, 4.2), (42, 3.6), (46, 2.9), (49, 2.1), (51.8, 1.0)])
COL_P = 0.5  # a rounded section, no keel
# the tip: one swelling of the dorsum (not a ball set on it): wide, long run-in, broad blend
# re-review: the tip is the sprite's biggest form, a broad round lobe between the alae (cols 17-30,
# rows 29-46, ~40% of the nose's width) standing well above them: a wide dome, its crown ~4 px over
# the levelled dorsum, blended into it (no trench)
TIP_C, TIP_R, TIP_H = (24.5, 36.4), (8.6, 8.0), 17.6
TIP_RUP = 10.0  # px: the tip's radius up the face (a long run-in from the bridge, no step)
TIP_K = 6.0  # px blend of the tip into the ridge
TIP_P = 0.6  # rounder shoulders than the other parts: a domed mass, not a ridge
# alae: low rounded wings flowing into the tip (broad blend, no supra-alar trench)
ALA_C, ALA_R, ALA_H = (12.6, 37.4), (7.6, 8.0), 9.6
ALA_K, COL_K = 3.6, 3.0  # a soft alar groove between ala and tip (the sprite's shade at cols 14-17)
BASE = 2.2
DOME_P = 0.7  # dome profile (1 - q)^p: softer than a sphere so the parts flow into each other
# nostrils: dark crescent slits on the nose's lower, down-facing slope (under the alae, beside the
# columella), where the sprite has its pal 1; a smile-shaped band in a frame tilted inner end down:
# centre (c, r), tilt (rad), half-length L, end lift B, half-thickness T (px)
# re-review: broad, low, irregular shadows under the tip and inner ala, down at the bottom edge (the
# sprite's right nostril: rows 40-47, cols 27-36, its inner end running down beside the columella),
# not almonds: a kidney, wide and low at the inner end, rising thinner under the ala. Right one in
# (c, r); the left is its mirror.
NOS_POLY = [(26.4, 47.6), (25.9, 46.4), (26.5, 45.0), (28.0, 43.8), (29.6, 43.6), (30.8, 43.9),
            (32.2, 42.9), (34.0, 42.3), (35.4, 42.8), (35.4, 44.0), (34.2, 45.3), (32.6, 46.3),
            (30.6, 46.9), (28.4, 47.7)]
NOS_DEPTH = 1.8  # px recess inside the shadow
NOS_FLOOR = 2.8  # px: the tongue (newsh-caret-269, 2.6 px tall) lies under the nose; never cut below it


WALL = 0.7  # px: a short upright side at the silhouette (the voxel shell of a knife edge came out ragged)


def dome(c, r, cen, rad, h, p=DOME_P):
    q = ((c - cen[0]) / rad[0]) ** 2 + ((r - cen[1]) / rad[1]) ** 2
    # outside the dome the value keeps falling from 0 (no jump to NEG: inside a smooth union a jump
    # leaves a step in the surface, which read as the ball's crease)
    return h * (1 - q) ** p if q < 1 else -FALL * (math.sqrt(q) - 1)


def ridge(c, r, r0, r1, hf, wf, p=0.7):
    if r < r0 or r > r1:
        return NEG
    w = wf(r)
    u = (c - XA) / w
    if abs(u) >= 1:
        return -FALL * (abs(u) - 1)
    return hf(r) * (1 - u * u) ** p


def smax(a, b, k=SMAX_K):
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k / 4


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def set_span(poly):
    """Per-row centre and half-width of the faired footprint, smoothed down the rows (sigma 1.5 px)."""
    rows = [k * 0.25 for k in range(int(H / 0.25) + 1)]
    raw = {}
    for r in rows:
        xs = []
        n = len(poly)
        for i in range(n):
            (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
            if (y0 > r) != (y1 > r):
                xs.append(x0 + (x1 - x0) * (r - y0) / (y1 - y0))
        if len(xs) >= 2:
            raw[r] = ((min(xs) + max(xs)) / 2, (max(xs) - min(xs)) / 2)
    keys = sorted(raw)
    for r in keys:
        ws = [(math.exp(-0.5 * ((q - r) / 1.5) ** 2), raw[q]) for q in keys if abs(q - r) < 4.5]
        tw = sum(w for w, _ in ws)
        SPAN[r] = (sum(w * v[0] for w, v in ws) / tw, sum(w * v[1] for w, v in ws) / tw)


def span(r):
    k = round(r * 4) / 4
    return SPAN.get(k, (XA, 0.0))


def bridge(c, r):
    """Dorsum: a rounded section spanning the bridge's full faired width (no shelf, no slab top)."""
    if r < 1.0:
        return NEG
    s = smoothstep(25.0, 31.0, r)
    cen0, hw0 = span(min(r, 25.0))
    cen = cen0 * (1 - s) + XA * s
    w = (hw0 + 0.4) * (1 - s) + DWL(r) * s
    u = (c - cen) / w
    if abs(u) >= 1:
        return -FALL * (abs(u) - 1)
    return DH(r) * (1 - u * u) ** 0.75  # DH is 0 from r 38.5 on


def tip_ball(c, r):
    # the radius eases from the lower 7 px to TIP_RUP above the apex (no curvature step = no sheen line)
    ry = TIP_R[1] + (TIP_RUP - TIP_R[1]) * smoothstep(TIP_C[1] + 2.0, TIP_C[1] - 5.0, r)
    return dome(c, r, TIP_C, (TIP_R[0], ry), TIP_H, p=TIP_P)


def parts(c, r):
    tip = tip_ball(c, r)
    ala = max(dome(c, r, ALA_C, ALA_R, ALA_H), dome(c, r, (2 * XA - ALA_C[0], ALA_C[1]), ALA_R, ALA_H))
    dor = bridge(c, r)
    col = ridge(c, r, 37.0, 52.0, CH, CW, p=COL_P)
    return tip, ala, dor, col


def _nos_polys():
    right = [(x, y) for x, y in gauss_smooth(resample(NOS_POLY, 0.2), 0.45)]
    left = [(2 * XA - x, y) for x, y in reversed(right)]
    return [left, right]


NOS_POLYS = None


def nostril_sd(c, r):
    """Signed distance into the nearest nostril shadow (px, > 0 inside)."""
    global NOS_POLYS
    if NOS_POLYS is None:
        NOS_POLYS = _nos_polys()
    best = -9.0
    for poly in NOS_POLYS:
        if abs(c - poly[0][0]) > 12:
            continue
        d = seg_dist(poly, c, r)
        best = max(best, d if inside(poly, c, r) else -d)
    return best


def height(c, r, d):
    tip, ala, dor, col = parts(c, r)
    z = BASE
    for v, k in ((dor, SMAX_K), (ala, ALA_K), (col, COL_K), (tip, TIP_K)):
        z = smax(z, v, k)
    sd = nostril_sd(c, r)
    if sd > -0.4:
        w = smoothstep(-0.4, 1.2, sd)
        z -= w * min(NOS_DEPTH, max(0.0, z - NOS_FLOOR))
    e = min(d / RIM, 1.0)
    return WALL + (z - WALL) * math.sqrt(max(0.0, 1 - (1 - e) ** 2))


def paint_of(c, r, z):
    if nostril_sd(c, r) > 0:
        return HOLE
    return SKIN


def paint_loops():
    """Closed (c, r) polylines the paint changes along: the mesh gets edges there (clean borders)."""
    if NOS_POLYS is None:
        nostril_sd(0, 0)
    return [resample(p, 0.38) for p in NOS_POLYS]


# ------------------------------------------------------------------------------------------------
# Mesh
# ------------------------------------------------------------------------------------------------

SEAM_R, SEAM_C = 28.0, 24.0  # piece cuts: r = 28 across the whole, c = 24 down the nose (r > 28)


def seam_insert(outline):
    """Insert the points where the outline crosses the piece cuts, so the rim has a vertex on each cut."""
    out = []
    n = len(outline)
    hits = {"r": [], "c": []}
    for i in range(n):
        a, b = outline[i], outline[(i + 1) % n]
        out.append(a)
        cand = []
        if (a[1] - SEAM_R) * (b[1] - SEAM_R) < 0:
            t = (SEAM_R - a[1]) / (b[1] - a[1])
            cand.append((t, (a[0] + (b[0] - a[0]) * t, SEAM_R), "r"))
        if (a[0] - SEAM_C) * (b[0] - SEAM_C) < 0:
            t = (SEAM_C - a[0]) / (b[0] - a[0])
            q = (SEAM_C, a[1] + (b[1] - a[1]) * t)
            if q[1] > SEAM_R:
                cand.append((t, q, "c"))
        for t, q, k in sorted(cand):
            if 0.02 < t < 0.98:
                out.append(q)
                hits[k].append(q)
            else:  # snap the nearer end onto the cut instead of adding a sliver
                j = len(out) - 1 if t <= 0.02 else None
                if j is not None:
                    out[j] = q
                    hits[k].append(q)
                else:
                    hits[k].append(("next", q))
    # snap pending "next" ends
    fixed = {"r": [], "c": []}
    for k in hits:
        for q in hits[k]:
            if q[0] == "next":
                q = q[1]
                j = min(range(len(out)), key=lambda m: math.dist(out[m], q))
                out[j] = q
            fixed[k].append(q)
    return out, fixed


def seam_lines(hits, step=0.38):
    """Open polylines along the cuts, between the outline crossings."""
    lines = []
    rs = sorted(hits["r"])
    if len(rs) >= 2:
        a, b = rs[0][0], rs[-1][0]
        n = max(2, int((b - a) / step))
        lines.append([(a + (b - a) * k / n, SEAM_R) for k in range(1, n)])
    cs = [q for q in hits["c"]]
    if cs:
        b = max(q[1] for q in cs)
        a = SEAM_R
        n = max(2, int((b - a) / step))
        lines.append([(SEAM_C, a + (b - a) * k / n) for k in range(0, n)])
    return lines, rs


def build(coll, poly, sprite):
    outline, hits = seam_insert(resample(poly, 0.38))
    seams, rs = seam_lines(hits)
    loops = paint_loops()
    pts = list(outline)
    nb = len(outline)
    near_seam = lambda c, r: any(seg_dist_open(sl, c, r) < STEP * 0.45 for sl in seams)  # noqa: E731
    # rings parallel to the silhouette for the rounded rim (even quads, no ruffles)
    for d in RINGS:  # noqa: B007
        ring = resample(offset(poly, -d), 0.38 + d * 0.06)
        for c, rr in ring:
            if inside(poly, c, rr) and abs(seg_dist(outline, c, rr) - d) < 0.12 and not near_seam(c, rr):
                pts.append((c, rr))
    # hex lattice inside, kept STEP*0.6 away from the outline
    dy = STEP * math.sqrt(3) / 2
    r = 0.0
    row = 0
    while r < H:
        c = (STEP / 2) * (row % 2)
        while c < W:
            if inside(poly, c, r) and seg_dist(outline, c, r) > RINGS[-1] + STEP * 0.6 \
                    and all(seg_dist(lp, c, r) > STEP * 0.45 for lp in loops) and not near_seam(c, r):
                pts.append((c, r))
            c += STEP
        r += dy
        row += 1
    edges = [(i, (i + 1) % nb) for i in range(nb)]
    for lp in loops:
        i0 = len(pts)
        pts.extend(lp)
        edges.extend((i0 + i, i0 + (i + 1) % len(lp)) for i in range(len(lp)))
    # the cuts: open polylines ending on the rim's crossing vertices
    def rim_index(q):
        return min(range(nb), key=lambda m: math.dist(outline[m], q))
    for k, sl in enumerate(seams):
        i0 = len(pts)
        pts.extend(sl)
        chain = list(range(i0, i0 + len(sl)))
        if k == 0:  # across r = 28: rim crossing .. rim crossing
            chain = [rim_index(rs[0])] + chain + [rim_index(rs[-1])]
        else:  # down c = 24 from the r = 28 line to the rim at the columella
            # (its first point, (24, 28), lies on the r = 28 line; the CDT splits that edge there)
            chain = chain + [rim_index(max(hits["c"], key=lambda q: q[1]))]
        edges.extend((chain[i], chain[i + 1]) for i in range(len(chain) - 1))
    res = geometry.delaunay_2d_cdt([Vector(p) for p in pts], edges, [list(range(nb))], 1, 1e-6)
    vco, _e, faces = res[0], res[1], res[2]
    bm = bmesh.new()
    vs = []
    dist = []
    for p in vco:
        c, rr = p.x, p.y
        d = seg_dist(outline, c, rr)
        dist.append(d)
        vs.append(bm.verts.new((X(c), Y(rr), height(c, rr, d) * PX)))
    mats_order = [SKIN, HOLE]
    for f in faces:
        if len(f) < 3:
            continue
        cc = sum(vco[i].x for i in f) / len(f)
        cr = sum(vco[i].y for i in f) / len(f)
        if not inside(poly, cc, cr):
            continue
        # r runs down: CDT winding in (c, r) is mirrored in Blender XY; fix below with recalc
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        face.material_index = mats_order.index(paint_of(cc, cr, 0))
        face.smooth = True
    # underside: the outline filled flat at z = 0 (shares the rim verts)
    bm.verts.ensure_lookup_table()
    # the upright side: the rim (at z = WALL) dropped to z = 0, the underside closes that ring
    top_rim = [vs[i] for i in range(nb)]
    rim = [bm.verts.new((v.co.x, v.co.y, 0.0)) for v in top_rim]
    for i in range(nb):
        j = (i + 1) % nb
        try:
            f = bm.faces.new([top_rim[i], top_rim[j], rim[j], rim[i]])
            f.material_index = 0
            f.smooth = True
        except ValueError:
            pass
    res2 = geometry.delaunay_2d_cdt([Vector(p) for p in outline], edges, [list(range(nb))], 1, 1e-6)
    for f in res2[2]:
        cc = sum(res2[0][i].x for i in f) / len(f)
        cr = sum(res2[0][i].y for i in f) / len(f)
        if not inside(poly, cc, cr):
            continue
        ids = [res2[3][i][0] if res2[3][i] else None for i in f]
        if any(i is None or i >= nb for i in ids):
            continue
        try:
            face = bm.faces.new([rim[i] for i in ids][::-1])
        except ValueError:
            continue
        face.material_index = 0
        face.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].smooth != e.link_faces[1].smooth:
            e.smooth = False
    mesh = bpy.data.meshes.new(NAME)
    bm.to_mesh(mesh)
    bm.free()
    analytic_normals(mesh, outline)
    for i in mats_order:
        mesh.materials.append(common.palette_material(sprite, i, TAG, metallic=0.0, roughness=ROUGH[i]))
    obj = bpy.data.objects.new(NAME, mesh)
    coll.objects.link(obj)
    return obj


def analytic_normals(mesh, outline, e=0.12):
    """Top-surface corner normals from the height field's own gradient (central differences), not
    from the triangles: no specular sparkle where the lattice meets the cut lines and the paint loops.
    Rim verts within 0.6 px of the silhouette and the flat underside keep the mesh's normals."""
    def h(c, r):
        return height(c, r, seg_dist(outline, c, r))
    vn = []
    for v in mesh.vertices:
        c, r = v.co.x / PX + C0, R0 - v.co.y / PX
        d = seg_dist(outline, c, r)
        if d < 0.6 or v.co.z <= 1e-6:
            vn.append(None)
            continue
        if d > RIM + 2 * e:
            dc = (height(c + e, r, d) - height(c - e, r, d)) / (2 * e)
            dr = (height(c, r + e, d) - height(c, r - e, d)) / (2 * e)
        else:
            dc = (h(c + e, r) - h(c - e, r)) / (2 * e)
            dr = (h(c, r + e) - h(c, r - e)) / (2 * e)
        vn.append(Vector((-dc, dr, 1.0)).normalized())  # z = h PX, X = c PX, Y = -r PX
    cn = mesh.corner_normals
    out = []
    for f in mesh.polygons:
        for li in f.loop_indices:
            n = vn[mesh.loops[li].vertex_index] if f.use_smooth else None
            out.append(n if n is not None else (cn[li].vector.copy() if f.use_smooth else f.normal.copy()))
    mesh.normals_split_custom_set(out)


# ------------------------------------------------------------------------------------------------
# Outline shell (copied from assembly-newshe-123: sink + open split)
# ------------------------------------------------------------------------------------------------

def sink_shell(shell, model, margin=0.6 * PX, reach=1.4 * PX, floor=0.8 * PX):
    from mathutils.bvhtree import BVHTree
    dg = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(model, dg)
    mw = shell.matrix_world
    inv = mw.inverted()
    mm = model.matrix_world
    mi = mm.inverted()
    for v in shell.data.vertices:
        w = mw @ v.co
        tops, misses = [], 0
        for rad, ks in ((0.0, 1), (0.5 * reach, 10), (reach, 12)):
            for k in range(ks):
                a = 2 * math.pi * k / ks
                hit = tree.ray_cast(mi @ Vector((w.x + rad * math.cos(a), w.y + rad * math.sin(a), 5.0)),
                                    Vector((0, 0, -1)))
                if hit[0] is None:
                    misses += 1
                else:
                    tops.append((mm @ hit[0]).z)
        if not tops:
            continue
        z = min(w.z, max(0.0, min(tops) - margin))
        if misses == 0:
            z = min(z, floor)
        v.co = inv @ Vector((w.x, w.y, z))
    shell.data.update()


def split_shell(shell, layout, coll):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for m in shell.data.materials:
            me.materials.append(m)
        me.shade_smooth()
        o = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out


def carry_normals(whole, piece, x0, y0):
    """Give each piece the unsplit mesh's corner normals (copied from assembly-newsh9-197.py), so the
    cuts leave no shading break; faces not on the whole's surface (seam caps) keep their own normal."""
    from mathutils.bvhtree import BVHTree
    wm = whole.data
    tree = BVHTree.FromPolygons([v.co for v in wm.vertices], [p.vertices[:] for p in wm.polygons])
    cn = wm.corner_normals
    pm = piece.data
    off = Vector((x0, y0, 0))
    out = [None] * len(pm.loops)
    for f in pm.polygons:
        c = f.center + off
        loc, nrm, idx, dist = tree.find_nearest(c)
        ok = idx is not None and dist < 1e-4 and nrm.dot(f.normal) > 0.98
        for li in f.loop_indices:
            if not ok:
                out[li] = f.normal.copy()
                continue
            pv = pm.vertices[pm.loops[li].vertex_index].co + off
            wf = wm.polygons[idx]
            wl = list(wf.loop_indices)
            if len(wl) == 3:
                a, b, c3 = (wm.vertices[wm.loops[k].vertex_index].co for k in wl)
                w = geometry.barycentric_transform(pv, a, b, c3, Vector((1, 0, 0)), Vector((0, 1, 0)),
                                                   Vector((0, 0, 1)))
                out[li] = sum((cn[k].vector * max(0.0, w[j]) for j, k in enumerate(wl)), Vector()).normalized()
            else:
                best = min(wl, key=lambda k: (wm.vertices[wm.loops[k].vertex_index].co - pv).length)
                out[li] = cn[best].vector.copy()
    pm.normals_split_custom_set(out)


def flat_seam_caps(piece, eps=1e-4):
    me = piece.data
    for f in me.polygons:
        vs = [me.vertices[i].co for i in f.vertices]
        if all(abs(abs(v.x) - 1.0) < eps for v in vs) or all(abs(abs(v.y) - 14 / 12) < eps for v in vs):
            f.use_smooth = False


# ------------------------------------------------------------------------------------------------

def footprint(inner):
    """The sprite's inner mask traced, smoothed (no pixel stairs: a nose is round) and pushed out so
    its area is the mask's plus GROW px all round."""
    poly = gauss_smooth(resample(trace(inner, rounds=0), 0.25), SIGMA)
    # the bridge (rows < 28) is a plain taper: fair its pixel-traced sides much harder (no wobble);
    # the nose's alae/nostril outline below keeps the light smoothing
    soft = gauss_smooth(poly, BRIDGE_SIGMA)
    poly = [(x0 + (x1 - x0) * smoothstep(29.0, 25.0, y0), y0 + (y1 - y0) * smoothstep(29.0, 25.0, y0))
            for (x0, y0), (x1, y1) in zip(poly, soft)]
    want = sum(map(sum, inner))
    for _ in range(3):
        poly = offset(poly, (want - abs(signed_area(poly))) / perimeter(poly))
        poly = resample(poly, 0.25)
    return offset(poly, GROW)


def main(only=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(NAME)
    idx, colors = composite()
    m = S.masks(idx, colors)
    poly = footprint(m["inner"])
    set_span(poly)
    sprite = {"name": NAME, "colors": {str(k): list(v) for k, v in colors.items()}}
    obj = build(coll, poly, sprite)
    pieces = common.split_assembly(obj, LAYOUT, coll)
    for name, dx, dy in LAYOUT:
        flat_seam_caps(pieces[name])
        carry_normals(obj, pieces[name], dx / 12, -dy / 12)
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    whole = common.outline_shell(sealed, coll, voxel=0.014, faces=3000, smooth=6, inside=0.006, islands="outer")
    sink_shell(whole, sealed, margin=0.5 * PX, reach=0.6 * PX, floor=1.2 * PX)
    bpy.data.objects.remove(sealed, do_unlink=True)
    cut = split_shell(whole, LAYOUT, coll)
    bpy.data.objects.remove(whole, do_unlink=True)
    total = 0
    exports = {}
    for name, dx, dy in LAYOUT:
        p, sh = pieces[name], cut[name]
        sh.name = sh.data.name = f"{name}_outline"
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{name}: {tris} tris, outline {len(sh.data.polygons)} faces")
        if not len(sh.data.polygons):
            print("WARNING empty outline", name)
        exports[name] = (p, sh)
    print("total tris", total)
    for name, (p, sh) in exports.items():
        if only is None or name in only:
            data = common.load_sprite(ROOT, name)
            common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", data["sprites"])
    for name, dx, dy in LAYOUT:
        for o in exports[name]:
            o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()
    obj.hide_render = True
    obj.hide_set(True)
    if "--out" in argv:
        common.export_glb([e[0] for e in exports.values()] + [e[1] for e in exports.values()], argv[argv.index("--out") + 1])
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1])
        rv.mkdir(parents=True, exist_ok=True)
        review([e[0] for e in exports.values()], [e[1] for e in exports.values()], rv, total)


# ------------------------------------------------------------------------------------------------
# Review renders + top-view IoU (only with --review)
# ------------------------------------------------------------------------------------------------

def review(pieces, shells, out, total):
    scene = bpy.context.scene
    YC = Y(28)  # canvas centre (c 24, r 28)

    def cam(location, look_at, ortho=None, fov=None, top=False):
        data = bpy.data.cameras.new("cam")
        if ortho:
            data.type = "ORTHO"
            data.ortho_scale = ortho
        else:
            data.sensor_fit = "VERTICAL"
            data.angle_y = math.radians(fov)
        c = bpy.data.objects.new("cam", data)
        scene.collection.objects.link(c)
        c.location = location
        c.rotation_euler = (0, 0, 0) if top else (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
        return c

    def render(c, path, rx, ry):
        scene.camera = c
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.resolution_percentage = 100
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(c, do_unlink=True)

    for s in shells:
        s.hide_render = True
    scene.render.engine = "BLENDER_WORKBENCH"
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "MATERIAL"
    sh.show_cavity = False
    sh.show_object_outline = False
    sh.show_shadows = False
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    k = 8
    render(cam((0, YC, 20), None, ortho=H / 12, top=True), out / "top_flat.png", W * k, H * k)
    # top view silhouette -> IoU per piece and whole
    img = bpy.data.images.load(str(out / "top_flat.png"))
    w, h = img.size
    px = list(img.pixels)
    alpha = [[px[((h - 1 - y) * w + x) * 4 + 3] > 0.5 for x in range(w)] for y in range(h)]
    bpy.data.images.remove(img)
    idx, colors = composite()
    stats = {"tris": total}
    stats["whole"] = S.measure(S.masks(idx, colors), alpha)
    for name, c0, r0 in PLACE:
        pidx, pcol = S.load(name)
        sub = [row[c0 * k:(c0 + 24) * k] for row in alpha[r0 * k:(r0 + 28) * k]]
        stats[name] = S.measure(S.masks(pidx, pcol), sub)
    # nose pieces as the catalogue's 48 x 28 assembly grid
    aidx = [row[:] for row in idx[28:56]]
    stats["nose_assembly"] = S.measure(S.masks(aidx, colors), [row[:] for row in alpha[28 * k:56 * k]])
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    for kk, v in stats.items():
        if isinstance(v, dict):
            print("IOU", kk, v["iou_rule_grid"], v["iou_rule"])
    # palette-index top view
    scene.display_settings.display_device = "sRGB"
    scene.render.dither_intensity = 0
    mats = {m for p in pieces for m in p.data.materials}
    keep = {}
    for mt in mats:
        keep[mt.name] = tuple(mt.diffuse_color)
        fc = {SKIN: (0.8, 0.35, 0.05), HOLE: (0.05, 0.2, 0.9)}
        mt.diffuse_color = (*fc[int(mt.name.split("_")[1])], 1)
    render(cam((0, YC, 20), None, ortho=H / 12, top=True), out / "top_index.png", W * k, H * k)
    for mt in mats:
        mt.diffuse_color = keep[mt.name]
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "EEVEE" in e)
    world = scene.world or bpy.data.worlds.new("game")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.45, 0.55, 1.0)
    bg.inputs[1].default_value = 1.0
    sun_data = bpy.data.lights.new("game_sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("game_sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, 8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    ink = bpy.data.materials.new("ink")
    ink.use_nodes = True
    bs = next(n for n in ink.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bs.inputs["Roughness"].default_value = 1.0
    ink.use_backface_culling = True
    for s in shells:
        hh = s.copy()
        hh.data = s.data.copy()
        hh.data.materials.clear()
        hh.data.materials.append(ink)
        scene.collection.objects.link(hh)
        bm = bmesh.new()
        bm.from_mesh(hh.data)
        bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * 0.03
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.to_mesh(hh.data)
        bm.free()
        hh.hide_render = False
    render(cam((0, YC, 20), None, ortho=H / 12, top=True), out / "top_game.png", W * 8, H * 8)
    zc = 0.4
    render(cam((30, YC, zc), (0, YC, zc), ortho=5.4), out / "side.png", 600, 300)
    render(cam((0, YC - 30, zc), (0, YC, zc), ortho=4.6), out / "front.png", 500, 300)
    render(cam((0, YC + 30, zc), (0, YC, zc), ortho=4.6), out / "rear.png", 500, 300)
    d = 14
    render(cam((d * 0.55, YC - d * 0.6, d * 0.5), (0, YC, 0.4), fov=30), out / "q1.png", 700, 600)
    render(cam((-d * 0.6, YC + d * 0.5, d * 0.55), (0, YC, 0.4), fov=30), out / "q2.png", 700, 600)
    tilt = math.radians(32)
    render(cam((0, YC - d * math.sin(tilt), d * math.cos(tilt)), (0, YC, 0.4), fov=26), out / "game.png", 700, 600)
    render(cam((0, YC - d * 0.3, -d * 0.9), (0, YC, 0), fov=32), out / "under.png", 500, 400)


if __name__ == "__main__":
    main(only=["newsh5-191", "newsh5-193"])
