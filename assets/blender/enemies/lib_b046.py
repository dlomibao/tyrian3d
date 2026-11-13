"""Shared builder for batch b046 (merged item assembly-newsh-caret-269): the tongue, the eyeball and the lips: three organic sprites built as
faired flesh height fields over each sprite's inner mask.

1. TONGUE, assembly-newsh-caret-269 (newsh^ 267 over 269, 24 x 56 px): the NOSE DRIP (4.25) face's
   tongue. In the C it is drawn FIRST, under the face's pod, nose bridge (154) and nose (191/193):
   only 2-3 px slivers show either side of the bridge between the eyes and the alae (composite of
   the draw list at t300). So it stays a low slab, at most 2.4 px tall, and its later-drawn
   neighbours keep their own height (D181 coverHeight only lifts a draw over a TALLER earlier one).
   Fix round 1: it is also held 0.5 px under the surfaces of the face pieces drawn over it (the
   bridge 154, the nose 191/193 and the pod 121-f3 at its rest place), read from their glbs at build
   time (Tongue.cover_field): in game the tongue showed through the nose. Rebuild it after those
   batch-1 models change. Fix round 2: that ceiling is min filtered then Gaussian blurred, so the
   tongue slopes smoothly under the face (no stepped trenches), and the side bands the sprite paints
   dark (pal 68, the slivers showing beside the bridge) are pal 68. What it is: a broad tongue with a
   median furrow (column 11, pal 67 in the sprite: a real groove, painted at its floor), domed
   halves, rounding to the tip; its torn root (rows 2-11) is three broad flesh folds (pal 68) with
   three wet blood tears (pal 115) and a few soft crevices (the sprite's interior 1/64 pixels).
   The pale stripe right of the furrow and the light patch on the left bulge are sheen (rubric).
2. EYEBALL, newsh5-270 (24 x 28, 21 px orb): a glossy ball, sclera pal 61 (median; the white upper
   half is sheen), the iris (pal 57) low on the ball (the eye looks down the screen) under a
   faint corneal lift, a darker limbal ring (pal 53) and a pupil (pal 51). The glint is sheen.
   Opaque (no clear glass, D192). A true sphere (~9 px tall, rim angle ~86 deg) on the rim's mean radius, its smooth
   Fourier-lobed rim (Eye.RF, needed for the IoU) a faint radial warp of the lower wall; iris and pupil one
   faired convex corneal bell (fix round 2). Metallic 0 (organic); its own sealed outline shell,
   unsunk (a convex ball inks its silhouette).
3. LIPS, assembly-newsh-caret-196 (newsh^ 196 + 208 side by side, 48 x 28): puffy red lips, the
   upper (pal 69) with the cupid's bow from the sprite's silhouette and its central tubercle
   dipping into the parting line, the fuller lower lip (pal 71), and the mouth slit between them
   (the sprite's interior ink line, pal 16) as a real crease painted dark at its floor.

All flesh: metallic 0, satin roughness (the nose of batch e4-enemies-1 is metallic 0 / 0.42).
Height fields: Delaunay lattice inside the traced, smoothed inner-mask footprint (area matched),
rounded over the last px to the silhouette, flat closed underside. One sealed outline shell per
model (common.outline_shell islands="outer", D189), sunk under the top so ink is on the silhouette
only, split per piece for assemblies (D90/D118).

build-models.sh skips lib_ files. Each model script (assembly-newsh-caret-269.py = the tongue,
newsh5-270.py = the eyeball, assembly-newsh-caret-196.py = the lips) calls run(<key>) and exports only
its own models (public/models/enemies/<piece>.glb + src/render/spriteModels/<piece>.json). Review renders
and per-piece glbs are written only behind --review DIR / --game DIR (after a "--").
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry

WT = next(p for p in Path(__file__).resolve().parents if (p / "package.json").exists())
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import sprite_mask as S  # noqa: E402

ROOT = WT
PX = 1 / 12
NEG = -50.0


# ------------------------------------------------------------------------------------------------
# Small maths
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


def smax(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k / 4


def smin(a, b, k):
    return -smax(-a, -b, k)


def sstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ell_q(c, r, cen, rad, ang=0.0):
    dx, dy = c - cen[0], r - cen[1]
    u = dx * math.cos(ang) + dy * math.sin(ang)
    v = -dx * math.sin(ang) + dy * math.cos(ang)
    return (u / rad[0]) ** 2 + (v / rad[1]) ** 2


def ell_loop(cen, rad, ang=0.0, n=48):
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        u, v = rad[0] * math.cos(t), rad[1] * math.sin(t)
        out.append((cen[0] + u * math.cos(ang) - v * math.sin(ang), cen[1] + u * math.sin(ang) + v * math.cos(ang)))
    return out


# ------------------------------------------------------------------------------------------------
# Footprint (from the nose design of e4-enemies-1, numpy for the distance queries)
# ------------------------------------------------------------------------------------------------

def trace(mask):
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
    return [tuple(map(float, p)) for p in max(loops, key=len)]


def signed_area(poly):
    return 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))


def perimeter(poly):
    return sum(math.dist(a, b) for a, b in zip(poly, poly[1:] + poly[:1]))


def offset(poly, d):
    sgn = 1 if signed_area(poly) > 0 else -1
    out = []
    n = len(poly)
    for i, (x, y) in enumerate(poly):
        ax, ay = poly[i - 1]
        bx, by = poly[(i + 1) % n]
        tx, ty = bx - ax, by - ay
        ln = math.hypot(tx, ty) or 1
        nx, ny = ty / ln, -tx / ln
        out.append((x + sgn * nx * d, y + sgn * ny * d))
    return out


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


def gauss_smooth(poly, sigma):
    n = len(poly)
    step = perimeter(poly) / n
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


def footprint(inner, sigma, grow=0.0):
    poly = gauss_smooth(resample(trace(inner), 0.25), sigma)
    want = sum(map(sum, inner))
    for _ in range(3):
        poly = offset(poly, (want - abs(signed_area(poly))) / perimeter(poly))
        poly = resample(poly, 0.25)
    return offset(poly, grow) if grow else poly


class Poly:
    """A closed polygon with vectorised inside / distance queries."""

    def __init__(self, pts):
        self.pts = pts
        a = np.array(pts)
        self.a, self.b = a, np.roll(a, -1, axis=0)

    def dist(self, x, y):
        a, b = self.a, self.b
        d = b - a
        L = (d ** 2).sum(1)
        L[L == 0] = 1
        t = np.clip(((x - a[:, 0]) * d[:, 0] + (y - a[:, 1]) * d[:, 1]) / L, 0, 1)
        return float(np.sqrt((a[:, 0] + t * d[:, 0] - x) ** 2 + (a[:, 1] + t * d[:, 1] - y) ** 2).min())

    def inside(self, x, y):
        a, b = self.a, self.b
        cond = (a[:, 1] > y) != (b[:, 1] > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = (b[:, 0] - a[:, 0]) * (y - a[:, 1]) / (b[:, 1] - a[:, 1]) + a[:, 0]
        return bool((cond & (x < xi)).sum() % 2)


# ------------------------------------------------------------------------------------------------
# Sprites
# ------------------------------------------------------------------------------------------------

def composite(place, w, h):
    idx = [[-1] * w for _ in range(h)]
    colors = {}
    for name, c0, r0 in place:
        data = json.loads((ROOT / "reference" / "models" / name / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in data["colors"].items()})
        for r, row in enumerate(data["frames"][0]["pixels"]):
            for c, v in enumerate(int(t) for t in row.split()):
                if v >= 0:
                    idx[r0 + r][c0 + c] = v
    return idx, colors


def smooth_series(xs, ys, sigma):
    """Gaussian-smooth samples ys at positions xs (pixel stairs out of a profile)."""
    xs, ys = np.array(xs, float), np.array(ys, float)
    out = []
    for x in xs:
        w = np.exp(-0.5 * ((xs - x) / sigma) ** 2)
        out.append(float((w * ys).sum() / w.sum()))
    return out


def row_extents(mask):
    out = {}
    for r, line in enumerate(mask):
        cs = [c for c, v in enumerate(line) if v]
        if cs:
            out[r] = (min(cs), max(cs) + 1)
    return out


# ------------------------------------------------------------------------------------------------
# Model specs
# ------------------------------------------------------------------------------------------------

class Tongue:
    key = "tongue"
    name = "assembly-newsh-caret-269"
    tag = "nshc269a"
    W, H = 24, 56
    C0, R0 = 12, 28
    place = [("newsh-caret-267", 0, 0), ("newsh-caret-269", 0, 28)]
    BODY, FURROW, ROOT, BLOOD = 70, 67, 68, 115
    mats = {70: 0.36, 67: 0.42, 68: 0.40, 115: 0.28}
    sigma = 1.7  # a smooth rim: no mask stair-steps baked in as bumps (fix round 1)
    step = 0.5
    rim = 1.6
    rings = (0.1, 0.3, 0.6, 1.0, 1.45)
    TMAX = 2.4
    FC = 11.5  # furrow column (edge coords: centre of pixel column 11)
    # blood tears on the torn root: centre (c, r), radii, angle (rad)
    BLOODS = [((4.2, 10.1), (1.9, 1.5), 0.25), ((10.9, 9.0), (1.5, 2.7), -0.35), ((15.8, 7.2), (1.45, 1.75), 0.0)]
    # the root's main crevices (the sprite's interior near-black pixels): few and soft (fix round 1:
    # nine pits read as noise)
    CREV = [(11.5, 7.0), (7.2, 7.8), (17.5, 7.8), (18.8, 11.3)]
    # root lumps: centre, radii, height (px): three broad folds
    LUMPS = [((13.0, 5.4), (4.2, 2.8), 2.2), ((7.4, 9.0), (5.4, 3.2), 2.2), ((17.8, 9.4), (4.4, 3.0), 2.1)]
    # The face's pieces drawn over the tongue in the C (draw list, NOSE DRIP main=25 t180: all on the
    # top layer, same base, rigidly stacked): model, sprite top-left on screen. The tongue's own
    # top-left is (139, 39). It stays under their surfaces (the renderer's D181 lift only raises a
    # later draw over a TALLER earlier one, so a tongue taller than the nose there showed through it).
    COVER = [("newsh5-121-f3", 139, 45), ("newsh5-154", 138, 37), ("newsh5-191", 126, 65), ("newsh5-193", 150, 65)]
    TL = (139, 39)
    CLEAR = 0.5  # px kept under the covering surface

    def __init__(self, inner):
        ext = row_extents(inner)
        rows = sorted(ext)
        xs = [r + 0.5 for r in rows]
        self.xc = pchip(list(zip(xs, smooth_series(xs, [(ext[r][0] + ext[r][1]) / 2 for r in rows], 1.5))))
        self.hw = pchip(list(zip(xs, smooth_series(xs, [(ext[r][1] - ext[r][0]) / 2 for r in rows], 1.5))))
        # thickest (2.4 px) where only the bridge covers it; under the nose (rows 26+, whose base
        # between the alae and the columella is ~2.2 px) it thins so no red shows through
        self.T = pchip([(1.5, 2.1), (10, 2.3), (14, 2.4), (24, 2.35), (31, 1.9), (40, 1.6), (44, 1.2), (46.5, 0.8), (48.5, 0.5), (50, 0.4)])

    def root_line(self, c):
        """Row where the torn root gives way to the smooth tongue."""
        return 11.6 + 0.5 * math.sin(c * 0.9)

    def height(self, c, r, d):
        e = min(d / self.rim, 1.0)
        roundr = math.sqrt(max(0.0, 1 - (1 - e) ** 2))
        u = (c - self.xc(r)) / max(1.0, self.hw(r))
        # two domed halves either side of the furrow
        dome = 0.86 + 0.14 * (1 - min(1.0, u * u))
        z = self.T(r) * dome
        # median furrow (fades in under the root, out before the tip)
        f = sstep(11.0, 14.5, r) * (1 - sstep(43.0, 47.5, r))
        z -= 0.8 * f * math.exp(-((c - self.FC) / 0.95) ** 2)
        # torn root: lumps blended in, crevices, sunken blood
        wr = 1 - sstep(self.root_line(c) - 1.2, self.root_line(c) + 1.0, r)
        if wr > 0:
            lump = 1.2
            for cen, rad, hh in self.LUMPS:
                q = ell_q(c, r, cen, rad)
                if q < 1:
                    lump = smax(lump, hh * (1 - q) ** 0.6, 0.8)
            z = z * (1 - wr) + lump * wr
            for cx, cy in self.CREV:
                z -= 0.9 * wr * math.exp(-((c - cx) ** 2 + (r - cy) ** 2) / 0.55)
            for cen, rad, ang in self.BLOODS:
                q = ell_q(c, r, cen, rad, ang)
                if q < 1.3:
                    z -= 0.35 * (1 - sstep(0.6, 1.3, q))
        z = min(z, self.TMAX)
        z = max(0.35, z)
        cov = self.cover_at(c, r)
        if cov is not None:
            z = smin(z, cov, 0.35)
        return max(0.28, z) * roundr

    cov = None
    poly = None
    # Fix round 2: the clamp field is smoothed before use (a min filter of MINR px, then a Gaussian
    # of BLUR px): the tongue slopes under the face, no stepped trenches or mesa walls. OPEN is the
    # ceiling where nothing covers it (above TMAX: no clamp).
    MINR = 3.5
    BLUR = 2.0
    OPEN = 3.4
    EDGE = 1.15  # px: the dark edge band (pal 66-68 in the sprite: columns 0 and 20-22 of rows 12-34,
    # and round the tip, rows 43-49): the only tongue edges that show beside the face's pieces
    EDGE_R = ((12.6, 34.0), (42.5, 99.0))

    def in_band(self, r):
        return any(a < r < b for a, b in self.EDGE_R)

    def cover_dir(self):
        """Where the covering face models are read from: the repo's own public/models/enemies (the
        nose, bridge and pod of D195), so rebuild the tongue whenever those models change."""
        return ROOT / "public" / "models" / "enemies"

    def cover_field(self):
        """Heights (px) of the covering models' bodies over the tongue's grid (0.25 px), as placed by
        the draw list, read from their exported glbs by casting rays down; then smooth_cover."""
        from mathutils.bvhtree import BVHTree
        st = 0.25
        nc, nr = int(self.W / st) + 1, int(self.H / st) + 1
        field = np.full((nr, nc), np.inf)
        trees = []
        cdir = self.cover_dir()
        print("tongue cover models from", cdir)
        for name, sx, sy in self.COVER:
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(cdir / f"{name}.glb"))
            new = [o for o in bpy.data.objects if o not in before]
            off = Vector(((sx + 12 - (self.TL[0] + self.C0)) * PX, ((self.TL[1] + self.R0) - (sy + 14)) * PX, 0))
            for o in new:
                if o.parent is None:
                    o.location += off
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            for o in new:
                if o.type == "MESH" and "outline" not in o.name and not o.get("tyrian_outline"):
                    bm = bmesh.new()
                    bm.from_object(o, dg)
                    bm.transform(o.matrix_world)
                    trees.append(BVHTree.FromBMesh(bm))
                    bm.free()
            for o in new:
                me = o.data if o.type == "MESH" else None
                bpy.data.objects.remove(o, do_unlink=True)
                if me is not None and me.users == 0:
                    bpy.data.meshes.remove(me)
        for m in [m for m in bpy.data.materials if m.users == 0]:
            bpy.data.materials.remove(m)
        for j in range(nr):
            for i in range(nc):
                c, r = i * st, j * st
                o = Vector(((c - self.C0) * PX, (self.R0 - r) * PX, 5.0))
                best = -np.inf
                for t in trees:
                    hit = t.ray_cast(o, Vector((0, 0, -1)))
                    if hit[0] is not None:
                        best = max(best, hit[0].z / PX)
                if best > -np.inf:
                    field[j, i] = best
        self.cov_raw = field
        self.cov, self.cov_st = self.smooth_cover(field, st), st
        print("tongue cover: %d of %d grid points covered" % (np.isfinite(field).sum(), field.size))

    def smooth_cover(self, field, st):
        """The tongue's ceiling: CLEAR px under the covering surfaces (OPEN where uncovered), min
        filtered over MINR px (it also dips just beyond their edges: no red rim round the nose at the
        tilted camera), then Gaussian blurred over BLUR px, so it slopes smoothly with no steps. The
        min radius is wide enough that the blur stays under the hard ceiling (checked, printed)."""
        hard = np.where(np.isfinite(field), np.maximum(0.3, field - self.CLEAR), self.OPEN)
        hard = np.minimum(hard, self.OPEN)
        nr, nc = hard.shape
        rad = int(round(self.MINR / st))
        out = hard.copy()
        pad = np.pad(hard, rad, mode="edge")
        for dj in range(-rad, rad + 1):
            for di in range(-rad, rad + 1):
                if di * di + dj * dj <= rad * rad:
                    out = np.minimum(out, pad[rad + dj:rad + dj + nr, rad + di:rad + di + nc])
        sg = self.BLUR / st
        k = np.arange(-int(3 * sg) - 1, int(3 * sg) + 2)
        w = np.exp(-0.5 * (k / sg) ** 2)
        w /= w.sum()
        n = len(k) // 2
        p = np.pad(out, ((n, n), (0, 0)), mode="edge")
        out = sum(wi * p[i:i + nr] for i, wi in enumerate(w))
        p = np.pad(out, ((0, 0), (n, n)), mode="edge")
        out = sum(wi * p[:, i:i + nc] for i, wi in enumerate(w))
        fin = np.isfinite(field)
        viol = np.where(fin, out - hard, -np.inf)
        print("tongue ceiling: smoothed field exceeds the hard ceiling by at most %.3f px (at the covers' rims, "
              "where the hard ceiling is the 0.3 floor)" % viol.max())
        # never above the covering surface itself (a safety net: only a few rim points, < 0.2 px)
        out = np.where(fin, np.minimum(out, np.maximum(0.28, field - 0.1)), out)
        return out

    def cover_at(self, c, r):
        if self.cov is None:
            return None
        st = self.cov_st
        nr, nc = self.cov.shape
        i = min(max(c / st, 0.0), nc - 1.001)
        j = min(max(r / st, 0.0), nr - 1.001)
        i0, j0 = int(i), int(j)
        fi, fj = i - i0, j - j0
        g = self.cov
        return ((1 - fi) * (1 - fj) * g[j0, i0] + fi * (1 - fj) * g[j0, i0 + 1]
                + (1 - fi) * fj * g[j0 + 1, i0] + fi * fj * g[j0 + 1, i0 + 1])

    def paint(self, c, r):
        for cen, rad, ang in self.BLOODS:
            if ell_q(c, r, cen, rad, ang) < 1:
                return self.BLOOD
        if r < self.root_line(c):
            return self.ROOT
        if abs(c - self.FC) < 0.5 and 12.0 < r < 45.0:
            return self.FURROW
        if self.poly is not None and self.in_band(r) and self.poly.dist(c, r) < self.EDGE:
            return self.ROOT
        return self.BODY

    def loops(self):
        out = [(ell_loop(*b), True) for b in self.BLOODS]
        out.append(([(c / 4, self.root_line(c / 4)) for c in range(0, 97)], False))
        out.append(([(self.FC - 0.5, 12.0), (self.FC - 0.5, 45.0), (self.FC + 0.5, 45.0), (self.FC + 0.5, 12.0)], True))
        if self.poly is not None:
            # the dark edge bands' inner edges: runs of the inset ring inside the band rows (open)
            ring = resample(offset(self.poly.pts, -self.EDGE), 0.35)
            n = len(ring)
            k0 = next((k for k in range(n) if not self.in_band(ring[k][1])), 0)
            seg = []
            for k in range(1, n + 1):
                p = ring[(k0 + k) % n]
                if self.in_band(p[1]):
                    seg.append(p)
                else:
                    if len(seg) > 1:
                        out.append((seg, False))
                    seg = []
            if len(seg) > 1:
                out.append((seg, False))
        return out


class Eye:
    key = "eye"
    name = "newsh5-270"
    tag = "n5a270"
    W, H = 24, 28
    C0, R0 = 12, 14
    place = [("newsh5-270", 0, 0)]
    SCLERA, IRIS, LIMBUS, PUPIL = 61, 57, 53, 51
    mats = {61: 0.2, 57: 0.18, 53: 0.25, 51: 0.15}
    sigma = 1.2
    step = 0.45
    rim = 0.0
    rings = (0.03, 0.08, 0.16, 0.28, 0.45, 0.7, 1.0, 1.4)
    IRIS_C, IRIS_R = (13.25, 15.6), (6.1, 5.3)
    PUP_C, PUP_R = (13.55, 16.05), (2.35, 2.05)
    LIMB = 0.9  # limbal ring: outer fraction of the iris radius
    BULGE = 0.3  # cornea, px: a faint lift, so the ball's outline stays round from the side

    # The ball's rim (edge coords): centre and r(theta) = a0 + sum_n (a_n cos n.theta + b_n sin n.theta),
    # theta = atan2(row - cy, col - cx). Fitted (least squares to the inner mask's radius per angle,
    # then a climb that shrinks the lobes while the rule-grid IoU stays >= 0.955 with the rim
    # jittered 0.04 px) to n <= 8: a smooth, faintly lobed circle (under 1 px peak to peak about
    # 10.17 px; no per-pixel notches). A plain disc cannot pass the IoU (best ellipse ~0.937), so the
    # lobes stay, but only as a faint warp of the lower wall. Fix round 3: re-climbed to minimise
    # sum n^2 |c_n|^2 at rule-grid IoU >= 0.9555 (rim jittered +-0.04 px): n=7 gone, n=2..6 halved;
    # n=8 (0.24 px, the sprite's pixel-circle octagon) is what the IoU needs.
    RC = (12.388, 12.3816)
    RF = (10.1705, 0.0385, -0.0021, 0.0595, 0.0009, -0.0234, 0.0061, 0.0211, -0.0479, -0.1796, 0.0046,
          -0.0535, 0.0714, 0.0008, 0.009, -0.2419, -0.0001)
    sink = False  # a convex ball: its own sealed shell, unsunk, inks the silhouette only

    def __init__(self, inner):
        self.cen = self.RC
        # Fix round 3: the dome is a TRUE sphere on the rim's MEAN radius (a0), its centre ZC px under
        # the base (rim angle ~86 deg). The rim's Fourier lobes (+-0.55 px about a0) are a pure radial
        # warp of that sphere that fades in over the outer FADE of the radius (the bottom ~4 px of
        # the near-vertical wall): no shelf, no flaring foot, the wall never leans out. Footprint
        # (and IoU) unchanged.
        self.RM = self.RF[0]
        self.RS = math.sqrt(self.RM ** 2 + self.ZC ** 2)

    ZC = 0.6  # sphere centre under the base, px
    FADE = 0.12  # lobe warp fades in over the outer 12% of the radius

    def radius_t(self, t):
        f = self.RF
        return f[0] + sum(f[2 * n - 1] * math.cos(n * t) + f[2 * n] * math.sin(n * t) for n in range(1, 9))

    def radius(self, c, r):
        return self.radius_t(math.atan2(r - self.RC[1], c - self.RC[0]))

    def footprint(self, inner):
        n = 720
        out = []
        for k in range(n):
            t = -2 * math.pi * k / n
            rr = self.radius_t(t)
            out.append((self.RC[0] + rr * math.cos(t), self.RC[1] + rr * math.sin(t)))
        return out

    def ball(self, c, r):
        """Height (px) of the ball: the mean-radius sphere, radially warped onto the lobed rim."""
        rho = math.hypot(c - self.RC[0], r - self.RC[1])
        rf = self.radius(c, r)
        b = sstep(1.0 - self.FADE, 1.0, rho / rf)
        rw = rho * (1.0 + (self.RM / rf - 1.0) * b)  # = RM on the rim, = rho inside the fade
        return max(0.0, math.sqrt(max(0.0, self.RS ** 2 - rw * rw)) - self.ZC)

    def height(self, c, r, d):
        z = self.ball(c, r) if d > 0 else 0.0
        # cornea: one faired convex lift over iris and pupil (a smooth bell in the radius, no
        # plateau, no step at the limbus, nothing sunken), fading out just past the limbus
        qi = ell_q(c, r, self.IRIS_C, self.IRIS_R)
        if qi < self.QB:
            z += self.BULGE * (1 - qi / self.QB) ** 2
        return z

    QB = 1.45  # cornea extent, in iris radii squared

    def paint(self, c, r):
        if ell_q(c, r, self.PUP_C, self.PUP_R) < 1:
            return self.PUPIL
        qi = ell_q(c, r, self.IRIS_C, self.IRIS_R)
        if qi < self.LIMB ** 2:
            return self.IRIS
        if qi < 1:
            return self.LIMBUS
        return self.SCLERA

    def loops(self):
        return [(ell_loop(self.PUP_C, self.PUP_R), True),
                (ell_loop(self.IRIS_C, (self.IRIS_R[0] * self.LIMB, self.IRIS_R[1] * self.LIMB), n=64), True),
                (ell_loop(self.IRIS_C, self.IRIS_R, n=72), True)]


class Lips:
    key = "lips"
    name = "assembly-newsh-caret-196"
    tag = "nshc196a"
    W, H = 48, 28
    C0, R0 = 24, 14
    place = [("newsh-caret-196", 0, 0), ("newsh-caret-208", 24, 0)]
    UPPER, LOWER, SLIT = 69, 71, 16
    mats = {69: 0.45, 71: 0.42, 16: 0.7}
    sigma = 0.8
    step = 0.45
    rim = 2.0
    rings = (0.06, 0.2, 0.4, 0.65, 0.95, 1.3, 1.7)
    # parting line (edge coords): the sprite's interior ink line, pixel centres
    P = staticmethod(pchip([(2.0, 13.0), (5.0, 14.2), (8.0, 14.4), (12.0, 13.6), (16.5, 12.75), (20.5, 13.5), (24.5, 14.55),
               (28.5, 13.5), (32.5, 12.75), (37.0, 13.6), (41.0, 14.4), (44.0, 14.2), (47.0, 13.0)]))
    SLIT_W = 0.5

    def __init__(self, inner):
        ext = {}
        for c in range(self.W):
            rs = [r for r in range(self.H) if inner[r][c]]
            if rs:
                ext[c] = (min(rs), max(rs) + 1)
        cols = sorted(ext)
        xs = [c + 0.5 for c in cols]
        self.top = pchip(list(zip(xs, smooth_series(xs, [ext[c][0] for c in cols], 1.4))))
        self.bot = pchip(list(zip(xs, smooth_series(xs, [ext[c][1] for c in cols], 1.4))))

    def env(self, c):
        u = (c - 24.5) / 23.0
        return max(0.18, (1 - u * u)) ** 0.55

    def height(self, c, r, d):
        e = min(d / self.rim, 1.0)
        roundr = math.sqrt(max(0.0, 1 - (1 - e) ** 2))
        p = self.P(c)
        env = self.env(c)
        if r < p:
            t = self.top(c)
            v = max(0.0, min(1.0, (r - t) / max(0.6, p - t)))
            # rises from the vermilion border, crowns at ~45%, rolls steeply into the slit
            lobe = 5.2 * env * max(0.0, 1 - abs((v - 0.45) / (0.55 if v > 0.45 else 0.45)) ** 2.2) ** 0.5
        else:
            b = self.bot(c)
            w = max(0.0, min(1.0, (r - p) / max(0.6, b - p)))
            lobe = 6.2 * env * max(0.0, 1 - abs((w - 0.42) / (0.58 if w > 0.42 else 0.42)) ** 2.0) ** 0.5
        z = max(lobe, 0.0)
        # the slit: a crease along the parting line
        s = abs(r - p)
        z = min(z, 0.55 + 2.6 * s * s) if s < 1.6 else z
        return max(0.5, z) * roundr

    def paint(self, c, r):
        p = self.P(c)
        if abs(r - p) < self.SLIT_W and 3.5 < c < 44.5:
            return self.SLIT
        return self.UPPER if r < p else self.LOWER

    def loops(self):
        out = []
        for sgn in (-1, 1):
            out.append(([(c / 4, self.P(c / 4) + sgn * self.SLIT_W) for c in range(14, 179)], False))
        return out


# ------------------------------------------------------------------------------------------------
# Mesh
# ------------------------------------------------------------------------------------------------

def build(spec, coll, poly_pts, sprite):
    poly = Poly(poly_pts)
    X = lambda c: (c - spec.C0) * PX  # noqa: E731
    Y = lambda r: (spec.R0 - r) * PX  # noqa: E731
    outline = resample(poly_pts, 0.36)
    opoly = Poly(outline)
    pts = list(outline)
    nb = len(outline)
    for d in spec.rings:
        ring = resample(offset(poly_pts, -d), 0.36 + d * 0.05)
        for c, rr in ring:
            if poly.inside(c, rr) and abs(opoly.dist(c, rr) - d) < 0.1:
                pts.append((c, rr))
    edges = [(i, (i + 1) % nb) for i in range(nb)]
    cons = []
    for lp, closed in spec.loops():
        keep = [p for p in lp if poly.inside(*p) and opoly.dist(*p) > spec.rings[-1] * 0.5]
        if len(keep) < 2:
            continue
        cons.append((keep, closed and len(keep) == len(lp)))
    step = spec.step
    dy = step * math.sqrt(3) / 2
    r = 0.0
    row = 0
    allc = [p for lp, _ in cons for p in lp]
    carr = np.array(allc) if allc else np.zeros((0, 2))
    while r < spec.H:
        c = (step / 2) * (row % 2)
        while c < spec.W:
            if poly.inside(c, r) and opoly.dist(c, r) > spec.rings[-1] + step * 0.55:
                if not len(carr) or np.hypot(carr[:, 0] - c, carr[:, 1] - r).min() > step * 0.45:
                    pts.append((c, r))
            c += step
        r += dy
        row += 1
    for lp, closed in cons:
        i0 = len(pts)
        pts.extend(lp)
        n = len(lp)
        edges.extend((i0 + i, i0 + (i + 1) % n) for i in range(n if closed else n - 1))
    res = geometry.delaunay_2d_cdt([Vector(p) for p in pts], edges, [list(range(nb))], 1, 1e-6)
    vco, faces = res[0], res[2]
    bm = bmesh.new()
    vs = []
    for p in vco:
        c, rr = p.x, p.y
        d = 0.0 if not poly.inside(c, rr) else opoly.dist(c, rr)
        vs.append(bm.verts.new((X(c), Y(rr), spec.height(c, rr, d) * PX)))
    order = list(spec.mats)
    for f in faces:
        if len(f) < 3:
            continue
        cc = sum(vco[i].x for i in f) / len(f)
        cr = sum(vco[i].y for i in f) / len(f)
        if not poly.inside(cc, cr):
            continue
        try:
            face = bm.faces.new([vs[i] for i in f])
        except ValueError:
            continue
        face.material_index = order.index(spec.paint(cc, cr))
        face.smooth = True
    # flat closed underside on the rim verts
    rim = [vs[i] for i in range(nb)]
    res2 = geometry.delaunay_2d_cdt([Vector(p) for p in outline], [(i, (i + 1) % nb) for i in range(nb)],
                                    [list(range(nb))], 1, 1e-6)
    for f in res2[2]:
        cc = sum(res2[0][i].x for i in f) / len(f)
        cr = sum(res2[0][i].y for i in f) / len(f)
        if not poly.inside(cc, cr):
            continue
        ids = [res2[3][i][0] if res2[3][i] else None for i in f]
        if any(i is None or i >= nb for i in ids):
            continue
        try:
            face = bm.faces.new([rim[i] for i in ids][::-1])
        except ValueError:
            continue
        face.material_index = order.index(spec.paint(cc, cr))
        face.smooth = False
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.link_faces[0].smooth != e.link_faces[1].smooth:
            e.smooth = False
    mesh = bpy.data.meshes.new(spec.name)
    bm.to_mesh(mesh)
    bm.free()
    for i in order:
        mesh.materials.append(common.palette_material(sprite, i, spec.tag, metallic=0.0, roughness=spec.mats[i]))
    obj = bpy.data.objects.new(spec.name, mesh)
    coll.objects.link(obj)
    return obj


# ------------------------------------------------------------------------------------------------
# Outline shell: sink + split (from the nose design of e4-enemies-1)
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


def flat_seam_caps(piece, eps=1e-4):
    me = piece.data
    for f in me.polygons:
        vs = [me.vertices[i].co for i in f.vertices]
        if all(abs(abs(v.x) - 1.0) < eps for v in vs) or all(abs(abs(v.y) - 14 / 12) < eps for v in vs):
            f.use_smooth = False


# ------------------------------------------------------------------------------------------------

def make(spec_cls, argv):
    coll = common.reset_collection(spec_cls.name)
    idx, colors = composite(spec_cls.place, spec_cls.W, spec_cls.H)
    m = S.masks(idx, colors)
    spec = spec_cls(m["inner"])
    if hasattr(spec, "cover_field"):
        spec.cover_field()
    poly = spec.footprint(m["inner"]) if hasattr(spec, "footprint") else footprint(m["inner"], spec.sigma)
    poly = resample(poly, 0.25)
    if hasattr(spec, "poly"):
        spec.poly = Poly(poly)
    sprite = {"name": spec.name, "colors": {str(k): list(v) for k, v in colors.items()}}
    obj = build(spec, coll, poly, sprite)
    layout = [(n, c + 12 - spec.C0, r + 14 - spec.R0) for n, c, r in spec.place]
    sealed = obj.copy()
    sealed.data = obj.data.copy()
    coll.objects.link(sealed)
    bpy.context.view_layer.update()
    whole = common.outline_shell(sealed, coll, voxel=0.014, faces=3000, smooth=6, inside=0.006, islands="outer")
    if getattr(spec, "sink", True):
        sink_shell(whole, sealed, margin=0.4 * PX, reach=0.6 * PX, floor=min(1.2, 0.5 * spec_max_h(sealed)) * PX)
    bpy.data.objects.remove(sealed, do_unlink=True)
    if len(layout) > 1:
        pieces = common.split_assembly(obj, layout, coll)
        for p in pieces.values():
            flat_seam_caps(p)
        cut = split_shell(whole, layout, coll)
        bpy.data.objects.remove(whole, do_unlink=True)
    else:
        name = layout[0][0]
        pieces = {name: obj}
        whole.name = whole.data.name = f"{name}_outline"
        cut = {name: whole}
    total = 0
    exports = {}
    for name, dx, dy in layout:
        p, sh = pieces[name], cut[name]
        sh.name = sh.data.name = f"{name}_outline"
        tris = sum(len(f.vertices) - 2 for f in p.data.polygons)
        total += tris
        print(f"{spec.key} {name}: {tris} tris, outline {len(sh.data.polygons)} faces")
        if not len(sh.data.polygons):
            print("WARNING empty outline", name)
        exports[name] = (p, sh)
    print(spec.key, "total tris", total)
    if "--game" in argv:
        gdir = Path(argv[argv.index("--game") + 1])
        for name, (p, sh) in exports.items():
            common.export_glb([p, sh], gdir / f"{name}.glb")
    for name, (p, sh) in exports.items():
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", data["sprites"])
    if "--review" not in argv:
        for o in list(coll.objects):
            o.hide_render = True
        return
    for name, dx, dy in layout:
        for o in exports[name]:
            o.location = (dx / 12, -dy / 12, 0)
    bpy.context.view_layer.update()
    if len(layout) > 1:
        obj.hide_render = True
        obj.hide_set(True)
    if "--review" in argv:
        rv = Path(argv[argv.index("--review") + 1]) / spec.key
        rv.mkdir(parents=True, exist_ok=True)
        review(spec, [e[0] for e in exports.values()], [e[1] for e in exports.values()], rv, total, idx, colors)
    for o in list(coll.objects):
        o.hide_render = True


def spec_max_h(obj):
    return max(v.co.z for v in obj.data.vertices) * 12


# ------------------------------------------------------------------------------------------------
# Review renders + top-view IoU (only with --review)
# ------------------------------------------------------------------------------------------------

def review(spec, pieces, shells, out, total, idx, colors):
    scene = bpy.context.scene
    for o in scene.objects:
        if o not in pieces and o.type == "MESH":
            o.hide_render = True
    for p in pieces:
        p.hide_render = False
    W, H = spec.W, spec.H
    YC = (spec.R0 - H / 2) * PX
    XC = (spec.C0 - W / 2) * -PX
    big = max(W, H) / 12

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
    topcam = lambda: cam((XC, YC, 20), None, ortho=max(W, H) / 12, top=True)  # noqa: E731
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    render(topcam(), out / "top_flat.png", W * k, H * k)
    img = bpy.data.images.load(str(out / "top_flat.png"))
    w, h = img.size
    px = np.array(img.pixels[:]).reshape(h, w, 4)[::-1]
    alpha = (px[:, :, 3] > 0.5).tolist()
    bpy.data.images.remove(img)
    stats = {"tris": total}
    stats["whole"] = S.measure(S.masks(idx, colors), alpha)
    if len(spec.place) > 1:
        for name, c0, r0 in spec.place:
            pidx, pcol = S.load(name)
            sub = [row[c0 * k:(c0 + 24) * k] for row in alpha[r0 * k:(r0 + 28) * k]]
            stats[name] = S.measure(S.masks(pidx, pcol), sub)
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    for kk, v in stats.items():
        if isinstance(v, dict):
            print("IOU", spec.key, kk, v["iou_rule_grid"], v["iou_rule"])
    # palette-index map
    mats = {m for p in pieces for m in p.data.materials}
    keep = {}
    rng = [(0.9, 0.4, 0.1), (0.95, 0.9, 0.1), (0.1, 0.3, 0.95), (0.2, 0.85, 0.3), (0.85, 0.2, 0.8)]
    for i, mt in enumerate(sorted(mats, key=lambda m: m.name)):
        keep[mt.name] = tuple(mt.diffuse_color)
        mt.diffuse_color = (*rng[list(spec.mats).index(int(mt.name.split("_")[1])) % 5], 1)
    render(topcam(), out / "top_index.png", W * k, H * k)
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
    sun = bpy.data.objects.get("game_sun")
    if sun is None:
        sun_data = bpy.data.lights.new("game_sun", "SUN")
        sun_data.energy = 3.0
        sun = bpy.data.objects.new("game_sun", sun_data)
        scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, 8.4, 20)).normalized().to_track_quat("Z", "Y").to_euler()
    ink = bpy.data.materials.get("ink_review") or bpy.data.materials.new("ink_review")
    ink.use_nodes = True
    bs = next(n for n in ink.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bs.inputs["Base Color"].default_value = (0, 0, 0, 1)
    bs.inputs["Roughness"].default_value = 1.0
    ink.use_backface_culling = True
    hulls = []
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
        hulls.append(hh)
    render(topcam(), out / "top_game.png", W * 8, H * 8)
    zc = 0.3
    render(cam((XC + 30, YC, zc), (XC, YC, zc), ortho=big * 1.15), out / "side.png", 600, 300)
    render(cam((XC, YC - 30, zc), (XC, YC, zc), ortho=big * 1.15), out / "front.png", 600, 300)
    render(cam((XC, YC + 30, zc), (XC, YC, zc), ortho=big * 1.15), out / "rear.png", 600, 300)
    d = big * 3.2
    render(cam((XC + d * 0.55, YC - d * 0.6, d * 0.5), (XC, YC, 0.3), fov=30), out / "q1.png", 600, 520)
    render(cam((XC - d * 0.6, YC + d * 0.5, d * 0.55), (XC, YC, 0.3), fov=30), out / "q2.png", 600, 520)
    tilt = math.radians(32)
    render(cam((XC, YC - d * math.sin(tilt), d * math.cos(tilt)), (XC, YC, 0.3), fov=30), out / "game.png", 600, 520)
    render(cam((XC, YC - d * 0.3, -d * 0.9), (XC, YC, 0), fov=32), out / "under.png", 500, 400)
    for hh in hulls:
        bpy.data.objects.remove(hh, do_unlink=True)
    for p in pieces:
        p.hide_render = True


def run(key):
    """Build and export one model: key is tongue, eye or lips."""
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    make({"tongue": Tongue, "eye": Eye, "lips": Lips}[key], argv)
