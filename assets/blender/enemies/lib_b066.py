"""GRYPHON (level 2.6 end boss) back spikes: newsh0-7 (left) and its mirror newsh0-9 (D179).

What it is: the upper halves (tips) of the GRYPHON's two long horns, swept back up the screen from
the skull and leaning toward each other. The lower halves are the D170 horn in assembly-newsh0-79
(pieces newsh0-45 / newsh0-47); this model continues that horn from the batch's cut at row 28 to
the tip, so it IS that horn: the same keeled section (HORN_SEC), the same material (pal 55, the tip
band rows 0-20 one palette step lighter, pal 56, the sprite's own median there), the same rise
(z 14.5 - 0.125 r px) and, at row 28, exactly the D170 ring (its stations 27.5 / 29.5 rebuilt here
from the reference sprites as assembly-newsh0-79.py build_horn computes them).

Readability first (small tilted game camera): a clean tapering spike whose keel catches the light, a
section that rounds up toward the tip, a slight upward curl, and the sprite's dark flute (col 13,
rows 17-27) as one continuous modelled channel with a pal 54 strip, fading out toward the tip. The
lower shaft widths are pchip-smoothed (no pixel staircase). Underside: the section's shallow belly,
closed. Outline shell from a sealed copy (D90/D118).

Units: c, r = assembly px (newsh0-7's tile is cols 72-96, rows 0-28); tile-local Blender
X = (c - 84) / 12, Y = (14 - r) / 12, Z = z px / 12 (absolute, as the D170 pieces).
newsh0-9 = mirror about assembly col 96.5: local X9 = -X7 + 1/12.

Run (via newsh0-7.py / newsh0-9.py): blender --background --python assets/blender/enemies/newsh0-7.py
"""
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
sys.path.insert(0, str(ROOT / "assets" / "blender"))
sys.path.insert(0, str(ROOT / "tools"))
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "newsh0-7"
TILE_C0, TILE_W, TILE_H = 72, 24, 28
CUT = 28.0          # the batch cut (bottom edge of this tile)
GROOVE_C = 85.5     # assembly col of the flute (sprite col 13 of the tile, its centre)


def X(c):
    return (c - TILE_C0 - TILE_W / 2) / 12


def Y(r):
    return (TILE_H / 2 - r) / 12


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# --------------------------------------------------------------------------------------------------
# Sprite data (regenerated from reference/, as assembly-newsh0-79.py compose_sprite)
# --------------------------------------------------------------------------------------------------

def compose_d170():
    lay = common.load_sprite(ROOT, "newsh0-39")["assemblyLayout"]
    W, H = 168, 84
    idx = -np.ones((H, W), int)
    cols = {}
    for e in lay:
        s = common.load_sprite(ROOT, e["model"])
        cols.update({int(k): tuple(v) for k, v in s["colors"].items()})
        px = np.array(s["frames"][0]["pixels"])
        h, w = px.shape
        x0, y0 = e["cx"] - w // 2 - 30, e["cy"] - h // 2 + 32
        m = px >= 0
        idx[y0:y0 + h, x0:x0 + w][m] = px[m]
    return idx, cols


IDX, COLORS = compose_d170()
_M = SM.masks(IDX.tolist(), COLORS)
F = np.array(_M["inner"], bool) | np.array(_M["free"], bool)

SPRITE = common.load_sprite(ROOT, NAME)
OWN = SM.masks(SPRITE["frames"][0]["pixels"], {int(k): tuple(v) for k, v in SPRITE["colors"].items()})
INNER = np.array(OWN["inner"], bool)


def d170_path():
    """The D170 horn sweep stations [(c, r, z, w, h)] (assembly-newsh0-79.py build_horn)."""
    rows = []
    for r in range(0, 44):
        cs = np.where(F[r, 78:97])[0]
        if len(cs):
            rows.append((r + 0.5, 78 + cs.min(), 78 + cs.max() + 1))
    rr = np.array([q[0] for q in rows])
    cc = np.array([(q[1] + q[2]) / 2 for q in rows])
    ww = np.array([(q[2] - q[1]) / 2 for q in rows])
    ker = np.ones(5) / 5
    cs_ = np.convolve(np.pad(cc, 2, mode="edge"), ker, "valid")
    ws_ = np.convolve(np.pad(ww, 2, mode="edge"), ker, "valid")
    out = {}
    for r, cm, wm in list(zip(rr, cs_, ws_))[1::2]:
        w = wm + 0.2
        ring = 1.0 + 0.03 * math.cos(2 * math.pi * r / 4.0) * smoothstep(8, 20, r)
        z = 14.5 - 5.5 * r / 44
        hr = 0.42 + 0.4 * smoothstep(26, 44, r)
        out[round(float(r), 2)] = (float(cm), float(r), z, w * ring, w * hr * ring)
    return out


D170 = d170_path()

# D170 horn section (u across, v up).
HORN_SEC = [(0.95 * u, v) for u, v in ((1.0, 0.0), (0.78, 0.5), (0.42, 0.86), (0.0, 1.0), (-0.42, 0.86),
                                       (-0.78, 0.5), (-1.0, 0.0), (-0.7, -0.5), (0.0, -0.66), (0.7, -0.5))]
SUBDIV = 4




def sec_point(k, t, s):
    """Point at parameter t of edge k of the section: the D170 10-gon (s 0) blended toward the
    Catmull-Rom curve through its corners (s 1)."""
    n = len(HORN_SEC)
    P = [Vector((u, v)) for u, v in HORN_SEC]
    p0, p1, p2, p3 = P[(k - 1) % n], P[k % n], P[(k + 1) % n], P[(k + 2) % n]
    lin = p1.lerp(p2, t)
    t2, t3 = t * t, t * t * t
    smo = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
    return lin.lerp(smo, s)


def top_at_u(u, s):
    """The point of the top arc (edges 2 and 3, u 0.399 -> -0.399) at u."""
    lo, hi = 0.0, 2.0
    for _ in range(40):
        mid = (lo + hi) / 2
        q = sec_point(2 + int(min(mid, 1.999)), mid - int(min(mid, 1.999)), s)
        if q.x > u:
            lo = mid
        else:
            hi = mid
    T = (lo + hi) / 2
    return sec_point(2 + int(min(T, 1.999)), T - int(min(T, 1.999)), s)


STRIP_PX = 0.42      # half width of the flute strip, px
STRIP_FACES = (3, 4)  # the two faces either side of the flute line in each ring band
FLUTE_FROM = 12.0


def section_for(s, ug, hw):
    """One ring's (u, v, on_top) points: the top arc sampled so that the flute line (ug) and its
    strip edges (ug +- hw) are vertices (a clean strip, no face-picked staircase), then the rest of
    the section on its own edges in SUBDIV steps (the D170 corners kept, so at the cut it is the D170
    ring exactly; there ug is 0, the keel corner)."""
    u2 = HORN_SEC[2][0]
    us = list(np.linspace(u2, ug + hw, 4)) + [ug] + list(np.linspace(ug - hw, -u2, 4))[:-1]
    out = []
    for u in us:
        q = top_at_u(u, s) if abs(u - u2) > 1e-9 else sec_point(2, 0.0, s)
        out.append((q.x, q.y, True))
    for k in range(4, 12):
        for j in range(SUBDIV):
            q = sec_point(k, j / SUBDIV, s)
            out.append((q.x, q.y, False))
    return out


# --------------------------------------------------------------------------------------------------
# Plan: centreline and width from the sprite's inner mask, blended into the D170 values at the cut
# --------------------------------------------------------------------------------------------------

def pchip(xs, ys, xq):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0], m[-1] = d[0], d[-1]
    out = []
    for x in np.atleast_1d(xq):
        i = int(np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2))
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        out.append(h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1])
    return np.array(out)


def steps(rows, vals):
    """Keys of a staircase edge: at each step (the row edge between two runs) the mean of the two
    edges, and each run's own value at its middle when the run is 3 rows or longer (2 rows in from
    both ends when it is 7 or longer). A smooth curve
    through them crosses every step at its corner, so each step's new pixel is half covered on its
    own row edge and the rows either side fall on the right side of half."""
    ks, vs = [], []
    i = 0
    runs = []
    while i < len(vals):
        j = i
        while j + 1 < len(vals) and vals[j + 1] == vals[i]:
            j += 1
        runs.append((rows[i], rows[j] + 1, vals[i]))
        i = j + 1
    for k, (a, b, v) in enumerate(runs):
        if b - a >= 7:      # a long straight run holds its edge to near both ends
            ks += [a + 2.0, b - 2.0]
            vs += [v, v]
        elif b - a >= 3 or k == 0:
            ks.append((a + b) / 2)
            vs.append(v)
        if k + 1 < len(runs):
            ks.append(float(b) + STEP_SHIFT)
            vs.append((v + runs[k + 1][2]) / 2)
    return ks, vs


STEP_SHIFT = float(os.environ.get("STEP_SHIFT", "0.0"))


# Width keys: the staircase of the inner mask sampled at each step's middle (half a pixel each side
# of a 1 px step), so every row's edge pixel is half covered at most where the sprite steps.
def plan():
    rows = [r for r in range(TILE_H) if INNER[r].any()]
    L = np.array([TILE_C0 + np.where(INNER[r])[0].min() for r in rows], float)
    R = np.array([TILE_C0 + np.where(INNER[r])[0].max() + 1 for r in rows], float)
    rc = np.array(rows, float) + 0.5
    # centre: 3-row weighted smoothing; edges: keys at the middle of each run of equal edges
    def runs(vals):
        ks, vs = [], []
        i = 0
        while i < len(vals):
            j = i
            while j + 1 < len(vals) and vals[j + 1] == vals[i]:
                j += 1
            ks.append((rc[i] + rc[j]) / 2)
            vs.append(vals[i])
            i = j + 1
        return ks, vs
    kl, vl = steps(rows, list(L))
    kr, vr = steps(rows, list(R))
    return rows, rc, L, R, (kl, vl), (kr, vr)


ROWS, RC, LEFT, RIGHT, KL, KR = plan()
TIP_R = 0.55          # the point (rows 0-1 are free tip-border pixels in the rule)
TIP_C = 15.25 + TILE_C0


def edges_at(r):
    """Own plan left / right edge at row r (pchip through the runs' middles; above the first inner
    row it closes to the tip point)."""
    kl, vl = KL
    kr, vr = KR
    kl2, vl2 = [TIP_R] + kl, [TIP_C - 0.02] + vl
    kr2, vr2 = [TIP_R] + kr, [TIP_C + 0.02] + vr
    # extend past the cut so the blend has data
    kl2, vl2 = kl2 + [CUT + 2], vl2 + [vl2[-1]]
    kr2, vr2 = kr2 + [CUT + 2], vr2 + [vr2[-1]]
    lo = float(pchip(kl2, vl2, [r])[0])
    hi = float(pchip(kr2, vr2, [r])[0])
    return lo, hi


def d170_at(r):
    """Linear interpolation of the D170 stations (c, z, w, h) at row r."""
    keys = sorted(D170)
    for a, b in zip(keys, keys[1:]):
        if a <= r <= b:
            t = (r - a) / (b - a)
            pa, pb = D170[a], D170[b]
            return tuple(pa[i] + (pb[i] - pa[i]) * t for i in (0, 2, 3, 4))
    raise ValueError(r)


W_PAD = float(os.environ.get("W_PAD", "0.05"))     # fitted: the section's widest point is u 0.95, so the plan edge needs a little room
CURL = 0.7       # px of extra rise at the tip (zero slope change at the cut)


def station(r):
    """(c, z, half width, half height, ring factor, smooth weight, groove depth) at row r < 27.5."""
    lo, hi = edges_at(r)
    c_own = (lo + hi) / 2
    w_own = max((hi - lo) / 2 + W_PAD * smoothstep(TIP_R, 4.0, r), 0.0) / 0.95
    c_d, z_d, w_d, h_d = d170_at(max(r, 1.5))
    b = smoothstep(24.0, 27.5, r)         # 0 = own plan, 1 = D170 at the cut
    c = c_own + (c_d - c_own) * b
    ring = 1.0 + 0.03 * math.cos(2 * math.pi * r / 4.0) * smoothstep(9, 17, r)
    w_d_bare = w_d / (1.0 + 0.03 * math.cos(2 * math.pi * 27.5 / 4.0))  # D170 w without its ring
    w = (w_own + (w_d_bare - w_own) * b) * ring
    hr_cut = 0.42 + 0.4 * smoothstep(26, 44, 27.5)
    hr = hr_cut + (0.8 - hr_cut) * (1 - smoothstep(5.0, 26.0, r))
    z = 14.5 - 0.125 * r + CURL * ((27.5 - r) / 27.5) ** 2.2
    gd = 0.34 * smoothstep(11.0, 20.0, r) * (1 - smoothstep(25.0, 27.5, r))
    s = 1 - smoothstep(24.5, 27.5, r)     # smooth section away from the cut
    return c, z, w, w * hr, s, gd


def fair_lower_shaft(st):
    """Fair the plan's pixel staircase out of the lower shaft: widths and centres of the stations in
    rows 12-27.4 are replaced by a pchip curve through keys every 2 rows (each the mean over its +-1
    row neighbourhood), blended in over rows 12-16 so the tip keeps its own plan. The last key is the
    last own station, so the join to the D170 ring keeps its value."""
    rr = np.array([q["r"] for q in st])
    for key in ("w", "c"):
        v = np.array([q[key] for q in st])
        ks = [float(x) for x in np.arange(12.0, 27.0, 2.0)] + [float(rr[-1])]
        kv = [float(np.mean(v[np.abs(rr - k) <= 1.0])) for k in ks]
        kv[-1] = float(v[-1])
        sm = pchip(ks, kv, rr)
        for q, x in zip(st, sm):
            if q["r"] >= 12.0:
                a = smoothstep(12.0, 16.0, q["r"])
                q[key] = q[key] + (float(x) - q[key]) * a
    monotone_edges(st)


def isotonic(v, increasing=True):
    """Pool-adjacent-violators: the closest monotone sequence to v."""
    sgn = 1.0 if increasing else -1.0
    blocks = []                       # [sum, count]
    for x in v:
        blocks.append([sgn * x, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            a = blocks.pop()
            blocks[-1][0] += a[0]
            blocks[-1][1] += a[1]
    out = []
    for sm, n in blocks:
        out += [sgn * sm / n] * n
    return out


MONO_FROM = (4.0, 4.5)   # rows from which the left edge only widens, and the right edge only widens
MONO_WIN = float(os.environ.get("MONO_WIN", "0.75"))   # half width of the moving mean, rows


def monotone_edges(st):
    """No lumps in the plan: below the tip, the left (outer) edge only moves out and the right edge
    only moves out, as the sprite's staircase does. Each edge is the isotonic fit of the faired edge,
    then a moving mean (+-MONO_WIN rows, narrowing to nothing at both ends so the tip and the D170
    join keep their values; a mean of a monotone run stays monotone) that rounds the plateaus off.
    The last own station (it meets the D170 ring) is kept as it is."""
    rr = np.array([q["r"] for q in st])
    L = np.array([q["c"] - 0.95 * q["w"] for q in st])
    R = np.array([q["c"] + 0.95 * q["w"] for q in st])
    for arr, r0, inc in ((L, MONO_FROM[0], False), (R, MONO_FROM[1], True)):
        sel = np.where(rr >= r0)[0][:-1]
        iso = np.array(isotonic(list(arr[sel]), inc))
        rs = rr[sel]
        sm = iso.copy()
        for k in range(len(sel)):
            hw = min(MONO_WIN, rs[k] - rs[0], rs[-1] - rs[k])
            sm[k] = float(np.mean(iso[np.abs(rs - rs[k]) <= hw + 1e-9]))
        arr[sel] = sm
    for q, lo, hi in zip(st, L, R):
        hr = q["h"] / q["w"]
        q["c"] = (lo + hi) / 2
        q["w"] = (hi - lo) / (2 * 0.95)
        q["h"] = q["w"] * hr


def build_stations():
    st = []
    r = 1.0
    while r < 27.4:
        c, z, w, h, s, gd = station(r)
        st.append(dict(c=c, r=r, z=z, w=w, h=h, s=s, gd=gd, tan=None))
        r += 0.5 if r > 3 else 0.25
    fair_lower_shaft(st)
    # the D170 stations themselves at and past the cut, with D170's tangents
    for rk, prev, nxt in ((27.5, 25.5, 29.5), (29.5, 27.5, 31.5)):
        c, rr, z, w, h = D170[rk]
        a, b = D170[prev], D170[nxt]
        t = Vector((X(b[0]) - X(a[0]), Y(b[1]) - Y(a[1]), 0)).normalized()
        st.append(dict(c=c, r=rr, z=z, w=w, h=h, s=0.0, gd=0.0, tan=t))
    return st


# --------------------------------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------------------------------

MATS = []


def mat(index, metallic, rough):
    m = common.palette_material(SPRITE, index, f"nsh07b{len(MATS)}", metallic=metallic, roughness=rough)
    MATS.append(m)
    return len(MATS) - 1


M_HORN = mat(55, 0.05, 0.42)    # D170 M_HORN: the base, rows 20-28 (sprite rows 21-27 mix 55/56; D170 below is 55)
M_TIP = mat(56, 0.05, 0.42)     # the same blue steel, one step lighter: rows 0-20 (sprite median 56)
TIP_BAND = 20.0                 # the colour step sits on a growth-ring crest (cos(2 pi r / 4) = 1)
M_FLUTE = mat(54, 0.05, 0.5)    # the dark strip down the flute


# --------------------------------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------------------------------

SIGMA = 0.32
BAND_DROP = 4.0       # rows the tip band reaches further down on the belly than on the flute line


def band_row(u, v, ug):
    """Row of the pal 56 / pal 55 boundary at section point (u, v): TIP_BAND on the flute line (the
    chevron's point, on top), easing down the flanks to TIP_BAND + BAND_DROP under the belly, a smooth
    function of the angle round the section (no per-face steps)."""
    a = math.atan2(u - ug, v)               # 0 on top, +-pi underneath
    return TIP_BAND + BAND_DROP * 0.5 * (1 - math.cos(a))


def cut_band(bm, verts, vals):
    """Cut the mesh along the zero set of the band field (vals[i] = row - band_row at verts[i]) and
    put pal 56 on the tip side, pal 55 on the base side: the colour boundary is one smooth cut edge
    through the faces, not a staircase of whole quads. Flute faces keep pal 54 on both sides."""
    g = {v: (x if abs(x) > 1e-6 else 1e-6) for v, x in zip(verts, vals)}
    for e in list(bm.edges):
        a, b = e.verts
        ga, gb = g[a], g[b]
        if ga * gb < 0:
            t = ga / (ga - gb)
            _e, nv = bmesh.utils.edge_split(e, a, t)
            g[nv] = 0.0
    for f in list(bm.faces):
        zs = [v for v in f.verts if g[v] == 0.0]
        if len(zs) == 2 and not any(e for e in f.edges if set(e.verts) == set(zs)):
            bmesh.utils.face_split(f, zs[0], zs[1])
    for f in bm.faces:
        if f.material_index == M_FLUTE:
            continue
        m = sum(g[v] for v in f.verts) / len(f.verts)
        f.material_index = M_TIP if m < 0 else M_HORN


def build_horn():
    st = build_stations()
    bm = bmesh.new()
    up = Vector((0, 0, 1))
    pts = [Vector((X(s["c"]), Y(s["r"]), s["z"] / 12)) for s in st]
    rings, meta = [], []
    tip = Vector((X(TIP_C), Y(TIP_R), (14.5 - 0.125 * TIP_R + CURL * ((27.5 - TIP_R) / 27.5) ** 2.2) / 12))
    rings.append([bm.verts.new(tip)])
    meta.append(None)
    band_val = [TIP_R - TIP_BAND]
    for i, s in enumerate(st):
        if s["tan"] is not None:
            t = s["tan"]
        else:
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            t = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        side = t.cross(up)
        # the flute line in section coordinates (eased onto the keel, u 0, at the cut)
        ug = (GROOVE_C - s["c"]) / (s["w"] * side.x) * (1 - smoothstep(25.0, 27.5, s["r"]))
        hw = min(max(STRIP_PX * smoothstep(FLUTE_FROM, FLUTE_FROM + 8.0, s["r"]), 0.02) / s["w"], 0.2)
        lim = 0.399 - hw - 0.06
        ug = max(-lim, min(lim, ug))
        ring = []
        for u, v, top in section_for(s["s"], ug, hw):
            band_val.append(s["r"] - band_row(u, v, ug))
            if top and s["gd"] > 0:
                v -= s["gd"] * math.exp(-0.5 * ((u - ug) * s["w"] / SIGMA) ** 2) / s["h"]
            ring.append(bm.verts.new(pts[i] + side * (u * s["w"] / 12) + up * (v * s["h"] / 12)))
        rings.append(ring)
        meta.append(s)
    n = len(rings[-1])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        rr = meta[k + 1]["r"] if meta[k] is None else (meta[k]["r"] + meta[k + 1]["r"]) / 2
        for j in range(n):
            jn = (j + 1) % n
            if len(r0) == 1:
                f = bm.faces.new((r0[0], r1[jn], r1[j]))
            else:
                f = bm.faces.new((r0[j], r0[jn], r1[jn], r1[j]))
            f.smooth = True
            f.material_index = M_FLUTE if (j in STRIP_FACES and rr > FLUTE_FROM) else M_HORN
    f = bm.faces.new(rings[-1])
    f.material_index = M_HORN
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cut_band(bm, [v for rg in rings for v in rg], band_val)
    # the batch cut at row 28, capped (the D170 piece below is cut on the same plane)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    cut = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, Y(CUT), 0), plane_no=(0, -1, 0), clear_outer=True)
    edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
    res = bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    for f in res["faces"]:
        f.smooth = False
        f.material_index = M_HORN
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in MATS:
        me.materials.append(m)
    return me


def mirror_mesh(me, name):
    """newsh0-9: mirrored about assembly col 96.5 (local X9 = -X7 + 1/12), winding restored."""
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.x = -v.co.x + 1 / 12
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in me.materials:
        out.materials.append(m)
    return out


def make_object(me, name, coll):
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    me.set_sharp_from_angle(angle=math.radians(40))
    sealed = o.copy()
    sealed.data = me.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    sh = common.outline_shell(sealed, coll, voxel=0.01, faces=900, inside=0.003)
    sh.name = sh.data.name = f"{name}_outline"
    bpy.data.objects.remove(sealed, do_unlink=True)
    return o, sh


def run(name, script_file, groove_col=None, groove_from=None):
    """Build and export newsh0-7 (the horn) or newsh0-9 (its mirror)."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    coll = common.reset_collection(name)
    me = build_horn()
    if name == "newsh0-9":
        me = mirror_mesh(me, name)
    obj, shell = make_object(me, name, coll)
    print("tris", sum(len(p.vertices) - 2 for p in me.polygons))
    sprite = SPRITE if name == NAME else common.load_sprite(ROOT, name)
    common.export_sprite_model(ROOT, [obj, shell], f"enemies/{name}", sprite["sprites"])
