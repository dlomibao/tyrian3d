"""The lava bubbles of newshe.shp: one smooth glass ball whose heat is painted, not modelled (D230).

Users: assembly-newshe-229.py (the big bubble, four pieces), newshe-195.py (the small one),
newshe-235.py (the clear one).

WHAT IT IS: a bubble of dark glass with fire inside, the flying kin of the lava bubbles STARGATE's
and BUBBLES' ground is made of (shapesz): a black crown, a red-hot rim that runs up to an orange and
yellow crescent on the lower right, and two to four glints. Nothing on it is a part: no cap, no
lenses, no belt. The sprite draws one ball and a tone ramp over it, a palette step or two per pixel.

HOW IT IS BUILT
- Shape: one closed spheroid. Its plan is the sprite's inner mask (D74) traced in polar form and
  low-passed; a superellipse dome over it, a shallower closed bowl under it. Smooth normals come
  from the surface's own equation, so the four pieces of the big bubble shade as one ball.
- Tone: every sprite pixel becomes a tone t (index - ramp base; the black crown below 0), the inner
  mask's tones are carried outward past the edge, and the whole is made smooth: a Gaussian of
  `sigma` px (a wider one where the tone is low), a second one ALONG the rim near it, and the top
  of the ramp stretched back to what the smoothing took off the cores. C(t) is the palette ramp
  read between its entries.
- Palette (art rule 5, D7): the surface is cut along the tone's own contours into bands, and each
  band is one `pal_<index>` material: the crown `pal_1`, lit, and the fire ramp's entries `bands`,
  each band holding the tones up to its own entry. So every region carries its sprite index (to
  within a step or two) and the hit flash moves each band to its own shade.
- Glow (D126): the fire bands glow at strength 1 (the palette colour, unlit) through an emissive
  map that only ever takes the band's colour DOWN to C(t): M = C(t) / palette[band], at most 1,
  per channel, in the band's own tile of the piece's atlas. At a band's upper edge M is 1 and the
  next band starts at the same colour, so the ramp is continuous across the cut: no step to see,
  at any size. No channel of M goes under `tint` of its strongest: the map bends the band's hue
  for the fire ramp, and under the hit flash's bank an unbounded bend drew red and yellow fringes
  (so one band per ramp entry where the hue turns fastest). The map is the sprite's tones, not a
  concept (no projection bake, rule 4), and is kept lossless; there is no AO bake, a ball has none.
- Where the paint sits: looked up at (u, v - `lean` 0.268 z), between straight down (lean 0: the
  top view is the sprite) and the game camera's ray at mid-screen (lean 1: the game's view is the
  sprite there), so neither view is off by more than about a pixel at the crown. Up and down the
  screen the camera's rays lean from about 0 to 0.6 px per px of height, so the paint drifts over
  the ball by a pixel or two more; the dome is kept low for that.
- Gloss: dielectric, faint on the crown and fainter on the fire bands (a glow under a glossy
  dielectric reads as its reflection, D173). The sprite's white spots are painted glints (glow),
  flush: highlights are not lumps (rule 2). The sprite's light comes from the upper left; the
  game's sun would put a highlight of its own below them, so the gloss is kept broad and faint.
- Underside: the closed bowl, painted like the dome above it (rule 3).
- The clear bubble (`clear`, newshe-235): the same ball in the pale ramp, with no crown, and the film
  cut out by coverage (the atlas's alpha, glTF MASK at a half) where the sprite is see-through. Its
  film is the dome alone, and its outline shell is only the strip of the bowl under the rim (a
  whole ball's inverted hull would show, dark, through every opening).

Units while building: u = sprite column edge (east), v = sprite row edge (south), z = height in
sprite px (the equator at 0). Blender X = (u - W/2) / 12, Y = (H/2 - v) / 12, Z = z / 12.

Outside Blender (numpy only) the tone and the atlas still import, for checks.
"""

import math
import sys
from pathlib import Path

import numpy as np

WT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT / "assets/blender"))
sys.path.insert(0, str(WT / "tools"))
import sprite_mask as SM  # noqa: E402  (read only: the sprite's inner mask, D74)

try:
    import bmesh
    import bpy
    import common
except ImportError:  # outside Blender: the tone and the atlas only
    bmesh = bpy = common = None

PX = 1 / 12
LEAN_GAME = math.tan(math.radians(15))  # the game camera's ray: px up the screen per px of height

DEFAULTS = dict(
    base=112,                      # the ramp's first palette index (tone 0)
    black={1: -1.2, 64: -0.6},     # indices below the ramp: the crown's black and its edge
    crown=1,                       # the crown's material index (lit, no glow)
    crown_level=-0.6,              # the crown ends where the tone rises past this (the sprite's 64)
    bands=(2, 4, 7, 8, 9, 10, 11, 13, 14, 15),  # ramp entries that get a material; each holds the tones
                                   # up to itself. One per entry where the ramp's hue turns (orange, yellow, white)
    tint=0.5,                      # no channel of the emissive map goes under this share of its strongest:
                                   # the map bends a band's hue for the fire ramp, and the hit flash puts
                                   # another bank's colours under it (without it: red and yellow fringes)
    texels=5,                      # texels per sprite px in the emissive atlas
    sigma=0.33,                    # Gaussian (sprite px) that makes the tone smooth
    soft=(0.8, 0.3, 1.8),          # ... and a wider one where the tone is low (below these tones, blended):
                                   # the crown's edge is a hard step of two near-blacks, drawn in stairs
    peak=(9.5, 1.45),              # past this tone the smooth tone is stretched by this factor: the
                                   # smoothing takes the top off the glints' cores and the crescent
    rim=(0.7, 0.9, 1.2),           # past these shares of the plan radius the tone is also smoothed
                                   # ALONG the rim, by this Gaussian (px): the rim's pixel stairs go
    harmonics=5,                   # Fourier terms kept of the traced plan: round, not lumpy
    h_top=7.0, p_top=2.3,          # the dome: height (px) and superellipse exponent
    h_bot=4.5, p_bot=2.0,          # the bowl under it
    n_theta=80, n_top=18, n_bot=4,
    lean=0.6,                      # share of the game camera's lean the paint is looked up with
    gloss=(0.45, 0.16),            # roughness, Specular IOR Level of the crown
    band_gloss=(0.5, 0.07),        # ... of the dark fire bands: sheen over a dim glow reads as dust (D173)
    hot_gloss=(0.6, 0.04),         # ... of the bands from `hot_from` on
    hot_from=7,                    # (the first band at or past this ramp entry)
    glow=1.0,                      # D126 strength of the fire bands
    core_glow=1.35,                # ... of the last band, whose tones past `core_from` rise to it:
    core_from=14.0,                # the white cores, which Neutral tone mapping would grey at 1
    shell_faces=1600,
    clear=None,                    # a clear bubble (newshe-235): the Gaussian (px) that rounds the edge of
                                   # the sprite's see-through pixels, which are cut out of the film (alpha)
)


# ---------------------------------------------------------------- sprite and tone -------------
def load_block(pieces, w, h):
    """The pieces' first frames composed in their w x h block: indices (h, w; -1 clear), colours."""
    import json
    idx = np.full((h, w), -1, dtype=int)
    colors = {}
    for name, c0, r0 in pieces:
        d = json.loads((WT / "reference" / "models" / name / "sprite.json").read_text())
        colors.update({int(k): tuple(v) for k, v in d["colors"].items()})
        for r, row in enumerate(d["frames"][0]["pixels"]):
            for c, v in enumerate(int(x) for x in row.split()):
                if v >= 0:
                    idx[r0 + r, c0 + c] = v
    return idx, colors


def _blur(a, sigma):
    r = int(3 * sigma + 1)
    x = np.arange(-r, r + 1)
    k = np.exp(-x * x / (2 * sigma * sigma))
    k /= k.sum()
    for axis in (0, 1):
        pad = [(r, r) if ax == axis else (0, 0) for ax in (0, 1)]
        p = np.pad(a, pad, mode="edge")
        a = np.apply_along_axis(lambda m: np.convolve(m, k, mode="valid"), axis, p)
    return a


def _spread(vals, known):
    """Carry the known values outward, a ring at a time (the mean of the known 8-neighbours)."""
    vals, known = vals.copy(), known.copy()
    h, w = vals.shape
    while not known.all():
        s = np.zeros((h, w))
        n = np.zeros((h, w))
        pv = np.pad(np.where(known, vals, 0.0), 1)
        pk = np.pad(known.astype(float), 1)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                s += pv[dy:dy + h, dx:dx + w]
                n += pk[dy:dy + h, dx:dx + w]
        new = (~known) & (n > 0)
        vals[new] = s[new] / n[new]
        known |= new
    return vals


def _enclosed(clear):
    """The clear pixels that cannot be reached from the picture's edge."""
    h, w = clear.shape
    seen = np.zeros((h, w), dtype=bool)
    stack = [(r, c) for r in range(h) for c in (0, w - 1)] + [(r, c) for r in (0, h - 1) for c in range(w)]
    while stack:
        r, c = stack.pop()
        if not (0 <= r < h and 0 <= c < w) or seen[r, c] or not clear[r, c]:
            continue
        seen[r, c] = True
        stack += [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
    return clear & ~seen


class Tone:
    """The sprite's smooth tone field and the palette ramp it indexes."""

    def __init__(self, idx, colors, cfg):
        self.idx, self.colors, self.cfg = idx, colors, cfg
        base, k = cfg["base"], cfg["texels"]
        m = SM.masks(idx.tolist(), colors)
        self.masks = m
        self.inner = np.array(m["inner"], dtype=bool)
        t = np.where(idx >= base, idx - base, 0).astype(float)
        for i, v in cfg["black"].items():
            t[idx == i] = v
        self.k = k
        self.plan = self.inner
        self.cover = None
        if cfg["clear"]:
            # A clear bubble: the plan is what the sprite's outline encloses, and the film is
            # cut out where the sprite is see-through. D74's border test takes the film's dark
            # pixels beside a see-through one for ink; the film keeps the inner mask and the thin
            # parts' border (`free`, the ring where it is one dark pixel wide) and leaves the rest
            # of that border clear, which is what the top-view rule measures.
            solid = (idx >= 0) | _enclosed(idx < 0)
            film = self.inner | np.array(m["free"], dtype=bool)
            # the plan: what the outline encloses, less its ink where that lies on the outside (D74)
            pad = np.pad(solid, 1)
            edge = ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
            self.plan = solid & ~(np.array(m["border"], dtype=bool) & edge)
            c = np.repeat(np.repeat((film | ~solid).astype(float), k, axis=0), k, axis=1)
            self.cover = _blur(c, cfg["clear"] * k)
            t = _spread(t, idx >= 0)  # every drawn pixel's tone counts, the dark ones too
        else:
            t = _spread(t, self.inner)
        up = np.repeat(np.repeat(t, k, axis=0), k, axis=1)
        self.field = _blur(up, cfg["sigma"] * k)
        sig, lo, hi = cfg["soft"]
        soft = _blur(up, sig * k)
        ws = np.clip((soft - lo) / (hi - lo), 0, 1)
        ws = ws * ws * (3 - 2 * ws)
        self.field = soft * (1 - ws) + self.field * ws
        self.cu, self.cv = centroid(self.plan)
        self.R = polar_trace(self.plan, self.cu, self.cv, cfg["harmonics"])
        self._smooth_rim()
        t0, gain = cfg["peak"]
        self.field = np.where(self.field > t0, np.minimum(t0 + (self.field - t0) * gain, 15.0), self.field)
        # the ramp: every entry from the sprite's colours, a missing one read between its neighbours
        have = {i - base: np.array(colors[i], dtype=float) for i in colors if base <= i < base + 16}
        ks = sorted(have)
        self.ramp = np.array([[np.interp(j, ks, [have[q][c] for q in ks]) for c in range(3)] for j in range(16)])
        self.black = np.array(colors[cfg["crown"]], dtype=float)
        self.t_black = min(min(cfg["black"].values()), -1e-6)

    def _smooth_rim(self):
        """Near the rim, average the tone along the rim (same share of the plan radius): the
        sprite draws the rim's ramp in pixel stairs and single hot pixels, which a round blur
        leaves as blotches."""
        s0, s1, sig = self.cfg["rim"]
        f, k = self.field, self.k
        yy, xx = np.mgrid[0:f.shape[0], 0:f.shape[1]]
        du, dv = (xx + 0.5) / k - self.cu, (yy + 0.5) / k - self.cv
        rho, th = np.hypot(du, dv), np.arctan2(-dv, du)
        s = rho / self.R(th)
        w = np.clip((s - s0) / (s1 - s0), 0, 1)
        w = w * w * (3 - 2 * w)
        acc, tot = np.zeros_like(f), 0.0
        step = 0.5
        n = int(3 * sig / step)
        for j in range(-n, n + 1):
            g = math.exp(-(j * step) ** 2 / (2 * sig * sig))
            th2 = th + j * step / np.maximum(rho, 1.0)
            r2 = s * self.R(th2)
            acc += g * self.at(self.cu + r2 * np.cos(th2), self.cv - r2 * np.sin(th2))
            tot += g
        self.field = f * (1 - w) + acc / tot * w

    def at(self, u, v):
        """The tone at sprite position (u, v), bilinear between texel centres."""
        f, k = self.field, self.k
        x = np.clip(np.asarray(u, dtype=float) * k - 0.5, 0, f.shape[1] - 1.001)
        y = np.clip(np.asarray(v, dtype=float) * k - 0.5, 0, f.shape[0] - 1.001)
        x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
        fx, fy = x - x0, y - y0
        return (f[y0, x0] * (1 - fx) * (1 - fy) + f[y0, x0 + 1] * fx * (1 - fy)
                + f[y0 + 1, x0] * (1 - fx) * fy + f[y0 + 1, x0 + 1] * fx * fy)

    def colour(self, t):
        """C(t), sRGB 0..255: the ramp between its entries; below 0 it runs into the crown's black."""
        t = np.asarray(t, dtype=float)
        tt = np.clip(t, 0, 15)
        lo = np.floor(tt).astype(int)
        hi = np.minimum(lo + 1, 15)
        f = (tt - lo)[..., None]
        c = self.ramp[lo] * (1 - f) + self.ramp[hi] * f
        w = np.clip(t / self.t_black, 0, 1)[..., None]
        return c * (1 - w) + self.black * w


def _lin(c):
    c = np.asarray(c, dtype=float) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def atlas(tone, box, bands):
    """The emissive atlas: one tile per fire band of `bands` over the sprite box (u0, v0, u1, v1), each
    M = C(t) / palette[band] in linear light, at most 1 (sRGB-encoded, as glTF reads an emissive
    texture). A channel the band's colour hasn't got takes the ratio of the next stronger one, so
    another bank's colours (the hit flash) are dimmed the same way. Returns (pixels h x w x 3 in 0..1, top row
    first; tiles: band -> (x0, y0) in texels; tile size)."""
    cfg, k = tone.cfg, tone.k
    u0, v0, u1, v1 = box
    tw, th = (u1 - u0) * k, (v1 - v0) * k
    t = tone.field[v0 * k:v1 * k, u0 * k:u1 * k]
    c = _lin(tone.colour(t))
    cols = 4 if len(bands) > 4 else len(bands)
    rows = -(-len(bands) // cols)
    img = np.zeros((rows * th, cols * tw, 3 if tone.cover is None else 4))
    tiles = {}
    for n, b in enumerate(bands):
        g = cfg["glow"]
        if b == cfg["bands"][-1]:  # the cores: the band glows stronger, and only its top tones use it
            g = cfg["core_glow"]
            lift = np.clip((t - cfg["core_from"]) / (15 - cfg["core_from"]), 0, 1)
            c = c * (1 + (g - 1) * lift * lift * (3 - 2 * lift))[..., None]
        p = _lin(tone.ramp[b]) * g
        m = np.empty_like(c)
        last = None
        for ch in np.argsort(-p):  # strongest channel first; one the band hasn't got follows the one before
            if p[ch] > 0.02 or last is None:
                last = np.clip(c[..., ch] / max(p[ch], 1e-6), 0, 1)
            m[..., ch] = last
        m = np.maximum(m, cfg["tint"] * m.max(axis=-1, keepdims=True))
        x0, y0 = (n % cols) * tw, (n // cols) * th
        img[y0:y0 + th, x0:x0 + tw, :3] = _srgb(m)
        if tone.cover is not None:  # the film's coverage, the same in every tile
            img[y0:y0 + th, x0:x0 + tw, 3] = tone.cover[v0 * k:v1 * k, u0 * k:u1 * k]
        tiles[b] = (x0, y0)
    return img, tiles, (tw, th)


# ---------------------------------------------------------------- plan ------------------------
def centroid(mask):
    ys, xs = np.nonzero(mask)
    return float(xs.mean() + 0.5), float(ys.mean() + 0.5)


def polar_trace(mask, cu, cv, harmonics, n=360):
    """Radius of the mask's edge round (cu, cv) per angle (east 0, north 90), low-passed to
    `harmonics` Fourier terms. Returns r(theta) for arrays."""
    h, w = mask.shape
    raw = []
    for i in range(n):
        a = 2 * math.pi * i / n
        du, dv = math.cos(a), -math.sin(a)
        t, last = 0.0, 0.0
        while t < 40:
            c, r = int(math.floor(cu + du * t)), int(math.floor(cv + dv * t))
            if 0 <= r < h and 0 <= c < w and mask[r, c]:
                last = t
            elif t > 2:
                break
            t += 0.02
        raw.append(last)
    raw = np.array(raw)
    ang = 2 * math.pi * np.arange(n) / n
    coef = [(raw.mean(), 0.0)]
    for k in range(1, harmonics + 1):
        coef.append((2 * (raw * np.cos(k * ang)).mean(), 2 * (raw * np.sin(k * ang)).mean()))

    def r(theta):
        theta = np.asarray(theta, dtype=float)
        return sum(a * np.cos(k * theta) + b * np.sin(k * theta) for k, (a, b) in enumerate(coef))
    return r


# ---------------------------------------------------------------- the ball --------------------
class Ball:
    """Vertices (position in sprite px, unit normal, tone, paint position) and convex polygons."""

    def __init__(self, tone, cfg):
        self.tone, self.cfg = tone, cfg
        self.cu, self.cv, self.R = tone.cu, tone.cv, tone.R
        self.P, self.N, self.T, self.Q = [], [], [], []
        self.polys = []  # (vertex ids, band); band -1 = the crown, else an index into cfg["bands"]
        self._mid = {}
        self._grid()

    # the surface (rho / R(theta))^p + (|z| / H)^p = 1, its own normal
    def _point(self, theta, a, top):
        c = self.cfg
        h, p = (c["h_top"], c["p_top"]) if top else (c["h_bot"], c["p_bot"])
        s = math.cos(a) ** (2 / p)
        z = h * math.sin(a) ** (2 / p) * (1 if top else -1)
        r = float(self.R(theta))
        rho = s * r
        u, v = self.cu + rho * math.cos(theta), self.cv - rho * math.sin(theta)
        d = 1e-3
        dr = float(self.R(theta + d) - self.R(theta - d)) / (2 * d)
        f_rho = p * s ** (p - 1) / r
        f_th = -p * s ** p * dr / r / max(rho, 1e-6)
        f_z = p * (abs(z) / h) ** (p - 1) / h * (1 if top else -1)
        er = (math.cos(theta), -math.sin(theta))
        et = (-math.sin(theta), -math.cos(theta))
        n = np.array([er[0] * f_rho + et[0] * f_th, er[1] * f_rho + et[1] * f_th, f_z])
        return (u, v, z), n / np.linalg.norm(n)

    def _add(self, pos, nrm):
        lean = self.cfg["lean"] * LEAN_GAME
        q = (pos[0], pos[1] - lean * pos[2])
        self.P.append(np.array(pos, dtype=float))
        self.N.append(np.array(nrm, dtype=float))
        self.Q.append(np.array(q, dtype=float))
        self.T.append(float(self.tone.at(q[0], q[1])))
        return len(self.P) - 1

    def _grid(self):
        c = self.cfg
        nt = c["n_theta"]
        ths = [2 * math.pi * j / nt for j in range(nt)]
        rings = []
        for i in range(c["n_bot"] - 1, 0, -1):  # from near the bottom pole up to near the equator
            a = (math.pi / 2) * i / c["n_bot"]
            rings.append([self._add(*self._point(th, a, False)) for th in ths])
        for i in range(c["n_top"]):  # the equator, then up to near the top pole
            a = (math.pi / 2) * i / c["n_top"]
            rings.append([self._add(*self._point(th, a, True)) for th in ths])
        bot = self._add((self.cu, self.cv, -c["h_bot"]), (0, 0, -1))
        top = self._add((self.cu, self.cv, c["h_top"]), (0, 0, 1))
        self.rings, self.equator = rings, c["n_bot"] - 1
        dome, bowl = [], []
        for n, (a, b) in enumerate(zip(rings, rings[1:])):
            for j in range(nt):
                k = (j + 1) % nt
                (bowl if n < c["n_bot"] - 1 else dome).extend([[a[j], a[k], b[k]], [a[j], b[k], b[j]]])
        for j in range(nt):
            k = (j + 1) % nt
            bowl.append([bot, rings[0][k], rings[0][j]])
            dome.append([top, rings[-1][j], rings[-1][k]])
        # a clear bubble shows no underside: its film is the dome
        self.tris = dome if c["clear"] else bowl + dome

    def mid(self, i, j, f, tag):
        key = (min(i, j), max(i, j), tag)
        if key not in self._mid:
            if i > j:
                i, j, f = j, i, 1 - f
            n = self.N[i] * (1 - f) + self.N[j] * f
            self.P.append(self.P[i] * (1 - f) + self.P[j] * f)
            self.N.append(n / np.linalg.norm(n))
            self.Q.append(self.Q[i] * (1 - f) + self.Q[j] * f)
            self.T.append(self.T[i] * (1 - f) + self.T[j] * f)
            self._mid[key] = len(self.P) - 1
        return self._mid[key]

    def split(self, poly, val, level, tag):
        """A convex polygon cut where `val(vertex)` crosses `level`: (the part below, the part above)."""
        lo, hi = [], []
        n = len(poly)
        for k in range(n):
            i, j = poly[k], poly[(k + 1) % n]
            vi, vj = val(i), val(j)
            if vi <= level:
                lo.append(i)
            if vi >= level:
                hi.append(i)
            if (vi < level < vj) or (vj < level < vi):
                m = self.mid(i, j, (level - vi) / (vj - vi), tag)
                lo.append(m)
                hi.append(m)
        return (lo if self._area(lo) else None), (hi if self._area(hi) else None)

    def _area(self, poly):
        if len(poly) < 3:
            return False
        p = [self.P[i] for i in poly]
        a = sum((np.linalg.norm(np.cross(p[k] - p[0], p[k + 1] - p[0])) for k in range(1, len(p) - 1)), 0.0)
        return a > 1e-7

    def cut_bands(self):
        """Cut every triangle along the tone's contours into the crown and the fire bands."""
        c = self.cfg
        levels = [c["crown_level"]] + [b - 0.1 for b in c["bands"][:-1]]
        tone = lambda i: self.T[i]  # noqa: E731
        for tri in self.tris:
            cur = tri
            for n, lv in enumerate(levels):
                lo, cur = self.split(cur, tone, lv, ("t", n))
                if lo:
                    self.polys.append((lo, n - 1))
                if not cur:
                    break
            if cur:
                self.polys.append((cur, len(levels) - 1))

    def clip(self, u0, v0, u1, v1):
        """The polygons inside the sprite box, cut at its sides; and the cut's loops per side."""
        out = []
        for poly, band in self.polys:
            cur = poly
            for axis, level, keep_hi in ((0, u0, True), (0, u1, False), (1, v0, True), (1, v1, False)):
                lo, hi = self.split(cur, lambda i, a=axis: self.P[i][a], level, ("c", axis, level))
                cur = hi if keep_hi else lo
                if not cur:
                    break
            if cur:
                out.append((cur, band))
        return out


def _cut_caps(ball, polys, box):
    """Flat faces closing a piece where it was cut from the ball: per cut side, the chain of edges
    lying in that side, closed and fanned from its middle. Returns [(points, normal)]."""
    u0, v0, u1, v1 = box
    caps = []
    for axis, level, sign in ((0, u0, -1), (0, u1, 1), (1, v0, -1), (1, v1, 1)):
        on = lambda i: abs(ball.P[i][axis] - level) < 1e-6  # noqa: E731
        edges = {}
        for poly, _ in polys:
            for k in range(len(poly)):
                i, j = poly[k], poly[(k + 1) % len(poly)]
                if i != j and on(i) and on(j):
                    edges[(min(i, j), max(i, j))] = edges.get((min(i, j), max(i, j)), 0) + 1
        edges = [e for e, n in edges.items() if n == 1]
        if len(edges) < 2:
            continue
        pts = sorted({i for e in edges for i in e})
        mid = np.mean([ball.P[i] for i in pts], axis=0)
        nrm = np.zeros(3)
        nrm[axis] = sign
        tris = []
        for i, j in edges:
            a, b = ball.P[i], ball.P[j]
            if np.dot(np.cross(a - mid, b - mid), nrm) < 0:
                a, b = b, a
            tris.append((mid, a, b))
        # the open side of the chain (the piece's inner corner line): close it too
        ends = [i for i in pts if sum(i in e for e in edges) == 1]
        if len(ends) == 2:
            a, b = ball.P[ends[0]], ball.P[ends[1]]
            if np.dot(np.cross(a - mid, b - mid), nrm) < 0:
                a, b = b, a
            tris.append((mid, a, b))
        caps.append((tris, nrm))
    return caps


# ---------------------------------------------------------------- Blender ---------------------
def _to_blender(p, w, h):
    return ((p[0] - w / 2) * PX, (h / 2 - p[1]) * PX, p[2] * PX)


def _mesh(name, ball, polys, caps, mats, uv_of, size, origin=(0.0, 0.0)):
    """A mesh of the polygons (smooth, the ball's normals) and the cut caps (flat, the crown).
    `mats`: {band (-1 the crown): material}; a band without one takes the crown's."""
    w, h = size
    used = sorted({i for poly, _ in polys for i in poly})
    remap = {i: n for n, i in enumerate(used)}
    verts = [_to_blender(ball.P[i], w, h) for i in used]
    norms = [(ball.N[i][0], -ball.N[i][1], ball.N[i][2]) for i in used]
    faces, fmat, fuv = [], [], []
    keys = sorted(mats)
    slot = {b: n for n, b in enumerate(keys)}
    for poly, band in polys:
        faces.append([remap[i] for i in poly])
        fmat.append(slot.get(band, 0))
        fuv.append([uv_of(ball.Q[i], band) if uv_of else (0.0, 0.0) for i in poly])
    for tris, nrm in caps:
        for tri in tris:
            base = len(verts)
            verts += [_to_blender(p, w, h) for p in tri]
            norms += [(nrm[0], -nrm[1], nrm[2])] * 3
            faces.append([base, base + 1, base + 2])
            fmat.append(0)
            fuv.append([(0.0, 0.0)] * 3)
    verts = [(x - origin[0], y - origin[1], z) for x, y, z in verts]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for b in keys:
        me.materials.append(mats[b])
    me.polygons.foreach_set("material_index", fmat)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    uv = me.uv_layers.new(name="paint")
    k = 0
    for f in fuv:
        for q in f:
            uv.data[k].uv = q
            k += 1
    me.update()
    # winding: outward (the ball's normals); flip any face wound the other way
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    for f in bm.faces:
        n = np.mean([norms[v.index] for v in f.verts], axis=0)
        if f.normal.dot(n) < 0:
            f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.normals_split_custom_set_from_vertices(norms)
    return me


def _materials(tone, cfg, tag, image, bands):
    """The crown (lit) and one glowing material per fire band of `bands`, its emission through the
    atlas. Returns {band or -1 for the crown: material}."""
    sprite_d = {"name": tag, "colors": {str(k): list(v) for k, v in tone.colors.items()}}
    base = cfg["base"]
    for b in cfg["bands"]:  # a ramp entry the sprite itself never uses still names its band
        sprite_d["colors"].setdefault(str(base + b), [int(round(x)) for x in tone.ramp[b]])
    r0, s0 = cfg["gloss"]
    crown = common.palette_material(sprite_d, cfg["crown"], f"{tag}_crown", metallic=0.0, roughness=r0)
    _bsdf(crown).inputs["Specular IOR Level"].default_value = s0
    mats = {-1: crown}
    for b in bands:
        r, s = cfg["hot_gloss"] if b >= cfg["hot_from"] else cfg["band_gloss"]
        glow = cfg["core_glow"] if b == cfg["bands"][-1] else cfg["glow"]
        m = common.palette_material(sprite_d, base + b, f"{tag}_fire{b}", metallic=0.0, roughness=r,
                                    emission_strength=glow)
        bsdf = _bsdf(m)
        bsdf.inputs["Specular IOR Level"].default_value = s
        nt = m.node_tree
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "paint"
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = image
        tex.extension = "EXTEND"
        nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(tex.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = tuple(bsdf.inputs["Emission Color"].default_value)
        nt.links.new(mul.outputs[2], bsdf.inputs["Emission Color"])
        if tone.cover is not None:
            # the film's coverage, cut at a half (glTF alphaMode MASK: the game draws no blended models)
            cut = nt.nodes.new("ShaderNodeMath")
            cut.operation = "ROUND"
            nt.links.new(tex.outputs["Alpha"], cut.inputs[0])
            nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
            # glTF reads coverage from the base colour texture: the same image there (its colour
            # does nothing, a glow of 1 leaves no lit colour), so the glb holds the atlas once
            lit = nt.nodes.new("ShaderNodeMix")
            lit.data_type = "RGBA"
            lit.blend_type = "MULTIPLY"
            lit.inputs[0].default_value = 1.0
            nt.links.new(tex.outputs["Color"], lit.inputs[6])
            lit.inputs[7].default_value = tuple(bsdf.inputs["Base Color"].default_value)
            nt.links.new(lit.outputs[2], bsdf.inputs["Base Color"])
        mats[b] = m
    return mats


def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _image(name, img):
    h, w, ch = img.shape
    im = bpy.data.images.new(name, w, h, alpha=ch == 4)
    if ch == 4:
        im.alpha_mode = "CHANNEL_PACKED"  # the colour is not premultiplied by the coverage
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :ch] = img[::-1]  # a byte image's pixels are its stored (sRGB-encoded) values, bottom row first
    im.pixels.foreach_set(rgba.ravel())
    im.pack()
    return im


def _split_shell(shell, layout, coll):
    """The whole ball's outline shell cut open at the pieces' boxes (no caps: a cap would ink the seam)."""
    out = {}
    for name, cx, cy in layout:
        x0, y0 = cx * PX, -cy * PX
        bm = bmesh.new()
        bm.from_mesh(shell.data)
        bmesh.ops.transform(bm, matrix=shell.matrix_world, verts=bm.verts)
        hw, hh = 1.0, 14 / 12
        for co, no in (((x0 - hw, 0, 0), (-1, 0, 0)), ((x0 + hw, 0, 0), (1, 0, 0)),
                       ((0, y0 - hh, 0), (0, -1, 0)), ((0, y0 + hh, 0), (0, 1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=(-x0, -y0, 0), verts=bm.verts)
        me = bpy.data.meshes.new(name + "_outline")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(shell.data.materials[0])
        me.shade_smooth()
        o = bpy.data.objects.new(name + "_outline", me)
        coll.objects.link(o)
        o["tyrian_outline"] = True
        out[name] = o
    return out


def _rim_shell(ball, name, coll, size):
    """A clear bubble's outline shell: only the strip of the bowl under the rim. The game's ink is
    the shell's back faces pushed out (an inverted hull); a whole ball's would show, dark, through
    every opening in the film. Seen from above this strip lies under the film's own ring."""
    w, h = size
    a, b = ball.rings[ball.equator - 1], ball.rings[ball.equator]
    ids = a + b
    n = len(a)
    verts = [_to_blender(ball.P[i], w, h) for i in ids]
    norms = [(ball.N[i][0], -ball.N[i][1], ball.N[i][2]) for i in ids]
    faces = [[j, (j + 1) % n, n + (j + 1) % n, n + j] for j in range(n)]
    me = bpy.data.meshes.new(name + "_outline")
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    for f in bm.faces:
        if f.normal.dot(np.mean([norms[v.index] for v in f.verts], axis=0)) < 0:
            f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.normals_split_custom_set_from_vertices(norms)
    me.materials.append(common.material("outline_shell", (0.0, 0.0, 0.0), roughness=1.0))
    shell = bpy.data.objects.new(name + "_outline", me)
    coll.objects.link(shell)
    shell["tyrian_outline"] = True
    return shell


def _export(objects, path):
    """common.export_glb, with the atlas kept exact: a WebP at quality 100 is lossless (at 85 its
    error, up to a fifth of a dark texel, showed as steps where two bands meet)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        if obj is not None:
            obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True,
                              export_apply=True, export_cameras=False, export_lights=False, export_extras=True,
                              export_image_format="WEBP", export_image_quality=100)
    return path


def build(script_file, name, pieces, size, **over):
    """Build the bubble `name` from its pieces [(piece, column, row)] in a size = (w, h) block and
    export one model per piece (the game contract: each at its own centre, its sprites registered).
    Options after `--`: --out DIR writes the glbs there instead (no spriteModels entry); --debug DIR
    saves the smooth sprite C(t) and each piece's atlas as PNGs."""
    import json
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    cfg = dict(DEFAULTS, **over)
    root = common.repo_root(script_file)
    w, h = size
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(name)
    idx, colors = load_block(pieces, w, h)
    tone = Tone(idx, colors, cfg)
    ball = Ball(tone, cfg)
    ball.cut_bands()
    k = tone.k
    dbg = Path(argv[argv.index("--debug") + 1]) if "--debug" in argv else None

    def save(fn, px):
        dbg.mkdir(parents=True, exist_ok=True)
        im = _image("dbg", px)
        im.filepath_raw = str(dbg / fn)
        im.file_format = "PNG"
        im.save()
        bpy.data.images.remove(im)

    if dbg:
        save(f"{name}_field.png", tone.colour(tone.field) / 255)
    # the whole ball, bare: the outline shell is made from it (D51, D90), before the cut
    plain = common.palette_material({"name": name, "colors": {str(i): list(c) for i, c in colors.items()}},
                                    cfg["crown"], f"{name}_plain")
    whole = bpy.data.objects.new(f"{name}_whole", _mesh(f"{name}_whole", ball, ball.polys, [], {-1: plain}, None, size))
    coll.objects.link(whole)
    zs = [p[2] for p in ball.P]
    print(f"{name}: centre {ball.cu:.2f},{ball.cv:.2f}, {len(whole.data.polygons)} faces, "
          f"{sum(len(p.vertices) - 2 for p in whole.data.polygons)} tris, z {min(zs):.2f}..{max(zs):.2f} px, faces per band "
          f"{[sum(1 for _, b in ball.polys if b == n) for n in range(-1, len(cfg['bands']))]}")
    shell = _rim_shell(ball, name, coll, size) if cfg["clear"] else common.outline_shell(whole, coll, faces=cfg["shell_faces"])
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    single = len(pieces) == 1
    layout = [(pn, c0 + 12 - w / 2, r0 + 14 - h / 2) for pn, c0, r0 in pieces]
    shells = {pieces[0][0]: shell} if single else _split_shell(shell, layout, coll)
    ys, xs = np.nonzero(idx >= 0)
    for (pn, c0, r0), (_, cx, cy) in zip(pieces, layout):
        pbox = (c0, r0, c0 + 24, r0 + 28)
        polys = ball.polys if single else ball.clip(*pbox)
        caps = [] if single else _cut_caps(ball, polys, pbox)
        # the piece's own atlas: its part of the sprite and a margin for the lean and the filter,
        # the bands it has
        box = (int(max(0, pbox[0] - 3, xs.min() - 3)), int(max(0, pbox[1] - 3, ys.min() - 3)),
               int(min(w, pbox[2] + 3, xs.max() + 4)), int(min(h, pbox[3] + 3, ys.max() + 4)))
        bands = [b for n, b in enumerate(cfg["bands"]) if any(pb == n for _, pb in polys)]
        img, tiles, (tw, th) = atlas(tone, box, bands)
        ih, iw, _ = img.shape
        if dbg:
            save(f"{pn}_atlas.png", img)
        mats = _materials(tone, cfg, pn, _image(f"{pn}_fire", img), bands)

        def uv_of(q, band):
            if band < 0:
                return (0.0, 0.0)
            x0, y0 = tiles[cfg["bands"][band]]
            x = x0 + min(max((q[0] - box[0]) * k, 0.5), tw - 0.5)
            y = y0 + min(max((q[1] - box[1]) * k, 0.5), th - 0.5)
            return (x / iw, 1 - y / ih)

        by_band = {-1: mats[-1], **{n: mats[b] for n, b in enumerate(cfg["bands"]) if b in mats}}
        me = _mesh(pn, ball, polys, caps, by_band, uv_of, size, origin=(cx * PX, -cy * PX))
        obj = bpy.data.objects.new(pn, me)
        coll.objects.link(obj)
        s = shells[pn]
        print(f"piece {pn}: {sum(len(q.vertices) - 2 for q in obj.data.polygons)} tris, shell {len(s.data.polygons)}, "
              f"bands {[cfg['base'] + b for b in bands]}, atlas {iw}x{ih}")
        if out_dir:
            print("exported", _export([obj, s], out_dir / f"{pn}.glb"))
        else:
            # the game contract, as common.export_sprite_model: the model at its own centre, its sprites registered
            model = f"enemies/{pn}"
            out = _export([obj, s], root / "public" / "models" / f"{model}.glb")
            entry = root / "src" / "render" / "spriteModels" / f"{pn}.json"
            entry.write_text(json.dumps({"model": model, "sprites": common.load_sprite(root, pn)["sprites"]}, indent=1) + "\n")
            print(f"exported {out} ({out.stat().st_size} bytes, {len(obj.data.polygons)} faces) and {entry}")
    whole.hide_render = True
    return ball
