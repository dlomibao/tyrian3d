"""Brown beetle pod under a dark housing (newshd.shp frames 245 over 281/283): a 3D version of
its sprites.

Seen in episodes 1-3 (levels 1.5, 1.6, 2.8, 3.15): in the fortress set (assembly-newshd-127)
newshd-245 always stands directly above newshd-281, at both ends of the middle rows, making one
24 x 56 px object. A dark grey housing with a red bar and a grey step sits at the back; in front
of it a big round brown shell with a red band across it and two glowing lamps in the band. The
two frames of newshd-281 only switch the lamps on (281) and off (283), so one model covers
them, with a set of lamps for each frame (frame_part).

Built whole in the pair's coordinates and cut into the two pieces with common.split_assembly.

Run: blender --background --python assets/blender/enemies/assembly-newshd-245.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "assembly-newshd-245"
PIECES = [["newshd-245"], ["newshd-281"]]


def build(sprite, g):
    coll = common.reset_collection(NAME)
    m = L.Mats("nshd245", sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    def rect(c0, r0, c1, r1):
        return [(g.ex(c0), g.ey(r1)), (g.ex(c1), g.ey(r1)), (g.ex(c1), g.ey(r0)), (g.ex(c0), g.ey(r0))]

    # Dark housing at the back (columns 4-15, rows 0-11), a red bar and a grey step in front.
    L.dome(bm, g.x(10.0), g.y(5.5), 6.4 * L.U, 6.2 * L.U, 0.44, z0=0.0, sides=20, rings=4,
           mat=m.metal(4), power=3.5, flat=0.35)
    L.loft_y(bm, g.x(7.6), [(g.ey(0.6), 1.0 * L.U, 0.03, 0.4), (g.ey(9.6), 1.0 * L.U, 0.03, 0.38)],
             sides=6, mat=m.metal(9))  # the highlight ridge down its left
    L.pillow(bm, rect(7, 11.6, 14, 14), 0.0, 0.3, 0.5 * L.U, mat=m.metal(162), top_mat=m.metal(67))
    L.pillow(bm, rect(6, 14, 15, 17), 0.0, 0.2, 0.5 * L.U, mat=m.metal(5), top_mat=m.metal(8))

    # The brown shell (columns 1-19, rows 20-44).
    cx, cy, rx, ry, h = g.x(10.0), g.y(32.5), 9.4 * L.U, 12.4 * L.U, 0.42
    L.dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=28, rings=7, mat=m.metal(23))
    zf = L.dome_z(cx, cy, rx, ry, h, z0=0.0)
    red = m.metal(72)
    # The red band (rows 28-34) and the dark seam down the back half, painted on its surface.
    L.painted(bm, g, 1, 26, 20, 36, zf, lambda i: red if 65 <= i <= 77 else None, skip=(-1, 1), max_run=2)
    L.painted(bm, g, 9, 36, 12, 44, zf, lambda i: m.metal(17) if i in (16, 17, 18) else None, skip=(-1, 1))
    # The two lamps in the band (columns 8-12, rows 30-35) with a dark bar between them.
    L.pillow(bm, rect(7.6, 29.6, 13.4, 36.0), h - 0.06, h + 0.04, 0.4 * L.U, mat=m.metal(163),
             top_mat=m.metal(163))
    # They glow on frame 281 and are off, the band's red, on 283.
    parts = []
    for frame, mat in ((281, m.glow(121, 3.5)), (283, m.metal(73))):
        lbm = bmesh.new()
        for r0, r1 in ((30.0, 31.9), (32.9, 35.6)):
            L.pillow(lbm, rect(8.0, r0, 13.0, r1), h + 0.02, h + 0.07, 0.4 * L.U, mat=mat)
        parts.append(L.part(f"lamps-{frame}", lbm, m, coll, [frame]))
    return L.finish(NAME, bm, m, coll), [], parts


if __name__ == "__main__":
    L.run_assembly(NAME, PIECES, build, __file__, 1, 2)
