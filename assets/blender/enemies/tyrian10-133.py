"""Cyan crystal pyramid (tyrian.shp #10 frame 133): a 3D version of its sprite.

Seen in episode 4 (level 10). A small blue-green crystal seen from above: a square diamond with
its corners up, down, left and right, rising to a bright point in the middle along four light
ridges. Built as a bipyramid (a low point underneath) with narrow ridge facets along its edges,
the darker lower facets in the sprite's darker blues and a glowing tip.

Run: blender --background --python assets/blender/enemies/tyrian10-133.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b039 as lib  # noqa: E402

NAME = "tyrian10-133"
MODEL = f"enemies/{NAME}"
ROOT = common.repo_root(__file__)
U = 1 / 12

# The apex sits over column 6, row 7 of the 12x14 tile.
CX, CY = lib.px(6, 12), lib.row(7, 14)


def ring(radius, z, ridge):
    """12 points round the diamond at height z: for each corner (right, up, left, down) a point
    `ridge` px before it along the edge, the corner, and a point `ridge` px after it."""
    pts = []
    for k in range(4):
        a = math.pi / 2 * k
        c = (math.cos(a), math.sin(a))
        prev = (math.cos(a - math.pi / 2), math.sin(a - math.pi / 2))
        nxt = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
        corner = (c[0] * radius, c[1] * radius)
        for d in (prev, None, nxt):
            if d is None:
                p = corner
            else:  # along the edge toward the neighbouring corner
                ex, ey = d[0] * radius - corner[0], d[1] * radius - corner[1]
                n = math.hypot(ex, ey)
                p = (corner[0] + ex / n * ridge, corner[1] + ey / n * ridge)
            pts.append((CX + p[0], CY + p[1], z))
    return pts


def build(sprite):
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(213, metallic=0.3, roughness=0.2),  # 0 upper facets
        pal(216, metallic=0.3, roughness=0.15),  # 1 light ridges
        pal(210, metallic=0.3, roughness=0.3),  # 2 dark lower facets
        pal(212, metallic=0.3, roughness=0.25),  # 3 lower ridges
        pal(221, emission_strength=3.0),  # 4 glowing tip
        pal(211, metallic=0.3, roughness=0.25),  # 5 the two facets toward the bottom of the screen
    ]
    FACET, RIDGE, LOW, LOW_RIDGE, TIP, SHADE = range(6)
    up = [RIDGE, RIDGE, FACET, RIDGE, RIDGE, FACET, RIDGE, RIDGE, SHADE, RIDGE, RIDGE, SHADE]
    low = [LOW_RIDGE, LOW_RIDGE, LOW] * 4
    bm = bmesh.new()
    R = 5.6
    rings = [
        [(CX, CY, 3.3 * U)],
        ring(1.3 * U, 2.6 * U, 0.6 * U),
        ring(R * 0.55 * U, 1.5 * U, 0.9 * U),
        ring(R * U, 0.0, 0.7 * U),
        ring(R * 0.5 * U, -1.0 * U, 0.6 * U),
        [(CX, CY, -1.9 * U)],
    ]
    lib.ring_loft(bm, rings, [TIP, up, up, low, low])
    return common.mesh_object(NAME, bm, mats, coll, smooth=False)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], MODEL, sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite)


if __name__ == "__main__":
    main()
