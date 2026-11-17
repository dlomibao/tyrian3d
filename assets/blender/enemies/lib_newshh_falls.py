"""The TORM waterfall's fields (assembly-newshh-129.py, DECISIONS.md D212): numpy only, no bpy.

The waterfall's sprite is a full rectangle of scenery painted to run on into the tiles round it: the
shadowed flanks of the jungle's cliff wall, a curtain of falling water (its crest is in the river
tiles ABOVE the sprite), a plunge pool, bushes. So it is built as the island rock of D66/D84 is: a
relief whose colour is palette data in a texture (lib_tiles.rock_material: R shade, G ramp code,
B bump height, A coverage), made from the sprite's own pixels, fading out at the rectangle's edge.

Everything here lives on one canvas: the catalogue's 5 x 2 layout (120 x 56 px; u east, s = the art's
screen row), PAD px wider on every side (edges repeated). newshh-129 and newshh-205 appear three
times side by side, so every noise is periodic over 24 px along u and each piece's fields are cut
from its HOME copy (the middle one for those two: its neighbours are copies of itself).

  static layer   rock, bushes and what lies under the water (dark wet rock): one texture
  water layer    falls, foam and pool, one texture per animation phase. Clear between the strands
                 (the wet rock behind shows), and its top edge is ragged: each bright strand starts
                 up to LIP_REACH px above the sprite's first row, thinning into the river's tone

The paint: each palette shade's region keeps its tone and gets a smooth outline (`levels`), mixed
with a little plain blur; strands are kept crisp across and soft along, the pool's dither becomes
mottling with the bright pixels as glints. The water's paint is darkened by what the game's lights
add to a model (GAIN_*), so it meets the terrain, which shows its palette colours as they are.

`heights` gives the real shape, as a height above the ground for every point of the art (the model
is a surface over the art's oblique view: a point drawn at row s with height h stands at plan row
v = s + h, `tyrian_oblique` 1): the cliffs' capped buttresses with the paint's lit stone standing
out, the river rolling over ROLL rows into a near-plumb curtain, the pool.
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiles"))
import lib_rock_hd as rh  # noqa: E402

TEX = 8          # texels per sprite px
HRES = 4         # height samples per sprite px
PAD = 4          # px of canvas round the assembly
W, H = 120, 56
PW, PH = 24, 28
PIECES = ["newshh-117", "newshh-129", "newshh-153", "newshh-157", "newshh-205", "newshh-207"]
#: The sprite frames of each piece, by animation phase.
CYCLES = {
    "newshh-117": [165, 234, 240, 117], "newshh-129": [167, 236, 242, 129], "newshh-153": [169, 238, 244, 153],
    "newshh-157": [203, 272, 278, 157], "newshh-205": [205, 274, 280, 267], "newshh-207": [207, 276, 282, 269],
}
LAYOUT = [("newshh-117", 0, 0), ("newshh-129", 24, 0), ("newshh-129", 48, 0), ("newshh-129", 72, 0), ("newshh-153", 96, 0),
          ("newshh-157", 0, 28), ("newshh-205", 24, 28), ("newshh-205", 48, 28), ("newshh-205", 72, 28), ("newshh-207", 96, 28)]
#: Where each piece's fields are cut from (its top-left on the canvas).
HOME = {"newshh-117": (0, 0), "newshh-129": (48, 0), "newshh-153": (96, 0),
        "newshh-157": (0, 28), "newshh-205": (48, 28), "newshh-207": (96, 28)}

STATIC_RAMPS = (0, 2, 12)   # grey rock, the two greens (code 0, 0.5, 1)
WATER_RAMPS = (3,)

# --- the shape (px) ---------------------------------------------------------------------------
CREST_H = 30.0     # height of the river where it goes over
CREST_ROW = 0.2    # the art row where the water starts to fall (it wanders, crest_row)
LIP_REACH = 2.6    # px above the sprite's first row the brightest strands start (the river tiles run on under them)
ROLL = 4.5         # px (art rows) over which the river rolls from level to falling
FOOT_ROW = 37.6    # where the curtain meets the pool
POOL_H = 1.6       # the pool's surface (the static bed lies WATER_OVER under the water everywhere)
WATER_OVER = 1.6   # px the water layer lies over the static one, at least
WATER_BUMP = 0.3   # how much of the water's paint is relief in the bump map
ROCK_BUMP = 0.5    # and of the rock's
GAP_CLEAR = 0.65   # how clear the water layer is between the strands (1: only the wet rock behind shows)
RIVER_SHADE = 6.6  # the water shade that, lit, matches the HD river tiles above the falls
SPARKLE = 7        # water shades over this are sparkles on the pool
#: The game lights a model's up-facing matte surface to about 1.3 times its palette colour and the
#: plumb curtain to about 1.2 (measured at TORM t4050, D205's lights), while the terrain round it
#: shows its palette colour as it is: the water's paint is that much darker, so pool and river meet.
GAIN_POOL, GAIN_FALL = 0.74, 0.84
BANK_H = 1.5       # the banks' height
FACE_RISE = 0.9    # px of height per art row up the cliffs' faces (1 = plumb)
#: Per column u: the art row of the cliffs' foot, and of the rim where their caps roll over into the face.
FOOT = [(0, 41.0), (4.0, 41.0), (5.0, 38.0), (6.0, 37.0), (7.0, 36.2), (8.0, 35.4), (9.0, 34.6), (10.0, 34.0),
        (11.0, 33.6), (12.0, 33.4), (12.6, 33.3), (104.4, 33.3), (105.0, 33.6), (106.0, 34.0), (108.0, 35.0),
        (110.0, 36.4), (111.0, 37.8), (112.0, 41.0), (113.0, 44.0), (114.0, 45.0), (120, 45.0)]
RIM = [(0, 7.3), (1.0, 6.8), (2.0, 5.8), (3.0, 5.4), (4.0, 5.3), (5.0, 5.9), (6.0, 6.7), (9.0, 6.8), (10.0, 6.3),
       (11.5, 5.6), (12.5, 5.0), (105.5, 0.5), (109.5, 0.5), (110.0, 3.6), (112.6, 3.8), (113.5, 4.6), (114.0, 5.6),
       (115.0, 6.6), (116.0, 7.6), (120, 7.8)]


# --- helpers ----------------------------------------------------------------------------------

def blur(a, sy, sx=None):
    """Gaussian blur, its sigma along rows (sy) and columns (sx) in samples; edges repeat."""
    out = a.astype(float)
    for axis, sg in ((0, sy), (1, sy if sx is None else sx)):
        if sg <= 0:
            continue
        r = max(1, int(math.ceil(3 * sg)))
        k = np.exp(-0.5 * (np.arange(-r, r + 1) / sg) ** 2)
        k /= k.sum()
        pad = [(0, 0), (0, 0)]
        pad[axis] = (r, r)
        p = np.pad(out, pad, mode="edge")
        n = out.shape[axis]
        out = sum(k[i] * (p[i:i + n] if axis == 0 else p[:, i:i + n]) for i in range(2 * r + 1))
    return out


def interp(table, x):
    xs, ys = zip(*table)
    return np.interp(x, xs, ys)


def noise(shape, per_px, cells_u, cells_s, seed):
    """Smooth noise in -1..1 over a padded canvas at `per_px` samples per px, periodic over 24 px along u."""
    h, w = shape
    return rh.periodic_noise(h, w, period=(h, PW * per_px), cells=(cells_s, cells_u), seed=seed,
                             origin=(0, (-PAD * per_px) % (PW * per_px)))


def coords(per_px):
    """(u, s) of every sample of the padded canvas at `per_px` samples per px (sample centres)."""
    h, w = (H + 2 * PAD) * per_px, (W + 2 * PAD) * per_px
    s = (np.arange(h) + 0.5) / per_px - PAD
    u = (np.arange(w) + 0.5) / per_px - PAD
    return u[None, :], s[:, None]


def up(a, k):
    return np.repeat(np.repeat(a, k, 0), k, 1)


def canvas(frames, phase):
    """The assembly's pixels in animation phase `phase`: an (H, W) array of palette indices.
    `frames`: {piece: {sprite frame: rows of palette indices}}."""
    g = np.full((H, W), -1, np.int32)
    for name, c0, r0 in LAYOUT:
        g[r0:r0 + PH, c0:c0 + PW] = np.asarray(frames[name][CYCLES[name][phase]], np.int32)[:PH, :PW]
    return g


def padded(g):
    return np.pad(g, PAD, mode="edge")


def water_mask(grids):
    """Where the water is (falls, foam, pool), the same for every phase: a pixel that is water colour in
    any phase, and the dark gaps (palette 1, 2) between such pixels along a row (the black between the
    strands is water in shadow, not rock; a wide black area open to the cliff is wet rock)."""
    blue = np.zeros(grids[0].shape, bool)
    dark = np.ones(grids[0].shape, bool)
    for g in grids:
        blue |= (g >> 4) == 3
        dark &= (g == 1) | (g == 2)
    out = blue.copy()
    for r in range(out.shape[0]):
        cols = np.flatnonzero(blue[r])
        for a, b in zip(cols, cols[1:]):
            if 1 < b - a <= 7 and dark[r, a + 1:b].all():
                out[r, a + 1:b] = True
    return out


def fill_from(values, valid, steps):
    """`values` grown `steps` px out of `valid` (each new pixel the mean of its filled neighbours);
    returns (values, how many steps out each pixel is: 0 inside, steps + 1 where never reached)."""
    v = np.where(valid, values, 0.0).astype(float)
    ok = valid.copy()
    dist = np.where(valid, 0, steps + 1)
    for n in range(1, steps + 1):
        pv, po = np.pad(v, 1), np.pad(ok, 1).astype(float)
        sm = pv[:-2, 1:-1] + pv[2:, 1:-1] + pv[1:-1, :-2] + pv[1:-1, 2:]
        cn = po[:-2, 1:-1] + po[2:, 1:-1] + po[1:-1, :-2] + po[1:-1, 2:]
        new = ~ok & (cn > 0)
        v[new] = sm[new] / cn[new]
        dist[new] = n
        ok |= new
    return v, dist


def gain(shade, ramp_lum, g):
    """Shade numbers moved along their ramp (its brightness per shade, rising) to g times their brightness."""
    idx = np.arange(len(ramp_lum))
    return np.interp(np.interp(shade, idx, ramp_lum) * g, ramp_lum, idx)


def levels(shade, sig_s, sig_u, soft=0.16, top=15):
    """A pixel-art shade map (0..top, whole numbers) at TEX texels per px as smooth-edged flats: every
    shade's region keeps its tone and gets a rounded outline (each level set blurred and re-thresholded),
    so a strand stays a strand and a stone a stone, with no stair steps."""
    out = np.zeros((shade.shape[0] * TEX, shade.shape[1] * TEX))
    for level in range(1, top + 1):
        m = shade >= level
        if not m.any():
            break
        out += rh.smoothstep(0.5 - soft, 0.5 + soft, blur(up(m.astype(float), TEX), sig_s * TEX, sig_u * TEX))
    return out


# --- the layers -------------------------------------------------------------------------------

class Fields:
    """Everything the model is made from. `frames`: {piece: {sprite frame: rows of palette indices}};
    `colors`: {palette index: (r, g, b)}."""

    def __init__(self, frames, colors):
        self.colors = {int(k): tuple(v) for k, v in colors.items()}
        self.lum = np.zeros(257)
        for i, (r, g, b) in self.colors.items():
            self.lum[i] = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        self.grids = [padded(canvas(frames, k)) for k in range(4)]
        self.water = water_mask(self.grids)
        self.u, self.s = coords(TEX)
        shape = (self.s.shape[0], self.u.shape[1])
        self.shape = shape
        self.wob = noise(shape, TEX, 9, 14, 11) * 0.6 + noise(shape, TEX, 17, 30, 12) * 0.4
        self.wsoft = blur(up(self.water.astype(float), TEX), 0.85 * TEX)
        # the water columns at the top and bottom edges (0..1 along u), for the edges' fades
        self.top_water = blur(up(self.water[PAD:PAD + 1].astype(float), TEX), 0, 0.5 * TEX)[0]
        self.bottom_water = blur(up(self.water[PAD + H - 1:PAD + H].astype(float), TEX), 0, 0.5 * TEX)[0]

    # ---- static: rock, bushes, the bed under the water ----
    def static(self):
        g = self.grids[0]
        ramp, shade = g >> 4, (g & 15).astype(float)
        rock = ~self.water
        # under the water: the rock's own shade a little way in, then dark wet rock
        filled, dist = fill_from(shade, rock, 3)
        under = np.clip(dist / 3.0, 0, 1)
        shade1 = np.where(rock, shade, np.round(filled * (1 - under) + 1.0 * under))
        hd = levels(shade1, 0.42, 0.42, soft=0.11)
        hd = 0.8 * hd + 0.2 * blur(up(shade1, TEX), 0.5 * TEX)
        # ramp code: grey 0, green (32..) 0.5, green (192..) 1; the nearest painted ramp wins
        code = np.zeros(self.shape)
        best = np.full(self.shape, -1.0)
        for r, c in zip(STATIC_RAMPS, (0.0, 0.5, 1.0)):
            m = blur(up(((ramp == r) & rock).astype(float) if r else ((ramp == 0) | ~rock).astype(float), TEX), 0.4 * TEX)
            code = np.where(m > best, c, code)
            best = np.maximum(best, m)
        code = blur(code, 0.8)
        green = np.clip(code * 2, 0, 1)
        # bump: the painted light as relief (a little), and grain
        tone = hd / 15.0 * (1 - 0.55 * green)
        grain = noise(self.shape, TEX, 31, 70, 21) * 0.5 + noise(self.shape, TEX, 61, 140, 22) * 0.5
        tone = blur(tone, 0.2 * TEX)
        height = 0.5 + ROCK_BUMP * (tone - blur(tone, 1.2 * TEX)) + 0.02 * grain
        hd = hd + 0.35 * grain * (1 - green) * np.clip(hd / 3.0, 0.3, 1)
        # coverage: out at the rectangle's edge (wobbling), and before the water's own soft edges
        d_l, d_r = self.u + 0.15, W - self.u + 0.15
        d_t = self.s + 0.15 - 2.6 * self.top_water[None, :]
        d_b = H - self.s + 0.15 - 2.6 * self.bottom_water[None, :]
        d = np.minimum(np.minimum(d_l, d_r), np.minimum(d_t, d_b)) + 0.45 * self.wob
        alpha = rh.smoothstep(-0.55, 0.55, d)
        return {"shade": np.clip(hd, 0, 15), "code": code, "height": np.clip(height, 0, 1), "alpha": alpha}

    # ---- water: one per phase ----
    def lip(self, phase):
        """The art row where the water layer ends at the top, per texel column: the river tiles above
        run on under it, each bright strand reaching a little higher than the dark between."""
        row = (self.grids[phase][PAD:PAD + 2] & 15).astype(float).mean(0)
        row = np.where(self.water[PAD], row, 6.0)
        bright = blur(up(row[None, :], TEX), 0, 0.4 * TEX)[0] / 15.0
        return 0.6 - LIP_REACH * np.clip((bright - 0.36) / 0.4, -0.3, 1) + 0.5 * self.wob[0]

    def crest_row(self, per_px):
        """The art row where the river starts to roll over, per column (it wanders)."""
        shape = ((H + 2 * PAD) * per_px, (W + 2 * PAD) * per_px)
        return CREST_ROW + 1.7 * noise(shape, per_px, 9, 1, 41)[:1] + 0.9 * noise(shape, per_px, 4, 1, 42)[:1]

    def foot_row(self, per_px):
        """The art row where the curtain meets the pool, per column (it wanders)."""
        shape = ((H + 2 * PAD) * per_px, (W + 2 * PAD) * per_px)
        return FOOT_ROW + 1.1 * noise(shape, per_px, 7, 1, 43)[:1]

    def water_layer(self, phase):
        g = self.grids[phase]
        blue = (g >> 4) == 3
        shade = np.where(blue, g & 15, 0).astype(float)   # the dark between the strands: palette 48
        filled, _ = fill_from(shade, self.water, 2)
        shade1 = np.where(self.water, shade, np.round(filled))
        foot = self.foot_row(TEX)
        fall = 1 - rh.smoothstep(-1.5, 1.5, self.s - foot)   # 1 on the curtain, 0 on the pool
        # how steep the water is here: 0 level (the river going over, the pool), 1 falling
        steep = fall * (1 - np.exp(-np.clip(self.s - self.crest_row(TEX), 0, None) / ROLL))
        # strands: crisp across, soft along
        soft = blur(up(shade1, TEX), 0.6 * TEX, 0.26 * TEX)
        strands = 0.65 * levels(shade1, 0.5, 0.28, top=14) + 0.35 * soft
        # pool and foam: the dither as soft mottling, the sparkles (the bright pixels) as round glints
        calm = np.minimum(shade1, SPARKLE)
        ripple = noise(self.shape, TEX, 9, 44, 31 + phase)   # long along u: the river's swirls
        blots = 0.4 * levels(calm, 0.5, 0.5, soft=0.3, top=14) + 0.6 * blur(up(calm, TEX), 0.6 * TEX)
        hd = fall * strands + (1 - fall) * blots
        hd = gain(hd, self.lum[48:63], GAIN_POOL + (GAIN_FALL - GAIN_POOL) * steep)
        hd = hd + (1 - fall) * (1.15 * levels(shade1 - calm, 0.36, 0.36, top=14) + 0.4 * ripple)
        # above the sprite's first row the strands' heads thin out into the river's own tone
        hd = hd + np.clip(-self.s / LIP_REACH, 0, 1) * (RIVER_SHADE - hd) * 0.7
        # between the strands the wet rock behind shows (the static layer: matte, so the gaps stay black)
        gaps = 1 - GAP_CLEAR * fall * (1 - rh.smoothstep(0.2, 1.7, blur(soft, 0.15 * TEX)))
        tone = blur(hd, 0.25 * TEX) / 14.0
        height = 0.5 + WATER_BUMP * (tone - blur(tone, 1.0 * TEX)) + 0.02 * ripple * (1 - fall)
        inside = rh.smoothstep(0.4, 0.6, self.wsoft)
        top = rh.smoothstep(-0.9, 0.9, self.s - self.lip(phase)[None, :])
        bottom = rh.smoothstep(-0.9, 0.9, H + 0.2 - self.s + 0.6 * self.wob)
        return {"shade": np.clip(hd, 0, 14), "code": np.zeros(self.shape), "height": np.clip(height, 0, 1),
                "alpha": inside * top * bottom * gaps}   # 14: the water ramp's last colour is palette 62

    # ---- the shape ----
    def heights(self):
        """(static, water): height in px above the ground of each layer at every point of the padded
        canvas, HRES samples per px."""
        u, s = coords(HRES)
        shape = (s.shape[0], u.shape[1])
        g = self.grids[0]
        k = HRES
        wsoft = blur(up(self.water.astype(float), k), 0.35 * k)
        # the falls: level at the crest, rolling over ROLL rows into a near-plumb curtain down to the pool
        crest, foot = self.crest_row(k), self.foot_row(k)
        t = np.clip(s - crest, 0, None)
        span = foot - crest
        drop = lambda x: x - ROLL * (1 - np.exp(-x / ROLL))   # noqa: E731
        fall = CREST_H * np.clip(1 - drop(t) / drop(span), 0, 1)
        water = np.maximum(fall, 0) + POOL_H
        # the cliffs: bank, a leaning face from foot to rim, a cap that rolls over the rim
        foot, rim = interp(FOOT, u), interp(RIM, u)
        h_rim = BANK_H + FACE_RISE * (foot - rim)
        over = np.clip(rim - s, 0, None)
        cliff = np.where(s >= foot, BANK_H,
                         np.where(s >= rim, BANK_H + FACE_RISE * (foot - s), h_rim + 2.4 * (1 - np.exp(-over / 1.6)) + 0.1 * over))
        base = np.maximum(water - WATER_OVER - 0.6, 0.0)
        static = cliff * (1 - wsoft) + base * wsoft
        # relief from the paint: lit stone stands out, dark sinks; bushes are mounds
        ramp = g >> 4
        lum = np.where(self.water, 0.05, self.lum[g])
        lum_hd = blur(up(lum, k), 0.45 * k)
        green = blur(up(((ramp == 2) | (ramp == 12)).astype(float), k), 0.4 * k)
        relief = 9.0 * (lum_hd - blur(lum_hd, 2.5 * k)) * (1 - green) + green * (0.8 + 9.0 * lum_hd)
        static = blur(static, 0.4 * k) + relief * (1 - wsoft)
        # never overhanging in the art's view (it would face away from the art's eye): going up one
        # row the surface gains at most 0.95 px
        static = np.maximum(static, 0.0)
        step = 0.95 / k
        for r in range(shape[0] - 2, -1, -1):
            static[r] = np.minimum(static[r], static[r + 1] + step)
        water = np.maximum(blur(water, 0.3 * k), static + WATER_OVER)
        for r in range(shape[0] - 2, -1, -1):
            water[r] = np.minimum(water[r], water[r + 1] + step)
        water = np.maximum(water, static + 1.0)
        return static, water


def piece_texture(ch, name):
    """A piece's part of a layer's channels: its box and PAD px round it."""
    c0, r0 = HOME[name]
    return {k: v[r0 * TEX:(r0 + PH + 2 * PAD) * TEX, c0 * TEX:(c0 + PW + 2 * PAD) * TEX] for k, v in ch.items()}


def preview(colors, ch, ramps, back=None):
    """What the game draws of a layer, unlit: (h, w, 3) floats 0..255 over `back` (or black), and its alpha."""
    cols = np.zeros((256, 3))
    for i, c in colors.items():
        cols[int(i)] = c
    s = np.clip(ch["shade"], 0, 15)
    lo = np.floor(s).astype(int)
    hi = np.minimum(lo + 1, 15)
    f = (s - lo)[..., None]
    n = len(ramps) - 1
    pos = np.clip(ch["code"], 0, 1) * n
    out = np.zeros(s.shape + (3,))
    for j, r in enumerate(ramps):
        w = np.clip(1 - np.abs(pos - j), 0, 1)[..., None]
        out += w * (cols[r * 16 + lo] * (1 - f) + cols[r * 16 + hi] * f)
    a = ch["alpha"][..., None]
    return (out * a + (back if back is not None else 0) * (1 - a)), ch["alpha"]
