"""Glowing red block in a grey clamp (newshs.shp frames 229-235): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.21, 1.5, 1.6, 2.8, 3.15), two of them side by side in the
fortress set (assembly-newshd-127). A big rounded block of glowing red crystal sits in a dark
clamp with a grey bracket behind it. The frames only pulse its glow, so one model covers them.

Run: blender --background --python assets/blender/enemies/newshs-229.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshs-229"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # Grey bracket behind (columns 8-15, rows 2-4) and the dark clamp jaws on the flanks.
    L.pillow(bm, L.rect(g, 7.5, 1.6, 16.5, 4.6), 0.0, 0.2, 0.5 * L.U, mat=m.metal(5), top_mat=m.metal(3))
    L.pillow(bm, L.rect(g, 1, 8, 4.5, 19), 0.0, 0.16, 0.5 * L.U, mat=m.metal(3), top_mat=m.metal(2))
    L.pillow(bm, L.rect(g, 18.5, 8, 22, 19), 0.0, 0.16, 0.5 * L.U, mat=m.metal(3), top_mat=m.metal(2))
    L.pillow(bm, L.rect(g, 7.5, 23.5, 16.5, 25.6), 0.0, 0.12, 0.5 * L.U, mat=m.metal(2))
    # The crystal (columns 4-18, rows 4-23): rounded, its top a shade lighter.
    L.dome(bm, g.ex(11.5), g.ey(14), 7.6 * L.U, 10.2 * L.U, 0.27, z0=0.0, sides=24, rings=4,
           mat=m.glow(118, 2.5), power=4.0, flat=0.45)
    L.dome(bm, g.ex(12.2), g.ey(13.2), 3.2 * L.U, 4.6 * L.U, 0.03, z0=0.255, sides=16, rings=2,
           mat=m.glow(116, 2.0), power=2.5, flat=0.6)  # the darker swirl in its heart
    # A bright rim along its upper-left edges (the highlight at columns 5-6 and rows 5-6).
    L.tube(bm, [(g.x(5.6), g.y(21.0), 0.215), (g.x(5.6), g.y(6.4), 0.24), (g.x(7.0), g.y(5.4), 0.24),
                (g.x(14.5), g.y(5.4), 0.215)], 0.5 * L.U, sides=6, mat=m.glow(123, 3.5), flat=0.5)
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
