"""The full-width walkway bridge of TYRIAN (map 1-9, layer 2, rows 199-201, 223-225 and 236-238;
15x3 tiles), after the concepts assets/blender/features/concepts/tyr-bridge-a/-b/-c.jpg: a riveted
metal walkway (tile 180) with a raised maze relief, a curb plate along its top edge over a dark
shadow groove and a lower plate along its foot, running off both map edges; above it the island's
rock rim (tile 121: grey stones and tan boulders), below it the rocky underside (tile 141): a band
of grey stones with a few tan nuggets, and the stalactites and roots hanging down from it.

The bridge is drawn in the Background3Over pass (height 4.15, over the player), so everything stays
under L2_OVER_MAX. It replaces its tiles, so the model carries their rock. Rock and stones are built
here rather than with Structure.rock()'s per-tile boulders: the rim's big tan boulders straddle the
tile edges, and per-tile halves left a dark seam down each one; the underside is built as separate
tapering stalactites in front of a shallow dark face instead of one hanging curtain.

The concept: tyr-bridge-a (the painted look closest to the tiles) registered on all three spans
(b drifted to a photographic, crumbly look, and c's boulders sat off the tiles' and baked half dark).
Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_bridge.py
    python tools/concept_maps.py tile:shapesz-tyrbld-bridge --part tyr-bridge-a:0,0,2,5 \
        --part tyr-bridge-a:0,5,2,10 --part tyr-bridge-a:0,9,2,14 --px 8
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-bridge --size 4096
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import lib_tiles as lt  # noqa: E402
import lib_tyrbld as tb  # noqa: E402

# Pixel rows (pattern px, 1x) of the walkway row (pattern row 1: py 28..55), from tile 180's art.
WALK_Y0, WALK_Y1 = 28, 56
CURB = (28, 30)  # the bright curb plate along the top edge
GROOVE = (30, 32)  # the dark shadow line under the curb
FOOT = (53, 56)  # the bright plate along the foot
DECK = tb.L2_DECK  # 0.06
CURB_Z = DECK + 0.07
FOOT_Z = DECK + 0.045
GROOVE_Z = DECK - 0.03
RIDGE_Z = DECK + 0.018  # the maze's raised lines
SEAM_EVERY = 24  # the plates are segmented once per tile
SLAB_BOTTOM = -0.34  # the walkway's slab (over: bottoms about -0.35)

# Rock.
RIM_COL0 = 2  # the rim starts at col 2 (cols 0-1 are other tiles' in one copy: per-tile models)
LEDGE_Y = 23  # rim stones centred below this (1x, in the rim row) are the grey ledge slabs
UNDER_Y0 = 56  # the underside row
UNDER_FACE_BOTTOM = -0.40  # the dark face behind the stalactites
SPIKE_DROP = 0.62  # how far a stalactite drops over the underside tile's height
SPIKE_MAX = -0.82


def stone_pattern(s):
    """The pattern with its usual neighbours round it (one tile each side, as lt.context), the
    rim's missing cols 0-1 filled with 121 as in two of the three copies: the stones are found on
    this and cut to the model's own cells, so the ones crossing an edge match the per-tile models."""
    rim, walk, under = (list(r) for r in s.pattern)
    rim = [121 if t < 0 else t for t in rim]
    up = lt.context(s.ts, 121)[0][1]
    down = lt.context(s.ts, 141)[2][1]
    W = len(rim) + 2
    return [[up] * W, [121] + rim + [121], [180] + walk + [180], [141] + under + [141], [down] * W]


def cut(bm, x0=None, x1=None, y0=None, y1=None):
    """Remove the geometry outside the box (model units; None: open)."""
    planes = []
    if x0 is not None:
        planes.append(((x0, 0, 0), (-1, 0, 0)))
    if x1 is not None:
        planes.append(((x1, 0, 0), (1, 0, 0)))
    if y0 is not None:
        planes.append(((0, y0, 0), (0, -1, 0)))
    if y1 is not None:
        planes.append(((0, y1, 0), (0, 1, 0)))
    for co, no in planes:
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=Vector(co), plane_no=Vector(no), clear_outer=True)


def stones(s, grey, tan_rim, tan_under):
    """Rounded boulders for the painted stones of the rim and of the underside's stone band, built
    whole over the full row and cut to the model's cells. Colours: tan boulders and nuggets keep
    their ochre; everything else (the ledge slabs, the underside stones) is grey stone, with the
    underside's tan nuggets in one tan."""
    P = stone_pattern(s)
    g2 = s.ts.grid(P, 2)
    lum = lt.lum_of(s.ts, g2)
    frame = lt.Frame(P, 2)  # same centre as the model's frame (one tile all round)
    th = lt.TILE_H * 2
    rows = np.arange(g2.shape[0])[:, None]
    rim_band = (rows >= th) & (rows < 2 * th)
    under_band = (rows >= 3 * th) & (rows < 4 * th)
    out = []
    for band, kind in ((rim_band, "rim"), (under_band, "under")):
        mask = (g2 >= 0) & band
        for ys, xs in lt.hills(lum, mask, sigma=2.2, floor=0.22):
            if len(ys) < 8:
                continue
            cx, cy, rx, ry, ang = lt.ellipse(ys, xs)
            ly = cy / 2 - (1 if kind == "rim" else 3) * lt.TILE_H  # 1x, within its tile row
            if kind == "under" and ly > 14:
                continue  # roots and stalactites: built as spikes
            idx = g2[ys, xs]
            bright = idx[lum[ys, xs] > 0.22]
            ramps = np.maximum(bright, 0) >> 4
            tan_frac = np.isin(ramps, (1, 10)).mean() if len(bright) else 0.0
            if kind == "rim" and tan_frac > 0.5 and ly < LEDGE_Y:
                mat = tan_rim(idx, lum[ys, xs])
            elif kind == "under" and tan_frac > 0.6:
                mat = tan_under
            else:
                mat = grey
            rx, ry = (rx + 0.6) / 24, (ry + 0.6) / 24
            height = min(0.2, 0.55 * min(rx, ry) + 0.02)
            out.append((kind, frame.x(cx), frame.y(cy), rx, ry, -ang, height, mat))
    for kind, bx, by, rx, ry, ang, height, mat in out:
        sb = bmesh.new()
        lt.dome(sb, bx, by, rx, ry, ang, -0.03, height, mat, sides=12, rings=3, squash=0.2)
        if kind == "rim":
            cut(sb, x0=s.x(RIM_COL0 * lt.TILE_W), x1=s.x(s.W), y0=s.y(WALK_Y0), y1=s.y(0))
        else:
            cut(sb, x0=s.x(0), x1=s.x(s.W), y0=s.y(s.H), y1=s.y(UNDER_Y0))
        s._merge(sb, smooth=True)
    return out


def spike(bm, a, b, r, mat, sides=6, flat=0.7):
    """A tapering stalactite from the point a (its root, radius r) to the tip b (model units)."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    u = axis.cross(Vector((1, 0, 0))).normalized()
    if u.length < 1e-6:
        u = axis.cross(Vector((0, 1, 0))).normalized()
    v = axis.cross(u).normalized()
    rings = []
    for t, k in ((0.0, 1.0), (0.45, 0.62), (0.8, 0.3)):
        c = a.lerp(b, t)
        rings.append([bm.verts.new(c + (u * math.cos(2 * math.pi * i / sides) * flat
                                        + v * math.sin(2 * math.pi * i / sides)) * r * k) for i in range(sides)])
    tip = bm.verts.new(b)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((r0[i], r0[j], r1[j], r1[i])).material_index = mat
    for i in range(sides):
        bm.faces.new((rings[-1][i], rings[-1][(i + 1) % sides], tip)).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat


def underside(s, dark):
    """The underside row (tile 141): a slab under its stone band, its south face a shallow dark
    wall, and a tapering stalactite or root for each one painted below the stones."""
    th, tw = lt.TILE_H * 2, lt.TILE_W * 2
    g2 = s.ts.grid(s.pattern, 2)
    lum = lt.lum_of(s.ts, g2)
    H2, W2 = g2.shape
    r0 = 2 * th
    start = np.full(W2, r0 + th * 0.3)
    for x in range(W2):
        col = np.nonzero((g2[r0:r0 + th, x] >= 0) & (lum[r0:r0 + th, x] > 0.22))[0]
        col = col[col < th * 0.55]
        if len(col):
            start[x] = r0 + col.max() + 1
    yy = np.arange(H2)[:, None]
    band = (yy >= r0) & (yy < start[None, :]) & (g2 >= 0)
    bm = bmesh.new()
    lt.mask_slab(bm, band, lt.Frame(s.pattern, 2), UNDER_FACE_BOTTOM, 0.0, dark, dark)
    lt.dissolve_coplanar(bm)
    s._merge(bm)

    hang = (yy >= start[None, :]) & (yy < r0 + th) & (g2 >= 0) & (lum >= 0.12)
    frame = lt.Frame(s.pattern, 2)
    sb = bmesh.new()
    n = 0
    for ys, xs in lt.components(hang):
        if len(ys) < 3:
            continue
        cx = xs.mean() + 0.5
        w = max(1.2, (xs.max() - xs.min() + 1) / 2)
        xi = int(min(W2 - 1, max(0, round(cx - 0.5))))
        top, bot = start[xi], ys.max() + 1
        if bot - top < 3:
            continue
        span = r0 + th - start.min()

        def drop(y):
            return -SPIKE_DROP * np.clip((y - top) / span, 0, 1) ** 0.8

        zt, zb = -0.06, max(SPIKE_MAX, drop(bot) - 0.08)
        a = (frame.x(cx), frame.y(top - 1.0), zt)
        b = (frame.x(cx), frame.y(bot), zb)
        idx = s.ts.grid(s.pattern, 2)[ys, xs]
        col = lt.dominant(idx, s.ts.lum, quantile=0.5)
        spike(sb, a, b, w * lt.PX / 2 * 1.6, s.pal(col, roughness=0.85) if col is not None else dark)
        n += 1
    bmesh.ops.recalc_face_normals(sb, faces=sb.faces)
    s._merge(sb, smooth=True)
    return n


def build():
    s = tb.Structure("bridge")
    W = s.W
    rows = np.arange(s.H)[:, None] * np.ones((1, W), int)
    band = lambda y0, y1: (rows >= y0) & (rows < y1)  # noqa: E731
    walk = s.cells_mask(tb.WALK) & s.footprint

    # The deck: the maze plate, flat at DECK, its light lines raised as ridges.
    s.set_region(walk, DECK, s.m("walk"))
    light = walk & band(GROOVE[1], FOOT[0]) & (s.grid >= 6)
    s.set_region(light, RIDGE_Z, s.m(6, metallic=0.5, roughness=0.45))
    # The shadow groove under the curb.
    s.set_region(walk & band(*GROOVE), GROOVE_Z, s.m("walk_dark"))
    # Curb and foot plates, segmented per tile with a 1 px seam at deck height.
    cols = np.arange(W)[None, :] * np.ones((s.H, 1), int)
    seam = (cols % SEAM_EVERY) == 0
    s.set_region(walk & band(*CURB) & ~seam, CURB_Z, s.m("rail"))
    s.set_region(walk & band(*CURB) & seam, DECK, s.m("walk_dark"))
    s.set_region(walk & band(*FOOT) & ~seam, FOOT_Z, s.m("rail"))
    s.set_region(walk & band(*FOOT) & seam, DECK, s.m("walk_dark"))

    # Rivets on the plates, two per tile on the curb and the foot.
    rail = s.m("metal")
    for c in range(15):
        for off in (6, 18):
            s.dome(c * 24 + off, 29.0, 0.9, 0.9, CURB_Z - 0.005, 0.02, rail, sides=6, rings=1)
            s.dome(c * 24 + off, 54.5, 0.9, 0.9, FOOT_Z - 0.005, 0.02, rail, sides=6, rings=1)

    # The rim's slab (tile 121), dark between the stones, as the per-tile models.
    rim_cells = [(0, c) for c in range(15) if s.pattern[0][c] >= 0]
    s.rock(cells=rim_cells, boulders=False)
    dark = s.pal(2, roughness=0.9)
    grey = s.m("rock", roughness=0.85)
    tans = {}

    def tan_rim(idx, lum):
        c = lt.dominant(idx, s.ts.lum, quantile=0.5)
        key = c if c is not None else tb.PAL_T["tan"]
        if key not in tans:
            tans[key] = s.pal(key, roughness=0.75)
        return tans[key]

    tan_under = s.pal(21, roughness=0.75)
    built = stones(s, grey, tan_rim, tan_under)
    n_spikes = underside(s, dark)
    print(f"bridge: {len(built)} stones (tan shades {sorted(tans)}), {n_spikes} stalactites")

    objects = s.objects(deck_bm=s.terrace(bottom=SLAB_BOTTOM))
    s.check(objects)
    s.export(objects)


build()
