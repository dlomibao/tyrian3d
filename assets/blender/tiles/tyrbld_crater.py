"""The small craters in TYRIAN's islands (map 1-9, layer 2; tile 153, one tile, no enemy): three
bore holes sunk into the island's grey rock, each in a machined brass collar clamped with pink
fittings, and brass pipes laid over the rock between them. A big bore (upper right) and a small one
(left) glow red deep down; a little capped socket sits lower right. Hard-surface rebuild (D65,
D141), design A of structure wave 2.

The tile is authoritative (CLAUDE.md art rules 1-3): every collar outline is a smooth periodic
radial curve and every pipe a tube along a smooth spline, both fitted to the tile's own-parts mask
(brass/tan/pink/red pixels plus the convex hull of each collar's pixels: the grey arc a collar shows
on its upper right is part of the collar) by a scratch fitting script (mean IoU at 1x and
2x samples); the constants below are its result. Colours are the tile's per-region palette indices
(trimmed median by luminance): collars 24 (small 25), the upper-right arcs of the big and small
collars steel 8 / 5 (the tile paints them grey), pipes 167 (the top pipe brass 24: its own pixels
are 24/28/25/27), pink fittings 77, bore walls 2, the core 114 (a low dark-red glow, emission 1.3,
an ellipse over the tile's ~3x2 px red patch) ringed by 66, the socket's cap 167 with a small dark
hole on the tile's index-4 pixel.

How it is built (pattern px, y down; heights in units, layer 2: z = 0 the island's rock top):
- Collars: a lofted band (chamfered section with a machined groove along its top) round the
  fitted outline, split into arcs with 0.15 px panel gaps where brass meets the steel segment; a
  narrow inner lip; the bore below it, stepped inward by machined ribs, down to a floor at -0.24
  with a glowing domed core. The rock is cut under each bore and under the socket, whose cap is
  recessed below the rock's top (Structure.rock(cut=...)). The build prints the visible top view's
  IoU (a z-buffer: parts buried under the plain rock don't count; Building.coverage counts them).
- Pink fittings: saddle clamps lofted along the collar (chamfered end stations) with a bolt head,
  at the tile's pink pixels; the top pipe ends in a pink floor coupling.
- Pipes: swept tubes lying on the rock, sleeves where they meet a collar and couplings along their
  length; free ends turn down into the rock through a flange.
- Underside: the rock slab (plain, unbaked, as the per-tile islands) closes it; bores end in floors.
Texture: the model's own AO/roughness bake only (lib_l1bld bake_model), no concept projection, no
outline shell (tile models draw no ink outline, D141).

Build (writes public/models/tiles/shapesz/tyrbld-crater.glb and its tileModels json):

    tools/build-models.sh -j 2 assets/blender/tiles/tyrbld_crater.py

    /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \\
        --python assets/blender/tiles/tyrbld_crater.py -- [--no-bake] [--preview <dir>]
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

PX = lt.PX

# --- Fitted layout (tools/fit3.py; pattern px) -----------------------------------------------------
# rings: centre (px) then 24 outline radii (px) at screen angles 0, 15, ... 345 degrees (a rotated
# superellipse times low harmonics; the big ring's 30, 210 and 285 degree radii nudged out by hand
# against the visible top view, fix round 1); pipes: control points (px) and radius (px); flanges: (px, py, r).
PARAMS = {
 "rings": {
  "big": [15.305, 9.838, 6.665, 6.871, 7.298, 6.215, 5.223, 4.53, 4.269, 4.38, 4.789, 5.411, 6.127, 6.596, 6.526, 6.466, 7.005, 6.547, 5.942, 5.274, 4.713, 4.584, 4.23, 4.508, 5.234, 6.149],
  "small": [5.98, 16.896, 4.096, 4.137, 4.056, 3.786, 3.468, 3.236, 3.151, 3.243, 3.476, 3.786, 4.034, 4.095, 4.068, 4.122, 4.052, 3.786, 3.467, 3.231, 3.145, 3.241, 3.485, 3.808, 4.068, 4.131],
  "socket": [20.026, 23.032, 3.201, 3.248, 3.351, 3.392, 3.321, 3.191, 3.107, 3.157, 3.285, 3.383, 3.373, 3.278, 3.201, 3.248, 3.351, 3.392, 3.321, 3.191, 3.107, 3.157, 3.285, 3.383, 3.373, 3.278],
 },
 "pipes": {
  "top": ([(11.615, 0.293), (10.35, 1.41), (8.337, 2.515), (6.9, 3.4), (6.5, 4.151), (7.306, 5.727), (7.441, 7.271)], 0.59),
  "left_a": ([(0.6, 6.386), (1.6, 6.6), (2.695, 7.66), (3.8, 8.8), (4.36, 10.3), (4.173, 11.947), (3.3, 12.6)], 0.651),
  "left_b": ([(1.2, 7.254), (1.3, 7.6), (2.2, 8.5), (3.19, 9.6), (3.371, 10.6), (3.1, 12.076), (2.3, 12.5)], 0.45),
  "link": ([(8.324, 15.001), (9.451, 14.3), (10.449, 13.3)], 0.54),
  "drop_a": ([(19.257, 13.6), (18.709, 15.737), (18.4, 17.6), (17.847, 19.892), (18.872, 20.658)], 0.68),
  "drop_b": ([(17.6, 14.0), (17.6, 15.8), (17.2, 17.4), (16.352, 18.3), (15.411, 18.58)], 0.599),
  "drop_c": ([(19.3, 14.2), (18.948, 16.5), (19.543, 18.519)], 0.45),
  "low_a": ([(9.548, 18.6), (9.435, 21.379), (10.735, 21.6), (11.66, 22.406), (13.524, 22.5)], 0.615),
  "low_b": ([(6.768, 20.352), (8.071, 21.201), (9.675, 22.598), (11.233, 23.693), (12.313, 25.016), (13.344, 24.795), (12.933, 26.149), (10.004, 26.003), (8.315, 25.8), (6.731, 25.468)], 0.679),
 },
 "flanges": {
  "top_end": [6.484, 6.131, 1.109],
 },
}

# --- Palette (the tile's per-region trimmed medians, tools/colours.py) ---------------------------
P_COLLAR = {"big": 24, "small": 25, "socket": 24}
P_STEEL = {"big": 8, "small": 5}
P_PIPE = 167
P_PIPE_TOP = 24  # the top pipe: its own pixels are brass (24/28/25/27), trimmed median 24
P_PINK = 77
P_WALL = 2
P_WALL_HI = 3
P_LIP = 5
P_CORE = 114
CORE_EMIT = 1.3  # the tile's core is dark maroon (113/114): a low glow, not a bright red blob
P_CORE_RING = 66
P_CORE_DIM = 113
P_CAP = 167
P_BOLT = 24

# Steel arcs (screen angle, degrees: 0 right, 90 down) and the pink clamps (centre angle, arc px).
STEEL = {"big": (-80.0, -6.0), "small": (-84.0, -12.0)}
CLAMPS = {"big": [(-130.0, 3.2), (172.0, 1.8), (3.0, 2.0), (52.0, 1.7)],
          "small": [(-110.0, 1.9), (-168.0, 1.7)],
          "socket": [(-135.0, 1.7), (-10.0, 1.6)]}
# Band widths (px), lip widths (px), bore depths, glow (core radius as a fraction of the floor).
BAND_W = {"big": 1.35, "small": 1.15, "socket": 1.1}
LIP_W = {"big": 0.45, "small": 0.35, "socket": 0.3}
DEPTH = {"big": -0.24, "small": -0.2, "socket": -0.03}
# The core's centre (offset from the ring centre, px) and its ellipse semi-axes (px): the tile's
# red patch (big: 113/114 over x 14-17, y 8-9, a ~3x2 px rectangle; small: 114 at (5-6,16),(5,17)).
# The socket's dark centre hole sits on the tile's index-4 pixel (20, 22).
CORE_SHIFT = {"big": (0.35, -0.85), "small": (-0.15, -0.15), "socket": (0.45, -0.5)}
CORE_AXES = {"big": (1.55, 0.95), "small": (0.95, 0.72)}

BAND_TOP = 0.095
BAND_FOOT = -0.035
CLAMP_TOP = 0.13
LIP_TOP = 0.035
PIPE_SINK = 0.15  # fraction of the radius a pipe sits in the rock
N_RING = 40


# --- Small helpers -----------------------------------------------------------------------------------

def catmull(pts, step=0.2):
    """Catmull-Rom through `pts` (px), sampled every `step` px: the same curve tools/fit3.py fits."""
    P = np.array(pts, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, int(np.ceil(np.linalg.norm(p2 - p1) / step)))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def radial(radii, th):
    """The collar's outline radius (px) at screen angle th: periodic Catmull-Rom of K radii."""
    K = len(radii)
    u = (th % (2 * math.pi)) / (2 * math.pi) * K
    i = int(math.floor(u))
    t = u - i
    p0, p1, p2, p3 = radii[(i - 1) % K], radii[i % K], radii[(i + 1) % K], radii[(i + 2) % K]
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


class Ring:
    def __init__(self, params):
        self.cx, self.cy = params[0], params[1]
        self.radii = list(params[2:])

    def pt(self, th, d):
        r = max(0.25, radial(self.radii, th) - d)
        return self.cx + r * math.cos(th), self.cy + r * math.sin(th)

    def min_r(self):
        return min(radial(self.radii, 2 * math.pi * i / 64) for i in range(64))


def loft(bm, s, stations, mats, closed_u, closed_v=True, cap=True):
    """Loft rings of points: `stations` [[(px, py, z), ...], ...] (each a section, all the same
    length). Section points join in a loop when closed_v; consecutive stations join, and the
    last back to the first when closed_u. `mats(i_station, j_point)` gives each face's material.
    Open ends are capped when `cap`."""
    vs = [[bm.verts.new((s.x(p[0]), s.y(p[1]), p[2])) for p in st] for st in stations]
    nu, nv = len(vs), len(vs[0])
    for i in range(nu if closed_u else nu - 1):
        a, b = vs[i], vs[(i + 1) % nu]
        for j in range(nv if closed_v else nv - 1):
            k = (j + 1) % nv
            f = bm.faces.new((a[j], b[j], b[k], a[k]))
            f.material_index = mats(i, j)
    if cap and not closed_u:
        for ring, mi in ((vs[0], mats(0, 0)), (vs[-1], mats(nu - 2, 0))):
            try:
                bm.faces.new(ring).material_index = mi
            except ValueError:
                pass
    return vs


# --- Parts -------------------------------------------------------------------------------------------

def band_profile(w):
    """The collar band's closed section [(inset px, z)], outer edge first (inset 0 = outline): a
    chamfered top with a machined groove along its middle."""
    c = min(0.28, w * 0.22)
    g = w * 0.5
    return [(0.0, BAND_FOOT), (0.0, BAND_TOP - 0.025), (c, BAND_TOP), (g - 0.14, BAND_TOP), (g - 0.07, BAND_TOP - 0.014),
            (g + 0.07, BAND_TOP - 0.014), (g + 0.14, BAND_TOP), (w - c, BAND_TOP), (w, BAND_TOP - 0.03), (w, BAND_FOOT)]


def arc_loft(bm, s, ring, a0, a1, prof, mat, n=None, end_shrink=None):
    """A section `prof` [(inset, z)] lofted along the ring's outline from angle a0 to a1 (rad),
    capped; `end_shrink` (d_inset, dz): the end stations pulled in and down (a chamfered end)."""
    n = n or max(4, int(abs(a1 - a0) / (2 * math.pi) * N_RING) + 1)
    ths = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
    stations = []
    for i, th in enumerate(ths):
        p = prof
        if end_shrink and i in (0, n):
            dd, dz = end_shrink
            lo = min(z for _, z in prof)
            p = [(d + (dd if d < 0.5 * (prof[0][0] + max(q[0] for q in prof)) else -dd), z if z <= lo + 1e-6 else z - dz) for d, z in prof]
        stations.append([ring.pt(th, d) + (z,) for d, z in p])
    if end_shrink:
        # chamfer: second and second-last stations at full size
        pass
    loft(bm, s, stations, lambda i, j: mat, closed_u=False)


def collar(s, name, ring, mats):
    """Band (brass, with the steel arc), lip, stepped bore, floor and glowing core."""
    bm = bmesh.new()
    w = BAND_W[name]
    prof = band_profile(w)
    brass, steel = mats["collar"], mats.get("steel")
    gap = 0.15  # px: panel gap between brass and steel
    if name in STEEL:
        a0, a1 = (math.radians(v) for v in STEEL[name])
        r_mean = sum(ring.radii) / len(ring.radii)
        da = gap / r_mean
        arc_loft(bm, s, ring, a0 + da / 2, a1 - da / 2, prof, steel)
        arc_loft(bm, s, ring, a1 + da / 2, a0 + 2 * math.pi - da / 2, prof, brass)
    else:
        ths = [2 * math.pi * i / N_RING for i in range(N_RING)]
        loft(bm, s, [[ring.pt(th, d) + (z,) for d, z in prof] for th in ths], lambda i, j: brass, closed_u=True)

    # The inner lip and the bore: one open surface of revolution, from the band's inner foot in.
    lw = LIP_W[name]
    depth = DEPTH[name]
    d0 = w
    # One closed solid of revolution: up the outside just inside the collar's outline from the
    # slab's bottom (it closes the rock's cut from below: a plain shape), over under the band, the
    # lip, down the stepped bore; the floor closes its top, a flat cap its bottom.
    zb = tb.L2_SLAB_BOTTOM + 0.004
    sec = [(0.15, zb), (0.15, BAND_FOOT + 0.01), (d0 - 0.05, BAND_TOP - 0.035), (d0 + 0.02, LIP_TOP), (d0 + lw, LIP_TOP - 0.01), (d0 + lw, 0.0)]
    mats_sec = [mats["wall"], mats["wall"], mats["lip"], mats["lip"], mats["wall_hi"]]
    if name == "socket":
        # A shallow capped port: a recessed cap and a small dark centre hole.
        sec += [(d0 + lw, depth)]
        mats_sec += [mats["wall_hi"]]
    else:
        d = d0 + lw
        z = 0.0
        steps = [(-0.06, 0.18), (-0.12, 0.22), (-0.18, 0.25)]
        for zs, inset in steps:
            sec += [(d, zs), (d + inset, zs)]
            mats_sec += [mats["wall_hi"] if zs > -0.07 else mats["wall"], mats["wall"]]
            d += inset
        sec += [(d, depth)]
        mats_sec += [mats["wall"]]
    ths = [2 * math.pi * i / N_RING for i in range(N_RING)]
    vs = loft(bm, s, [[ring.pt(th, dd) + (zz,) for dd, zz in sec] for th in ths],
              lambda i, j: mats_sec[j], closed_u=True, closed_v=False, cap=False)
    bm.faces.new([v[0] for v in reversed(vs)]).material_index = mats["wall"]
    # Floor: the last ring closed with a fan to the (shifted) centre, the core ring and the core.
    last = [v[-1] for v in vs]
    cx, cy = ring.cx + CORE_SHIFT[name][0], ring.cy + CORE_SHIFT[name][1]
    if name == "socket":
        cap = mats["cap"]
        hole_r = 0.55
        inner = [bm.verts.new((s.x(cx + hole_r * math.cos(t)), s.y(cy + hole_r * math.sin(t)), depth)) for t in ths]
        for i in range(N_RING):
            j = (i + 1) % N_RING
            bm.faces.new((last[i], last[j], inner[j], inner[i])).material_index = cap
        bot = [bm.verts.new((v.co.x, v.co.y, depth - 0.05)) for v in inner]
        for i in range(N_RING):
            j = (i + 1) % N_RING
            bm.faces.new((inner[i], inner[j], bot[j], bot[i])).material_index = mats["wall"]
        bm.faces.new(list(reversed(bot))).material_index = mats["wall"]
    else:
        ea, eb = CORE_AXES[name]
        # A round core: an ellipse about the core's centre (the tile's red patch), kept inside the
        # floor (92% of the floor's rim radius in that direction, from the ring's centre).
        def fpt(t, f, z):
            qx, qy = cx + ea * f * math.cos(t), cy + eb * f * math.sin(t)
            ang = math.atan2(qy - ring.cy, qx - ring.cx)
            lim = 0.92 * (radial(ring.radii, ang) - sec[-1][0])
            dist = math.hypot(qx - ring.cx, qy - ring.cy)
            if dist > lim:
                qx, qy = ring.cx + (qx - ring.cx) * lim / dist, ring.cy + (qy - ring.cy) * lim / dist
            return bm.verts.new((s.x(qx), s.y(qy), z))
        r1 = [fpt(t, 1.3, depth) for t in ths]
        r2 = [fpt(t, 1.0, depth + 0.004) for t in ths]
        r3 = [fpt(t, 0.66, depth + 0.012) for t in ths]
        r4 = [fpt(t, 0.3, depth + 0.018) for t in ths]
        for (a, b), m in ((( last, r1), mats["wall"]), ((r1, r2), mats["core_ring"]), ((r2, r3), mats["core_dim"]), ((r3, r4), mats["core"])):
            for i in range(N_RING):
                j = (i + 1) % N_RING
                bm.faces.new((a[i], a[j], b[j], b[i])).material_index = m
        mid = bm.verts.new((s.x(cx), s.y(cy), depth + 0.02))
        for i in range(N_RING):
            j = (i + 1) % N_RING
            bm.faces.new((r4[i], r4[j], mid)).material_index = mats["core"]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)

    # Pink saddle clamps over the band, each with a bolt head.
    for ang, length in CLAMPS[name]:
        th = math.radians(ang)
        r_here = radial(ring.radii, th) - w / 2
        half = length / 2 / max(1.0, r_here)
        rr = 0.22  # px: the saddle's rounded shoulders
        cprof = [(0.0, BAND_FOOT + 0.02)]
        cprof += [(rr - rr * math.cos(a), CLAMP_TOP - 0.03 + 0.03 * math.sin(a)) for a in (0, math.pi / 4, math.pi / 2)]
        cprof += [(w + 0.08 - rr + rr * math.sin(a), CLAMP_TOP - 0.03 + 0.03 * math.cos(a)) for a in (0, math.pi / 4, math.pi / 2)]
        cprof += [(w + 0.08, BAND_FOOT + 0.02)]
        bm = bmesh.new()
        n = 6
        ths_c = [th - half + 2 * half * i / n for i in range(n + 1)]
        stations = []
        for i, t in enumerate(ths_c):
            shrink = 0.1 if i in (0, n) else 0.0
            dz = 0.025 if i in (0, n) else 0.0
            stations.append([ring.pt(t, d + (shrink if d < w / 2 else -shrink)) + (z if z < 0.05 else z - dz,) for d, z in cprof])
        loft(bm, s, stations, lambda i, j: mats["pink"], closed_u=False)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm)
        bx, by = ring.pt(th, w / 2)
        s.bolts([(bx, by)], CLAMP_TOP, r_px=0.32, height=0.012, mat=mats["bolt"])


def tube(s, path3, r, mat, sides=8, cap=True, smooth=True):
    """A tube of radius r (px) along `path3` [(px, py, z)], parallel-transport frames."""
    bm = bmesh.new()
    P = np.array([(s.x(p[0]), s.y(p[1]), p[2]) for p in path3])
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None] + 1e-12
    up = np.array([0.0, 0.0, 1.0])
    nrm = np.cross(T[0], up)
    if np.linalg.norm(nrm) < 1e-6:
        nrm = np.array([1.0, 0.0, 0.0])
    nrm /= np.linalg.norm(nrm)
    rings = []
    rad = r * PX
    for i in range(len(P)):
        if i:
            nrm = nrm - T[i] * (nrm @ T[i])
            nrm /= np.linalg.norm(nrm) + 1e-12
        bi = np.cross(T[i], nrm)
        rings.append([bm.verts.new(tuple(P[i] + rad * (math.cos(a) * nrm + math.sin(a) * bi)))
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k])).material_index = mat
    if cap:
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=smooth)


def pipe(s, name, pts, r, mats, ends):
    """A pipe lying on the rock along the fitted control points: `ends` (start, end) each "dive"
    (turns down into the rock through a flange), "sleeve" (meets a collar: a sleeve) or None."""
    pts = [(min(max(x, r + 0.1), 24 - r - 0.1), min(max(y, r + 0.1), 28 - r - 0.1)) for x, y in pts]
    c = catmull(pts, step=0.35)
    zc = r * PX * (1 - PIPE_SINK)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))])
    total = L[-1]
    z = np.full(len(c), zc)
    dive_len = 1.3
    for k, kind in enumerate(ends):
        if kind == "dive":
            dist = L if k == 0 else total - L
            u = np.clip(1 - dist / dive_len, 0, 1)
            z -= (zc + r * PX * 1.6) * u ** 2
    path3 = [(x, y, zz) for (x, y), zz in zip(c, z)]
    tube(s, path3, r, mats["pipe"])
    # Sleeves at collars, flanges where it dives, couplings along a long run.
    P3 = np.array(path3)

    def span(a, b, n=4):
        """The path between arc lengths a and b, resampled (n points)."""
        ls = np.linspace(max(0.0, a), min(total, b), n)
        return [tuple(np.interp(l, L, P3[:, k]) for k in range(3)) for l in ls]

    for k, kind in enumerate(ends):
        if kind == "sleeve":
            a, b = (0.1, 0.75) if k == 0 else (total - 0.75, total - 0.1)
            tube(s, span(a, b), r * 1.2, mats["sleeve"], sides=8, smooth=False)
        if kind == "dive":
            near = (L <= dive_len) if k == 0 else (L >= total - dive_len)
            i = int(np.argmin(np.abs(z) + np.where(near, 0, 9)))
            fx, fy = c[i]
            s.slab(s.ngon(fx, fy, r * 1.3, 10), -0.02, 0.018, mats["sleeve"], chamfer_px=0.15, drop=0.008)
    if total > 6.0:
        for f in (0.38, 0.72):
            l0 = total * f
            seg = span(l0 - 0.3, l0 + 0.3)
            if min(p[2] for p in seg) > 0.0:
                tube(s, seg, r * 1.16, mats["sleeve"], sides=8, smooth=False)


PIPE_ENDS = {
    "top": ("dive", "dive"),
    "left_a": ("dive", "dive"), "left_b": ("dive", "dive"),
    "link": ("sleeve", "sleeve"),
    "drop_a": ("sleeve", "sleeve"), "drop_b": ("sleeve", "dive"), "drop_c": ("sleeve", "dive"),
    "low_a": ("sleeve", "dive"), "low_b": ("sleeve", "dive"),
}


def own_mask(g):
    """What tile 153 paints for the crater's own parts (bool, pattern px): its brass, tan, pink and
    red pixels, plus the convex hull of each collar's pixels (brass/tan/pink/red/dark), so a
    collar's grey arc and its dark bore count. The rule tools/fit3.py fits to."""
    px = g
    ramp = ((px >= 24) & (px <= 31)) | ((px >= 160) & (px <= 175)) | ((px >= 76) & (px <= 79)) | np.isin(px, [66, 67, 113, 114])
    dark = ((px >= 0) & (px <= 3)) | np.isin(px, [161, 162])
    H, W = px.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    m = ramp.copy()
    rings = {"big": ((9, 5, 21, 13), {(9, 13)}), "small": ((2, 14, 9, 19), {(8, 14), (9, 14), (9, 15)}),
             "socket": ((17, 20, 22, 25), set())}
    for (x0, y0, x1, y1), drop in rings.values():
        pts = []
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if (ramp[y, x] or dark[y, x]) and (x, y) not in drop:
                    pts += [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
        hull = _hull(pts)
        inside = np.ones((H, W), bool)
        for (ax, ay), (bx, by) in zip(hull, hull[1:] + hull[:1]):
            inside &= (bx - ax) * (yy - ay) - (by - ay) * (xx - ax) >= -1e-9
        m |= inside
    return m


def _hull(pts):
    """Convex hull (Andrew's monotone chain), counter-clockwise in screen axes' math sense."""
    P = sorted(set(pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def iou_at(s, objects, mask, scale):
    cov = s.coverage(objects, scale=scale)
    ref = np.kron(mask, np.ones((scale, scale), bool))
    return float((cov & ref).sum()) / max(1, (cov | ref).sum()), cov, ref


def visible_top(s, objects, scale=1):
    """What the model shows from straight above: bool (H*scale, W*scale), a sample on where the
    topmost face over the sample's centre is the model's (not the plain rock). A z-buffer over every
    triangle, plain ones included, so a part buried under the rock does not count (Building.coverage
    counts it: report as a shared follow-up)."""
    H, W = s.H * scale, s.W * scale
    zbuf = np.full((H, W), -1e9)
    top = np.zeros((H, W), bool)
    for o in objects:
        if o.type != "MESH":
            continue
        me, mw = o.data, o.matrix_world
        me.calc_loop_triangles()
        co = np.array([tuple(mw @ v.co) for v in me.vertices]).reshape(-1, 3)
        if not len(co):
            continue
        sx = (co[:, 0] / lt.PX + s.W / 2) * scale
        sy = (s.H / 2 - co[:, 1] / lt.PX) * scale
        plain = [bool(m and m.get("tyrian_plain")) for m in me.materials]
        for tri in me.loop_triangles:
            vi = list(tri.vertices)
            xs, ys, zs = sx[vi], sy[vi], co[vi, 2]
            x0, x1 = max(0, int(np.floor(xs.min()))), min(W, int(np.ceil(xs.max())) + 1)
            y0, y1 = max(0, int(np.floor(ys.min()))), min(H, int(np.ceil(ys.max())) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            gy, gx = np.mgrid[y0:y1, x0:x1] + 0.5
            (ax, bx, cx), (ay, by, cy) = xs, ys
            d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(d) < 1e-12:
                continue
            l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
            l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            z = l1 * zs[0] + l2 * zs[1] + l3 * zs[2]
            win = inside & (z > zbuf[y0:y1, x0:x1] + 1e-5)
            zbuf[y0:y1, x0:x1][win] = z[win]
            is_plain = bool(plain and plain[tri.material_index])
            top[y0:y1, x0:x1][win] = not is_plain
    return top


def build(bake=True, preview=None):
    lb.clear_scene()
    s = tb.Structure("crater")
    P = PARAMS
    mask = own_mask(s.grid)
    mats = {
        "pipe": s.m(P_PIPE, roughness=0.42, metallic=0.55),
        "sleeve": s.m(P_COLLAR["big"], roughness=0.35, metallic=0.6),
        "pink": s.m(P_PINK, roughness=0.5, metallic=0.05),
        "bolt": s.m(P_BOLT, roughness=0.35, metallic=0.6),
        "lip": s.m(P_LIP, roughness=0.6, metallic=0.2),
        "wall": s.m(P_WALL, roughness=0.85),
        "wall_hi": s.m(P_WALL_HI, roughness=0.8),
        "core": s.pal(P_CORE, emission_strength=CORE_EMIT, roughness=0.45),
        "core_ring": s.m(P_CORE_RING, roughness=0.6),
        "core_dim": s.pal(P_CORE_DIM, emission_strength=0.6, roughness=0.5),
        "cap": s.m(P_CAP, roughness=0.5, metallic=0.4),
    }
    rings = {k: Ring(v) for k, v in P["rings"].items()}
    for name, ring in rings.items():
        m = dict(mats)
        m["collar"] = s.m(P_COLLAR[name], roughness=0.38, metallic=0.6)
        if name in P_STEEL:
            m["steel"] = s.m(P_STEEL[name], roughness=0.35, metallic=0.55)
        collar(s, name, ring, m)
    top_mats = dict(mats, pipe=s.m(P_PIPE_TOP, roughness=0.4, metallic=0.58))
    for name, (pts, r) in P["pipes"].items():
        pipe(s, name, pts, r, top_mats if name == "top" else mats, PIPE_ENDS[name])
    # The top pipe's pink saddle bracket, bolted to the rock where the tile paints its pink fleck.
    fx, fy, fr = P["flanges"]["top_end"]
    pts, r = P["pipes"]["top"]
    c = catmull([(min(max(x, r + 0.1), 24 - r - 0.1), min(max(y, r + 0.1), 28 - r - 0.1)) for x, y in pts], step=0.32)
    i = int(np.argmin(np.hypot(c[:, 0] - fx, c[:, 1] - fy)))
    i = int(np.clip(i, 2, len(c) - 3))
    tx, ty = (c[i + 1] - c[i - 1]) / np.linalg.norm(c[i + 1] - c[i - 1])
    nx, ny = -ty, tx
    bx, by = c[i]
    hw, hl = fr * 1.0, 0.75
    plate = [(fx + sx * tx * hl + sy * nx * hw, fy + sx * ty * hl + sy * ny * hw) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    s.slab(plate, -0.02, 0.02, mats["pink"], chamfer_px=0.18, drop=0.01)
    zc = r * PX * (1 - PIPE_SINK)
    seg = [(c[k][0], c[k][1], zc) for k in range(i - 2, i + 3) if abs((c[k][0] - bx) * tx + (c[k][1] - by) * ty) <= hl * 0.9]
    if len(seg) >= 2:
        tube(s, seg, r * 1.38, mats["pink"], sides=10, smooth=False)
    s.bolts([(fx + nx * hw * 0.7, fy + ny * hw * 0.7), (fx - nx * hw * 0.7, fy - ny * hw * 0.7)], 0.02, r_px=0.22, height=0.012, mat=mats["bolt"])

    # The island's rock round it (plain, unbaked), cut under the bores and the socket (its recessed
    # cap is below the rock's top), dark under the parts.
    H, W = s.H, s.W
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    cut = np.zeros((H, W), bool)
    for name, ring in rings.items():
        th = np.arctan2(yy - ring.cy, xx - ring.cx)
        rr = np.vectorize(lambda t: radial(ring.radii, t))(th)
        cut |= np.hypot(xx - ring.cx, yy - ring.cy) <= rr - BAND_W[name] * 0.55
    s.rock(exclude=lb.erode(mask, 1) & ~cut, cut=cut)

    objects = s.objects()
    for sc in (1, 2):
        vis = visible_top(s, objects, sc)
        ref = np.kron(mask, np.ones((sc, sc), bool))
        print(f"visible top view {sc}x: IoU {float((vis & ref).sum()) / max(1, (vis | ref).sum()):.3f} "
              f"(model only {(vis & ~ref).sum() / sc ** 2:.0f} px, art only {(ref & ~vis).sum() / sc ** 2:.0f} px)")
    s.finish(objects, mask, bake=bake, preview=preview, ao=(0.02, 0.12))


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
