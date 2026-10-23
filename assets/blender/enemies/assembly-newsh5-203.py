"""Falling fireball (newsh5.shp frames 203/205 and 241/243, assembly of 2 pieces): a 3D version
of its sprites.

Seen in episode 4 (levels 4.22 and 4.31). Two 2x2 enemies one above the other make one 24x54 px
fireball dropping down the screen: a round, white-hot head (newsh5-241) trailing a flame that
narrows to a thin red tip (newsh5-203). Its colours run from a dark red rim through orange and
yellow to a near-white core. The model is a teardrop of nested glowing shells, each narrower but
taller than the one round it, so that from above it shows the same bands of colour as the sprite.
Each piece's two frames only flicker the flame's edge, so one model covers both.

sprite.json's layout only places newsh5-241 (the head); the tail sits right on top of it (its
bottom row continues the head's top row), 28 px higher.

Run: blender --background --python assets/blender/enemies/assembly-newsh5-203.py [-- --preview out.png]
(the preview is the whole fireball; each piece also gets <piece>.png next to it).
"""

import sys
from pathlib import Path

import bmesh

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import common  # noqa: E402
import lib_b042 as lib  # noqa: E402

NAME = "assembly-newsh5-203"
ROOT = common.repo_root(__file__)
PIECES = ["newsh5-203", "newsh5-241"]

# Rows of the 24 x 56 px assembly: the tail (newsh5-203) is rows 0-27, the head (newsh5-241) rows
# 28-55. Each shell: (row, centre column, half width px); its half height is a fixed share of the
# outer shell's half width at that row, larger for inner shells, so they bulge out of the outer.
OUTER = [(-0.4, 11.5, 0.0), (0.5, 11.5, 0.7), (6.5, 11.6, 1.0), (7.5, 11.5, 2.0), (12.5, 11.8, 2.6),
         (13.5, 11.6, 4.0), (16.5, 11.5, 4.9), (21.5, 11.5, 5.0), (22.5, 11.0, 5.5), (26.5, 11.0, 6.0),
         (27.5, 11.0, 6.6), (29.0, 11.0, 7.4), (35.5, 11.0, 7.5), (38.0, 11.0, 8.0), (41.0, 11.0, 8.5),
         (43.5, 11.0, 8.2), (46.5, 11.0, 7.5), (49.5, 10.8, 6.6), (51.0, 10.8, 5.6), (52.0, 11.0, 4.6),
         (53.0, 11.0, 3.5), (53.8, 11.0, 2.0), (54.2, 11.0, 0.0)]
ORANGE = [(7.0, 11.5, 0.0), (8.0, 11.6, 0.9), (13.0, 11.8, 1.6), (18.0, 11.6, 2.6), (22.5, 11.4, 3.6),
          (27.0, 11.2, 4.6), (30.0, 11.0, 5.8), (41.0, 11.0, 7.0), (46.5, 11.0, 6.0), (49.5, 10.8, 5.0),
          (51.5, 11.0, 3.6), (53.0, 11.0, 1.8), (53.6, 11.0, 0.0)]
YELLOW = [(17.0, 11.6, 0.0), (18.5, 11.6, 1.0), (21.5, 11.8, 1.8), (24.5, 11.4, 2.6), (27.5, 11.0, 3.8),
          (30.5, 11.0, 5.0), (41.0, 11.0, 6.2), (46.0, 11.0, 5.2), (49.0, 11.0, 4.0), (51.0, 11.0, 2.4),
          (52.0, 11.0, 0.0)]
WHITE = [(20.5, 11.8, 0.0), (22.0, 11.9, 0.9), (25.0, 11.4, 1.6), (28.0, 11.2, 3.0), (32.0, 11.2, 4.3),
         (37.0, 11.0, 5.0), (42.0, 11.0, 5.0), (45.0, 11.2, 4.0), (47.5, 11.0, 2.4), (49.0, 11.0, 0.0)]


def outer_width(r):
    """The outer shell's half width (px) at row r (linear between its sections)."""
    for (r0, _, w0), (r1, _, w1) in zip(OUTER, OUTER[1:]):
        if r0 <= r <= r1:
            return w0 + (w1 - w0) * (r - r0) / (r1 - r0)
    return 0.0


def build(sprite):
    g = lib.Grid(24, 56)
    coll = common.reset_collection(NAME)
    pal = lambda i, **kw: common.palette_material(sprite, i, NAME, **kw)  # noqa: E731
    mats = [
        pal(119, roughness=0.6, metallic=0.0, emission_strength=2.5),  # 0 red rim
        pal(121, roughness=0.6, metallic=0.0, emission_strength=3.0),  # 1 orange
        pal(124, roughness=0.6, metallic=0.0, emission_strength=4.0),  # 2 yellow
        pal(127, roughness=0.6, metallic=0.0, emission_strength=5.0),  # 3 white-hot core
    ]
    bm = bmesh.new()
    for mat, (shell, share) in enumerate(((OUTER, 0.2), (ORANGE, 0.29), (YELLOW, 0.35), (WHITE, 0.41))):
        path = [(c, r, 0.0, w, share * outer_width(r) / 12 if w else 0.0) for r, c, w in shell]
        lib.sweep(bm, g, path, sides=12, mat=mat)
    return lib.to_object(NAME, bm, mats, coll)


def main():
    sprite = lib.merged_sprite(ROOT, PIECES)
    obj = build(sprite)
    # The assembly's centre (14 px above the head's centre) is the origin; the tail is 28 px above
    # the head, in the same column.
    layout = [("newsh5-203", 0, -14), ("newsh5-241", 0, 14)]
    lib.export_assembly(ROOT, obj, layout, size=4)


if __name__ == "__main__":
    main()
