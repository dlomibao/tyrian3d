"""TIME WAR's grey mothership (newsh9.shp), whole: 48 x 112 px, four rigid rows of 2x2 enemies on one
link (16|18, 54|56, 244|246, 92|94; the "shield ship" of D195/D196). One builder for both assemblies:
assembly-newsh9-54.py exports the top four pieces, assembly-newsh9-92.py the lower four.

What it is: a capital ship seen from above. A glossy blue canopy over the forward half, split by a
raised grey spine (hatch, flat nose block, a long sunk slot); a grey armoured collar under the canopy's
rim; a band of dark blue bridge windows (a centre window and one wrapping round each flank, between two
pillars); under the sill two blue lamps; then the stern: overlapping armour plates on the flanks
(chevron seams), stepped plates beside a glowing blue channel, and a rolled lip round the stern.

How it is built (D213's method, on a hull): the sprite's own structure traced crisp, every tone measured
from the sprite, none chosen by hand.
  - BLUEPRINT: the plates as polygons in sprite px (pixel EDGES: column c spans x = c..c+1, row r spans
    y = r..r+1; the left half is written down, the right half is its mirror), on the sprite's own
    seams. Where the sprite draws a seam line the blueprint leaves that pixel row or column, or a
    diagonal strip, between two plates.
  - Each plate is a skin draped on the hull surface S(x, y), standing `lift` px proud. Within `edge` px
    of its rim it is a bevel that ramps `drop` px down to the seam. Its top is cut into tone cells
    (`xcuts`, `rcuts`; the stern lip along its curve) and its bevel into runs of about 4 px; each cell
    and each run takes the MEDIAN palette index of the sprite pixels under it (per side: the left half
    reads the left pixels, the right half the right). So the hull's left-lit and right-shaded bands,
    the lit bevels beside the seams and the shadowed edges are the sprite's own, as pal_<index>
    materials (D176: the game's near-overhead sun cannot shade a 1 px bevel into the sprite's two- to
    fourfold tone steps; and it shines from the south where the sprite is lit from the north, see GLINT).
  - A seam is a floor: the diagonal ones a strip plate just over the hull skin in the seam's own tone
    (the lower quartile of the pixels it covers), the straight ones a tile per sprite pixel in that
    pixel's index, as is anything else the blueprint leaves open.
  - Glass (canopy, windows, lamps, channel) is plates too, glowing in the sprite's blue indices (D126);
    the canopy lobes and the channel's cells take each animation phase's index (D17).
  - The hull body is one closed loft (deck, bilge, a plain belly) under the skin; the outline shell
    (D51) is a coarser loft of the same shape, so the ink is the silhouette's and no plate is inked.
Heights are low on purpose: the game's camera looks from 15-35 degrees off plumb, and every px of height
slides a feature up the screen by 0.3-0.7 px (D181). The deck stands 3.6 px over the gunwale, the canopy
8 px, and every piece carries one `tyrian_anchor` near deck height, so the seams, windows and lamps land
on their sprite pixels.

Each piece exports three nodes: <piece> (the skin: plates, seam floors and tiles; it casts no shadow),
<piece>_hull (its part of the body, the cuts filled; it casts the shadow) and <piece>_outline. Every corner's normal is the uncut craft's (the
plates' are the hull surface's own), so the shading runs on across the piece seams.

Pure Python + numpy down to "Blender" below: `python lib_newsh9_mothership.py --proto out.png` (system
Python with PIL) paints the blueprint flat beside the sprite and prints its fit; Blender is only needed
for main(). `-- --all` exports all eight pieces from either wrapper, `-- --whole X.glb` the uncut craft
(review only).
"""

import math
import os
import sys
from pathlib import Path

import numpy as np


def _find_repo():
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "assets" / "blender" / "common.py").exists() and (p / "package.json").exists():
            return p
    env = os.environ.get("TYRIAN_REPO")
    if env:
        return Path(env)
    raise RuntimeError("repo root not found above " + str(here))


ROOT = _find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "tools")]
import sprite_data  # noqa: E402
import sprite_mask  # noqa: E402

PX = 1 / 12
GW, GH = 48, 112
AX = 24.0
SHEET = "newsh9.shp"
# Rows of the craft, top to bottom: (left piece, right piece) and each piece's frames per animation phase.
ROWS = [("newsh9-16", "newsh9-18"), ("newsh9-54", "newsh9-56"), ("newsh9-244", "newsh9-246"),
        ("newsh9-92", "newsh9-94")]
FRAMES = {"newsh9-16": [16, 168, 250], "newsh9-18": [18, 170, 252], "newsh9-54": [54, 206, 126],
          "newsh9-56": [56, 208, 128], "newsh9-244": [244], "newsh9-246": [246],
          # spriteModels order (92, 130, 282); the sim cycles 92, 282, 130, 282: phase 1 is 282, phase 2 is 130
          "newsh9-92": [92, 130, 282], "newsh9-94": [94, 132, 284]}
PHASE_FRAMES = {"newsh9-16": [16, 168, 250], "newsh9-18": [18, 170, 252], "newsh9-54": [54, 206, 126],
                "newsh9-56": [56, 208, 128], "newsh9-244": [244, 244, 244], "newsh9-246": [246, 246, 246],
                "newsh9-92": [92, 282, 130], "newsh9-94": [94, 284, 132]}
TOP_PIECES = ["newsh9-16", "newsh9-18", "newsh9-54", "newsh9-56"]
LOW_PIECES = ["newsh9-244", "newsh9-246", "newsh9-92", "newsh9-94"]
# piece centres relative to the craft's centre (24, 56), px (split layout)
LAYOUT = [(n, -12 + 24 * c, -42 + 28 * r) for r, row in enumerate(ROWS) for c, n in enumerate(row)]

# ---- heights (px over the gunwale, the widest line, z = 0) ----------------------------------------
DECK, DECK_ROLL = 3.6, 7.0        # the hull's deck height and the width of its roll down to the gunwale
DOME, DOME_ROLL = 8.0, 14.0       # the canopy's crown and roll
ROLL_POWER = 2.2
BELLY = 0.55                      # the underside's depth as a share of the top's height
ANCHOR = 3.2                      # tyrian_anchor (px): the plane the game puts on the sprite's camera ray (D181)
LIFT, EDGE, DROP = 0.5, 0.9, 0.35  # a plate's stand-off, its bevel band's plan width and its drop
BASE_LIFT = 0.08                  # the seam tiles' stand-off over the hull skin
WALL = 0.45                       # a plate's skirt reaches this far under the hull skin
GRID = 2.5                        # drape grid (px)
CANOPY_VEIL = 4.0                 # what the gloss adds to the canopy's glowing blue in game (luma, measured)


# ====================================================================================================
# The sprite
# ====================================================================================================

def load_ship():
    """(grid[phase][row][col] palette indices, 256 RGB colours, {piece: sprite_data dict})."""
    sheet = sprite_data.data_file(ROOT, SHEET).read_bytes()
    grids = np.full((3, GH, GW), -1, int)
    for ri, row in enumerate(ROWS):
        for ci, name in enumerate(row):
            for ph in range(3):
                grids[ph, ri * 28:(ri + 1) * 28, ci * 24:(ci + 1) * 24] = np.array(
                    sprite_data.compose(sheet, 2, PHASE_FRAMES[name][ph]))
    pal = np.array(sprite_data.palette_rgb(ROOT), dtype=float)
    pieces = {n: sprite_data.load(ROOT, n, SHEET, FRAMES[n]) for row in ROWS for n in row}
    return grids, pal, pieces


def luma(rgb):
    return 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]


def is_grey(i):
    return 1 <= i <= 15


def is_blue(i):
    return 144 <= i <= 159 or i in (62, 63)


class Sprite:
    """The craft's pixels, masks and the tone lookups the build samples."""

    def __init__(self):
        self.grids, self.pal, self.pieces = load_ship()
        self.g = self.grids[0]
        colors = {i: tuple(self.pal[i]) for i in range(256)}
        m = sprite_mask.masks([list(map(int, row)) for row in self.g], colors)
        self.inner = np.array(m["inner"], bool)
        self.masks = m
        self.luma = luma(self.pal)
        # every opaque pixel as a grey (1..15) for the steel: greys as they are, the few anti-aliasing
        # pixels (82-86, 98, 102, 103 ...) as the nearest grey by luma; blues stay blue
        greys = np.arange(1, 16)
        self.grey = np.full(self.g.shape, 0, int)
        for (r, c), v in np.ndenumerate(self.g):
            if v < 0:
                continue
            if is_grey(v):
                self.grey[r, c] = v
            elif not is_blue(v):
                self.grey[r, c] = int(greys[np.argmin(np.abs(self.luma[greys] - self.luma[v]))])

    def colors(self):
        """sprite["colors"] for common.palette_material: every palette index."""
        return {str(i): [int(v) for v in self.pal[i]] for i in range(256)}


# ====================================================================================================
# Geometry helpers (px space: x right, y down the sprite)
# ====================================================================================================

def pchip(xs, ys):
    """Monotone cubic through (xs, ys), linear outside (as usp_talon.pchip)."""
    xs, ys = list(map(float, xs)), list(map(float, ys))
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0] + m[0] * (x - xs[0])
        if x >= xs[-1]:
            return ys[-1] + m[-1] * (x - xs[-1])
        i = max(0, min(n - 2, int(np.searchsorted(xs, x, side="right")) - 1))
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def poly_area(p):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(p, p[1:] + p[:1]))


def inside_poly(p, x, y):
    """Even-odd point in polygon; x, y arrays."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    out = np.zeros(x.shape, bool)
    for (x0, y0), (x1, y1) in zip(p, p[1:] + p[:1]):
        if y0 == y1:
            continue
        c = (y0 > y) != (y1 > y)
        xi = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
        out ^= c & (x < xi)
    return out


def seg_dist(p, x, y):
    """For points (x, y): (distance to the closed polygon p's boundary, nearest edge index, parameter t
    along that edge)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    best = np.full(x.shape, 1e9)
    bi = np.zeros(x.shape, int)
    bt = np.zeros(x.shape)
    for i, ((x0, y0), (x1, y1)) in enumerate(zip(p, p[1:] + p[:1])):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            continue
        t = np.clip(((x - x0) * dx + (y - y0) * dy) / L2, 0, 1)
        d = np.hypot(x - x0 - t * dx, y - y0 - t * dy)
        m = d < best
        best = np.where(m, d, best)
        bi = np.where(m, i, bi)
        bt = np.where(m, t, bt)
    return best, bi, bt


# ====================================================================================================
# The hull: outline and surface
# ====================================================================================================

class Hull:
    """The plan outline (the sprite's inner mask, smoothed) and the top surface S(x, y) over it."""

    def __init__(self, sp):
        inner = sp.inner
        rows = [r for r in range(GH) if inner[r].any()]
        hw = {}
        for r in rows:
            cols = np.nonzero(inner[r])[0]
            hw[r] = ((AX - cols[0]) + (cols[-1] + 1 - AX)) / 2
        self.r0, self.r1 = rows[0], rows[-1] + 1          # y of the nose and the stern end
        # one knot in the middle of each run of rows of one width (the middle of each pixel step)
        ks, ws = [], []
        r = rows[0]
        while r <= rows[-1]:
            e = r
            while e + 1 <= rows[-1] and hw[e + 1] == hw[r]:
                e += 1
            if e - r >= 4:      # a long straight run: held from end to end, not only at its middle
                ks += [r + 1.5, e + 1 - 1.5]
                ws += [hw[r], hw[r]]
            else:
                ks.append((r + e + 1) / 2)
                ws.append(hw[r])
            r = e + 1
        # blunt ends, as the mask's: the first and last rows' own widths, held to the end
        ks = [self.r0] + ks + [self.r1]
        ws = [ws[0]] + ws + [ws[-1]]
        self._w = pchip(ks, ws)
        self.wmax = max(ws)
        ys = np.arange(self.r0, self.r1 + 1e-6, 0.5)
        left = [(AX - self.W(y), y) for y in ys]
        right = [(AX + self.W(y), y) for y in ys[::-1]]
        self.outline = left + right

    def W(self, y):
        """Half-width (px) at y."""
        y = max(self.r0, min(self.r1, y))
        return max(0.5, min(self.wmax, self._w(y)))

    def left(self, y, inset=0.0):
        return (AX - self.W(y) + inset, y)

    def normal(self, y):
        """Inward unit normal of the LEFT outline at y."""
        d = (self.W(y + 0.25) - self.W(y - 0.25)) / 0.5
        L = math.hypot(1.0, d)
        return (1.0 / L, d / L)

    def left_in(self, y, w):
        """The left outline's point at y moved w px inward along its normal."""
        nx, ny = self.normal(y)
        return (AX - self.W(y) + nx * w, y + ny * w)

    def dist(self, x, y):
        """Distance to the outline for points inside (0 outside)."""
        d, _, _ = seg_dist(self.outline, x, y)
        return np.where(inside_poly(self.outline, x, y), d, 0.0)

    @staticmethod
    def crown(y):
        """Deck / canopy crown height (px) and roll width by row: the canopy's dome over rows 2-34,
        falling to the deck by row 47."""
        t = np.clip((np.asarray(y, float) - 33.0) / 14.0, 0, 1)
        t = t * t * (3 - 2 * t)
        return DOME + (DECK - DOME) * t, DOME_ROLL + (DECK_ROLL - DOME_ROLL) * t

    def S(self, x, y):
        """Top surface height (px) at (x, y)."""
        h, f = self.crown(y)
        t = np.clip(self.dist(x, y) / f, 0, 1)
        return h * (1 - (1 - t) ** ROLL_POWER)

    def normals(self, x, y, crown=False):
        """Unit normals of the top surface at (x, y), in Blender's axes (x right, y up the sprite, z up):
        the plates' shading normals, so a draped plate is as smooth as the hull whatever its triangles."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        d = 0.25
        if crown:
            sx = np.zeros(x.shape)
            sy = (self.S_crown(y + d) - self.S_crown(y - d)) / (2 * d)
        else:
            # central differences; at the rim, where one sample falls outside the hull (S = 0 there), the
            # one-sided slope from the inside, so the rim's normals run on smoothly along it
            s0 = self.S(x, y)

            def slope(xa, ya, xb, yb):
                a, b = self.S(xa, ya), self.S(xb, yb)
                ina, inb = self.dist(xa, ya) > 0, self.dist(xb, yb) > 0
                return np.where(ina & inb, (b - a) / (2 * d), np.where(inb, (b - s0) / d, np.where(ina, (s0 - a) / d, 0.0)))
            sx = slope(x - d, y, x + d, y)
            sy = slope(x, y - d, x, y + d)
        n = np.stack([-sx, sy, np.ones(x.shape)], axis=-1)
        return n / np.linalg.norm(n, axis=-1, keepdims=True)

    def S_crown(self, y):
        """The surface on the centre line (the spine's and housing's level)."""
        y = np.asarray(y, float)
        return self.S(np.full(y.shape, AX), y)


# ====================================================================================================
# The blueprint
# ====================================================================================================

class Plate:
    """One plate: `poly` vertices (x, y) or (x, y, "f") in px edges, clockwise or not; "f" marks the edge
    that starts at that vertex as flush (no bevel band: it butts against a neighbour of the same level).
    kind: "steel" | "lip" (steel that keeps its gloss on any slope) | "seam" (a matte seam floor) |
    "canopy" | "window" | "lamp" | "channel" (glass). mode: "hull" (draped on S) or
    "crown" (level across the ship at the centre line's height). `side`: "L" as written, "R" mirrored,
    "C" a centre plate (as written, its cuts absolute).
    The bevel band is the strip within `edge` px of an unflushed edge: there the plate's top ramps down
    `drop` px to its rim, and the tone is the band's own (Tones.run)."""

    def __init__(self, name, poly, kind="steel", lift=LIFT, edge=EDGE, mode="hull", xcuts=(), rcuts=(),
                 grid=GRID, side="C", drop=DROP, guide=None, gstep=3.2):
        self.name, self.kind, self.lift, self.mode, self.side = name, kind, lift, mode, side
        self.grid, self.drop = grid, drop
        pts = [(float(v[0]), float(v[1])) for v in poly]
        flush = [len(v) > 2 and v[2] == "f" for v in poly]
        if side == "R":
            n = len(pts)
            pts = [(GW - x, y) for x, y in reversed(pts)]
            flush = [flush[(n - 2 - j) % n] for j in range(n)]
            xcuts = [GW - x for x in xcuts]
            guide = [(GW - x, y) for x, y in guide] if guide else None
        # a strip along a curve (the stern lip) is cut into tone cells across that curve, every gstep px
        self.guide, self.gstep = guide, gstep
        self.poly, self.flush = pts, flush
        self.xcuts, self.rcuts = sorted(xcuts), sorted(rcuts)
        glass = kind in ("canopy", "window", "lamp", "channel")
        self.edges = [0.0 if (f or glass or edge <= 0) else edge for f in flush]
        self.banded = [i for i, e in enumerate(self.edges) if e]
        # bevel runs: each edge in pieces of about 4 px
        self.runs = []
        for (x0, y0), (x1, y1) in zip(self.poly, self.poly[1:] + self.poly[:1]):
            self.runs.append(max(1, int(round(math.hypot(x1 - x0, y1 - y0) / 4.0))))

    def band(self, x, y):
        """For points (x, y): (depth into the bevel band 0..1, 0 = at the plate's rim, 1 = on the flat top or
        past it; the banded edge that is nearest; the parameter along it)."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        best = np.full(x.shape, 1.0)
        bi = np.full(x.shape, -1)
        bt = np.zeros(x.shape)
        n = len(self.poly)
        for i in self.banded:
            (x0, y0), (x1, y1) = self.poly[i], self.poly[(i + 1) % n]
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            if L2 < 1e-12:
                continue
            t = np.clip(((x - x0) * dx + (y - y0) * dy) / L2, 0, 1)
            d = np.hypot(x - x0 - t * dx, y - y0 - t * dy) / self.edges[i]
            m = d < best
            best = np.where(m, d, best)
            bi = np.where(m, i, bi)
            bt = np.where(m, t, bt)
        return best, bi, bt

    def cells_of(self, x, y):
        """Tone cells of points (arrays): (column band, row band), or (station along the guide, 0)."""
        x, y = np.asarray(x, float), np.asarray(y, float)
        if self.guide:
            return (self._along(x, y) // self.gstep).astype(int), np.zeros(x.shape, int)
        return np.searchsorted(self.xcuts, x, side="right"), np.searchsorted(self.rcuts, y, side="right")

    def cell(self, x, y):
        i, j = self.cells_of(np.array([x]), np.array([y]))
        return int(i[0]), int(j[0])

    def _along(self, x, y):
        """Arc length along the guide of each point's nearest guide point."""
        g = self.guide
        best = np.full(x.shape, 1e9)
        out = np.zeros(x.shape)
        s0 = 0.0
        for (x0, y0), (x1, y1) in zip(g, g[1:]):
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy)
            if L < 1e-9:
                continue
            t = np.clip(((x - x0) * dx + (y - y0) * dy) / (L * L), 0, 1)
            d = np.hypot(x - x0 - t * dx, y - y0 - t * dy)
            m = d < best
            best = np.where(m, d, best)
            out = np.where(m, s0 + t * L, out)
            s0 += L
        return out

    def guide_cuts(self):
        """(point, unit tangent) of the guide at every cell boundary, for the cuts across the strip."""
        if not self.guide:
            return []
        out, s0, k = [], 0.0, 1
        for (x0, y0), (x1, y1) in zip(self.guide, self.guide[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            while L > 1e-9 and k * self.gstep <= s0 + L:
                t = (k * self.gstep - s0) / L
                out.append(((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), ((x1 - x0) / L, (y1 - y0) / L)))
                k += 1
            s0 += L
        return out


def blueprint(hull):
    """Every plate of the craft. Coordinates are read off the sprite's index map (phase 0)."""
    P = []

    def LR(name, poly, **kw):
        P.append(Plate(name + ".L", poly, side="L", **kw))
        P.append(Plate(name + ".R", poly, side="R", **kw))

    def C(name, poly, **kw):
        P.append(Plate(name, poly, side="C", **kw))

    def O(y):
        """The left outline's x at y."""
        return hull.left(y)[0]

    def ol(y0, y1, step=2.0, inset=0.0):
        """Points down (or up) the left outline from y0 to y1."""
        n = max(1, int(math.ceil(abs(y1 - y0) / step)))
        return [hull.left(y0 + (y1 - y0) * k / n, inset) for k in range(n + 1)]

    # ---- the canopy: the hull's own upper surface in glass, down to the rim. The sprite draws the rim
    # 1.5 px lower on its lit left than on its right (rows 33-45); the model's is the mean of the two.
    rim_glass = [(1.8, 37.0), (2.6, 39.0), (3.6, 40.5), (4.6, 41.7), (5.8, 42.8), (7.2, 43.8), (8.8, 44.5),
                 (10.8, 45.0), (18.0, 45.0)]
    LR("canopy", ol(3.0, 35.0) + rim_glass + [(18.0, 3.0)], kind="canopy", lift=0.35, grid=1.5)
    SEAM = dict(kind="seam", lift=0.12, edge=0.0)   # a seam's floor between two plates, in the sprite's seam tone

    # ---- the spine (cols 18-29): two rails and the nose block at one level, the hatch (rows 2-6) and
    # the long slot (rows 17-48) sunk between them
    C("spine", [(18, 2), (20, 2, "f"), (20, 7), (28, 7, "f"), (28, 2), (30, 2), (30, 49), (28, 49, "f"), (28, 17),
                (20, 17, "f"), (20, 49), (18, 49)], mode="crown", lift=1.6, edge=1.0, xcuts=[20, 28],
      rcuts=[7, 12, 17, 24, 31, 38, 44])
    C("hatch", [(20, 2), (28, 2), (28, 7), (20, 7)], mode="crown", lift=0.9, rcuts=[4.5])
    C("slot", [(20, 17), (28, 17), (28, 49), (20, 49)], mode="crown", lift=0.6, rcuts=[22, 29, 35, 41])
    # the housing at the spine's end (rows 49-58): a block with a lit bar across it (rows 51-53)
    C("housing", [(18, 49), (30, 49), (30, 59), (18, 59)], mode="crown", lift=2.0, rcuts=[51, 52, 53, 54])

    # ---- the frame: collar under the rim, the pillar (cols 11-14), the strip under the sill and the
    # strut beside the lamps (cols 16-19), one plate round the side window. Its edge along the canopy
    # is the sprite's lit bevel (rows 37-46), its edge along the window's lower side the lit sill bead.
    frame_top = [(O(36.6), 36.6), (1.5, 38.0), (2.2, 39.8), (3.1, 41.2), (4.1, 42.4), (5.3, 43.5), (6.7, 44.5),
                 (8.4, 45.3), (10.6, 45.8), (18.5, 45.8, "f")]
    win_top = [(O(49.3), 49.3), (3, 52.3), (5, 54.5), (7, 56.4), (9, 57.4), (11, 58.2)]
    win_low = [(11, 71), (9, 70.2), (7, 69.2), (6, 68.2), (5, 67.2), (4, 65.5), (3, 63.5), (2, 61.5), (O(60.0), 60.0)]
    seam2_up = [(16, 75.1), (8.8, 75.1), (6.9, 74.2), (4.9, 73.2), (3.3, 72.2), (2.2, 71.2), (O(70.3), 70.3)]
    LR("frame", frame_top + [(18.5, 59), (15, 59), (15, 72), (20, 72, "f"), (20, 87), (16, 87)] + seam2_up
       + [(O(60.0), 60.0)] + list(reversed(win_low))[1:] + [(11, 58.2)] + list(reversed(win_top))[1:],
       xcuts=[4, 7, 11, 16, 18], rcuts=[59, 72, 80.5])
    # the canopy's seat: the strip between the glass and the frame's lit bevel
    LR("rimseam", [hull.left(35.0)] + rim_glass + [(v[0], v[1]) for v in reversed(frame_top)], xcuts=[4, 8, 12], **SEAM)

    # ---- the bridge windows: dark blue glass a little under the frame, cut on the sprite's mullions
    C("window", [(15, 59), (18, 59), (18, 60), (30, 60), (30, 59), (33, 59), (33, 72), (15, 72)], kind="window",
      lift=0.15, xcuts=[19, 20, 23, 24, 26, 27, 30, 31], rcuts=[60, 64, 65, 68, 69])
    LR("sidewin", win_top + win_low, kind="window", lift=0.15, xcuts=[3, 5, 7, 9],
       rcuts=[52, 54, 56, 58, 60, 62, 64, 66, 68])

    # ---- under the sill: the lamp bed with its two bars (rows 77, 82) and the two lamps
    C("lampbed", [(20, 72), (28, 72, "f"), (28, 84, "f"), (20, 84, "f")], rcuts=[73, 77, 78, 82, 83])
    for k, y in enumerate((74, 79)):
        C(f"lamp{k}", [(20, y), (28, y), (28, y + 3), (20, y + 3)], kind="lamp", lift=0.85,
          xcuts=[21, 22, 23, 26, 27], rcuts=[y + 1, y + 2])

    # ---- the flank's armour: the chevron plate between the two diagonal seams (its upper edge the lit
    # line of rows 72-76, its lower edge the dark seam of rows 78-83) and the stern flank under it
    seam2_low = [(O(71.2), 71.2), (2, 72), (3, 73), (4.5, 74), (6.5, 75), (8.5, 76), (15, 76)]
    seam3_up = [(15, 83), (8, 83), (6, 82), (4.5, 80.6), (3, 79), (2, 78), (O(77.2), 77.2)]
    LR("chevron", seam2_low + seam3_up, lift=0.65, xcuts=[4, 7, 11])
    LR("seam2", seam2_up + seam2_low + [(16, 76)], xcuts=[4, 9], **SEAM)
    lipw = lambda y: 1.5 + 1.3 * smoothstep((y - 88.0) / 9.0)  # noqa: E731  the stern lip's width
    lip_in = []
    y = 88.0
    lip_end = None                 # where the lip's inner side meets the channel (x = 20)
    while y <= hull.r1 - 0.2:
        q = hull.left_in(y, lipw(y))
        if q[0] >= 20.0:
            a = lip_in[-1]
            lip_end = (20.0, a[1] + (q[1] - a[1]) * (20.0 - a[0]) / (q[0] - a[0]))
            break
        lip_in.append(q)
        y += 1.5
    y_end = y
    if lip_end is None:
        lip_end = (20.0, lip_in[-1][1])
    flank_in = [q for q in lip_in if q[0] < 12.0]
    a, b = flank_in[-1], lip_in[len(flank_in)]
    t = (12.0 - a[0]) / (b[0] - a[0])
    corner = (12.0, a[1] + (b[1] - a[1]) * t)
    seam3_low = [(O(78.1), 78.1), (2, 78.9), (3, 79.9), (4.5, 81.5), (6, 82.9), (8, 83.9), (12, 84)]
    if math.hypot(corner[0] - flank_in[-1][0], corner[1] - flank_in[-1][1]) < 0.3:
        flank_in = flank_in[:-1]
    LR("flank", seam3_low + [corner] + [(q[0], q[1], "f") for q in reversed(flank_in)] + ol(88.0, 78.1)[:-1],
       xcuts=[4, 7], rcuts=[91, 97])
    LR("seam3", seam3_up + seam3_low + [(15, 84)], xcuts=[4, 9], **SEAM)
    # the rolled lip round the stern (rows 88-110): the sprite's lit bevel, dark on the lower left, a
    # bright sheen on the lower right
    lip_out = ol(88.0, min(y_end, hull.r1 - 0.3), step=1.5)
    LR("lip", lip_out + [(20.0, lip_out[-1][1] - 0.2), lip_end] + [(q[0], q[1]) for q in reversed(lip_in)], kind="lip",
       edge=0.0, guide=lip_out + [(20.0, lip_out[-1][1])], gstep=3.0)

    # ---- the stepped plates beside the channel (cols 13-19 | 28-34): rows 85-86, 87-90 (lit top edge
    # row 87), 92-103 (lit top edge row 92); the dark rows 84 and 91 and cols 12 | 35 are the seams
    LR("tier0", [(13, 85), (16, 85, "f"), (16, 87, "f"), (13, 87)], edge=0.6)
    LR("tier1", [(13, 87), (20, 87, "f"), (20, 91), (13, 91)], lift=0.8)
    LR("tier2", [(13, 92), (20, 92, "f"), (20, 104), (16, 104), (13, 103)], lift=0.8, rcuts=[96, 100])
    # the dark pan between the last plate and the lip (rows 103-106)
    LR("sternpan", [corner, (13, 103), (16, 104), (20, 104), lip_end] + [q for q in reversed(lip_in) if q[0] > 12.0],
       xcuts=[16], **SEAM)

    # ---- the channel (cols 20-27, rows 84-110): a glowing trough, darker along its left wall
    C("channel", [(20, 84), (28, 84), (28, 110.3), (26.5, 111), (21.5, 111), (20, 110.3)], kind="channel", lift=0.25,
      xcuts=[22, 24], rcuts=[y for y in range(86, 111, 2)])
    # an edge that runs along the hull's outline has no bevel band: the hull's roll is its bevel
    for p in P:
        n = len(p.poly)
        on = [abs(abs(x - AX) - hull.W(y)) < 0.06 for x, y in p.poly]
        for i in range(n):
            if on[i] and on[(i + 1) % n]:
                p.edges[i] = 0.0
        p.banded = [i for i, e in enumerate(p.edges) if e]
    return P


# ====================================================================================================
# Tones: the sprite's median index per cell, bevel run and seam tile
# ====================================================================================================

GLASS_KINDS = ("canopy", "window", "lamp", "channel")


class Tones:
    """Palette indices for every cell and bevel run of every plate, read from the sprite.

    A steel index is a grey 1..12 (the sprite's rare brighter pixels are glints: 13-15 read as 12).
    A glass index is the phase-0 blue; `shift(kind, i)` gives its phase 1 and 2 indices."""

    def __init__(self, sp, plates):
        self.sp, self.plates = sp, plates
        ys, xs = np.mgrid[0:GH, 0:GW]
        self.cx, self.cy = xs + 0.5, ys + 0.5
        self.cells, self.runs, self.canopy = {}, {}, {}
        for p in plates:
            self._plate(p)
        # which plate covers each sprite pixel (the highest), for the seam tiles and the proto
        self.cover = np.zeros((GH, GW), bool)
        for p in plates:
            self.cover |= inside_poly(p.poly, self.cx, self.cy)

    def _pool(self, p):
        """(mask of usable pixels, their index array) for a plate's kind."""
        sp = self.sp
        if p.kind in GLASS_KINDS:
            g = sp.g
            blue = ((g >= 144) & (g <= 159)) | (g == 62) | (g == 63)
            return blue, np.where((g == 62) | (g == 63), 159, g)
        return (sp.grey > 0) & sp.inner, np.minimum(sp.grey, 12)

    def _plate(self, p):
        ok, idx = self._pool(p)
        inp = inside_poly(p.poly, self.cx, self.cy)
        mid = np.median
        if p.kind == "seam":
            # a thin strip holds few pixel centres: every pixel it covers 0.4 of counts, and the seam's
            # tone is the lower quartile of those (the strip's edges take in the plates' own pixels)
            n = 4
            ys, xs = np.mgrid[0:GH * n, 0:GW * n]
            inp = inside_poly(p.poly, (xs + 0.5) / n, (ys + 0.5) / n).reshape(GH, n, GW, n).mean(axis=(1, 3)) >= 0.4
            mid = lambda a: np.percentile(a, 25, method="lower")  # noqa: E731
        depth, ei, et = p.band(self.cx, self.cy)
        top = inp & ok & (depth >= 1.0)
        whole = int(mid(idx[top])) if top.any() else (int(mid(idx[inp & ok])) if (inp & ok).any() else None)
        if whole is None:   # a plate over pixels of the other kind only: the nearest usable pixels
            d = np.where(ok, np.hypot(self.cx - np.mean([v[0] for v in p.poly]), self.cy - np.mean([v[1] for v in p.poly])), 1e9)
            whole = int(idx.flat[np.argmin(d)])
        ci, cj = p.cells_of(self.cx, self.cy)
        # windows and lamps in the even steps of the blue ramp only (half the materials); the channel keeps
        # every step (its ramp is steep there: 150 is luma 23, 151 is 35, 152 is 54)
        even = (lambda v: 144 + 2 * ((v - 144) // 2)) if p.kind in ("window", "lamp") else (lambda v: v)
        for i, j in {(int(a), int(b)) for a, b in zip(ci[top], cj[top])}:
            self.cells[(p.name, i, j)] = even(int(mid(idx[top & (ci == i) & (cj == j)])))
        whole = even(whole)
        if p.kind == "canopy":
            # One tone for a whole lobe of the canopy, per animation phase: the ramp index whose luma is
            # nearest the lobe's MEAN luma in that phase (the median is 150 on both lobes, though the right
            # one is drawn a third darker; and the ramp is steep, 150 is luma 23, 153 is 69), less
            # CANOPY_VEIL, what the game's glossy glass adds to its palette colour (measured in game).
            blues = np.arange(144, 160)
            lum = self.sp.luma
            per = []
            for g in self.sp.grids:
                v = np.where((g == 62) | (g == 63), 159, g)[inp & ok]
                per.append(int(blues[np.argmin(np.abs(lum[blues] - (lum[v].mean() - CANOPY_VEIL)))]))
            whole = per[0]
            self.canopy[p.name] = (per[1], per[2])
            self.cells = {k: v for k, v in self.cells.items() if k[0] != p.name}
        self.cells[(p.name, None)] = whole
        # bevel runs: the pixels whose centre lies in the band of each edge (a hair over its width, so a
        # 0.9 px band still owns the pixel row or column along it), by run
        band = inp & ok & (depth * np.array([p.edges[i] if i >= 0 else 1.0 for i in ei.ravel()]).reshape(ei.shape) <= 0.95) & (ei >= 0)
        for e in p.banded:
            n = p.runs[e]
            for k in range(n):
                m = band & (ei == e) & (np.minimum((et * n).astype(int), n - 1) == k)
                if m.any():
                    self.runs[(p.name, e, k)] = int(np.median(idx[m]))

    def cell(self, p, x, y):
        i, j = p.cell(x, y)
        return self.cells.get((p.name, i, j), self.cells[(p.name, None)])

    def run(self, p, e, t, x, y):
        """Index of the bevel run at parameter t of edge e (its own pixels; else the cell behind it)."""
        k = min(int(t * p.runs[e]), p.runs[e] - 1)
        v = self.runs.get((p.name, e, k))
        return self.cell(p, x, y) if v is None else v

    def shift(self, p, i):
        """(phase 1, phase 2) indices of a glass plate's index i, as the sprite's frames shift it: every
        canopy pixel walks 3 and 7 steps up the ramp (past 159 it is the white of 62/63; the lobe's tone
        per phase is read in _plate), every channel pixel 2 and 5; windows and lamps are on the one-frame
        pieces and don't move."""
        if p.kind == "canopy":
            return self.canopy[p.name]
        if p.kind == "channel":
            return (i, i) if i <= 144 else (min(i + 2, 159), min(i + 5, 159))
        return i, i

    def base(self, r, c):
        """("steel" | "blue", index) of the seam tile at pixel (r, c), None where no tile is wanted."""
        sp = self.sp
        v = sp.g[r, c]
        if v < 0 or not sp.inner[r, c]:
            return None
        if is_blue(v):
            return ("blue", 158 if v in (62, 63) else 144 + 2 * ((int(v) - 144) // 2))
        return ("steel", int(min(sp.grey[r, c], 12)))


# ====================================================================================================
# 2D proto: the blueprint painted flat beside the sprite (system Python + PIL)
# ====================================================================================================

def proto(out_png, k=10):
    from PIL import Image
    sp = Sprite()
    hull = Hull(sp)
    plates = blueprint(hull)
    tones = Tones(sp, plates)
    n = 4
    ys, xs = np.mgrid[0:GH * n, 0:GW * n]
    X, Y = (xs + 0.5) / n, (ys + 0.5) / n
    img = np.zeros((GH * n, GW * n), int) - 1
    level = np.full(img.shape, -1e9)
    crown_lv = 2.0   # crown-mode plates sit on the centre line: over the hull-mode ones
    inside = inside_poly(hull.outline, X, Y)
    for r in range(GH):
        for c in range(GW):
            b = tones.base(r, c)
            if b:
                img[r * n:(r + 1) * n, c * n:(c + 1) * n] = b[1]
    img[~inside] = -1
    for p in plates:
        lv = p.lift + (crown_lv if p.mode == "crown" else 0.0)
        inp = inside_poly(p.poly, X, Y) & inside & (lv > level)
        if not inp.any():
            continue
        depth, ei, et = p.band(X, Y)
        yy, xx = np.nonzero(inp)
        for y_, x_ in zip(yy, xx):
            px, py = X[y_, x_], Y[y_, x_]
            if depth[y_, x_] >= 1.0:
                img[y_, x_] = tones.cell(p, px, py)
            else:
                img[y_, x_] = tones.run(p, int(ei[y_, x_]), float(et[y_, x_]), px, py)
            level[y_, x_] = lv
    pal = sp.pal
    rgb = np.zeros(img.shape + (3,), np.uint8)
    rgb[:] = (90, 0, 90)
    rgb[img >= 0] = pal[img[img >= 0]].astype(np.uint8)
    spr = np.zeros((GH, GW, 3), np.uint8)
    spr[:] = (90, 0, 90)
    spr[sp.g >= 0] = pal[sp.g[sp.g >= 0]].astype(np.uint8)
    z = k
    a = Image.fromarray(spr).resize((GW * z, GH * z), Image.NEAREST)
    b = Image.fromarray(rgb).resize((GW * z, GH * z), Image.NEAREST)
    both = Image.new("RGB", (GW * z * 2 + 10, GH * z), (0, 0, 0))
    both.paste(a, (0, 0))
    both.paste(b, (GW * z + 10, 0))
    both.save(out_png)
    # fit: the outline against the inner mask (the rule's grid IoU) and the flat paint's tone error
    cov = inside.reshape(GH, n, GW, n).mean(axis=(1, 3)) >= 0.5
    inner = sp.inner
    iou = (cov & inner).sum() / (cov | inner).sum()
    lum = luma(pal)
    pl = np.where(img >= 0, lum[np.maximum(img, 0)], 0).reshape(GH, n, GW, n).mean(axis=(1, 3))
    sl = np.where(sp.g >= 0, lum[np.maximum(sp.g, 0)], 0)
    m = inner & cov
    print(f"outline grid IoU vs inner mask {iou:.4f}; flat paint vs sprite, mean |luma error| {np.abs(pl - sl)[m].mean():.1f} "
          f"(sprite mean {sl[m].mean():.1f}); plates {len(plates)}, uncovered inner px {(inner & ~tones.cover).sum()}")
    return sp, hull, plates, tones


# ====================================================================================================
# Blender
# ====================================================================================================

FINISH = {
    # satin grey steel (D225: metallic 0.7 mirrored the dark room and read near-black)
    "steel": dict(metallic=0.3, roughness=0.45),
    # the same steel with no gloss: the body, seam floors and tiles, and every face that tilts toward GLINT
    "matte": dict(metallic=0.1, roughness=0.85),
    # The canopy glows in its palette blue (D126: 1.0 is the colour unlit) under a glossy coat for the
    # sheen. Lit, a blue this saturated came out periwinkle (+30-40 on red and green at phase 0, whatever
    # its Specular IOR Level); put down to the Neutral tone mapping, which pulls a colour whose brightest
    # channel passes its knee toward white.
    "canopy": dict(metallic=0.0, roughness=0.12, emit=1.1, spec=0.5),
    # windows, lamps and the channel glow in their own palette colour too, with no specular (Specular IOR
    # Level 0), so no room light hazes or streaks them; at strength 1.0 they drew 0.8 of their sprite's luma
    # (the canopy 0.9), hence 1.2 and 1.1
    "glow": dict(metallic=0.0, roughness=0.6, emit=1.2, spec=0.0),
}
# The game's sun stands south-west of plumb (sun.ts: (-6, 20, 8.4), z down the screen) and its camera looks
# from the south, so a face tilted about 25 degrees to the south mirrors the sun into the camera; the sprite
# is lit from the north-west, and draws those faces in shade. GLINT is that mirror normal for the craft's
# place on screen (Blender axes: x right, y up the sprite, z up); a steel face within GLINT_DEG of it is
# matte, so the game's sun does not light what the sprite shades (the spine's fall to the collar, rows 31-46,
# drew 1.5-1.8x its sprite; every south bevel drew a bright line).
GLINT = (-0.17, -0.43, 0.89)
GLINT_DEG = 20.0
PHASE1 = [168, 170, 206, 208, 282, 284]
PHASE2 = [250, 252, 126, 128, 130, 132]


def X(x):
    return (x - AX) * PX


def Y(y):
    return (GH / 2 - y) * PX


class Mats:
    """pal_<index> materials by (finish, index, phase indices), made on first use."""

    def __init__(self, sp):
        import common
        self.common = common
        self.sprite = {"name": "newsh9 mothership", "colors": sp.colors()}
        self.list, self.slots = [], {}

    def __call__(self, finish, index, phases=None):
        if phases is not None and phases[0] == index and phases[1] == index:
            phases = None
        key = (finish, index, phases)
        if key not in self.slots:
            f = FINISH[finish]
            frames = None
            if phases is not None:
                frames = {**{fr: phases[0] for fr in PHASE1}, **{fr: phases[1] for fr in PHASE2}}
            m = self.common.palette_material(self.sprite, index, f"nsh9m{len(self.list)}", metallic=f["metallic"],
                                             roughness=f["roughness"], emission_strength=f.get("emit", 0.0), frames=frames)
            if "spec" in f:
                bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                if "Specular IOR Level" in bsdf.inputs:
                    bsdf.inputs["Specular IOR Level"].default_value = f["spec"]
            self.slots[key] = len(self.list)
            self.list.append(m)
        return self.slots[key]


class Acc:
    """Vertices and faces collected for one mesh (px space; converted on to_object). A face may bring
    its own corner normals (the hull surface's, for a draped top); the others keep Blender's."""

    def __init__(self):
        self.v, self.f, self.m, self.s, self.n = [], [], [], [], []

    def vert(self, x, y, z):
        self.v.append((X(x), Y(y), z * PX))
        return len(self.v) - 1

    def face(self, idx, mat, smooth, normals=None):
        idx = list(idx)
        if len(set(idx)) < 3:
            return
        self.f.append(idx)
        self.m.append(mat)
        self.s.append(smooth)
        self.n.append(normals)

    def face_up(self, idx, mat, smooth, normals=None):
        """A face wound so its normal points up; a degenerate one is left out."""
        a = self.v[idx[0]]
        nz = 0.0
        for k in range(1, len(idx) - 1):
            b, c = self.v[idx[k]], self.v[idx[k + 1]]
            nz += (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(nz) < 1e-9:
            return
        if nz < 0:
            idx = list(reversed(idx))
            normals = list(reversed(normals)) if normals is not None else None
        self.face(idx, mat, smooth, normals)

    def flat_normal(self, idx):
        import numpy as _np
        p = _np.array([self.v[i] for i in idx])
        n = _np.zeros(3)
        for k in range(len(p)):
            a, b = p[k], p[(k + 1) % len(p)]
            n += _np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
        L = _np.linalg.norm(n)
        n = n / L if L > 1e-12 else _np.array([0.0, 0.0, 1.0])
        return n if n[2] >= 0 else -n

    def to_object(self, name, mats, coll):
        import bpy
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.polygons.foreach_set("material_index", self.m)
        me.polygons.foreach_set("use_smooth", self.s)
        me.update()
        if any(n is not None for n in self.n):
            auto = [c.vector.copy() for c in me.corner_normals]
            out = []
            for poly, n in zip(me.polygons, self.n):
                for k, li in enumerate(poly.loop_indices):
                    out.append(tuple(auto[li]) if n is None else tuple(float(q) for q in n[k]))
            me.normals_split_custom_set(out)
        for m in mats:
            me.materials.append(m)
        o = bpy.data.objects.new(name, me)
        coll.objects.link(o)
        return o


def _tessellate(p, xs, ys):
    """The plate's polygon as a flat bmesh (px x, -y): triangulated, cut along the drape grid and the tone
    cuts (x in xs, y in ys), and along the inner side of every bevel band (only the faces near that edge)."""
    import bmesh
    from mathutils import Vector
    poly = p.poly
    bm = bmesh.new()
    pts = poly if poly_area([(x, -y) for x, y in poly]) > 0 else list(reversed(poly))
    f = bm.faces.new([bm.verts.new((x, -y, 0.0)) for x, y in pts])
    bm.normal_update()
    bmesh.ops.triangulate(bm, faces=[f])
    for x in xs:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    for y in ys:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, -y, 0), plane_no=(0, 1, 0))
    n = len(poly)
    sgn = 1.0 if poly_area(poly) > 0 else -1.0
    for i in p.banded:
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        nx, ny = -dy / L * sgn, dx / L * sgn          # inward normal (px, y down)
        w = p.edges[i]
        a, b = Vector((x0, -y0, 0.0)), Vector((x1, -y1, 0.0))
        near = []
        for fc in bm.faces:
            c = fc.calc_center_median()
            t = max(0.0, min(1.0, (c - a).dot(b - a) / (L * L)))
            if (c - (a + (b - a) * t)).length < w + p.grid:
                near.append(fc)
        geom = list({v for fc in near for v in fc.verts}) + list({e for fc in near for e in fc.edges}) + near
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(x0 + nx * w, -(y0 + ny * w), 0.0), plane_no=(nx, -ny, 0.0))
    for (gx, gy), (tx, ty) in p.guide_cuts():
        o = Vector((gx, -gy, 0.0))
        near = [fc for fc in bm.faces if (fc.calc_center_median() - o).length < 6.0]
        geom = list({v for fc in near for v in fc.verts}) + list({e for fc in near for e in fc.edges}) + near
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=o, plane_no=(tx, -ty, 0.0))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-3)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-3, edges=bm.edges[:])
    bm.verts.index_update()
    bm.faces.index_update()
    return bm


def _lines(lo, hi, step, cuts):
    out = {round(c, 4) for c in cuts if lo < c < hi}
    k = math.floor(lo / step) + 1
    while k * step < hi:
        if all(abs(k * step - c) > 0.3 for c in out):
            out.add(round(k * step, 4))
        k += 1
    return sorted(out)


def build_plate(acc, mats, hull, tones, p):
    """One plate: its draped top in tone cells, the bevel band (a ramp down to the rim, in the tone of its
    run) and a skirt under the rim."""
    glass = p.kind in GLASS_KINDS
    gl = np.array(GLINT) / np.linalg.norm(GLINT)
    cos_glint = math.cos(math.radians(GLINT_DEG))

    def finish(n):
        """A face's finish from its shading normal n."""
        if glass:
            return "canopy" if p.kind == "canopy" else "glow"
        if p.kind == "lip":           # the stern's rolled lip keeps its gloss: the sun's sheen is the sprite's lit bevel
            return "steel"
        if p.kind == "seam" or float(np.dot(n, gl)) > cos_glint:
            return "matte"
        return "steel"

    def height(xs, ys):
        xs, ys = np.asarray(xs, float), np.asarray(ys, float)
        return (hull.S_crown(ys) if p.mode == "crown" else hull.S(xs, ys))

    def mat_of(i, n=(0.0, 0.0, 1.0)):
        return mats(finish(n), i, tones.shift(p, i) if glass else None)

    xs_, ys_ = [v[0] for v in p.poly], [v[1] for v in p.poly]
    mx, my = float(np.mean(xs_)), float(np.mean(ys_))
    bm = _tessellate(p, _lines(min(xs_), max(xs_), p.grid, p.xcuts), _lines(min(ys_), max(ys_), p.grid, p.rcuts))
    bm.verts.ensure_lookup_table()
    vx = np.array([v.co.x for v in bm.verts])
    vy = np.array([-v.co.y for v in bm.verts])
    depth, _, _ = p.band(vx, vy)
    vz = height(vx, vy) + p.lift - p.drop * (1.0 - np.minimum(depth, 1.0)) * (1.0 if p.banded else 0.0)
    vid = [acc.vert(x, y, z) for x, y, z in zip(vx, vy, vz)]
    vn = hull.normals(vx, vy, crown=(p.mode == "crown"))
    for f in bm.faces:
        c = f.calc_center_median()
        d, ei, et = p.band(np.array([c.x]), np.array([-c.y]))
        ids = [vid[v.index] for v in f.verts]
        if p.banded and d[0] < 1.0:
            # a bevel face: flat, in its run's tone
            fn = acc.flat_normal(ids)
            acc.face_up(ids, mat_of(tones.run(p, int(ei[0]), float(et[0]), c.x, -c.y), fn), True, [fn] * len(ids))
        else:
            ns = [vn[v.index] for v in f.verts]
            acc.face_up(ids, mat_of(tones.cell(p, c.x, -c.y), np.mean(ns, axis=0)), True, ns)
    for ed in bm.edges:
        fs = ed.link_faces
        a, b = ed.verts
        if len(fs) != 1:
            continue
        # the rim: a skirt straight down under the hull skin, facing away from the plate
        ax, ay, bx, by = a.co.x, -a.co.y, b.co.x, -b.co.y
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        d, ei, et = p.band(np.array([cx + (mx - cx) * 0.02]), np.array([cy + (my - cy) * 0.02]))
        if p.banded and d[0] < 1.0:
            wall_m = mat_of(tones.run(p, int(ei[0]), float(et[0]), cx, cy))
        else:
            wall_m = mat_of(tones.cell(p, cx + (mx - cx) * 0.02, cy + (my - cy) * 0.02))
        za = float(height([ax], [ay])[0]) - WALL
        zb = float(height([bx], [by])[0]) - WALL
        w = [acc.vert(ax, ay, float(vz[a.index])), acc.vert(bx, by, float(vz[b.index])), acc.vert(bx, by, zb),
             acc.vert(ax, ay, za)]
        fc = fs[0].calc_center_median()
        ox_, oy_ = cx - fc.x, -(cy + fc.y)             # outward, in Blender's (x, -y): edge middle minus face centre
        ex, ey = (bx - ax), -(by - ay)
        # the quad (a, b, b_low, a_low) faces (edge) x (down) = (-ey, ex, 0)
        acc.face(w if (-ey * ox_ + ex * oy_) >= 0 else list(reversed(w)), wall_m, False)
    bm.free()


def build_seams(acc, mats, hull, tones, plates):
    """A tile per sprite pixel that the plates leave open (wholly or in part), in that pixel's index."""
    n = 4
    ys, xs = np.mgrid[0:GH * n, 0:GW * n]
    Xs, Ys = (xs + 0.5) / n, (ys + 0.5) / n
    cov = np.zeros(Xs.shape, bool)
    for p in plates:
        cov |= inside_poly(p.poly, Xs, Ys)
    frac = cov.reshape(GH, n, GW, n).mean(axis=(1, 3))
    count = 0
    for r in range(GH):
        for c in range(GW):
            b = tones.base(r, c)
            if b is None or frac[r, c] > 0.999:
                continue
            quad = []
            for x, y in ((c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)):
                y = min(max(y, hull.r0 + 0.02), hull.r1 - 0.02)
                w = hull.W(y) - 0.03
                x = min(max(x, AX - w), AX + w)
                quad.append((x, y))
            if abs(poly_area(quad)) < 0.05:
                continue
            qx, qy = np.array([q[0] for q in quad]), np.array([q[1] for q in quad])
            z = hull.S(qx, qy) + BASE_LIFT
            m = mats("glow", b[1]) if b[0] == "blue" else mats("matte", b[1])
            acc.face_up([acc.vert(q[0], q[1], float(zz)) for q, zz in zip(quad, z)], m, True, list(hull.normals(qx, qy)))
            count += 1
    return count


def build_body(acc, mats, hull):
    """The closed hull under the plates: deck and bilge as S, a plain belly."""
    top_m = belly_m = mats("matte", 2)
    us = [-math.cos(math.pi * k / 28) for k in range(29)]          # denser toward the bilge
    ys, y = [hull.r0 + 0.04], hull.r0 + 0.5
    while y < hull.r1 - 0.3:
        ys.append(y)
        y += 0.75 if (y < 14 or y > 94) else 1.5      # finer where the outline turns: a round silhouette
    ys.append(hull.r1 - 0.04)
    rings = []
    for y in ys:
        w = hull.W(y)
        xs = np.array([AX + w * u for u in us])
        zs = hull.S(xs, np.full(xs.shape, y))
        top = [acc.vert(x, y, z) for x, z in zip(xs, zs)]
        bot = [acc.vert(x, y, -BELLY * z - 0.25 * (1 - abs(u)) ** 0.5) for x, z, u in zip(xs[1:-1], zs[1:-1], us[1:-1])]
        rings.append((top, bot))
    for (t0, b0), (t1, b1) in zip(rings, rings[1:]):
        for k in range(len(t0) - 1):
            acc.face([t0[k], t1[k], t1[k + 1], t0[k + 1]], top_m, True)   # y grows down the sprite (-Y in Blender): up
        lo0, lo1 = [t0[0]] + b0 + [t0[-1]], [t1[0]] + b1 + [t1[-1]]
        for k in range(len(lo0) - 1):
            acc.face([lo0[k], lo0[k + 1], lo1[k + 1], lo1[k]], belly_m, True)
    for (t, b), flip in ((rings[0], True), (rings[-1], False)):
        loop = t + list(reversed(b))
        acc.face(list(reversed(loop)) if flip else loop, belly_m, False)


def build_shell(hull, coll):
    """The ink's shell (D51): the hull's own closed shape as a coarse, smooth loft on the body's skin
    (under every plate, window and seam floor, so none of its faces shows through them). Made directly,
    not by a voxel remesh: a remeshed, decimated shell had a few folded triangles that drew as ink ticks
    on the canopy."""
    import common
    acc = Acc()
    us = [-math.cos(math.pi * k / 16) for k in range(17)]
    ys, y = [hull.r0 + 0.04], hull.r0 + 0.5
    while y < hull.r1 - 0.3:
        ys.append(y)
        y += 0.9 if (y < 14 or y > 94) else 2.5
    ys.append(hull.r1 - 0.04)
    rings = []
    for y in ys:
        w = hull.W(y)
        xs = np.array([AX + w * u for u in us])
        zs = hull.S(xs, np.full(xs.shape, y))
        top = [acc.vert(x, y, z + 0.03) for x, z in zip(xs, zs)]
        bot = [acc.vert(x, y, -BELLY * z - 0.25 * (1 - abs(u)) ** 0.5) for x, z, u in zip(xs[1:-1], zs[1:-1], us[1:-1])]
        rings.append((top, bot))
    for (t0, b0), (t1, b1) in zip(rings, rings[1:]):
        for k in range(len(t0) - 1):
            acc.face([t0[k], t1[k], t1[k + 1], t0[k + 1]], 0, True)
        lo0, lo1 = [t0[0]] + b0 + [t0[-1]], [t1[0]] + b1 + [t1[-1]]
        for k in range(len(lo0) - 1):
            acc.face([lo0[k], lo0[k + 1], lo1[k + 1], lo1[k]], 0, True)
    for (t, b), flip in ((rings[0], True), (rings[-1], False)):
        loop = t + list(reversed(b))
        acc.face(list(reversed(loop)) if flip else loop, 0, True)
    shell = acc.to_object("mothership_outline", [common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0)], coll)
    shell.data.shade_smooth()
    shell["tyrian_outline"] = True
    return shell


# ---- cutting into the eight pieces ------------------------------------------------------------------

def _cut(obj, name, cx, cy, fill, coll, suffix=""):
    import bmesh
    import bpy
    x0, y0 = cx / 12, -cy / 12
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    for co, no in (((x0 - 1, 0, 0), (-1, 0, 0)), ((x0 + 1, 0, 0), (1, 0, 0)),
                   ((0, y0 - 14 / 12, 0), (0, -1, 0)), ((0, y0 + 14 / 12, 0), (0, 1, 0))):
        cut = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                     clear_outer=True)
        if fill:
            edges = [e for e in cut["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
            if edges:
                bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
    me = bpy.data.meshes.new(name + suffix)
    bm.to_mesh(me)
    bm.free()
    for mm in obj.data.materials:
        me.materials.append(mm)
    o = bpy.data.objects.new(name + suffix, me)
    coll.objects.link(o)
    return o


def keep_normals(piece, whole, offset, fill_mat):
    """The faces a cut filled go flat (in the body's dark, `fill_mat`); every smooth corner takes the
    uncut mesh's normal there (its custom normals included), so the shading runs on across the piece
    seams."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from mathutils.interpolate import poly_3d_calc
    mesh = piece.data
    hw, hh, eps = 1.0, 14 / 12, 1e-4
    for poly in mesh.polygons:
        vs = [mesh.vertices[i].co for i in poly.vertices]
        if fill_mat is not None and (any(all(abs(v.x - b) < eps for v in vs) for b in (-hw, hw)) or
                                     any(all(abs(v.y - b) < eps for v in vs) for b in (-hh, hh))):
            poly.use_smooth = False
            poly.material_index = fill_mat
    src = whole.data
    smooth = [p.index for p in src.polygons if p.use_smooth]
    tree = BVHTree.FromPolygons([v.co.copy() for v in src.vertices], [list(src.polygons[i].vertices) for i in smooth])
    corner = src.corner_normals
    off = Vector((offset[0], offset[1], 0.0))
    normals = []
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            if not poly.use_smooth:
                normals.append(poly.normal.copy())
                continue
            # from a hair inside the face, so a corner on a crease finds its own side of it
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            co = co + (poly.center - co) * 0.03 + off
            hit, _, fi, _ = tree.find_nearest(co)
            sp_ = src.polygons[smooth[fi]]
            w = poly_3d_calc([src.vertices[v].co for v in sp_.vertices], hit)
            nn = Vector()
            for wk, lk in zip(w, sp_.loop_indices):
                nn += wk * corner[lk].vector
            normals.append(nn.normalized() if nn.length > 1e-6 else poly.normal.copy())
    mesh.normals_split_custom_set(normals)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def volume(o):
    """Signed volume of a closed mesh: positive when its faces point outward."""
    me = o.data
    v = 0.0
    for p in me.polygons:
        cs = [me.vertices[i].co for i in p.vertices]
        for k in range(1, len(cs) - 1):
            v += cs[0].dot(cs[k].cross(cs[k + 1])) / 6
    return v


def main(only=None):
    """Build the whole craft and export the pieces in `only` (default: all eight)."""
    import json
    import bpy
    import common
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection("newsh9-mothership")
    sp = Sprite()
    hull = Hull(sp)
    plates = blueprint(hull)
    tones = Tones(sp, plates)
    mats = Mats(sp)

    body_acc, skin_acc = Acc(), Acc()
    build_body(body_acc, mats, hull)
    for p in plates:
        build_plate(skin_acc, mats, hull, tones, p)
    seams = build_seams(skin_acc, mats, hull, tones, plates)
    body = body_acc.to_object("mothership-body", mats.list, coll)
    skin = skin_acc.to_object("mothership-skin", mats.list, coll)
    bpy.context.view_layer.update()

    # the ink: one smooth shell of the hull's shape (D51), cut open per piece
    shell = build_shell(hull, coll)
    bpy.context.view_layer.update()
    if volume(body) <= 0 or volume(shell) <= 0:
        raise SystemExit(f"inside-out hull: body volume {volume(body):.3f}, shell {volume(shell):.3f}")

    fill = mats.slots[("matte", 2, None)]
    groups, info = {}, {"plates": len(plates), "seam_tiles": seams, "whole_tris": tris(body) + tris(skin),
                        "shell_tris": tris(shell), "materials": len(mats.list), "pieces": {}}
    for name, cx, cy in LAYOUT:
        # each piece: its part of the closed body (cuts filled), its part of the skin (plates and seam
        # tiles: skins, cut open) and of the shell; every corner keeps the uncut craft's normal
        b = _cut(body, name, cx, cy, True, coll, "_hull")
        s = _cut(skin, name, cx, cy, False, coll)
        keep_normals(b, body, (cx / 12, -cy / 12), fill)
        keep_normals(s, skin, (cx / 12, -cy / 12), None)
        sh = _cut(shell, name, cx, cy, False, coll, "_outline")
        sh.data.shade_smooth()
        sh["tyrian_outline"] = True
        for o in (b, s, sh):
            o["tyrian_anchor"] = ANCHOR * PX
        # The skin casts no shadow (`tyrian_ground` is the game's switch for that, modelPrep.castsShadow;
        # D66, D212): the closed body under it has the same shape and casts the craft's. That halves the
        # skin's draw calls (one per material in the shadow pass too).
        s["tyrian_ground"] = True
        groups[name] = [s, b, sh]
        info["pieces"][name] = {"tris": tris(s) + tris(b), "outline_tris": tris(sh),
                                "materials": len({p.material_index for o in (s, b) for p in o.data.polygons})}
    bad = [g[2].name for g in groups.values() if len(g[2].data.polygons) == 0]
    if bad:
        raise SystemExit(f"empty outline shells: {bad}")
    for o in (body, skin, shell):
        o.hide_render = True
    bpy.context.view_layer.update()
    for name in (list(only) if only and "--all" not in argv else list(groups)):   # --all: a review build of all eight
        common.export_sprite_model(ROOT, groups[name], f"enemies/{name}", sp.pieces[name]["sprites"])
    if "--whole" in argv:   # review only: the uncut craft and its shell, to scratch
        out = Path(argv[argv.index("--whole") + 1])
        common.export_glb([skin, body], out)
    print("BUILD_INFO", json.dumps(info))


if __name__ == "__main__" and "--proto" in sys.argv:
    proto(sys.argv[sys.argv.index("--proto") + 1])
