"""Grey dome with a green window (newshs.shp frames 11, 125, 277): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.21, 1.5, 1.6, 2.8, 3.15). A light grey dome stands at the back
of the tile on the stone floor, casting a dark shadow to its right; a ribbed dark wall runs
down from its front, and a square window on top lights up green. The frames only switch the
window on and off, so one model covers them all (the window is modelled lit).

Run: blender --background --python assets/blender/enemies/newshs-11.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshs-11"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][1]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # Ribbed wall below the dome (columns 5-17, rows 12-22).
    wall = [(g.ex(4.5), g.ey(22.5)), (g.ex(17.5), g.ey(22.5)), (g.ex(18.5), g.ey(12)), (g.ex(3.5), g.ey(12))]
    L.pillow(bm, wall, 0.0, 0.16, 0.5 * L.U, mat=m.stone(4), top_mat=m.stone(3))
    for c in (6.5, 9.0, 10.5, 12.5, 15.0):
        L.loft_y(bm, g.x(c), [(g.ey(12), 0.5 * L.U, 0.03, 0.16), (g.ey(22.3), 0.5 * L.U, 0.03, 0.16)],
                 sides=6, mat=m.metal(6), smooth=True)
    # The dome (columns 3-19, rows 0-14).
    L.dome(bm, g.x(11.0), g.y(6.5), 8.4 * L.U, 7.6 * L.U, 0.36, z0=L.FLOOR - 0.01, sides=24, rings=5,
           mat=m.metal(10), power=2.2)
    # Its rim, slightly darker, and the window (columns 9-14, rows 2-5) in a dark frame.
    L.dome(bm, g.x(11.0), g.y(6.5), 8.6 * L.U, 7.8 * L.U, 0.05, z0=L.FLOOR - 0.01, sides=24, rings=1,
           mat=m.metal(7), power=2.2, flat=0.95)
    frame = [(g.ex(8.6), g.ey(6.4)), (g.ex(15.4), g.ey(6.4)), (g.ex(15.4), g.ey(1.6)), (g.ex(8.6), g.ey(1.6))]
    L.pillow(bm, frame, 0.26, 0.4, 0.3 * L.U, mat=m.metal(5), top_mat=m.metal(4))
    win = [(g.ex(9.2), g.ey(5.8)), (g.ex(14.8), g.ey(5.8)), (g.ex(14.8), g.ey(2.2)), (g.ex(9.2), g.ey(2.2))]
    L.pillow(bm, win, 0.38, 0.42, 0.4 * L.U, mat=m.glow(201, 3.0))
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
