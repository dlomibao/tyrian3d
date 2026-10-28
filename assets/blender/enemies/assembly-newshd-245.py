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

    # Dark housing at the back (columns 3-18, rows 0-11): a drum lying along the column, round in
    # section (the highlight streak down its left, the dark right side), about 10 px tall; a red
    # bar and a grey step in front of it.
    # Sections (row edge, half width, half height in px); each sits on the floor.
    hx, hp = g.x(10.0), 2.3
    hsec = [(0.2, 3.4, 1.2), (0.9, 6.0, 3.8), (2.2, 7.3, 5.0), (9.6, 7.3, 5.0), (11.0, 6.6, 4.4), (11.8, 5.0, 3.0)]
    L.loft_y(bm, hx, [(g.ey(r), w * L.U, hh * L.U, hh * L.U) for r, w, hh in hsec], sides=20, mat=m.metal(4),
             power=hp)

    def housing_z(x, y):
        r = (g.h / 2 - y / L.U)  # row edge
        for (r0, w0, h0), (r1, w1, h1) in zip(hsec, hsec[1:]):
            if r0 <= r <= r1:
                t = (r - r0) / (r1 - r0)
                w, hh = (w0 + (w1 - w0) * t) * L.U, (h0 + (h1 - h0) * t) * L.U
                u = min(1.0, abs(x - hx) / w)
                return hh + hh * (1 - u ** hp) ** (1 / hp) + 0.015
        return 0.0

    def inside_housing(c, r):
        for dc in (0, 1):
            for dr in (0, 1):
                rr = r + dr
                if not 1.0 <= rr <= 11.0:
                    return False
                w = next(w0 + (w1 - w0) * (rr - r0) / (r1 - r0) for (r0, w0, _), (r1, w1, _) in zip(hsec, hsec[1:])
                         if r0 <= rr <= r1)
                if abs(g.ex(c + dc) - hx) > 0.9 * w * L.U:
                    return False
        return True

    # Its face (the highlight streak down its left, the dark right side) painted from the sprite.
    greys = {1: 1, 2: 1, 3: 3, 4: 3, 5: 5, 6: 5, 7: 7, 8: 7, 9: 9, 10: 9, 11: 11, 12: 11, 14: 11}
    face = L.Grid(g.w, g.h, [[v if v in greys and inside_housing(c, r) else -1 for c, v in enumerate(row)]
                             for r, row in enumerate(g.pixels)])
    L.painted(bm, face, 3, 0, 19, 12, housing_z, lambda i: m.metal(greys[i]))
    L.pillow(bm, rect(7, 11.6, 14, 14), 0.0, 0.42, 0.5 * L.U, mat=m.metal(162), top_mat=m.metal(67))
    L.pillow(bm, rect(6, 14, 15, 17), 0.0, 0.25, 0.5 * L.U, mat=m.metal(5), top_mat=m.metal(8))

    # The brown shell (columns 1-19, rows 20-44): round, an egg cut lengthwise, about 11 px tall.
    cx, cy, rx, ry, h = g.x(10.0), g.y(32.5), 9.4 * L.U, 12.4 * L.U, 0.92
    L.dome(bm, cx, cy, rx, ry, h, z0=0.0, sides=28, rings=7, mat=m.metal(20))
    zf = L.dome_z(cx, cy, rx, ry, h, z0=0.0)
    # Its face painted from the sprite inside its edge: the browns of the shell, the red band
    # across it (rows 28-34), the dark seam down its back half.
    tones = {16: 17, 17: 17, 18: 17, 19: 20, 20: 20, 21: 21, 22: 21, 23: 23, 24: 23, 25: 25, 26: 25, 29: 25,
             65: 67, 66: 67, 67: 67, 68: 68, 69: 68, 70: 70, 71: 70, 72: 72, 73: 72, 74: 74, 76: 74, 77: 74}

    def on_shell(c, r):
        return all(((g.ex(c + dc) - cx) / rx) ** 2 + ((g.ey(r + dr) - cy) / ry) ** 2 < 0.88
                   for dc in (0, 1) for dr in (0, 1))

    shell = L.Grid(g.w, g.h, [[v if v in tones and r >= 19 and on_shell(c, r) else -1 for c, v in enumerate(row)]
                              for r, row in enumerate(g.pixels)])
    L.painted(bm, shell, 0, 19, 21, 46, zf, lambda i: m.metal(tones[i]))
    # The two lamps in the band (columns 8-12, rows 30-35) with a dark bar between them.
    L.pillow(bm, rect(7.6, 29.6, 13.4, 36.0), h - 0.2, h + 0.04, 0.4 * L.U, mat=m.metal(163),
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
