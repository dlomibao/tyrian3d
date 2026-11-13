"""Blue cyclops beast grown into the GYGES wall (newshh.shp, assembly of newshh-5, -7, -43, -45; frames
5/9/13, 7/11/15, 43/47/51, 45/49/53): a 3D version of its 2x2 sprite (48x56 px). Level 2.4.

WHAT IT IS: a fixed growth in the layer-2 wall (it drifts with the middle map layer, 2 px/tick), not a
flyer. Read from the sprite: a domed head with one glowing eye looking south-east, on a hunched,
plated neck/torso; a big rounded back (haunch) to the right with a dorsal hump and a curled spine
hook; a thick left foreleg from a shoulder with a hooked claw outside it; a thin right hind leg
reaching to the bottom right; a thin left shin; and under the body a dark mat of cable-like tissue
whose strands drip down the panel. The sprite's grey vein panel is terrain, not part of the creature
(D130): no backing, the HD layer-2 wall shows behind it.

Every mass is a loft of chamfered superellipse sections along its own axis, the stations taken from
that part's pixels (so the plan matches the sprite row by row) and smoothed with pchip; heights are
staged so the parts separate at the game camera: head crown highest (+6.2 px over the wall), haunch,
torso, foreleg, then legs and the low tissue mat. Plates are modelled (throat plates, haunch seams,
elbow and wrist rings, a brow plate). The eye is a socket rim (48), an emissive lens (114 -> 115 -> 117)
and a hot core (118 -> 126 -> 127), metallic 1 / rough (D126, D173); the head pulses 52 -> 56 -> 59
with it (the only parts that change over the 3 frames; the top two pieces carry them).

Underside: flat sealed base on the wall plane (plausible closed shape only). Outline shell (D51) from
the sealed creature, cut into the pieces with it.

Part labels of the 48x56 block are in assembly-newshh-45.labels.json next to this script.

Run: blender -b --python assets/blender/enemies/assembly-newshh-45.py -- [--views DIR --viewsmod views_B.py]
[--pieces DIR]. Exports public/models/enemies/newshh-{5,7,43,45}.glb and their spriteModels entries.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import usp_talon as T  # noqa: E402

WT = common.repo_root(__file__)

HERE = Path(__file__).resolve().parent
LABELS = HERE / "assembly-newshh-45.labels.json"
NAME = "assembly-newshh-45"
TAG = "nshh45"
W, H = 48, 56
ZB = -3.0  # wall plane, sprite px (-0.25 u)
PIECES = [("newshh-5", 0, 0), ("newshh-7", 24, 0), ("newshh-43", 0, 28), ("newshh-45", 24, 28)]
# frames of the top pieces whose head/eye colours step up (newshh-5 and newshh-7 share the materials)
F_MID, F_HOT = (9, 11), (13, 15)


def anim(mid, hot):
    return {**{f: mid for f in F_MID}, **{f: hot for f in F_HOT}}


# --- sprite data --------------------------------------------------------------------------------

def load_data():
    d = json.loads(LABELS.read_text())
    lab = np.array([list(r) for r in d["labels"]])
    colors = dict(d["colors"])
    for name, _, _ in PIECES:
        colors.update(common.load_sprite(WT, name)["colors"])
    return lab, {"name": NAME, "colors": colors}


# --- geometry helpers (sprite px: u east, v south, z up) -------------------------------------------

def to_blender(u, v, z):
    return Vector(((u - W / 2) / 12, (H / 2 - v) / 12, z / 12))


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.part = self.bm.faces.layers.int.new("part")

    def vert(self, p):
        return self.bm.verts.new(to_blender(*p))

    def face(self, vs, mat, part):
        try:
            f = self.bm.faces.new(vs)
        except ValueError:
            return None
        f.material_index = mat
        f[self.part] = part
        return f


def supersample(mask, k=8):
    """Sub-pixel centres (u, v) inside a pixel mask."""
    rs, cs = np.nonzero(mask)
    o = (np.arange(k) + 0.5) / k
    uu = (cs[:, None, None] + o[None, None, :]).repeat(k, 1).reshape(-1)
    vv = (rs[:, None, None] + o[None, :, None]).repeat(k, 2).reshape(-1)
    return uu, vv


def smooth(a, n=1):
    a = np.asarray(a, float)
    for _ in range(n):
        b = a.copy()
        b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
        a = b
    return a


def gsmooth(a, sig):
    """Gaussian smoothing (sig in samples), ends padded with their own values."""
    a = np.asarray(a, float)
    if sig <= 0:
        return a
    r = int(3 * sig) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(a, r, mode="edge"), k, mode="valid")


def stations(mask, axis_deg, step=0.5, rounds=2, sigma=0.6):
    """Extents of a part across its axis at stations along it. axis_deg: 0 = south (down the
    rows), 90 = east. Returns origin, unit axis d, unit across n (d rotated -90: east of south-going),
    station list s and (tmin, tmax) per station, smoothed with pchip through 1-px samples."""
    a = math.radians(axis_deg)
    d = np.array([math.sin(a), math.cos(a)])  # (du, dv)
    n = np.array([d[1], -d[0]])
    uu, vv = supersample(mask)
    o = np.array([uu.mean(), vv.mean()])
    s = (uu - o[0]) * d[0] + (vv - o[1]) * d[1]
    t = (uu - o[0]) * n[0] + (vv - o[1]) * n[1]
    s0, s1 = s.min(), s.max()
    ks = np.arange(s0 + 0.0625, s1 - 0.0625 + 1e-6, 0.125)
    lo, hi, keep = [], [], []
    for x in ks:
        sel = np.abs(s - x) < 0.0626
        if sel.sum() == 0:
            continue
        lo.append(t[sel].min() - 0.0625)
        hi.append(t[sel].max() + 0.0625)
        keep.append(x)
    keep, rlo, rhi = np.array(keep), np.array(lo), np.array(hi)
    # smooth the pixel staircase, but never past the raw envelope (+ a hair): ends stay as narrow
    # as the sprite's
    lo = gsmooth(np.maximum(gsmooth(rlo, sigma * 8), rlo - 0.12), sigma * 8)
    hi = gsmooth(np.minimum(gsmooth(rhi, sigma * 8), rhi + 0.12), sigma * 8)
    # ...and pin the last 1.5 px at each end to the raw envelope so the ends stay narrow
    e = np.minimum(keep - keep[0], keep[-1] - keep)
    pin = np.clip(1 - e / 1.5, 0, 1)
    lo = np.maximum(lo, rlo - 0.12 - 2 * (1 - pin))
    hi = np.minimum(hi, rhi + 0.12 + 2 * (1 - pin))
    flo, fhi = T.pchip(list(keep), list(lo)), T.pchip(list(keep), list(hi))
    ss = list(np.arange(s0, s1 + 1e-6, step))
    if ss[-1] < s1 - 1e-3:
        ss.append(s1)
    ss = np.array(ss)
    ext = [(flo(min(max(x, keep[0]), keep[-1])), fhi(min(max(x, keep[0]), keep[-1]))) for x in ss]
    return o, d, n, ss, ext


def section(w, h, n=2.6, sides=22):
    """Superellipse arch from +w (right) over the top to -w, z from 0 up to h."""
    pts = []
    for i in range(sides + 1):
        a = math.pi * i / sides
        c, s_ = math.cos(a), math.sin(a)
        x = math.copysign(abs(c) ** (2 / n), c)
        y = abs(s_) ** (2 / n)
        pts.append((w * x, h * y))
    return pts


def loft_part(M, mask, axis_deg, hfun, mat, part, n=2.6, sides=22, step=0.5, rounds=2, end_round=2.0,
              wmul=None, z0=ZB, aspect=1.6, sigma=0.6):
    """Loft a mass over its pixels: sections across the axis, height hfun(f) (f = 0..1 along the
    axis), capped by `aspect` * half width, rounded down over `end_round` px at both ends; flat sealed
    base on z0. wmul(f) optionally narrows the width (grooves)."""
    o, d, nn, ss, ext = stations(mask, axis_deg, step, rounds, sigma)
    L = ss[-1] - ss[0]
    rings = []
    for x, (lo, hi) in zip(ss, ext):
        f = (x - ss[0]) / L if L else 0.5
        w = max(0.05, (hi - lo) / 2)
        tc = (hi + lo) / 2
        h = min(hfun(f), aspect * w)
        e = min(x - ss[0], ss[-1] - x)
        if e < end_round:
            h *= math.sqrt(max(0.0, 1 - ((end_round - e) / end_round) ** 2)) * 0.85 + 0.15
        if wmul:
            w *= wmul(f)
        c = o + d * x + nn * tc
        ring = []
        for (a, z) in section(w, max(h, 0.05), n, sides):
            p = c + nn * a
            ring.append(M.vert((p[0], p[1], z0 + z)))
        rings.append(ring)
    _skin(M, rings, mat, part)
    return o, d, nn, ss


def _skin(M, rings, mat, part, cap=True):
    k = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(k - 1):
            M.face([a[i], b[i], b[i + 1], a[i + 1]], mat, part)
        M.face([a[k - 1], b[k - 1], b[0], a[0]], mat, part)  # base
    if cap:
        M.face(list(reversed(rings[0])), mat, part)
        M.face(list(rings[-1]), mat, part)


def catmull(pts, per=6):
    """Centripetal-ish Catmull-Rom through points (tuples); returns a dense list."""
    P = [np.array(p, float) for p in pts]
    if len(P) < 3:
        return [tuple(P[0] + (P[1] - P[0]) * i / per) for i in range(per)] + [tuple(P[1])]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for j in range(per):
            t = j / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(P[-2]))
    return out


def tube(M, path, mat, part, sides=10, per=6, ribs=None, squash=1.0):
    """Sweep a round section along path [(u, v, z, r)] (px). ribs: (period px, amplitude) collars."""
    pts = catmull(path, per)
    rings = []
    acc = 0.0
    prev = None
    up = Vector((0, 0, 1))
    for i, p in enumerate(pts):
        c = Vector(p[:3])
        a = Vector(pts[min(i + 1, len(pts) - 1)][:3]) - Vector(pts[max(i - 1, 0)][:3])
        if a.length < 1e-6:
            a = Vector((0, 1, 0))
        a.normalize()
        if prev is not None:
            acc += (c - prev).length
        prev = c
        side = a.cross(up)
        if side.length < 1e-4:
            side = a.cross(Vector((1, 0, 0)))
        side.normalize()
        nrm = side.cross(a).normalized()
        r = max(0.05, p[3])
        if ribs:
            ph = (acc % ribs[0]) / ribs[0]
            r *= 1 + ribs[1] * math.exp(-((ph - 0.5) / 0.12) ** 2)
        ring = []
        for k in range(sides):
            t = 2 * math.pi * k / sides
            q = c + side * (math.cos(t) * r) + nrm * (math.sin(t) * r * squash)
            ring.append(M.vert((q.x, q.y, q.z)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            M.face([a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]], mat, part)
    M.face(list(reversed(rings[0])), mat, part)
    M.face(list(rings[-1]), mat, part)


def limb(M, path, mat, part, hk=1.0, collars=(), sides=20, per=8):
    """A limb sitting on the wall: a tube whose section is a half-superellipse arch of half width r
    and height hk * r (plan width = 2r exactly), base flat on ZB. collars: (path index, depth)."""
    P = catmull([(u, v, r) for u, v, _, r in path], per)
    rings = []
    for i, p in enumerate(P):
        a = np.array(P[min(i + 1, len(P) - 1)][:2]) - np.array(P[max(i - 1, 0)][:2])
        a = a / (np.linalg.norm(a) + 1e-9)
        nrm = np.array([a[1], -a[0]])
        r = max(0.08, p[2])
        f = 1.0
        for ci, dep in collars:
            f -= dep * math.exp(-((i - ci * per) / (0.35 * per)) ** 2)
        e = min(i, len(P) - 1 - i) / per
        hr = hk * r * f * (math.sqrt(min(1.0, e / 0.6)) * 0.8 + 0.2 if e < 0.6 else 1.0)
        ring = []
        for (x, z) in section(r * (1 - 0.3 * (1 - f)), hr, 2.2, sides):
            q = np.array(p[:2]) + nrm * x
            ring.append(M.vert((q[0], q[1], ZB + z)))
        rings.append(ring)
    _skin(M, rings, mat, part)


def ellipsoid(M, centre, axes, radii, mat, part, seg=20, rings=10, zmin=None, cut=None):
    """UV ellipsoid in a local frame axes (3 Vectors), radii (a, b, c) in px. cut: keep the cap with
    local z >= cut * c (a lens cap), closed by a flat disc."""
    C = Vector(centre)
    ex, ey, ez = axes
    a, b, c = radii
    lo = -math.pi / 2 if cut is None else math.asin(max(-1.0, min(1.0, cut)))
    vs = []
    for j in range(rings + 1):
        ph = lo + (math.pi / 2 - lo) * j / rings
        row = []
        for i in range(seg):
            th = 2 * math.pi * i / seg
            x, y, z = a * math.cos(ph) * math.cos(th), b * math.cos(ph) * math.sin(th), c * math.sin(ph)
            q = C + ex * x + ey * y + ez * z
            if zmin is not None:
                q.z = max(q.z, zmin)
            row.append(q)
        vs.append(row)
    top = M.vert(tuple(C + ez * c))
    R = [[M.vert(tuple(q)) for q in row] for row in vs[:-1]]
    for r0, r1 in zip(R, R[1:]):
        for i in range(seg):
            M.face([r0[i], r0[(i + 1) % seg], r1[(i + 1) % seg], r1[i]], mat, part)
    for i in range(seg):
        M.face([R[-1][i], R[-1][(i + 1) % seg], top], mat, part)
    M.face(list(reversed(R[0])), mat, part)


def torus(M, centre, axes, R1, R2, r, mat, part, seg=28, sides=8, lift=0.0):
    """Elliptic ring (radii R1, R2 in the ex/ey plane) of tube radius r."""
    C = Vector(centre)
    ex, ey, ez = axes
    rings = []
    for i in range(seg):
        th = 2 * math.pi * i / seg
        p = C + ex * (R1 * math.cos(th)) + ey * (R2 * math.sin(th)) + ez * lift
        radial = (ex * (R1 * math.cos(th)) + ey * (R2 * math.sin(th))).normalized()
        ring = []
        for k in range(sides):
            a = 2 * math.pi * k / sides
            q = p + radial * (r * math.cos(a)) + ez * (r * math.sin(a))
            ring.append(M.vert(tuple(q)))
        rings.append(ring)
    for i in range(seg):
        a, b = rings[i], rings[(i + 1) % seg]
        for k in range(sides):
            M.face([a[k], b[k], b[(k + 1) % sides], a[(k + 1) % sides]], mat, part)


def ball_head(M, mask, centre, mat, part, z_eq=2.7, rz_up=3.8, p_up=2.3, seg=72, lat=14,
              ry_s=(5.9, 6.7), sig_deg=7.0):
    """Ball head, round in plan. Plan radius R(theta) from `centre` (u, v): north half (v < centre)
    marched out to the edge of `mask` (sub-pixel) and smoothed around the circle; south half an
    ellipse of half width R(east/west) and depth ry_s (west, east), so the chin is round. Upper half
    a superellipsoid (exponent p_up, rz_up over the equator at ZB + z_eq), lower half an ellipsoid
    down to just under the wall (closed)."""
    cu, cv = centre
    th = np.linspace(0, 2 * math.pi, seg, endpoint=False)  # 0 = east, pi/2 = south (v down)
    hgt, wid = mask.shape

    def inside(u, v):
        j, i = int(math.floor(v)), int(math.floor(u))
        return 0 <= j < hgt and 0 <= i < wid and bool(mask[j, i])

    rm = []
    for t in th:
        du, dv = math.cos(t), math.sin(t)
        r = 0.0
        while r < 20 and inside(cu + du * (r + 0.02), cv + dv * (r + 0.02)):
            r += 0.02
        rm.append(r)
    rm = np.array(rm)
    # circular gaussian smoothing of the pixel staircase
    s = sig_deg / (360 / seg)
    k = np.exp(-0.5 * (np.arange(-int(3 * s) - 1, int(3 * s) + 2) / s) ** 2)
    k /= k.sum()
    pad = len(k) // 2
    rs = np.convolve(np.concatenate([rm[-pad:], rm, rm[:pad]]), k, mode="valid")
    re, rw = rs[0], rs[seg // 2]
    R = []
    for t, r in zip(th, rs):
        du, dv = math.cos(t), math.sin(t)
        if dv <= 0:
            R.append(r)
            continue
        # south half: ellipse; half width blends west -> east, depth blends west -> east (SE bulge)
        a = re if du >= 0 else rw
        e = max(0.0, du)
        b = ry_s[0] + (ry_s[1] - ry_s[0]) * (0.5 + 0.5 * math.tanh(2.5 * (du + 0.15)))
        b *= 1 + 0.04 * math.exp(-((t - math.radians(55)) / 0.5) ** 2) * (1 + e)
        R.append(1 / math.sqrt((du / a) ** 2 + (dv / b) ** 2))
    R = np.array(R)
    zb = ZB - 0.4
    rz_dn = z_eq - (zb - ZB)
    rings = []
    # latitude from the bottom pole to just short of the crown
    for j in range(1, 2 * lat):
        ph = -math.pi / 2 + math.pi * j / (2 * lat)
        if ph < 0:
            rho, z = math.cos(ph), ZB + z_eq + rz_dn * math.sin(ph)
        else:
            c_, s_ = math.cos(ph), math.sin(ph)
            rho, z = c_ ** (2 / p_up), ZB + z_eq + rz_up * s_ ** (2 / p_up)
        rings.append([M.vert((cu + rho * Rk * math.cos(t), cv + rho * Rk * math.sin(t), z))
                      for t, Rk in zip(th, R)])
    bot = M.vert((cu, cv, ZB + z_eq - rz_dn))
    top = M.vert((cu, cv, ZB + z_eq + rz_up))
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            M.face([a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]], mat, part)
    for i in range(seg):
        M.face([rings[0][(i + 1) % seg], rings[0][i], bot], mat, part)
        M.face([rings[-1][i], rings[-1][(i + 1) % seg], top], mat, part)


# --- the creature ---------------------------------------------------------------------------------

PART_NAMES = ["head", "torso", "haunch", "hump", "arm", "claw", "legR", "shinL", "tangle", "cable",
              "eye", "brow", "backing"]
PID = {n: i for i, n in enumerate(PART_NAMES)}


def saw(period, depth, start=0.0, sharp=0.2):
    """Overlapping-plate profile: each plate swells to its rear edge, then steps sharply down."""
    def f(x):
        ph = ((x - start) / period) % 1.0
        if ph > 1 - sharp:
            return 1 - depth * (ph - (1 - sharp)) / sharp
        return 1 - depth * (1 - ph / (1 - sharp)) ** 2
    return f


def grooves(centres, depth, width=0.35):
    def f(x):
        m = 1.0
        for c in centres:
            m -= depth * math.exp(-((x - c) / width) ** 2)
        return m
    return f


def build(lab, sprite):
    coll = common.reset_collection(f"{NAME}_B")
    mats = []
    mi = {}

    def mat(key, idx, **kw):
        if key not in mi:
            mi[key] = len(mats)
            mats.append(common.palette_material(sprite, idx, f"{TAG}_{key}", **kw))
        return mi[key]

    HIDE = dict(metallic=0.35, roughness=0.42)
    m_head = mat("head", 52, frames=anim(56, 59), **HIDE)
    # fix round 2: the torso shares the hide's satin (0.1 / 0.62 washed palette 51 to grey)
    m_torso = mat("torso", 51, **HIDE)
    m_haunch = mat("haunch", 54, **HIDE)
    m_arm = mat("arm", 53, **HIDE)
    m_shin = mat("shin", 55, **HIDE)
    m_sock = mat("socket", 48, metallic=0.4, roughness=0.5)
    m_lens = mat("lens", 114, metallic=1.0, roughness=0.55, emission_strength=1.6, frames=anim(115, 117))
    # core = median of the sprite's 2x2 eye centre per phase: 118 red, 121 orange (118/119/121/126),
    # 126 pale yellow (123/126/126/127); fix round 2: 127 read near white
    m_core = mat("core", 118, metallic=1.0, roughness=0.55, emission_strength=2.2, frames=anim(121, 126))
    m_tis = mat("tissue", 97, metallic=0.2, roughness=0.6)
    m_tis2 = mat("tissue2", 96, metallic=0.2, roughness=0.65)

    M = Mesh()
    m = lambda k: lab == k  # noqa: E731

    rows = np.arange(H)[:, None] + np.zeros((1, W), int)
    # Head: a round ball (fix round 2: the loft over the head's pixels gave a hood with straight sides
    # and a flat south edge). Plan: the north half follows the head's own outline from the ball's
    # centre (the crown takes the top arc of the ring, row 10 and row 11's ends: ink on frames 5 and 9,
    # head colour on the hot frame 13, so the rule IoU holds on all three phases); the south half is
    # an ellipse whose lower edge bulges south-east under the eye (sprite frame 13: rows ~22 west,
    # ~23 east). Equator 2.7 px over the wall, crown +6.5; the lower half tucks into the neck.
    head = m("H").copy()
    head[10, 18:23] = True
    head[11, [16, 17, 23, 24]] = True
    ball_head(M, head, (20.5, 16.4), m_head, PID["head"])
    # Neck under the ball: the head's straight-sided lower rows (16-23) as a low collar below the
    # ball's equator, so it shows only at the corners the round ball leaves, as the sprite's dark
    # neck shoulders there.
    collar = (m("H") & (rows >= 16)) | (m("N") & (rows <= 23))
    loft_part(M, collar, 0, lambda f: 2.4, m_torso, PID["torso"], n=2.0, sides=24, step=0.3,
              end_round=3.0, aspect=1.0)
    # Neck/torso: overlapping throat plates down the upper neck (rows 22-30), then a smooth chest
    # falling from 5 px at the collar to 2.8 px where it meets the tissue mat; its north end starts
    # just under the ball's equator (2.7 px) so the ball's round south face shows above it.
    plates = saw(2.6, 0.07)
    neck = lambda f: plates(f * 19.5) if f < 0.45 else 1.0  # noqa: E731
    rise = lambda f: 0.55 + 0.45 * min(1.0, f / 0.14) ** 2 * (3 - 2 * min(1.0, f / 0.14))  # noqa: E731
    loft_part(M, m("N"), 0, lambda f: (5.0 - 2.2 * f ** 1.5) * neck(f) * rise(f), m_torso, PID["torso"],
              n=2.25, sides=28, step=0.25, end_round=1.6, aspect=1.0,
              wmul=lambda f: 1 - 0.3 * (1 - neck(f)))
    # Haunch: the big rounded back along its own axis (upper left -> lower right), two chitin seams.
    seams = grooves([0.36, 0.62], 0.05, 0.025)
    loft_part(M, m("B"), -38, lambda f: 5.4 * max(0.0, 1 - abs(2 * f - 0.9) ** 2.4) ** 0.5 * seams(f) + 1.0,
              m_haunch, PID["haunch"], n=2.2, sides=28, step=0.3, end_round=2.5, aspect=1.0, sigma=1.1,
              wmul=lambda f: 1 - 0.5 * (1 - seams(f)))
    # Dorsal hump on the haunch's top edge (cols 29-38, rows 21-25), across.
    loft_part(M, m("P"), 90, lambda f: 5.0 * (1 - abs(2 * f - 1) ** 2) ** 0.5, m_haunch, PID["hump"], n=2.1,
              sides=18, end_round=1.5, aspect=1.3)
    # Spine hook curling back down off the hump (blueprint path, z relative to the wall).
    tube(M, [(33.5, 22.6, ZB + 3.8, 0.85), (35.6, 22.4, ZB + 3.6, 0.75), (37.0, 23.4, ZB + 2.6, 0.6),
             (37.3, 24.6, ZB + 1.6, 0.48), (37.1, 25.4, ZB + 0.7, 0.3)], m_haunch, PID["hump"], sides=10)
    # Foreleg: one bent limb from the shoulder (in the torso, row 26) out to col 8 and down the
    # forearm to the foot at row 39; elbow and wrist collars.
    arm_path = [(15.0, 27.5, 0.0, 1.7), (12.0, 27.4, 0.0, 1.8), (9.6, 28.0, 0.0, 2.6), (9.3, 29.8, 0.0, 3.3),
                (9.5, 32.2, 0.0, 3.5), (9.5, 34.8, 0.0, 3.45), (8.0, 36.7, 0.0, 2.3), (7.1, 38.1, 0.0, 1.0),
                (6.9, 38.9, 0.0, 0.5)]
    limb(M, arm_path, m_arm, PID["arm"], hk=1.15, collars=[(3, 0.12), (6, 0.12)])
    # Hooked claw outside the foreleg (cols 2-5, rows 26-38): a tapering tube following the sprite's
    # curved strip, bulging out at the knuckle and ending in a point that digs into the wall.
    tube(M, [(6.0, 27.1, ZB + 0.9, 0.6), (5.3, 28.4, ZB + 1.6, 1.0), (4.65, 29.8, ZB + 1.9, 1.35),
             (4.75, 32.2, ZB + 1.9, 1.3), (5.1, 34.2, ZB + 1.6, 1.05), (5.6, 35.9, ZB + 1.2, 0.8),
             (5.6, 37.4, ZB + 0.6, 0.45), (5.2, 38.5, ZB + 0.1, 0.18)], m_haunch, PID["claw"], sides=14, per=8,
         ribs=(3.2, 0.1))
    tube(M, [(7.8, 36.9, ZB + 1.8, 1.0), (7.1, 38.3, ZB + 1.1, 0.75), (6.9, 39.0, ZB + 0.4, 0.35)],
         m_arm, PID["arm"], sides=10)
    # Right hind leg (cols 37-45, rows 32-41) and its toes to the bottom right.
    limb(M, [(36.6, 32.6, 0.0, 1.4), (38.4, 33.6, 0.0, 1.9), (40.0, 35.0, 0.0, 1.8), (41.2, 36.4, 0.0, 1.2),
             (42.4, 38.1, 0.0, 0.95), (43.3, 39.5, 0.0, 1.05), (44.7, 40.3, 0.0, 0.75)], m_arm, PID["legR"], hk=1.25,
         collars=[(3, 0.15)], sides=16)
    tube(M, [(44.6, 39.8, ZB + 1.3, 0.6), (45.5, 40.5, ZB + 1.0, 0.5), (46.5, 41.6, ZB + 0.8, 0.5),
             (47.2, 43.0, ZB + 0.5, 0.55), (47.7, 44.6, ZB + 0.3, 0.4)], m_arm, PID["legR"], sides=10, ribs=(1.6, 0.15))
    tube(M, [(43.3, 40.5, ZB + 1.0, 0.5), (42.7, 42.4, ZB + 0.85, 0.5), (42.3, 44.2, ZB + 0.75, 0.55),
             (41.6, 46.0, ZB + 0.6, 0.5), (41.2, 47.6, ZB + 0.5, 0.55), (40.0, 48.9, ZB + 0.4, 0.6),
             (38.4, 50.4, ZB + 0.3, 0.6), (36.8, 51.9, ZB + 0.2, 0.55), (36.4, 52.6, ZB + 0.15, 0.4)],
         m_arm, PID["legR"], sides=10, ribs=(1.6, 0.15))
    # Thin left shin (col 13, rows 37-45).
    tube(M, [(13.8, 36.0, ZB + 2.4, 0.95), (14.4, 39.0, ZB + 1.8, 1.2), (13.9, 40.3, ZB + 1.4, 0.9), (13.5, 41.5, ZB + 1.2, 0.75),
             (13.5, 44.0, ZB + 0.8, 0.7), (13.5, 45.6, ZB + 0.4, 0.45)], m_shin, PID["shinL"], sides=12,
         ribs=(2.0, 0.12))

    # Flesh skin under everything at the wall (fills the creases between the masses, as the sprite's
    # dark joins do), then the tissue mat: low membrane over the dark pool (heightfield on a 4x grid), then cables over it.
    # body skin: contoured inside the parts' own outline (thr above the mask edge's 0.5) and kept off
    # the head dome above its jaw (row 19), so no plate shows past the round head
    body = np.isin(lab, list("HNBPA")) & ~((lab == "H") & (rows < 19))
    tissue_mat(M, body, m_torso, PID["torso"], height=1.0, thr=0.68, k=3)
    # tangle: a low fleshy mound under the cables, its slope easing up from the contour (smoothstep)
    # so no edge stands up as a slab (fix round 1)
    tissue_mat(M, m("T"), m_tis2, PID["tangle"], height=1.3, thr=0.5, passes=6, soft=60,
               ramp=lambda x: x * x * (3 - 2 * x), lumps=14)
    for path, r in TANGLE:
        tube(M, [(u, v, ZB + z, r * k) for (u, v, z, k) in path], m_tis, PID["cable"], sides=12, ribs=(1.8, 0.12), squash=0.9)

    obj = to_object(f"{NAME}_creature", M, mats, coll)
    add_eye(obj, coll, mats, mi, m_head, m_sock, m_lens, m_core)
    return obj, coll, mats, mi


# cable tissue: (u, v, z above the wall, radius factor) paths with base radius
TANGLE = [
    # two strands knotted across the mat, one clear of the other
    ([(16.6, 39.2, 1.4, 0.8), (18.5, 40.0, 1.7, 1), (21.0, 39.4, 1.8, 1), (23.6, 40.2, 1.7, 1), (26.4, 39.5, 1.8, 1),
      (29.2, 40.4, 1.7, 1), (32.0, 39.8, 1.8, 1), (34.8, 40.6, 1.6, 1), (37.4, 39.8, 1.2, 0.7)], 0.95),
    ([(18.4, 42.0, 1.2, 0.8), (20.6, 42.5, 1.3, 1), (23.0, 42.0, 1.4, 1), (25.8, 42.7, 1.3, 1), (28.4, 42.3, 1.4, 1),
      (31.0, 42.3, 1.3, 1), (33.6, 42.7, 1.3, 1), (36.4, 43.4, 1.0, 0.8)], 0.75),
    # drips (the sprite's 1-px ink tendrils), wandering down the panel into the wall: round, apart
    ([(22.8, 41.0, 1.4, 1), (23.0, 43.4, 1.1, 1), (23.6, 45.8, 0.9, 0.95), (23.4, 48.4, 0.75, 0.9),
      (23.7, 51.6, 0.6, 0.85), (23.5, 55.6, 0.5, 0.7)], 0.7),
    ([(27.9, 41.8, 1.4, 1), (28.1, 44.2, 1.1, 1), (28.4, 46.4, 0.8, 0.95), (28.5, 48.4, 0.6, 0.85),
      (28.5, 49.8, 0.45, 0.6)], 0.68),
    ([(33.0, 41.8, 1.4, 1), (33.9, 44.6, 1.1, 1), (33.6, 47.0, 0.9, 0.95), (32.7, 48.8, 0.7, 0.85),
      (32.4, 50.8, 0.5, 0.6)], 0.68),
    ([(36.5, 43.0, 1.2, 1), (36.6, 44.4, 1.0, 1), (36.4, 45.4, 0.6, 0.7)], 0.5),
]


def tissue_mat(M, mask, mat, part, k=4, height=1.1, thr=0.56, passes=3, ramp=None, lumps=0, soft=0):
    """Low membrane over the pixel mask: the mask blurred on a k-times grid and contoured at `thr`
    (marching squares, edge points interpolated), so its outline is smooth, not whole grid cells
    (fix round 1: the cell staircase read as stepped plates). Height from the blur, 0 on the
    contour, where the top meets the flat sealed base on the wall."""
    up = np.kron(mask.astype(float), np.ones((k, k)))
    pad = np.pad(up, k, mode="constant")
    for _ in range(passes):
        b = pad.copy()
        b[1:-1, 1:-1] = (pad[:-2, 1:-1] + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:] + pad[1:-1, 1:-1] * 4) / 8
        pad = b
    hh, ww = pad.shape
    # field at cell corners (grid nodes)
    cor = np.zeros((hh + 1, ww + 1))
    cor[1:-1, 1:-1] = (pad[:-1, :-1] + pad[1:, :-1] + pad[:-1, 1:] + pad[1:, 1:]) / 4
    ins = cor > thr
    hf = cor
    if soft:
        # height from a much softer blur of the mask, so the slope eases over ~1-2 px instead of
        # standing up at the contour (the contour still comes from `cor`)
        hp = np.pad(up, k * 3, mode="constant")
        for _ in range(soft):
            b = hp.copy()
            b[1:-1, 1:-1] = (hp[:-2, 1:-1] + hp[2:, 1:-1] + hp[1:-1, :-2] + hp[1:-1, 2:] + hp[1:-1, 1:-1] * 4) / 8
            hp = b
        hp = hp[k * 2:-k * 2, k * 2:-k * 2]
        hf = np.zeros((hh + 1, ww + 1))
        hf[1:-1, 1:-1] = (hp[:-1, :-1] + hp[1:, :-1] + hp[:-1, 1:] + hp[1:, 1:]) / 4
    verts = {}
    bump = np.zeros_like(cor)
    if lumps:
        # a fleshy mass, not a sheet: soft lumps scattered over the mask (fixed seed)
        rng = np.random.default_rng(45)
        js, is_ = np.nonzero(cor > thr + 0.15)
        jj, ii = np.mgrid[0:hh + 1, 0:ww + 1]
        for n in rng.choice(len(js), size=min(lumps, len(js)), replace=False):
            bump += np.exp(-(((jj - js[n]) ** 2 + (ii - is_[n]) ** 2) / (2 * (1.1 * k) ** 2)))
        bump = 0.6 * np.minimum(bump, 1.4)

    def zof_at(j, i):
        x = min(1.0, max(0.0, (hf[j, i] - thr) / (1 - thr)))
        prof = ramp(x) if ramp else min(1.0, x * 1.6) ** 0.6
        return ZB + height * prof * (1 + bump[j, i])

    def node(j, i, base):
        key = ("b" if base else "t", j, i)
        if key not in verts:
            verts[key] = M.vert(((i - k) / k, (j - k) / k, ZB if base else zof_at(j, i)))
        return verts[key]

    def edge(a, b):
        """Contour point on the grid edge between nodes a and b (one inside, one out): shared by the
        top and the base (height 0 there)."""
        key = ("e",) + (a + b if a < b else b + a)
        if key not in verts:
            va, vb = cor[a], cor[b]
            t = (thr - va) / (vb - va)
            j = a[0] + (b[0] - a[0]) * t
            i = a[1] + (b[1] - a[1]) * t
            verts[key] = M.vert(((i - k) / k, (j - k) / k, ZB))
        return verts[key]

    for j in range(hh):
        for i in range(ww):
            ring = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            flags = [ins[c] for c in ring]
            if not any(flags):
                continue
            top, bot = [], []
            for n in range(4):
                a, b = ring[n], ring[(n + 1) % 4]
                if flags[n]:
                    top.append(node(*a, False))
                    bot.append(node(*a, True))
                if flags[n] != flags[(n + 1) % 4]:
                    e = edge(a, b)
                    top.append(e)
                    bot.append(e)
            if len(top) >= 3:
                M.face(top[::-1], mat, part)
                M.face(bot, mat, part)


def to_object(name, M, mats, coll):
    bm = M.bm
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for mt in mats:
        me.materials.append(mt)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(40))
    except AttributeError:
        pass
    return obj


def surface_at(obj, u, v):
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    hit = bvh.ray_cast(to_blender(u, v, 40), Vector((0, 0, -1)))
    return hit


def add_eye(obj, coll, mats, mi, m_head, m_sock, m_lens, m_core):
    """Socket rim, lens and core on the head at the sprite's eye (rows 13-17, cols 19-25), facing up,
    east and south (towards the game camera); a brow plate arcs over its north-west side."""
    uc, vc = 22.4, 15.5
    hit = surface_at(obj, uc, vc)
    p = hit[0] * 12  # Blender units x 12
    ez = (hit[1] * 0.45 + Vector((0.42, -0.38, 0.82)).normalized() * 0.55).normalized()
    ex = Vector((1, 0, 0))
    ex = (ex - ez * ex.dot(ez)).normalized()
    ey = ez.cross(ex)
    brow = []
    for a in np.linspace(math.radians(100), math.radians(205), 8):
        u = uc + 3.7 * math.cos(a)
        v = vc - 3.1 * math.sin(a)
        h = surface_at(obj, u, v)
        z = h[0].z * 12 if h[0] is not None else ZB
        brow.append((u, v, z + 0.1, 0.6))
    brow[0] = brow[0][:3] + (0.25,)
    brow[-1] = brow[-1][:3] + (0.25,)
    M = Mesh()
    _eye_parts(M, p, ex, ey, ez, EYE_SINK, m_head, m_sock, m_lens, m_core)
    tube(M, brow, m_head, PID["brow"], sides=8, squash=0.7)
    bm = M.bm
    tmp = bpy.data.meshes.new("eye")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(tmp)
    bm.free()
    for mt in mats:
        tmp.materials.append(mt)
    eo = bpy.data.objects.new("eye", tmp)
    coll.objects.link(eo)
    tmp.shade_smooth()
    join(obj, [eo])


EYE_SINK = 0.75  # fix rounds 1-2: keeps the eye inside the +-0.35 u layer-2 band on the ball crown


class PxMesh(Mesh):
    """Mesh whose vert() takes Blender-unit points scaled by 12 (no u/v remap)."""

    def vert(self, p):
        return self.bm.verts.new(Vector(p) / 12)


def _eye_parts(M, p, ex, ey, ez, sink, m_head, m_sock, m_lens, m_core):
    PM = PxMesh()
    PM.bm.free()
    PM.bm, PM.part = M.bm, M.part
    c = p - ez * sink
    ellipsoid(PM, c - ez * 0.2, (ex, ey, ez), (3.1, 2.45, 0.9), m_sock, PID["eye"], seg=24, rings=8, cut=0.0)
    torus(PM, c + ez * 0.25, (ex, ey, ez), 2.85, 2.2, 0.42, m_head, PID["eye"], seg=30, sides=8)
    ellipsoid(PM, c + ez * 0.1, (ex, ey, ez), (2.45, 1.85, 0.85), m_lens, PID["eye"], seg=24, rings=8, cut=0.0)
    ellipsoid(PM, c + ez * 0.55 + ex * 0.3, (ex, ey, ez), (0.95, 0.8, 0.5), m_core, PID["eye"], seg=16, rings=6,
              cut=0.0)


def join(obj, others):
    bpy.ops.object.select_all(action="DESELECT")
    for o in [obj] + others:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    return obj


# --- cutting into pieces (fix round 1) ---------------------------------------------------------------

def split_open(obj, layout):
    """common.split_assembly without the cap fill: each piece keeps the part of `obj` inside its
    24x28 px box, open along the cut. The neighbouring piece closes the surface in the game, so no
    cap is needed; a filled cap pulled the smooth normals at the cut vertices (a dark seam through
    the head and torso), and on the outline shell it drew ink across the model. (Candidate for
    common.split_assembly(fill=False).)"""
    result = {}
    coll = obj.users_collection[0]
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        hw, hh = 12 / 12, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        for mt in obj.data.materials:
            mesh.materials.append(mt)
        piece = bpy.data.objects.new(name, mesh)
        coll.objects.link(piece)
        result[name] = piece
    return result


def keep_normals(piece, source, cx, cy):
    """Copy the uncut model's normals onto a piece (Data Transfer, custom normals, nearest face
    interpolated), so the shading runs across the cut as if the model were whole."""
    piece.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    mod = piece.modifiers.new("keep_normals", "DATA_TRANSFER")
    mod.object = source
    mod.use_loop_data = True
    mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "POLYINTERP_NEAREST"
    mod.use_object_transform = True
    bpy.ops.object.select_all(action="DESELECT")
    piece.select_set(True)
    bpy.context.view_layer.objects.active = piece
    bpy.ops.object.modifier_apply(modifier=mod.name)
    piece.location = (0, 0, 0)
    bpy.context.view_layer.update()


# --- main -----------------------------------------------------------------------------------------

PIECE_FRAMES = {"newshh-5": [5, 9, 13], "newshh-7": [7, 11, 15], "newshh-43": [43, 47, 51], "newshh-45": [45, 49, 53]}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):  # the startup scene's cube, camera and light
        bpy.data.objects.remove(o, do_unlink=True)
    lab, sprite = load_data()
    creature, coll, mats, mi = build(lab, sprite)
    # outline shell from the sealed creature (before any cut)
    shell = common.outline_shell(creature, coll, voxel=0.012, faces=8000, smooth=6, inside=0.006)
    if "--views" in argv:
        import importlib.util
        spec = importlib.util.spec_from_file_location("views_B", argv[argv.index("--viewsmod") + 1])
        vb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vb)
        vb.run(creature, None, shell, Path(argv[argv.index("--views") + 1]), PART_NAMES)
    model = creature.copy()
    model.data = creature.data.copy()
    coll.objects.link(model)
    model.name = NAME
    layout = [(n, (c0 + 12 - W / 2), (r0 + 14 - H / 2)) for n, c0, r0 in PIECES]
    # split_assembly wants screen px (x right, y down): X = cx/12, Y = -cy/12
    pieces = split_open(model, layout)
    spieces = split_open(shell, [(n + "_o", cx, cy) for n, cx, cy in layout])
    for n, cx, cy in layout:
        keep_normals(pieces[n], creature, cx, cy)
    for n, _, _ in layout:
        sp = spieces[n + "_o"]
        sp["tyrian_outline"] = True
        sp.data.materials.clear()
        sp.data.materials.append(bpy.data.materials["outline_shell"])
        sprites = [{"sheet": "newshh.shp", "size": 2, "frames": PIECE_FRAMES[n]}]
        if "--pieces" in argv:
            common.export_glb([pieces[n], sp], Path(argv[argv.index("--pieces") + 1]) / f"{n}.glb")
        else:
            common.export_sprite_model(WT, [pieces[n], sp], f"enemies/{n}", sprites)


if __name__ == "__main__":
    main()
