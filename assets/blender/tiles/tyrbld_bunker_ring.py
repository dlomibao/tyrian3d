"""TYRIAN's bunker ring (map 1-9, layer 0; tiles 320 321 / 330 331, 2x2, six copies on the dirt) as a
hard-surface model. It is what the enemy assembly-newsh2-115 ("brass dome works", a ground enemy on
all four cells) leaves standing once it is destroyed: a dark shield-shaped armoured emplacement on
the dirt, with at its top a riveted brass ring (a squarish superellipse, plated in twelve segments)
round a sunken pit holding a grille (four dim vertical bars and a bright L-bracket with its diagonal
brace), two squat brass half-domes on the shoulders each under a grey gun housing that points at the
camera (dark bore in front), a brass crescent (hook) low in the middle, grey armour blocks down both
flanks, a grey spine between the domes, two brass feed rods to the crescent, a dark cross pipe under
the ring and a dark foot plate at the bottom point.

Every shape is placed from the tiles' pixels (the sprite wins): the hull is the art's own outline
(no painted drop shadow), the ring's outer and inner edges are superellipses least-squares fitted to
the art's edge pixels, the crescent and the grey blocks are the art's own pixel regions, smoothed,
the domes and gun housings are the art's boxes. Colours: each region's own palette index (trimmed
median, measure()). Hard surface only: chamfered slabs, lofts with chamfered sections, lathed rods,
rivets; AO/roughness bake only (bake_model, no concept projection). No outline shell (tile models
draw no ink outline, D141). All tops <= 0.375 (every cell is an enemy cell: ENEMY_MAX 0.38). Stands
on z = 0 (the tiles stay drawn, keepTiles; no dirt pad, D86/D103). Export removes the old per-tile
model shapesz-bunker-ring.

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_bunker_ring.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bunker_ring.py -- [--no-bake] [--preview <dir>]
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402


# --- Layout (pattern px at 1x, 48 x 56, y down), read off the tiles ---------------------------------
# The art's outline of the bunker, row by row (inclusive columns). The dark pixels right of the ring
# (rows 4-10, cols 32-37) and beyond col 37/38 lower down are the painted drop shadow on the dirt,
# not the bunker; row 52's dark specks are dirt.
SPANS = {0: (13, 27), 1: (10, 28), 2: (9, 29), 3: (8, 30), 4: (7, 31), 5: (6, 32), 6: (5, 33), 7: (5, 33),
         8: (4, 34), 9: (4, 34), 10: (4, 34), 11: (3, 35), 12: (2, 36)}
SPANS.update({r: (1, 37) for r in range(13, 30)})
SPANS.update({r: (0, 38) for r in range(30, 35)})
SPANS.update({r: (1, 37) for r in range(35, 40)})
SPANS.update({40: (6, 36), 41: (6, 34), 42: (6, 34), 43: (6, 33), 44: (6, 33), 45: (6, 34), 46: (9, 33), 47: (9, 33),
              48: (10, 32), 49: (11, 32), 50: (12, 32), 51: (13, 31)})
# Superellipses (cx, cy, rx, ry, n) fitted to the art's edge pixels (fit.py): the ring's outer edge
# and the pit's edge (the ring's inner edge).
OUTER = (19.53, 10.92, 15.44, 11.12, 2.13)
INNER = (18.55, 12.07, 10.62, 6.88, 3.86)
DOMES = [(6.5, 30.2), (32.0, 30.2)]
DOME_RX, DOME_RY = 5.4, 5.2
GUNS = [(5.0, 31.0, 10.0, 36.0), (29.0, 31.0, 34.0, 36.0)]  # grey gun housings (art boxes)
CRESCENT_BOX = (11, 35, 28, 46)  # rows/cols holding the crescent's brass pixels
CRES_OUT = (19.5, 40.5, 7.5, 4.8, 2.0)  # the crescent's outer edge
CRES_IN = (16.8, 42.0, 3.2, 2.4, 2.0)  # its hollow
CRES_GAP = (100.0, 165.0)  # screen degrees (0 right, 90 down) left open: the hook opens to the lower left
BARS = [18.5, 21.5, 23.5, 25.5]  # the grille's dim vertical bars (pixel columns + 0.5)

# --- Heights (layer 0: z = 0 the ground; enemy cells top <= 0.38) ------------------------------------
BOTTOM = -0.04
HULL_TOP = 0.06  # the hull's base and the pit floor
BODY_TOP = 0.15  # the armour shield
RING_TOP = 0.36
DOME_Z, DOME_TOP = 0.10, 0.365
GUN_BACK, GUN_FRONT = 0.372, 0.33
CRESCENT_TOP = 0.33
BLOCK_TOP = 0.22
PLATE_TOP = 0.165

# Panel seams across the shield (pattern px segments) and the grey blocks / spine read off the art's
# grey pixel groups (polygons in pattern px; tops), and its raised dark (index 1) plates.
SEAMS = [((0, 25.8), (40, 25.8)), ((0, 37.4), (40, 37.4)), ((13.6, 25.8), (13.6, 37.4)), ((25.8, 25.8), (25.8, 37.4)),
         ((19.5, 44.5), (19.5, 53)), ((6.0, 41.0), (12.5, 47.5)), ((33.5, 41.0), (27.0, 47.5)), ((0, 19.6), (8, 19.6)),
         ((31, 19.6), (40, 19.6))]
GREY_BLOCKS = [
    ("left flank", [(1.8, 12.4), (3.6, 11.8), (5.0, 14.6), (7.2, 17.4), (7.2, 19.2), (4.0, 19.2), (1.8, 17.2)], BLOCK_TOP),
    ("left flank low", [(3.6, 19.9), (7.2, 19.9), (7.2, 21.8), (5.4, 22.4), (5.2, 25.8), (1.8, 25.8), (1.8, 22.4), (3.6, 22.0)], BLOCK_TOP),
    ("right flank low", [(32.8, 20.4), (36.4, 20.0), (37.2, 21.0), (37.2, 25.8), (34.0, 25.8), (32.8, 23.0)], BLOCK_TOP),
    ("left strut", [(9.0, 22.6), (11.8, 21.8), (14.0, 24.0), (14.0, 25.2), (10.0, 25.2), (9.0, 24.2)], BLOCK_TOP - 0.02),
    ("left foot", [(6.8, 39.8), (11.2, 39.8), (11.2, 42.6), (12.2, 43.4), (12.2, 45.0), (9.8, 45.0), (6.8, 43.0)], BLOCK_TOP),
    ("right foot", [(27.8, 40.4), (32.2, 40.4), (32.2, 43.0), (27.8, 43.0)], BLOCK_TOP),
    ("spine box", [(20.0, 32.8), (23.2, 32.8), (23.2, 36.2), (20.0, 36.2)], BLOCK_TOP + 0.02),
]
SPINE = [((19.5, 24.6), (19.5, 30.4), 1.0), ((21.5, 25.6), (21.5, 33.0), 1.0), ((16.8, 31.8), (19.2, 29.6), 0.9)]
DARK_PLATES = [(7.0, 36.6, 12.2, 38.9), (27.8, 36.6, 35.2, 38.9), (9.6, 45.6, 13.0, 47.2), (16.6, 46.6, 20.0, 48.0)]
TOP = 0.375

SC = 4  # supersampling of the pixel masks before tracing (smooth outlines)


# --- Masks and outlines --------------------------------------------------------------------------------

def art_mask(H, W):
    m = np.zeros((H, W), bool)
    for r, (a, b) in SPANS.items():
        m[r, a:b + 1] = True
    return m


def hi_grid(H, W):
    yy, xx = np.mgrid[0:H * SC, 0:W * SC]
    return (xx + 0.5) / SC, (yy + 0.5) / SC


def superellipse(H, W, se, grow=0.0):
    cx, cy, rx, ry, n = se
    xx, yy = hi_grid(H, W)
    return (np.abs(xx - cx) / (rx + grow)) ** n + (np.abs(yy - cy) / (ry + grow)) ** n <= 1.0


def se_point(se, a, grow=0.0):
    """A point on the superellipse at parameter angle a (screen: 0 right, pi/2 down)."""
    cx, cy, rx, ry, n = se
    c, s = math.cos(a), math.sin(a)
    return (cx + (rx + grow) * math.copysign(abs(c) ** (2 / n), c), cy + (ry + grow) * math.copysign(abs(s) ** (2 / n), s))


def up(mask1x):
    return np.kron(mask1x, np.ones((SC, SC), bool))


def blur_hi(mask_hi, sigma_px):
    """Gaussian-smoothed, re-thresholded hi-res mask: rounds the art's pixel staircases."""
    if sigma_px <= 0:
        return mask_hi
    from math import ceil
    s = sigma_px * SC
    k = int(ceil(3 * s))
    x = np.arange(-k, k + 1)
    g = np.exp(-0.5 * (x / s) ** 2)
    g /= g.sum()
    f = mask_hi.astype(np.float32)
    f = np.apply_along_axis(lambda r: np.convolve(r, g, mode="same"), 1, f)
    f = np.apply_along_axis(lambda r: np.convolve(r, g, mode="same"), 0, f)
    return f >= 0.5


def polys(mask_hi, tol=0.3, min_px=2.0):
    """Outer outlines (pattern px) of each part of a hi-res mask, simplified."""
    out = []
    for ys, xs in lt.components(mask_hi):
        if len(ys) < min_px * SC * SC:
            continue
        part = np.zeros(mask_hi.shape, bool)
        part[ys, xs] = True
        loop = [(x / SC, y / SC) for x, y in ls.trace(part)]
        poly = ls.simplify(loop, tol)
        if len(poly) >= 3 and abs(ls.area(poly)) > 0.5:
            out.append(poly)
    return out


def shrink(m, r_px):
    """Erode a hi-res mask by r_px (box steps, cheap)."""
    k = int(round(r_px * SC))
    out = m.copy()
    for _ in range(k):
        out = out & np.roll(out, 1, 0) & np.roll(out, -1, 0) & np.roll(out, 1, 1) & np.roll(out, -1, 1)
    return out


def grow(m, r_px):
    k = int(round(r_px * SC))
    out = m.copy()
    for _ in range(k):
        out = out | np.roll(out, 1, 0) | np.roll(out, -1, 0) | np.roll(out, 1, 1) | np.roll(out, -1, 1)
    return out


# --- Colours -------------------------------------------------------------------------------------------

def measure(s, region, name, lo=0.2, hi=0.15):
    """The region's palette index: its pixels sorted by brightness, the darkest `lo` (shading,
    outline) and brightest `hi` (sheen) dropped, the median of the rest."""
    vals = [int(v) for v in s.grid[region & (s.grid >= 0)]]
    vals.sort(key=lambda v: s.ts.lum[v])
    n = len(vals)
    keep = vals[int(n * lo):max(int(n * lo) + 1, n - int(n * hi))]
    idx = keep[len(keep) // 2]
    print(f"colour {name}: index {idx} ({n} px)")
    MEASURED[name] = (idx, n)
    return idx


MEASURED = {}


# --- Geometry helpers ------------------------------------------------------------------------------------

def band_loft(s, outer, inner, profile, mats, a0, a1, segs, cap=True):
    """A band between two superellipses from parameter angle a0 to a1: each station's cross-section
    runs from the outer edge (t 0) to the inner (t 1) through `profile` [(t, z), ...] (a closed
    loop, bottom included); `mats` one per profile edge. Closed ends."""
    bm = bmesh.new()
    rings = []
    for k in range(segs + 1):
        a = a0 + (a1 - a0) * k / segs
        po, pi = se_point(outer, a), se_point(inner, a)
        rings.append([bm.verts.new((s.x(po[0] + (pi[0] - po[0]) * t), s.y(po[1] + (pi[1] - po[1]) * t), z)) for t, z in profile])
    n = len(profile)
    for ra, rb in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((ra[i], ra[j], rb[j], rb[i]))
            f.material_index = mats[i]
    if cap:
        bm.faces.new(rings[0]).material_index = mats[0]
        bm.faces.new(list(reversed(rings[-1]))).material_index = mats[0]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = len(f.verts) == 4 and abs(f.normal.z) < 0.98
    s._merge(bm)


def rod(s, p0, p1, r_px, z, mat, sides=8, cap=True):
    """A round rod (cylinder) between two pixel points at height z (its axis)."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    ln = math.hypot(dx, dy)
    ux, uy = dx / ln, dy / ln
    nx, ny = -uy, ux  # side direction (pattern px)
    bm = bmesh.new()
    rings = []
    for px, py in ((x0, y0), (x1, y1)):
        ring = []
        for i in range(sides):
            a = 2 * math.pi * (i + 0.5) / sides
            off, w = math.cos(a) * r_px, math.sin(a) * r_px
            ring.append(bm.verts.new((s.x(px + nx * off), s.y(py + ny * off), z + w * lt.PX)))
        rings.append(ring)
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i])).material_index = mat
    if cap:
        bm.faces.new(rings[0]).material_index = mat
        bm.faces.new(list(reversed(rings[1]))).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm, smooth=True)


def strap(s, p0, p1, w_px, z0, z1, mat, chamfer=0.25):
    """A flat bar from p0 to p1 (pattern px), w_px wide, chamfered top."""
    (x0, y0), (x1, y1) = p0, p1
    ln = math.hypot(x1 - x0, y1 - y0)
    ox, oy = -(y1 - y0) / ln * w_px / 2, (x1 - x0) / ln * w_px / 2
    poly = [(x0 + ox, y0 + oy), (x1 + ox, y1 + oy), (x1 - ox, y1 - oy), (x0 - ox, y0 - oy)]
    s.slab(poly, z0, z1, mat, chamfer_px=min(chamfer, w_px * 0.3), drop=0.012)


def rivets(s, pts, z, mat, r=0.42):
    for px, py in pts:
        bm = bmesh.new()
        lt.dome(bm, s.x(px), s.y(py), r * lt.PX, r * lt.PX, 0.0, z - 0.004, 0.022, mat, sides=8, rings=2)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm, smooth=True)


def dome_z(cx, cy, x, y):
    t = ((x - cx) / DOME_RX) ** 2 + ((y - cy) / DOME_RY) ** 2
    return DOME_Z + (DOME_TOP - DOME_Z) * math.sqrt(max(0.0, 1 - t))


# --- Build ---------------------------------------------------------------------------------------------

def build(bake=True, preview=None):
    lb.clear_scene()
    s = tb.Structure("bunker-ring")
    H, W = s.H, s.W
    mask = art_mask(H, W)
    g = s.grid
    greys = ((g >= 3) & (g <= 10)) | (g == 106) | (g == 169)
    brass_px = (g >= 19) & (g <= 31)

    # ---- regions for the colours
    outer_hi = superellipse(H, W, OUTER)
    inner_hi = superellipse(H, W, INNER)
    ring1 = (outer_hi & ~inner_hi).reshape(H, SC, W, SC).mean(axis=(1, 3)) > 0.5
    pit1 = inner_hi.reshape(H, SC, W, SC).mean(axis=(1, 3)) > 0.5
    cx0, cy0, cx1, cy1 = CRESCENT_BOX
    cres1 = np.zeros((H, W), bool)
    cres1[cy0:cy1, cx0:cx1] = brass_px[cy0:cy1, cx0:cx1]
    gun1 = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in GUNS:
        gun1[int(y0):int(y1), int(x0):int(x1)] = True
    dome1 = np.zeros((H, W), bool)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    for dx, dy in DOMES:
        dome1 |= (((xx - dx) / DOME_RX) ** 2 + ((yy - dy) / DOME_RY) ** 2 <= 1.0)
    dome1 &= ~gun1 & mask
    body1 = mask & ~ring1 & ~pit1 & ~dome1 & ~gun1 & ~cres1 & ~greys

    P_RING = measure(s, ring1 & mask & brass_px, "ring brass")
    P_DOME = measure(s, dome1 & brass_px, "dome brass")
    P_CRES = measure(s, cres1, "crescent brass")
    P_GUN = measure(s, gun1, "gun housing grey")
    P_BODY = measure(s, body1, "hull/body dark", lo=0.0, hi=0.3)
    P_PIT = measure(s, pit1 & ~brass_px & (g != 18) & (g != 17) & (g != 16), "pit floor", lo=0.0, hi=0.0)
    P_BARS = measure(s, pit1 & np.isin(np.arange(W)[None, :].repeat(H, 0), [18, 21, 23, 25]) & (g >= 16) & (g <= 20), "grille bars")
    bracket1 = np.zeros((H, W), bool)
    bracket1[5:16, 11:19] = True
    P_BRACKET = measure(s, bracket1 & pit1 & (g >= 19) & (g <= 29), "pit bracket brass")
    P_PLATE = 1  # the art's raised dark plates (index 1, 12 12 12) against the hull's 32
    P_ROD = measure(s, np.isin(np.arange(W)[None, :].repeat(H, 0), [23, 25]) & (np.arange(H)[:, None] >= 30) & (np.arange(H)[:, None] <= 33) & brass_px, "feed rods")

    m_hull = s.m(P_BODY, metallic=0.2, roughness=0.62)
    m_pit = s.m(P_PIT, metallic=0.2, roughness=0.75)
    m_plate = s.m(P_PLATE, metallic=0.3, roughness=0.55)
    m_ring = s.m(P_RING, metallic=0.75, roughness=0.38)
    m_ring_wall = s.m(max(16, P_RING - 3), metallic=0.7, roughness=0.42)
    m_dome = s.m(P_DOME, metallic=0.75, roughness=0.36)
    m_dome_strap = s.m(min(28, P_DOME + 2), metallic=0.75, roughness=0.34)
    m_cres = s.m(P_CRES, metallic=0.75, roughness=0.38)
    m_bars = s.m(P_BARS, metallic=0.6, roughness=0.45)
    m_bracket = s.m(P_BRACKET, metallic=0.7, roughness=0.38)
    m_gun = s.m(P_GUN, metallic=0.45, roughness=0.5)
    m_rod = s.m(P_ROD, metallic=0.7, roughness=0.4)
    m_rivet = s.m(min(28, P_RING + 2), metallic=0.75, roughness=0.32)

    mask_hi = up(mask)
    # ---- hull base: the art's outline, rounded; under the ring kept inside the ring's outer edge
    hull_hi = blur_hi(mask_hi, 0.9)
    top_rows = hi_grid(H, W)[1] < 14.0
    hull_hi &= ~(top_rows & ~superellipse(H, W, OUTER, grow=-0.6))
    for poly in polys(hull_hi):
        s.slab(poly, BOTTOM, HULL_TOP, m_hull, chamfer_px=0.8, drop=0.03)

    # ---- armour shield (body): below the ring, a sloped-edge slab, its top edge chamfered wide
    body_hi = shrink(hull_hi, 0.5) & ~superellipse(H, W, OUTER, grow=-1.2) & (hi_grid(H, W)[1] > 10.0)
    body_hi = blur_hi(body_hi, 0.6)
    for poly in polys(body_hi, min_px=6):
        s.slab(poly, 0.0, BODY_TOP - 0.01, m_hull, chamfer_px=2.0, drop=0.06)

    # ---- the ring: 12 riveted brass plates with hairline gaps, rounded top, walls to the pit
    prof = [(0.0, -0.02), (0.0, 0.25), (0.06, 0.32), (0.16, RING_TOP - 0.008), (0.3, RING_TOP),
            (0.7, RING_TOP), (0.84, RING_TOP - 0.008), (0.94, 0.32), (1.0, 0.25), (1.0, HULL_TOP - 0.01)]
    pm = [m_ring_wall, m_ring_wall, m_ring, m_ring, m_ring, m_ring, m_ring, m_ring_wall, m_ring_wall, m_ring_wall]
    nseg = 12
    gap = math.radians(0.9)
    base = -math.pi / 2 + math.pi / nseg  # seams off the axes (the superellipse's parameter stretches there)
    for k in range(nseg):
        a0 = base + 2 * math.pi * k / nseg + gap
        a1 = base + 2 * math.pi * (k + 1) / nseg - gap
        band_loft(s, OUTER, INNER, prof, pm, a0, a1, 10)
        # rivets either side of each seam, on the band's crown
        for a in (a0 + math.radians(4.5), a1 - math.radians(4.5)):
            po, pi = se_point(OUTER, a), se_point(INNER, a)
            pts = [(po[0] + (pi[0] - po[0]) * t, po[1] + (pi[1] - po[1]) * t) for t in (0.35, 0.65)]
            rivets(s, pts, RING_TOP, m_rivet, r=0.36)
    # a dark sub-ring under the plates (fills the seams, the plates' bed)
    band_loft(s, OUTER, INNER, [(0.03, -0.02), (0.03, 0.30), (0.97, 0.30), (0.97, -0.02)],
              [m_ring_wall] * 4, -math.pi / 2, 1.5 * math.pi, 96)

    # ---- the pit's grille: dim vertical bars, the bright L-bracket and its diagonal brace, a low
    # cross pipe
    cxi, cyi, rxi, ryi, ni = INNER
    for bx in BARS:
        t = abs(bx - cxi) / rxi
        h = ryi * (max(0.0, 1 - t ** ni)) ** (1 / ni)
        strap(s, (bx, cyi - h + 0.2), (bx, cyi + h - 0.2), 0.9, HULL_TOP - 0.01, 0.24, m_bars, chamfer=0.2)
    strap(s, (15.5, cyi - ryi + 0.4), (15.5, 11.9), 1.0, HULL_TOP - 0.01, 0.29, m_bracket)
    strap(s, (12.0, 11.5), (16.0, 11.5), 1.0, HULL_TOP - 0.01, 0.30, m_bracket)
    strap(s, (12.5, 11.0), (12.5, 15.8), 1.1, HULL_TOP - 0.01, 0.29, m_bracket)
    strap(s, (13.0, 12.0), (18.3, 16.2), 0.9, HULL_TOP - 0.01, 0.275, m_bracket)
    rod(s, (cxi - rxi + 0.3, 16.6), (cxi + rxi - 0.3, 16.6), 0.55, HULL_TOP + 0.05, m_bars, sides=8)
    rivets(s, [(12.5, 11.5), (15.5, 11.5)], 0.30, m_rivet, r=0.35)

    # ---- dark armour plates under the ring and the cross pipe (art rows 22-24)
    for x0, y0, x1, y1 in ((12.5, 21.6, 17.0, 25.2), (21.5, 21.6, 30.0, 25.2)):
        s.slab(s.rounded_box(x0, y0, x1, y1, 0.6, 1), BODY_TOP - 0.02, BODY_TOP + 0.045, m_plate, chamfer_px=0.5, drop=0.02)
    rod(s, (12.0, 23.5), (29.0, 23.5), 0.55, BODY_TOP + 0.03, m_bars, sides=8)

    # ---- armour plates on the shield: the body's top split by panel seams (0.3 px grooves)
    xx_hi, yy_hi = hi_grid(H, W)
    seam = np.zeros_like(body_hi)
    for (x0, y0), (x1, y1) in SEAMS:
        dx, dy = x1 - x0, y1 - y0
        ln2 = dx * dx + dy * dy
        t = np.clip(((xx_hi - x0) * dx + (yy_hi - y0) * dy) / ln2, 0, 1)
        dist = np.hypot(xx_hi - (x0 + t * dx), yy_hi - (y0 + t * dy))
        seam |= dist < 0.18
    plates_hi = shrink(body_hi, 1.9) & ~seam
    for poly in polys(plates_hi, tol=0.3, min_px=3):
        s.slab(poly, BODY_TOP - 0.05, PLATE_TOP, m_hull, chamfer_px=0.35, drop=0.015)

    # ---- grey blocks, placed on the art's grey pixel groups (index per block from its pixels)
    for name, poly, z1 in GREY_BLOCKS:
        reg = polys_mask(poly, H, W)
        idx = measure(s, reg & greys, f"grey {name}", lo=0.15, hi=0.15) if (reg & greys).any() else 4
        s.slab(poly, 0.02, z1, s.m(idx, metallic=0.55, roughness=0.42), chamfer_px=0.4, drop=0.025)
    m_grey = s.m(4, metallic=0.55, roughness=0.42)
    for p0, p1, w in SPINE:
        strap(s, p0, p1, w, BODY_TOP - 0.02, 0.235, m_grey, chamfer=0.25)
    # dark plates under the gun fronts and either side of the foot (the art's index-1 groups)
    for x0, y0, x1, y1 in DARK_PLATES:
        s.slab(s.rounded_box(x0, y0, x1, y1, 0.5, 1), BODY_TOP - 0.03, PLATE_TOP + 0.03, m_plate, chamfer_px=0.35, drop=0.015)

    # ---- domes: dark plinth, squat brass half-dome, seam strap, rivets round the foot
    for dx, dy in DOMES:
        s.lathe([(0.0, DOME_RX + 0.5), ((DOME_Z + 0.04) / lt.PX, DOME_RX + 0.5), ((DOME_Z + 0.04) / lt.PX, 0.0)], dx, dy,
                axis="z", z=0.0, mat=m_plate, sides=32, smooth=False)
        bm = bmesh.new()
        lt.dome(bm, s.x(dx), s.y(dy), DOME_RX * lt.PX, DOME_RY * lt.PX, 0.0, DOME_Z, DOME_TOP - DOME_Z, m_dome, sides=40, rings=10)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        s._merge(bm, smooth=True)
        # seam strap over the crown, back to the gun housing
        prof = []
        n = 12
        for i in range(n + 1):
            py = dy - DOME_RY * 0.97 + (DOME_RY * 0.97 + 1.2) * i / n
            prof.append((py, dome_z(dx, dy, dx, py) + 0.012))
        under = [(py, z - 0.05) for py, z in reversed(prof)]
        s.prism(prof + under, dx - 0.5, dx + 0.5, mat=m_dome_strap)
        rv = []
        for i in range(10):
            a = math.pi * (1.05 + 0.9 * i / 9)  # the back half (the front is under the gun housing)
            rv.append((dx + (DOME_RX - 0.55) * math.cos(a), dy + (DOME_RY - 0.55) * math.sin(a)))
        for px, py in rv:
            rivets(s, [(px, py)], dome_z(dx, dy, px, py) - 0.006, m_rivet, r=0.32)

    # ---- gun housings: grey wedge blocks over the domes' fronts, a dark bore in each front face
    for x0, y0, x1, y1 in GUNS:
        prof = [(y0, 0.03), (y0, GUN_BACK - 0.02), (y0 + 0.4, GUN_BACK), (y1 - 0.6, GUN_FRONT), (y1, GUN_FRONT - 0.04), (y1, 0.03)]
        s.prism(prof, x0, x1, mat=m_gun)
        # the muzzle: a raised lip and a dark recessed bore on the front face
        s.prism([(y1 - 0.01, 0.10), (y1 - 0.01, 0.27), (y1 + 0.25, 0.27), (y1 + 0.25, 0.10)], x0 + 0.6, x1 - 0.6, mat=m_gun)
        s.prism([(y1 + 0.2, 0.13), (y1 + 0.2, 0.24), (y1 + 0.3, 0.24), (y1 + 0.3, 0.13)], x0 + 1.2, x1 - 1.2, mat=m_pit)
        # cheek rails along the top edges
        for xr in (x0 + 0.45, x1 - 0.45):
            strap(s, (xr, y0 + 0.5), (xr, y1 - 0.6), 0.5, GUN_FRONT - 0.04, GUN_FRONT + 0.012, m_gun, chamfer=0.1)

    # ---- the crescent: the art's brass hook, smoothed, a chamfered brass slab with rivets
    # a rounded brass band along an elliptic arc (outer and hollow ellipses fitted to the art's
    # hook), open at the lower left as the art; square-cut ends
    cprof = [(0.0, 0.02), (0.0, 0.25), (0.1, 0.30), (0.28, CRESCENT_TOP), (0.72, CRESCENT_TOP), (0.9, 0.30),
             (1.0, 0.25), (1.0, 0.02)]
    cm = [m_ring_wall, m_cres, m_cres, m_cres, m_cres, m_cres, m_ring_wall, m_ring_wall]
    band_loft(s, CRES_OUT, CRES_IN, cprof, cm, math.radians(CRES_GAP[1]), math.radians(CRES_GAP[0] + 360), 40)
    def on_cres(deg, f):
        po, pi = se_point(CRES_OUT, math.radians(deg)), se_point(CRES_IN, math.radians(deg))
        return (po[0] + (pi[0] - po[0]) * f, po[1] + (pi[1] - po[1]) * f)
    rivets(s, [on_cres(d, 0.5) for d in (-165, -120, -75, -35, 75)], CRESCENT_TOP, m_rivet, r=0.36)

    # ---- feed rods: from the spine down to the crescent, and on below it to the foot plate
    for x in (23.5, 25.5):
        rod(s, (x, 28.8), (x, 36.8), 0.45, BODY_TOP + 0.04, m_rod, sides=8)
    for x in (22.5, 24.5):
        rod(s, (x, 44.0), (x, 48.8), 0.45, BODY_TOP + 0.02, m_plate, sides=8)
    # ---- foot plate (art rows 49-50, index 1) with two cross ribs
    s.slab(s.rounded_box(15.5, 48.6, 26.5, 51.2, 0.6, 1), BODY_TOP - 0.03, BODY_TOP + 0.04, m_plate, chamfer_px=0.5, drop=0.02)
    for y in (49.4, 50.5):
        strap(s, (16.2, y), (25.8, y), 0.35, BODY_TOP + 0.035, BODY_TOP + 0.055, m_plate, chamfer=0.08)
    # ---- the right flank's pipe (art col 36, rows 13-18, grey 3)
    rod(s, (36.5, 12.6), (36.5, 19.4), 0.55, BODY_TOP - 0.02, s.m(3, metallic=0.6, roughness=0.45), sides=8)

    objects = s.objects()
    return s.finish(objects, mask, bake=bake, preview=preview)


def polys_mask(poly, H, W):
    """A 1x pixel mask of a polygon (pixel centres inside)."""
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    inside = np.zeros((H, W), bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cond = (y0 > yy) != (y1 > yy)
        xc = x0 + (yy - y0) * (x1 - x0) / (y1 - y0 + 1e-9)
        inside ^= cond & (xx < xc)
    return inside


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
