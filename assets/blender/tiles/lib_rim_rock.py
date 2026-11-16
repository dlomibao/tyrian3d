"""The asteroid platforms' rock rim (shapesz.dat, layer 0; DECISIONS.md D211): the boulders round the
woven floor of ASTEROID1, ASTEROID2, ASTEROID? and AST. CITY as 3D rock, one tile model per rim tile.

numpy only (no bpy), so the Blender builder (shapesz_rim_rock.py) and checks outside Blender run the
same code.

The platforms are an autotile kit: a woven stone floor (371) ringed by twelve rim tiles (the corners
360/362/380/382, the sides 361/370/372/381 and the inner corners 363/364/373/374), each a band of
boulders about ten pixels deep along the platform's outline, with the weave behind it. The maps put
them together in hundreds of ways, so a model per platform can't cover them; a model per rim tile
does, if every pair the maps put side by side meets without a step:

1. **Field.** Each tile is read among its most common neighbours (a 3x3 block at MMPX 2x). The band
   (within BAND px of space) is split into the art's stones: brightness hills, as lib_tiles.hills
   (a boulder's lit top and shadowed flank climb to one peak; the crevices are the valleys). A hill
   whose median lies within STONE_BAND px of space is a boulder (deeper ones are the weave), and
   each boulder is a round dome over its own pixels, taller the wider it is, on a low bed; all of it
   rises across the outline's dark ring (the rock covers the ring: it showed as a stepped grey band
   round the rock) and fades out where the weave starts. Brightness is not height (art rule 2): the
   lit and shadowed sides come from the game's light on the facets.
2. **Seams.** Every tile side's edge profile is replaced by the mean over every side the maps put
   against it (the union of the pairs in tiles.json's neighbour counts), blended in over FALL px, so
   two tiles meet on the same heights; corners settle in a few passes. A side that mostly meets
   the floor's tiles (`Kit.inner_side`: the weave, a base's channels) goes to the floor at its edge.
3. **Mesh.** The field on a grid of STEP px, each vertex jittered (along the edge only on a tile's
   edges, by the same offsets in every tile, so neighbours share their edge vertices), two triangles
   per cell (split along the flatter diagonal), clipped at the rock's outline (the zero contour: a
   smooth curve, not the pixel steps).
4. **Facets** (D175's facet ramp, the enemy asteroids' look): faces grown into chips within ANGLE and
   CHIP px, each shaded flat and given one grey of the tile's own ramp, ranked by the art's
   brightness under it, how squarely it faces the art's light (upper left) and how high it stands
   (the crevices darker), matched to the tile's distribution of shades over its rock (BIAS darker).
   The shade rides on COLOR_0 as a multiplier of one palette material (D209's tone), so a tile is
   one draw however many shades it shows.
5. **Ink** (shapesz_rim_rock.py): D90's outline shell, made from the rock among its neighbours and
   cut open at the tile's edges, so the ink runs on across seams, as on the enemy asteroids.

Units as lib_tiles: 1 unit = 12 tile px, origin at the tile's centre, X right, Y up, Z up, z = 0 the
ground (where the painted tile is drawn: it stays under the rock; layer 0 keeps its tiles).
"""

import json
import math
from pathlib import Path

import numpy as np

TILE_W, TILE_H = 24, 28
S = 2  # grid points per tile px (the field is evaluated on MMPX 2x pixel corners)

#: The rim tiles (0-based shapesz.dat records).
RIM_TILES = (360, 361, 362, 363, 364, 370, 372, 373, 374, 380, 381, 382)

H_MAX = 0.30  # units: the boulders' height (ground enemies sit at 0.45; lib_l1bld's rim rocks reach 0.50)
OUTLINE_SIGMA = 0.6  # px: the distance to space is smoothed this much (the outline's stair steps)
RING_IN = (0.15, 1.4)  # px from space: the envelope rises across the outline ring (the rock covers it)
BAND = (10.0, 14.0)  # px from space: the envelope falls to the floor between these (the weave starts)
STONE_SIGMA = 0.9  # px: the brightness the stones are found on
STONE_MIN = 4  # px: smaller hills are crumbs (left to the bed)
STONE_BAND = 10.0  # px from space: a hill whose median lies deeper is the weave, not a boulder
STONE_K = 0.075  # units of height per px of a stone's inscribed radius
STONE_H = (0.10, H_MAX)  # a stone's top, clamped
BED = 0.03  # units: the rubble bed the boulders sit on (the crevices' floor)
BED_REACH = 1.0  # px the bed reaches past the boulders
DARK_MAX = 2  # palette indices <= this are the ring and the crevices (left out of the facet shades)
LIFT = 0.012  # units: the outline is where the rock is this high (the zero contour of f = h - LIFT)
FALL = 4.0  # px over which a side's seam correction fades in
ANGLE = 13.0  # degrees: a facet's faces stay within this of its first face
CHIP = 1.6  # px: a facet's faces stay within this of its first face's centre
SPRITE_W = 0.55  # facet rank: weight of the art's brightness under the facet,
LIGHT_W = 0.25  # of facing the art's light (upper left), the rest of its height (the crevices darker:
#                 they read as cracks between boulders, as the asteroids' grooves do)
BIAS = 0.16  # facet ramp: shift toward the darker shades (the game's light brightens the lit chips)
ART_LIGHT = np.array((-1.0, 1.0, 1.4)) / np.linalg.norm((-1.0, 1.0, 1.4))
STEP = 1.0  # px between the mesh's vertices
JITTER = 0.32  # px: how far each vertex is moved off the grid
SKIRT = -0.02  # units: the walls at a tile's edges go down to here (hidden inside the neighbour's rock)


class Kit:
    """reference/tiles/shapesz/tiles.json: the rim tiles' 2x pixels, their neighbours, the palette."""

    def __init__(self, root, shapes="shapesz"):
        data = json.loads((Path(root) / "reference" / "tiles" / shapes / "tiles.json").read_text())
        self.colors = {int(k): tuple(v) for k, v in data["colors"].items()}
        self.lum = np.zeros(256)
        for i, (r, g, b) in self.colors.items():
            self.lum[i] = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        self.px2 = {}
        self.px = {}
        self.nb = {}
        for n, t in data["tiles"].items():
            n = int(n)
            self.px[n] = np.array([[int(v) for v in r.split()] for r in t["pixels"]], dtype=np.int32)
            self.px2[n] = np.array([[int(v) for v in r.split()] for r in t["pixels2x"]], dtype=np.int32)
            self.nb[n] = {k: [(e["tile"], e["count"]) for e in v] for k, v in t["neighbours"].items()}

    def usual(self, n, side):
        """The most common tile on that side of n (the map's edge left out; 0, space, if none)."""
        for t, _ in self.nb.get(n, {}).get(side, []):
            if t >= 0 and t in self.px2:
                return t
        return 0

    def context_tiles(self, n):
        """n among its usual neighbours: 3x3 tile numbers, the corners from the sides' own neighbours."""
        up, down, left, right = (self.usual(n, s) for s in ("up", "down", "left", "right"))
        return [[self.usual(up, "left"), up, self.usual(up, "right")],
                [left, n, right],
                [self.usual(down, "left"), down, self.usual(down, "right")]]

    def context(self, n):
        """n among its usual neighbours, 3x3 tiles at 2x."""
        return np.block([[self.px2[t] for t in row] for row in self.context_tiles(n)])

    def inner_side(self, n, side):
        """Whether side ("L", "R", "T", "B") of rim tile n mostly meets tiles that aren't rim (the
        floor: weave, channels, a base's parts); space (0, and ASTEROID?'s 58) and the map's edge
        don't count."""
        key = {"L": "left", "R": "right", "T": "up", "B": "down"}[side]
        rim = other = 0
        for t, c in self.nb[n][key]:
            if t in RIM_TILES:
                rim += c
            elif t not in (-1, 0, 58):
                other += c
        return other > rim

    def pairs(self):
        """Every pair of rim tiles the maps put side by side: (a, b, "h") for a left of b, (a, b, "v")
        for a above b."""
        out = set()
        for a in RIM_TILES:
            for b, _ in self.nb[a]["right"]:
                if b in RIM_TILES:
                    out.add((a, b, "h"))
            for b, _ in self.nb[a]["left"]:
                if b in RIM_TILES:
                    out.add((b, a, "h"))
            for b, _ in self.nb[a]["down"]:
                if b in RIM_TILES:
                    out.add((a, b, "v"))
            for b, _ in self.nb[a]["up"]:
                if b in RIM_TILES:
                    out.add((b, a, "v"))
        return sorted(out)


# --- field ---------------------------------------------------------------------------------------

def _distance(mask, reach):
    """Distance (in 2x px) from each pixel centre to the nearest pixel of `mask`, up to `reach`."""
    h, w = mask.shape
    r = int(math.ceil(reach))
    pad = np.pad(mask, r, constant_values=False)
    out = np.full((h, w), float(reach))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d >= reach:
                continue
            hit = pad[r + dy:r + dy + h, r + dx:r + dx + w]
            out = np.where(hit & (d < out), d, out)
    return out


def _dilate(mask, r):
    """Grow a bool array by r pixels (8-connected steps)."""
    out = mask.copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | p[:-2, :-2] | p[2:, 2:] | p[:-2, 2:] | p[2:, :-2]
    return out


def _smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _corners(img):
    """Pixel-centred values (2x) to the pixel corners between them (the mean of the four round each)."""
    return 0.25 * (img[:-1, :-1] + img[1:, :-1] + img[:-1, 1:] + img[1:, 1:])


def _blur(img, sigma):
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(img, r, mode="edge")
    tmp = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, tmp)


def _climb(sm, mask):
    """Each masked pixel climbs the smoothed brightness to its peak (8-neighbours): a label per pixel
    (the peak's flat index), -1 outside the mask. The pixels of one peak are one stone."""
    h, w = sm.shape
    v = np.where(mask, sm, -np.inf)
    pad = np.pad(v, 1, constant_values=-np.inf)
    best = np.arange(h * w).reshape(h, w)
    bv = v.copy()
    yy, xx = np.mgrid[0:h, 0:w]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nv = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            up = nv > bv
            bv = np.where(up, nv, bv)
            best = np.where(up, np.clip(yy + dy, 0, h - 1) * w + np.clip(xx + dx, 0, w - 1), best)
    nxt = best.ravel()
    for _ in range(h + w):
        nn = nxt[nxt]
        if np.array_equal(nn, nxt):
            break
        nxt = nn
    return np.where(mask, nxt.reshape(h, w), -1)


def raw_field(kit, n):
    """The rock's height on tile n's grid of 2x pixel corners ((2*28+1) x (2*24+1)), from the tile
    among its usual neighbours, and the tile's own pixel-centred features (for the facets).

    The boulders are the art's stones: the band's pixels split into brightness hills (each pixel
    climbs the smoothed brightness to its peak; a boulder's lit top and shadowed flank fall to the
    same peak, the crevices between boulders are the valleys). A hill whose middle lies within
    STONE_BAND px of space is a boulder, deeper ones are the weave. Each boulder is a dome over its
    own pixels (height by the distance to its edge against its widest, so a big stone stands taller
    than a chip), on a low rubble bed, and the bed and boulders rise from the outline ring's inner
    edge."""
    ctx = kit.context(n)
    space = ctx == 0
    # 1x px from space, smoothed so the outline is a curve through the art's stair steps
    ds = _blur(_distance(space, (BAND[1] + 2) * S) / S, OUTLINE_SIGMA * S)
    rock = (ds < BAND[1]) & ~space
    lum = kit.lum[ctx]
    sm = _blur(np.where(rock, lum, 0.0), STONE_SIGMA * S)
    labels = _climb(sm, rock)
    stone = np.zeros(ctx.shape, dtype=bool)
    peaks = {}
    for lab in np.unique(labels[rock]):
        m = labels == lab
        if m.sum() < STONE_MIN * S * S:
            continue
        if np.median(ds[m]) > STONE_BAND:
            continue
        peaks[lab] = m
        stone |= m
    # distance to the stone's own edge (another stone, the weave, space)
    h = np.zeros(ctx.shape)
    env_out = _smoothstep(*RING_IN, ds)
    for lab, m in peaks.items():
        d = _distance(~m, 8 * S) / S
        r = max(float(d[m].max()), 0.75)
        top = float(np.clip(STONE_K * r, STONE_H[0], H_MAX))
        t = np.clip(d / r, 0.0, 1.0)
        dome = top * np.sqrt(np.clip(1 - (1 - t) ** 2, 0.0, 1.0))
        h = np.where(m, np.maximum(h, dome), h)
    env = env_out * (1 - _smoothstep(*BAND, ds))
    h = np.maximum(h, BED * env * _dilate(stone, int(BED_REACH * S))) * env_out
    oy, ox = TILE_H * S, TILE_W * S
    # the corners of the centre tile: one 2x pixel of context on every side
    f = _corners(h[oy - 1:oy + TILE_H * S + 1, ox - 1:ox + TILE_W * S + 1]) - LIFT
    own = slice(oy, oy + TILE_H * S), slice(ox, ox + TILE_W * S)
    return f, {"env": env[own], "idx": ctx[own], "lum": kit.lum[ctx[own]]}


EDGES = {"L": (slice(None), 0), "R": (slice(None), -1), "T": (0, slice(None)), "B": (-1, slice(None))}


def _side_weight(shape, side):
    """Weight of a side's seam correction over the grid: 1 on that edge, fading to 0 FALL px in."""
    rows, cols = shape
    yy, xx = np.mgrid[0:rows, 0:cols].astype(float)
    d = {"L": xx, "R": cols - 1 - xx, "T": yy, "B": rows - 1 - yy}[side] / S
    return np.clip(1 - d / FALL, 0, 1) ** 2


def fields(kit):
    """Every rim tile's field with its seams solved: {tile: (f, features)}."""
    raw = {n: raw_field(kit, n) for n in RIM_TILES}
    f = {n: raw[n][0].copy() for n in RIM_TILES}
    # side classes: the union of every pair's facing sides
    parent = {}

    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for a, b, kind in kit.pairs():
        x, y = ((a, "R"), (b, "L")) if kind == "h" else ((a, "B"), (b, "T"))
        parent[find(x)] = find(y)
    for _ in range(3):  # sides, then the other sides (which moves the corners), then again
        for sides in (("L", "R"), ("T", "B")):
            groups = {}
            for n in RIM_TILES:
                for s in sides:
                    groups.setdefault(find((n, s)), []).append((n, s))
            for members in groups.values():
                inner = any(kit.inner_side(n, s) for n, s in members)
                if len(members) < 2 and not inner:
                    continue
                # a side that mostly meets the floor's tiles (the weave, the bases' channels) has no
                # rock at its edge: a wall there would show against the flat tile next to it
                target = 0 * f[members[0][0]][EDGES[members[0][1]]] - LIFT if inner else \
                    np.mean([f[n][EDGES[s]] for n, s in members], axis=0)
                for n, s in members:
                    delta = target - f[n][EDGES[s]]
                    w = _side_weight(f[n].shape, s)
                    f[n] += w * (delta[:, None] if s in "LR" else delta[None, :])
    return {n: (f[n], raw[n][1]) for n in RIM_TILES}


# --- mesh ----------------------------------------------------------------------------------------

def _x(gx):
    return (gx / S - TILE_W / 2) / 12


def _y(gy):
    return (TILE_H / 2 - gy / S) / 12


def _jitter(k, salt):
    """A fixed pseudo-random offset in [-1, 1] for integer k (the same in every tile, so the vertices
    on a tile's edges sit where the neighbour's do)."""
    x = math.sin(k * 12.9898 + salt * 78.233) * 43758.5453
    return 2 * (x - math.floor(x)) - 1


def _sample(f, gy, gx):
    """f (on the 2x corner grid) at a fractional grid point, bilinearly."""
    rows, cols = f.shape
    y0 = min(int(math.floor(gy)), rows - 2)
    x0 = min(int(math.floor(gx)), cols - 2)
    ty, tx = gy - y0, gx - x0
    return ((1 - ty) * ((1 - tx) * f[y0, x0] + tx * f[y0, x0 + 1])
            + ty * ((1 - tx) * f[y0 + 1, x0] + tx * f[y0 + 1, x0 + 1]))


def mesh(f):
    """The rock surface of one tile: vertices [(x, y, z)], triangles [(a, b, c)] (counter-clockwise
    from above), clipped at the zero contour of f. The vertices are a grid of STEP px, each moved by
    up to JITTER px (along the edge only, on a tile's edges: the same offsets in every tile, so
    neighbours share their edge vertices), so the chips are irregular rather than pixel blocks; f is
    sampled where they land. Grid vertices keep their grid key, contour vertices the edge they cut,
    so they're shared by the triangles round them."""
    nr, nc = int(TILE_H / STEP) + 1, int(TILE_W / STEP) + 1
    pos = np.zeros((nr, nc, 2))  # (gy, gx) on f's 2x corner grid
    for i in range(nr):
        for j in range(nc):
            y, x = i * STEP, j * STEP
            if 0 < i < nr - 1:
                y += JITTER * _jitter(i, 1) if j in (0, nc - 1) else JITTER * _jitter(i * 131 + j, 2)
            if 0 < j < nc - 1:
                x += JITTER * _jitter(j, 3) if i in (0, nr - 1) else JITTER * _jitter(i * 131 + j, 4)
            pos[i, j] = y * S, x * S
    fv = np.array([[_sample(f, *pos[i, j]) for j in range(nc)] for i in range(nr)])
    verts, index = [], {}

    def grid_v(p):
        k = ("g",) + p
        if k not in index:
            index[k] = len(verts)
            gy, gx = pos[p]
            verts.append((_x(gx), _y(gy), max(float(fv[p]), 0.0)))
        return index[k]

    def cut_v(p, q):
        k = ("c",) + tuple(sorted((p, q)))
        if k not in index:
            a, b = fv[p], fv[q]
            t = a / (a - b)
            g = pos[p] + t * (pos[q] - pos[p])
            index[k] = len(verts)
            verts.append((_x(g[1]), _y(g[0]), 0.0))
        return index[k]

    tris = []

    def clip(tri):
        # tri: three grid points (i, j), counter-clockwise from above
        inside = [fv[p] > 0 for p in tri]
        if not any(inside):
            return
        if all(inside):
            tris.append(tuple(grid_v(p) for p in tri))
            return
        poly = []
        for k in range(3):
            p, q = tri[k], tri[(k + 1) % 3]
            if inside[k]:
                poly.append(grid_v(p))
            if inside[k] != inside[(k + 1) % 3]:
                poly.append(cut_v(p, q))
        for k in range(1, len(poly) - 1):
            tris.append((poly[0], poly[k], poly[k + 1]))

    for i in range(nr - 1):
        for j in range(nc - 1):
            a, b, cc, d = (i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)  # TL, TR, BR, BL (y down)
            if max(fv[a], fv[b], fv[cc], fv[d]) <= 0:
                continue
            # counter-clockwise from above (Y up, rows down): split along the flatter diagonal
            if abs(fv[a] - fv[cc]) <= abs(fv[b] - fv[d]):
                clip((a, d, cc))
                clip((a, cc, b))
            else:
                clip((a, d, b))
                clip((b, d, cc))
    return verts, tris


def facets(verts, tris, feat, kit):
    """D175's facet ramp on one tile: [facet per triangle], [facet normal], [palette index per facet]."""
    v = np.array(verts)
    t = np.array(tris)
    p0, p1, p2 = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    cr = np.cross(p1 - p0, p2 - p0)
    area = np.linalg.norm(cr, axis=1) / 2
    nrm = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    cen = (p0 + p1 + p2) / 3
    # adjacency by shared edges
    edge_faces = {}
    for k, (a, b, c) in enumerate(tris):
        for e in ((a, b), (b, c), (c, a)):
            edge_faces.setdefault(tuple(sorted(e)), []).append(k)
    nbrs = [[] for _ in tris]
    for fs in edge_faces.values():
        for i in fs:
            for j in fs:
                if i != j:
                    nbrs[i].append(j)
    cos_lim = math.cos(math.radians(ANGLE))
    reach = CHIP / 12
    region = np.full(len(tris), -1)
    regions = []
    for k in np.argsort(-area):  # big faces seed first
        if region[k] >= 0:
            continue
        rid = len(regions)
        region[k] = rid
        stack, members = [k], []
        while stack:
            cur = stack.pop()
            members.append(cur)
            for j in nbrs[cur]:
                if region[j] < 0 and nrm[j] @ nrm[k] >= cos_lim and np.linalg.norm(cen[j] - cen[k]) <= reach:
                    region[j] = rid
                    stack.append(j)
        regions.append(members)
    # per facet: area-weighted normal, facing the light, the art's brightness under it, top-view area
    rows, cols = feat["idx"].shape
    light, seen, bright, fnorm, low = [], [], [], [], []
    for members in regions:
        m = np.array(members)
        n = (nrm[m] * area[m, None]).sum(0)
        n = n / max(np.linalg.norm(n), 1e-12)
        fnorm.append(n)
        light.append(float(n @ ART_LIGHT))
        low.append(float((cen[m, 2] * area[m]).sum() / max(area[m].sum(), 1e-12)))
        top = area[m] * np.maximum(nrm[m, 2], 0)
        seen.append(float(top.sum()))
        gx = np.clip(((cen[m, 0] * 12 + TILE_W / 2) * S).astype(int), 0, cols - 1)
        gy = np.clip(((TILE_H / 2 - cen[m, 1] * 12) * S).astype(int), 0, rows - 1)
        lum = feat["lum"][gy, gx]
        bright.append(float((lum * top).sum() / top.sum()) if top.sum() > 0 else float(lum.mean()))
    key = LIGHT_W * _ranks(light) + SPRITE_W * _ranks(bright) + (1 - LIGHT_W - SPRITE_W) * _ranks(low)
    # the tile's own shades over its rock (the boulders' greys, ring and crevices left out)
    idx = feat["idx"][(feat["env"] > 0.5) & (feat["idx"] > DARK_MAX) & (feat["idx"] < 16)]
    shades, counts = np.unique(idx, return_counts=True)
    cdf = np.cumsum(counts) / counts.sum()
    order = np.argsort(key, kind="stable")
    total = sum(seen) or 1.0
    pick = np.zeros(len(regions), dtype=int)
    acc = 0.0
    for r in order:
        q = min(max((acc + seen[r] / 2) / total - BIAS, 0.0), 1.0)
        acc += seen[r]
        pick[r] = int(shades[min(np.searchsorted(cdf, q - 1e-9), len(shades) - 1)])
    return region, np.array(fnorm), pick


def _ranks(vals):
    vals = np.asarray(vals, float)
    order = np.argsort(vals, kind="stable")
    out = np.empty(len(vals))
    out[order] = np.arange(len(vals)) / max(len(vals) - 1, 1)
    return out


def srgb_lin(c):
    c = np.asarray(c, float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def tone(kit, index, base):
    """COLOR_0 for a face of palette shade `index` on a material of palette colour `base`: three.js
    multiplies the two, so the face shows the palette's own colour for `index` (the greys are neutral)."""
    r = srgb_lin(kit.colors[index]) / np.maximum(srgb_lin(kit.colors[base]), 1e-4)
    return tuple(float(min(1.0, x)) for x in r) + (1.0,)


def build(kit):
    """Every rim tile, ready for Blender: {tile: dict(verts, tris, region, normals, shade, base)}."""
    out = {}
    for n, (f, feat) in fields(kit).items():
        verts, tris = mesh(f)
        region, fnorm, pick = facets(verts, tris, feat, kit)
        base = int(pick.max())
        out[n] = {"f": f, "verts": verts, "tris": tris, "region": region, "normals": fnorm,
                  "shade": pick, "base": base}
    return out
