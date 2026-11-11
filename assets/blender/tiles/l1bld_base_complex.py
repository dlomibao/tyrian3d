r"""The ASTEROID? (map 1-3) base complex (shapesz.dat, 39 x 13 tiles), hard-surface (D65, D141), after
the blueprint: cross-sections first, then the parts.

Engineering read of the tile art (312 x 1092 px, 13 x 39 cells; the art wins on outline, feature
placement and colours):

  section through the rim, outside -> in (z in units, 1 unit = 12 px, z = 0 the HD ground):

      stones 0.36..0.47 (<= 0.374 on enemy cells)     kerb posts ~0.366   bricks 0.345   dirt ~0.306
        __    __    __                                     ||  ||  ||    _/\_/\_/\_    ~~~~~~~~~
   ____/  \__/  \__/  \_ bed top 0.14 (rubble, pal 2) _____||__||__||___|seams 0.318|__|        |_ deck 0.30
  /  talus chamfer                                                                       (pal 3)
 /_____________________________________________________________ slab bottom -0.04 (plain, closed)

- foundation bed: the painted footprint (pits, the yard, the fork's slots are holes) as one closed
  prism, its outer edge a talus chamfer, top in the rubble colour the rocks stand in;
- rim rocks: one chain of craggy, angular stones (8-11 px across) with small stones in its gaps,
  flat-shaded (an irregular 5-8 sided foot, a tilted shoulder ring, a crown ring, an off-centre
  peak), sunk into the dark bed, which shows in the crevices round each stone as the art's
  near-black gaps; each facet in the kit's ramp by its face to the sun (3 in shadow .. 8 lit,
  round the band's median 5: lib_l1kit.facet_index, D148); kept under the enemies on enemy cells;
- kerb: the art's dashed comb of light stubs inside the rocks, as separate closed posts every 4 px,
  deduplicated across all outlines (none closer than 3.6 px), kept clear of the stones, each a
  little different in size, lean and height (lib_l1kit.Kit.kerb);
- paving: the art's basket weave (2 x 2 alternating units of three bricks per cell, lib_l1kit.WEAVE)
  as bricks 0.027 proud of a groove floor in the seams' colour, their long sides bevelled
  (lib_l1kit.Kit.paving / brick, D148, D150);
- channels: the kit's dirt (D148): a soft, jittered ground of the art's dark earth (3) with its rust
  mud (164, 163, 21 clods) winding through it, pebbles on the earth (lib_l1kit.Kit.dirt);
- the lights (338/339/347: domed dark-red lenses, faintly lit), the sensor pods (384), the round hatch (305-316), the two blasted
  hatches (318-329) and the turret block (298-309) as machined parts, each region in the art's
  own palette index (trimmed median of its pixels; table in blueprint.json "regions").

Only AO/roughness from the model's own bake (Building.bake_model, ground=0.0 occluder, D86, with the
kit's worn finish lib_l1kit.GRIT: deeper occlusion, edge sheen, a grime mottle, D148); no
concept projection ("bake": "model" in textures/shapesz-l1bld-base-complex/maps.json). No D51 outline shell
(tile models draw no ink outline: structureInstances.ts, D8, D141). Exported through Building.export (the
tile contract: model l1bld-base-complex, layer 0, the pattern, default keepTiles / minRows).

    tools/build-models.sh -j 2 assets/blender/tiles/l1bld_base_complex.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_base_complex.py -- [--no-bake] [--preview dir]
"""

import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_l1bld as lb  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_sockets as ls  # noqa: E402
import lib_tiles as lt  # noqa: E402

TW, TH = lt.TILE_W, lt.TILE_H

# ---- heights (section above) ----
ENEMY_MAX, RIM_MAX = lb.ENEMY_MAX, lb.RIM_MAX
BOTTOM = -0.04
BED_TOP = 0.14  # low, so the boulders show a real dome above it (the deck's walls hide behind the kerb)
DECK_TOP = 0.300
CAV_FLOOR = 0.12  # the blasted hatches' cavity floor
ROCK_BAND, KERB_W = 13, 4
OPEN = [(120, 0, 192, 21), (300, 31 * 28, 312, 39 * 28)]  # platform runs on past the pattern (top: the junction's stem): no rim
# The join with the pipe junction (l1bld_pipe_junction.py, whose stem ends in these cells): above
# JOIN_Y in cells (0, 5)-(0, 7) the stem's rock, brick walls and channel are the junction's (it builds
# through its pattern's row 10, py 280..280 + JOIN_Y); this model starts at JOIN_Y there, its deck and
# the kerb comb (not across the channel) on that line, as the art's comb along the bottom of 363 / 364.
JOIN_Y = 19  # the row-0 deck's top edge (the rim band ends there all along the row)
JOIN_BOX = (120, 0, 192, JOIN_Y)

# ---- the art's palette index per region (trimmed medians, blueprint.json "regions") ----
# The shared parts' (bed 2, mortar 3, kerb 7, bricks 6, the channels' dirt, the rim rocks' facet ramp
# round the band's median 5: counts with the bed / gap px left out 3:10481 4:8133 5:7007 6:5642
# 7:4674 8:3749) are lib_l1kit's PAL_* and facet_index (D148); this building's own parts:
PAL_BED, PAL_MORTAR = 2, 3
PAL_LENS, PAL_LENS_FAT, PAL_HOUSING, PAL_POD, PAL_EYE = 113, 114, 8, 8, 113  # lens medians: capsules 113, big lights 114
PAL_RH_DISC, PAL_RH_SPOKE, PAL_RH_CLAMP, PAL_FRAME = 1, 4, 163, 9
PAL_RH_SEAT = 3  # the round hatch is dark all through in the art (annulus medians 1 / 1 / 3 / 5 from the centre out)
PAL_LEAF, PAL_PIT, PAL_EMBER = 7, 1, 113
PAL_TURRET, PAL_SOCKET, PAL_VENT, PAL_TURRET_HI = 163, 1, 113, 165
PAL_TUR_BAR, PAL_TUR_FRAME = 161, 9  # the left bar near-black brown, striped pal 1; the socket's light grey frame

# ---- features (pattern px, from the tiles) ----
CAPS = [((194, 114, 211, 120), 'x'), ((194, 123, 211, 129), 'x'), ((194, 132, 211, 138), 'x'),
        ((98, 142, 115, 148), 'x'), ((98, 151, 115, 157), 'x'), ((98, 160, 115, 166), 'x'),
        ((145, 173, 150, 190), 'y'), ((153, 173, 158, 190), 'y'), ((161, 173, 166, 190), 'y')]
FAT = [(100, 564, 114, 583), (124, 564, 138, 583), (196, 564, 210, 583), (220, 564, 234, 583)]
PODS = [(155.5, 569.5), (179.5, 569.5)]
RHATCH = (165.5, 475.0, 20.0, 24.5)
HATCH = [(124, 840, 166, 890), (196, 840, 238, 890)]
TURRET = (246, 588, 288, 642)

# Channel strips (lib_l1kit.ARMS / STUB / CH_*): centre (CH_X, CH_Y) in the cell, half widths as the
# art's 389 (x 3.5..18.5) and 379 (y 4.5..22.5); the pipe junction's stem channel is the same strip,
# so the two meet edge to edge. The paving's basket weave is lib_l1kit.WEAVE.
from lib_l1kit import CH_HX, CH_HY, CH_X, CH_Y  # noqa: E402


# Pixel-mask helpers, Geo (one oriented bmesh), rbox, ell: lib_l1kit.py (the ASTEROID? station kit,
# whose part builders are copies of this script's inline ones, for the other platforms).
from lib_l1kit import Geo, dil4, dil_disk, ell, ero_disk, gauss, maxf, rbox, regions, shift  # noqa: E402,F401


# ======================================================================= build

def build(bake=True):
    s = lb.Building("base-complex")
    H, W = s.H, s.W
    grid, fp = s.grid, s.footprint
    red = s.masks()["red"]
    dep = lb.depth(fp)
    enemy = s.enemy_mask
    g = Geo(s)
    M = lambda i, **kw: s.m(i, **kw)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5

    def box(x0, y0, x1, y1):
        m = np.zeros((H, W), bool)
        m[max(0, int(y0)):int(y1), max(0, int(x0)):int(x1)] = True
        return m

    openm = np.zeros((H, W), bool)
    for b in OPEN:
        openm |= box(*b)
    join = box(*JOIN_BOX)  # the pipe junction's (see JOIN_Y)
    fpg = fp & ~join  # what this model builds on

    feat = np.zeros((H, W), bool)
    for (x0, y0, x1, y1), _ in CAPS:
        feat |= box(x0 - 3, y0 - 3, x1 + 4, y1 + 4)
    for (x0, y0, x1, y1) in FAT:
        feat |= box(x0 - 3, y0 - 3, x1 + 4, y1 + 4)
    for (px, py) in PODS:
        feat |= box(px - 9, py - 10, px + 9, py + 10)
    cx, cy, rx, ry = RHATCH
    feat |= ((xx - cx) / (rx + 2.5)) ** 2 + ((yy - cy) / (ry + 2.5)) ** 2 <= 1
    for b in HATCH:
        feat |= box(b[0] - 1, b[1] - 1, b[2] + 1, b[3] + 1)
    feat |= box(*TURRET)

    # materials (surface finish per part: satin metal, rough rubble and stone)
    m_bed = M(PAL_BED, roughness=0.95)
    m_mortar = M(PAL_MORTAR, roughness=0.9)
    m_house = M(PAL_HOUSING, roughness=0.4, metallic=0.55)
    m_lens = M(PAL_LENS, roughness=0.22, metallic=0.1, emission_strength=0.45)  # a dark red glass that glows a little
    m_lens_fat = M(PAL_LENS_FAT, roughness=0.22, metallic=0.1, emission_strength=0.45)
    m_pod = M(PAL_POD, roughness=0.4, metallic=0.55)
    m_sock = M(PAL_SOCKET, roughness=0.8)
    m_eye = M(PAL_EYE, roughness=0.3, emission_strength=1.0)
    m_frame = M(PAL_FRAME, roughness=0.4, metallic=0.5)
    m_disc = M(PAL_RH_DISC, roughness=0.6, metallic=0.3)
    m_spoke = M(PAL_RH_SPOKE, roughness=0.45, metallic=0.5)
    m_clamp = M(PAL_RH_CLAMP, roughness=0.5, metallic=0.4)
    m_leaf = M(PAL_LEAF, roughness=0.5, metallic=0.45)
    m_pit = M(PAL_PIT, roughness=0.95)
    m_ember = M(PAL_EMBER, roughness=0.4, emission_strength=1.5)
    m_tur = M(PAL_TURRET, roughness=0.5, metallic=0.4)
    m_vent = M(PAL_VENT, roughness=0.4, emission_strength=1.8)

    # 1. Foundation bed: the painted footprint, holes cut; talus chamfer at the outer edge.
    # the blasted hatches' cavities go down through the bed and the deck (the frames line them)
    cav = np.zeros((H, W), bool)
    for (x0, y0, x1, y1) in HATCH:
        cav |= box(x0 + 3, y0 + 4.5, x1 - 3, y1 - 3)
    for outer, holes in regions(fpg & ~cav, tol=1.9):
        g.prism(outer, holes, BOTTOM, BED_TOP, m_bed, chamfer=1.5, drop=0.10)

    # 2. Deck (the joint colour) inside the rock band.
    deck_mask = fp & (dep > ROCK_BAND - 1)
    deck_mask = dil_disk(ero_disk(deck_mask, 4), 4)
    deck_mask = ero_disk(dil_disk(deck_mask, 4), 4) & fp & ~cav
    # at the join the deck runs straight across from the junction's stem end (JOIN_Y) down
    deck_mask = (deck_mask | (fp & box(JOIN_BOX[0], JOIN_Y, JOIN_BOX[2], JOIN_Y + 16))) & ~join
    deck_loops = regions(deck_mask, tol=1.6, min_px=30)
    for outer, holes in deck_loops:
        o = g.outer(outer)
        hs = [g.hole(h) for h in holes]
        g.walls(o, o, BED_TOP - 0.02, DECK_TOP, m_mortar)
        for h in hs:
            g.walls(h, h, BED_TOP - 0.02, DECK_TOP, m_mortar)
        g.cap([o] + hs, DECK_TOP, m_mortar)
    # the station kit's parts (lib_l1kit, D148) on this model's mesh: dirt, paving, rocks
    kt = kit.Kit(s)
    kt.g = g

    # Rim-rock layout (placed now, built in step 6, so the kerb can keep clear of the stones): as the
    #    art paints them, one chain of angular stones (about 9-10 px across) down the middle of the
    #    13 px band, small stones in the chain's gaps, each sized to leave a crevice of the dark bed
    #    (pal 2) round it, as the art's near-black gaps between its stones.
    bandm = fpg & (dep <= ROCK_BAND) & ~dil4(openm, 4)
    rng = np.random.default_rng(13)
    taken = []  # (x, y, rad, kind)
    block = np.zeros((H, W), bool)
    cover = np.zeros((H, W), bool)

    def stamp(mask, x, y, r):
        ri = int(math.ceil(r))
        ya, yb, xa, xb = max(0, int(y) - ri), min(H, int(y) + ri + 1), max(0, int(x) - ri), min(W, int(x) + ri + 1)
        mask[ya:yb, xa:xb] |= (yy[ya:yb, xa:xb] - y) ** 2 + (xx[ya:yb, xa:xb] - x) ** 2 <= r * r

    # the chain: centres 5-7 px in, about 9-10 px apart
    ys, xs = np.nonzero(bandm & (dep >= 5) & (dep <= 7))
    for k in rng.permutation(len(ys)):
        if block[ys[k], xs[k]]:
            continue
        x, y = xs[k] + 0.5, ys[k] + 0.5
        taken.append([x, y, 0.0, 0])
        stamp(block, x, y, 9.0)
    ta = np.array([(t[0], t[1]) for t in taken])
    for t in taken:
        d = np.sort(np.hypot(ta[:, 0] - t[0], ta[:, 1] - t[1]))[1:3]
        t[2] = float(np.clip(0.45 * d.mean() * (0.92 + 0.16 * rng.random()), 3.8, 5.8))  # < half the spacing: a crevice between
        stamp(cover, t[0], t[1], t[2] * 1.05)
    # the small stones: wherever the band still shows bed 2-11 px in, clear of the chain
    block = dil_disk(cover, 1)
    ys, xs = np.nonzero(bandm & (dep >= 2) & (dep <= 11) & ~dil_disk(cover, 2))
    for k in rng.permutation(len(ys)):
        if block[ys[k], xs[k]]:
            continue
        x, y = xs[k] + 0.5, ys[k] + 0.5
        rad = 2.0 + 1.1 * rng.random()
        taken.append([x, y, rad, 1])
        stamp(block, x, y, rad + 2.4)
    print(f"rocks: {sum(1 for t in taken if t[3] == 0)} chain, {sum(1 for t in taken if t[3] == 1)} small")

    def inside(m, x, y):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        return 0 <= xi < W and 0 <= yi < H and bool(m[yi, xi])

    # each stone's foot: an irregular 5-8 sided polygon (pattern px), every corner pulled in until it
    #    lies on the footprint and off the deck, so no stone reaches past the art's outline or into the
    #    kerb's row of posts
    feet = []
    for (x, y, rad, kind) in taken:
        big = kind == 0
        n = int(rng.integers(6, 9)) if big else int(rng.integers(5, 7))
        rot = rng.random() * math.tau
        angs = [rot + math.tau * (i + 0.55 * (rng.random() - 0.5)) / n for i in range(n)]
        fr = 0.82 + 0.36 * rng.random(n)  # uneven, not smoothed: angular corners
        ex, ey = 0.88 + 0.24 * rng.random(), 0.88 + 0.24 * rng.random()
        pts = []
        for a, f in zip(angs, fr):
            ca, sa = math.cos(a), math.sin(a)
            r = rad * f * (ex * abs(ca) + ey * abs(sa))
            while r > 0.35 * rad and (not inside(fp, x + r * ca, y + r * sa) or inside(deck_mask, x + r * ca, y + r * sa)):
                r *= 0.9
            pts.append((a, r))
        feet.append(pts)

    # 3. Kerb: the art's dashed comb of short light stubs along the paving's edge, as separate closed
    #    posts every KERB_STEP px round every deck outline (the dark mortar deck shows between them);
    #    none where the platform runs on past the pattern, nor at the hatch frames. Candidates from all
    #    outlines are deduplicated together (no two posts closer than KERB_MIN px, so none meet where
    #    outlines turn or touch), and a post a rim stone would reach is dropped.
    cav_near = dil4(cav, 3)
    # no kerb across the stem's channel where it comes down from the pipe junction
    ccx0 = JOIN_BOX[0] + TW + CH_X
    mouth = box(ccx0 - CH_HX - 1, 0, ccx0 + CH_HX + 1, JOIN_Y + 8)
    no_post = dil4(openm & ~box(*OPEN[0]), 3) | cav_near | feat | mouth
    kt.stones = [[x, y, rad, kind, pts] for (x, y, rad, kind), pts in zip(taken, feet)]
    nposts = kt.kerb(deck_mask, no_post=no_post)  # the kit's worn, jittered posts (D148)

    # 4. Channels: the channel tiles' strips (arms meeting at the centre square, clipped to the
    #    footprint), floored with the kit's dirt (D148: the art's dark earth and rust mud, not a grating).
    chan = kt.channels(fpg)

    # 5. Paving: the art's basket weave as bevelled bricks 0.027 proud of a groove floor in the seams'
    #    colour (the art's 1 px seams are the grooves); bricks the kerb, a channel or a feature cuts
    #    are trimmed along their length, slivers dropped.
    zone = ero_disk(deck_mask, KERB_W) & ~chan & ~feat
    nplates = kt.paving(zone)  # bevelled, worn bricks on the seams' groove floor (lib_l1kit, D148)

    # Where the platform runs on past the pattern (OPEN), every edge is cut square at the pattern's
    #    border: no chamfer or frustum slope there to catch the light where the next piece joins.
    def snap_open():
        ux = s.x(1) - s.x(0)
        uy = s.y(1) - s.y(0)
        for v in g.bm.verts:
            px, py = (v.co.x - s.x(0)) / ux, (v.co.y - s.y(0)) / uy
            if JOIN_BOX[0] - 2 <= px <= JOIN_BOX[2] + 2 and abs(py - JOIN_Y) < 0.6:
                v.co.y = s.y(JOIN_Y)  # the join's line, straight (the junction's stem ends on it)
            if px > W - 2.0 and OPEN[1][1] - 2 <= py <= H:
                v.co.x = s.x(W)

    snap_open()

    coll = common.reset_collection("shapesz-l1bld-base-complex")

    # 6. Rim rocks (the layout above): craggy, angular stones as the art's, never smooth domes. Each a
    #    flat-shaded faceted lump (lib_l1kit.Kit.stone): an irregular 5-8 sided foot sunk just under the
    #    bed's top, a shoulder ring at uneven heights (the crown tilted), a crown ring and an off-centre
    #    peak, so its top is many flat facets that catch the light one by one; the dark bed (pal 2)
    #    shows in the crevices round it.
    kt.rocks()  # each facet in the index of its face to the sun (lib_l1kit.facet_index, D148)

    # 7. Red light capsules (338 x2, 339) and the big lights (347): a machined housing, a dark seat and
    #    a domed dark-red lens over a rounded rectangle (the art paints rounded capsules), faintly lit, under the enemies drawn over.
    m_dark = M(PAL_SOCKET, roughness=0.8)

    def pillow(poly, z0, h, mat, corner):
        """A domed lens over a rounded rectangle: rings stepping in and up (a quarter-ellipse profile), smooth."""
        o = g.outer(poly)
        prof = [(0.0, 0.0), (0.35, 0.45), (0.9, 0.78), (1.7, 0.95), (2.6, 1.0)]
        mn = min(max(p[0] for p in o) - min(p[0] for p in o), max(p[1] for p in o) - min(p[1] for p in o))
        k = min(1.0, (mn / 2 - 0.5) / 2.6, 0.9 * corner / 2.6)
        rings = [[g.v(x, y, z0 + h * t) for x, y in ([tuple(q) for q in ls.inset(o, d * k)] if d else o)] for d, t in prof]
        n = len(o)
        for lo, hi in zip(rings, rings[1:]):
            if len(hi) != n:
                break
            for i in range(n):
                j = (i + 1) % n
                g.face((lo[i], lo[j], hi[j], hi[i]), mat, smooth=True)
        g.face(rings[-1], mat, smooth=True)

    def lens_unit(x0, y0, x1, y1, fat):
        hx0, hy0, hx1, hy1 = x0 - 1.2, y0 - 1.2, x1 + 2.2, y1 + 2.2
        ztop = 0.350
        g.prism(rbox(hx0, hy0, hx1, hy1, 3.0 if fat else 2.0, 2), [], DECK_TOP - 0.005, ztop, m_house, chamfer=0.7, drop=0.012, bottom=False)
        w, h = x1 - x0 + 1, y1 - y0 + 1
        corner = 3.0 if fat else min(2.2, min(w, h) / 2 - 0.1)
        g.prism(rbox(x0 - 0.4, y0 - 0.4, x1 + 1.4, y1 + 1.4, corner + 0.4, 2), [], ztop - 0.02, ztop + 0.002, m_dark, bottom=False)
        pillow(rbox(x0, y0, x1 + 1, y1 + 1, corner, 2), ztop - 0.004, 0.030, m_lens_fat if fat else m_lens, corner)

    for (x0, y0, x1, y1), ax in CAPS:
        lens_unit(x0, y0, x1, y1, False)
    for (x0, y0, x1, y1) in FAT:
        lens_unit(x0, y0, x1, y1, True)
        cy_ = (y0 + y1 + 1) / 2
        for xs_ in (x0 - 1.0, x1 + 2.0):  # bolts on the housing's flanks
            g.prism(ell(xs_, cy_, 0.8, 0.8, 6), [], 0.345, 0.358, m_house, bottom=False)

    # 8. Sensor pods (384): a dark socket ring, a shell dome, the red eye slits as the art's.
    for (px, py) in PODS:
        g.prism(ell(px, py, 8.0, 9.0, 18), [], DECK_TOP - 0.005, 0.318, m_sock, chamfer=0.6, drop=0.006, bottom=False)
        g.dome(px - 0.5, py, 6.5, 7.5, 0.312, 0.058, m_pod, n=16, rings=4)
        g.prism(rbox(px - 2.5, py - 7, px + 2.5, py - 4.5, 0.5, 1), [], 0.345, 0.369, m_eye, bottom=False)
        g.prism(rbox(px - 5.5, py - 1, px - 3.5, py + 5, 0.5, 1), [], 0.345, 0.368, m_eye, bottom=False)

    # 9. Round hatch in the yard: seat ring, dark recessed disc, six spokes, hub, brown clamps.
    cx, cy, rx, ry = RHATCH
    g.prism(ell(cx, cy, rx + 1.5, ry + 1.5, 32), [ell(cx, cy, rx - 2.5, ry - 2.5, 32)], DECK_TOP - 0.01, 0.348, M(PAL_RH_SEAT, roughness=0.45, metallic=0.5),
            chamfer=0.7, drop=0.012, bottom=False)
    g.prism(ell(cx, cy, rx - 2.4, ry - 2.4, 32), [], DECK_TOP - 0.01, 0.322, m_disc, bottom=False)
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx
        p0, p1 = (cx + 5 * dx * rx / ry, cy + 5 * dy), (cx + (rx - 3.5) * dx, cy + (ry - 3.5) * dy)
        w = 1.1
        poly = [(p0[0] + nx * w, p0[1] + ny * w), (p1[0] + nx * w, p1[1] + ny * w), (p1[0] - nx * w, p1[1] - ny * w), (p0[0] - nx * w, p0[1] - ny * w)]
        g.prism(poly, [], 0.318, 0.338, m_spoke, chamfer=0.3, drop=0.006, bottom=False)
    g.prism(ell(cx, cy, 5.0, 5.5, 16), [], 0.318, 0.352, m_spoke, chamfer=0.8, drop=0.01, bottom=False)
    g.prism(ell(cx, cy, 2.2, 2.4, 10), [], 0.350, 0.360, m_disc, bottom=False)
    for sx in (-1, 1):
        x_ = cx + sx * (rx + 0.5)
        for y_ in ((cy - 6, cy - 0.4), (cy + 0.4, cy + 6)):  # split clamp blocks
            g.prism(rbox(x_ - 3, y_[0], x_ + 3, y_[1], 0.8, 1), [], DECK_TOP, 0.372, m_clamp, chamfer=0.6, drop=0.012, bottom=False)

    # 10. Blasted hatches: heavy frame, dark cavity, torn leaves bent down into it, embers.
    for (x0, y0, x1, y1) in HATCH:
        o = rbox(x0, y0, x1, y1, 1.5, 2)
        i_ = rbox(x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5, 1.0, 1)
        g.prism(o, [i_], CAV_FLOOR, 0.370, m_frame, chamfer=0.8, drop=0.012, bottom=False)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        g.prism(rbox(mx - 0.5, y0 + 0.6, mx + 0.5, y0 + 4.4, 0.2, 1), [], 0.362, 0.372, m_pit, bottom=False)  # top joint
        for bx_, by_ in ((x0 + 1.8, y0 + 2.5), (x1 - 1.8, y0 + 2.5), (x0 + 1.8, y1 - 1.8), (x1 - 1.8, y1 - 1.8)):
            g.prism(ell(bx_, by_, 0.7, 0.7, 6), [], 0.364, 0.378, m_frame, bottom=False)
        g.cap([g.outer(i_)], CAV_FLOOR + 0.002, m_pit)  # the cavity's floor
        # blasted leaves: each side's leaf is broken into three jagged wedge shards hinged under the
        # frame's lip, bent down into the cavity at different angles, tips torn at random lengths,
        # a few loose ones on the floor (pal 7); dark cracks between them
        ix0, iy0, ix1, iy1 = x0 + 3.5, y0 + 5, x1 - 3.5, y1 - 3.5
        sides = [((ix0 + 1, iy0 + 0.5), (ix1 - 1, iy0 + 0.5)), ((ix1 - 1, iy1 - 0.5), (ix0 + 1, iy1 - 0.5)),
                 ((ix0 + 0.5, iy1 - 1), (ix0 + 0.5, iy0 + 1)), ((ix1 - 0.5, iy0 + 1), (ix1 - 0.5, iy1 - 1))]

        def shard(P, Q, T, zh, zt, th=0.016):
            top = [g.v(P[0], P[1], zh), g.v(Q[0], Q[1], zh), g.v(T[0], T[1], zt)]
            bot = [g.v(P[0], P[1], zh - th), g.v(Q[0], Q[1], zh - th), g.v(T[0], T[1], zt - th)]
            for f in (top, bot[::-1], (top[0], bot[0], bot[1], top[1]), (top[1], bot[1], bot[2], top[2]), (top[2], bot[2], bot[0], top[0])):
                g.face(tuple(f), m_leaf)

        for si, (a, b) in enumerate(sides):
            ln = math.dist(a, b)
            ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
            inx, iny = mx - (a[0] + b[0]) / 2, my - (a[1] + b[1]) / 2
            il = math.hypot(inx, iny)
            inx, iny = inx / il, iny / il
            n3 = 3
            for k in range(n3):
                t0, t1 = k / n3 + 0.02, (k + 1) / n3 - 0.02
                P = (a[0] + ux * ln * t0, a[1] + uy * ln * t0)
                Q = (a[0] + ux * ln * t1, a[1] + uy * ln * t1)
                reach = 4.0 + 7.0 * rng.random()
                lat = (rng.random() - 0.5) * 0.5 * ln / n3
                mid = ((P[0] + Q[0]) / 2 + inx * reach + ux * lat, (P[1] + Q[1]) / 2 + iny * reach + uy * lat)
                zt = 0.31 - 0.08 * rng.random() - 0.04 * (k == 1)
                shard(P, Q, mid, 0.352, zt)
            # a lone small splinter on the floor
            fx, fy = mx + (rng.random() - 0.5) * 18, my + (rng.random() - 0.5) * 20
            ang = rng.random() * math.tau
            T3 = [(fx + r_ * math.cos(ang + k_), fy + r_ * math.sin(ang + k_)) for r_, k_ in ((3.2, 0), (2.4, 2.2), (1.8, 4.0))]
            top = [g.v(p[0], p[1], CAV_FLOOR + 0.03) for p in T3]
            bot = [g.v(p[0], p[1], CAV_FLOOR + 0.004) for p in T3]
            g.face(tuple(top), m_leaf)
            g.face(tuple(bot[::-1]), m_leaf)
            for i in range(3):
                j = (i + 1) % 3
                g.face((top[i], bot[i], bot[j], top[j]), m_leaf)
        # embers where the art paints the red in the hatch, glowing on the cavity floor
        hm = box(x0 + 4, y0 + 5, x1 - 4, y1 - 4) & red
        for outer, holes in regions(dil4(hm, 1), tol=0.7, min_px=4):
            g.prism(outer, [], CAV_FLOOR, CAV_FLOOR + 0.05, m_ember, bottom=False)

    # 11. Turret block (no enemy: stands taller): dark socket, cruciform pump housing, a pipe, vents.
    x0, y0, x1, y1 = TURRET
    # the socket: a light grey frame (pal 9, the art's) round a dark well
    m_tframe = M(PAL_TUR_FRAME, roughness=0.45, metallic=0.5)
    g.prism(rbox(x0 + 1, y0, x1 - 1, y1, 2.0, 2), [rbox(x0 + 3.5, y0 + 2.5, x1 - 3.5, y1 - 2.5, 1.0, 2)], DECK_TOP - 0.01, 0.332, m_tframe,
            chamfer=0.6, drop=0.01, bottom=False)
    g.prism(rbox(x0 + 3.4, y0 + 2.4, x1 - 3.4, y1 - 2.4, 1.0, 2), [], DECK_TOP - 0.01, 0.318, m_sock, bottom=False)
    g.prism(rbox(250, 606, 286, 626, 3.0, 2), [], 0.32, 0.50, m_tur, chamfer=1.2, drop=0.03, bottom=False)
    g.prism(rbox(260, 590, 280, 640, 3.0, 2), [], 0.32, 0.56, m_tur, chamfer=1.2, drop=0.03, bottom=False)
    m_tur_hi = M(PAL_TURRET_HI, roughness=0.45, metallic=0.4)
    g.prism(ell(270, 615, 8.5, 9.5, 20), [], 0.55, 0.61, m_tur_hi, chamfer=1.0, drop=0.02, bottom=False)
    g.prism(ell(270, 615, 5.5, 6.2, 16), [], 0.60, 0.65, m_tur, chamfer=0.8, drop=0.015, bottom=False)
    g.prism(ell(270, 615, 2.0, 2.2, 10), [], 0.64, 0.665, m_house, bottom=False)
    # the long left bar: near-black brown (pal 161) with dark lengthwise stripes (pal 1), as the art
    m_tbar = M(PAL_TUR_BAR, roughness=0.5, metallic=0.4)
    g.cyl_y(254.5, 588.5, 640.5, 3.6, 0.43, m_tbar, n=12, stripe=m_sock, stripes=(2, 4))
    for yb in (594, 634):
        g.prism(rbox(250, yb - 2, 259, yb + 2, 0.8, 1), [], 0.32, 0.43, m_tur, chamfer=0.5, drop=0.01, bottom=False)
    for yb in (606, 626):  # panel joints on the spine: a dark recessed strip
        g.prism(rbox(261, yb - 0.5, 279, yb + 0.5, 0.2, 1), [], 0.55, 0.562, m_sock, bottom=False)
    for vx0, vy0, vx1, vy1 in ((267, 598, 274, 604), (263, 628, 266, 633), (274, 628, 277, 633)):
        g.prism(rbox(vx0, vy0, vx1, vy1, 0.6, 1), [], 0.52, 0.565, m_vent, bottom=False)
    g.prism(rbox(252.0, 622, 257.0, 634, 0.6, 1), [], 0.40, 0.473, m_vent, bottom=False)

    # orient the shards (closed pieces): recalc only those faces' normals
    bm = g.bm
    leaf_faces = [f for f in bm.faces if f.material_index == m_leaf]
    bmesh.ops.recalc_face_normals(bm, faces=leaf_faces)
    bm.normal_update()

    # No needles: drop any degenerate face, and any upright face thinner than 0.2 px across that
    #    stands taller than it is wide (a sliver spike from a snapped edge or a tiny outline step).
    pxu = lt.PX
    drop_f = []
    for f in bm.faces:
        a = f.calc_area()
        L = max(e.calc_length() for e in f.edges)
        if L <= 1e-9 or a <= 1e-10:
            drop_f.append(f)
            continue
        if abs(f.normal.z) > 0.7:
            continue
        zs_ = [v.co.z for v in f.verts]
        xy = max(math.hypot(v.co.x - w.co.x, v.co.y - w.co.y) for v in f.verts for w in f.verts)
        if xy < 0.2 * pxu and (max(zs_) - min(zs_)) > xy:
            drop_f.append(f)
    bmesh.ops.delete(bm, geom=drop_f, context="FACES_ONLY")
    print(f"slivers removed: {len(drop_f)}")

    return s, g, coll, nposts, nplates, len(taken), fpg, openm


def main(bake=True, preview=None):
    s, g, coll, nposts, nplates, nrocks, fp, openm = build()
    obj = lb.mesh_object("shapesz-l1bld-base-complex-parts", g.bm, s.pal.materials, coll)
    objects = [obj]
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"plates {nplates} kerb parts {nposts} rocks {nrocks} triangles {tris}")
    per = {}
    for p_ in obj.data.polygons:
        k_ = obj.data.materials[p_.material_index].name
        per[k_] = per.get(k_, 0) + len(p_.vertices) - 2
    print("triangles per material:", sorted(per.items(), key=lambda kv: -kv[1])[:14])
    s.check(objects)
    iou = s.top_iou(objects, fp, scale=1)
    if bake:
        objects = s.bake_model(objects, size=2048, ground=0.0, grit=kit.GRIT)
    hard = objects[0]
    hard_tris = sum(len(p.vertices) - 2 for p in hard.data.polygons)
    print(f"base-complex: {hard_tris} triangles (hard), IoU {iou:.4f}")
    if preview:
        lt.preview(s.ts, objects, s.pattern, Path(preview) / "shapesz-l1bld-base-complex.png", view_px=480)
    s.export(objects, baked=bake)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
main(bake="--no-bake" not in argv, preview=lt.preview_arg())
