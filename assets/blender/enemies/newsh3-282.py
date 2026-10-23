"""Rock spur (newsh3.shp frame 282): a 3D version of its sprite.

Seen in episode 4 (levels 4.2 and 4.29), on the ground. A wedge of brown rock filling the left
of its block and ending in a ragged diagonal edge from the top left to the bottom right: a lit
flat top along the left side, a pale crest running down from the top, and a shaded, cracked
slope falling away to the right towards the edge; the bottom left corner dips into shadow.

Built as one surface over the wedge (rows of vertices spread between the left side and the
diagonal edge), its height falling from the crest to the edge, the cracks traced from the sprite
pressed in as dark grooves, and the faces coloured by region (lit top, pale crest, shaded slope,
dark foot); the sides drop to the ground.

Run: blender --background --python assets/blender/enemies/newsh3-282.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
import lib_b076 as lib  # noqa: E402

NAME = "newsh3-282"
ROOT = common.repo_root(__file__)
F = lib.Frame(24, 28)

# The diagonal edge: the right end (pixel edge column) of each row edge, smoothed from the sprite.
EDGE = [(0, 6.2), (3, 9.0), (6, 13.8), (9, 15.6), (12, 16.6), (15, 17.6), (18, 18.8), (20, 18.6),
        (24, 20.2), (27, 22.6), (28, 23.4)]
COLS = 16  # vertices across each row


def right_edge(r):
    for (r0, c0), (r1, c1) in zip(EDGE, EDGE[1:]):
        if r <= r1:
            return c0 + (c1 - c0) * (r - r0) / (r1 - r0)
    return EDGE[-1][1]


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


CRACKS = [[(9.6, 9.0), (10.2, 12.8), (9.8, 16.2), (10.6, 20.0), (11.8, 21.6), (13.4, 24.0), (13.6, 25.8)],
          [(12.2, 21.6), (15.2, 23.6), (15.6, 27.6)], [(5.6, 0.6), (8.4, 5.2)], [(13.0, 6.2), (14.6, 9.6)]]


def crest(r):
    """The pale crest line's column at row r (it runs down from the top left)."""
    return 0.5 + 0.45 * min(r, 16.0)


def crack_dist(c, r):
    best = 99.0
    for line in CRACKS:
        for (c0, r0), (c1, r1) in zip(line, line[1:]):
            dx, dy = c1 - c0, r1 - r0
            t = max(0.0, min(1.0, ((c - c0) * dx + (r - r0) * dy) / (dx * dx + dy * dy)))
            best = min(best, math.hypot(c - c0 - t * dx, r - r0 - t * dy))
    return best


def build(sprite):
    coll = common.reset_collection(NAME)
    tag = NAME
    pal = lambda i: common.palette_material(sprite, i, tag, metallic=0.0, roughness=0.95)  # noqa: E731
    mats = [pal(21), pal(23), pal(22), pal(20), pal(19), pal(18), pal(17)]
    TOP, CREST, CREST2, SLOPE, LOW, EDGE_, CRACK = range(7)

    def colour(c, r):
        d = right_edge(r) - c
        if crack_dist(c, r) < 0.55 and d > 0.8:
            return CRACK
        if d < 1.3:
            return EDGE_
        k = c - crest(r)
        if r < 16.5:
            if abs(k) < 0.6:
                return CREST
            if -1.4 < k < 1.2:
                return CREST2
            return TOP if k < 0 else (SLOPE if d > 3.5 else LOW)
        if c < 2.6 + (r - 16) * 0.12:
            return LOW if r < 25 else SLOPE
        return TOP if k < 3.2 else (SLOPE if d > 3.0 else LOW)

    def height(c, r):
        d = right_edge(r) - c  # distance in from the diagonal edge, px
        z = 0.05 + 0.33 * smooth(d / 9.0)
        # The bottom left corner dips into shadow.
        z -= 0.1 * smooth((r - 16) / 8) * smooth((4 - c) / 4)
        # Cracks pressed in, and a gentle swell along the crest.
        z -= 0.04 * smooth(1 - crack_dist(c, r) / 1.0) * smooth(d / 1.5)
        z += 0.03 * math.exp(-((c - crest(r)) ** 2) / 4.0)
        # Rough stone.
        z += 0.012 * math.sin(1.7 * c + 0.6 * r) * math.cos(1.3 * r - 0.4 * c) * smooth(d / 2)
        return max(0.02, z)

    bm = bmesh.new()
    grid = []
    for r in range(29):
        re = right_edge(r)
        grid.append([bm.verts.new((F.ex(re * i / COLS), F.ey(r), height(re * i / COLS, r)))
                     for i in range(COLS + 1)])
    for r in range(28):
        for i in range(COLS):
            a, b, c, d = grid[r + 1][i], grid[r + 1][i + 1], grid[r][i + 1], grid[r][i]
            f = bm.faces.new((a, b, c, d))
            cx = (a.co.x + b.co.x + c.co.x + d.co.x) / 4
            cy = (a.co.y + b.co.y + c.co.y + d.co.y) / 4
            f.material_index = colour(cx * 12 + 12, 14 - cy * 12)
            f.smooth = True

    # Sides down to the ground: the diagonal edge, the left side, the top and the bottom.
    def wall(top_verts, mat):
        for v0, v1 in zip(top_verts, top_verts[1:]):
            g0 = bm.verts.new((v0.co.x, v0.co.y, 0.0))
            g1 = bm.verts.new((v1.co.x, v1.co.y, 0.0))
            f = bm.faces.new((v0, g0, g1, v1))
            f.material_index = mat
            f.smooth = False

    dark = EDGE_
    wall([grid[r][COLS] for r in range(28, -1, -1)], dark)  # bottom to top along the right edge
    wall([grid[r][0] for r in range(29)], dark)  # top to bottom along the left
    wall([grid[0][i] for i in range(COLS, -1, -1)], dark)  # right to left along the top
    wall([grid[28][i] for i in range(COLS + 1)], dark)  # left to right along the bottom

    return lib.to_object(NAME, bm, mats, coll)


def main():
    lib.run(ROOT, NAME, lambda sprite: [(NAME, [build(sprite)], sprite["sprites"])], __file__)


if __name__ == "__main__":
    main()
