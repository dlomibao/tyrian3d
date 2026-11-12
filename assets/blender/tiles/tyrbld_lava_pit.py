"""The lava pit on TYRIAN's islands (map 1-9, layer 2; tile 143, one tile): a round pit sunk into the
island's grey rock, the emplacement of the star-core turret (newsh2 153/155/157) that sits on every
copy, so it shows only after that enemy dies. Hard-surface standard (D65/D141).

What the tile paints (1x px, the tile is 24x28): a dark hollow over px 3-19, rows 7-19 (black edge,
a dark brown ring of lava-lit wall, a red pool of 113-117 with dark 64-66 crust patches), a bright
lip sheen along its far (upper) edge, and three tan stones lit pink by the glow: left (px 1-4,
rows 8-15), right (px 18-22, rows 10-16) and one below the mouth (px 8-13, rows 19-25). The rest is
the island's rock (its tan pebbles included), which the per-tile rock draws.

Built from the tile's own pixels:
- every outline (mouth, pool, lip) is the art's hollow traced as a radial profile and low-passed
  (Fourier, <= 6 harmonics), so it is round where the art is round and follows its bulges;
- the lip: 13 dressed stone blocks, chamfered on every edge (V joints), mitred round the mouth; the
  inner edge is the hollow's traced outline, the outer edge the hollow grown 2 px (disc), traced;
- the walls: chamfered ledges stepping down from the mouth to the pool, all black (index 0, the art's
  1/80 edge) but a thin lava-lit foot (64, 112); the pool sits 0.27 down and POOL_INSET px inside the
  mouth, so the black ring reads from overhead and the tilted camera sees a deep black far wall;
- the pool: emissive lava (114) under Voronoi crust plates; each plate's kind comes from the art's
  pixels under it (64-66 and black: dark crust 64; 112/113: cooling crust 112, glowing; 114: open lava),
  each plate small (shrunk inside its cell, so lava shows round it), and a low swell on each of the
  art's 115-117 pixels in that pixel's own index (115 small, 116/117 bigger), so the embers are the
  sprite's. Every pool glow is strength ~1 (D126: the palette colour unlit), metallic and rough so it
  reflects nothing (review #17: a glossy pool read as a pink lid);
- the three stones: rough-cut stones over the convex hull of the art's tan components, leaning on
  the lip (highest toward the pit, faceted top: lit faces, not paint);
- the island's rock round it: Structure.rock (plain, unbaked), cut under the lip.
Everything under L2_ENEMY_MAX (0.33): the whole tile is an enemy cell. Underside: a plain closed
plug to the slab's bottom. Texture: the model's own AO/roughness bake only (no concept projection).

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/tyrbld_lava_pit.py
    blender --background --factory-startup --python assets/blender/tiles/tyrbld_lava_pit.py -- [--no-bake] [--preview <dir>]
"""

import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

N = 48  # vertices round every ring
HARM = 4  # Fourier harmonics kept in the traced outlines
LIP_W = 1.9  # px: the lip blocks' width outside the mouth
CUT_W = 0.7  # px: the rock's hole outside the mouth (hidden under the lip)
LIP_BLOCKS = 13
LIP_TOP = (0.075, 0.105)
LAVA_Z = -0.27  # deep enough that the black walls read from overhead and the tilted camera
CRUST_Z = 0.012
POOL_INSET = 1.9  # px: the black wall ring seen from overhead (the art's black edge, 1-4 px)
STONE_TOP = {"left": 0.16, "right": 0.14, "bottom": 0.13}

# Palette classes of the tile's pixels.
RED = set(range(112, 126))
CRUST = {64, 65, 66, 67, 161, 16, 17}
TAN = {24, 25, 27, 28, 77, 78, 79, 126, 163, 164, 165, 166, 167}


# --- Outline tracing (pattern px) --------------------------------------------------------------------

def radial_profile(mask, cx, cy, n=N, harm=HARM, step=0.05, rmax=14.0):
    """The outer edge of `mask` seen from (cx, cy): r(theta) at n angles, low-passed to `harm`
    harmonics. theta measured in screen terms (x right, y down)."""
    H, W = mask.shape
    th = 2 * np.pi * np.arange(n * 4) / (n * 4)
    rs = np.arange(0, rmax, step)
    r_out = np.zeros(len(th))
    for k, t in enumerate(th):
        xs, ys = cx + rs * np.cos(t), cy + rs * np.sin(t)
        ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
        inside = np.zeros(len(rs), bool)
        inside[ok] = mask[ys[ok].astype(int), xs[ok].astype(int)]
        idx = np.nonzero(inside)[0]
        r_out[k] = rs[idx.max()] + step if len(idx) else 0.0
    f = np.fft.rfft(r_out)
    f[harm + 1:] = 0
    r = np.fft.irfft(f, len(th))
    return r[::4]


def ring_pts(cx, cy, r, d=0.0):
    n = len(r)
    return [(cx + (r[i] + d) * math.cos(2 * math.pi * i / n), cy + (r[i] + d) * math.sin(2 * math.pi * i / n)) for i in range(n)]


def poly_mask(poly, W, H, ss=1):
    yy, xx = (np.mgrid[0:H * ss, 0:W * ss] + 0.5) / ss
    inside = np.zeros(xx.shape, bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cond = (y0 > yy) != (y1 > yy)
        xint = (x1 - x0) * (yy - y0) / ((y1 - y0) if y1 != y0 else 1e-9) + x0
        inside ^= cond & (xx < xint)
    if ss > 1:
        inside = inside.reshape(H, ss, W, ss).mean(axis=(1, 3)) >= 0.5
    return inside


# --- Masks from the art --------------------------------------------------------------------------

def label(mask):
    """4-connected components (lib_tiles.components) as a list of bool masks, biggest first."""
    out = []
    for ys, xs in lt.components(mask):
        m = np.zeros(mask.shape, bool)
        m[ys, xs] = True
        out.append(m)
    return sorted(out, key=lambda m: -m.sum())


def fill_holes(mask):
    H, W = mask.shape
    outside = np.zeros((H + 2, W + 2), bool)
    pad = np.zeros((H + 2, W + 2), bool)
    pad[1:-1, 1:-1] = mask
    outside[0, :] = outside[-1, :] = outside[:, 0] = outside[:, -1] = True
    outside &= ~pad
    while True:
        grown = outside | (lb.dilate(outside, 1) & ~pad)
        if (grown == outside).all():
            break
        outside = grown
    return ~outside[1:-1, 1:-1]


def masks(s):
    g = s.grid
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    red = np.isin(g, list(RED))
    crust = np.isin(g, list(CRUST))
    black = (g >= 0) & ((g <= 3) | (g == 80))
    tan = np.isin(g, list(TAN))
    near = ((xx - 11.5) / 8.5) ** 2 + ((yy - 13.3) / 6.8) ** 2 <= 1
    pit = lb.close((red | crust | black) & near, 1)
    pit = fill_holes(label(pit)[0])
    pool = fill_holes(label(lb.close((red | crust) & lb.erode(pit, 1), 1))[0])
    stones = {}
    zone = lb.dilate(pit, 3)
    for m in label(tan & ~pit):
        if m.sum() < 6 or not (m & zone).any():
            continue
        ys, xs = np.nonzero(m)
        if ys.mean() < 7 or ys.mean() > 26:
            continue
        key = "left" if xs.mean() < 6 else "right" if xs.mean() > 17 else "bottom"
        stones[key] = stones.get(key, np.zeros_like(m)) | m
    for k in stones:
        stones[k] = fill_holes(lb.close(stones[k], 1)) & ~pit
    return dict(red=red, crust=crust, black=black, tan=tan, pit=pit, pool=pool, stones=stones)


def tone(s, mask, lo=0.15, hi=0.15):
    """The region's palette index: the pixel at the median luminance after dropping the darkest
    `lo` and brightest `hi` (shading and highlights are lighting)."""
    v = s.grid[mask & (s.grid >= 0)]
    if not len(v):
        return None
    lum = s.ts.lum[v]
    o = np.argsort(lum, kind="stable")
    v = v[o]
    a, b = int(len(v) * lo), len(v) - int(len(v) * hi)
    core = v[a:b] if b - a >= 3 else v
    return int(core[len(core) // 2])


# --- Builders ------------------------------------------------------------------------------------

def loft_rings(bm, rings, mats, close_top=None, close_bottom=None):
    """Quads between consecutive rings (lists of BMVerts, same length, closed)."""
    n = len(rings[0])
    for k in range(1, len(rings)):
        a, b = rings[k - 1], rings[k]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mats[k - 1]
    if close_top is not None:
        bm.faces.new(rings[-1]).material_index = close_top
    if close_bottom is not None:
        bm.faces.new(list(reversed(rings[0]))).material_index = close_bottom


def hull(pts):
    """Convex hull (monotone chain) of points (px)."""
    p = sorted(set((float(x), float(y)) for x, y in pts))
    if len(p) < 3:
        return p

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def stone(s, poly, z0, ztop, mat, rng, toward):
    """A rough-cut stone over `poly` (pattern px), leaning on the pit's lip: highest on the side
    toward `toward` (the pit's centre) and sloping away; vertical faces, a chamfer, and a top split
    into facets round a low ridge point, flat shaded (lit faces carry the art's light and shade)."""
    pts = [(float(x), float(y)) for x, y in poly]
    if ls.area(pts) < 0:
        pts.reverse()
    a = ls.area(pts)
    ch1 = ls.inset(pts, 0.5)
    ch2 = ls.inset(pts, 1.1)
    if ls.area(ch2) < 0.25 * a:
        ch2 = ls.inset(pts, 0.75)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    dx, dy = toward[0] - cx, toward[1] - cy
    d = math.hypot(dx, dy) or 1.0
    dx, dy = dx / d, dy / d
    near = max(dx * (x - cx) + dy * (y - cy) for x, y in pts)
    slope = 0.011 + rng.uniform(-0.002, 0.002)

    def zt(p, z):
        # highest at the edge nearest the pit, falling away from it
        return z - slope * (near - (dx * (p[0] - cx) + dy * (p[1] - cy)))

    bm = bmesh.new()
    base = [bm.verts.new((s.x(x), s.y(y), z0)) for x, y in pts]
    wall = [bm.verts.new((s.x(x), s.y(y), zt((x, y), ztop - 0.04))) for x, y in pts]
    mid = [bm.verts.new((s.x(x), s.y(y), zt((x, y), ztop - 0.012))) for x, y in ch1]
    top = [bm.verts.new((s.x(x), s.y(y), zt((x, y), ztop))) for x, y in ch2]
    loft_rings(bm, [base, wall, mid, top], [mat, mat, mat], close_bottom=mat)
    ax, ay = cx + dx * 0.6 + rng.uniform(-0.4, 0.4), cy + dy * 0.6 + rng.uniform(-0.4, 0.4)
    apex = bm.verts.new((s.x(ax), s.y(ay), zt((ax, ay), ztop) + 0.014))
    n = len(top)
    for i in range(n):
        bm.faces.new((top[i], top[(i + 1) % n], apex)).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)


def crust_cells(rng, pool_poly, step=2.3, crack=0.2):
    """Voronoi cells of jittered seeds inside the pool polygon, each shrunk by `crack` px from its
    neighbours and the pool's edge (clipped to the pool's edge shrunk 0.25 px)."""
    edge = ls.inset(pool_poly, 0.3)
    xs = [p[0] for p in edge]
    ys = [p[1] for p in edge]
    seeds = []
    y = min(ys) - step
    j = 0
    while y < max(ys) + step:
        x = min(xs) - step + (step / 2 if j % 2 else 0)
        while x < max(xs) + step:
            seeds.append((x + rng.uniform(-0.7, 0.7), y + rng.uniform(-0.6, 0.6)))
            x += step
        y += step * 0.87
        j += 1

    def clip(poly, a, b, c):
        out = []
        for i, p in enumerate(poly):
            q = poly[(i + 1) % len(poly)]
            dp, dq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
            if dp <= 0:
                out.append(p)
            if (dp <= 0) != (dq <= 0):
                t = dp / (dp - dq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
        return out

    cells = []
    for k, (sx, sy) in enumerate(seeds):
        poly = list(edge)
        for m, (tx, ty) in enumerate(seeds):
            if m == k or abs(tx - sx) > step * 2.5 or abs(ty - sy) > step * 2.5:
                continue
            a, b = tx - sx, ty - sy
            d = math.hypot(a, b)
            a, b = a / d, b / d
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            poly = clip(poly, a, b, a * mx + b * my - crack)
            if len(poly) < 3:
                break
        if len(poly) >= 3 and abs(ls.area(poly)) > 0.45:
            cells.append(((sx, sy), poly))
    return cells


def build(bake=True, preview=None):
    lb.clear_scene()
    s = tb.Structure("lava-pit")
    rng = random.Random("tyrbld-lava-pit-A")
    H, W = s.H, s.W
    M = masks(s)
    pit, pool = M["pit"], M["pool"]
    ys, xs = np.nonzero(pit)
    CX, CY = xs.mean() + 0.5, ys.mean() + 0.5
    r_pit = radial_profile(pit, CX, CY)
    r_pool = radial_profile(pool, CX, CY)
    r_pool = np.minimum(r_pool, r_pit - POOL_INSET)
    mouth = ring_pts(CX, CY, r_pit)
    # The lip's outer edge: the art's hollow grown 2 px (its own staircase, traced and low-passed).
    lip_art = kit.dil_disk(pit, 2)
    r_lip = np.clip(radial_profile(lip_art, CX, CY, harm=6), r_pit + 1.1, r_pit + 3.0)
    lip_out = ring_pts(CX, CY, r_lip)
    cut_poly = ring_pts(CX, CY, r_pit, CUT_W)

    # --- Colours: the art's own index per region ---------------------------------------------------
    lip_ring = lb.dilate(pit, 2) & ~pit & ~M["tan"]
    P_LIP = tone(s, lip_ring)
    wall_px = pit & ~pool
    P_WALL = 0  # the art's black edge (1/80 in the art: black)
    P_WARM = 64  # the lava-lit foot of the wall, just over the pool (64 in the art: near black)
    mats = dict(
        lip=[s.m(P_LIP, roughness=0.75), s.m(max(P_LIP - 1, 4), roughness=0.78), s.m(P_LIP + 1, roughness=0.72)],
        wall=s.m(P_WALL, roughness=0.85),
        # D126: strength 1 = the palette colour unlit (the sprite's pixel); a little over 1 on the
        # brightest swells only, so the reds stay red under tone mapping. Metallic 1 and rough: in game
        # the lit colour of a strength >= 1 glow is black, so a metal one reflects nothing (a glossy
        # dielectric pool caught the sun as a grey-pink film over the red, the "lid" of review #17).
        warm=s.pal(P_WARM, emission_strength=1.0, roughness=0.9, metallic=1.0),
        hotwall=s.pal(112, emission_strength=1.0, roughness=0.9, metallic=1.0),
        lava=s.pal(114, emission_strength=1.0, roughness=0.9, metallic=1.0),
        swell={115: s.pal(115, emission_strength=1.0, roughness=0.85, metallic=1.0),
               116: s.pal(116, emission_strength=1.1, roughness=0.85, metallic=1.0),
               117: s.pal(117, emission_strength=1.25, roughness=0.85, metallic=1.0)},
        crust_dark=s.pal(64, roughness=0.95),
        crust_red=s.pal(112, emission_strength=1.0, roughness=0.9, metallic=1.0),  # cooling crust: the art's 112/113
        plug=s.m(0, roughness=0.95),
    )
    regions = [("lip", lip_ring, P_LIP), ("wall(black)", wall_px & M["black"] | (wall_px & ~lb.dilate(pool, 1)), P_WALL),
               ("pool", pool, 114)]

    # --- 1. The bowl: mouth -> chamfered ledges -> pool. Rings as (fraction mouth->pool, z, mat) ---
    steps = [(0.0, -0.005, None),
             (0.0, -0.045, "wall"), (0.08, -0.055, "wall"),          # the mouth's wall and chamfer
             (0.30, -0.06, "wall"), (0.30, -0.10, "wall"), (0.37, -0.11, "wall"),   # ledge 1
             (0.58, -0.125, "wall"), (0.58, -0.17, "wall"), (0.65, -0.18, "wall"),  # ledge 2
             (0.84, -0.19, "wall"), (0.86, LAVA_Z + 0.03, "warm"), (0.93, LAVA_Z + 0.006, "hotwall"),
             (1.0, LAVA_Z, "hotwall")]
    bm = bmesh.new()
    rings = []
    for f, z, _ in steps:
        r = r_pit + (r_pool - r_pit) * f
        rings.append([bm.verts.new((s.x(x), s.y(y), z)) for x, y in ring_pts(CX, CY, r)])
    mi = [mats[m] for _, _, m in steps[1:]]
    loft_rings(bm, rings, mi)
    bm.faces.new(rings[-1]).material_index = mats["lava"]  # the lava under the crust
    # The plug: from the mouth out under the lip to the cut, down to the slab's bottom, closed.
    cut_top = [bm.verts.new((s.x(x), s.y(y), -0.005)) for x, y in cut_poly]
    cut_bot = [bm.verts.new((s.x(x), s.y(y), tb.L2_SLAB_BOTTOM)) for x, y in cut_poly]
    n = len(cut_poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((rings[0][j], rings[0][i], cut_top[i], cut_top[j])).material_index = mats["plug"]
        bm.faces.new((cut_top[j], cut_top[i], cut_bot[i], cut_bot[j])).material_index = mats["plug"]
    bm.faces.new(list(reversed(cut_bot))).material_index = mats["plug"]
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)

    # --- 2. The crust: plates coloured by the art under them; hot lava open where it is brightest --
    pool_poly = ring_pts(CX, CY, r_pool)
    g = s.grid
    pc = bmesh.new()
    hot_spots = []
    stats = dict(dark=0, cool=0, open=0)
    # The art's bright lava pixels (115-117): one swell each, at its own place.
    swell_px = [(x + 0.5, y + 0.5, int(g[y, x])) for y, x in zip(*np.nonzero(np.isin(g, [115, 116, 117]) & pool))]
    for (sx, sy), poly in crust_cells(rng, pool_poly, step=1.9, crack=0.22):
        pm = poly_mask(poly, W, H, ss=4)
        v = g[pm & (g >= 0)]
        if not len(v):
            v = g[int(sy), int(sx)][None]
        dark = np.isin(v, list(CRUST) + [1, 2, 3, 80]).mean()
        reds = v[np.isin(v, list(RED))]
        red_med = int(np.median(reds)) if len(reds) else 113
        if any(abs(hx - sx) < 1.3 and abs(hy - sy) < 1.3 for hx, hy, _ in swell_px):
            kind = "open"  # round a hot spot the lava is open
        elif dark >= 0.35:
            kind = "dark"
        elif red_med <= 113 or dark >= 0.3:
            kind = "cool"
        else:
            kind = "open"
        stats[kind] += 1
        if kind == "open":
            continue  # the lava itself shows
        mat = mats["crust_dark"] if kind == "dark" else mats["crust_red"]
        z1 = LAVA_Z + (CRUST_Z if kind == "dark" else CRUST_Z * 0.55) + rng.uniform(-0.003, 0.003)
        # small plates: each cell shrunk a further 0.15 px, so the lava shows round every one
        poly = ls.inset(poly if ls.area(poly) > 0 else poly[::-1], 0.15)
        if len(poly) < 3 or abs(ls.area(poly)) < 0.25:
            continue
        inner = ls.inset(poly, 0.2)
        if len(inner) < 3 or abs(ls.area(inner)) < 0.12:
            inner = poly
        bot = [pc.verts.new((s.x(x), s.y(y), LAVA_Z - 0.004)) for x, y in poly]
        side = [pc.verts.new((s.x(x), s.y(y), z1 - 0.006)) for x, y in poly]
        top = [pc.verts.new((s.x(x), s.y(y), z1)) for x, y in inner] if inner is not poly else None
        if top is None:
            loft_rings(pc, [bot, side], [mats["crust_dark"]], close_top=mat)
        else:
            loft_rings(pc, [bot, side, top], [mats["crust_dark"], mat], close_top=mat)
    print("crust cells", stats)
    bmesh.ops.recalc_face_normals(pc, faces=pc.faces)
    s._merge(pc)
    # Hot lava welling up where the art is brightest: low smooth swells.
    # 115 a small low swell, 116/117 a bigger, brighter one: the art's embers, each at its own pixel.
    for hx, hy, idx in swell_px:
        r = 0.8 if idx == 115 else 1.1
        s.dome(hx, hy, r, r * 0.9, LAVA_Z - 0.004, 0.007 if idx == 115 else 0.011, mats["swell"][idx], sides=14, rings=3)
    print("swells", swell_px)

    # --- 3. The lip: dressed stone blocks round the mouth (V joints from their chamfers) ----------
    a_off = rng.uniform(0, 2 * math.pi / LIP_BLOCKS)
    for k in range(LIP_BLOCKS):
        t0 = a_off + 2 * math.pi * k / LIP_BLOCKS
        t1 = a_off + 2 * math.pi * (k + 1) / LIP_BLOCKS
        ts = [t0 + (t1 - t0) * u for u in np.linspace(0, 1, 6)]
        z = rng.uniform(*LIP_TOP)
        tilt = rng.uniform(-0.01, 0.01)
        zs = [z + tilt * (2 * u - 1) for u in np.linspace(0, 1, 6)]
        mat = mats["lip"][k % 3]
        bb = bmesh.new()

        def r_at(t, arr):
            # the traced radius, interpolated round the ring
            u = (t % (2 * math.pi)) / (2 * math.pi) * N
            i0 = int(u) % N
            return arr[i0] + (arr[(i0 + 1) % N] - arr[i0]) * (u - int(u))

        def loop(d, dz, joint=0.0, arr=r_pit):
            out = []
            for idx, (t, zz) in enumerate(zip(ts, zs)):
                # pull the ends in a little at the top: the V joint between blocks
                tt = t + (joint if idx == 0 else -joint if idx == len(ts) - 1 else 0.0)
                r = r_at(tt, arr) + d
                out.append(bb.verts.new((s.x(CX + r * math.cos(tt)), s.y(CY + r * math.sin(tt)), zz + dz)))
            return out

        jt = 0.35 / 8.0  # ~0.35 px of arc at the mouth
        foot_in = loop(-0.35, -0.07 - z)
        lip = loop(-0.35, -0.03, jt * 0.5)
        top_in = loop(0.15, 0.0, jt)
        top_out = loop(-0.6, 0.0, jt, r_lip)
        chamf = loop(-0.15, -0.03, jt * 0.5, r_lip)
        foot_out = loop(0.0, -0.025 - z, 0.0, r_lip)
        loops = [foot_in, lip, top_in, top_out, chamf, foot_out]
        for li in range(len(loops) - 1):
            a_, b_ = loops[li], loops[li + 1]
            for i in range(len(ts) - 1):
                bb.faces.new((a_[i], a_[i + 1], b_[i + 1], b_[i])).material_index = mat
        for i in range(len(ts) - 1):
            bb.faces.new((foot_out[i], foot_out[i + 1], foot_in[i + 1], foot_in[i])).material_index = mats["plug"]
        for end in (0, len(ts) - 1):
            bb.faces.new([lp[end] for lp in loops]).material_index = mat
        bmesh.ops.recalc_face_normals(bb, faces=bb.faces)
        s._merge(bb)

    # --- 4. The three tan stones, lit pink by the glow ---------------------------------------------
    stone_mask = np.zeros((H, W), bool)
    stone_px = np.zeros((H, W), bool)
    for key, m in sorted(M["stones"].items()):
        P = tone(s, m, lo=0.2, hi=0.3)
        regions.append((f"stone/{key}", m, P))
        stone_px |= m
        for poly in s.outlines(m, tol=0.75, min_px=6):
            poly = hull(poly)
            stone_mask |= poly_mask(poly, W, H, ss=4)
            stone(s, poly, -0.03, STONE_TOP.get(key, 0.12), s.m(P, roughness=0.7), rng, (CX, CY))

    # --- 5. The island's rock round it (plain, unbaked), cut under the lip --------------------------
    lip_mask = poly_mask(lip_out, W, H, ss=4)
    own = lip_mask | stone_mask
    s.rock(exclude=lb.erode(own, 1), cut=poly_mask(cut_poly, W, H, ss=4))

    objects = s.objects()
    for name, m, P in regions:
        print(f"colour {name:14s} model {P}  art(trimmed) {tone(s, m)}  ({int(m.sum())} px)")
    s.finish(objects, lip_art | stone_px, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
