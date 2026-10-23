"""Flame bowl (newsh5.shp frames 156 and 158): a 3D version of their sprites.

Seen in episode 4 (level 25). Two 2x2 pieces side by side make one 48x28 px blaze: a crescent of
fire, rounded underneath and white-hot in its middle, with eight tongues licking up from it (tall
curling horns at both ends, shorter flickers between them).

The whole blaze is built once in assembly coordinates: a crescent body swept along its midline
and a tapered, flattened tongue up to each tip. Each face takes the fire colour of the pixels under
it (glowing more the brighter it is), then common.split_assembly cuts it into newsh5-156 (left)
and newsh5-158 (right). One frame each.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-156.py [-- --preview out.png]
(the preview is the whole blaze; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b051 as lib  # noqa: E402

NAME = "assembly-newsh5-156"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-156", "newsh5-158"]

# The crescent body, left to right: (column, top row, bottom row, half height). Its top follows the
# bottoms of the notches between the tongues.
BODY = [(1.6, 7.0, 13.0, 0.0), (2.2, 6.0, 15.4, 0.1), (4.0, 6.0, 18.2, 0.14), (7.0, 6.5, 21.2, 0.17),
        (10.0, 7.0, 23.2, 0.19), (14.0, 6.8, 25.2, 0.21), (18.5, 8.2, 25.4, 0.22), (24.0, 10.6, 25.4, 0.22),
        (29.5, 8.2, 25.4, 0.22), (34.5, 6.8, 25.2, 0.21), (38.0, 7.0, 23.2, 0.19), (41.0, 6.5, 21.2, 0.17),
        (44.0, 6.0, 18.2, 0.14), (45.8, 6.0, 15.4, 0.1), (46.4, 7.0, 13.0, 0.0)]

# Tongues from inside the body up to their tips: spine points (column, row, half width px).
TONGUES = [
    [(4.2, 11.0, 3.2), (4.0, 6.5, 2.8), (3.8, 4.5, 2.3), (3.4, 2.4, 1.4), (3.1, 1.0, 0.8), (3.0, -0.4, 0.0)],
    [(10.4, 11.0, 3.4), (10.2, 6.5, 2.9), (9.8, 4.5, 2.2), (9.0, 2.4, 1.2), (8.6, 1.2, 0.6), (8.3, 0.5, 0.0)],
    [(16.0, 11.0, 2.8), (16.0, 7.5, 2.0), (16.0, 5.6, 1.2), (16.0, 4.5, 0.6), (16.0, 3.5, 0.0)],
    [(21.3, 11.5, 2.8), (21.3, 8.5, 2.0), (21.5, 6.6, 1.3), (21.8, 5.5, 0.6), (22.0, 4.5, 0.0)],
    [(27.0, 11.5, 2.8), (27.0, 8.5, 2.0), (26.7, 6.6, 1.3), (26.4, 5.5, 0.6), (26.2, 4.5, 0.0)],
    [(32.6, 11.0, 2.9), (32.5, 7.5, 2.1), (32.3, 5.6, 1.3), (32.1, 4.5, 0.6), (32.0, 3.5, 0.0)],
    [(38.2, 11.0, 3.4), (38.4, 6.5, 2.9), (38.8, 4.5, 2.2), (39.6, 2.4, 1.2), (40.0, 1.2, 0.6), (40.2, 0.5, 0.0)],
    [(44.0, 11.0, 3.2), (44.3, 6.5, 2.6), (44.6, 4.5, 2.0), (45.0, 2.4, 1.4), (45.2, 1.0, 0.8), (45.3, -0.4, 0.0)],
]


def resample(points, n):
    """n+1 points evenly along a polyline of tuples (linear in each component)."""
    import math
    seg = [math.dist(a[:2], b[:2]) for a, b in zip(points, points[1:])]
    total = sum(seg)
    out = []
    for k in range(n + 1):
        d = total * k / n
        for i, s in enumerate(seg):
            if d <= s or i == len(seg) - 1:
                t = min(1.0, d / s) if s else 0.0
                out.append(tuple(a + (b - a) * t for a, b in zip(points[i], points[i + 1])))
                break
            d -= s
    return out


def body_top(c, r):
    """Height of the body's upper surface at pixel (c, r)."""
    import math
    for (c0, t0, b0, h0), (c1, t1, b1, h1) in zip(BODY, BODY[1:]):
        if c0 <= c <= c1:
            k = (c - c0) / (c1 - c0)
            t, b, h = t0 + (t1 - t0) * k, b0 + (b1 - b0) * k, h0 + (h1 - h0) * k
            u = (r - (t + b) / 2) / ((b - t) / 2)
            return h * math.sqrt(max(0.0, 1 - u * u))
    return 0.0


def build(g, sprite):
    coll = common.reset_collection(NAME)
    mats = lib.fire_materials(sprite, "nsh5_156")
    bm = bmesh.new()

    # Crescent body, swept left to right with its width across the sweep.
    path = [(c, (t + b) / 2, 0.0, (b - t) / 2, h) for c, t, b, h in resample(BODY, 30)]
    path[0] = (*path[0][:3], 0.0, 0.0)
    path[-1] = (*path[-1][:3], 0.0, 0.0)
    lib.sweep(bm, g, path, sides=12, mat=2)

    # Tongues, flattened and tapering to a point; each rises out of the body as a low lobe, so
    # the fire reads as strands licking up from the blaze.
    for spine in TONGUES:
        c0, r0, w0 = spine[0]
        pts = resample([(c0 + (24 - c0) * 0.12, 18.0, 2.2)] + spine, 12)
        path = []
        for c, r, w in pts:
            hh = 0.12 * (w / 3.2) ** 0.6
            path.append((c, r, max(0.03, body_top(c, r) - 0.6 * hh), w + 0.5 * (w > 0), hh))
        lib.sweep(bm, g, path, sides=8, mat=3, power=0.8)

    lib.paint_soft(bm, g, lib.fire_slot, len(mats), pct=0.6, crest=0.9, flank=-1.0)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    g, layout, sprite = lib.assembly(ROOT, PIECES)
    obj = build(g, sprite)
    pieces = common.split_assembly(obj, layout)
    for name in PIECES:
        data = common.load_sprite(ROOT, name)
        common.export_sprite_model(ROOT, [pieces[name]], f"enemies/{name}", data["sprites"])
    lib.preview_assembly(ROOT, obj, pieces, g, sprite, size=4)


if __name__ == "__main__":
    main()
