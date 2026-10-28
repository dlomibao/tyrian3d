"""Brown fingertip (newsh5.shp frame 154): a 3D version of its sprite.

Seen in episode 4 (level 4.25, the flying face). A rounded brown finger pointing up the screen,
running off the bottom of the sprite: a domed tip, a smooth oval nail down its middle with a
bright rim on its lit left side, and the next finger's knuckle peeking out on the right past a
dark crease.

Run: blender --background --python assets/blender/enemies/newsh5-154.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b013 as lib  # noqa: E402

NAME = "newsh5-154"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = lib.U


# Palette indices the body is painted with (each sprite pixel takes the nearest one), so the top
# view keeps the sprite's colours: the lit nail on the left, the dark knuckle and crease on the right.
PAINT = [17, 19, 20, 21, 22, 23, 24, 26, 28]
FLOOR = 16  # darkest index the paint samples (the outline pixels read as this)
TOP_SEG = 26  # segments over the rounded top of each cross-section
BOT_SEG = 2  # segments across the flat underside (it sits on z = 0, nothing below)
CREST = 0.45  # the crest sits this far across the width from the left (the lit side)
CROWN = 0.42  # the highest section, as a fraction of the length down from the top (under the highlight)
HEIGHT = 11.0  # px at the crown
SIDE = 1.45  # cap on a section's height over its half-width, so the narrow tip stays a dome, not a spire
WALL = 2.5  # px the shaded front wall at the bottom edge (the sprite's dark bottom band) stands
GROW = 0.0  # px the outline is pushed out
BLEND = 3.0  # px over which the length profile and the width cap blend, so there's no kink between them
ROUNDS = 4  # smoothing rounds on the outline, so the shoulders don't terrace
ROUGH = 1.0  # matte stone/skin, so the painted highlight does the lighting, not a specular band


def crossing(poly, y):
    """Leftmost and rightmost x where the horizontal line at y crosses the polygon."""
    xs = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 - y) * (y1 - y) <= 0 and y0 != y1:
            xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
    return min(xs), max(xs)


def smooth_min(a, b, k):
    """min(a, b) with the corner rounded over a difference of k (it dips at most k/4 below)."""
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k / 4


def softened(g):
    """The sprite's pixels with their dithering evened out (each one averaged with its four
    neighbours at half weight), so the paint follows its shading bands rather than single pixels."""
    rows = []
    for r in range(g.h):
        row = []
        for c in range(g.w):
            v = g.at(c, r)
            if v < 0:
                row.append(v)
                continue
            acc, wt = 2.0 * max(v, FLOOR), 2.0
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = g.at(c + dc, r + dr)
                if n >= 0:
                    acc, wt = acc + max(n, FLOOR), wt + 1
            row.append(int(round(acc / wt)))
        rows.append(row)
    return lib.Grid(g.w, g.h, rows)


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.0, roughness=ROUGH) for i in PAINT]
    BASE = PAINT.index(21)
    g = lib.Grid(24, 28, common.load_sprite(ROOT, NAME)["frames"][0]["pixels"])
    bm = bmesh.new()

    # The finger: one smooth body, a half-round section across the sprite's width at every row,
    # as tall as it is half wide (about 5 px over the narrow tip, 9-10 px over the wide base),
    # its crest a little left of centre under the lit nail, rounding down over the tip and cut
    # off at the bottom where the sprite runs off its frame.
    outline = lib.resample(lib.mask_outline(g, lambda v: v >= 0, rounds=ROUNDS, inset=-GROW), 160)
    rows = [r for r in range(g.h) if any(v >= 0 for v in g.pixels[r])]
    top, bottom = g.y(rows[0] - 0.5), g.y(rows[-1] + 0.5)
    depth = round((top - bottom) / U)
    ds = [0.12, 0.4] + list(range(1, depth)) + [depth - 0.6, depth - 0.25, depth - 0.02]  # px down from the top edge
    spans = [crossing(outline, top - d * U) for d in ds]
    half = [(b - a) / 2 for a, b in spans]

    def smooth_half(i):
        near = [half[j] for j in range(len(ds)) if abs(ds[j] - ds[i]) <= 3 and ds[j] >= 1]
        return sum(near) / len(near) if near else half[i]

    # Along the length: a dome rising from the tip to the crown under the highlight, then a
    # circular arc falling from the crown to a short front wall at the bottom edge.
    dc = CROWN * depth
    run = depth - dc
    drop = HEIGHT - WALL
    radius = (run * run + drop * drop) / (2 * drop)

    def along(d):
        if d <= dc:
            return HEIGHT * math.sqrt(max(0.0, 1 - ((dc - d) / dc) ** 2))
        x = d - dc
        return HEIGHT - (radius - math.sqrt(max(0.0, radius * radius - x * x)))

    loops = []
    for i, d in enumerate(ds):
        a, b = spans[i]
        xc = a + (b - a) * CREST
        h = smooth_min(along(d), SIDE * smooth_half(i) / U, BLEND) * U
        y = top - d * U
        ring = []
        for k in range(TOP_SEG + 1):  # left rim, over the crest, to the right rim
            t = math.pi * (1 - k / TOP_SEG)
            c = math.cos(t)
            ring.append(bm.verts.new((xc + c * ((xc - a) if c < 0 else (b - xc)), y, h * math.sin(t))))
        for k in range(1, BOT_SEG):  # back along the flat underside
            t = math.pi * k / BOT_SEG
            c = math.cos(t)
            ring.append(bm.verts.new((xc + c * ((xc - a) if c < 0 else (b - xc)), y, 0.0)))
        loops.append(ring)

    first = lib.nfaces(bm)
    n = len(loops[0])
    for ra, rb in zip(loops, loops[1:]):
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((rb[k], rb[j], ra[j], ra[k])).material_index = BASE
    # The rounded tip closes on a point; the cut end at the bottom is a flat cap of its own.
    tip_ring = loops[0]
    apex = bm.verts.new(tuple(sum(v.co[i] for v in tip_ring) / n for i in range(3)))
    for k in range(n):
        bm.faces.new((tip_ring[k], tip_ring[(k + 1) % n], apex)).material_index = BASE
    lib.set_smooth(bm, first)
    # The underside is flat and meets the sides at a sharp rim on the ground.
    for f in bm.faces[first:]:
        if all(abs(v.co.z) < 1e-6 for v in f.verts):
            f.smooth = False
            for e in f.edges:
                e.smooth = False
    lib.paint(bm, first, softened(g), lambda v: PAINT.index(min(PAINT, key=lambda p: abs(p - max(v, 16)))), min_nz=-0.3)
    cap = [bm.verts.new(v.co) for v in loops[-1]]
    centre = bm.verts.new(tuple(sum(v.co[i] for v in cap) / n for i in range(3)))
    f0 = lib.nfaces(bm)
    for k in range(n):
        bm.faces.new((cap[(k + 1) % n], cap[k], centre)).material_index = PAINT.index(20)
    lib.set_smooth(bm, f0, smooth=False)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
