"""Three red capsules in a grey rack (newshs.shp frames 191-201): a 3D version of its sprite.

Seen in episodes 1-3 (levels 1.21, 1.5, 2.8, 3.15); in the fortress set (assembly-newshd-127) a
row of them makes a long red bank along the bottom. A raised grey rack across the tile holds
three upright red capsules with rounded ends, round in section (as tall as they are wide). The frames only light up one capsule after
another, so one model covers them all, each capsule's colour following the frame
(palette_material frames=).

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
    L.pillow(bm, rack, 0.0, 0.1, 0.5 * L.U, mat=m(7, metallic=0.4, roughness=0.4), top_mat=m(7, metallic=0.4, roughness=0.4))
    # Light rims round each capsule's slot and the capsules themselves (columns 1-6, 9-14, 17-22).
    # Each capsule lights up (117) and brightens (119) in turn: the right one on 191/193, the
    # middle one on 195/197, the left one on 199/201.
    for c, lit in ((3.5, (199, 201)), (11.5, (195, 197)), (19.5, (191, 193))):
        L.dome(bm, g.x(c), g.y(13.5), 3.6 * L.U, 9.6 * L.U, 0.04, z0=0.095, sides=16, rings=1,
               mat=m(11, metallic=0.75, roughness=0.3), power=2.6, flat=0.8)
        # Round capsules about 6 px across and 6 px tall, standing on the floor through the rack.
        zc = 0.25
        L.loft_y(bm, g.x(c), [(g.ey(4.4), 0.0, 0.0, zc), (g.ey(5.0), 1.8 * L.U, 0.13, zc),
                              (g.ey(6.2), 2.8 * L.U, 0.21, zc), (g.ey(8.0), 3.1 * L.U, 0.245, zc),
                              (g.ey(19.0), 3.1 * L.U, 0.245, zc), (g.ey(20.8), 2.8 * L.U, 0.21, zc),
                              (g.ey(22.0), 1.8 * L.U, 0.13, zc), (g.ey(22.6), 0.0, 0.0, zc)],
                 sides=12, mat=m.anim(114, f"capsule{lit[0]}", {lit[0]: 117, lit[1]: 119}, roughness=0.12,
                                      emission_strength=1.0))
    obj = L.finish(NAME, bm, m, coll)
    return [(NAME, [obj], sprite["sprites"])]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
