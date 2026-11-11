"""The burnt-out wreck on TYRIAN's ground (map 1-9, layer 0; tiles 340-342 / 350-352, 3x2; the
variant wreck-cut is the copy the map's right edge cuts): what is left where a craft came down and
burned. A charcoal crater torn into the dirt; across its lower half a row of torn hull plates still
stands, leaning back (the art's grey leaves are their lit faces), between charred plates that have
sagged lower; over the upper right a field of broken structure (girder stubs, a pipe, torn plate
chunks); over the upper left a thinner spray of chunks; in the middle the dirt shows through the
soot (the art's own dirt pixels are holes in the model, so the tiles below show).

Every cell carries a ground enemy (the "rock outcrop", assembly-newshe-39): the wreck shows once it
is killed (D86 covered structure) and every top stays under ENEMY_MAX 0.38 (plates up to 0.35, the
crater floor 0.03, its torn lip 0.06, the charred heap under the plate row up to about 0.09).
keepTiles: the dirt tiles stay drawn; the model covers only the wreck's own dark outline.

Hard surface (D65, D141): the floor is one constrained-Delaunay surface over the art's outline
(holes where the art paints dirt), its facets lit as rubble, each facet in the palette index the art
paints under it (32 soot, 1 charred, 161 scorched dirt). The plates are planes tilted back over
the art's grey blobs, so their top view is the blob: 0.6 px thick, a chamfered front, a riveted
strap across the face, two frame ribs on the back. The debris are chamfered tilted chunks over the
art's grey specks, I-beams and a flanged pipe. AO/roughness bake only ("bake": "model"), no concept
projection, no outline shell (tile models draw no ink outline, D141).

Its export also writes the variant wreck-cut (the copy cut by the map's right edge, cols 12-13).
Run from the repo root:

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_wreck.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_wreck.py -- [--no-bake] [--preview <dir>]
"""

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils import geometry as mg  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


# --- Heights (units; layer 0: z = 0 the ground) --------------------------------------------------
EDGE = 0.012     # the torn outline, just above the dirt
LIP = 0.10       # the charred lip's crest (varies +-0.025 along the outline)
FLOOR = 0.03     # the crater floor
HEAP = 0.06      # extra height of the charred heap under the plate row (lower lobe)
BOTTOM = -0.04   # the floor's underside

# --- Palette (level palette 5; the art's per-region medians, see measure()) ----------------------
P_SOOT, P_CHAR, P_SCORCH = 32, 1, 161

# --- The standing plates: (name, blob selector, top z, lean) -------------------------------------
# Each is a grey blob of the art (its lit face), cut where two plates touch. Their base is the blob's
# south edge, their top edge its north edge.
PLATES = [
    # x0, x1, y0, y1 (pattern px box the blob is taken from), top z, material from the blob
    ("p_tall_l", (19, 25, 27, 36), 0.31),
    ("p_big_l", (27, 32, 30, 38), 0.29),
    ("p_big_r", (32, 39, 31, 43), 0.35),
    ("p_mid_r", (45, 51, 30, 39), 0.33),
    ("p_far_l", (8, 13, 28, 33), 0.20),
    ("p_far_r", (52, 57, 29, 33), 0.17),
]
# Charred plates (the art's larger '1' blobs in the lower lobe), lower and sagging.
CHARRED = [
    ("c_east", (55, 64, 31, 40), 0.20),
    ("c_mid", (41, 46, 33, 41), 0.19),
    ("c_west", (12, 20, 36, 44), 0.15),
    ("c_low", (27, 33, 36, 43), 0.13),
    ("c_se", (52, 57, 36, 41), 0.12),
    ("c_s", (40, 47, 42, 47), 0.09),
]


# --- Pixel helpers -------------------------------------------------------------------------------

def wreck_mask(g):
    """The wreck's own outline: soot (32), charred (1), grey debris (2-15) and scorched dirt
    (160-163), 1 px gaps closed, specks dropped, small dirt specks inside filled. Bigger dirt patches
    stay holes (the art paints dirt there)."""
    dark = (g == 32) | (g == 80) | ((g >= 0) & (g < 16)) | ((g >= 160) & (g < 164))
    fp = lb.close(dark, 1)
    fp = lb.drop_small(lb.open_(fp, 1), 40)
    holes = ~fp
    fp |= holes & ~lb.drop_small(holes, 16)
    return fp


def blur(mask, sigma):
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    f = np.pad(mask.astype(float), r + 2)
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, f)
    f = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, f)
    return f, r + 2


def contours(field, off, level=0.5):
    """Every closed iso-line of `field` (marching squares on pixel centres) as (px, py) loops."""
    h, w = field.shape
    pts, nxt = {}, {}

    def ept(a, b):
        (ya, xa), (yb, xb) = a, b
        fa, fb = field[ya, xa], field[yb, xb]
        t = (level - fa) / (fb - fa)
        return (xa + (xb - xa) * t + 0.5 - off, ya + (yb - ya) * t + 0.5 - off)

    for y in range(h - 1):
        for x in range(w - 1):
            c = [(y, x), (y, x + 1), (y + 1, x + 1), (y + 1, x)]
            ins = [field[p] >= level for p in c]
            if all(ins) or not any(ins):
                continue
            for i in range(4):
                if ins[i] != ins[(i + 1) % 4]:
                    k = tuple(sorted((c[i], c[(i + 1) % 4])))
                    pts[k] = ept(c[i], c[(i + 1) % 4])
            for i in [i for i in range(4) if ins[i] and not ins[(i + 1) % 4]]:
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
        if len(loop) >= 6:
            loops.append(np.array(loop))
    return loops


def resample(loop, step):
    p = np.vstack([loop, loop[:1]])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    n = max(6, int(d[-1] / step))
    t = np.linspace(0, d[-1], n, endpoint=False)
    return np.c_[np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])]


def inside_any(loops, pts):
    """Even-odd test of points (N, 2) against all loops (holes included)."""
    pts = np.asarray(pts, float)
    res = np.zeros(len(pts), bool)
    for lp in loops:
        x, y = lp[:, 0], lp[:, 1]
        x2, y2 = np.roll(x, -1), np.roll(y, -1)
        px, py = pts[:, 0:1], pts[:, 1:2]
        cond = ((y > py) != (y2 > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (x2 - x) * (py - y) / np.where(y2 == y, 1e-9, y2 - y) + x
        res ^= (np.count_nonzero(cond & (px < xi), axis=1) % 2).astype(bool)
    return res


def dist_to(loops, pts):
    allp = np.vstack(loops)
    pts = np.asarray(pts, float)
    out = np.empty(len(pts))
    for i in range(0, len(pts), 512):
        d = np.hypot(pts[i:i + 512, None, 0] - allp[None, :, 0], pts[i:i + 512, None, 1] - allp[None, :, 1])
        out[i:i + 512] = d.min(axis=1)
    return out


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def trimmed_median(vals, lum):
    """The region's palette index: the median by brightness, the darkest and brightest 15 % dropped
    (shading and sheen)."""
    vals = sorted((int(v) for v in vals if v >= 0), key=lambda v: lum[v])
    if not vals:
        return None
    k = int(len(vals) * 0.15)
    core = vals[k:len(vals) - k] or vals
    return core[len(core) // 2]


# --- The floor -----------------------------------------------------------------------------------

class Floor:
    def __init__(self, s, mask, rng):
        self.s, self.rng = s, rng
        f, off = blur(mask, 0.6)
        loops = [resample(lp, 0.55) for lp in contours(f, off)]
        # A light tear along the outline: small sideways teeth.
        torn = []
        for lp in loops:
            n = len(lp)
            t = np.roll(lp, -1, axis=0) - np.roll(lp, 1, axis=0)
            t /= np.maximum(np.hypot(*t.T), 1e-6)[:, None]
            nrm = np.c_[-t[:, 1], t[:, 0]]
            a = np.array([rng.uniform(-0.18, 0.18) for _ in range(n)])
            torn.append(lp + nrm * a[:, None])
        self.loops = torn
        self.mask = mask
        # Lower lobe weight (the charred heap under the plate row): rows 28-46.
        yy, xx = np.mgrid[0:s.H, 0:s.W] + 0.5
        self.heap = (smoothstep(25.0, 31.0, yy) * (1 - smoothstep(42.0, 48.0, yy)))
        self.noise = lt.blur(np.array([[rng.uniform(-1, 1) for _ in range(s.W)] for _ in range(s.H)]), 1.2)
        self.noise2 = lt.blur(np.array([[rng.uniform(-1, 1) for _ in range(s.W)] for _ in range(s.H)]), 2.5)

    def z(self, pts, d=None):
        pts = np.asarray(pts, float)
        if d is None:
            d = dist_to(self.loops, pts)
        ix = np.clip(pts[:, 0].astype(int), 0, self.s.W - 1)
        iy = np.clip(pts[:, 1].astype(int), 0, self.s.H - 1)
        crest = LIP + 0.025 * self.noise2[iy, ix] / max(1e-6, np.abs(self.noise2).max())
        lip = EDGE + (crest - EDGE) * smoothstep(0.0, 1.4, d)
        inner = 1 - smoothstep(1.5, 3.4, d)  # 1 on the lip, 0 inside
        base = FLOOR + HEAP * self.heap[iy, ix] * smoothstep(2.0, 6.0, d) + 0.012 * self.noise[iy, ix] * smoothstep(1.5, 3.0, d)
        z = np.where(d < 1.4, lip, inner * crest + (1 - inner) * base)
        return np.maximum(z, EDGE)

    def build(self, cls):
        """The top surface (CDT over the outline loops and an interior grid) and a closed underside.
        `cls` (H, W): the palette index per px for the facets."""
        s, rng = self.s, self.rng
        bpts = np.vstack(self.loops)
        edges, k = [], 0
        for lp in self.loops:
            n = len(lp)
            edges += [(k + i, k + (i + 1) % n) for i in range(n)]
            k += n
        # Interior points: a jittered grid, denser near the outline (the lip).
        grid = []
        for y in np.arange(0.4, s.H, 0.95):
            for x in np.arange(0.4 + (0.47 if int(y / 0.95) % 2 else 0), s.W, 0.95):
                grid.append((x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2)))
        grid = np.array(grid)
        grid = grid[inside_any(self.loops, grid)]
        dg = dist_to(self.loops, grid)
        keep = (dg > 0.4) & ((dg < 3.6) | (np.arange(len(grid)) % 2 == 0))
        grid = grid[keep]
        allp = np.vstack([bpts, grid])
        vs, es, fs, ov, oe, of = mg.delaunay_2d_cdt([Vector(p) for p in allp], edges, [], 0, 1e-4)
        vs = np.array([tuple(v) for v in vs])
        tris = [f for f in fs if len(f) == 3]
        cent = np.array([vs[list(f)].mean(axis=0) for f in tris])
        ins = inside_any(self.loops, cent)
        tris = [f for f, i in zip(tris, ins) if i]
        zs = self.z(vs)
        nb = len(bpts)
        top_of = {}  # input boundary index -> output vertex
        for oi, orig in enumerate(ov):
            for i in orig:
                if i < nb:
                    top_of[i] = oi
        bm = bmesh.new()
        top = [bm.verts.new((s.x(p[0]), s.y(p[1]), z)) for p, z in zip(vs, zs)]
        for f in tris:
            c = vs[list(f)].mean(axis=0)
            idx = cls[min(s.H - 1, int(c[1])), min(s.W - 1, int(c[0]))]
            try:
                bm.faces.new([top[i] for i in f]).material_index = s.m(int(idx), roughness=0.95)
            except ValueError:
                continue
        # The underside: the outline alone, triangulated flat at BOTTOM; walls down the outline.
        bv, _, bf, bov, _, _ = mg.delaunay_2d_cdt([Vector(p) for p in bpts], edges, [], 0, 1e-4)
        bv = np.array([tuple(v) for v in bv])
        btris = [f for f in bf if len(f) == 3]
        bcent = np.array([bv[list(f)].mean(axis=0) for f in btris])
        btris = [f for f, i in zip(btris, inside_any(self.loops, bcent)) if i]
        bot = [bm.verts.new((s.x(p[0]), s.y(p[1]), BOTTOM)) for p in bv]
        bot_of = {}
        for oi, orig in enumerate(bov):
            for i in orig:
                bot_of[i] = oi
        under = s.m(P_SOOT, roughness=0.95)
        for f in btris:
            try:
                bm.faces.new([bot[i] for i in reversed(f)]).material_index = under
            except ValueError:
                pass
        side = s.m(P_CHAR, roughness=0.95)
        for a, b in edges:
            ta, tb_, ba, bb = top[top_of[a]], top[top_of[b]], bot[bot_of[a]], bot[bot_of[b]]
            if len({ta, tb_}) < 2 or len({ba, bb}) < 2:
                continue
            try:
                bm.faces.new((ta, tb_, bb, ba)).material_index = side
            except ValueError:
                pass
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm)
        print(f"floor: {len(tris)} top triangles, {len(self.loops)} loops")


# --- Leaning parts: a surface rising from a base line, curled or flat ----------------------------

class Lean:
    """A surface over the ground plan: from the base line through `base` (px) it rises along the
    unit direction `d` (px, screen: (0, -1) is north) over `L` px of plan, from zb to zt, along the
    profile f(t) = 1 - (1 - t)^curl (curl 1: a flat plane; > 1: steep at the base, curling back
    flatter toward the top, as a hull plate peeled back). P(px, py, h): the point on it over (px, py),
    lifted h px along its normal there."""

    def __init__(self, s, base, d, L, zb, zt, curl=1.0):
        self.s, self.bx, self.by = s, base[0], base[1]
        n = math.hypot(*d)
        self.dx, self.dy = d[0] / n, d[1] / n
        self.L, self.zb, self.zt, self.curl = max(0.5, L), zb, zt, curl

    def t(self, px, py):
        return min(1.0, max(0.0, ((px - self.bx) * self.dx + (py - self.by) * self.dy) / self.L))

    def P(self, px, py, h=0.0):
        t = self.t(px, py)
        f = 1 - (1 - t) ** self.curl
        df = self.curl * (1 - t) ** (self.curl - 1) if self.curl != 1 else 1.0
        z = self.zb + (self.zt - self.zb) * f
        slope = (self.zt - self.zb) * df / (self.L * lt.PX)  # units of z per unit of plan
        gx, gy = slope * self.dx, -slope * self.dy           # world gradient
        nrm = Vector((-gx, -gy, 1.0)).normalized()
        return Vector((self.s.x(px), self.s.y(py), z)) + nrm * (h * lt.PX)


def densify(poly, step):
    out = []
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        k = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / step)))
        out += [(x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k) for j in range(k)]
    return out


def surf_slab(bm, lean, poly, h0, h1, mat, chamfer=0.0, drop=0.0, mat_side=None, step=0.6, spacing=0.9):
    """A closed slab over the polygon `poly` (px, its plan) between offsets h0 < h1 px along the
    surface's normal: the h1 face triangulated (constrained Delaunay, interior points every
    `spacing` px) so it follows a curled surface, its rim `chamfer` px wide dropped `drop` px."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    side = mat if mat_side is None else mat_side
    outer = densify(pts, step)
    loops = [outer]
    if chamfer:
        inner = ls.inset(pts, chamfer)
        if abs(ls.area(inner)) > 0.3 * abs(ls.area(pts)) and ls.area(inner) > 0:
            loops.append(densify(inner, step))
    allp = [p for lp in loops for p in lp]
    no = len(outer)
    edges, k = [], 0
    for lp in loops:
        n = len(lp)
        edges += [(k + i, k + (i + 1) % n) for i in range(n)]
        k += n
    ol = np.array(outer)
    xs, ys = ol[:, 0], ol[:, 1]
    grid = [(x, y) for y in np.arange(ys.min() + 0.45, ys.max(), spacing) for x in np.arange(xs.min() + 0.45, xs.max(), spacing)]
    if grid:
        grid = np.array(grid)
        lp_all = [np.array(lp) for lp in loops]
        ok = inside_any([ol], grid) & (dist_to(lp_all, grid) > 0.35)
        allp += [tuple(p) for p in grid[ok]]
    vs, es, fs, ov, oe, of = mg.delaunay_2d_cdt([Vector(p) for p in allp], edges, [], 0, 1e-5)
    vs2 = np.array([tuple(v) for v in vs])
    tris = [f for f in fs if len(f) == 3]
    if not tris:
        return
    cent = np.array([vs2[list(f)].mean(axis=0) for f in tris])
    tris = [f for f, i in zip(tris, inside_any([ol], cent)) if i]
    is_outer = [any(o < no for o in orig) for orig in ov]
    top = [bm.verts.new(lean.P(p[0], p[1], h1 - (drop if (chamfer and is_outer[i] and len(loops) > 1) else 0.0)))
           for i, p in enumerate(vs2)]
    bot = [bm.verts.new(lean.P(p[0], p[1], h0)) for p in vs2]
    ecount = {}
    for f in tris:
        try:
            bm.faces.new([top[i] for i in f]).material_index = mat
            bm.faces.new([bot[i] for i in reversed(f)]).material_index = side
        except ValueError:
            continue
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            key = (min(a, b), max(a, b))
            ecount[key] = ecount.get(key, 0) + 1
    for (a, b), c in ecount.items():
        if c == 1:
            bm.faces.new((top[a], top[b], bot[b], bot[a])).material_index = side


def row_span(poly, py):
    """The widest x-interval of the polygon on row py."""
    xs = []
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > py) != (y1 > py):
            xs.append(x0 + (x1 - x0) * (py - y0) / (y1 - y0))
    xs.sort()
    best = None
    for a, b in zip(xs[0::2], xs[1::2]):
        if best is None or b - a > best[1] - best[0]:
            best = (a, b)
    return best


def col_span(poly, px):
    return row_span([(y, x) for x, y in poly], px)


def blob_poly(s, blob, tol=0.45):
    polys = s.outlines(blob, tol=tol, min_px=2)
    if not polys:
        return None
    return [(float(x), float(y)) for x, y in max(polys, key=lambda p: abs(ls.area(p)))]


def torn_edge(poly, rng, keep, amp=0.45, tooth=0.7):
    """Tear the polygon's edges where keep(x, y) holds: each edge split into teeth ~`tooth` px long,
    their points pushed in and out by up to `amp` px (inward more than outward, so the plan stays
    inside the art's blob)."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    out = []
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        L = math.hypot(x1 - x0, y1 - y0)
        k = max(1, int(round(L / tooth)))
        nx, ny = (y1 - y0) / max(L, 1e-6), -(x1 - x0) / max(L, 1e-6)  # outward-ish for CCW in y-down
        for j in range(k):
            x, y = x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k
            if j and keep(x, y):
                a = rng.uniform(-amp, amp * 0.35) if j % 2 else rng.uniform(-amp * 0.3, amp * 0.25)
                x, y = x + nx * a, y + ny * a
            out.append((x, y))
    return out


def standing_plate(s, rng, poly, zb, zt, mat, thick=0.6, strap=True, ribs=True, rivet_mat=None, curl=1.9, plan=None):
    """A torn hull plate peeled up and back over `poly` (its plan, px): its base on the polygon's
    south edge (zb), steep there, curling back to its torn top edge on the north edge (zt). Front
    chamfered; a riveted strap across the face and a rivet row along the base; frame ribs behind."""
    ys = [p[1] for p in poly]
    xs = [p[0] for p in poly]
    yb, yt = max(ys), min(ys)
    lean = Lean(s, ((min(xs) + max(xs)) / 2, yb), (0, -1), yb - yt, zb, zt, curl=curl)
    bm = bmesh.new()
    surf_slab(bm, lean, poly, -thick, 0.0, mat, chamfer=0.3, drop=0.14)
    plan = poly if plan is None else plan
    inner = ls.inset(plan if ls.area(plan) > 0 else list(reversed(plan)), 0.9)
    rm = mat if rivet_mat is None else rivet_mat
    if strap and yb - yt > 3.5:
        sy = yb - (yb - yt) * 0.30
        span = row_span(inner, sy)
        if span and span[1] - span[0] > 1.6:
            a, b = span
            surf_slab(bm, lean, [(a, sy - 0.5), (b, sy - 0.5), (b, sy + 0.5), (a, sy + 0.5)], -0.05, 0.24, mat, chamfer=0.15, drop=0.08)
            nr = max(2, int((b - a) / 1.4))
            for i in range(nr):
                rx = a + 0.5 + (b - a - 1.0) * i / max(1, nr - 1)
                surf_slab(bm, lean, s.ngon(rx, sy, 0.24, sides=6), 0.15, 0.38, rm)
        by = yb - 0.9
        span = row_span(inner, by)
        if span and span[1] - span[0] > 1.5:
            a, b = span
            nr = max(2, int((b - a) / 1.4))
            for i in range(nr):
                rx = a + 0.4 + (b - a - 0.8) * i / max(1, nr - 1)
                surf_slab(bm, lean, s.ngon(rx, by, 0.22, sides=6), -0.05, 0.2, rm)
    if ribs and yb - yt > 3.0:
        x0, x1 = min(xs), max(xs)
        for fx in ((0.28, 0.72) if x1 - x0 > 3.5 else (0.5,)):
            rx = x0 + (x1 - x0) * fx
            span = col_span(inner, rx)
            if span and span[1] - span[0] > 1.5:
                a, b = span
                surf_slab(bm, lean, [(rx - 0.3, a + 0.2), (rx + 0.3, a + 0.2), (rx + 0.3, b + 0.6), (rx - 0.3, b + 0.6)],
                          -thick - 0.8, -thick + 0.02, s.m(P_CHAR, metallic=0.3, roughness=0.7))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)
    return lean


def shard(s, rng, poly, zf, zt, mat, thick=0.45):
    """A torn sheet fragment over `poly` (plan px) propped up on one edge: from the floor (zf) on the
    side facing a random direction, rising to zt on the far side."""
    p = np.array(poly)
    c = p.mean(axis=0)
    a = rng.uniform(0, 2 * math.pi)
    d = (math.cos(a), math.sin(a))
    proj = (p - c) @ np.array(d)
    base = c + np.array(d) * proj.min()
    L = max(0.8, proj.max() - proj.min())
    lean = Lean(s, tuple(base), d, L, zf, zt, curl=1.0)
    bm = bmesh.new()
    surf_slab(bm, lean, poly, -thick, 0.0, mat, chamfer=0.2, drop=0.1, spacing=1.2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def chunk(s, rng, poly, z0, ztop, mat, tilt=0.02):
    """A charred lump: a chamfered prism over `poly` (px) with a tilted top."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    a = rng.uniform(0, 2 * math.pi)
    gx, gy = tilt * math.cos(a), tilt * math.sin(a)
    bm = bmesh.new()
    s._prism(bm, poly, lambda x, y: max(z0 + 0.012, ztop + gx * (x - cx) + gy * (y - cy)), z0, mat, chamfer=0.25, drop=0.014)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def frame_along(s, p0, p1):
    """An orthonormal frame for a part from p0 to p1 (Vectors, world): u along, v across (level), w."""
    u = (p1 - p0).normalized()
    v = Vector((0, 0, 1)).cross(u)
    if v.length < 1e-6:
        v = Vector((1, 0, 0))
    v.normalize()
    w = u.cross(v)
    return u, v, w


def extrude(s, p0, p1, profile, mat, mats=None):
    """A prism along p0 -> p1 (world) with the closed `profile` [(v, w) px] as its section."""
    u, v, w = frame_along(s, p0, p1)
    bm = bmesh.new()
    e0 = [bm.verts.new(p0 + v * (a * lt.PX) + w * (b * lt.PX)) for a, b in profile]
    e1 = [bm.verts.new(p1 + v * (a * lt.PX) + w * (b * lt.PX)) for a, b in profile]
    n = len(profile)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((e0[i], e0[j], e1[j], e1[i])).material_index = mats[i] if mats else mat
    bm.faces.new(e0).material_index = mat
    bm.faces.new(list(reversed(e1))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def ibeam(s, p0, p1, mat, wf=1.2, h=1.0, tf=0.25, tw=0.3):
    """An I-beam lying on its flange, section wf x h px."""
    a, b, c = wf / 2, tw / 2, h / 2
    prof = [(-a, -c), (a, -c), (a, -c + tf), (b, -c + tf), (b, c - tf), (a, c - tf), (a, c), (-a, c), (-a, c - tf),
            (-b, c - tf), (-b, -c + tf), (-a, -c + tf)]
    extrude(s, p0, p1, prof, mat)


def tube(s, p0, p1, r, mat, sides=10, flange=None, flange_mat=None):
    """A pipe from p0 to p1 (world), radius r px, closed; `flange` (r px, length px) at p0."""
    u, v, w = frame_along(s, p0, p1)
    L = (p1 - p0).length / lt.PX
    stations = [(0.0, r), (L, r)]
    if flange:
        fr, fl = flange
        stations = [(0.0, fr), (fl, fr), (fl, r), (L, r)]
    bm = bmesh.new()
    rings = []
    for t, rr in stations:
        ring = []
        for i in range(sides):
            ang = 2 * math.pi * i / sides
            ring.append(bm.verts.new(p0 + u * (t * lt.PX) + v * (rr * math.cos(ang) * lt.PX) + w * (rr * math.sin(ang) * lt.PX)))
        rings.append(ring)
    for k, (ra, rb) in enumerate(zip(rings, rings[1:])):
        mi = flange_mat if (flange and k < 2 and flange_mat is not None) else mat
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((ra[i], ra[j], rb[j], rb[i])).material_index = mi
    bm.faces.new(rings[0]).material_index = flange_mat if (flange and flange_mat is not None) else mat
    bm.faces.new(list(reversed(rings[-1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = len(f.verts) == 4
    s._merge(bm, smooth=False)


# --- Build ---------------------------------------------------------------------------------------

def box_blob(mask, box):
    x0, x1, y0, y1 = box
    out = np.zeros_like(mask)
    out[y0:y1, x0:x1] = mask[y0:y1, x0:x1]
    return out


def build(bake=True, preview=None):
    lb.clear_scene()
    s = tb.Structure("wreck")
    g = s.grid
    lum = s.ts.lum
    rng = random.Random("tyrbld-wreck-A")
    mask = wreck_mask(g)
    s.set_footprint(mask)
    grey = (g >= 2) & (g < 16)
    char = g == 1

    # Facet colours: the art's index per px, greys replaced by their surroundings (debris parts
    # cover them), dirt specks inside the outline by soot.
    cls = np.where((g >= 160) & (g < 164), P_SCORCH, np.where(char, P_CHAR, P_SOOT))
    floor = Floor(s, mask, rng)
    floor.build(cls)

    def mat_of(blob, **kw):
        return s.m(trimmed_median(g[blob], lum), **kw)

    metal = dict(metallic=0.45, roughness=0.55)
    taken = np.zeros_like(mask)
    regions = {}
    # Standing plates.
    for name, box, zt in PLATES:
        blob = lb.close(box_blob(grey, box), 1)
        blob = lb.drop_small(blob, 4)
        clean = blob_poly(s, blob, tol=0.8)
        ys = [p[1] for p in clean]
        yt, yb = min(ys), max(ys)
        poly = torn_edge(clean, rng, lambda x, y, yt=yt, yb=yb: y - yt < (yb - yt) * 0.55, amp=0.6, tooth=0.8)
        cx = sum(p[0] for p in poly) / len(poly)
        zb = float(floor.z([(cx, max(ys) - 0.3)])[0]) - 0.03
        idx = trimmed_median(g[blob], lum)
        standing_plate(s, rng, poly, zb, zt, s.m(idx, **metal), rivet_mat=s.m(min(idx + 1, 9), **metal), plan=clean)
        taken |= lb.dilate(blob, 1)
        regions[name] = (blob, idx)
    # Charred plates: the art's '1' blobs, sagging lower.
    for name, box, zt in CHARRED:
        blob = lb.close(box_blob(char, box), 1) & ~taken
        blob = lb.drop_small(blob, 6)
        if not blob.any():
            continue
        poly = blob_poly(s, blob, tol=0.8)
        ys = [p[1] for p in poly]
        yt, yb = min(ys), max(ys)
        poly = torn_edge(poly, rng, lambda x, y, yt=yt, yb=yb: y - yt < (yb - yt) * 0.6, amp=0.45)
        cx = sum(p[0] for p in poly) / len(poly)
        zb = float(floor.z([(cx, max(ys) - 0.3)])[0]) - 0.03
        standing_plate(s, rng, poly, zb, zt, s.m(P_CHAR, metallic=0.2, roughness=0.8), thick=0.5, strap=False, ribs=True, curl=1.4)
        taken |= blob
        regions[name] = (blob, P_CHAR)

    # The upper right's broken structure.
    # A charred girder lying E-W along the black bar of rows 9-10, its west end lifted.
    p0 = Vector((s.x(43.6), s.y(9.9), FLOOR + 0.04))
    p1 = Vector((s.x(50.2), s.y(9.6), FLOOR + 0.02))
    ibeam(s, p0, p1, s.m(P_SOOT, metallic=0.3, roughness=0.7), wf=1.6, h=0.9)
    taken |= s.box_mask(43, 8.5, 51, 11)
    # The flanged pipe along row 13-14 (the art's '45555'): bright grey, lying E-W.
    pb = lb.close(box_blob(grey, (44, 51, 12, 16)), 1)
    idx = trimmed_median(g[pb], lum)
    r = 1.1
    tube(s, Vector((s.x(44.6), s.y(13.6), FLOOR + r * lt.PX + 0.004)), Vector((s.x(50.6), s.y(13.3), FLOOR + r * lt.PX - 0.004)), r,
         s.m(idx, **metal), flange=(1.45, 0.6), flange_mat=s.m(max(3, idx - 1), **metal))
    taken |= lb.dilate(pb, 1)
    regions["pipe"] = (pb, idx)
    # A bent I-beam stub across the field (rows 19-24, the art's diagonal of grey specks).
    for (ax, ay, az), (bx, by, bz) in (((50.0, 24.0, 0.04), (53.5, 20.6, 0.10)), ((39.6, 21.6, 0.035), (41.4, 18.6, 0.09))):
        ibeam(s, Vector((s.x(ax), s.y(ay), FLOOR + az)), Vector((s.x(bx), s.y(by), FLOOR + bz)), s.m(4, **metal), wf=1.1, h=0.8)
    # Chunks over the art's other grey specks (upper half and leftovers).
    rest = grey & ~taken & mask
    nchunks = 0
    for ys_, xs_ in lt.components(lb.close(rest, 1) & mask):
        if len(ys_) < 2:
            continue
        blob = np.zeros_like(mask)
        blob[ys_, xs_] = True
        poly = blob_poly(s, blob, tol=0.7)
        if poly is None or abs(ls.area(poly)) < 1.2:
            # A tiny speck: a small hex chip.
            cx, cy = xs_.mean() + 0.5, ys_.mean() + 0.5
            poly = s.ngon(cx, cy, 0.9, sides=5, angle=rng.uniform(0, 3))
        cy = ys_.mean()
        zf = float(floor.z([(xs_.mean() + 0.5, cy + 0.5)])[0])
        hgt = 0.04 + min(0.08, 0.008 * len(ys_)) + rng.uniform(0, 0.03)
        idx = trimmed_median(g[blob], lum)
        poly = torn_edge(poly, rng, lambda x, y: True, amp=0.3, tooth=0.6)
        shard(s, rng, poly, zf - 0.015, zf + hgt, s.m(idx, **metal))
        regions[f"chunk{nchunks}"] = (blob, idx)
        nchunks += 1
    # Low charred lumps scattered over the debris field and the upper left (the art's '1' specks
    # there), so the field reads as rubble from the side.
    lumps = char & ~taken & mask & (np.mgrid[0:s.H, 0:s.W][0] < 30)
    for ys_, xs_ in lt.components(lumps):
        if len(ys_) < 2:
            continue
        cx, cy = xs_.mean() + 0.5, ys_.mean() + 0.5
        r = min(1.6, 0.5 + 0.25 * len(ys_))
        zf = float(floor.z([(cx, cy)])[0])
        poly = s.ngon(cx, cy, r, sides=rng.choice((5, 6, 7)), angle=rng.uniform(0, 3), ry_px=r * rng.uniform(0.6, 1.0))
        chunk(s, rng, poly, zf - 0.02, zf + rng.uniform(0.025, 0.05), s.m(P_CHAR, roughness=0.9), tilt=0.03)
    print(f"wreck: {nchunks} chunks")

    open_edges = sum(1 for e in s.parts.edges if len(e.link_faces) != 2)
    print(f"wreck: {open_edges} open / non-manifold edges")
    objects = s.objects()
    s.finish(objects, mask, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
