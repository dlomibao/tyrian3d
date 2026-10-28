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


# Palette indices the body is painted with. The sprite's light and dark (its outline ring, the
# dark tip and right side, the bright rim of the nail) is drawn lighting, not paint: the game
# lights the model and draws its own outline. So the skin is one mid-tone and only the real
# markings get their own colours: the nail plate, the crease, and the next finger's knuckle
# (a separate finger in shadow, a step darker than this one).
SKIN, NAIL, CREASE, KNUCKLE = 20, 23, 17, 19
PAINT = [SKIN, NAIL, CREASE, KNUCKLE]
NAIL_C, NAIL_R = 10.3, 15.0  # nail oval centre in sprite pixels (column, row)
NAIL_A, NAIL_B = 2.6, 8.7  # its half-width and half-length in pixels
CREASE_C = (16.6, 18.0)  # sprite columns of the dark crease left of the knuckle
CREASE_R = 14.5  # the crease and knuckle start this many rows down (where the knuckle shows;
# above it the dark pixels there are the outline)
SKIN_ROUGH = 0.75  # matte skin: metallic 0, rough, so the light shades the curve softly
NAIL_ROUGH = 0.35  # the nail is smooth and glossy; its bright left rim is the light's shine on it
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


def marking(g, x, y):
    """The palette index for a point of the finger's surface, from where it sits over the sprite."""
    c, r = g.col(x), g.row(y)
    if ((c - NAIL_C) / NAIL_A) ** 2 + ((r - NAIL_R) / NAIL_B) ** 2 <= 1:
        return NAIL
    if r >= CREASE_R and CREASE_C[0] <= c <= CREASE_C[1]:
        return CREASE
    if r >= CREASE_R and c > CREASE_C[1]:
        return KNUCKLE
    return SKIN


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [pal(i, metallic=0.0, roughness=NAIL_ROUGH if i == NAIL else SKIN_ROUGH) for i in PAINT]
    BASE = PAINT.index(SKIN)
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

    def uniform(a, b):
        xc = a + (b - a) * CREST
        return [xc + c * ((xc - a) if c < 0 else (b - xc)) for c in
                (math.cos(math.pi * (1 - k / TOP_SEG)) for k in range(TOP_SEG + 1))]

    def column(row, col):
        """The ring column nearest sprite column `col` on the ring at sprite row `row`."""
        i = min(range(len(ds)), key=lambda i: abs(g.row(top - ds[i] * U) - row))
        uni = uniform(*spans[i])
        return min(range(TOP_SEG + 1), key=lambda k: abs(uni[k] - g.x(col)))

    # The ring columns that carry the nail's edges (nearest them where it is widest) and the
    # crease's edges (half way down it).
    kl, kr = column(NAIL_R, NAIL_C - NAIL_A), column(NAIL_R, NAIL_C + NAIL_A)
    kc0, kc1 = column(20, CREASE_C[0]), column(20, CREASE_C[1])

    loops = []
    for i, d in enumerate(ds):
        a, b = spans[i]
        xc = a + (b - a) * CREST
        h = smooth_min(along(d), SIDE * smooth_half(i) / U, BLEND) * U
        y = top - d * U
        ring = []
        xs = uniform(a, b)
        # Columns kl and kr slide onto the nail's oval edge, and kc0 and kc1 onto the crease's
        # edges (the others follow in proportion), so these markings have clean outlines, not
        # staircases. The vertices only move along the section's own curve: the shape is unchanged.
        pins = [(0, a)]
        e = 1 - ((g.row(y) - NAIL_R) / NAIL_B) ** 2
        if e > 0:
            hw = NAIL_A * math.sqrt(e) * U
            pins += [(kl, g.x(NAIL_C) - hw), (kr, g.x(NAIL_C) + hw)]
        if g.row(y) >= CREASE_R - 1.5 and g.x(CREASE_C[1]) < xs[TOP_SEG - 1]:
            pins += [(kc0, g.x(CREASE_C[0])), (kc1, g.x(CREASE_C[1]))]
        pins.append((TOP_SEG, b))
        assert all(p[0] < q[0] and p[1] < q[1] for p, q in zip(pins, pins[1:])), pins
        uni = list(xs)
        for (k0, x0), (k1, x1) in zip(pins, pins[1:]):
            for k in range(k0, k1 + 1):
                xs[k] = x0 + (uni[k] - uni[k0]) * (x1 - x0) / (uni[k1] - uni[k0])
        for x in xs:
            c = (x - xc) / ((xc - a) if x < xc else (b - xc))
            ring.append(bm.verts.new((x, y, h * math.sqrt(max(0.0, 1 - c * c)))))
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
    bm.faces.ensure_lookup_table()
    for f in bm.faces[first:]:
        if not all(abs(v.co.z) < 1e-6 for v in f.verts):  # the hidden underside stays skin
            c = f.calc_center_median()
            f.material_index = PAINT.index(marking(g, c.x, c.y))
    cap = [bm.verts.new(v.co) for v in loops[-1]]
    centre = bm.verts.new(tuple(sum(v.co[i] for v in cap) / n for i in range(3)))
    f0 = lib.nfaces(bm)
    for k in range(n):
        bm.faces.new((cap[(k + 1) % n], cap[k], centre)).material_index = BASE
    lib.set_smooth(bm, f0, smooth=False)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview(ROOT, [obj], sprite)


if __name__ == "__main__":
    main()
