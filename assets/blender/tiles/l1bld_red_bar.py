r"""ASTEROID? (map 1-3) red bar: the small light platform of the ground layer (shapesz.dat,
3 x 6 tiles at rows 225-227, cols 4-9: 360 361 361 361 361 362 / 370 347 339 339 347 372 / 380 381
381 381 381 382). Ground enemies (newshs red lights) stand on the band's four cells (row 1, cols 1-4),
drawn at 0.45, so everything there stays under ENEMY_MAX 0.38. NOT D139: no cover parts.

What the art paints (the art wins on outline, feature placement and per-region palette index):
- a crenellated rim of rock round the whole platform, heaped at both ends (360/370/380, 362/372/382),
  round crowns along the top (361), pointed shards hanging off the bottom (381);
- inside it a paved deck with the kerb comb of light stubs along its edge;
- the light band across the middle: two big square red panes (347) in a dark 1 px seat (ring index 3,
  then 4), flanking a cast rack of six capsule lights (339 339: 6 x 18 px windows on an 8 px pitch,
  a bright satin web between them, ring index 8).

Built with lib_l1kit (the base complex's parts: bed, deck, rim rocks, kerb, basket-weave paving), so it
matches every other map 1-3 platform, plus its own lights:
- the capsule rack: ONE machined frame plate (rounded box, chamfered top edge) with six stadium
  windows cut through it where the art's six red capsules are (one window per red component), a dark
  seat in each, a domed dark-red glass capsule bulging just above the web, a rivet at each corner;
  one plate rather than six overlapping kit housings (the 2 px webs would z-fight);
- the two big panes: a dark gunmetal frame (the art's ring index 4) with a chamfered top, a
  near-black seat lip (index 3) and a domed fat lens (index 114), bolts on its flanks.
Heights: bed 0.14, deck 0.30, bricks 0.345, kerb 0.366, rack web 0.356, capsule glass 0.364, pane frame
0.352, pane glass 0.372; rocks <= RIM_MAX. AO/roughness from the model's own bake only (no concept
projection, "bake": "model"), no outline shell (tile models draw none: D141). Underside: the bed's
closed slab bottom at -0.04.

Run from the repo root:

    tools/build-models.sh -j 2 -p <dir> assets/blender/tiles/l1bld_red_bar.py
    blender --background --factory-startup --python assets/blender/tiles/l1bld_red_bar.py -- [--no-bake] [--preview <dir>]
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

# ---- heights (units; z = 0 the HD ground) ----
RACK_TOP = 0.356  # the capsule rack's web
CAP_SEAT = 0.326  # the dark seat inside each window
CAP_GLASS = 0.034  # capsule dome height above the seat -> 0.360 (+ rim)
PANE_FRAME_TOP = 0.352
PANE_SEAT = 0.344
PANE_GLASS = 0.028  # -> 0.372

# ---- the art's palette indices for this building's own parts (trimmed medians, measured below) ----
PAL_RACK = 8  # capsule ring (1 px round the six windows)
PAL_PANE_FRAME = 4  # second ring round the 347 panes
PAL_PANE_SEAT = 3  # first ring round the 347 panes
PAL_CAP_LENS = 113
PAL_PANE_LENS = 114


def trimmed_index(vals, lum, cut=1 / 6):
    """The art's palette index of a region: the median of its pixels, the darkest and brightest
    `cut` (shading, sheen) left out."""
    vals = np.asarray(vals)
    order = np.argsort(lum[vals], kind="stable")
    k = int(len(vals) * cut)
    keep = vals[order[k:len(vals) - k]] if len(vals) > 6 else vals
    return int(np.median(keep))


def measure(b, red_lab, fat_ids, cap_ids):
    """Per-region indices from the tiles (printed: model vs art)."""
    lum = b.ts.lum
    grid = b.grid
    red = red_lab > 0
    fat = np.isin(red_lab, fat_ids)
    caps = np.isin(red_lab, cap_ids)
    ring = lambda m, r: kit.dil4(m, r) & ~kit.dil4(m, r - 1) & ~red if r > 1 else kit.dil4(m, 1) & ~m & ~red  # noqa: E731
    out = {
        "pane lens": (trimmed_index(grid[fat], lum), PAL_PANE_LENS),
        "capsule lens": (trimmed_index(grid[caps], lum), PAL_CAP_LENS),
        "pane seat (ring 1)": (trimmed_index(grid[ring(fat, 1)], lum), PAL_PANE_SEAT),
        "pane frame (ring 2)": (trimmed_index(grid[ring(fat, 2)], lum), PAL_PANE_FRAME),
        "capsule rack (ring 1)": (trimmed_index(grid[ring(caps, 1)], lum), PAL_RACK),
    }
    return out


def stadium(x0, y0, x1, y1, n=5):
    """A capsule window over the art's red box (edges x0..x1, y0..y1): straight sides, round ends."""
    return kit.rbox(x0, y0, x1, y1, c=(x1 - x0) / 2 - 0.05, seg=n)


def build(bake=True, preview=None):
    lb.clear_scene()
    b = lb.Building("red-bar")
    k = kit.Kit(b)
    g = k.g
    fp = b.footprint
    grid = b.grid
    M = b.m

    # The art's red lights, one component each (raw ramp 7: masks()["red"] closes the 2 px webs and
    # merges the six capsules into one blob).
    red = (grid >= 0) & ((grid >> 4) == 7)
    lab = np.zeros(grid.shape, int)
    boxes = []
    for i, (ys, xs) in enumerate(lt.components(red), start=1):
        if len(ys) < 20:
            continue
        lab[ys, xs] = len(boxes) + 1
        boxes.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    fat_ids = [i + 1 for i, (x0, y0, x1, y1) in enumerate(boxes) if x1 - x0 > 10]
    cap_ids = [i + 1 for i in range(len(boxes)) if i + 1 not in fat_ids]
    fats = [boxes[i - 1] for i in fat_ids]
    caps = sorted(boxes[i - 1] for i in cap_ids)
    print(f"red bar lights: {len(fats)} panes {fats}, {len(caps)} capsules {caps}")
    meas = measure(b, lab, fat_ids, cap_ids)
    for kname, (art, model) in meas.items():
        print(f"REGION {kname}: art {art} model {model}")

    rack = (min(c[0] for c in caps) - 1.6, min(c[1] for c in caps) - 1.6,
            max(c[2] for c in caps) + 1.6, max(c[3] for c in caps) + 1.6)
    frames = [(x0 - 1.6, y0 - 1.6, x1 + 1.6, y1 + 1.6) for (x0, y0, x1, y1) in fats]

    # ---- the platform (kit, as the base complex) ----
    k.bed(fp)
    dm = k.deck_mask(fp)
    k.deck(dm)
    parts = np.zeros_like(fp)
    for (x0, y0, x1, y1) in [rack] + frames:
        parts |= k.box(math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1))
    k.rock_layout(fp, dm)
    k.kerb(dm, no_post=kit.dil4(parts, 3))
    chan = k.channels(fp)
    zone = kit.ero_disk(dm, kit.KERB_W) & ~chan & ~parts
    print(f"bricks {k.paving(zone)}")
    k.rocks()

    # ---- the capsule rack ----
    m_rack = M(PAL_RACK, roughness=0.35, metallic=0.6)
    m_seat = M(1, roughness=0.8)
    m_cap = M(PAL_CAP_LENS, roughness=0.2, metallic=0.1, emission_strength=0.45)
    windows = [stadium(*c) for c in caps]
    g.prism(kit.rbox(*rack, c=2.4, seg=3), windows, kit.DECK_TOP - 0.005, RACK_TOP, m_rack,
            chamfer=0.45, drop=0.010, bottom=False)
    for c, win in zip(caps, windows):
        g.prism(win, [], kit.DECK_TOP - 0.005, CAP_SEAT, m_seat, bottom=False)
        x0, y0, x1, y1 = c
        inset = 0.35
        k.pillow(stadium(x0 + inset, y0 + inset, x1 - inset, y1 - inset), CAP_SEAT - 0.002, CAP_GLASS, m_cap,
                 corner=(x1 - x0) / 2 - inset)
    rx0, ry0, rx1, ry1 = rack
    for bx, by in ((rx0 + 0.9, ry0 + 0.9), (rx1 - 0.9, ry0 + 0.9), (rx0 + 0.9, ry1 - 0.9), (rx1 - 0.9, ry1 - 0.9)):
        g.prism(kit.ell(bx, by, 0.55, 0.55, 6), [], RACK_TOP - 0.006, RACK_TOP + 0.008, m_rack, bottom=False)
    # a tie bar across the rack's middle web line at each window's waist (the art's dark mid notch)
    # is not painted: left out (the art wins).

    # ---- the two big panes ----
    m_pf = M(PAL_PANE_FRAME, roughness=0.45, metallic=0.5)
    m_ps = M(PAL_PANE_SEAT, roughness=0.7, metallic=0.2)
    m_pl = M(PAL_PANE_LENS, roughness=0.22, metallic=0.1, emission_strength=0.45)
    for (x0, y0, x1, y1), (fx0, fy0, fx1, fy1) in zip(fats, frames):
        seat = kit.rbox(x0 - 0.7, y0 - 0.7, x1 + 0.7, y1 + 0.7, 3.0, 3)
        g.prism(kit.rbox(fx0, fy0, fx1, fy1, 3.4, 3), [seat], kit.DECK_TOP - 0.005, PANE_FRAME_TOP, m_pf,
                chamfer=0.5, drop=0.012, bottom=False)
        g.prism(seat, [], kit.DECK_TOP - 0.005, PANE_SEAT, m_ps, bottom=False)
        k.pillow(kit.rbox(x0, y0, x1, y1, 2.6, 3), PANE_SEAT - 0.002, PANE_GLASS, m_pl, corner=2.6)
        cy = (y0 + y1) / 2
        for bx in (fx0 + 0.75, fx1 - 0.75):
            for by in (cy - 5.5, cy + 5.5):
                g.prism(kit.ell(bx, by, 0.5, 0.5, 6), [], PANE_FRAME_TOP - 0.008, PANE_FRAME_TOP + 0.007, m_pf, bottom=False)

    print("needles", k.no_needles())
    objects = k.objects()

    b.finish(objects, fp, bake=bake, preview=preview, grit=kit.GRIT)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
build(bake="--no-bake" not in argv, preview=lt.preview_arg())
