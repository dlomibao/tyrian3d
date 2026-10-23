"""Three red capsules in a grey rack (newshs.shp frames 191-201): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.21, 1.5, 2.8, 3.15); in the fortress set (assembly-newshd-127) a
row of them makes a long red bank along the bottom. A raised grey rack across the tile holds
three upright red capsules with rounded ends. The frames only light up one capsule after
another, so one model covers them all.

Run: blender --background --python assets/blender/enemies/newshs-191.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshs-191"


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][0]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"])

    # The rack: a grey block across rows 4-23, its top a little lighter.
    rack = [(g.ex(0), g.ey(23.5)), (g.ex(24), g.ey(23.5)), (g.ex(24), g.ey(4)), (g.ex(0), g.ey(4))]
    L.pillow(bm, rack, 0.0, 0.1, 0.5 * L.U, mat=m.metal(8), top_mat=m.metal(7))
    # Light rims round each capsule's slot and the capsules themselves (columns 1-6, 9-14, 17-22).
    for c in (3.5, 11.5, 19.5):
        L.dome(bm, g.x(c), g.y(13.5), 3.6 * L.U, 9.6 * L.U, 0.04, z0=0.095, sides=16, rings=1,
               mat=m.metal(11), power=2.6, flat=0.8)
        L.loft_y(bm, g.x(c), [(g.ey(4.4), 0.0, 0.0, 0.14), (g.ey(5.0), 1.8 * L.U, 0.05, 0.14),
                              (g.ey(6.2), 2.8 * L.U, 0.09, 0.14), (g.ey(8.0), 3.1 * L.U, 0.11, 0.14),
                              (g.ey(19.0), 3.1 * L.U, 0.11, 0.14), (g.ey(20.8), 2.8 * L.U, 0.09, 0.14),
                              (g.ey(22.0), 1.8 * L.U, 0.05, 0.14), (g.ey(22.6), 0.0, 0.0, 0.14)],
                 sides=12, mat=m.glow(115, 2.0))
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
