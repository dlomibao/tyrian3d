"""Glass orb (newshu.shp, four 2x2 pieces: newshu-91 | -93 over newshu-129 | -131):
an engineered bio-reactor pod built from its cross-sections, then cut into the four pieces.

Reading of the sprite (48 x 56 px block; x = column, y = row, pixel edges; front = screen bottom):
- A big glass ball. Its dark rim, the dark lower-right side, the bright crescent round the
  lower-right edge and the white-cyan blob on the upper left are the glass catching light, not shapes.
- Every frame is one drawing with another palette (class Drawing). Dim (frame 91): a slate-blue mass
  (102, lighter 103-105 bands where it bulges, 98-101 in the ball's own shade) behind neutral grey
  gaps (3-6). The fade's last step (241) draws what still glows in green on that slate: the core's
  bulb under the highlight (x 11-20, y 14-24), the bud at the top right of it (x 19-26, y 8-15), the
  lamp at the lower right (centre 36, 36) and a connected web of 1 px veins over the lower half and up
  the right side, with the ribs along the bottom. On the lit frames (153..237) the mass and then the
  rest turn green.

Construction (cross-sections first, D50-D53/D65 style):
- Plan: the sprite's D74 inner mask's outline as a polar Fourier curve R(t) (order 6), moved 0.55 of
  the way out to the whole sprite's outline (OUTLINE_GROW); every horizontal section of the pod is
  that outline scaled, so the top view follows the sprite.
- Equatorial girdle: a chamfered steel collar whose outer face IS the plan outline, with a modelled
  groove and 16 hex bolt heads 0.25 px proud (the sprite's dark rim ring is where it sits). The glass
  is inset 1 px under it, so the collar's outer face sits cleanly outside the glass.
- Glass dome above it (an ellipsoidal cap, HZ 21.5 px tall), its surface triangulated in plan
  (delaunay, 0.62 px) and painted by the sprite's regions, flush under the smooth skin: the mass,
  its lighter bands and the grey gaps with smooth boundaries (blurred class fields), the core, bud
  and lamp as round two-tone blobs, and the vein web drawn from the sprite's own vein pixels
  (web_graph: a segment between every two touching pixels, so it is connected wherever the sprite's
  is; 1 px wide). No tubes, lenses or fittings: it is all inside the glass.
- Lower bowl (pchip profile) and a socket boss underneath: a plausible closed shape only.
- Three states share the plan and the drawing: grey (dim, frames 91 / 241), -f2 green (lit fade,
  153..237, the glowing parts emissive), -f3 purple (one closed smooth shell, 246). Each region's
  palette index follows the sprite frame by frame (common.palette_material frames=): the commonest
  index of that region's pixels on the frame, the ink, the glare and the darkest and brightest
  shading left out.
- Cut into the pieces (common.split_assembly), shading copied from the whole pod so no seam shows;
  outline shell (D51) per state, held under the skin (tuck_shell), cut open at the piece seams.

  blender -b --factory-startup -P assembly-newshu-129.py -- [--review] [--out review.glb] [--pieces DIR]
                                                            [--report report.json]

Default does the real export (export_sprite_model: models, frames, spriteModels JSON). --review writes
a review copy instead (every state's four pieces with their outline shells at their places, the states
5 units apart in X) to --out; --pieces also writes each piece's glb into DIR.
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector, geometry, interpolate
from mathutils.bvhtree import BVHTree

WT = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(WT / "assets" / "blender"))
sys.path.insert(0, str(WT / "tools"))
import common  # noqa: E402
import usp_talon as T  # noqa: E402
import sprite_mask as SM  # noqa: E402

NAME = "assembly-newshu-129"
ROOT = WT
W, H = 48, 56
PX = 1 / 12
# piece, its centre relative to the block centre (screen px), its frame offset from the composed key
PIECES = [("newshu-91", -12, -14, 0), ("newshu-93", 12, -14, 2), ("newshu-129", -12, 14, 38),
          ("newshu-131", 12, 14, 40)]
FADE = [91, 153, 157, 161, 165, 229, 233, 237, 241]
PURPLE_FR = {"newshu-91": 246, "newshu-93": 170, "newshu-129": 284, "newshu-131": 208}
STATE_KEYS = {"grey": [91, 241], "green": [153, 157, 161, 165, 229, 233, 237], "purple": [246]}
SUFFIX = {"grey": "", "green": "-f2", "purple": "-f3"}

# Regions (material slots). The first NPAINT are what shows through the glass.
(GLASS, GREY, ORGAN, ORGAN_HI, CORE, CORE_HI, BUD, BUD_HI, LAMP, LAMP_HI, VEIN, VEIN_HI, RIB,
 GIRDLE, GROOVE, BOLT, SOCKET) = range(17)
RNAMES = ["glass", "grey", "organ", "organhi", "core", "corehi", "bud", "budhi", "lamp", "lamphi", "vein", "veinhi",
          "rib", "girdle", "groove", "bolt", "socket"]
NPAINT = 13
BASE = (GLASS, GREY, ORGAN, ORGAN_HI)
# the machined steel keeps its palette index in every state
FIXED = {GIRDLE: 102, GROOVE: 100, BOLT: 104, SOCKET: 101}
# a blob's bright centre takes its ring's colour on a frame that draws only glare there
PARTNER = {CORE_HI: CORE, BUD_HI: BUD, LAMP_HI: LAMP, VEIN_HI: VEIN}

# Construction constants (sprite px)
HZ = 21.5          # dome height above the girdle plane
GIRDLE_IN = 1.0    # dome radius = plan outline - this (the collar's face is the outline)
# The plan outline: the sprite's D74 inner mask's outline moved this share of the way out to the
# whole sprite's (its ink ring is about 1 px). At 0 (the inner edge) the top view missed the ring's
# 28-33 px per piece (IoU with the sprite 0.92-0.96, tools/review_sheet.py); at 0.55 every piece is
# >= 0.95 against the sprite and still >= 0.95 against the inner mask (tools/sprite_mask.py).
OUTLINE_GROW = 0.55
OUTLINE_ORDER = 6
CAP_RHO = 0.95     # plan triangulation out to here; a polar band below
NT = 144           # angular samples of the band / girdle
SPACING = 0.62     # plan triangulation spacing
HB = 16.5          # bowl depth below the plane
# relief (px) each region presses into the glass with, and the blur of that relief
# the organs are inside the glass: flush under a smooth skin, so the dome's silhouette stays a clean
# sphere (no relief, no lenses)
RELIEF = {}
RELIEF_SIGMA = 1.4
EDGE_SIGMA = 1.0
PAINT_RHO = 0.915  # the organs' paint is gone by here (plan radius fraction) ...
PAINT_FADE = 0.09  # ... fading over this much, so their edges round off before the steep flank
WEB_RHO = 0.905    # the veins stop here
BLOB_SIGMA = 0.7   # edge blur (px) of the small organs (core, bud, lamp): round, not pixel stairs
VEIN_W = 0.5       # half width (px) of a vein line (the sprite draws them 1 px wide)
VEIN_RELAX = 3     # smoothing passes over the veins' pixel stairs
# The glass skin's sheen, one for everything under it (its glints cross the paint unbroken), measured in
# the game's render (4-1 HARVEST t2550, 4K, compare): Specular IOR Level 0.45 (0.5 = F0 4 %) at
# roughness 0.6. The reflection is a thin neutral veil over the whole dome that gives the dark
# palette colours back what the game's tone curve (Neutral's toe) takes off them: the slate renders
# 43 59 73 (median) against the sprite's 48 60 69, and the veins the sprite's olive instead of pure
# green. At 0.2 / 0.3 the dome was charcoal and navy with three milky spots (the sun and the room
# lights, apart); from roughness 0.55 they are one soft glint; at 1.0 / 0.7 the dome is pale silver.
GLASS_SPEC = 0.45
GLASS_ROUGH = 0.6


# --- Sprite ---------------------------------------------------------------------------------------

def load():
    sprites = {n: common.load_sprite(ROOT, n) for n, *_ in PIECES}
    colors = {}
    for s in sprites.values():
        colors.update(s["colors"])
    return sprites, colors


def compose(sprites, key):
    g = -np.ones((H, W), int)
    for n, dx, dy, off in PIECES:
        idx = PURPLE_FR[n] if key == 246 else key + off
        fr = next(f for f in sprites[n]["frames"] if f["index"] == idx)
        c0, r0 = W // 2 + dx - 12, H // 2 + dy - 14
        g[r0:r0 + 28, c0:c0 + 24] = np.array(fr["pixels"])
    return g


def inner_mask(g, colors):
    ci = {int(k): tuple(v) for k, v in colors.items()}
    return np.array(SM.masks(g.tolist(), ci)["inner"]).astype(bool)


def boundary_points(mask):
    """The pixel-edge midpoints of a mask's boundary."""
    ys, xs = np.nonzero(mask)
    pts = []
    for r, c in zip(ys, xs):
        for dc, dr, ex, ey in ((0, -1, c + 0.5, r), (0, 1, c + 0.5, r + 1), (-1, 0, c, r + 0.5), (1, 0, c + 1, r + 0.5)):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < H and 0 <= cc < W) or not mask[rr, cc]:
                pts.append((ex, ey))
    return np.array(pts)


def fit_polar(mask, cx, cy, order):
    """Polar Fourier fit of a mask's pixel-edge boundary about (cx, cy): the coefficients."""
    pts = boundary_points(mask)
    t = np.arctan2(-(pts[:, 1] - cy), pts[:, 0] - cx)
    rad = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
    cols = [np.ones_like(t)]
    for k in range(1, order + 1):
        cols += [np.cos(k * t), np.sin(k * t)]
    return np.linalg.lstsq(np.stack(cols, 1), rad, rcond=None)[0]


def fit_outline(inner, outer, grow=OUTLINE_GROW, order=OUTLINE_ORDER):
    """The plan outline (cx, cy, coeffs): the inner mask's outline about its centroid, moved `grow`
    of the way out to the whole sprite's outline."""
    ys, xs = np.nonzero(inner)
    cx, cy = xs.mean() + 0.5, ys.mean() + 0.5
    ci, co = fit_polar(inner, cx, cy, order), fit_polar(outer, cx, cy, order)
    return float(cx), float(cy), ci + grow * (co - ci)


class Plan:
    def __init__(self, cx, cy, coef):
        self.cx, self.cy, self.coef = cx, cy, coef

    def R(self, t):
        v = self.coef[0]
        for k in range(1, (len(self.coef) - 1) // 2 + 1):
            v += self.coef[2 * k - 1] * math.cos(k * t) + self.coef[2 * k] * math.sin(k * t)
        return v

    def polar(self, c, r):
        dx, dy = c - self.cx, self.cy - r
        t = math.atan2(dy, dx)
        return t, math.hypot(dx, dy)

    def at(self, t, rad):
        return self.cx + rad * math.cos(t), self.cy - rad * math.sin(t)


GREENS = set(range(35, 44)) | set(range(192, 208))  # lit greens (32-34 are the ramp's ink-dark steps)
GLARE = {7, 8, 11, 12, 107} | set(range(133, 142))  # the glass's highlight (lighting, not paint)


class Drawing:
    """What the sprite draws inside the glass, read off its two grey frames (every frame is the same
    drawing with another palette: a class's pixels are one or two indices on each frame).

    Frame 91 (dim): the organs are slate blue (102, lighter 103-105 where they bulge, 98-101 where
    the ball's own shade falls on them), the gaps between them neutral grey (3-6). Frame 241 (the fade's last step) draws what still
    glows in green on that slate: the core's bulb under the highlight, the bud, the lamp, and a
    connected web of 1 px veins over the lower half and up the right side, with the ribs along the
    bottom (those and the lamp stay green on frame 91). The bright crescent inside the lower right
    rim and the white-cyan blob on the core are the glass's sheen: not drawn.

    base   (H, W) GLASS (the mass in the ball's shade, 98-101, and the default round it) / GREY (the
           gaps) / ORGAN / ORGAN_HI, -1 where the pixel says nothing (ink, purple shadow, glare)
    blob   (H, W) CORE(_HI) / BUD(_HI) / LAMP(_HI) or -1
    web    (H, W) VEIN / VEIN_HI / RIB or -1
    src    {region: (H, W) bool}: the pixels a region's palette index is read from on every frame
    """

    def __init__(self, g91, g241, plan):
        cc, rr = np.meshgrid(np.arange(W) + .5, np.arange(H) + .5)
        rho = np.zeros((H, W))
        for r in range(H):
            for c in range(W):
                t, d = plan.polar(c + .5, r + .5)
                rho[r, c] = d / plan.R(t)
        self.rho = rho

        def box(c0, r0, c1, r1):
            return (cc >= c0) & (cc <= c1) & (rr >= r0) & (rr <= r1)

        def ell(x, y, a, b):
            return ((cc - x) / a) ** 2 + ((rr - y) / b) ** 2 <= 1

        base = np.full((H, W), -1, int)
        base[np.isin(g91, [98, 99, 100, 101])] = GLASS
        base[g91 == 102] = ORGAN
        base[np.isin(g91, [103, 104, 105])] = ORGAN_HI
        base[np.isin(g91, [3, 4, 5, 6])] = GREY
        green = np.isin(g241, list(GREENS))
        glare = np.isin(g241, list(range(133, 142)))
        # the rim crescent (lower right, and the lowest arc) is sheen
        crescent = ((rho > 0.86) & (cc > plan.cx) & (rr > plan.cy)) | (rr > 46)
        green &= ~crescent
        lo = green & ((g241 <= 38) | (g241 >= 192))
        hi = green & (g241 >= 42) & (g241 <= 43)
        blob = np.full((H, W), -1, int)
        core = (green | glare) & box(11, 14, 21, 25)
        blob[core] = CORE
        blob[core & (hi | glare)] = CORE_HI
        bud = green & box(19, 8, 27, 16) & ~core
        blob[bud] = BUD
        blob[bud & (g241 >= 41)] = BUD_HI
        lamp = green & ell(36.0, 36.2, 3.6, 3.9)
        blob[lamp] = LAMP
        blob[lamp & ~lo] = LAMP_HI
        web = np.full((H, W), -1, int)
        vein = green & (blob < 0)
        web[vein] = VEIN_HI
        web[vein & lo] = VEIN
        web[vein & np.isin(g91, list(range(32, 44)))] = RIB  # still green on the dim frame
        self.base, self.blob, self.web = base, blob, web
        self.src = {k: (base == k) & (blob < 0) & (web < 0) for k in BASE}
        for k in (CORE, CORE_HI, BUD, BUD_HI, LAMP, LAMP_HI):
            self.src[k] = blob == k
        for k in (VEIN, VEIN_HI, RIB):
            self.src[k] = web == k
        print("drawing:", {RNAMES[k]: int(v.sum()) for k, v in self.src.items()})


def gblur(a, s):
    r = int(math.ceil(3 * s))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2)
    k /= k.sum()
    a = np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(np.pad(v, r, mode="edge"), k, "valid"), 1, a)


class Field:
    """Bilinear sampling of per-pixel arrays at pixel-edge coords (c, r)."""

    def __init__(self, arr):
        self.a = arr

    def __call__(self, c, r):
        x, y = c - 0.5, r - 0.5
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - x0, y - y0
        a = self.a
        h, w = a.shape[:2]

        def g(yy, xx):
            return a[min(max(yy, 0), h - 1), min(max(xx, 0), w - 1)]
        return ((1 - fx) * (1 - fy) * g(y0, x0) + fx * (1 - fy) * g(y0, x0 + 1)
                + (1 - fx) * fy * g(y0 + 1, x0) + fx * fy * g(y0 + 1, x0 + 1))


# --- Colours ----------------------------------------------------------------------------------

def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def region_index(g, sel, colors, drop=0.15):
    """A region's palette index on a frame: the commonest index of its pixels once the glass's glare,
    the ink, and the darkest and brightest `drop` share (lighting) are left out. None when the frame
    draws only glare or ink there."""
    v = [int(x) for x in g[sel] if x >= 0 and int(x) not in GLARE]
    v = [x for x in v if luma(colors[str(x)]) >= SM.INK_LUMA]
    if not v:
        return None
    v.sort(key=lambda i: luma(colors[str(i)]))
    n = len(v)
    cut_ = int(n * drop) if n >= 20 else 0
    return Counter(v[cut_:n - cut_]).most_common(1)[0][0]


def state_colours(sprites, colors, drawing, state):
    """{region: (base index, {piece frame: index})} for one state."""
    keys = STATE_KEYS[state]
    per = {}
    for k in keys:
        g = compose(sprites, k)
        if state == "purple":
            idx = region_index(g, (drawing.rho < 0.86) & (g >= 0), colors)
            per[k] = {reg: idx for reg in range(NPAINT)}
            continue
        per[k] = {reg: region_index(g, drawing.src[reg], colors) for reg in range(NPAINT)}
        for reg, other in PARTNER.items():
            if per[k][reg] is None:
                per[k][reg] = per[k][other]
        for reg in range(NPAINT):
            if per[k][reg] is None:
                per[k][reg] = per[k][GLASS]
        # the dark glass is the slate mass in the ball's own shade (100 / 101, the steps under its
        # 102): lit by the game it is that slate, not the shade (art rule 2). On the lit frames the
        # sprite draws it unlit, as dark as the grey gaps (navy 98-100, then the ramp's dark greens).
        per[k][GLASS] = per[k][ORGAN] if state == "grey" else per[k][GREY]
    out = {}
    for reg in range(NPAINT):
        base = per[keys[0]][reg]
        frames = {}
        for k in keys[1:]:
            if per[k][reg] != base:
                for n, _dx, _dy, off in PIECES:
                    frames[k + off] = per[k][reg]
        out[reg] = (base, frames)
    for reg, idx in FIXED.items():
        out[reg] = (idx, {})
    return out


# --- Geometry ---------------------------------------------------------------------------------

FH = 0.25          # fine region grid cell (px)
MIN_ISLAND = 1.2   # px^2: region islands smaller than this join their neighbours
# domed relief of the glowing organs (lit forms under the glass, not paint): (height, rise width) px
LENS = {}
LIP = (0.28, 0.75)  # the inset lip round them: depth, width (px)


def boxsum(a, r):
    """Sum of a 2D array over (2r+1)^2 windows (edges clamped)."""
    p = np.pad(np.pad(a, r, mode="edge").cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    n = 2 * r + 1
    return p[n:, n:] - p[:-n, n:] - p[n:, :-n] + p[:-n, :-n]


def mode_filter(lab, r, k=NPAINT):
    cnt = np.stack([boxsum((lab == i).astype(float), r) for i in range(k)], -1)
    return np.argmax(cnt, -1)


def drop_islands(lab, min_cells):
    """Every 4-connected region island under min_cells joins its commonest neighbour label."""
    h, w = lab.shape
    lab = lab.copy()
    for _ in range(3):
        seen = np.zeros((h, w), bool)
        changed = False
        for y0 in range(h):
            for x0 in range(w):
                if seen[y0, x0]:
                    continue
                k = lab[y0, x0]
                stack, cells, nb = [(y0, x0)], [], Counter()
                seen[y0, x0] = True
                while stack:
                    y, x = stack.pop()
                    cells.append((y, x))
                    for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                        if 0 <= yy < h and 0 <= xx < w:
                            if lab[yy, xx] == k:
                                if not seen[yy, xx]:
                                    seen[yy, xx] = True
                                    stack.append((yy, xx))
                            else:
                                nb[lab[yy, xx]] += 1
                if len(cells) < min_cells and nb:
                    nk = nb.most_common(1)[0][0]
                    for y, x in cells:
                        lab[y, x] = nk
                    changed = True
        if not changed:
            break
    return lab


def signed_distance(mask, h):
    """Distance (px) of every fine cell to the mask's boundary: + inside, - outside."""
    ys, xs = np.nonzero(mask)
    edge = np.zeros_like(mask)
    edge[:-1] |= mask[:-1] != mask[1:]
    edge[1:] |= mask[:-1] != mask[1:]
    edge[:, :-1] |= mask[:, :-1] != mask[:, 1:]
    edge[:, 1:] |= mask[:, :-1] != mask[:, 1:]
    by, bx = np.nonzero(edge)
    bpts = np.stack([bx, by], 1).astype(float) * h
    gy, gx = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    q = np.stack([gx.ravel(), gy.ravel()], 1).astype(float) * h
    d = np.empty(len(q))
    for i in range(0, len(q), 4000):
        d[i:i + 4000] = np.sqrt(((q[i:i + 4000, None, :] - bpts[None]) ** 2).sum(-1)).min(1)
    d = d.reshape(mask.shape) - h / 2
    return np.where(mask, np.maximum(d, 0), -np.maximum(d, 0))


class FineField:
    """Bilinear sampling of a fine-grid array (cell FH) at plan coords (c, r) px."""

    def __init__(self, arr):
        self.a = arr

    def __call__(self, c, r):
        x, y = c / FH - 0.5, r / FH - 0.5
        x0, y0 = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - x0, y - y0
        a = self.a
        h, w = a.shape

        def g(yy, xx):
            return a[min(max(yy, 0), h - 1), min(max(xx, 0), w - 1)]
        return ((1 - fx) * (1 - fy) * g(y0, x0) + fx * (1 - fy) * g(y0, x0 + 1)
                + (1 - fx) * fy * g(y0 + 1, x0) + fx * fy * g(y0 + 1, x0 + 1))


def fine_sample(a):
    """A per-pixel array (H, W[, n]) sampled bilinearly at the FH cell centres."""
    nx, ny = int(W / FH), int(H / FH)
    X, Y = np.meshgrid((np.arange(nx) + 0.5) * FH - 0.5, (np.arange(ny) + 0.5) * FH - 0.5)
    x0 = np.clip(np.floor(X).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(Y).astype(int), 0, H - 1)
    x1 = np.clip(x0 + 1, 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1)
    fx = np.clip(X - np.floor(X), 0, 1)
    fy = np.clip(Y - np.floor(Y), 0, 1)
    if a.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    return (1 - fx) * (1 - fy) * a[y0, x0] + fx * (1 - fy) * a[y0, x1] + (1 - fx) * fy * a[y1, x0] + fx * fy * a[y1, x1]


def web_graph(web):
    """The veins as a graph: a node per vein pixel (its centre), a segment between 4-neighbours and
    between diagonal neighbours no 4-path joins, so the web is connected wherever the sprite's
    pixels touch. The pixel stairs are relaxed into smooth lines (nodes with two neighbours move
    toward them; ends and junctions stay). Returns (positions px, segments, each node's region);
    pixels touching no other vein pixel are left out (specks, not lines)."""
    ys, xs = np.nonzero(web >= 0)
    ids = {(int(r), int(c)): i for i, (r, c) in enumerate(zip(ys, xs))}
    segs = []
    for (r, c), i in ids.items():
        for dr, dc in ((0, 1), (1, 0)):
            j = ids.get((r + dr, c + dc))
            if j is not None:
                segs.append((i, j))
        for dr, dc in ((1, 1), (1, -1)):
            j = ids.get((r + dr, c + dc))
            if j is not None and (r + dr, c) not in ids and (r, c + dc) not in ids:
                segs.append((i, j))
    nbr = [[] for _ in ids]
    for i, j in segs:
        nbr[i].append(j)
        nbr[j].append(i)
    pos = np.array([(c + .5, r + .5) for r, c in zip(ys, xs)], float).reshape(-1, 2)
    for _ in range(VEIN_RELAX):
        new = pos.copy()
        for i, n in enumerate(nbr):
            if len(n) == 2:
                new[i] = 0.5 * pos[i] + 0.25 * (pos[n[0]] + pos[n[1]])
        pos = new
    reg = np.array([int(web[r, c]) for r, c in zip(ys, xs)], int)
    lone = sum(1 for n in nbr if not n)
    print(f"web: {len(pos)} vein px, {len(segs)} segments, {lone} lone px left out")
    return pos, segs, reg


class Pod:
    def __init__(self, plan, drawing):
        self.plan = plan
        self.drawing = drawing
        # the pixels that say nothing (ink, the purple shadow, glare) count faintly as the default
        # (GLASS: the mass in shade), so the organs' and gaps' edges stand where the sprite's
        # pixels end and the default takes the rest, out to the rim
        onehot = np.stack([(drawing.base == k).astype(float) for k in BASE], -1)
        onehot[..., 0] += 0.4 * (drawing.base < 0)
        self.soft = Field(np.stack([gblur(onehot[..., k], EDGE_SIGMA) for k in range(len(BASE))], -1))
        rel = np.zeros((H, W))
        for k, a in RELIEF.items():
            rel += a * (drawing.base == k)
        self.relief = Field(gblur(rel, RELIEF_SIGMA))
        self.flab = self.fine_labels()
        # the core and bud: domed lenses rising from an inset lip, on the cleaned regions
        lens = np.zeros(self.flab.shape)
        lip = np.zeros(self.flab.shape)
        for k, (a, wd) in LENS.items():
            sd = signed_distance(self.flab == k, FH)
            u = np.clip(sd / wd, 0, 1)
            lens += np.where(sd > 0, a * np.sqrt(1 - (1 - u) ** 2), 0)
            v = np.clip(-sd / LIP[1], 0, 1)
            lip = np.minimum(lip, np.where(sd < 0, -LIP[0] * np.sin(math.pi * v), 0))
        lens = np.where(lens > 0, lens, lip)  # the lip only off the lenses
        self.lens = FineField(gblur(lens, 0.8))

    def fine_labels(self):
        """The region of every FH cell. Glass and organs: argmax of the blurred class fields, then
        cleaned (a majority filter shaves peninsulas and hairs under ~0.6 px, islands under
        MIN_ISLAND px^2 join their neighbours), so every region edge is a clean curve with no comb
        of spikes. Over them the small organs (core, bud, lamp: their pixels blurred BLOB_SIGMA and
        cut at half, the bright centre where its own field leads), then the vein web (web_graph:
        every cell within VEIN_W of a segment, and the inside of any 2 x 2 block of vein pixels)."""
        nx, ny = int(W / FH), int(H / FH)
        d = self.drawing
        v = fine_sample(self.soft.a)
        X, Y = np.meshgrid((np.arange(nx) + 0.5) * FH, (np.arange(ny) + 0.5) * FH)
        # the organs fade out before the dome gets steep: a region's edge there rounds off on its
        # own field instead of running into the cap ring, so no edge is cut along a latitude line
        # or stepped on the steep flank
        dx, dy = X - self.plan.cx, self.plan.cy - Y
        t = np.arctan2(dy, dx)
        R = np.full(t.shape, self.plan.coef[0])
        for k in range(1, (len(self.plan.coef) - 1) // 2 + 1):
            R += self.plan.coef[2 * k - 1] * np.cos(k * t) + self.plan.coef[2 * k] * np.sin(k * t)
        rho = np.hypot(dx, dy) / (R - GIRDLE_IN)
        fade = np.clip((PAINT_RHO - rho) / PAINT_FADE, 0, 1)[..., None]
        keep = np.array([0.0, 1.0, 1.0, 1.0])
        v = v * (1 - keep * (1 - fade))
        lab = np.array(BASE)[np.argmax(v, -1)]
        before = lab.copy()
        lab = mode_filter(lab, 2)
        lab = drop_islands(lab, int(MIN_ISLAND / FH ** 2))
        lab = mode_filter(lab, 1)
        lab = drop_islands(lab, int(MIN_ISLAND / FH ** 2))
        print(f"fine labels: {int((lab != before).sum())} of {lab.size} cells cleaned")
        for ring, centre in ((CORE, CORE_HI), (BUD, BUD_HI), (LAMP, LAMP_HI)):
            whole = fine_sample(gblur(((d.blob == ring) | (d.blob == centre)).astype(float), BLOB_SIGMA))
            inner = fine_sample(gblur((d.blob == centre).astype(float), BLOB_SIGMA))
            lab[whole > 0.5] = ring
            lab[(whole > 0.5) & (inner > whole - inner)] = centre
        pos, segs, reg = web_graph(d.web)
        best = np.full(X.shape, 1e9)
        who = np.zeros(X.shape, int)
        for i, j in segs:
            a, b = pos[i], pos[j]
            ab = b - a
            tt = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / max(float(ab @ ab), 1e-9), 0, 1)
            dist = np.hypot(X - a[0] - tt * ab[0], Y - a[1] - tt * ab[1])
            upd = dist < best
            best[upd] = dist[upd]
            who[upd] = np.where(tt < 0.5, i, j)[upd]
        node = d.web >= 0
        block = np.zeros((H, W), bool)  # block[r, c]: the four pixels round the corner (c + 1, r + 1)
        block[:-1, :-1] = node[:-1, :-1] & node[1:, :-1] & node[:-1, 1:] & node[1:, 1:]
        bc = np.clip(np.floor(X - 0.5).astype(int), 0, W - 1)
        br = np.clip(np.floor(Y - 0.5).astype(int), 0, H - 1)
        line = ((best < VEIN_W) | block[br, bc]) & (rho < WEB_RHO) & (best < 1.5)
        lab[line] = reg[who[line]]
        return drop_islands(lab, 12)  # no speck under 0.75 px^2 (a vein's end cut off by WEB_RHO)

    def flabel(self, c, r):
        h, w = self.flab.shape
        return int(self.flab[min(max(int(r / FH), 0), h - 1), min(max(int(c / FH), 0), w - 1)])

    def Rd(self, t):
        return self.plan.R(t) - GIRDLE_IN

    def rho(self, c, r):
        t, d = self.plan.polar(c, r)
        return t, d / self.Rd(t)

    def dome(self, c, r, relief=True, lift=0.0):
        """3D point (Blender units) on the dome above plan point (c, r) and its normal."""
        t, rho = self.rho(c, r)
        rho = min(rho, 1.0)
        z = HZ * math.sqrt(max(1 - rho * rho, 0.0))
        Rd = self.Rd(t)
        dx, dy = c - self.plan.cx, self.plan.cy - r
        n = Vector((dx / Rd ** 2, dy / Rd ** 2, z / HZ ** 2)).normalized()
        p = Vector(((c - 24), (28 - r), z))
        h = lift
        if relief:
            h += (self.relief(c, r) + self.lens(c, r)) * max(0.0, min(1.0, (0.9 - rho) / 0.12))
        return (p + n * h) * PX, n

    def label(self, c, r):
        return self.flabel(c, r), None


def region_contours(pod, h=0.25, smooth=4, step=0.35):
    """The region boundaries as smooth plan polylines (px): the argmax of the smoothed region fields
    on a fine grid, its cell edges chained between junctions, relaxed and resampled. They go into
    the triangulation as constraint edges so the paint follows round curves, not triangle steps."""
    h = FH
    nx, ny = int(W / h), int(H / h)
    xs = (np.arange(nx) + 0.5) * h
    ys = (np.arange(ny) + 0.5) * h
    lab = pod.flab
    inside = np.zeros((ny, nx), bool)
    for r in range(ny):
        for c in range(nx):
            t, rho = pod.rho(xs[c], ys[r])
            inside[r, c] = rho < CAP_RHO - 0.03
    adj = {}

    def link(p, q):
        adj.setdefault(p, set()).add(q)
        adj.setdefault(q, set()).add(p)
    for r in range(ny):
        for c in range(nx):
            if not inside[r, c]:
                continue
            if c + 1 < nx and inside[r, c + 1] and lab[r, c] != lab[r, c + 1]:
                link((c + 1, r), (c + 1, r + 1))
            if r + 1 < ny and inside[r + 1, c] and lab[r, c] != lab[r + 1, c]:
                link((c, r + 1), (c + 1, r + 1))
    seen = set()
    chains = []
    nodes = [p for p, n in adj.items() if len(n) != 2]
    def walk(p, q):
        ch = [p, q]
        seen.add(frozenset((p, q)))
        while len(adj[q]) == 2:
            nxt = next(n for n in adj[q] if frozenset((q, n)) not in seen) if any(
                frozenset((q, n)) not in seen for n in adj[q]) else None
            if nxt is None:
                break
            seen.add(frozenset((q, nxt)))
            ch.append(nxt)
            q = nxt
        return ch
    for p in nodes:
        for q in adj[p]:
            if frozenset((p, q)) not in seen:
                chains.append(walk(p, q))
    for p in adj:  # closed loops
        for q in adj[p]:
            if frozenset((p, q)) not in seen:
                chains.append(walk(p, q))
    out = []
    for ch in chains:
        P = [np.array((c * h, r * h)) for c, r in ch]
        closed = len(P) > 2 and ch[0] == ch[-1]
        for _ in range(smooth):
            Q = [P[0]] + [(P[i - 1] + 2 * P[i] + P[i + 1]) / 4 for i in range(1, len(P) - 1)] + [P[-1]]
            if closed:
                Q[0] = Q[-1] = (P[-2] + 2 * P[0] + P[1]) / 4
            P = Q
        L = [0.0]
        for i in range(1, len(P)):
            L.append(L[-1] + float(np.linalg.norm(P[i] - P[i - 1])))
        # every chain stays, however short: a vein crossing a region edge makes junctions under a
        # pixel apart, and a dropped chain between them opens the vein's patch to the glass round it
        # (label_faces then paints the whole vein glass)
        n = max(2, int(round(L[-1] / step)) + 1)
        res = []
        k = 0
        for i in range(n):
            d = L[-1] * i / (n - 1)
            while k < len(L) - 2 and L[k + 1] < d:
                k += 1
            t = (d - L[k]) / max(L[k + 1] - L[k], 1e-9)
            q = P[k] * (1 - t) + P[k + 1] * t
            res.append((float(q[0]), float(q[1])))
        if closed:
            res[-1] = res[0]
            res = res[:-1] + [res[0]]
        out.append(res)
    return out


def label_faces(pod, verts2, faces, res, nt):
    """Each face's region: the faces between the contour constraint edges form patches, and a patch
    takes the (area-weighted) commonest fine-grid label of its faces, so every region edge runs
    exactly along a smooth contour (no comb of triangles on the wrong side). A patch whose faces
    disagree a lot (a leak round a contour's end) keeps its per-face labels."""
    cons = set()
    for ei, e in enumerate(res[1]):
        if res[4][ei]:
            cons.add(frozenset(e))
    owner = {}
    for fi, f in enumerate(faces):
        for i in range(len(f)):
            owner.setdefault(frozenset((f[i], f[(i + 1) % len(f)])), []).append(fi)
    per = []
    area = []
    for f in faces:
        c = sum((verts2[i] for i in f), Vector((0.0, 0.0))) / len(f)
        per.append(pod.flabel(c.x, c.y))
        a, b, cc = verts2[f[0]], verts2[f[1]], verts2[f[2]]
        area.append(abs((b - a).cross(cc - a)) / 2)
    labels = list(per)
    seen = [False] * len(faces)
    mixed = 0
    for f0 in range(len(faces)):
        if seen[f0]:
            continue
        stack, patch = [f0], []
        seen[f0] = True
        while stack:
            fi = stack.pop()
            patch.append(fi)
            f = faces[fi]
            for i in range(len(f)):
                e = frozenset((f[i], f[(i + 1) % len(f)]))
                if e in cons:
                    continue
                for g in owner[e]:
                    if not seen[g]:
                        seen[g] = True
                        stack.append(g)
        hist = Counter()
        for fi in patch:
            hist[per[fi]] += area[fi]
        k, a = hist.most_common(1)[0]
        if a >= 0.8 * sum(hist.values()):
            for fi in patch:
                labels[fi] = k
        else:
            mixed += 1
    # no speck of paint: a group of same-region faces under 0.3 px^2 takes the region round it
    done = [False] * len(faces)
    specks = 0
    for f0 in range(len(faces)):
        if done[f0]:
            continue
        stack, comp, nb = [f0], [], Counter()
        done[f0] = True
        while stack:
            fi = stack.pop()
            comp.append(fi)
            f = faces[fi]
            for i in range(len(f)):
                for g in owner[frozenset((f[i], f[(i + 1) % len(f)]))]:
                    if labels[g] != labels[f0]:
                        nb[labels[g]] += 1
                    elif not done[g]:
                        done[g] = True
                        stack.append(g)
        if nb and sum(area[fi] for fi in comp) < 0.3:
            k = nb.most_common(1)[0][0]
            for fi in comp:
                labels[fi] = k
            specks += 1
    print(f"cap: {specks} specks of paint under 0.3 px^2 joined their surroundings")
    off = sum(a for a, k, q in zip(area, labels, per) if k != q)
    print(f"cap: {mixed} mixed patches kept per-face labels; {off:.1f} of {sum(area):.0f} px^2 differ from the grid")
    return labels


def cap_mesh(bm, pod, painted, relief):
    """The dome inside CAP_RHO: a delaunay triangulation of plan points, painted by region with
    boundaries snapped onto the smoothed region fields; then the polar band down to the girdle."""
    plan = pod.plan
    ts = [2 * math.pi * i / NT for i in range(NT)]
    ring = [plan.at(t, CAP_RHO * pod.Rd(t)) for t in ts]
    pts = list(ring)
    edges = [(i, (i + 1) % NT) for i in range(NT)]
    chains = region_contours(pod) if painted else []
    cpts = []
    ends = Counter()
    for ch in chains:
        ends[(round(ch[0][0], 4), round(ch[0][1], 4))] += 1
        ends[(round(ch[-1][0], 4), round(ch[-1][1], 4))] += 1
    for ch in chains:
        k0 = len(pts)
        pts.extend(ch)
        edges.extend((k0 + i, k0 + i + 1) for i in range(len(ch) - 1))
        cpts.extend(ch)
        # a contour that stops short of the cap ring is tied to the nearest ring vertex, so the
        # regions it parts stay closed (no region leaks round its end)
        for ki, q in ((k0, ch[0]), (k0 + len(ch) - 1, ch[-1])):
            if ch[0] == ch[-1] or ends[(round(q[0], 4), round(q[1], 4))] != 1:
                continue
            if pod.rho(*q)[1] > CAP_RHO - 0.12:
                ri = min(range(NT), key=lambda i: (ring[i][0] - q[0]) ** 2 + (ring[i][1] - q[1]) ** 2)
                edges.append((ki, ri))
    # hex fill, kept clear of the ring and of the contour points (no slivers)
    grid = {}
    for q in cpts:
        grid.setdefault((int(q[0] // 0.5), int(q[1] // 0.5)), []).append(q)

    def near_contour(x, y, d=0.3):
        gx, gy = int(x // 0.5), int(y // 0.5)
        for ax in (gx - 1, gx, gx + 1):
            for ay in (gy - 1, gy, gy + 1):
                for q in grid.get((ax, ay), ()):
                    if (q[0] - x) ** 2 + (q[1] - y) ** 2 < d * d:
                        return True
        return False
    for s, fine in ((SPACING, False), (0.4, True)):
        dy = s * math.sqrt(3) / 2
        j = 0
        y = plan.cy - 26
        while y < plan.cy + 26:
            x = plan.cx - 26 + (s / 2 if j % 2 else 0)
            while x < plan.cx + 26:
                t, rho = pod.rho(x, y)
                if rho * pod.Rd(t) < CAP_RHO * pod.Rd(t) - 0.45 and not near_contour(x, y, 0.25 if fine else 0.3):
                    # the lenses get a finer fill so their domes are round
                    if fine == (relief and pod.flabel(x, y) in LENS):
                        pts.append((x, y))
                x += s
            y += dy
            j += 1
    res = geometry.delaunay_2d_cdt([Vector(p) for p in pts], edges, [list(range(NT))], 1, 1e-5)
    verts2 = [Vector((v.x, v.y)) for v in res[0]]
    faces = [list(f) for f in res[2]]
    inv = {}
    for oi, origs in enumerate(res[3]):
        for ii in origs:
            inv[ii] = oi
    ring_ids = [inv[i] for i in range(NT)]
    labels = [GLASS] * len(faces)
    if painted:
        labels = label_faces(pod, verts2, faces, res, NT)
    bv = [bm.verts.new(pod.dome(p.x, p.y, relief)[0]) for p in verts2]
    for fi, f in enumerate(faces):
        try:
            face = bm.faces.new([bv[i] for i in f])
        except ValueError:
            print("cap: skipped a duplicate face")
            continue
        face.material_index = labels[fi]
    # polar band: the cap ring (vertices 0..NT-1 of the triangulation) down to the girdle plane
    rhos = [CAP_RHO, 0.965, 0.98, 0.99, 1.0]
    rings = [[bv[i] for i in ring_ids]]
    for rh in rhos[1:]:
        ringv = []
        for t in ts:
            c, r = plan.at(t, rh * pod.Rd(t))
            ringv.append(bm.verts.new(pod.dome(c, r, False)[0]))
        rings.append(ringv)
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for i in range(NT):
            i2 = (i + 1) % NT
            face = bm.faces.new((r0[i], r1[i], r1[i2], r0[i2]))
            # the steep band is clear glass: the paint stops on the cap ring (a smooth constraint
            # curve), never in per-quad steps
            face.material_index = GLASS
    return rings[-1]


def seam_angle(plan, d, axis, val, t0):
    """The angle near t0 where the outline offset by d crosses x = val (axis 0) or y = val (axis 1)."""
    def f(t):
        return plan.at(t, plan.R(t) + d)[axis] - val
    a, b = t0 - 0.3, t0 + 0.3
    fa = f(a)
    for _ in range(60):
        m = (a + b) / 2
        fm = f(m)
        if (fm < 0) == (fa < 0):
            a, fa = m, fm
        else:
            b = m
    return (a + b) / 2


def girdle(bm, pod):
    """The steel collar: a chamfered section swept round the plan outline (outer face = R(t)) with a
    modelled panel-line groove, and 16 hex bolt heads 0.25 px proud. Its inner edge reaches 0.25 px
    past the glass's inset (GIRDLE_IN), so the glass never shows through the outer face."""
    plan = pod.plan
    top, bot, gin = 1.0, -2.4, GIRDLE_IN + 0.25
    # (radial offset from the outline, z) px, inner top edge round the outside to the inner bottom edge
    sec = [(-gin, top), (-gin, top + 0.3), (-0.4, top + 0.3), (0.0, top - 0.1), (0.0, -0.45), (-0.3, -0.55),
           (-0.3, -0.85), (0.0, -0.95), (0.0, bot + 0.35), (-0.35, bot), (-gin, bot), (-gin, bot + 0.2)]
    mats = [GIRDLE, GIRDLE, GIRDLE, GIRDLE, GROOVE, GROOVE, GROOVE, GIRDLE, GIRDLE, GIRDLE, GIRDLE, GIRDLE]
    ts = [2 * math.pi * i / NT for i in range(NT)]
    # the piece cuts (x = 24 and y = 28 px) run through a section ring: the ring nearest each cut
    # puts every section vertex on the cut plane, so the cut makes no new vertices, the halves meet
    # vertex for vertex and the collar runs unbroken across the seam
    seams = {}
    for t0, axis, val in ((math.pi / 2, 0, 24.0), (3 * math.pi / 2, 0, 24.0), (0.0, 1, 28.0), (math.pi, 1, 28.0)):
        i = int(round(t0 / (2 * math.pi) * NT)) % NT
        seams[i] = [seam_angle(plan, d, axis, val, t0) for d, _z in sec]
    rings = []
    for i, t in enumerate(ts):
        ring = []
        for k, (d, z) in enumerate(sec):
            tt = seams[i][k] if i in seams else t
            c, r = plan.at(tt, plan.R(tt) + d)
            ring.append(bm.verts.new(Vector((c - 24, 28 - r, z)) * PX))
        rings.append(ring)
    n = len(sec)
    faces = []
    for i in range(NT):
        a, b = rings[i], rings[(i + 1) % NT]
        for k in range(n):
            k2 = (k + 1) % n
            f = bm.faces.new((a[k], b[k], b[k2], a[k2]))
            f.material_index = mats[k]
            faces.append(f)
    # the winding must put the outer face's normal outward
    f0 = faces[4]
    cen = f0.calc_center_median()
    out = Vector((cen.x - (plan.cx - 24) * PX, cen.y - (28 - plan.cy) * PX, 0))
    if f0.normal.dot(out) < 0:
        bmesh.ops.reverse_faces(bm, faces=faces)
    # hex bolt heads on the band below the groove
    for j in range(16):
        t = 2 * math.pi * (j + 0.5) / 16
        R = plan.R(t)
        c, r = plan.at(t, R)
        base = Vector((c - 24, 28 - r, -1.65)) * PX
        outv = Vector((math.cos(t), math.sin(t), 0))
        up = Vector((0, 0, 1))
        side = up.cross(outv)
        inner, outer = [], []
        for k in range(6):
            a = 2 * math.pi * k / 6 + math.pi / 6
            off = (side * math.cos(a) + up * math.sin(a)) * 0.42 * PX
            inner.append(bm.verts.new(base + off - outv * 0.05 * PX))
            outer.append(bm.verts.new(base + off * 0.75 + outv * 0.25 * PX))
        for k in range(6):
            k2 = (k + 1) % 6
            bm.faces.new((inner[k], inner[k2], outer[k2], outer[k])).material_index = BOLT
        bm.faces.new(outer).material_index = BOLT


def bowl(bm, pod):
    """Lower bowl and socket boss: a plain closed shape (seen only from below)."""
    plan = pod.plan
    # radius fraction of Rd vs z (px), pchip; top tucked inside the collar
    zs = [-2.3, -5.0, -9.0, -13.0, -15.5, -16.5]
    fr = [0.995, 0.97, 0.86, 0.64, 0.44, 0.40]
    prof = T.pchip([-z for z in zs], fr)
    ts = [2 * math.pi * i / 96 for i in range(96)]
    levels = [-2.3, -3.5, -5.0, -7.0, -9.0, -11.0, -13.0, -14.6, -15.8, -16.5]
    rings = []
    for z in levels:
        f = prof(-z)
        ring = []
        for t in ts:
            c, r = plan.at(t, f * pod.Rd(t))
            ring.append(bm.verts.new(Vector((c - 24, 28 - r, z)) * PX))
        rings.append(ring)
    # socket boss: a short cylinder with a chamfer
    sock_r = 0.40 * 21.0
    cxw, cyw = plan.cx - 24, 28 - plan.cy
    for z, rr in ((-17.6, sock_r), (-18.4, sock_r - 0.6)):
        rings.append([bm.verts.new(Vector((cxw + rr * math.cos(t), cyw + rr * math.sin(t), z)) * PX) for t in ts])
    for k, (r0, r1) in enumerate(zip(rings, rings[1:])):
        mat = GLASS if k < len(levels) - 1 else SOCKET
        for i in range(96):
            i2 = (i + 1) % 96
            bm.faces.new((r0[i], r0[i2], r1[i2], r1[i])).material_index = mat
    bm.faces.new(rings[-1][::-1]).material_index = SOCKET
    # the top ring is closed by a hidden disc (inside the collar) so the bowl is watertight
    bm.faces.new(rings[0]).material_index = GLASS


def close_dome(bm, base_ring):
    bm.faces.new(base_ring[::-1]).material_index = GLASS


def build(state, pod, mats, coll):
    bm = bmesh.new()
    painted = state != "purple"
    base = cap_mesh(bm, pod, painted, relief=painted)
    close_dome(bm, base)
    girdle(bm, pod)
    bowl(bm, pod)
    # sliver triangles (three contour points in a line, where a vein's edge meets a region's): their
    # normals are noise, the 40 degree sharp-edge pass then shades them flat and each is a dark
    # pixel on the glass
    thin = sum(1 for f in bm.faces if f.calc_area() < 1e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=0.002, edges=bm.edges[:])
    left = sum(1 for f in bm.faces if f.calc_area() < 1e-6)
    print(f"{state}: {thin} sliver faces dissolved, {left} left")
    obj = common.mesh_object(f"{NAME}-{state}", bm, mats, coll, smooth=True)
    obj.data.set_sharp_from_angle(angle=math.radians(40))
    return obj


# --- Pieces -------------------------------------------------------------------------------------

def copy_shading(whole, piece, x0, y0):
    """Give a piece the whole pod's corner normals (so the cuts leave no seam); cut caps flat.
    A corner takes the whole's normal at the coincident vertex of a face with the same facing; a vertex
    made by the cut takes it from the nearest face of that facing (never from the glass under the
    collar or the collar under a bolt, which a plain nearest-face lookup would pick)."""
    wm = whole.data
    wm.calc_normals_split() if hasattr(wm, "calc_normals_split") else None
    cn = wm.corner_normals
    G = 1000.0
    cells = {}
    for poly in wm.polygons:
        for li in poly.loop_indices:
            co = wm.vertices[wm.loops[li].vertex_index].co
            key = (round(co.x * G), round(co.y * G), round(co.z * G))
            cells.setdefault(key, []).append((co.copy(), Vector(poly.normal), Vector(cn[li].vector)))
    bm = bmesh.new()
    bm.from_mesh(wm)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    corner = {}
    for poly in wm.polygons:
        corner[poly.index] = {wm.loops[li].vertex_index: Vector(cn[li].vector) for li in poly.loop_indices}
    me = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    normals = []
    for poly in me.polygons:
        vs = [me.vertices[i].co for i in poly.vertices]
        cap = False
        for axis, lim in ((0, hw), (1, hh)):
            for sg in (-1, 1):
                if all(abs(v[axis] - sg * lim) < eps for v in vs):
                    cap = True
        pn = Vector(poly.normal)
        # a sliver the cut left along a seam: its own normal is noise (a dark pixel on the glass),
        # so its corners take the whole's shading whatever it faces
        thin = poly.area < 2e-7
        for li in poly.loop_indices:
            if cap:
                normals.append(tuple(pn))
                continue
            co = me.vertices[me.loops[li].vertex_index].co + Vector((x0, y0, 0))
            kx, ky, kz = round(co.x * G), round(co.y * G), round(co.z * G)
            best, bd = None, 0.0
            for ax in (kx - 1, kx, kx + 1):
                for ay in (ky - 1, ky, ky + 1):
                    for az in (kz - 1, kz, kz + 1):
                        for wco, fn, cnv in cells.get((ax, ay, az), ()):
                            if (wco - co).length < 3e-5 and (fn.dot(pn) > bd or (thin and best is None and fn.z > 0)):
                                best, bd = cnv, max(fn.dot(pn), 0.6 if thin else 0.0)
            if best is not None and bd > 0.5:
                normals.append(tuple(best.normalized()))
                continue
            # a vertex made by the cut lies on a face of the whole of the same material and facing
            # (never the glass under a collar chamfer, whose facing can be close)
            fi = None
            bestd = 1e9
            for _loc, _no, j, dd in tree.find_nearest_range(co, 0.004):
                f = bm.faces[j]
                if (f.material_index == poly.material_index and (thin or Vector(f.normal).dot(pn) > 0.7)
                        and dd < bestd):
                    fi, bestd = j, dd
            if fi is None:
                _loc, _no, fi, _d = tree.find_nearest(co)
            if fi is None or (not thin and Vector(bm.faces[fi].normal).dot(pn) < 0.7):
                normals.append(tuple(pn))
                continue
            f = bm.faces[fi]
            w = interpolate.poly_3d_calc([v.co for v in f.verts], co)
            nn = Vector()
            for wt, v in zip(w, f.verts):
                nn += wt * corner[fi][v.index]
            normals.append(tuple(nn.normalized()) if nn.length > 1e-6 else tuple(pn))
    me.normals_split_custom_set(normals)
    me.update()
    bm.free()


def tuck_shell(shell, whole, depth=0.008):
    """Hold the outline shell under the pod's skin: every shell vertex that stands outside the
    nearest face of `whole`, or less than `depth` (units; 0.1 px) under it, goes to that depth.
    The voxel shell otherwise stands a hair outside the dome at its vertices: black pockmarks all
    over the glass wherever the shell is drawn with the model (the review renders). One even
    offset, no deeper pushes: a shell dented further along the corner where the dome meets the
    collar drew scratches of ink across the flank in the game."""
    bm = bmesh.new()
    bm.from_mesh(whole.data)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    moved = 0
    for v in shell.data.vertices:
        loc, no, _i, _d = tree.find_nearest(v.co)
        if loc is not None and (v.co - loc).dot(no) > -depth:
            v.co = loc - no * depth
            moved += 1
    shell.data.update()
    bm.free()
    print(f"shell: {moved} of {len(shell.data.vertices)} vertices tucked under the skin")


def split_open(obj, layout, coll):
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx / 12, -cy / 12
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                       ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(f"{name}_outline")
        bm.to_mesh(me)
        bm.free()
        for mt in obj.data.materials:
            me.materials.append(mt)
        sh = bpy.data.objects.new(f"{name}_outline", me)
        coll.objects.link(sh)
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[name] = sh
    return out


def materials(state, cols, palette):
    mats = []
    # lit: the core and bud glow, the veins, ribs and lamp a little less
    emis = {"grey": {},
            "green": {CORE: 1.0, CORE_HI: 1.0, BUD: 1.0, BUD_HI: 1.0, VEIN: 0.8, VEIN_HI: 0.8, RIB: 0.8, LAMP: 0.8,
                      LAMP_HI: 0.8},
            "purple": {}}[state]
    for reg in range(len(RNAMES)):
        idx, frames = cols[reg]
        if reg >= NPAINT:
            met, rough = 0.6, 0.42
        else:
            met, rough = 0.05, GLASS_ROUGH
        tag = f"nsu129A_{state}_{RNAMES[reg]}"
        mt = common.palette_material(palette, idx, tag, metallic=met, roughness=rough,
                                     emission_strength=emis.get(reg, 0.0), frames=frames or None)
        if state != "purple" and reg < NPAINT:
            # the glass skin's F0 (D176: through Specular IOR Level), see GLASS_SPEC
            bsdf = next(n for n in mt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = GLASS_SPEC
        mats.append(mt)
    return mats


def classify_piece_frames(sprites, name, state):
    _n, _dx, _dy, off = next(p for p in PIECES if p[0] == name)
    if state == "purple":
        return [PURPLE_FR[name]]
    return [k + off for k in STATE_KEYS[state]]


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sprites, colors = load()
    palette = {"name": NAME, "colors": colors}
    g91, g241 = compose(sprites, 91), compose(sprites, 241)
    plan = Plan(*fit_outline(inner_mask(g91, colors), g91 >= 0))
    drawing = Drawing(g91, g241, plan)
    pod = Pod(plan, drawing)
    report = {"plan": {"cx": plan.cx, "cy": plan.cy, "coef": [float(c) for c in plan.coef]}, "states": {}}
    layout = [(n, dx, dy) for n, dx, dy, _ in PIECES]
    export, pieces_out = [], {}
    for si, state in enumerate(("grey", "green", "purple")):
        coll = common.reset_collection(f"{NAME}-A-{state}")
        cols = state_colours(sprites, colors, drawing, state)
        report["states"][state] = {RNAMES[k]: [v[0], {str(a): b for a, b in v[1].items()}] for k, v in cols.items()}
        mats = materials(state, cols, palette)
        whole = build(state, pod, mats, coll)
        tris = sum(len(p.vertices) - 2 for p in whole.data.polygons)
        print(f"{state}: {tris} triangles")
        report["states"][state]["_tris"] = tris
        shell = common.outline_shell(whole, coll, voxel=0.025, faces=5000, smooth=8, inside=0.006)
        tuck_shell(shell, whole)
        lay = [(n + SUFFIX[state], dx, dy) for n, dx, dy in layout]
        pieces = common.split_assembly(whole, lay, coll)
        shells = split_open(shell, lay, coll)
        for name, dx, dy in lay:
            copy_shading(whole, pieces[name], dx / 12, -dy / 12)
            pieces_out[name] = (pieces[name], shells[name], state)
        whole.hide_render = shell.hide_render = True
        for name, dx, dy in lay:
            for o in (pieces[name], shells[name]):
                o["tyrian_state"] = state
                export.append((o, dx / 12 + 5 * si, -dy / 12))
    if "--report" in argv:
        Path(argv[argv.index("--report") + 1]).write_text(json.dumps(report, indent=1))
    if "--review" not in argv:
        for name, (p, sh, state) in pieces_out.items():
            base = name[:-3] if state != "grey" else name
            ref = sprites[base]["sprites"][0]
            subset = [{"sheet": ref["sheet"], "size": ref["size"],
                       "frames": classify_piece_frames(sprites, base, state)}]
            common.export_sprite_model(ROOT, [p, sh], f"enemies/{name}", subset)
        return
    if "--pieces" in argv:
        d = Path(argv[argv.index("--pieces") + 1])
        for name, (p, sh, state) in pieces_out.items():
            common.export_glb([p, sh], d / f"{name}.glb")
    out = argv[argv.index("--out") + 1] if "--out" in argv else f"{NAME}_review.glb"
    for o, x, y in export:
        o.location = (x, y, 0)
    common.export_glb([o for o, _, _ in export], out)
    print("wrote", out)


if __name__ == "__main__":
    main()
