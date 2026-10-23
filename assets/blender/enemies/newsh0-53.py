"""Blue rock wedge (newsh0.shp frame 53): a 3D version of its sprite.

Seen in episode 2 (level 2.12). The bottom-right corner of a mottled blue-steel mass: it fills
the tile's top-left and ends in a long diagonal edge from the top right down to the bottom left,
with a short grey rim at the top of that edge. Its top and left sides run off the tile (it
continues in the sprites next to it), so it stays full height there; toward the diagonal edge
it rounds down. The top is a rough faceted surface, each facet coloured from the mottled sprite
under it.

Run: blender --background --python assets/blender/enemies/newsh0-53.py [-- --preview out.png]
"""

import math
import random
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_b025 as lib  # noqa: E402
from lib_b025 import common  # noqa: E402

NAME = "newsh0-53"
ROOT = common.repo_root(__file__)
G = lib.Grid(24, 28)
# The diagonal edge: (pixel-edge row, pixel-edge column) points from the top right down.
EDGE = [(0, 18), (4, 16.5), (12, 13), (15.5, 11), (24.5, 2), (25.4, 0.6)]


def edge_col(r):
    for (r0, c0), (r1, c1) in zip(EDGE, EDGE[1:]):
        if r <= r1:
            return c0 + (c1 - c0) * (r - r0) / (r1 - r0)
    return EDGE[-1][1]


def build(sprite):
    coll = common.reset_collection(NAME)
    m = lib.Mats(NAME, sprite["colors"])
    shades = {i: m(i, metallic=0.2, roughness=0.65) for i in (50, 52, 54, 56, 58)}
    RIM = m(3, metallic=0.6, roughness=0.4)
    bm = bmesh.new()

    rnd = random.Random(53)
    noise = {}

    def height(c, r):
        d = (edge_col(r) - c) * 0.8  # roughly the distance to the diagonal edge, in px
        z = -0.04 + 0.16 * math.sin(min(d / 4.5, 1.0) * math.pi / 2)
        if d > 0.8:
            key = (round(c, 2), round(r, 2))
            noise.setdefault(key, rnd.uniform(-0.014, 0.014))
            z += noise[key]
        return z

    rows = [r * 1.5 for r in range(17)] + [25.3]
    top = lib.span_mass(bm, G, rows, lambda r: (0, edge_col(r)), height, -0.14, ncols=10, mat=shades[54])
    lib.paint_faces(bm, top, G, sprite["frames"][0]["pixels"],
                    lambda i: shades[min(shades, key=lambda k: abs(k - i))] if 48 <= i <= 62 else None)
    # Grey rim at the top of the diagonal edge (columns 16-17, rows 0-3).
    lib.sweep(bm, G, [(16.9, -0.4, 0.0, 0.8, 0.07), (16.6, 1.5, 0.0, 0.8, 0.07), (16.0, 3.6, -0.01, 0.6, 0.05),
                      (15.6, 4.4, -0.02, 0.0, 0.0)], sides=8, mat=RIM)
    lib.clip(bm, [((0, G.ey(0), 0), (0, 1, 0))])
    return lib.to_object(NAME, bm, m.list, coll)


def main():
    sprite = common.load_sprite(ROOT, NAME)
    obj = build(sprite)
    common.export_sprite_model(ROOT, [obj], f"enemies/{NAME}", sprite["sprites"])
    lib.preview([obj], ROOT, NAME, sprite["frames"][0]["image"])


if __name__ == "__main__":
    main()
