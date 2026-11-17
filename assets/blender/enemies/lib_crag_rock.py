"""Crag rock: the loose asteroids as heaps of jagged stones with deep crevices (D239).

The asteroid sprites (newshd.shp) draw a heap of angular stones packed together: each stone a pale
top with a lit rim and a shadowed flank, the stones parted by dark crevices one or two pixels wide
(a tenth to an eighth of the rock's pixels), the tones running from near-white tops to near-black
gaps. The builders before this one (D125, D175, the hulls of newshd-123/-85/-229 and of the
assemblies) gave one closed body, or stones meeting in hairline grooves, with broad near-level
faces and an occlusion map that never went under 0.48: under the game's lights (more than half of
an up-facing face's light is fill) nothing in them could go dark, so they read as clay, and D175
painted the sprite's shades on the facets to get its range.

Here the light and dark come from the form (art rule 2; no tone is painted on a facet):

- **Stones.** The sprite's rock pixels are split into its bright masses (a watershed on the blurred
  brightness with the crevice pixels as walls, masses merged across shallow saddles; or grown from
  given centres). Each stone is a convex polyhedron cut from planes, a many-sided boulder: a crown
  of two or three faces tilted apart, a ring of bevel faces and one of shoulders (random tangent
  planes of a dome over the stone's pixels), a break or two, sides leaning in that stand on the
  stone's own pixels (they stop short of the sprite's crevice pixels; elsewhere two neighbours meet
  in a V groove), a closed belly. One matte palette material per stone: an index of its own pixels
  (art rule 1), by default the one 0.7 of the way up their luminance, its lit top's, since the
  darker pixels are the shadow and crevice the form now casts by itself; the result is checked in
  the game's render against the sprite's median and spread.
- **Core.** A low, faceted body lofted from the sprite's inner mask (lib_newshd_rock.rock_body, D74)
  in the crevices' own dark index: the floor of every crevice and the round, closed underside. The
  stones stand out of it by two thirds of their height, so the crevices are deep enough for the
  occlusion bake and the game's sun to leave them dark. With `body` the darkest pixels are the
  core's own face and the stones are set in it (tried for the four small blue-grey rocks, which
  stay on D175's builder: see D239). A mask that is not star-shaped gets one loft per piece
  (main_heap).
- **Pits.** The sprite's dark spots inside a stone, and a few more by chance, are dished out of it.
- **Bake** (no concept projection, D50/D65): a colour multiplier (occlusion at two scales taken
  down to near black in the crevices, a little lighter on the broken edges, darker in the pores and
  hollows of a procedural stone surface) and a tangent normal map of that same surface. The
  material stays matte (roughness 0.9, metallic 0); no roughness map.
- **Ink.** D90's outline shell from a sealed copy kept out of the bake (D118).

A model script calls `main(NAME, SPEC)` (one sprite, every frame on one model; `paint` and `parts`
hooks for a vent or a gem), `main_assembly(NAME, PIECES, SPEC)` (the catalogue's 2 x 2 assemblies) or
`main_heap(NAME, TILES, SPEC)` (2 x 2 and 1 x 1 pieces that travel together). SPEC keys (all
optional):

    frame        the sprite frame the rock is read from (default: the model's first)
    source       another model whose sprite the rock is read from (the same rock with a part added)
    ramp         palette ramp (index >> 4) of the rock besides the neutral greys (a blue-grey rock: 6)
    seed         random seed
    h_top/h_bot  height of the tallest stone above the waist / depth of the core's underside (units;
                 default 0.38 sqrt(inner px) px, at most 10 px, and 0.7 of that)
    core         the core's height as a share of h_top (0.35)
    body         the darkest share of the sprite's pixels (by luminance) that is the core's own face,
                 a dark body the stones are set in, and no stone's (0: every pixel is some stone's)
    core_fine    fracture faces on the core (12; more where `body` shows it)
    blur         px: the brightness blur before the watershed (0.7)
    merge        luminance: two masses whose saddle is shallower than this are one stone (6)
    wall         luminance taken off the crevice pixels before the watershed (30)
    min_px       a mass smaller than this joins its best neighbour (12)
    seeds        [(col, row)]: stone centres, instead of the brightness peaks
    gap          px between two neighbouring stones' sides where the sprite draws a crevice (1.2)
    lap          px a stone's side runs into its neighbour where it draws none (-0.25: just short)
    crevice      luminance under the local mean at which a pixel is crevice (10)
    sides        side planes per stone (11)
    side_el      (lo, hi) degrees the sides lean in from vertical (12, 24); rim_lean: more at the rim (6)
    boxy         the stones' dome profile exponent (2: round; more: boxy shoulders)
    bevel        (lo, hi) how far out the bevel faces touch the dome, share of the radius (0.45, 0.7)
    shoulder     the same for the shoulder faces (0.8, 0.93); wobble: degrees either is turned (20)
    tops         (lo, hi) degrees the crown faces tilt (14, 34)
    rim_low      a stone at the rim stands this share of h_top at least (0.6)
    pits         extra random pits per stone of 40 px or more (1); pit_r (lo, hi) px (1.1, 1.9)
    q            which of a stone's own pixels gives its palette index, by luminance (0.7: its lit top)
    tone         index steps added to that (0)
    sectors      the core loft's sides round the outline (56)
    core_pal     the core's palette index (default: of the sprite's crevice pixels, or of the `body`
                 pixels, the one `core_q` of the way up their luminance: 0.5, the median)
    tex, ntex    the colour map's and the normal map's size (512, 256)
    reach        units: the wide occlusion's distance in the bake (0.4; the near one is an eighth)
    clip         px the stones may stand outside the core's outline (0.15); None: no clip
    shell        outline_shell keywords (default D90's)

build-models.sh skips lib_ files.

    blender -b --factory-startup -P assets/blender/enemies/<name>.py -- [--no-bake] [--out file.glb]
        [--stats file.json] [--review DIR]
    (--stats also writes the segmentation maps beside it as .npz; --review, assemblies only, the
    whole rock with its pieces placed as DIR/cell.glb; CRAG_BAKE_DIR keeps the baked maps as PNGs)
"""

import json
import math
import os
import random
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_newshd_rock as R  # noqa: E402

common = R.common
SM = R.SM
WT = R.WT

DEFAULTS = {
    "frame": None, "source": None, "ramp": None, "seed": 1, "h_top": None, "h_bot": None, "core": 0.35, "body": 0.0,
    "core_fine": 12, "blur": 0.7, "merge": 6.0, "wall": 30.0, "min_px": 12, "seeds": None, "gap": 1.2, "lap": -0.25,
    "crevice": 10.0, "sides": 11, "side_el": (12.0, 24.0), "rim_lean": 6.0, "bevel": (0.45, 0.7),
    "shoulder": (0.8, 0.93), "boxy": 2.0, "wobble": 20.0, "tops": (14.0, 34.0), "rim_low": 0.6, "pits": 1,
    "pit_r": (1.1, 1.9), "q": 0.7, "tone": 0, "core_pal": None, "core_q": 0.5, "sectors": 56, "tex": 512, "ntex": 256, "reach": 0.4, "clip": 0.15,
    "shell": None, "roughness": 0.9,
}


def _lum(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


# --- the sprite ----------------------------------------------------------------------------------

class Sprite:
    """The rock as its sprite draws it: palette indices, the inner mask (D74), the luminance of its
    rock pixels (a vent's or a gem's pixels take the rock's median round them)."""

    def __init__(self, name, cfg, data=None):
        idx, colors = data or SM.load(name, cfg["frame"])
        self.colors = colors
        self.idx = np.array(idx, dtype=int)
        self.h, self.w = self.idx.shape
        self.inner = np.array(SM.masks(idx, colors)["inner"], dtype=bool)
        ramp = cfg["ramp"]
        rock = np.zeros(self.idx.shape, bool)
        lum = np.zeros(self.idx.shape)
        for i, rgb in colors.items():
            sel = self.idx == i
            lum[sel] = _lum(rgb)
            if (ramp is not None and i >> 4 == ramp) or max(rgb) - min(rgb) < 40:
                rock |= sel
        self.rock = rock & self.inner
        other = self.inner & ~rock
        if other.any():  # a vent, a gem: the rock goes on under it
            fill = lum.copy()
            for y, x in zip(*np.nonzero(other)):
                win = self.rock[max(0, y - 3):y + 4, max(0, x - 3):x + 4]
                vals = lum[max(0, y - 3):y + 4, max(0, x - 3):x + 4][win]
                fill[y, x] = np.median(vals) if len(vals) else np.median(lum[self.rock])
            lum = fill
        self.lum = lum
        # distance (px) of each inner pixel's centre from the nearest pixel outside the mask
        ys, xs = np.nonzero(~self.inner)
        pad = [(-1, x) for x in range(-1, self.w + 1)] + [(self.h, x) for x in range(-1, self.w + 1)]
        pad += [(y, -1) for y in range(self.h)] + [(y, self.w) for y in range(self.h)]
        oy = np.concatenate([ys, [p[0] for p in pad]])
        ox = np.concatenate([xs, [p[1] for p in pad]])
        iy, ix = np.nonzero(self.inner)
        d = np.sqrt(((iy[:, None] - oy[None]) ** 2 + (ix[:, None] - ox[None]) ** 2).min(axis=1))
        self.dist = np.zeros(self.idx.shape)
        self.dist[iy, ix] = d

    def x(self, u):
        return (u - self.w / 2) / 12

    def y(self, v):
        return (self.h / 2 - v) / 12

    def uv(self, x, y):
        return x * 12 + self.w / 2, self.h / 2 - y * 12

    def inside(self, u, v):
        c, r = int(math.floor(u)), int(math.floor(v))
        return 0 <= r < self.h and 0 <= c < self.w and bool(self.inner[r, c])


def _blur(a, mask, sigma):
    """Gaussian blur of `a` over `mask` only (normalised, so the outside never darkens the rim)."""
    n = max(1, int(math.ceil(sigma * 3)))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sigma) ** 2)
    k /= k.sum()

    def conv(z):
        z = np.pad(z, n)
        z = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 0, z)
        z = np.apply_along_axis(lambda v: np.convolve(v, k, mode="same"), 1, z)
        return z[n:-n, n:-n]
    w = conv(mask.astype(float))
    return np.where(mask, conv(np.where(mask, a, 0.0)) / np.maximum(w, 1e-6), -1.0)


def segment(s, cfg, crev=None):
    """Label the inner mask's pixels by stone (0..n-1; -1 outside): each pixel climbs the blurred
    brightness to a peak (or floods out from the given seeds), then masses parted by a saddle
    shallower than `merge`, and masses under `min_px`, join their best neighbour."""
    sm = _blur(s.lum, s.inner, cfg["blur"])
    if crev is not None:  # the sprite's crevice lines part the stones whatever the blur leaves of them
        sm = np.where(crev, sm - cfg["wall"], sm)
    h, w = s.h, s.w
    lab = -np.ones((h, w), int)
    if cfg["seeds"]:
        # each pixel to the seed it is cheapest to walk to: a step costs 1, more across a crevice
        # pixel and across a change of brightness, so the regions end on the sprite's dark lines
        import heapq
        heap = []
        cost = np.full((h, w), np.inf)
        for k, (u, v) in enumerate(cfg["seeds"]):
            y, x = int(v), int(u)
            cost[y, x] = 0.0
            lab[y, x] = k
            heapq.heappush(heap, (0.0, y, x, k))
        while heap:
            c, y, x, k = heapq.heappop(heap)
            if c > cost[y, x]:
                continue
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                yy, xx = y + dy, x + dx
                if not (0 <= yy < h and 0 <= xx < w and s.inner[yy, xx]):
                    continue
                step = math.hypot(dy, dx) * (1.0 + (5.0 if crev is not None and crev[yy, xx] else 0.0)) \
                    + 0.12 * abs(float(s.lum[yy, xx]) - float(s.lum[y, x]))
                if c + step < cost[yy, xx]:
                    cost[yy, xx] = c + step
                    lab[yy, xx] = k
                    heapq.heappush(heap, (c + step, yy, xx, k))
        return lab
    nxt = np.arange(h * w)
    for y in range(h):
        for x in range(w):
            if not s.inner[y, x]:
                continue
            best, bv = y * w + x, sm[y, x]
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and sm[yy, xx] > bv:
                        best, bv = yy * w + xx, sm[yy, xx]
            nxt[y * w + x] = best
    for _ in range(h + w):
        nxt = nxt[nxt]
    peaks = nxt.reshape(h, w)
    ids = {p: k for k, p in enumerate(np.unique(peaks[s.inner]))}
    for y, x in zip(*np.nonzero(s.inner)):
        lab[y, x] = ids[peaks[y, x]]
    while True:
        n = lab.max() + 1
        size = np.bincount(lab[s.inner], minlength=n)
        peak = np.array([sm[lab == k].max() if size[k] else -1 for k in range(n)])
        saddle = {}
        for y in range(h):
            for x in range(w):
                a = lab[y, x]
                if a < 0:
                    continue
                for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and lab[yy, xx] >= 0 and lab[yy, xx] != a:
                        key = (min(a, lab[yy, xx]), max(a, lab[yy, xx]))
                        saddle[key] = max(saddle.get(key, -1), min(sm[y, x], sm[yy, xx]))
        best = None
        for (a, b), sv in saddle.items():
            prom = min(peak[a], peak[b]) - sv
            small = min(size[a], size[b]) < cfg["min_px"]
            if prom < cfg["merge"] or small:
                score = prom - (1000 if small else 0)
                if best is None or score < best[0]:
                    best = (score, a, b)
        if best is None:
            break
        _, a, b = best
        lab[lab == b] = a
        lab[lab > b] -= 1
    return lab


def crevices(s, cfg):
    """The sprite's crevice pixels: darker than the mean round them (5 x 5 over the mask) by
    `crevice` and in the rock's darker third; not the rim ring (its dark is the limb's shadow)."""
    w = s.inner.astype(float)
    pad = np.pad(np.where(s.inner, s.lum, 0.0), 2)
    padw = np.pad(w, 2)
    tot = np.zeros(s.lum.shape)
    cnt = np.zeros(s.lum.shape)
    for dy in range(5):
        for dx in range(5):
            tot += pad[dy:dy + s.h, dx:dx + s.w]
            cnt += padw[dy:dy + s.h, dx:dx + s.w]
    mean = tot / np.maximum(cnt, 1)
    p35 = np.percentile(s.lum[s.inner], 35)
    return s.inner & (s.lum < mean - cfg["crevice"]) & (s.lum < p35) & (s.dist > 1.2)


def region_index(s, sel, q=0.5, tone=0, ramp=None):
    """The palette index a region stands for: of its rock pixels in its own ramp, sorted by
    luminance, the one `q` of the way up (0.5: the median, as D125's trimmed median; a stone takes
    0.7, its lit top's index: the darker half of its pixels is the shadow and crevice the form now
    casts by itself); `tone` steps further along the ramp."""
    vals = [int(v) for v in s.idx[sel & s.rock]]
    if not vals:
        return None
    ramps = [v >> 4 for v in vals]
    main = max(set(ramps), key=ramps.count)  # the region's own ramp: a stray pixel of another never wins
    if ramp is not None and ramps.count(ramp) * 5 >= len(ramps):
        main = ramp  # the rock's own ramp where the region has it (the neutral greys are its ink and limb)
    vals = sorted((v for v in vals if v >> 4 == main), key=lambda v: _lum(s.colors[v]))
    i = vals[min(int(len(vals) * q), len(vals) - 1)]
    if tone:
        ramp = sorted((j for j in s.colors if j >> 4 == main), key=lambda j: _lum(s.colors[j]))
        i = ramp[min(max(ramp.index(i) + tone, 0), len(ramp) - 1)]
    return i


# --- geometry ------------------------------------------------------------------------------------

def convex(planes, size=14.0):
    """The convex solid inside every plane (unit normal n, offset d: n . p <= d), cut from a cube."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=size)
    for n, d in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True)
        cut = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if cut:
            bmesh.ops.holes_fill(bm, edges=cut, sides=0)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def _dir(az, el):
    return Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))


def stone_planes(s, sel, crev, zt, depth, rng, cfg):
    """The planes of one stone: a many-sided boulder, the random tangent planes of a boxy dome over
    the stone's own pixels. `sel`: its pixels; `crev`: the sprite's crevice pixels (where they part
    it from its neighbour its side stops short of them; elsewhere it runs `lap` px into the
    neighbour, so the two meet in a V groove down to the waist); zt: its top's height; depth: its
    belly below the waist (units)."""
    keep = sel & ~crev
    if keep.sum() < 3:
        keep = sel
    ys, xs = np.nonzero(keep)
    cu, cv = xs.mean() + 0.5, ys.mean() + 0.5
    corners = np.concatenate([np.stack([xs + a, ys + b], 1) for a in (0, 1) for b in (0, 1)]).astype(float)
    ya, xa = np.nonzero(sel)
    corners_all = np.concatenate([np.stack([xa + a, ya + b], 1) for a in (0, 1) for b in (0, 1)]).astype(float)
    c = Vector((s.x(cu), s.y(cv), 0.0))
    m = cfg["sides"]
    off = rng.uniform(0, 2 * math.pi)
    planes, radius = [], []
    for j in range(m):
        az = off + 2 * math.pi * (j + rng.uniform(-0.3, 0.3)) / m
        du, dv = math.cos(az), -math.sin(az)  # sprite rows run down
        r = float(((corners[:, 0] - cu) * du + (corners[:, 1] - cv) * dv).max())
        r_all = float(((corners_all[:, 0] - cu) * du + (corners_all[:, 1] - cv) * dv).max())
        rim = not s.inside(cu + du * (r_all + 0.8), cv + dv * (r_all + 0.8))
        if rim:
            r = r_all
        elif r_all - r < 0.5:  # no crevice drawn this way: into the neighbour
            r = r_all + cfg["lap"]
        else:
            r = max(r - cfg["gap"] / 2, 0.6)
        radius.append((az, r))
        p = c + Vector((math.cos(az), math.sin(az), 0.0)) * (r / 12)
        lo, hi = cfg["side_el"]
        el = math.radians(rng.uniform(lo, hi) + (cfg["rim_lean"] if rim else 0))
        n = _dir(az, el)
        planes.append((n, n.dot(p)))
        n = _dir(az, -math.radians(rng.uniform(38, 62)))
        planes.append((n, n.dot(p)))

    def r_at(az):
        return min(radius, key=lambda t: abs((t[0] - az + math.pi) % (2 * math.pi) - math.pi))[1] / 12
    top = Vector((c.x, c.y, zt))
    pw = cfg["boxy"]

    def tangent(az, rho, wobble):
        """The dome's tangent plane at azimuth az, rho of the way out (z = zt (1 - rho^pw)^(1/pw))."""
        rr = r_at(az)
        z = zt * (1 - rho ** pw) ** (1 / pw)
        slope = zt / rr * rho ** (pw - 1) * (1 - rho ** pw) ** (1 / pw - 1)
        el = math.atan2(1.0, slope) + math.radians(rng.uniform(-wobble, wobble))
        el = min(max(el, math.radians(14)), math.radians(86))
        p = Vector((c.x + math.cos(az) * rr * rho, c.y + math.sin(az) * rr * rho, z))
        n = _dir(az, el)
        return n, n.dot(p)
    # the crown: three or four faces tilted apart, meeting in ridges
    nt = rng.choice((2, 3, 3))
    off = rng.uniform(0, 2 * math.pi)
    for j in range(nt):
        az = off + 2 * math.pi * (j + rng.uniform(-0.25, 0.25)) / nt
        n = _dir(az, math.radians(90 - rng.uniform(*cfg["tops"])))
        p = top + Vector((math.cos(az), math.sin(az), 0.0)) * r_at(az) * rng.uniform(0.0, 0.22)
        planes.append((n, n.dot(p)))
    # the bevel ring and the shoulders
    for count, (lo, hi) in ((rng.randint(3, 5), cfg["bevel"]), (rng.randint(3, 5), cfg["shoulder"])):
        off = rng.uniform(0, 2 * math.pi)
        for j in range(count):
            az = off + 2 * math.pi * (j + rng.uniform(-0.3, 0.3)) / count
            planes.append(tangent(az, rng.uniform(lo, hi), cfg["wobble"]))
    # a break or two: a chunk off one shoulder
    for _ in range(rng.choice((2, 2, 3))):
        az = rng.uniform(0, 2 * math.pi)
        n = _dir(az, math.radians(rng.uniform(18, 42)))
        p = Vector((c.x, c.y, zt * rng.uniform(0.4, 0.75))) + Vector((math.cos(az), math.sin(az), 0.0)) * r_at(az) * 0.84
        planes.append((n, n.dot(p)))
    planes.append((Vector((0, 0, -1)), depth))
    return planes, (cu, cv)


def _core_lobe(s, mask, cfg, mat, coll, name, fine):
    """One lofted body over `mask` (star-shaped from its middle): (object, grid, spec)."""
    g = R.Grid.__new__(R.Grid)
    g.w, g.h, g.inner = s.w, s.h, mask.tolist()
    ys, xs = np.nonzero(mask)
    k = int(np.argmax(s.dist[ys, xs]))
    spec = {
        "summit": (float(xs.mean() + 0.5) * 0.6 + (xs[k] + 0.5) * 0.4, float(ys.mean() + 0.5) * 0.6 + (ys[k] + 0.5) * 0.4),
        "h_top": cfg["h_top"] * cfg["core"], "h_bot": cfg["h_bot"], "seed": cfg["seed"], "summit_gain": 0.0,
        "ridges": [], "tilt": 0.0, "lumps": 0.05, "waist": 0.05, "rise": 0.6, "fall": 0.8, "top_pow": 0.5,
        "grow": 0.0, "smooth": 1, "steps": 144, "fine": fine, "fine_depth": (0.02, 0.05), "rim_spalls": 10,
        "rim_depth": (0.012, 0.022),
        "cuts": [(30, -55, 0.05), (150, -50, 0.05), (260, -58, 0.05), (100, -64, 0.04), (200, -28, 0.03),
                 (320, -26, 0.03), (80, -30, 0.03)],
    }
    bm, _ = R.rock_body(g, spec, sectors=cfg["sectors"], rings_top=4, rings_bot=3)
    R.cut_planes(bm, spec["cuts"] + R.fine_cuts(spec))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    obj = common.mesh_object(f"{name}_core", bm, [mat], coll, smooth=False)
    return obj, g, spec


def _grown(mask, inner, px):
    """`mask` grown `px` pixels (8-neighbour) inside `inner`."""
    m = mask.copy()
    for _ in range(px):
        pad = np.pad(m, 1)
        m = inner & np.logical_or.reduce([pad[1 + dy:pad.shape[0] - 1 + dy, 1 + dx:pad.shape[1] - 1 + dx]
                                          for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
    return m


def core_object(s, cfg, mat, coll, name, lobes=None):
    """The core: a low faceted body lofted from the inner mask, round and closed underneath:
    (object, [(grid, spec)] of its lofts). The loft traces the mask by rays from its middle, so a
    mask that is not star-shaped (a heap with its corners missing) is given as `lobes`, masks that
    are (an assembly's cells): one loft per lobe, each grown 3 px into its neighbours, joined."""
    if not lobes:
        obj, g, spec = _core_lobe(s, s.inner, cfg, mat, coll, name, cfg["core_fine"])
        return obj, [(g, spec)]
    obj, outlines = None, []
    for lobe in lobes:
        if lobe.sum() < 4:
            continue
        ob, g, spec = _core_lobe(s, _grown(lobe, s.inner, 3), cfg, mat, coll, name, max(4, cfg["core_fine"] // 2))
        outlines.append((g, spec))
        if obj is None:
            obj = ob
        else:
            _boolean(obj, ob, "UNION")
            bpy.data.objects.remove(ob)
            bpy.context.view_layer.update()
    return obj, outlines


def clip_prism(outlines, grow_px, coll):
    """A tall prism on the core's outline grown `grow_px` (the lofts' prisms joined): the stones are
    cut to it, so the top view stays on the sprite's inner mask."""
    prism = None
    for g, spec in outlines:
        cu, cv, radii = g.outline(steps=spec["steps"], grow=grow_px, smooth=spec["smooth"])
        bm = bmesh.new()
        n = len(radii)
        lo, hi = [], []
        for k in range(n):
            a = 2 * math.pi * k / n
            u, v = cu + radii[k] * math.cos(a), cv - radii[k] * math.sin(a)
            lo.append(bm.verts.new((g.x(u), g.y(v), -4.0)))
            hi.append(bm.verts.new((g.x(u), g.y(v), 4.0)))
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((lo[k], lo[j], hi[j], hi[k]))
        bm.faces.new(hi)
        bm.faces.new(lo[::-1])
        ob = common.mesh_object("crag_clip", bm, [], coll, smooth=False)
        if prism is None:
            prism = ob
        else:
            _boolean(prism, ob, "UNION")
            bpy.data.objects.remove(ob)
            bpy.context.view_layer.update()
    return prism


def _boolean(obj, operand, op, coll=None):
    mod = obj.modifiers.new("crag", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    if coll is not None:
        mod.operand_type = "COLLECTION"
        mod.collection = coll
    else:
        mod.object = operand
    try:
        mod.material_mode = "TRANSFER"
    except (AttributeError, TypeError):
        pass
    bpy.context.view_layer.update()
    common._apply_modifiers(obj)


def build(name, cfg, coll, sprite_json, data=None, lobes=None):
    """The rock: (object, Sprite, info). `sprite_json`: a load_sprite dict (for palette_material)."""
    s = Sprite(cfg["source"] or name, cfg, data)
    rng = random.Random(cfg["seed"])
    n_px = int(s.inner.sum())
    if cfg["h_top"] is None:
        cfg["h_top"] = min(0.38 * math.sqrt(n_px), 10.0) / 12
    if cfg["h_bot"] is None:
        cfg["h_bot"] = cfg["h_top"] * 0.7
    crev = crevices(s, cfg)
    lab = segment(s, cfg, crev)
    # the stones stand on the sprite's lit pixels; with `body`, its darkest share is the core's own
    # face (a dark body the stones are set in), not stone
    lit = s.inner if cfg["body"] <= 0 else s.inner & (s.lum >= np.percentile(s.lum[s.inner], cfg["body"] * 100))
    core_pal = cfg["core_pal"]
    if core_pal is None:
        dark = (s.inner & ~lit) if cfg["body"] > 0 else crev
        core_pal = region_index(s, dark if dark.sum() >= 4 else s.inner & (s.lum <= np.percentile(s.lum[s.inner], 15)),
                                q=cfg["core_q"], ramp=cfg["ramp"])
    mats = {}

    def mat(i):
        if i not in mats:
            mats[i] = common.palette_material(sprite_json, i, name, metallic=0.0, roughness=cfg["roughness"])
        return mats[i]
    core, outlines = core_object(s, cfg, mat(core_pal), coll, name, lobes(s) if lobes else None)
    stones = bpy.data.collections.new(f"{name}_stones")
    bpy.context.scene.collection.children.link(stones)
    dmax = float(s.dist.max())
    info = {"stones": [], "core_pal": core_pal}
    tops, stone_pal = {}, {}
    for k in range(lab.max() + 1):
        sel = (lab == k) & lit
        if sel.sum() < 3:
            continue
        pal = region_index(s, sel & ~crev if (sel & ~crev).sum() >= 3 else sel, cfg["q"], cfg["tone"])
        if pal is None:
            continue
        ys, xs = np.nonzero(sel)
        d = float(s.dist[ys, xs].max())  # how deep into the rock the stone reaches
        env = cfg["rim_low"] + (1 - cfg["rim_low"]) * min(1.0, d / max(0.55 * dmax, 1.0)) ** 0.8
        zt = cfg["h_top"] * env * rng.uniform(0.86, 1.08)
        planes, (cu, cv) = stone_planes(s, sel, crev, zt, cfg["h_bot"] * rng.uniform(0.35, 0.6), rng, cfg)
        bm = convex(planes)
        ob = common.mesh_object(f"{name}_stone{k}", bm, [mat(pal)], stones, smooth=False)
        tops[k] = zt
        stone_pal[k] = pal
        info["stones"].append({"k": k, "pal": pal, "px": int(sel.sum()), "centre": [round(cu, 1), round(cv, 1)], "z": round(zt * 12, 1)})
    bpy.context.view_layer.update()
    if cfg["clip"] is not None:
        prism = clip_prism(outlines, cfg["clip"], coll)
        for ob in list(stones.objects):
            _boolean(ob, prism, "INTERSECT")
        bpy.data.objects.remove(prism)
    _boolean(core, None, "UNION", stones)
    for ob in list(stones.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(stones)
    core.name = core.data.name = name
    # pits: the sprite's dark spots inside a stone, and a few by chance
    pits = bpy.data.collections.new(f"{name}_pits")
    bpy.context.scene.collection.children.link(pits)
    pit_mat = bpy.data.materials.new("crag_pit")  # marks the pits' faces through the boolean
    bvh = BVHTree.FromObject(core, bpy.context.evaluated_depsgraph_get())
    spots = []
    for k in tops:
        sel = (lab == k) & lit
        ys, xs = np.nonzero(sel & ~crev & (s.dist > 1.5))
        if not len(ys):
            continue
        med = np.median(s.lum[sel])
        dark = [(s.lum[y, x], x + 0.5, y + 0.5) for y, x in zip(ys, xs)
                if s.lum[y, x] < med - 16 and s.lum[y, x] <= s.lum[max(0, y - 1):y + 2, max(0, x - 1):x + 2].min()]
        for _, u, v in sorted(dark)[:2]:
            spots.append((u, v))
        for _ in range(cfg["pits"] if sel.sum() >= 40 else 0):
            j = rng.randrange(len(ys))
            spots.append((xs[j] + rng.random(), ys[j] + rng.random()))
    n_pits = 0
    for u, v in spots:
        hit = bvh.ray_cast(Vector((s.x(u), s.y(v), 5.0)), Vector((0, 0, -1)))
        if hit[0] is None or hit[1].z < 0.35:
            continue
        r = rng.uniform(*cfg["pit_r"]) / 12
        pb = bmesh.new()
        bmesh.ops.create_icosphere(pb, subdivisions=1, radius=r)
        bmesh.ops.scale(pb, vec=(1, rng.uniform(0.6, 0.9), 0.7), verts=pb.verts)
        bmesh.ops.rotate(pb, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 3.1), 3, "Z"), verts=pb.verts)
        bmesh.ops.translate(pb, vec=hit[0] + hit[1] * r * 0.42, verts=pb.verts)
        common.mesh_object(f"{name}_pit{n_pits}", pb, [pit_mat], pits, smooth=False)
        n_pits += 1
    if n_pits:
        bpy.context.view_layer.update()
        _boolean(core, None, "DIFFERENCE", pits)
    for ob in list(pits.objects):
        bpy.data.objects.remove(ob)
    bpy.data.collections.remove(pits)
    # a pit's faces take the colour of the stone they are cut in; the marker material goes
    me = core.data
    slot_of = {}
    for k, m in enumerate(me.materials):
        if m and m != pit_mat:
            slot_of.setdefault(next(i for i, mm in mats.items() if mm == m), k)
    pit_slots = {k for k, m in enumerate(me.materials) if m == pit_mat or m is None}
    for p in me.polygons:
        if p.material_index in pit_slots:
            u, v = s.uv(p.center.x, p.center.y)
            col, row = min(max(int(u), 0), s.w - 1), min(max(int(v), 0), s.h - 1)
            p.material_index = slot_of.get(stone_pal.get(int(lab[row, col]), core_pal) if lit[row, col] else core_pal, 0)
    for k in sorted(pit_slots, reverse=True):
        me.materials.pop(index=k)
    bpy.data.materials.remove(pit_mat)
    bm = bmesh.new()
    bm.from_mesh(core.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(core.data)
    bm.free()
    for p in core.data.polygons:
        p.use_smooth = False
    info.update(tris=len(core.data.polygons), open_edges=open_edges, pits=n_pits, h_top=cfg["h_top"], h_bot=cfg["h_bot"],
                materials=sorted(mats))
    info["_maps"] = {"lab": lab, "crev": crev, "lum": s.lum, "inner": s.inner}
    info["_mats"] = mats
    print(f"{name}: {len(info['stones'])} stones, {n_pits} pits, {info['tris']} triangles, open edges {open_edges}, "
          f"stone pal {[t['pal'] for t in info['stones']]}, core pal {core_pal}")
    return core, s, info


# --- measuring -----------------------------------------------------------------------------------

def top_view(objs, w, h, k=8, centre=(0.0, 0.0)):
    """The objects' top view on a w x h sprite grid, k px per sprite px: rows of bools."""
    img = np.zeros((h * k, w * k), bool)
    for obj in objs:
        me = obj.data
        mw = obj.matrix_world
        vs = np.array([(mw @ v.co)[:2] for v in me.vertices])
        px = (vs[:, 0] - centre[0]) * 12 * k + w * k / 2
        py = h * k / 2 - (vs[:, 1] - centre[1]) * 12 * k
        me.calc_loop_triangles()
        for t in me.loop_triangles:
            a, b, c = t.vertices
            x0, x1 = int(max(0, math.floor(min(px[a], px[b], px[c])))), int(min(w * k - 1, math.ceil(max(px[a], px[b], px[c]))))
            y0, y1 = int(max(0, math.floor(min(py[a], py[b], py[c])))), int(min(h * k - 1, math.ceil(max(py[a], py[b], py[c]))))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (py[b] - py[c]) * (px[a] - px[c]) + (px[c] - px[b]) * (py[a] - py[c])
            if abs(d) < 1e-12:
                continue
            l1 = ((py[b] - py[c]) * (gx - px[c]) + (px[c] - px[b]) * (gy - py[c])) / d
            l2 = ((py[c] - py[a]) * (gx - px[c]) + (px[a] - px[c]) * (gy - py[c])) / d
            img[y0:y1 + 1, x0:x1 + 1] |= (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
    return img.tolist()


def measure(name, objs, frame=None, centre=(0.0, 0.0)):
    idx, colors = SM.load(name, frame)
    partners = SM.pulse_partners(idx, SM.load_frames(name))
    m = SM.masks(idx, colors, partners)
    out = SM.measure(m, top_view(objs, len(idx[0]), len(idx), centre=centre))
    print(f"{name}{'' if frame is None else f' frame {frame}'}: top-view rule IoU grid {out['iou_rule_grid']} (fine {out['iou_rule']}), "
          f"edge {out['edge_vs_inner_px']:+.2f} px")
    return out


# --- bake ----------------------------------------------------------------------------------------

def _gpu(scene, samples):
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
    except Exception as err:  # noqa: BLE001
        print("crag: no GPU bake", err)


def uv_overlap(obj, n=512):
    """Share of the UV map's covered texels that more than one triangle covers (interiors only: a
    texel on a shared edge counts once), so two islands laid over each other show up."""
    me = obj.data
    uv = me.uv_layers.active.data
    count = np.zeros((n, n), np.int16)
    me.calc_loop_triangles()
    for t in me.loop_triangles:
        (ax, ay), (bx, by), (cx, cy) = (uv[i].uv * n for i in t.loops)
        mx, my = (ax + bx + cx) / 3, (ay + by + cy) / 3
        # shrink a little toward the centroid, so neighbours sharing an edge never both claim a texel
        ax, ay, bx, by, cx, cy = (mx + (ax - mx) * 0.9, my + (ay - my) * 0.9, mx + (bx - mx) * 0.9, my + (by - my) * 0.9,
                                  mx + (cx - mx) * 0.9, my + (cy - my) * 0.9)
        x0, x1 = int(max(0, math.floor(min(ax, bx, cx)))), int(min(n - 1, math.ceil(max(ax, bx, cx))))
        y0, y1 = int(max(0, math.floor(min(ay, by, cy)))), int(min(n - 1, math.ceil(max(ay, by, cy))))
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if x1 < x0 or y1 < y0 or abs(d) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
        count[y0:y1 + 1, x0:x1 + 1] += ((l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)).astype(np.int16)
    covered = (count > 0).sum()
    return float((count > 1).sum() / covered) if covered else 0.0


def bake(obj, tag, size=512, nsize=256, samples=48, caps=(), reach=0.4):
    """UV the rock and bake its two maps (module doc): `<tag>_colour` (a grey multiplier of the
    palette colour) and `<tag>_normal` (tangent space), wired into every material. `caps`: polygon
    indices that get no texels (an assembly piece's cut faces, hidden against its neighbours: baked,
    they are black islands whose edge bleeds into the islands beside them as a dark hairline along
    the seam). `reach`: the wide occlusion's distance (units); the near one's is an eighth of it."""
    scene = bpy.context.scene
    _gpu(scene, samples)
    bpy.context.view_layer.update()  # (objects unlinked since the last sync leave dead entries)
    me = obj.data
    uv = me.uv_layers.new(name="bake")
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(48), island_margin=0.004, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    uv = me.uv_layers["bake"]  # (the layer's data moved while in edit mode)
    for k in caps:
        p = me.polygons[k]
        loops = range(p.loop_start, p.loop_start + p.loop_total)
        cu = sum(uv.data[i].uv.x for i in loops) / p.loop_total
        cv = sum(uv.data[i].uv.y for i in loops) / p.loop_total
        for i in loops:
            uv.data[i].uv = (cu, cv)
    over = uv_overlap(obj)
    if over > 0.002:
        print(f"{tag}: WARNING uv overlap {over:.4f}")
    col_img = bpy.data.images.new(f"{tag}_colour", size, size, alpha=False)
    nrm_img = bpy.data.images.new(f"{tag}_normal", nsize, nsize, alpha=False)
    nrm_img.colorspace_settings.name = "Non-Color"
    mats = [m for m in me.materials if m]
    out_dir = os.environ.get("CRAG_BAKE_DIR") or tempfile.mkdtemp(prefix=f"{tag}_bake_")

    def surface(nt, tmp):
        """The stone's fine surface: its height, its pits and hollows (0..1) and its grain (0..1)."""
        N, L = nt.nodes.new, nt.links.new

        def node(kind, **props):
            n = N(kind)
            for k, v in props.items():
                setattr(n, k, v)
            tmp.append(n)
            return n

        def math_(op, a, b=None, c=None):
            n = node("ShaderNodeMath", operation=op)
            for k, v in enumerate((a, b, c)):
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    n.inputs[k].default_value = v
                else:
                    L(v, n.inputs[k])
            return n.outputs[0]
        def smooth(v, lo, hi):
            n = node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
            L(v, n.inputs["Value"])
            n.inputs["From Min"].default_value = lo
            n.inputs["From Max"].default_value = hi
            return n.outputs["Result"]
        co = node("ShaderNodeNewGeometry").outputs["Position"]  # world: an assembly's pieces share it

        def noise(scale, detail, rough=0.55):
            n = node("ShaderNodeTexNoise")
            n.inputs["Scale"].default_value = scale
            n.inputs["Detail"].default_value = detail
            n.inputs["Roughness"].default_value = rough
            L(co, n.inputs["Vector"])
            return n.outputs["Fac"]
        pores = smooth(noise(15.0, 2.0), 0.57, 0.68)      # irregular pits under a pixel wide
        hollows = smooth(noise(5.5, 1.0), 0.56, 0.74)     # broad shallow hollows
        grain = noise(42.0, 4.0, 0.65)
        cavity = math_("MAXIMUM", pores, math_("MULTIPLY", hollows, 0.55))
        height = math_("SUBTRACT", math_("MULTIPLY", grain, 0.4),
                       math_("ADD", pores, math_("MULTIPLY", hollows, 0.7)))
        return height, cavity, grain, math_, node

    saved = {}
    for m in mats:
        nt = m.node_tree
        out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
        saved[m.name] = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
    for mode, img in (("colour", col_img), ("normal", nrm_img)):
        tmps = {}
        for m in mats:
            nt = m.node_tree
            tmp = []
            height, cavity, grain, math_, node = surface(nt, tmp)
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
            if mode == "colour":
                ao_s = node("ShaderNodeAmbientOcclusion", samples=24)
                ao_s.inputs["Distance"].default_value = max(0.02, reach / 8)
                ao_l = node("ShaderNodeAmbientOcclusion", samples=24)
                ao_l.inputs["Distance"].default_value = reach
                bev = node("ShaderNodeBevel", samples=8)
                bev.inputs["Radius"].default_value = 0.012
                geo = node("ShaderNodeNewGeometry")
                dot = node("ShaderNodeVectorMath", operation="DOT_PRODUCT")
                nt.links.new(bev.outputs["Normal"], dot.inputs[0])
                nt.links.new(geo.outputs["True Normal"], dot.inputs[1])
                worn = math_("MINIMUM", math_("MULTIPLY", math_("SUBTRACT", 1.0, dot.outputs["Value"]), 6.0), 1.0)
                # occlusion: the wide one to the power 1.6 (a crevice floor ~0.05), the near one for the
                # foot of each stone
                occl = math_("MULTIPLY", math_("POWER", ao_l.outputs["AO"], 1.8), math_("POWER", ao_s.outputs["AO"], 0.5))
                v = math_("ADD", 0.04, math_("MULTIPLY", occl, 0.96))
                v = math_("MULTIPLY", v, math_("SUBTRACT", 1.0, math_("MULTIPLY", cavity, 0.55)))
                v = math_("MULTIPLY", v, math_("ADD", 0.9, math_("MULTIPLY", grain, 0.24)))
                v = math_("MINIMUM", math_("ADD", v, math_("MULTIPLY", math_("MULTIPLY", worn, occl), 0.12)), 1.0)
                em = node("ShaderNodeEmission")
                comb = node("ShaderNodeCombineColor")
                for k in range(3):
                    nt.links.new(v, comb.inputs[k])
                nt.links.new(comb.outputs[0], em.inputs["Color"])
                nt.links.new(em.outputs[0], out.inputs["Surface"])
            else:
                bump = node("ShaderNodeBump")
                bump.inputs["Strength"].default_value = 1.0
                bump.inputs["Distance"].default_value = 0.035
                nt.links.new(height, bump.inputs["Height"])
                nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
                if saved[m.name] is not None:
                    nt.links.new(saved[m.name], out.inputs["Surface"])
            tgt = node("ShaderNodeTexImage")
            tgt.image = img
            uvn = node("ShaderNodeUVMap")
            uvn.uv_map = "bake"
            nt.links.new(uvn.outputs["UV"], tgt.inputs["Vector"])
            nt.nodes.active = tgt
            tmps[m.name] = tmp
        if mode == "colour":
            bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        else:
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=6, use_clear=True)
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
        ntex = nt.nodes.new("ShaderNodeTexImage")
        ntex.image = nrm_img
        nt.links.new(uvn.outputs["UV"], ntex.inputs["Vector"])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.uv_map = "bake"
        nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return col_img, nrm_img


# --- the model scripts' entry points -------------------------------------------------------------

def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    stats = Path(argv[argv.index("--stats") + 1]) if "--stats" in argv else None
    return argv, out, stats


def _write_stats(stats, info):
    """--stats file.json: the build's numbers, and beside it the segmentation maps (.npz) for review."""
    maps = info.pop("_maps", None)
    info.pop("_mats", None)
    if not stats:
        return
    stats.parent.mkdir(parents=True, exist_ok=True)
    stats.write_text(json.dumps(info, indent=1))
    if maps:
        np.savez(stats.with_suffix(".npz"), **maps)


def _shell(obj, coll, name, cfg):
    closed = obj.copy()
    closed.data = obj.data.copy()
    coll.objects.link(closed)
    bpy.context.view_layer.update()  # (objects removed since the last sync leave dead entries)
    shell = common.outline_shell(closed, coll, **(cfg["shell"] or R.D90_SHELL))
    shell.name = shell.data.name = f"{name}_outline"
    bpy.data.objects.remove(closed)
    return shell


def main(name, spec=None, paint=None, parts=None):
    """Build, bake and export one asteroid, every frame of its sprite on the one model.

    paint(sprite_json, s, obj, info): optional, before the bake: may cut the rock and add palette
    materials. parts(sprite_json, s, obj, coll): optional extra objects exported with the rock, not
    baked (a glowing vent, a gem), frame-tagged where they change."""
    argv, out, stats = _args()
    # an empty scene: the factory scene's cube (2 units, round the origin) stood in the bake's
    # occlusion rays and drew its square on the rock
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg = dict(DEFAULTS, **(spec or {}))
    sprite = common.load_sprite(WT, name)
    coll = common.reset_collection(name)
    obj, s, info = build(name, cfg, coll, sprite)
    if paint:
        paint(sprite, s, obj, info)
    extra = parts(sprite, s, obj, coll) if parts else []
    info["iou"] = {}
    for f in sprite["sprites"][0]["frames"]:
        info["iou"][str(f)] = measure(name, [obj], frame=f)["iou_rule_grid"]
    fmt = "AUTO"
    shell = _shell(obj, coll, name, cfg)  # from the unbaked rock; kept out of the bake (D118)
    coll.objects.unlink(shell)
    if "--no-bake" not in argv:
        hidden = [o for o in extra if o.name in coll.objects]
        for o in hidden:
            coll.objects.unlink(o)
        bake(obj, name, size=cfg["tex"], nsize=cfg["ntex"], reach=cfg["reach"])
        for o in hidden:
            coll.objects.link(o)
        fmt = "WEBP"
    coll.objects.link(shell)
    objs = [obj, *extra, shell]
    if out:
        common.export_glb(objs, out, image_format=fmt)
    else:
        common.export_sprite_model(WT, objs, f"enemies/{name}", sprite["sprites"], image_format=fmt)
    info["shell_tris"] = sum(len(p.vertices) - 2 for p in shell.data.polygons)
    _write_stats(stats, info)
    return obj


def _cut(obj, cells, coll, fill, suffix=""):
    """`obj` cut into one object per cell ((model, cx, cy, hw, hh): its centre and half size in px,
    from the rock's middle), each moved so its cell's centre is the origin. `fill`: close the cuts
    (the rock's pieces, as common.split_assembly); open for the outline shell's pieces, so no ink runs
    along the seams (assembly-newshe-39)."""
    out = {}
    for name, cx, cy, hw, hh in cells:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.transform(bm, matrix=obj.matrix_world, verts=bm.verts)
        for co, no in (((x0 - hw / 12, 0, 0), (-1, 0, 0)), ((x0 + hw / 12, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh / 12, 0), (0, -1, 0)), ((0, y0 + hh / 12, 0), (0, 1, 0))):
            res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                         clear_outer=True)
            edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if fill and edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        if fill:
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(f"{name}{suffix}")
        bm.to_mesh(me)
        bm.free()
        for m in obj.data.materials:
            me.materials.append(m)
        piece = bpy.data.objects.new(f"{name}{suffix}", me)
        coll.objects.link(piece)
        out[name] = piece
    return out


def _assemble(name, cells, cfg, data, lobes, argv, out, stats):
    """Build the whole rock from the composed sprite `data`, cut it into `cells`, bake each piece with
    the others in place (their occlusion across the cuts), export every piece with its slice of the
    outline shell."""
    coll = common.reset_collection(name)
    idx, colors = data
    sprite = {"name": name, "colors": {str(k): list(v) for k, v in colors.items()}, "frames": [{"pixels": idx}]}
    obj, s, info = build(name, cfg, coll, sprite, data=data, lobes=lobes)
    m = SM.masks(idx, colors)
    whole = SM.measure(m, top_view([obj], len(idx[0]), len(idx)))
    print(f"{name}: top-view rule IoU grid {whole['iou_rule_grid']} (fine {whole['iou_rule']})")
    info["iou"] = {"whole": whole["iou_rule_grid"]}
    shell = _shell(obj, coll, name, cfg)
    parts = _cut(obj, cells, coll, True)
    shells = _cut(shell, cells, coll, False, "_outline")
    bpy.data.objects.remove(shell)
    coll.objects.unlink(obj)
    for sh in shells.values():
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        coll.objects.unlink(sh)
    fmt = "AUTO"
    for pname, cx, cy, _, _ in cells:
        q = parts[pname]
        for p in q.data.polygons:
            p.use_smooth = False
        q.location = (cx / 12, -cy / 12, 0)
    bpy.context.view_layer.update()
    info["pieces"] = {}
    for pname, cx, cy, _, _ in cells:
        q = parts[pname]
        info["iou"][pname] = measure(pname, [q], centre=(cx / 12, -cy / 12))["iou_rule_grid"]
        info["pieces"][pname] = len(q.data.polygons)
    if "--no-bake" not in argv:
        for pname, _, _, hw, hh in cells:
            # each piece's own copies of the materials, so each carries its own maps
            q = parts[pname]
            for k, mm in enumerate(q.data.materials):
                if mm:
                    q.data.materials[k] = mm.copy()
            caps = [p.index for p in q.data.polygons if abs(p.normal.z) < 1e-3 and (
                all(abs(abs(q.data.vertices[v].co.x) - hw / 12) < 1e-4 for v in p.vertices)
                or all(abs(abs(q.data.vertices[v].co.y) - hh / 12) < 1e-4 for v in p.vertices))]
            small = hw < 12
            bake(q, pname, size=cfg["tex"] // (2 if small else 1), nsize=cfg["ntex"] // (2 if small else 1), caps=caps,
                 reach=cfg["reach"])
        fmt = "WEBP"
    if "--review" in argv:
        d = Path(argv[argv.index("--review") + 1])
        d.mkdir(parents=True, exist_ok=True)
        objs = []
        for pname, cx, cy, _, _ in cells:
            sh = shells[pname]
            coll.objects.link(sh)
            sh.location = (cx / 12, -cy / 12, 0)
            objs += [parts[pname], sh]
        bpy.context.view_layer.update()
        common.export_glb(objs, d / "cell.glb", image_format=fmt)
        for pname, *_ in cells:
            coll.objects.unlink(shells[pname])
    for pname, *_ in cells:
        parts[pname].location = (0, 0, 0)
        shells[pname].location = (0, 0, 0)
    bpy.context.view_layer.update()
    for pname, *_ in cells:
        sh = shells[pname]
        coll.objects.link(sh)
        piece = common.load_sprite(WT, pname)
        target = None if out is None else out.parent / f"{pname}.glb"
        if target:
            common.export_glb([parts[pname], sh], target, image_format=fmt)
        else:
            common.export_sprite_model(WT, [parts[pname], sh], f"enemies/{pname}", piece["sprites"], image_format=fmt)
    _write_stats(stats, info)
    return parts


def main_assembly(name, pieces, spec=None):
    """An assembly of 2 x 2 enemies (the catalogue's `assembly`): the whole rock built from the
    composed sprite, cut into its pieces."""
    argv, out, stats = _args()
    # an empty scene: the factory scene's cube (2 units, round the origin) stood in the bake's
    # occlusion rays and drew its square on the rock
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg = dict(DEFAULTS, **(spec or {}))
    first = common.load_sprite(WT, pieces[0])
    entries = [e for e in first["assemblyLayout"] if e["model"] in pieces]
    # the composed sprite's origin, as sprite_mask composes it (24 x 28 pieces by their centres)
    x0 = min(e["cx"] - 12 for e in entries)
    y0 = min(e["cy"] - 14 for e in entries)
    x1 = max(e["cx"] + 12 for e in entries)
    y1 = max(e["cy"] + 14 for e in entries)
    centre = ((x0 + x1) / 2, (y0 + y1) / 2)
    cells = [(e["model"], e["cx"] - centre[0], e["cy"] - centre[1], 12, 14) for e in entries]
    return _assemble(name, cells, cfg, SM.load(name), None, argv, out, stats)


def main_heap(name, tiles, spec=None):
    """A heap made of 2 x 2 enemies and 1 x 1 edge pieces that travel together: `tiles` is
    [(model, left, top, size)], each piece's top-left corner (screen px, any origin) and size (2:
    24 x 28, 1: 12 x 14). The sprite is composed from every piece's own frame, the rock built whole
    (its core one loft per piece: such a heap's outline is not star-shaped) and cut into the pieces."""
    argv, out, stats = _args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg = dict(DEFAULTS, **(spec or {}))
    boxes = [(model, left, top, 12 * size, 14 * size) for model, left, top, size in tiles]
    x0 = min(b[1] for b in boxes)
    y0 = min(b[2] for b in boxes)
    x1 = max(b[1] + b[3] for b in boxes)
    y1 = max(b[2] + b[4] for b in boxes)
    idx = [[-1] * (x1 - x0) for _ in range(y1 - y0)]
    colors = {}
    for model, left, top, w, h in boxes:
        px, col = SM.load(model)
        colors.update(col)
        assert len(px) == h and len(px[0]) == w, (model, len(px[0]), len(px))
        for y, row in enumerate(px):
            for x, v in enumerate(row):
                if v >= 0:
                    idx[top - y0 + y][left - x0 + x] = v
    centre = ((x0 + x1) / 2, (y0 + y1) / 2)
    cells = [(model, left + w / 2 - centre[0], top + h / 2 - centre[1], w / 2, h / 2) for model, left, top, w, h in boxes]

    def lobes(s):
        out = []
        for model, left, top, w, h in boxes:
            m = np.zeros(s.inner.shape, bool)
            m[top - y0:top - y0 + h, left - x0:left - x0 + w] = True
            out.append(m & s.inner)
        return out
    return _assemble(name, cells, cfg, (idx, colors), lobes, argv, out, stats)
