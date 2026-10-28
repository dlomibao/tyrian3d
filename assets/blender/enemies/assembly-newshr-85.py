"""Domed city (newshr.shp, nine 2x2 pieces in a 3x3 block): a 3D version of its sprites.

Seen in episode 3 (levels 3.4 and 3.19). Nine ground enemies side by side make one 72x84 px
structure: an egg-shaped purple glass dome (narrow end up the screen, a white glare at its upper
left and a bright rim down its right side) over a cluster of blue-grey skyscrapers, standing on
cobbled brown ground with a dark shadow ring around the dome's foot.

    newshr-5   newshr-7   newshr-9        (top row: the dome's back, transparent corners)
    newshr-43  newshr-45  newshr-47       (middle: the city, ground at the sides)
    newshr-81  newshr-83  newshr-85       (bottom: the dome's front rim and the ground)

The glass is a shell from the dome's foot up to a window over the city (the sprite shows the
towers through it), so its back half stands as a curved wall behind the towers and its sides and
front are a lower rim. Over the window a frame of glass ribs on the same egg surface closes the
bubble (the panes between the ribs are the clear glass), so it encloses the city. The towers
are boxes on the sprite's building blocks, tallest at the back (the sprite draws them in an
oblique view, so each block's drawn area is its footprint here), coloured by the block's average
shade. Glass and walls take one mid-tone each (the game lights and outlines them). The ground is a low slab with cobbles where the sprite's ground is brown. The whole thing is
built once in assembly coordinates and cut into the nine pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshr-85.py [-- --preview out.png]
(the preview is the whole city; each piece also gets <piece>.png next to it).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402

NAME = "assembly-newshr-85"
ROOT = common.repo_root(__file__)
GRID = [["newshr-5", "newshr-7", "newshr-9"],
        ["newshr-43", "newshr-45", "newshr-47"],
        ["newshr-81", "newshr-83", "newshr-85"]]
PIECES = [n for row in GRID for n in row]
W, H = 72, 84  # assembly size in px; (0, 0) is the top-left corner of newshr-5
TAG = "nshr85"


def X(c):
    """Assembly pixel edge column (fractions allowed) to Blender X; the block's centre is 0."""
    return (c - W / 2) / 12


def Y(r):
    """Assembly pixel edge row to Blender Y (sprite up is +Y)."""
    return (H / 2 - r) / 12


# --- the sprite as one index map ---------------------------------------------------------------

def index_map():
    """Every piece's first frame placed in the 72x84 block: rows of palette indices (-1 empty)."""
    m = [[-1] * W for _ in range(H)]
    for gr, names in enumerate(GRID):
        for gc, name in enumerate(names):
            frame = common.load_sprite(ROOT, name)["frames"][0]
            for r, row in enumerate(frame["pixels"]):
                for c, v in enumerate(row):
                    m[gr * 28 + r][gc * 24 + c] = v
    return m


def sample(m, c, r, keep, radius=1, remap=None):
    """Mean of the indices that `keep` accepts around pixel (c, r), or None. `remap` maps indices
    from another ramp (the glare's greys) onto the one being averaged."""
    vals = []
    for rr in range(int(r) - radius, int(r) + radius + 1):
        for cc in range(int(c) - radius, int(c) + radius + 1):
            if 0 <= rr < H and 0 <= cc < W and keep(m[rr][cc]):
                v = m[rr][cc]
                vals.append(remap.get(v, v) if remap else v)
    return sum(vals) / len(vals) if vals else None


# --- outlines (pixel edges) --------------------------------------------------------------------

# The dome's outer edge, (row, left column, right column + 1), read off the sprite's outline.
EGG = [(2.2, 27, 36), (3, 24.5, 39), (5, 20.5, 43), (7, 17.5, 46), (9, 15.5, 48), (11, 13.5, 50),
       (13, 11.5, 52), (15, 10.5, 53), (17, 9.5, 54), (19, 8.5, 55), (21, 7.5, 56), (23, 6.5, 57),
       (25, 5.5, 58), (27, 4.5, 59), (30, 3.5, 60), (34, 2.5, 61), (40, 1.5, 62), (44, 1.5, 62.5),
       (48, 1.5, 61.5), (51, 2.5, 61), (54, 3.5, 59.5), (56, 5, 58.5), (58, 7.5, 57.5),
       (60, 10.5, 55), (62, 13.5, 52.5), (64, 17, 50), (66, 23, 46), (67.6, 30, 39)]

# The window in the glass over the city (counter-clockwise from the top of the central tower),
# the inner edge of the purple in the sprite.
WINDOW = [(35, 9), (29.5, 9), (29.5, 17), (26, 20), (20, 21), (19, 26), (15.5, 27), (14.5, 23.5),
          (10, 23.5), (9.5, 30), (8.5, 40), (8.5, 48), (10, 54), (13, 57.5), (18, 59.5), (24, 61.5),
          (30, 62), (37, 63), (42, 62.5), (47, 60), (51, 56), (54, 52), (55, 46), (55, 39.5),
          (51, 37), (47, 33), (45.5, 27), (45, 20), (40, 19.5), (37.5, 19.5), (36, 12)]

CENTRE = (32.0, 37.0)  # the dome's middle, in pixel edges

# The dome's height profile: a bubble about 28 px tall (a bit under half its 61 px width), its
# crown set back toward the sprite's top (the egg's narrow end, where the sprite's glare sits),
# with steep sides that curve right down to the cobbles. z = DOME_H * (1 - rn^2)^DOME_EXP, where
# rn is the distance from APEX relative to the egg's edge along the same ray.
APEX = (32.0, 26.0)
DOME_H = 28 / 12
DOME_EXP = 0.4
GLASS_T = 1.0 / 12  # the glass shell's thickness
TOWER_MARGIN = 1.5 / 12  # how far every tower roof stays under the glass
COBBLE_LIFT = 0.3  # cobbles take the ground shade under them, this many indices lighter

# The glass over the window is a frame of ribs on the same egg surface (the panes between them
# are the clear glass the sprite looks through), so the bubble is closed over the city: parallels
# at these fractions of the way from APEX to the egg's edge, MERIDIANS ribs from the crown cap and
# as many again between them from the second parallel.
PARALLELS = (0.35, 0.68)
MERIDIANS = 8
CAP_RN = 0.12
RIB_W = 1.0  # px
GLASS_MID = 84  # the glass's purple: the sprite's glass averages ~85 with the glare; one step darker since the
# environment's reflections already lighten the glossy shell from the game camera
WALL_MID = 101  # the towers' facades: the city ramp's mid-tone (the game lights the walls)


def dome_height(c, r, egg):
    """Height of the dome's outer surface over pixel edges (c, r) (0 outside the egg)."""
    d = math.dist((c, r), APEX)
    if d < 1e-6:
        return DOME_H
    hit = ray_hit(egg, APEX, math.atan2(r - APEX[1], c - APEX[0]))
    rn = d / max(1e-6, math.dist(hit, APEX))
    return DOME_H * max(0.0, 1 - rn * rn) ** DOME_EXP


def egg_outline():
    left = [(l, r) for r, l, _ in EGG]
    right = [(rr, r) for r, _, rr in reversed(EGG)]
    return left + right  # down the left side, up the right side


def ray_hit(poly, centre, angle):
    """Farthest point where a ray from `centre` at `angle` crosses the closed polygon."""
    cx, cy = centre
    dx, dy = math.cos(angle), math.sin(angle)
    best = None
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((x1 - cx) * ey - (y1 - cy) * ex) / den
        u = ((x1 - cx) * dy - (y1 - cy) * dx) / den
        if t > 0 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t > best):
            best = t
    return (cx + dx * best, cy + dy * best)


def inside(poly, x, y):
    hit = False
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit


# --- geometry ----------------------------------------------------------------------------------

def box(bm, c0, c1, r0, r1, z0, z1, side_mat, top_mat, south=None, east=None, north=None, west=None):
    """A box over pixel edges c0..c1, r0..r1, from z0 to z1, with its own top material (and
    optionally its own material per wall; south is the screen-bottom wall)."""
    xs, ys = (X(c0), X(c1)), (Y(r1), Y(r0))
    v = [bm.verts.new((xs[i], ys[j], z)) for z in (z0, z1) for j in (0, 1) for i in (0, 1)]
    # v index: bottom 0..3 (x0y0, x1y0, x0y1, x1y1), top 4..7
    pick = lambda m: side_mat if m is None else m  # noqa: E731
    quads = [((0, 2, 3, 1), side_mat), ((4, 5, 7, 6), top_mat), ((0, 1, 5, 4), pick(south)),
             ((1, 3, 7, 5), pick(east)), ((3, 2, 6, 7), pick(north)), ((2, 0, 4, 6), pick(west))]
    for idx, mat in quads:
        f = bm.faces.new([v[i] for i in idx])
        f.material_index = mat
        f.smooth = False


def stone(bm, rng, c, r, z, rx_px, ry_px, h, mat, sides=7):
    """A cobble: an irregular polygon with a bevelled flat top, centred on pixel edges (c, r)."""
    a0 = rng.random() * math.tau
    base, top = [], []
    for i in range(sides):
        a = a0 + math.tau * i / sides
        k = rng.uniform(0.8, 1.1)
        x, y = math.cos(a) * rx_px * k / 12, math.sin(a) * ry_px * k / 12
        base.append(bm.verts.new((X(c) + x, Y(r) + y, z)))
        top.append(bm.verts.new((X(c) + x * 0.65, Y(r) + y * 0.65, z + h)))
    faces = [bm.faces.new(top), bm.faces.new(list(reversed(base)))]
    for i in range(sides):
        j = (i + 1) % sides
        faces.append(bm.faces.new((base[i], base[j], top[j], top[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False


def slab_px(bm, poly, z0, z1, mat):
    """An extruded outline of pixel-edge points, z0 to z1."""
    pts = [(X(c), Y(r)) for c, r in poly]
    # common.slab wants counter-clockwise seen from above; normals get recalculated anyway.
    n = len(bm.faces)
    common.slab(bm, pts, z1 - z0, z=(z0 + z1) / 2, mat_index=mat)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n:]:
        f.smooth = False


# --- the city ----------------------------------------------------------------------------------

# Building blocks: (col0, col1, row0, row1, height). Their drawn facades are their footprints.
TOWERS = [
    (29.5, 35, 9, 24, 0.66),  # the central tower, tallest, at the back
    (26, 36, 21.5, 37, 0.46),  # the block at its foot
    (37.5, 45, 19.5, 34, 0.54),  # the right tower
    (36, 45, 33, 41, 0.36),
    (10, 15, 23.5, 41, 0.48),  # the left tower
    (15, 19, 28, 40, 0.3),
    (19, 26, 21, 33, 0.5),
    (19, 23, 33, 41, 0.38),
    (31, 36, 37, 47, 0.3),
    (26.5, 30.5, 37.5, 47, 0.32),  # the light front tower
    (23.5, 26.5, 39.5, 48, 0.24),
    (33, 45, 41, 51, 0.24),
    (44.5, 50, 30, 51, 0.3),
    (49.5, 55, 38.5, 52, 0.18),
    (9, 15.5, 41, 51, 0.22),
    (15, 20.5, 40, 48, 0.22),
    (20.5, 26, 33, 41, 0.28),
    (15, 24, 48, 57, 0.14),
    (24, 33, 47, 60, 0.12),
    (33, 41, 51, 61, 0.12),
    (41, 51, 50, 59, 0.12),
]


def tower_px(h):
    """A TOWERS height (the old, quarter-scale units) as the skyscraper height in sprite px: the
    central tower about 24 px, the ring of smaller blocks 10-16 px, the front rim blocks about 6."""
    return 24 * (h / 0.66) ** 0.8


def build(sprite, m):
    coll = common.reset_collection(NAME)
    # Glossy glass: the game's sun and environment make the sprite's glare and bright rim.
    glass = dict(metallic=0.05, roughness=0.1)
    rock = dict(metallic=0.0, roughness=0.9)
    city = dict(metallic=0.3, roughness=0.4)
    pal = lambda i, **kw: common.palette_material(sprite, i, TAG, **kw)  # noqa: E731
    glass_idx = [82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95]
    city_idx = [96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 109]
    ground_idx = [16, 17, 18, 19, 20]
    mats = ([pal(i, **glass) for i in glass_idx] + [pal(i, **city) for i in city_idx]
            + [pal(i, **rock) for i in ground_idx])
    G0, C0, S0 = 0, len(glass_idx), len(glass_idx) + len(city_idx)

    def nearest(idx_list, base, value):
        k = min(range(len(idx_list)), key=lambda i: abs(idx_list[i] - value))
        return base + k

    def glass_mat(c, r):
        """The glass's colour: one mid-tone purple all over. The sprite's glare, its bright right
        rim, its dark lower-right side and its dark outline ring at the foot are drawn light, which
        the game's lights and outline make on the glossy shell, so none of it is painted on."""
        return nearest(glass_idx, G0, GLASS_MID)

    bm = bmesh.new()

    # Ground: a low slab under the bottom two rows of pieces and the city floor in the window.
    slab_px(bm, [(0, 28), (0, 84), (72, 84), (72, 28)], 0.0, 0.03, S0)
    slab_px(bm, WINDOW, 0.0, 0.035, C0)

    # Cobbles where the sprite's ground is brown, outside the dome, in the warmer browns.
    egg = egg_outline()
    rng = random.Random(85)
    step = 4.3
    r = 28 + step / 2
    while r < H:
        c = (rng.random() * step) / 2
        while c < W:
            cc, rr = c + rng.uniform(-0.8, 0.8), r + rng.uniform(-0.8, 0.8)
            v = sample(m, cc, rr, lambda x: 16 <= x <= 20, radius=1)
            if v is not None and not inside(egg, cc, rr) and 0 < cc < W and 28 < rr < H:
                stone(bm, rng, cc, rr, 0.03, rng.uniform(2.3, 2.9), rng.uniform(1.9, 2.4),
                      rng.uniform(0.025, 0.04), nearest(ground_idx, S0, v + COBBLE_LIFT))
            c += step
        r += step

    # The glass: a thin shell from the dome's foot (on the cobbles, z = 0) up to the window over
    # the city, where it stops so the city shows from above (the rest of the bubble is the clear
    # glass the sprite looks through). Rings run from the foot inwards along rays from CENTRE,
    # closer together near the foot where the shell is steep; heights follow dome_height.
    N, K = 96, 9
    outer, inner = [], []
    for i in range(N):
        a = 2 * math.pi * i / N
        outer.append(ray_hit(egg, CENTRE, a))
        inner.append(ray_hit(WINDOW, CENTRE, a))

    pts = []  # pts[k][i]: pixel-edge (c, r) of ring k
    for k in range(K + 1):
        t = 1 - math.cos(k / K * math.pi / 2)
        pts.append([(o[0] + (n[0] - o[0]) * t, o[1] + (n[1] - o[1]) * t) for o, n in zip(outer, inner)])
    zs = [[0.0 if k == 0 else dome_height(c, r, egg) for c, r in ring] for k, ring in enumerate(pts)]
    out_rings = [[bm.verts.new((X(c), Y(r), z)) for (c, r), z in zip(ring, zr)] for ring, zr in zip(pts, zs)]
    in_rings = [out_rings[0]] + [[bm.verts.new((X(c), Y(r), max(0.0, z - GLASS_T))) for (c, r), z in zip(ring, zr)]
                                 for ring, zr in zip(pts[1:], zs[1:])]

    def quad(a, b, c, d, mat, smooth):
        f = bm.faces.new((a, b, c, d))
        f.material_index = mat
        f.smooth = smooth
        return f

    for k in range(K):
        for i in range(N):
            j = (i + 1) % N
            o0, o1, i0, i1 = out_rings[k], out_rings[k + 1], in_rings[k], in_rings[k + 1]
            pc = [(pts[k][i][0] + pts[k][j][0] + pts[k + 1][i][0] + pts[k + 1][j][0]) / 4,
                  (pts[k][i][1] + pts[k][j][1] + pts[k + 1][i][1] + pts[k + 1][j][1]) / 4]
            quad(o0[i], o0[j], o1[j], o1[i], glass_mat(*pc), True)  # outside: the sprite's shade
            if k == 0:  # the foot ring is shared, so the first inner band is a triangle fan strip
                f = bm.faces.new((o0[j], o0[i], i1[i], i1[j]))
            else:
                f = bm.faces.new((i0[j], i0[i], i1[i], i1[j]))
            f.material_index = G0  # the inside of the glass, dark
            f.smooth = True
    for i in range(N):  # the cut edge of the glass round the window
        j = (i + 1) % N
        quad(out_rings[K][i], out_rings[K][j], in_rings[K][j], in_rings[K][i], G0, False)

    # The frame closing the bubble over the window (see PARALLELS).
    rib_mat = nearest(glass_idx, G0, GLASS_MID + 1)
    win_in = lambda p: inside(WINDOW, *p)  # noqa: E731

    def on_egg(rn, a):
        h = ray_hit(egg, APEX, a)
        return (APEX[0] + (h[0] - APEX[0]) * rn, APEX[1] + (h[1] - APEX[1]) * rn)

    def rib(path, closed, lift):
        """A rib along `path` (pixel edges), RIB_W wide, its top on the egg surface (+ lift px)
        and GLASS_T deep, kept to the window (plus one sample under the solid glass each end)."""
        n = len(path)
        ok = [win_in(p) for p in path]
        if not any(ok):
            return
        runs = []
        if closed and all(ok):
            runs.append((list(range(n)), True))
        else:
            start = next(i for i in range(n) if not ok[i]) if closed else 0
            order = [(start + k) % n for k in range(n)] if closed else list(range(n))
            cur = []
            for idx in order:
                if ok[idx]:
                    cur.append(idx)
                elif cur:
                    runs.append((cur, False))
                    cur = []
            if cur:
                runs.append((cur, False))
            ext = []
            for run, _ in runs:
                a, b = run[0], run[-1]
                pre = (a - 1) % n if closed else a - 1
                post = (b + 1) % n if closed else b + 1
                run = ([pre] if (closed or pre >= 0) else []) + run + ([post] if (closed or post < n) else [])
                ext.append((run, False))
            runs = ext
        for run, loop in runs:
            if len(run) < 2:
                continue
            secs = []
            for k, idx in enumerate(run):
                p0 = path[run[k - 1]] if (k > 0 or loop) else path[idx]
                p1 = path[run[(k + 1) % len(run)]] if (k < len(run) - 1 or loop) else path[idx]
                tx, ty = p1[0] - p0[0], p1[1] - p0[1]
                ln = math.hypot(tx, ty) or 1
                nx, ny = -ty / ln * RIB_W / 2, tx / ln * RIB_W / 2
                c, r = path[idx]
                sec = []
                for s in (-1, 1):
                    cc, rr = c + nx * s, r + ny * s
                    z = dome_height(cc, rr, egg) + lift / 12
                    sec.append((cc, rr, z))
                vt = [bm.verts.new((X(cc), Y(rr), z)) for cc, rr, z in sec]
                vb = [bm.verts.new((X(cc), Y(rr), z - GLASS_T)) for cc, rr, z in sec]
                secs.append((vt[0], vt[1], vb[1], vb[0]))  # top-left, top-right, bottom-right, bottom-left
            pairs = list(zip(secs, secs[1:])) + ([(secs[-1], secs[0])] if loop else [])
            for s0, s1 in pairs:
                quad(s0[0], s0[1], s1[1], s1[0], rib_mat, True)  # top
                quad(s0[3], s1[3], s1[2], s0[2], G0, True)  # underside
                quad(s0[1], s0[2], s1[2], s1[1], rib_mat, False)  # sides
                quad(s0[0], s1[0], s1[3], s0[3], rib_mat, False)
            if not loop:
                for s in (secs[0], secs[-1]):
                    quad(s[0], s[1], s[2], s[3], rib_mat, False)

    def samples_along(fn, t0, t1, approx_len, step=0.7):
        n = max(2, int(approx_len / step) + 1)
        return [fn(t0 + (t1 - t0) * i / (n - 1)) for i in range(n)]

    R_EST = 30.0  # px, the egg's rough radius from APEX, only for sampling density
    for rn in PARALLELS:
        n = max(16, int(math.tau * rn * R_EST / 0.7))
        rib([on_egg(rn, math.tau * i / n) for i in range(n)], True, 0.12)
    for j in range(2 * MERIDIANS):
        a = math.tau * j / (2 * MERIDIANS) + math.pi / 2  # j = 0 runs straight down the screen
        rn0 = CAP_RN if j % 2 == 0 else PARALLELS[1]
        rib(samples_along(lambda t: on_egg(t, a), rn0 * 0.9, 1.0, (1 - rn0) * R_EST), False, 0.0)
    # The crown cap the main meridians meet at.
    ring = [on_egg(CAP_RN, math.tau * i / 16) for i in range(16)]
    top_c = bm.verts.new((X(APEX[0]), Y(APEX[1]), DOME_H + 0.06 / 12))
    bot_c = bm.verts.new((X(APEX[0]), Y(APEX[1]), DOME_H + 0.06 / 12 - GLASS_T))
    tops = [bm.verts.new((X(c), Y(r), dome_height(c, r, egg) + 0.06 / 12)) for c, r in ring]
    bots = [bm.verts.new((X(c), Y(r), dome_height(c, r, egg) + 0.06 / 12 - GLASS_T)) for c, r in ring]
    for i in range(16):
        j = (i + 1) % 16
        f = bm.faces.new((top_c, tops[i], tops[j]))
        f.material_index, f.smooth = rib_mat, True
        f = bm.faces.new((bot_c, bots[j], bots[i]))
        f.material_index, f.smooth = G0, True
        quad(tops[i], bots[i], bots[j], tops[j], rib_mat, False)

    # The towers: upright blocks, kept under the glass. Each roof carries the sprite's own pixels
    # in the city ramp (runs of one shade per row, a hair above the roof), so from above the city
    # has the sprite's dark blue-teal blocks, pale cyan lit edges and window dots. The west walls
    # take the pale lit-face shade, the south and east walls darker, and the south and west walls
    # get rows of lit windows.
    decals = []  # (face, the way it must face)

    def decal(corners, mat, facing):
        f = bm.faces.new([bm.verts.new(p) for p in corners])
        f.material_index = mat
        f.smooth = False
        decals.append((f, facing))

    def city_shade(v, fallback):
        if 96 <= v <= 110:
            return nearest(city_idx, C0, v)
        if 0 <= v <= 2:  # the sprite's black outlines between blocks
            return nearest(city_idx, C0, 96)
        return fallback

    UP, SOUTH, WEST = Vector((0, 0, 1)), Vector((0, -1, 0)), Vector((-1, 0, 0))
    wrng = random.Random(4385)
    for c0, c1, r0, r1, h in TOWERS:
        a0, a1, b0, b1 = c0 + 0.45, c1 - 0.45, r0 + 0.45, r1 - 0.45
        under = min(dome_height(a0 + (a1 - a0) * i / 4, b0 + (b1 - b0) * j / 4, egg)
                    for i in range(5) for j in range(5)) - GLASS_T - TOWER_MARGIN
        h = max(0.12, min(tower_px(h) / 12, under))
        vals = [m[rr][cc] for rr in range(int(r0), int(math.ceil(r1))) for cc in range(int(c0), int(math.ceil(c1)))
                if 96 <= m[rr][cc] <= 109]
        avg = sum(vals) / len(vals) if vals else 100
        top = nearest(city_idx, C0, avg - 1)
        box(bm, a0, a1, b0, b1, 0.035, h, nearest(city_idx, C0, WALL_MID), top)
        # The roof's pixels: runs of one shade per sprite row, clipped to the roof.
        zt = h + 0.01
        for rr in range(int(math.floor(b0)), int(math.ceil(b1))):
            y0, y1 = max(rr, b0), min(rr + 1, b1)
            run_mat, run_start = None, None
            cols = list(range(int(math.floor(a0)), int(math.ceil(a1))))
            for cc in cols + [None]:
                mat = None if cc is None else city_shade(m[rr][cc], top)
                if mat != run_mat:
                    if run_mat is not None and run_mat != top:
                        x0, x1 = max(run_start, a0), min(cc if cc is not None else a1, a1)
                        decal([(X(x0), Y(y1), zt), (X(x1), Y(y1), zt), (X(x1), Y(y0), zt), (X(x0), Y(y0), zt)],
                              run_mat, UP)
                    run_mat, run_start = mat, cc
        # Windows: rows of lit windows along the walls, a floor every 3 px (the sprite's horizontal
        # light bands), each row broken into a run or two, some floors dark.
        if h * 12 < 9:
            continue
        floors = [z / 12 for z in range(4, int(h * 12) - 2, 3)]
        for wall, lo, hi in (("south", a0, a1), ("west", b0, b1)):
            for z in floors:
                if wrng.random() > 0.7:
                    continue
                cuts = [lo + 0.7, hi - 0.7]
                if hi - lo > 6 and wrng.random() < 0.5:
                    g = wrng.uniform(lo + 2.5, hi - 2.5)
                    cuts = [lo + 0.7, g - 0.5, g + 0.5, hi - 0.7]
                mat = nearest(city_idx, C0, wrng.choice((104, 105, 106, 107)))
                z1 = z + 1.0 / 12
                for s0, s1 in zip(cuts[::2], cuts[1::2]):
                    if wall == "south":
                        y = Y(b1) - 0.006
                        decal([(X(s0), y, z), (X(s1), y, z), (X(s1), y, z1), (X(s0), y, z1)], mat, SOUTH)
                    else:
                        x = X(a0) - 0.006
                        decal([(x, Y(s0), z), (x, Y(s1), z), (x, Y(s1), z1), (x, Y(s0), z1)], mat, WEST)

    return to_object(NAME, bm, mats, coll, decals)


def to_object(name, bm, mats, coll, decals=()):
    """Like common.mesh_object, but keeps each face's own smooth/flat flag, and turns each loose
    decal face to face the way it was made for (recalc can't tell for a face on its own)."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f, facing in decals:
        f.normal_update()
        if f.normal.dot(facing) < 0:
            f.normal_flip()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for mat in mats:
        mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


def merged_sprite():
    """newshr-85's sprite.json with the colours of every piece, so any piece's index is valid."""
    data = common.load_sprite(ROOT, "newshr-85")
    for name in PIECES:
        data["colors"].update(common.load_sprite(ROOT, name)["colors"])
    return data


def layout():
    """(piece, cx, cy) in assembly pixels relative to the block's centre, as split_assembly wants."""
    return [(name, gc * 24 + 12 - W / 2, gr * 28 + 14 - H / 2)
            for gr, names in enumerate(GRID) for gc, name in enumerate(names)]


def composite_png(m, colors, out):
    """The whole block's sprite as one image, 72 x 84 px, already the 24:28 shape render_preview expects."""
    import numpy as np
    img = np.zeros((H, W, 4), dtype=np.float32)
    for r in range(H):
        for c in range(W):
            v = m[r][c]
            if v >= 0:
                img[r, c] = [*(ch / 255 for ch in colors[str(v)]), 1.0]
    im = bpy.data.images.new("assembly_sprite", W, H, alpha=True)
    im.pixels[:] = img[::-1].ravel()
    im.filepath_raw = str(out)
    im.file_format = "PNG"
    im.save()
    bpy.data.images.remove(im)
    return out


def main():
    sprite = merged_sprite()
    m = index_map()
    obj = build(sprite, m)
    pieces = common.split_assembly(obj, layout())
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    print(f"whole: {len(obj.data.polygons)} faces")
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        import tempfile
        ref = composite_png(m, sprite["colors"], Path(tempfile.mkdtemp()) / "assembly.png")
        common.render_preview([obj], str(out), ref, size=6, view_px=480)
        for name in PIECES:
            data = common.load_sprite(ROOT, name)
            img = ROOT / "reference" / "models" / name / data["frames"][0]["image"]
            common.render_preview([pieces[name]], str(out.parent / f"{name}.png"), img, size=2)


if __name__ == "__main__":
    main()
