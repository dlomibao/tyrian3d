"""The large base complex of map 1-3's ground (shapesz.dat; 39 x 13 tiles, map rows 248-286, cols 1-13),
after the concept assets/blender/features/concepts/l1-bld-base-complex.jpg (stitched from two halves):

- the top square: a ring of brown channels, four black pits ringed by rocks, three stacks of red
  light capsules (338 at cells 4,8 and 5,4; 339 at 6,6, under red-light enemies);
- the neck down to the middle hall: the channel runs on into a U-shaped yard (black space) holding a
  round dark hatch on a pad (305 306 / 315 316, under a pad enemy);
- the row of red lights and orbs (347 347 384 384 347 347, row 20) and the turret block
  (298 299 / 308 309, rows 21-22; no enemy is drawn there, so it stands taller);
- the long spine down to the fork: two hatches (318 319 / 328 329, rows 30-31, under hatch enemies)
  and the forked fingers at the bottom, with their channels.

All of it is flat paving at DECK_Z (0.33) with clean channel strips inlaid (CHANNEL_Z), a dark
rubble band along every edge with low rounded boulders on it in two rows (they also ring the pits,
the yard and the fork's slots: holes in the footprint), and the lights, hatches and turret as parts.
Ground enemies sit on many cells (lib_l1bld BUILDINGS["base-complex"]["enemies"]): the paving is in
their band everywhere and every part under them stays at or below ENEMY_MAX.

Texture bake: texture_bake.py smart-UV-projects the glb and packs every island; with hundreds of
rocks the islands, not the area, decide how much of the texture the deck gets. So: the deck's
T-junctions are welded and coplanar faces dissolved (weld_deck), the unseen bottoms are deleted
(strip_bottoms), rocks are low and smooth shaded (rocks()), the rim band is a colour, not a step.
About 13 texels per unit on the deck at the default 2048 px (the concept has about 16).

About 32k triangles (it is 91 units long): about 26k of them are the ~830 rocks along its long
outline, pits, yard and slots.

Concept maps: the concept is two Gemini halves stitched, and one box (tools/concept_maps.py
--concept-box) can't register it (best IoU 0.64, misplaced features). Its maps were made with a
thin-plate-spline warp through 32 landmarks (channel corners, lights, hatches; listed in
assets/blender/textures/shapesz-l1bld-base-complex/maps.json), by concept_maps.py's own steps
otherwise; areas the concept cuts off (the top two rows, the fork's right edge) are mirrored in.

Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_base_complex.py
    (concept maps: see above; re-run only if the concept changes)
    blender --background --factory-startup --python assets/blender/texture_bake.py -- tile:shapesz-l1bld-base-complex
"""

import math
import sys
from pathlib import Path

import bmesh
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_l1bld as lb  # noqa: E402
import lib_tiles as lt  # noqa: E402

DECK_Z = 0.33  # the paving (within the enemy band 0.30-0.38)
CHANNEL_Z = DECK_Z - lb.CHANNEL_DROP  # 0.30: still in the band, though no enemy cell holds a channel
ROCK_SLOPE = 0.7  # a rock's height over its radius at most: low boulders (see rocks())
QUANT = 4  # the slab's outline on a 4 px grid (a superset of the footprint): far fewer wall faces

RIM_BAND = 7  # px from the outline: the dark rubble the rocks stand on
OPEN = [(120, 0, 192, 14), (300, 31 * 28, 312, 39 * 28)]  # pixel boxes, see open_mask()

# Channel tiles: which arms (up, down, left, right) each carries, and where a stub ends (px in the
# tile from its top / left), from the tiles' brown pixels. The channel runs centred at x = 11 (vertical)
# and y = 13 (horizontal), CH_HALF px either side, as straight, clean strips (the tiles' brown is a
# dithered brick pattern; the concept draws a clean inlaid strip).
CH_X, CH_Y, CH_HALF = 11.0, 13.5, 4.5
ARMS = {
    389: "ud", 379: "lr", 365: "dr", 367: "dl", 385: "ur", 387: "ul",
    366: "lrd", 386: "lru", 376: "udlr", 375: "udr", 377: "udl",
    388: "u", 378: "d", 369: "l", 368: "r",
}
STUB = {388: ("u", 17), 378: ("d", 6), 369: ("l", 14), 368: ("r", 6)}
LIGHT_TOP = 0.37  # red capsules, orbs, hatch frames: under the enemies drawn over them

# Red light capsules from the tiles' red pixels (pixel boxes x0, y0, x1, y1, inclusive), and their axis.
CAPSULES = [
    # 338 at cell (4, 8): three horizontal capsules stacked
    ((194, 114, 211, 120), "x"), ((194, 123, 211, 129), "x"), ((194, 132, 211, 138), "x"),
    # 338 at cell (5, 4)
    ((98, 142, 115, 148), "x"), ((98, 151, 115, 157), "x"), ((98, 160, 115, 166), "x"),
    # 339 at cell (6, 6): three vertical capsules side by side
    ((145, 173, 150, 190), "y"), ((153, 173, 158, 190), "y"), ((161, 173, 166, 190), "y"),
    # 347 at row 20, cols 4, 5, 8, 9: one fat upright capsule each
    ((100, 564, 114, 583), "y"), ((124, 564, 138, 583), "y"),
    ((196, 564, 210, 583), "y"), ((220, 564, 234, 583), "y"),
]
ORBS = [(155, 570), (179, 570)]  # 384 at (20, 6), (20, 7): small metal orbs with a red eye
ROUND_HATCH = (165.5, 475.0, 19.5, 24.0)  # 305 306 / 315 316: centre and radii in px
HATCHES = [(121, 842, 167, 895), (193, 842, 239, 895)]  # 318 319 / 328 329 pairs
TURRET = (240, 588, 288, 644)  # 298 299 / 308 309


def disc(b, cx, cy, rx, ry, z0, z1, mat, sides=24):
    """A flat cylinder (pixel centre and radii) from z0 to z1."""
    bm = bmesh.new()
    lo, hi = [], []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        x, y = b.x(cx + rx * math.cos(a)), b.y(cy + ry * math.sin(a))
        lo.append(bm.verts.new((x, y, z0)))
        hi.append(bm.verts.new((x, y, z1)))
    bm.faces.new(hi).material_index = mat
    bm.faces.new(list(reversed(lo))).material_index = mat
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    b._merge(bm)


def round_hatch(b):
    """The round, spoked hatch in the yard (the concept's dark metal disc): a bevelled metal ring,
    a dark bronze panel a little lower, four spokes and a hub."""
    cx, cy, rx, ry = ROUND_HATCH
    metal = b.m("metal")
    disc(b, cx, cy, rx + 1.5, ry + 1.5, DECK_Z - 0.04, DECK_Z + 0.01, b.m(3))  # the seat
    disc(b, cx, cy, rx, ry, DECK_Z - 0.03, LIGHT_TOP - 0.01, metal)  # the rim
    disc(b, cx, cy, rx - 3, ry - 3, LIGHT_TOP - 0.03, LIGHT_TOP - 0.005, b.m(165, roughness=0.3, metallic=0.6))
    for a in (0.0, 0.5 * math.pi):
        w = 1.4
        dx, dy = math.cos(a), math.sin(a)
        if dx > 0.5:
            b.wall_block(cx - rx + 3, cy - w, cx + rx - 3, cy + w, LIGHT_TOP - 0.04, LIGHT_TOP, metal, bevel=0.3)
        else:
            b.wall_block(cx - w, cy - ry + 3, cx + w, cy + ry - 3, LIGHT_TOP - 0.04, LIGHT_TOP, metal, bevel=0.3)
    b.dome(cx, cy, 4.0, 4.5, LIGHT_TOP - 0.02, 0.02, metal, sides=12, rings=2)


def turret(b):
    """The turret block: a chamfered brown-metal base, a squat dome and a gun barrel pointing down
    the screen (the sprite's gun), red sensor lights on its sides."""
    x0, y0, x1, y1 = TURRET
    body = b.m(165, metallic=0.4, roughness=0.5)
    b.wall_block(x0 + 3, y0 + 4, x1 - 3, y1 - 3, DECK_Z - 0.04, 0.44, b.m(4), bevel=0.25)
    b.wall_block(x0 + 7, y0 + 8, x1 - 7, y1 - 7, 0.43, 0.52, body, bevel=0.35)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 1
    b.dome(cx, cy, 11, 12, 0.51, 0.14, b.m(166, metallic=0.5, roughness=0.4), sides=16, rings=4)
    # Barrel: a narrow box from the dome down the screen.
    b.wall_block(cx - 2, cy + 6, cx + 2, y1 - 1, 0.55, 0.60, b.m(3, metallic=0.6, roughness=0.35), bevel=0.4)
    for sx in (x0 + 9, x1 - 9):
        b.capsule(sx, y0 + 12, 6, 2.0, axis="y", z=0.53, housing=False)


def open_mask(b):
    """Where the platform runs on past the pattern's edge, without a rim: the channel's way up into
    the pipe junction (top edge, cols 5-7) and the fork's right side at the map's edge (col 12, rows
    31-38)."""
    m = np.zeros((b.H, b.W), bool)
    for x0, y0, x1, y1 in OPEN:
        m |= b.box_mask(x0, y0, x1, y1)
    return m


def channels(b):
    """The channel strips as a pixel mask, from the channel tiles' arms."""
    m = np.zeros((b.H, b.W), bool)
    for r, row in enumerate(b.pattern):
        for c, t in enumerate(row):
            arms = ARMS.get(t)
            if not arms:
                continue
            x0, y0 = c * lt.TILE_W, r * lt.TILE_H
            cx, cy = x0 + CH_X, y0 + CH_Y
            stub = STUB.get(t)
            for a in arms:
                if a == "u":
                    box = (cx - CH_HALF, y0, cx + CH_HALF, (y0 + stub[1]) if stub else cy + CH_HALF)
                elif a == "d":
                    box = (cx - CH_HALF, (y0 + stub[1]) if stub else cy - CH_HALF, cx + CH_HALF, y0 + lt.TILE_H)
                elif a == "l":
                    box = (x0, cy - CH_HALF, (x0 + stub[1]) if stub else cx + CH_HALF, cy + CH_HALF)
                else:
                    box = ((x0 + stub[1]) if stub else cx - CH_HALF, cy - CH_HALF, x0 + lt.TILE_W, cy + CH_HALF)
                m |= b.box_mask(*box)
    return m


def rocks(b, spacing, inset, radius, height, sink, keep_out=None, sides=(5, 7)):
    """Rim rocks like lib_l1bld's rim_rocks (jittered, along the outline, `inset` px in from it, one
    every `spacing` px), but shaped as faceted boulders whose every face looks up by less than
    45 degrees (texture_bake's smart UV project then puts it in the top-down projection): a jittered base ring, a shoulder ring and a jagged
    cap, low and rounded (smooth shaded). Each rock then unwraps as one UV island (a prism's sides
    each make their own, and with a few hundred rocks the packed deck got a sliver of the texture).
    Over an enemy cell a rock is capped at ENEMY_MAX. Returns the count."""
    rng = b._rng
    d = lb.depth(b.footprint)
    ring = (d >= max(1, inset - 1)) & (d <= inset + 1)
    ys, xs = np.nonzero(ring)
    order = list(range(len(ys)))
    rng.shuffle(order)
    taken, cell = [], {}
    for i in order:
        px, py = xs[i] + 0.5, ys[i] + 0.5
        if keep_out is not None and keep_out[int(py), int(px)]:
            continue
        gx, gy = int(px // spacing), int(py // spacing)
        if any((qx - px) ** 2 + (qy - py) ** 2 < spacing * spacing
               for dx in (-1, 0, 1) for dy in (-1, 0, 1) for qx, qy in cell.get((gx + dx, gy + dy), ())):
            continue
        cell.setdefault((gx, gy), []).append((px, py))
        taken.append((px, py))
    mats = [b.m(6), b.m(7), b.m(9), b.m(5)]  # lighter than the paving (6), as the concept's boulders
    for k, (px, py) in enumerate(taken):
        r_px = radius[0] + (radius[1] - radius[0]) * rng.random()
        top = height[0] + (height[1] - height[0]) * rng.random()
        y0, y1 = int(max(0, py - r_px)), int(min(b.H, py + r_px + 1))
        x0, x1 = int(max(0, px - r_px)), int(min(b.W, px + r_px + 1))
        if b.enemy_mask[y0:y1, x0:x1].any():
            top = min(top, lb.ENEMY_MAX)
        here = b.height[min(b.H - 1, int(py)), min(b.W - 1, int(px))]
        z0 = (DECK_Z if np.isnan(here) else float(here)) - sink
        r = r_px * lt.PX
        ex, ey = 0.85 + 0.3 * rng.random(), 0.85 + 0.3 * rng.random()
        top = min(top, z0 + ROCK_SLOPE * r * min(ex, ey))  # slopes kept low (see above)
        n = rng.randint(*sides)
        rot = rng.random() * math.tau
        bm = bmesh.new()

        spokes = [(rot + math.tau * (i + 0.3 * (rng.random() - 0.5)) / n, 0.88 + 0.24 * rng.random()) for i in range(n)]

        def ring_at(scale, z, jz):
            return [bm.verts.new((b.x(px) + r * scale * f * ex * math.cos(a), b.y(py) + r * scale * f * ey * math.sin(a),
                                  z + jz * (rng.random() - 0.5))) for a, f in spokes]

        h = top - z0
        base = ring_at(1.0, z0, 0.0)
        shoulder = ring_at(0.76, z0 + 0.5 * h, 0.1 * h)
        cap = ring_at(0.4, top - 0.1 * h, 0.08 * h)
        peak = bm.verts.new((b.x(px) + r * 0.1 * (rng.random() - 0.5), b.y(py) + r * 0.1 * (rng.random() - 0.5), top))
        mi = mats[rng.randrange(len(mats))]
        for lo, hi in ((base, shoulder), (shoulder, cap)):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mi
        for i in range(n):
            bm.faces.new((cap[i], cap[(i + 1) % n], peak)).material_index = mi
        bm.faces.new(list(reversed(base))).material_index = mi  # closed (objects() recalcs normals)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) == 4])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # Smooth shaded: rounded boulders as in the concept, and the glb keeps the rock's vertices
        # shared (flat faces are split apart on export, and each would be its own UV island).
        b._merge(bm, smooth=True)
    return len(taken)


def lens(b, box):
    """A red light capsule as the concept draws it, flat enough for its whole outline to show above the
    deck: lib_l1bld's capsule() is round in section, so a capsule a few px wide is mostly sunk under
    the paving. Here: a light metal housing plate two px larger than the light, and on it a low,
    glowing half-ellipsoid over the light's pixel box (x0, y0, x1, y1, inclusive), its top at
    LIGHT_TOP (under the red-light enemies drawn over them)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
    rx, ry = (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2
    b.wall_block(x0 - 2.0, y0 - 2.0, x1 + 3.0, y1 + 3.0, DECK_Z - 0.03, DECK_Z + 0.025,
                 b.m(8, metallic=0.6, roughness=0.3), bevel=0.3)
    b.dome(cx, cy, rx, ry, DECK_Z + 0.005, LIGHT_TOP - DECK_Z - 0.005, b.m("red"), sides=16, rings=3)


def weld_deck(bm):
    """terrace() merges equal pixels into rectangles that meet in T-junctions, so its faces share
    few edges: each rectangle unwraps as its own UV island and the bake's packing wastes most of the
    texture. Split every edge at the vertices lying on it (all on the pixel grid, axis-aligned), weld,
    then dissolve coplanar faces of one material into large n-gons: fewer islands and triangles. The
    winding terrace() set is kept (no normal recalculation)."""
    from collections import defaultdict
    for _ in range(3):
        on_line = defaultdict(list)  # (axis, fixed coord, z) -> verts
        key = lambda v: (round(v.co.x, 4), round(v.co.y, 4), round(v.co.z, 4))
        for v in bm.verts:
            x, y, z = key(v)
            on_line[("y", y, z)].append((x, v))  # horizontal line at y
            on_line[("x", x, z)].append((y, v))
        split = 0
        for e in list(bm.edges):
            a, c = e.verts
            ax, ay, az = key(a)
            cx, cy, cz = key(c)
            if az != cz:
                continue
            if ay == cy and ax != cx:
                lo, hi = sorted((ax, cx))
                inner = sorted(((t, v) for t, v in on_line[("y", ay, az)] if lo < t < hi), key=lambda tv: tv[0])
                start = ax
            elif ax == cx and ay != cy:
                lo, hi = sorted((ay, cy))
                inner = sorted(((t, v) for t, v in on_line[("x", ax, az)] if lo < t < hi), key=lambda tv: tv[0])
                start = ay
            else:
                continue
            if not inner:
                continue
            if start == hi:
                inner = inner[::-1]
            # Split from the start vertex `a` toward `c`, putting each new vertex on the inner one.
            cur = e
            for t, v in inner:
                ne, nv = bmesh.utils.edge_split(cur, a, 0.5)
                nv.co = v.co.copy()
                a = nv
                cur = ne if c in ne.verts else next(ed for ed in nv.link_edges if c in ed.verts)
                split += 1
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        if not split:
            break
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts, edges=bm.edges,
                             delimit={"MATERIAL", "NORMAL"})
    return bm


def strip_bottoms(objects):
    """Delete the faces nobody sees: those facing down (the slab's bottom, the rocks' and blocks'
    bases, all under the deck or on the ground). Fewer triangles, and fewer UV islands for the bake
    (texture_bake.py packs one island per face cluster: thousands of tiny ones leave the deck tops a
    sliver of the texture)."""
    for o in objects:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        dead = [f for f in bm.faces if f.normal.z < -0.95]
        bmesh.ops.delete(bm, geom=dead, context="FACES_ONLY")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(o.data)
        bm.free()


def main():
    b = lb.Building("base-complex")
    b.surface(deck=DECK_Z, channel=False, pits=False, red=False)
    # The slab's outline: the footprint on a QUANT px grid (a superset; rocks cover its edge).
    H, W = b.H, b.W
    q = b.footprint.reshape(H // QUANT, QUANT, W // QUANT, QUANT).any(axis=(1, 3))  # 1092 x 312: divisible
    slab = np.repeat(np.repeat(q, QUANT, 0), QUANT, 1) & b.cover
    b.height[:] = np.nan
    b.height[slab] = DECK_Z
    b.mat[slab] = b.m("pave")
    b.footprint = b.footprint | slab  # set_region and rim_rocks work on the slab
    b.set_region(channels(b), CHANNEL_Z, b.m("channel"))
    # The rim band: dark rubble where the rocks stand, so the gaps between them read as crevices
    # (the concept's black between its boulders), not paving. Not where the platform runs on past
    # the pattern (OPEN).
    band = b.footprint & (lb.depth(b.footprint) <= RIM_BAND) & ~open_mask(b)
    # On a QUANT grid like the outline, and only a colour (a step down made hundreds of short walls,
    # each its own UV island: the bake's texture went to them).
    q = band.reshape(H // QUANT, QUANT, W // QUANT, QUANT).mean(axis=(1, 3)) >= 0.5
    band = np.repeat(np.repeat(q, QUANT, 0), QUANT, 1) & b.footprint & (b.mat == b.m("pave"))
    b.set_region(band, None, b.m(3, roughness=0.95))
    deck = b.terrace()
    print("deck faces", len(deck.faces))
    weld_deck(deck)
    print("deck faces welded", len(deck.faces))

    for box, axis in CAPSULES:
        lens(b, box)
    for px, py in ORBS:
        b.dome(px, py, 6, 6, DECK_Z - 0.01, LIGHT_TOP - DECK_Z, b.m("metal"), sides=12, rings=3)
    round_hatch(b)
    for x0, y0, x1, y1 in HATCHES:
        # The tiles' hatches are light plates with a dark, red-lit crack (the concept's broken
        # hatch): a light frame, a light recessed plate, a dark glowing slot across its middle.
        b.hatch(x0, y0, x1, y1, z=LIGHT_TOP, frame_px=3, depth_=0.03,
                mat_frame=b.m(10, metallic=0.4, roughness=0.4), mat_inside=b.m(9, roughness=0.6))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        b.wall_block(cx - 4, y0 + 8, cx + 4, y1 - 8, DECK_Z, LIGHT_TOP - 0.025,
                     b.m(lb.PAL["red_dark"], emission_strength=0.8, roughness=0.5), bevel=0.0)
    turret(b)
    keep_out = lb.dilate(open_mask(b), 6)
    n1 = rocks(b, spacing=9.0, inset=4.0, radius=(5.0, 7.5), height=(0.44, 0.50), sink=0.03, keep_out=keep_out)
    n2 = rocks(b, spacing=9.0, inset=10.0, radius=(4.0, 6.0), height=(0.39, 0.45), sink=0.04, keep_out=keep_out)
    print("rocks", n1, n2)
    objects = b.objects(deck)
    strip_bottoms(objects)
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objects)
    print("triangles", tris)
    b.check(objects)
    b.export(objects)


main()
