"""HD island rock (DECISIONS.md D75): the floating islands' cobbles as smooth stones, from the tiles'
own pixels, as a texture the game colours from the live palette.

numpy only (no bpy, PIL or scipy), so Blender's builders (lib_tiles.rock_tile, sprite_rock) and the
checks outside Blender (tools/rock_hd_check.py, previews) run the same code.

From a patch of palette-index art (a tile among its neighbours, or an enemy's sprite):
1. MMPX 2x, then the stones: each pixel climbs the smoothed brightness to its peak, the pixels of one
   peak are one stone (`climb`), and stones whose saddle is nearly as bright as the dimmer peak merge
   (`merge`: one stone with two highlights). Pixels darker than STONE_LUM are mortar, roots, outline.
2. At TEX texels per pixel: the signed distance to a stone's edge (`sd`: + inside a stone, - outside;
   from the 4x boundary, upsampled and smoothed, so the outline is a smooth curve and not stair
   steps), the stones' own shading (the art's shade numbers, smoothed within stones), the dark
   areas' shading, and a ramp code per stone (its majority colour: grey, brass, tan or the patch's
   extra ramp).
3. `compose`, pointwise: a soft mortar line along every stone edge, a cushion (height rising over
   CUSHION px from the edge, the stone's shading a little darker toward its edge), a little
   tile-periodic surface noise. Out: shade (0..15, continuous), ramp code (0..1), height (0..1).

The game draws the texture with lib_tiles' rock material (src/render/rockMaterial.ts): colour =
palette[ramp * 16 + shade], interpolated between the two shades, so fades, the hit flash and the
smoothies' hues work as on palette materials.

Seams: a tile's fields are computed among its usual neighbours on TYRIAN's map, then every tile
side's edge strip is solved jointly over every pair the map puts side by side (tools/terrain_hd.py's
method, D58) and each tile's border is moved onto its strips before `compose`, so the stones' edges
and shading meet whatever tile is next to it.
"""

import hashlib
import json
import math
import os
import struct
import tempfile
from pathlib import Path

import numpy as np

TILE_W, TILE_H = 24, 28
TEX = 8  # texels per original pixel
#: Palette ramps (index >> 4) a stone can be, in ramp-code order: grey, tan, brass (tan next to grey,
#: so the mortar between a tan and a grey stone doesn't pass through brass). A patch may add one
#: more (ramp code 1).
RAMPS = (0, 10, 1)
STONE_LUM = 0.12  # smoothed brightness below which a 2x pixel isn't stone (mortar, outline, roots)
CLIMB_SIGMA = 1.5  # 2x px: the brightness the stones are found on
MERGE_SADDLE = 0.7  # basins merge when their saddle is this bright against the dimmer peak
SHADE_SIGMA = 1.5  # 2x px: the stones' shading, smoothed
GLINT = 0.8  # how much of the art's highlights over that is kept
GLINT_SIGMA = 0.6  # 2x px: the highlights' smoothing
EDGE_SMOOTH = 0.35  # px: the signed distance's smoothing (rounds the 2x stair steps)
MORTAR = (0.05, 0.3)  # px from a stone's edge: mortar to stone
CUSHION = 1.8  # px: how far in from its edge a stone reaches its top
MORTAR_SHADE = 0.55  # a mortar line's shade against what is round it
EDGE_DARK = 0.15  # how much darker a stone's shading is at its edge than at its top
NOISE = 0.35  # shade units of surface variation on the stones
DIST_R = 12  # 4x texels: how far the distance to an edge is measured (3 px)

# Seam solve (tools/terrain_hd.py's, D58), in TEX texels.
LAMBDA = 0.15
STRIP_TEXELS = 3
STRIP_SIGMA = 2.0
BAND_LO = 20
BAND_HI = 3


# --- Small numpy kit -----------------------------------------------------------------------------

def blur(img, sigma):
    """Gaussian blur (edges repeat), separable, any float array 2D."""
    if sigma <= 0:
        return img.astype(float)
    r = max(1, int(math.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    a = img.astype(float)
    p = np.pad(a, ((r, r), (0, 0)), mode="edge")
    a = sum(k[i] * p[i:i + a.shape[0]] for i in range(2 * r + 1))
    p = np.pad(a, ((0, 0), (r, r)), mode="edge")
    return sum(k[i] * p[:, i:i + a.shape[1]] for i in range(2 * r + 1))


def blur1d(a, sigma):
    """Gaussian blur along axis 0 (edges repeat)."""
    r = max(1, int(math.ceil(3 * sigma)))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, [(r, r)] + [(0, 0)] * (a.ndim - 1), mode="edge")
    return sum(k[i] * p[i:i + a.shape[0]] for i in range(2 * r + 1))


def norm_blur(values, weight, sigma):
    """Blur of `values` over the pixels where `weight` (0..1), normalised: a smooth fill from them."""
    w = blur(weight.astype(float), sigma)
    return blur(np.where(weight > 0, values, 0.0) * weight, sigma) / np.maximum(w, 1e-4)


def upsample(a, k):
    """Bilinear upsample by an integer factor, pixel centres kept (edges repeat)."""
    h, w = a.shape
    ys = (np.arange(h * k) + 0.5) / k - 0.5
    xs = (np.arange(w * k) + 0.5) / k - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, h - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, w - 1)
    y1, x1 = np.clip(y0 + 1, 0, h - 1), np.clip(x0 + 1, 0, w - 1)
    fy = np.clip(ys - np.floor(ys), 0, 1)[:, None]
    fx = np.clip(xs - np.floor(xs), 0, 1)[None, :]
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy) + bot * fy


def nearest(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def mmpx2x(pix, luma):
    """MMPX 2x on palette indices, edges clamped: a copy of tools/terrain_hd.py's (the port of
    src/render/remaster/mmpx.ts that made the tiles' `pixels2x`), which needs PIL."""
    h, w = pix.shape
    P = np.pad(pix.astype(np.int32), 3, mode="edge")

    def s(dx, dy):
        return P[3 + dy:3 + dy + h, 3 + dx:3 + dx + w]

    A, B, C = s(-1, -1), s(0, -1), s(1, -1)
    D, E, F = s(-1, 0), s(0, 0), s(1, 0)
    G, H, I = s(-1, 1), s(0, 1), s(1, 1)
    Pp, S, Q, R = s(0, -2), s(0, 2), s(-2, 0), s(2, 0)
    Bl, Dl, El, Fl, Hl = luma[B], luma[D], luma[E], luma[F], luma[H]
    J, K, L, M = E.copy(), E.copy(), E.copy(), E.copy()
    act = (A != E) | (B != E) | (C != E) | (D != E) | (F != E) | (G != E) | (H != E) | (I != E)

    def any3(b, a0, a1, a2):
        return (b == a0) | (b == a1) | (b == a2)

    def all2(b, a0, a1):
        return (b == a0) & (b == a1)

    def all3(b, a0, a1, a2):
        return (b == a0) & (b == a1) & (b == a2)

    def all4(b, a0, a1, a2, a3):
        return (b == a0) & (b == a1) & (b == a2) & (b == a3)

    def none2(b, a0, a1):
        return (b != a0) & (b != a1)

    def none4(b, a0, a1, a2, a3):
        return (b != a0) & (b != a1) & (b != a2) & (b != a3)

    def put(cond, *pairs):
        c = act & cond
        for dst, src in pairs:
            dst[c] = src[c] if isinstance(src, np.ndarray) else src

    put((D == B) & (D != H) & (D != F) & ((El >= Dl) | (E == A)) & any3(E, A, C, G) & ((El < Dl) | (A != D) | (E != Pp) | (E != Q)), (J, D))
    put((B == F) & (B != D) & (B != H) & ((El >= Bl) | (E == C)) & any3(E, A, C, I) & ((El < Bl) | (C != B) | (E != Pp) | (E != R)), (K, B))
    put((H == D) & (H != F) & (H != B) & ((El >= Hl) | (E == G)) & any3(E, A, G, I) & ((El < Hl) | (G != H) | (E != S) | (E != Q)), (L, H))
    put((F == H) & (F != B) & (F != D) & ((El >= Fl) | (E == I)) & any3(E, C, G, I) & ((El < Fl) | (I != H) | (E != R) | (E != S)), (M, F))

    put((E != F) & all4(E, C, I, D, Q) & all2(F, B, H) & (F != s(3, 0)), (K, F), (M, F))
    put((E != D) & all4(E, A, G, F, R) & all2(D, B, H) & (D != s(-3, 0)), (J, D), (L, D))
    put((E != H) & all4(E, G, I, B, Pp) & all2(H, D, F) & (H != s(0, 3)), (L, H), (M, H))
    put((E != B) & all4(E, A, C, H, S) & all2(B, D, F) & (B != s(0, -3)), (J, B), (K, B))

    put((Bl < El) & all4(E, G, H, I, S) & none4(E, A, D, C, F), (J, B), (K, B))
    put((Hl < El) & all4(E, A, B, C, Pp) & none4(E, D, G, I, F), (L, H), (M, H))
    put((Fl < El) & all4(E, A, D, G, Q) & none4(E, B, C, I, H), (K, F), (M, F))
    put((Dl < El) & all4(E, C, F, I, R) & none4(E, B, A, G, H), (J, D), (L, D))

    hb = H != B
    h1 = hb & (H != A) & (H != E) & (H != C)
    put(h1 & all3(H, G, F, R) & none2(H, D, s(2, -1)), (L, M))
    put(h1 & all3(H, I, D, Q) & none2(H, F, s(-2, -1)), (M, L))
    b1 = hb & (B != I) & (B != G) & (B != E)
    put(b1 & all3(B, A, F, R) & none2(B, D, s(2, 1)), (J, K))
    put(b1 & all3(B, C, D, Q) & none2(B, F, s(-2, 1)), (K, J))
    fd = F != D
    d1 = fd & (D != I) & (D != E) & (D != C)
    put(d1 & all3(D, A, H, S) & none2(D, B, s(1, 2)), (J, L))
    put(d1 & all3(D, G, B, Pp) & none2(D, H, s(1, -2)), (L, J))
    f1 = fd & (F != E) & (F != A) & (F != G)
    put(f1 & all3(F, C, H, S) & none2(F, B, s(-1, 2)), (K, M))
    put(f1 & all3(F, I, B, Pp) & none2(F, H, s(-1, -2)), (M, K))

    out = np.empty((h * 2, w * 2), np.int32)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = J, K, L, M
    return out.astype(pix.dtype)


# --- Palette -------------------------------------------------------------------------------------

class Pal:
    """Colours {index: (r, g, b)} and their brightness (0..1, Rec. 601)."""

    def __init__(self, colors):
        self.colors = {int(k): tuple(v) for k, v in colors.items()}
        self.lum = np.zeros(257)
        for i, (r, g, b) in self.colors.items():
            if 0 <= i < 256:
                self.lum[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def rgb(self, index):
        return self.colors[int(index)]


# --- Stones --------------------------------------------------------------------------------------

def climb(sm, mask):
    """Each masked pixel's peak: steepest ascent over its 8 neighbours on `sm`, followed to the top.
    Returns the peak's flat index per pixel, -1 outside the mask."""
    h, w = sm.shape
    v = np.where(mask, sm, -9.0)
    P = np.pad(v, 1, constant_values=-9.0)
    yy, xx = np.mgrid[0:h, 0:w]
    best = yy * w + xx
    bv = v.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nv = P[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            better = nv > bv
            bv = np.where(better, nv, bv)
            best = np.where(better, np.clip(yy + dy, 0, h - 1) * w + np.clip(xx + dx, 0, w - 1), best)
    nxt = best.ravel()
    for _ in range(int(math.log2(h * w)) + 2):
        nxt = nxt[nxt]
    return np.where(mask, nxt.reshape(h, w), -1)


def merge(lab, sm, ratio=MERGE_SADDLE, kind=None):
    """Merge neighbouring basins (one stone with two highlights): where they touch, the boundary's
    mean brightness is at least `ratio` of the dimmer peak's, brightest first. A stone's edge is
    mostly dark even where its mortar breaks for a pixel, so the mean is used, not the brightest
    point. `kind` (like lab): basins whose majority kinds differ (a tan stone by a grey one) never
    merge."""
    peak = {int(l): float(sm.ravel()[l]) for l in np.unique(lab[lab >= 0])}
    major = {}
    if kind is not None:
        for l in peak:
            major[l] = int(np.argmax(np.bincount(kind[lab == l])))
    total, count = {}, {}
    for X, Y, S in ((lab[:, :-1], lab[:, 1:], np.minimum(sm[:, :-1], sm[:, 1:])),
                    (lab[:-1], lab[1:], np.minimum(sm[:-1], sm[1:]))):
        m = (X != Y) & (X >= 0) & (Y >= 0)
        for x, y, v in zip(np.minimum(X[m], Y[m]), np.maximum(X[m], Y[m]), S[m]):
            k = (int(x), int(y))
            total[k] = total.get(k, 0.0) + float(v)
            count[k] = count.get(k, 0) + 1
    saddle = {k: total[k] / count[k] for k in total}
    parent = {l: l for l in peak}

    def find(l):
        while parent[l] != l:
            parent[l] = parent[parent[l]]
            l = parent[l]
        return l

    for (x, y), s in sorted(saddle.items(), key=lambda kv: (-kv[1], kv[0])):
        a, b = find(x), find(y)
        if a == b or (major and major[a] != major[b]):
            continue
        if s >= ratio * min(peak[a], peak[b]):
            hi, lo = (a, b) if (peak[a], a) >= (peak[b], b) else (b, a)
            parent[lo] = hi
    out = lab.copy()
    for l in peak:
        r = find(l)
        if r != l:
            out[lab == l] = r
    return out


def edge_distance(lab, r=DIST_R):
    """Distance (4x texels, capped at r) from every 4x texel of `lab` (2x labels) to the nearest
    texel on a label boundary: where the label differs from a 4-neighbour."""
    lab4 = nearest(lab, 2)
    b = np.zeros(lab4.shape, bool)
    dx = lab4[:, 1:] != lab4[:, :-1]
    dy = lab4[1:] != lab4[:-1]
    b[:, 1:] |= dx
    b[:, :-1] |= dx
    b[1:] |= dy
    b[:-1] |= dy
    h, w = b.shape
    d2 = np.full((h, w), float(r * r))
    P = np.pad(b, r, constant_values=False)
    offs = sorted(((oy, ox) for oy in range(-r, r + 1) for ox in range(-r, r + 1) if oy * oy + ox * ox < r * r),
                  key=lambda o: o[0] ** 2 + o[1] ** 2)
    for oy, ox in offs:
        hit = P[r + oy:r + oy + h, r + ox:r + ox + w]
        d2 = np.where(hit & (d2 > oy * oy + ox * ox), oy * oy + ox * ox, d2)
    # The boundary texels sit on both sides of the label change: measure from the change itself.
    return np.maximum(np.sqrt(d2) - 0.5, 0.0)


def ramp_slot(index, ramps):
    """Position of a palette index's ramp in `ramps` (RAMPS + the patch's extra), or None."""
    r = int(index) >> 4
    return ramps.index(r) if r in ramps else None


def snap_index(pal, index, keep):
    """The nearest (RGB) of `keep` to palette index `index`."""
    rgb = pal.rgb(index)
    return min(keep, key=lambda k: sum((a - b) ** 2 for a, b in zip(pal.rgb(k), rgb)))


def fields(pal, g1, ramps=RAMPS):
    """The HD fields of a patch of art at TEX texels per pixel. `g1`: palette indices at 1x, -1
    transparent, already in the colours the rock may use (`ramps`' ramps). Returns a dict of float
    arrays: sd (signed px from a stone's edge), stone (stone shade 0..15), dark (the dark areas'
    shade), code (ramp code 0..1, the stones' and dark areas' ramps), alpha (0..1)."""
    g1 = np.asarray(g1, dtype=np.int32)
    luma = np.append(pal.lum[:256] * 765 + 1, 0.0)  # index -1 reads the appended 0
    g2 = mmpx2x(g1, luma)
    op = g2 >= 0
    idx = np.maximum(g2, 0)
    lum = np.where(op, pal.lum[idx], 0.0)
    sm = norm_blur(lum, op.astype(float), CLIMB_SIGMA)
    stone = op & (sm >= STONE_LUM)
    nslot = max(1, len(ramps) - 1)
    lut = np.array([ramps.index(i >> 4) if (i >> 4) in ramps else 0 for i in range(256)] + [-1])
    slot = lut[np.where(g2 >= 0, g2, 256)]  # -1 transparent; a ramp not in `ramps` counts as grey
    # Grey stones and warm ones (brass, tan, the extra ramp) are found apart: a tan stone's pixels
    # would otherwise climb into the brighter grey stone beside it.
    warm = slot > 0
    lab = np.maximum(climb(sm, stone & ~warm), climb(sm, stone & warm))
    lab = merge(lab, sm, kind=np.maximum(slot, 0))
    # Stones are their labels; the dark (mortar, roots, outline) is one region, the transparent another.
    lab = np.where(stone, lab, np.where(op, -1, -2))
    shade = (idx & 15).astype(float)
    # A stone's ramp is its pixels' most common one.
    code2 = np.where(slot >= 0, slot, 0).astype(float) / nslot
    for l in np.unique(lab[lab >= 0]):
        m = lab == l
        counts = np.bincount(slot[m], minlength=len(ramps))
        code2[m] = int(np.argmax(counts)) / nslot
    k = TEX // 2
    # The stones' shading: smooth, plus the art's highlights (the glints are sheen: kept as colour,
    # crisp, while the darker checker between them is smoothed away).
    wst = stone.astype(float)
    smooth = norm_blur(shade, wst, SHADE_SIGMA)
    stone_shade = smooth + GLINT * np.maximum(norm_blur(shade, wst, GLINT_SIGMA) - smooth, 0)
    d4 = edge_distance(lab)
    inside4 = nearest(stone, 2)
    sd4 = np.where(inside4, d4, -d4) / 4.0  # 4x texels -> px
    sd = blur(upsample(sd4, 2), EDGE_SMOOTH * TEX)
    return {
        "sd": sd,
        "stone": upsample(stone_shade, k),
        "dark": upsample(norm_blur(shade, (op & ~stone).astype(float), SHADE_SIGMA), k),
        "all": upsample(norm_blur(shade, op.astype(float), SHADE_SIGMA), k),
        "code": blur(nearest(code2, k), 0.25 * TEX),
        "alpha": blur(nearest(op.astype(float), k), 0.3 * TEX),
    }


def periodic_noise(h, w, period=(TILE_H * TEX, TILE_W * TEX), cells=(7, 6), seed=7, origin=(0, 0)):
    """Smooth value noise that repeats every `period` texels (a tile), so every tile edge meets its
    neighbour's whatever the neighbour is. `origin`: texel position of the array's top-left."""
    rng = np.random.default_rng(seed)
    grid = rng.uniform(-1, 1, cells)
    ys = ((np.arange(h) + origin[0]) % period[0]) / period[0] * cells[0]
    xs = ((np.arange(w) + origin[1]) % period[1]) / period[1] * cells[1]
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = smoothstep(0, 1, ys - y0)[:, None], smoothstep(0, 1, xs - x0)[None, :]
    g = lambda y, x: grid[y % cells[0]][:, x % cells[1]]  # noqa: E731
    top = g(y0, x0) * (1 - fx) + g(y0, x0 + 1) * fx
    bot = g(y0 + 1, x0) * (1 - fx) + g(y0 + 1, x0 + 1) * fx
    return top * (1 - fy) + bot * fy


def compose(F, origin=(0, 0)):
    """The texture channels from the fields: shade (0..15), code (0..1), height (0..1).

    A stone (sd > 0) is its own smoothed shading, a little darker toward its edge (EDGE_DARK over
    CUSHION px) and with a little surface noise; the dark areas (sd < 0) theirs; along every stone
    edge a mortar line darkens what is there to MORTAR_SHADE of it. The height is the cushion."""
    sd = F["sd"]
    line = 1 - smoothstep(MORTAR[0], MORTAR[1], np.abs(sd))
    cush = smoothstep(0.0, CUSHION, sd)
    h, w = sd.shape
    noise = periodic_noise(h, w, origin=origin) + 0.5 * periodic_noise(h, w, cells=(14, 12), seed=11, origin=origin)
    stone = F["stone"] * (1 - EDGE_DARK + EDGE_DARK * cush) + NOISE * noise * cush
    inside = smoothstep(-0.3, 0.3, sd)
    base = F["dark"] * (1 - inside) + stone * inside
    shade = base * (1 - line) + MORTAR_SHADE * F["all"] * line
    height = np.clip(cush * (0.9 + 0.1 * noise) + 0.15 * (1 - inside) * np.clip(F["dark"] / 6, 0, 1), 0, 1)
    # Mortar is grey whatever the stones beside it.
    code = np.clip(F["code"], 0, 1) * (1 - line)
    return {"shade": np.clip(shade, 0, 15), "code": code, "height": height, "alpha": F["alpha"]}


# --- TYRIAN's map: contexts and pairs ------------------------------------------------------------

MAP_SIZES = [(14, 300), (14, 600), (15, 600)]
SHAPES_PER_FILE = 600


def data_dir(root):
    env = os.environ.get("TYRIAN_DATA")
    return Path(env) if env else Path(root) / "data"


def level_map(root, level="1-9", layer=2):
    """The level's map on `layer` as 0-based shapes records (-1: nothing drawn), as levelTiles()
    resolves it (tools/terrain_hd.py LevelData, layers 1-2: blank shapes and the last entries are
    nothing)."""
    ep, num = (int(s) for s in level.split("-"))
    b = (data_dir(root) / f"tyrian{ep}.lvl").read_bytes()
    lvl_num = min(struct.unpack_from("<H", b, 0)[0], 42)
    pos = [struct.unpack_from("<I", b, 2 + 4 * i)[0] if i < lvl_num else len(b) for i in range(43)]
    p = pos[(num - 1) * 2]
    letter = chr(b[p + 1]).lower()
    p += 2 + 6
    p += 2 + 2 * struct.unpack_from("<H", b, p)[0]
    p += 2 + 11 * struct.unpack_from("<H", b, p)[0]
    map_sh = [list(struct.unpack_from(">128H", b, p + 256 * k)) for k in range(3)]
    p += 3 * 256
    raws = []
    for w, h in MAP_SIZES:
        raws.append(np.frombuffer(b, np.uint8, w * h, p).reshape(h, w))
        p += w * h
    sb = (data_dir(root) / f"shapes{letter}.dat").read_bytes()
    blank, q = [], 0
    for _ in range(SHAPES_PER_FILE):
        blank.append(sb[q] != 0)
        q += 1 + (0 if blank[-1] else TILE_W * TILE_H)
    lut = np.full(256, -1, np.int32)
    for x in range(72):
        z = map_sh[layer][x] - 1
        if 0 <= z < SHAPES_PER_FILE and not blank[z] and (layer == 0 or (x != 71 if layer == 1 else x < 70)):
            lut[x] = z
    return lut[raws[layer]]


def map_pairs(grid, tiles):
    """{("h", left, right) or ("v", top, bottom): count} for neighbouring cells both in `tiles`."""
    out = {}
    ok = np.isin(grid, list(tiles))
    for o, a, b, m in (("h", grid[:, :-1], grid[:, 1:], ok[:, :-1] & ok[:, 1:]),
                       ("v", grid[:-1], grid[1:], ok[:-1] & ok[1:])):
        for x, y in zip(a[m], b[m]):
            k = (o, int(x), int(y))
            out[k] = out.get(k, 0) + 1
    return out


def usual_context(grid, n):
    """Tile n among its most common neighbours in `grid` (sides and corners, -1 where the most
    common is nothing), as a 3x3 pattern."""
    h, w = grid.shape
    ys, xs = np.nonzero(grid == n)
    out = [[-1] * 3 for _ in range(3)]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                out[1][1] = n
                continue
            vals = [int(grid[y + dy, x + dx]) if 0 <= y + dy < h and 0 <= x + dx < w else -1 for y, x in zip(ys, xs)]
            if vals:
                c = {}
                for v in vals:
                    c[v] = c.get(v, 0) + 1
                out[dy + 1][dx + 1] = max(c, key=lambda v: (c[v], -v))
    return out


# --- Seams ---------------------------------------------------------------------------------------

def edge_strip(img, side):
    k = STRIP_TEXELS
    strip = {"left": img[:, :k].mean(1), "right": img[:, -k:].mean(1), "up": img[:k].mean(0), "down": img[-k:].mean(0)}[side]
    return blur1d(strip, STRIP_SIGMA)


def solve_strips(tiles, pairs, lam=LAMBDA):
    """tools/terrain_hd.py's solve_strips (D58): each side's strip, least squares over the map's
    pairs (weighted by count) plus a pull of `lam` toward the tile's own. `tiles`: {n: (H, W, C)}."""
    out = {}
    for o, (sa, sb) in {"h": ("right", "left"), "v": ("down", "up")}.items():
        nodes = sorted({(n, side) for n in tiles for side in (sa, sb)})
        idx = {nd: i for i, nd in enumerate(nodes)}
        N = len(nodes)
        M = np.zeros((N, N))
        deg = np.zeros(N)
        for (po, a, b), c in pairs.items():
            if po != o or a not in tiles or b not in tiles:
                continue
            i, j = idx[(a, sa)], idx[(b, sb)]
            M[i, i] += c
            M[j, j] += c
            M[i, j] -= c
            M[j, i] -= c
            deg[i] += c
            deg[j] += c
        lam_i = lam * np.maximum(deg, 1)
        M[np.arange(N), np.arange(N)] += lam_i
        own = np.stack([edge_strip(tiles[n], side) for n, side in nodes])
        sol = np.linalg.solve(M, (lam_i[:, None, None] * own).reshape(N, -1)).reshape(own.shape)
        for nd, i in idx.items():
            out[nd] = sol[i]
    return out


def apply_strips(img, strips, band_lo=BAND_LO, band_hi=BAND_HI):
    """Move each edge of `img` (H, W, C) onto its strip (terrain_hd.apply_strips)."""
    H, W = img.shape[:2]
    y = np.arange(H)[:, None] + 0.5
    x = np.arange(W)[None, :] + 0.5
    dist = {"left": np.broadcast_to(x, (H, W)), "right": np.broadcast_to(W - x, (H, W)),
            "up": np.broadcast_to(y, (H, W)), "down": np.broadcast_to(H - y, (H, W))}

    def spread(strip, side):
        return np.broadcast_to(strip[:, None, :] if side in ("left", "right") else strip[None, :, :], img.shape)

    out = img.astype(float).copy()
    for side, e in strips.items():
        wgt = (1 - smoothstep(0, band_lo, dist[side]))[..., None]
        out += wgt * spread(e - edge_strip(img, side), side)
    for side, e in strips.items():
        wgt = (1 - smoothstep(0, band_hi, dist[side]))[..., None]
        out = out * (1 - wgt) + spread(e, side) * wgt
    return out


# --- The island tiles ----------------------------------------------------------------------------

FIELD_KEYS = ("sd", "stone", "dark", "all", "code", "alpha")
CACHE_VERSION = 1


def snap_rock(pal, g1, keep, ramps=RAMPS):
    """The pixels the rock is drawn from: a pixel in one of `ramps` keeps its index (the texture
    carries any shade of them), any other is snapped to the nearest of `keep`
    (lib_tiles.ROCK_COLOURS: the pink and yellow glints, the blue-grey)."""
    out = np.array(g1, dtype=np.int32)
    flat = out.ravel()
    for v in np.unique(out[out >= 0]):
        if (int(v) >> 4) not in ramps:
            flat[flat == v] = snap_index(pal, int(v), keep)
    return out


def tile_patch(tiles_px, pattern, layer=2):
    """A pattern of tiles' 1x pixels as one array, -1 transparent (index 0 on layers 1-2)."""
    rows, cols = len(pattern), len(pattern[0])
    out = np.full((rows * TILE_H, cols * TILE_W), -1, np.int32)
    for r, row in enumerate(pattern):
        for c, n in enumerate(row):
            if n < 0 or n not in tiles_px:
                continue
            px = np.array(tiles_px[n], np.int32)
            if layer > 0:
                px = np.where(px == 0, -1, px)
            out[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W] = px
    return out


#: Pair bands (D75): how deep (texels) a tile's edge band is, and over how many texels of its inner
#: side it fades into the tile's own texture.
BAND_DEPTH = 3 * TEX
BAND_FADE = TEX
SIDES = ("left", "right", "up", "down")
CHANNELS = ("shade", "code", "height")


def _context(grid, n):
    return usual_context(grid, n) if (grid == n).any() else [[-1, -1, -1], [-1, n, -1], [-1, -1, -1]]


def pair_bands(pal, tiles_px, keep, grid, o, a, b):
    """The edge bands of a pair the map puts side by side (o "h": a left of b; "v": a over b),
    computed together: the two tiles among their usual neighbours, as one patch, so the stones that
    cross their seam are found once and both bands draw them the same. Returns (band of a, band of
    b): {channel: (BAND_DEPTH, edge length)}, row 0 at the seam."""
    ca, cb = _context(grid, a), _context(grid, b)
    if o == "h":
        pattern = [[ca[0][0], ca[0][1], cb[0][1], cb[0][2]], [ca[1][0], a, b, cb[1][2]], [ca[2][0], ca[2][1], cb[2][1], cb[2][2]]]
    else:
        pattern = [[ca[0][0], ca[0][1], ca[0][2]], [ca[1][0], a, ca[1][2]], [cb[1][0], b, cb[1][2]], [cb[2][0], cb[2][1], cb[2][2]]]
    F = fields(pal, snap_rock(pal, tile_patch(tiles_px, pattern), keep))
    th, tw = TILE_H * TEX, TILE_W * TEX
    ya, xa = th, tw
    yb, xb = (th, 2 * tw) if o == "h" else (2 * th, tw)
    A = compose({k: F[k][ya:ya + th, xa:xa + tw] for k in F})
    B = compose({k: F[k][yb:yb + th, xb:xb + tw] for k in F})
    d = BAND_DEPTH
    if o == "h":
        band_a = {c: A[c][:, ::-1][:, :d].T for c in CHANNELS}  # depth from a's right edge
        band_b = {c: B[c][:, :d].T for c in CHANNELS}
    else:
        band_a = {c: A[c][::-1][:d] for c in CHANNELS}  # depth from a's bottom edge
        band_b = {c: B[c][:d] for c in CHANNELS}
    return band_a, band_b


def island_tiles(root, tiles, tiles_px, colors, keep, level="1-9", band_tiles=(), cache=True):
    """The HD texture channels of island tiles: {n: compose() dict, plus "bands": {"<side>:<tile>":
    band}}. Each tile's texture is computed among its usual neighbours on the level's map and its
    edges solved against every tile the map puts next to it (the texture drawn where a neighbour
    has no band). For every pair of `band_tiles` side by side in the map, both tiles get an edge
    band computed with the other (pair_bands): the game draws a tile's band for the neighbour it
    actually has (src/render/rockMaterial.ts), so the stones meet across every seam the map has.
    `tiles_px`: {n: 1x pixels} for every tile (neighbours included); `colors`: the palette; `keep`:
    the rock colours. Cached in reference/tiles/rock-hd-<hash>.npz."""
    src = Path(__file__).read_bytes()
    key = hashlib.sha1(src + json.dumps([sorted(tiles), sorted(band_tiles), list(keep), level, CACHE_VERSION]).encode()
                       + b"".join(np.ascontiguousarray(tiles_px[n], np.int32).tobytes() for n in sorted(tiles_px))).hexdigest()[:16]
    path = Path(root) / "reference" / "tiles" / f"rock-hd-{key}.npz"
    if cache and path.exists():
        z = np.load(path)
        out = {n: {c: z[f"{n}_{c}"] for c in ("shade", "code", "height", "alpha")} for n in tiles}
        for n in tiles:
            out[n]["bands"] = {}
        for k in z.files:
            if k.startswith("band|"):
                _, n, bkey, c = k.split("|")
                out[int(n)]["bands"].setdefault(bkey, {})[c] = z[k]
        return out
    pal = Pal(colors)
    grid = level_map(root, level, 2)
    th, tw = TILE_H * TEX, TILE_W * TEX
    raw = {}
    for n in tiles:
        F = fields(pal, snap_rock(pal, tile_patch(tiles_px, _context(grid, n)), keep))
        raw[n] = np.stack([F[k][th:2 * th, tw:2 * tw] for k in FIELD_KEYS], -1)
    strips = solve_strips(raw, map_pairs(grid, set(tiles)))
    out = {}
    for n in tiles:
        img = apply_strips(raw[n], {side: strips[(n, side)] for side in SIDES})
        out[n] = compose({k: img[..., i] for i, k in enumerate(FIELD_KEYS)})
        out[n]["bands"] = {}
    for (o, a, b) in sorted(map_pairs(grid, set(band_tiles) & set(tiles))):
        band_a, band_b = pair_bands(pal, tiles_px, keep, grid, o, a, b)
        out[a]["bands"][f"{'right' if o == 'h' else 'down'}:{b}"] = band_a
        out[b]["bands"][f"{'left' if o == 'h' else 'up'}:{a}"] = band_b
    if cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".npz")
        os.close(fd)
        arrays = {f"{n}_{c}": d[c].astype(np.float32) for n, d in out.items() for c in ("shade", "code", "height", "alpha")}
        arrays.update({f"band|{n}|{k}|{c}": v[c].astype(np.float32) for n, d in out.items() for k, v in d["bands"].items() for c in CHANNELS})
        np.savez_compressed(tmp, **arrays)
        os.replace(tmp, path)
    return out


def band_texture(bands):
    """A tile's edge bands packed for the game: (keys in order, (BAND_DEPTH * n, TILE_H * TEX, 3)
    uint8 as texture_rgb), band i in rows i * BAND_DEPTH.., row 0 of each at the seam, column = place
    along the edge (top to bottom for left/right, left to right for up/down)."""
    keys = sorted(bands)
    L = TILE_H * TEX
    out = np.zeros((BAND_DEPTH * len(keys), L, 3), np.uint8)
    for i, k in enumerate(keys):
        rgb = texture_rgb(bands[k])
        out[i * BAND_DEPTH:(i + 1) * BAND_DEPTH, :rgb.shape[1]] = rgb
        out[i * BAND_DEPTH:(i + 1) * BAND_DEPTH, rgb.shape[1]:] = rgb[:, -1:]
    return keys, out


def texture_rgb(ch):
    """The texture's bytes (H, W, 3) uint8: R shade/15, G ramp code, B height."""
    rgb = np.stack([ch["shade"] / 15.0, ch["code"], ch["height"]], -1)
    return np.clip(np.round(rgb * 255), 0, 255).astype(np.uint8)


def preview_rgb(pal, ch, ramps=RAMPS):
    """What the game's rock material draws (flat, unlit), as RGB floats, for previews and checks."""
    s = np.clip(ch["shade"], 0, 15)
    lo = np.floor(s).astype(int).clip(0, 15)
    hi = np.clip(lo + 1, 0, 15)
    f = (s - lo)[..., None]
    cols = np.zeros((256, 3))
    for i, c in pal.colors.items():
        if 0 <= i < 256:
            cols[i] = c
    n = len(ramps) - 1
    pos = np.clip(ch["code"], 0, 1) * n
    out = np.zeros(s.shape + (3,))
    for j, r in enumerate(ramps):
        wj = np.clip(1 - np.abs(pos - j), 0, 1)[..., None]
        out += wj * (cols[r * 16 + lo] * (1 - f) + cols[r * 16 + hi] * f)
    return out
