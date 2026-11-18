"""The clear bubble (newshe.shp frame 235, 24 x 28 px, one frame): the lava bubbles' pale, see-through
kin, one round ball of film with its tones painted on it (D230; lib_bubble.py has the method).

WHAT IT IS: a bubble, not a machine (types 479 and 687: armour 1, no gun; they rise in swarms in
3.7 STARGATE and with the red bubbles in 1.4 BUBBLES, the BONUS levels, 2.9 MISTAKES and 3.6
FLEET). The sprite is the red bubbles' drawing in the pale ramp (palette 64-79), 16 px across, and
most of its inside is clear: 47 of the pixels its outline encloses are transparent, and the level
shows through them. What is drawn is the film: a ring one pixel wide (67 on the left, near-black
64-65 on the upper right), which widens to a crescent three pixels wide from the south to the east
(64-65 inside, a pale pink line 73-77 a pixel inside its edge), a pink-white glint (peak 79) and
two small dots beside it. The other dark pixels inside the ring (64-66 and 16, each beside a
see-through pixel) are the drawing's ink round those shapes (D74's border), not film.

HOW IT IS BUILT (round 3 of the walkthrough fixes; everything here is local to this script, the
shared lib_bubble.py is only read)
- A real ball, drawn in the sprite's own view. The ball is round (15.7 px across, 7.5 px of dome
  over 7.5 px of bowl), where the red bubbles are low domes: under the tilted camera a tall dome
  leans (0 to 0.6 px per px of height) and its paint drifts. So this one is drawn in the art's view
  (obliqueView.ts, D82/D165): `tyrian_oblique` 0.001 puts every vertex on the camera ray through its
  own place on the plan, so the game's picture is the top view at every place on the screen, at
  every camera, and `tyrian_depth_band` gives it its depth: a thin band 12.4-13 px over its base,
  dome-shaped inside it. A bubble drawn after another model is therefore over it, as the C drew it
  (a banded model takes no D181 lift, so the band itself has to clear what it is drawn over: the
  big bubble's top is 7 px, the tallest ship it crosses, MISTAKES' newsh2-267, 12 px), and a model
  drawn after it that covers it is lifted over the band by D181. Nothing interpenetrates: the
  jagged slivers were the low film dome and a red dome cutting through each other.
- The film is geometry, and its shape is drawn, not blurred from the pixels: a band inside the
  plan's edge (the ring, MIN_WIDTH wide, and the crescent, whose inner edge is one fitted circle),
  the glint as one ellipse and the two dots as small ones. The dome's faces are cut along that
  outline (each crossing found on the mesh's edges) and the rest of the dome is left out: one
  clean opening with three islands, its edges smooth at any size and anti-aliased as any mesh edge
  (the alpha test this replaces drew them in screen-pixel stairs). The ink pixels round the shapes
  are left clear (the rule's inner mask). Opaque materials: no alpha, no blending.
- Tone: every film pixel's tone, smoothed (a Gaussian, and along the rim in the band), then
  corrected so each sprite pixel keeps its own mean light: the smoothing takes the top off
  one-pixel lines (the pale line in the crescent is one pixel wide), which read 20-25% dark and
  copper. The emissive map also holds what three's Neutral tone mapping will take off again (its
  toe, 0.04 off every channel: the pale ramp lost its green and blue and read copper-brown; and
  its shoulder past 0.76), so each pixel shows the sprite's palette colour (within 3 of 255 along
  the ramp, 7 at its white end). The bands glow at 6 to leave room for that under the map's 1.
- From the side it is a closed ball: the bowl is whole (the rim's tones fading down from the
  equator to dark film, painted by tone from a ramp strip in each band's tile), and the dome is
  lined (the far wall's inner face, dark film). Both face away from the top view and every material
  is single-sided, so the game's view never shows them: through the openings the level shows, as
  before. (The viewer and Blender show the ball standing, as every model drawn in the art's view.)
- Ink: the outline shell is a strip inside the rim, only along the arc where the sprite's own edge
  is ink (the near-black upper right, 87 degrees); the game's ink is that strip pushed out, onto
  the sprite's ink pixels. The band stops a pixel inside the edge there (the crescent's horn runs
  on inside the ink, as drawn, to a round end) and a strip of dark film a third of a pixel wide
  keeps the edge itself, so the ball's belt is whole. Where the sprite draws colour to its edge
  (the pale rim, the left side's 67) there is no shell and no dark line.
- Measured (the exported glb, shell left out, straight down, 16 px per sprite px): the rule's
  IoU on the sprite's grid 0.969 (93 of the 94 inner pixels; three off: the ink-only island and
  two ink pixels of the outline's stair in the pale rim, which a round edge covers).

Run: tools/build-models.sh -j 2 assets/blender/enemies/newshe-235.py
or: blender --background --factory-startup --python newshe-235.py -- [--out DIR] [--debug DIR]
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_bubble as LB  # noqa: E402  (read only)

try:
    import bmesh
    import bpy
    import common
except ImportError:  # outside Blender: the film, the tone and the atlas only (checks)
    bmesh = bpy = common = None

NAME = "newshe-235"
SIZE = (24, 28)
PX = LB.PX

CFG = dict(
    LB.DEFAULTS,
    base=64, black={16: 0.0}, crown=64, crown_level=-99.0,  # no crown: the ramp's own dark is the film
    bands=(2, 4, 7, 8, 9, 10, 11, 13, 14, 15),
    texels=6,
    sigma=(0.36, 0.25, 1.0),     # px: the Gaussian that makes the tone smooth (the glint and the dots; the band),
                                 # and the one ALONG the rim in the band
    harmonics=4,                 # Fourier terms of the plan: round
    lean=0.0,                    # the paint is looked up straight down: the game draws the top view
    h_top=7.5, p_top=2.0, h_bot=7.5, p_bot=2.0,   # a ball
    n_theta=72, n_top=18, n_bot=8,
    glow=6.0, core_glow=6.0,     # band strength: room for the toe's and the shoulder's lift under the map's 1
    tint=0.2,                    # no channel of the map under this share of its strongest (the hit flash's bound)
    band_gloss=(0.5, 0.05), hot_gloss=(0.55, 0.04),
    clear=None,                  # (lib_bubble's alpha-cut film is not used: the film is cut from the mesh)
)
CRESCENT = 1.6        # px: where the band is wider than this in the sprite it is the crescent
INK_DROP = 1.0        # px: how far inside the plan's edge the film's outer edge lies along the ink arc (the ink's pixel)
MIN_WIDTH = 0.92      # px: the ring's width
DOT_MIN = 0.62        # px: least semi-axis of an island
MEAN_ROUNDS = 12      # rounds of the correction that keeps each sprite pixel's mean light
MEAN_ALONG = 1.5      # px: the Gaussian along the rim that the correction is averaged with in the band
TOE = 0.04            # three's NeutralToneMapping toe (src/render/lighting.ts NEUTRAL_TOE)
SHOULDER = 0.76       # ... and where its compression starts
PEAK = 0.94           # the brightest a channel is asked to show (the shoulder never reaches 1)
RISE = 4.5            # px: the equator's height over the model's base (the bowl's bottom 3 px under it, as the red bubble's)
BAND = (12.4, 13.0)   # px over the base: the depth band the dome is drawn in. Over the models it is drawn after in
                      # its pass (the big bubble's top is 7 px, MISTAKES' newsh2-267 12 px) and under the next
                      # pass but one (the sky enemies' base is 14.4 px over the ground enemies')
OBLIQUE = 0.001       # tyrian_oblique: (nearly) straight down
INK_LUMA = 26         # sprite_mask.INK_LUMA
INK_FILM = 0.36       # px: the width of the dark film at the plan's edge along the ink arc (under half the ink's pixel)
INK_STRIP = (1.55, 0.95, 0.8)  # px: the shell strip's two radii inside the plan's edge, and its height (the game's
                               # ink is that strip pushed out 0.5 px: from the horn's edge to the dark film)
LINING = (36, 6, 0.06)  # the lining's segments and rings, and how far inside the film it lies (px)
STRIP = 8             # texels: the height of each tile's ramp strip (its top rows, which the film's paint never
                      # reaches): the band's map over the whole ramp, tone 0 at the left, 15 at the right
BOWL_FADE = 0.6       # the bowl's tone is the rim's, fading to dark film by this share of its depth


# ---------------------------------------------------------------- the film ---------------------
def _components(mask):
    """8-connected components of a bool mask, as a list of bool masks."""
    h, w = mask.shape
    seen = np.zeros_like(mask)
    out = []
    for r0 in range(h):
        for c0 in range(w):
            if not mask[r0, c0] or seen[r0, c0]:
                continue
            comp = np.zeros_like(mask)
            stack = [(r0, c0)]
            while stack:
                r, c = stack.pop()
                if not (0 <= r < h and 0 <= c < w) or seen[r, c] or not mask[r, c]:
                    continue
                seen[r, c] = comp[r, c] = True
                stack += [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
            out.append(comp)
    return out


class FilmTone(LB.Tone):
    """The clear bubble's film: its plan (the sprite's whole outline), its outline (drawn shapes,
    `phi`) and its tone (each sprite pixel's mean light kept)."""

    def __init__(self, idx, colors, cfg):  # noqa: super().__init__ is not called: the film is made here
        self.idx, self.colors, self.cfg = idx, colors, cfg
        base, k = cfg["base"], cfg["texels"]
        self.k = k
        m = LB.SM.masks(idx.tolist(), colors)
        self.masks = m
        self.inner = inner = np.array(m["inner"], dtype=bool)
        opaque = idx >= 0
        solid = opaque | LB._enclosed(idx < 0)
        self.solid = solid
        pad = np.pad(solid, 1)
        edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        # the film's pixels: the rule's inner mask, and the outline's own ring where it is ink (so the
        # ring is whole); the parts of the inner mask that do not reach the outline are islands
        band = edge & opaque
        self.islands = []
        for c in _components(inner):
            if (c & edge).any():
                band = band | c
            elif max(LB.SM.luma(colors[int(i)]) for i in idx[c]) >= INK_LUMA:
                self.islands.append(c)  # (an island of ink alone, one near-black pixel inside the upper right's ring, is left out)
        self.band = band
        self.film = band.copy()
        for c in self.islands:
            self.film |= c
        # the plan: the sprite's whole outline, round
        self.plan = solid
        self.cover = None
        self.cu, self.cv = LB.centroid(solid)
        self.R = LB.polar_trace(solid, self.cu, self.cv, cfg["harmonics"])
        self.ink = self._ink_arc(edge & opaque)
        self.R_in = self._inner_edge()
        self.ellipses = [self._ellipse(c) for c in self.islands]
        # the ramp: every entry from the sprite's colours, a missing one read between its neighbours
        have = {i - base: np.array(colors[i], dtype=float) for i in colors if base <= i < base + 16}
        ks = sorted(have)
        self.ramp = np.array([[np.interp(j, ks, [have[q][c] for q in ks]) for c in range(3)] for j in range(16)])
        self.black = np.array(colors[cfg["crown"]], dtype=float)
        self.t_black = min(min(cfg["black"].values()), -1e-6)
        self._geo = None
        self.field = self._tone()

    # -- shape --
    def _inner_edge(self, n=720):
        """The inner edge of the band per angle. Where the band is the crescent (wider than
        CRESCENT px in the sprite) its inner edge is one circle, fitted to the radii where rays
        from the plan's edge inward first leave the band's pixels: a crescent is a round edge
        inside a round edge. Elsewhere the band is the ring, MIN_WIDTH wide."""
        h, w = self.band.shape
        pts, wide = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            du, dv = math.cos(a), -math.sin(a)
            t = float(self.R(a)) + 1.5
            inside, last = False, 0.0
            while t > 0:
                c, r = int(math.floor(self.cu + du * t)), int(math.floor(self.cv + dv * t))
                on = 0 <= r < h and 0 <= c < w and self.band[r, c]
                if on:
                    inside, last = True, t
                elif inside:
                    break
                t -= 0.02
            if float(self.R(a)) - last > CRESCENT:
                pts.append((self.cu + du * last, self.cv + dv * last))
                wide.append(i)
        pts = np.array(pts)
        # the crescent's end inside the ink arc (its horn): the last angle the sprite draws it at
        ink = [i for i in wide if self.ink[int(i * 360 / n) % 360]]
        self.horn = 2 * math.pi * (max(ink) + 1) / n if ink else None
        # the circle through the points, by least squares (x^2 + y^2 = 2 a x + 2 b y + c)
        sol = np.linalg.lstsq(np.c_[2 * pts, np.ones(len(pts))], (pts ** 2).sum(axis=1), rcond=None)[0]
        ox, oy = sol[0] - self.cu, sol[1] - self.cv
        rad = math.sqrt(sol[2] + sol[0] ** 2 + sol[1] ** 2)
        self.inner_circle = (float(sol[0]), float(sol[1]), rad)

        def r_in(th):
            th = np.asarray(th, dtype=float)
            along = ox * np.cos(th) - oy * np.sin(th)  # the circle's centre along the ray
            disc = rad * rad - (ox * ox + oy * oy) + along * along
            t = along + np.sqrt(np.maximum(disc, 0.0))
            return np.minimum(np.where(disc > 0, t, 1e3), self.R(th) - MIN_WIDTH)
        return r_in

    def _ink_at(self, th):
        """0 outside the ink arc, 1 inside it, its ends over a few degrees."""
        deg = np.degrees(np.mod(th, 2 * math.pi))
        return np.interp(deg, np.arange(361), np.append(self.ink_soft, self.ink_soft[0]))

    def _ellipse(self, comp):
        """An island as an ellipse of its pixels' moments and area: (cu, cv, axis matrix, mean semi-axis)."""
        ys, xs = np.nonzero(comp)
        cu, cv = xs.mean() + 0.5, ys.mean() + 0.5
        d = np.stack([xs - xs.mean(), ys - ys.mean()]).astype(float)
        cov = d @ d.T / len(xs) + np.eye(2) / 12  # the pixels' moments, each pixel a square
        val, vec = np.linalg.eigh(cov)
        ax = 2 * np.sqrt(val)  # a uniform ellipse's semi-axes
        ax *= math.sqrt(len(xs) / (math.pi * ax[0] * ax[1]))  # ... at the island's area
        ax = np.maximum(ax, DOT_MIN)
        return cu, cv, vec @ np.diag(1 / ax) @ vec.T, float(math.sqrt(ax[0] * ax[1]))

    def _ink_arc(self, ring, n=360):
        """Per degree (east 0, north 90): whether the outline's own pixel there is ink, in runs of 30
        degrees or more (the near-black upper right): where the game's ink outline is drawn."""
        h, w = ring.shape
        raw = np.zeros(n, dtype=bool)
        for i in range(n):
            a = 2 * math.pi * i / n
            du, dv = math.cos(a), -math.sin(a)
            t = float(self.R(a)) + 1.5
            while t > 0:
                c, r = int(math.floor(self.cu + du * t)), int(math.floor(self.cv + dv * t))
                if 0 <= r < h and 0 <= c < w and ring[r, c]:
                    raw[i] = LB.SM.luma(self.colors[int(self.idx[r, c])]) < INK_LUMA
                    break
                t -= 0.02
        out = np.zeros(n, dtype=bool)
        start = next((i for i in range(n) if not raw[i]), None)  # begin outside a run (runs may cross 0)
        if start is None:
            return ~out
        i = 0
        while i < n:
            if raw[(start + i) % n]:
                j = i
                while j < n and raw[(start + j) % n]:
                    j += 1
                if j - i >= 30:
                    for q in range(i, j):
                        out[(start + q) % n] = True
                i = j
            else:
                i += 1
        soft = out.astype(float)  # the arc's ends over a few degrees
        g = np.exp(-np.arange(-6, 7) ** 2 / (2 * 1.5 ** 2))
        self.ink_soft = np.convolve(np.concatenate([soft[-13:], soft, soft[:13]]), g / g.sum(), mode="same")[13:-13]
        return out

    def phi(self, u, v):
        """The film's outline: about the distance (px) inside the film at sprite position (u, v),
        negative in the openings. (The plan's own edge is the mesh's.) The film is
        - the band inside the plan's edge, from its inner edge (R_in) out. Along the ink arc, where
          the outline's own pixel is the game's ink, the band stops a pixel inside the plan's edge:
          there the ring is ink, and the crescent's horn runs on inside it to where the sprite ends
          it, with a round end;
        - along the ink arc, a strip of (dark) film INK_FILM wide at the plan's edge: with the ink
          inside it, the sprite's dark ring, and from the side the ball's belt stays whole;
        - the islands (the glint and the dots), ellipses."""
        u, v = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
        du, dv = u - self.cu, v - self.cv
        rho, th = np.hypot(du, dv), np.arctan2(-dv, du)
        big, r_in, ink = self.R(th), self.R_in(th), self._ink_at(th)
        f = np.minimum(rho - r_in, big + 1.0 - (1.0 + INK_DROP) * ink - rho)
        if self.horn is not None:
            # the horn's round end: a half disc as wide as the horn, its tip at the horn's last angle
            r0, r1 = float(self.R_in(self.horn)), float(self.R(self.horn)) - INK_DROP
            mid, half = (r0 + r1) / 2, max((r1 - r0) / 2, 0.05)
            c = self.horn - half / mid  # the disc's centre
            past = np.mod(th - c + math.pi, 2 * math.pi) - math.pi  # angle past the centre
            cap = half - np.hypot(past * mid, rho - mid)
            f = np.where((ink > 0.5) & (past > 0), np.minimum(f, cap), f)
        f = np.maximum(f, np.minimum(rho - (big - INK_FILM), (ink - 0.5) * 4.0))
        for cu, cv, mat, mean in self.ellipses:
            d = np.stack([u - cu, v - cv], axis=-1) @ mat
            f = np.maximum(f, (1 - np.hypot(d[..., 0], d[..., 1])) * mean)
        return f

    def shown(self):
        """What the game draws of the film, at the atlas's texels: inside the plan and the outline."""
        k = self.k
        h, w = self.idx.shape
        yy, xx = np.mgrid[0:h * k, 0:w * k]
        u, v = (xx + 0.5) / k, (yy + 0.5) / k
        du, dv = u - self.cu, v - self.cv
        return (self.phi(u, v) >= 0) & (np.hypot(du, dv) <= self.R(np.arctan2(-dv, du)))

    # -- tone --
    def _smooth(self, t_px):
        """The pixels' tones made smooth: a Gaussian (a narrower one in the band, whose pale line is
        one pixel wide), and in the band the tone is also averaged ALONG the rim (at the same share
        of the plan radius), so the pixel stairs of the line and its single hot pixels go."""
        k = self.k
        up = np.repeat(np.repeat(t_px, k, axis=0), k, axis=1)
        if self._geo is None:
            yy, xx = np.mgrid[0:up.shape[0], 0:up.shape[1]]
            du, dv = (xx + 0.5) / k - self.cu, (yy + 0.5) / k - self.cv
            rho, th = np.hypot(du, dv), np.arctan2(-dv, du)
            w = np.clip((rho - self.R_in(th) + 0.7) / 0.9, 0, 1)  # 0 inside the opening, 1 in the band
            self._geo = rho, th, w * w * (3 - 2 * w)
        rho, th, w = self._geo
        sig_in, sig_band, sig_along = self.cfg["sigma"]
        self.field = self._along(LB._blur(up, sig_in * k) * (1 - w) + LB._blur(up, sig_band * k) * w, sig_along)
        return self.field

    def _along(self, f, sig):
        """A field (at the atlas's texels) averaged along the rim in the band: a Gaussian of `sig` px
        along the arc at the same share of the plan radius. Outside the band it is left as it is."""
        rho, th, w = self._geo
        keep, self.field = self.field if hasattr(self, "field") else None, f
        s = rho / self.R(th)
        acc, tot = np.zeros_like(f), 0.0
        step = 0.5
        n = int(3 * sig / step)
        for j in range(-n, n + 1):
            g = math.exp(-(j * step) ** 2 / (2 * sig * sig))
            th2 = th + j * step / np.maximum(rho, 1.0)
            r2 = s * self.R(th2)
            acc += g * self.at(self.cu + r2 * np.cos(th2), self.cv - r2 * np.sin(th2))
            tot += g
        self.field = keep
        return f * (1 - w) + acc / tot * w

    def _tone(self):
        """The smooth tone, with the film's light kept: the smoothing spreads a one-pixel line into
        its dark neighbours and the film's drawn edge takes a share of some pixels, so the pixels'
        own tones are raised (or lowered) until the picture's mean luma over each film pixel is the
        sprite's. In the band the correction is itself averaged along the rim (the sprite's pale
        line is a stair of single pixels: kept pixel by pixel it comes back as a string of beads),
        so there the light is kept along the line, not per pixel."""
        k, idx, base = self.k, self.idx, self.cfg["base"]
        h, w = idx.shape
        t0 = np.where(idx >= base, idx - base, 0).astype(float)
        for i, v in self.cfg["black"].items():
            t0[idx == i] = v
        t0 = LB._spread(t0, self.film)  # the film's tones carried over the openings and past the edge
        luma = lambda c: c @ np.array([0.299, 0.587, 0.114])  # noqa: E731
        want = luma(self.colour(t0))
        slope = np.gradient(luma(self.ramp))  # luma per tone step, by ramp entry
        shown = self.shown()
        t = t0.copy()
        for _ in range(MEAN_ROUNDS):
            f = np.clip(self._smooth(t), 0.0, 15.0)
            got = (luma(self.colour(f)) * shown).reshape(h, k, w, k).mean(axis=(1, 3))
            err = np.where(self.film, want - got, 0.0)
            step = err / np.maximum(slope[np.clip(np.round(t).astype(int), 0, 15)], 6.0)
            along = self._along(np.repeat(np.repeat(step, k, axis=0), k, axis=1), MEAN_ALONG)
            step = along.reshape(h, k, w, k).mean(axis=(1, 3))
            t = np.clip(t + 0.8 * step, 0.0, np.minimum(t0 + 5.0, 18.0))
        self.t_px = t
        return np.clip(self._smooth(t), 0.0, 15.0)


# ---------------------------------------------------------------- the atlas --------------------
def untone(lin):
    """(colour, lift): the linear colour that three's NeutralToneMapping (exposure 1) shows as `lin`
    is colour + lift: its shoulder undone (peaks asked for are at most PEAK) and its toe, which it
    takes off every channel, added back (lighting.ts untoe)."""
    lin = np.clip(np.asarray(lin, dtype=float), 0, PEAK)
    peak = lin.max(axis=-1, keepdims=True)
    d = 1 - SHOULDER
    # the shoulder: shown peak = 1 - d^2 / (peak + d - SHOULDER); its desaturation is left (a few % here)
    back = np.where(peak > SHOULDER, (d * d / (1 - peak) - d + SHOULDER) / np.maximum(peak, 1e-6), 1.0)
    c = lin * back
    y = np.clip(c.min(axis=-1, keepdims=True), 0, None)
    return c, np.where(y >= TOE, TOE, 2 * np.sqrt(TOE * y) - y)


def neutral(c):
    """three's NeutralToneMapping (exposure 1), for checks."""
    c = np.asarray(c, dtype=float)
    x = c.min(axis=-1, keepdims=True)
    c = c - np.where(x < 0.08, x - 6.25 * x * x, 0.04)
    peak = c.max(axis=-1, keepdims=True)
    d = 1 - SHOULDER
    new = 1 - d * d / (np.maximum(peak, SHOULDER) + d - SHOULDER)
    out = c * new / np.maximum(peak, 1e-6)
    g = 1 - 1 / (0.15 * (peak - new) + 1)
    return np.where(peak < SHOULDER, c, out * (1 - g) + new * g)


def _toe(x):
    """What Neutral takes off every channel of a colour whose darkest channel is x."""
    return np.where(x < 2 * TOE, x - x * x / (4 * TOE), TOE)


def band_map(tone, t, b):
    """The emissive map of band `b` over the tones `t`: M = (C(t) + lift) / (palette[b] x glow), at
    most 1. The lift is what the tone mapping will take off again, which is its toe at the darkest
    channel the map can reach: where the band's colour hasn't the blue for the whole lift (the dark
    bands), the lift is the smaller toe of the blue it has, so the red and green still come out as
    C(t)'s. No channel of M goes under `tint` of its strongest (the hit flash's bound, lib_bubble):
    the share of the lift is the largest that keeps to that without the bound raising a channel."""
    cfg = tone.cfg
    c0, lift = untone(LB._lin(tone.colour(t)))
    p = np.maximum(LB._lin(tone.ramp[b]) * cfg["glow"], 1e-6)

    def ratio(share):
        add = lift * share
        for _ in range(8):  # the lift the reachable colour's own toe takes back
            add = np.minimum(add, _toe(np.minimum(c0 + add, p).min(axis=-1, keepdims=True)))
        m = np.clip((c0 + add) / p, 0, 1)
        return m, np.maximum(m, cfg["tint"] * m.max(axis=-1, keepdims=True))

    best, worst = None, None
    for share in np.linspace(0.0, 1.0, 21):  # rising: the last share that keeps to the bound wins
        raw, floored = ratio(share)
        over = (floored - raw).max(axis=-1) / np.maximum(raw.max(axis=-1), 1e-6)  # how far the bound raises a channel
        if best is None:
            best, worst = floored, over
        else:
            take = (over <= 0.02) | (over < worst)  # (where no share keeps to it: the one it changes least)
            best = np.where(take[..., None], floored, best)
            worst = np.where(take, over, worst)
    return best


def atlas(tone, box, bands):
    """One tile per band over the sprite box: the band's map. Each tile's top rows (STRIP texels,
    never reached by the film's paint) hold the band's map over the whole ramp, tone 0 at the left
    and 15 at the right: the bowl's and the lining's faces are painted from it, by their tone."""
    k = tone.k
    u0, v0, u1, v1 = box
    tw, th = (u1 - u0) * k, (v1 - v0) * k
    t = tone.field[v0 * k:v1 * k, u0 * k:u1 * k]
    cols = 4 if len(bands) > 4 else len(bands)
    rows = -(-len(bands) // cols)
    img = np.zeros((rows * th, cols * tw, 3))
    tiles = {}
    ramp = np.repeat(strip_tone(np.arange(tw) + 0.5, tw)[None, :], STRIP, axis=0)
    for n, b in enumerate(bands):
        x0, y0 = (n % cols) * tw, (n // cols) * th
        img[y0:y0 + th, x0:x0 + tw] = LB._srgb(band_map(tone, t, b))
        img[y0:y0 + STRIP, x0:x0 + tw] = LB._srgb(band_map(tone, ramp, b))
        tiles[b] = (x0, y0)
    return img, tiles, (tw, th)


def strip_tone(x, tw):
    """The tone at texel position x of a tile's ramp strip (tw wide; a margin of 2 texels each side)."""
    return np.clip((np.asarray(x, dtype=float) - 2.0) / (tw - 4.0), 0, 1) * 15.0


def strip_x(t, tw):
    """... and the position of tone t."""
    return 2.0 + min(max(t, 0.0), 15.0) / 15.0 * (tw - 4.0)


# ---------------------------------------------------------------- the ball ---------------------
class FilmBall(LB.Ball):
    """lib_bubble's ball, whole: the dome is cut along the film's outline (the openings are left
    out), the bowl is whole: the rim's tone, fading down to dark film."""

    def __init__(self, tone, cfg):
        self.F = {}  # the film's outline (phi) per vertex
        super().__init__(tone, cfg)
        self.cut_film()

    def _add(self, pos, nrm):
        i = super()._add(pos, nrm)
        if pos[2] < -1e-9:
            # the bowl: the rim's tone above it, fading down to dark film (rule 3: a plausible closed
            # shape, no detail); painted by its tone from the tiles' ramp strips
            du, dv = pos[0] - self.cu, pos[1] - self.cv
            th = math.atan2(-dv, du) if du or dv else 0.0
            r = float(self.R(th))
            rim = float(self.tone.at(self.cu + r * math.cos(th), self.cv - r * math.sin(th)))
            f = min(1.0, -pos[2] / self.cfg["h_bot"] / BOWL_FADE)
            self.T[i] = 1.0 + (rim - 1.0) * (1 - f * f * (3 - 2 * f)) if du or dv else 1.0
        return i

    def cut_bands(self):
        """The film is cut along the tone's contours into the bands (lib_bubble). The bowl is not:
        each of its faces takes the band of its highest tone (the band's ramp strip brings it down
        to the ramp, so the tone runs smoothly over the faces; only under the hit flash would the
        bands' edges show)."""
        c = self.cfg
        levels = [c["crown_level"]] + [b - 0.1 for b in c["bands"][:-1]]
        tris, self.tris = self.tris, [t for t in self.tris if not self.under(t)]
        super().cut_bands()
        self.tris = tris
        for tri in tris:
            if self.under(tri):
                top = max(self.T[i] for i in tri)
                self.polys.append((tri, sum(top > lv for lv in levels) - 1))

    def under(self, poly):
        """Whether a polygon belongs to the bowl."""
        return any(self.P[i][2] < -1e-9 for i in poly)

    def _phi(self, i):
        if i not in self.F:
            self.F[i] = float(self.tone.phi(self.Q[i][0], self.Q[i][1]))
        return self.F[i]

    def _cross(self, i, j):
        """The vertex where the film's outline crosses the edge from i (outside) to j (inside),
        found on the edge itself (bisection), so the cut follows the drawn outline, not the mesh."""
        key = (min(i, j), max(i, j), "film")
        if key not in self._mid:
            a, b = self.Q[i], self.Q[j]
            lo, hi = 0.0, 1.0
            for _ in range(18):
                m = (lo + hi) / 2
                q = a + (b - a) * m
                if float(self.tone.phi(q[0], q[1])) < 0:
                    lo = m
                else:
                    hi = m
            self.F[self.mid(i, j, (lo + hi) / 2, "film")] = 0.0
        return self._mid[key]

    def cut_film(self):
        """Keep the bowl, and of the dome the part inside the film's outline."""
        out = []
        for tri in self.tris:
            if self.under(tri):
                out.append(tri)
                continue
            vals = [self._phi(i) for i in tri]
            if min(vals) >= 0:
                out.append(tri)
                continue
            if max(vals) < 0:
                continue
            poly = []
            for n in range(3):
                i, j = tri[n], tri[(n + 1) % 3]
                if vals[n] >= 0:
                    poly.append(i)
                if (vals[n] < 0) != (vals[(n + 1) % 3] < 0):
                    poly.append(self._cross(i, j) if vals[n] < 0 else self._cross(j, i))
            if self._area(poly):
                out.append(poly)
        self.tris = out

    def lining(self):
        """The dome's inner face, whole and coarse: (points, inward normals, triangles), a little
        inside the film."""
        nt, nr, inset = LINING
        pts, nrm, tris = [], [], []
        for i in range(nr):
            a = (math.pi / 2) * i / nr
            for j in range(nt):
                p, n = self._point(2 * math.pi * j / nt, a, True)
                pts.append(np.array(p) - n * inset)
                nrm.append(-n)
        top = len(pts)
        pts.append(np.array([self.cu, self.cv, self.cfg["h_top"] - inset]))
        nrm.append(np.array([0.0, 0.0, -1.0]))
        for i in range(nr - 1):
            for j in range(nt):
                a, b, c, d = i * nt + j, i * nt + (j + 1) % nt, (i + 1) * nt + (j + 1) % nt, (i + 1) * nt + j
                tris += [[a, c, b], [a, d, c]]
        for j in range(nt):
            tris.append([(nr - 1) * nt + j, top, (nr - 1) * nt + (j + 1) % nt])
        return pts, nrm, tris


# ---------------------------------------------------------------- Blender ----------------------
def _to_blender(p, w, h):
    return ((p[0] - w / 2) * PX, (h / 2 - p[1]) * PX, (p[2] + RISE) * PX)


def _materials(tone, cfg, tag, image, bands):
    """One glowing material per band, its emission through the atlas; opaque and single-sided, so
    no view shows a face from behind."""
    sprite_d = {"name": tag, "colors": {str(k): list(v) for k, v in tone.colors.items()}}
    base = cfg["base"]
    for b in cfg["bands"]:  # a ramp entry the sprite itself never uses still names its band
        sprite_d["colors"].setdefault(str(base + b), [int(round(x)) for x in tone.ramp[b]])
    mats = {}
    for b in bands:
        r, s = cfg["hot_gloss"] if b >= cfg["hot_from"] else cfg["band_gloss"]
        m = common.palette_material(sprite_d, base + b, f"{tag}_film{b}", metallic=0.0, roughness=r,
                                    emission_strength=cfg["glow"])
        m.use_backface_culling = True
        bsdf = LB._bsdf(m)
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
        mats[b] = m
    return mats


def _mesh(name, ball, polys, mats, uv_of, size):
    """The ball's polygons [(vertex ids, band, painted by tone)] (smooth, its own normals) and the
    lining, dark film (tone 1 of the darkest band)."""
    w, h = size
    used = sorted({i for poly, _, _ in polys for i in poly})
    remap = {i: n for n, i in enumerate(used)}
    verts = [_to_blender(ball.P[i], w, h) for i in used]
    norms = [(ball.N[i][0], -ball.N[i][1], ball.N[i][2]) for i in used]
    keys = sorted(mats)
    slot = {b: n for n, b in enumerate(keys)}
    faces, fmat, fuv = [], [], []
    for poly, band, by_tone in polys:
        faces.append([remap[i] for i in poly])
        fmat.append(slot[band])
        fuv.append([uv_of(ball.Q[i], band, ball.T[i] if by_tone else None) for i in poly])
    lp, ln, lt = ball.lining()
    n0 = len(verts)
    verts += [_to_blender(p, w, h) for p in lp]
    norms += [(n[0], -n[1], n[2]) for n in ln]
    for tri in lt:
        faces.append([n0 + i for i in tri])
        fmat.append(slot[keys[0]])
        fuv.append([uv_of(None, keys[0], 1.0)] * 3)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for b in keys:
        me.materials.append(mats[b])
    me.polygons.foreach_set("material_index", fmat)
    me.polygons.foreach_set("use_smooth", [True] * len(faces))
    uv = me.uv_layers.new(name="paint")
    j = 0
    for f in fuv:
        for q in f:
            uv.data[j].uv = q
            j += 1
    me.update()
    bm = bmesh.new()  # winding: along each face's normals (outward on the ball, inward on the lining)
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    for f in bm.faces:
        n = np.mean([norms[v.index] for v in f.verts], axis=0)
        if f.normal.dot(n) < 0:
            f.normal_flip()
    bm.to_mesh(me)
    bm.free()
    me.normals_split_custom_set_from_vertices(norms)
    return me, len(lt)


def _ink_shell(ball, tone, name, coll, size):
    """The outline shell: a strip inside the rim, facing out and down, along the arc where the
    sprite's own edge is ink. The game's ink is the shell's back faces pushed out (an inverted
    hull, 0.5 px): seen from above that is a line on the middle of the sprite's ink pixels. Where
    the sprite draws colour to its edge there is no shell and no ink."""
    w, h = size
    r1, r2, tall = INK_STRIP
    n = 120
    on = [bool(tone.ink[int(round(360 * j / n)) % 360]) for j in range(n)]
    quads = [j for j in range(n) if on[j] and on[(j + 1) % n]]
    ids = sorted({j for q in quads for j in (q, (q + 1) % n)})
    at = {j: m for m, j in enumerate(ids)}
    m = len(ids)
    slope = np.array([tall, r1 - r2])  # the strip's normal: out and down
    slope = slope / np.linalg.norm(slope)
    verts, norms = [], []
    for r, z in ((r2, 0.0), (r1, -tall)):
        for j in ids:
            th = 2 * math.pi * j / n
            rad = float(tone.R(th)) - r
            verts.append(_to_blender((tone.cu + rad * math.cos(th), tone.cv - rad * math.sin(th), z), w, h))
            norms.append((math.cos(th) * slope[0], math.sin(th) * slope[0], -slope[1]))
    faces = [[at[j], at[(j + 1) % n], m + at[(j + 1) % n], m + at[j]] for j in quads]
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
    return shell, len(faces)


def make(cfg=CFG):
    """The sprite, its film and its ball (numpy only)."""
    idx, colors = LB.load_block([(NAME, 0, 0)], *SIZE)
    tone = FilmTone(idx, colors, cfg)
    ball = FilmBall(tone, cfg)
    ball.cut_bands()
    return idx, colors, tone, ball


def sprite_box(idx):
    """The atlas's box: the sprite and a margin for the filter and the ramp strips."""
    h, w = idx.shape
    ys, xs = np.nonzero(idx >= 0)
    return (int(max(0, xs.min() - 3)), int(max(0, ys.min() - 3)), int(min(w, xs.max() + 4)), int(min(h, ys.max() + 4)))


def build():
    import json
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    cfg = CFG
    root = common.repo_root(__file__)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    coll = common.reset_collection(NAME)
    idx, colors, tone, ball = make(cfg)
    k = tone.k
    dbg = Path(argv[argv.index("--debug") + 1]) if "--debug" in argv else None
    box = sprite_box(idx)
    bands = [b for n, b in enumerate(cfg["bands"]) if any(pb == n for _, pb in ball.polys)]
    img, tiles, (tw, th) = atlas(tone, box, bands)
    ih, iw, _ = img.shape
    if dbg:
        dbg.mkdir(parents=True, exist_ok=True)
        for fn, px in ((f"{NAME}_field.png", tone.colour(tone.field) / 255), (f"{NAME}_atlas.png", img)):
            im = LB._image("dbg", px)
            im.filepath_raw = str(dbg / fn)
            im.file_format = "PNG"
            im.save()
            bpy.data.images.remove(im)
    mats = _materials(tone, cfg, NAME, LB._image(f"{NAME}_film", img), bands)

    def uv_of(q, band, tone_of=None):
        x0, y0 = tiles[band]
        if tone_of is not None:  # by tone, from the band's ramp strip
            return ((x0 + strip_x(tone_of, tw)) / iw, 1 - (y0 + STRIP / 2) / ih)
        x = x0 + min(max((q[0] - box[0]) * k, 0.5), tw - 0.5)
        y = y0 + min(max((q[1] - box[1]) * k, STRIP + 0.5), th - 0.5)
        return (x / iw, 1 - y / ih)

    polys = [(poly, cfg["bands"][max(n, 0)], ball.under(poly)) for poly, n in ball.polys]
    me, lining = _mesh(NAME, ball, polys, mats, uv_of, SIZE)
    obj = bpy.data.objects.new(NAME, me)
    coll.objects.link(obj)
    # drawn in the art's view, straight down, in its depth band (obliqueView.ts): the dome's own
    # heights map onto the band, the bowl lies at its foot
    obj["tyrian_oblique"] = OBLIQUE
    obj["tyrian_depth_band"] = [BAND[0] * PX, BAND[1] * PX, RISE * PX, (RISE + cfg["h_top"]) * PX]
    shell, ink = _ink_shell(ball, tone, NAME, coll, SIZE)
    film = sum(len(p) - 2 for p, _, under in polys if not under)
    bowl = sum(len(p) - 2 for p, _, under in polys if under)
    print(f"{NAME}: centre {ball.cu:.2f},{ball.cv:.2f}, radius {float(tone.R(0.0)):.2f} east {float(tone.R(math.pi / 2)):.2f} north, "
          f"{film} film + {bowl} bowl + {lining} lining tris, shell {ink} quads, "
          f"z {RISE - cfg['h_bot']:.2f}..{RISE + cfg['h_top']:.2f} px, bands {[cfg['base'] + b for b in bands]}, atlas {iw}x{ih}, "
          f"islands {len(tone.islands)}, ink arc {int(tone.ink.sum())} deg")
    out_dir = Path(argv[argv.index("--out") + 1]) if "--out" in argv else None
    if out_dir:
        print("exported", LB._export([obj, shell], out_dir / f"{NAME}.glb"))
    else:
        # the game contract, as common.export_sprite_model: the model at its own centre, its sprites registered
        model = f"enemies/{NAME}"
        out = LB._export([obj, shell], root / "public" / "models" / f"{model}.glb")
        entry = root / "src" / "render" / "spriteModels" / f"{NAME}.json"
        entry.write_text(json.dumps({"model": model, "sprites": common.load_sprite(root, NAME)["sprites"]}, indent=1) + "\n")
        print(f"exported {out} ({out.stat().st_size} bytes, {len(obj.data.polygons)} faces) and {entry}")


if __name__ == "__main__":
    build()
