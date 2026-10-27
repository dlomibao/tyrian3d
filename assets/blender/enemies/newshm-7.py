"""Steel ledge with a glowing lamp (newshm.shp frames 7, 9, 11): a 3D version of its sprite.

Seen in episode 3 (level 3.15). A blue-steel ledge across the tile: a raised plate at the back
and one at the front with a dark channel between them, a bracket crossing the channel on the
right and, sunk in the channel, a lamp that glows from a dull ember to bright orange. The three
frames only change the glow, so one model covers them, with a lamp and socket for each frame
(frame_part). Frame 85 of the same catalogue entry is
a piece of the steel dome (assembly-newshm-45.py, model newshm-7-f2).

Run: blender --background --python assets/blender/enemies/newshm-7.py [-- --preview out.png]
"""

import sys
from pathlib import Path

import bmesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import lib_b073 as L  # noqa: E402

NAME = "newshm-7"
FRAMES = [7, 9, 11]


def build(sprite):
    coll = common.reset_collection(NAME)
    g = L.Grid(24, 28, sprite["frames"][2]["pixels"])
    m = L.Mats(NAME, sprite["colors"])
    bm = bmesh.new()
    L.floor(bm, g, m, sprite["colors"], rect=(0, 21, 24, 28))

    STEEL, LIGHT, DARK = m.metal(104), m.metal(106), m.metal(98)
    # Back plate (rows 0-5) with its seam, the channel (rows 6-16) and the front plate (rows 17-22).
    L.pillow(bm, L.rect(g, 0, 0, 24, 6), 0.0, 0.32, 0.4 * L.U, mat=STEEL, top_mat=m.metal(105))
    L.box(bm, g.ex(12), g.ey(6), g.ex(13), g.ey(0), 0.3, 0.325, mat=DARK)
    L.box(bm, g.ex(0), g.ey(16.5), g.ex(24), g.ey(5.5), 0.0, 0.14, mat=m.metal(97))
    L.pillow(bm, L.chamfer(g, -0.5, 16.5, 24.5, 23.5, 1.0), 0.0, 0.3, 0.4 * L.U, mat=STEEL, top_mat=LIGHT)
    L.box(bm, g.ex(12), g.ey(23), g.ex(13), g.ey(17), 0.28, 0.305, mat=DARK)
    # Pipe along the left of the channel and the bracket across it on the right (columns 20-23).
    L.tube(bm, [(g.x(1.6), g.ey(5.6), 0.16), (g.x(1.6), g.ey(16.4), 0.16)], 1.6 * L.U, sides=8, mat=STEEL)
    L.pillow(bm, L.rect(g, 20, 5.5, 23.5, 16.5), 0.0, 0.26, 0.4 * L.U, mat=STEEL, top_mat=LIGHT)
    obj = L.finish(NAME, bm, m, coll)
    # The lamp in a dark socket, opening wider each frame: a dull ember in a narrow socket on 7
    # (columns 10-13, rows 8-14), wider and brighter on 9 (columns 8-15) and widest on 11
    # (columns 7-17, rows 7-15).
    parts = [obj]
    for frame, c, r, rx, ry, sx, sy, glow in ((7, 11.5, 11.0, 2.2, 3.4, 3.4, 4.6, 117),
                                              (9, 11.5, 11.0, 4.0, 3.5, 5.2, 4.6, 120),
                                              (11, 12.2, 11.6, 5.0, 3.6, 6.0, 4.4, 120)):
        lbm = bmesh.new()
        L.dome(lbm, g.x(c), g.y(r), sx * L.U, sy * L.U, 0.05, z0=0.13, sides=16, rings=1,
               mat=m.metal(100), flat=0.85)
        L.ellipsoid(lbm, g.x(c), g.y(r), 0.17, rx * L.U, ry * L.U, 0.07, sides=16, rings=8,
                    mat=m.glow(glow, 3.5))
        parts.append(L.part(f"{NAME}-lamp-{frame}", lbm, m, coll, [frame]))
    return [(NAME, parts, L.sprites_with(L.common.repo_root(__file__), NAME, FRAMES))]


if __name__ == "__main__":
    L.run(NAME, build, __file__)
