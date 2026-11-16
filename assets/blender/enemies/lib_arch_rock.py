"""The SURFACE / DESERTRUN sandstone rock arch as ONE 3D rock: crown, edge rocks AND legs (D209).

Used by assembly-newsh3-198.py (the arch pieces and the two leg tile models) and its wrappers
newsh3-262.py / newsh3-180.py / newsh3-282.py (the edge rocks, D196); each exports only its own.

The rock is one height field in the arch's own frame (x = arch sheet column -24..144, row 0..112
south +, z up, 1 = 1 sprite px; no wall stretch), over the union of:
  - the arch sprite pieces newsh3 162/164/241 over 198/200/202/279/281 (assembly-newsh3-198),
  - the edge rocks newsh3-262/-180/-282 (D196; the right leg's shoulder, the left knob, the spur),
  - the rock pixels of the layer-0 leg tiles under the arch (shapes).dat 26-29 over 36-39 at
    columns -24..72, 8-9 over 18-19 at columns 96..144, top at sheet row 55; DESERTRUN t1050 and
    SURFACE t1800), which are two layer-0 tile models (keepTiles: they stand on their own tiles).
So there is no 3D crown meeting painted legs: the section at row 56 is one surface. (Layer 0 never
blends, so D203 does not keep the tile models off; the leg tiles occur only on those two levels.)

Height = C(g) * f_out(d_out) * f_in(d_in) + slab domes - crack grooves
  C(g)    crest envelope by the geodesic distance g from the legs' feet: 18 px over the crown, a
          convex pchip roll-off down each leg to the ground at its foot;
  f_out   rounded shoulder on the outer edge; f_in  S-drop to the lip on the opening side;
  slabs   the rock cut by the few long crack lines the sprite shows (traced from the sprite and the
          leg tiles); each slab a convex faired dome over its whole width, gentle on its north-west
          (lit) side, steeper on its south-east (shadow) side, rounding down into its cracks; short
          transverse breaks stack the leg slabs; the legs' vertical flutes are soft shallow grooves;
  grooves recessed V/U grooves (geometry), so the scene's light shades them (art rule 2);
  seam    within 9 px of column 72 the crown takes the wall stretches' section (seam_height of
          assembly-newsh3-198.py) so SURFACE's inserted stretches join flush.
Colour: a continuous tone (fractional palette index): the sprite's own value smoothed over the rock
(so the pale crown covers the sprite's light px and ends where the sprite's does) mixed with the
slab medians softened across their cracks, crack floors a little darker. Each slab takes one pal_
material (its brightest tone) and the tone rides on COLOR_0 as a multiplier of that palette colour
(Tone; three.js multiplies base colour by COLOR_0): a smooth ramp, no iso-line terraces (fix round 2).
Matte sandstone (metallic 0, roughness 0.88), no ribbons or painted lines.
Outline shell from a sealed pre-cut copy (common.outline_shell, islands="outer"), cut per piece
without caps so no ink crosses a join; underside flat at z = 0.
"""

import heapq
import json
import math
import os
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


def _find_repo():
    for p in Path(__file__).resolve().parents:
        if (p / "assets" / "blender" / "common.py").exists():
            return p
    raise RuntimeError("repo root (assets/blender/common.py) not found above " + __file__)


ROOT = _find_repo()
sys.path[:0] = [str(ROOT / "assets" / "blender"), str(ROOT / "tools")]
import common  # noqa: E402
import sprite_mask as SM  # noqa: E402

DATA = Path(os.environ.get("TYRIAN_DATA", ROOT / "data"))
U = 1 / 12

# ---- the scenes: the arch (arch frame) and the plain wall stretch ------------------------------
SCENE = "arch"
X0, W, H = -24, 168, 112          # sheet columns -24..144, rows 0..112
CENTRE = (60, 28)                 # the sheet's centre (the arch sheet is 120 x 56): Blender's origin
OPEN_ENDS = ()                    # sheet columns where the rock carries on into the next stretch
TILE_TOP = 55
LEG_TILES = {"left": ([[26, 27, 28, 29], [36, 37, 38, 39]], -24), "right": ([[8, 9], [18, 19]], 96)}
LEG_NAMES = {"left": "arch-leg-left", "right": "arch-leg-right"}
# draw order (later wins the pixel): ground-pass pieces, the arch, then the top-layer edge rocks
ARCH_PIECES = PIECES = [("newsh3-281", 96, 28), ("newsh3-282", 108, 28),
          ("newsh3-162", 24, 0), ("newsh3-164", 48, 0), ("newsh3-241", 72, 0),
          ("newsh3-198", 0, 28), ("newsh3-200", 24, 28), ("newsh3-202", 48, 28), ("newsh3-279", 72, 28),
          ("newsh3-262", 96, 14), ("newsh3-180", 12, 13)]


WALL_PIECES = [("newsh3-166", 0, 0), ("newsh3-168", 24, 0), ("newsh3-170", 48, 0),
               ("newsh3-204", 0, 28), ("newsh3-206", 24, 28), ("newsh3-208", 48, 28)]


def use(scene):
    """Switch the module to a scene: "arch" (crown, edge rocks, legs) or "wall" (the plain stretch
    SURFACE and DESERTRUN insert at the arch's column 72, 72 x 56 px, open at both ends)."""
    global SCENE, X0, W, H, CENTRE, OPEN_ENDS, PIECES, CRACKS, RIDGE
    SCENE = scene
    if scene == "arch":
        X0, W, H, CENTRE, OPEN_ENDS = -24, 168, 112, (60, 28), ()
        PIECES, CRACKS, RIDGE = ARCH_PIECES, ARCH_CRACKS, ARCH_RIDGE
    else:
        X0, W, H, CENTRE, OPEN_ENDS = 0, 72, 56, (36, 28), (0, 72)
        PIECES, CRACKS, RIDGE = WALL_PIECES, WALL_CRACKS, WALL_RIDGE


def read_shapes(path):
    sb = path.read_bytes()
    out, q = [], 0
    for _ in range(600):
        blank = sb[q] != 0
        q += 1
        if blank:
            out.append(None)
        else:
            out.append(np.frombuffer(sb, np.uint8, 24 * 28, q).reshape(28, 24).astype(int))
            q += 24 * 28
    return out


def level_rgb():
    pal = (DATA / "palette.dat").read_bytes()[5 * 768:6 * 768]
    c = [((v << 2) | (v >> 4)) & 0xFF for v in pal]
    return [tuple(c[3 * i:3 * i + 3]) for i in range(256)]


def compose():
    shapes = read_shapes(DATA / "shapes).dat")
    gnd = np.full((H, W), -1, int)
    for side, (pat, c0) in (LEG_TILES.items() if SCENE == "arch" else ()):
        for r, row in enumerate(pat):
            for c, t in enumerate(row):
                px = shapes[t]
                y, x = TILE_TOP + r * 28, c0 + c * 24 - X0
                hh = min(28, H - y)
                gnd[y:y + hh, x:x + 24] = px[:hh]
    spr = np.full((H, W), -1, int)
    owner = np.full((H, W), "", object)
    colors = {}
    for name, c0, r0 in PIECES:
        d = common.load_sprite(ROOT, name)
        colors.update(d["colors"])
        for yy, row in enumerate(d["frames"][0]["pixels"]):
            for xx, v in enumerate(row):
                if v >= 0:
                    spr[r0 + yy, c0 + xx - X0] = v
                    owner[r0 + yy, c0 + xx - X0] = name
    rgb = level_rgb()
    for i in range(256):
        colors.setdefault(str(i), list(rgb[i]))
    return spr, gnd, owner, colors


# ---- numpy-only image ops (Blender has no scipy) ------------------------------------------------

def shift(a, dr, dc, fill=False):
    out = np.full_like(a, fill)
    h, w = a.shape
    out[max(0, dr):h + min(0, dr), max(0, dc):w + min(0, dc)] = a[max(0, -dr):h + min(0, -dr), max(0, -dc):w + min(0, -dc)]
    return out


def dilate(m, n=1):
    for _ in range(n):
        m = m | shift(m, 1, 0) | shift(m, -1, 0) | shift(m, 0, 1) | shift(m, 0, -1)
    return m


def erode(m, n=1):
    for _ in range(n):
        m = m & shift(m, 1, 0, True) & shift(m, -1, 0, True) & shift(m, 0, 1, True) & shift(m, 0, -1, True)
    return m


def label(m):
    """4-connected components (0 = background)."""
    lab = np.zeros(m.shape, int)
    h, w = m.shape
    n = 0
    flat = m.ravel()
    lf = lab.ravel()
    for start in np.flatnonzero(flat):
        if lf[start]:
            continue
        n += 1
        stack = [start]
        lf[start] = n
        while stack:
            p = stack.pop()
            r, c = divmod(p, w)
            for q, ok in ((p - w, r > 0), (p + w, r < h - 1), (p - 1, c > 0), (p + 1, c < w - 1)):
                if ok and flat[q] and not lf[q]:
                    lf[q] = n
                    stack.append(q)
    return lab, n


def fill_holes(m):
    lab, n = label(~m)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    return m | ((lab > 0) & ~np.isin(lab, list(border)))


def gauss(a, sigma):
    r = int(math.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    p = np.pad(a, r, mode="edge")
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 0, p)
    p = np.apply_along_axis(lambda v: np.convolve(v, k, mode="valid"), 1, p)
    return p


def edt(feature):
    """Exact Euclidean distance to the nearest True cell, and its (row, col) (Felzenszwalb)."""
    h, w = feature.shape
    INF = 1e12
    # pass 1: per column, distance along the column and the feature row
    g = np.full((h, w), INF)
    gr = np.full((h, w), -1, int)
    last = np.full(w, -10 ** 9)
    for r in range(h):
        last = np.where(feature[r], r, last)
        g[r] = r - last
        gr[r] = last
    last = np.full(w, 10 ** 9)
    for r in range(h - 1, -1, -1):
        last = np.where(feature[r], r, last)
        d = last - r
        better = d < g[r]
        g[r] = np.where(better, d, g[r])
        gr[r] = np.where(better, last, gr[r])
    g = np.minimum(g, 1e6) ** 2
    D = np.empty((h, w))
    IR = np.empty((h, w), int)
    IC = np.empty((h, w), int)
    for r in range(h):
        f = g[r].tolist()
        v = [0] * w
        z = [0.0] * (w + 1)
        k = 0
        z[0], z[1] = -1e30, 1e30
        for q in range(1, w):
            while True:
                p = v[k]
                s = ((f[q] + q * q) - (f[p] + p * p)) / (2 * q - 2 * p)
                if s <= z[k] and k > 0:
                    k -= 1
                    continue
                if s <= z[k]:
                    # k == 0 and s <= -inf cannot happen; guard
                    pass
                break
            k += 1
            v[k] = q
            z[k] = s
            z[k + 1] = 1e30
        k = 0
        dr, cr = [0.0] * w, [0] * w
        for q in range(w):
            while z[k + 1] < q:
                k += 1
            p = v[k]
            dr[q] = (q - p) ** 2 + f[p]
            cr[q] = p
        D[r] = dr
        IC[r] = cr
        IR[r] = gr[r][cr]
    return np.sqrt(D), IR, IC


# ---- copied from assembly-newsh3-198.py: the wall stretches' seam section (SURFACE joins) -------
S_CREST, S_FOOT, S_LEG_ROW, S_SHOULDER, S_SHOULDER_H, S_FALL = 19.5, 3.0, 34, 6.0, 0.55, 8.0
S_LIP, S_LEG_LIP, S_LEG_ROWS, S_EDGE, S_TOE = 0.2, 0.6, (40, 50), 0.3, 0.9
SEAM_COL, SEAM_R0, SEAM_R1, SEAM_BLEND = 72, 3.0, 40.0, (2.0, 9.0)


def _c01(x):
    return max(0.0, min(1.0, x))


def _ss(x):
    x = _c01(x)
    return x * x * (3 - 2 * x)


def seam_height(r, h=56):
    crest = S_CREST - (S_CREST - S_FOOT) * _c01((r - S_LEG_ROW) / (h - S_LEG_ROW))
    d_out, d_in = max(0.0, r - SEAM_R0), max(0.0, SEAM_R1 - r)
    t = _c01((d_out - S_TOE) / S_SHOULDER)
    q = _c01((d_out - S_TOE - S_SHOULDER) / max(1.0, d_out + d_in - S_TOE - S_SHOULDER - S_FALL))
    rise = (1 - (1 - t) ** 2) * (S_SHOULDER_H + (1 - S_SHOULDER_H) * q)
    lip = S_LIP + (S_LEG_LIP - S_LIP) * _ss((r - S_LEG_ROWS[0]) / (S_LEG_ROWS[1] - S_LEG_ROWS[0]))
    return max(S_EDGE, crest * rise * (lip + (1 - lip) * _ss(_c01(d_in / S_FALL))))


# ---- the design's numbers -----------------------------------------------------------------------
K = 4                       # working grid cells per sprite px
STEP = 4                    # mesh vertex every 4 cells = 1 px (no decimation: clean tone contours)
CREST_G = [0, 2, 6, 14, 26, 40, 56, 74, 300]           # px from the foot (geodesic)
CREST_Z = [1.0, 4.0, 8.0, 11.5, 14.0, 16.0, 17.4, 18.0, 18.0]   # legs keep their mass to the foot
# across the band: a rounded shoulder on the outer (north) edge up to the crest RO px in, then a long
# fall over FALL px to the lip at the opening, so the sprite's pale crown is a broad top facing up and
# south (towards the game camera and its sun) and the brown front face drops into the opening; no
# sheer walls (fix round 2: the crest FALL px from the opening put the pale crown on a north-facing
# back slope the tilted camera crushed to a strip, and the outer edge was a cliff)
RO, FALL = 11.0, 20.0
PILLOW, R_LIT, R_SHADOW = 4.0, 5.0, 2.2     # slab bulge (px) and its lit / shadow fall-off radii
# grooves per crack kind: (depth px, half width px, flat floor half width px); the legs' traced
# columns (flutes) are slab boundaries too, so every leg column is its own bulging slab
GROOVE = {"main": (2.0, 1.5, 0.3), "break": (0.8, 1.2, 0.3), "flute": (1.3, 1.4, 0.3)}
TONE_SIGMA = 2.6            # px: slab tones blend across slab boundaries within the lit crown / the body
LIT_PAL = 24                # slabs at or above this index are the lit crown (blended among themselves)
SPINE_W, SPINE_LIFT = 1.1, 0.35
EDGE_Z = 0.4
LEG_CUT_INSET = -0.15       # px: a crown piece's outline shell stops this far short of the leg join
SHELL_KEEP = 3.0            # px: the outline shell is kept this far in from the silhouette
JOIN_CLEAR = 5.0            # px: and this far from a join in front of a lower-pass piece
ROUGH = 0.88
LEG_GROOVE_FADE = 0.25      # the traced long cracks keep this much less depth down the legs
FIS_T, FIS_WEAK, FIS_MIN, FIS_MAX = 3, 1, 9, 24   # fissure px: runs of >= FIS_MIN px >= 1 index under the closing round them holding one >= 3, index <= 24
FIS_SIGMA, FIS_LINE, FIS_FULL = 0.55, 0.16, 0.32   # fissure groove blur (px), line level, full depth level
FIS_DEPTH = 1.0             # px
TONE_MAX_PAL = 28           # highlights capped (the light makes the shine)
TONE_S_SIGMA, TONE_MIX = 2.0, 0.35  # the sprite's smoothed value (px) and the slab medians' share
TONE_P_SIGMA = 1.2          # px: the slab medians soften across their cracks
CRACK_DARK = 1.5            # indices darker at a groove's floor
TONE_ATTR = "rock_tone"     # COLOR_0: the continuous tone as a multiplier of the face's palette colour
ARCH_CRACKS = CRACKS = {
    'C1_lit_front':   [(36, 21.0), (44, 21.2), (51, 20.4), (60, 20.2), (68, 20.3), (73.4, 20.4)],
    'C2_right_leg':   [(76.5, 2.0), (74.6, 9), (73.6, 15), (73.4, 20.4), (77, 24), (80.5, 27.2), (87, 28.6),
                       (95, 31.5), (102, 35.5), (107, 41), (110, 47), (112, 52), (111.5, 57), (110.2, 64),
                       (109.6, 75), (109.6, 86), (110.5, 94)],
    'C3_front_inner': [(33.6, 33.4), (40, 33.5), (47, 32.8), (54, 32.2), (62, 31.7), (70, 31.6), (78, 31.6), (83, 32.4),
                       (90, 35.5), (96.5, 39.5), (99.5, 45), (101, 51), (101.4, 57), (100.6, 68), (100.2, 82), (100.4, 94)],
    'C4_hex_left':    [(51, 20.4), (50.8, 24), (51.4, 28), (53, 31), (54, 32.2)],
    'C6_right_wedge': [(80.5, 27.2), (85, 24.4), (90, 22.0), (96.2, 20.4), (104, 19.6), (112, 22)],
    'L2_knuckle_inner': [(36, 21.0), (35.4, 24.5), (34.6, 28.5), (33.6, 33.4), (31.6, 38), (29.4, 43), (27.2, 49),
                         (25.8, 56), (26.6, 66), (27.2, 78), (27.6, 90), (28, 100)],
    'L1_lit_mid':     [(31.6, 38), (26, 42), (21, 47), (16.5, 52), (14, 58), (13.2, 68), (13, 80), (13.2, 92), (13.6, 101)],
    'L0_outer':       [(16, 34), (10, 42), (5, 50), (1, 57), (-1.8, 64), (-3, 76), (-4, 88), (-5.5, 99)],
    'K_top':          [(36, 21.0), (30, 19.8), (24, 19.8)],
    'K_bot':          [(33.6, 33.4), (26, 35.0), (16, 34)],
    'R2_outer':       [(112, 22), (115, 30), (119, 38), (122, 47), (123.6, 57), (124.3, 70), (124.4, 84), (124, 96)],
    # leg columns traced on the leg tiles (left: lit outer column | mid | dark fissures | inner face)
    'L3_col':         [(36.5, 40), (34.6, 50), (33.4, 58), (34.6, 70), (35.6, 85), (36, 100)],
    'L4_col':         [(44, 36), (42.4, 48), (42, 60), (42.8, 75), (44, 92)],
    'L5_col':         [(4.5, 56), (5.6, 70), (6.6, 85), (6, 100)],
    'L6_col':         [(20.5, 58), (21.2, 72), (22, 88), (22.2, 100)],
    # right leg: mid columns between the inner face and the outer flank
    'R3_col':         [(86, 29), (95, 36), (103, 44), (106, 52), (105.4, 62), (104.6, 80), (105, 95)],
    # short transverse breaks: the leg columns are stacked blocks, not pipes (traced on the tiles)
    'T_l1': [(-6, 67), (-1, 64.5), (4.6, 62)],
    'T_l2': [(6.4, 84), (10, 81.5), (13.2, 79.5)],
    'T_l3': [(13.4, 64), (17.5, 62.6), (21, 61.4)],
    'T_l4': [(21.6, 77), (27, 75.6), (34.8, 74)],
    'T_l5': [(34, 62), (38.5, 60.8), (42.2, 59.6)],
    'T_l6': [(35.6, 84), (40, 82.4), (43.4, 81)],
    'T_l7': [(21.8, 91), (25, 89.6), (27.5, 88.6)],
    'T_r1': [(100.6, 68), (105, 66.5), (109.8, 65)],
    'T_r2': [(110.4, 58), (114, 56.6), (117.8, 55.4)],
    'T_r3': [(104.6, 84), (107.5, 82.6), (109.6, 81.6)],
    'T_r4': [(118.2, 75), (121.5, 73.6), (124.3, 72.4)],
    'T_r5': [(124.4, 62), (128.5, 60.5), (133, 59)],
    'R4_col':         [(100, 24), (109, 32), (115.5, 42), (117.6, 52), (118, 66), (118.2, 80), (118, 96)],
}
FLUTES = {"L3_col", "L4_col", "L5_col", "L6_col", "R3_col", "R4_col"}


def crack_kind(name):
    return "flute" if name in FLUTES else "break" if name.startswith("T_") else "main"


ARCH_RIDGE = RIDGE = [(31.5, 29), (33.5, 23.5), (37, 19), (42, 15.3), (50, 12.6), (56, 10.6), (64, 8.0), (70, 6.6), (76, 6.0)]
# the plain wall stretch (sheet 72 x 56): the lit top's front edge (meeting the arch's C1 at row ~20.5
# at both ends), two cracks across the lit top, a diagonal one, and the face's vertical breaks
WALL_CRACKS = {
    'W_front': [(-2, 20.5), (6, 20.6), (12, 21.4), (18, 22.4), (24, 22.0), (29, 24.2), (33, 25.0), (38, 24.0), (46, 22.0),
                (52, 21.6), (58, 22.4), (64, 21.6), (74, 20.5)],
    'W_v1': [(23.2, 3.0), (22.6, 9.0), (23.4, 15.0), (24.0, 21.6)],
    'W_v2': [(57.2, 3.0), (56.2, 9.0), (57.4, 15.5), (58.0, 22.4)],
    'W_d1': [(7.5, 11.5), (11.0, 15.0), (14.5, 19.0), (18.0, 22.4)],
    'W_l1': [(19.6, 22.6), (19.0, 28.0), (18.0, 34.0), (17.0, 41.0)],
    'W_l2': [(46.0, 22.0), (45.2, 27.0), (46.0, 34.0)],
    'W_l3': [(62.0, 22.0), (63.0, 28.0), (62.4, 38.0)],
}
WALL_RIDGE = [(28, 10.6), (36, 9.6), (44, 9.0), (52, 8.6), (60, 8.2)]


def pchip(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    h = np.diff(xs)
    d = np.diff(ys) / h
    m = np.zeros_like(ys)
    for k in range(1, len(xs) - 1):
        if d[k - 1] * d[k] > 0:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
    m[0], m[-1] = d[0], d[-1]

    def f(x):
        x = np.clip(x, xs[0], xs[-1])
        i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def ease(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def build_field():
    spr, gnd, owner, colors = compose()
    rgbs = {int(k): tuple(v) for k, v in colors.items()}
    rock_t = (gnd >= 16) & (gnd <= 31)
    lab, n = label(rock_t)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    rock_t = np.isin(lab, [i for i in range(1, n + 1) if sizes[i] > 40])
    rock_t = fill_holes(erode(dilate(rock_t, 1), 1) | rock_t)
    rock_t[:56] = False                        # the crown's sprite owns the rows above
    mask_s = spr >= 0
    full = mask_s | rock_t
    idx = np.where(mask_s, spr, gnd)
    # D74: the object's ink ring is the game's outline, not the model (ring px next to the outside)
    outside = ~full
    side_fill = not OPEN_ENDS             # past an open end the rock carries on: not outside
    ring = full & (shift(outside, 1, 0, True) | shift(outside, -1, 0, True)
                   | shift(outside, 0, 1, side_fill) | shift(outside, 0, -1, side_fill))
    ink = np.vectorize(lambda v: v >= 0 and SM.luma(rgbs[int(v)]) < SM.INK_LUMA)(idx)
    MASK = full & ~(ring & ink)
    # owners: sprite pixels as drawn; tile rock px by side
    own = owner.copy()
    xs_px = np.arange(W) + X0
    for r in range(56, H):
        for c in range(W):
            if rock_t[r, c] and own[r, c] == "":
                own[r, c] = "leg-left" if xs_px[c] < 84 else "leg-right"
    return spr, gnd, idx, MASK, full, rock_t, own, rgbs, colors


def raster(poly, shape):
    img = np.zeros(shape, bool)
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * K * 3) + 2
        for t in np.linspace(0, 1, n):
            c = int(((x0 + (x1 - x0) * t) - X0) * K)
            r = int((y0 + (y1 - y0) * t) * K)
            if 0 <= r < shape[0] and 0 <= c < shape[1]:
                img[r, c] = True
    return img


def geodesic(mask, seeds, step=2):
    m = mask[::step, ::step]
    s = seeds.reshape(mask.shape[0] // step, step, mask.shape[1] // step, step).any(axis=(1, 3))
    D = np.full(m.shape, np.inf)
    hq = []
    for r, c in zip(*np.nonzero(s & m)):
        D[r, c] = 0
        hq.append((0.0, r, c))
    heapq.heapify(hq)
    nb = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
    hh, ww = m.shape
    while hq:
        d, r, c = heapq.heappop(hq)
        if d > D[r, c]:
            continue
        for dr, dc, w_ in nb:
            rr, cc = r + dr, c + dc
            if 0 <= rr < hh and 0 <= cc < ww and m[rr, cc] and d + w_ < D[rr, cc]:
                D[rr, cc] = d + w_
                heapq.heappush(hq, (d + w_, rr, cc))
    D = D * step / K
    return np.kron(D, np.ones((step, step)))


def extend_cracks(cracks, Mf):
    Hf, Wf = Mf.shape
    imgs = {k: raster(v, Mf.shape) for k, v in cracks.items()}
    out = {}
    for k, v in cracks.items():
        others = np.zeros(Mf.shape, bool)
        for k2, im in imgs.items():
            if k2 != k:
                others |= im
        others = dilate(others, 1)
        pts = [tuple(p) for p in v]
        for end in (0, 1):
            seq = pts if end else pts[::-1]
            (xa, ya), (xb, yb) = seq[-2], seq[-1]

            def at(x, y):
                c, r = int((x - X0) * K), int(y * K)
                return (r, c) if 0 <= r < Hf and 0 <= c < Wf else None
            rc = at(xb, yb)
            if rc and others[rc]:
                continue
            L = math.hypot(xb - xa, yb - ya) or 1
            dx, dy = (xb - xa) / L, (yb - ya) / L
            x, y, ext = xb, yb, []
            for _ in range(200):
                x += dx * 0.25
                y += dy * 0.25
                rc = at(x, y)
                if rc is None or not Mf[rc]:
                    break
                ext.append((x, y))
                if others[rc]:
                    break
            if ext:
                pts = pts + [ext[-1]] if end else [ext[-1]] + pts
        out[k] = pts
    return out


def trimmed_median(vals, rgbs):
    if len(vals) == 0:
        return None
    lum = lambda i: sum(rgbs.get(int(i), (0, 0, 0)))  # noqa: E731
    v = np.array(sorted(vals, key=lum))
    lo, hi = int(len(v) * 0.15), int(math.ceil(len(v) * 0.85))
    v = v[lo:max(hi, lo + 1)]
    return int(np.median(v))


def norm_blur(val, sel, sigma):
    """Blur of `val` over the cells of `sel` only (normalised: no bleed from outside `sel`)."""
    num = gauss(np.where(sel, val, 0.0), sigma)
    den = gauss(sel.astype(float), sigma)
    return np.where(den > 1e-6, num / np.maximum(den, 1e-6), val)


def grey_close(v, n=1):
    """Grey-level closing (max then min over the 3x3 neighbourhood, n times each)."""
    a = v.copy()
    for _ in range(n):
        a = np.maximum.reduce([a] + [shift(a, dr, dc, -1) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))])
    for _ in range(n):
        a = np.minimum.reduce([a] + [shift(a, dr, dc, 99) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))])
    return a


def fissures(IDX, FULL):
    """The sprite's (and the leg tiles') dark crack lines: rock px at least FIS_T indices darker than
    the grey closing round them (a black-hat), inside the rock, in line-like runs of >= 3 px. Also the
    index image with those lines and the ink ring filled from round them (the rock's own tone)."""
    rock = FULL & (IDX >= 16) & (IDX <= 31)
    _, nr, nc = edt(rock)
    v = IDX[nr, nc].astype(int)               # every px: its nearest rock px's index
    cl = grey_close(v, 1)
    bh = cl - v
    inner = erode(FULL, 2)
    # hysteresis: runs of px >= FIS_T - 1 darker that hold at least one >= FIS_T, not inside a
    # highlight (the gaps between a highlight's specks read dark against it)
    weak = inner & rock & (bh >= FIS_WEAK) & (v <= FIS_MAX) & (cl <= 27)
    strong = weak & (bh >= FIS_T)
    lab, n = label(weak)
    keep = np.zeros(n + 1, bool)
    for s in range(1, n + 1):
        sel = lab == s
        rr, cc = np.nonzero(sel)
        if len(rr) >= FIS_MIN and max(rr.max() - rr.min(), cc.max() - cc.min()) >= FIS_MIN - 1 and strong[sel].any():
            keep[s] = True
    fis = keep[lab] & (lab > 0)
    ring = FULL & ~erode(FULL, 1)
    clean = np.where(fis | ring | ~rock, cl, v)
    return fis, np.clip(clean, 17, TONE_MAX_PAL), np.clip(bh, 0, 6)


def heights(tone_ref=None):
    """The rock's fields. `tone_ref` (wall scene): the arch's tone down its column 72, per working
    row; the stretch's rows are shifted so its cut ends take the arch's tone there (SURFACE and
    DESERTRUN put stretches into the arch at that column: no lighter or darker block)."""
    spr, gnd, IDX, MASK, FULL, rock_t, OWN, rgbs, colors = build_field()
    FIS, CLEAN, BH = fissures(IDX, FULL)
    up = lambda a: np.kron(a, np.ones((K, K), a.dtype))  # noqa: E731
    Mf = gauss(up(MASK).astype(float), 0.9 * K) > 0.5
    Mf |= erode(up(MASK), K // 2) & ~Mf
    # the rock tip newsh3-180 is a 7 px knob: its own pixels exactly (the smoothing would eat it)
    # and nothing more in its corner: no bridge over the 1 px slot between it and 198, no rounding
    # past its pixels (its sprite is 5 px inside the ink: a smoothed outline is half off it)
    Mf = fill_holes(Mf)
    if SCENE == "arch":
        tip = np.zeros(MASK.shape, bool)
        tip[13:28, 12 - X0:24 - X0] = True
        tip_own = MASK & (OWN == "newsh3-180")
        Mf = np.where(up(tip), (Mf & up(FULL & (OWN != "newsh3-180"))) | up(tip_own), Mf)
    Hf, Wf = Mf.shape
    xs = (np.arange(Wf) + 0.5) / K + X0
    ys = (np.arange(Hf) + 0.5) / K
    XX, YY = np.meshgrid(xs, ys)
    ext = ~Mf
    if SCENE == "arch":
        wall = np.zeros_like(ext)
        wall[int(96 * K):, int((30 - X0) * K):int((120 - X0) * K)] = True
        lab_e, _ = label(ext & ~wall)
        hole = lab_e == lab_e[int(70 * K), int((80 - X0) * K)]
        hole |= ext & wall & (XX > 44) & (XX < 100)
        assert not hole[int(2 * K), int((56 - X0) * K)], "the opening leaks into the outside"
    else:  # the stretch: the outside north of the band (its outer edge) and south of it (its foot)
        lab_e, _ = label(ext)
        north = set(np.unique(lab_e[0])) - {0}
        hole = ext & ~np.isin(lab_e, list(north))
    outer = ext & ~hole
    d_out = edt(outer)[0] / K
    d_in = edt(hole)[0] / K
    if SCENE == "arch":
        south = Mf & ~shift(Mf, -1, 0, False)
        feet = south & (YY > 86)
        G = geodesic(Mf, feet)
        G[~np.isfinite(G)] = 200
        C = pchip(CREST_G, CREST_Z)(np.clip(G, 0, 300))
        f_out = 0.08 + 0.92 * np.sin(0.5 * np.pi * np.clip(d_out / RO, 0, 1)) ** 1.0
        lip = 0.22 + 0.25 * ease((YY - 44) / 20)
        f_in = lip + (1 - lip) * np.sin(0.5 * np.pi * np.clip(d_in / FALL, 0, 1)) ** 1.1
        BASE = C * f_out * f_in
    else:  # the crown's section run along the stretch (seam_height's, measured from its own edges)
        C = S_CREST - (S_CREST - S_FOOT) * np.clip((YY - S_LEG_ROW) / (56 - S_LEG_ROW), 0, 1)
        t = np.clip((d_out - S_TOE) / S_SHOULDER, 0, 1)
        q = np.clip((d_out - S_TOE - S_SHOULDER) / np.maximum(1.0, d_out + d_in - S_TOE - S_SHOULDER - S_FALL), 0, 1)
        rise = (1 - (1 - t) ** 2) * (S_SHOULDER_H + (1 - S_SHOULDER_H) * q)
        lip_r = np.minimum(YY, SEAM_R1)
        lip = S_LIP + (S_LEG_LIP - S_LIP) * ease((lip_r - S_LEG_ROWS[0]) / (S_LEG_ROWS[1] - S_LEG_ROWS[0]))
        BASE = np.maximum(S_EDGE, C * rise * (lip + (1 - lip) * ease(d_in / S_FALL)))

    cracks = {k: chaikin_open(v) for k, v in extend_cracks(CRACKS, Mf).items()}
    imgs = {kind: np.zeros(Mf.shape, bool) for kind in GROOVE}
    for k, v in cracks.items():
        imgs[crack_kind(k)] |= raster(v, Mf.shape)
    dist = {kind: edt(im)[0] / K for kind, im in imgs.items()}
    # slabs: the rock between the main cracks (flutes and breaks only shape them)
    bounds = imgs["main"] | imgs["flute"]
    d_crack, ir, ic = edt(bounds)
    d_crack = d_crack / K
    cut = dilate(bounds, 2)
    slab_lab, n_slab = label(Mf & ~cut)
    sizes = np.bincount(slab_lab.ravel(), minlength=n_slab + 1)
    for s in range(1, n_slab + 1):
        if sizes[s] < 30 * K * K:
            slab_lab[slab_lab == s] = 0
    _, jr, jc = edt(slab_lab > 0)
    slab_lab = np.where(Mf, slab_lab[jr, jc], 0)

    # the sprite's own fissures (its dark crack px, fissures()): rounded grooves along them, and
    # each slab domes up between them
    fis_w = gauss(up(np.where(FIS, np.minimum(BH, 4) / 4.0, 0.0)), FIS_SIGMA * K)
    fis_line = Mf & (fis_w > FIS_LINE)
    d_fis = edt(fis_line)[0] / K if fis_line.any() else np.full(Mf.shape, 99.0)
    # the dome: distance to the nearest main crack, transverse break or fissure
    # (not the fissures: domes between every short dark px run made blobs, not slabs)
    d_dome = np.minimum(d_crack, dist["break"] + 0.4)
    vx = (ic - np.arange(Wf)[None, :]) / K
    vy = (ir - np.arange(Hf)[:, None]) / K
    se = (vx * 0.6 + vy * 0.8) > 0          # the crack lies south-east: steeper shadow face
    k_h = np.clip(C / 9.0, 0.6, 1.0)     # the leg slabs keep their bulge down to the feet
    maxd = np.zeros(n_slab + 1)
    np.maximum.at(maxd, slab_lab.ravel(), np.where(Mf, d_crack, 0).ravel())
    Ms = maxd[slab_lab]
    R_eff = np.clip(0.95 * Ms, 2.5, 10.0)
    R = np.where(se, np.minimum(R_eff, R_SHADOW + 0.35 * R_eff), R_eff)
    amp = PILLOW * np.clip(Ms / 4.5, 0.55, 1.35)
    # convex over the slab's width (sin-like rise, no flat plateau), rounded into the groove
    t = np.clip(d_dome / R, 0, 1)
    dome = amp * k_h * np.sin(0.5 * np.pi * ease(np.minimum(1.0, t * 1.15)) ** 0.85)
    groove = np.zeros_like(BASE)
    # down the legs the traced long cracks shallow out (full length they read as curtain folds); the
    # sprite's own broken fissures carry the legs
    leg_k = 1 - LEG_GROOVE_FADE * ease((YY - 58) / 14)
    for kind, (depth, half, floor) in GROOVE.items():
        g = depth * k_h * ease((half - dist[kind]) / (half - floor))
        groove = np.maximum(groove, g if kind == "break" else g * leg_k)
    groove = np.maximum(groove, FIS_DEPTH * k_h * ease(fis_w / FIS_FULL))
    gfrac = np.clip((groove / (FIS_DEPTH * k_h) - 0.4) / 0.6, 0, 1)   # the floor only
    fade = ease(d_out / 2.5) * ease(d_in / 2.5)
    Z = BASE + (dome - groove) * fade
    # rounded edge: the rock rolls over into a steep face at the silhouette (no cliff or comb at the lip)
    d_edge = np.minimum(d_out, d_in)
    # (over 2-3 px: rolled over within a px or so, the edge row's few grid vertices stood at uneven
    # heights over the projected silhouette and drew a saw of thin dark teeth along the base)
    Z = EDGE_Z + (Z - EDGE_Z) * (ease(d_out / 2.2) ** 0.8) * (ease(d_in / 3.0) ** 0.7)
    # SURFACE's wall stretches: the crown's section at column 72 is the stretches' seam_height
    seam = np.array([seam_height(y) for y in ys])[:, None] * np.ones((1, Wf))
    dsx = np.abs(XX - SEAM_COL) if SCENE == "arch" else np.minimum(np.abs(XX - OPEN_ENDS[0]), np.abs(XX - OPEN_ENDS[1]))
    wgt = 1 - ease((dsx - SEAM_BLEND[0]) / (SEAM_BLEND[1] - SEAM_BLEND[0]))
    wgt = np.where(YY < 44, wgt, 0.0)
    Z = Z + (seam - Z) * wgt
    Z = np.where(Mf, np.maximum(Z, 0.15), 0)
    d_ridge = edt(raster(chaikin_open(RIDGE), Mf.shape))[0] / K
    spine = Mf & (d_ridge < SPINE_W) & (YY < 30) & (wgt < 0.5)
    Z = np.where(spine, Z + SPINE_LIFT * (1 - d_ridge / SPINE_W), Z)

    # the outline shell's surface: the rock with its grooves bridged and its domes' small dips filled
    # (a closing), smoothed, never under the rock. Its horizon and silhouette are one smooth line, so
    # the ink keeps one width (fix round 2: the shell sunk under every dome followed the bumps and the
    # ink went thick, thin and jaggy). Over a groove it lies above the floor, facing up: the inverted
    # hull draws only back faces, so it inks nothing there.
    Zc = np.where(Mf, Z, -1e3)
    n_c = int(1.5 * K)
    for _ in range(n_c):
        Zc = np.maximum.reduce([Zc, shift(Zc, 1, 0, -1e3), shift(Zc, -1, 0, -1e3), shift(Zc, 0, 1, -1e3), shift(Zc, 0, -1, -1e3)])
    Zc = np.where(Mf, Zc, 1e3)
    for _ in range(n_c):
        Zc = np.minimum.reduce([Zc, shift(Zc, 1, 0, 1e3), shift(Zc, -1, 0, 1e3), shift(Zc, 0, 1, 1e3), shift(Zc, 0, -1, 1e3)])
    Zc = np.where(Mf & (Zc < 500), Zc, Z)
    ZS = np.maximum(Z, norm_blur(Zc, Mf, 1.2 * K))
    ZS = np.where(Mf, np.maximum(ZS, 0.1), 0)

    # colours
    ringpx = FULL & ~erode(FULL, 1)
    slab_px = slab_lab[K // 2::K, K // 2::K]
    info = {}
    for s in range(1, n_slab + 1):
        sel = (slab_px == s) & MASK & ~ringpx & (IDX >= 16) & (IDX <= 31)
        if not sel.any():
            sel = (slab_px == s) & FULL & (IDX >= 16) & (IDX <= 31)
        if not (slab_lab == s).any():
            continue
        rr, cc = np.nonzero(slab_lab == s)
        info[s] = {"pal": trimmed_median(IDX[sel].tolist(), rgbs) or 22,
                   "c": (round(cc.mean() / K + X0, 1), round(rr.mean() / K, 1)), "area": round(len(rr) / K / K, 1)}
    sp_sel = (d_ridge[K // 2::K, K // 2::K] < 1.6) & MASK & (IDX >= 16) & (np.arange(H)[:, None] < 30)
    spine_pal = min(28, trimmed_median(IDX[sp_sel].tolist(), rgbs) or 28)
    P = np.zeros(Mf.shape)
    for s, v in info.items():
        P[slab_lab == s] = v["pal"]
    P[Mf & (P == 0)] = 22
    # The tone is continuous (fix round 2): the sprite's own value (its index image with the fissures
    # and the ink ring filled in) smoothed over the rock, so the pale crown covers the sprite's light
    # px on each crown slab and its edge runs where the sprite's does (along its cracks, not a ruler
    # line), mixed with the slab medians softened across their cracks. It is never rounded to
    # indices: make_objects gives each slab one palette material and carries the tone as a COLOR_0
    # multiplier (no iso-line terraces).
    Pm = norm_blur(P, Mf, TONE_P_SIGMA * K)
    S = norm_blur(up(CLEAN).astype(float), Mf, TONE_S_SIGMA * K)
    T = TONE_MIX * Pm + (1 - TONE_MIX) * S
    # the cracks are dark lines in the sprite: their floors a few indices darker (and the groove's
    # own lighting on top)
    if tone_ref is not None and OPEN_ENDS:
        ends = Mf & ((np.abs(XX - OPEN_ENDS[0]) < 3) | (np.abs(XX - OPEN_ENDS[1]) < 3))
        corr = np.zeros(Mf.shape[0])
        for i in range(Mf.shape[0]):
            if ends[i].any() and i < len(tone_ref) and np.isfinite(tone_ref[i]):
                corr[i] = tone_ref[i] - np.median(T[i][ends[i]])
        corr = gauss(corr[:, None] * np.ones((1, 3)), 2.0 * K)[:, 1]
        T = T + corr[:, None]
    TF = np.clip(T - CRACK_DARK * gfrac * fade, 17, TONE_MAX_PAL)
    TONE = np.rint(TF).astype(int)
    # owner per working cell (nearest owned px)
    own_px = np.where(MASK | FULL, OWN, "")
    has = own_px != ""
    _, orr, occ = edt(has)
    own_full = own_px[orr, occ][(np.arange(Hf) // K)[:, None], (np.arange(Wf) // K)[None, :]]
    Bs = gauss(Mf.astype(float), 2.0)
    return dict(TPRE=T, Bs=Bs, Z=Z, Mf=Mf, xs=xs, ys=ys, XX=XX, YY=YY, slab=slab_lab, info=info, spine=spine,
                spine_pal=spine_pal, d_crack=d_crack, k_h=k_h, own=own_full, MASK=MASK, FULL=FULL,
                IDX=IDX, colors=colors, cracks=cracks, d_out=d_out, d_in=d_in, C=C, TONE=TONE, TF=TF, OWNPX=OWN, ZS=ZS)


# ---- mesh ---------------------------------------------------------------------------------------

def piece_centre(name):
    if name.startswith("leg-"):
        side = name[4:]
        pat, c0 = LEG_TILES[side]
        return c0 + 12 * len(pat[0]), TILE_TOP + 14 * len(pat)
    for n, c0, r0 in PIECES:
        if n == name:
            return (c0 + 6, r0 + 7) if n == "newsh3-180" else (c0 + 12, r0 + 14)
    raise KeyError(name)


def piece_box(name):
    """(c0, r0, c1, r1) in sheet px: the sprite's box, or the leg's tiles from the crown's edge down."""
    if name.startswith("leg-"):
        pat, c0 = LEG_TILES[name[4:]]
        return c0, 56, c0 + 24 * len(pat[0]), TILE_TOP + 28 * len(pat)
    for n, c0, r0 in PIECES:
        if n == name:
            w, h = (12, 14) if n == "newsh3-180" else (24, 28)
            return c0, r0, c0 + w, r0 + h
    raise KeyError(name)


def bx(c):
    return (c - CENTRE[0]) * U   # the sheet's centre at the origin


def by(r):
    return (CENTRE[1] - r) * U


def sample(A, x, y):
    j = (x - X0) * K - 0.5
    i = y * K - 0.5
    i0 = int(np.clip(math.floor(i), 0, A.shape[0] - 2))
    j0 = int(np.clip(math.floor(j), 0, A.shape[1] - 2))
    ti, tj = min(1, max(0, i - i0)), min(1, max(0, j - j0))
    return ((A[i0, j0] * (1 - tj) + A[i0, j0 + 1] * tj) * (1 - ti)
            + (A[i0 + 1, j0] * (1 - tj) + A[i0 + 1, j0 + 1] * tj) * ti)


def project(B, x, y):
    """Move (x, y) onto the smoothed silhouette (level 0.5 of B), a few Newton steps."""
    e = 0.5 / K
    for _ in range(6):
        v = sample(B, x, y) - 0.5
        gx = (sample(B, x + e, y) - sample(B, x - e, y)) / (2 * e)
        gy = (sample(B, x, y + e) - sample(B, x, y - e)) / (2 * e)
        g2 = gx * gx + gy * gy
        if g2 < 1e-6:
            break
        step = max(-0.6, min(0.6, v / g2))
        x, y = x - step * gx, y - step * gy
        if abs(v) < 0.01:
            break
    return x, y


def chaikin_open(pts, it=3):
    for _ in range(it):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [(a[0] * 0.75 + b[0] * 0.25, a[1] * 0.75 + b[1] * 0.25), (a[0] * 0.25 + b[0] * 0.75, a[1] * 0.25 + b[1] * 0.75)]
        out.append(pts[-1])
        pts = out
    return pts


def build_mesh(F):
    Z, Mf, xs, ys = F["Z"], F["Mf"], F["xs"], F["ys"]
    Hf, Wf = Mf.shape
    gi = np.arange(0, Hf, STEP)
    gj = np.arange(0, Wf, STEP)
    Mv = dilate(Mf, STEP)
    _, nr, nc = edt(Mf)
    vco, tv, vzs = {}, {}, {}
    for a, r in enumerate(gi):
        for b, c in enumerate(gj):
            if not Mv[r, c]:
                continue
            if Mf[r, c]:
                vco[a, b] = (xs[c], ys[r], Z[r, c])
                tv[a, b] = float(F["TF"][r, c])
                vzs[a, b] = float(F["ZS"][r, c])
            else:
                rr, cc = nr[r, c], nc[r, c]
                x, y = project(F["Bs"], xs[c], ys[r])
                vco[a, b] = (x, y, min(Z[rr, cc], EDGE_Z))
                tv[a, b] = float(F["TF"][rr, cc])
                vzs[a, b] = vco[a, b][2]
    if SCENE == "arch":  # the grid line at the arch's column 72 exactly on it (SURFACE's stretches meet it there)
        b72 = int(np.argmin(np.abs(xs[gj] - SEAM_COL)))
        for (a, b), (x, y, z) in list(vco.items()):
            if b == b72:
                vco[a, b] = (SEAM_COL, y, z)
    if OPEN_ENDS:  # the stretch's cut ends exactly on its sheet's edges (stretches and the arch meet there)
        last = len(gj) - 1
        for (a, b), (x, y, z) in list(vco.items()):
            if b in (0, last):
                vco[a, b] = (OPEN_ENDS[0] if b == 0 else OPEN_ENDS[1], y, z)
    quads = {}
    for a in range(len(gi) - 1):
        for b in range(len(gj) - 1):
            ks = [(a, b), (a, b + 1), (a + 1, b + 1), (a + 1, b)]
            if any(k not in vco for k in ks):
                continue
            if not any(Mf[gi[k[0]], gj[k[1]]] for k in ks):
                continue
            r = min(gi[a] + STEP // 2, Hf - 1)
            c = min(gj[b] + STEP // 2, Wf - 1)
            if not Mf[r, c]:
                r, c = nr[r, c], nc[r, c]
            quads[a, b] = (ks, int(F["slab"][r, c]), F["own"][r, c])
    # one set of vertex normals over the whole rock (area-weighted over every grid quad, whoever owns
    # it): the pieces and the leg tiles are separate meshes, and their own normals would part along
    # every cut (a shading step along each piece edge and the crown | leg join)
    acc = {}
    for ks, _, _ in quads.values():
        P = [np.array((bx(vco[k][0]), by(vco[k][1]), vco[k][2] * U)) for k in ks]
        n = np.cross(P[2] - P[0], P[3] - P[1])
        if n[2] < 0:
            n = -n
        for k in ks:
            acc[k] = acc.get(k, 0) + n
    nrm = {k: tuple(v / (np.linalg.norm(v) or 1)) for k, v in acc.items()}
    return vco, tv, vzs, quads, nrm


def srgb_lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


class Tone:
    """The continuous tone (a fractional palette index) as a multiplier of a face's palette colour:
    COLOR_0 = linear(palette colour at the tone, interpolated between its two indices) / linear(the
    face's palette colour). three.js multiplies the material colour by COLOR_0 (as newshd-245's lens
    tint), so the rock shows the continuous ramp whatever index each face's material takes."""

    def __init__(self, colors):
        self.lin = {int(k): srgb_lin(np.array(v[:3], float)) for k, v in colors.items()}

    def rgb(self, t):
        t = float(np.clip(t, 17, TONE_MAX_PAL))
        i = int(math.floor(t))
        f = t - i
        j = min(i + 1, TONE_MAX_PAL)
        return self.lin[i] * (1 - f) + self.lin[j] * f

    def ratio(self, t, base):
        r = self.rgb(t) / np.maximum(self.lin[base], 1e-4)
        return tuple(float(min(1.0, v)) for v in r) + (1.0,)


def make_objects(F, coll, mats):
    """One bmesh per owner (piece) plus a sealed whole for the outline shell. The top is the plain
    grid (two triangles per quad, split along the flatter diagonal); each slab takes one palette
    material (its median tone, raised where the tone runs brighter, so the multiplier stays <= 1)
    and the tone rides on COLOR_0 (Tone)."""
    vco, tv, vzs, quads, nrm = build_mesh(F)
    tone = Tone(F["colors"])
    slab_base = {}
    TF, SL = F["TF"], F["slab"]
    for s_ in np.unique(SL[F["Mf"]]):
        # (the slab's brightest tone, so nearly every face of it takes this one material: few draws)
        slab_base[int(s_)] = int(np.clip(math.ceil(float(np.percentile(TF[F["Mf"] & (SL == s_)], 99)) - 0.15),
                                         17, TONE_MAX_PAL))
    owners = sorted({q[2] for q in quads.values()})
    whole = bmesh.new()
    wv = {}

    def W_(k, z0=None):
        key = (k, z0)
        if key not in wv:
            x, y, _ = vco[k]
            wv[key] = whole.verts.new((bx(x), by(y), (vzs[k] if z0 is None else z0) * U))
        return wv[key]
    for (a, b), (ks, sl, ow) in quads.items():
        whole.faces.new([W_(k) for k in reversed(ks)])
        whole.faces.new([W_(k, 0.0) for k in ks])
        for e, (da, db) in enumerate(((-1, 0), (0, 1), (1, 0), (0, -1))):
            if (a + da, b + db) in quads:
                continue
            k0, k1 = ks[e], ks[(e + 1) % 4]
            whole.faces.new([W_(k1, 0.0), W_(k0, 0.0), W_(k0), W_(k1)])
    whole_obj = to_obj("arch_whole", whole, [], coll)

    # Each piece also takes the next piece's quads within a cell of the join (they overlap): the
    # pieces are drawn at different depths, and the rasteriser left a hairline of the sand between
    # two meshes that only met. Not across the arch's column 72, where SURFACE puts a stretch. The
    # overlap carries the same tone on both, so where both draw no seam shows.
    members = {ow: set() for ow in owners}
    xc = {k: sum(vco[kk][0] for kk in q[0]) / 4 for k, q in quads.items()}
    for (a, b), (ks, sl, o2) in quads.items():
        members[o2].add((a, b))
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                nb = quads.get((a + da, b + db))
                if nb is None or nb[2] == o2:
                    continue
                if SCENE == "arch" and (xc[a, b] - SEAM_COL) * (xc[a + da, b + db] - SEAM_COL) < 0:
                    continue
                members[nb[2]].add((a, b))
    objs = {}
    for ow in owners:
        bm = bmesh.new()
        col = bm.loops.layers.float_color.new(TONE_ATTR)
        vv = {}
        cx, cy = piece_centre(ow)
        normals = {}

        def V(k, z0=None, tag=0):
            key = (k, z0, tag)
            if key not in vv:
                x, y, z = vco[k]
                co = (bx(x) - bx(cx), by(y) - by(cy), (z if z0 is None else z0) * U)
                vv[key] = bm.verts.new(co)
                if z0 is None and tag == 0:
                    normals[pos_key(co)] = nrm.get(k, (0, 0, 1))
            return vv[key]
        slots = {}

        def slot(p):
            if p not in slots:
                slots[p] = len(slots)
            return slots[p]

        def paint(f, ts, base):
            f.material_index = slot(base)
            for lp, t in zip(f.loops, ts):
                lp[col] = tone.ratio(t, base)
        for (a, b), (ks, sl, o2) in quads.items():
            if (a, b) not in members[ow]:
                continue
            top = list(reversed(ks))
            if abs(vco[top[0]][2] - vco[top[2]][2]) <= abs(vco[top[1]][2] - vco[top[3]][2]):
                tris = [(top[0], top[1], top[2]), (top[0], top[2], top[3])]
            else:
                tris = [(top[0], top[1], top[3]), (top[1], top[2], top[3])]
            for tri in tris:
                try:
                    f = bm.faces.new([V(k) for k in tri])
                except ValueError:
                    continue
                ts = [tv[k] for k in tri]
                base = max(slab_base.get(sl, 22), int(math.ceil(max(ts) - 0.15)))
                paint(f, ts, min(TONE_MAX_PAL, base))
                f.smooth = True
            f = bm.faces.new([V(k, 0.0, 1) for k in ks])
            paint(f, [18] * 4, 18)
            for e, (da, db) in enumerate(((-1, 0), (0, 1), (1, 0), (0, -1))):
                nb = quads.get((a + da, b + db))
                if nb is not None:
                    # A piece join stays open (no cap): the pieces are drawn at different heights
                    # along the camera rays (D6, D181) and a cap showed as a band under every join.
                    continue
                k0, k1 = ks[e], ks[(e + 1) % 4]
                # the low wall on the silhouette (own verts, flat), a little darker than the top
                f = bm.faces.new([V(k1, 0.0, 2), V(k0, 0.0, 2), V(k0, None, 2), V(k1, None, 2)])
                ts = [tv[k1] - 0.8, tv[k0] - 0.8, tv[k0] - 0.5, tv[k1] - 0.5]
                paint(f, ts, min(TONE_MAX_PAL, max(slab_base.get(sl, 22), int(math.ceil(max(ts) - 0.15)))))
        ml = [None] * len(slots)
        for p, i in slots.items():
            ml[i] = mats(p)
        name = f"shapes)-{LEG_NAMES[ow[4:]]}" if ow.startswith("leg-") else ow
        o = to_obj(name, bm, ml, coll)
        set_normals(o, normals)
        o.location = (bx(cx), by(cy), 0)
        objs[ow] = o
    return whole_obj, objs


def pos_key(co):
    return (round(co[0], 4), round(co[1], 4), round(co[2], 4))


def set_normals(o, normals):
    """Custom split normals: the rock's shared vertex normals on its smooth top faces (so two
    pieces meeting along a cut shade as one surface), the face's own on the flat walls."""
    from mathutils import kdtree
    me = o.data
    keys = list(normals)
    tree = kdtree.KDTree(len(keys))
    for i, k in enumerate(keys):
        tree.insert(k, i)
    tree.balance()
    out = []
    miss = 0
    for p in me.polygons:
        for li in p.loop_indices:
            if p.use_smooth:
                co, i, d = tree.find(me.vertices[me.loops[li].vertex_index].co)
                if i is None or d > 2e-4:
                    miss += 1
                    n = tuple(p.normal)
                else:
                    n = normals[keys[i]]
            else:
                n = tuple(p.normal)
            out.append(n)
    me.normals_split_custom_set(out)
    if miss:
        print(f"set_normals {o.name}: {miss} loops without a shared normal")


def to_obj(name, bm, mats, coll):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    under = [f for f in bm.faces if f.normal.z < -0.99 and not f.smooth]
    if under:
        bmesh.ops.dissolve_faces(bm, faces=under)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def split_shell(shell, objs, F):
    """Each outline face goes to the piece that owns the px under its centre (open cuts, no caps)."""
    out = {}
    own, xs, ys = F["own"], F["xs"], F["ys"]
    me = shell.data
    mw = shell.matrix_world
    face_owner = []
    for p in me.polygons:
        c = mw @ p.center
        col = c.x / U + CENTRE[0]
        row = CENTRE[1] - c.y / U
        j = int(np.clip((col - X0) * K, 0, own.shape[1] - 1))
        i = int(np.clip(row * K, 0, own.shape[0] - 1))
        face_owner.append(own[i, j])
    # only the band along the silhouette inks (OutlineEffect draws the shell's back faces, depth
    # tested): the rest of the shell lies under the rock, where only an open join would show it
    d_edge = np.minimum(F["d_out"], F["d_in"])
    face_far = []
    for p in me.polygons:
        c = mw @ p.center
        j = int(np.clip((c.x / U + CENTRE[0] - X0) * K, 0, d_edge.shape[1] - 1))
        i = int(np.clip((CENTRE[1] - c.y / U) * K, 0, d_edge.shape[0] - 1))
        face_far.append(d_edge[i, j] > SHELL_KEEP)
    # and none near a join where this piece is drawn in front of the next one (a higher pass): the
    # join is open (make_objects), and through it the shell's underside showed as an ink blot
    passes = np.vectorize(pass_of)(own)
    lower = np.zeros(own.shape, bool)
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nb_p = shift(passes, dr, dc, 99)
        nb_o = shift(own, dr, dc, "")
        lower |= (nb_o != "") & (nb_o != own) & (nb_p < passes)
    for ow, o in objs.items():
        near = np.zeros(len(me.polygons), bool)
        jm = lower & (own == ow)
        if jm.any():
            dj = edt(jm)[0] / K
            for p in me.polygons:
                c = mw @ p.center
                j = int(np.clip((c.x / U + CENTRE[0] - X0) * K, 0, own.shape[1] - 1))
                i = int(np.clip((CENTRE[1] - c.y / U) * K, 0, own.shape[0] - 1))
                near[p.index] = dj[i, j] < JOIN_CLEAR
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        gone = [f for f in bm.faces if face_owner[f.index] != ow or face_far[f.index] or near[f.index]]
        bmesh.ops.delete(bm, geom=gone, context="FACES")
        bmesh.ops.transform(bm, matrix=mw, verts=bm.verts)
        # and nothing past its own box: the shell's flat bottom decimates into big triangles that
        # reach past the piece, and a crown piece is drawn lifted over the legs (D6), so their back
        # faces drew as black wedges on the leg tiles
        # A crown piece's bottom over the legs stops just short of the join: the crown is drawn
        # lifted far above the leg tiles (D6), so a shell edge past it drew as an ink line across
        # the rock there
        c0, r0, c1, r1 = piece_box(ow)
        m = 0.6
        mb = LEG_CUT_INSET if (SCENE == "arch" and not ow.startswith("leg-") and r1 == TILE_TOP + 1) else m
        for co, no in (((bx(c0 - m), 0, 0), (-1, 0, 0)), ((bx(c1 + m), 0, 0), (1, 0, 0)),
                       ((0, by(r0 - m), 0), (0, 1, 0)), ((0, by(r1 + mb), 0), (0, -1, 0))):
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_outer=True)
        bmesh.ops.translate(bm, vec=-o.location, verts=bm.verts)
        m2 = bpy.data.meshes.new(o.name + "_outline")
        bm.to_mesh(m2)
        bm.free()
        for mt in me.materials:
            m2.materials.append(mt)
        sh = bpy.data.objects.new(o.name + "_outline", m2)
        shell.users_collection[0].objects.link(sh)
        sh.location = o.location
        sh["tyrian_outline"] = True
        sh.data.shade_smooth()
        out[ow] = sh
    return out


def export_glb(objects, path, image_format="AUTO"):
    """common.export_glb plus the rock's tone attribute as COLOR_0 (export_vertex_color NAME: only
    meshes carrying TONE_ATTR get it; the outline shells and every other model get none). Copied
    from assembly-newshd-245's lens tint export; candidate for common.py."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.view_layer.update()
    for obj in bpy.context.view_layer.objects:
        if obj is not None:
            obj.select_set(False)
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_apply=True,
        export_cameras=False, export_lights=False, export_extras=True, export_image_format=image_format,
        export_image_quality=85, export_vertex_color="NAME", export_vertex_color_name=TONE_ATTR,
        export_all_vertex_colors=False, export_active_vertex_color_when_no_material=False,
    )
    return path


common.export_glb = export_glb   # (export_sprite_model and lib_tiles.export_tile_model call it)


TILE_MODELS = {"leg-left": "arch-leg-left", "leg-right": "arch-leg-right"}
# the passes the pieces are drawn in (draw list, SURFACE t1800): the leg tiles on the ground, 281/282
# with the ground enemies (282 lifted over 281 where they overlap, D181), the rest in TopEnemiesOver
PASSES = {"leg-left": 0, "leg-right": 0, "newsh3-281": 3, "newsh3-282": 4}


def pass_of(owner):
    return PASSES.get(owner, 13) if owner else 99


def model_name(owner):
    return TILE_MODELS.get(owner, owner)


def build(scene="arch"):
    """Build the whole rock; {model name: (piece object, outline object)} with each object's origin
    at its piece's centre (a sprite's centre, or a leg tile pattern's centre) and location 0."""
    ref = None
    if scene != "arch":   # the arch's tone down its column 72, which the stretch's ends take
        use("arch")
        Fa = heights()
        sel = Fa["Mf"] & (np.abs(Fa["XX"] - SEAM_COL) < 3)
        Tpre = Fa["TPRE"]
        ref = np.array([np.median(Tpre[i][sel[i]]) if sel[i].any() else np.nan for i in range(sel.shape[0])])
    use(scene)
    coll_name = f"{scene}_rock"
    F = heights(ref)
    print("slabs", {s: (v["pal"], v["area"], v["c"]) for s, v in F["info"].items()}, "spine", F["spine_pal"])
    coll = common.reset_collection(coll_name)
    sprite = {"name": "newsh3-200", "colors": F["colors"]}
    cache = {}

    def mats(p):
        if p not in cache:
            cache[p] = common.palette_material(sprite, int(p), "nsh3_198" if scene == "arch" else "nsh3_166",
                                               metallic=0.0, roughness=ROUGH)
            # single-sided (glTF doubleSided false): through a piece's open join the camera sees
            # the next piece, not this one's inside (make_objects)
            cache[p].use_backface_culling = True
        return cache[p]
    whole, objs = make_objects(F, coll, mats)
    # (finer voxels, more faces, more smoothing than before: the silhouette the ink follows is one
    # smooth line; the band split_shell keeps is a fraction of it)
    shell = common.outline_shell(whole, coll, voxel=0.022, faces=int(26000 * W * H / (168 * 112)), smooth=12,
                                 inside=0.004, islands="outer")
    if OPEN_ENDS:
        trim_ends(shell)
    shells = split_shell(shell, objs, F)
    whole.hide_render = shell.hide_render = True
    out = {}
    for ow, o in objs.items():
        sh = shells[ow]
        o.location = sh.location = (0, 0, 0)
        if not sh.data.polygons:
            raise RuntimeError(f"{ow}: empty outline")
        t = sum(len(p.vertices) - 2 for p in o.data.polygons)
        print(f"piece {model_name(ow)}: {t} tris, outline {len(sh.data.polygons)} faces, "
              f"mats {[m.name for m in o.data.materials]}")
        if not ow.startswith("leg-"):
            # The pieces are drawn far above the ground (their passes, D5) while the legs are layer-0
            # tiles; their shadow-map shadows fell as dark bands across the legs under the join and
            # across each other (D199). Like D66's island rock: no shadow from the crown (the legs,
            # at the ground's own height, still cast theirs).
            o["tyrian_ground"] = True
        out[model_name(ow)] = (o, sh)
    return out, F


def trim_ends(shell, reach=2.5 * U, facing=0.35):
    """Take the outline shell's faces off the open ends (the rock carries on in the next stretch or
    the arch: an inked cap would draw a line across the rock there)."""
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    bm.normal_update()
    mw = shell.matrix_world
    gone = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        for e, sign in ((OPEN_ENDS[0], -1), (OPEN_ENDS[1], 1)):
            if abs(c.x - bx(e)) < reach and f.normal.x * sign > facing:
                gone.append(f)
                break
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.to_mesh(shell.data)
    bm.free()
    print(f"trim_ends {shell.name}: {len(gone)} faces off the open ends")


def place(models):
    """Review layout: every model at its piece centre in the arch frame (units, sheet centre (60, 28))."""
    inv = {v: k for k, v in TILE_MODELS.items()}
    for name, objs in models.items():
        cx, cy = piece_centre(inv.get(name, name))
        for o in objs:
            o.location = (bx(cx), by(cy), 0)


def unplace(models):
    for objs in models.values():
        for o in objs:
            o.location = (0, 0, 0)


# ---- review renders -----------------------------------------------------------------------------

def renders(d, objs):
    d.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    # (review only) the tone attribute on the palette colour, as three.js applies COLOR_0
    done = set()
    for o in objs:
        for mt in o.data.materials:
            if mt is None or mt.name in done or not mt.use_nodes:
                continue
            done.add(mt.name)
            nt = mt.node_tree
            bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf is None or bsdf.inputs["Base Color"].is_linked:
                continue
            attr = nt.nodes.new("ShaderNodeVertexColor")
            attr.layer_name = TONE_ATTR
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            mix.inputs[6].default_value = bsdf.inputs["Base Color"].default_value
            nt.links.new(attr.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in objs:
            o.hide_render = True
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bgn = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bgn.inputs[0].default_value = (0.35, 0.33, 0.30, 1)
    bgn.inputs[1].default_value = 0.45
    sc.world = world
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 3.2
    sun.data.angle = 0.05
    sc.collection.objects.link(sun)
    # game sun (src/render/sun.ts {-6, 20, 8.4} three Y-up -> Blender (-6, -8.4, 20))
    sun.rotation_euler = (Vector((-6, -8.4, 20)).to_track_quat("Z", "Y")).to_euler()
    # ground (sand)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0.0, -2.33, -0.002))
    gp = bpy.context.active_object
    gm = bpy.data.materials.new("sand")
    gm.use_nodes = True
    pb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    pb.inputs["Base Color"].default_value = (0.42, 0.30, 0.17, 1)
    pb.inputs["Roughness"].default_value = 1
    gp.data.materials.append(gm)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cx, cy = bx(X0 + W / 2), by(H / 2)   # centre of the whole rock

    def shot(name, loc, look, ortho=None, res=(1200, 800), ground=True, lens=50):
        gp.hide_render = not ground
        cam.location = loc
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        if ortho:
            cam.data.type = "ORTHO"
            cam.data.ortho_scale = ortho
        else:
            cam.data.type = "PERSP"
            cam.data.lens = lens
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = str(d / f"{name}.png")
        bpy.ops.render.render(write_still=True)
    shot("top", (cx, cy, 30), (cx, cy, 0), ortho=W * U, res=(W * 8, H * 8))
    shot("game", (cx, cy - 26 * math.sin(math.radians(32)), 26 * math.cos(math.radians(32))), (cx, cy, 0), lens=55)
    shot("side", (cx - 30, cy, 0.6), (cx, cy, 0.6), ortho=10.5, res=(1200, 300), ground=False)
    shot("front", (cx, cy - 30, 0.6), (cx, cy, 0.6), ortho=14.5, res=(1400, 300), ground=False)
    shot("rear", (cx, cy + 30, 0.6), (cx, cy, 0.6), ortho=14.5, res=(1400, 300), ground=False)
    shot("q34_fl", (cx - 9, cy - 11, 9), (cx, cy, 0.4), lens=40)
    shot("q34_rr", (cx + 9, cy + 11, 9), (cx, cy, 0.4), lens=40)
    shot("under", (cx, cy, -30), (cx, cy, 0), ortho=15, res=(1000, 700), ground=False)
    # silhouette mask for IoU: workbench flat white on black, 4 px per sprite px
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "FLAT"
    sc.display.shading.color_type = "SINGLE"
    sc.display.shading.single_color = (1, 1, 1)
    sc.display.shading.background_type = "VIEWPORT"
    sc.display.shading.background_color = (0, 0, 0)
    sc.view_settings.view_transform = "Standard"
    gp.hide_render = True
    shot("mask", (cx, cy, 30), (cx, cy, 0), ortho=W * U, res=(W * 4, H * 4), ground=False)


if __name__ == "__main__":
    main()
