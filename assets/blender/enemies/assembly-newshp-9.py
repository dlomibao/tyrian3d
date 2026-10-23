"""Cable derrick over a grey pad (newshp.shp frames 9, 11 over 1/3 over 39, 41): a 3D version of
its sprites.

Seen in episode 1 (level 1.5). Six 2x2 pieces (two across, three down) make one 48 x 84 px
object: a light grey pad on the stone floor with a brown-rimmed pit in its middle and brown
anchor rings round it; a dark mast leans back from the pit to a brown T-shaped cap (newshp-9
and newshp-11, over the transparent sky of the sprite), with a grey hook hanging from the cap
and cables fanning down from the mast to the anchors. In newshp-1 and newshp-3 the cables at
the seam between them sway a little from frame to frame; one model covers those frames.

Built whole and cut into the pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshp-9.py [-- --preview out.png]
"""

import math
import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshp-9"
PIECES = [["newshp-9", "newshp-11"], ["newshp-1", "newshp-3"], ["newshp-39", "newshp-41"]]
PAD = 0.12
ANCHORS = [(14.0, 35.5), (33.0, 35.0), (6.2, 46.2), (38.6, 46.6), (15.0, 58.4), (33.2, 58.6)]


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshp9", sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"], rect=(0, 28, 48, 84))
    tones = L.grey_tones(m, sprite["colors"])
    BRASS, DARK, CABLE = m.metal(25), m(1, metallic=0.2, roughness=0.6), m.metal(3)

    # The pad (columns 4-42, rows 28-56), its top painted with its light and dark plates.
    L.pillow(bm, L.chamfer(g, 3.5, 27.6, 43, 56.5, 1.5), 0.0, PAD, 0.5 * L.U, mat=m.stone(6), top_mat=m.stone(9))
    L.painted(bm, g, 4, 28, 43, 56, lambda x, y: PAD + 0.002, lambda i: tones(i) if 4 <= i <= 15 else None)

    # The pit in the middle (columns 15-24, rows 41-52) with its brown rim.
    pc, pr = 19.6, 46.6
    L.dome(bm, g.x(pc), g.y(pr), 3.6 * L.U, 4.0 * L.U, 0.01, z0=PAD, sides=16, rings=1, mat=DARK, flat=0.9)
    ring = [(g.x(pc) + 4.1 * L.U * math.cos(a), g.y(pr) + 4.6 * L.U * math.sin(a), PAD + 0.03)
            for a in [2 * math.pi * k / 16 for k in range(17)]]
    L.tube(bm, ring, 1.2 * L.U, sides=6, mat=BRASS, caps=False)
    # Anchor rings round the pad.
    for c, r in ANCHORS:
        L.dome(bm, g.x(c), g.y(r), 3.4 * L.U, 2.8 * L.U, 0.07, z0=PAD - 0.02, sides=12, rings=2,
               mat=BRASS, flat=0.5)
        L.dome(bm, g.x(c), g.y(r), 1.5 * L.U, 1.2 * L.U, 0.02, z0=PAD + 0.045, sides=10, rings=1,
               mat=m.metal(163), flat=0.8)

    # The mast, leaning back from the pit to the cap, and the cap (columns 11-30, rows 1-5).
    base, top = (g.x(21.0), g.y(42.0), PAD), (g.x(21.6), g.y(8.0), 0.56)
    L.tube(bm, [base, top], [3.4 * L.U, 3.0 * L.U], sides=8, mat=m.metal(3), flat=1.0)
    L.tube(bm, [(g.x(21.6), g.y(11.5), 0.53), (g.x(21.6), g.y(4.5), 0.6)], 1.8 * L.U, sides=8, mat=m.metal(22))
    cap = [(g.ex(11), g.ey(5.6)), (g.ex(29), g.ey(5.6)), (g.ex(31.4), g.ey(4.6)), (g.ex(31.4), g.ey(3.4)),
           (g.ex(26), g.ey(1.2)), (g.ex(11.5), g.ey(1.2)), (g.ex(10.6), g.ey(2.2))]
    L.pillow(bm, cap, 0.56, 0.66, 0.5 * L.U, mat=m.metal(22), top_mat=m.metal(23))
    # The grey hook hanging from the cap's left end (columns 11-17, rows 5-23).
    L.tube(bm, [(g.x(11.6), g.y(4.0), 0.58), (g.x(11.6), g.y(10.0), 0.5), (g.x(11.8), g.y(19.0), 0.4),
                (g.x(13.0), g.y(22.0), 0.36), (g.x(16.5), g.y(22.8), 0.34)], 0.8 * L.U, sides=6,
           mat=m.metal(7))
    # Cables from the mast down to the anchors and the pit's rim.
    for i, (c, r) in enumerate(ANCHORS + [(16.6, 42.4), (24.0, 42.4), (18.0, 33.0), (26.5, 32.0)]):
        t = 0.5 + 0.1 * (i % 4)
        start = tuple(b + (a - b) * t for a, b in zip(top, base))
        start = (start[0] + (c - 21) * 0.15 * L.U, start[1], start[2])
        L.tube(bm, [start, (g.x(c), g.y(r), PAD + 0.05)], 0.7 * L.U, sides=5, mat=CABLE)
    return L.finish(NAME, bm, m, coll), []


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 2, 3)
