"""The lava pit in TYRIAN's islands (map 1-9, layer 2; tile 143, one tile), after the concept
assets/blender/features/concepts/tyr-lava-pit.jpg: a round crater sunk into the island's grey rock,
ringed by a lip of chamfered stone blocks, its walls stepping down (dark above, lit red near the
lava) into a pool of dark crust plates split by glowing cracks, hottest in the middle; the tile's
brown/tan stones lie round it as boulders, the big one left of the mouth included.

Every copy carries a top enemy (newsh2 153/155/157, the "star core panel" turret), so the pit is its
emplacement and shows only after it dies: the whole tile stays under L2_ENEMY_MAX (0.33); the rim
blocks reach about 0.12, the boulders about 0.2. The pit replaces its tile, so the model also carries
the tile's rock (Structure.rock, with a hole cut for the bowl), and its export removes the per-tile
model shapesz-t143.

The rock round the pit must look like the neighbouring per-tile rock models, which are untextured
(flat palette colours). So after concept_maps.py, `--maps` makes the concept's detail neutral (1.0,
no relief) outside the crater: the bake then leaves the rock in its plain palette colours and only
the crater carries the concept's detail. Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/tyrbld_lava_pit.py
    python tools/concept_maps.py tile:shapesz-tyrbld-lava-pit --concept tyr-lava-pit --span 0,0,0,0 --px 32
    python assets/blender/tiles/tyrbld_lava_pit.py --maps
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-tyrbld-lava-pit
"""

import math
import random
import sys
from pathlib import Path

# The crater in the tile's pixels (tile 143 at 1x: the dark ring spans about px 5-18, rows 8-19; the
# concept draws the crater's mouth over px 4.7-19.1, rows 6.3-19.7, and the lava over px 6.1-17.7,
# rows 9.2-18.3: its far (upper) wall shows more, so the pool sits a little low in the mouth).
MOUTH = (11.9, 13.1, 7.0, 6.5)  # cx, cy, rx, ry: the mouth's edge (the rim blocks' inner edge)
POOL = (11.9, 13.8, 5.2, 4.4)  # the lava's edge
CUT = (11.9, 13.2, 7.3, 6.8)  # the hole in the rock slab (hidden under the rim blocks)
LIP_OUT = 2.2  # px: the rim blocks' depth (mouth to outer edge)
RIM_SEGMENTS = 12
RIM_Z = (0.075, 0.12)  # the rim blocks' tops
LAVA_Z = -0.19  # the pool's surface (the cracks); the crust plates stand a little above it
CRUST_Z = 0.014
HOT = (11.6, 13.9, 1.25, 1.0)  # the hot middle: no crust
# The big tan stone left of the mouth (tile px 1-4, rows 8-15: warm pixels; the concept's rock).
LEFT_STONE = (2.4, 11.8, 2.1, 3.4, 0.25)  # cx, cy, rx, ry (px), angle (rad)
N = 32  # vertices round the crater
ENTRY = "shapesz-tyrbld-lava-pit"


def ell(c, t):
    """A point at angle t on the ellipse c (cx, cy, rx, ry), px."""
    cx, cy, rx, ry = c[:4]
    return cx + rx * math.cos(t), cy + ry * math.sin(t)


def lerp_ell(a, b, f):
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def grown(c, d):
    cx, cy, rx, ry = c[:4]
    return cx, cy, rx + d, ry + d


def clip(poly, a, b, c):
    """Sutherland-Hodgman: the part of polygon `poly` (px) where a*x + b*y <= c."""
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


def crust_cells(rng, crack=0.21):
    """Voronoi cells of jittered seeds in the pool, each shrunk by `crack` px from its neighbours and
    the pool's edge: the crust plates; the gaps between them are the glowing cracks."""
    cx, cy, rx, ry = POOL
    seeds = []
    step = 2.8
    for j in range(-4, 5):
        for i in range(-4, 5):
            x = cx + (i + 0.5 * (j % 2)) * step + rng.uniform(-0.85, 0.85)
            y = cy + j * step * 0.87 + rng.uniform(-0.75, 0.75)
            if ((x - cx) / (rx + 1.0)) ** 2 + ((y - cy) / (ry + 1.0)) ** 2 > 1.0:
                continue
            seeds.append((x, y))
    edge = [ell(grown(POOL, -0.25), 2 * math.pi * k / N) for k in range(N)]
    cells = []
    for k, (sx, sy) in enumerate(seeds):
        if ((sx - HOT[0]) / HOT[2]) ** 2 + ((sy - HOT[1]) / HOT[3]) ** 2 <= 1.0:
            continue
        poly = list(edge)
        for m, (tx, ty) in enumerate(seeds):
            if m == k:
                continue
            a, b = tx - sx, ty - sy
            d = math.hypot(a, b)
            a, b = a / d, b / d
            mx, my = (sx + tx) / 2, (sy + ty) / 2
            poly = clip(poly, a, b, a * mx + b * my - crack)
            if len(poly) < 3:
                break
        # and keep the hot middle open
        if len(poly) >= 3:
            hx, hy = HOT[0], HOT[1]
            a, b = hx - sx, hy - sy
            d = math.hypot(a, b) or 1.0
            a, b = a / d, b / d
            # the plane through the hot spot's edge nearest the seed
            ex, ey = hx - a * HOT[2] * 0.95, hy - b * HOT[3] * 0.95
            poly = clip(poly, a, b, a * ex + b * ey)
        if len(poly) >= 3:
            area = 0.5 * abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1])))
            if area > 0.6:
                cells.append(((sx, sy), poly))
    return cells


def build():
    import bmesh

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import lib_tiles as lt  # noqa: E402
    import lib_tyrbld as tb  # noqa: E402

    s = tb.Structure("lava-pit")
    rng = random.Random("tyrbld-lava-pit")
    rock_dark = s.m("rock_dark")
    rim_mats = [s.m(6), s.m(7), s.m(5), s.m(8)]  # the rim blocks, each its own grey
    wall = s.m(2)  # the crater's upper walls, dark in shadow
    wall_warm = s.pal(112, emission_strength=0.35, roughness=0.7)  # lower walls, lit by the lava
    wall_hot = s.pal(113, emission_strength=0.9, roughness=0.6)  # the ledge just over the lava
    crack = s.m("lava", emission_strength=2.2)  # the lava itself, showing in the cracks
    hot = s.pal(117, emission_strength=2.6, roughness=0.4)  # the hot middle and bubbles
    crust = [s.pal(1, roughness=0.9), s.pal(112, emission_strength=0.35, roughness=0.8), s.pal(113, emission_strength=0.7, roughness=0.75)]

    # The bowl: rings from the mouth down the stepped walls (flat ledges with short drops) to the
    # pool's edge. (fraction from mouth to pool, z, material of the band above this ring)
    walls = [(0.0, -0.01, None), (0.22, -0.035, wall), (0.27, -0.08, wall), (0.5, -0.095, wall_warm),
             (0.55, -0.14, wall_warm), (0.8, -0.15, wall_hot), (0.84, LAVA_Z + 0.005, wall_hot),
             (1.0, LAVA_Z, wall_hot)]
    bm = bmesh.new()
    rings = []
    for f, z, _ in walls:
        e = lerp_ell(MOUTH, POOL, f)
        ring = []
        for i in range(N):
            t = 2 * math.pi * i / N
            px, py = ell(e, t)
            ring.append(bm.verts.new((s.x(px), s.y(py), z)))
        rings.append(ring)
    for k in range(1, len(rings)):
        a_, b_ = rings[k - 1], rings[k]
        for i in range(N):
            j = (i + 1) % N
            bm.faces.new((a_[i], a_[j], b_[j], b_[i])).material_index = walls[k][2]
    # The lava's surface: one flat face (the cracks' glow), no fan to show facets.
    bm.faces.new(rings[-1]).material_index = crack
    # Under the mouth: a skirt from the mouth down to the slab's bottom, and a plug closing the
    # hole from below (the islands' undersides show at the screen's top).
    skirt = []
    for i in range(N):
        px, py = ell(grown(CUT, 0.4), 2 * math.pi * i / N)
        skirt.append(bm.verts.new((s.x(px), s.y(py), tb.L2_SLAB_BOTTOM)))
    mouth = rings[0]
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((skirt[i], skirt[j], mouth[j], mouth[i])).material_index = rock_dark
    bm.faces.new(list(reversed(skirt))).material_index = rock_dark
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    s._merge(bm)

    # The crust: dark plates (black at the edge, dark red toward the middle) split by bright cracks.
    pc = bmesh.new()
    for (sx, sy), poly in crust_cells(rng):
        r = math.hypot((sx - POOL[0]) / POOL[2], (sy - POOL[1]) / POOL[3])
        mat = crust[0] if r > 0.82 else crust[1] if r > 0.5 else crust[2]
        if rng.random() < 0.25:
            mat = crust[2] if mat is not crust[2] else crust[1]
        z1 = LAVA_Z + CRUST_Z + rng.uniform(-0.003, 0.004)
        top = [pc.verts.new((s.x(x), s.y(y), z1)) for x, y in poly]
        bot = [pc.verts.new((s.x(x), s.y(y), LAVA_Z - 0.006)) for x, y in poly]
        pc.faces.new(top).material_index = mat
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            pc.faces.new((bot[i], bot[j], top[j], top[i])).material_index = crust[0]
    bmesh.ops.recalc_face_normals(pc, faces=pc.faces)
    s._merge(pc)
    # The hot middle: a low glowing swell, smooth, and bubbles big enough to read from the game camera.
    s.dome(HOT[0], HOT[1], HOT[2] * 1.05, HOT[3] * 1.05, LAVA_Z - 0.004, 0.022, hot, sides=16, rings=3)
    for cx, cy, r in ((9.4, 12.6, 0.7), (14.4, 15.3, 0.65), (11.0, 16.4, 0.55)):
        s.dome(cx, cy, r, r, LAVA_Z + CRUST_Z - 0.006, 0.028, hot, sides=12, rings=3)

    # The rim: chamfered stone blocks round the mouth, each its own grey and height, butted close
    # (the joints narrow, not open to the dark slab).
    rim_z = []
    for k in range(RIM_SEGMENTS):
        a0 = 2 * math.pi * (k + 0.012) / RIM_SEGMENTS + 0.15
        a1 = 2 * math.pi * (k + 1 - 0.012) / RIM_SEGMENTS + 0.15
        z = rng.uniform(*RIM_Z)
        rim_z.append(z)
        out = LIP_OUT + rng.uniform(-0.35, 0.45)
        ts = [a0 + (a1 - a0) * u for u in (0.0, 0.25, 0.5, 0.75, 1.0)]
        tilt = rng.uniform(-0.012, 0.012)
        zs = [z + tilt * (2 * u - 1) for u in (0.0, 0.25, 0.5, 0.75, 1.0)]
        mat = rim_mats[k % len(rim_mats)] if k % 3 else rim_mats[(k + 1) % len(rim_mats)]
        bb = bmesh.new()

        def loop(d, dz, ts=ts, zs=zs, bb=bb):
            return [bb.verts.new((s.x(px), s.y(py), zz + dz)) for (px, py), zz in zip([ell(grown(MOUTH, d), t) for t in ts], zs)]

        # Section from the pit's side outward: foot inside the bowl, a chamfer down to the pit,
        # the flat top, a chamfer at the outer edge, the outer foot on the slab.
        foot_in = loop(-0.35, -0.10 - z)
        lip = loop(-0.35, -0.035)
        top_in = loop(0.35, 0.0)
        top_out = loop(out - 0.7, 0.0)
        chamf = loop(out - 0.2, -0.035)
        foot_out = [bb.verts.new((v.co.x, v.co.y, -0.02)) for v in loop(out, 0.0)]
        loops = [foot_in, lip, top_in, top_out, chamf, foot_out]
        mats = [rock_dark, mat, mat, mat, mat]
        for li in range(len(loops) - 1):
            a_, b_ = loops[li], loops[li + 1]
            for i in range(len(ts) - 1):
                bb.faces.new((a_[i], a_[i + 1], b_[i + 1], b_[i])).material_index = mats[li]
        for i in range(len(ts) - 1):  # underside
            bb.faces.new((foot_out[i], foot_out[i + 1], foot_in[i + 1], foot_in[i])).material_index = rock_dark
        for end in (0, len(ts) - 1):
            bb.faces.new([lp[end] for lp in loops]).material_index = mat
        bmesh.ops.recalc_face_normals(bb, faces=bb.faces)
        s._merge(bb)

    # The big tan stone left of the mouth, leaning on the rim (as the tile's warm pixels and the
    # concept's rock), coloured like the tile's tan stones.
    lx, ly, lrx, lry, lang = LEFT_STONE
    warm = s.box_mask(0, 8, 4, 15) & s.ramp_mask(1, 10)
    tan = s.m(s.dominant(warm) if warm.any() else "tan")
    sb = bmesh.new()
    lt.dome(sb, s.x(lx), s.y(ly), lrx / 12, lry / 12, lang, -0.03, 0.2, tan, sides=10, rings=3, squash=0.2)
    bmesh.ops.recalc_face_normals(sb, faces=sb.faces)
    s._merge(sb)

    # The island's rock round it: the slab with a hole for the bowl, boulders where the tile has
    # stones, none in the crater or under the left stone.
    cut = s.ellipse_mask(*CUT)
    keep_out = s.ellipse_mask(*grown(MOUTH, -0.5)) | s.ellipse_mask(lx, ly, lrx + 0.3, lry + 0.3)
    s.rock(exclude=keep_out, cut=cut)

    objects = s.objects()
    s.check(objects)
    s.export(objects)


def maps():
    """Neutral detail and flat relief outside the crater (so the rock bakes in its plain palette
    colours, like the per-tile rock round it); run after concept_maps.py, before the bake."""
    import json

    import numpy as np
    from PIL import Image

    root = Path(__file__).resolve().parents[3]
    d = root / "assets/blender/textures" / ENTRY
    meta = json.loads((d / "maps.json").read_text())
    k = meta["texels_per_px"]
    for name, value in (("detail.png", 1.0), ("height.png", None)):
        im = Image.open(d / name)
        mode = im.mode
        a = np.asarray(im.convert("F") if mode not in ("I;16", "I") else im, dtype=np.float64)
        h, w = a.shape
        yy, xx = (np.mgrid[0:h, 0:w] + 0.5) / k
        cx, cy, rx, ry = grown(MOUTH, LIP_OUT + 0.3)
        r = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        keep = np.clip((1.12 - r) / 0.12, 0, 1)  # 1 inside the crater and its rim, fading out
        full = 65535.0 if mode.startswith("I") else 255.0
        out = value * full if value is not None else float(np.median(a))
        b = a * keep + out * (1 - keep)
        if mode.startswith("I"):
            Image.fromarray(np.clip(b, 0, 65535).astype(np.uint16)).save(d / name)
        else:
            Image.fromarray(np.clip(b + 0.5, 0, 255).astype(np.uint8), "L").convert(mode).save(d / name)
        print(f"{name}: {mode} {w}x{h}, neutral outside the crater")


if "--maps" in sys.argv:
    maps()
else:
    build()
