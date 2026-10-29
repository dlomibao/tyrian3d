"""The burnt-out wreck on TYRIAN's ground (map 1-9, layer 0; tiles 340-342 / 350-352, 3x2), after
the concept assets/blender/features/concepts/tyr-wreck.jpg: a blackened, torn crater in the dirt,
its floor charcoal with brown dirt breaking through between the two lobes and on the left, a row of
broad torn hull plates (scorched grey metal, rust-streaked) standing across its lower half, leaning
back, two of them bent or fallen, and dense debris (chips, shards, rusted bars) strewn over its
upper right.

Every cell carries a ground enemy (the "rock outcrop", assembly-newshe-39), so the wreck shows only
after kills and everything stays under ENEMY_MAX (0.38): the plates rise to about 0.35, the floor is
low (0.03, its torn lip 0.06). The tiles stay drawn (keepTiles): the model covers only the wreck's own
dark outline, not the dirt round it. The floor is one smooth torn polygon traced at sub-pixel
resolution from that outline (not the pixel-stepped terrace), its lip sloping down to just above the
dirt. Its export writes the variant wreck-cut (the copy cut by the map's right edge, cols 12-13) and
removes the old per-tile relief shapesz-wreck.
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_wreck.py
    python tools/concept_maps.py tile:shapesz-tyrbld-wreck --concept tyr-wreck --span 0,0,1,2 --px 32
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-wreck
"""

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

EDGE = 0.012  # the torn outline, just above the dirt tiles (z 0)
LIP = 0.062  # the charred lip's crest
FLOOR = 0.03  # the crater's charcoal floor
BOTTOM = -0.02  # the floor slab's underside

# Standing hull plates, in pattern px (72 x 56), lined up with the tiles' grey blobs: (x0, x1, base
# row, top row, top height, segments, kind). kind: "up" leans back; "bent" stands to half height
# then folds back; "fallen" lies almost flat, propped on one edge.
PLATES = [
    (5.0, 11.0, 33.5, 28.5, 0.20, 3, "up"),
    (12.5, 19.5, 37.0, 29.0, 0.29, 3, "up"),
    (19.5, 26.5, 37.5, 28.0, 0.34, 4, "up"),
    (27.0, 34.0, 42.0, 31.5, 0.35, 4, "up"),
    (34.0, 40.0, 42.5, 33.0, 0.31, 3, "bent"),
    (40.5, 46.5, 42.5, 34.5, 0.14, 3, "fallen"),
    (46.0, 53.0, 39.5, 31.0, 0.33, 4, "up"),
    (53.5, 60.0, 40.0, 31.5, 0.27, 3, "bent"),
]
# Fallen plates lying on the floor, torn and tilted: (cx, cy, half length, half width, angle deg,
# z top, pieces).
SLABS = [
    (13.0, 39.5, 3.4, 1.6, -20, 0.10, 2),
    (60.5, 41.0, 2.4, 1.4, 30, 0.09, 1),
    (47.5, 13.6, 3.0, 1.3, 5, 0.09, 2),
    (59.5, 15.5, 2.0, 1.2, 50, 0.08, 1),
    (8.0, 19.0, 1.8, 1.0, 30, 0.07, 1),
    (24.0, 44.0, 2.2, 1.0, -10, 0.07, 1),
]
# Rusted bars and brackets: (x0, y0, x1, y1, width px, z top).
BARS = [
    (51.5, 19.5, 58.0, 15.0, 0.8, 0.09),
    (50.5, 27.0, 56.0, 26.5, 0.7, 0.07),
    (41.0, 25.0, 45.5, 23.5, 0.7, 0.07),
    (61.0, 22.5, 63.5, 20.0, 0.6, 0.065),
    (11.0, 23.0, 13.5, 20.0, 0.6, 0.065),
    (44.0, 12.5, 44.0, 15.0, 0.6, 0.10),
    (50.0, 12.5, 50.0, 15.0, 0.6, 0.10),
    (39.0, 41.5, 37.0, 44.5, 0.6, 0.07),
]
# Upright shard bits in the debris fields (small plates): (x0, x1, base, top row, z top, segs).
SHARDS = [
    (51.0, 54.0, 12.5, 10.5, 0.10, 2),
    (6.0, 8.5, 25.0, 22.0, 0.14, 2),
    (58.5, 61.5, 18.0, 14.0, 0.16, 2),
    (62.5, 64.5, 26.0, 23.0, 0.12, 2),
]
# The dense debris field, upper right, and a thinner one upper left: (x0, y0, x1, y1, chips, bars).
FIELDS = [
    (38.0, 8.0, 66.0, 29.0, 80, 9, "metal"),
    (5.0, 16.0, 18.0, 27.0, 14, 3, "metal"),
    (6.0, 36.0, 66.0, 50.0, 40, 3, "char"),
]
# The dirt tongue cut into the outline from the top, between the lobes: (cx, cy, rx, ry) px.
TONGUE = (31.0, 3.0, 5.0, 8.5)
# Brown dirt breaking through the char, where the concept paints it: (cx, cy, rx, ry, angle deg).
DIRT_PATCHES = [
    (24.0, 13.5, 5.5, 3.8, 10), (31.0, 15.0, 5.0, 3.8, -10), (28.0, 20.5, 5.5, 3.2, -15), (21.5, 22.5, 4.0, 2.6, 20),
    (12.0, 18.5, 3.6, 2.6, 30), (9.0, 23.5, 2.6, 1.8, -10), (33.5, 15.0, 2.8, 2.0, 40),
]


# --- Outline: a smooth torn polygon at sub-pixel resolution ----------------------------------------

def blur(mask, sigma):
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    f = np.pad(mask.astype(float), r + 2)
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, f)
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, f)
    return f, r + 2


def contour(field, off, level=0.5):
    """The longest closed iso-line of `field` (marching squares on pixel centres), as (px, py)
    points in pattern px."""
    h, w = field.shape
    segs = {}

    def ept(a, b):
        (ya, xa), (yb, xb) = a, b
        fa, fb = field[ya, xa], field[yb, xb]
        t = (level - fa) / (fb - fa)
        return (xa + (xb - xa) * t + 0.5 - off, ya + (yb - ya) * t + 0.5 - off)

    pts = {}
    nxt = {}
    for y in range(h - 1):
        for x in range(w - 1):
            c = [(y, x), (y, x + 1), (y + 1, x + 1), (y + 1, x)]
            ins = [field[p] >= level for p in c]
            if all(ins) or not any(ins):
                continue
            edges = [(c[i], c[(i + 1) % 4]) for i in range(4) if ins[i] != ins[(i + 1) % 4]]
            keys = [tuple(sorted(e)) for e in edges]
            for k, e in zip(keys, edges):
                pts[k] = ept(*e)
            # Pair crossing edges: going round the square, an edge leaving the inside goes to the
            # next edge entering it (saddles split consistently).
            outs = [i for i in range(4) if ins[i] and not ins[(i + 1) % 4]]
            for i in outs:
                k0 = tuple(sorted((c[i], c[(i + 1) % 4])))
                j = (i + 1) % 4
                while not (not ins[j] and ins[(j + 1) % 4]):
                    j = (j + 1) % 4
                k1 = tuple(sorted((c[j], c[(j + 1) % 4])))
                nxt[k1] = k0
    loops, seen = [], set()
    for k in nxt:
        if k in seen:
            continue
        loop = []
        while k not in seen and k in nxt:
            seen.add(k)
            loop.append(pts[k])
            k = nxt[k]
        loops.append(loop)
    return max(loops, key=len)


def resample(loop, step):
    p = np.array(loop + [loop[0]])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    n = max(8, int(d[-1] / step))
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.c_[np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])]


def smooth(p, k=2, n=1):
    for _ in range(n):
        p = sum(np.roll(p, i, axis=0) for i in range(-k, k + 1)) / (2 * k + 1)
    return p


def normals_in(p):
    """Unit normals pointing into the polygon."""
    t = np.roll(p, -1, axis=0) - np.roll(p, 1, axis=0)
    t /= np.maximum(np.hypot(*t.T), 1e-6)[:, None]
    nrm = np.c_[-t[:, 1], t[:, 0]]
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return nrm if area > 0 else -nrm


def noise1(rng, n, waves):
    """Smooth periodic noise along a loop of n points: a sum of (period count, amplitude) waves."""
    t = np.arange(n) / n * 2 * math.pi
    out = np.zeros(n)
    for k, a in waves:
        out += a * np.sin(k * t + rng.uniform(0, 2 * math.pi))
    return out


def _cross2(u, v):
    return u[..., 0] * v[..., 1] - u[..., 1] * v[..., 0]


def first_crossing(p):
    """The first pair (i, j) of a closed loop's segments that cross, or None."""
    a, b = p, np.roll(p, -1, axis=0)
    n = len(p)
    for i in range(n):
        j = np.arange(i + 2, n if i else n - 1)
        if not len(j):
            continue
        d1 = _cross2(b[i] - a[i], a[j] - a[i])
        d2 = _cross2(b[i] - a[i], b[j] - a[i])
        d3 = _cross2(b[j] - a[j], a[i] - a[j])
        d4 = _cross2(b[j] - a[j], b[i] - a[j])
        hit = np.nonzero((d1 * d2 < 0) & (d3 * d4 < 0))[0]
        if len(hit):
            return i, int(j[hit[0]])
    return None


def crossings(p):
    return 0 if first_crossing(p) is None else 1


def untangle(p):
    """Cut the little loops an inset makes at tight concave corners: where segments i and j cross,
    the shorter run of points between them is laid along the chord (keeps the point count)."""
    p = p.copy()
    n = len(p)
    for _ in range(50):
        c = first_crossing(p)
        if c is None:
            return p
        i, j = c
        if j - i <= n // 2:
            idx = list(range(i + 1, j + 1))
        else:
            idx = [k % n for k in range(j + 1, i + n + 1)]
        # Spread the run evenly along the chord from the point before it to the point after it.
        a0, a1 = p[(idx[0] - 1) % n], p[(idx[-1] + 1) % n]
        f = (np.arange(len(idx)) + 1) / (len(idx) + 1)
        p[idx] = a0 + (a1 - a0) * f[:, None]
    return p


def width_in(f, off, p, d, level=0.5, step=0.25, limit=12.0):
    """How far (px) a ray from outline point p along inward normal d stays inside the field."""
    h, w = f.shape
    t = step
    while t < limit:
        x, y = p[0] + d[0] * t - 0.5 + off, p[1] + d[1] * t - 0.5 + off
        ix, iy = int(math.floor(x)), int(math.floor(y))
        if not (0 <= ix < w - 1 and 0 <= iy < h - 1):
            break
        fx, fy = x - ix, y - iy
        v = (f[iy, ix] * (1 - fx) * (1 - fy) + f[iy, ix + 1] * fx * (1 - fy) + f[iy + 1, ix] * (1 - fx) * fy
             + f[iy + 1, ix + 1] * fx * fy)
        if v < level:
            break
        t += step
    return t


def floor(s, rng, fp, mats):
    """The crater floor: a closed slab whose top is the torn outline (EDGE) rising to the charred lip
    (LIP) and dropping to the floor (FLOOR). Returns the outline loop (px)."""
    char, char2 = mats
    f, off = blur(fp, 1.1)
    loop = smooth(resample(contour(f, off), 0.5), 1, 2)
    n = len(loop)
    nin = normals_in(loop)
    # Torn: a slow wobble, a faster ragged tear, and small teeth.
    tear = noise1(rng, n, [(5, 0.5), (11, 0.35), (23, 0.25), (41, 0.15)]) + smooth(np.array([rng.uniform(-0.35, 0.35) for _ in range(n)]), 1, 1)
    # Sharp tears: short spikes of torn edge reaching out over the dirt.
    for _ in range(n // 14):
        i, w, a = rng.randrange(n), rng.randint(2, 4), rng.uniform(0.4, 1.1)
        for k in range(-w, w + 1):
            tear[(i + k) % n] += a * (1 - abs(k) / (w + 1))
    outer = loop - nin * (tear[:, None] - 0.2)
    nin0 = nin
    nin = normals_in(smooth(outer, 2, 2))
    # The lip and floor insets, clamped where the outline is narrow (the dirt channel down between
    # the lobes) so the two sides never cross: at most a share of the width straight across.
    across = np.array([width_in(f, off, p, d) for p, d in zip(loop, nin0)]) + tear - 0.2
    across = np.min([np.roll(across, k) for k in range(-6, 7)], axis=0)  # the narrowest nearby
    lipw = np.minimum(1.5 + noise1(rng, n, [(7, 0.4), (17, 0.25)]), 0.28 * across)
    lip = smooth(outer + nin * lipw[:, None], 1, 2)
    inner = untangle(smooth(outer + nin * np.minimum(lipw + 1.2, 0.42 * across)[:, None], 2, 4))
    lip = untangle(lip)
    for name, q in (("outer", outer), ("lip", lip), ("inner", inner)):
        k = crossings(q)
        if k:
            raise AssertionError(f"wreck floor: the {name} loop crosses itself ({k})")
    lipz = LIP + noise1(rng, n, [(9, 0.012), (19, 0.008)])

    bm = bmesh.new()
    V = lambda p, z: bm.verts.new((s.x(p[0]), s.y(p[1]), z))  # noqa: E731
    vb = [V(p, BOTTOM) for p in outer]
    vo = [V(p, EDGE) for p in outer]
    vl = [V(p, z) for p, z in zip(lip, lipz)]
    vi = [V(p, FLOOR) for p in inner]
    for a, b, m in ((vb, vo, char2), (vo, vl, char2), (vl, vi, char)):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = m
    top = bm.faces.new(vi)
    top.material_index = char
    bot = bm.faces.new(list(reversed(vb)))
    bot.material_index = char2
    bmesh.ops.triangulate(bm, faces=[top, bot], quad_method="BEAUTY", ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)
    return outer, inner


def inside(poly, px, py):
    x, y = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    c = ((y > py) != (y2 > py)) & (px < (x2 - x) * (py - y) / np.where(y2 == y, 1e-9, y2 - y) + x)
    return bool(np.count_nonzero(c) % 2)


# --- Pieces ---------------------------------------------------------------------------------------

def torn(s, rng, cx, cy, rx, ry, ang_deg, z0, z1, mat, n=7, tilt=(0.0, 0.0), rough=0.35):
    """A torn flat piece (patch, slab, chip): an irregular n-gon of radii ~(rx, ry) px turned by
    `ang_deg`, from z0 to a top at z1 tilted by `tilt` (units per px along its own x, y)."""
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    bm = bmesh.new()
    lo, hi = [], []
    for i in range(n):
        t = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / n
        f = rng.uniform(1 - rough, 1.0)
        u, v = rx * f * math.cos(t), ry * f * math.sin(t)
        px, py = cx + u * ca - v * sa, cy + u * sa + v * ca
        lo.append(bm.verts.new((s.x(px), s.y(py), z0)))
        hi.append(bm.verts.new((s.x(px), s.y(py), max(z0 + 0.004, z1 + tilt[0] * u + tilt[1] * v))))
    bm.faces.new(hi).material_index = mat
    bm.faces.new(list(reversed(lo))).material_index = mat
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def plate(s, rng, x0, x1, ybase, ytop, ztop, segs, mats, thick_px=0.6, yaw_deg=0.0, z0=-0.02, roll_px=0.0, notch=True):
    """A broad torn plate standing on the floor from row `ybase` (z0), leaning back so that its top
    edge reaches row `ytop` at `ztop`: strips across its width, a flat but torn top edge (heights
    varied a little, one notch), `thick_px` thick. Returns the top edge [(px, py, z)]."""
    n = segs + 1
    xs = [x0 + (x1 - x0) * i / segs for i in range(n)]
    tops = [ztop * (rng.uniform(0.72, 0.88) if i in (0, n - 1) else rng.uniform(0.86, 1.0)) for i in range(n)]
    if notch and n > 3:
        k = rng.randrange(1, n - 1)
        tops[k] *= rng.uniform(0.72, 0.85)
    cx, cy = (x0 + x1) / 2, ybase
    yaw = math.radians(yaw_deg)

    def pt(px, py, z):
        dx, dy = px - cx, py - cy
        return (s.x(cx + dx * math.cos(yaw) - dy * math.sin(yaw)), s.y(cy + dx * math.sin(yaw) + dy * math.cos(yaw)), z)

    def yat(z):
        return ybase + (ytop - ybase) * (z - z0) / (ztop - z0)

    bm = bmesh.new()
    front, back, edge = [], [], []
    for i, px in enumerate(xs):
        zt = tops[i]
        jx = (rng.uniform(-0.25, 0.25) if 0 < i < n - 1 else 0.0) + roll_px * (zt - z0) / (ztop - z0)
        fb = bm.verts.new(pt(px, ybase, z0))
        ft = bm.verts.new(pt(px + jx, yat(zt), zt))
        bb = bm.verts.new(pt(px, ybase - thick_px, z0))
        bt = bm.verts.new(pt(px + jx, yat(zt) - thick_px, zt))
        front.append((fb, ft))
        back.append((bb, bt))
        edge.append((px + jx, yat(zt), zt))
    for i in range(segs):
        mi = mats[rng.randrange(len(mats))]
        (fb0, ft0), (fb1, ft1) = front[i], front[i + 1]
        (bb0, bt0), (bb1, bt1) = back[i], back[i + 1]
        for quad in ((fb0, fb1, ft1, ft0), (bb1, bb0, bt0, bt1), (ft0, ft1, bt1, bt0), (fb1, fb0, bb0, bb1)):
            bm.faces.new(quad).material_index = mi
    for (fb, ft), (bb, bt) in ((front[0], back[0]), (front[-1], back[-1])):
        bm.faces.new((fb, ft, bt, bb)).material_index = mats[0]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)
    return yaw_deg


def bar(s, rng, x0, y0, x1, y1, w, z0, z1, mat):
    """A thin rusted bar (a box) from (x0, y0) to (x1, y1), w px wide, its far end a little lower."""
    L = math.hypot(x1 - x0, y1 - y0) / 2
    a = math.atan2(y1 - y0, x1 - x0)
    ca, sa = math.cos(a), math.sin(a)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bm = bmesh.new()
    lo, hi = [], []
    for u, v in ((-L, -w / 2), (L, -w / 2), (L, w / 2), (-L, w / 2)):
        px, py = cx + u * ca - v * sa, cy + u * sa + v * ca
        lo.append(bm.verts.new((s.x(px), s.y(py), z0)))
        hi.append(bm.verts.new((s.x(px), s.y(py), z1 - (0.02 if u > 0 else 0.0))))
    bm.faces.new(hi).material_index = mat
    bm.faces.new(list(reversed(lo))).material_index = mat
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def build():
    s = tb.Structure("wreck")
    rng = random.Random("tyrbld-wreck-v4")
    g = s.grid

    # The wreck's outline: the near-black (32) and grey (ramp 0) pixels, closed, small specks of
    # dirt inside it filled, stray specks outside dropped.
    dark = (g == 32) | ((g >= 0) & (g < 16))
    fp = lb.close(dark, 2)
    fp = lb.drop_small(lb.open_(fp, 1), 60)
    holes = s.cover & ~fp
    fp |= holes & ~lb.drop_small(holes, 30)
    # The dirt tongue down from the top between the two lobes (the art's dip, the concept's dirt).
    fp &= ~s.ellipse_mask(TONGUE[0], TONGUE[1], TONGUE[2], TONGUE[3])
    s.set_footprint(fp)

    char, char2, ash = s.m(1), s.m(32), s.m(4)
    mk = dict(metallic=0.35, roughness=0.65)
    steel, steel_lt, steel_dk = s.m(4, **mk), s.m(5, **mk), s.m(3, **mk)
    rust, rust_dk, rust_lt = s.m(20, roughness=0.75), s.m(18, roughness=0.8), s.m(21, roughness=0.7)
    dirt = [s.m(19, roughness=0.95), s.m(20, roughness=0.95), s.m(18, roughness=0.95)]
    plate_mats = [steel, steel_dk, steel, rust_dk, steel_lt, rust]

    # The floor, its torn lip and outline.
    outer, inner = floor(s, rng, s.footprint, (char, char2))

    def ok(px, py, margin_poly=inner):
        return inside(margin_poly, px, py)

    # Brown dirt breaking through: broad low patches with lumps on them.
    for cx, cy, rx, ry, ang in DIRT_PATCHES:
        torn(s, rng, cx, cy, rx, ry, ang, FLOOR - 0.01, FLOOR + 0.012, rng.choice(dirt), n=9, rough=0.3)
        for _ in range(int(rx * ry / 4)):
            t, f = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random()) * 0.7
            a = math.radians(ang)
            u, v = rx * f * math.cos(t), ry * f * math.sin(t)
            px, py = cx + u * math.cos(a) - v * math.sin(a), cy + u * math.sin(a) + v * math.cos(a)
            r = rng.uniform(0.7, 1.4)
            s.knob(px, py, r, FLOOR, FLOOR + rng.uniform(0.03, 0.06), mat=rng.choice(dirt), sides=rng.choice((5, 6, 7)),
                   angle=rng.random() * math.pi, bevel=0.5, ry_px=r * rng.uniform(0.7, 1.0))

    # Charred lumps just inside the lip: small, varied, never past the outline.
    n = len(inner)
    for i in range(0, n, 9):
        if rng.random() < 0.35:
            continue
        nin = normals_in(inner)[i]
        px, py = inner[i] + nin * rng.uniform(0.6, 1.6)
        r = rng.uniform(0.6, 1.5)
        s.knob(px, py, r, FLOOR - 0.01, FLOOR + rng.uniform(0.03, 0.07), mat=rng.choice([char2, char, s.m(3)]),
               sides=rng.choice((4, 5, 6)), angle=rng.random() * math.pi, bevel=0.4, ry_px=r * rng.uniform(0.6, 1.0))

    # The hull plates: broad, flat torn tops, varied lean; two bent, one fallen.
    taken = np.zeros_like(fp)
    for x0, x1, yb, yt, zt, segs, kind in PLATES:
        yaw = rng.uniform(-12, 12)
        taken |= s.box_mask(x0 - 1, yt - 1.5, x1 + 1, yb + 1)
        if kind == "up":
            plate(s, rng, x0, x1, yb, yt + rng.uniform(-1, 1), zt, segs, plate_mats, yaw_deg=yaw, roll_px=rng.uniform(-1.0, 1.0))
        elif kind == "bent":
            zk = zt * 0.55
            yk = yb - (yb - yt) * 0.3
            plate(s, rng, x0, x1, yb, yk, zk, segs, plate_mats, yaw_deg=yaw, notch=False)
            # The upper half folded back, its edge lower than an upright plate's.
            plate(s, rng, x0 + 0.3, x1 - 0.3, yk + 0.3, yt - 2.5, zt * 0.8, segs, plate_mats, yaw_deg=yaw + rng.uniform(-6, 6),
                  z0=zk - 0.02, roll_px=rng.uniform(-1.5, 1.5))
        else:
            plate(s, rng, x0, x1, yb, yt, zt, segs, plate_mats, yaw_deg=yaw + 15, thick_px=0.5)
    for x0, x1, yb, yt, zt, segs in SHARDS:
        plate(s, rng, x0, x1, yb, yt, zt, segs, [steel_lt, steel, rust], thick_px=0.5, yaw_deg=rng.uniform(-25, 25), notch=False)

    # Fallen plates: torn, tilted, the bigger ones broken in two.
    for cx, cy, hx, hy, ang, zt, pieces in SLABS:
        a = math.radians(ang)
        for k in range(pieces):
            off = (k - (pieces - 1) / 2) * hx * 1.05
            px, py = cx + off * math.cos(a), cy + off * math.sin(a)
            torn(s, rng, px, py, hx / pieces * 1.1, hy * rng.uniform(0.8, 1.1), ang + rng.uniform(-15, 15), FLOOR - 0.01, zt,
                 rng.choice([steel_dk, steel, rust_dk]), n=rng.choice((5, 6)), tilt=(rng.uniform(-0.012, 0.012), rng.uniform(-0.02, 0.02)),
                 rough=0.3)
    for x0, y0, x1, y1, w, zt in BARS:
        bar(s, rng, x0, y0, x1, y1, w, FLOOR - 0.01, zt, rng.choice([rust, rust_dk, rust_lt]))

    # The debris fields: dense fine chips and thin rusted bars.
    chips = bars = 0
    for x0, y0, x1, y1, nc, nb, kind in FIELDS:
        chip_mats = [steel_lt, steel, steel, rust, rust_lt, ash] if kind == "metal" else [char2, s.m(3), ash, steel_dk, rust_dk]
        tries = 0
        while nc > 0 and tries < 4000:
            tries += 1
            px, py = rng.uniform(x0, x1), rng.uniform(y0, y1)
            if not ok(px, py) or taken[int(py), int(px)]:
                continue
            r = rng.uniform(0.35, 0.9)
            torn(s, rng, px, py, r, r * rng.uniform(0.5, 1.0), rng.uniform(0, 180), FLOOR - 0.005, FLOOR + rng.uniform(0.01, 0.045),
                 rng.choice(chip_mats), n=rng.choice((4, 5)), rough=0.35,
                 tilt=(rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02)))
            nc -= 1
            chips += 1
        tries = 0
        while nb > 0 and tries < 4000:
            tries += 1
            px, py = rng.uniform(x0, x1), rng.uniform(y0, y1)
            L, a = rng.uniform(1.5, 4.5), rng.uniform(0, math.pi)
            qx, qy = px + L * math.cos(a), py + L * math.sin(a)
            if not (ok(px, py) and ok(qx, qy)) or taken[int(py), int(px)]:
                continue
            bar(s, rng, px, py, qx, qy, rng.uniform(0.3, 0.45), FLOOR - 0.005, FLOOR + rng.uniform(0.025, 0.05),
                rng.choice([rust, rust_dk, rust_dk]))
            nb -= 1
            bars += 1
    # Chips where the art paints small grey specks, away from the plates.
    grey = (g >= 3) & (g < 16)
    for cx, cy, rx, ry, ang in s.blobs(grey & s.footprint & ~taken, min_px=2):
        if rx * ry > 12 or not ok(cx, cy):
            continue
        r = max(0.6, min(1.2, (rx + ry) / 2))
        torn(s, rng, cx, cy, r, r * 0.8, math.degrees(ang), FLOOR - 0.005, FLOOR + rng.uniform(0.02, 0.05),
             rng.choice([steel_lt, steel, rust, ash]), n=5, rough=0.35)
        chips += 1
    print(f"wreck: {chips} chips, {bars} bars")

    objects = s.objects()
    s.check(objects)
    s.export(objects)


build()
