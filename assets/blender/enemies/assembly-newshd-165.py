"""Giant stone face (newshd 155/165 + newshp 123/127, one 48x56 carving), carved-rock rebuild (D120/D122, D125/D148).

What it is: a giant bald head carved in the asteroid's rock, lying face up, crown to the top of the
screen; a static ground carving beside the HD shapesz bricks. Design B leads with what reads from
the game's camera (Tilted, 15 deg from straight down, game sun from the left and the camera side):
  1. SMOOTH FORM: the sprite's inner-mask footprint (D74) x a pchip profile down the face x a
     superellipse section, plus the face's forms pushed for readability: a dressed forehead plane
     (the sprite's bright 9 patch, a lit face, rock rule), a brow bar with a steep fall into deep
     sockets, closed lid mounds, a wedge nose with a crest and wings, cheekbone blocks, a lip block
     with a deep mouth cut, a chin boss.
  2. CHISELLED: Poisson-disc seeds; each seed's least-squares plane of the smooth form, and the
     surface is the MIN of the nearest planes (a cut-stone polyhedron: straight, crisp creases
     between lit planar facets, D125/D148 rock language). Big facets on the skull and jaw, smaller
     ones blended toward the smooth form on the face so brow, sockets, nose, lips and chin hold.
  3. CUTS: V-groove cracks on the D87 damage paths (163/125/167/129 darken exactly these), crevices
     on a hashed share of the skull's facet borders, spalls (shallow chipped pits), the lid lines,
     mouth, under-nose and nasolabial grooves.
  4. PALETTE (rule 1 + rock rule): each region's sprite index (stone 5, forehead / nose / lips /
     cheeks / chin a step lighter, sockets 2-3), shifted by how the facet faces the game sun
     (D148 facet_index), grooves fixed dark. Matte (roughness 0.88, metallic 0).
  5. BAKE: AO at two scales + edge lift + a grime mottle that only darkens (D148/D150 GRIT-like),
     roughness from the same terms; "bake": "model" (D65), no projection. One 512 atlas per piece.
  6. Built whole, cut into the four 24x28 pieces (split_assembly), outline shell (D51) as a ring
     only (its tops over the carving removed, as D121 fix 2), cut open per piece.
Underside: a flat closed base at z 0 (plausible closed shape only).

Exports the four pieces through common.export_sprite_model (public/models/enemies/<piece>.glb and
src/render/spriteModels/<piece>.json); review renders and colours.json go to the scratch folder.
Final pass: crown peaks clamped (the chisel never rises more than 0.4 px over the smooth form), the
forehead plate on pal 9 with only the two D87 cracks crossing it, sockets with a wide chamfered rim
and a lid that sits flush (a recess under the brow), region bases at the sprite medians.

Coordinates: sprite edge px (x right, y down) of the 48x56 assembly; model X = (x - 24) / 12,
Y = (28 - y) / 12, Z = z / 12.
Run: tools/build-models.sh -j 2 assets/blender/enemies/assembly-newshd-165.py (extra args after --: [--no-bake] [--renders DIR])
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask  # noqa: E402

HERE = Path("/Users/dlomibao/projects/tyrian-scratch/user-models/assembly-newshd-165/final")
HERE.mkdir(parents=True, exist_ok=True)
NAME = "assembly-newshd-165"
TAG = "nshd165"
W, H = 48, 56
PIECES = {"newshd-155": (0, 0), "newshp-123": (24, 0), "newshd-165": (0, 28), "newshp-127": (24, 28)}
SUN = np.array([-6.0, -8.4, 20.0]) / 22.47   # the game's sun (src/render/view.ts) in model axes

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ---------------------------------------------------------------------------------------------
# Footprint: the INNER mask of the composed assembly (D74), rows averaged over 3, crown and chin
# rounded (as the blueprint: IoU 0.998).
# ---------------------------------------------------------------------------------------------
IDX, COLORS = sprite_mask.load(NAME)
MASKS = sprite_mask.masks(IDX, COLORS)
INNER = np.array(MASKS["inner"], bool)
_raw = []
for r in range(H):
    c = np.nonzero(INNER[r])[0]
    if len(c):
        _raw.append((r + 0.5, c.min(), c.max() + 1.0))
EDGE = []
for i, (y, _, _) in enumerate(_raw):
    n = _raw[max(0, i - 1):i + 2]
    EDGE.append((y, sum(q[1] for q in n) / len(n), sum(q[2] for q in n) / len(n)))
(y0_, a0, b0), (y1_, a1, b1) = EDGE[0], EDGE[-1]
EDGE = [(y0_ - 0.5, a0 + 1.6, b0 - 1.6), (y0_ - 0.15, a0 + 0.35, b0 - 0.35)] + EDGE + \
       [(y1_ + 0.2, a1 + 0.5, b1 - 0.5), (y1_ + 0.5, a1 + 1.3, b1 - 1.3)]
EDGE = np.array(EDGE)
Y_TOP, Y_BOT = EDGE[0, 0], EDGE[-1, 0]


def edges_at(y):
    return np.interp(y, EDGE[:, 0], EDGE[:, 1]), np.interp(y, EDGE[:, 0], EDGE[:, 2])


def u_across(x, y):
    l, r = edges_at(y)
    return np.clip(np.abs(x - (l + r) / 2) / np.maximum((r - l) / 2, 0.3), 0, 1)


def in_foot(x, y):
    l, r = edges_at(y)
    return (y >= Y_TOP) & (y <= Y_BOT) & (x >= l) & (x <= r)


# ---------------------------------------------------------------------------------------------
# 1. smooth form (px)
# ---------------------------------------------------------------------------------------------
def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson), vectorised."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        x = np.clip(np.asarray(x, float), xs[0], xs[-1])
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


PROFILE = pchip([3.5, 4.5, 6.5, 9.5, 13.5, 18, 21.5, 25, 30, 35, 40, 44, 47, 49.5, 51, 52.2],
                [0.6, 2.6, 4.9, 6.8, 8.0, 8.6, 8.9, 8.2, 7.9, 7.6, 7.2, 6.6, 5.6, 4.0, 2.3, 0.6])
SECTION_P = 2.4


def base_z(x, y):
    t = u_across(x, y)
    return PROFILE(y) * np.power(np.clip(1 - np.power(t, SECTION_P), 0, 1), 1 / SECTION_P)


def sd_ell(x, y, cx, cy, rx, ry):   # + inside
    return (1 - np.hypot((x - cx) / rx, (y - cy) / ry)) * min(rx, ry)


def sd_rrect(x, y, x0, x1, y0, y1, r):
    hx, hy = (x1 - x0) / 2 - r, (y1 - y0) / 2 - r
    qx, qy = np.abs(x - (x0 + x1) / 2) - hx, np.abs(y - (y0 + y1) / 2) - hy
    return -(np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r)


def sd_cap(x, y, ax, ay, bx, by, r):
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0, 1)
    return r - np.hypot(x - ax - t * dx, y - ay - t * dy)


def sd(shape, x, y):
    k, a = shape
    return {"ell": sd_ell, "rrect": sd_rrect, "cap": sd_cap}[k](x, y, *a)


# Forms (positions from the sprite). Design B: brow, sockets, nose and mouth pushed so the face
# reads at the game's scale; chamfer c = width (px) of the slope inside the shape.
FORMS = [
    ("brow", ("cap", (15.0, 21.6, 34.0, 21.6, 1.5)), 1.1, 0.9),
    ("socket_L", ("ell", (18.9, 25.3, 4.6, 2.9)), -2.7, 1.9),
    ("socket_R", ("ell", (30.3, 25.4, 4.5, 2.9)), -2.7, 1.9),
    ("nostril_L", ("ell", (22.7, 33.9, 1.6, 1.15)), 1.5, 0.8),
    ("nostril_R", ("ell", (27.2, 33.9, 1.6, 1.15)), 1.5, 0.8),
    ("cheek_L", ("ell", (17.0, 31.2, 3.9, 2.9)), 1.2, 2.0),
    ("cheek_R", ("ell", (31.8, 31.3, 3.7, 2.9)), 1.2, 2.0),
    ("lip_upper", ("ell", (24.2, 38.4, 5.0, 1.7)), 1.05, 1.3),
    ("lip_lower", ("ell", (24.0, 41.6, 4.1, 1.3)), 0.95, 1.0),
    ("chin", ("ell", (23.8, 45.4, 4.7, 2.8)), 1.0, 1.7),
]
NOSE = dict(x=25.0, y0=22.0, tip=33.5, end=35.6, h=3.35)
FOREHEAD = dict(shape=("rrect", (17.2, 31.4, 10.6, 21.0, 3.2)), z0=9.25, gx=0.06, gy=0.05, c=1.3)
FACE_C = (24.6, 33.0, 11.5, 14.0)


def nose_delta(x, y):
    """A chamfered stone wedge (fix 1: was a triangular crest that read as a thorn): a flat bridge
    plane (half-width bt) that widens down the face, chamfered shoulders (a shallow 0.55 px/px
    slope), steep cut sides out to the base half-width w; the tip is blunt and rounded (in profile
    the bridge rolls over with zero slope at the tip; in plan the wedge closes as a half-ellipse)."""
    s = np.clip((y - NOSE["y0"]) / (NOSE["tip"] - NOSE["y0"]), 0, 1)
    h = 0.7 + (NOSE["h"] - 0.7) * np.power(s, 1.2)
    w = 1.35 + 1.55 * s
    bt = 0.35 + 0.6 * s
    u = np.clip((y - NOSE["tip"]) / (NOSE["end"] - NOSE["tip"]), 0, 1)
    after = y > NOSE["tip"]
    roll = np.sqrt(np.clip(1 - u * u, 0, 1))        # plan: half-ellipse closing the tip
    h = np.where(after, NOSE["h"] * (1 - np.power(u, 1.8)) * (1 - 0.25 * u), h)   # blunt roll-over
    w = np.where(after, w * (0.45 + 0.55 * roll), w)
    bt = np.where(after, bt * roll, bt)
    ax = np.abs(x - NOSE["x"])
    side = h * (w - ax) / np.maximum(w - bt - 0.35, 0.3)       # steep cut side
    cham = h - 0.55 * np.maximum(ax - bt, 0)                     # chamfered shoulder
    v = np.clip(np.minimum(np.minimum(h, cham), side), 0, None)
    return np.where((y >= NOSE["y0"]) & (y <= NOSE["end"]), v, 0.0)


def smooth_z(x, y):
    b = base_z(x, y)
    z = b.copy()
    parts = {}
    wf = np.clip(sd(FOREHEAD["shape"], x, y) / FOREHEAD["c"], 0, 1)
    p = FOREHEAD["z0"] + FOREHEAD["gx"] * (x - 24.3) + FOREHEAD["gy"] * (y - 15.8)
    z = z * (1 - wf) + np.maximum(p, z - 0.2) * wf
    parts["forehead"] = wf
    for name, shape, h, c in FORMS:
        if name.startswith("eyelid"):
            continue
        if name.startswith("socket"):
            # closed eye: a pocket deep under the brow whose lower part the lid mound fills flush,
            # so only a dark crescent stays open at the top (the sprite's dark rows 23-24)
            cx, cy, rx, ry = shape[1]
            w = np.clip(sd(shape, x, y) / c, 0, 1)
            k = np.hypot((x - cx) / (rx - 0.1), (y - (cy + 0.9)) / (ry + 0.3))
            lid = (-h - 0.15) * np.sqrt(np.clip(1 - k * k, 0, 1))
            parts[name] = h * w
            parts["eyelid" + name[6:]] = np.where(k < 0.92, lid, 0.0) * w
            z = z + w * (h + lid)
            continue
        v = h * np.clip(sd(shape, x, y) / c, 0, 1)
        parts[name] = v
        z = z + v
    parts["nose"] = nose_delta(x, y)
    # nostril wings sit beside the wedge, not stacked on it: max, not sum (fix 1)
    wings = np.maximum(parts["nostril_L"], parts["nostril_R"])
    z = z - wings + np.maximum(parts["nose"], wings)
    t = u_across(x, y)
    z = b + (z - b) * np.clip((1 - t) / 0.12, 0, 1)
    return z, parts


REGIONS = ["cranium", "forehead", "brow", "midface", "socket", "socket_top", "nose", "eyelid", "cheek",
           "jaw", "lips", "chin", "crack", "crevice", "lidline", "mouth", "groove", "wall", "underside"]
RI = {r: i for i, r in enumerate(REGIONS)}


def region_of(x, y, parts):
    reg = np.where(y < 22, RI["cranium"], np.where(y < 35.5, RI["midface"], RI["jaw"]))
    order = [  # lowest priority first; later ones overwrite
        ((parts["cheek_L"] > 0.3) | (parts["cheek_R"] > 0.3), "cheek"),
        (parts["chin"] > 0.3, "chin"),
        ((parts["lip_upper"] > 0.3) | (parts["lip_lower"] > 0.3), "lips"),
        (parts["forehead"] > 0.5, "forehead"),
        ((parts["brow"] > 0.3) & (y > 20.3), "brow"),
        ((parts["nose"] > 0.3) | (parts["nostril_L"] > 0.4) | (parts["nostril_R"] > 0.4), "nose"),
        ((parts["socket_L"] < -0.3) | (parts["socket_R"] < -0.3), "socket"),
        ((parts["eyelid_L"] > 0.8) | (parts["eyelid_R"] > 0.8), "eyelid"),
        (((parts["socket_L"] < -0.3) | (parts["socket_R"] < -0.3)) & (y < 24.3), "socket_top"),
    ]
    for m, r in order:
        reg = np.where(m, RI[r], reg)
    return reg


def face_zone(x, y):
    cx, cy, rx, ry = FACE_C
    return (y > 20.3) & (y < 48.5) & (np.hypot((x - cx) / rx, (y - cy) / ry) < 1)


# ---------------------------------------------------------------------------------------------
# 2. chiselled facets
# ---------------------------------------------------------------------------------------------
R_FACE, R_SKULL, R_FORE = 2.4, 3.1, 3.6


def cell_r(x, y):
    if sd(FOREHEAD["shape"], np.array(x), np.array(y)) > 0.6:
        return R_FORE
    if face_zone(np.array(x), np.array(y)):
        return R_FACE
    return R_SKULL


def make_seeds():
    rng = np.random.default_rng(165)
    seeds = []
    kd_pts = []
    for _ in range(60000):
        if len(seeds) >= 700:
            break
        x, y = 9 + rng.random() * 31, Y_TOP + rng.random() * (Y_BOT - Y_TOP)
        if not in_foot(np.array(x), np.array(y)):
            continue
        r = cell_r(x, y)
        ok = all(math.hypot(sx - x, sy - y) >= min(r, sr) for sx, sy, sr in kd_pts
                 if abs(sx - x) < 4 and abs(sy - y) < 4)
        if ok:
            kd_pts.append((x, y, r))
            seeds.append(dict(x=x, y=y, r=r, jx=rng.random() - 0.5, jy=rng.random() - 0.5,
                              lift=rng.random(), pit=rng.random()))
    return seeds


SEEDS = make_seeds()
SX = np.array([s["x"] for s in SEEDS])
SY = np.array([s["y"] for s in SEEDS])
KD = KDTree(len(SEEDS))
for i, s in enumerate(SEEDS):
    KD.insert((s["x"], s["y"], 0.0), i)
KD.balance()


def nearest(x, y, k):
    """(ids, dists) arrays [N, k] of the k nearest seeds."""
    ids = np.zeros((len(x), k), int)
    ds = np.zeros((len(x), k))
    for n, (px, py) in enumerate(zip(x, y)):
        res = KD.find_n((float(px), float(py), 0.0), k)
        for j, (co, i, d) in enumerate(res):
            ids[n, j], ds[n, j] = i, d
    return ids, ds


def fit_planes():
    """Least-squares plane z = a + b (x - sx) + c (y - sy) per seed cell, from the smooth form
    sampled every 0.2 px; then a small random tilt (fracture faces)."""
    gx, gy = np.meshgrid(np.arange(8.0, 41.0, 0.2), np.arange(Y_TOP, Y_BOT, 0.2))
    gx, gy = gx.ravel(), gy.ravel()
    keep = in_foot(gx, gy)
    gx, gy = gx[keep], gy[keep]
    z, _ = smooth_z(gx, gy)
    ids, _ = nearest(gx, gy, 1)
    ids = ids[:, 0]
    P = np.zeros((len(SEEDS), 3))
    for i, s in enumerate(SEEDS):
        m = ids == i
        if m.sum() < 6:
            P[i] = (z[m].mean() if m.any() else 0, 0, 0)
            continue
        A = np.stack([np.ones(m.sum()), gx[m] - s["x"], gy[m] - s["y"]], 1)
        P[i] = np.linalg.lstsq(A, z[m], rcond=None)[0]
        fz = face_zone(np.array(s["x"]), np.array(s["y"]))
        j = 0.025 if fz else 0.085
        P[i, 1] += s["jx"] * 2 * j
        P[i, 2] += s["jy"] * 2 * j
        # lift: each plane a little proud so the min of the planes sits on the form, not under it
        P[i, 0] += 0.18 + (0.0 if fz else 0.12 * s["lift"])
    return P


PLANES = fit_planes()
_sp = smooth_z(SX, SY)[1]
SEED_CHEEK = (np.maximum(_sp["cheek_L"], _sp["cheek_R"]) > 0.3) & (_sp["nose"] < 0.3) & \
    (np.minimum(_sp["socket_L"], _sp["socket_R"]) > -0.3)
print("cheek facets", int(SEED_CHEEK.sum()))


def hash2(i, j):
    a, b = np.minimum(i, j), np.maximum(i, j)
    h = (a * 73856093) ^ (b * 19349663)
    h = (h * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0xFFFFFF)


# ---------------------------------------------------------------------------------------------
# 3. cuts
# ---------------------------------------------------------------------------------------------
CRACKS = [
    ([(17.6, 6.6), (20.2, 7.6), (23.2, 8.5), (25.8, 8.0), (28.4, 6.3), (28.6, 4.3)], 0.6, 0.95),
    ([(30.6, 8.6), (29.6, 11.2), (28.6, 13.6), (27.2, 15.6), (25.4, 17.4), (24.0, 18.6), (23.4, 20.4),
      (23.8, 22.2)], 0.55, 0.9),
    ([(35.2, 9.4), (34.4, 11.0), (32.6, 12.5)], 0.5, 0.75),
    ([(33.0, 16.0), (34.6, 17.2), (36.4, 18.3), (37.6, 20.4)], 0.5, 0.75),
    ([(12.4, 13.0), (14.0, 14.8), (15.2, 16.5), (17.4, 16.6), (20.4, 16.6), (22.6, 17.6), (24.4, 18.2)], 0.55, 0.85),
    ([(14.6, 16.4), (14.2, 18.2), (12.8, 19.8)], 0.45, 0.6),
    ([(13.4, 35.2), (14.8, 36.6), (16.2, 38.2), (17.2, 39.6), (16.6, 41.4), (17.4, 43.6), (18.4, 45.4),
      (18.6, 47.6), (19.6, 48.6)], 0.42, 0.6),
    ([(30.2, 36.0), (32.0, 37.8), (33.4, 39.4)], 0.36, 0.45),
    ([(29.6, 39.8), (28.4, 41.4), (28.4, 44.0), (29.2, 46.2)], 0.34, 0.42),
]
CUTS = [
    ("lidline", ("cap", (16.4, 24.9, 21.4, 24.9, 0.35)), 0.6),
    ("lidline", ("cap", (27.8, 25.0, 32.8, 25.0, 0.35)), 0.6),
    ("mouth", ("ell", (24.0, 40.1, 5.5, 0.55)), 1.2),
    ("groove", ("cap", (21.8, 35.5, 28.2, 35.5, 0.5)), 0.55),
    ("groove", ("cap", (21.2, 35.0, 19.6, 38.0, 0.3)), 0.35),
    ("groove", ("cap", (28.6, 35.0, 30.0, 38.0, 0.3)), 0.35),
]


def crack_dist(pts, x, y):
    best = np.full(x.shape, 1e9)
    tat = np.zeros(x.shape)
    seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    tot, L = sum(seg), 0.0
    for (ax, ay), (bx, by), l in zip(pts, pts[1:], seg):
        dx, dy = bx - ax, by - ay
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / (l * l), 0, 1)
        d = np.hypot(x - ax - t * dx, y - ay - t * dy)
        m = d < best
        best = np.where(m, d, best)
        tat = np.where(m, (L + t * l) / tot, tat)
        L += l
    return best, tat


def surface(x, y):
    """(z px, region index, facet seed id) for arrays x, y inside the footprint."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    zs, parts = smooth_z(x, y)
    reg = region_of(x, y, parts)
    K = 5
    ids, ds = nearest(x, y, K)
    # min of the nearby planes (only those within reach, so a far plane never digs a pit)
    pz = PLANES[ids, 0] + PLANES[ids, 1] * (x[:, None] - SX[ids]) + PLANES[ids, 2] * (y[:, None] - SY[ids])
    # farther planes are lifted (continuous in x, y), so a far plane never digs a pit and the
    # surface has no seams where the nearest-seed set changes
    pz = pz + 1.6 * np.maximum(0.0, ds - ds[:, :1] - 0.9)
    j = pz.argmin(1)
    zp = pz[np.arange(len(x)), j]
    facet = ids[np.arange(len(x)), j]
    zp = np.maximum(zp, zs - 0.7)
    fz = face_zone(x, y)
    eyes = np.maximum(np.clip(sd(FORMS[1][1], x, y) / 1.2 + 0.7, 0, 1), np.clip(sd(FORMS[2][1], x, y) / 1.2 + 0.7, 0, 1))
    nose = np.clip(np.maximum(parts["nose"], np.maximum(parts["nostril_L"], parts["nostril_R"])) / 0.6, 0, 1)
    # cheekbones: whole facets (by their seed) are the cheek, fully planar, so the pal 7 region
    # ends on facet borders and reads as lit cheekbone planes (fix 1, rock rule)
    chk = SEED_CHEEK[facet]
    wf = np.where(fz, np.where(chk, 1.0, 0.7), 1.0) * (1 - eyes) * (1 - 0.55 * nose)
    # the chisel only cuts into the nose (never a raised point on the narrow ridge, fix 1)
    up = 0.4 * (1 - nose)
    z = zs + np.clip(zp - zs, -0.7 + 0.4 * nose, up) * wf
    low = np.isin(reg, [RI["cranium"], RI["midface"], RI["jaw"], RI["cheek"]])
    plain = np.where(y < 22, RI["cranium"], np.where(y < 35.5, RI["midface"], RI["jaw"]))
    reg = np.where(low, np.where(chk, RI["cheek"], plain), reg)
    # spalls: a few shallow chipped pits on skull facets (weathering)
    pit = np.array([SEEDS[i]["pit"] for i in facet])
    sx, sy = SX[facet], SY[facet]
    dpit = np.hypot(x - sx - 0.4, y - sy + 0.3)
    spall = (pit < 0.16) & ~fz & (parts["forehead"] < 0.3)
    z = z - np.where(spall, 0.45 * np.clip(1 - dpit / 1.1, 0, 1) ** 0.7, 0)
    # crevices: a hashed share of the facet borders off the face are V grooves (weathered joints)
    g = (ds[:, 1] - ds[:, 0]) / 2
    hs = hash2(ids[:, 0], ids[:, 1])
    crev = (~fz) & (parts["forehead"] < 0.5) & (g < 0.42) & (hs < 0.26)
    z = z - np.where(crev, 0.6 * np.clip(1 - (g / 0.42) ** 2, 0, 1) ** 1.5, 0)
    reg = np.where(crev & (g < 0.2), RI["crevice"], reg)
    for rname, shape, d in CUTS:
        v = sd(shape, x, y)
        z = z - d * np.clip((v + 0.25) / 0.45, 0, 1)
        reg = np.where(v > 0, RI[rname], reg)
    for pts, w, d in CRACKS:
        dd, t = crack_dist(pts, x, y)
        taper = np.clip(np.minimum(t, 1 - t) / 0.15, 0.25, 1)
        ww = w * 1.35 * taper
        z = z - np.where(dd < ww, d * taper * np.clip(1 - (dd / ww) ** 2, 0, 1) ** 1.5, 0)
        reg = np.where(dd < ww * 0.5, RI["crack"], reg)
    t = u_across(x, y)
    z = np.maximum(z * np.clip((1 - t) / 0.02, 0, 1), np.where(t < 0.98, 0.05, 0))
    return z, reg, facet


# ---------------------------------------------------------------------------------------------
# 4. palette
# ---------------------------------------------------------------------------------------------
BASE = {"cranium": 6, "forehead": 9, "brow": 6, "midface": 4, "socket": 3, "socket_top": 1, "nose": 5,
        "eyelid": 3, "cheek": 6, "jaw": 4, "lips": 8, "chin": 4, "crack": 2, "crevice": 3, "lidline": 2,
        "mouth": 2, "groove": 3, "wall": 3, "underside": 3}
FIXED = {"crack", "crevice", "lidline", "mouth", "groove", "wall", "underside", "socket_top"}


def shift_of(lam):
    """The game-sun lambert of a facet relative to a flat top (0.89): lit faces climb the ramp,
    faces turned away drop (D148 facet_index, rock rule)."""
    return np.select([lam >= 0.975, lam >= 0.86, lam >= 0.45], [2, 1, 0], -1)


def palette(reg, normals):
    lam = normals @ SUN
    base = np.array([BASE[REGIONS[r]] for r in reg])
    fixed = np.array([REGIONS[r] in FIXED for r in reg])
    return np.where(fixed, base, np.clip(base + shift_of(lam), 2, 10))


# ---------------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------------
def to_model(x, y, z):
    return ((x - 24) / 12, (28 - y) / 12, z / 12)


def build(coll, sprite):
    NC = 240
    NR = int(math.ceil((Y_BOT - Y_TOP) / 0.125))
    ys = np.linspace(Y_TOP, Y_BOT, NR + 1)
    l, r = edges_at(ys)
    X = l[:, None] + (r - l)[:, None] * np.linspace(0, 1, NC + 1)[None, :]
    Y = np.repeat(ys[:, None], NC + 1, 1)
    z, _, _ = surface(X.ravel(), Y.ravel())
    Z = z.reshape(X.shape)
    Z[:, 0] = Z[:, -1] = 0
    Z[0, :] = Z[-1, :] = 0
    bm = bmesh.new()
    vs = [[bm.verts.new(to_model(X[k, j], Y[k, j], Z[k, j])) for j in range(NC + 1)] for k in range(NR + 1)]
    for k in range(NR):
        for j in range(NC):
            a, b, c, d = vs[k][j], vs[k][j + 1], vs[k + 1][j + 1], vs[k + 1][j]
            # split each quad along its flatter diagonal (keeps crease lines straighter)
            if abs(a.co.z + c.co.z - b.co.z - d.co.z) < 1e-9 or \
                    abs(a.co.z - c.co.z) <= abs(b.co.z - d.co.z):
                bm.faces.new((a, c, b))
                bm.faces.new((a, d, c))
            else:
                bm.faces.new((a, d, b))
                bm.faces.new((b, d, c))
    # closing floor at z 0: the rim ring (crown row, right edge, chin row, left edge), facing down
    ring = ([vs[0][j] for j in range(NC + 1)] + [vs[k][NC] for k in range(1, NR + 1)]
            + [vs[NR][j] for j in range(NC - 1, -1, -1)] + [vs[k][0] for k in range(NR - 1, 0, -1)])
    bm.faces.new(ring)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    nz = sum(1 for f in bm.faces if f.normal.z < 0)
    print(f"faces facing down: {nz} of {len(bm.faces)}")
    # merge the planar facets (exact planes from the min-of-planes) into n-gons, then re-triangulate
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.6), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.normal_update()
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    print('validate', me.validate(verbose=False))
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # decimate the dense smooth-ish face zone a little (planar parts are already single n-gons)
    n0 = len(me.polygons)
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    target = float(ARGV[ARGV.index("--tris") + 1]) if "--tris" in ARGV else 20000
    dec.ratio = min(1.0, target / n0)
    dec.use_collapse_triangulate = True
    common._apply_modifiers(obj)
    print(f"faces {n0} -> {len(me.polygons)}")
    paint(obj, sprite)
    me.shade_flat()
    return obj


MATS = {}


def mat(sprite, idx):
    if idx not in MATS:
        MATS[idx] = common.palette_material(sprite, int(idx), TAG, metallic=0.0, roughness=0.88)
    return MATS[idx]


def paint(obj, sprite):
    me = obj.data
    n = len(me.polygons)
    cen = np.zeros(n * 3)
    nor = np.zeros(n * 3)
    me.polygons.foreach_get("center", cen)
    me.polygons.foreach_get("normal", nor)
    cen, nor = cen.reshape(n, 3), nor.reshape(n, 3)
    px, py = cen[:, 0] * 12 + 24, 28 - cen[:, 1] * 12
    top = (nor[:, 2] > -0.5) & (cen[:, 2] > 1e-4)
    inside = in_foot(px, py)
    reg = np.full(n, RI["wall"])
    ok = top & inside
    _, r, _ = surface(px[ok], py[ok])
    reg[ok] = r
    reg[nor[:, 2] < -0.5] = RI["underside"]
    pal = palette(reg, nor)
    idxs = sorted(set(pal.tolist()))
    me.materials.clear()
    for i in idxs:
        me.materials.append(mat(sprite, i))
    slot = {i: k for k, i in enumerate(idxs)}
    me.polygons.foreach_set("material_index", np.array([slot[i] for i in pal], np.int32))
    obj["regions"] = json.dumps({REGIONS[k]: int((reg == k).sum()) for k in set(reg.tolist())})
    # colour check: per region, the model's top-view palette index (area-weighted median of the
    # top faces) vs the sprite's trimmed median (pixels of that region, 15-85 % luma)
    area = np.zeros(n)
    me.polygons.foreach_get("area", area)
    proj = area * np.clip(nor[:, 2], 0, 1)
    gx, gy = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
    sel = INNER.ravel()
    _, parts = smooth_z(gx.ravel()[sel], gy.ravel()[sel])
    preg = region_of(gx.ravel()[sel], gy.ravel()[sel], parts)
    pidx = np.array(IDX).ravel()[sel]
    lum = {i: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for i, c in COLORS.items()}
    out = {}
    for k in sorted(set(preg.tolist())):
        v = sorted(pidx[preg == k].tolist(), key=lambda i: lum[i])
        lo, hi = int(len(v) * 0.15), max(int(len(v) * 0.85), int(len(v) * 0.15) + 1)
        mm = (reg == k) & ok
        if mm.any():
            o = np.argsort(pal[mm])
            cw = np.cumsum(proj[mm][o])
            model_med = int(pal[mm][o][np.searchsorted(cw, cw[-1] / 2)])
        else:
            model_med = None
        out[REGIONS[k]] = {"sprite_px": len(v), "sprite_median": int(v[lo:hi][len(v[lo:hi]) // 2]),
                           "model_median": model_med, "base": BASE[REGIONS[k]]}
    allm = ok & (proj > 0)
    hist = {int(i): round(float(proj[allm & (pal == i)].sum() / proj[allm].sum()), 3) for i in sorted(set(pal[allm].tolist()))}
    (HERE / "colours.json").write_text(json.dumps({"regions": out, "model_index_share": hist}, indent=1))


# ---------------------------------------------------------------------------------------------
# outline shell helpers (copied from the D121 script: ring only, cut open per piece)
# ---------------------------------------------------------------------------------------------
def in_carved_face(px, py):
    return (math.hypot((px - 24.6) / 11.5, (py - 33.5) / 15.5) < 1.0
            or float(sd_rrect(px, py, 13.0, 36.0, 4.0, 29.6, 2.5)) > 0.0)


def mask_shell(shell):
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    kill = [f for f in bm.faces if f.normal.z > 0.3 and f.calc_center_median().z > 0.02
            and in_carved_face(f.calc_center_median().x * 12 + 24, 28 - f.calc_center_median().y * 12)]
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()


def close_piece(obj):
    """Fix 1: the bisect at the crown and chin rows leaves a sub-0.04 unit sliver open on the base
    corner of each piece. Weld, collapse the tiny boundary edges and fill what is left."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    for _ in range(3):
        b = [e for e in bm.edges if e.is_boundary]
        if not b:
            break
        short = [e for e in b if e.calc_length() < 0.006]
        if short:
            bmesh.ops.collapse(bm, edges=short, uvs=True)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        b = [e for e in bm.edges if e.is_boundary]
        if b:
            bmesh.ops.holes_fill(bm, edges=b, sides=0)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    nb = sum(1 for e in bm.edges if e.is_boundary)
    bm.to_mesh(obj.data)
    bm.free()
    print(f"close {obj.name}: boundary edges {nb}")


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


# ---------------------------------------------------------------------------------------------
# 5. bake (copied from usp_talon.bake_maps, with a GRIT-like grime term; per object, own images)
# ---------------------------------------------------------------------------------------------
GRIT = dict(floor=0.42, occl=0.66, edge=0.2, grime=0.26, rough=0.18, scale=1.1)


def bake(obj, size=512, samples=32, grit=GRIT):
    scene = bpy.context.scene
    try:
        scene.render.engine = "CYCLES"
    except TypeError:
        pass
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # only the top surface gets atlas space: the floor and the piece's cut walls are never seen
    # from the game's camera (and only as a closed shape otherwise); they keep UV (0, 0)
    x0, y0 = obj.location.x, obj.location.y
    for poly in me.polygons:
        c = poly.center
        cut = (abs(abs(c.x) - 1.0) < 1e-3 and abs(poly.normal.x) > 0.99) or \
              (abs(abs(c.y) - 14 / 12) < 1e-3 and abs(poly.normal.y) > 0.99)
        poly.select = poly.normal.z > -0.5 and not cut
    for e in me.edges:
        e.select = False
    for v in me.vertices:
        v.select = False
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    col_img = bpy.data.images.new(f"{obj.name}_colour", size, size, alpha=False)
    rm_img = bpy.data.images.new(f"{obj.name}_rm", size // 2, size // 2, alpha=False)
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
        L = nt.links.new
        tmp = []

        def node(kind):
            n = nt.nodes.new(kind)
            tmp.append(n)
            return n

        def M(op, a, b=None):
            n = node("ShaderNodeMath")
            n.operation = op
            for k, v in enumerate((a, b)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        ao_s = node("ShaderNodeAmbientOcclusion")
        ao_s.samples = 24
        ao_s.inputs["Distance"].default_value = 0.05
        ao_l = node("ShaderNodeAmbientOcclusion")
        ao_l.samples = 24
        ao_l.inputs["Distance"].default_value = 0.28
        bev = node("ShaderNodeBevel")
        bev.samples = 8
        bev.inputs["Radius"].default_value = 0.006
        geo = node("ShaderNodeNewGeometry")
        dot = node("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        L(bev.outputs["Normal"], dot.inputs[0])
        L(geo.outputs["True Normal"], dot.inputs[1])
        edge = M("MINIMUM", M("MULTIPLY", M("SUBTRACT", 1.0, dot.outputs["Value"]), 8.0), 1.0)
        occl = M("MULTIPLY", M("POWER", ao_s.outputs["AO"], 0.9),
                 M("ADD", 0.55, M("MULTIPLY", ao_l.outputs["AO"], 0.45)))
        # grime mottle (object space): stains + a finer speckle + per-island value; darkens only
        tc = node("ShaderNodeTexCoord")
        n1 = node("ShaderNodeTexNoise")
        n1.inputs["Scale"].default_value = grit["scale"]
        n1.inputs["Detail"].default_value = 4.0
        n1.inputs["Roughness"].default_value = 0.6
        L(tc.outputs["Object"], n1.inputs["Vector"])
        n2 = node("ShaderNodeTexNoise")
        n2.inputs["Scale"].default_value = grit["scale"] * 6.0
        n2.inputs["Detail"].default_value = 2.0
        L(tc.outputs["Object"], n2.inputs["Vector"])
        stain = M("MAXIMUM", M("MULTIPLY", M("SUBTRACT", n1.outputs["Fac"], 0.42), 3.2), 0.0)
        speck = M("MAXIMUM", M("MULTIPLY", M("SUBTRACT", n2.outputs["Fac"], 0.5), 2.2), 0.0)
        mottle = M("MINIMUM", M("ADD", M("MULTIPLY", stain, 0.75), M("MULTIPLY", speck, 0.45)), 1.0)
        em = node("ShaderNodeEmission")
        if mode == "colour":
            v = M("MINIMUM", M("ADD", M("ADD", grit["floor"], M("MULTIPLY", occl, grit["occl"])),
                               M("MULTIPLY", edge, grit["edge"])), 1.0)
            v = M("MULTIPLY", v, M("SUBTRACT", 1.0, M("MULTIPLY", mottle, grit["grime"])))
            comb = node("ShaderNodeCombineColor")
            for k in range(3):
                L(v, comb.inputs[k])
            L(comb.outputs[0], em.inputs["Color"])
        else:
            r = M("ADD", rough, M("SUBTRACT", M("MULTIPLY", M("SUBTRACT", 1.0, occl), 0.25),
                                  M("MULTIPLY", edge, 0.12)))
            r = M("ADD", r, M("MULTIPLY", M("SUBTRACT", mottle, 0.3), grit["rough"]))
            r = M("MAXIMUM", M("MINIMUM", r, 1.0), 0.05)
            comb = node("ShaderNodeCombineColor")
            comb.inputs[0].default_value = 1.0
            L(r, comb.inputs[1])
            comb.inputs[2].default_value = 0.0
            L(comb.outputs[0], em.inputs["Color"])
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        L(em.outputs[0], out.inputs["Surface"])
        tgt = node("ShaderNodeTexImage")
        tgt.image = col_img if mode == "colour" else rm_img
        uvn = node("ShaderNodeUVMap")
        uvn.uv_map = "bake"
        L(uvn.outputs["UV"], tgt.inputs["Vector"])
        nt.nodes.active = tgt
        return tmp

    tmpdir = HERE / "bake"
    tmpdir.mkdir(exist_ok=True)
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
        img.filepath_raw = str(tmpdir / f"{img.name}.png")
        img.file_format = "PNG"
        img.save()
    # per-object materials (the palette materials are shared by the pieces, each with its own map)
    new = []
    for m in mats:
        m2 = m.copy()
        m2.name = f"{m.name.split('.')[0]}_{obj.name}"
        nt = m2.node_tree
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
        new.append(m2)
    for i, m2 in enumerate(new):
        me.materials[i] = m2


# ---------------------------------------------------------------------------------------------
# review renders
# ---------------------------------------------------------------------------------------------
def renders(objs, shells, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    for o in list(scene.objects):
        if o not in objs and o not in shells:
            o.hide_render = True
    # 1. top views per piece for the IoU (flat white on transparent, shells hidden), 8 px per px
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as err:
        scene.render.engine = next(e for e in str(err).replace("'", " ").replace(",", " ").split() if "WORKBENCH" in e)
    sh = scene.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.show_object_outline = False
    sh.show_cavity = False
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Standard"
    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    K = 8

    def shoot(path, loc, look, ortho=None, lens=50, rx=None, ry=None):
        cam_d.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            cam_d.ortho_scale = ortho
        cam_d.lens = lens
        cam.location = loc
        d = Vector(look) - Vector(loc)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        if rx:
            scene.render.resolution_x, scene.render.resolution_y = rx, ry
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)

    for s in shells:
        s.hide_render = True
    for o in objs:
        for p in objs:
            p.hide_render = p is not o
        cx, cy = o.location.x, o.location.y
        scene.render.resolution_x, scene.render.resolution_y = 24 * K, 28 * K
        cam_d.sensor_fit = "VERTICAL"
        shoot(out_dir / f"top_{o.name}.png", (cx, cy, 10), (cx, cy, 0), ortho=28 / 12, rx=24 * K, ry=28 * K)
        cam.rotation_euler = (0, 0, 0)
        bpy.ops.render.render(write_still=True)
    for p in objs:
        p.hide_render = False
    scene.render.resolution_x, scene.render.resolution_y = W * K, H * K
    cam.location = (0, 0, 10)
    cam.rotation_euler = (0, 0, 0)
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = H / 12
    scene.render.filepath = str(out_dir / "top_whole_mask.png")
    bpy.ops.render.render(write_still=True)

    # 2. lit views (Cycles, the game's sun + a hemisphere-like world), shells shown as ink
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.device = "CPU"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "Standard"
    world = scene.world or bpy.data.worlds.new("w")
    scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.42, 0.47, 0.58, 1)
    bg.inputs[1].default_value = 0.9
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(2)
    sun = bpy.data.objects.new("sun", sun_d)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector(tuple(-SUN)).to_track_quat("-Z", "Y").to_euler()
    # ground plane under it (the bricks' mid grey) so the base sits on something
    gm = bpy.data.meshes.new("ground")
    bmg = bmesh.new()
    for v in ((-6, -6, -0.002), (6, -6, -0.002), (6, 6, -0.002), (-6, 6, -0.002)):
        bmg.verts.new(v)
    bmg.faces.new(bmg.verts)
    bmg.to_mesh(gm)
    ground = bpy.data.objects.new("ground", gm)
    gm.materials.append(common.material("ground_grey", (0.06, 0.065, 0.075), roughness=0.9))
    scene.collection.objects.link(ground)
    for s in shells:
        s.hide_render = False
        sol = s.modifiers.new("ink", "SOLIDIFY")
        sol.thickness = 0.012
        sol.offset = 1.0
        sol.use_flip_normals = True
    ink = common.material("ink_backface", (0, 0, 0), roughness=1)
    ink.use_backface_culling = True
    for s in shells:
        s.data.materials.clear()
        s.data.materials.append(ink)
    R = 520
    views = {
        "game": ((0, -9.0 * math.sin(math.radians(15)), 9.0 * math.cos(math.radians(15))), 62),
        "steep": ((0, -9.0 * math.sin(math.radians(32)), 9.0 * math.cos(math.radians(32))), 62),
        "q34_high": ((4.2, -4.6, 4.4), 70),
        "q34_crown": ((-4.0, 4.4, 3.6), 70),
        "side": ((7.5, 0, 0.45), 58),
        "front": ((0, 8.0, 0.45), 70),
        "rear": ((0, -8.0, 0.45), 70),
        "under": ((2.5, -3.5, -5.5), 50),
    }
    for name, (loc, lens) in views.items():
        ground.hide_render = name in ("under", "side", "front", "rear")
        look = (0, 0, 0.3)
        shoot(out_dir / f"view_{name}.png", loc, look, lens=lens, rx=R, ry=R)
    ground.hide_render = False
    shoot(out_dir / "view_top.png", (0, 0, 10), (0, 0, 0), ortho=H / 12 * 1.04, rx=W * 10, ry=H * 10)
    cam.rotation_euler = (0, 0, 0)
    bpy.ops.render.render(write_still=True)
    # top view without the ink and the ground (for the palette measure), flat emission of the
    # palette index: done in Python from the regions instead (see measure.py)


def main():
    sprite = common.load_sprite(WT, "newshd-155")
    for n in PIECES:
        sprite["colors"].update(common.load_sprite(WT, n)["colors"])
    sprite["name"] = NAME
    coll = common.reset_collection(NAME)
    for o in list(bpy.data.objects):
        if o.name not in coll.objects:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    obj = build(coll, sprite)
    print("regions", obj["regions"])
    print("materials", [m.name for m in obj.data.materials])
    shell = common.outline_shell(obj, coll, voxel=0.014, faces=5000, smooth=6, inside=0.01)
    mask_shell(shell)
    layout = [(n, x0 + 12 - W / 2, y0 + 14 - H / 2) for n, (x0, y0) in PIECES.items()]
    if "--no-bake" not in ARGV:
        # one bake of the whole head before the cut, so no edge lift or AO step at the seams;
        # the pieces keep the "bake" UVs (bisect interpolates them) and share the atlas
        shell.hide_render = True
        bake(obj, size=1024)
        shell.hide_render = False
    pieces = common.split_assembly(obj, layout, coll)
    for p in pieces.values():
        close_piece(p)
    shells = split_open(shell, layout, coll, "_outline")
    outline_mat = common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)
    objs, sh_objs = [], []
    for name, cx, cy in layout:
        p, s = pieces[name], shells[name]
        p.location = (cx / 12, -cy / 12, 0)
        s.location = p.location
        p.data.shade_flat()
        s.data.shade_smooth()
        s["tyrian_outline"] = True
        s.data.materials.clear()
        s.data.materials.append(outline_mat)
        objs.append(p)
        if s.data.polygons:
            sh_objs.append(s)
    obj.hide_render = True
    shell.hide_render = True
    coll.objects.unlink(obj)
    coll.objects.unlink(shell)
    tris = 0
    for p in objs:
        p.data.validate(verbose=False)
        p.data.calc_loop_triangles()
        tris += len(p.data.loop_triangles)
        print(f"piece {p.name}: {len(p.data.loop_triangles)} tris, mats {[m.name for m in p.data.materials]}")
    for p in objs:
        s = next((o for o in sh_objs if o.name == p.name + "_outline"), None)
        group = [p] + ([s] if s else [])
        keep = [tuple(o.location) for o in group]
        for o in group:
            o.location = (0, 0, 0)
        data = common.load_sprite(WT, p.name)
        common.export_sprite_model(WT, group, f"enemies/{p.name}", data["sprites"],
                                   image_format="AUTO" if "--no-bake" in ARGV else "WEBP")
        for o, loc in zip(group, keep):
            o.location = loc
    print(f"built {NAME}: {tris} triangles")
    if "--renders" in ARGV:
        renders(objs, sh_objs, ARGV[ARGV.index("--renders") + 1])


if __name__ == "__main__":
    main()
