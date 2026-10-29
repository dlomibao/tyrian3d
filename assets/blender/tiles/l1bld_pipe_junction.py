"""The forked-channel platform ("pipe junction") of map 1-3's ground (shapesz.dat; 12 x 9 tiles,
rows 238-249, cols 3-11; one copy), after the concept
assets/blender/features/concepts/l1-bld-pipe-junction.jpg: two square wings of brick paving ringed
by a rocky rim, a brown channel looping round an L-shaped brick island in each wing, the loops
meeting in a central bar, two short fingers of brick where the channels fork, and a funnel into
the long stem channel that runs down a rock-lined neck into the base complex below.

The pattern's last two rows are the base's top edge (context only: the base model covers them), so
the model covers rows 0-9 and the stem ends open at the base's edge. No ground enemies sit on it.

The channel layout is transcribed (in pattern px) from the concept registered on the tiles (the
Gemini crop has the tiles at offset (6, 4); the concept is that crop at 2.925x). The concept is
mirror-symmetric to within a few px: the loops about x = 110, the fingers and stem about 108.5.

Run from the repo root:

    blender --background --factory-startup --python assets/blender/tiles/l1bld_pipe_junction.py
    python tools/concept_maps.py tile:shapesz-l1bld-pipe-junction --concept l1-bld-pipe-junction \
        --concept-box 18,26,649,994
    blender --background --factory-startup --python assets/blender/texture_bake.py -- \
        tile:shapesz-l1bld-pipe-junction --size 2048

The concept box is the pattern's painted box (tiles at crop (6, 4), concept 2.925x the crop): the
cut-out runs on into the base below (IoU 0.849 -> 0.92). Bake at 2048: at the default 1024 the
deck's long thin faces bleed into dark lines across the paving.

Depth (review: too flat): the deck sits low (0.27) so the rim's domed boulders stand 3-4 px over
it, the channels are cut about 2 px deep behind a two-step rounded lip, and the islands and the
notch wall stand clearly proud. Near the stem's open end the deck and channel floor step up to the
base complex's heights (deck 0.33, channel 0.30) so the stem meets the base flush.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bmesh  # noqa: E402
import numpy as np  # noqa: E402

import lib_l1bld as lb  # noqa: E402

DECK = 0.27  # the brick paving
FLOOR = 0.10  # the channels' floor (about 2 px under the deck)
BASE_DECK = 0.33  # the base complex's deck and channel (l1bld_base_complex.py), met at the stem's end
BASE_CHANNEL = 0.30
CORNER_PX = 5  # round corners of the channels (disc radius)
LOOP_AXIS = 110.0  # mirror axis of the wing loops in the concept
STEM_AXIS = 108.5  # mirror axis of the fingers, funnel and stem

# Channel boxes (x0, y0, x1, y1) of the left wing; mirrored about LOOP_AXIS for the right one.
LOOP_LEFT = [
    (32, 39, 68, 52),  # top bar
    (32, 39, 44, 107),  # outer side
    (54, 39, 68, 80),  # inner side, down to the central bar
    (54, 66, LOOP_AXIS, 80),  # central bar (the right half is its mirror)
    (32, 93, 92, 107),  # bottom bar
]
# Boxes about STEM_AXIS: the funnel's sides round the fingers (mirrored), and the centre.
FUNNEL_LEFT = [(77, 93, 92, 124)]
CENTRE = [
    (101, 79, 116, 124),  # between the fingers
    (77, 122, 140, 130),  # the funnel
    (85, 130, 132, 134),
    (94, 134, 123, 138),
    (102, 138, 115, 336),  # the stem, open at the base's edge (cut at the footprint)
]
# The brick wall across the top notch between the wings (concept: a wall face under the rocks).
NOTCH_WALL = (70, 44, 150, 62)
NOTCH_TOP = 0.45
ISLAND = 0.41
# The stem's end: (from py, deck, channel floor) steps up to the base's heights.
END_STEPS = [(214, DECK, 0.14), (228, DECK, 0.18), (242, 0.30, 0.22), (254, 0.30, 0.26),
             (264, BASE_DECK, BASE_CHANNEL)]


def mirror(box, axis):
    x0, y0, x1, y1 = box
    return (2 * axis - x1, y0, 2 * axis - x0, y1)


def disc_dilate(mask, r):
    out = mask.copy()
    h, w = mask.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r + r * 0.5:
                continue
            src = mask[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
            out[max(0, dy):h - max(0, -dy), max(0, dx):w - max(0, -dx)] |= src
    return out


def disc_erode(mask, r):
    return ~disc_dilate(~mask, r)


def channel_mask(b):
    boxes = list(LOOP_LEFT) + [mirror(bx, LOOP_AXIS) for bx in LOOP_LEFT]
    boxes += list(FUNNEL_LEFT) + [mirror(bx, STEM_AXIS) for bx in FUNNEL_LEFT] + CENTRE
    m = np.zeros((b.H, b.W), bool)
    for bx in boxes:
        m |= b.box_mask(*bx)
    # The concept's channels turn with rounded corners, outside and in.
    m = disc_dilate(disc_erode(m, CORNER_PX), CORNER_PX)
    m = disc_erode(disc_dilate(m, CORNER_PX - 1), CORNER_PX - 1)
    return m & b.footprint


def levels(b):
    """Per-pixel deck and channel-floor heights (they step up at the stem's end)."""
    deck = np.full((b.H, b.W), DECK)
    floor = np.full((b.H, b.W), FLOOR)
    for y0, dz, fz in END_STEPS:
        deck[y0:] = dz
        floor[y0:] = fz
    return deck, floor


def boulder(bm, cx, cy, rx, ry, angle, z0, z1, mat, sides, rng, jitter):
    """A rounded boulder: an elliptic prism with a domed, faceted top (rings narrowing to a cap)."""
    ca, sa = math.cos(angle), math.sin(angle)
    h = z1 - z0
    prof = [(0.0, 1.0), (0.45, 1.0), (0.72, 0.9), (0.9, 0.66), (1.0, 0.3)]
    rings = []
    for k, (fz, sc) in enumerate(prof):
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            j = 1.0 + (rng.random() - 0.5) * jitter if k else 1.0 + (rng.random() - 0.5) * jitter * 0.5
            lx, ly = rx * sc * j * math.cos(t), ry * sc * j * math.sin(t)
            z = z0 + h * fz
            if 0 < k:
                z = min(z1, z + (rng.random() - 0.5) * jitter * h * 0.25)
            ring.append(bm.verts.new((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca, z)))
        rings.append(ring)
    bm.faces.new(rings[-1]).material_index = mat
    for a, c in zip(rings[1:], rings[:-1]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((c[i], c[j], a[j], a[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat


def boulders(b, spacing, inset, size, height, sink, keep, sides, jitter):
    """lib_l1bld.rim_rocks' placement with domed boulders (no enemy cells on this building)."""
    lt = lb.lt
    mats = [b.m("rim"), b.m(4), b.m(6)]
    d = lb.depth(b.footprint)
    ring = (d >= max(1, inset - 1)) & (d <= inset + 1)
    ys, xs = np.nonzero(ring)
    order = list(range(len(ys)))
    b._rng.shuffle(order)
    taken = []
    for i in order:
        px, py = xs[i] + 0.5, ys[i] + 0.5
        if all((qx - px) ** 2 + (qy - py) ** 2 >= spacing * spacing for qx, qy in taken):
            taken.append((px, py))
    n = 0
    for k, (px, py) in enumerate(taken):
        if not keep(px, py):
            continue
        big = k % 2 == 0
        r_px = spacing * (size[1] if big else size[0]) * (0.9 + 0.2 * b._rng.random())
        rx = r_px * (0.8 + 0.3 * b._rng.random()) * lt.PX
        ry = r_px * (0.8 + 0.3 * b._rng.random()) * lt.PX
        top = height[0] + (height[1] - height[0]) * (b._rng.random() * (1.0 if big else 0.6))
        here = float(b.height[min(b.H - 1, int(py)), min(b.W - 1, int(px))])
        bm = bmesh.new()
        boulder(bm, b.x(px), b.y(py), rx, ry, b._rng.random() * math.pi, here - sink, top,
                mats[b._rng.randrange(len(mats))], b._rng.randint(*sides), b._rng, jitter)
        b._merge(bm)
        n += 1
    return n


def main():
    b = lb.Building("pipe-junction")
    b.surface(deck=DECK, channel=False, pits=False, red=False)
    deck_z, floor_z = levels(b)
    b.set_region(b.footprint, None, None)
    b.height[b.footprint] = deck_z[b.footprint]
    ch = channel_mask(b)
    # The channel: a two-step rounded lip (lit inner edge, shadowed wall), then the floor. The
    # stem's end at the bottom edge is kept open (no lip across it).
    lip2 = disc_erode(ch, 1)
    inner = disc_erode(ch, 2)
    open_end = b.box_mask(0, 270, b.W, b.H)
    lip2 |= ch & open_end & disc_erode(ch | open_end, 1)
    inner |= ch & open_end & disc_erode(ch | open_end, 2)
    step = deck_z - floor_z
    b.set_region(ch, None, b.m(166))
    b.height[ch] = (deck_z - step * 0.3)[ch]
    b.height[lip2] = (deck_z - step * 0.6)[lip2]
    b.set_region(inner, None, b.m("channel"))
    b.height[inner] = floor_z[inner]
    # The brick islands the channels loop round (the L-shapes with their fingers): raised brick
    # blocks with a chamfer step and lit top edges, as in the concept.
    d = lb.depth(b.footprint)
    rest = b.footprint & ~ch
    for ys, xs in lb.lt.components(rest):
        if d[ys, xs].min() > 14:
            isl = np.zeros_like(rest)
            isl[ys, xs] = True
            b.set_region(isl, ISLAND - 0.05, b.m("pave"))
            b.set_region(lb.erode(isl, 2), ISLAND, b.m(7))
    # The notch wall: a chamfered step up.
    x0, y0, x1, y1 = NOTCH_WALL
    b.raise_box(x0, y0, x1, y1, NOTCH_TOP - 0.05, b.m("pave"))
    b.raise_box(x0 + 2, y0 + 2, x1 - 2, y1 - 2, NOTCH_TOP, b.m(7))
    deck = b.terrace()

    # The rim: domed boulders in two rows (the outer big and tall), none across the stem's open end.
    def keep(px, py):
        return py < 268

    boulders(b, spacing=9.0, inset=4.5, size=(0.55, 0.80), height=(0.50, 0.66), sink=0.10, keep=keep,
             sides=(7, 9), jitter=0.3)
    boulders(b, spacing=8.0, inset=11.5, size=(0.42, 0.58), height=(0.40, 0.48), sink=0.08, keep=keep,
             sides=(6, 8), jitter=0.3)
    objects = b.objects(deck)
    b.check(objects)
    b.export(objects)


main()
