r"""ASTEROID?'s square bunker (map 1-3's ground, shapesz.dat; 6 x 6 tiles, five on the map).

What it is (from the art and the game): a gun pit on a paved station platform. The platform is the
base complex's (lib_l1kit: rubble bed, mortar deck, kerb comb, basket-weave paving, a chain of
craggy rim stones). In the middle a raised square collar: a paved glacis sloping up on all four
sides (the tiles' bevel ring 415-419 and the dark front band 399, whose light and dark bands are
the slopes' lighting, not paint), a machined steel coping along its crest, angle-iron ribs on the
four hips, and inside it a recessed pad holding the bunker's blasted hatch (318 319 / 328 329:
k.blasted_hatch over k.cavity). The game draws a ground enemy (newshp turret) over the four hatch
cells at 0.45: everything over them stays under ENEMY_MAX (0.38); the collar's crest stands
outside them, so the turret sits in its pit.

    section through the collar (z in units; 1 unit = 12 px):

        coping 0.75 ___
      glacis   ___/   \  inner lining
    paving ___/        \____ pad paving / hatch frame (enemy cells)
    0.345     outer foot    deck 0.30, bed 0.14, slab bottom -0.04 (closed)

AO/roughness bake only (bake_model, ground occluder at z 0, D86/D141); no concept projection; no
outline shell (tile models draw none, D141).

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/l1bld_bunker.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_bunker.py -- [--no-bake] [--preview <dir>]
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402
import lib_l1kit as kit  # noqa: E402
import lib_tiles as lt  # noqa: E402

TW, TH = lt.TILE_W, lt.TILE_H

# ---- the art, read off the tiles (pattern px, x0 y0 x1 y1) ----
HATCH = (52, 56, 94, 106)  # the blasted hatch's frame (as the base complex: cell + (4, 0) .. (46, 50))
COLLAR_FOOT = (27, 35, 118, 137)  # where the bevel bands start (light N / W, dark E / S)
COLLAR_RIDGE = (46, 49, 100, 114)  # the crest line (the bands end; the inner shadow starts)
PIT = (48, 56, 96, 112)  # the pad inside the collar = the four enemy cells
CREST_W = 1.6  # px: the flat crest inside the ridge line (under the coping)

# ---- heights ----
Z_FOOT = kit.MORTAR_TOP  # the glacis starts on the paving's mortar plate (bricks 0.008 above)
Z_RIDGE = 0.72  # the glacis' crest
Z_COPING = 0.75  # the coping's top (outside the enemy cells; under TALL_MAX)
Z_PAD = kit.MORTAR_TOP
BRICK = kit.PLATE_TOP - kit.MORTAR_TOP  # bricks stand this much over the mortar

PAL_COPING = 6  # the crest ring's trimmed median (its bright line is sheen)
#                 measured: crest ring 6, inner faces 6, hips 5
PAL_LINING = 6  # the pit's inner faces (trimmed median 6; their shadow is lighting)
PAL_RIB = 5  # the hip lines' trimmed median


def boxloop(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def glacis_z(x, y):
    """The collar's surface height at pattern px (x, y): planar trapezoid facets with straight hips
    from COLLAR_FOOT (Z_FOOT) up to COLLAR_RIDGE (Z_RIDGE)."""
    fx0, fy0, fx1, fy1 = COLLAR_FOOT
    rx0, ry0, rx1, ry1 = COLLAR_RIDGE
    t = min((x - fx0) / (rx0 - fx0), (y - fy0) / (ry0 - fy0), (fx1 - x) / (fx1 - rx1), (fy1 - y) / (fy1 - ry1))
    t = max(0.0, min(1.0, t))
    return Z_FOOT + (Z_RIDGE - Z_FOOT) * t


def collar(b, k):
    g, m = k.g, k.mat
    M = b.m
    coping = M(PAL_COPING, roughness=0.42, metallic=0.55)
    lining = M(PAL_LINING, roughness=0.6, metallic=0.35)
    rib = M(PAL_RIB, roughness=0.45, metallic=0.55)
    fx0, fy0, fx1, fy1 = COLLAR_FOOT
    rx0, ry0, rx1, ry1 = COLLAR_RIDGE
    foot = g.outer(boxloop(*COLLAR_FOOT))
    ridge = g.outer(boxloop(*COLLAR_RIDGE))
    # outer skirt (deck up to the mortar plate) and the four glacis facets (mortar; bricks on them)
    g.walls(foot, foot, kit.DECK_TOP - 0.005, Z_FOOT, m["mortar"])
    g.walls(foot, ridge, Z_FOOT, Z_RIDGE, m["mortar"])
    # flat crest, then the pit's lining down to the pad, and a skirt from the deck up to the pad
    crest_in = (rx0 + CREST_W, ry0 + CREST_W, rx1 - CREST_W, ry1 - CREST_W)
    ci = g.hole(boxloop(*crest_in))
    g.cap([ridge, ci], Z_RIDGE, m["mortar"])
    pit = g.hole(boxloop(*PIT))
    g.walls(pit, ci, Z_PAD, Z_RIDGE, lining)
    g.walls(pit, pit, kit.DECK_TOP - 0.005, Z_PAD, lining)

    # the coping: a machined steel ring over the crest, chamfered both edges, closed underside
    co, ci2 = kit.rbox(rx0 - 0.9, ry0 - 0.9, rx1 + 0.9, ry1 + 0.9, 1.2, 2), kit.rbox(*crest_in, 0.6, 1)
    g.prism(co, [ci2], Z_RIDGE - 0.035, Z_COPING, coping, chamfer=0.7, drop=0.014)
    # bolt heads along the coping (every ~9 px), and its four corner plates
    for (ax, ay), (bx, by) in zip(boxloop(rx0, ry0, rx1, ry1), boxloop(rx0, ry0, rx1, ry1)[1:] + boxloop(rx0, ry0, rx1, ry1)[:1]):
        L = math.dist((ax, ay), (bx, by))
        n = max(2, int(round(L / 9)))
        for i in range(1, n):
            t = i / n
            px, py = ax + (bx - ax) * t, ay + (by - ay) * t
            # sit them on the coping's centre line
            px += (0.0 if ax != bx else (CREST_W / 2 - 0.9 / 2) * (1 if ax == rx0 else -1))
            py += (0.0 if ay != by else (CREST_W / 2 - 0.9 / 2) * (1 if ay == ry0 else -1))
            g.prism(kit.ell(px, py, 0.55, 0.55, 6), [], Z_COPING - 0.004, Z_COPING + 0.008, rib, bottom=False)
    for cx, cy, sx, sy in ((rx0, ry0, 1, 1), (rx1, ry0, -1, 1), (rx1, ry1, -1, -1), (rx0, ry1, 1, -1)):
        x0_, x1_ = sorted((cx - sx * 0.9, cx + sx * CREST_W))
        y0_, y1_ = sorted((cy - sy * 0.9, cy + sy * CREST_W))
        g.prism(kit.rbox(x0_, y0_, x1_, y1_, 0.6, 1), [], Z_COPING - 0.004, Z_COPING + 0.010, rib, chamfer=0.4, drop=0.006, bottom=False)

    # angle-iron ribs on the four hips (foot corner -> ridge corner), proud of the glacis
    for (ax, ay), (bx, by) in zip(boxloop(*COLLAR_FOOT), boxloop(*COLLAR_RIDGE)):
        L = math.dist((ax, ay), (bx, by))
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        w = 0.7
        segs = 6
        top, bot = [], []
        for i in range(segs + 1):
            t = i / segs
            # stop short of the coping and of the foot
            s_ = 1.0 + t * (L - 2.2)
            px, py = ax + ux * s_, ay + uy * s_
            z = glacis_z(px, py)
            row_t, row_b = [], []
            for side in (-1, 1):
                qx, qy = px + nx * w * side, py + ny * w * side
                zq = glacis_z(qx, qy)
                row_t.append(g.v(qx, qy, max(z, zq) + 0.018))
                row_b.append(g.v(qx, qy, min(z, zq) - 0.01))
            top.append(row_t)
            bot.append(row_b)
        for i in range(segs):
            a0, a1 = top[i]
            b0, b1 = top[i + 1]
            g.face((a0, b0, b1, a1), rib)
            # sides
            c0, c1 = bot[i]
            d0, d1 = bot[i + 1]
            g.face((c0, d0, b0, a0), rib)
            g.face((a1, b1, d1, c1), rib)
        # end caps
        g.face((bot[0][0], top[0][0], top[0][1], bot[0][1]), rib)
        g.face((bot[-1][1], top[-1][1], top[-1][0], bot[-1][0]), rib)
        # a foot plate where the rib meets the paving
        g.prism(kit.ell(ax + ux * 1.4, ay + uy * 1.4, 1.5, 1.5, 8), [], Z_FOOT, kit.PLATE_TOP + 0.016, rib, chamfer=0.4, drop=0.006, bottom=False)


def glacis_bricks(b, k):
    """The basket weave carried up the glacis (the art paints it across the bevel bands): the
    paving's WEAVE bricks over COLLAR_FOOT minus COLLAR_RIDGE, each run split every px so it
    follows the facets (hips included), BRICK over the mortar."""
    g = k.g
    zone = k.box(*COLLAR_FOOT) & ~k.box(*COLLAR_RIDGE)
    # keep clear of the hip ribs
    fx0, fy0, fx1, fy1 = COLLAR_FOOT
    rx0, ry0, rx1, ry1 = COLLAR_RIDGE
    yy, xx = np.mgrid[0:b.H, 0:b.W] + 0.5
    for (ax, ay), (bx, by) in zip(boxloop(*COLLAR_FOOT), boxloop(*COLLAR_RIDGE)):
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        d = np.abs((xx - ax) * uy - (yy - ay) * ux)
        s = (xx - ax) * ux + (yy - ay) * uy
        zone &= ~((d < 1.6) & (s > -1) & (s < L + 1))
    n = 0
    for r in range(b.H // TH):
        for c in range(b.W // TW):
            x0, y0 = c * TW, r * TH
            if not zone[y0:y0 + TH, x0:x0 + TW].any():
                continue
            for bx0, by0, bx1, by1 in kit.WEAVE:
                X0, Y0, X1, Y1 = x0 + bx0, y0 + by0, x0 + bx1, y0 + by1
                mm = zone[Y0:Y1, X0:X1]
                horiz = (X1 - X0) > (Y1 - Y0)
                full = list(mm.all(axis=0) if horiz else mm.all(axis=1)) + [False]
                start = None
                for kk, ok in enumerate(full):
                    if ok and start is None:
                        start = kk
                    elif not ok and start is not None:
                        a_, b_ = start, kk
                        start = None
                        if b_ - a_ < 2:
                            continue
                        e0 = 0.05 if a_ == 0 else 0.5
                        e1 = 0.05 if b_ == len(full) - 1 else 0.5
                        if horiz:
                            ts = [X0 + a_ + e0] + [float(X0 + q) for q in range(a_ + 1, b_)] + [X0 + b_ - e1]
                            ya, yb = Y0 + 0.05, Y1 - 0.05
                            pts = [((t, yb), (t, ya)) for t in ts]
                        else:
                            ts = [Y0 + a_ + e0] + [float(Y0 + q) for q in range(a_ + 1, b_)] + [Y0 + b_ - e1]
                            xa, xb = X0 + 0.05, X1 - 0.05
                            pts = [((xa, t), (xb, t)) for t in ts]
                        rows = [[g.v(px, py, glacis_z(px, py) + BRICK) for px, py in pair] for pair in pts]
                        for i in range(len(rows) - 1):
                            p0, p1 = rows[i]
                            q0, q1 = rows[i + 1]
                            # winding: up-facing in world (pattern y down)
                            f = g.face((p0, q0, q1, p1), k.mat["pave"])
                            if f is not None:
                                f.normal_update()
                                if f.normal.z < 0:
                                    f.normal_flip()
                        n += 1
    return n


def build(bake=True, preview=None):
    lb.clear_scene()
    b = lb.Building("bunker")
    k = kit.Kit(b)
    fp = b.footprint
    cav = k.cavity(*HATCH)
    k.bed(fp & ~cav)
    dm = k.deck_mask(fp, cut=cav)
    k.deck(dm)
    collar_m = k.box(*COLLAR_FOOT)
    k.rock_layout(fp, dm, exclude=kit.dil4(collar_m, 2))
    k.kerb(dm, no_post=kit.dil4(collar_m, 3) | kit.dil4(cav, 3))
    chan = k.channels(fp)
    pad = k.box(*PIT) & ~k.box(*HATCH)
    zone = kit.ero_disk(dm, kit.KERB_W) & ~chan & (~collar_m | pad)
    k.paving(zone)
    k.rocks()
    collar(b, k)
    nb = glacis_bricks(b, k)
    print(f"glacis bricks: {nb}")
    k.blasted_hatch(*HATCH, red=b.masks()["red"])
    k.no_needles()
    objects = k.objects()

    b.finish(objects, fp, bake=bake, preview=preview)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
